# Pre-Phase 3 Independent Verification Report

**Date:** 2026-10-15  
**Auditor:** Antigravity AI Pair Programmer (Independent Audit)  
**Repository:** `MCP-FRAMEWORK` (`e:\MCP-FRAMEWORK`)  
**Project:** Security and Reliability of MCP-Based Multi-Agent Systems: An Empirical Study of Vulnerabilities and Defense Mechanisms  
**Target:** Pre-Phase 3 Verification of Authentication, Metrics, Latency, and Historical Data  

---

## 1. Executive Verdict

### Verdict: **NOT READY FOR PHASE 3 (READY WITH BLOCKERS)**

While the core mechanics of authentication gating (`security/auth.py`), monotonic high-resolution timing (`time.perf_counter()`), and basic security event logging have been implemented and pass all 41 offline unit tests, the framework is **NOT READY** to begin Phase 3 adversarial experiments due to several critical research-validity and measurement blockers:

1. **Phase 3 Attack Infrastructure is Empty:** The directory `attacks/` contains only an empty `__init__.py`, `benchmark_dataset/attack_cases.json` does not exist, and there is zero code implementing ground-truth evaluation predicates for `attack_success` or `breach_occurred`.
2. **Measurement Conflation of "Not Observed" vs. "Verified No Event" in Security Events:** In `pipeline/graph.py`, `security_events` unconditionally initializes `permission_denied: False`, `input_validation_failed: False`, and `output_validation_failed: False`. As a result, when security controls are disabled (Config A) or when execution halts at the authentication boundary, unmeasured controls are serialized to CSV as `False`. This falsely claims that inactive or skipped controls actively evaluated and verified the payload.
3. **Configuration Discrepancy (Config B Output Validation):** `docs/configuration_matrix.md` states Config B implements Output Validation as *"Length Only (5000 characters)"*. However, `agents/execution_agent.py` executes keyword content scanning whenever `output_validation` is enabled, causing Config B to silently enforce an 8-keyword content blocklist.
4. **Confounded Experimental Configurations:** Config B simultaneously bundles authentication, tool permission scoping, and output validation; Config C bundles input validation (length + keywords), tighter output truncation, and verbose logging. Individual control efficacy cannot be causally isolated under the current configuration matrix.
5. **Dormant Configuration Parameters:** `max_tool_calls_per_run: 3` in `configs/hardened.yaml` is never enforced in code. Furthermore, `agents/research_agent.py` can only ever select `read_file` or `web_search`, both of which are always permitted in Config B and C; tool permission scoping is therefore unable to reject any normal tool request.
6. **Fragile Config Name Resolution:** `load_security_config()` in `agents/planner_agent.py` silently defaults any unrecognized or misspelled configuration name (e.g., `"config_B"`, `"hardened"`) to `no_security.yaml`, opening a silent authentication and security bypass in programmatic invocations.

Phase 3 adversarial testing must remain paused until the prioritized remediation checklist in Section 9 is addressed and approved.

---

## 2. Repository Files Inspected

| File Path | Size (Bytes) | Role & Inspection Scope |
|:---|:---:|:---|
| `security/auth.py` | 5,436 | Authentication enforcement, constant-time comparison, secret resolution, self-referential check |
| `security/logging_config.py` | 1,194 | Dynamic logging level configuration across configs (INFO vs. DEBUG) |
| `pipeline/graph.py` | 11,876 | LangGraph state graph wiring, pipeline entry gating, latency measurement, event propagation |
| `main.py` | 7,393 | CLI entry point, argument parsing (`--config`, `--token`), baseline and single-task runners |
| `configs/no_security.yaml` | 305 | Config A specification (all security controls disabled) |
| `configs/basic_security.yaml` | 392 | Config B specification (auth, tool scoping, output validation) |
| `configs/hardened.yaml` | 545 | Config C specification (full defense: input/output validation, scoping, auth) |
| `metrics/collector.py` | 14,959 | Metrics collection, monotonic timing, schema migration, 20-column CSV writer |
| `agents/planner_agent.py` | 6,298 | Planner agent, input validation enforcement, `load_security_config()` |
| `agents/research_agent.py` | 7,351 | Research agent, tool parameter validation, tool permission scoping, output truncation |
| `agents/execution_agent.py` | 6,217 | Execution agent, final synthesis, output content scanning |
| `agents/evaluation_agent.py` | 6,864 | Evaluation agent, LLM-as-judge scoring, heuristic fallback, completion criteria |
| `results/raw_results.csv` | 7,827 | Historical benchmark results (44 historical rows + 20-column header) |
| `tests/test_security_controls.py` | 19,760 | Unit tests for auth, permission scoping, input/output validation (23 tests) |
| `tests/test_metrics.py` | 16,145 | Unit tests for latency, schema consistency, migration, security events (12 tests) |
| `tests/test_mcp_servers.py` | 3,432 | Unit tests for MCP server mock data and imports (6 tests) |
| `tests/test_mcp_integration.py` | 6,897 | Integration tests for stdio MCP client-server communication (3 tests) |
| `tests/test_groq_connection.py` | 3,740 | Live connectivity tests for Groq API and LangSmith tracing |
| `tests/test_happy_path.py` | 5,467 | End-to-end integration tests (asserts outdated 16-col schema, mutates raw CSV) |
| `docs/configuration_matrix.md` | 8,920 | Authoritative configuration reference documentation |
| `README.md` | 15,646 | Architecture, execution instructions, CSV specification |
| `reports/authentication_remediation_report.md` | 14,316 | Prior remediation report for authentication module |
| `reports/metrics_remediation_report.md` | 20,408 | Prior remediation report for metrics and latency |
| `reports/security_evaluation_report.md` | 25,994 | Early security evaluation report (2026-10-14) |
| `reports/PROJECT_HANDOVER_REPORT.md` | 83,773 | Comprehensive project handover documentation |

