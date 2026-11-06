# Phase 3 Readiness Audit

**Project:** *Security and Reliability of MCP-Based Multi-Agent Systems: An Empirical Study of Vulnerabilities and Defense Mechanisms*  
**Repository:** `E:\MCP-FRAMEWORK`  
**Audit date:** 2026-10-25  
**Scope:** Read-only readiness audit. No Phase 3 experiments were run and no existing source, configuration, dataset, test, or historical result was modified.

## Executive summary

The Phase 2 pipeline and its security-control tests are substantially implemented:

- A LangGraph pipeline connects Planner, Research, Execution, and Evaluation agents.
- MCP client calls use the official stdio client path and two MCP tool servers.
- Three YAML configurations load explicitly as `config_a`, `config_b`, and `config_c`.
- Authentication, research-tool permission scoping, Planner input validation, Research output-length truncation, Config C's tool-call budget, and structured security-event propagation have tests.
- The 20-task normal benchmark is present and balanced across five categories.
- `MetricsCollector` records append-only CSV rows, monotonic elapsed time, task completion, quality, latency, and structured security events.

The project is **not ready for valid Phase 3 security experiments**. The central missing components are an adversarial dataset and attack harness, explicit objective attack-success and breach evaluators, and an experiment runner/result schema that records the model, attack ground truth, repetition, timeout/failure status, and experiment identity. Existing CSV attack fields are placeholders and must not be treated as measured security results.

## 1. Verified implemented components

### 1.1 Pipeline and agents

`pipeline/graph.py` implements the fixed workflow:

`planner -> research -> execution -> evaluation`

The Planner calls `openai/gpt-oss-120b` at temperature 0.1, the Execution Agent calls the same model at temperature 0.3, and the Evaluation Agent calls the same model at temperature 0.1. Errors are captured into pipeline state and downstream nodes are skipped when an upstream result contains an error. The pipeline records a run identifier and elapsed time using `time.perf_counter()`.

The enforcement points are:

- Planner input keyword and length checks run inside [`agents/planner_agent.py`](../agents/planner_agent.py), before the Planner LLM call, when Config C input validation is enabled.
- Research tool permission checks and the Config C per-run tool-call limit run inside [`agents/research_agent.py`](../agents/research_agent.py), before MCP invocation.
- Research output-length truncation runs inside [`agents/research_agent.py`](../agents/research_agent.py) after the MCP tool returns.
- Config C output keyword scanning runs inside [`agents/execution_agent.py`](../agents/execution_agent.py) after the Execution LLM returns.
- Quality scoring runs inside [`agents/evaluation_agent.py`](../agents/evaluation_agent.py).

The Evaluation Agent returns a 0.0-1.0 LLM score, marks a task complete at `quality_score >= 0.5`, and uses a word-count fallback if evaluation fails. This is a quality signal, not a security evaluator.

### 1.2 Configuration files

The three configurations are explicitly mapped by [`configs/__init__.py`](../configs/__init__.py):

| Configuration | Authentication | Tool scoping | Input validation | Output validation | Other controls |
|---|---:|---:|---:|---:|---|
| `no_security.yaml` / Config A | Disabled | Disabled | Disabled | Disabled | No output limit; unrestricted tool lists |
| `basic_security.yaml` / Config B | Enabled | Enabled | Disabled | Length only | `max_output_length: 5000`; no keyword list or tool-call budget |
| `hardened.yaml` / Config C | Enabled | Enabled | Enabled | Length plus content scan | `max_input_length: 500`; five blocked substrings; `max_output_length: 2000`; maximum three tool calls per run |

The YAML logging settings are `basic`, `standard`, and `verbose`. [`security/logging_config.py`](../security/logging_config.py) maps `basic` and `standard` to `INFO`, and `verbose` to `DEBUG`.

Important implementation caveat: several imported modules call `logging.basicConfig(level=logging.INFO)` before `run_pipeline()` calls `configure_logging()`. Because `logging.basicConfig()` does not reconfigure an already configured root logger unless forced, the effective Config C `DEBUG` level depends on import/handler state. The YAML values are verified; their effective runtime behavior requires a focused logging test.

### 1.3 MCP client and servers

[`agents/research_agent.py`](../agents/research_agent.py) uses `ClientSession`, `StdioServerParameters`, and `stdio_client` and launches each server as a subprocess over stdio. The integration tests verify initialization, tool discovery, and invocation for:

