
from biohit_pipettor_plus.deck_structure.labware_classes.labware import Labware
from biohit_pipettor_plus.deck_structure.serializable import register_class, Serializable
from biohit_pipettor_plus.deck_structure.labware_classes.reservoir import Reservoir

from typing import Optional
import copy

@register_class
class ReservoirHolder(Labware):
    def __init__(self, size_x: float, size_y: float, size_z: float, hooks_across_x: int, hooks_across_y: int, reservoir_template: Reservoir = None,
                remove_height: float = -45, add_height: float = 0, offset: tuple[float, float] = (0, 0),
                 labware_id: str = None, position: tuple[float, float] = None, can_be_stacked_upon: bool = False, x_spacing:float=None, y_spacing:float=None, each_tip_needs_separate_item = False):
        """
        Initialize a ReservoirHolder instance that can hold multiple reservoirs.

        Parameters
        ----------
        size_x : float
            Width of the ReservoirHolder in millimeters.
        size_y : float
            Depth of the ReservoirHolder in millimeters.
        size_z : float
            Height of the ReservoirHolder in millimeters.
        hooks_across_x : int
            Number of hooks along X-axis.
        hooks_across_y : int
            Number of hooks along Y-axis (rows of hooks).
        add_height : float
            relative height at which liquid is dispensed
        remove_height: float
            relative height at which liquid is aspirated
        reservoir_template : reservoir
            example or individual reservoir that will be placed across all hooks.
        labware_id : str, optional
            Unique ID for the holder.
        position : tuple[float, float], optional
            (x, y) position coordinates of the ReservoirHolder in millimeters.
            If None, position is not set.
        x_spacing : float, optional
            Distance along x-axis between hooks in millimeters.
        y_spacing : float, optional
            Distance along y-axis between hooks in millimeters.
        each_tip_needs_separate_item : bool, optional
            If True, each pipette tip needs its own reservoir.
            If False, all tips can access the same reservoir (default: False).

        """
        super().__init__(size_x, size_y, size_z, offset, labware_id, position, can_be_stacked_upon=can_be_stacked_upon)

        if hooks_across_x <= 0 or hooks_across_y <= 0:
            raise ValueError("hooks_across_x and hooks_across_y cannot be negative or 0")

        self.add_height = add_height
        self.remove_height = remove_height
        self._columns = hooks_across_x
        self._rows = hooks_across_y
        self.total_hooks = hooks_across_x * hooks_across_y
        self._each_tip_needs_separate_item = each_tip_needs_separate_item
        self.x_spacing = x_spacing
        self.y_spacing = y_spacing

        # Initialize empty hooks - maps hook_id to reservoir (or None if empty)
        # hook_id ranges from 1 to total_hooks
        self.__hook_to_reservoir: dict[int, Optional[Reservoir]] = {
            i: None for i in range(1, self.total_hooks + 1)
        }

        # Place reservoirs to holder if provided
        if reservoir_template is not None:
            self.place_reservoirs(reservoir_template)

    def each_tip_needs_separate_item(self) -> bool:
        return self._each_tip_needs_separate_item  # Reservoirs are large, all tips fit in one

    def hook_id_to_position(self, hook_id: int) -> tuple[int, int]:
        """
        Convert hook_id to (col, row) position.

        Parameters
        ----------
        hook_id : int
            Hook ID (1-indexed, 1 to total_hooks)

        Returns
        -------
        tuple[int, int]
            (col, row) where col is 0 to hooks_across_x-1,
            row is 0 to hooks_across_y-1

        Example
        -------
        For hooks_across_x=3, hooks_across_y=2::

            hook_id: 1 2 3 4 5 6
            layout: [1 2 3]  <- row 0
                    [4 5 6]  <- row 1
        """
        if hook_id < 1 or hook_id > self.total_hooks:
            raise ValueError(f"hook_id {hook_id} out of range (1 to {self.total_hooks})")

        # Convert to 0-indexed
        idx = hook_id - 1
        row = idx // self._columns
        col = idx % self._columns
        return col, row

    def position_to_hook_id(self, col: int, row: int) -> int:
        """
        Convert (col, row) position to hook_id.

        Parameters
        ----------
        col : int
            Column (0 to hooks_across_x-1)
        row : int
            Row (0 to hooks_across_y-1)

        Returns
        -------
        int
            hook_id (1-indexed)
        """
        if col < 0 or col >= self._columns:
            raise ValueError(f"col {col} out of range (0 to {self._columns - 1})")
        if row < 0 or row >= self._rows:
            raise ValueError(f"row {row} out of range (0 to {self._rows - 1})")

        return row * self._columns + col + 1

    def get_reservoirs(self) -> list[Reservoir]:
        """Return list of all unique reservoirs (no duplicates)."""
        seen_ids = set()
        reservoirs = []
        for res in self.__hook_to_reservoir.values():
            if res is not None and res.labware_id not in seen_ids:
                seen_ids.add(res.labware_id)
                reservoirs.append(res)
        return reservoirs

    def get_hook_to_reservoir_map(self) -> dict[int, Optional[Reservoir]]:
        """Return the complete hook to reservoir mapping."""
        return self.__hook_to_reservoir

    def get_available_hooks(self) -> list[int]:
        """Return list of available (empty) hook IDs."""
        return [hook_id for hook_id, res in self.__hook_to_reservoir.items() if res is None]

    def get_all_children(self) -> list[Reservoir]:
        return self.get_reservoirs()

    def get_child_at(self, col: int, row: int) -> Optional[Reservoir]:
        # Convert grid (col, row) to hook_id (1-indexed)
        hook_id = self.position_to_hook_id(col, row)
        return self.__hook_to_reservoir.get(hook_id)

    def get_occupied_hooks(self) -> list[int]:
        """Return list of occupied hook IDs."""
        return [hook_id for hook_id, res in self.__hook_to_reservoir.items() if res is not None]

    def _validate_hooks_form_rectangle(self, hook_ids: list[int]) -> tuple[bool, int, int]:
        """
        Check if hook IDs form a rectangular grid.

        Returns
        -------
        tuple[bool, int, int]
            (is_valid, width, height) where width and height are in hook units
        """
        if not hook_ids:
            return False, 0, 0

        # Convert all hook_ids to (col, row) location
        location = [self.hook_id_to_position(hid) for hid in hook_ids]
        cols = [pos[0] for pos in location]
        rows = [pos[1] for pos in location]

        min_col, max_col = min(cols), max(cols)
        min_row, max_row = min(rows), max(rows)

        width = max_col - min_col + 1
        height = max_row - min_row + 1

        # Check if all location in the rectangle are present
        expected_location = {
            (c, r) for c in range(min_col, max_col + 1)
            for r in range(min_row, max_row + 1)
        }
        actual_location = set(location)

        is_valid = expected_location == actual_location
        return is_valid, width, height

    def place_reservoir(self, hook_ids: list[int], reservoir: Reservoir) -> None:
        """
        Place a single reservoir on specific hooks.

        Parameters
        ----------
        hook_ids : list[int] or int
            List of hook location to place the reservoir (must form a rectangle).
        reservoir : Reservoir
            Reservoir instance to place.

        Raises
        ------
        ValueError
            If hook_ids are invalid, don't form a rectangle, already occupied,
            or reservoir dimensions incompatible.
        """
        # Allow single int for backwards compatibility
        if isinstance(hook_ids, int):
            hook_ids = [hook_ids]

        if not hook_ids:
            raise ValueError("Must specify at least one hook_id")


        # Check if all hook_ids are valid and available
        for hook_id in hook_ids:

            if hook_id not in self.__hook_to_reservoir:
                raise ValueError(
                    f"Hook ID {hook_id} is invalid. Must be between 1 and {self.total_hooks}"
                )

            if self.__hook_to_reservoir[hook_id] is not None:
                raise ValueError(f"Hook {hook_id} is already occupied")

        # Check if hooks form a valid rectangle
        is_valid, width_hooks, height_hooks = self._validate_hooks_form_rectangle(hook_ids)
        if not is_valid:
            raise ValueError(
                f"Hook IDs {hook_ids} must form a rectangular grid"
            )

        # Calculate maximum dimensions per hook
        max_width_per_hook = self.size_x / self._columns
        max_height_per_hook = self.size_y / self._rows

        # Calculate available space for this reservoir
        max_width_for_reservoir = max_width_per_hook * width_hooks
        max_height_for_reservoir = max_height_per_hook * height_hooks

        # Check dimensional compatibility
        if reservoir.size_x > max_width_for_reservoir:
            raise ValueError(
                f"Reservoir width ({reservoir.size_x} mm) exceeds "
                f"available width ({max_width_for_reservoir:.2f} mm = "
                f"{max_width_per_hook:.2f} mm/hook × {width_hooks} hooks)"
            )
        if reservoir.size_y > max_height_for_reservoir:
            raise ValueError(
                f"Reservoir depth ({reservoir.size_y} mm) exceeds "
                f"available depth ({max_height_for_reservoir:.2f} mm = "
                f"{max_height_per_hook:.2f} mm/hook × {height_hooks} hooks)"
            )
        if reservoir.size_z > self.size_z:
            raise ValueError(
                f"Reservoir height ({reservoir.size_z} mm) exceeds "
                f"holder height ({self.size_z} mm)"
            )

        is_valid, error_msg = self.validate_multichannel_compatible(reservoir.size_y)
        if not is_valid:
            raise ValueError(error_msg)

        # Assign hook_ids and place reservoir. also find col and row
        reservoir.hook_ids = hook_ids
        positions = [self.hook_id_to_position(hid) for hid in hook_ids]
        cols = [pos[0] for pos in positions]
        rows = [pos[1] for pos in positions]
        reservoir.column = min(cols)  # Leftmost column
        reservoir.row = min(rows)  # Topmost row
        reservoir.width_hooks = width_hooks
        reservoir.height_hooks = height_hooks

        reservoir.labware_id = f"{self.labware_id}_{reservoir.column}:{reservoir.row}"

        for hook_id in hook_ids:
            self.__hook_to_reservoir[hook_id] = reservoir

    def place_reservoirs(self, reservoir_template: Reservoir) -> None:
        """
        allocate duplicate reservoir to all available hooks, unless specific hook id specified

            If hook_ids is specified, the reservoir will be placed there, given that position is empty
            Otherwise, calculates required hooks based on dimensions and allocates automatically.

        Raises
        ------
        ValueError
            If a specified hook_id is occupied, insufficient space, or
            reservoir parameters are invalid.
        """
        template = reservoir_template
        if template.hook_ids:
            hook_ids_to_use = template.hook_ids
            reservoir_copy = copy.deepcopy(template)
            self.place_reservoir(hook_ids_to_use, reservoir_copy)

        else:

            max_width_per_hook = self.size_x / self._columns
            max_height_per_hook = self.size_y / self._rows

            reservoir_width = template.size_x
            reservoir_height = template.size_y

            # Calculate minimum hooks needed based on dimensions
            min_hooks_x = int(reservoir_width / max_width_per_hook)
            if reservoir_width % max_width_per_hook > 0: min_hooks_x += 1

            min_hooks_y = int(reservoir_height / max_height_per_hook)
            if reservoir_height % max_height_per_hook > 0: min_hooks_y += 1

            hooks_x = min_hooks_x
            hooks_y = min_hooks_y

            # raises error if not even one placement is possible.
            if hooks_x > self._columns or hooks_y > self._rows:
                raise ValueError(
                    f"Placement Error: Required reservoir size is {hooks_x}x{hooks_y} hooks, "
                    f"but the ReservoirHolder is only {self._columns}x{self._rows}."
                )

            while True:
                hook_ids_to_use = None

                # Re-check available hooks for each placement attempt
                available = set(self.get_available_hooks())

                # Find the *first* available rectangular region of size hooks_x x hooks_y
                for start_row in range(self._rows - hooks_y + 1):
                    for start_col in range(self._columns - hooks_x + 1):

                        # Check if this rectangular block (starting at start_row, start_col)
                        # is entirely available (not occupied)
                        candidate_hooks = []
                        is_available = True

                        for r in range(start_row, start_row + hooks_y):
                            for c in range(start_col, start_col + hooks_x):
                                hook_id = self.position_to_hook_id(c, r)
                                if hook_id not in available:
                                    is_available = False
                                    break
                                candidate_hooks.append(hook_id)
                            if not is_available:
                                break

                        if is_available:
                            hook_ids_to_use = candidate_hooks
                            break
                    if hook_ids_to_use:
                        break

                # If we couldn't find a spot, we exit the loop
                if hook_ids_to_use is None:
                    break

                # --- Placement Execution for the Found Spot ---
                reservoir_copy = copy.deepcopy(template)
                self.place_reservoir(hook_ids_to_use, reservoir_copy)

    def remove_reservoir(self, hook_id: int) -> Reservoir:
        """
        Remove a reservoir from the holder.

        Parameters
        ----------
        hook_id : int
            Any hook ID occupied by the reservoir to remove

        Returns
        -------
        Reservoir
            The removed reservoir

        Raises
        ------
        ValueError
            If no reservoir at the specified hook
        """
        if hook_id not in self.__hook_to_reservoir:
            raise ValueError(f"Invalid hook_id {hook_id}")

        reservoir = self.__hook_to_reservoir[hook_id]
        if reservoir is None:
            raise ValueError(f"No reservoir at hook {hook_id}")

        # Clear all hooks occupied by this reservoir
        for hid in reservoir.hook_ids:
            self.__hook_to_reservoir[hid] = None

        return reservoir

    def add_content(self, hook_id: int, content: str, volume: float) -> None:
        """
        Add content to a reservoir at a specific hook.

        Parameters
        ----------
        hook_id : int
            Hook ID where the reservoir is located
        content : str
            Type of content to add (e.g., "PBS", "water")
        volume : float
            Volume to add (µL)

        Raises
        ------
        ValueError
            If no reservoir at hook or volume exceeds capacity
        """
        if hook_id not in self.__hook_to_reservoir or self.__hook_to_reservoir[hook_id] is None:
            raise ValueError(f"No reservoir at hook {hook_id}")
        self.__hook_to_reservoir[hook_id].add_content(content, volume)

    def remove_content(self, hook_id: int, volume: float, return_dict: bool = False) -> Optional[dict[str, float]]:
        """
        Remove content from a reservoir at a specific hook.

        Parameters
        ----------
        hook_id : int
            Hook ID where the reservoir is located
        volume : float
            Volume to remove (µL)
        return_dict : bool, optional
            If True, return a dictionary of removed content types and volumes (default: False)

        Returns
        -------
        Optional[dict[str, float]]
            If return_dict is True, returns dictionary mapping content types to removed volumes.
            Otherwise, returns None.

        Raises
        ------
        ValueError
            If no reservoir at hook or insufficient volume
        """
        if hook_id not in self.__hook_to_reservoir or self.__hook_to_reservoir[hook_id] is None:
            raise ValueError(f"No reservoir at hook {hook_id}")
        return self.__hook_to_reservoir[hook_id].remove_content(volume, return_dict=return_dict)

    def get_waste_reservoirs(self) -> list[Reservoir]:
        """
        Get all unique reservoirs that contain 'waste' in any content type.

        Returns
        -------
        list[Reservoir]
            List of waste reservoirs
        """
        return [
            res for res in self.get_reservoirs()
            if any("waste" in content_type.lower() for content_type in res.content.keys())
        ]

    def get_reservoirs_by_content_type(self, content_type: str) -> list[Reservoir]:
        """
        Get all unique reservoirs that contain a specific content type.

        Parameters
        ----------
        content_type : str
            Content type to search for (case-insensitive)

        Returns
        -------
        list[Reservoir]
            List of reservoirs containing this content type
        """
        return [
            res for res in self.get_reservoirs()
            if res.has_content_type(content_type)
        ]

    def get_state_snapshot(self) -> dict:
        """Return deep copy of all reservoirs' state"""
        # Get unique reservoirs and snapshot each once
        snapshots = {}
        for reservoir in self.get_reservoirs():
            snapshots[reservoir.labware_id] = reservoir.get_state_snapshot()
        return {'reservoirs': snapshots}

    def restore_state_snapshot(self, snapshot: dict) -> None:
        """Restore all reservoirs' state from snapshot"""
        reservoir_snapshots = snapshot['reservoirs']
        # Restore each unique reservoir
        for reservoir in self.get_reservoirs():
            if reservoir.labware_id in reservoir_snapshots:
                reservoir.restore_state_snapshot(reservoir_snapshots[reservoir.labware_id])

    def to_dict(self) -> dict:
        """Serialize the ReservoirHolder instance to a dictionary."""
        base = super().to_dict()

        # Store only unique reservoirs with their hook_ids
        unique_reservoirs = {}
        for res in self.get_reservoirs():
            key = f"{res.column}:{res.row}"  # ✅ Consistent with Plate/PipetteHolder
            unique_reservoirs[key] = res.to_dict()

        base.update({
            "add_height": self.add_height,
            "remove_height": self.remove_height,
            "hooks_across_x": self.hooks_across_x,
            "hooks_across_y": self.hooks_across_y,
            "each_tip_needs_separate_item": self._each_tip_needs_separate_item,
            "reservoirs": unique_reservoirs,
            "x_spacing": self.x_spacing,
            "y_spacing": self.y_spacing,
        })
        return base

    @classmethod
    def _from_dict(cls, data: dict) -> "ReservoirHolder":
        """Deserialize a ReservoirHolder instance from a dictionary."""
        # Safely handle position deserialization
        position = tuple(data["position"]) if data.get("position") else None

        reservoir_holder = cls(
            size_x=data["size_x"],
            size_y=data["size_y"],
            size_z=data["size_z"],
            can_be_stacked_upon=data.get("can_be_stacked_upon", False),
            add_height = data["add_height"],
            remove_height = data["remove_height"],
            offset=data["offset"],
            hooks_across_x=data["hooks_across_x"],
            hooks_across_y=data.get("hooks_across_y", 1),  # Default to 1 for backwards compatibility
            each_tip_needs_separate_item=data.get("each_tip_needs_separate_item", False),
            labware_id=data["labware_id"],
            reservoir_template=None,
            position=position,
            x_spacing=data.get("x_spacing", None),
            y_spacing=data.get("y_spacing", None),
        )

        # Restore reservoirs
        reservoirs_data = data.get("reservoirs", {})
        for res_data in reservoirs_data.values():
            reservoir = Serializable.from_dict(res_data)
            # Place on the hooks specified in hook_ids
            if reservoir.hook_ids:
                reservoir_holder.place_reservoir(reservoir.hook_ids, reservoir)

        return reservoir_holder

    @property
    def hooks_across_x(self) -> int:
        return self._columns

    @property
    def hooks_across_y(self) -> int:
        return self._rows

    @property
    def grid_x(self) -> int:
        return self._columns

    @property
    def grid_y(self) -> int:
        return self._rows
