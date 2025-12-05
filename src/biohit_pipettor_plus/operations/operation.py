
from .operationtype import OperationType

from typing import Any
from dataclasses import dataclass, field
import uuid

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
        from .workflow_executor import WorkflowExecutor

        executor = WorkflowExecutor(pipettor, deck)
        executor.execute_single_operation(self)