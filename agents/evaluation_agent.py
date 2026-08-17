"""
Evaluation Agent
Phase 2: Scores the quality and accuracy of the final output

This agent receives the original task and execution result, then scores
the quality from 0.0 to 1.0 based on completeness and correctness.
"""

import json
import logging
from typing import Dict, Any
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# System prompt for LLM scoring
EVALUATION_SYSTEM_PROMPT = """You are an Evaluation Agent. Score the quality of this task output from 0.0 to 1.0.
0.0 = completely wrong or empty
0.5 = partially correct or incomplete
1.0 = fully correct and complete
Respond with ONLY a JSON object: {"score": 0.0, "reason": "brief explanation"}"""


def evaluation_agent(original_task: str, execution_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate the quality and accuracy of the execution result.
    
    Args:
        original_task: The original user task string
        execution_result: Dictionary from Execution Agent with result and execution_success
    
    Returns:
        Dictionary containing:
        - task_completed: bool
        - quality_score: float (0.0 to 1.0)
        - completion_reason: str
        - word_count: int
        - evaluation_notes: str
    """
    logger.info("Evaluation Agent scoring execution result")
    
    execution_success = execution_result.get("execution_success", False)
    result = execution_result.get("result", "")
    
    # If execution failed, mark as not completed with score 0.0
    if not execution_success:
        logger.warning("Execution failed, marking task as incomplete")
        return {
            "task_completed": False,
            "quality_score": 0.0,
            "completion_reason": execution_result.get("error", "Execution failed"),
            "word_count": 0,
            "evaluation_notes": "Task could not be completed due to execution failure"
        }
    
    # If result is empty or under 10 words, mark as incomplete with low score
    word_count = len(result.split())
    if not result or word_count < 10:
        logger.warning(f"Result too short ({word_count} words), marking as incomplete")
        return {
            "task_completed": False,
            "quality_score": 0.1,
            "completion_reason": "Result too short or empty",
            "word_count": word_count,
            "evaluation_notes": "Output was insufficient to complete the task"
        }
    
    # Use LLM to score quality
    llm = ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0.1
    )
    
    messages = [
        SystemMessage(content=EVALUATION_SYSTEM_PROMPT),
        HumanMessage(content=f"""Original Task: {original_task}

Execution Result:
{result}

Score the quality of this output from 0.0 to 1.0 based on:
- How well it addresses the original task
- Completeness of the information
- Accuracy and relevance

Respond with ONLY a JSON object: {{"score": 0.0, "reason": "brief explanation"}}""")
    ]
    
    try:
        # Call LLM
        response = llm.invoke(messages)
        response_text = response.content.strip()
        
        # Parse JSON response
        if response_text.startswith("```"):
            response_text = response_text.strip("`").strip()
            if response_text.startswith("json"):
                response_text = response_text[4:].strip()
        
        score_data = json.loads(response_text)
        quality_score = float(score_data.get("score", 0.5))
        reason = score_data.get("reason", "No reason provided")
        
        # Clamp score to valid range
        quality_score = max(0.0, min(1.0, quality_score))
        
        # Determine if task was completed based on score
        task_completed = quality_score >= 0.5
        
        logger.info(f"Evaluation complete. Score: {quality_score}, Task completed: {task_completed}")
        
        return {
            "task_completed": task_completed,
            "quality_score": quality_score,
            "completion_reason": reason,
            "word_count": word_count,
            "evaluation_notes": f"LLM evaluation: {reason}"
        }
    
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM evaluation response: {e}")
        # Fallback to basic heuristic
        quality_score = 0.5 if word_count >= 10 else 0.1
        return {
            "task_completed": quality_score >= 0.5,
            "quality_score": quality_score,
            "completion_reason": "Evaluation parsing failed, used fallback heuristic",
            "word_count": word_count,
            "evaluation_notes": f"Could not parse LLM evaluation: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Error in evaluation agent: {e}")
        return {
            "task_completed": False,
            "quality_score": 0.0,
            "completion_reason": f"Evaluation error: {str(e)}",
            "word_count": word_count,
            "evaluation_notes": f"Evaluation failed: {str(e)}"
        }
