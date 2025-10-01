from typing import Tuple, List, Dict
from .labware import Labware, ReservoirHolder, Reservoir
from .serializable import Serializable, register_class

@register_class
class Position_allocator:

    def calculate_multi(
        self,
        lw: Labware,
        x_corner: float,
        y_corner: float,
        offset: Tuple[float, float],
        x_spacing: float,
        y_spacing: float,
        obj_across_x: int,
        obj_across_y: int):
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
        offset : (float, float)
            Offset (x, y) from the slot corner.
        x_spacing : float
            Distance between containers along X.
        y_spacing : float
            Distance between containers along Y.
        obj_across_x : int
            Number of wells/reservoirs/PipetteHolder along X axis.
        obj_across_y: int
            Number of wells/reservoirs/PipetteHolder along Y axis.

        """
        positions = []
        offset_x, offset_y = offset

        for i in range(obj_across_y):
            for j in range(obj_across_x):
                x_pos = x_corner + offset_x + j * x_spacing
                y_pos = y_corner + offset_y + i * y_spacing
                location = (f"{j},{i}")
                positions.append((x_pos, y_pos,location))

        # Special handling for ReservoirHolder labware

        if isinstance(lw, ReservoirHolder):
            self.update_reservoir_positions(lw, positions)

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
                center_x = sum(xs) / len(xs)
                center_y = sum(ys) / len(ys)
                res.position = (center_x, center_y)
