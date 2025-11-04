import sys
import os
from typing import Literal

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import uuid
from serializable import Serializable, register_class
import copy
from typing import Optional


Pipettors_in_Multi = 8
Default_Reservoir_Capacity = 30000
Default_well_capacity = 1000
Spacing_Between_Adjacent_Pipettor = 2  # Add this (adjust value based on multipipettor used.)
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
                        f"Minimum required: {min_required_y}mm")

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
            can_be_stacked_upon=data["can_be_stacked_upon"],
            labware_id=data["labware_id"],
            position=position
        )

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
    add_height : float
        Height above the well bottom used when adding liquid (in mm).
    remove_height : float
        Height above the well bottom used when removing liquid (in mm).
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

@register_class
class Plate(Labware):

    def __init__(self, size_x: float,
            size_y: float,
            size_z: float,
            wells_x: int,
            wells_y: int,
            well: Well,
            add_height: float = -3,
            remove_height: float = -10,
            offset: tuple[float, float] = (0, 0),
            labware_id: str = None,
            position: tuple[float, float] = None,
            can_be_stacked_upon: bool = False):
        """
        Initialize a Plate instance.

        Parameters
        ----------
        size_x : float
            Width of the plate.
        size_y : float
            Depth of the plate.
        size_z : float
            Height of the plate.
        wells_x : int
            Number of wells in X direction.
        wells_y : int
            Number of wells in Y direction.
        add_height : float
            Height above the well bottom used when adding liquid (in mm).
        remove_height : float
            Height above the well bottom used when removing liquid (in mm).
        well : Well
            Template well to use for all wells in the plate.
        offset : tuple[float, float], optional
            Offset of the plate.
        labware_id : str, optional
            Unique ID for the plate.
        position : tuple[float, float], optional
            (x, y) position coordinates of the plate in millimeters.
        """

        super().__init__(size_x=size_x, size_y=size_y, size_z=size_z, offset=offset, labware_id=labware_id,
                         position=position, can_be_stacked_upon=can_be_stacked_upon)

        if wells_x <= 0 or wells_y <= 0:
            raise ValueError("wells_x and wells_y cannot be negative or 0")

        self._columns = wells_x
        self._rows = wells_y
        self.add_height = add_height
        self.remove_height = remove_height

        self.__wells: dict[tuple[int, int], Well] = {}
        self.well = well

        if self._columns * well.size_x > size_x or self._rows * well.size_y > size_y:
                raise ValueError("Well is too big for this Plate")

        self.place_wells()


    def place_wells(self):
        """Create wells across the grid using the template well."""
        for x in range(self._columns):
            for y in range(self._rows):
                well = copy.deepcopy(self.well)
                well.labware_id = f'{self.labware_id}_{x}:{y}'
                well.row = y
                well.column = x
                self.__wells[(x, y)] = well

    def get_wells(self) -> dict[tuple[int, int], Well]:  # ✅ Correct type
        """Get all wells in the plate."""
        return self.__wells

    def get_well_at(self, column: int, row: int) -> Optional[Well]:
        """
                Get the well at a specific position.

                Parameters
                ----------
                column : int
                    Column index
                row : int
                    Row index

                Returns
                -------
                Optional[Well]
                    The well at the position, or None if not found
                """
        return self.__wells.get((column, row))

    def get_wells_in_column(self, column: int) -> list[Well]:
        """Get all wells in a specific column."""
        wells = []
        for row in range(self._rows):
            well = self.get_well_at(column, row)
            if well:
                wells.append(well)
        return wells

    def get_wells_in_row(self, row: int) -> list[Well]:
        """Get all wells in a specific row."""
        wells = []
        for col in range(self._columns):
            well = self.get_well_at(col, row)
            if well:
                wells.append(well)
        return wells

    def to_dict(self):
        """Serialize the Plate instance to a dictionary."""
        base = super().to_dict()
        base.update({
            "add_height": self.add_height,
            "remove_height": self.remove_height,
            "wells_x": self.wells_x,
            "wells_y": self.wells_y,
            "wells": {
                f"{col}:{row}": well.to_dict()
                for (col, row), well in self.__wells.items()
            }
        })
        return base

    @classmethod
    def _from_dict(cls, data: dict) -> "Plate":
        position = tuple(data["position"]) if data.get("position") else None
        wells_data = data.get("wells", {})

        if not wells_data:
            raise ValueError("Cannot deserialize Plate without wells data")

        # Get the first well as a template
        first_well_data = next(iter(wells_data.values()))
        template_well = Serializable.from_dict(first_well_data)

        # ADD: Pass well parameter!
        plate = cls(
            size_x=data["size_x"],
            size_y=data["size_y"],
            size_z=data["size_z"],
            offset=data["offset"],
            add_height=data["add_height"],
            remove_height=data["remove_height"],
            labware_id=data["labware_id"],
            wells_x=data["wells_x"],
            wells_y=data["wells_y"],
            can_be_stacked_upon=data.get("can_be_stacked_upon", False),
            well=template_well,
            position=position,
        )

        # Restore wells with their actual state
        for wid, wdata in wells_data.items():
            col, row = map(int, wid.split(':'))
            restored_well = Serializable.from_dict(wdata)
            plate._Plate__wells[(col, row)] = restored_well

        return plate

    @property
    def wells_x(self) -> int:
        """Number of wells in X direction (columns)"""
        return self._columns

    @property
    def wells_y(self) -> int:
        """Number of wells in Y direction (rows)"""
        return self._rows

    @property
    def grid_x(self) -> int:
        """Standard grid dimension (columns)"""
        return self._columns

    @property
    def grid_y(self) -> int:
        """Standard grid dimension (rows)"""
        return self._rows

