from typing import Tuple, List, Dict
from .labware import Labware, ReservoirHolder, Reservoir, Plate, PipetteHolder
from .serializable import Serializable, register_class

@register_class
class Position_allocator:

    def calculate_multi(
        self,
        lw: Labware,
        x_corner: float,
        y_corner: float,
        x_spacing: float ,
        y_spacing: float,
        rows : float,
        columns : float,
        ):
        """
        Generate grid positions for labware containers inside a slot.

        Parameters
        ----------
        x_corner : float
            X coordinate of the slot's corner.
        y_corner : float
            Y coordinate of the slot's corner.
        lw : Labware
            Labware object to place.
        x_spacing : float
            Distance between containers along X.
        y_spacing : float
            Distance between containers along Y.
        rows: float
            Number of rows in the labware.
        columns: float
            Number of columns in the labware.
        """
        positions = []

        rows = rows
        columns = columns
        offset_x, offset_y = lw.offset

        """
            if x and y spacing is None -: 
                x spacing =  (size_x of the parent labware - offset*2 (from both sides)) / lw.rows
                y spacing = (size_y of the parent labware - offset*2 (from both sides)) / lw.columns
        """

        if x_spacing is None or y_spacing is None:
            try:
                x_spacing = round((lw.size_x - 2 * offset_x) / (columns - 1), 2)
                y_spacing = round((lw.size_y - 2 * offset_y) / (rows - 1), 2)
            except Exception:
                x_spacing = 0
                y_spacing = 0

            # Ensure spacing is never negative
            if x_spacing < 0:
                x_spacing = 0
            if y_spacing < 0:
                y_spacing = 0

            print(f"x_spacing: {x_spacing}, y_spacing: {y_spacing}")


        for i in range(rows):
            for j in range(columns):
                x_pos = x_corner + j * x_spacing
                y_pos = y_corner + i * y_spacing
                location = (f"{j},{i}")
                positions.append((x_pos, y_pos,location))

        # Special handling for ReservoirHolder labware

        if isinstance(lw, ReservoirHolder):
            self.update_reservoir_positions(lw, positions)

        if isinstance(lw, Plate):
            self.update_plate_positions(lw, positions)

        if isinstance(lw, PipetteHolder):
            self.update_PipetteHolder_positions(lw, positions)

    def update_reservoir_positions(
            self,
            holder: ReservoirHolder,
            positions: list[tuple[float, float, str]]  # positions from calculate_multi
    ) -> None:
        """
        Update the position of reservoirs based on occupied hooks.

        Parameters
        ----------
        holder : ReservoirHolder
            The ReservoirHolder object containing reservoirs and hook mapping.
        positions : list[tuple[float, float, str]]
            List of all hook positions as (x, y, location_id).
            location_id is optional metadata.
        """
        hook_to_res = holder.get_hook_to_reservoir_map()  # dict[int, Optional[Reservoir]]
        # Build a mapping: reservoir -> list of hook positions
        reservoir_positions: dict[Reservoir, list[tuple[float, float]]] = {}

        for hook_id, res in hook_to_res.items():
            if res is not None:
                # hook_id is 1-indexed; positions list is 0-indexed
                idx = hook_id - 1
                x, y, _ = positions[idx]
                if res not in reservoir_positions:
                    reservoir_positions[res] = []
                reservoir_positions[res].append((x, y))

        # Update reservoir positions
        for res, hooks_pos in reservoir_positions.items():
            if len(hooks_pos) == 1:
                res.position = hooks_pos[0]
            else:
                # Compute center of multiple hooks
                xs, ys = zip(*hooks_pos)
                center_x = round((sum(xs) / len(xs)),2)
                center_y = round((sum(ys) / len(ys)),2)
                res.position = (center_x, center_y)

    def update_plate_positions(
            self,
            plate: Plate,
            positions: list[tuple[float, float, str]]  # positions from calculate_multi
    ) -> None:
        """
        Update the position of wells in a plate based on their grid layout.

        Parameters
        ----------
        plate : Plate
            The Plate object containing wells.
        positions : list[tuple[float, float, str]]
            List of all well positions as (x, y, location_id).
            location_id format is "col,row" (e.g., "0,0", "1,2").
        """
        wells = plate.get_wells()  # dict[str, Well or None]

        for well_id, well in wells.items():
            if well is not None:
                # Parse well_id which is in format "column:row" (e.g., "0:0", "1:2")
                try:
                    col, row = map(int, well_id.replace("well_", "").split(":"))
                except (ValueError, AttributeError):
                    continue  # Skip invalid well IDs

                # Calculate position index in the grid
                # The positions list is organized by rows then columns
                idx = row * plate.wells_x + col

                if idx < len(positions):
                    x_base, y_base, _ = positions[idx]

                    # Add the first_well_xy offset to get the actual well center
                    well.position = (x_base , y_base)

    def update_PipetteHolder_positions(
            self,
            holder: PipetteHolder,
            positions: list[tuple[float, float, str]]  # positions from calculate_multi
    ) -> None:
        """
        Update the position of individual pipette holders based on their grid layout.

        Parameters
        ----------
        holder : PipetteHolder
            The PipetteHolder object containing individual holder positions.
        positions : list[tuple[float, float, str]]
            List of all holder positions as (x, y, location_id).
            location_id format is "col,row" (e.g., "0,0", "1,2").
        """
        # Get the individual holders from the PipetteHolder
        individual_holders = holder.get_individual_holders()  # dict[str, IndividualPipetteHolder or None]

        for holder_id, individual_holder in individual_holders.items():
            if individual_holder is not None:
                # Parse holder_id which is in format "holder_col:row" (e.g., "holder_0:0", "holder_1:2")
                try:
                    col, row = map(int, holder_id.replace("holder_", "").split(":"))
                except (ValueError, AttributeError):
                    continue  # Skip invalid holder IDs

                # Calculate position index in the grid
                # The positions list is organized by rows then columns
                idx = row * holder.holders_across_x + col

                if idx < len(positions):
                    x_pos, y_pos, _ = positions[idx]
                    individual_holder.position = (x_pos, y_pos)