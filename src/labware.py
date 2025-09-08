class Labware:
    """Labware Base Class"""
    def __init__(self, size_x: float, size_y: float, size_z: float):
        self.size_x = size_x
        self.size_y = size_y
        self.size_z = size_z

    def to_dict(self) -> dict:
        return {
            "size_x": self.size_x,
            "size_y": self.size_y,
            "size_z": self.size_z
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Labware":
        return cls(
            size_x=data["size_x"],
            size_y=data["size_y"],
            size_z=data["size_z"]
        )

class Trash(Labware):
    def __init__(self):
        pass

class Plate(Labware):
    def __init__(self, size_x, size_y, size_z, wells_x, wells_y, first_well_xy:tuple[float, float]):
        super.__init__(size_x = size_x, size_y = size_y, size_z = size_z)
        self.wells_x = wells_x
        self.wells_y = wells_y
        self.first_well_xy = first_well_xy

class PipetteHolder(Labware):
    def __init__(self):
        pass
