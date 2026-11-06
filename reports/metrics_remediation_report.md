# Experiment Metrics Remediation Report

**Date:** 2026-10-15  
**Repository:** MCP-FRAMEWORK  
**Project:** Security and Reliability of MCP-Based Multi-Agent Systems: An Empirical Study of Vulnerabilities and Defense Mechanisms  
**Component Audited:** Experiment Metrics Collection & Latency Measurement (`metrics/collector.py`, `pipeline/graph.py`, `agents/`, `results/raw_results.csv`, `tests/`)

---

## 1. Executive Summary

This audit examined the experimental measurement and metrics recording subsystem of the MCP-FRAMEWORK research pipeline. The investigation revealed several critical issues in the measurement layer:
1. Use of non-monotonic system wall-clock time (`time.time()`) for latency measurement.
2. Inconsistent latency measurement boundaries across pipeline entry and exit points.
3. Brittle inference of security events from error message substring matching instead of direct structured reporting.
4. Premature assignment of `False` to unmeasured attack outcomes (`attack_success`, `breach_occurred`) during Phase 2 baseline runs, introducing false negatives.
5. Schema corruption in `results/raw_results.csv`, where legacy 16-column observations and newer 20-column observations coexisted under an outdated 16-column header.

All identified defects have been remediated. The metrics collector and pipeline now use high-resolution monotonic timers (`time.perf_counter()`), propagate structured security event payloads directly from point-of-occurrence, leave unmeasured attack labels explicitly empty (`""` / null), and support automated, non-destructive migration of historical CSV observations. A comprehensive suite of 12 offline unit tests was authored and verified, passing with zero real LLM API calls.

---

## 2. Problems Identified

### 2.1 Elapsed-Time Measurement Using `time.time()`
In the original `metrics/collector.py`, elapsed time was measured via `time.time()`:
```python
# Original implementation
self.run_start_times[run_id] = time.time()
...
latency_ms = int((time.time() - start_time) * 1000)
```
**Defect:** `time.time()` returns system wall-clock time. It is non-monotonic and susceptible to system clock adjustments (NTP synchronizations, leap seconds, manual time updates, and timezone alterations). In scientific benchmarking, this can lead to jitter, inaccurate latency recordings, or even negative durations.

### 2.2 Ambiguous and Inconsistent Latency Boundaries
In `pipeline/graph.py`, `run_pipeline()` lacked internal timing instrumentation. If an external harness called `run_pipeline()` directly without invoking `collector.start_run()`, latency was unrecorded or defaulted to `0`. Furthermore, when authentication failed at the pipeline gateway, the pipeline returned immediately without recording the elapsed time required to process the authentication decision.

### 2.3 Brittle Security Event Inference via Error Substrings
The original collector attempted to deduce whether a security control had fired by parsing error strings from agent outputs:
```python
# Original fragile heuristics
auth_success = "Authentication failed" not in str(plan.get("error", ""))
permission_denied = "Tool not permitted" in str(research_result.get("error", ""))
input_validation_failed = "Input blocked" in str(plan.get("error", ""))
output_validation_failed = "TRUNCATED" in str(raw_result)
```
**Defect:** 
- Substring matching is brittle: minor phrasing changes in error logs or agent prompts invalidate the metrics.
- The substring `"TRUNCATED"` could trigger false positives if legitimate search results (e.g., academic abstracts or documentation) naturally contained that token.
- Agents already enforce security controls at concrete execution points; inferring events downstream from error messages discarded ground-truth execution context.

### 2.4 False Negative Fallacy in Attack Metrics
In Phase 2 baseline runs, no adversarial attacks were injected (`attack_injected = False`, `attack_type = "none"`). However, the collector previously serialized:
```python
str(state_dict.get("attack_success", False))  # Logged "False"
str(state_dict.get("breach_occurred", False)) # Logged "False"
```
**Defect:** Coercing unmeasured attack outcomes to `False` creates a false negative fallacy in research results. It falsely asserts that attacks were executed and successfully defended against, when in reality attacks had not yet been introduced. In scientific empirical research, unmeasured variables must remain explicitly null/empty until Phase 3 adversarial experiments are activated with labeled ground-truth criteria.

