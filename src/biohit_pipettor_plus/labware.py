import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import uuid
from .serializable import Serializable, register_class
import copy
from typing import Optional

Pipettors_in_Multi = 8

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

    def __init__(self, size_x: float, size_y: float, size_z: float, offset= tuple[float, float], labware_id: str = None, position: tuple[float, float] = None):
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
        self.offset = offset or (0,0)
        self.position = position or None
        self.labware_id = labware_id or f"labware_{uuid.uuid4().hex}"


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
    media : str or None
        Optional description of the media (e.g. "water", "buffer").
    add_height : float
        Height above the well bottom used when adding liquid (in mm).
    remove_height : float
        Height above the well bottom used when removing liquid (in mm).
    suck_offset_xy : tuple[float, float]
        XY offset inside the well for pipetting (in mm).
    """

    def __init__(
        self,
        size_x: float,
        size_y: float,
        size_z: float,
        offset: tuple[float, float] = (0,0),
        position: tuple[float, float] = None,
        labware_id: str = None,
        row: int = None,
        column: int = None,
        media: str = None,
        add_height: float = 5,
        remove_height: float = 5,
        suck_offset_xy: tuple[float, float] = (2, 2),
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
            If None, position is not set.
        media : str, optional
            Name/type of media contained in the well.
        add_height : float, optional
            Pipette dispensing height above bottom of the well (default = 5 mm).
        remove_height : float, optional
            Pipette aspiration height above bottom of the well (default = 5 mm).
        suck_offset_xy : tuple[float, float], optional
            XY offset from the well corner for aspiration/dispense (default = (2, 2)).
        """
        super().__init__(size_x=size_x, size_y=size_y, size_z=size_z, offset = offset, labware_id=labware_id, position=position)
        self.media = media
        self.add_height = add_height
        self.remove_height = remove_height
        self.suck_offset_xy = suck_offset_xy
        self.row = row
        self.column = column

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
                "media": self.media,
                "add_height": self.add_height,
                "remove_height": self.remove_height,
                "suck_offset_xy": list(self.suck_offset_xy),
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
        Well
            Reconstructed Well instance.
        """

        # Safely handle position deserialization
        position = tuple(data["position"]) if data.get("position") else None

        base_obj = super()._from_dict(data)  # Labware attributes

        # overwrite base_obj with correct class instantiation
        obj = cls(
            size_x=base_obj.size_x,
            size_y=base_obj.size_y,
            size_z=base_obj.size_z,
            offset =base_obj.offset,
            labware_id=base_obj.labware_id,
            position=base_obj.position,
            media=data.get("media"),
            add_height=data.get("add_height", 5),
            remove_height=data.get("remove_height", 5),
            suck_offset_xy=tuple(data.get("suck_offset_xy", (2, 2))),
            row=data.get("row"),
            column=data.get("column")
        )
        return obj


@register_class
class Plate(Labware):
    """
    Represents a Plate labware with wells.
    Attributes
    ----------
    wells_x : int
        Number of wells in X direction.
    wells_y : int
        Number of wells in Y direction.
    """

# TODO for plate, isn't offset and first well part of same equation. or is offset only till corners of the plate (if yes, what is the purpose to go to corner of any labware.
    def __init__(self, size_x, size_y, size_z, wells_x, wells_y, offset = (0,0), well: Well = None,
                 labware_id: str = None, position: tuple[float, float] = None):
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
        labware_id : str, optional
            Unique ID for the plate.
        """

        super().__init__(size_x, size_y, size_z, offset, labware_id, position)

        if wells_x <= 0 or wells_y <= 0:
            raise ValueError("wells_x and wells_y cannot be negative or 0")

        self._columns = wells_x  # Store internally
        self._rows = wells_y

        self.__wells: dict[str, Well or None] = {}
        self.well = well

        if well:
            if self._columns * well.size_x > size_x or self._rows * well.size_y > size_y:
                raise ValueError("Well is to big for this Plate")
            else:
                self.place_wells()
        else:
            for x in range(self._columns):
                for y in range(self._rows):
                    self.__wells[f'{x}:{y}'] = None

    def get_wells(self):
        return self.__wells

    def place_wells(self):
        for x in range(self._columns):
            for y in range(self._rows):
                well = copy.deepcopy(self.well)  # Create a new copy
                well.labware_id = f'well_{x}:{y}'
                self.__wells[well.labware_id] = well

    # TODO question existence   
    def place_unique_well(self, row, column, well: Well):
        well_placement = f"{column}:{row}"
        if well_placement not in self.__wells.keys():
            raise ValueError(f"{well_placement} is not a valid well placement")

        well.labware_id = well_placement
        well.row = row
        well.column = column
        self.__wells[well.labware_id] = well

    def to_dict(self):
        """
        Serialize the Plate instance to a dictionary including wells information.

        Returns
        -------
        dict
            dictionary representation of the plate.
        """
        base = super().to_dict()
        base.update({
            "wells_x": self.wells_x,
            "wells_y": self.wells_y,
            "wells": {wid: well.to_dict() if well else None for wid, well in self.__wells.items()}
        })
        return base

    @classmethod
    def _from_dict(cls, data: dict) -> "Plate":
        """
        Deserialize a Plate instance from a dictionary using the base Labware _from_dict.

        Parameters
        ----------
        data : dict
            dictionary containing plate attributes.

        Returns
        -------
        Plate
            Reconstructed Plate instance.
        """
        # Safely handle position deserialization
        position = tuple(data["position"]) if data.get("position") else None

        plate = cls(
            size_x=data["size_x"],
            size_y=data["size_y"],
            size_z=data["size_z"],
            offset=data["offset"],
            labware_id=data["labware_id"],
            wells_x=data["wells_x"],
            wells_y=data["wells_y"],
            position=position,)

        wells_data = data.get("wells", {})
        for wid, wdata in wells_data.items():
            if wdata is None:
                plate._Plate__wells[wid] = None
            else:
                plate._Plate__wells[wid] = Serializable.from_dict(wdata)
        return plate


    @property
    def wells_x(self) -> int:
        """Alias for grid_x"""
        return self._columns

    @property
    def wells_y(self) -> int:
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
class IndividualPipetteHolder(Labware):
    """
    Represents an individual pipette holder position within a PipetteHolder.
    Tracks occupancy status and pipette type.

    Attributes
    ----------
    is_occupied : bool
        Whether this holder position currently contains a pipette.
    pipette_type : str or None
        Type/model of pipette that can be stored here (e.g., "P1000", "P200").
    """

    def __init__(
            self,
            size_x: float,
            size_y: float,
            size_z: float,
            offset: tuple[float, float] = (0,0),
            pipette_type: str = "P1000",
            is_occupied: bool = False,
            labware_id: str = None,
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
        pipette_type : str, optional
            Type of pipette this holder is designed for (e.g., "P1000", "P200").
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
            position=position
        )

        self.pipette_type = pipette_type
        self.is_occupied = is_occupied

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
            "pipette_type": self.pipette_type,
            "is_occupied": self.is_occupied,
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
            position=position,
            pipette_type=data.get("pipette_type"),
            is_occupied=data.get("is_occupied", False),
        )