@register_class
class IndividualPipetteHolder(Labware):
    """
    Represents an individual pipette holder position within a PipetteHolder.
    Tracks occupancy status and pipette type.

    Attributes
    ----------
    is_occupied : bool
        Whether this holder position currently contains a pipette.
    """

    def __init__(
            self,
            size_x: float,
            size_y: float,
            size_z: float,
            offset: tuple[float, float] = (0, 0),
            is_occupied: bool = True,
            row: int = None,
            column: int = None,
            labware_id: str = None,
            can_be_stacked_upon: bool = False,
            position: tuple[float, float] = None
    ):
        """
        Initialize an IndividualPipetteHolder instance.

        Parameters
        ----------
        size_x : float
            Width of the individual holder position in millimeters.
        size_y : float
            Depth of the individual holder position in millimeters.
        size_z : float
            Height of the individual holder position in millimeters.
        is_occupied : bool, optional
            Whether a pipette is currently stored here. Default is False.
        labware_id : str, optional
            Unique identifier for this holder position. If None, a UUID will be generated.
        position : tuple[float, float], optional
            (x, y) absolute position coordinates in millimeters.
            If None, position is not set.
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

        self.is_occupied = is_occupied
        self.row = row
        self.column = column

    def place_pipette(self) -> None:
        """
        Mark this holder position as occupied (pipette placed).
        Raises ValueError If the holder position is already occupied.
        """
        if self.is_occupied:
            raise ValueError(
                f"Holder position {self.labware_id} is already occupied"
            )

        self.is_occupied = True

    def remove_pipette(self) -> None:
        """
        Mark this holder position as available (pipette removed).

        Raises
        ------
        ValueError
            If the holder position is already empty.
        """
        if not self.is_occupied:
            raise ValueError(f"Holder position {self.labware_id} is already empty")

        self.is_occupied = False

    def is_available(self) -> bool:
        """
        Check if this holder position is available for placing a pipette.
        Returns bool.True if available (not occupied), False otherwise.
        """
        return not self.is_occupied

    def to_dict(self) -> dict:
        """
        Serialize the IndividualPipetteHolder to a dictionary.
        Returns dict
            Dictionary containing all holder attributes.
        """
        base = super().to_dict()
        base.update({
            "is_occupied": self.is_occupied,
            "row": self.row,
            "column": self.column,
        })
        return base

    @classmethod
    def _from_dict(cls, data: dict) -> "IndividualPipetteHolder":
        """
        Deserialize an IndividualPipetteHolder instance from a dictionary.

        Parameters
        data : dict
            Dictionary with IndividualPipetteHolder attributes.

        Returns IndividualPipetteHolder
            Reconstructed IndividualPipetteHolder instance.
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
            is_occupied=data.get("is_occupied", False),
            row=data.get("row"),
            column=data.get("column"),
        )

