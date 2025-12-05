
import os
from datetime import datetime
from typing import Optional
from .operation import Operation


class OperationLogger:
    """
    Logger for recording operation execution results to a session-based log file.

    Creates one log file per application session with format:
    operation_status_YYYY-MM-DD_HH-MM-SS.txt
    """

    def __init__(self, log_dir: str = "logs"):
        """
        Initialize the operation logger.

        Parameters
        ----------
        log_dir : str
            Directory to store log files (default: "logs")
        """
        self.log_dir = log_dir

        # Create logs directory if it doesn't exist
        os.makedirs(self.log_dir, exist_ok=True)

        # Create log file with timestamp
        date_str = datetime.now().strftime("%Y-%m-%d")
        self.log_file_path = os.path.join(self.log_dir, f"operation_status_{date_str}.txt")

        # Write header to log file
        self._write_header_if_new()

    def _write_header_if_new(self):
        """Write header only if this is a new file"""
        # Check if file already exists
        if os.path.exists(self.log_file_path):
            # File exists - append session start marker
            with open(self.log_file_path, 'a') as f:
                f.write("\n" + "=" * 100 + "\n")
                f.write(f"NEW SESSION - Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 100 + "\n\n")
        else:
            # New file - write full header
            with open(self.log_file_path, 'w') as f:
                f.write("=" * 100 + "\n")
                f.write(f"OPERATION LOG - {datetime.now().strftime('%Y-%m-%d')}\n")
                f.write("=" * 100 + "\n\n")

    def _format_parameters(self, params: dict) -> str:
        """
        Format operation parameters for logging.

        Parameters
        ----------
        params : dict
            Operation parameters

        Returns
        -------
        str
            Formatted parameter string
        """
        # Format parameters as key=value pairs
        param_strs = []
        for key, value in params.items():
            # Handle list/tuple values (like positions)
            if isinstance(value, (list, tuple)):
                if len(value) > 3:
                    # Shorten long lists
                    value_str = f"[{len(value)} items]"
                else:
                    value_str = str(value)
            else:
                value_str = str(value)
            param_strs.append(f"{key}={value_str}")

        return ", ".join(param_strs)

    def log_success(self, mode: str, operation: Operation, workflow_name: Optional[str] = None):
        """
        Log a successful operation execution.

        Parameters
        ----------
        mode : str
            Execution mode ("direct" or "builder")
        operation : Operation
            The operation that was executed
        workflow_name : str, optional
            Name of the workflow (for builder mode)
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        op_type = operation.operation_type.value
        params = self._format_parameters(operation.parameters)

        # Build log entry
        if workflow_name:
            log_entry = f"{timestamp} | {mode.upper()} | SUCCESS | {op_type} | Workflow: '{workflow_name}' | {params}\n"
        else:
            log_entry = f"{timestamp} | {mode.upper()} | SUCCESS | {op_type} | {params}\n"

        # Write to file
        with open(self.log_file_path, 'a') as f:
            f.write(log_entry)

    def log_failure(self, mode: str, operation: Operation, error_message: str, workflow_name: Optional[str] = None):
        """
        Log a failed operation execution.

        Parameters
        ----------
        mode : str
            Execution mode ("direct" or "builder")
        operation : Operation
            The operation that failed
        error_message : str
            Error message from the exception
        workflow_name : str, optional
            Name of the workflow (for builder mode)
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        op_type = operation.operation_type.value
        params = self._format_parameters(operation.parameters)

        # Build log entry
        if workflow_name:
            log_entry = (f"{timestamp} | {mode.upper()} | FAILED | {op_type} | "
                         f"Workflow: '{workflow_name}' | {params} | Error: {error_message}\n")
        else:
            log_entry = f"{timestamp} | {mode.upper()} | FAILED | {op_type} | {params} | Error: {error_message}\n"

        # Write to file
        with open(self.log_file_path, 'a') as f:
            f.write(log_entry)

    def log_workflow_start(self, workflow_name: str, num_operations: int):
        """
        Log the start of workflow execution.

        Parameters
        ----------
        workflow_name : str
            Name of the workflow
        num_operations : int
            Number of operations in the workflow
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"\n{timestamp} | BUILDER | WORKFLOW_START | '{workflow_name}' | {num_operations} operations\n"

        with open(self.log_file_path, 'a') as f:
            f.write(log_entry)

    def log_workflow_complete(self, workflow_name: str, num_completed: int, total_operations: int):
        """
        Log successful workflow completion.

        Parameters
        ----------
        workflow_name : str
            Name of the workflow
        num_completed : int
            Number of operations completed
        total_operations : int
            Total number of operations in workflow
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = (f"{timestamp} | BUILDER | WORKFLOW_COMPLETE | '{workflow_name}' | "
                     f"Completed {num_completed}/{total_operations} operations\n\n")

        with open(self.log_file_path, 'a') as f:
            f.write(log_entry)

    def log_workflow_failed(self, workflow_name: str, failed_at: int, total_operations: int, error_message: str):
        """
        Log workflow failure.

        Parameters
        ----------
        workflow_name : str
            Name of the workflow
        failed_at : int
            Index of operation that failed (0-based)
        total_operations : int
            Total number of operations in workflow
        error_message : str
            Error message from the exception
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = (f"{timestamp} | BUILDER | WORKFLOW_FAILED | '{workflow_name}' | "
                     f"Failed at operation {failed_at + 1}/{total_operations} | Error: {error_message}\n\n")

        with open(self.log_file_path, 'a') as f:
            f.write(log_entry)

    def log_validation(self, mode: str, success: bool, details: str):
        """
        Log validation results.

        Parameters
        ----------
        mode : str
            Validation mode ("direct" or "builder")
        success : bool
            Whether validation succeeded
        details : str
            Details about the validation
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = "VALIDATION_SUCCESS" if success else "VALIDATION_FAILED"
        log_entry = f"{timestamp} | {mode.upper()} | {status} | {details}\n"

        with open(self.log_file_path, 'a') as f:
            f.write(log_entry)