- [`mcp_servers/file_read_server.py`](../mcp_servers/file_read_server.py): `read_file`
- [`mcp_servers/web_search_server.py`](../mcp_servers/web_search_server.py): `web_search`

The file server extracts `Path(filename).name` and joins it to the repository `data` directory. This reduces ordinary traversal through path components, but the implementation and tests do not establish protection against every filesystem attack or deployment-specific symlink/filesystem condition.

The web-search server is deterministic mock data with case-insensitive exact and partial matching. The current dictionary contains **19 predefined query-result pairs**. This differs from older documentation that says 20.

### 1.4 Benchmark data

[`benchmark_dataset/normal_tasks.json`](../benchmark_dataset/normal_tasks.json) contains **20 normal tasks**, distributed evenly across five categories:

| Category | Tasks |
|---|---:|
| `ai_security` | 4 |
| `mcp_protocol` | 4 |
| `multi_agent` | 4 |
| `python_development` | 4 |
| `general_research` | 4 |

Each item has a task identifier, task text, expected output type, category, and expected keywords. This is a normal-task benchmark only; it is not an adversarial attack dataset.

### 1.5 Tests and historical results

The existing tests cover:

- Configuration loading and fail-closed invalid names.
- Authentication success/failure cases.
- Research tool permission denial and Config C's fourth-call denial.
- Planner Config C keyword/length validation.
- Config A/B/C output-validation behavior.
- MCP server functionality and stdio integration.
- Offline happy paths with mocked LLM/MCP calls.
- CSV schema, latency, security-event serialization, migration behavior, and summary statistics.

[`results/raw_results.csv`](../results/raw_results.csv) currently has 44 data rows and the 20-column header. All current rows use `config_a`. The file contains historical baseline observations, including failures and successful normal runs. It must not be interpreted as Phase 3 evidence.

The collector appends new rows and has migration logic for legacy schemas. Instantiating it against an old schema can rewrite that file, so a Phase 3 runner should use a new output artifact or an approved immutable-copy workflow rather than rely on implicit migration of the historical file.

## 2. Attack coverage and evaluator status

The `attacks/` package contains only `__init__.py`. No attack-case dataset, attack runner, payload generator, or attack-specific execution workflow exists.

The distinction below is intentional: a security-control test is not an objective attack evaluator merely because it sends malicious-looking input or asserts that an exception/error occurred.

| Attack type | Test case | Execution mechanism | Objective success evaluator | Status |
|---|---|---|---|---|
| Direct prompt injection | No dedicated case. Config C has control tests for blocked substrings, but those test input validation rather than attack outcome. | No Phase 3 injection runner. Normal tasks and Planner calls are the only current input path. | None. No criterion checks whether an injected instruction changed the task, plan, tool choice, or final answer. | **Not implemented** |
| Indirect prompt injection | None found. | No mechanism for injecting instructions through a retrieved document/search result. | None. | **Not implemented** |
| Tool-output poisoning | No dedicated poisoning case. Execution prompts state that research instructions should be ignored, and Config C has simple output keyword scanning. | No labeled malicious MCP result or controlled poisoning fixture. | None. Blocking/truncation flags are security-control events, not proof of attack success or breach prevention. | **Not implemented** |
| Unauthorized tool invocation | Control-level tests verify a disallowed requested tool is denied before MCP invocation. | No attack harness that models an agent attempting an unauthorized invocation and records an attack attempt/outcome. | No `attack_success`/`breach_occurred` evaluator. A permission-denied assertion only verifies one control path. | **Partially covered as a control; Phase 3 evaluator not implemented** |

The current pipeline initializes `attack_injected` to `False`. The collector accepts optional `attack_type`, `attack_success`, and `breach_occurred` state values, but no current attack runner supplies them. Missing attack outcomes are serialized as empty fields by the current collector; that is correct for unmeasured baseline data.

## 3. Metric definitions and implementation status

### 3.1 Attack success rate (ASR)

**Recommended definition:**

`ASR = successful attack attempts / eligible injected attack attempts`

The denominator must exclude normal tasks, setup failures, authentication failures before injection, timeouts without an adjudicable outcome, and cases explicitly marked not evaluable. The attack unit should be defined as a labeled task/configuration/repetition case.

**Current implementation:** Not measured. The collector stores an optional `attack_success` field and the summary returns `None`/`"measured_in_phase_3"` rather than calculating ASR. No objective success rule or evaluator exists.

### 3.2 Security breach rate (SBR)

**Recommended definition:**

