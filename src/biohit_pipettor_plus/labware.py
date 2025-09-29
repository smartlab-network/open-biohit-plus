import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import uuid
from .serializable import Serializable, register_class
import copy
from typing import Optional

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
            width of the labware.
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
            dictionary representation of the labware.
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
            dictionary containing labware attributes.

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
            cidth of the well in mm.
        size_y : float
            Depth of the well in mm.
        size_z : float
            Height of the well in mm.
        labware_id : str, optional
            Unique identifier for this well. If None, a UUID will be generated.
        media : str, optional
            Name/type of media contained in the well.
        add_height : float, optional
            Pipette dispensing height above bottom of the well (default = 5 mm).
        remove_height : float, optional
            Pipette aspiration height above bottom of the well (default = 5 mm).
        suck_offset_xy : tuple[float, float], optional
            XY offset from the well center for aspiration/dispense (default = (2, 2)).
        """
        super().__init__(size_x=size_x, size_y=size_y, size_z=size_z, labware_id=labware_id)

        self.media = media
        self.add_height = add_height
        self.remove_height = remove_height
        self.suck_offset_xy = suck_offset_xy

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
        )
        return obj

@register_class
class Plate(Labware):
    """
    Represents a Plate labware with containers.
    Attributes
    ----------
    containers_x : int
        Number of containers in X direction.
    containers_y : int
        Number of containers in Y direction.
    first_well_xy : tuple[float, float]
        Coordinates of the first well.
    """

    def __init__(self, size_x, size_y, size_z, containers_x, containers_y, first_well_xy, well: Well = None, labware_id: str = None):
        """
        Initialize a Plate instance.

        Parameters
        ----------
        size_x : float
            cidth of the plate.
        size_y : float
            Depth of the plate.
        size_z : float
            Height of the plate.
        containers_x : int
            Number of containers in X direction.
        containers_y : int
            Number of containers in Y direction.
        first_well_xy : tuple[float, float]
            Coordinates of the first well.
        labware_id : str, optional
            Unique ID for the plate.
        """
        super().__init__(size_x, size_y, size_z, labware_id)
        self.containers_x = containers_x
        self.containers_y = containers_y
        self.first_well_xy = first_well_xy

        self.__containers: dict[str, Well or None] = {}
        self.well = well

        if well:
            if containers_x * well.size_x > size_x or containers_y * well.size_y > size_y:
                raise ValueError("Well is to big for this Plate")
            else:
                self.place_containers()
        else:
            for x in range(self.containers_x):
                for y in range(self.containers_y):
                    self.__containers[f'{x}:{y}'] = None

    def get_containers(self):
        return self.__containers

    def place_containers(self):
        for x in range(self.containers_x):
            for y in range(self.containers_y):
                well = copy.deepcopy(self.well)  # Create a new copy
                well.labware_id = f'{x}:{y}'
                self.__containers[well.labware_id] = well

    def place_unique_well(self, well_placement: str, well: Well):
        if well_placement not in self.__containers.keys():
            raise ValueError(f"{well_placement} is not a valid well placement")

        well.labware_id = well_placement
        self.__containers[well.labware_id] = well

    def to_dict(self):
        """
        Serialize the Plate instance to a dictionary including containers information.

        Returns
        -------
        dict
            dictionary representation of the plate.
        """
        base = super().to_dict()
        base.update({
            "containers_x": self.containers_x,
            "containers_y": self.containers_y,
            "first_well_xy": list(self.first_well_xy),
             "containers": {cid: well.to_dict() if well else None for cid, well in self.__containers.items()}
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
        plate = cls(
            size_x=data["size_x"],
            size_y=data["size_y"],
            size_z=data["size_z"],
            labware_id=data["labware_id"],
            containers_x=data["containers_x"],
            containers_y=data["containers_y"],
            first_well_xy=tuple(data["first_well_xy"]))

        containers_data = data.get("containers", {})
        for cid, wdata in containers_data.items():
            if wdata is None:
                plate._Plate__containers[cid] = None
            else:
                plate._Plate__containers[cid] = Serializable.from_dict(wdata)

        return plate

@register_class
class PipetteHolder(Labware):
    """
    Represents a Pipette Holder labware.
    """

    def __init__(self, labware_id: str = None):
        """
        Initialize a PipetteHolder instance.

        Parameters
        ----------
        labware_id : str, optional
            Unique ID for the pipette holder.
        """
        super().__init__(size_x=20, size_y=20, size_z=50, labware_id=labware_id)

    @classmethod
    def _from_dict(cls, data: dict) -> "PipetteHolder":
        """
        Deserialize a PipetteHolder instance from a dictionary using the base Labware _from_dict.

        Parameters
        ----------
        data : dict
            dictionary containing labware attributes.

        Returns
        -------
        PipetteHolder
            Reconstructed PipetteHolder instance.
        """
        return super().from_dict(data)

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
            cidth of the drop zone.
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
        return cls(
            size_x=data["size_x"],
            size_y=data["size_y"],
            size_z=data["size_z"],
            labware_id=data["labware_id"],
            drop_x=data["drop_x"],
            drop_y=data["drop_y"],
            drop_height_relative=data["drop_height_relative"]
        )

Default_Reservoir_Capacity = 30000


@register_class
class Reservoir(Labware):
    def __init__(self, size_x: float, size_y: float, size_z: float,
                 capacity: float = Default_Reservoir_Capacity, filled_volume: float = None,
                 content: str = None, hook_id: int = None, labware_id: str = None):

        """
        Initialize a Reservoir instance. These are containers that store the medium to be filled in and removed from well
        size_x, size_y, size_z are dimensions of the Reservoir labware
        capacity is maximum amount of liquid that well can hold. if not provided, it is equal to Default_Reservoir_Capacity
        filled_volume is the initial volume at the time of defining the reservoir. Default is 0 for waste and capacity for rest
        hook_id is location on Reservoirs where this reservoir is going to be placed.
        """
        super().__init__(size_x, size_y, size_z, labware_id)
        self.hook_id = hook_id
        self.capacity = capacity
        self.current_volume = filled_volume if filled_volume is not None else capacity
        self.content = content

        #validate inputs
        if self.current_volume > self.capacity:
            raise ValueError(f"Filled volume ({self.current_volume}) cannot exceed capacity ({capacity})")
        if self.current_volume < 0:
            raise ValueError("Filled volume cannot be negative")
        if self.capacity < 0:
            raise ValueError("Capacity cannot be negative")

    def add_volume(self, volume: float) -> None:
        """
        Add volume to the reservoir.
        Volume to add in µL.
        ValueError if adding volume would exceed capacity."""

        if volume < 0:
            raise ValueError("Volume to add must be positive")
        if self.current_volume + volume > self.capacity:
            raise ValueError(f"Overflow! Capacity: {self.capacity} µl")
        self.current_volume += volume

    def remove_volume(self, volume: float) -> None:
        """
       Removes volume from the reservoir.
       Volume to remove in µL.
       ValueError if remove volume exceed current volume."""
        if volume < 0:
            raise ValueError("Volume to add must be positive")
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
            "hook_id": self.hook_id,
            "capacity": self.capacity,
            "filled_volume": self.current_volume,
            "content": self.content,
        })
        return base

    @classmethod
    def _from_dict(cls, data: dict) -> "Reservoir":
        """Deserialize a Reservoir instance from a dictionary."""
        return cls(
            size_x=data["size_x"],
            size_y=data["size_y"],
            size_z=data["size_z"],
            labware_id=data["labware_id"],
            hook_id=data.get("hook_id"),
            capacity=data.get("capacity", Default_Reservoir_Capacity),
            filled_volume=data.get("filled_volume"),
            content=data.get("content"),
        )


@register_class
class Reservoirs(Labware):
    def __init__(self, size_x: float, size_y: float, size_z: float, hook_count: int, reservoir_dict: dict[int, dict] = None, labware_id: str = None):
        """ Initialize a Reservoirs instance that can hold multiple reservoirs.

        size_x, size_y, size_z are dimensions of the reservoirs labware
        hook_count = no of hooks. This determines the no of individual reservoir that can be placed
        reservoir_dict is an optional variable that defines the individual reservoir and its attribute.
        """
        super().__init__(size_x, size_y, size_z, labware_id)
        self.hook_count = hook_count

        # Initialize empty hooks
        self.__reservoirs: dict[int, Optional[Reservoir]] = {
            i: None for i in range(1,hook_count + 1)
        }

        # Place reservoirs if provided
        if reservoir_dict:
            self.place_reservoirs(reservoir_dict)

    def get_reservoirs(self) -> dict[int, Optional[Reservoir]]:
        """Return the dictionary of all reservoirs."""
        return self.__reservoirs

    def get_available_hooks(self) -> list[int]:
        """Return list of available (empty) hook IDs."""
        return [hook_id for hook_id, res in self.__reservoirs.items() if res is None]

    def get_occupied_hooks(self) -> list[int]:
        """Return list of occupied hook IDs."""
        return [hook_id for hook_id, res in self.__reservoirs.items() if res is not None]

    def place_reservoir(self, hook_id: int, reservoir: Reservoir) -> None:
        """ Place a single reservoir on a specific hook.

        Parameters:
            hook_id : int
                Hook position to place the reservoir.
            reservoir : Reservoir
                Reservoir instance to place.

        Raises ValueError If hook_id is invalid, already occupied, or reservoir dimensions incompatible.
        """
        # Check if hook_id is valid
        if hook_id not in self.__reservoirs:
            raise ValueError(f"Hook ID {hook_id} is invalid. Must be between 1 and {self.hook_count}")

        # Check if hook is available
        if self.__reservoirs[hook_id] is not None:
            raise ValueError(f"Hook {hook_id} is already occupied")

        # Check dimensional compatibility
        max_width_per_hook = self.size_x / self.hook_count

        # Check dimensional compatibility
        if reservoir.size_x > max_width_per_hook:
            raise ValueError(
                f"Reservoir width ({reservoir.size_x} mm) exceeds "
                f"maximum width per hook ({max_width_per_hook:.2f} mm = {self.size_x} mm / {self.hook_count} hooks)"
            )
        if reservoir.size_y > self.size_y:
            raise ValueError(
                f"Reservoir depth ({reservoir.size_y} mm) exceeds "
                f"Reservoirs depth ({self.size_y} mm)"
            )
        if reservoir.size_z > self.size_z:
            raise ValueError(
                f"Reservoir height ({reservoir.size_z} mm) exceeds "
                f"Reservoirs height ({self.size_z} mm)"
            )

        # Assign hook_id and place reservoir
        reservoir.hook_id = hook_id
        self.__reservoirs[hook_id] = reservoir

    def place_reservoirs(self, reservoir_dict: dict[int, dict]) -> None:
        """
        Place multiple reservoirs from a dictionary.

        Parameters
        ----------
        reservoir_dict : dict[int, dict]
            Dictionary where keys are ignored. Each value should contain:
            - Required: size_x, size_y, size_z
            - Optional: capacity, filled_volume, content, labware_id, hook_id

            If hook_id is specified in params, the reservoir will be placed there.
            Otherwise, the next available hook will be used.

        Raises ValueError If a specified hook_id is occupied, all hooks are full, or
            reservoir parameters are invalid.
        """
        for params in reservoir_dict.values():

            specified_hook = params.get("hook_id")
            if specified_hook is not None:
                # Check if hook_id is valid
                if specified_hook not in self.__reservoirs:
                    raise ValueError(f"Hook ID {specified_hook} is invalid. Must be between 0 and {self.hook_count - 1}")
                # Check if hook is free
                if self.__reservoirs[specified_hook] is not None:
                    raise ValueError(f"Hook {specified_hook} is already occupied")
            else:
                # If no hook specified, ensure at least one is free
                available_hooks = self.get_available_hooks()
                if not available_hooks:
                    raise ValueError("All hooks are occupied. Cannot place reservoir.")
                specified_hook = available_hooks[0]  # pick the first free hook

            # Create Reservoir instance from parameters
            reservoir = Reservoir(
                size_x=params["size_x"],
                size_y=params["size_y"],
                size_z=params["size_z"],
                capacity=params.get("capacity", Default_Reservoir_Capacity),
                filled_volume=params.get("filled_volume"),
                content=params.get("content"),
                labware_id=params.get("labware_id"),
                hook_id=specified_hook,
            )

            self.place_reservoir(specified_hook, reservoir)

    def add_volume(self, hook_id: int, volume: float) -> None:
        """Add volume to a reservoir at a specific hook."""
        if hook_id not in self.__reservoirs or self.__reservoirs[hook_id] is None:
            raise ValueError(f"No reservoir at hook {hook_id}")
        self.__reservoirs[hook_id].add_volume(volume)

    def remove_volume(self, hook_id: int, volume: float) -> None:
        """ Remove volume from a reservoir at a specific hook."""
        if hook_id not in self.__reservoirs or self.__reservoirs[hook_id] is None:
            raise ValueError(f"No reservoir at hook {hook_id}")
        self.__reservoirs[hook_id].remove_volume(volume)

    def get_waste_containers(self) -> list[Reservoir]:
        """ Get all reservoirs labeled as waste."""
        return [
            res for res in self.__reservoirs.values()
            if res is not None and res.content and "waste" in res.content.lower()
        ]

    def get_equivalent_containers(self, content: str) -> list[Reservoir]:
        """ Get all reservoirs with the same content. """
        return [
            res for res in self.__reservoirs.values()
            if res is not None and res.content and res.content.lower() == content.lower()
        ]

    def get_reservoir_by_content(self, content: str) -> Optional[Reservoir]:
        """ Get the first matching reservoir with the specified content."""
        for res in self.__reservoirs.values():
            if res is not None and res.content and res.content.lower() == content.lower():
                return res
        return None

    def to_dict(self) -> dict:
        """Serialize the Reservoirs instance to a dictionary."""
        base = super().to_dict()
        base.update({
            "hook_count": self.hook_count,
            "reservoirs": {
                hook_id: res.to_dict() if res else None
                for hook_id, res in self.__reservoirs.items()
            },
        })
        return base

    @classmethod
    def _from_dict(cls, data: dict) -> "Reservoirs":
        """Deserialize a Reservoirs instance from a dictionary."""
        reservoirs = cls(
            size_x=data["size_x"],
            size_y=data["size_y"],
            size_z=data["size_z"],
            hook_count=data["hook_count"],
            labware_id=data["labware_id"],
        )

        # Restore reservoirs
        reservoirs_data = data.get("reservoirs", {})
        for hook_id_str, res_data in reservoirs_data.items():
            hook_id = int(hook_id_str)
            if res_data is not None:
                reservoir = Serializable.from_dict(res_data)
                reservoirs._Reservoirs__reservoirs[hook_id] = reservoir

        return reservoirs
