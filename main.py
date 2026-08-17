"""
MCP Security Research Framework
Entry point for running the multi-agent pipeline

Usage:
    python main.py                          # Run all 20 baseline tasks
    python main.py --task "your task here"  # Run a single task
    python main.py --config config_b        # Run with specific security config
    python main.py --summary                # Show results summary
"""

import argparse
import json
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv
from pipeline.graph import run_pipeline
from metrics.collector import MetricsCollector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


def run_single_task(task: str, security_config: str = "config_a") -> None:
    """
    Run a single task through the pipeline.
    
    Args:
        task: The user task to process
        security_config: Security configuration name
    """
    logger.info(f"Running single task with config: {security_config}")
    
    # Initialize metrics collector
    collector = MetricsCollector()
    
    # Start the run
    run_id = collector.start_run(task, security_config)
    
    # Run the pipeline
    state = run_pipeline(task, security_config)
    
    # Update state with the run_id from collector
    state["run_id"] = run_id
    
    # End the run (log to CSV)
    collector.end_run(run_id, state)
    
    # Print summary
    evaluation = state.get("evaluation_result", {})
    task_completed = evaluation.get("task_completed", False)
    quality_score = evaluation.get("quality_score", 0.0)
    
    # Calculate latency
    import time
    latency_ms = 0  # Will be calculated by collector
    
    print(f"[{run_id}] Task completed: {task_completed} | Quality: {quality_score:.2f} | Latency: {latency_ms}ms")


def run_baseline_tasks(security_config: str = "config_a") -> None:
    """
    Run all 20 baseline tasks from the benchmark dataset.
    
    Args:
        security_config: Security configuration name
    """
    logger.info(f"Running baseline tasks with config: {security_config}")
    
    # Load benchmark dataset
    dataset_path = Path(__file__).parent / "benchmark_dataset" / "normal_tasks.json"
    
    if not dataset_path.exists():
        logger.error(f"Benchmark dataset not found at: {dataset_path}")
        print("Error: benchmark_dataset/normal_tasks.json not found")
        sys.exit(1)
    
    with open(dataset_path, 'r', encoding='utf-8') as f:
        tasks = json.load(f)
    
    logger.info(f"Loaded {len(tasks)} tasks from benchmark dataset")
    
    # Initialize metrics collector
    collector = MetricsCollector()
    
    completed_count = 0
    total_quality = 0.0
    total_latency = 0
    
    # Run each task
    for i, task_data in enumerate(tasks, 1):
        task = task_data["task"]
        task_id = task_data["task_id"]
        
        logger.info(f"[{i}/{len(tasks)}] Running task {task_id}")
        
        # Start the run
        run_id = collector.start_run(task, security_config)
        
        # Run the pipeline
        state = run_pipeline(task, security_config)
        
        # Update state with the run_id from collector
        state["run_id"] = run_id
        
        # End the run (log to CSV)
        collector.end_run(run_id, state)
        
        # Print summary
        evaluation = state.get("evaluation_result", {})
        task_completed = evaluation.get("task_completed", False)
        quality_score = evaluation.get("quality_score", 0.0)
        
        # Get latency from collector (approximate)
        # In production, this would be returned from end_run
        latency_ms = 0  # Placeholder
        
        print(f"[{run_id}] Task completed: {task_completed} | Quality: {quality_score:.2f} | Latency: {latency_ms}ms")
        
        if task_completed:
            completed_count += 1
        total_quality += quality_score
        total_latency += latency_ms
    
    # Print baseline summary
    avg_quality = total_quality / len(tasks) if tasks else 0.0
    avg_latency = total_latency / len(tasks) if tasks else 0
    
    print(f"\n[BASELINE COMPLETE] {len(tasks)} tasks | {completed_count} completed | Avg quality: {avg_quality:.2f} | Avg latency: {avg_latency}ms")


def show_summary() -> None:
    """
    Show summary statistics from collected metrics.
    """
    logger.info("Generating metrics summary")
    
    collector = MetricsCollector()
    summary = collector.get_summary()
    
    if "error" in summary:
        print(f"Error: {summary['error']}")
        return
    
    print("\n=== Metrics Summary ===")
    print(f"Total runs: {summary['total_runs']}")
    print(f"Average quality score: {summary['avg_quality_score']}")
    print(f"Average latency: {summary['avg_latency_ms']}ms")
    print(f"Completed runs: {summary['completed_runs']}")
    print(f"Completion rate: {summary['completion_rate']:.1%}")
    
    if "by_security_config" in summary:
        print("\nRuns by security config:")
        for config, count in summary["by_security_config"].items():
            print(f"  {config}: {count}")


def main():
    """
    Main entry point for the MCP Security Research Framework.
    """
    parser = argparse.ArgumentParser(
        description="MCP Security Research Framework - Multi-Agent Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                          # Run all 20 baseline tasks
  python main.py --task "What is AI?"     # Run a single task
  python main.py --config config_b        # Run with specific security config
  python main.py --summary                # Show results summary
        """
    )
    
    parser.add_argument(
        "--task",
        type=str,
        help="Run a single task (string)"
    )
    
    parser.add_argument(
        "--config",
        type=str,
        default="config_a",
        choices=["config_a", "config_b", "config_c"],
        help="Security configuration (default: config_a)"
    )
    
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Show results summary from CSV"
    )
    
    args = parser.parse_args()
    
    # Check for required environment variables
    import os
    if not os.getenv("GROQ_API_KEY"):
        logger.warning("GROQ_API_KEY not set in environment variables")
        print("Warning: GROQ_API_KEY not set. Please set it in .env file.")
    
    if not os.getenv("LANGCHAIN_API_KEY"):
        logger.warning("LANGCHAIN_API_KEY not set in environment variables")
        print("Warning: LANGCHAIN_API_KEY not set. LangSmith tracing will not work.")
    
    # Execute based on arguments
    if args.summary:
        show_summary()
    elif args.task:
        run_single_task(args.task, args.config)
    else:
        # Default: run baseline tasks
        run_baseline_tasks(args.config)


if __name__ == "__main__":
    main()
