from typing import Optional, Union
from .labware import Labware, Plate, ReservoirHolder, Reservoir, Well
from .slot import Slot

DYNAMIC_LOCATION_FINDER = 0

class PositionCalculator:
    """
    General position calculator for labware (plates, reservoirs, tips).
    Provides dynamic computation instead of hardcoded offsets.
    Locations are based on actuator values.
    """

    def __init__(self, x_corner: float, y_corner: float):
        """
        Initialize position calculator with corner reference point.

        Parameters
        ----------
        x_corner : float
            X coordinate of the reference corner (based on actuator values)
        y_corner : float
            Y coordinate of the reference corner (based on actuator values)

        Top right = (0,0)
        """
        self.x_corner = x_corner
        self.y_corner = y_corner

    def position_multi(
            self,
            container_x: int,
            container_y: int,
            step_x: float = 0,
            step_y: float = 0,
            offset: tuple[float, float] = (0, 0),
    ) -> dict[str, tuple[float, float]]:
        """
        In a multipipette setting, compute location of given labware and returns a dict.

        Parameters
        ----------
        container_x : int
            Number of containers (along x-axis)
        container_y : int
            Number of containers (along y-axis)
        step_x : float
            Spacing along X
        step_y : float
            Spacing along Y
        offset : tuple[float, float]
            (dx, dy) offset for first container

        Returns
        -------
        dict[str, tuple[float, float]]
            Dictionary mapping container_index to (x, y) position.
        """
        dx, dy = offset
        temp_dict = {}
        for row in range(container_y):
            for col in range(container_x):
                x = (self.x_corner + dx) + col * step_x
                y = (self.y_corner + dy) + row * step_y
                temp_dict[f"{col}:{row}"] = (x, y)
        return temp_dict


    def update_labware_positions_multi(
            labware: Labware,
            slot: Slot,
            container_x: Optional[int] = None,
            container_y: Optional[int] = None,
            step_x: Optional[float] = None,
            step_y: Optional[float] = None,
            offset: tuple[float, float] = (0, 0),
    ) -> None:
        """
        Update position attributes for all containers within a labware based on its slot.

        This function calculates the corner position from the slot, creates a PositionCalculator,
        and updates the position attribute of all containers (wells, reservoirs, etc.) within
        the labware.

        Parameters
        ----------
        labware : Labware
            The labware object whose container positions need to be updated.
        slot : Slot
            The slot where the labware is placed.
        container_x : int, optional
            Number of containers along X-axis. Auto-detected for Plate and ReservoirHolder.
        container_y : int, optional
            Number of containers along Y-axis. Auto-detected for Plate and ReservoirHolder.
        step_x : float, optional
            Spacing between containers along X-axis. Auto-calculated if not provided.
        step_y : float, optional
            Spacing between containers along Y-axis. Auto-calculated if not provided.
        offset : tuple[float, float], optional
            (dx, dy) offset for the first container. Default is (0, 0).

        Raises
        ------
        ValueError
            If labware is not in the slot or required parameters cannot be determined.

        Examples
        --------
        >>> # For a plate
        >>> plate = Plate(...)
        >>> slot.place_labware(plate, min_z=0)
        >>> update_labware_positions_multi(plate, slot)

        >>> # For a reservoir holder with custom offset
        >>> res_holder = ReservoirHolder(...)
        >>> slot.place_labware(res_holder, min_z=0)
        >>> update_labware_positions_multi (res_holder, slot, offset=(5, 5))
        """
        # Verify labware is in slot
        if labware.labware_id not in slot.labware_stack:
            raise ValueError(
                f"Labware {labware.labware_id} not found in slot {slot.slot_id}"
            )

        # Get corner position from slot
        x_corner = slot.range_x[0]
        y_corner = slot.range_y[0]

        # Create position calculator
        calculator = PositionCalculator(x_corner, y_corner)

        # Handle different labware types
        if isinstance(labware, Plate):
            _update_plate_positions(labware, calculator, container_x, container_y,
                                    step_x, step_y, offset)
        elif isinstance(labware, ReservoirHolder):
            _update_reservoir_holder_positions(labware, calculator, container_x,
                                               container_y, step_x, step_y, offset)
        else:
            # Generic labware - just update its own position
            labware.position = (x_corner + offset[0], y_corner + offset[1])


    def _update_plate_positions(
            plate: Plate,
            calculator: PositionCalculator,
            container_x: Optional[int],
            container_y: Optional[int],
            step_x: Optional[float],
            step_y: Optional[float],
            offset: tuple[float, float],
    ) -> None:
        """
        Update positions for all wells in a plate.

        Parameters
        ----------
        plate : Plate
            Plate object to update
        calculator : PositionCalculator
            Position calculator with corner reference
        container_x : int, optional
            Number of wells along X. Uses plate.containers_x if None.
        container_y : int, optional
            Number of wells along Y. Uses plate.containers_y if None.
        step_x : float, optional
            Spacing along X. Auto-calculated from well size if None.
        step_y : float, optional
            Spacing along Y. Auto-calculated from well size if None.
        offset : tuple[float, float]
            Offset for first well position
        """
        # Auto-detect parameters from plate
        containers_x = container_x if container_x is not None else plate.containers_x
        containers_y = container_y if container_y is not None else plate.containers_y

        # Get first well to determine spacing
        wells = plate.get_containers()
        first_well = next((w for w in wells.values() if w is not None), None)

        if first_well is None:
            # No wells in plate, just update plate position
            plate.position = (calculator.x_corner + offset[0],
                              calculator.y_corner + offset[1])
            return

        # Auto-calculate step sizes from well dimensions if not provided
        if step_x is None:
            step_x = first_well.size_x
        if step_y is None:
            step_y = first_well.size_y

        # Use first_well_xy offset if available
        if hasattr(plate, 'first_well_xy') and plate.first_well_xy:
            offset = plate.first_well_xy

        # Calculate positions for all wells
        positions = calculator.position_multi(
            container_x=containers_x,
            container_y=containers_y,
            step_x=step_x,
            step_y=step_y,
            offset=offset,
        )

        # Update plate position
        plate.position = (calculator.x_corner + offset[0],
                          calculator.y_corner + offset[1])

        # Update each well's position
        for well_id, position in positions.items():
            if well_id in wells and wells[well_id] is not None:
                wells[well_id].position = position


    def _update_reservoir_holder_positions(
            res_holder: ReservoirHolder,
            calculator: PositionCalculator,
            container_x: Optional[int],
            container_y: Optional[int],
            step_x: Optional[float],
            step_y: Optional[float],
            offset: tuple[float, float],
    ) -> None:
        """
        Update positions for all reservoirs in a reservoir holder.
        For reservoirs spanning multiple hooks, position is set to the middle of the span.
        ASSUMES reservoirs are only spread in x-axis. If both,
        Parameters
        ----------
        res_holder : ReservoirHolder
            ReservoirHolder object to update
        calculator : PositionCalculator
            Position calculator with corner reference
        container_x : int, optional
            Number of hooks along X. Uses res_holder.hook_count if None.
        container_y : int, optional
            Number of hooks along Y. Always 1 for current implementation.
        step_x : float, optional
            Hook spacing along X. Auto-calculated if None.
        step_y : float, optional
            Spacing along Y. Defaults to 0 for single row.
        offset : tuple[float, float]
            Offset for first hook position
        """
        # Auto-detect parameters
        containers_x = container_x if container_x is not None else res_holder.hook_count
        containers_y = container_y if container_y is not None else 1  # Single row

        # Calculate hook spacing (step_x is same as hook spacing)
        if step_x is None:
            step_x = res_holder.size_x / res_holder.hook_count

        if step_y is None:
            step_y = 0  # Single row, no Y spacing

        # Calculate positions for all hooks
        hook_positions = calculator.position_multi(
            container_x=containers_x,
            container_y=containers_y,
            step_x=step_x,
            step_y=step_y,
            offset=offset,
        )

        # Update reservoir holder position
        res_holder.position = (calculator.x_corner + offset[0],
                               calculator.y_corner + offset[1])

        # Get unique reservoirs and update their positions
        reservoirs = res_holder.get_reservoirs()

        for reservoir in reservoirs:
            if not reservoir.hook_ids:
                continue

            # For multi-hook reservoirs, calculate center position
            if len(reservoir.hook_ids) > 1:
                # Get positions of all hooks this reservoir spans
                hook_xs = []
                hook_ys = []
                for hook_id in reservoir.hook_ids:
                    hook_key = f"{hook_id - 1}:0"  # hook_ids are 1-indexed, positions are 0-indexed
                    if hook_key in hook_positions:
                        x, y = hook_positions[hook_key]
                        hook_xs.append(x)
                        hook_ys.append(y)

                if hook_xs and hook_ys:
                    # Position at the center of the span
                    center_x = (min(hook_xs) + max(hook_xs)) / 2
                    center_y = sum(hook_ys) / len(hook_ys)
                    reservoir.position = (center_x, center_y)
            else:
                # Single hook reservoir
                hook_id = reservoir.hook_ids[0]
                hook_key = f"{hook_id - 1}:0"  # hook_ids are 1-indexed
                if hook_key in hook_positions:
                    reservoir.position = hook_positions[hook_key]


    def get_container_position(
            labware: Labware,
            container_id: str,
    ) -> Optional[tuple[float, float]]:
        """
        Get the position of a specific container within a labware.

        Parameters
        ----------
        labware : Labware
            The labware containing the container
        container_id : str
            ID of the container (well ID like "0:0" or hook_id for reservoirs)

        Returns
        -------
        tuple[float, float] or None
            (x, y) position of the container, or None if not found

        Examples
        --------
        >>> pos = get_container_position(plate, "2:3")
        >>> pos = get_container_position(res_holder, "1")
        """
        if isinstance(labware, Plate):
            wells = labware.get_containers()
            if container_id in wells and wells[container_id] is not None:
                return wells[container_id].position

        elif isinstance(labware, ReservoirHolder):
            hook_to_res = labware.get_hook_to_reservoir_map()
            try:
                hook_id = int(container_id)
                if hook_id in hook_to_res and hook_to_res[hook_id] is not None:
                    return hook_to_res[hook_id].position
            except ValueError:
                pass

        return None