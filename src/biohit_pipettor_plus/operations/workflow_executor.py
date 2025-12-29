"""
Workflow executor with error handling and progress tracking.

This module handles the execution of workflows, providing:
- Sequential operation execution
- Error handling and recovery
- Progress tracking
- Execution logging
"""

from typing import Callable, Optional
from .workflow import Workflow
from .operation import Operation
from .operationtype import OperationType
from .executionresult import ExecutionResult
import traceback

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
        self.current_result = ExecutionResult(
            status=ExecutionResult.NOT_STARTED,
            operations_completed=0,
            total_operations=0
        )
        self.current_operation_index = 0
        self.on_progress: Optional[Callable[[int, int], None]] = None
        self.on_operation_complete: Optional[Callable[[int, Operation], None]] = None
        self.on_error: Optional[Callable[[int, Operation, str], None]] = None

    @property
    def status(self) -> str:
        """Get current execution status"""
        return self.current_result.status

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
        total_ops = len(workflow.operations)

        self.current_result = ExecutionResult(
            status=ExecutionResult.RUNNING,
            operations_completed=start_from,
            total_operations=total_ops
        )
        self.current_operation_index = start_from

        try:
            for i in range(start_from, total_ops):
                self.current_operation_index = i
                operation = workflow.operations[i]

                # Execute operation
                self.execute_single_operation(operation)

                # Update progress
                self.current_result.operations_completed = i + 1

                # Call progress callback
                if self.on_progress:
                    self.on_progress(i + 1, total_ops)

                # Call operation complete callback
                if self.on_operation_complete:
                    self.on_operation_complete(i, operation)

            # Mark as completed
            self.current_result.status = ExecutionResult.COMPLETED
            return self.current_result

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}\n\n{traceback.format_exc()}"

            # Update result with failure info
            self.current_result.status = ExecutionResult.FAILED
            self.current_result.error_message = error_msg
            self.current_result.failed_operation_index = self.current_operation_index

            # Call error callback
            if self.on_error:
                self.on_error(self.current_operation_index, operation, error_msg)

            return self.current_result

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

        # Validate channel mode compatibility
        if 'channels' in params:
            operation_channels = params['channels']
            current_channels = self.pipettor.tip_count

            if operation_channels != current_channels:
                op_mode = "single-channel" if operation_channels == 1 else "multichannel"
                current_mode = "single-channel" if current_channels == 1 else "multichannel"

                raise ValueError(
                    f"Operation mode mismatch: This operation was created for {op_mode} mode, "
                    f"but pipettor is currently in {current_mode} mode. "
                    f"Please edit operation or reinitialise the pipettor in {op_mode} mode to execute this workflow."
                )

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
            labware = get_labware(params['labware']['id'])
            actual_positions = self.pipettor.pick_tips(
                pipette_holder=labware,
                list_col_row=params['positions']
            )


        elif op_type == OperationType.RETURN_TIPS:
            labware = get_labware(params['labware']['id'])
            actual_positions = self.pipettor.return_tips(
                pipette_holder=labware,
                list_col_row=params['positions']
            )


        elif op_type == OperationType.REPLACE_TIPS:
            return_labware = get_labware(params['return_labware']['id'])
            pick_labware = get_labware(params['pick_labware']['id'])

            actual_positions = self.pipettor.replace_tips(
                pipette_holder=return_labware,
                pick_pipette_holder=pick_labware,
                return_list_col_row=params['return_positions'],
                pick_list_col_row=params['pick_positions']
            )

        elif op_type == OperationType.DISCARD_TIPS:
            labware = get_labware(params['labware']['id'])
            self.pipettor.discard_tips(
                tip_dropzone=labware,
            )

        elif op_type == OperationType.ADD_MEDIUM:
            source = get_labware(params['source_labware']['id'])
            dest = get_labware(params['dest_labware']['id'])

            change_tips = params.get('change_tips', False)
            mix_volume = params.get('mix_volume', 0)
            self.pipettor.change_tips = change_tips

            try:
                self.pipettor.add_medium(
                    source=source,
                    source_col_row=params['source_positions'][0],
                    destination=dest,
                    dest_col_row=params['dest_positions'],
                    volume_per_well=params['volume'],
                    mix_volume=mix_volume
                )
            finally:
                self.pipettor.change_tips = False

        elif op_type == OperationType.REMOVE_MEDIUM:
            source = get_labware(params['source_labware']['id'])
            dest = get_labware(params['dest_labware']['id'])
            change_tips = params.get('change_tips', False)
            self.pipettor.change_tips = change_tips

            try:
                self.pipettor.remove_medium(
                    source=source,
                    destination=dest,
                    source_col_row=params['source_positions'],
                    destination_col_row=params['dest_positions'][0],
                    volume_per_well=params['volume'],
                )
            finally:
                self.pipettor.change_tips = False


        elif op_type == OperationType.TRANSFER_PLATE_TO_PLATE:
            source = get_labware(params['source_labware']['id'])
            dest = get_labware(params['dest_labware']['id'])

            mix_volume = params.get('mix_volume', 0)
            change_tips = params.get('change_tips', False)
            self.pipettor.change_tips = change_tips

            try:
                self.pipettor.transfer_plate_to_plate(
                    source=source,
                    destination=dest,
                    source_col_row=params['source_positions'],
                    dest_col_row=params['dest_positions'],
                    volume_per_well=params['volume'],
                    mix_volume=mix_volume
                )
            finally:
                self.pipettor.change_tips = False


        elif op_type == OperationType.REMOVE_AND_ADD:
            # Get labware
            plate = get_labware(params['plate_labware']['id'])
            remove_reservoir = get_labware(params['remove_reservoir']['id'])
            source_reservoir = get_labware(params['source_reservoir']['id'])

            volume = params['volume']
            mix_volume = params.get('mix_volume', 0)
            plate_positions = params['plate_positions']
            remove_positions = params['remove_positions']
            source_positions = params['source_positions']

            # Handle change_tips flag
            change_tips = params.get('change_tips', False)
            self.pipettor.change_tips = change_tips

            try:

                # Calculate how many positions we can handle per trip
                tip_capacity = self.pipettor.tip_volume
                positions_per_trip = int(tip_capacity / volume)
                if positions_per_trip < 1:
                    positions_per_trip = 1  # At minimum, handle one position per trip

                # Batch the positions
                for i in range(0, len(plate_positions), positions_per_trip):
                    batch = plate_positions[i:i + positions_per_trip]

                    # Step 1: Remove from plate to remove reservoir
                    self.pipettor.remove_medium(
                        source=plate,
                        destination=remove_reservoir,
                        source_col_row=batch,
                        destination_col_row=remove_positions[0],
                        volume_per_well=volume,
                    )

                    # Step 2: Add fresh medium from source reservoir to plate
                    self.pipettor.add_medium(
                        source=source_reservoir,
                        source_col_row=source_positions[0],
                        destination=plate,
                        dest_col_row=batch,
                        volume_per_well=volume,
                        mix_volume=mix_volume
                    )
            finally:
                self.pipettor.change_tips = False

        elif op_type == OperationType.HOME:
            self.pipettor.home()

        elif op_type == OperationType.MOVE_XY:
            self.pipettor.move_xy(params['x'], params['y'])

        elif op_type == OperationType.MOVE_Z:
            self.pipettor.move_z(params['z'])

        elif op_type == OperationType.MEASURE_FOC:
            self.pipettor.measure_foc(
                seconds=params['wait_seconds'],
                platename=params['plate_name'],
            )

        else:
            raise ValueError(f"Unknown operation type: {op_type}")