
from typing import Optional
from dataclasses import dataclass

@dataclass
class ExecutionResult:
    """
    Result of workflow execution with status tracking.

    Combines execution status and result information in a single class.
    """
    # Status tracking
    NOT_STARTED = "not_started"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"

    status: str  # One of the status constants above
    operations_completed: int
    total_operations: int
    error_message: Optional[str] = None
    failed_operation_index: Optional[int] = None

    @property
    def success(self) -> bool:
        """Check if execution was successful"""
        return self.status == self.COMPLETED

    @property
    def progress_percent(self) -> float:
        """Get progress as percentage"""
        if self.total_operations == 0:
            return 0.0
        return (self.operations_completed / self.total_operations) * 100

    @property
    def is_running(self) -> bool:
        """Check if execution is currently running"""
        return self.status == self.RUNNING

    @property
    def is_paused(self) -> bool:
        """Check if execution is paused"""
        return self.status == self.PAUSED

    @property
    def is_failed(self) -> bool:
        """Check if execution failed"""
        return self.status == self.FAILED
