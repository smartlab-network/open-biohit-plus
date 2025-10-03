from typing import Dict, Tuple, List
from .labware import Labware, ReservoirHolder, PipetteHolder, Plate
from .serializable import Serializable, register_class
#TODO get this right
from .position import Position_allocator

@register_class
class Slot(Serializable):
    """
    Represents a single slot on a Deck. A slot can hold multiple Labware objects stacked
    vertically with specified Z-ranges.

    Attributes
    ----------
    range_x : tuple[float, float]
        Minimum and maximum x coordinates of the slot.
    range_y : tuple[float, float]
        Minimum and maximum y coordinates of the slot.
    range_z : float
        Maximum height of the slot.
    slot_id : str
        Unique identifier for the slot.
    labware_stack : dict[str, list[Labware, tuple[float, float]]]
        Dictionary mapping Labware IDs to a list containing the Labware object and its Z-range
        (min_z, max_z) within the slot.
    """

    def __init__(self, range_x: tuple[float, float], range_y: tuple[float, float],
                 range_z: float, slot_id: str):
        self.range_x = range_x
        self.range_y = range_y
        self.range_z = range_z
        self.slot_id = slot_id

        # Dictionary storing stacked labware: {labware_id: [Labware, (min_z, max_z)]}
        self.labware_stack: Dict[str, List] = {}

    def place_labware(self, lw: Labware, min_z: float):
        """
        Add a Labware object to the slot at a specific Z-range.

        Parameters
        ----------
        lw : Labware
            Labware object to place.
        min_z : float
            Minimum Z coordinate within the slot for this Labware.

        Raises
        ------
        ValueError
            If the Labware exceeds the slot's Z range.
        """
        max_z = min_z + lw.size_z
        if max_z > self.range_z:
            raise ValueError(f"Cannot place labware {lw.labware_id}: exceeds slot height.")
        self.labware_stack[lw.labware_id] = [lw, (min_z, max_z)]

    def remove_labware(self, labware_id: str):
        """
        Remove a specific Labware from the stack.

        Parameters
        ----------
        labware_id : str
            ID of the Labware to remove.
        """
        if labware_id in self.labware_stack:
            del self.labware_stack[labware_id]

    def allocate_position(
            self,
            lw: Labware,
            x_spacing: float = None,
            y_spacing: float = None,
    ):
        """
        if labware is placed in slot, x & y coordinates of the labware is slot 
        """
        if lw.labware_id not in self.labware_stack:
            raise ValueError("Labware not in labware stack")

        x_corner = min(self.range_x[0], self.range_x[1])
        y_corner = min(self.range_y[0], self.range_y[1])
        offset_x, offset_y = lw.offset

        #position is slot corner + offset of the labware.
        lw.position = (x_corner + offset_x, y_corner + offset_y)

        #if not none, then labware contains labware within them. Like ReservoirHolder - reservoirs, Plate - wells, pipetteHolder -Zone
        if hasattr(lw, "_rows") and hasattr(lw, "_columns"):
            if not isinstance(lw, (Plate, ReservoirHolder, PipetteHolder)):
                raise ValueError("Only (plate, reservoir, pipetteHolder) contain labware within them (wells, reservoirs, zone). Update the code for your labware")
            else:
                position_allocator = Position_allocator()
                position_allocator.calculate_multi(
                    lw,
                    lw.position[0],
                    lw.position[1],
                    x_spacing,
                    y_spacing,
                )

    def is_compatible_labware(self, lw: Labware, min_z: float) -> bool:
        """
        Check if a Labware object fits within X, Y, and Z dimensions of the slot.

        Parameters
        ----------
        lw : Labware
            Labware object to check.
        min_z : float
            Minimum Z position where the Labware would be placed.

        Returns
        -------
        bool
            True if the labware fits, False otherwise.
        """
        fits_xy = (abs(self.range_x[1] - self.range_x[0]) >= lw.size_x
                   and abs(self.range_y[1] - self.range_y[0]) >= lw.size_y)
        fits_z = min_z + lw.size_z <= self.range_z
        return fits_xy and fits_z

    def to_dict(self) -> dict:
        """
        Serialize the Slot instance to a dictionary, including stacked labware and their Z-ranges.

        Returns
        -------
        dict
            Dictionary representation of the slot.
        """
        return {
            "class": self.__class__.__name__,
            "slot_id": self.slot_id,
            "range_x": list(self.range_x),
            "range_y": list(self.range_y),
            "range_z": self.range_z,
            "labware_stack": {
                lw_id: [lw.to_dict(), zr] for lw_id, (lw, zr) in self.labware_stack.items()
            }
        }

    @classmethod
    def _from_dict(cls, data: dict) -> "Slot":
        """
        Deserialize a Slot instance from a dictionary, restoring stacked Labware with Z-ranges.

        Parameters
        ----------
        data : dict
            Dictionary containing slot attributes and labware stack.

        Returns
        -------
        Slot
            Reconstructed Slot instance.
        """
        slot = cls(
            range_x= tuple(data["range_x"]),
            range_y= tuple(data["range_y"]),
            range_z=data["range_z"],
            slot_id=data["slot_id"]
        )

        for lw_id, (lw_data, zr) in data.get("labware_stack", {}).items():
            slot.labware_stack[lw_id] = [Serializable.from_dict(lw_data), tuple(zr)]
        return slot