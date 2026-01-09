

from biohit_pipettor_plus.deck_structure.labware_classes import Labware
from biohit_pipettor_plus.deck_structure.serializable import register_class
from biohit_pipettor_plus.deck_structure.labware_classes.labware import Default_Reservoir_Capacity, Defined_shape

from typing import Optional


@register_class
class Reservoir(Labware):
    def __init__(self, size_x: float, size_y: float, size_z: float, offset: tuple[float, float] = (0, 0), labware_id: str = None, position: tuple[float, float] = None,
                 can_be_stacked_upon: bool = False, capacity: float = Default_Reservoir_Capacity, content: dict = None,
                 hook_ids: list[int] = None, row: int = None, column: int = None,
                shape: Defined_shape = None):
        """
        Initialize a Reservoir instance. These are containers that store the medium to be filled in and removed from well.

        Parameters
        ----------
        size_x : float
            Width of the reservoir in millimeters.
        size_y : float
            Depth of the reservoir in millimeters.
        size_z : float
            Height of the reservoir in millimeters.
        capacity : float, optional
            Maximum amount of liquid that reservoir can hold. Default is Default_Reservoir_Capacity.
        content : dict, optional
            Dictionary mapping content types to volumes (µL).
            Example: {"PBS": 25000, "water": 5000}
        hook_ids : list[int], optional
            List of hook locations on ReservoirHolder where this reservoir is going to be placed.
        labware_id : str, optional
            Unique ID for the reservoir.
        position : tuple[float, float], optional
            (x, y) position coordinates of the reservoir in millimeters.
            If None, position is not set.
        """
        super().__init__(size_x, size_y, size_z, offset, labware_id, position, can_be_stacked_upon=can_be_stacked_upon)
        self.capacity = capacity
        self.hook_ids = hook_ids if hook_ids is not None else []
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
            raise ValueError(f"Total content volume ({total_volume}) cannot exceed capacity ({self.capacity})")
        if self.capacity < 0:
            raise ValueError("Capacity cannot be negative")

    def add_content(self, content_type: str, volume: float) -> None:
        """
        Add content to the reservoir with intelligent mixing logic.

        When adding content to a reservoir:
        - Same content type: volumes are combined
        - Different content type: tracked separately (but physically mixed)

        Note: Once liquids are mixed in a reservoir, they cannot be separated.
        Removal is always proportional from all content types.

        Parameters
        ----------
        content_type : str
            Content to add (e.g., "PBS", "water", "waste")
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
        Remove content from the reservoir proportionally.

        When content is removed from a reservoir, it's removed proportionally from all
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
            raise ValueError("Cannot remove from empty reservoir")

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

            # Clean up zero or negative volumes
            if self.content[content_type] <= 1e-6:  # Use small epsilon for floating point comparison
                del self.content[content_type]

        # Return the dictionary if requested
        if return_dict:
            return removed_content
        return None

    def get_total_volume(self) -> float:
        """
        Get total volume of all content in the reservoir.

        Returns
        -------
        float
            Total volume in µL
        """
        return sum(self.content.values()) if self.content else 0.0

    def get_available_volume(self) -> float:
        """
        Get the remaining capacity available in the reservoir.

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
        return {
            "content_summary": self.get_content_summary(),
            "available_volume": self.get_available_volume(),
            "total_capacity": self.capacity
        }

    def get_content_summary(self) -> str:
        """
        Get a human-readable summary of reservoir content.

        Returns
        -------
        str
            Summary string like "PBS: 25000µL, water: 5000µL" or "empty"
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
        """Clear all content from the reservoir."""
        self.content = {}

    def has_content_type(self, content_type: str) -> bool:
        """
        Check if reservoir contains specific content type.l
            True if content type is present
        """
        return content_type in self.content and self.content[content_type] > 0

    def get_state_snapshot(self) -> dict:
        """Return deep copy of mutable state"""
        return {'content': self.content.copy()}

    def restore_state_snapshot(self, snapshot: dict) -> None:
        """Restore state from snapshot"""
        self.content = snapshot['content'].copy()

    def is_waste_reservoir(self) -> bool:
        """
        Check if this is a waste reservoir.

        Returns
        -------
        bool
            True if any content type contains "waste" (case-insensitive)
        """
        return any("waste" in ct.lower() for ct in self.content.keys())

    def to_dict(self) -> dict:
        """Serialize the Reservoir to a dictionary."""
        base = super().to_dict()
        base.update({
            "hook_ids": self.hook_ids,
            "capacity": self.capacity,
            "content": self.content,
            "row": self.row,
            "column": self.column,
            "shape" : self.shape,
        })
        return base

    @classmethod
    def _from_dict(cls, data: dict) -> "Reservoir":
        """Deserialize a Reservoir instance from a dictionary."""
        # Safely handle position deserialization
        position = tuple(data["position"]) if data.get("position") else None


        return cls(
            size_x=data["size_x"],
            size_y=data["size_y"],
            size_z=data["size_z"],
            offset=data["offset"],
            can_be_stacked_upon=data.get("can_be_stacked_upon", False),
            labware_id=data["labware_id"],
            hook_ids=data.get("hook_ids", []),
            capacity=data.get("capacity", Default_Reservoir_Capacity),
            content=data.get("content"),
            row=data.get("row"),
            column=data.get("column"),
            position=position,
            shape=data.get("shape", None),
        )

    @property
    def grid_width(self) -> int:
        """How many grid columns this reservoir occupies."""
        # We use getattr to safely check if width_hooks was set during placement
        return getattr(self, 'width_hooks', 1)

    @property
    def grid_height(self) -> int:
        """How many grid rows this reservoir occupies."""
        return getattr(self, 'height_hooks', 1)