@register_class
class PipetteHolder(Labware):
    def __init__(self, size_x: float, size_y: float, size_z: float, holders_across_x: int, holders_across_y: int,
                 individual_holder: IndividualPipetteHolder, add_height: float = -15, remove_height : float = 15, offset: tuple[float, float] = (0, 0),
                 labware_id: str = None, position: tuple[float, float] = None, can_be_stacked_upon: bool = False,):
        """
        Initialize a PipetteHolder instance.

        Parameters
        ----------
        size_x : float
            Width of the pipette holder in millimeters.
        size_y : float
            Depth of the pipette holder in millimeters.
        size_z : float
            Height of the pipette holder in millimeters.
        holders_across_x : int
            Number of individual holder positions across X-axis.
        holders_across_y : int
            Number of individual holder positions across Y-axis.
        individual_holder : IndividualPipetteHolder
            Template for individual holder positions. If provided, copies will be created for each position in the grid.
        labware_id : str, optional
            Unique ID for the pipette holder.
        add_height : float
            Height above the well bottom used when adding liquid (in mm).
        remove_height : float
            Height above the well bottom used when removing liquid (in mm).
        position : tuple[float, float], optional
            (x, y) position coordinates of the pipette holder in millimeters.
            If None, position is not set.
        """
        super().__init__(size_x=size_x, size_y=size_y, size_z=size_z, offset=offset, labware_id=labware_id,
                         position=position, can_be_stacked_upon=can_be_stacked_upon)

        if holders_across_x <= 0 or holders_across_y <= 0:
            raise ValueError("holders_across_x and holders_across_y cannot be negative or 0")

        self.add_height = add_height
        self.remove_height = remove_height
        self._columns = holders_across_x
        self._rows = holders_across_y

        self.__individual_holders: dict[tuple[int, int], IndividualPipetteHolder] = {}
        self.individual_holder = individual_holder

        # Validate that individual holder fits
        if holders_across_x * individual_holder.size_x > size_x or holders_across_y * individual_holder.size_y > size_y:
            raise ValueError("Individual holder is too big for this PipetteHolder")
        else:
            self.place_individual_holders()

    def place_individual_holders(self):
        """Create individual holder positions across the grid."""
        for x in range(self._columns):
            for y in range(self._rows):
                holder = copy.deepcopy(self.individual_holder)
                holder.labware_id = f'{self.labware_id}_{x}:{y}'
                holder.column = x
                holder.row = y
                self.__individual_holders[(x, y)] = holder

    def get_individual_holders(self) -> dict[tuple[int, int], IndividualPipetteHolder]:
        """Get all individual holder positions."""
        return self.__individual_holders

    def get_available_holders(self) -> list[IndividualPipetteHolder]:
        """
        Get all available (unoccupied) holder positions.

        Returns
        -------
        list[IndividualPipetteHolder]
            List of available holders.
        """
        return [holder for holder in self.__individual_holders.values()
                if holder and holder.is_available()]

    def get_occupied_holders(self) -> list[IndividualPipetteHolder]:
        """
        Get all occupied holder positions.

        Returns
        -------
        list[IndividualPipetteHolder]
            List of occupied holders.
        """
        return [holder for holder in self.__individual_holders.values()
                if holder and holder.is_occupied]

    def get_holder_at(self, column: int, row: int) -> Optional[IndividualPipetteHolder]:
        """
        Get the individual holder at a specific position.

        Parameters
        ----------
        column : int
            Column index
        row : int
            Row index

        Returns
        -------
        Optional[IndividualPipetteHolder]
            The holder at the position, or None if not found
        """
        return self.__individual_holders.get((column, row))

    def place_pipette_at(self, column: int, row: int) -> None:
        """
        Place a pipette at a specific position.

        Parameters
        ----------
        column : int
            Column index (0-indexed).
        row : int
            Row index (0-indexed).

        Raises
        ------
        ValueError
            If position is out of range, no holder exists, or position is occupied.
        """

        self.validate_col_row_or_raise([column], row)
        individual_holder = self.get_holder_at(column, row)

        if individual_holder is None:
            raise ValueError(
                f"No individual holder found at position {column}:{row}"
            )
        individual_holder.place_pipette()

    def remove_pipette_at(self, column: int, row: int) -> None:
        """
        Remove a pipette from a specific position.

        Parameters
        ----------
        column : int
            Column index (0-indexed).
        row : int
            Row index (0-indexed).

        Raises
        ------
        ValueError
            If position is out of range, no holder exists, or position is empty.
        """

        self.validate_col_row_or_raise([column], row)
        individual_holder = self.get_holder_at(column, row)

        if individual_holder is None:
            raise ValueError(
                f"No individual holder found at position {column}:{row}"
            )

        individual_holder.remove_pipette()

    def place_consecutive_pipettes_multi(self, columns: list[int], row: int = 0) -> None:
        """
        Place pipettes in consecutive positions within specified columns for multichannel pipettor.

        Parameters
        ----------
        columns : list[int]
            List of column indices (0-indexed) where pipettes should be placed.
        row : int, optional
            Starting row index (0-indexed). Pipettes will be placed from row to row + 7.
            Default is 0.

        Raises
        ------
        ValueError
            If any column index is out of range, row out of range, or if any position
            in the specified columns is already occupied.
        """

        self.validate_col_row_or_raise(columns, row, Pipettors_in_Multi)

        # Check if all positions are available before placing
        for col in columns:
            for i in range(Pipettors_in_Multi):
                current_row = row + i
                individual_holder = self.get_holder_at(col, current_row)

                if individual_holder is None:
                    raise ValueError(
                        f"No individual holder found at position {col}:{current_row}"
                    )

                if individual_holder.is_occupied:
                    raise ValueError(
                        f"Holder at position {col}:{current_row} is already occupied"
                    )

        # Place pipettes in all positions
        for col in columns:
            for i in range(Pipettors_in_Multi):
                current_row = row + i
                individual_holder = self.get_holder_at(col, current_row)
                individual_holder.place_pipette()

    def remove_consecutive_pipettes_multi(self, columns: list[int], row: int = 0) -> None:
        """
        Remove pipettes from consecutive positions within specified columns for multichannel pipettor.

        Parameters
        ----------
        columns : list[int]
            List of column indices (0-indexed) where pipettes should be removed.
        row : int, optional
            Starting row index (0-indexed). Pipettes will be removed from row to row + 7.
            Default is 0.

        Raises
        ------
        ValueError
            If any column index is out of range, row out of range, or if any position
            in the specified columns is already empty.
        """

        self.validate_col_row_or_raise(columns, row, Pipettors_in_Multi)

        # Check if all positions have pipettes before removing
        for col in columns:
            for i in range(Pipettors_in_Multi):
                current_row = row + i
                individual_holder = self.get_holder_at(col, current_row)

                if individual_holder is None:
                    raise ValueError(
                        f"No individual holder found at position {col}:{current_row}"
                    )

                if not individual_holder.is_occupied:
                    raise ValueError(
                        f"Holder at position {col}:{current_row} is already empty"
                    )

        # Remove pipettes from all positions
        for col in columns:
            for i in range(Pipettors_in_Multi):
                current_row = row + i
                individual_holder = self.get_holder_at(col, current_row)
                individual_holder.remove_pipette()

    def check_col_start_row_multi(self, col: int, start_row: int) -> str:
        """
        Check the occupancy status of 8 consecutive positions starting from (col, start_row).

        Parameters
        ----------
        col : int
            Column index
        start_row : int
            Starting row index

        Returns
        -------
        str
            Status of the 8 consecutive positions:
            - "FULLY_OCCUPIED": All 8 positions exist and are occupied
            - "FULLY_AVAILABLE": All 8 positions exist and are empty
            - "MIXED": All 8 positions exist but have mixed occupancy
            - "INVALID": One or more positions don't exist (out of bounds)
        """
        # Check if all positions exist
        if col < 0 or col >= self._columns:
            return "INVALID"
        if start_row < 0 or start_row + Pipettors_in_Multi > self._rows:
            return "INVALID"

        # Check occupancy of all 8 positions
        occupied_count = 0
        for i in range(Pipettors_in_Multi):
            current_row = start_row + i
            individual_holder = self.get_holder_at(col, current_row)

            if individual_holder is None:
                return "INVALID"

            if individual_holder.is_occupied:
                occupied_count += 1

        # Determine status
        if occupied_count == Pipettors_in_Multi:
            return "FULLY_OCCUPIED"
        elif occupied_count == 0:
            return "FULLY_AVAILABLE"
        else:
            return "MIXED"

    def get_occupied_holder_multi(self) -> list[tuple[int, int]]:
        """
        Get all columns with starting rows where 8 consecutive occupied positions exist.
        No holder is reused - blocks are non-overlapping.
        """
        occupied_positions = []

        for col in range(self._columns):
            used_rows = set()

            for start_row in range(self._rows - Pipettors_in_Multi + 1):
                if start_row in used_rows:
                    continue

                # Use helper function instead of manual checking
                status = self.check_col_start_row_multi(col, start_row)

                if status == "FULLY_OCCUPIED":
                    occupied_positions.append((col, start_row))
                    # Mark all rows in this block as used
                    for i in range(Pipettors_in_Multi):
                        used_rows.add(start_row + i)

        return occupied_positions

    def get_available_holder_multi(self) -> list[tuple[int, int]]:
        """
        Get all columns with starting rows where 8 consecutive available positions exist.
        No holder is reused - blocks are non-overlapping.
        """
        available_positions = []

        for col in range(self._columns):
            used_rows = set()

            for start_row in range(self._rows - Pipettors_in_Multi + 1):
                if start_row in used_rows:
                    continue

                status = self.check_col_start_row_multi(col, start_row)

                if status == "FULLY_AVAILABLE":
                    available_positions.append((col, start_row))
                    for i in range(Pipettors_in_Multi):
                        used_rows.add(start_row + i)

        return available_positions

    def to_dict(self) -> dict:
        """
        Serialize the PipetteHolder instance to a dictionary.

        Returns
        -------
        dict
            Dictionary representation of the pipette holder.
        """
        base = super().to_dict()
        base.update({
            "add_height": self.add_height,
            "remove_height": self.remove_height,
            "holders_across_x": self.holders_across_x,
            "holders_across_y": self.holders_across_y,
            "individual_holders": {
            f"{col}:{row}": holder.to_dict()
            for (col, row), holder in self.__individual_holders.items()
        }
        })
        return base



    @classmethod
    def _from_dict(cls, data: dict) -> "PipetteHolder":
        """Deserialize a PipetteHolder instance from a dictionary."""
        position = tuple(data["position"]) if data.get("position") else None

        holders_data = data.get("individual_holders", {})

        if not holders_data:
            raise ValueError("Cannot deserialize PipetteHolder without individual_holders data")

        # Get the first holder as a template
        first_holder_data = next(iter(holders_data.values()))
        template_holder = Serializable.from_dict(first_holder_data)

        # Create the PipetteHolder with the template
        holder = cls(
            size_x=data["size_x"],
            size_y=data["size_y"],
            size_z=data["size_z"],
            can_be_stacked_upon = ["can_be_stacked_upon"],
            add_height=data["add_height"],
            remove_height=data["remove_height"],
            offset=data["offset"],
            labware_id=data["labware_id"],
            holders_across_x=data["holders_across_x"],
            holders_across_y=data["holders_across_y"],
            individual_holder=template_holder,
            position=position,
        )

        # Restore individual holders with tuple keys
        for hid, hdata in holders_data.items():
            # Parse "col:row" format from JSON
            col, row = map(int, hid.split(':'))
            restored_holder = Serializable.from_dict(hdata)
            holder._PipetteHolder__individual_holders[(col, row)] = restored_holder

        return holder
    @property
    def holders_across_x(self) -> int:
        """Alias for grid_x"""
        return self._columns

    @property
    def holders_across_y(self) -> int:
        """Alias for grid_y"""
        return self._rows

    @property
    def grid_x(self) -> int:
        """Standard grid dimension"""
        return self._columns

    @property
    def grid_y(self) -> int:
        """Standard grid dimension"""
        return self._rows

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

