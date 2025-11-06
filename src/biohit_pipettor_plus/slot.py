from typing import Dict, List
from .labware import Labware, ReservoirHolder, PipetteHolder, Plate
from .serializable import Serializable, register_class
#TODO get this right
from .position import Position_allocator

@register_class
class Slot(Serializable):
    """
    Represents a single slot on a Deck. A slot can hold multiple Labware objects stacked
    vertically with specified Z-ranges

    Attributes
    ---------
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
                 range_z: float, slot_id: str) -> None:
        self.range_x = range_x
        self.range_y = range_y
        self.range_z = range_z
        self.slot_id = slot_id

        # Dictionary storing stacked labware: {labware_id: [Labware, (min_z, max_z)]}
        self.labware_stack: Dict[str, List[Labware, tuple[float, float]]] = {}

    def _place_labware(self, lw: Labware, min_z: float):
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
        self.is_compatible_labware(lw=lw, min_z=min_z)
        max_z = min_z + lw.size_z
        self.labware_stack[lw.labware_id] = [lw, (min_z, max_z)]

    def _remove_labware(self, labware_id: str):
        """
        Remove a specific Labware from the stack.

        Parameters
        ----------
        labware_id : str
            ID of the Labware to remove.
        """
        if labware_id in self.labware_stack:
            del self.labware_stack[labware_id]

    def _allocate_position(
            self,
            lw: Labware,
            x_spacing: float = None,
            y_spacing: float = None,
    ):
        """
        if labware is placed in slot, x & y coordinates of the labware + offset is slot.
        """
        if lw.labware_id not in self.labware_stack:
            raise ValueError("Labware not in labware stack")

        offset_x, offset_y = lw.offset
        x_corner = min(self.range_x[0], self.range_x[1]) + offset_x
        y_corner = min(self.range_y[0], self.range_y[1]) + offset_y

        #position is slot corner + offset of the labware.
        lw.position = (x_corner, y_corner)

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
                    lw._rows,
                    lw._columns,
                )

    def is_compatible_labware(self, lw: Labware, min_z: float) -> None:
        """
        Checks if a Labware object can be placed at the given Z position, raising
        a ValueError if any constraint (XY fit, Z range, stacking, or overlap) is violated.
        """
        slot_width = abs(self.range_x[1] - self.range_x[0])
        slot_depth = abs(self.range_y[1] - self.range_y[0])
        max_z_new = min_z + lw.size_z

        # --- 1 & 2. Basic XY Fit & Z-Range Check (Remains the same) ---
        if lw.size_x > slot_width or lw.size_y > slot_depth:
            raise ValueError(
                f"Labware '{lw.labware_id}' (Size X:{lw.size_x}, Y:{lw.size_y}) "
                f"is too large for slot '{self.slot_id}' (Size X:{slot_width}, Y:{slot_depth})."
            )

        if max_z_new > self.range_z:
            raise ValueError(
                f"Placement of Labware '{lw.labware_id}' at min_z={min_z} "
                f"exceeds the slot's total height capacity ({self.range_z})."
            )

        # --- 3. Stacking Constraint Check (UPDATED LOGIC) ---
        if self.labware_stack:
            top_lw = None
            max_z_seen = -1.0

            # Find the existing labware that occupies the highest Z-level.
            for existing_lw, (min_z_exist, max_z_exist) in self.labware_stack.values():
                if max_z_exist > max_z_seen:
                    max_z_seen = max_z_exist
                    top_lw = existing_lw

            # Use getattr to safely check the property, defaulting to False
            # if the attribute is missing (which matches the default behavior of blocking stacking).
            can_stack_upon = getattr(top_lw, 'can_be_stacked_upon', False)

            if not can_stack_upon:
                # If can_be_stacked_upon is False, raise an error.
                raise ValueError(
                    f"Stacking error in slot '{self.slot_id}': Labware '{top_lw.labware_id}' "
                    f"is not designed to have other labware placed on top of it (can_be_stacked_upon=False)."
                )

            # --- 4. Z-Overlap Check (Remains the same) ---
            for existing_lw, (min_z_exist, max_z_exist) in self.labware_stack.values():
                if max_z_exist > min_z and min_z_exist < max_z_new:
                    raise ValueError(
                        f"Z-Overlap error in slot '{self.slot_id}': Placement range Z:[{min_z}, {max_z_new}] "
                        f"overlaps with existing labware '{existing_lw.labware_id}' Z-range:[{min_z_exist}, {max_z_exist}]."
                    )

        # If all checks pass, the function returns silently (None).
        return


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