@register_class
class PipetteHolder(Labware):
    """
    Represents a Pipette Holder labware that contains multiple individual holder positions.

    Attributes
    ----------
    holders_across_x : int
        Number of individual holder positions across X-axis.
    holders_across_y : int
        Number of individual holder positions across Y-axis.
    """

    def __init__(self,
                 size_x: float,
                 size_y: float,
                 size_z: float,
                 holders_across_x: int,
                 holders_across_y: int,
                 offset: float = (0, 0),
                 individual_holder: IndividualPipetteHolder = None,
                 labware_id: str = None,
                 position: tuple[float, float] = None):
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
        individual_holder : IndividualPipetteHolder, optional
            Template for individual holder positions. If provided, copies will be created
            for each position in the grid.
        labware_id : str, optional
            Unique ID for the pipette holder.
        position : tuple[float, float], optional
            (x, y) position coordinates of the pipette holder in millimeters.
            If None, position is not set.
        """
        super().__init__(size_x=size_x, size_y=size_y, size_z=size_z, offset=offset, labware_id=labware_id, position=position)

        if holders_across_x <= 0 or holders_across_y <= 0:
            raise ValueError("wells_x and wells_y cannot be negative or 0")

        self._columns = holders_across_x
        self._rows = holders_across_y

        self.__individual_holders: dict[str, IndividualPipetteHolder] = {}
        self.individual_holder = individual_holder

        if holders_across_y < Pipettors_in_Multi:
            raise ValueError(f"PipetteHolder should atleast contatin{Pipettors_in_Multi} rows")

        if individual_holder:
            # Validate that individual holder fits
            if holders_across_x * individual_holder.size_x > size_x or holders_across_y * individual_holder.size_y > size_y:
                raise ValueError("Individual holder is too big for this PipetteHolder")
            else:
                self.place_individual_holders()
        else:
            # Create empty positions
            for x in range(self._columns):
                for y in range(self._rows):
                    self.__individual_holders[f'{x}:{y}'] = None

    def place_individual_holders(self):
        """Create individual holder positions across the grid."""
        for x in range(self._columns):
            for y in range(self._rows):
                holder = copy.deepcopy(self.individual_holder)
                holder.labware_id = f'holder_{x}:{y}'
                self.__individual_holders[holder.labware_id] = holder

    def get_individual_holders(self) -> dict[str, IndividualPipetteHolder]:
        """
        Get all individual holder positions.
        Returns dict[str, IndividualPipetteHolder]
            Dictionary mapping position IDs to IndividualPipetteHolder instances.
        """
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

    def place_pipettes_in_columns(self, columns: list[int]) -> None:
        """
        Place pipettes in all positions within specified columns.

        Parameters
        ----------
        columns : list[int]
            List of column indices (0-indexed) where pipettes should be placed.

        Raises
        ------
        ValueError
            If any column index is out of range or if any position in the
            specified columns is already occupied.
        """
        # Validate column indices
        for col in columns:
            if col < 0 or col >= self._columns:
                raise ValueError(
                    f"Column index {col} is out of range. "
                    f"Valid range is 0 to {self._columns - 1}"
                )

        # Check if all positions are available before placing
        for col in columns:
            for row in range(self._rows):
                holder_id = f'holder_{col}:{row}'
                individual_holder = self.__individual_holders.get(holder_id)

                if individual_holder is None:
                    raise ValueError(
                        f"No individual holder found at position {col}:{row}"
                    )

                if individual_holder.is_occupied:
                    raise ValueError(
                        f"Holder at position {col}:{row} is already occupied"
                    )

        # Place pipettes in all positions
        for col in columns:
            for row in range(self._rows):
                holder_id = f'holder_{col}:{row}'
                self.__individual_holders[holder_id].place_pipette()

    def remove_pipettes_from_columns(self, columns: list[int]) -> None:
        """
        Remove pipettes from all positions within specified columns.

        Parameters
        ----------
        columns : list[int]
            List of column indices (0-indexed) where pipettes should be removed.

        Raises
        ------
        ValueError
            If any column index is out of range or if any position in the
            specified columns is already empty.
        """
        # Validate column indices
        for col in columns:
            if col < 0 or col >= self._columns:
                raise ValueError(
                    f"Column index {col} is out of range. "
                    f"Valid range is 0 to {self._columns - 1}"
                )

        # Check if all positions have pipettes before removing
        for col in columns:
            for row in range(self._rows):
                holder_id = f'holder_{col}:{row}'
                individual_holder = self.__individual_holders.get(holder_id)

                if individual_holder is None:
                    raise ValueError(
                        f"No individual holder found at position {col}:{row}"
                    )

                if not individual_holder.is_occupied:
                    raise ValueError(
                        f"Holder at position {col}:{row} is already empty"
                    )

        # Remove pipettes from all positions
        for col in columns:
            for row in range(self._rows):
                holder_id = f'holder_{col}:{row}'
                self.__individual_holders[holder_id].remove_pipette()

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
        if column < 0 or column >= self._columns:
            raise ValueError(
                f"Column index {column} is out of range. "
                f"Valid range is 0 to {self._columns - 1}"
            )

        if row < 0 or row >= self._rows:
            raise ValueError(
                f"Row index {row} is out of range. "
                f"Valid range is 0 to {self._rows - 1}"
            )

        holder_id = f'holder_{column}:{row}'
        individual_holder = self.__individual_holders.get(holder_id)

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
        if column < 0 or column >= self._columns:
            raise ValueError(
                f"Column index {column} is out of range. "
                f"Valid range is 0 to {self._columns - 1}"
            )

        if row < 0 or row >= self._rows:
            raise ValueError(
                f"Row index {row} is out of range. "
                f"Valid range is 0 to {self._rows - 1}"
            )

        holder_id = f'holder_{column}:{row}'
        individual_holder = self.__individual_holders.get(holder_id)

        if individual_holder is None:
            raise ValueError(
                f"No individual holder found at position {column}:{row}"
            )

        individual_holder.remove_pipette()

    def get_available_columns(self) -> list[int]:
        """
        Get all columns that have at least one available (unoccupied) holder position.

        Returns
        -------
        list[int]
            List of column indices that have available positions.
        """
        available_cols = set()

        for col in range(self._columns):
            for row in range(self._rows):
                holder_id = f'holder_{col}:{row}'
                individual_holder = self.__individual_holders.get(holder_id)

                if individual_holder and individual_holder.is_available():
                    available_cols.add(col)
                    break  # Found at least one available in this column

        return sorted(list(available_cols))

    def get_occupied_columns(self) -> list[int]:
        """
        Get all columns that have at least one occupied holder position.

        Returns
        -------
        list[int]
            List of column indices that have occupied positions.
        """
        occupied_cols = set()

        for col in range(self._columns):
            for row in range(self._rows):
                holder_id = f'holder_{col}:{row}'
                individual_holder = self.__individual_holders.get(holder_id)

                if individual_holder and individual_holder.is_occupied:
                    occupied_cols.add(col)
                    break  # Found at least one occupied in this column

        return sorted(list(occupied_cols))

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
            "holders_across_x": self.holders_across_x,
            "holders_across_y": self.holders_across_y,
            "individual_holders": {
                hid: holder.to_dict() if holder else None
                for hid, holder in self.__individual_holders.items()
            }
        })
        return base

    @classmethod
    def _from_dict(cls, data: dict) -> "PipetteHolder":
        """
        Deserialize a PipetteHolder instance from a dictionary.

        Parameters
        ----------
        data : dict
            Dictionary containing pipette holder attributes.

        Returns
        -------
        PipetteHolder
            Reconstructed PipetteHolder instance.
        """
        # Safely handle position deserialization
        position = tuple(data["position"]) if data.get("position") else None

        holder = cls(
            size_x=data["size_x"],
            size_y=data["size_y"],
            size_z=data["size_z"],
            offset=data["offset"],
            labware_id=data["labware_id"],
            holders_across_x=data["holders_across_x"],
            holders_across_y=data["holders_across_y"],
            position=position,
        )

        # Restore individual holders
        holders_data = data.get("individual_holders", {})
        for hid, hdata in holders_data.items():
            if hdata is None:
                holder._PipetteHolder__individual_holders[hid] = None
            else:
                holder._PipetteHolder__individual_holders[hid] = Serializable.from_dict(hdata)

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

#TODO question existence
@register_class
class TipDropzone(Labware):
    """
    Represents a Tip Dropzone labware with relative drop position and height.

    Attributes
    ----------
    drop_x : float
        X position (absolute in Labware, relative in Slot).
    drop_y : float
        Y position (absolute in Labware, relative in Slot).
    drop_height_relative : float
        Drop height relative to the labware height.
    """

    def __init__(self, size_x: float,
                 size_y: float,
                 size_z: float,
                 drop_x: float,
                 drop_y: float,
                 offset: tuple[float,float] = (0, 0),
                 labware_id: str = None,
                 position: tuple[float, float] = None,
                 drop_height_relative: float = 20
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
        drop_x : float
            X position (absolute in Labware, relative in Slot).
        drop_y : float
            Y position (absolute in Labware, relative in Slot).
        labware_id : str, optional
            Unique ID for the dropzone object.
        position : tuple[float, float], optional
            (x, y) position coordinates of the tip dropzone in millimeters.
            If None, position is not set.
        drop_height_relative : float, optional
            Height from which tips are dropped relative to the labware. Default is 20.
        """
        super().__init__(size_x=size_x, size_y=size_y, size_z=size_z, offset=offset, labware_id=labware_id, position=position)
        self.drop_x = drop_x
        self.drop_y = drop_y
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
            "drop_x": self.drop_x,
            "drop_y": self.drop_y,
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
            labware_id=data["labware_id"],
            drop_x=data["drop_x"],
            drop_y=data["drop_y"],
            drop_height_relative=data["drop_height_relative"],
            position=position
        )