---

## 3. Authentication Verification Matrix

The authentication subsystem was verified by code inspection of `security/auth.py`, `pipeline/graph.py`, `main.py`, `configs/*.yaml`, and newly executed tests in `tests/test_security_controls.py`.

| # | Verification Item | Target Requirement | Code Reference | Verified Status | Notes & Evidence |
|:---:|:---|:---|:---|:---:|:---|
| 1 | **Config A Auth Disabled** | Must allow access without credentials | `security/auth.py`: lines 71–75 | **VERIFIED** | `auth_enabled = security_config.get("authentication", False)`. If `False`, returns `(True, None)` immediately. Validated by `test_auth_disabled_allows_access`. |
| 2 | **Config B & C Auth Required** | Must enforce credential check | `configs/basic_security.yaml`: line 3<br>`configs/hardened.yaml`: line 3 | **VERIFIED** | Both YAMLs declare `authentication: true`. `check_authentication()` rejects missing credentials. Validated by `test_config_b_enforcement` and `test_config_c_enforcement`. |
| 3 | **Secret / Credential Independence** | Server expected secret and client supplied token must be decoupled | `security/auth.py`: lines 78–93 | **VERIFIED** | Expected secret resolves from `expected_auth_secret` (`$AUTH_SECRET`). Client token is supplied via `auth_token` argument or `AUTH_TOKEN` env var. Distinct variable namespaces prevent self-matching. |
| 4 | **Rejection of Invalid States** | Reject missing secret, missing token, empty, whitespace, wrong, self-referential | `security/auth.py`: lines 78–107 | **VERIFIED** | Rejects: missing secret (`None`), unset env secret, self-referential (`$AUTH_TOKEN`), missing token (`None`), empty string (`""`), whitespace (`"   "`), incorrect token. All return `(False, "<reason>")`. |
| 5 | **Acceptance of Correct Credentials** | Matching credentials grant access | `security/auth.py`: lines 105–110 | **VERIFIED** | When `supplied_token == expected_secret`, returns `(True, None)`. Validated by `test_auth_enabled_with_correct_credential_allows_access`. |
| 6 | **Constant-Time Comparison** | Resist timing attacks | `security/auth.py`: line 105 | **VERIFIED** | `hmac.compare_digest(supplied_token, expected_secret)` is used for all comparisons. Eliminates short-circuit byte-comparison timing side-channels. |
| 7 | **Gating Gaps & Pipeline Prevention** | Auth failure must block graph construction and all agent executions | `pipeline/graph.py`: lines 273–295 | **VERIFIED** | Auth check occurs at pipeline entry. On failure, returns immediately. `create_graph()` and `graph.invoke()` are never called; zero LLM calls or MCP subprocesses spawned. Validated by `test_auth_failure_prevents_agents_from_running` (mocked graph verified uncalled). |
| 8 | **Secret & Credential Confidentiality** | No secret or token values in logs or errors | `security/auth.py`: lines 47, 80, 84, 89, 96, 101, 106 | **VERIFIED** | Error messages state reason only (`"invalid credential"`, `"empty credential"`, etc.). No tokens or secrets are formatted into error strings or loggers. |
| 9 | **CLI Token & Env Fallback** | `--token` flag takes precedence over `AUTH_TOKEN` env var | `main.py`: lines 193–198<br>`security/auth.py`: line 93 | **VERIFIED** | `main.py` parses `--token` and passes `auth_token=args.token`. In `auth.py`, `supplied_token = auth_token if auth_token is not None else os.getenv("AUTH_TOKEN")`. |
| 10 | **Default Configuration Safety** | Default configuration cannot bypass auth when Config B/C is requested | `main.py`: line 188<br>`agents/planner_agent.py`: lines 46–52 | **PARTIALLY VERIFIED / IDENTIFIED RISK** | CLI enforces `choices=["config_a", "config_b", "config_c"]`. However, in programmatic calls, `load_security_config()` silently defaults any invalid/misspelled string to `no_security.yaml` without raising an error. |

