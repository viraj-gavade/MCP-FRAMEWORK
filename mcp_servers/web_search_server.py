"""
Web Search MCP Server
Phase 2 — MCP Security Research Project

Runs as a standalone MCP server process using stdio transport.
Exposes one tool: web_search (mock data for research)

Start with:
    python mcp_servers/web_search_server.py
"""

import logging

from mcp.server.fastmcp import FastMCP


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# MOCK: Replace with real search API for production
# This is a research mock with predefined query -> result pairs
MOCK_SEARCH_RESULTS = {
    "prompt injection": (
        "Prompt injection is a security vulnerability where malicious users "
        "craft inputs that manipulate AI systems into bypassing safety measures "
        "or executing unintended commands. It affects AI systems by allowing "
        "attackers to override system prompts, extract sensitive information, "
        "or cause the model to produce harmful content."
    ),

    "LLM vulnerabilities": (
        "Large Language Model vulnerabilities include prompt injection, "
        "data poisoning, model inversion attacks, and adversarial examples. "
        "These vulnerabilities arise from the model's pattern-matching nature "
        "and can lead to information leaks, biased outputs, or security breaches."
    ),

    "adversarial attacks": (
        "Adversarial attacks on AI systems involve crafting inputs designed "
        "to cause model misbehavior. These include evasion attacks (modifying "
        "inputs to fool classifiers), poisoning attacks (corrupting training "
        "data), and extraction attacks (stealing model parameters)."
    ),

    "MCP architecture": (
        "Model Context Protocol (MCP) is a standardized protocol for connecting "
        "AI models to external tools and data sources. It defines a client-server "
        "architecture where MCP servers expose tools that LLMs can invoke through "
        "structured requests, enabling safe and extensible tool integration."
    ),

    "tool calling": (
        "Tool calling in AI systems refers to the ability of language models "
        "to invoke external functions or APIs to perform actions beyond text "
        "generation. MCP provides a standardized interface for tool calling, "
        "including schema definitions, parameter validation, and result formatting."
    ),

    "agent communication": (
        "Multi-agent communication involves coordinating multiple AI agents "
        "to collaborate on complex tasks. Agents can share information, delegate "
        "subtasks, and synchronize their actions through message passing, shared "
        "state, or orchestration frameworks like LangGraph."
    ),

    "LangGraph": (
        "LangGraph is a framework for building stateful, multi-actor applications "
        "with LLMs. It models agent workflows as directed graphs where nodes "
        "represent agent functions and edges represent state transitions, enabling "
        "complex multi-agent orchestration with built-in state management."
    ),

    "multi-agent systems": (
        "Multi-agent systems consist of multiple autonomous agents that interact "
        "to achieve individual or collective goals. In AI research, these systems "
        "enable task decomposition, parallel processing, and specialized agent "
        "roles for improved performance on complex problems."
    ),

    "Python best practices": (
        "Python best practices include using type hints, writing docstrings, "
        "following PEP 8 style guidelines, using virtual environments, writing "
        "tests with pytest, handling exceptions gracefully, and using context "
        "managers for resource management."
    ),

    "async programming": (
        "Async programming in Python uses asyncio to write concurrent code "
        "using async/await syntax. It's particularly useful for I/O-bound "
        "operations like network requests, file operations, and database queries, "
        "allowing efficient handling of many concurrent tasks."
    ),

    "testing in Python": (
        "Python testing frameworks like pytest and unittest enable automated "
        "verification of code correctness. Best practices include writing unit "
        "tests for individual functions, integration tests for component "
        "interactions, and using fixtures for test setup and teardown."
    ),

    "research methodology": (
        "Research methodology involves systematic approaches to investigating "
        "questions, including experimental design, data collection, statistical "
        "analysis, and reproducibility. Key principles include hypothesis "
        "formulation, controlled experiments, peer review, and ethical considerations."
    ),

    "academic writing": (
        "Academic writing requires clear structure, formal tone, proper citation, "
        "and logical argumentation. Key elements include abstract, introduction, "
        "literature review, methodology, results, discussion, and references "
        "sections, following discipline-specific formatting guidelines."
    ),

    "benchmarking": (
        "Benchmarking involves evaluating system performance against standardized "
        "metrics and baselines. In AI research, benchmarking includes measuring "
        "accuracy, latency, throughput, and resource usage across different "
        "configurations to enable fair comparisons and identify optimization "
        "opportunities."
    ),

    "AI security": (
        "AI security encompasses protecting AI systems from adversarial attacks, "
        "ensuring data privacy, preventing model misuse, and maintaining system "
        "integrity. Key concerns include robustness against perturbations, secure "
        "deployment, and alignment with safety guidelines."
    ),

    "MCP protocol": (
        "The Model Context Protocol defines a standardized way for AI models "
        "to interact with external tools. It specifies message formats, tool "
        "schemas, error handling, and transport mechanisms, enabling interoperability "
        "between different LLM applications and tool providers."
    ),

    "agent collaboration": (
        "Agent collaboration in multi-agent systems involves agents working "
        "together through communication, coordination, and negotiation. Effective "
        "collaboration requires clear role definitions, shared goals, and protocols "
        "for conflict resolution and decision making."
    ),

    "Python type hints": (
        "Type hints in Python (PEP 484) allow developers to specify expected "
        "types for function parameters and return values. They improve code "
        "readability, enable static type checking with tools like mypy, and "
        "support better IDE autocomplete and error detection."
    ),

    "LangGraph state management": (
        "LangGraph provides built-in state management through TypedDict schemas "
        "that define the data flowing between agents. State is updated at each "
        "node, supports persistence, and enables complex workflows with "
        "conditional routing and error handling."
    ),
}


mcp = FastMCP("web-search-server")


@mcp.tool()
def web_search(query: str) -> str:
    """
    Search for information using a query.
    Returns mock results for research purposes.
    """

    if not query:
        return "Error: query parameter is required"

    # Search for the query in mock results
    # Case-insensitive partial matching
    query_lower = query.lower().strip()

    # Exact match
    for key, value in MOCK_SEARCH_RESULTS.items():
        if query_lower == key.lower():
            logger.info(
                f"Mock search found exact match for: {query}"
            )

            return value

    # Partial match
    for key, value in MOCK_SEARCH_RESULTS.items():
        if (
            query_lower in key.lower()
            or key.lower() in query_lower
        ):
            logger.info(
                f"Mock search found partial match for: "
                f"{query} (matched: {key})"
            )

            return value

    # No match
    logger.warning(
        f"Mock search found no results for: {query}"
    )

    return (
        f"No mock search results found for query: '{query}'. "
        "MOCK: This is a research mock - replace with real "
        "search API for production."
    )


if __name__ == "__main__":
    mcp.run()