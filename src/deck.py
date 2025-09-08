from .slot import Slot
from .labware import Labware

class Deck:
    def __init__(self, range_x: tuple[int, int], range_y: tuple[int, int]):
        self.range_x = range_x #(min, max)
        self.range_y = range_y #(min, max)

        self.used_pos_x: list[tuple] = [range_x]
        self.used_pos_y: list[tuple] = [range_y]

        self.__slots: dict[Slot] = {}
        self.__labware: dict[Labware] = {}

    def add_slot(self, slot: Slot, slot_id: str):
        """
        Adds a slot to the Deck. Checks if the area of the new slot is free to use and inside the
        range of the Deck.
        """
        if slot_id in self.slots:
            raise ValueError(f"Slot-ID '{slot_id}' does already exist in this Deck.")

        if not self._is_within_range(slot):
            raise ValueError(
                f"Slot {slot_id}is not in the of this deck"
                f"x={self.range_x}, y={self.range_y}"
            )
        for existing_id, existing_slot in self.slots.items():
            if self._overlaps(slot, existing_slot):
                raise ValueError(
                    f"Slot {slot_id} does overlap with existing slot: {existing_id}."
                )
        self.slots[slot_id] = slot

    def add_labware(self, labware: Labware, slot_id: str):
        """adds labware to specific slot"""

        if not isinstance(labware, Labware):
            raise TypeError(f"Object {labware} is not a Labwear.")

        if slot_id not in self.slots:
            raise ValueError(f"Slot '{slot_id}' does not exist.")

        slot: Slot = self.__slots[slot_id]

        if slot.labware is not None:
            raise ValueError(f"'{slot_id}' allready has an assigned labwear: {slot.labware}.")

        if not slot.is_compatible_labware(labware = labware):
            raise ValueError(f"{slot.labware} does not fit into: '{slot_id}' .")

        slot.labware = labware

    def _is_within_range(self, slot, Slot):
        """checks if the slot is within the range of the deck"""
        return (
                self.range_x[0] <= slot.range_x[0]
                and slot.range_x[1] <= self.range_x[1]
                and self.range_y[0] <= slot.range_y[0]
                and slot.range_y[1] <= self.range_y[1]
        )

    def _overlaps(self, s1: Slot, s2: Slot) -> bool:
        """checks if two slots, s1 and s2 do overlap"""

        return not (
                s1.range_x[1] <= s2.range_x[0]
                or s2.range_x[1] <= s1.range_x[0]
                or s1.range_y[1] <= s2.range_y[0]
                or s2.range_y[1] <= s1.range_y[0]
        )

    def to_dict(self):
        return {
            "range_x": list(self.range_x),
            "range_y": list(self.range_y),
            "slots": [slot.to_dict() for slot in self.slots],
            "labware": [lw.to_dict() for lw in self.labware]
        }

    @classmethod
    def from_dict(cls, data: dict):
        deck = cls(tuple(data["range_x"]), tuple(data["range_y"]))
        deck.slots = [Slot.from_dict(s) for s in data.get("slots", [])]
        deck.labware = [Labware.from_dict(lw) for lw in data.get("labware", [])]
        return deck
