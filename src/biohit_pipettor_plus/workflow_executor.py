"""
Workflow executor with error handling and progress tracking.

This module handles the execution of workflows, providing:
- Sequential operation execution
- Error handling and recovery
- Progress tracking
- Execution logging
"""

from typing import Callable, Optional
from dataclasses import dataclass
from enum import Enum
import traceback

from workflow import Workflow, Operation, OperationType


class ExecutionStatus(Enum):
    """Status of workflow execution"""
    NOT_STARTED = "not_started"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ExecutionResult:
    """Result of workflow execution"""
    status: ExecutionStatus
    operations_completed: int
    total_operations: int
    error_message: Optional[str] = None
    failed_operation_index: Optional[int] = None

    @property
    def success(self) -> bool:
        """Check if execution was successful"""
        return self.status == ExecutionStatus.COMPLETED

    @property
    def progress_percent(self) -> float:
        """Get progress as percentage"""
        if self.total_operations == 0:
            return 0.0
        return (self.operations_completed / self.total_operations) * 100


class WorkflowExecutor:
    """
    Executes workflows with error handling and progress tracking.
    """

    def __init__(self, pipettor, deck):
        """
        Initialize executor.

        Parameters
        ----------
        pipettor : PipettorPlus
            Pipettor instance
        deck : Deck
            Deck instance
        """
        self.pipettor = pipettor
        self.deck = deck
        self.status = ExecutionStatus.NOT_STARTED
        self.current_operation_index = 0
        self.on_progress: Optional[Callable[[int, int], None]] = None
        self.on_operation_complete: Optional[Callable[[int, Operation], None]] = None
        self.on_error: Optional[Callable[[int, Operation, str], None]] = None

    def execute_workflow(self, workflow: Workflow, start_from: int = 0) -> ExecutionResult:
        """
        Execute a complete workflow.

        Parameters
        ----------
        workflow : Workflow
            Workflow to execute
        start_from : int
            Operation index to start from (for resuming)

        Returns
        -------
        ExecutionResult
            Result of execution
        """
        self.status = ExecutionStatus.RUNNING
        self.current_operation_index = start_from

        total_ops = len(workflow.operations)

        try:
            for i in range(start_from, total_ops):
                self.current_operation_index = i
                operation = workflow.operations[i]

                # Execute operation
                self.execute_single_operation(operation)

                # Call progress callback
                if self.on_progress:
                    self.on_progress(i + 1, total_ops)

                # Call operation complete callback
                if self.on_operation_complete:
                    self.on_operation_complete(i, operation)

            self.status = ExecutionStatus.COMPLETED
            return ExecutionResult(
                status=ExecutionStatus.COMPLETED,
                operations_completed=total_ops,
                total_operations=total_ops
            )

        except Exception as e:
            self.status = ExecutionStatus.FAILED
            error_msg = f"{type(e).__name__}: {str(e)}\n\n{traceback.format_exc()}"

            # Call error callback
            if self.on_error:
                self.on_error(self.current_operation_index, operation, error_msg)

            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                operations_completed=self.current_operation_index,
                total_operations=total_ops,
                error_message=error_msg,
                failed_operation_index=self.current_operation_index
            )

    def execute_single_operation(self, operation: Operation) -> None:
        """
        Execute a single operation.

        Parameters
        ----------
        operation : Operation
            Operation to execute
        """
        op_type = operation.operation_type
        params = operation.parameters

        # Get labware objects from deck
        labware_cache = {}

        def get_labware(labware_id: str):
            """Get labware object from deck"""
            if labware_id in labware_cache:
                return labware_cache[labware_id]

            # Search through deck
            for slot_id, slot in self.deck.slots.items():
                if not slot.labware_stack:
                    continue
                for lw_id, (lw, _) in slot.labware_stack.items():
                    if lw.labware_id == labware_id:
                        labware_cache[labware_id] = lw
                        return lw

            raise ValueError(f"Labware '{labware_id}' not found on deck")

        # Execute based on operation type
        if op_type == OperationType.PICK_TIPS:
            labware = get_labware(params['labware_id'])
            self.pipettor.pick_tips(
                pipette_holder=labware,
                list_col_row=params['positions']
            )

        elif op_type == OperationType.RETURN_TIPS:
            labware = get_labware(params['labware_id'])
            self.pipettor.return_tips(
                pipette_holder=labware,
                list_col_row=params['positions']
            )

        elif op_type == OperationType.REPLACE_TIPS:
            return_labware = get_labware(params['return_labware_id'])
            pick_labware = get_labware(params['pick_labware_id'])
            self.pipettor.replace_tips(
                pipette_holder=return_labware,
                pick_pipette_holder=pick_labware,
                return_list_col_row=params['return_positions'],
                pick_list_col_row=params['pick_positions']
            )

        elif op_type == OperationType.DISCARD_TIPS:
            labware = get_labware(params['labware_id'])
            self.pipettor.discard_tips(
                tip_dropzone=labware,
            )

        elif op_type == OperationType.ADD_MEDIUM:
            source = get_labware(params['source_labware_id'])
            dest = get_labware(params['dest_labware_id'])

            self.pipettor.add_medium(
                source=source,
                source_col_row=params['source_positions'],
                destination=dest,
                dest_col_row=params['dest_positions'],
                volume_per_well=params['volume'],
            )

        elif op_type == OperationType.REMOVE_MEDIUM:
            source = get_labware(params['source_labware_id'])
            dest = get_labware(params['dest_labware_id'])

            self.pipettor.remove_medium(
                source=source,
                destination=dest,
                source_col_row=params['source_positions'],
                destination_col_row=params['dest_positions'],
                volume_per_well=params['volume'],
            )

        elif op_type == OperationType.TRANSFER_PLATE_TO_PLATE:
            source = get_labware(params['source_labware_id'])
            dest = get_labware(params['dest_labware_id'])

            self.pipettor.transfer_plate_to_plate(
                source=source,
                destination=dest,
                source_col_row=params['source_positions'],
                dest_col_row=params['dest_positions'],
                volume_per_well=params['volume'],
            )
        elif op_type == OperationType.SUCK:
            labware = get_labware(params['labware_id'])
            self.pipettor.suck(
                source=labware,
                source_col_row=params['position'],
                volume=params['volume']
            )

        elif op_type == OperationType.SPIT:
            labware = get_labware(params['labware_id'])
            self.pipettor.spit(
                destination=labware,
                dest_col_row=params['position'],
                volume=params['volume']
            )

        elif op_type == OperationType.HOME:
            self.pipettor.home()

        elif op_type == OperationType.MOVE_XY:
            self.pipettor.move_xy(params['x'], params['y'])

        elif op_type == OperationType.MOVE_Z:
            self.pipettor.move_z(params['z'])

        else:
            raise ValueError(f"Unknown operation type: {op_type}")
