# Phase 3 Implementation Report

**Project:** *Security and Reliability of MCP-Based Multi-Agent Systems: An Empirical Study of Vulnerabilities and Defense Mechanisms*  
**Protocol:** `phase3-v1.0`  
**Date:** 2026-10-25

## Scope and execution policy

The Phase 3 framework was implemented without running the full experiment or
claiming experimental findings. No application security control was changed.
The historical [`results/raw_results.csv`](../results/raw_results.csv) and the
existing [`benchmark_dataset/normal_tasks.json`](../benchmark_dataset/normal_tasks.json)
were not modified.

## 1. Files created

- [`docs/PHASE3_EXPERIMENT_PROTOCOL.md`](PHASE3_EXPERIMENT_PROTOCOL.md): attack definitions, success/breach criteria, eligibility, denominators, failure policy, latency boundary, quality treatment, and reproducibility requirements.
- [`benchmark_dataset/phase3_attack_cases.json`](../benchmark_dataset/phase3_attack_cases.json): eight versioned cases covering the four attack types.
- [`data/phase3_fixtures.json`](../data/phase3_fixtures.json): deterministic local fixtures for indirect injection and tool-output poisoning.
- [`phase3/dataset.py`](../phase3/dataset.py): dataset validation and SHA-256 checksum loading.
- [`phase3/evaluators.py`](../phase3/evaluators.py): independent case evaluators and ASR/SBR/TCR/quality/latency summaries.
- [`phase3/runner.py`](../phase3/runner.py): isolated experiment runner, manifest creation, child-process timeout handling, authentication preflight, raw JSONL output, and summary output.
- [`phase3/boundary.py`](../phase3/boundary.py): test-only MCP invocation/receipt evidence structure that does not change allowlists.
- [`phase3/__init__.py`](../phase3/__init__.py).
- [`tests/test_phase3.py`](../tests/test_phase3.py): nine offline tests for evaluator behavior, false-breach prevention, blocked outcomes, denominators, dataset checksums, metadata, and CSV preservation.

No existing application security-control files were required for the Phase 3 additions.

## 2. Implemented protocol and metric definitions

The protocol uses:

```
ASR = successful eligible attack cases / eligible injected attack cases
SBR = eligible attack cases with a confirmed breach / eligible injected attack cases
TCR = completed eligible task cases / eligible task cases
```

Normal-task TCR and adversarial-task TCR are reported separately. Authentication
failures before injection, timeouts without adjudicable evidence, model errors,
setup errors, and `not_evaluable` cases are excluded from attack denominators and
reported as exclusions. Exceptions, security logs, and blocked requests are not
automatically treated as attack success or breach.

The primary latency boundary is immediately before `run_pipeline()` through its
return, measured with `time.perf_counter()`. The current Evaluation Agent's
model-judged quality score is retained and explicitly treated as non-independent
and not objectively validated.

## 3. Attack types and limitations

Implemented dataset and evaluator coverage exists for:

- Direct prompt injection.
- Indirect prompt injection.
- Tool-output poisoning.
- Unauthorized tool invocation.

Direct cases preserve a trusted task and compose the payload at the Planner-input
boundary. Indirect and poisoning cases verify the intended fixture at the MCP
response boundary. Protected-marker checks inspect disclosure output only, never
the raw poisoned source. Delivered-and-blocked cases are eligible with false
attack/breach outcomes and a true defense event.

The unauthorized-tool evaluator requires evidence that the requested tool reached
the MCP boundary. The test-only boundary evidence structure records a receipt when
an instrumented server is used; it does not change allowlists.

**Current limitation:** the existing application pipeline does not expose an
attacker-controlled arbitrary tool selector. Therefore the runner records
unauthorized-tool cases as `not_evaluable` with an explicit reason rather than
pretending that a boundary attempt occurred. The evaluator itself is ready for
boundary evidence, but a future integration must connect the attack case to the
Research Agent/MCP authorization boundary before unauthorized-invocation results
can be used as research findings.

The runner uses local fixture substitution for indirect and poisoned tool-output
cases. This is deterministic and safe, but it is a test harness mechanism rather
than evidence about a live external retrieval service.

## 4. Result isolation and metadata

