from .slot import Slot
from .labware import Labware
from .serializable import Serializable, register_class
from typing import Optional


@register_class
class Deck(Serializable):
    """
    Represents the Deck of a Pipettor. The Deck can contain multiple slots,
    each of which can hold multiple Labware objects stacked vertically.

    Attributes
    ----------
    deck_id : str
        Unique identifier for the deck instance.
    range_x : tuple[int, int]
        Minimum and maximum x coordinates of the deck.
    range_y : tuple[int, int]
        Minimum and maximum y coordinates of the deck.
    used_pos_x : list[tuple]
        List of used x-ranges (reserved for future use).
    used_pos_y : list[tuple]
        List of used y-ranges (reserved for future use).
    slots : dict[str, Slot]
        Dictionary mapping slot IDs to Slot objects.
    labware : dict[str, Labware]
        Dictionary mapping labware IDs to Labware objects.
    """

    def __init__(self, range_x: tuple[int, int], range_y: tuple[int, int], deck_id: str):
        self.deck_id = deck_id
        self.range_x = range_x
        self.range_y = range_y

        self.used_pos_x: list[tuple] = [range_x]  # reserved x-ranges
        self.used_pos_y: list[tuple] = [range_y]  # reserved y-ranges

        self.slots: dict[str, Slot] = {}           # store Slot objects
        self.labware: dict[str, Labware] = {}     # global access to Labware objects

    def add_slots(self, slots: list[Slot]):
        """
        Add a Slot to the Deck after validating range and overlap.

        Parameters
        ----------
        slot : Slot
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
            If the slot does not exist or labware does not fit in the slot.
        """
        if not isinstance(labware, Labware):
            raise TypeError(f"Object {labware} is not a Labware instance.")

        if slot_id not in self.slots:
            raise ValueError(f"Slot '{slot_id}' does not exist.")

        slot: Slot = self.slots[slot_id]

        if not slot.is_compatible_labware(lw=labware, min_z=min_z):
            raise ValueError(
                f"Labware '{labware.labware_id}' does not fit in slot '{slot_id}' "
                f"at min_z={min_z}."
            )

        # Place labware in the slot stack
        slot.place_labware(lw=labware, min_z=min_z)

        # Optionally store in deck's global labware dict
        self.labware[labware.labware_id] = labware

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
            "slots": {sid: slot.to_dict() for sid, slot in self.slots.items()},
            "labware": {lid: lw.to_dict() for lid, lw in self.labware.items()},
        }

    @classmethod
    def _from_dict(cls, data: dict) -> "Deck":
        """
        Deserialize a Deck from a dictionary, restoring slots and stacked labware.

        Parameters
        ----------
        data : dict
            Dictionary containing deck, slot, and labware attributes.

        Returns
        -------
        Deck
            Reconstructed Deck instance.
        """
        deck = cls(tuple(data["range_x"]), tuple(data["range_y"]), deck_id=data["deck_id"])

        # Restore slots
        for sid, sdata in data.get("slots", {}).items():
            deck.slots[sid] = Serializable.from_dict(sdata)

        # Restore global labware references
        for lid, lwdata in data.get("labware", {}).items():
            deck.labware[lid] = Serializable.from_dict(lwdata)

        return deck

    def get_slot_for_labware(self, labware_id: str) -> Optional[str]:
            """
            Find the slot ID containing the given labware_id.
            Parameters
            ----------
            deck : Deck
                The Deck instance to search.
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