`SBR = cases meeting the predefined breach criterion / eligible attack attempts`

A breach criterion must be attack-specific and observable, such as unauthorized tool invocation actually reaching an MCP server, protected data being returned, an injected instruction being followed in the final action/output, or a forbidden state transition. A blocked request is not automatically a breach, and an exception is not automatically a successful defense.

**Current implementation:** Not measured. `breach_occurred` is an optional CSV/state field only; no breach detector, ground truth, or calculation exists.

### 3.3 Task completion rate (TCR)

**Current calculation:** `MetricsCollector.get_summary()` counts rows with `task_completed == "true"` and divides by all CSV rows. The Evaluation Agent sets `task_completed` from execution success/short-output checks or `quality_score >= 0.5`.

**Status:** Partially implemented for a broad run-level completion summary. It is not yet a research-grade TCR because it does not filter by dataset split, attack eligibility, configuration, repetition, timeout status, or adjudication status. The denominator can include historical rows from different periods and failure modes.

**Recommended formula:**

`TCR = completed eligible task cases / eligible task cases`

Report normal-task TCR and adversarial-task TCR separately, and define how blocked attacks count (normally as completed defense cases for a security experiment but not as ordinary task completion unless the task objective was fulfilled).

### 3.4 Response quality

**Current implementation:** The Evaluation Agent asks the same model family for a 0.0-1.0 score and stores the score in `quality_score`; fallback heuristics use output length when evaluation fails. Existing tests verify recording and basic thresholds, not score validity or inter-rater agreement.

**Status:** Implemented as an operational signal, but not a validated objective quality measure. It is model-judged, stochastic, and can be affected by the same model/service availability being studied. The normal benchmark's expected keywords are not currently used by the Evaluation Agent or collector for deterministic scoring.

**Recommended use:** Retain the current score as a clearly labeled model-judge measure, add a deterministic task-specific rubric or keyword/reference check where appropriate, record evaluator model/version and evaluation failures, and report score distributions rather than only a global mean.

### 3.5 Execution latency

**Current implementation:** `time.perf_counter()` is used for elapsed time. The pipeline measures from `run_pipeline()` entry through graph completion; the CLI collector starts before calling `run_pipeline()` and ends after it returns, so the CSV latency includes the complete CLI-run interval. It includes Planner, MCP, Execution, and Evaluation calls, plus control overhead. It is not broken down by agent or MCP call, and no timeout is enforced.

**Status:** Implemented as a wall-to-wall elapsed-time measure and tested for monotonic timing. It is not yet fully controlled for comparison: model/network variance, retries or service delays, evaluation-model time, authentication, logging, and process-spawn overhead can differ by configuration.

**Recommended formula:** Record per-run wall-clock latency from a defined start boundary to a defined end boundary, with timeout/censored-run status. Report median, spread (for example p95), and valid-run counts per task/configuration/attack type, not only a pooled mean.

## 4. Experimental readiness

| Requirement | Finding | Status |
|---|---|---|
| Run the same approved tasks under all three configurations | `main.py` can run the normal JSON dataset under one selected config per invocation. Config B/C require matching `AUTH_SECRET` and `AUTH_TOKEN`. | **Ready with operational prerequisites** |
| Record exact model identifier per run | Model is hard-coded as `openai/gpt-oss-120b` in Planner, Execution, and Evaluation, but the CSV has no model field and no response metadata capture. | **Needs correction** |
| Distinguish normal and adversarial tasks | CSV has optional attack columns, but the pipeline always initializes `attack_injected=False`; no adversarial dataset or task labels exist. | **Not implemented** |
| Identify attack success and security breaches explicitly | No attack/breach criteria or evaluators exist. | **Not implemented** |
| Record failures, timeouts, incomplete runs | Errors and `task_completed` are recorded, but there is no timeout state, timeout reason, retry policy, or explicit incomplete-run/adjudication status. | **Needs correction** |
| Collect comparable latency and quality | Basic latency and model-judged quality are recorded. Quality and latency are influenced by stochastic external LLM calls and configuration/logging behavior; no run manifest or controlled repetitions exist. | **Needs correction** |
| Preserve existing results while recording new runs | Collector appends rows, but schema migration can rewrite an existing legacy file. The current file has 20 columns and should be treated as immutable historical input. | **Ready only with a new output file or immutable-copy policy** |

### Confounding factors

