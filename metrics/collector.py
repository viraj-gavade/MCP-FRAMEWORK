"""
Metrics Collector
Phase 2: Auto-logs every pipeline run to CSV for analysis

This module provides the MetricsCollector class that automatically logs
every pipeline run to results/raw_results.csv with structured metrics.
"""

import csv
import logging
import random
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
    - Creating the CSV file with standardized 20-column headers
    - Preserving and migrating legacy CSV files without fabricating data
    - High-resolution elapsed-time measurement using time.perf_counter()
    - Logging structured security events directly from execution points
    - Preserving unmeasured attack and breach metrics until Phase 3
    """
    
    HEADERS = [
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
        "auth_success",
        "permission_denied",
        "input_validation_failed",
        "output_validation_failed",
        "notes"
    ]
    
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
        
        # Dictionary to track start times using high-resolution monotonic clock
        self._run_start_times: Dict[str, float] = {}
    
    def _ensure_csv_exists(self) -> None:
        """
        Create the CSV file with headers if it doesn't exist,
        or migrate legacy headers while preserving all historical observations.
        """
        if not self.csv_path.exists():
            self.csv_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(self.HEADERS)
                logger.info(f"Created metrics CSV at: {self.csv_path}")
            except Exception as e:
                logger.error(f"Failed to create CSV file: {e}")
            return
        
        # Read existing file to inspect header and schema
        try:
            with open(self.csv_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                rows = list(reader)
        except Exception as e:
            logger.error(f"Failed to read existing CSV file: {e}")
            return
        
        if not rows:
            # File is empty, write standardized header
            try:
                with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(self.HEADERS)
            except Exception as e:
                logger.error(f"Failed to initialize header in empty CSV file: {e}")
            return
        
        existing_header = rows[0]
        # Check if header needs migration (e.g. legacy 16 columns)
        if existing_header != self.HEADERS:
            logger.info(f"Migrating CSV header at {self.csv_path} to standardized 20-column schema")
            migrated_rows = []
            for row in rows[1:]:
                if not row or not any(field.strip() for field in row):
                    continue
                if len(row) == 16:
                    # Legacy 16 columns: 15 metrics + notes. Pad 4 security columns before notes.
                    migrated_row = row[:15] + ["", "", "", ""] + [row[15]]
                elif len(row) == len(self.HEADERS):
                    # Already 20 columns
                    migrated_row = row
                elif len(row) < len(self.HEADERS):
                    # Pad missing columns with empty string
                    migrated_row = row + [""] * (len(self.HEADERS) - len(row))
                else:
                    # Truncate surplus columns
                    migrated_row = row[:len(self.HEADERS)]
                migrated_rows.append(migrated_row)
            
            try:
                with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(self.HEADERS)
                    writer.writerows(migrated_rows)
                logger.info(f"Successfully migrated {len(migrated_rows)} historical rows to 20-column schema")
            except Exception as e:
                logger.error(f"Failed to write migrated CSV file: {e}")
    
    def start_run(self, user_task: str, security_config: str) -> str:
        """
        Start tracking a new pipeline run.
        
        Args:
            user_task: The user task being processed
            security_config: Security configuration name
        
        Returns:
            Unique run ID for this run
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_suffix = f"{random.randint(1000, 9999)}"
        run_id = f"RUN_{timestamp}_{random_suffix}"
        
        # Record start time using high-resolution monotonic clock
        self._run_start_times[run_id] = time.perf_counter()
        
        logger.info(f"Started tracking run: {run_id}")
        return run_id
    
    def end_run(self, run_id: str, state: Optional[AgentState] = None) -> int:
        """
        Log a completed pipeline run to the CSV.
        
        Args:
            run_id: Unique run ID from start_run() or pipeline state
            state: Final state from the pipeline
        
        Returns:
            Latency in milliseconds
        """
        # Calculate latency using high-resolution monotonic clock
        if run_id in self._run_start_times:
            start_time = self._run_start_times[run_id]
            latency_ms = max(0, int(round((time.perf_counter() - start_time) * 1000)))
        elif state and state.get("latency_ms") is not None:
            latency_ms = max(0, int(state["latency_ms"]))
        else:
            latency_ms = 0
        
        # Extract metrics safely from state
        state_dict: Dict[str, Any] = state or {}
        evaluation_result = state_dict.get("evaluation_result") or {}
        plan = state_dict.get("plan") or {}
        research_result = state_dict.get("research_result") or {}
        execution_result = state_dict.get("execution_result") or {}
        sec_events = state_dict.get("security_events") or {}
        
        # Determine success flags
        planner_success = bool(plan and "error" not in plan)
        research_success = bool(research_result and research_result.get("retrieval_success", False))
        execution_success = bool(execution_result and execution_result.get("execution_success", False))
        
        # Get tool called
        tool_called = research_result.get("tool_called", "none") if research_result else "none"
        
        # Determine security event flags directly from structured representations (tri-state: True, False, or None)
        auth_success = sec_events.get("auth_success")
        permission_denied = sec_events.get("permission_denied")
        input_validation_failed = sec_events.get("input_validation_failed")
        output_validation_failed = sec_events.get("output_validation_failed")
        
        # Legacy fallback ONLY if security_events dictionary was not present at all
        if not sec_events and state_dict:
            if "Authentication failed" in str(plan.get("error", "")):
                auth_success = False
            if "Tool not permitted" in str(research_result.get("error", "")):
                permission_denied = True
            if "Input blocked" in str(plan.get("error", "")) or "Input blocked" in str(state_dict.get("errors", [])):
                input_validation_failed = True
            if "TRUNCATED" in str(research_result.get("raw_result", "")) or "OUTPUT BLOCKED" in str(execution_result.get("result", "")):
                output_validation_failed = True
        
        # Attack outcomes: unmeasured in Phase 2 baseline
        attack_type = state_dict.get("attack_type", "none")
        attack_injected = state_dict.get("attack_injected", False)
        attack_success = state_dict.get("attack_success", None)
        breach_occurred = state_dict.get("breach_occurred", None)
        
        # Task completion and quality score
        task_completed = evaluation_result.get("task_completed", False)
        quality_score = evaluation_result.get("quality_score", 0.0)
        
        # Build row data matching HEADERS (serialize None as empty string "")
        row = [
            run_id,
            datetime.now().isoformat(),
            str(state_dict.get("user_task", ""))[:100],
            str(state_dict.get("security_config", "config_a")),
            str(attack_type),
            str(attack_injected),
            str(attack_success) if attack_success is not None else "",
            str(breach_occurred) if breach_occurred is not None else "",
            str(task_completed),
            str(quality_score),
            str(latency_ms),
            str(planner_success),
            str(research_success),
            str(execution_success),
            str(tool_called),
            str(auth_success) if auth_success is not None else "",
            str(permission_denied) if permission_denied is not None else "",
            str(input_validation_failed) if input_validation_failed is not None else "",
            str(output_validation_failed) if output_validation_failed is not None else "",
            "; ".join(str(e) for e in state_dict.get("errors", []))[:200]
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
        
        return latency_ms
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Generate basic statistics from the collected metrics.
        
        Returns:
            Dictionary with summary statistics
        """
        if not self.csv_path.exists():
            return {"error": "CSV file does not exist"}
        
        try:
            with open(self.csv_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            if not rows:
                return {"total_runs": 0}
            
            total_runs = len(rows)
            
            quality_scores = []
            latencies = []
            completed = 0
            by_config: Dict[str, int] = {}
            
            for row in rows:
                # Quality score
                qs = row.get("quality_score")
                if qs not in (None, ""):
                    try:
                        quality_scores.append(float(qs))
                    except ValueError:
                        pass
                
                # Latency
                lat = row.get("latency_ms")
                if lat not in (None, ""):
                    try:
                        latencies.append(int(round(float(lat))))
                    except ValueError:
                        pass
                
                # Task completion
                tc = str(row.get("task_completed", "")).strip().lower()
                if tc == "true":
                    completed += 1
                
                # Configuration count
                config = row.get("security_config", "unknown") or "unknown"
                by_config[config] = by_config.get(config, 0) + 1
            
            avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
            avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
            
            # Security events summary
            auth_success_count = sum(1 for r in rows if str(r.get("auth_success", "")).strip().lower() == "true")
            permission_denied_count = sum(1 for r in rows if str(r.get("permission_denied", "")).strip().lower() == "true")
            input_val_failed_count = sum(1 for r in rows if str(r.get("input_validation_failed", "")).strip().lower() == "true")
            output_val_failed_count = sum(1 for r in rows if str(r.get("output_validation_failed", "")).strip().lower() == "true")
            
            # Attack outcomes
            attack_injected_count = sum(1 for r in rows if str(r.get("attack_injected", "")).strip().lower() == "true")
            
            return {
                "total_runs": total_runs,
                "avg_quality_score": round(avg_quality, 3),
                "avg_latency_ms": round(avg_latency, 2),
                "completed_runs": completed,
                "completion_rate": round(completed / total_runs, 3) if total_runs > 0 else 0.0,
                "by_security_config": by_config,
                "security_events": {
                    "auth_success_count": auth_success_count,
                    "permission_denied_count": permission_denied_count,
                    "input_validation_failed_count": input_val_failed_count,
                    "output_validation_failed_count": output_val_failed_count
                },
                "attack_metrics": {
                    "attacks_injected_count": attack_injected_count,
                    "attack_success_rate": None if attack_injected_count == 0 else "measured_in_phase_3",
                    "status": "Phase 2 baseline - attacks not injected" if attack_injected_count == 0 else "Phase 3 active"
                }
            }
        
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return {"error": str(e)}
