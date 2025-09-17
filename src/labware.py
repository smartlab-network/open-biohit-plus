import uuid
from .serializable import Serializable, register_class

@register_class
class Labware(Serializable):
    """Base class with auto registry for subclasses."""
    registry: dict[str, type] = {}

    def __init_subclass__(cls, **kwargs):
        """Automatically register subclasses by their class name."""
        super().__init_subclass__(**kwargs)
        Labware.registry[cls.__name__] = cls

    def __init__(self, size_x: float, size_y: float, size_z: float, labware_id: str = None):
        self.size_x = size_x
        self.size_y = size_y
        self.size_z = size_z
        self.labware_id = labware_id or f"labware_{uuid.uuid4().hex}"

    def to_dict(self) -> dict:
        return {
            "labware_id": self.labware_id,
            "class": self.__class__.__name__,
            "size_x": self.size_x,
            "size_y": self.size_y,
            "size_z": self.size_z,
        }

    @classmethod
    def _from_dict(cls, data: dict) -> "Labware":
        class_name = data.get("class", "Labware")
        target_cls = Labware.registry.get(class_name)
        if not target_cls:
            raise ValueError(f"Unknown Labware class: {class_name}")
        return target_cls._from_dict(data)  # delegate to subclass

    @classmethod
    def _from_dict(cls, data: dict) -> "Labware":
        """
        Base reconstruction (can be overridden by subclasses).
        """
        return cls(
            size_x=data["size_x"],
            size_y=data["size_y"],
            size_z=data["size_z"],
            labware_id=data["labware_id"],
        )

class Trash(Labware):
    def __init__(self, labware_id: str = None):
        super().__init__(size_x=0, size_y=0, size_z=0, labware_id=labware_id)

    def _from_dict(cls, data: dict) -> "Trash":
        return cls(labware_id=data["labware_id"])

@register_class
class Plate(Labware):
    def __init__(self, size_x, size_y, size_z, wells_x, wells_y, first_well_xy, labware_id: str = None):
        super().__init__(size_x, size_y, size_z, labware_id)
        self.wells_x = wells_x
        self.wells_y = wells_y
        self.first_well_xy = first_well_xy

    def to_dict(self):
        return {
            "class": self.__class__.__name__,
            "size_x": self.size_x,
            "size_y": self.size_y,
            "size_z": self.size_z,
            "wells_x": self.wells_x,
            "wells_y": self.wells_y,
            "first_well_xy": self.first_well_xy,
            "labware_id": self.labware_id
        }

    @classmethod
    def _from_dict(cls, data: dict) -> "Plate":
        return cls(
            size_x=data["size_x"],
            size_y=data["size_y"],
            size_z=data["size_z"],
            wells_x=data["wells_x"],
            wells_y=data["wells_y"],
            first_well_xy=tuple(data["first_well_xy"]),
            labware_id=data["labware_id"],
        )


class PipetteHolder(Labware):
    def __init__(self, labware_id: str = None):
        super().__init__(size_x=20, size_y=20, size_z=50, labware_id=labware_id)

    @classmethod
    def _from_dict(cls, data: dict) -> "PipetteHolder":
        return cls(labware_id=data["labware_id"])