---

## 4. Metrics and Latency Verification Matrix

Verified through inspection of `metrics/collector.py`, `pipeline/graph.py`, `agents/*.py`, and `tests/test_metrics.py`.

| # | Verification Item | Target Requirement | Code Reference | Verified Status | Notes & Evidence |
|:---:|:---|:---|:---|:---:|:---|
| 1 | **Monotonic Timer Usage** | Use `time.perf_counter()`, not `time.time()` | `metrics/collector.py`: lines 156, 175<br>`pipeline/graph.py`: lines 259, 275, 322, 329 | **VERIFIED** | Monotonic high-resolution timer is used across all latency measurement points. No instances of `time.time()` for elapsed time. |
| 2 | **Latency Boundary Coverage** | Start/end boundaries measured on success, auth failure, and exception paths | `pipeline/graph.py`: lines 259, 275, 322, 329 | **VERIFIED** | $t_{\text{start}}$ captured at entry of `run_pipeline()`. $t_{\text{end}}$ captured immediately after auth check (Path A), after `graph.invoke()` (Path B), and in `except Exception` block (Path C). |
| 3 | **Fallback Latency Path** | Fallback works when `collector.start_run()` was not invoked | `metrics/collector.py`: lines 176–177 | **VERIFIED** | If `run_id not in self._run_start_times`, collector extracts `state["latency_ms"]`. Validated by `test_latency_calculation_from_state_fallback`. |
| 4 | **Point-of-Enforcement Security Events** | Events recorded at actual control point and propagated | `agents/planner_agent.py`: line 93<br>`agents/research_agent.py`: lines 156, 203<br>`agents/execution_agent.py`: line 163<br>`pipeline/graph.py`: lines 77, 119, 160 | **VERIFIED** | Events emitted directly as structured dictionaries (`{"security_events": {...}}`) by enforcement agents, merged into `state["security_events"]` in LangGraph nodes. |
| 5 | **Absence of Event vs. Verified Defense** | Inactive/skipped controls must not be recorded as verified defenses | `pipeline/graph.py`: lines 288–293, 308–313<br>`metrics/collector.py`: lines 198–222 | **FAILED (DEFECT)** | **Critical semantic conflation.** Controls are initialized to `False` in `pipeline/graph.py` even when disabled (Config A) or skipped (auth failure). See Section 4.1 below. |
| 6 | **Unmeasured Attack Outcomes** | `attack_success` and `breach_occurred` remain empty (`""`) when no attack evaluated | `metrics/collector.py`: lines 241–242 | **VERIFIED (NEW) / NOTED (LEGACY)** | Collector writes `""` when `attack_success` is `None`. Confirmed in recent CSV rows 38–45. Legacy rows 1–36 contain legacy `"False"` entries. |
| 7 | **Task Completion & Quality Score** | Matches documented definitions | `agents/evaluation_agent.py`: lines 82–170<br>`metrics/collector.py`: lines 230–231 | **VERIFIED** | `task_completed = quality_score >= 0.5` and `execution_success == True`. Fallback scoring uses word count heuristics when LLM is unavailable. |
| 8 | **CSV Row-Header Column Alignment** | CSV rows match 20-column header | `metrics/collector.py`: lines 35–56, 234–255 | **VERIFIED** | Declared `HEADERS` has 20 columns; `row` list has 20 elements. Validated by `test_csv_headers_and_row_consistency`. |
| 9 | **Legacy CSV Migration** | Preserves run IDs, timestamps, observations, notes, row counts | `metrics/collector.py`: lines 109–139 | **VERIFIED** | Legacy 16-col rows are padded with 4 empty strings before the notes column (`row[:15] + ["","","",""] + [row[15]]`). Tested in `test_historical_data_preservation_and_migration`. |
| 10 | **Migration Idempotency** | Re-running migration does not alter, duplicate, or reorder data | `metrics/collector.py`: line 111 | **VERIFIED** | If header matches `HEADERS`, migration is bypassed. When executed, 20-col rows are retained as-is. |
| 11 | **Preservation of Raw CSV** | File was not altered during audit | `results/raw_results.csv` | **VERIFIED** | Historical CSV was inspected read-only. File size (7,827 bytes) and row count (44 data rows) remain unaltered. |

---

### 4.1 Deep Dive: Security Events `False` ("Verified No Event") vs. `""` ("Not Observed")

