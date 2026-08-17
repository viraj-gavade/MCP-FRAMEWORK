"""
Metrics Collector
Phase 2: Auto-logs every pipeline run to CSV for analysis

This module provides the MetricsCollector class that automatically logs
every pipeline run to results/raw_results.csv with structured metrics.
"""

import csv
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from pipeline.graph import AgentState

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Collects and logs metrics from pipeline runs to CSV.
    
    This class handles:
    - Creating the CSV file with headers if it doesn't exist
    - Appending one row per pipeline run
    - Generating unique run IDs
    - Calculating latency metrics
    - Handling file write errors gracefully
    """
    
    def __init__(self, csv_path: Optional[str] = None):
        """
        Initialize the MetricsCollector.
        
        Args:
            csv_path: Path to the CSV file. Defaults to results/raw_results.csv
        """
        if csv_path is None:
            csv_path = str(Path(__file__).parent.parent / "results" / "raw_results.csv")
        
        self.csv_path = Path(csv_path)
        self._ensure_csv_exists()
        
        # Dictionary to track start times for runs
        self._run_start_times: Dict[str, float] = {}
    
    def _ensure_csv_exists(self) -> None:
        """
        Create the CSV file with headers if it doesn't exist.
        """
        if not self.csv_path.exists():
            self.csv_path.parent.mkdir(parents=True, exist_ok=True)
            
            headers = [
                "run_id",
                "timestamp",
                "user_task",
                "security_config",
                "attack_type",
                "attack_injected",
                "attack_success",
                "breach_occurred",
                "task_completed",
                "quality_score",
                "latency_ms",
                "planner_success",
                "research_success",
                "execution_success",
                "tool_called",
                "notes"
            ]
            
            try:
                with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(headers)
                logger.info(f"Created metrics CSV at: {self.csv_path}")
            except Exception as e:
                logger.error(f"Failed to create CSV file: {e}")
    
    def start_run(self, user_task: str, security_config: str) -> str:
        """
        Start tracking a new pipeline run.
        
        Args:
            user_task: The user task being processed
            security_config: Security configuration name
        
        Returns:
            Unique run ID for this run
        """
        # Generate run ID: RUN_YYYYMMDD_HHMMSS_XXXX
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        import random
        random_suffix = f"{random.randint(1000, 9999)}"
        run_id = f"RUN_{timestamp}_{random_suffix}"
        
        # Record start time
        self._run_start_times[run_id] = time.time()
        
        logger.info(f"Started tracking run: {run_id}")
        return run_id
    
    def end_run(self, run_id: str, state: AgentState) -> None:
        """
        Log a completed pipeline run to the CSV.
        
        Args:
            run_id: Unique run ID from start_run()
            state: Final state from the pipeline
        """
        # Calculate latency
        start_time = self._run_start_times.get(run_id, time.time())
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Extract metrics from state
        evaluation_result = state.get("evaluation_result", {})
        plan = state.get("plan", {})
        research_result = state.get("research_result", {})
        execution_result = state.get("execution_result", {})
        
        # Determine success flags
        planner_success = "error" not in plan
        research_success = research_result.get("retrieval_success", False) if research_result else False
        execution_success = execution_result.get("execution_success", False) if execution_result else False
        
        # Get tool called
        tool_called = research_result.get("tool_called", "none") if research_result else "none"
        
        # Phase 2: no attacks
        attack_type = "none"
        attack_injected = False
        attack_success = False
        breach_occurred = False
        
        # Build row data
        row = [
            run_id,
            datetime.now().isoformat(),
            state.get("user_task", "")[:100],  # Truncate long tasks
            state.get("security_config", "config_a"),
            attack_type,
            str(attack_injected),
            str(attack_success),
            str(breach_occurred),
            str(evaluation_result.get("task_completed", False)),
            str(evaluation_result.get("quality_score", 0.0)),
            str(latency_ms),
            str(planner_success),
            str(research_success),
            str(execution_success),
            tool_called,
            "; ".join(state.get("errors", []))[:200]  # Truncate error notes
        ]
        
        # Write to CSV
        try:
            with open(self.csv_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(row)
            logger.info(f"Logged run {run_id} to CSV. Latency: {latency_ms}ms")
        except Exception as e:
            logger.error(f"Failed to write to CSV: {e}")
        
        # Clean up start time
        if run_id in self._run_start_times:
            del self._run_start_times[run_id]
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Generate basic statistics from the collected metrics.
        
        Returns:
            Dictionary with summary statistics
        """
        if not self.csv_path.exists():
            return {"error": "CSV file does not exist"}
        
        try:
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            if not rows:
                return {"total_runs": 0}
            
            total_runs = len(rows)
            
            # Calculate averages
            quality_scores = [float(row.get("quality_score", 0)) for row in rows if row.get("quality_score")]
            latencies = [int(row.get("latency_ms", 0)) for row in rows if row.get("latency_ms")]
            
            avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
            avg_latency = sum(latencies) / len(latencies) if latencies else 0
            
            # Count completions
            completed = sum(1 for row in rows if row.get("task_completed") == "True")
            
            # Count by security config
            by_config = {}
            for row in rows:
                config = row.get("security_config", "unknown")
                by_config[config] = by_config.get(config, 0) + 1
            
            return {
                "total_runs": total_runs,
                "avg_quality_score": round(avg_quality, 3),
                "avg_latency_ms": round(avg_latency, 2),
                "completed_runs": completed,
                "completion_rate": round(completed / total_runs, 3) if total_runs > 0 else 0.0,
                "by_security_config": by_config
            }
        
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return {"error": str(e)}
