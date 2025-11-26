"""
Workflow system for laboratory automation.

This module provides a serializable, inspectable workflow system that replaces
the previous lambda-based approach. It enables:
- JSON persistence of workflows
- Virtual deck state tracking during workflow building
- Proper execution with error handling
- Operation introspection and editing
"""

import json
import uuid
from typing import Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
import copy
from labware import Plate, PipetteHolder, ReservoirHolder, TipDropzone


class OperationType(Enum):
    """Types of pipetting operations"""
    PICK_TIPS = "pick_tips"
    RETURN_TIPS = "return_tips"
    REPLACE_TIPS = "replace_tips"
    DISCARD_TIPS = "discard_tips"
    ADD_MEDIUM = "add_medium"
    REMOVE_MEDIUM = "remove_medium"
    TRANSFER_PLATE_TO_PLATE = "transfer_plate_to_plate"
    TRANSFER_RESERVOIR_TO_PLATE = "transfer_reservoir_to_plate"
    TRANSFER_PLATE_TO_RESERVOIR = "transfer_plate_to_reservoir"


@dataclass
class Operation:
    """
    Serializable operation object.

    Attributes
    ----------
    operation_type : OperationType
        Type of operation
    operation_id : str
        Unique identifier
    parameters : dict
        Operation parameters (all JSON-serializable)
    description : str
        Human-readable description
    """
    operation_type: OperationType
    parameters: dict[str, Any]
    description: str
    operation_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary"""
        return {
            'operation_type': self.operation_type.value,
            'operation_id': self.operation_id,
            'parameters': self.parameters,
            'description': self.description
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Operation':
        """Reconstruct from dictionary"""
        return cls(
            operation_type=OperationType(data['operation_type']),
            operation_id=data['operation_id'],
            parameters=data['parameters'],
            description=data['description']
        )

    def execute(self, pipettor, deck) -> None:
        """
        Execute this operation.

        Parameters
        ----------
        pipettor : PipettorPlus
            Pipettor instance to use
        deck : Deck
            Deck instance to use
        """
        # Import here to avoid circular dependency
        from workflow_executor import WorkflowExecutor
        executor = WorkflowExecutor(pipettor, deck)
        executor.execute_single_operation(self)


class WorkflowState:
    """
    Tracks virtual deck state during workflow building.

    This allows the workflow builder to show the predicted state of the deck
    as operations are added, enabling dynamic UI updates.
    """

    def __init__(self, deck):
        """
        Initialize workflow state from current deck.

        Parameters
        ----------
        deck : Deck
            The current deck to base virtual state on
        """
        self.deck = deck
        # Deep copy the deck state
        self.virtual_deck_state = self._copy_deck_state()
        self.has_tips = False

    def _copy_deck_state(self) -> dict:
        """Create a deep copy of current deck state"""
        state = {}
        for slot_id, slot in self.deck.slots.items():
            if not slot.labware_stack:
                continue

            # Get top labware
            top_lw_id, (top_lw, (min_z, max_z)) = max(
                slot.labware_stack.items(),
                key=lambda item: item[1][1][1]
            )

            if isinstance(top_lw, Plate):
                # Copy well states
                well_states = {}
                for (col, row), well in top_lw.get_wells().items():
                    well_states[(col, row)] = {
                        'content': copy.deepcopy(well.content),
                        'row': row,
                        'column': col
                    }
                state[slot_id] = {
                    'type': 'plate',
                    'labware_id': top_lw.labware_id,
                    'wells': well_states
                }

            elif isinstance(top_lw, PipetteHolder):
                # Copy tip states
                tip_states = {}
                for (col, row), holder in top_lw.get_individual_holders().items():
                    tip_states[(col, row)] = {
                        'is_occupied': holder.is_occupied,
                        'row': row,
                        'column': col
                    }
                state[slot_id] = {
                    'type': 'pipette_holder',
                    'labware_id': top_lw.labware_id,
                    'tips': tip_states
                }

            elif isinstance(top_lw, ReservoirHolder):
                # Copy reservoir states
                reservoir_states = {}
                for res in top_lw.get_reservoirs():
                    res_key = (res.column, res.row)
                    reservoir_states[res_key] = {
                        'content': copy.deepcopy(res.content),
                        'row': res.row,
                        'column': res.column
                    }
                state[slot_id] = {
                    'type': 'reservoir_holder',
                    'labware_id': top_lw.labware_id,
                    'reservoirs': reservoir_states
                }

            elif isinstance(top_lw, TipDropzone):
                state[slot_id] = {
                    'type': 'tip_dropzone',
                    'labware_id': top_lw.labware_id
                }

        return state

    def apply_operation(self, operation: Operation) -> None:
        """
        Apply an operation to the virtual state.

        Parameters
        ----------
        operation : Operation
            Operation to apply
        """
        op_type = operation.operation_type
        params = operation.parameters

        if op_type == OperationType.PICK_TIPS:
            self._apply_pick_tips(params)
        elif op_type == OperationType.RETURN_TIPS:
            self._apply_return_tips(params)
        elif op_type == OperationType.REPLACE_TIPS:
            self._apply_replace_tips(params)
        elif op_type == OperationType.DISCARD_TIPS:
            self._apply_discard_tips(params)
        elif op_type == OperationType.ADD_MEDIUM:
            self._apply_add_medium(params)
        elif op_type == OperationType.REMOVE_MEDIUM:
            self._apply_remove_medium(params)
        elif op_type == OperationType.TRANSFER_PLATE_TO_PLATE:
            self._apply_transfer_plate_to_plate(params)
        elif op_type == OperationType.TRANSFER_RESERVOIR_TO_PLATE:
            self._apply_transfer_reservoir_to_plate(params)
        elif op_type == OperationType.TRANSFER_PLATE_TO_RESERVOIR:
            self._apply_transfer_plate_to_reservoir(params)

    def _apply_pick_tips(self, params: dict) -> None:
        """Apply pick tips operation to virtual state"""
        labware_id = params['labware_id']
        positions = params['positions']

        for slot_id, labware_state in self.virtual_deck_state.items():
            if labware_state['labware_id'] == labware_id:
                if labware_state['type'] == 'pipette_holder':
                    # Mark tips as not occupied (picked up)
                    for pos in positions:
                        if pos in labware_state['tips']:
                            labware_state['tips'][pos]['is_occupied'] = False

                    self.has_tips = True
                break

    def _apply_return_tips(self, params: dict) -> None:
        """Apply return tips operation to virtual state"""
        labware_id = params['labware_id']
        positions = params['positions']

        for slot_id, labware_state in self.virtual_deck_state.items():
            if labware_state['labware_id'] == labware_id:
                if labware_state['type'] == 'pipette_holder':
                    # Mark tips as occupied (returned)
                    for pos in positions:
                        if pos in labware_state['tips']:
                            labware_state['tips'][pos]['is_occupied'] = True

                    self.has_tips = False
                break

    def _apply_replace_tips(self, params: dict) -> None:
        """Apply replace tips operation to virtual state"""
        # This is pick + return in sequence
        self._apply_return_tips({
            'labware_id': params['return_labware_id'],
            'positions': params['return_positions']
        })
        self._apply_pick_tips({
            'labware_id': params['pick_labware_id'],
            'positions': params['pick_positions']
        })

    def _apply_discard_tips(self, params: dict) -> None:
        """Apply discard tips operation to virtual state"""
        # Tips are removed from pipettor
        self.has_tips = False

    def _apply_add_medium(self, params: dict) -> None:
        """Apply add medium operation to virtual state"""
        dest_labware_id = params['dest_labware_id']
        dest_positions = params['dest_positions']
        volume = params['volume']
        source_labware_id = params['source_labware_id']

        # Update source reservoir
        for slot_id, labware_state in self.virtual_deck_state.items():
            if labware_state['labware_id'] == source_labware_id:
                if labware_state['type'] == 'reservoir_holder':
                    # Decrease reservoir volume
                    source_pos = params['source_positions']
                    if source_pos in labware_state['reservoirs']:
                        for content_type in labware_state['reservoirs'][source_pos]['content']:
                            total_vol = volume * len(dest_positions)
                            if params.get('channels') == 8:
                                total_vol *= 8
                            labware_state['reservoirs'][source_pos]['content'][content_type] -= total_vol
                break

        # Update destination plate
        for slot_id, labware_state in self.virtual_deck_state.items():
            if labware_state['labware_id'] == dest_labware_id:
                if labware_state['type'] == 'plate':
                    # Increase well volumes
                    for pos in dest_positions:
                        if pos in labware_state['wells']:
                            # Add to content (assuming 'medium' type)
                            if 'medium' not in labware_state['wells'][pos]['content']:
                                labware_state['wells'][pos]['content']['medium'] = 0
                            labware_state['wells'][pos]['content']['medium'] += volume
                break

    def _apply_remove_medium(self, params: dict) -> None:
        """Apply remove medium operation to virtual state"""
        source_labware_id = params['source_labware_id']
        source_positions = params['source_positions']
        volume = params['volume']

        # Update source plate
        for slot_id, labware_state in self.virtual_deck_state.items():
            if labware_state['labware_id'] == source_labware_id:
                if labware_state['type'] == 'plate':
                    # Decrease well volumes
                    for pos in source_positions:
                        if pos in labware_state['wells']:
                            for content_type in labware_state['wells'][pos]['content']:
                                labware_state['wells'][pos]['content'][content_type] -= volume
                break

        # Note: Could also update destination reservoir, but typically waste

    def _apply_transfer_plate_to_plate(self, params: dict) -> None:
        """Apply plate to plate transfer operation to virtual state"""
        # Remove from source
        self._apply_remove_medium({
            'source_labware_id': params['source_labware_id'],
            'source_positions': params['source_positions'],
            'volume': params['volume']
        })

        # Add to destination
        self._apply_add_medium({
            'source_labware_id': params['source_labware_id'],  # Not actually used in add
            'dest_labware_id': params['dest_labware_id'],
            'dest_positions': params['dest_positions'],
            'volume': params['volume'],
            'channels': params.get('channels', 1),
            'source_positions': None  # Not used
        })

    def _apply_transfer_reservoir_to_plate(self, params: dict) -> None:
        """Apply reservoir to plate transfer"""
        self._apply_add_medium(params)

    def _apply_transfer_plate_to_reservoir(self, params: dict) -> None:
        """Apply plate to reservoir transfer"""
        self._apply_remove_medium(params)

    def get_labware_state(self, labware_id: str) -> Optional[dict]:
        """
        Get the current virtual state of a labware.

        Parameters
        ----------
        labware_id : str
            ID of the labware

        Returns
        -------
        Optional[dict]
            State dictionary or None if not found
        """
        for slot_id, labware_state in self.virtual_deck_state.items():
            if labware_state['labware_id'] == labware_id:
                return labware_state
        return None

    #todo delete
    def get_well_volume(self, labware_id: str, position: str, content_type: str = None) -> float:
        """Get the volume in a well"""
        state = self.get_labware_state(labware_id)
        if state and state['type'] == 'plate':
            if position in state['wells']:
                if content_type:
                    return state['wells'][position]['content'].get(content_type, 0)
                else:
                    return sum(state['wells'][position]['content'].values())
        return 0.0

    def reset(self) -> None:
        """Reset virtual state to match current deck"""
        self.virtual_deck_state = self._copy_deck_state()
        self.has_tips = False

@dataclass
class Workflow:
    """
    Container for a workflow of operations.

    Attributes
    ----------
    name : str
        Workflow name
    operations : list[Operation]
        List of operations in order
    workflow_id : str
        Unique identifier
    description : str
        Optional description
    """
    name: str
    operations: list[Operation] = field(default_factory=list)
    workflow_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""

    def add_operation(self, operation: Operation) -> None:
        """Add an operation to the workflow"""
        self.operations.append(operation)

    def remove_operation(self, index: int) -> None:
        """Remove an operation by index"""
        if 0 <= index < len(self.operations):
            del self.operations[index]

    def move_operation(self, from_index: int, to_index: int) -> None:
        """Move an operation to a different position"""
        if 0 <= from_index < len(self.operations) and 0 <= to_index < len(self.operations):
            operation = self.operations.pop(from_index)
            self.operations.insert(to_index, operation)

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary"""
        return {
            'name': self.name,
            'workflow_id': self.workflow_id,
            'description': self.description,
            'operations': [op.to_dict() for op in self.operations]
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Workflow':
        """Reconstruct from dictionary"""
        workflow = cls(
            name=data['name'],
            workflow_id=data['workflow_id'],
            description=data.get('description', '')
        )
        workflow.operations = [Operation.from_dict(op) for op in data['operations']]
        return workflow

    def save_to_file(self, filepath: str) -> None:
        """Save workflow to JSON file"""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load_from_file(cls, filepath: str) -> 'Workflow':
        """Load workflow from JSON file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)

    def __len__(self) -> int:
        """Return number of operations"""
        return len(self.operations)