A critical scientific distinction exists between:
1. **"Verified No Event Occurred" (`False`):** The security control was active, inspected the input/tool/output, and confirmed no violation occurred (e.g., Config C input validation scanned the input and found no prohibited keywords).
2. **"Not Observed / Unmeasured" (`""` / `None`):** The security control was never evaluated because:
   - The control was **disabled by configuration** (e.g., Config A disables all controls; Config B disables input validation).
   - The execution **halted upstream before reaching the control** (e.g., auth failure halted pipeline before planner or research ran; planner error aborted pipeline before tool execution).

**The Current Implementation Defect:**
In `pipeline/graph.py` (lines 288–293 and 308–313):
```python
# Auth failure path:
"security_events": {
    "auth_success": False,
    "permission_denied": False,       # DEFECT: Research agent never ran!
    "input_validation_failed": False, # DEFECT: Planner agent never ran!
    "output_validation_failed": False # DEFECT: Execution agent never ran!
}

# Pipeline initial state (even in Config A):
"security_events": {
    "auth_success": True,
    "permission_denied": False,       # DEFECT: Config A disables tool scoping!
    "input_validation_failed": False, # DEFECT: Config A/B disables input validation!
    "output_validation_failed": False # DEFECT: Config A disables output validation!
}
```

In `results/raw_results.csv`, rows 38–45 (logged under `config_a`) record:
`auth_success=True, permission_denied=False, input_validation_failed=False, output_validation_failed=False`.

**Scientific Consequence:** If an adversarial prompt containing injection keywords is evaluated under Config A, `input_validation_failed` will be recorded as `False`. A researcher analyzing the CSV would be unable to distinguish whether Config A defended against the injection or simply lacked an input filter. 

**Recommended Tri-State Semantic Architecture:**
Security event variables must be tri-state:
- `True`: Control was active, evaluated payload, and triggered (violation detected).
- `False`: Control was active, evaluated payload, and allowed (no violation).
- `""` (null): Control was disabled in YAML, or the node was not executed.

*(Per instructions, this fix alters metric semantics and CSV schema interpretation and is documented in Section 9 for researcher approval rather than silently applied).*

---

## 5. Exact Test Commands and Newly Observed Results

All tests were newly executed during this verification audit.

### 5.1 Test Execution Summary

| Test Command | Scope | Exit Code | Tests Passed | Tests Skipped | Tests Failed | Execution Time | External APIs |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| `python -m pytest tests/test_security_controls.py -v` | Auth, Scoping, Validation | **0** | **23** | 0 | 0 | 17.60s | None (Offline) |
| `python -m pytest tests/test_metrics.py -v` | Metrics, Latency, CSV Schema | **0** | **12** | 0 | 0 | 2.31s | None (Offline) |
| `python -m pytest tests/test_mcp_servers.py -v` | MCP Server Unit Tests | **0** | **6** | 0 | 0 | 1.08s | None (Offline) |
| `python -m pytest tests/test_mcp_integration.py -v` | MCP Integration (Pytest) | **0** | **1** | 2 | 0 | 1.02s | None (Offline) |
| `python -X utf8 tests/test_mcp_integration.py` | MCP Integration (Direct) | **0** | **3** | 0 | 0 | 7.85s | None (Subprocess) |
| **Total Automated Offline Tests** | | **0** | **45** | 0* | 0 | **29.86s** | **Zero API Calls** |

*\*Note: The 2 async integration tests skipped by pytest were fully validated via standalone runner in UTF-8 mode.*

### 5.2 Newly Observed Terminal Outputs