### 2.5 Historical CSV Schema Corruption
Inspection of `results/raw_results.csv` revealed that:
- Rows 1 to 36 followed the Phase 2.0 16-column format (`run_id` through `tool_called`, plus `notes`).
- Rows 37 to 44 followed a 20-column format, where four security event columns (`auth_success`, `permission_denied`, `input_validation_failed`, `output_validation_failed`) were appended before `notes`.
- The CSV header was still the 16-column header. Consequently, in rows 37–44, `auth_success` appeared under the `notes` column, and the remaining 4 columns were orphaned beyond the declared header.
- `_ensure_csv_exists()` only checked `not self.csv_path.exists()`, failing to migrate or align existing files when schema changes occurred.

---

## 3. Changes Made

### 3.1 Timing Subsystem Remediation
- Replaced all elapsed-time measurements in `metrics/collector.py` and `pipeline/graph.py` with `time.perf_counter()`, which provides a monotonic, high-resolution clock designed specifically for benchmarking execution durations.
- Latency is computed using:
  $$\text{latency\_ms} = \max\left(0, \operatorname{round}\left((t_{\text{end}} - t_{\text{start}}) \times 1000\right)\right)$$

### 3.2 Standardized Pipeline Latency Boundaries
- In `pipeline/graph.py`, `start_time = time.perf_counter()` is captured at the very beginning of `run_pipeline()`.
- On authentication rejection, the elapsed time of the rejection is recorded in `state["latency_ms"]` before returning.
- On successful pipeline execution or pipeline exception, `state["latency_ms"]` is updated before returning the final state.
- In `metrics/collector.py`, `end_run()` supports dual-boundary latency extraction:
  1. Primary: Uses `self._run_start_times[run_id]` if `collector.start_run()` was called.
  2. Fallback: Extracts `state["latency_ms"]` measured directly inside `run_pipeline()`.
  3. Default: Sets `0` if neither is available.

### 3.3 Structured Security Event Reporting
- Updated `pipeline/graph.py` to declare `security_events: Dict[str, Any]` and `latency_ms: Optional[int]` in `AgentState`.
- Initialized `security_events` at pipeline inception:
  - On auth failure: `{"auth_success": False, "permission_denied": False, "input_validation_failed": False, "output_validation_failed": False}`
  - On auth success: `{"auth_success": True, "permission_denied": False, "input_validation_failed": False, "output_validation_failed": False}`
- Graph nodes (`planner_node`, `research_node`, `execution_node`) inspect agent return dictionaries and propagate `security_events` into `state["security_events"]`.
- `agents/planner_agent.py` emits `{"security_events": {"input_validation_failed": True}}` when keywords or length limits are violated.
- `agents/research_agent.py` emits `{"security_events": {"permission_denied": True}}` on tool policy violations and `{"security_events": {"output_validation_failed": True}}` when tool output exceeds character limits and is truncated.
- `agents/execution_agent.py` emits `{"security_events": {"output_validation_failed": True}}` when unsafe patterns are detected in final model generation.
- `metrics/collector.py` reads `state["security_events"]` directly, maintaining backwards-compatible string fallbacks only if structured events are omitted.

### 3.4 Explicit Handling of Unmeasured Outcomes
- Refactored `metrics/collector.py` to check for `None`:
  ```python
  attack_success = state_dict.get("attack_success", None)
  breach_occurred = state_dict.get("breach_occurred", None)
  ...
  str(attack_success) if attack_success is not None else "",
  str(breach_occurred) if breach_occurred is not None else "",
  ```
- Unmeasured values serialize as empty strings `""` in the CSV, preserving semantic distinction between "attack evaluated and defended" (`False`) versus "attack not evaluated" (`""` / null).

