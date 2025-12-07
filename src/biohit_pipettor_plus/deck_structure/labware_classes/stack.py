from .labware import Labware
from ..serializable import register_class


@register_class
class Stack(Labware):
    """
    A labware that serves as a platform for stacking other labware on top.
    Has no functional elements itself - purely structural.

    Attributes
    ----------
    can_be_stacked_upon : bool
        Whether other labware can be placed on top of this stack (default True)
    """

    def __init__(
            self,
            size_x: float,
            size_y: float,
            size_z: float,
            offset: tuple[float, float] = (0.0, 0.0),
            labware_id: str = None,
            position: tuple[float, float] = None,
            can_be_stacked_upon: bool = True  # Stack's purpose is to be stacked upon
    ):
        """
        Initialize a Stack instance.

        """
        super().__init__(
            size_x=size_x,
            size_y=size_y,
            size_z=size_z,
            offset=offset,
            labware_id=labware_id,
            position=position,
            can_be_stacked_upon=can_be_stacked_upon
        )

    def each_tip_needs_separate_item(self) -> bool:
        """
        Stack has no functional items.

        Returns
        -------
        bool
            False - Stack is purely structural
        """
        return False

    def validate_col_row_or_raise(
            self,
            columns: list[int],
            start_row: int,
            consecutive_rows: int = 1
    ) -> None:
        """
        Stack has no positions to validate - always raises.
        """
        raise ValueError(
            f"Stack '{self.labware_id}' has no functional positions. "
            "It is only used as a platform for stacking other labware."
        )

    def get_state_snapshot(self) -> dict:
        """Return empty snapshot - Stack has no mutable state"""
        return {}

    def restore_state_snapshot(self, snapshot: dict) -> None:
        """No-op - Stack has no mutable state to restore"""
        pass

    def to_dict(self) -> dict:
        """
        Serialize the Stack to a dictionary.

        Returns
        -------
        dict
            Dictionary containing all stack attributes.
        """
        base = super().to_dict()
        return base

    @classmethod
    def _from_dict(cls, data: dict) -> "Stack":
        """
        Deserialize a Stack instance from a dictionary.

        Parameters
        ----------
        data : dict
            Dictionary with Stack attributes.

        Returns
        -------
        Stack
            Reconstructed Stack instance.
        """
        # Safely handle position deserialization
        position = tuple(data["position"]) if data.get("position") else None

        return cls(
            size_x=data["size_x"],
            size_y=data["size_y"],
            size_z=data["size_z"],
            offset=tuple(data.get("offset", (0.0, 0.0))),
            labware_id=data["labware_id"],
            position=position,
            can_be_stacked_upon=data.get("can_be_stacked_upon", True)
        )

    def __repr__(self):
        return (f"Stack(id='{self.labware_id}', "
                f"size=({self.size_x}, {self.size_y}, {self.size_z}), "
                f"position={self.position})")