from biohit_pipettor_plus.deck_structure.labware_classes import *
from biohit_pipettor_plus.deck_structure.serializable import register_class


@register_class
class PositionAllocator:

    def calculate_multi(
            self,
            lw: Labware,
            x_corner: float,
            y_corner: float,
            rows: int,
            columns: int,
    ):
        """
        Generate grid positions for labware containers inside a slot.

        Parameters
        ----------
        x_corner : float
            X coordinate of the slot's corner. Left
        y_corner : float
            Y coordinate of the slot's corner. Top
        lw : Labware
            Labware object to place.
        rows: float
            Number of rows in the labware.
        columns: float
            Number of columns in the labware.
        """
        positions = []
        rows = int(rows)
        columns = int(columns)
        offset_x, offset_y = lw.offset

        if lw.x_spacing is None:
            # Handle single column case (no horizontal spacing needed)
            if columns == 1:
                lw.x_spacing = 0
            else:
                lw.x_spacing = round((lw.size_x - 2 * offset_x) / (columns - 1), 2)
                # Ensure spacing is never negative
                if lw.x_spacing < 0:
                    lw.x_spacing = 0

        if lw.y_spacing is None:
            # Handle single row case (no vertical spacing needed)
            if rows == 1:
                lw.y_spacing = 0
            else:
                lw.y_spacing = round((lw.size_y - 2 * offset_y) / (rows - 1), 2)
                # Ensure spacing is never negative
                if lw.y_spacing < 0:
                    lw.y_spacing = 0

        print(f"labware : {lw.labware_id} x_spacing: {lw.x_spacing}, y_spacing: {lw.y_spacing}")

        for i in range(rows):
            for j in range(columns):
                x_pos = x_corner - j * lw.x_spacing
                y_pos = y_corner + i * lw.y_spacing
                location = f"{j},{i}"
                positions.append((x_pos, y_pos, location))

        # Special handling for labware which contain labwares
        if isinstance(lw, ReservoirHolder):
            self.update_reservoir_positions(lw, positions)

        if isinstance(lw, Plate):
            self.update_plate_positions(lw, positions)

        if isinstance(lw, PipetteHolder):
            self.update_pipetteholder_positions(lw, positions)

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
                hook_x, hook_y = hooks_pos[0]  # Single hook
            else:
                # Multiple hooks - find average
                xs, ys = zip(*hooks_pos)
                hook_x = round((sum(xs) / len(xs)), 2)
                hook_y = round((sum(ys) / len(ys)), 2)

            # Step 2: Add half the reservoir size to get center + any offset
            center_x = round(hook_x - (res.size_x  / 2) - res.offset[0], 2)
            center_y = round(hook_y + (res.size_y / 2) + res.offset[1], 2)
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
        """
        wells = plate.get_wells()  # dict[str, Well or None]

        for well_id, well in wells.items():
            if well is not None and well.column is not None and well.row is not None:
                # Use the well's column and row attributes directly
                col = well.column
                row = well.row

                # Calculate position index in the grid
                # The positions list is organized by rows then columns
                idx = row * plate.wells_x + col

                if idx < len(positions):
                    x_pos, y_pos, _ = positions[idx]
                    # Add half of well size to get center position
                    center_x = round(x_pos - (well.size_x / 2) - well.offset[0], 2)
                    center_y = round(y_pos + (well.size_y / 2) + well.offset[1], 2)
                    well.position = (center_x, center_y)

    def update_pipetteholder_positions(
            self,
            holder: PipetteHolder,
            positions: list[tuple[float, float, str]]  # positions from calculate_multi
    ) -> None:
        """
        Update the position of individual pipette holders based on their grid layout.

        Parameters
        ---------
        holder : PipetteHolder
            The PipetteHolder object containing individual holder positions.
        positions : list[tuple[float, float, str]]
            List of all holder positions as (x, y, location_id).
        """
        individual_holders = holder.get_individual_holders()  # dict[str, IndividualPipetteHolder or None]

        for holder_id, individual_holder in individual_holders.items():
            if individual_holder is not None and individual_holder.column is not None and individual_holder.row is not None:
                col = individual_holder.column
                row = individual_holder.row

                # Calculate position index in the grid
                # The positions list is organized by rows then columns
                idx = row * holder.holders_across_x + col

                x_pos, y_pos, _ = positions[idx]
                # Add half of holder size to get center position
                center_x = round(x_pos - (individual_holder.size_x / 2) - individual_holder.offset[0], 2)
                center_y = round(y_pos + (individual_holder.size_y / 2) + individual_holder.offset[1], 2)
                individual_holder.position = (center_x, center_y)