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
            cidth of the labware.
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


@register_class
class Reservoir(Labware):
    """
    Represents a Reservoir from which medium will be aspirated and dispensed.

    Attributes
    ----------
    x_corner : float
        X coordinate of the reservoir's start point.
    y_corner : float
        Y coordinate of the reservoir's start point.
    volume : float
        Volume of the reservoir.
    """

    def __init__(self, size_x : float, size_y : float, size_z: float, x_corner: float, y_corner: float, volume: float, labware_id: str = None,):
        super().__init__( size_x = size_x, size_y = size_y, size_z = size_z, labware_id = labware_id)
        self.size_x = size_x
        self.size_y = size_y
        self.size_z = size_z
        self.x_corner = x_corner
        self.y_corner = y_corner
        self.volume = volume

    @classmethod
    def from_dict(cls, data: dict):
        """Deserialize a Reservoir from a dictionary."""
        return cls(
            size_x = data["size_x"],
            size_y = data["size_y"],
            size_z = data["size_z"],
            x_corner=data["x_corner"],
            y_corner=data["y_corner"],
            volume=data["volume"]
        )

    def to_dict(self) -> dict:
        """Serialize the Reservoir to a dictionary."""
        return {
            "size_x" :  self.size_x,
            "size_y" : self.size_y,
            "size_z" : self.size_z,
            "x_corner": self.x_corner,
            "y_corner": self.y_corner,
            "volume": self.volume
        }

