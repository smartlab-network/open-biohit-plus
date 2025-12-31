from typing import Literal

import uuid
from ..serializable import Serializable, register_class
from ...pipettor_plus.pipettor_constants import Pipettors_in_Multi, Spacing_Between_Adjacent_Pipettor

Default_Reservoir_Capacity = 30000
Default_well_capacity = 1000
Defined_shape = Literal["rectangular", "circular", "conical", "u_bottom"]

@register_class
class Labware(Serializable):
    """
    Base class for all labware objects with automatic subclass registry.

    Attributes
    ----------
    size_x : float
        Width of the labware in millimeters.
    size_y : float
        Depth of the labware in millimeters.
    size_z : float
        Height of the labware in millimeters.
    position: tuple[float, float]
        x,y coordinate of the labware.
    labware_id : str
        Unique identifier of the labware instance.
    """
    registry: dict[str, type] = {}

    def __init_subclass__(cls, **kwargs):
        """
        Automatically register subclasses by their class name in the Labware registry.
        """
        super().__init_subclass__(**kwargs)
        Labware.registry[cls.__name__] = cls

    @staticmethod
    def validate_positive_dimensions(size_x: float, size_y: float, size_z: float, labware_type: str = "Labware"):
        """Validate that dimensions are positive"""
        if size_x <= 0:
            raise ValueError(f"{labware_type} size_x must be positive, got {size_x}")
        if size_y <= 0:
            raise ValueError(f"{labware_type} size_y must be positive, got {size_y}")
        if size_z <= 0:
            raise ValueError(f"{labware_type} size_z must be positive, got {size_z}")

    def __init__(self, size_x: float, size_y: float, size_z: float, offset: tuple[float, float] = (0.0, 0.0),
                 labware_id: str = None, position: tuple[float, float] = None, can_be_stacked_upon :bool = False):
        """
        Initialize a Labware instance.

        Parameters
        ----------
        size_x : float
            Width of the labware in millimeters.
        size_y : float
            Depth of the labware in millimeters.
        size_z : float
            Height of the labware in millimeters.
        labware_id : str, optional
            Unique ID for the labware. If None, a UUID will be generated.
        position : tuple[float, float], optional
            (x, y) position coordinates of the labware in millimeters.
            If None, position is not set.
    """
        Labware.validate_positive_dimensions(size_x, size_y, size_z, self.__class__.__name__)
        self.size_x = size_x
        self.size_y = size_y
        self.size_z = size_z
        self.offset = offset
        self.position = position
        self.can_be_stacked_upon = can_be_stacked_upon
        self.labware_id = labware_id or f"labware_{uuid.uuid4().hex[:8]}"

    def validate_col_row(self, columns: list[int], row: int, consecutive_rows: int = 1) -> tuple[bool, str]:
        """
        Validate column indices and row range for grid-based labware operations.

        Parameters
        ----------
        columns : list[int]
            List of column indices to validate
        row : int
            Starting row index
        consecutive_rows : int, optional
            Number of consecutive rows needed (default: 1). For multichannel pipette, generally 8

        Returns
        -------
        tuple[bool, str]
            (is_valid, error_message)
            - is_valid: True if validation passes, False otherwise
            - error_message: Empty string if valid, error description if invalid
        """
        # Check if this labware has a grid structure
        if not hasattr(self, '_columns') or not hasattr(self, '_rows'):
            return (False, f"{self.__class__.__name__} does not have a grid structure")

        # Validate column indices
        for col in columns:
            if col < 0 or col >= self._columns:
                return (False, f"Column index {col} is out of range. Valid range is 0 to {self._columns - 1}")

        # Validate row range
        if row < 0:
            return (False, f"Row index {row} cannot be negative")

        if row + consecutive_rows > self._rows:
            return (False,
                    f"Row index {row} is out of range. Need {consecutive_rows} consecutive row(s). Valid range is 0 to {self._rows - consecutive_rows}")

        return (True, "")

    def validate_col_row_or_raise(self, columns: list[int], row: int, consecutive_rows: int = 1) -> None:
        """
        Validate column and row, raising ValueError if invalid.

        Convenience method for when you want to raise an error immediately.
        """
        is_valid, error_msg = self.validate_col_row(columns, row, consecutive_rows)
        if not is_valid:
            raise ValueError(error_msg)

    def each_tip_needs_separate_item(self) -> bool:
        """
            For multichannel operation, does each tip need to access a separate item?

                Returns
                -------
                bool
                    True: Each tip needs its own item (e.g., Plate - small wells)
                    False: All tips can share one item (e.g., ReservoirHolder - large reservoirs)
                """
        return True  # Default: items are small, tips need separate items. overwritten for some labwares like plate

    def validate_multichannel_compatible(self, item_size_y: float) -> tuple[bool, str]:
        """
        Validate if an item is large enough for multichannel operation.

        Parameters
        ----------
        item_size_y : float
            The Y-dimension of the item to validate (e.g., reservoir, well)

        Returns
        -------
        tuple[bool, str]
            (is_valid, error_message)
        """
        if not self.each_tip_needs_separate_item():
            min_required_y = Pipettors_in_Multi * Spacing_Between_Adjacent_Pipettor
            if item_size_y < min_required_y:
                return (False,
                        f"Item size_y ({item_size_y}mm) is too small for multichannel operation. "
                        f"Minimum required: {min_required_y}mm. "
                        f"Increase size y or set labware to one item per tip ")

        return (True, "")

    def to_dict(self) -> dict:
        """
        Serialize the Labware instance to a dictionary.

        Returns
        -------
        dict
            dictionary representation of the labware.
        """
        return {
            "class": self.__class__.__name__,
            "labware_id": self.labware_id,
            "size_x": self.size_x,
            "size_y": self.size_y,
            "size_z": self.size_z,
            "offset": self.offset,
            "can_be_stacked_upon": self.can_be_stacked_upon,
            "position": list(self.position) if self.position else None,
        }

    @classmethod
    def _from_dict(cls, data: dict) -> "Labware":
        """
        Deserialize a Labware instance from a dictionary.

        Parameters
        ----------
        data : dict
            dictionary containing labware attributes.

        Returns
        -------
        Labware
            Reconstructed Labware instance.
        """

        # Safely handle position deserialization
        position = tuple(data["position"]) if data.get("position") else None

        return cls(
            size_x=data["size_x"],
            size_y=data["size_y"],
            size_z=data["size_z"],
            offset=data["offset"],
            can_be_stacked_upon=data.get("can_be_stacked_upon", False),
            labware_id=data["labware_id"],
            position=position
        )