Default_Reservoir_Capacity = 30000


@register_class
class Reservoir(Labware):
    def __init__(self, size_x: float, size_y: float, size_z: float, offset: tuple[float,float] = (0, 0),
                 capacity: float = Default_Reservoir_Capacity, filled_volume: float = None,
                 content: str = None, hook_ids: list[int] = None, labware_id: str = None,
                 position: tuple[float, float] = None):
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
        filled_volume : float, optional
            Initial volume at the time of defining the reservoir. Default is 0 for waste and capacity for rest.
        content : str, optional
            Description of the reservoir content.
        hook_ids : list[int], optional
            List of hook locations on ReservoirHolder where this reservoir is going to be placed.
        labware_id : str, optional
            Unique ID for the reservoir.
        position : tuple[float, float], optional
            (x, y) position coordinates of the reservoir in millimeters.
            If None, position is not set.
        """
        super().__init__(size_x, size_y, size_z, offset, labware_id, position)
        self.capacity = capacity
        self.filled_volume = filled_volume
        self.hook_ids = hook_ids if hook_ids is not None else []

        # Default filled_volume logic: capacity for non-waste, 0 for waste
        if filled_volume is None:
            if content and "waste" in content.lower():
                filled_volume = 0
            else:
                filled_volume = capacity

        self.current_volume = filled_volume
        self.content = content

        # Validate inputs
        if self.current_volume > self.capacity:
            raise ValueError(f"Filled volume ({self.current_volume}) cannot exceed capacity ({self.capacity})")
        if self.current_volume < 0:
            raise ValueError("Filled volume cannot be negative")
        if self.capacity < 0:
            raise ValueError("Capacity cannot be negative")

    def add_volume(self, volume: float) -> None:
        """
        Add volume to the reservoir.
        Volume to add in µL.
        ValueError if adding volume would exceed capacity.
        """
        if volume < 0:
            raise ValueError("Volume to add must be positive")
        if self.current_volume + volume > self.capacity:
            raise ValueError(f"Overflow! Capacity: {self.capacity} µl")
        self.current_volume += volume

    def remove_volume(self, volume: float) -> None:
        """
        Removes volume from the reservoir.
        Volume to remove in µL.
        ValueError if remove volume exceed current volume.
        """
        if volume < 0:
            raise ValueError("Volume to remove must be positive")
        if self.current_volume < volume:
            raise ValueError(f"Underflow! Available: {self.current_volume} µl")
        self.current_volume -= volume

    def get_available_volume(self) -> float:
        """Return the current available volume in µL."""
        return self.current_volume

    def to_dict(self) -> dict:
        """Serialize the Reservoir to a dictionary."""
        base = super().to_dict()
        base.update({
            "hook_ids": self.hook_ids,
            "capacity": self.capacity,
            "filled_volume": self.current_volume,
            "content": self.content,
        })
        return base

    @classmethod
    def _from_dict(cls, data: dict) -> "Reservoir":
        """Deserialize a Reservoir instance from a dictionary."""

        # Safely handle position deserialization
        position = None

        if data.get("position") is not None:
            position = tuple(data["position"])

        return cls(
            size_x=data["size_x"],
            size_y=data["size_y"],
            size_z=data["size_z"],
            offset=data["offset"],
            labware_id=data["labware_id"],
            hook_ids=data.get("hook_ids", []),
            capacity=data.get("capacity", Default_Reservoir_Capacity),
            filled_volume=data.get("filled_volume"),
            content=data.get("content"),
            position=position,
        )

@register_class
class ReservoirHolder(Labware):
    def __init__(self, size_x: float, size_y: float, size_z: float, hooks_across_x: int, hooks_across_y: int,
                offset: tuple[float,float] = (0, 0), reservoir_dict: dict[int, dict] = None,
                 labware_id: str = None, position: tuple[float, float] = None):
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
        reservoir_dict : dict[int, dict], optional
            Dictionary defining individual reservoirs and their attributes.
        labware_id : str, optional
            Unique ID for the holder.
        position : tuple[float, float], optional
            (x, y) position coordinates of the ReservoirHolder in millimeters.
            If None, position is not set.
        """
        super().__init__(size_x, size_y, size_z, offset, labware_id, position)

        if hooks_across_x <= 0 or hooks_across_y <= 0:
            raise ValueError("wells_x and wells_y cannot be negative or 0")

        self._columns = hooks_across_x
        self._rows = hooks_across_y
        self.total_hooks = hooks_across_x * hooks_across_y

        # Initialize empty hooks - maps hook_id to reservoir (or None if empty)
        # hook_id ranges from 1 to total_hooks
        self.__hook_to_reservoir: dict[int, Optional[Reservoir]] = {
            i: None for i in range(1, self.total_hooks + 1)
        }

        # Place reservoirs to holder if provided
        if reservoir_dict:
            self.place_reservoirs(reservoir_dict)

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
        return (col, row)

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

        # Check if all hook_ids are valid
        for hook_id in hook_ids:
            if hook_id not in self.__hook_to_reservoir:
                raise ValueError(
                    f"Hook ID {hook_id} is invalid. Must be between 1 and {self.total_hooks}"
                )

        # Check if hooks form a valid rectangle
        is_valid, width_hooks, height_hooks = self._validate_hooks_form_rectangle(hook_ids)
        if not is_valid:
            raise ValueError(
                f"Hook IDs {hook_ids} must form a rectangular grid"
            )

        # Check if hooks are available
        for hook_id in hook_ids:
            if self.__hook_to_reservoir[hook_id] is not None:
                raise ValueError(f"Hook {hook_id} is already occupied")

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

        # Assign hook_ids and place reservoir
        reservoir.hook_ids = hook_ids
        for hook_id in hook_ids:
            self.__hook_to_reservoir[hook_id] = reservoir

    def place_reservoirs(self, reservoir_dict: dict[int, dict]) -> None:
        """
        Place multiple reservoirs from a dictionary.

        Parameters
        ----------
        reservoir_dict : dict[int, dict]
            Dictionary where keys are ignored. Each value should contain:
            - Required: size_x, size_y, size_z
            - Optional: capacity, filled_volume, content, labware_id, hook_ids (list or int),
              num_hooks_x (int), num_hooks_y (int)

            If hook_ids is specified, the reservoir will be placed there.
            If num_hooks_x and/or num_hooks_y are specified, will allocate that many hooks.
            Otherwise, calculates required hooks based on dimensions and allocates automatically.

        Raises
        ------
        ValueError
            If a specified hook_id is occupied, insufficient space, or
            reservoir parameters are invalid.
        """
        for params in reservoir_dict.values():
            # Determine which hooks to use
            specified_hooks = params.get("hook_ids")
            num_hooks_x = params.get("num_hooks_x", 1)
            num_hooks_y = params.get("num_hooks_y", 1)

            if specified_hooks is not None:
                # User specified exact hooks - convert to list if needed
                if isinstance(specified_hooks, int):
                    hook_ids_to_use = [specified_hooks]
                else:
                    hook_ids_to_use = specified_hooks
            else:
                # Auto-allocate hooks in a rectangle
                max_width_per_hook = self.size_x / self._columns
                max_height_per_hook = self.size_y / self._rows
                reservoir_width = params["size_x"]
                reservoir_height = params["size_y"]

                # Calculate minimum hooks needed based on dimensions
                min_hooks_x = int(reservoir_width / max_width_per_hook)
                if reservoir_width % max_width_per_hook > 0:
                    min_hooks_x += 1

                min_hooks_y = int(reservoir_height / max_height_per_hook)
                if reservoir_height % max_height_per_hook > 0:
                    min_hooks_y += 1

                # Use the larger of calculated or requested
                hooks_x = max(min_hooks_x, num_hooks_x)
                hooks_y = max(min_hooks_y, num_hooks_y)

                # Find available rectangular region
                available = set(self.get_available_hooks())
                hook_ids_to_use = None

                for start_row in range(self._rows - hooks_y + 1):
                    for start_col in range(self._columns - hooks_x + 1):
                        # Check if this rectangle is available
                        candidate_hooks = []
                        valid = True
                        for r in range(start_row, start_row + hooks_y):
                            for c in range(start_col, start_col + hooks_x):
                                hook_id = self.position_to_hook_id(c, r)
                                if hook_id not in available:
                                    valid = False
                                    break
                                candidate_hooks.append(hook_id)
                            if not valid:
                                break

                        if valid:
                            hook_ids_to_use = candidate_hooks
                            break
                    if hook_ids_to_use:
                        break

                if hook_ids_to_use is None:
                    raise ValueError(
                        f"Cannot find {hooks_x}×{hooks_y} rectangular region of "
                        f"available hooks for reservoir"
                    )

            # Create Reservoir instance
            reservoir = Reservoir(
                size_x=params["size_x"],
                size_y=params["size_y"],
                size_z=params["size_z"],
                capacity=params.get("capacity", Default_Reservoir_Capacity),
                filled_volume=params.get("filled_volume"),
                content=params.get("content"),
                labware_id=params.get("labware_id"),
                position=params.get("position", None),
            )

            #print(f"Placing reservoir with size_y={params['size_y']}, hooks_x={hooks_x}, hooks_y={hooks_y}, hook_ids={hook_ids_to_use}")
            self.place_reservoir(hook_ids_to_use, reservoir)

    def add_volume(self, hook_id: int, volume: float) -> None:
        """Add volume to a reservoir at a specific hook."""
        if hook_id not in self.__hook_to_reservoir or self.__hook_to_reservoir[hook_id] is None:
            raise ValueError(f"No reservoir at hook {hook_id}")
        self.__hook_to_reservoir[hook_id].add_volume(volume)

    def remove_volume(self, hook_id: int, volume: float) -> None:
        """Remove volume from a reservoir at a specific hook."""
        if hook_id not in self.__hook_to_reservoir or self.__hook_to_reservoir[hook_id] is None:
            raise ValueError(f"No reservoir at hook {hook_id}")
        self.__hook_to_reservoir[hook_id].remove_volume(volume)

    def get_waste_reservoirs(self) -> list[Reservoir]:
        """Get all unique reservoirs labeled as waste."""
        return [
            res for res in self.get_reservoirs()
            if res.content and "waste" in res.content.lower()
        ]

    def get_equivalent_reservoirs(self, content: str) -> list[Reservoir]:
        """Get all unique reservoirs with the same content."""
        return [
            res for res in self.get_reservoirs()
            if res.content and res.content.lower() == content.lower()
        ]

    def get_reservoir_by_content(self, content: str) -> Optional[Reservoir]:
        """Get the first matching reservoir with the specified content."""
        for res in self.get_reservoirs():
            if res.content and res.content.lower() == content.lower():
                return res
        return None

    def to_dict(self) -> dict:
        """Serialize the ReservoirHolder instance to a dictionary."""
        base = super().to_dict()

        # Store only unique reservoirs with their hook_ids
        unique_reservoirs = {}
        for res in self.get_reservoirs():
            unique_reservoirs[res.labware_id] = res.to_dict()

        base.update({
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
            offset = data["offset"],
            hooks_across_x=data["hooks_across_x"],
            hooks_across_y=data.get("hooks_across_y", 1),  # Default to 1 for backwards compatibility
            labware_id=data["labware_id"],
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