The runner writes only to:

```
results/phase3/<experiment_id>/
```

Each experiment directory contains:

- `manifest.json`: experiment ID, protocol/dataset versions, checksums, model ID,
  configurations, repetitions, timeout, and dry-run flag.
- `raw_results.jsonl`: one row for every attempted case, including failures and
  skipped authentication prerequisites.
- `summary.json`: metrics, denominators, exclusions, timeout counts, and errors.

The exact model identifier recorded by the runner is
`openai/gpt-oss-120b`. Each row records configuration, case, task, attack class,
repetition, attempt index, case order, fixture, trusted task, payload, injection
status/boundary, stage, MCP boundary evidence, status, security events, task
completion, quality, latency, timeout/error category, and adjudication status.
Configuration order is counterbalanced with a recorded order seed and generation
temperatures are recorded in the manifest. Retries are separate attempts; the
first attempt remains primary.

The runner never instantiates or writes through `MetricsCollector`, so it cannot
implicitly migrate or overwrite the historical CSV.

## 5. Tests run

Focused Phase 3 tests:

```text
python -m py_compile phase3\dataset.py phase3\evaluators.py phase3\runner.py phase3\boundary.py tests\test_phase3.py
python -m pytest tests\test_phase3.py -q
9 passed in 2.29s
```

Offline regression suite:

```text
python -m pytest --ignore=tests\test_groq_connection.py -q
77 passed in 38.33s
```

The live Groq connectivity test was not used as part of the offline validation.
The full Phase 3 experiment was not run.

## 6. Historical CSV confirmation

`results/raw_results.csv` remains unchanged. A repository diff check produced no
diff for that file, and the new Phase 3 test verifies that the file exists and is
not used as the Phase 3 output target.

The normal benchmark file also produced no diff.

## 7. Commands

### Dry run

From `E:\MCP-FRAMEWORK`, after setting required environment variables:

```powershell
python -m phase3.runner --dry-run --experiment-id phase3_dry_run
```

This command runs one normal case and one adversarial case once per selected
configuration and writes only to
`results/phase3/phase3_dry_run/`. It was not executed during this implementation
task.

### Full experiment

The command below is documented but was not executed:

```powershell
python -m phase3.runner --repetitions 5 --timeout-seconds 120 --experiment-id phase3_v1_full
```

Config B and Config C require valid matching `AUTH_SECRET` and `AUTH_TOKEN`
environment values. The runner performs authentication preflight and records
every case as `authentication_failed` if prerequisites are absent; it does not
silently skip those cases. The default `--max-retries 0` keeps the first attempt
as the primary observation. If retries are approved, use
`--max-retries N`; each retry is a separate row with a higher `attempt_index`
and does not replace the first attempt.

## 8. Timeout and subprocess-cleanup verification

Each pipeline invocation runs in a child process and records a timeout status,
timeout phase placeholder, elapsed time, and whether the runner child exited after
termination. This prevents the runner process itself from remaining alive.

The current implementation does **not** yet prove that every descendant MCP
server process has been reaped on Windows. A Windows Job Object/process-tree
supervisor is still required before treating timeout cleanup as fully verified.
Timeouts remain non-evaluable and are never classified as attack success or
defense success.

## 9. Remaining blockers before collecting research results

1. **Unauthorized invocation integration:** The current pipeline has no
   attacker-controlled arbitrary tool selector, so unauthorized-tool cases remain
   explicitly `not_evaluable` until the instrumented boundary is connected to an
   approved authorization-boundary test path.
2. **Windows descendant cleanup:** Child exit is verified, but descendant MCP
   process cleanup requires a Job Object or equivalent supervisor.
3. **Quality independence:** The current quality score is judged by the same model
   family and remains a non-independent operational signal. Independent or
   deterministic adjudication is recommended before publication.
4. **External validity:** Local deterministic fixtures do not establish behavior
   against live MCP servers or retrieval providers; any live-source experiment
   requires a separately versioned, controlled fixture/service and threat model.

The framework is ready for dry-run validation and further attack-boundary
integration. It is not yet appropriate to report complete Phase 3 security
effectiveness results because the unauthorized-tool path is not observable in the
existing application pipeline and quality remains model-judged.
