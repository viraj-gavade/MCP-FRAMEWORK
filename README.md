# MCP Security Research Framework

**Security and Reliability of MCP-Based Multi-Agent Systems: An Empirical Study of Vulnerabilities and Defense Mechanisms**

**Investigators:** Viraj Vinayak Gavade (PI), Tanmay Macchindra Jare (Co-I)

**Institution:** Mulund College of Commerce (Autonomous), affiliated to University of Mumbai

---

## Project Description

This research project builds a multi-agent AI system using LangGraph + Groq + MCP (Model Context Protocol), then runs adversarial attack experiments to benchmark how well different security configurations defend against prompt injection, tool poisoning, and unauthorized tool access. This is academic research — the system is designed to be clean, well-documented, and fully reproducible.

### Research Objectives

- Build a multi-agent system using LangGraph for orchestration
- Implement MCP (Model Context Protocol) servers for tool integration
- Test three security configurations (no security, basic security, hardened)
- Run baseline experiments with legitimate tasks
- Conduct adversarial attack experiments (Phase 3)
- Measure and analyze security effectiveness metrics

---

## Tech Stack

- **Python 3.10+**
- **LangGraph** — multi-agent orchestration as a directed state graph
- **LangChain + langchain-groq** — LLM integration
- **Groq API** — LLM inference (model: llama-3.1-8b-instant)
- **MCP Python SDK** — Model Context Protocol tool servers
- **LangSmith** — full tracing and observability of every run
- **python-dotenv** — environment variable management
- **PyYAML** — configuration file parsing

**NOT used:** OpenAI, Anthropic API directly, LangChain agents (using LangGraph only), any paid APIs beyond Groq free tier.

---

## Project Structure

```
mcp-security-framework/
│
├── agents/                        # Multi-agent implementations
│   ├── __init__.py
│   ├── planner_agent.py           # Interprets tasks and creates plans
│   ├── research_agent.py          # Retrieves information via MCP tools
│   ├── execution_agent.py         # Processes data and produces output
│   └── evaluation_agent.py        # Scores output quality
│
├── attacks/                       # Adversarial attack implementations (Phase 3)
│   └── __init__.py
│
├── configs/                       # Security configuration files
│   ├── __init__.py
│   ├── no_security.yaml           # Config A - No security measures
│   ├── basic_security.yaml        # Config B - Basic authentication + scoping
│   └── hardened.yaml              # Config C - Full security with validation
│
├── mcp_servers/                   # MCP tool server implementations
│   ├── __init__.py
│   ├── file_read_server.py        # MCP server for file reading
│   └── web_search_server.py       # MCP server for web search (mock)
│
├── metrics/                       # Metrics collection and analysis
│   ├── __init__.py
│   ├── collector.py              # Auto-logs runs to CSV
│   └── analyser.py                # Generates summary stats (Phase 4)
│
├── benchmark_dataset/            # Test task datasets
│   ├── normal_tasks.json          # 20 legitimate test tasks
│   └── attack_cases.json          # Attack scenarios (Phase 3)
│
├── results/                       # Experiment results
│   └── raw_results.csv            # Auto-generated metrics log
│
├── pipeline/                      # LangGraph orchestration
│   ├── __init__.py
│   └── graph.py                   # State graph wiring all 4 agents
│
├── tests/                         # Test suite
│   ├── test_groq_connection.py    # Groq API connectivity tests
│   ├── test_mcp_servers.py        # MCP server functionality tests
│   └── test_happy_path.py         # End-to-end happy path tests
│
├── data/                          # Data folder for file_read_server
│
├── .env                           # Environment variables (not committed)
├── .gitignore
├── requirements.txt
├── README.md
└── main.py                        # Entry point for running the pipeline
```

---

## Setup Instructions

### Prerequisites

