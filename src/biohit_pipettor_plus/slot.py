from .labware import Labware
from .serializable import Serializable, register_class

@register_class
class Slot(Serializable):
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
            "class": self.__class__.__name__,  # <--- hinzufügen
            "slot_id": self.slot_id,
            "range_x": list(self.range_x),
            "range_y": list(self.range_y),
            "labware": self.labware.to_dict() if self.labware else None
        }

    @classmethod
    def _from_dict(cls, data: dict) -> "Slot":
        labware = Serializable.from_dict(data["labware"]) if data.get("labware") else None
        return cls(
            range_x=tuple(data["range_x"]),
            range_y=tuple(data["range_y"]),
            slot_id=data["slot_id"],
            labware=labware
        )