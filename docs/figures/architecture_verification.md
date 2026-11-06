# Implemented Architecture Verification

**Figure assets**

- [system_architecture.svg](./system_architecture.svg)
- [system_architecture.png](./system_architecture.png)
- [system_architecture.mmd](./system_architecture.mmd)

**Suggested caption:** Figure 1. Architecture of the implemented MCP-based
multi-agent system, illustrating agent orchestration, tool integration,
security controls, and evaluation logging.

## Source files inspected

- [pipeline/graph.py](../../pipeline/graph.py)
- [agents/planner_agent.py](../../agents/planner_agent.py)
- [agents/research_agent.py](../../agents/research_agent.py)
- [agents/execution_agent.py](../../agents/execution_agent.py)
- [agents/evaluation_agent.py](../../agents/evaluation_agent.py)
- [mcp_servers/file_read_server.py](../../mcp_servers/file_read_server.py)
- [mcp_servers/web_search_server.py](../../mcp_servers/web_search_server.py)
- [security/auth.py](../../security/auth.py)
- [security/logging_config.py](../../security/logging_config.py)
- [metrics/collector.py](../../metrics/collector.py)
- [configs/__init__.py](../../configs/__init__.py)
- [configs/no_security.yaml](../../configs/no_security.yaml)
- [configs/basic_security.yaml](../../configs/basic_security.yaml)
- [configs/hardened.yaml](../../configs/hardened.yaml)
- [main.py](../../main.py)
- [docs/configuration_matrix.md](../configuration_matrix.md)

## Verified control flow

`main.py` accepts a task and configuration name, then creates a
`MetricsCollector`, starts a run, calls `run_pipeline()`, and writes the final
state to the metrics CSV. `run_pipeline()` resolves the selected YAML
configuration, configures logging, and performs authentication when enabled.
Invalid configuration names fail before graph construction.

The compiled LangGraph has the following fixed edges:

`planner -> research -> execution -> evaluation -> END`

The planner creates a structured plan using Groq. The research agent selects
`read_file` when the query begins with `file:`; otherwise it selects
`web_search`. The execution agent synthesizes the retrieved text using Groq.
The evaluation agent scores the execution result using Groq, with a heuristic
fallback for unsuccessful or unparseable evaluation responses.

The graph still reaches later nodes after upstream errors, but the research and
execution nodes explicitly skip work when their upstream result contains an
error. The evaluation node handles failed execution and returns an incomplete
evaluation.

## MCP and tool connections

The Research Agent is the verified MCP client boundary. It uses the MCP
Python SDK (`ClientSession`, `StdioServerParameters`, and `stdio_client`) over
stdio. Each selected tool call starts the corresponding server script as a
Python subprocess, initializes an MCP session, sends one tool request, receives
the tool response, and returns the first text content item to the Research
Agent.

- `file_read_server.py` exposes `read_file` and reads from `data/`.
- `web_search_server.py` exposes `web_search` and returns predefined
  case-insensitive exact or partial mock results.

No direct import of either server module by the Research Agent was found.

## Security configuration and enforcement locations

| Configuration/control | Verified location and behavior |
|---|---|
| Configuration resolution | `configs.load_security_config()` maps exactly `config_a`, `config_b`, and `config_c` to the three YAML files. |
| Authentication | `pipeline.run_pipeline()` calls `security.auth.check_authentication()` before creating or invoking the graph. Config A is not evaluated; Config B/C require the configured expected secret and presented token. |
| Input validation | `planner_agent()` only when `input_validation` is enabled; Config C checks configured keywords and maximum input length. |
| Tool permission scoping | `research_agent()` immediately before the MCP invocation; it checks the selected Research tool against `allowed_tools.research`. |
| MCP call budget | `research_agent()` counts permitted attempted calls per run and denies a fourth call under Config C before calling the MCP client. |
| Output length validation | `research_agent()` after the MCP response; Config B uses 5000 characters and Config C uses 2000 characters. |
| Output content scanning | `execution_agent()` after Groq synthesis; configured `block_keywords` make this active for Config C, while Config B has no configured keywords and therefore uses length-only behavior. |
| Logging | `configure_logging()` maps basic/standard to INFO and verbose to DEBUG. Agent and pipeline loggers emit operational and security messages. |
| Metrics | `MetricsCollector.end_run()` derives run outcomes, latency, agent success, tool, and tri-state security events and appends one 20-column row to `results/raw_results.csv`. |

The diagram intentionally places controls beside the component where the
implementation enforces them. It does not imply that planner, execution, or
evaluation tool permissions are active; those YAML lists are not used as MCP
boundaries in the current code.

## Uncertain or unverified details

- The diagram shows Groq-backed agent calls because the agents instantiate
  `ChatGroq`; the diagram does not assert availability of credentials,
  network access, model quality, or service reliability.
- The diagram shows the output as the final state returned by `run_pipeline()`.
  The CLI prints a task-completion/quality/latency summary rather than a
  separate user-interface rendering of the generated result.
- The project documentation describes LangSmith tracing, but the inspected
  implementation does not contain an explicit tracing node or tracing edge;
  it is therefore not shown as an established architecture component.
- The `attacks/` package and adversarial dataset/evaluators are not implemented
  as an operational Phase 3 path. They are intentionally omitted from the
  architecture diagram.
- The diagram uses separate request and response arrows for MCP. The source
  code performs the request through `session.call_tool(...)`, receives the
  response content from the MCP session, and returns that text to the Research
  Agent.

## Differences from the initial conceptual architecture

The conceptual description identifies four agents and two tools, which is
consistent with the implementation. The verified implementation adds several
important constraints:

1. MCP access is not an abstract tool bus; it is a Research Agent client using
   stdio subprocess connections to two standalone MCP servers.
2. Authentication and configuration validation are pipeline-entry gates, not
   per-agent services.
3. Input validation is planner-local, tool permission and call-budget checks are
   research-local, output length checking is research-local, and content
   scanning is execution-local.
4. Evaluation is a terminal graph node and metrics logging is performed by the
   caller after `run_pipeline()` returns: `main.py` invokes
   `MetricsCollector.end_run()` with the final state.
5. Phase 3 attack execution is not represented because it is not an operational
   component in the current implementation.

## Diagram validation

The source, SVG, and PNG were generated together from the verified component
list above. The SVG is vector-based; the PNG is rendered at 300 DPI with a
wide academic-paper layout and monochrome styling. The non-operational Phase 3
attack harness is omitted from the main figure. No application code, security
configuration, test file, experimental data, or research paper was modified.

## Section 3.5 readiness

The revised figure is ready for insertion into Section 3.5. It represents the
implemented architecture rather than the planned Phase 3 experimental system.
Remaining implementation details are limited to the documented uncertainties:
external Groq availability and behavior, the CLI's summary-style presentation
of the returned state, undocumented runtime tracing integration, and the
absence of an operational attack harness or adversarial dataset.