### 3.5 Automated Non-Destructive CSV Schema Migration
- Updated `MetricsCollector._ensure_csv_exists()` to inspect the existing header of `results/raw_results.csv`:
  - If the header does not match the standardized 20-column `HEADERS`, the collector automatically migrates the file.
  - Legacy 16-column rows are padded with four empty strings `["", "", "", ""]` for the unmeasured security fields, ensuring the historical `notes` column remains at index 19.
  - Rows already containing 20 columns are retained as-is.
  - No historical data is deleted, overwritten, or fabricated.
- All 44 historical observations in `results/raw_results.csv` have been cleanly migrated and validated.

---

## 4. Metric Definitions and Operational Formulations

The study measures five primary empirical research metrics and four security event indicators:

| Metric | Type | Scale / Values | Operational Definition / Formulation |
| :--- | :--- | :--- | :--- |
| **Attack Success Rate (ASR)** | Aggregate Rate | $[0.0, 1.0]$ | Ratio of attacks achieving adversarial objective: $$ASR = \frac{\sum \mathbb{I}(\text{attack\_success} = \text{True})}{\sum \mathbb{I}(\text{attack\_injected} = \text{True})}$$ *Note: Unmeasured in Phase 2 baseline (attacks injected = 0).* |
| **Security Breach Rate (SBR)** | Aggregate Rate | $[0.0, 1.0]$ | Proportion of total runs resulting in policy breach: $$SBR = \frac{\sum \mathbb{I}(\text{breach\_occurred} = \text{True})}{N_{\text{total}}}$$ *Note: Unmeasured in Phase 2 baseline.* |
| **Task Completion Rate (TCR)** | Aggregate Rate | $[0.0, 1.0]$ | Proportion of runs where the agent pipeline completed the task successfully: $$TCR = \frac{\sum \mathbb{I}(\text{task\_completed} = \text{True})}{N_{\text{total}}}$$ Evaluated by `evaluation_agent` based on `quality_score >= 0.5` and `execution_success == True`. |
| **Response Quality Score ($Q$)** | Continuous Score | $[0.0, 1.0]$ | Quality and completeness score evaluated by `evaluation_agent`. Assessed via LLM evaluation prompt or deterministic heuristic fallback when LLM parsing is unavailable. |
| **Pipeline Latency ($L$)** | Continuous (ms) | Integer $\ge 0$ | Total wall elapsed execution time from pipeline invocation to final state return: $$L = \max\left(0, \operatorname{round}\left((t_{\text{end}} - t_{\text{start}}) \times 1000\right)\right)$$ measured via `time.perf_counter()`. |
| **`auth_success`** | Security Event | `True`, `False`, `""` | `True` if presented credential matches expected secret or auth is disabled; `False` if rejected; `""` if unmeasured (historical rows). |
| **`permission_denied`** | Security Event | `True`, `False`, `""` | `True` if agent requested an MCP tool not permitted by config policy; `False` if permitted; `""` if unmeasured. |
| **`input_validation_failed`**| Security Event | `True`, `False`, `""` | `True` if input task exceeded length limit or matched prohibited keyword blacklist; `False` otherwise; `""` if unmeasured. |
| **`output_validation_failed`**| Security Event | `True`, `False`, `""` | `True` if tool output was truncated due to length limits or execution output contained unsafe patterns; `False` otherwise; `""` if unmeasured. |

---

## 5. Measurement Boundaries

The exact start and end measurement boundaries for latency across all execution pathways are formally defined below:

```
[run_pipeline() Invoked / collector.start_run()]
       │
       ▼
t_start = time.perf_counter()
       │
       ├─► [Check Authentication] ──(Failed)──► t_end = time.perf_counter()
       │                                         latency_ms = (t_end - t_start) * 1000
       │                                         Return error state immediately
       ▼ (Passed)
[Initialize AgentState with security_events]
       │
       ▼
[LangGraph invoke(): Planner -> Research -> Execution -> Evaluation]
       │
       ▼
t_end = time.perf_counter()
latency_ms = (t_end - t_start) * 1000
       │
       ▼
[collector.end_run()] ──► Log standardized row to results/raw_results.csv
```

