"""Versioned Phase 3 case loading and checksum utilities."""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


PHASE3_DATASET_VERSION = "phase3-attacks-v1.0"


def load_cases(path: str | Path) -> Tuple[List[Dict[str, Any]], str]:
    dataset_path = Path(path)
    raw = dataset_path.read_bytes()
    cases = json.loads(raw.decode("utf-8"))
    if not isinstance(cases, list) or not cases:
        raise ValueError("Phase 3 attack dataset must be a non-empty JSON list")
    required = {
        "case_id", "task_id", "task_class", "attack_type", "category",
        "trusted_task", "payload", "injection_boundary", "expected_behavior",
        "success_criteria", "breach_criteria", "expected_tool_policy",
        "protocol_version",
    }
    for case in cases:
        missing = required.difference(case)
        if missing:
            raise ValueError(f"Case {case.get('case_id', '<unknown>')} is missing fields: {sorted(missing)}")
        if case["protocol_version"] != "phase3-v1.0":
            raise ValueError(f"Unsupported protocol version in {case['case_id']}")
    return cases, hashlib.sha256(raw).hexdigest()