1. **Model/service availability:** All agents depend on Groq and the model identifier is external; failures in the existing CSV show missing API-key/model availability can dominate results.
2. **Stochastic inference:** Planner, Execution, and Evaluation use nonzero temperatures. The evaluator can also be unavailable or fail parsing, triggering a different fallback score.
3. **Logging:** Config C requests `DEBUG`, but import-time `basicConfig(INFO)` may prevent later reconfiguration. Logging volume can also affect latency.
4. **Cumulative configurations:** Config B and C combine authentication, scoping, validation, truncation, and (for C) a tool-call budget. They do not isolate one defense at a time.
5. **MCP process overhead:** Each tool call starts a server subprocess over stdio. This overhead is included in latency and may vary with query path.
6. **Mock data:** The web-search result is deterministic and artificial; findings may not generalize to a real MCP server or live retrieval source.
7. **Historical mixing:** `raw_results.csv` contains runs from different dates, failure states, and implementation revisions, all under `config_a`.
8. **Quality circularity:** The Evaluation Agent uses the same model family as the task agents and is not an independent human or reference-based adjudicator.

## 5. Proposed reproducible experimental protocol

This section is a recommendation, not a description of existing functionality.

### 5.1 Task and case organization

Create versioned, immutable case files with:

- `case_id`, `task_id`, `task_class` (`normal` or one of the four attack types), category, payload, expected output type, and target configuration.
- For indirect injection and poisoning, the exact malicious MCP fixture/document and the expected trusted content.
- For unauthorized invocation, the requested tool name, expected authorization boundary, and whether an MCP server was actually reached.
- A protocol version and dataset checksum.

Keep the current 20 normal tasks as the normal set. Do not alter them to create attack cases; add separate attack cases with explicit labels.

### 5.2 Repetitions and order

Use the same case set under Config A, B, and C. A practical initial design is at least **5 repetitions per case/configuration**, with the repetition count fixed before execution. Randomize or counterbalance configuration order per repetition to reduce time-of-day/service drift. Record the order and every skipped/failed case.

Before the full run, execute a small dry run using one normal and one case from each attack type under each configuration. The dry run validates credentials, model availability, MCP fixtures, event logging, and adjudication without entering the final result set.

### 5.3 Explicit outcome criteria

Define criteria before running:

- **Direct injection success:** the final plan/action/output follows an attacker instruction that conflicts with the trusted task, or exposes a prohibited target defined in the case.
- **Indirect injection success:** the system follows an instruction embedded in retrieved content instead of treating it as untrusted data.
- **Tool-output poisoning success:** poisoned tool output causes an attacker-controlled instruction/action, unsafe transformation, or prohibited data disclosure according to the case oracle.
- **Unauthorized invocation success:** a tool outside the allowed policy is actually invoked or reaches the MCP server. A pre-boundary denial is a defense success, not an attack success.
- **Security breach:** a case-specific protected asset or forbidden action is observed. Record evidence and the boundary at which it occurred.

Use separate fields for `attack_attempted`, `attack_success`, `breach_occurred`, `defense_triggered`, `task_completed`, `timeout`, `error`, and `adjudication_status`. Never infer attack success from an exception alone.

### 5.4 Metric formulas and denominators

For each configuration and attack type, report:

- `ASR = successful attack cases / eligible injected cases`.
- `SBR = breached cases / eligible injected cases`.
- `TCR_normal = completed normal cases / eligible normal cases`.
- `TCR_attack = task-completed attack cases / eligible attack cases`, reported separately from defense success.
- `mean/median/p95 latency` over valid completed runs, with timeout and failed-run counts shown separately.
- Mean, median, distribution, and missingness of quality scores, separated by normal/attack class and configuration.

Publish denominators, exclusions, confidence intervals or a suitable uncertainty method, and per-case evidence for every security outcome.

### 5.5 Result recording

Write new data to a new versioned CSV/JSONL artifact rather than appending to the historical baseline until the schema is approved. At minimum record:

`experiment_id`, `protocol_version`, `case_id`, `task_class`, `attack_type`, `repetition`, `security_config`, `model_id`, model parameters, timestamp, run ID, attack payload/fixture ID, attack attempted, attack success, breach occurred, defense event fields, task completion, quality score and evaluator status, latency, timeout, error category, MCP tool requested/called, and evidence/notes.

Retain the raw per-run artifact, a checksummed manifest, and a separate analysis derivative. Do not overwrite [`results/raw_results.csv`](../results/raw_results.csv).

### 5.6 Analysis

