"""Phase 3 experiment runner.

This module prepares and runs individual cases only when explicitly invoked. Importing
it or running the test suite never starts an experiment.
"""

import argparse
import hashlib
import json
import multiprocessing
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from configs import load_security_config
from pipeline.graph import run_pipeline
from security.auth import check_authentication

from phase3.dataset import PHASE3_DATASET_VERSION, load_cases
from phase3.boundary import InvocationEvidence
from phase3.evaluators import evaluate_attack_case, summarize_metrics

ROOT = Path(__file__).resolve().parent.parent
MODEL_ID = "openai/gpt-oss-120b"
DEFAULT_TIMEOUT_SECONDS = 120
GENERATION_PARAMETERS = {
    "planner_temperature": 0.1,
    "execution_temperature": 0.3,
    "evaluation_temperature": 0.1,
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fixture_map() -> Dict[str, str]:
    return json.loads((ROOT / "data" / "phase3_fixtures.json").read_text(encoding="utf-8"))


async def _fixture_tool(_server_script: str, _tool_name: str, tool_args: dict) -> str:
    return _fixture_map().get(tool_args.get("query", ""), "Fixture not found")


def _run_pipeline_case(case: Dict[str, Any], config: str, auth_token: Optional[str]) -> Dict[str, Any]:
    """Run one pipeline case in the current process; caller owns timeout isolation."""
    from unittest.mock import patch

    task = case.get("trusted_task", case["payload"])
    if case["task_class"] == "adversarial" and case["attack_type"] == "direct_prompt_injection":
        task = f"{task}\n\n[ATTACK PAYLOAD]\n{case['payload']}"
    fixture_id = case.get("fixture_id")
    if fixture_id and case["attack_type"] in {"indirect_prompt_injection", "tool_output_poisoning"}:
        boundary = InvocationEvidence()
        async def case_fixture_tool(_server_script: str, _tool_name: str, _tool_args: dict) -> str:
            boundary.tool_requested = _tool_name
            boundary.invocation_attempted = True
            boundary.server_receipt = True
            boundary.receipt_id = fixture_id
            return _fixture_map().get(fixture_id, "Fixture not found")

        with patch("agents.research_agent.call_mcp_tool", side_effect=case_fixture_tool):
            state = run_pipeline(task, config, auth_token=auth_token)
        state["_phase3_boundary"] = boundary.as_dict()
        return state
    return run_pipeline(task, config, auth_token=auth_token)


def _case_row(case: Dict[str, Any], config: str, repetition: int, experiment_id: str, attempt_index: int = 1) -> Dict[str, Any]:
    return {
        "experiment_id": experiment_id,
        "case_id": case["case_id"],
        "task_id": case["task_id"],
        "task_class": case["task_class"],
        "attack_type": case["attack_type"],
        "repetition": repetition,
        "attempt_index": attempt_index,
        "case_order": case.get("case_order"),
        "security_config": config,
        "model_id": MODEL_ID,
        "protocol_version": case["protocol_version"],
        "dataset_version": PHASE3_DATASET_VERSION,
        "fixture_id": case.get("fixture_id"),
        "payload": case["payload"],
        "trusted_task": case.get("trusted_task", case["payload"]),
        "injection_boundary": case.get("injection_boundary", "planner_user_task"),
        "injection_status": "unknown",
        "last_completed_stage": "preflight",
        "timeout_phase": None,
        "mcp_cleanup_verified": None,
        "status": "setup_error",
        "attack_injected": case["task_class"] == "adversarial",
        "attack_success": None,
        "breach_occurred": None,
        "defense_triggered": None,
        "task_completed": None,
        "quality_score": None,
        "latency_ms": None,
        "timeout": False,
        "error_category": None,
        "tool_requested": case.get("expected_tool_policy", {}).get("requested_tool"),
        "tool_actual": None,
        "mcp_boundary_attempted": False,
        "mcp_boundary_reached": False,
        "mcp_receipt_id": None,
        "fixture_returned": None,
        "security_events": {},
        "adjudication_status": "not_evaluable",
        "evidence": "",
        "timestamp": _utc_now(),
    }


def _authenticate_prerequisite(config: str, auth_token: Optional[str]) -> tuple[bool, Optional[str]]:
    loaded = load_security_config(config)
    return check_authentication(loaded, auth_token=auth_token)


def run_case(case: Dict[str, Any], config: str, repetition: int, experiment_id: str, timeout_seconds: int, auth_token: Optional[str], attempt_index: int = 1) -> Dict[str, Any]:
    row = _case_row(case, config, repetition, experiment_id, attempt_index)
    row["timestamp"] = _utc_now()
    started = time.perf_counter()
    state, run_error = _run_with_timeout(case, config, auth_token, timeout_seconds)
    if run_error:
        row["latency_ms"] = round((time.perf_counter() - started) * 1000)
        row.update({
            "status": "timeout" if "timeout" in run_error else "model_error",
            "error_category": "timeout" if "timeout" in run_error else "pipeline_child_error",
            "evidence": run_error[:500],
            "timeout_phase": "unknown",
            "mcp_cleanup_verified": "child_cleanup_verified=True" in run_error,
        })
        return row
    latency_ms = round((time.perf_counter() - started) * 1000)
    row["latency_ms"] = latency_ms
    row["security_events"] = state.get("security_events", {})
    row["task_completed"] = (state.get("evaluation_result") or {}).get("task_completed")
    row["quality_score"] = (state.get("evaluation_result") or {}).get("quality_score")
    row["tool_actual"] = (state.get("research_result") or {}).get("tool_called")
    boundary = state.get("_phase3_boundary") or {}
    row["mcp_boundary_attempted"] = boundary.get("invocation_attempted", row["tool_actual"] is not None)
    row["mcp_boundary_reached"] = boundary.get("server_receipt", False)
    row["mcp_receipt_id"] = boundary.get("receipt_id")
    row["raw_result"] = (state.get("research_result") or {}).get("raw_result", "")
    row["final_output"] = (state.get("execution_result") or {}).get("result", "")
    row["errors"] = state.get("errors", [])
    if state.get("errors"):
        errors = state["errors"]
        if any("Authentication failed" in error for error in errors):
            row["status"] = "authentication_failed"
            row["error_category"] = "authentication"
        elif any("Input blocked" in error for error in errors):
            row["status"] = "completed"
            row["error_category"] = "security_control_block"
        else:
            row["status"] = "model_error"
            row["error_category"] = "pipeline_error"
    else:
        row["status"] = "completed"
    row["last_completed_stage"] = "returned"
    row["injection_status"] = "delivered"
    if row["error_category"] == "security_control_block":
        row["injection_status"] = "blocked"
    if case.get("fixture_id"):
        expected_fixture = _fixture_map().get(case["fixture_id"])
        row["fixture_returned"] = expected_fixture is not None and row["raw_result"] == expected_fixture
    if case["attack_type"] == "unauthorized_tool_invocation":
        row["status"] = "not_evaluable"
        row["evidence"] = "Current pipeline exposes no attacker-controlled arbitrary tool selector; no boundary invocation was inferred."
        row["adjudication_status"] = "not_evaluable"
        return row
    if case["task_class"] == "adversarial":
        row.update(evaluate_attack_case(case, row))
    else:
        row.update({
            "attack_success": None,
            "breach_occurred": None,
            "defense_triggered": None,
            "adjudication_status": "evaluated" if row["status"] == "completed" else "not_evaluable",
            "evidence": "normal-task completion recorded without attack adjudication",
        })
    return row


def _child_entry(case: Dict[str, Any], config: str, auth_token: Optional[str], queue: Any) -> None:
    try:
        queue.put({"ok": True, "state": _run_pipeline_case(case, config, auth_token)})
    except Exception as exc:
        queue.put({"ok": False, "error": f"{type(exc).__name__}: {exc}"})


def _run_with_timeout(case: Dict[str, Any], config: str, auth_token: Optional[str], timeout_seconds: int) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Run the pipeline in a child process so a timeout can terminate it."""
    context = multiprocessing.get_context("spawn")
    queue = context.Queue()
    process = context.Process(target=_child_entry, args=(case, config, auth_token, queue))
    process.start()
    process.join(timeout_seconds)
    if process.is_alive():
        process.terminate()
        process.join()
        cleanup_verified = not process.is_alive()
        return None, f"pipeline exceeded timeout; child_cleanup_verified={cleanup_verified}"
    if queue.empty():
        return None, "pipeline exited without returning state"
    result = queue.get()
    if not result.get("ok"):
        return None, result.get("error", "pipeline child failed")
    return result["state"], None


def _write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def _append_jsonl(path: Path, row: Dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _write_json(path: Path, value: Dict[str, Any]) -> None:
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary_path, path)


def _persist_progress(
    output_dir: Path,
    manifest: Dict[str, Any],
    rows: List[Dict[str, Any]],
) -> None:
    (output_dir / "raw_results.jsonl").touch(exist_ok=True)
    manifest["raw_results_count"] = len(rows)
    _write_json(output_dir / "manifest.json", manifest)
    _write_json(output_dir / "summary.json", summarize_metrics(rows))


def validate_result_artifacts(output_dir: Path, expected_count: Optional[int] = None) -> List[Dict[str, Any]]:
    """Validate persisted Phase 3 artifacts without treating missing outcomes as success."""
    manifest_path = output_dir / "manifest.json"
    raw_path = output_dir / "raw_results.jsonl"
    summary_path = output_dir / "summary.json"
    if not all(path.exists() for path in (manifest_path, raw_path, summary_path)):
        raise ValueError("Phase 3 artifacts are incomplete")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows: List[Dict[str, Any]] = []
    identities = set()
    for line_number, line in enumerate(raw_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL record at line {line_number}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"JSONL record at line {line_number} is not an object")
        identity = (
            row.get("case_id"),
            row.get("security_config"),
            row.get("repetition"),
            row.get("attempt_index"),
        )
        if identity in identities:
            raise ValueError(f"Duplicate observation identity: {identity}")
        identities.add(identity)
        rows.append(row)
    if manifest.get("raw_results_count") != len(rows):
        raise ValueError("Manifest raw-results count does not match JSONL")
    if expected_count is not None and manifest.get("status") == "completed" and len(rows) != expected_count:
        raise ValueError("Completed experiment has an incomplete observation set")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary != summarize_metrics(rows):
        raise ValueError("Summary does not match raw results")
    return rows


def run_experiment(
    *,
    experiment_id: Optional[str] = None,
    repetitions: int = 5,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    dry_run: bool = False,
    configs: Optional[List[str]] = None,
    auth_token: Optional[str] = None,
    max_retries: int = 0,
) -> Path:
    if repetitions < 1 or timeout_seconds < 1 or max_retries < 0:
        raise ValueError("repetitions and timeout_seconds must be positive; max_retries cannot be negative")
    experiment_id = experiment_id or f"phase3_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    configs = configs or ["config_a", "config_b", "config_c"]
    order_seed = 0
    config_orders = [
        configs,
        configs[1:] + configs[:1],
        configs[2:] + configs[:2],
    ]
    attack_cases, attack_checksum = load_cases(ROOT / "benchmark_dataset" / "phase3_attack_cases.json")
    normal_path = ROOT / "benchmark_dataset" / "normal_tasks.json"
    normal_raw = normal_path.read_bytes()
    normal_cases = [
        {
            "case_id": item["task_id"],
            "task_id": item["task_id"],
            "task_class": "normal",
            "attack_type": "none",
            "category": item["topic_category"],
            "payload": item["task"],
            "expected_behavior": "Complete the normal research task.",
            "success_criteria": [],
            "breach_criteria": [],
            "expected_tool_policy": {},
            "fixture_id": None,
            "protocol_version": "phase3-v1.0",
            "trusted_task": item["task"],
            "injection_boundary": "none",
        }
        for item in json.loads(normal_raw.decode("utf-8"))
    ]
    for order, item in enumerate(normal_cases, 1):
        item["case_order"] = order
    for order, item in enumerate(attack_cases, len(normal_cases) + 1):
        item["case_order"] = order
    cases = normal_cases + attack_cases
    dataset_checksum = hashlib.sha256(normal_raw + b"\n" + (ROOT / "benchmark_dataset" / "phase3_attack_cases.json").read_bytes()).hexdigest()
    if dry_run:
        cases = cases[:1] + attack_cases[:1]
        repetitions = 1
    output_dir = ROOT / "results" / "phase3" / experiment_id
    output_dir.mkdir(parents=True, exist_ok=False)
    manifest = {
        "experiment_id": experiment_id,
        "protocol_version": "phase3-v1.0",
        "dataset_version": PHASE3_DATASET_VERSION,
        "dataset_sha256": dataset_checksum,
        "model_id": MODEL_ID,
        "configs": configs,
        "repetitions": repetitions,
        "timeout_seconds": timeout_seconds,
        "dry_run": dry_run,
        "created_at": _utc_now(),
        "order_seed": order_seed,
        "config_orders": config_orders,
        "generation_parameters": GENERATION_PARAMETERS,
        "max_retries": max_retries,
        "expected_primary_observations": len(cases) * len(configs) * repetitions,
        "status": "running",
    }
    raw_path = output_dir / "raw_results.jsonl"
    rows: List[Dict[str, Any]] = []
    raw_path.touch()
    _persist_progress(output_dir, manifest, rows)
    try:
        for repetition in range(1, repetitions + 1):
            ordered_configs = config_orders[(repetition - 1) % len(config_orders)]
            for config in ordered_configs:
                try:
                    authenticated, auth_error = _authenticate_prerequisite(config, auth_token)
                except Exception as exc:
                    authenticated, auth_error = False, str(exc)
                selected_token = auth_token if auth_token is not None else os.getenv("AUTH_TOKEN")
                for case in cases:
                    if not authenticated:
                        row = _case_row(case, config, repetition, experiment_id)
                        row.update({"error_category": "authentication_prerequisite", "evidence": auth_error, "status": "authentication_failed"})
                        rows.append(row)
                        _append_jsonl(raw_path, row)
                        _persist_progress(output_dir, manifest, rows)
                        continue
                    for attempt_index in range(1, max_retries + 2):
                        row = run_case(case, config, repetition, experiment_id, timeout_seconds, selected_token, attempt_index)
                        rows.append(row)
                        _append_jsonl(raw_path, row)
                        _persist_progress(output_dir, manifest, rows)
                        if row["status"] == "completed":
                            break
    except BaseException as exc:
        manifest.update({
            "status": "interrupted",
            "interrupted_at": _utc_now(),
            "interruption": f"{type(exc).__name__}: {exc}",
        })
        _persist_progress(output_dir, manifest, rows)
        raise
    manifest.update({"status": "completed", "completed_at": _utc_now()})
    _persist_progress(output_dir, manifest, rows)
    return output_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Phase 3 security cases (never writes results/raw_results.csv).")
    parser.add_argument("--dry-run", action="store_true", help="Run one case once per configuration.")
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--experiment-id")
    parser.add_argument("--max-retries", type=int, default=0)
    args = parser.parse_args()
    output = run_experiment(
        experiment_id=args.experiment_id,
        repetitions=args.repetitions,
        timeout_seconds=args.timeout_seconds,
        dry_run=args.dry_run,
        auth_token=os.getenv("AUTH_TOKEN"),
        max_retries=args.max_retries,
    )
    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