- Python 3.10 or higher
- Groq API key (free tier available at https://console.groq.com/)
- LangSmith API key (optional, for tracing)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd mcp-security-framework
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   
   # On Windows:
   venv\Scripts\activate
   
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   
   Create a `.env` file in the project root:
   ```env
   GROQ_API_KEY=your_groq_key_here
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_API_KEY=your_langsmith_key_here
   LANGCHAIN_PROJECT=mcp-security-research
   ```
   
   Replace the placeholder values with your actual API keys.

5. **Create data folder**
   ```bash
   mkdir data
   ```

---

## Running Baseline Experiments

### Run all 20 baseline tasks (default: config_a)
```bash
python main.py
```

### Run a single task
```bash
python main.py --task "What is prompt injection?"
```

### Run with specific security configuration
```bash
python main.py --config config_b
```

Available configurations:
- `config_a` — No security (baseline)
- `config_b` — Basic security (authentication + tool scoping)
- `config_c` — Hardened (full security with validation)

### Show results summary
```bash
python main.py --summary
```

---

## Interpreting Results

### CSV Output Format

Results are automatically logged to `results/raw_results.csv` with the following columns:

| Column | Description |
|--------|-------------|
| run_id | Unique identifier for each run |
| timestamp | ISO timestamp of the run |
| user_task | The task that was processed |
| security_config | Security configuration used |
| attack_type | Type of attack (Phase 3) |
| attack_injected | Whether an attack was injected |
| attack_success | Whether the attack succeeded |
| breach_occurred | Whether a security breach occurred |
| task_completed | Whether the task was completed successfully |
| quality_score | Quality score (0.0 to 1.0) |
| latency_ms | Total execution time in milliseconds |
| planner_success | Whether planner agent succeeded |
| research_success | Whether research agent succeeded |
| execution_success | Whether execution agent succeeded |
| tool_called | Which tool was called |
| notes | Additional notes or errors |

### Quality Score Interpretation

- **0.0** — Completely wrong or empty
- **0.5** — Partially correct or incomplete
- **1.0** — Fully correct and complete

### Security Configurations

#### Config A (no_security.yaml)
- No authentication
- No tool permission scoping
- No input/output validation
- Basic logging
- All tools allowed for all agents

#### Config B (basic_security.yaml)
- Authentication enabled
- Tool permission scoping enabled
- No input/output validation
- Standard logging
- Restricted tool access per agent

#### Config C (hardened.yaml)
- Authentication enabled
- Tool permission scoping enabled
- Input validation (keyword blocking, length limits)
- Output validation (content scanning, length limits)
- Verbose logging
- Restricted tool access per agent
- Max tool calls per run: 3
- Max input length: 500 characters
- Blocked keywords: ["ignore previous", "disregard", "override", "forget instructions", "new instruction"]

---

## Running Tests

### Run all tests
```bash
pytest tests/
```

### Run specific test file
```bash
pytest tests/test_groq_connection.py
pytest tests/test_mcp_servers.py
pytest tests/test_happy_path.py
```

### Run tests manually
```bash
python tests/test_groq_connection.py
python tests/test_mcp_servers.py
python tests/test_happy_path.py
```

---

## Benchmark Dataset

The benchmark dataset (`benchmark_dataset/normal_tasks.json`) contains 20 legitimate research tasks across 5 topic categories:

- **ai_security** (4 tasks) — Prompt injection, LLM vulnerabilities, adversarial attacks
- **mcp_protocol** (4 tasks) — MCP architecture, tool calling, agent communication
- **multi_agent** (4 tasks) — Agent collaboration, LangGraph, multi-agent systems
- **python_development** (4 tasks) — Python best practices, async programming, testing
- **general_research** (4 tasks) — Research methodology, academic writing, benchmarking

Each task includes:
- `task_id` — Unique identifier
- `task` — The task description
- `expected_output_type` — Expected output format (summary, answer, list)
- `topic_category` — Topic category
- `expected_keywords` — Expected keywords in the result

---

## MCP Servers

### file_read_server.py

Exposes a `read_file` tool that reads files from the local `data/` folder.

**Usage:**
```bash
python mcp_servers/file_read_server.py
```

**Tool parameters:**
- `filename` (string) — Name of the file to read

### web_search_server.py

Exposes a `web_search` tool that returns mock search results for research purposes.

**Usage:**
```bash
python mcp_servers/web_search_server.py
```

**Tool parameters:**
- `query` (string) — Search query

**Note:** This is a research mock with 20 predefined query-result pairs. Replace with a real search API for production.

---

## Multi-Agent Pipeline

The pipeline uses LangGraph to orchestrate 4 agents in a directed state graph:

```
START → planner_node → research_node → execution_node → evaluation_node → END
```

### Agent Roles

1. **Planner Agent** — Interprets user task and creates a structured plan
2. **Research Agent** — Retrieves information using MCP tools
3. **Execution Agent** — Processes retrieved data and produces final output
4. **Evaluation Agent** — Scores the quality and accuracy of the output

### State Schema

```python
class AgentState(TypedDict):
    user_task: str
    security_config: str
    plan: Optional[dict]
    research_result: Optional[dict]
    execution_result: Optional[dict]
    evaluation_result: Optional[dict]
    run_id: str
    errors: list[str]
    attack_injected: bool
```

---

## Paper

[Paper link — to be added after submission]

---

## License

MIT License

---

## Acknowledgments

This research project is conducted at Mulund College of Commerce (Autonomous), affiliated to University of Mumbai, under the guidance of the Principal and Department of Computer Science.

---

## Contact

**Principal Investigator:** Viraj Vinayak Gavade  
**Co-Investigator:** Tanmay Macchindra Jare

---

## Phase Status

- ✅ **Phase 1** — Project setup and requirements
- ✅ **Phase 2** — Baseline multi-agent system (current)
- ⏳ **Phase 3** — Adversarial attack implementation
- ⏳ **Phase 4** — Metrics analysis and reporting