@register_class
class ReservoirHolder(Labware):
    def __init__(self, size_x: float, size_y: float, size_z: float, hooks_across_x: int, hooks_across_y: int, reservoir_template: Reservoir = None,
                remove_height: float = -45, add_height: float = 0, offset: tuple[float, float] = (0, 0),
                 labware_id: str = None, position: tuple[float, float] = None, can_be_stacked_upon: bool = False):
        """
        Initialize a ReservoirHolder instance that can hold multiple reservoirs.

        Parameters
        ----------
        size_x : float
            Width of the ReservoirHolder in millimeters.
        size_y : float
            Depth of the ReservoirHolder in millimeters.
        size_z : float
            Height of the ReservoirHolder in millimeters.
        hooks_across_x : int
            Number of hooks along X-axis.
        hooks_across_y : int
            Number of hooks along Y-axis (rows of hooks).
        add_height : float
            relative height at which liquid is dispensed
        remove_height: float
            relative height at which liquid is aspirated
        reservoir_template : reservoir
            example or individual reservoir that will be placed across all hooks.
        labware_id : str, optional
            Unique ID for the holder.
        position : tuple[float, float], optional
            (x, y) position coordinates of the ReservoirHolder in millimeters.
            If None, position is not set.
        """
        super().__init__(size_x, size_y, size_z, offset, labware_id, position, can_be_stacked_upon=can_be_stacked_upon)

        if hooks_across_x <= 0 or hooks_across_y <= 0:
            raise ValueError("hooks_across_x and hooks_across_y cannot be negative or 0")

        self.add_height = add_height
        self.remove_height = remove_height
        self._columns = hooks_across_x
        self._rows = hooks_across_y
        self.total_hooks = hooks_across_x * hooks_across_y

        # Initialize empty hooks - maps hook_id to reservoir (or None if empty)
        # hook_id ranges from 1 to total_hooks
        self.__hook_to_reservoir: dict[int, Optional[Reservoir]] = {
            i: None for i in range(1, self.total_hooks + 1)
        }

        # Place reservoirs to holder if provided
        if reservoir_template is not None:
            self.place_reservoirs(reservoir_template)

    def each_tip_needs_separate_item(self) -> bool:
        return False  # Reservoirs are large, all tips fit in one

    def hook_id_to_position(self, hook_id: int) -> tuple[int, int]:
        """
        Convert hook_id to (col, row) position.

        Parameters
        ----------
        hook_id : int
            Hook ID (1-indexed, 1 to total_hooks)

        Returns
        -------
        tuple[int, int]
            (col, row) where col is 0 to hooks_across_x-1, row is 0 to hooks_across_y-1

        Example
        -------
        For hooks_across_x=3, hooks_across_y=2:
        hook_id: 1 2 3 4 5 6
        layout: [1 2 3]  <- row 0
                [4 5 6]  <- row 1
        """
        if hook_id < 1 or hook_id > self.total_hooks:
            raise ValueError(f"hook_id {hook_id} out of range (1 to {self.total_hooks})")

        # Convert to 0-indexed
        idx = hook_id - 1
        row = idx // self._columns
        col = idx % self._columns
        return col, row

    def position_to_hook_id(self, col: int, row: int) -> int:
        """
        Convert (col, row) position to hook_id.

        Parameters
        ----------
        col : int
            Column (0 to hooks_across_x-1)
        row : int
            Row (0 to hooks_across_y-1)

        Returns
        -------
        int
            hook_id (1-indexed)
        """
        if col < 0 or col >= self._columns:
            raise ValueError(f"col {col} out of range (0 to {self._columns - 1})")
        if row < 0 or row >= self._rows:
            raise ValueError(f"row {row} out of range (0 to {self._rows - 1})")

        return row * self._columns + col + 1

