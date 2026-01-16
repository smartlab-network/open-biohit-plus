
from biohit_pipettor_plus.deck_structure.slot import Slot
from biohit_pipettor_plus.deck_structure.labware_classes import *
from biohit_pipettor_plus.deck_structure.serializable import Serializable, register_class

from typing import Optional


@register_class
class Deck(Serializable):
    """
    Represents the Deck of a Pipettor. The Deck can contain multiple slots,
    each of which can hold multiple Labware objects stacked vertically.

    Attributes
    ---------
    deck_id : str
        Unique identifier for the deck instance.
    range_x : tuple[int, int]
        Minimum and maximum x coordinates of the deck.
    range_y : tuple[int, int]
        Minimum and maximum y coordinates of the deck.
    slots : dict[str, Slot]
        Dictionary mapping slot IDs to Slot objects.
    labware : dict[str, Labware]
        Dictionary mapping labware IDs to Labware objects.
    range_z : float, optional
            Maximum vertical range of the deck (mm). This is the total Z-axis travel
            from top (pipettor home) to bottom (deck surface).
    """

    def __init__(self, range_x: tuple[int, int], range_y: tuple[int, int], deck_id: str, range_z : float = 500):
        self.deck_id = deck_id
        self.range_x = range_x
        self.range_y = range_y
        self.range_z = range_z

        self.slots: dict[str, Slot] = {}           # store Slot objects
        self.labware: dict[str, Labware] = {}     # global access to Labware objects

    def add_slots(self, slots: list[Slot]):
        """
        Add a Slot to the Deck after validating range and overlap.

        Parameters
        ----------
        slots : list of slots
            The slot to add to the deck.
        Raises
        ------
        ValueError
            If slot ID already exists, is out of deck range, or overlaps an existing slot.
        """

        for slot in slots:
            if not isinstance(slot, Slot):
                raise TypeError(f"Object {slot} is not a Slot instance.")
            slot_id = slot.slot_id

            if slot_id in self.slots:
                raise ValueError(f"Slot-ID '{slot_id}' already exists in this Deck.")

            if not self._is_within_range(slot):
                raise ValueError(
                    f"Slot '{slot_id}' is outside the deck range "
                    f"x={self.range_x}, y={self.range_y}"
                )

            for existing_id, existing_slot in self.slots.items():
                if self._overlaps(slot, existing_slot):
                    raise ValueError(
                        f"Slot '{slot_id}' overlaps with existing slot: '{existing_id}'."
                    )
            self.slots[slot_id] = slot

    def remove_slot(self, slot_id: str, unplace_labware: bool = False):
        """
        Remove a Slot from the Deck.

        Parameters
        ----------
        slot_id : str
            The ID of the slot to remove.
        unplace_labware : bool
            If True, unplace (remove) all labware contained within the slot first.
            If False (default), raise an error if the slot contains labware.

        Returns
        -------
        list[Labware]
            A list of Labware objects that were unplaced (if unplace_labware is True).
        """
        # Check if slot exists
        if slot_id not in self.slots:
            raise ValueError(f"Slot '{slot_id}' does not exist in the deck.")

        slot = self.slots[slot_id]
        unplaced_labware_list = []

        # Check if slot has any labware stacked
        if slot.labware_stack:
            if not unplace_labware:
                labware_ids = list(slot.labware_stack.keys())
                raise ValueError(
                    f"Cannot remove slot '{slot_id}' because it still contains labware: {labware_ids}. "
                    f"Use remove_slot(..., unplace_labware=True) to proceed."
                )
            else:
                # UNPLACE ALL CONTAINED LABWARE
                lw_ids_to_remove = list(slot.labware_stack.keys())  # Must copy
                lw_ids_to_remove.reverse() #ensures sequential removal

                for lw_id in lw_ids_to_remove:
                    # Use the new remove_labware function
                    labware = self.remove_labware(lw_id)
                    unplaced_labware_list.append(labware)

                # The slot's labware_stack is now guaranteed to be empty due to remove_labware calls.

        # Remove slot from deck's registry
        del self.slots[slot_id]

        # Reset slot position
        slot.position = None
        print(f"✓ Removed slot '{slot_id}' from deck.")
        return slot, unplaced_labware_list  # Return the slot and any unplaced labware

    def add_labware(self, labware: Labware, slot_id: str, min_z: float):
        """
        Add a Labware to a specific Slot at a specific Z position.

        Parameters
        ----------
        labware : Labware
            Labware object to place.
        slot_id : str
            ID of the slot where the labware will be placed.
        min_z : float
            Starting Z coordinate within the slot.
        Raises
        ------
        TypeError
            If the object is not a Labware instance.
        ValueError
            If the slot does not exist, labware ID already exists, or labware does not fit in the slot.
        """
        if not isinstance(labware, Labware):
            raise TypeError(f"Object {labware} is not a Labware instance.")

        if slot_id not in self.slots:
            raise ValueError(f"Slot '{slot_id}' does not exist.")

        # CHECK FOR DUPLICATE LABWARE ID
        if labware.labware_id in self.labware:
            existing_slot = self.get_slot_for_labware(labware.labware_id)
            raise ValueError(
                f"Labware ID '{labware.labware_id}' already exists in the deck "
                f"(in slot '{existing_slot}'). Each labware must have a unique ID."
            )

        slot: Slot = self.slots[slot_id]

        # Place labware in the slot stack
        slot._place_labware(lw=labware, min_z=min_z)

        # allocation position to labware on deck.
        slot._allocate_position(labware)

        # store in deck's global labware dict
        self.labware[labware.labware_id] = labware

    def remove_labware(self, labware_id: str) -> Labware:
        """
        Remove a Labware from its Slot and the Deck.
        Only the topmost labware in a slot's stack can be removed.
        Returns the Labware object for reuse or deletion.
        """
        if labware_id not in self.labware:
            raise ValueError(
                f"Labware '{labware_id}' not found in deck. "
                f"Cannot remove labware that was never added."
            )

        labware = self.labware[labware_id]

        # Find the actual slot containing the labware
        slot_id = self.get_slot_for_labware(labware_id)

        if not slot_id:
            raise ValueError(f"Internal error: Labware '{labware_id}' is placed but has no slot association.")

        slot = self.slots[slot_id]

        #topmost level removal
        stack_keys = list(slot.labware_stack.keys())
        if not stack_keys:
            # This should not happen assuming get_slot_for_labware works, but safe to check
            raise ValueError(f"Internal error: Slot '{slot_id}' is unexpectedly empty.")

        topmost_lw_id = stack_keys[-1]
        if labware_id != topmost_lw_id:
            # If the requested labware is NOT the topmost item, raise an error.
            raise ValueError(
                f"Cannot remove labware '{labware_id}'. It is not the topmost item in slot '{slot_id}'. "
                f"The topmost labware is '{topmost_lw_id}', which must be removed first."
            )

        # 1. Call the slot's internal removal method and Remove from global labware registry
        slot._remove_labware(labware_id)
        del self.labware[labware_id]

        # 2. Reset labware state
        labware.position = None

        if isinstance(labware, Plate):
            for well in labware.get_wells().values():
                if well:
                    well.position = None
        elif isinstance(labware, ReservoirHolder):
            for reservoir in labware.get_reservoirs():
                if reservoir:
                    reservoir.position = None
        elif isinstance(labware, PipetteHolder):
            for holder in labware.get_individual_holders().values():
                if holder:
                    holder.position = None

        print(f"✓ Removed '{labware_id}' from slot '{slot_id}'")
        return labware  # Return the object to the caller (gui)

    def _is_within_range(self, slot: Slot) -> bool:
        return (
            self.range_x[0] <= slot.range_x[0]
            and slot.range_x[1] <= self.range_x[1]
            and self.range_y[0] <= slot.range_y[0]
            and slot.range_y[1] <= self.range_y[1]
        )

    def _overlaps(self, s1: Slot, s2: Slot) -> bool:
        return not (
            s1.range_x[1] <= s2.range_x[0]
            or s2.range_x[1] <= s1.range_x[0]
            or s1.range_y[1] <= s2.range_y[0]
            or s2.range_y[1] <= s1.range_y[0]
        )

    def to_dict(self) -> dict:
        """
        Serialize the Deck to a dictionary for JSON export, including slots
        with stacked labware.

        Returns
        -------
        dict
            Dictionary containing deck attributes, slots, and labware.
        """
        return {
            "class": self.__class__.__name__,
            "deck_id": self.deck_id,
            "range_x": list(self.range_x),
            "range_y": list(self.range_y),
            "range_z": self.range_z,
            "slots": {sid: slot.to_dict() for sid, slot in self.slots.items()},
            "labware": {lid: lw.to_dict() for lid, lw in self.labware.items()},
        }

    @classmethod
    def _from_dict(cls, data: dict) -> "Deck":
        deck = cls(
            range_x=tuple(data["range_x"]),
            range_y=tuple(data["range_y"]),
            range_z=data["range_z"],
            deck_id=data["deck_id"]
        )

        # ✅ STEP 1: Create all labware FIRST
        for lid, lwdata in data.get("labware", {}).items():
            deck.labware[lid] = Serializable.from_dict(lwdata)

        # ✅ STEP 2: Create slots (without labware)
        for sid, sdata in data.get("slots", {}).items():
            deck.slots[sid] = Serializable.from_dict(sdata)

        # ✅ STEP 3: Populate slot labware_stack with existing labware objects
        for slot_id, slot in deck.slots.items():
            if hasattr(slot, '_pending_labware_data'):
                for lw_id, (lw_data, z_range) in slot._pending_labware_data.items():
                    if lw_id in deck.labware:
                        slot.labware_stack[lw_id] = (deck.labware[lw_id], tuple(z_range))
                    else:
                        print(f"⚠️ Warning: {lw_id} in slot but not in deck.labware")

                # Clean up temporary data
                delattr(slot, '_pending_labware_data')

        return deck
    def get_slot_for_labware(self, labware_id: str) -> Optional[str]:
            """
            Find the slot ID containing the given labware_id.
            Parameters
            ---------
            labware_id : str
                The ID of the labware to locate.

            Returns
            -------
            Optional[str]
                The slot ID if found, else None.
            """
            for slot_id, slot in self.slots.items():
                if labware_id in slot.labware_stack:
                    return slot_id
            return None