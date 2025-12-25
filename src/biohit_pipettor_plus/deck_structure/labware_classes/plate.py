
from .labware import Labware
from ..serializable import register_class, Serializable
from .well import Well

from typing import Optional
import copy

@register_class
class Plate(Labware):

    def __init__(self, size_x: float,
            size_y: float,
            size_z: float,
            wells_x: int,
            wells_y: int,
            well: Well,
            add_height: float = -3,
            remove_height: float = -10,
            offset: tuple[float, float] = (0, 0),
            labware_id: str = None,
            position: tuple[float, float] = None,
            can_be_stacked_upon: bool = False):
        """
        Initialize a Plate instance.

        Parameters
        ----------
        size_x : float
            Width of the plate.
        size_y : float
            Depth of the plate.
        size_z : float
            Height of the plate.
        wells_x : int
            Number of wells in X direction.
        wells_y : int
            Number of wells in Y direction.
        add_height : float
            Height above the well bottom used when adding liquid (in mm).
        remove_height : float
            Height above the well bottom used when removing liquid (in mm).
        well : Well
            Template well to use for all wells in the plate.
        offset : tuple[float, float], optional
            Offset of the plate.
        labware_id : str, optional
            Unique ID for the plate.
        position : tuple[float, float], optional
            (x, y) position coordinates of the plate in millimeters.
        """
        super().__init__(size_x=size_x, size_y=size_y, size_z=size_z, offset=offset, labware_id=labware_id,
                         position=position, can_be_stacked_upon=can_be_stacked_upon)

        if wells_x <= 0 or wells_y <= 0:
            raise ValueError("wells_x and wells_y cannot be negative or 0")

        self._columns = wells_x
        self._rows = wells_y
        self.add_height = add_height
        self.remove_height = remove_height
        self.__wells: dict[tuple[int, int], Well] = {}
        self.well = well

        min_required_x = round((wells_x * well.size_x) + (2*abs(offset[0])),2)
        min_required_y = round((wells_y * well.size_y) +  (2*abs(offset[1])),2)

        if size_x < min_required_x:
            print("to fix size validation after taking real value from Tim")
            pass
            """raise ValueError(
                f"Plate width ({size_x}mm) is too small for {wells_x} wells of width {well.size_x}mm. "
                f"Minimum required: {min_required_x:.1f}mm (including offsets)"
            )
            """

        if size_y < min_required_y:
            raise ValueError(
                f"Plate height ({size_y}mm) is too small for {wells_y} wells of height {well.size_y}mm. "
                f"Minimum required: {min_required_y:.1f}mm (including offsets)"
            )

        if well.size_z > size_z:
            raise ValueError(
                f"Well height ({well.size_z}mm) exceeds plate height ({size_z}mm)"
            )

        self.place_wells()

    def place_wells(self):
        """Create wells across the grid using the template well."""
        for x in range(self._columns):
            for y in range(self._rows):
                well = copy.deepcopy(self.well)
                well.labware_id = f'{self.labware_id}_{x}:{y}'
                well.row = y
                well.column = x
                self.__wells[(x, y)] = well

    def get_wells(self) -> dict[tuple[int, int], Well]:  # ✅ Correct type
        """Get all wells in the plate."""
        return self.__wells

    def get_all_children(self) -> list[Well]:
        return list(self.__wells.values())

    def get_child_at(self, column: int, row: int) -> Optional[Well]:
        return self.__wells.get((column, row))

    def get_well_at(self, column: int, row: int) -> Optional[Well]:
        """
                Get the well at a specific position.

                Parameters
                ----------
                column : int
                    Column index
                row : int
                    Row index

                Returns
                -------
                Optional[Well]
                    The well at the position, or None if not found
                """
        return self.__wells.get((column, row))

    def get_wells_in_column(self, column: int) -> list[Well]:
        """Get all wells in a specific column."""
        wells = []
        for row in range(self._rows):
            well = self.get_well_at(column, row)
            if well:
                wells.append(well)
        return wells

    def get_wells_in_row(self, row: int) -> list[Well]:
        """Get all wells in a specific row."""
        wells = []
        for col in range(self._columns):
            well = self.get_well_at(col, row)
            if well:
                wells.append(well)
        return wells

    def get_state_snapshot(self) -> dict:
        """Return deep copy of all wells' state"""
        return {
            'wells': {pos: well.get_state_snapshot()
                      for pos, well in self._Plate__wells.items()}
        }

    def restore_state_snapshot(self, snapshot: dict) -> None:
        """Restore all wells' state from snapshot"""
        for pos, well_snapshot in snapshot['wells'].items():
            self._Plate__wells[pos].restore_state_snapshot(well_snapshot)

    def to_dict(self):
        """Serialize the Plate instance to a dictionary."""
        base = super().to_dict()
        base.update({
            "add_height": self.add_height,
            "remove_height": self.remove_height,
            "wells_x": self.wells_x,
            "wells_y": self.wells_y,
            "wells": {
                f"{col}:{row}": well.to_dict()
                for (col, row), well in self.__wells.items()
            }
        })
        return base

    @classmethod
    def _from_dict(cls, data: dict) -> "Plate":
        position = tuple(data["position"]) if data.get("position") else None
        wells_data = data.get("wells", {})

        if not wells_data:
            raise ValueError("Cannot deserialize Plate without wells data")

        # Get the first well as a template
        first_well_data = next(iter(wells_data.values()))
        template_well = Serializable.from_dict(first_well_data)

        # ADD: Pass well parameter!
        plate = cls(
            size_x=data["size_x"],
            size_y=data["size_y"],
            size_z=data["size_z"],
            offset=data["offset"],
            add_height=data["add_height"],
            remove_height=data["remove_height"],
            labware_id=data["labware_id"],
            wells_x=data["wells_x"],
            wells_y=data["wells_y"],
            can_be_stacked_upon=data.get("can_be_stacked_upon", False),
            well=template_well,
            position=position,
        )

        # Restore wells with their actual state
        for wid, wdata in wells_data.items():
            col, row = map(int, wid.split(':'))
            restored_well = Serializable.from_dict(wdata)
            plate._Plate__wells[(col, row)] = restored_well

        return plate

    @property
    def wells_x(self) -> int:
        """Number of wells in X direction (columns)"""
        return self._columns

    @property
    def wells_y(self) -> int:
        """Number of wells in Y direction (rows)"""
        return self._rows

    @property
    def grid_x(self) -> int:
        """Standard grid dimension (columns)"""
        return self._columns

    @property
    def grid_y(self) -> int:
        """Standard grid dimension (rows)"""
        return self._rows