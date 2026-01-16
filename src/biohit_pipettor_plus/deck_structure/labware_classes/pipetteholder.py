
from biohit_pipettor_plus.deck_structure.labware_classes.labware import Labware
from biohit_pipettor_plus.deck_structure.serializable import register_class, Serializable
from biohit_pipettor_plus.deck_structure.labware_classes.individualpipetteholder import IndividualPipetteHolder

from biohit_pipettor_plus.pipettor_plus.config import load_config

from typing import Optional
import copy
import warnings

@register_class
class PipetteHolder(Labware):
    def __init__(self, size_x: float, size_y: float, size_z: float, holders_across_x: int, holders_across_y: int,
                 individual_holder: IndividualPipetteHolder, add_height: float = 0, remove_height : float = 0, offset: tuple[float, float] = (0, 0),
                 x_spacing: float = None, y_spacing: float = None, labware_id: str = None, position: tuple[float, float] = None, can_be_stacked_upon: bool = False,):
        """
        Initialize a PipetteHolder instance.

        Parameters
        ----------
        size_x : float
            Width of the pipette holder in millimeters.
        size_y : float
            Depth of the pipette holder in millimeters.
        size_z : float
            Height of the pipette holder in millimeters.
        holders_across_x : int
            Number of individual holder positions across X-axis.
        holders_across_y : int
            Number of individual holder positions across Y-axis.
        individual_holder : IndividualPipetteHolder
            Template for individual holder positions. If provided, copies will be created for each position in the grid.
        labware_id : str, optional
            Unique ID for the pipette holder.
        add_height : float
            Height above the well bottom used when adding liquid (in mm).
        remove_height : float
            Height above the well bottom used when removing liquid (in mm).
        x_spacing : float, optional
            Distance along x-axis between hooks in millimeters.
        y_spacing : float, optional
            Distance along y-axis between hooks in millimeters.
        position : tuple[float, float], optional
            (x, y) position coordinates of the pipette holder in millimeters.
            If None, position is not set.
        """

        super().__init__(size_x=size_x, size_y=size_y, size_z=size_z, offset=offset, labware_id=labware_id,
                         position=position, can_be_stacked_upon=can_be_stacked_upon)

        if holders_across_x <= 0 or holders_across_y <= 0:
            raise ValueError("holders_across_x and holders_across_y must be positive")

        self.add_height = add_height
        self.remove_height = remove_height
        self._columns = holders_across_x
        self._rows = holders_across_y
        self.__individual_holders: dict[tuple[int, int], IndividualPipetteHolder] = {}
        self.individual_holder = individual_holder
        self.x_spacing = x_spacing
        self.y_spacing = y_spacing

        cfg = load_config()
        self.tip_count = int(cfg["Pipettors_in_Multi"])

        min_required_x = round((holders_across_x * individual_holder.size_x) + (2*abs(offset[0])),2)
        min_required_y = round((holders_across_y * individual_holder.size_y) + (2*abs(offset[1])),2)

        if size_x < min_required_x:
            warnings.warn(
                 f"PipetteHolder width ({size_x}mm) is too small for {holders_across_x} holders of width {individual_holder.size_x}mm. "
                f"Minimum required: {min_required_x:.1f}mm (including offsets)",
                UserWarning,
                stacklevel=2
            )

        if size_y < min_required_y:
            warnings.warn(
                f"PipetteHolder height ({size_y}mm) is too small for {holders_across_y} holders of height {individual_holder.size_y}mm. "
                f"Minimum required: {min_required_y:.1f}mm (including offsets)",
                UserWarning,
                stacklevel=2
            )

        if individual_holder.size_z > size_z:
            raise ValueError(
                f"Individual holder height ({individual_holder.size_z}mm) exceeds PipetteHolder height ({size_z}mm)"
            )

        self.place_individual_holders()

    def place_individual_holders(self):
        """Create individual holder positions across the grid."""
        for x in range(self._columns):
            for y in range(self._rows):
                holder = copy.deepcopy(self.individual_holder)
                holder.labware_id = f'{self.labware_id}_{x}:{y}'
                holder.column = x
                holder.row = y
                self.__individual_holders[(x, y)] = holder

    def get_individual_holders(self) -> dict[tuple[int, int], IndividualPipetteHolder]:
        """Get all individual holder positions."""
        return self.__individual_holders

    def get_available_holders(self) -> list[IndividualPipetteHolder]:
        """
        Get all available (unoccupied) holder positions.

        Returns
        -------
        list[IndividualPipetteHolder]
            List of available holders.
        """
        return [holder for holder in self.__individual_holders.values()
                if holder and holder.is_available()]

    def get_occupied_holders(self) -> list[IndividualPipetteHolder]:
        """
        Get all occupied holder positions.

        Returns
        -------
        list[IndividualPipetteHolder]
            List of occupied holders.
        """
        return [holder for holder in self.__individual_holders.values()
                if holder and holder.is_occupied]

    def get_holder_at(self, column: int, row: int) -> Optional[IndividualPipetteHolder]:
        """
        Get the individual holder at a specific position.

        Parameters
        ----------
        column : int
            Column index
        row : int
            Row index

        Returns
        -------
        Optional[IndividualPipetteHolder]
            The holder at the position, or None if not found
        """
        return self.__individual_holders.get((column, row))

    def place_pipette_at(self, column: int, row: int) -> None:
        """
        Place a pipette at a specific position.

        Parameters
        ----------
        column : int
            Column index (0-indexed).
        row : int
            Row index (0-indexed).

        Raises
        ------
        ValueError
            If position is out of range, no holder exists, or position is occupied.
        """

        self.validate_col_row_or_raise([column], row)
        individual_holder = self.get_holder_at(column, row)

        if individual_holder is None:
            raise ValueError(
                f"No individual holder found at position {column}:{row}"
            )
        individual_holder.place_pipette()

    def remove_pipette_at(self, column: int, row: int) -> None:
        """
        Remove a pipette from a specific position.

        Parameters
        ----------
        column : int
            Column index (0-indexed).
        row : int
            Row index (0-indexed).

        Raises
        ------
        ValueError
            If position is out of range, no holder exists, or position is empty.
        """

        self.validate_col_row_or_raise([column], row)
        individual_holder = self.get_holder_at(column, row)

        if individual_holder is None:
            raise ValueError(
                f"No individual holder found at position {column}:{row}"
            )

        individual_holder.remove_pipette()

    def get_all_children(self) -> list[IndividualPipetteHolder]:
        return list(self.__individual_holders.values())

    def get_child_at(self, column: int, row: int) -> Optional[IndividualPipetteHolder]:
        return self.__individual_holders.get((column, row))

    def place_consecutive_pipettes_multi(self, columns: list[int], row: int = 0) -> None:
        """
        Place pipettes in consecutive positions within specified columns for multichannel pipettor.

        Parameters
        ----------
        columns : list[int]
            List of column indices (0-indexed) where pipettes should be placed.
        row : int, optional
            Starting row index (0-indexed). Pipettes will be placed from row to row + 7.
            Default is 0.

        Raises
        ------
        ValueError
            If any column index is out of range, row out of range, or if any position
            in the specified columns is already occupied.
        """

        self.validate_col_row_or_raise(columns, row, self.tip_count)

        # Check if all positions are available before placing
        for col in columns:
            for i in range(self.tip_count):
                current_row = row + i
                individual_holder = self.get_holder_at(col, current_row)

                if individual_holder is None:
                    raise ValueError(
                        f"No individual holder found at position {col}:{current_row}"
                    )

                if individual_holder.is_occupied:
                    raise ValueError(
                        f"Holder at position {col}:{current_row} is already occupied"
                    )

        # Place pipettes in all positions
        for col in columns:
            for i in range(self.tip_count):
                current_row = row + i
                individual_holder = self.get_holder_at(col, current_row)
                individual_holder.place_pipette()

    def remove_consecutive_pipettes_multi(self, columns: list[int], row: int = 0) -> None:
        """
        Remove pipettes from consecutive positions within specified columns for multichannel pipettor.

        Parameters
        ----------
        columns : list[int]
            List of column indices (0-indexed) where pipettes should be removed.
        row : int, optional
            Starting row index (0-indexed). Pipettes will be removed from row to row + 7.
            Default is 0.

        Raises
        ------
        ValueError
            If any column index is out of range, row out of range, or if any position
            in the specified columns is already empty.
        """

        self.validate_col_row_or_raise(columns, row, self.tip_count)

        # Check if all positions have pipettes before removing
        for col in columns:
            for i in range(self.tip_count):
                current_row = row + i
                individual_holder = self.get_holder_at(col, current_row)

                if individual_holder is None:
                    raise ValueError(
                        f"No individual holder found at position {col}:{current_row}"
                    )

                if not individual_holder.is_occupied:
                    raise ValueError(
                        f"Holder at position {col}:{current_row} is already empty"
                    )

        # Remove pipettes from all positions
        for col in columns:
            for i in range(self.tip_count):
                current_row = row + i
                individual_holder = self.get_holder_at(col, current_row)
                individual_holder.remove_pipette()

    def check_col_start_row_multi(self, col: int, start_row: int) -> str:
        """
        Check the occupancy status of 8 consecutive positions starting from (col, start_row).

        Parameters
        ----------
        col : int
            Column index
        start_row : int
            Starting row index

        Returns
        -------
        str
            Status of the 8 consecutive positions:
            - "FULLY_OCCUPIED": All 8 positions exist and are occupied
            - "FULLY_AVAILABLE": All 8 positions exist and are empty
            - "MIXED": All 8 positions exist but have mixed occupancy
            - "INVALID": One or more positions don't exist (out of bounds)
        """
        # Check if all positions exist
        if col < 0 or col >= self._columns:
            return "INVALID"
        if start_row < 0 or start_row + self.tip_count > self._rows:
            return "INVALID"

        # Check occupancy of all 8 positions
        occupied_count = 0
        for i in range(self.tip_count):
            current_row = start_row + i
            individual_holder = self.get_holder_at(col, current_row)

            if individual_holder is None:
                return "INVALID"

            if individual_holder.is_occupied:
                occupied_count += 1

        # Determine status
        if occupied_count == self.tip_count:
            return "FULLY_OCCUPIED"
        elif occupied_count == 0:
            return "FULLY_AVAILABLE"
        else:
            return "MIXED"

    def get_occupied_holder_multi(self) -> list[tuple[int, int]]:
        """
        Get all columns with starting rows where 8 consecutive occupied positions exist.
        No holder is reused - blocks are non-overlapping.
        """
        occupied_positions = []

        for col in range(self._columns):
            used_rows = set()

            for start_row in range(self._rows - self.tip_count + 1):
                if start_row in used_rows:
                    continue

                # Use helper function instead of manual checking
                status = self.check_col_start_row_multi(col, start_row)

                if status == "FULLY_OCCUPIED":
                    occupied_positions.append((col, start_row))
                    # Mark all rows in this block as used
                    for i in range(self.tip_count):
                        used_rows.add(start_row + i)

        return occupied_positions

    def get_available_holder_multi(self) -> list[tuple[int, int]]:
        """
        Get all columns with starting rows where 8 consecutive available positions exist.
        No holder is reused - blocks are non-overlapping.
        """
        available_positions = []

        for col in range(self._columns):
            used_rows = set()

            for start_row in range(self._rows - self.tip_count + 1):
                if start_row in used_rows:
                    continue

                status = self.check_col_start_row_multi(col, start_row)

                if status == "FULLY_AVAILABLE":
                    available_positions.append((col, start_row))
                    for i in range(self.tip_count):
                        used_rows.add(start_row + i)

        return available_positions

    def get_state_snapshot(self) -> dict:
        """Return deep copy of all holders' state"""
        return {
            'holders': {pos: holder.get_state_snapshot()
                        for pos, holder in self._PipetteHolder__individual_holders.items()}
        }

    def restore_state_snapshot(self, snapshot: dict) -> None:
        """Restore all holders' state from snapshot"""
        for pos, holder_snapshot in snapshot['holders'].items():
            self._PipetteHolder__individual_holders[pos].restore_state_snapshot(holder_snapshot)

    def to_dict(self) -> dict:
        """
        Serialize the PipetteHolder instance to a dictionary.

        Returns
        -------
        dict
            Dictionary representation of the pipette holder.
        """
        base = super().to_dict()
        base.update({
            "add_height": self.add_height,
            "remove_height": self.remove_height,
            "holders_across_x": self.holders_across_x,
            "holders_across_y": self.holders_across_y,
            "x_spacing": self.x_spacing,
            "y_spacing": self.y_spacing,
            "individual_holders": {
            f"{col}:{row}": holder.to_dict()
            for (col, row), holder in self.__individual_holders.items()
        }
        })
        return base

    @classmethod
    def _from_dict(cls, data: dict) -> "PipetteHolder":
        """Deserialize a PipetteHolder instance from a dictionary."""
        position = tuple(data["position"]) if data.get("position") else None

        holders_data = data.get("individual_holders", {})

        if not holders_data:
            raise ValueError("Cannot deserialize PipetteHolder without individual_holders data")

        # Get the first holder as a template
        first_holder_data = next(iter(holders_data.values()))
        template_holder = Serializable.from_dict(first_holder_data)

        # Create the PipetteHolder with the template
        holder = cls(
            size_x=data["size_x"],
            size_y=data["size_y"],
            size_z=data["size_z"],
            can_be_stacked_upon = data.get("can_be_stacked_upon", False),
            add_height=data["add_height"],
            remove_height=data["remove_height"],
            offset=data["offset"],
            labware_id=data["labware_id"],
            holders_across_x=data["holders_across_x"],
            holders_across_y=data["holders_across_y"],
            individual_holder=template_holder,
            position=position,
            x_spacing=data.get("x_spacing", None),
            y_spacing=data.get("y_spacing", None),
        )

        # Restore individual holders with tuple keys
        for hid, hdata in holders_data.items():
            # Parse "col:row" format from JSON
            col, row = map(int, hid.split(':'))
            restored_holder = Serializable.from_dict(hdata)
            holder._PipetteHolder__individual_holders[(col, row)] = restored_holder

        return holder
    @property
    def holders_across_x(self) -> int:
        """Alias for grid_x"""
        return self._columns

    @property
    def holders_across_y(self) -> int:
        """Alias for grid_y"""
        return self._rows

    @property
    def grid_x(self) -> int:
        """Standard grid dimension"""
        return self._columns

    @property
    def grid_y(self) -> int:
        """Standard grid dimension"""
        return self._rows
