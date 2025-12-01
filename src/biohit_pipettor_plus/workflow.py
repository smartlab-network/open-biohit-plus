"""
Workflow system for laboratory automation.

This module provides a serializable, inspectable workflow system. It enables:
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
    SUCK = "suck"
    SPIT = "spit"
    HOME = "home"
    MOVE_XY = "move_xy"
    MOVE_Z = "move_z"


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
        print(operation)

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