#### Command 1: `python -m pytest tests/test_security_controls.py -v`
```
platform win32 -- Python 3.13.13, pytest-8.3.5, pluggy-1.6.0
rootdir: E:\MCP-FRAMEWORK
plugins: anyio-4.13.0, langsmith-0.8.5, mock-3.14.0
collected 23 items

tests/test_security_controls.py::TestAuthentication::test_auth_disabled_allows_access PASSED [  4%]
tests/test_security_controls.py::TestAuthentication::test_auth_enabled_without_expected_secret_denies_access PASSED [  8%]
tests/test_security_controls.py::TestAuthentication::test_auth_enabled_without_supplied_credential_denies_access PASSED [ 13%]
tests/test_security_controls.py::TestAuthentication::test_auth_enabled_with_empty_credential_denies_access PASSED [ 17%]
tests/test_security_controls.py::TestAuthentication::test_auth_enabled_with_incorrect_credential_denies_access PASSED [ 21%]
tests/test_security_controls.py::TestAuthentication::test_auth_enabled_with_correct_credential_allows_access PASSED [ 26%]
tests/test_security_controls.py::TestAuthentication::test_auth_rejects_arbitrary_string PASSED [ 30%]
tests/test_security_controls.py::TestAuthentication::test_auth_rejects_self_referential_auth_token_secret PASSED [ 34%]
tests/test_security_controls.py::TestAuthentication::test_auth_with_env_var_reference PASSED [ 39%]
tests/test_security_controls.py::TestAuthentication::test_config_b_enforcement PASSED [ 43%]
tests/test_security_controls.py::TestAuthentication::test_config_c_enforcement PASSED [ 47%]
tests/test_security_controls.py::TestAuthentication::test_auth_failure_prevents_agents_from_running PASSED [ 52%]
tests/test_security_controls.py::TestAuthentication::test_get_authentication_status PASSED [ 56%]
tests/test_security_controls.py::TestToolPermissionScoping::test_config_a_allows_all_tools PASSED [ 60%]
tests/test_security_controls.py::TestToolPermissionScoping::test_config_b_allows_configured_tools PASSED [ 65%]
tests/test_security_controls.py::TestToolPermissionScoping::test_config_c_allows_configured_tools PASSED [ 69%]
tests/test_security_controls.py::TestToolPermissionScoping::test_permission_check_before_mcp_invocation PASSED [ 73%]
tests/test_security_controls.py::TestInputValidation::test_config_a_no_input_validation PASSED [ 78%]
tests/test_security_controls.py::TestInputValidation::test_config_c_input_validation_blocks_keywords PASSED [ 82%]
tests/test_security_controls.py::TestInputValidation::test_config_c_input_validation_blocks_long_input PASSED [ 86%]
tests/test_security_controls.py::TestInputValidation::test_config_c_input_validation_accepts_valid_input PASSED [ 91%]
tests/test_security_controls.py::TestOutputValidation::test_config_a_no_output_validation PASSED [ 95%]
tests/test_security_controls.py::TestOutputValidation::test_config_c_output_validation_truncates_long_output PASSED [100%]

============================= 23 passed in 17.60s =============================
```

#### Command 2: `python -m pytest tests/test_metrics.py -v`
```
collected 12 items

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

============================= 12 passed in 2.31s ==============================
```

#### Command 3: `python -m pytest tests/test_mcp_servers.py -v`
```
collected 6 items

tests/test_mcp_servers.py::test_web_search_mock_data PASSED              [ 16%]
tests/test_mcp_servers.py::test_web_search_exact_match PASSED            [ 33%]
tests/test_mcp_servers.py::test_web_search_partial_match PASSED          [ 50%]
tests/test_mcp_servers.py::test_file_read_data_folder PASSED             [ 66%]
tests/test_mcp_servers.py::test_file_read_import PASSED                  [ 83%]
tests/test_mcp_servers.py::test_web_search_import PASSED                 [100%]

============================== 6 passed in 1.08s ==============================
```

#### Command 4: `python -X utf8 tests/test_mcp_integration.py`
```
[10/15/26 20:36:53] INFO Processing request of type ListToolsRequest
                    INFO Processing request of type CallToolRequest
INFO:__main__:Mock search found exact match for: prompt injection
======================================================================
Running MCP Integration Tests
======================================================================

[Test 1] Checking research_agent implementation...
✓ research_agent uses MCP SDK (ClientSession, StdioServerParameters, stdio_client)
✓ research_agent does NOT directly import server modules
✓ research_agent implements call_mcp_tool() for MCP communication

[Test 2] Testing file-read server MCP connection...
✓ File-read server connected successfully
  Available tools: ['read_file']
✓ read_file tool is available
✓ Tool call succeeded, result length: 761 chars

[Test 3] Testing web-search server MCP connection...
✓ Web-search server connected successfully
  Available tools: ['web_search']
✓ web_search tool is available
✓ Tool call succeeded, result length: 321 chars

======================================================================
All MCP integration tests passed!
======================================================================
```

### 5.3 Safe Test Exclusions

1. **`tests/test_happy_path.py` (EXCLUDED):**
   - **Reason:** Calls un-mocked `run_pipeline()`, which dispatches real API calls to Groq. Furthermore, lines 47 and 102 call `collector.end_run()`, which would append unapproved test rows directly to `results/raw_results.csv`. Lines 143–154 also still test for the obsolete 16-column CSV schema and would fail against the 20-column schema.
2. **`tests/test_groq_connection.py` (EXCLUDED):**
   - **Reason:** Explicitly designed to invoke live completions against Groq API endpoint (`openai/gpt-oss-120b`). Skipped to preserve offline testing boundaries and prevent API consumption.

---

## 6. Historical CSV Integrity Findings

Inspection of `results/raw_results.csv`:

```
File: results/raw_results.csv
Size: 7,827 bytes
Lines: 46 (1 Header Row + 44 Observation Rows + 1 Trailing Newline)
Declared Columns: 20
```

### 6.1 Column Alignment Verification
Every row in `results/raw_results.csv` contains exactly 19 commas (20 columns). There are zero orphaned trailing columns and zero truncated rows.

### 6.2 Data Cohorts
The historical observations fall into two distinct historical cohorts:

