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
EVALUATION_SYSTEM_PROMPT = """You are an Evaluation Agent scoring the quality of a task output.

Score from 0.0 to 1.0 using these guidelines:
- 1.0: Complete, accurate, directly answers the task
- 0.8: Mostly complete with minor gaps
- 0.6: Partially complete, addresses the main point
- 0.4: Minimal relevant content, significant gaps  
- 0.2: Very little relevant content
- 0.0: Empty, completely wrong, or execution failed

Be generous rather than strict — if the output makes a reasonable attempt at the task, score it 0.6 or above.
Respond with ONLY valid JSON: {"score": 0.7, "reason": "brief explanation"}
Do not include any text outside the JSON object."""


def fallback_score(execution_result: dict) -> tuple[float, str]:
    """
    Fallback scoring when LLM evaluation fails or gives suspiciously low scores.
    Uses heuristics based on output characteristics.
    
    Returns: (score, reason)
    """
    if not execution_result.get("execution_success", False):
        return 0.0, "Execution failed"
    
    result_text = execution_result.get("result", "")
    
    if not result_text or len(result_text.strip()) < 10:
        return 0.1, "Output too short"
    
    word_count = len(result_text.split())
    
    if word_count >= 50:
        return 0.7, f"Fallback: substantial output ({word_count} words)"
    elif word_count >= 20:
        return 0.5, f"Fallback: moderate output ({word_count} words)"
    else:
        return 0.3, f"Fallback: brief output ({word_count} words)"


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
        model="openai/gpt-oss-120b",
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
        
        # Apply fallback if LLM gives 0.0 for a successful execution with non-empty result
        if quality_score == 0.0 and execution_success and word_count >= 10:
            logger.warning(f"LLM gave score 0.0 for successful execution with {word_count} words, applying fallback")
            quality_score, reason = fallback_score(execution_result)
        
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
        # Use fallback heuristic
        quality_score, reason = fallback_score(execution_result)
        return {
            "task_completed": quality_score >= 0.5,
            "quality_score": quality_score,
            "completion_reason": f"Evaluation parsing failed, {reason}",
            "word_count": word_count,
            "evaluation_notes": f"Could not parse LLM evaluation: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Error in evaluation agent: {e}")
        # Use fallback heuristic
        quality_score, reason = fallback_score(execution_result)
        return {
            "task_completed": quality_score >= 0.5,
            "quality_score": quality_score,
            "completion_reason": f"Evaluation error, {reason}",
            "word_count": word_count,
            "evaluation_notes": f"Evaluation failed: {str(e)}"
        }
