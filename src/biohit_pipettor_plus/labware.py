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

    def __init__(self, size_x: float, size_y: float, size_z: float, labware_id: str = None, position: tuple[float, float] = None):
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
        self.position = position

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
        return cls(
            size_x=data["size_x"],
            size_y=data["size_y"],
            size_z=data["size_z"],
            labware_id=data["labware_id"],
            position=position,
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
                 content: str = None, hook_ids: list[int] = None, labware_id: str = None,
                 position: tuple[float, float] = None):
        """
        Initialize a Reservoir instance. These are containers that store the medium to be filled in and removed from well
        size_x, size_y, size_z are dimensions of the Reservoir labware
        capacity is maximum amount of liquid that well can hold. if not provided, it is equal to Default_Reservoir_Capacity
        filled_volume is the initial volume at the time of defining the reservoir. Default is 0 for waste and capacity for rest
        hook_ids is list of hook locations on ReservoirHolder where this reservoir is going to be placed.
        """
        super().__init__(size_x, size_y, size_z, labware_id, position)
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
        position = tuple(data["position"]) if data.get("position") else None
        return cls(
            size_x=data["size_x"],
            size_y=data["size_y"],
            size_z=data["size_z"],
            labware_id=data["labware_id"],
            hook_ids=data.get("hook_ids", []),
            capacity=data.get("capacity", Default_Reservoir_Capacity),
            filled_volume=data.get("filled_volume"),
            content=data.get("content"),
            position=position,
        )


@register_class
class ReservoirHolder(Labware):
    def __init__(self, size_x: float, size_y: float, size_z: float, hook_count: int,
                 hook_across_y: int, reservoir_dict: dict[int, dict] = None,
                 labware_id: str = None, position: tuple[float, float] = None):
        """
        Initialize a ReservoirHolder instance that can hold multiple reservoirs.

        Parameters
        ----------
        size_x : float
            Width of the ReservoirHolder
        size_y : float
            Depth of the ReservoirHolder
        size_z : float
            Height of the ReservoirHolder
        hook_count : int
            Number of hooks along X-axis
        hook_across_y : int
            Number of hooks along Y-axis (rows of hooks)
        reservoir_dict : dict[int, dict], optional
            Dictionary defining individual reservoirs and their attributes
        labware_id : str, optional
            Unique ID for the holder
        position : tuple[float, float], optional
            (x, y) position of the ReservoirHolder
        """
        super().__init__(size_x, size_y, size_z, labware_id, position)
        self.hook_count = hook_count
        self.hook_across_y = hook_across_y
        self.total_hooks = hook_count * hook_across_y

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
            (col, row) where col is 0 to hook_count-1, row is 0 to hook_across_y-1

        Example
        -------
        For hook_count=3, hook_across_y=2:
        hook_id: 1 2 3 4 5 6
        layout: [1 2 3]  <- row 0
                [4 5 6]  <- row 1
        """
        if hook_id < 1 or hook_id > self.total_hooks:
            raise ValueError(f"hook_id {hook_id} out of range (1 to {self.total_hooks})")

        # Convert to 0-indexed
        idx = hook_id - 1
        row = idx // self.hook_count
        col = idx % self.hook_count
        return (col, row)

    def position_to_hook_id(self, col: int, row: int) -> int:
        """
        Convert (col, row) position to hook_id.

        Parameters
        ----------
        col : int
            Column (0 to hook_count-1)
        row : int
            Row (0 to hook_across_y-1)

        Returns
        -------
        int
            hook_id (1-indexed)
        """
        if col < 0 or col >= self.hook_count:
            raise ValueError(f"col {col} out of range (0 to {self.hook_count - 1})")
        if row < 0 or row >= self.hook_across_y:
            raise ValueError(f"row {row} out of range (0 to {self.hook_across_y - 1})")

        return row * self.hook_count + col + 1


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
        max_width_per_hook = self.size_x / self.hook_count
        max_height_per_hook = self.size_y / self.hook_across_y

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
                max_width_per_hook = self.size_x / self.hook_count
                max_height_per_hook = self.size_y / self.hook_across_y
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

                for start_row in range(self.hook_across_y - hooks_y + 1):
                    for start_col in range(self.hook_count - hooks_x + 1):
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

    def get_waste_containers(self) -> list[Reservoir]:
        """Get all unique reservoirs labeled as waste."""
        return [
            res for res in self.get_reservoirs()
            if res.content and "waste" in res.content.lower()
        ]

    def get_equivalent_containers(self, content: str) -> list[Reservoir]:
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
            "hook_count": self.hook_count,
            "hook_across_y": self.hook_across_y,
            "reservoirs": unique_reservoirs,
        })
        return base

    @classmethod
    def _from_dict(cls, data: dict) -> "ReservoirHolder":
        """Deserialize a ReservoirHolder instance from a dictionary."""
        position = tuple(data["position"]) if data.get("position") else None
        reservoir_holder = cls(
            size_x=data["size_x"],
            size_y=data["size_y"],
            size_z=data["size_z"],
            hook_count=data["hook_count"],
            hook_across_y=data.get("hook_across_y", 1),  # Default to 1 for backwards compatibility
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