1. **Start Boundary ($t_{\text{start}}$):**
   - Instantiated via `time.perf_counter()` immediately upon entry to `run_pipeline(user_task, security_config, auth_token)` or `collector.start_run(user_task, security_config)`.
   - Precedes configuration loading, credential verification, and state dictionary allocation.

2. **End Boundary ($t_{\text{end}}$):**
   - **Path A (Authentication Failure):** Captured immediately after `check_authentication()` returns `(False, error)`. Ensures authentication overhead is measured and logged.
   - **Path B (Successful Pipeline Completion):** Captured immediately after `graph.invoke(initial_state)` returns the evaluated final state. Encompasses all agent LLM calls, stdio MCP subprocess tool calls, and evaluation scoring.
   - **Path C (Pipeline Exception):** Captured inside the outer `except Exception` handler if LangGraph execution raises an unhandled error, ensuring failed runs record the time spent before crashing.

---

## 6. CSV Schema and Compatibility Decisions

### 6.1 Standardized 20-Column Schema
The standardized header declared in `MetricsCollector.HEADERS` is:

```csv
run_id,timestamp,user_task,security_config,attack_type,attack_injected,attack_success,breach_occurred,task_completed,quality_score,latency_ms,planner_success,research_success,execution_success,tool_called,auth_success,permission_denied,input_validation_failed,output_validation_failed,notes
```

### 6.2 Schema Mapping and Legacy Migration
To preserve data integrity without fabricating historical records, the migration logic maps columns as follows:

| Index | Column Name | Legacy 16-Col Source | Standard 20-Col Mapping | Historical Migration Strategy |
| :---: | :--- | :--- | :--- | :--- |
| 0–14 | `run_id` ... `tool_called` | `row[0:15]` | `row[0:15]` | Direct 1:1 copy |
| 15 | `auth_success` | Not present | `row[15]` | Populated with `""` (unmeasured) |
| 16 | `permission_denied` | Not present | `row[16]` | Populated with `""` (unmeasured) |
| 17 | `input_validation_failed` | Not present | `row[17]` | Populated with `""` (unmeasured) |
| 18 | `output_validation_failed` | Not present | `row[18]` | Populated with `""` (unmeasured) |
| 19 | `notes` | `row[15]` | `row[19]` | Shifted to column 19 to preserve notes text |

### 6.3 Historical Dataset Audit
- Before remediation: 44 historical runs existed across mixed 16- and 20-column layouts.
- After remediation: Exactly 44 observation rows plus 1 standardized 20-column header row.
- Zero historical rows were deleted or overwritten.
- Security event columns in runs 1–36 are padded with `""` (null), correctly reflecting that security events were not instrumented during initial baseline runs.

---

## 7. Tests Executed and Results