class Reservoirs:
    """
    Manages a collection of containers in a reservoir, tracking their capacities, volumes, and equivalent groups.

    Attributes
    ----------
    containers : dict[int, Reservoir]
        dictionary mapping container IDs to Reservoir objects.
    capacities : dict[int, float]
        dictionary mapping container IDs to their capacities (in µl).
    current_volume : dict[int, float]
        dictionary mapping container IDs to their current volumes (in µl).
    disabled_containers : set[int]
        set of container IDs that are disabled (treated as non-existent).
    equivalent_groups : dict[int, list[int]]
        dictionary mapping container IDs to lists of equivalent containers IDs (e.g., containers with the same solution).
    """
    default_capacity = 30000  # Default container capacity in µl
    container_spacing = 18  # Spacing between containers in mm
    x_offset = 3  # X offset for container positioning
    y_offset = 40  # Y offset for container positioning
    add_height = 65  # Height for adding liquid
    remove_height = 103  # Height for removing liquid
    underflow_buffer = 3000  # Buffer to prevent complete liquid removal

    def __init__(self, size_x : float, size_y : float, size_z: float, x_corner: float, y_corner: float, container_ids: list[int], capacities: Optional[dict[int, float]] = None,
                 disabled_containers: Optional[set[int]] = None, waste_containers: Optional[set[int]] = None, filled_vol: Optional[dict[int, float]] = None,equivalent_groups: Optional[dict[int, list[int]]] = None):
        """
        Initialize a Reservoirs object.

        Parameters
        ----------
        x_corner : float
            X coordinate of the reservoir's start point.
        y_corner : float
            Y coordinate of the reservoir's start point.
        container_ids : list[int]
            list of container IDs to initialize. For 7 container, pass a list of 7 Ids.
        capacities : Optional[dict[int, float]]
            dictionary of container IDs to their capacities (in µl). If None, uses default capacity.
        disabled_containers : Optional[set[int]]
            set of container IDs to disable. If None, no containers are disabled.
        waste_containers : set[int]
            Set of container IDs designated as waste containers.
        equivalent_groups : Optional[dict[int, list[int]]]
            dictionary mapping container IDs to lists of equivalent container IDs. If None, each container is its own group.
        filled_vol : Optional[dict[int, float]]
            dictionary of well IDs to their initial fill volumes (in µl). If None, uses capacities or default fill.
        """
        self.containers = {}
        self.capacities = {}
        self.current_volume = {}
        self.disabled_containers = set(disabled_containers) if disabled_containers is not None else set()
        self.waste_containers = (
            set(waste_containers) if waste_containers is not None and waste_containers.issubset(set(container_ids))
            else {1} if 1 in container_ids
            else set()
        )
        self.equivalent_groups = equivalent_groups if equivalent_groups is not None else {cid: [cid] for cid in container_ids}

        # Initialize container positions and capacities
        for cid in container_ids:

            # Calculate X & Y position: containers are spaced from right to left
            container_x = x_corner + (max(container_ids) - cid) * self.container_spacing + self.x_offset
            container_y = y_corner + self.y_offset

            # Create Reservoir object for each container
            self.containers[cid] = Reservoir(size_x, size_y, size_z, x_corner =container_x, y_corner=container_y, volume=0)
            # set capacity
            self.capacities[cid] = 0 if cid in self.disabled_containers else (
                capacities.get(cid, self.default_capacity) if capacities is not None else self.default_capacity
            )
            # set initial volume: full for non-waste/disabled containers, 0 for disabled. 0 for waste if not stated otherwise
            if cid in self.disabled_containers:
                self.current_volume[cid] = 0
            else:
                initial_volume = (
                    filled_vol.get(cid, 0 if cid in self.waste_containers else self.capacities[cid])
                    if filled_vol is not None else
                    (0 if cid in self.waste_containers else self.capacities[cid])
                )
                if initial_volume > self.capacities[cid]:
                    raise ValueError(
                        f"Initial volume {initial_volume} µl for container {cid} exceeds capacity {self.capacities[cid]} µl")
                self.current_volume[cid] = initial_volume
            self.containers[cid].volume = self.current_volume[cid]

    def get_waste_containers(self) -> list[int]:
        """Return a list of container IDs designated as waste containers."""
        return list(self.waste_containers - self.disabled_containers)

    def add_volume(self, container: int, volume: float) -> None:
        """Add liquid to a container if capacity allows."""
        if container not in self.containers:
            raise ValueError(f"container {container} does not exist.")
        if container in self.disabled_containers:
            raise ValueError(f"container {container} is disabled.")
        if self.current_volume[container] + volume > self.capacities[container]:
            raise ValueError(f"Reservoir {container} overflow! Capacity: {self.capacities[container]} µl")
        self.current_volume[container] += volume
        self.containers[container].volume = self.current_volume[container]

    def remove_volume(self, container: int, volume: float) -> None:
        """Remove liquid from a container if enough is available."""
        if container not in self.containers:
            raise ValueError(f"container {container} does not exist.")
        if container in self.disabled_containers:
            raise ValueError(f"container {container} is disabled.")
        if self.current_volume[container] - self.remove_height < volume:
            raise ValueError(f"Reservoir {container} underflow! Only {self.current_volume[container]} µl available.")
        self.current_volume[container] -= volume
        self.containers[container].volume = self.current_volume[container]

    def get_equivalent_group(self, container: int) -> list[int]:
        """Return the list of equivalent containers for a given container, excluding disabled containers."""
        if container not in self.containers:
            return []
        return [w for w in self.equivalent_groups.get(container, [container]) if w not in self.disabled_containers]

    def to_dict(self) -> dict:
        """Serialize the Reservoirs object to a dictionary."""
        return {
            "containers": {str(cid): container.to_dict() for cid, container in self.containers.items()},
            "capacities": self.capacities,
            "current_volume": self.current_volume,
            "waste_containers": list(self.waste_containers),
            "disabled_containers": list(self.disabled_containers),
            "equivalent_groups": self.equivalent_groups
        }

    @classmethod
    def from_dict(cls, data: dict, size_x: float, size_y : float, size_z : float, x_corner: float, y_corner: float) -> 'Reservoirs':
        """Deserialize a Reservoirs object from a dictionary."""
        container_ids = [int(cid) for cid in data.get("containers", {}).keys()]
        containers_data = data.get("containers", {})
        capacities = data.get("capacities", {})
        filled_vol = data.get("current_volume", {})
        disabled_containers = set(data.get("disabled_containers", []))
        waste_containers = set(data.get("waste_containers", []))
        equivalent_groups = data.get("equivalent_groups", None)

        # Create Reservoirs instance
        reservoirs = cls(
            size_x= size_x,
            size_y= size_y,
            size_z= size_z,
            x_corner=x_corner,
            y_corner=y_corner,
            container_ids=container_ids,
            capacities=capacities,
            filled_vol=filled_vol,
            disabled_containers=disabled_containers,
            waste_containers=waste_containers,
            equivalent_groups=equivalent_groups
        )

        # Override container objects with deserialized data
        for cid, wdata in containers_data.items():
            reservoirs.containers[int(cid)] = Reservoir.from_dict(wdata)

        return reservoirs