1. **Cohort 1: Legacy Baseline Runs (Rows 1–36, Runs 1 to 36):**
   - **Timestamps:** `2026-08-17T12:33:24` to `2026-10-14T11:08:22`.
   - **Schema Origin:** Generated under the legacy 16-column format.
   - **Migration Assessment:** Successfully migrated. The 4 new security event columns (indices 15–18: `auth_success`, `permission_denied`, `input_validation_failed`, `output_validation_failed`) are populated with empty strings `""`, accurately representing that security events were uninstrumented at the time. The `notes` field was shifted to column 19 without data truncation.
   - **Anomaly Observed:** Columns 6 and 7 (`attack_success` and `breach_occurred`) contain `"False"` rather than `""`. This occurred because the original pre-remediation collector hardcoded `.get("attack_success", False)`.
2. **Cohort 2: Post-Remediation Baseline Runs (Rows 37–44, Runs 37 to 44):**
   - **Timestamps:** `2026-10-14T18:35:53` to `2026-10-14T18:38:00`.
   - **Schema Origin:** Generated directly under the 20-column schema.
   - **Attack Outcomes:** Columns 6 and 7 are correctly empty strings `""`.
   - **Security Events:** Recorded as `True,False,False,False` under `config_a` (illustrating Defect 4.1).

---

## 7. Configuration Comparison and Research-Validity Risks

### 7.1 Cross-Configuration Matrix: YAML vs. Actual Code Enforcement

| Parameter | Config A (`no_security.yaml`) | Config B (`basic_security.yaml`) | Config C (`hardened.yaml`) | Actual Enforcement Location |
|:---|:---:|:---:|:---:|:---|
| **Authentication** | `false` | `true` | `true` | `security/auth.py` (via `pipeline/graph.py`) |
| **Auth Secret Key** | N/A | `"$AUTH_SECRET"` | `"$AUTH_SECRET"` | Loaded from environment |
| **Tool Scoping** | `false` | `true` | `true` | `agents/research_agent.py`: line 148 |
| **Allowed Tools** | `planner: *`<br>`research: *`<br>`execution: *`<br>`evaluation: *` | `planner: none`<br>`research: [read_file, web_search]`<br>`execution: none`<br>`evaluation: none` | Same as Config B | Only enforced in `research_agent.py`; planner/execution/evaluation restrictions are decorative |
| **Input Validation** | `false` | `false` | `true` | `agents/planner_agent.py`: line 83 |
| **Max Input Length** | N/A | N/A | `500` chars | `agents/planner_agent.py`: line 98 |
| **Input Block Keywords**| N/A | N/A | 5 keywords | `agents/planner_agent.py`: line 88 |
| **Output Validation** | `false` | `true` | `true` | `research_agent.py` & `execution_agent.py` |
| **Max Output Length** | N/A | `5000` chars | `2000` chars | `agents/research_agent.py`: line 186 |
| **Output Content Scan** | None | **8 Default Keywords (UNDOCUMENTED)** | 5 Configured Keywords | `agents/execution_agent.py`: lines 130–151 |
| **Max Tool Calls** | N/A | N/A | `3` (DECLARED) | **NOT ENFORCED ANYWHERE IN CODE** |
| **Logging Level** | `basic` (INFO) | `standard` (INFO) | `verbose` (DEBUG) | `security/logging_config.py` |

### 7.2 Research Validity and Causal Attribution Hazards

1. **Bundling Confound: Config A vs. Config B:**
   - Moving from Config A to Config B enables: (1) Authentication, (2) Tool Permission Scoping, and (3) Output Length Truncation (5000 chars) + Content Scanning.
   - **Threat:** If an attack succeeds in Config A but fails in Config B, or if latency increases, the researcher **cannot attribute the effect to authentication vs. tool scoping vs. output truncation**. They are bundled as an all-or-nothing step.
2. **Bundling Confound: Config B vs. Config C:**
   - Moving from Config B to Config C enables: (1) Input keyword blocking, (2) Input length limit (500 chars), (3) Stricter output truncation (2000 vs 5000 chars), and (4) Stricter output keyword scanning.
   - **Threat:** A drop in Task Completion Rate (TCR) cannot be causally attributed to legitimate inputs exceeding 500 characters versus legitimate inputs triggering keyword false positives.
3. **Inability to Test Tool Permission Scoping in Baseline:**
   - In `agents/research_agent.py`, the only tool choices hardcoded into the agent logic are `read_file` (if query starts with `"file:"`) and `web_search` (otherwise).
   - In Config B and Config C, `allowed_tools.research` contains both `read_file` and `web_search`.
   - **Consequence:** Under normal baseline conditions, tool permission scoping can **never trigger a denial**. Unless Phase 3 specifically introduces an agent capable of generating arbitrary tool names, the scoping control is non-operational.
