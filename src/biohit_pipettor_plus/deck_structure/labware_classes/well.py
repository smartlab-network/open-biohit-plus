
from .labware import Labware
from ..serializable import register_class
from .labware import Default_well_capacity, Defined_shape

from typing import Optional

@register_class
class Well(Labware):
    """
    Represents a single Well, extending Labware with additional parameters
    for liquid handling.

    Attributes
    ----------
    content : dict
        Dictionary mapping content types to volumes (µL).
    capacity : float
        Maximum volume the well can hold (µL).
    """

    def __init__(
            self,
            size_x: float,
            size_y: float,
            size_z: float,
            offset: tuple[float, float] = (0, 0),
            position: tuple[float, float] = None,
            can_be_stacked_upon: bool = False,
            labware_id: str = None,
            row: int = None,
            column: int = None,
            content: dict = None,
            capacity: float = Default_well_capacity,
            shape: Defined_shape = None
    ):
        """
        Initialize a Well instance.

        Parameters
        ----------
        size_x : float
            Width of the well in millimeters.
        size_y : float
            Depth of the well in millimeters.
        size_z : float
            Height of the well in millimeters.
        position : tuple[float, float], optional
            (x, y) position coordinates of the well in millimeters.
        labware_id : str, optional
            Unique identifier for this well. If None, a UUID will be generated.
        row: int, optional.
            row inside of plate
        column: int, optional
            column inside of plate
        content : dict, optional
            Dictionary mapping content types to volumes (µL).
            Example: {"PBS": 150, "water": 100}
        capacity : float, optional
            Maximum volume the well can hold (µL). Default is Default_well_capacity
        """
        super().__init__(size_x=size_x, size_y=size_y, size_z=size_z, offset=offset, labware_id=labware_id,
                         position=position, can_be_stacked_upon=can_be_stacked_upon,)

        self.capacity = capacity
        self.row = row
        self.column = column
        self.shape = shape

        # Initialize content as dictionary for sophisticated tracking
        if content is None:
            self.content = {}
        elif isinstance(content, dict):
            self.content = content.copy()
        else:
            raise ValueError(f"Content must be dict or None, got {type(content)}")

        # Validate inputs
        total_volume = self.get_total_volume()
        if total_volume > self.capacity:
            raise ValueError(f"Total content volume ({total_volume}µL) cannot exceed capacity ({self.capacity}µL)")
        if self.capacity < 0:
            raise ValueError("Capacity cannot be negative")

    def add_content(self, content_type: str, volume: float) -> None:
        """
        Add content to the well with intelligent mixing logic.

        When adding content to a well:
        - Same content type: volumes are combined
        - Different content type: tracked separately (but physically mixed)

        Note: Once liquids are mixed in a well, they cannot be separated.
        Removal is always proportional from all content types.

        Parameters
        ----------
        content_type : str
            Content to add (e.g., "PBS", "water", "sample")
        volume : float
            Volume to add (µL)

        Raises
        ------
        ValueError
            If adding volume would exceed capacity or volume is negative
        """
        if volume < 0:
            raise ValueError("Volume to add must be positive")

        if not content_type:
            raise ValueError("Content type cannot be empty")

        # Check if adding would exceed capacity
        if self.get_total_volume() + volume > self.capacity:
            raise ValueError(
                f"Overflow! Adding {volume}µL would exceed capacity of {self.capacity}µL. "
                f"Current volume: {self.get_total_volume()}µL"
            )

        # Add content to dictionary
        if content_type in self.content:
            self.content[content_type] += volume
        else:
            self.content[content_type] = volume

    def remove_content(self, volume: float, return_dict: bool = False) -> Optional[dict[str, float]]:
        """
        Remove content from the well proportionally.

        When content is removed from a well, it's removed proportionally from all
        content types since they are mixed together.

        Parameters
        ----------
        volume : float
            Volume to remove (µL)
        return_dict : bool, optional
            If True, return a dictionary of removed content types and volumes (default: False)

        Returns
        -------
        Optional[dict[str, float]]
            If return_dict is True, returns dictionary mapping content types to removed volumes.
            Otherwise, returns None.

        Raises
        ------
        ValueError
            If trying to remove more volume than available or volume is negative
        """
        if volume < 0:
            raise ValueError("Volume to remove must be positive")

        total_volume = self.get_total_volume()

        if total_volume <= 0:
            raise ValueError("Cannot remove from empty well")

        if volume > total_volume:
            raise ValueError(
                f"Underflow! Cannot remove {volume}µL, only {total_volume}µL available"
            )

        # Dictionary to track what was removed
        removed_content: dict[str, float] = {}

        # Remove proportionally from all content types (since they're mixed)
        removal_ratio = volume / total_volume

        # Remove proportionally from each content type
        content_types = list(self.content.keys())
        for content_type in content_types:
            remove_amount = self.content[content_type] * removal_ratio
            removed_content[content_type] = remove_amount
            self.content[content_type] -= remove_amount

            # Clean up zero or negative volumes (use epsilon for floating point comparison)
            if self.content[content_type] <= 1e-6:
                del self.content[content_type]

        # Return the dictionary if requested
        if return_dict:
            return removed_content
        return None

    def get_total_volume(self) -> float:
        """
        Get total volume of all content in the well.

        Returns
        -------
        float
            Total volume in µL
        """
        return sum(self.content.values()) if self.content else 0.0

    def get_available_volume(self) -> float:
        """
        Get the remaining capacity available in the well.

        Returns
        -------
        float
            Available volume in µL
        """
        return self.capacity - self.get_total_volume()

    def get_content_info(self) -> dict:
        """
        Get current content information.

        Returns
        -------
        dict
            Dictionary with detailed content information
        """
        total_volume = self.get_total_volume()
        return {
            "content_dict": self.content.copy(),
            "total_volume": total_volume,
            "available_capacity": self.get_available_volume(),
            "is_empty": total_volume <= 0,
            "is_full": total_volume >= self.capacity,
            "content_summary": self.get_content_summary()
        }

    def get_content_summary(self) -> str:
        """
        Get a human-readable summary of well content.

        Returns
        -------
        str
            Summary string like "PBS: 150.0µL, water: 100.0µL" or "empty"
        """
        if not self.content or self.get_total_volume() <= 0:
            return "empty"

        parts = []
        for content_type, volume in self.content.items():
            parts.append(f"{content_type}: {volume:.1f}µL")

        return ", ".join(parts)

    def get_content_by_type(self, content_type: str) -> float:
        """
        Get volume of specific content type.

        Parameters
        ----------
        content_type : str
            Type of content to query

        Returns
        -------
        float
            Volume of specified content type (0 if not present)
        """
        return self.content.get(content_type, 0.0)

    def clear_content(self) -> None:
        """Clear all content from the well."""
        self.content = {}

    def has_content_type(self, content_type: str) -> bool:
        """
        Check if well contains specific content type.

        Parameters
        ----------
        content_type : str
            Type of content to check

        Returns
        -------
        bool
            True if content type is present with volume > 0
        """
        return content_type in self.content and self.content[content_type] > 0

    def get_state_snapshot(self) -> dict:
        return {'content': self.content.copy()}

    def restore_state_snapshot(self, snapshot: dict) -> None:
        """Restore state from snapshot"""
        self.content = snapshot['content'].copy()

    def to_dict(self) -> dict:
        """
        Serialize the Well to a dictionary for JSON export.

        Returns
        -------
        dict
            dictionary containing all well attributes.
        """
        base = super().to_dict()
        base.update(
            {
                "row": self.row,
                "column": self.column,
                "content": self.content,
                "capacity": self.capacity,
                "shape": self.shape,
            }
        )
        return base

    @classmethod
    def _from_dict(cls, data: dict) -> "Well":
        """
        Deserialize a Well instance from a dictionary.

        Parameters
        ----------
        data : dict
            dictionary with Well attributes.

        Returns
        -------
        Reconstructed Well instance.
        """
        # Safely handle position deserialization
        position = tuple(data["position"]) if data.get("position") else None

        return cls(
            size_x=data["size_x"],
            size_y=data["size_y"],
            size_z=data["size_z"],
            offset=data["offset"],
            labware_id=data["labware_id"],
            can_be_stacked_upon=data.get("can_be_stacked_upon", False),
            position=position,
            content=data.get("content"),
            capacity=data.get("capacity", Default_well_capacity),
            row=data.get("row"),
            column=data.get("column"),
            shape = data.get("shape", None)
        )