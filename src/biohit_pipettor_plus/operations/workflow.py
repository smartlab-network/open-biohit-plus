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
from dataclasses import dataclass, field
from biohit_pipettor_plus.operations.operation import Operation


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