4. **Undocumented Content Scan in Config B:**
   - In `agents/execution_agent.py` (lines 130–143), `if config.get("output_validation", False):` executes. Because Config B has `output_validation: true` but omits `block_keywords`, the code falls back to an internal list of 8 hardcoded keywords (`"system prompt"`, `"instruction set"`, etc.).
   - This directly contradicts `docs/configuration_matrix.md`, which defines Config B as *"Length Only"*.

---

## 8. Every Confirmed Defect with References

### Defect 1: Undocumented Output Content Filtering in Config B
- **File:** `agents/execution_agent.py` (lines 130–143)
- **Defect:** When `output_validation: true` is set in Config B, `execution_agent` falls back to default `block_keywords` and blocks responses containing terms like `"system prompt"`.
- **Mismatch:** `docs/configuration_matrix.md` (lines 13, 132) explicitly documents Config B as *"Length Only (5000 characters)"* with content scanning restricted to Config C.

### Defect 2: Unmeasured Security Controls Initialized as Verified Defenses (`False`)
- **File:** `pipeline/graph.py` (lines 288–293, 308–313) and `metrics/collector.py` (lines 198–222)
- **Defect:** `permission_denied`, `input_validation_failed`, and `output_validation_failed` are set to `False` at pipeline inception and on auth failure.
- **Impact:** Disabled or unexecuted security controls are serialized as `False`, falsely indicating that defenses were actively evaluated and passed.

### Defect 3: Silent Fallback to Config A on Misspelled Configuration Name
- **File:** `agents/planner_agent.py` (line 52) and `agents/research_agent.py` (line 42)
- **Defect:** `config_map.get(config_name, "no_security.yaml")` defaults to `"no_security.yaml"` for any unrecognized string.
- **Impact:** Programmatic callers passing `"Config_B"`, `"config-c"`, or `"hardened"` will silently run with authentication and security controls completely disabled.

### Defect 4: Declared `max_tool_calls_per_run` is Dormant
- **File:** `configs/hardened.yaml` (line 14)
- **Defect:** `max_tool_calls_per_run: 3` is declared in YAML and handover reports, but never referenced anywhere in executable Python code.

### Defect 5: Vacuous Tests for Scoping and Output Validation
- **File:** `tests/test_security_controls.py` (lines 374–380, 440–448)
- **Defect:** `test_permission_check_before_mcp_invocation` and `test_config_c_output_validation_truncates_long_output` assert only that YAML booleans are `True`. Neither test executes an unauthorized tool or an over-length string to verify that enforcement logic actually triggers.

### Defect 6: `test_happy_path.py` Schema Mismatch and Mutating Side-Effects
- **File:** `tests/test_happy_path.py` (lines 47, 102, 143–154)
- **Defect:** Executes unmocked pipeline runs against Groq, appends unapproved rows to `results/raw_results.csv`, and asserts obsolete 16-column headers.

### Defect 7: Windows Console `UnicodeEncodeError` in MCP Integration Test
- **File:** `tests/test_mcp_integration.py` (lines 47, 54, 63, 150)
- **Defect:** Prints Unicode checkmark `\u2713` directly to stdout, crashing on default Windows `cp1252` encoding unless run with `-X utf8` or UTF-8 environment settings.

### Defect 8: Missing `pytest-asyncio` Dependency for Async Tests
- **File:** `tests/test_mcp_integration.py` (lines 26, 73)
- **Defect:** Pytest emits `PytestUnhandledCoroutineWarning` and skips async test coroutines unless `pytest-asyncio` is installed and registered.

### Defect 9: Non-Null Serialization Safeguard Missing in Metrics Collector
- **File:** `metrics/collector.py` (lines 250–253)
- **Defect:** `str(auth_success)` does not guard against `None`. If `auth_success` is `None` (unmeasured), it writes `"None"` instead of `""`.

---

## 9. Prioritized Remediation Checklist

### Priority 0: Pre-Phase 3 Blockers (Must Complete Before Any Attack Runs)

- [ ] **P0.1 Implement Attack Test Harness and Labeled Dataset**
  - Create `benchmark_dataset/attack_cases.json` with structured schemas: `attack_id`, `attack_type` (direct prompt injection, indirect injection, tool poisoning, unauthorized tool invocation), `payload`, `canary_token`, `target_config`, and `ground_truth_criteria`.
  - Implement attack injection runner in `attacks/` that populates `state["attack_injected"] = True` and sets `state["attack_type"]`.

- [ ] **P0.2 Define and Implement Objective Attack Success & Breach Evaluators**
  - Replace placeholder attack outcome logging with deterministic ground-truth checks:
    - *Canary Exfiltration:* Regex detection of target secret in execution output.
    - *Goal Hijacking:* Deterministic compliance checks against attacker instruction.
    - *Unauthorized Tool Invocation:* Interception of forbidden tool requests in `call_mcp_tool()`.
  - Ensure `attack_success` and `breach_occurred` are populated only during attack evaluations, remaining `""` during baseline runs.

