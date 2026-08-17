"""
LangGraph Pipeline
Phase 2: Orchestrates the multi-agent system as a directed state graph

This module builds the LangGraph state graph connecting all 4 agents:
planner → research → execution → evaluation
"""

import logging
import uuid
from typing import TypedDict, Optional, Dict, Any
from langgraph.graph import StateGraph, END

from agents.planner_agent import planner_agent
from agents.research_agent import research_agent
from agents.execution_agent import execution_agent
from agents.evaluation_agent import evaluation_agent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """
    State schema for the multi-agent pipeline.
    
    Attributes:
        user_task: Original user task string
        security_config: Security configuration name (config_a, config_b, config_c)
        plan: Output from Planner Agent
        research_result: Output from Research Agent
        execution_result: Output from Execution Agent
        evaluation_result: Output from Evaluation Agent
        run_id: Unique identifier for this pipeline run
        errors: List of errors encountered during execution
        attack_injected: Whether an attack was injected (Phase 3, always False in Phase 2)
    """
    # Input
    user_task: str
    security_config: str
    
    # Agent outputs
    plan: Optional[Dict[str, Any]]
    research_result: Optional[Dict[str, Any]]
    execution_result: Optional[Dict[str, Any]]
    evaluation_result: Optional[Dict[str, Any]]
    
    # Metadata
    run_id: str
    errors: list[str]
    attack_injected: bool


def planner_node(state: AgentState) -> AgentState:
    """
    LangGraph node for the Planner Agent.
    
    Args:
        state: Current pipeline state
    
    Returns:
        Updated state with plan from Planner Agent
    """
    logger.info(f"[{state['run_id']}] Planner node executing")
    
    try:
        plan = planner_agent(state["user_task"], state["security_config"])
        
        if "error" in plan:
            logger.error(f"[{state['run_id']}] Planner failed: {plan['error']}")
            state["errors"].append(f"Planner: {plan['error']}")
            state["plan"] = plan
        else:
            state["plan"] = plan
            logger.info(f"[{state['run_id']}] Planner completed successfully")
    
    except Exception as e:
        error_msg = f"Planner node exception: {str(e)}"
        logger.error(f"[{state['run_id']}] {error_msg}")
        state["errors"].append(error_msg)
        state["plan"] = {"error": error_msg}
    
    return state


def research_node(state: AgentState) -> AgentState:
    """
    LangGraph node for the Research Agent.
    
    Args:
        state: Current pipeline state
    
    Returns:
        Updated state with research results from Research Agent
    """
    logger.info(f"[{state['run_id']}] Research node executing")
    
    # Skip research if planner failed
    if state["plan"] and "error" in state["plan"]:
        logger.warning(f"[{state['run_id']}] Skipping research due to planner error")
        state["research_result"] = {"error": "Skipped due to planner error"}
        return state
    
    try:
        research_result = research_agent(state["plan"], state["security_config"])
        
        if "error" in research_result:
            logger.error(f"[{state['run_id']}] Research failed: {research_result['error']}")
            state["errors"].append(f"Research: {research_result['error']}")
        
        state["research_result"] = research_result
        logger.info(f"[{state['run_id']}] Research completed")
    
    except Exception as e:
        error_msg = f"Research node exception: {str(e)}"
        logger.error(f"[{state['run_id']}] {error_msg}")
        state["errors"].append(error_msg)
        state["research_result"] = {"error": error_msg}
    
    return state


def execution_node(state: AgentState) -> AgentState:
    """
    LangGraph node for the Execution Agent.
    
    Args:
        state: Current pipeline state
    
    Returns:
        Updated state with execution result from Execution Agent
    """
    logger.info(f"[{state['run_id']}] Execution node executing")
    
    # Skip execution if research failed
    if state["research_result"] and "error" in state["research_result"]:
        logger.warning(f"[{state['run_id']}] Skipping execution due to research error")
        state["execution_result"] = {"error": "Skipped due to research error"}
        return state
    
    try:
        execution_result = execution_agent(state["plan"], state["research_result"], state["security_config"])
        
        if "error" in execution_result:
            logger.error(f"[{state['run_id']}] Execution failed: {execution_result['error']}")
            state["errors"].append(f"Execution: {execution_result['error']}")
        
        state["execution_result"] = execution_result
        logger.info(f"[{state['run_id']}] Execution completed")
    
    except Exception as e:
        error_msg = f"Execution node exception: {str(e)}"
        logger.error(f"[{state['run_id']}] {error_msg}")
        state["errors"].append(error_msg)
        state["execution_result"] = {"error": error_msg}
    
    return state


def evaluation_node(state: AgentState) -> AgentState:
    """
    LangGraph node for the Evaluation Agent.
    
    Args:
        state: Current pipeline state
    
    Returns:
        Updated state with evaluation result from Evaluation Agent
    """
    logger.info(f"[{state['run_id']}] Evaluation node executing")
    
    try:
        evaluation_result = evaluation_agent(state["user_task"], state["execution_result"])
        
        state["evaluation_result"] = evaluation_result
        logger.info(f"[{state['run_id']}] Evaluation completed. Score: {evaluation_result.get('quality_score', 0.0)}")
    
    except Exception as e:
        error_msg = f"Evaluation node exception: {str(e)}"
        logger.error(f"[{state['run_id']}] {error_msg}")
        state["errors"].append(error_msg)
        state["evaluation_result"] = {
            "task_completed": False,
            "quality_score": 0.0,
            "completion_reason": error_msg,
            "word_count": 0,
            "evaluation_notes": error_msg
        }
    
    return state


def create_graph() -> StateGraph:
    """
    Create the LangGraph state graph for the multi-agent pipeline.
    
    Returns:
        Compiled StateGraph ready for execution
    """
    # Create the state graph
    graph = StateGraph(AgentState)
    
    # Add nodes
    graph.add_node("planner", planner_node)
    graph.add_node("research", research_node)
    graph.add_node("execution", execution_node)
    graph.add_node("evaluation", evaluation_node)
    
    # Define the workflow: START → planner → research → execution → evaluation → END
    graph.set_entry_point("planner")
    graph.add_edge("planner", "research")
    graph.add_edge("research", "execution")
    graph.add_edge("execution", "evaluation")
    graph.add_edge("evaluation", END)
    
    # Compile the graph
    compiled_graph = graph.compile()
    
    logger.info("LangGraph pipeline created successfully")
    return compiled_graph


def run_pipeline(user_task: str, security_config: str = "config_a") -> Dict[str, Any]:
    """
    Run the full multi-agent pipeline for a given task.
    
    Args:
        user_task: The user task to process
        security_config: Security configuration name (config_a, config_b, config_c)
    
    Returns:
        Dictionary containing the final state with all agent outputs
    """
    # Generate unique run ID
    run_id = f"RUN_{uuid.uuid4().hex[:8].upper()}"
    
    logger.info(f"[{run_id}] Starting pipeline for task: {user_task[:50]}...")
    
    # Initialize state
    initial_state: AgentState = {
        "user_task": user_task,
        "security_config": security_config,
        "plan": None,
        "research_result": None,
        "execution_result": None,
        "evaluation_result": None,
        "run_id": run_id,
        "errors": [],
        "attack_injected": False  # Phase 2: always False
    }
    
    # Create and run the graph
    graph = create_graph()
    
    try:
        final_state = graph.invoke(initial_state)
        logger.info(f"[{run_id}] Pipeline completed successfully")
        return final_state
    
    except Exception as e:
        logger.error(f"[{run_id}] Pipeline failed with exception: {e}")
        initial_state["errors"].append(f"Pipeline exception: {str(e)}")
        return initial_state