#todo fix it
    def get_reservoirs(self) -> list[Reservoir]:
        """Return list of all unique reservoirs (no duplicates)."""
        seen_ids = set()
        reservoirs = []
        for res in self.__hook_to_reservoir.values():
            if res is not None and res.labware_id not in seen_ids:
                seen_ids.add(res.labware_id)
                reservoirs.append(res)
        return reservoirs

    def get_hook_to_reservoir_map(self) -> dict[int, Optional[Reservoir]]:
        """Return the complete hook to reservoir mapping."""
        return self.__hook_to_reservoir

    def get_available_hooks(self) -> list[int]:
        """Return list of available (empty) hook IDs."""
        return [hook_id for hook_id, res in self.__hook_to_reservoir.items() if res is None]

    def get_occupied_hooks(self) -> list[int]:
        """Return list of occupied hook IDs."""
        return [hook_id for hook_id, res in self.__hook_to_reservoir.items() if res is not None]

    def _validate_hooks_form_rectangle(self, hook_ids: list[int]) -> tuple[bool, int, int]:
        """
        Check if hook IDs form a rectangular grid.

        Returns
        -------
        tuple[bool, int, int]
            (is_valid, width, height) where width and height are in hook units
        """
        if not hook_ids:
            return False, 0, 0

        # Convert all hook_ids to (col, row) location
        location = [self.hook_id_to_position(hid) for hid in hook_ids]
        cols = [pos[0] for pos in location]
        rows = [pos[1] for pos in location]

        min_col, max_col = min(cols), max(cols)
        min_row, max_row = min(rows), max(rows)

        width = max_col - min_col + 1
        height = max_row - min_row + 1

        # Check if all location in the rectangle are present
        expected_location = {
            (c, r) for c in range(min_col, max_col + 1)
            for r in range(min_row, max_row + 1)
        }
        actual_location = set(location)

        is_valid = expected_location == actual_location
        return is_valid, width, height

    def place_reservoir(self, hook_ids: list[int], reservoir: Reservoir) -> None:
        """
        Place a single reservoir on specific hooks.

        Parameters
        ----------
        hook_ids : list[int] or int
            List of hook location to place the reservoir (must form a rectangle).
        reservoir : Reservoir
            Reservoir instance to place.

        Raises
        ------
        ValueError
            If hook_ids are invalid, don't form a rectangle, already occupied,
            or reservoir dimensions incompatible.
        """
        # Allow single int for backwards compatibility
        if isinstance(hook_ids, int):
            hook_ids = [hook_ids]

        if not hook_ids:
            raise ValueError("Must specify at least one hook_id")


        # Check if all hook_ids are valid and available
        for hook_id in hook_ids:

            if hook_id not in self.__hook_to_reservoir:
                raise ValueError(
                    f"Hook ID {hook_id} is invalid. Must be between 1 and {self.total_hooks}"
                )

            if self.__hook_to_reservoir[hook_id] is not None:
                raise ValueError(f"Hook {hook_id} is already occupied")

        # Check if hooks form a valid rectangle
        is_valid, width_hooks, height_hooks = self._validate_hooks_form_rectangle(hook_ids)
        if not is_valid:
            raise ValueError(
                f"Hook IDs {hook_ids} must form a rectangular grid"
            )

        # Calculate maximum dimensions per hook
        max_width_per_hook = self.size_x / self._columns
        max_height_per_hook = self.size_y / self._rows

        # Calculate available space for this reservoir
        max_width_for_reservoir = max_width_per_hook * width_hooks
        max_height_for_reservoir = max_height_per_hook * height_hooks

        # Check dimensional compatibility
        if reservoir.size_x > max_width_for_reservoir:
            raise ValueError(
                f"Reservoir width ({reservoir.size_x} mm) exceeds "
                f"available width ({max_width_for_reservoir:.2f} mm = "
                f"{max_width_per_hook:.2f} mm/hook × {width_hooks} hooks)"
            )
        if reservoir.size_y > max_height_for_reservoir:
            raise ValueError(
                f"Reservoir depth ({reservoir.size_y} mm) exceeds "
                f"available depth ({max_height_for_reservoir:.2f} mm = "
                f"{max_height_per_hook:.2f} mm/hook × {height_hooks} hooks)"
            )
        if reservoir.size_z > self.size_z:
            raise ValueError(
                f"Reservoir height ({reservoir.size_z} mm) exceeds "
                f"holder height ({self.size_z} mm)"
            )

        is_valid, error_msg = self.validate_multichannel_compatible(reservoir.size_y)
        if not is_valid:
            raise ValueError(error_msg)

        # Assign hook_ids and place reservoir. also find col and row
        reservoir.hook_ids = hook_ids
        positions = [self.hook_id_to_position(hid) for hid in hook_ids]
        cols = [pos[0] for pos in positions]
        rows = [pos[1] for pos in positions]
        reservoir.column = min(cols)  # Leftmost column
        reservoir.row = min(rows)  # Topmost row

        reservoir.labware_id = f"{self.labware_id}_{reservoir.column}:{reservoir.row}"

        for hook_id in hook_ids:
            self.__hook_to_reservoir[hook_id] = reservoir

    def place_reservoirs(self, reservoir_template: Reservoir) -> None:
        """
        allocate duplicate reservoir to all available hooks, unless specific hook id specified

            If hook_ids is specified, the reservoir will be placed there, given that position is empty
            Otherwise, calculates required hooks based on dimensions and allocates automatically.

        Raises
        ------
        ValueError
            If a specified hook_id is occupied, insufficient space, or
            reservoir parameters are invalid.
        """
        template = reservoir_template
        if template.hook_ids:
            hook_ids_to_use = template.hook_ids
            reservoir_copy = copy.deepcopy(template)
            self.place_reservoir(hook_ids_to_use, reservoir_copy)

        else:

            max_width_per_hook = self.size_x / self._columns
            max_height_per_hook = self.size_y / self._rows

            reservoir_width = template.size_x
            reservoir_height = template.size_y

            # Calculate minimum hooks needed based on dimensions
            min_hooks_x = int(reservoir_width / max_width_per_hook)
            if reservoir_width % max_width_per_hook > 0: min_hooks_x += 1

            min_hooks_y = int(reservoir_height / max_height_per_hook)
            if reservoir_height % max_height_per_hook > 0: min_hooks_y += 1

            hooks_x = min_hooks_x
            hooks_y = min_hooks_y

            # raises error if not even one placement is possible.
            if hooks_x > self._columns or hooks_y > self._rows:
                raise ValueError(
                    f"Placement Error: Required reservoir size is {hooks_x}x{hooks_y} hooks, "
                    f"but the ReservoirHolder is only {self._columns}x{self._rows}."
                )

            while True:
                hook_ids_to_use = None

                # Re-check available hooks for each placement attempt
                available = set(self.get_available_hooks())

                # Find the *first* available rectangular region of size hooks_x x hooks_y
                for start_row in range(self._rows - hooks_y + 1):
                    for start_col in range(self._columns - hooks_x + 1):

                        # Check if this rectangular block (starting at start_row, start_col)
                        # is entirely available (not occupied)
                        candidate_hooks = []
                        is_available = True

                        for r in range(start_row, start_row + hooks_y):
                            for c in range(start_col, start_col + hooks_x):
                                hook_id = self.position_to_hook_id(c, r)
                                if hook_id not in available:
                                    is_available = False
                                    break
                                candidate_hooks.append(hook_id)
                            if not is_available:
                                break

                        if is_available:
                            hook_ids_to_use = candidate_hooks
                            break
                    if hook_ids_to_use:
                        break

                # If we couldn't find a spot, we exit the loop
                if hook_ids_to_use is None:
                    break

                # --- Placement Execution for the Found Spot ---
                reservoir_copy = copy.deepcopy(template)
                self.place_reservoir(hook_ids_to_use, reservoir_copy)

    def remove_reservoir(self, hook_id: int) -> Reservoir:
        """
        Remove a reservoir from the holder.

        Parameters
        ----------
        hook_id : int
            Any hook ID occupied by the reservoir to remove

        Returns
        -------
        Reservoir
            The removed reservoir

        Raises
        ------
        ValueError
            If no reservoir at the specified hook
        """
        if hook_id not in self.__hook_to_reservoir:
            raise ValueError(f"Invalid hook_id {hook_id}")

        reservoir = self.__hook_to_reservoir[hook_id]
        if reservoir is None:
            raise ValueError(f"No reservoir at hook {hook_id}")

        # Clear all hooks occupied by this reservoir
        for hid in reservoir.hook_ids:
            self.__hook_to_reservoir[hid] = None

        return reservoir

    def add_content(self, hook_id: int, content: str, volume: float) -> None:
        """
        Add content to a reservoir at a specific hook.

        Parameters
        ----------
        hook_id : int
            Hook ID where the reservoir is located
        content : str
            Type of content to add (e.g., "PBS", "water")
        volume : float
            Volume to add (µL)

        Raises
        ------
        ValueError
            If no reservoir at hook or volume exceeds capacity
        """
        if hook_id not in self.__hook_to_reservoir or self.__hook_to_reservoir[hook_id] is None:
            raise ValueError(f"No reservoir at hook {hook_id}")
        self.__hook_to_reservoir[hook_id].add_content(content, volume)

    def remove_content(self, hook_id: int, volume: float, return_dict: bool = False) -> Optional[dict[str, float]]:
        """
        Remove content from a reservoir at a specific hook.

        Parameters
        ----------
        hook_id : int
            Hook ID where the reservoir is located
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
            If no reservoir at hook or insufficient volume
        """
        if hook_id not in self.__hook_to_reservoir or self.__hook_to_reservoir[hook_id] is None:
            raise ValueError(f"No reservoir at hook {hook_id}")
        return self.__hook_to_reservoir[hook_id].remove_content(volume, return_dict=return_dict)

    def get_waste_reservoirs(self) -> list[Reservoir]:
        """
        Get all unique reservoirs that contain 'waste' in any content type.

        Returns
        -------
        list[Reservoir]
            List of waste reservoirs
        """
        return [
            res for res in self.get_reservoirs()
            if any("waste" in content_type.lower() for content_type in res.content.keys())
        ]

    def get_reservoirs_by_content_type(self, content_type: str) -> list[Reservoir]:
        """
        Get all unique reservoirs that contain a specific content type.

        Parameters
        ----------
        content_type : str
            Content type to search for (case-insensitive)

        Returns
        -------
        list[Reservoir]
            List of reservoirs containing this content type
        """
        return [
            res for res in self.get_reservoirs()
            if res.has_content_type(content_type)
        ]

    def to_dict(self) -> dict:
        """Serialize the ReservoirHolder instance to a dictionary."""
        base = super().to_dict()

        # Store only unique reservoirs with their hook_ids
        unique_reservoirs = {}
        for res in self.get_reservoirs():
            key = f"{res.column}:{res.row}"  # ✅ Consistent with Plate/PipetteHolder
            unique_reservoirs[key] = res.to_dict()

        base.update({
            "add_height": self.add_height,
            "remove_height": self.remove_height,
            "hooks_across_x": self.hooks_across_x,
            "hooks_across_y": self.hooks_across_y,
            "reservoirs": unique_reservoirs,
        })
        return base

    @classmethod
    def _from_dict(cls, data: dict) -> "ReservoirHolder":
        """Deserialize a ReservoirHolder instance from a dictionary."""
        # Safely handle position deserialization
        position = tuple(data["position"]) if data.get("position") else None

        reservoir_holder = cls(
            size_x=data["size_x"],
            size_y=data["size_y"],
            size_z=data["size_z"],
            can_be_stacked_upon=data.get("can_be_stacked_upon", False),
            add_height = data["add_height"],
            remove_height = data["remove_height"],
            offset=data["offset"],
            hooks_across_x=data["hooks_across_x"],
            hooks_across_y=data.get("hooks_across_y", 1),  # Default to 1 for backwards compatibility
            labware_id=data["labware_id"],
            reservoir_template=None,
            position=position,
        )

        # Restore reservoirs
        reservoirs_data = data.get("reservoirs", {})
        for res_data in reservoirs_data.values():
            reservoir = Serializable.from_dict(res_data)
            # Place on the hooks specified in hook_ids
            if reservoir.hook_ids:
                reservoir_holder.place_reservoir(reservoir.hook_ids, reservoir)

        return reservoir_holder

    @property
    def hooks_across_x(self) -> int:
        return self._columns

    @property
    def hooks_across_y(self) -> int:
        return self._rows

    @property
    def grid_x(self) -> int:
        return self._columns

    @property
    def grid_y(self) -> int:
        return self._rows