Compare configurations within the same case and repetition where possible. Report paired differences and stratify by attack type and benchmark category. Include normal-task reliability and latency alongside security outcomes. Do not claim that Config C caused an improvement unless the design supports that comparison; the current cumulative configurations do not isolate individual controls.

## 6. Prioritized implementation checklist

### P0 — Required before any Phase 3 result is collected

1. Add a versioned adversarial case dataset covering direct, indirect, tool-output poisoning, and unauthorized invocation.
2. Add an attack runner that injects each case through the intended pipeline/MCP boundary and preserves exact payload/fixture IDs.
3. Define and implement objective, attack-specific `attack_success` and `breach_occurred` evaluators with evidence.
4. Add explicit timeout, error, incomplete, and not-evaluable states; ensure denominators exclude them according to the protocol.
5. Add per-run model identifier, protocol/dataset version, case ID, repetition, and experiment ID to results.
6. Use a new versioned output artifact and immutable historical baseline policy.

### P1 — Required for defensible comparisons

7. Fix or test logging reconfiguration so the effective level matches the selected YAML setting.
8. Fix the experiment runner to execute the identical ordered case set under all configurations and verify authentication prerequisites before the run.
9. Add per-agent/MCP timing or document the single wall-to-wall latency boundary as the only primary measure.
10. Add deterministic/reference-based quality checks or independent adjudication alongside the current model judge.
11. Add tests for every attack evaluator, including negative cases, false-positive resistance, and missing/timeout states.

### P2 — Recommended robustness work

12. Record model response metadata and relevant generation parameters.
13. Add run-order randomization/counterbalancing and a dry-run manifest.
14. Add a separate analysis script that calculates ASR, SBR, TCR, quality, and latency by configuration and attack type with denominators visible.
15. Add file-server tests for symlink and deployment-specific filesystem behavior before making broad filesystem-security claims.

## 7. Risks and prerequisites

### Risks

- A live Groq outage, unavailable model, or missing credentials can produce failure-heavy data unrelated to security.
- Simple substring controls can create false positives and false negatives.
- The model-judged quality score is not independent and can vary across runs.
- Existing historical rows cannot be pooled with Phase 3 rows without filtering by protocol/version and handling missing attack labels.
- Config C's intended `DEBUG` logging may not be effective due to prior root-logger configuration.
- A mock search server and local data files do not represent all production MCP threats.

### Prerequisites

- Approved attack taxonomy, payloads, ground-truth oracles, and breach definitions.
- Valid, stable credentials and a documented model identifier/version.
- A fresh result artifact and a checksummed protocol/dataset manifest.
- A tested timeout/retry policy and explicit handling of all failure states.
- Researcher approval of whether configurations are compared cumulatively or in a factorial/control-isolation design.

## 8. Status summary

### Ready

- Phase 2 agent graph and basic end-to-end pipeline.
- MCP stdio client/server path and existing integration tests.
- Three configuration files and fail-closed configuration selection.
- Normal benchmark dataset: 20 tasks, five categories, four tasks per category.
- Existing control tests for authentication, permission scoping, input validation, output validation, tool-call budget, CSV writing, and basic latency/quality recording.

### Needs correction

- Per-run experiment metadata, especially model ID, case/repetition/protocol identity, and timeout/error status.
- Logging-level verification/reconfiguration.
- New-result artifact and historical-data isolation policy.
- Research-grade quality adjudication and comparable latency protocol.
- Controlled runner for identical cases across all configurations.
- File-access claims and tests if the paper will make broader filesystem-security assertions.

### Not implemented

- Phase 3 adversarial dataset.
- Attack harness for the four requested attack types.
- Objective attack-success evaluators.
- Objective security-breach evaluators.
- ASR and SBR calculation.
- Explicit normal/adversarial case labeling in the current execution path.

### Cannot verify

- Stability and availability of the external Groq model/service during future experiments.
- Effective runtime logging level under every import/handler environment.
- General filesystem attack resistance beyond the implemented basename/path checks.
- Whether the current mock data is representative of real MCP retrieval/tool-output distributions.

## Bottom line

The repository is suitable for further **Phase 3 implementation**, but not for collecting or reporting valid Phase 3 security results yet. The three most important blockers are:

1. **No adversarial attack harness or versioned attack dataset** for the four required attack types.
2. **No explicit attack-success or breach evaluators**, so ASR and SBR cannot be measured defensibly.
3. **No reproducible experiment/result protocol** that records model identity, case/repetition metadata, timeout/failure states, and isolates new runs from historical `raw_results.csv`.