- [ ] **P0.3 Fix Tri-State Security Events (Approval Requested)**
  - Update `pipeline/graph.py` and `metrics/collector.py` to record `None` (serialized as `""`) for security events when a control is disabled in YAML or when upstream execution failed before reaching the control node.

- [ ] **P0.4 Align Config B Output Validation with Documentation**
  - Modify `agents/execution_agent.py` line 130 to check `if config.get("output_validation", False) and config.get("block_keywords"):`, ensuring Config B enforces length-only truncation as documented, or update `docs/configuration_matrix.md` if content scanning was intended.

- [ ] **P0.5 Fix Unrecognized Configuration Handling in `load_security_config()`**
  - Replace `config_map.get(config_name, "no_security.yaml")` with strict validation that raises `ValueError(f"Invalid security configuration: '{config_name}'. Must be one of {list(config_map.keys())}")`.

### Priority 1: Measurement Integrity and Test Suite Robustness

- [ ] **P1.1 Update and Mock `tests/test_happy_path.py`**
  - Update expected header assertion to 20 columns.
  - Redirect CSV logging to a temporary directory (`tmp_path`) to prevent contaminating `results/raw_results.csv`.
  - Mock `ChatGroq` calls to allow safe, offline end-to-end regression testing.

- [ ] **P1.2 Add Concrete Enforcement Tests for Scoping and Output Truncation**
  - In `tests/test_security_controls.py`, add a test passing an unpermitted tool name to `research_agent()` to verify permission denial.
  - Add a test verifying that `research_agent()` truncates strings exceeding `max_output_length` and appends `[TRUNCATED: ...]`.

- [ ] **P1.3 Fix MCP Test Script Windows Encoding and Async Runner**
  - In `tests/test_mcp_integration.py`, replace `\u2713` with ASCII `[PASS]` or configure UTF-8 stdout wrapper.
  - Add `pytest-asyncio` to `requirements.txt` to enable native pytest execution of async MCP tests.

### Priority 2: Research Design Enhancements (For Phase 4 Paper)

- [ ] **P2.1 Document Experimental Bundling Limitations**
  - In research paper methodology, explicitly note that Config B and C represent cumulative defense baselines rather than isolated factorial treatments.
- [ ] **P2.2 Enforce or Remove `max_tool_calls_per_run`**
  - Implement loop counter in `agents/research_agent.py` to enforce the 3-tool limit declared in `hardened.yaml`, or delete the dormant parameter from YAML.

---

## 10. Separation of Verified Facts, Report Claims, and Unresolved Questions

### 10.1 Verified Facts (Empirically Confirmed)
1. Offline security control unit tests pass (23/23 tests in `tests/test_security_controls.py`).
2. Offline metrics collection and latency unit tests pass (12/12 tests in `tests/test_metrics.py`).
3. Offline MCP server functionality tests pass (6/6 tests in `tests/test_mcp_servers.py`).
4. Monotonic `time.perf_counter()` is used for all elapsed-time measurements.
5. Authentication gating in Config B and C completely prevents agent execution, graph construction, and Groq inference upon credential failure.
6. Constant-time comparison (`hmac.compare_digest`) is used for credentials.
7. Secrets and presented tokens are never logged or exposed in error messages.
8. Historical `results/raw_results.csv` contains 44 rows aligned to the 20-column schema without row loss.

### 10.2 Report Claims Corrected
1. *Claim in Prior Reports:* "All security controls are fully verified by tests."  
   *Correction:* Output truncation and permission denial tests in `test_security_controls.py` were vacuous checks that only verified YAML dictionary boolean presence.
2. *Claim in Prior Reports:* "Config B output validation is Length Only."  
   *Correction:* `agents/execution_agent.py` executes content pattern scanning in Config B using an internal 8-keyword fallback list.
3. *Claim in Prior Reports:* "Security events track ground truth."  
   *Correction:* Inactive and unreached security controls are logged as `False`, creating false positive defense records under Config A.

### 10.3 Unresolved Questions for Researcher Approval
1. **Output Validation in Config B:** Should Config B enforce length-only truncation (requiring an edit to `agents/execution_agent.py`), or should `docs/configuration_matrix.md` be updated to reflect that content scanning is enabled in Config B?
2. **Tri-State Metric Schema:** Do you approve migrating `security_events` to a tri-state model (`True`, `False`, `""`), where disabled or unreached controls serialize as empty strings?
3. **Historical Data Normalization:** Should historical rows 1–36 in `results/raw_results.csv` have `attack_success` and `breach_occurred` cleaned from `"False"` to `""` to match rows 37–44, or must the raw historical file remain strictly immutable?

---

*Report prepared by Antigravity AI Pair Programmer. Phase 3 experiments have not been started.*