A comprehensive unit test suite was developed in [tests/test_metrics.py](file:///e:/MCP-FRAMEWORK/tests/test_metrics.py) to validate all remediation objectives without making real Groq LLM API calls.

### 7.1 Test Suite Breakdown (`tests/test_metrics.py`)

| Test Method | Target Functionality | Verification Criteria | Status |
| :--- | :--- | :--- | :---: |
| `test_latency_calculation_with_start_run` | High-resolution timing | Verifies `time.perf_counter()` tracking in `start_run()` / `end_run()`, ensures non-negative latency and clean state dictionary cleanup. | **PASSED** |
| `test_latency_calculation_from_state_fallback` | Latency boundary fallback | Verifies latency extraction directly from `state["latency_ms"]` when `start_run()` was not invoked externally. | **PASSED** |
| `test_successful_task_completion` | Successful run metrics | Confirms `task_completed=True`, valid `quality_score`, and positive agent success flags. | **PASSED** |
| `test_failed_task_completion` | Failed run metrics | Confirms `task_completed=False`, `quality_score=0.0`, error propagation to `notes`. | **PASSED** |
| `test_missing_metric_values_handling` | Graceful null handling | Passes completely empty state `{}`; verifies zero crashes, sensible defaults, and unmeasured attack fields remaining `""`. | **PASSED** |
| `test_authentication_failure_metrics` | Auth security event | Confirms `auth_success=False` recorded properly with other flags `False`. | **PASSED** |
| `test_permission_denial_metrics` | Permission security event | Confirms structured `permission_denied=True` recorded from research agent. | **PASSED** |
| `test_input_validation_failure_metrics` | Input validation event | Confirms structured `input_validation_failed=True` recorded from planner agent. | **PASSED** |
| `test_output_validation_failure_metrics`| Output validation event | Confirms structured `output_validation_failed=True` recorded on truncation/filtering. | **PASSED** |
| `test_csv_headers_and_row_consistency` | Schema column alignment | Validates that multiple logged runs have exactly 20 columns matching `HEADERS`. | **PASSED** |
| `test_historical_data_preservation_and_migration` | CSV migration | Simulates legacy 16-column CSV; verifies automatic 20-column upgrade, data preservation, and notes alignment. | **PASSED** |
| `test_get_summary_statistics` | Aggregate summary statistics | Validates calculation of run counts, average quality, average latency, and security event frequencies. | **PASSED** |

### 7.2 Execution Output
```
platform win32 -- Python 3.13.13, pytest-8.3.5
rootdir: E:\MCP-FRAMEWORK

tests/test_metrics.py::TestMetricsCollector::test_latency_calculation_with_start_run PASSED [  8%]
tests/test_metrics.py::TestMetricsCollector::test_latency_calculation_from_state_fallback PASSED [ 16%]
tests/test_metrics.py::TestMetricsCollector::test_successful_task_completion PASSED [ 25%]
tests/test_metrics.py::TestMetricsCollector::test_failed_task_completion PASSED [ 33%]
tests/test_metrics.py::TestMetricsCollector::test_missing_metric_values_handling PASSED [ 41%]
tests/test_metrics.py::TestMetricsCollector::test_authentication_failure_metrics PASSED [ 50%]
tests/test_metrics.py::TestMetricsCollector::test_permission_denial_metrics PASSED [ 58%]
tests/test_metrics.py::TestMetricsCollector::test_input_validation_failure_metrics PASSED [ 66%]
tests/test_metrics.py::TestMetricsCollector::test_output_validation_failure_metrics PASSED [ 75%]
tests/test_metrics.py::TestMetricsCollector::test_csv_headers_and_row_consistency PASSED [ 83%]
tests/test_metrics.py::TestMetricsCollector::test_historical_data_preservation_and_migration PASSED [ 91%]
tests/test_metrics.py::TestMetricsCollector::test_get_summary_statistics PASSED [100%]

============================= 12 passed in 2.25s ==============================
```

### 7.3 Regression Verification
The existing security control test suite (`tests/test_security_controls.py`) was also executed to ensure that timing and structured security events did not regress control enforcement:
```
============================= 23 passed in 13.30s =============================
```

---

## 8. Remaining Limitations

1. **Phase 3 Adversarial Attack Metrics Not Yet Active:**
   - In accordance with the study design, `attack_success` and `breach_occurred` remain unmeasured (`""`) during Phase 2 baseline runs.
   - Formal attack evaluation criteria (e.g., ground-truth canary token exfiltration, prompt injection success markers) must be implemented and benchmarked during Phase 3 adversarial testing.
2. **Quality Scoring Dependency:**
   - When Groq API keys are present, response quality is scored using LLM evaluation via `ChatGroq`. When the API is unavailable or returns invalid JSON, the evaluation agent falls back to word-count heuristics (`fallback_score`).
3. **Subprocess MCP Tool Latency Granularity:**
   - The current latency metric captures total end-to-end pipeline latency. While total latency includes MCP server subprocess execution, individual tool call durations are not currently isolated into distinct CSV columns. If individual tool profiling is required in later phases, sub-timers can be added to `call_mcp_tool()`.
