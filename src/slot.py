from .labware import Labware

class Slot:
    def __init__(self, range_x: tuple[float, float], range_y: tuple[float, float],slot_id: str, labware: Labware = None):
        self.range_x = range_x #(min, max)
        self.range_y = range_y #(min, max)
        self.slot_id = slot_id

        self.labware: Labware = labware

    def place_labware(self, lw: Labware):
        if self.labware is not None:
            raise ValueError(f"Slot {self.slot_id} ist bereits mit {self.labware.name} belegt!")
        self.labware = lw

    def remove_labware(self):
        self.labware = None

    def is_compatible_labware(self, labware: Labware):
        return (abs(self.range_x[0]- self.range_x[1]) >= labware.size_x
            and abs(self.range_y[0] - self.range_y[1]) >= labware.size_x)

    def to_dict(self):
        return {
            "slot_id": self.slot_id,
            "range_x": list(self.range_x),
            "range_y": list(self.range_y),
            "labware": self.labware.to_dict() if self.labware else None
        }

    @classmethod
    def from_dict(cls, data: dict):
        slot = cls(data["slot_id"], tuple(data["range_x"]), tuple(data["range_y"]))
        if data.get("labware"):
            slot.labware = Labware.from_dict(data["labware"])
        return slot