import uuid
from .serializable import Serializable, register_class


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

    def __init__(self, size_x: float, size_y: float, size_z: float, labware_id: str = None):
        """
        Initialize a Labware instance.

        Parameters
        ----------
        size_x : float
            Width of the labware.
        size_y : float
            Depth of the labware.
        size_z : float
            Height of the labware.
        labware_id : str, optional
            Unique ID for the labware. If None, a UUID will be generated.
        """
        self.size_x = size_x
        self.size_y = size_y
        self.size_z = size_z
        self.labware_id = labware_id or f"labware_{uuid.uuid4().hex}"

    def to_dict(self) -> dict:
        """
        Serialize the Labware instance to a dictionary.

        Returns
        -------
        dict
            Dictionary representation of the labware.
        """
        return {
            "class": self.__class__.__name__,
            "labware_id": self.labware_id,
            "size_x": self.size_x,
            "size_y": self.size_y,
            "size_z": self.size_z,
        }

    @classmethod
    def _from_dict(cls, data: dict) -> "Labware":
        """
        Deserialize a Labware instance from a dictionary.

        Parameters
        ----------
        data : dict
            Dictionary containing labware attributes.

        Returns
        -------
        Labware
            Reconstructed Labware instance.
        """
        return cls(
            size_x=data["size_x"],
            size_y=data["size_y"],
            size_z=data["size_z"],
            labware_id=data["labware_id"],
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
            Width of the well in mm.
        size_y : float
            Depth of the well in mm.
        size_z : float
            Height of the well in mm.
        labware_id : str, optional
            Unique identifier for this well. If None, a UUID will be generated.
        row: int, optional.
            row inside of plate
        column: int, optional
            column inside of plate
        media : str, optional
            Name/type of media contained in the well.
        add_height : float, optional
            Pipette dispensing height above bottom of the well (default = 5 mm).
        remove_height : float, optional
            Pipette aspiration height above bottom of the well (default = 5 mm).
        suck_offset_xy : tuple[float, float], optional
            XY offset from the well corner for aspiration/dispense (default = (2, 2)).
        """
        super().__init__(size_x=size_x, size_y=size_y, size_z=size_z, labware_id=labware_id)

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
            Dictionary containing all well attributes.
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
            Dictionary with Well attributes.

        Returns
        -------
        Well
            Reconstructed Well instance.
        """
        base_obj = super()._from_dict(data)  # Labware attributes
        # overwrite base_obj with correct class instantiation
        obj = cls(
            size_x=base_obj.size_x,
            size_y=base_obj.size_y,
            size_z=base_obj.size_z,
            labware_id=base_obj.labware_id,
            media=data.get("media"),
            add_height=data.get("add_height", 5),
            remove_height=data.get("remove_height", 5),
            suck_offset_xy=tuple(data.get("suck_offset_xy", (2, 2))),
            row= data.get("row"),
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
    first_well_xy : tuple[float, float]
        Coordinates of the first well.
    """

    def __init__(self, size_x, size_y, size_z, wells_x, wells_y, first_well_xy, well: Well = None, labware_id: str = None):
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
        first_well_xy : tuple[float, float]
            Coordinates of the first well.
        labware_id : str, optional
            Unique ID for the plate.
        """
        super().__init__(size_x, size_y, size_z, labware_id)
        self.wells_x = wells_x
        self.wells_y = wells_y
        self.first_well_xy = first_well_xy

        self.__wells: dict[str, Well or None] = {}
        self.well = well

        if well:
            if wells_x * well.size_x > size_x or wells_y * well.size_y > size_y:
                raise ValueError("Well is to big for this Plate")
            else:
                self.place_wells()
        else:
            for x in range(self.wells_x):
                for y in range(self.wells_y):
                    self.__wells[f'{x}:{y}'] = None

    def get_wells(self):
        return self.__wells

    def place_wells(self):
        for x in range(self.wells_x):
            for y in range(self.wells_y):
                well = self.well
                well.column = x
                well.row = y
                well.labware_id = f'{x}:{y}'
                self.__wells[well.labware_id] = well


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
            Dictionary representation of the plate.
        """
        base = super().to_dict()
        base.update({
            "wells_x": self.wells_x,
            "wells_y": self.wells_y,
            "first_well_xy": list(self.first_well_xy),
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
            Dictionary containing plate attributes.

        Returns
        -------
        Plate
            Reconstructed Plate instance.
        """
        plate = cls(
            size_x=data["size_x"],
            size_y=data["size_y"],
            size_z=data["size_z"],
            labware_id=data["labware_id"],
            wells_x=data["wells_x"],
            wells_y=data["wells_y"],
            first_well_xy=tuple(data["first_well_xy"]))

        wells_data = data.get("wells", {})
        for wid, wdata in wells_data.items():
            if wdata is None:
                plate._Plate__wells[wid] = None
            else:
                plate._Plate__wells[wid] = Serializable.from_dict(wdata)

        return plate

@register_class
class PipetteHolder(Labware):
    """
    Represents a Pipette Holder labware.
    """

    def __init__(self, labware_id: str = None, size_x: float  = 20, size_y: float = 20, size_z : float = 50):
        """
        Initialize a PipetteHolder instance.

        Parameters
        ----------
        labware_id : str, optional
            Unique ID for the pipette holder.
        """
        super().__init__(size_x=size_x, size_y=size_y, size_z=size_z, labware_id=labware_id)

    @classmethod
    def _from_dict(cls, data: dict) -> "PipetteHolder":
        """
        Deserialize a PipetteHolder instance from a dictionary using the base Labware _from_dict.

        Parameters
        ----------
        data : dict
            Dictionary containing labware attributes.

        Returns
        -------
        PipetteHolder
            Reconstructed PipetteHolder instance.
        """
        return super()._from_dict(data)

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
                 labware_id: str = None,
                 drop_height_relative: float = 20):
        """
        Initialize a TipDropzone instance.

        Parameters
        ----------
        size_x : float
            Width of the drop zone.
        size_y : float
            Depth of the drop zone.
        size_z : float
            Height of the drop zone.
        drop_x : float
            X position (absolute in Labware, relative in Slot).
        drop_y : float
            Y position (absolute in Labware, relative in Slot).
        labware_id : str, optional
            Unique ID for the dropzone object.
        drop_height_relative : float, optional
            Height from which tips are dropped relative to the labware. Default is 20.
        """
        super().__init__(size_x=size_x, size_y=size_y, size_z=size_z, labware_id=labware_id)
        self.drop_x = drop_x
        self.drop_y = drop_y
        self.drop_height_relative = drop_height_relative

    def to_dict(self) -> dict:
        """
        Serialize the TipDropzone instance to a dictionary, extending the base Labware fields.

        Returns
        -------
        dict
            Dictionary representation of the tip dropzone.
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
            Dictionary containing tip dropzone attributes.

        Returns
        -------
        TipDropzone
            Reconstructed TipDropzone instance.
        """
        return cls(
            size_x=data["size_x"],
            size_y=data["size_y"],
            size_z=data["size_z"],
            labware_id=data["labware_id"],
            drop_x=data["drop_x"],
            drop_y=data["drop_y"],
            drop_height_relative=data["drop_height_relative"]
        )

class Reservoirs(Labware):
    def __init__(self, size_x: float,
                 size_y: float,
                 size_z: float,
                 labware_id: str = None):

        super().__init__(size_x = size_x, size_y = size_y,size_z = size_z, labware_id = labware_id)