@register_class
class TipDropzone(Labware):
    """
    Represents a Tip Dropzone labware with relative drop position and height.

    Attributes
    ----------
    drop_height_relative : float
        Drop height relative to the labware height.
    """

    def __init__(self, size_x: float,
                 size_y: float,
                 size_z: float,
                 can_be_stacked_upon: bool = False,
                 offset: tuple[float, float] = (0, 0),
                 drop_height_relative: float = 20,
                 position: tuple[float, float] = None,
                 labware_id: str = None
                 ):
        """
        Initialize a TipDropzone instance.

        Parameters
        ----------
        size_x : float
            Width of the drop zone in millimeters.
        size_y : float
            Depth of the drop zone in millimeters.
        size_z : float
            Height of the drop zone in millimeters.
        labware_id : str, optional
            Unique ID for the dropzone object.
        position : tuple[float, float], optional
            (x, y) position coordinates of the tip dropzone in millimeters.
            If None, position is not set.
        drop_height_relative : float, optional
            Height from which tips are dropped relative to the labware. Default is 20.
        """
        super().__init__(size_x=size_x, size_y=size_y, size_z=size_z, offset=offset, labware_id=labware_id,
                         position=position, can_be_stacked_upon=can_be_stacked_upon)
        self.drop_height_relative = drop_height_relative

    def to_dict(self) -> dict:
        """
        Serialize the TipDropzone instance to a dictionary, extending the base Labware fields.

        Returns
        -------
        dict
            dictionary representation of the tip dropzone.
        """
        base_dict = super().to_dict()
        base_dict.update({
            "drop_height_relative": self.drop_height_relative,
        })
        return base_dict

    @classmethod
    def _from_dict(cls, data: dict) -> "TipDropzone":
        """
        Deserialize a TipDropzone instance from a dictionary using the base Labware _from_dict.

        Parameters
        ----------
        data : dict
            dictionary containing tip dropzone attributes.

        Returns
        -------
        TipDropzone
            Reconstructed TipDropzone instance.
        """
        # Safely handle position deserialization
        # Safely handle position deserialization
        position = tuple(data["position"]) if data.get("position") else None

        return cls(
            size_x=data["size_x"],
            size_y=data["size_y"],
            size_z=data["size_z"],
            offset=data["offset"],
            can_be_stacked_upon=data.get("can_be_stacked_upon", False),
            position=position,
            drop_height_relative=data["drop_height_relative"],
            labware_id=data["labware_id"]
        )

