from .pipettor import Pipettor
from typing import Literal, List, Optional, Union
from math import ceil

# from .cursor import total_volume
from .deck import Deck
from .slot import Slot
from .labware import Labware, Plate, Well, ReservoirHolder, Reservoir, PipetteHolder, IndividualPipetteHolder, \
    TipDropzone, Pipettors_in_Multi
from .errors import CommandFailed


class PipettorPlus(Pipettor):
    def __init__(self, tip_volume: Literal[200, 1000], *, multichannel: bool, initialize: bool = True, deck: Deck):
        """
        Interface to the Biohit Roboline pipettor with deck/slot/labware structure

        Parameters
        ----------
       tip_volume : Literal[200, 1000]
            The tip volume (must be 1000 if multichannel is True)
        multichannel : bool
            If True, it is assumed the device uses a multichannel pipet
        initialize : bool
            If True, the device will be initialized
        deck : Deck
            The deck containing slots and labware
                """
        super().__init__(tip_volume=tip_volume, multichannel=multichannel, initialize=initialize)
        self.deck = deck
        self.slots: dict[str, Slot] = deck.slots

        # Tip content tracking
        self.tip_count = 8
        self.has_tips = False
        self.tip_content: dict = {}  # Current content in tip as dict {content_type: volume}
        self.volume_present_in_tip: float = 0.0  # Volume remaining in tip
        self.change_tips = 0  # control if tips are to be changed

    def pick_multi_tips(self, pipette_holder: Labware, columns: Optional[List[int]] = None) -> None:
        """
        Pick tips from a PipetteHolder going through specified columns (right to left).

        Parameters
        ----------
        pipette_holder: str
            PipetteHolder labware
        columns : List[int], optional
            List of column indices to try. If None, uses all occupied columns.

        Raises
        ------
        ValueError
            If pipette holder not found or no tips available
        """

        if not self.multichannel:
            raise ValueError("pick_multi_tips requires multichannel pipettor")

        if self.has_tips:
            raise ValueError("pipettor already has tips")

        # Find the pipette holder
        if not isinstance(pipette_holder, PipetteHolder):
            raise ValueError("Pick tips only work on pipette_holders")

        if columns is None:
            columns = pipette_holder.get_occupied_columns()

        if not columns:
            raise ValueError(f"No occupied columns found in pipette holder {pipette_holder.labware_id}")

        print(f"pick_multi_tips: start, trying columns {columns}")

        for col in sorted(columns):  # ascending attempts to pick pipette
            # Get the position for the first row of this column
            holder_id = f'{pipette_holder.labware_id}_{col}:0'
            individual_holder = pipette_holder.get_individual_holders().get(holder_id)
            if individual_holder is None or not individual_holder.is_occupied:
                continue

            try:
                # Move to the tip position
                if individual_holder.position is None:
                    raise ValueError(f"Individual holder {holder_id} has no position set")

                x, y = individual_holder.position
                self.move_xy(x, y)

                # TODO understand height attribute
                self.move_z(22)  # pick_height
                self.pick_tip()

                # Mark all tips in this column as removed
                pipette_holder.remove_pipettes_from_columns([col])
                self.has_tips = True
                print(f"Picked up tips from column {col}")
                break

            except CommandFailed:
                print(f"Failed to pick tips from column {col}")
                continue
            finally:
                self.move_z(0)
        else:
            raise RuntimeError(f"Failed to pick tips from any of the specified columns {columns}")

    def return_multi_tips(self, pipette_holder: Labware, columns: Optional[List[int]] = None) -> None:
        """
        Return tips to PipetteHolder in available columns (left to right).

        Parameters
        ----------
        pipette_holder : str
            PipetteHolder labware
        columns : List[int], optional
            List of column indices to try for returning tips.
            If None, uses all available columns.

        Raises
        ------
        ValueError
            If pipette holder not found, no empty columns available, or no tips to return
        RuntimeError
            If failed to return tips to any available column

        Notes
        -----
        This function returns tips to the pipette holder if there are empty columns.
        It's useful for reusing tip positions instead of discarding to a dropzone.
        """

        if not self.multichannel:
            raise ValueError("return_multi_tips requires multichannel pipettor")

        if not self.has_tips:
            raise ValueError("No tips to return - pipettor is empty")

        if not isinstance(pipette_holder, PipetteHolder):
            raise ValueError("Pick tips only work with pipette_holders")

        if columns is None:
            columns = pipette_holder.get_available_columns()

        if not columns:
            raise ValueError(f"No empty columns found in pipette holder {pipette_holder.labware_id}")

        print(f"return_multi_tips: start, trying columns {columns}")

        for col in sorted(columns, reverse=True):  # attempts to return tips in descending order to available columns.
            # Get the position for the first row of this column
            holder_id = f'{pipette_holder.labware_id}_{col}:0'
            individual_holder = pipette_holder.get_individual_holders().get(holder_id)

            if individual_holder is None or individual_holder.is_occupied:
                continue

            try:
                # Move to the tip return position
                if individual_holder.position is None:
                    raise ValueError(f"Individual holder {holder_id} has no position set")

                x, y = individual_holder.position
                self.move_xy(x, y)
                # TODO Fix height
                self.move_z(22)  # Slightly above pick height
                self.eject_tip()

                # Mark all tips in this column as placed
                pipette_holder.place_pipettes_in_columns([col])
                self.initialize_tips()
                print(f"Returned tips to column {col}")
                break

            except Exception as e:
                print(f"Failed to return tips to column {col}: {e}")
                continue
            finally:
                self.move_z(0)
        else:
            raise RuntimeError(
                f"Failed to return tips to any available column {columns}. "
                f"Holder is full. Tips still attached to pipettor."
            )

    def discard_tips(self, tip_dropzone: Labware) -> None:
        """
               Discard tips to a TipDropzone.
               Parameters
               ----------
               tip_dropzone : labware
                    TipDropzone labware
               """

        if not self.has_tips:
            raise RuntimeError("No tips to discard")

        if not isinstance(tip_dropzone, TipDropzone):
            raise ValueError("discard_tips only works with TipDropzone")

        # Todo understand drop height
        x, y = tip_dropzone.position
        self.move_xy(x, y)
        self.move_z(tip_dropzone.drop_height_relative)
        self.eject_tip()
        self.initialize_tips()
        self.move_z(0)

    def replace_multi_tips(self, pipette_holder: Labware) -> None:
        """ Replace multiple tips. By return current tips to and picking new ones from the pipette_holder.
            Does not take tips from the column it returned to """
        if not isinstance(pipette_holder, PipetteHolder):
            raise ValueError("replace_multi_tips only works with PipetteHolder")

        if self.multichannel:
            """
                get a list of available columns -> Place tips back with .return_multi ->
                get a list of occupied columns -> Common column is the used column ->
                pretend to remove tips from used columns -> pick tips  with .pick_multi
                pretend to put tips back to used columns.``
            """
            available_columns = pipette_holder.get_available_columns()
            self.return_multi_tips(pipette_holder)
            occupied_columns = pipette_holder.get_occupied_columns()
            returned_column = list(set(available_columns) & set(occupied_columns))
            pipette_holder.remove_pipettes_from_columns(returned_column)
            self.pick_multi_tips(pipette_holder)
            pipette_holder.place_pipettes_in_columns(returned_column)

    def add_medium(self,
                   source: ReservoirHolder,
                   source_col_row: tuple[int, int],
                   destination: Plate,
                   volume_per_well: float,
                   dest_col_row: List[tuple[int, int]]) -> None:
        """
        Add medium from reservoir to plate wells.

        Parameters
        ----------
        source : ReservoirHolder
            Source reservoir holder
        source_col_row : tuple[int, int]
            Column and row index in reservoir holder (which reservoir to use)
        destination : Plate
            Destination plate
        volume_per_well : float
            Volume to add per well (µL)
        dest_col_row : List[tuple[int, int]]
            List of destination (column, row) tuples to dispense to.

        Example
        -------
        # Add 200µL medium from reservoir at (0,0) to plate positions
        pipettor.add_medium(reservoir_holder, (0,0), plate1, 200, [(0,0), (1,0), (2,0)])
        """

        if not self.multichannel:
            raise ValueError("add_medium requires multichannel pipettor")

        # Initial validation
        self.check_tips()
        self.check_col_row(source_col_row, source)
        self.check_col_row(dest_col_row, destination)

        # Calculate volumes for multichannel operation
        volume_per_destination = volume_per_well * self.tip_count  # total per destination column
        max_vol_per_aspirate = self.tip_volume * self.tip_count  # total capacity across all tips

        if volume_per_destination <= 0:
            raise ValueError("volume_per_well must be > 0")

        print(f"Transferring {volume_per_well}µL per well to {len(dest_col_row)} destinations")
        print(f"Max volume per aspirate: {max_vol_per_aspirate}µL")
        print(f"Volume per destination: {volume_per_destination}µL")

        # If a single destination needs more than a full load, handle per-destination multi-trips
        if volume_per_destination > max_vol_per_aspirate:
            for dest_pos in dest_col_row:
                remaining = volume_per_destination
                while remaining > 0:
                    vol = min(remaining, max_vol_per_aspirate)
                    self.suck(source, source_col_row, vol)
                    self.spit(destination, dest_pos, vol)
                    remaining -= vol
                    if remaining > 0:
                        print(f"Destination requires refill: {remaining}µL remaining")
            return

        # Otherwise, batch multiple destinations per aspirate without refills
        batch_size = max(1, int(max_vol_per_aspirate / volume_per_destination))
        print(f"Batch size (destinations per aspirate): {batch_size}")

        # Process in chunks
        idx = 0
        n = len(dest_col_row)
        while idx < n:
            chunk = dest_col_row[idx: min(idx + batch_size, n)]
            total_chunk_volume = len(chunk) * volume_per_destination
            volume_to_aspirate = min(total_chunk_volume, max_vol_per_aspirate)

            # Aspirate once for the entire chunk
            self.suck(source, source_col_row, volume_to_aspirate)

            # Dispense to each destination in the chunk
            for dest_pos in chunk:
                self.spit(destination, dest_pos, volume_per_destination)

            idx += len(chunk)

    def suck(self, source: Labware, source_col_row: tuple[int, int], volume: float) -> None:
        """
        Aspirate from a source labware.

        Parameters
        ----------
        source : Labware
            Source labware
        source_col_row : tuple[int, int]
            Column and row index in source labware
        volume : float
            Total volume to aspirate across all tips (µL)

        Raises
        ------
        ValueError
            If labware position is invalid or volume is negative
        """
        # Validation
        self.check_col_row(source_col_row, source)
        if volume <= 0:
            raise ValueError("Volume must be positive")

        # Check if labware supports content tracking
        has_content = (hasattr(source, 'content') and
                       hasattr(source, 'get_total_volume') and
                       hasattr(source, 'remove_content'))

        if has_content:
            source_col, source_row = source_col_row

            if self.multichannel:
                # For multichannel: handle content for all tip_count rows
                if hasattr(source, 'get_reservoirs'):
                    # Reservoir: usually one massive reservoir for all 8 tips
                    reservoirs = source.get_reservoirs()
                    source_id = f"{source.labware_id}_{source_col}:{source_row}"
                    source_item = None
                    for res in reservoirs:
                        if res.labware_id == source_id:
                            source_item = res
                            break
                    if source_item is None:
                        raise ValueError(f"Reservoir not found at position ({source_col}, {source_row})")

                    # Check if reservoir has enough content for all tips
                    available_volume = source_item.get_total_volume()
                    if available_volume < volume:
                        raise ValueError(
                            f"Insufficient volume in reservoir {source_id}. "
                            f"Available: {available_volume}µL, Requested: {volume}µL"
                        )

                    # Remove content from reservoir and get what was removed
                    removed_content = source_item.remove_content(volume)

                    # Add the removed content to tips
                    for content_type, volume_removed in removed_content.items():
                        if volume_removed > 0:
                            self.add_content(content_type, volume_removed)

                    # Move to reservoir position
                    if source_item.position is not None:
                        x, y = source_item.position
                        self.move_xy(x, y)
                        aspiration_height = source_item.size_z * 0.8
                        self.move_z(aspiration_height)
                        self.aspirate(volume)
                        self.move_z(0)

                elif hasattr(source, 'get_wells'):
                    # Plate: handle each well individually for each tip
                    wells_map = source.get_wells()
                    total_volume_available = 0
                    source_wells = []

                    # Collect all wells for this column across tip_count rows
                    for tip_idx in range(self.tip_count):
                        well_id = f"{source.labware_id}_{source_col}:{source_row + tip_idx}"
                        well = wells_map.get(well_id)
                        if well is None:
                            raise ValueError(f"Well not found at position ({source_col}, {source_row + tip_idx})")
                        source_wells.append(well)
                        total_volume_available += well.get_total_volume()

                    if total_volume_available < volume:
                        raise ValueError(
                            f"Insufficient volume in wells. "
                            f"Available: {total_volume_available}µL, Requested: {volume}µL"
                        )

                    # Distribute volume across wells proportionally
                    volume_per_well = volume / self.tip_count
                    for well in source_wells:
                        well_volume = min(volume_per_well, well.get_total_volume())
                        if well_volume > 0:
                            # Remove content from well and get what was removed
                            removed_content = well.remove_content(well_volume)

                            # Add the removed content to tips
                            for content_type, volume_removed in removed_content.items():
                                if volume_removed > 0:
                                    self.add_content(content_type, volume_removed)

                    # Move to first well position (multichannel covers the column)
                    first_well = source_wells[0]
                    if first_well.position is not None:
                        x, y = first_well.position
                        self.move_xy(x, y)
                        aspiration_height = first_well.remove_height
                        self.move_z(aspiration_height)
                        self.aspirate(volume)
                        self.move_z(0)
            else:
                # Single channel: handle one position
                source_id = f"{source.labware_id}_{source_col}:{source_row}"

                if hasattr(source, 'get_reservoirs'):
                    reservoirs = source.get_reservoirs()
                    source_item = None
                    for res in reservoirs:
                        if res.labware_id == source_id:
                            source_item = res
                            break
                    if source_item is None:
                        raise ValueError(f"Reservoir not found at position ({source_col}, {source_row})")
                elif hasattr(source, 'get_wells'):
                    wells_map = source.get_wells()
                    source_item = wells_map.get(source_id)
                    if source_item is None:
                        raise ValueError(f"Well not found at position ({source_col}, {source_row})")
                else:
                    source_item = source

                # Check if source has enough content
                available_volume = source_item.get_total_volume()
                if available_volume < volume:
                    raise ValueError(
                        f"Insufficient volume in {source_id}. "
                        f"Available: {available_volume}µL, Requested: {volume}µL"
                    )

                # Remove content from source and get what was removed
                removed_content = source_item.remove_content(volume)

                # Add the removed content to tips
                for content_type, volume_removed in removed_content.items():
                    if volume_removed > 0:
                        self.add_content(content_type, volume_removed)

                # Move to the position if available
                if hasattr(source_item, 'position') and source_item.position is not None:
                    x, y = source_item.position
                    self.move_xy(x, y)

                    if hasattr(source_item, 'remove_height'):
                        aspiration_height = source_item.remove_height
                    elif hasattr(source_item, 'size_z'):
                        aspiration_height = source_item.size_z * 0.8
                    else:
                        aspiration_height = 5

                    self.move_z(aspiration_height)
                    self.aspirate(volume)
                    self.move_z(0)

            # Update total volume present in tip
            self.volume_present_in_tip += volume

        print(f"  → Aspirated {volume}µL from {source.labware_id} at {source_col_row}")
        print(f"  → Tip content now: {self._get_tip_content_summary()}")
        print(f"  → Total volume in tips: {self.volume_present_in_tip}µL")

    def change_medium_multi(self):
        pass

    def dilute_multi(self):
        pass

    def spit_all(self):
        pass

    def spit(self, destination: Labware, dest_col_row: tuple[int, int], volume: float) -> None:
        """
        Dispense from tips to a destination labware position.

        Parameters
        ----------
        destination : Labware
            Destination labware
        dest_col_row : tuple[int, int]
            Column and row index in destination labware
        volume : float
            Total volume to dispense across all tips (µL)

        Behavior
        --------
        - Proportionally distributes the current tip content into the destination content
        - Removes the dispensed volume from tip_content proportionally
        - Moves to the destination position and performs a dispense
        """
        dest_col, dest_row = dest_col_row

        # Validation
        self.check_col_row(dest_col_row, destination)
        if volume <= 0:
            raise ValueError("Dispense volume must be positive")
        if self.volume_present_in_tip <= 0 or not self.tip_content:
            raise ValueError("No content in tips to dispense")
        if volume > self.volume_present_in_tip:
            raise ValueError(
                f"Insufficient volume in tips. Available: {self.volume_present_in_tip}µL, Requested: {volume}µL"
            )

        # Check if destination supports content tracking
        has_content = (hasattr(destination, 'content') and
                       hasattr(destination, 'get_total_volume') and
                       hasattr(destination, 'add_content'))

        if has_content:
            if self.multichannel:
                # For multichannel: handle content for all tip_count rows
                if hasattr(destination, 'get_reservoirs'):
                    # Reservoir: usually one massive reservoir for all 8 tips
                    reservoirs = destination.get_reservoirs()
                    dest_id = f"{destination.labware_id}_{dest_col}:{dest_row}"
                    dest_item = None
                    for res in reservoirs:
                        if res.labware_id == dest_id:
                            dest_item = res
                            break
                    if dest_item is None:
                        raise ValueError(f"Reservoir not found at position ({dest_col}, {dest_row})")

                    # Distribute content proportionally to reservoir
                    total_tip_volume_before = self.volume_present_in_tip
                    if total_tip_volume_before <= 0:
                        raise ValueError("Tips are empty; cannot dispense")

                    # Add content to reservoir proportionally
                    for content_type, content_volume in list(self.tip_content.items()):
                        if content_volume <= 0:
                            continue
                        proportion = content_volume / total_tip_volume_before
                        add_volume = volume * proportion
                        if add_volume > 0:
                            dest_item.add_content(content_type, add_volume)

                    # Move to reservoir position
                    if dest_item.position is not None:
                        x, y = dest_item.position
                        self.move_xy(x, y)
                        dispense_height = dest_item.size_z * 0.2
                        self.move_z(dispense_height)
                        self.dispense(volume)
                        self.move_z(0)

                elif hasattr(destination, 'get_wells'):
                    # Plate: handle each well individually for each tip
                    wells_map = destination.get_wells()
                    dest_wells = []

                    # Collect all wells for this column across tip_count rows
                    for tip_idx in range(self.tip_count):
                        well_id = f"{destination.labware_id}_{dest_col}:{dest_row + tip_idx}"
                        well = wells_map.get(well_id)
                        if well is None:
                            raise ValueError(f"Well not found at position ({dest_col}, {dest_row + tip_idx})")
                        dest_wells.append(well)

                    # Distribute volume across wells proportionally
                    total_tip_volume_before = self.volume_present_in_tip
                    if total_tip_volume_before <= 0:
                        raise ValueError("Tips are empty; cannot dispense")

                    volume_per_well = volume / self.tip_count
                    for well in dest_wells:
                        well_volume = min(volume_per_well, volume)  # Ensure we don't exceed total volume
                        if well_volume > 0:
                            # Add content to well proportionally
                            for content_type, content_volume in list(self.tip_content.items()):
                                if content_volume <= 0:
                                    continue
                                proportion = content_volume / total_tip_volume_before
                                add_volume = well_volume * proportion
                                if add_volume > 0:
                                    well.add_content(content_type, add_volume)

                    # Move to first well position (multichannel covers the column)
                    first_well = dest_wells[0]
                    if first_well.position is not None:
                        x, y = first_well.position
                        self.move_xy(x, y)
                        dispense_height = first_well.add_height
                        self.move_z(dispense_height)
                        self.dispense(volume)
                        self.move_z(0)
            else:
                # Single channel: handle one position
                dest_id = f"{destination.labware_id}_{dest_col}:{dest_row}"

                if hasattr(destination, 'get_reservoirs'):
                    reservoirs = destination.get_reservoirs()
                    dest_item = None
                    for res in reservoirs:
                        if res.labware_id == dest_id:
                            dest_item = res
                            break
                    if dest_item is None:
                        raise ValueError(f"Reservoir not found at position ({dest_col}, {dest_row})")
                elif hasattr(destination, 'get_wells'):
                    wells_map = destination.get_wells()
                    dest_item = wells_map.get(dest_id)
                    if dest_item is None:
                        raise ValueError(f"Well not found at position ({dest_col}, {dest_row})")
                else:
                    dest_item = destination

                # Distribute content proportionally to destination
                total_tip_volume_before = self.volume_present_in_tip
                if total_tip_volume_before <= 0:
                    raise ValueError("Tips are empty; cannot dispense")

                # Add content to destination proportionally
                for content_type, content_volume in list(self.tip_content.items()):
                    if content_volume <= 0:
                        continue
                    proportion = content_volume / total_tip_volume_before
                    add_volume = volume * proportion
                    if add_volume > 0:
                        dest_item.add_content(content_type, add_volume)

                # Move to the position if available
                if hasattr(dest_item, 'position') and dest_item.position is not None:
                    x, y = dest_item.position
                    self.move_xy(x, y)

                    if hasattr(dest_item, 'add_height'):
                        dispense_height = dest_item.add_height
                    elif hasattr(dest_item, 'size_z'):
                        dispense_height = dest_item.size_z * 0.2
                    else:
                        dispense_height = 5

                    self.move_z(dispense_height)
                    self.dispense(volume)
                    self.move_z(0)

            # Remove content from tips proportionally
            self.remove_content(volume)

        print(f"  → Dispensed {volume}µL to {destination.labware_id} at {dest_col_row}")
        print(f"  → Tip content now: {self._get_tip_content_summary()}")

    def home(self):
        self.move_z(0)
        self.move_xy(0, 0)

    def initialize_tips(self) -> None:
        """Clear tip content when tips are discarded."""
        self.has_tips = False
        self.tip_content = {}
        self.volume_present_in_tip = 0.0
        print(f"  → Tips discarded, content cleared")

    def add_content(self, content_type: str, volume: float) -> None:
        """
        Add content to the tips with intelligent mixing logic.

        When adding content to tips:
        - Same content type: volumes are combined
        - Different content type: tracked separately (but physically mixed)

        Note: Once liquids are mixed in tips, they cannot be separated.
        Removal is always proportional from all content types.

        Parameters
        ----------
        content_type : str
            Content to add (e.g., "PBS", "water", "sample")
        volume : float
            Volume to add (µL)

        Raises
        ------
        ValueError
            If adding volume would exceed tip capacity or volume is negative
        """
        if volume < 0:
            raise ValueError("Volume to add must be positive")

        if not content_type:
            raise ValueError("Content type cannot be empty")

        # Check if adding would exceed tip capacity
        max_tip_capacity = self.tip_volume * self.tip_count
        if self.volume_present_in_tip + volume > max_tip_capacity:
            raise ValueError(
                f"Overflow! Adding {volume}µL would exceed tip capacity of {max_tip_capacity}µL. "
                f"Current volume: {self.volume_present_in_tip}µL"
            )

        # Add content to dictionary
        if content_type in self.tip_content:
            self.tip_content[content_type] += volume
        else:
            self.tip_content[content_type] = volume

        # Update total volume present in tip
        self.volume_present_in_tip += volume

    def remove_content(self, volume: float) -> None:
        """
        Remove content from the tips proportionally.

        When content is removed from tips, it's removed proportionally from all
        content types since they are mixed together.

        Parameters
        ----------
        volume : float
            Volume to remove (µL)

        Raises
        ------
        ValueError
            If trying to remove more volume than available or volume is negative
        """
        if volume < 0:
            raise ValueError("Volume to remove must be positive")

        if self.volume_present_in_tip <= 0:
            raise ValueError("Cannot remove from empty tips")

        if volume > self.volume_present_in_tip:
            raise ValueError(
                f"Underflow! Cannot remove {volume}µL, only {self.volume_present_in_tip}µL available"
            )

        # Remove proportionally from all content types (since they're mixed)
        removal_ratio = volume / self.volume_present_in_tip

        # Remove proportionally from each content type
        content_types = list(self.tip_content.keys())
        for content_type in content_types:
            remove_amount = self.tip_content[content_type] * removal_ratio
            self.tip_content[content_type] -= remove_amount

            # Clean up zero or negative volumes (use epsilon for floating point comparison)
            if self.tip_content[content_type] <= 1e-6:
                del self.tip_content[content_type]

        # Update total volume present in tip
        self.volume_present_in_tip -= volume

    # Helper functions. Not necessarily available for GUI
    def _get_tip_content_summary(self) -> str:
        """
        Get a readable summary of tip content.
        Returns
        -------
        str
            Summary string like "PBS: 150µL, water: 100µL" or "empty"
        """
        if not self.tip_content or self.volume_present_in_tip <= 0:
            return "empty"

        parts = []
        for content_type, volume in self.tip_content.items():
            parts.append(f"{content_type}: {volume:.1f}µL")

        return ", ".join(parts)

    def get_tip_status(self) -> dict:
        """
        Get current tip status.

        Returns
        -------
        dict
            Dictionary with tip content and remaining volume information
        """
        return {
            "content_dict": self.tip_content.copy(),
            "volume_remaining": self.volume_present_in_tip,
            "is_empty": self.volume_present_in_tip <= 0,
            "content_summary": self._get_tip_content_summary()
        }

    def check_tips(self) -> None:
        """
        Check if tip change is required. if yes, do it.
        """

        # todo figure out how to provide labware id
        lw = self.find_labware_by_type("PipetteHolder")[0]  # Gets first PipetteHolder
        if self.change_tips and not self.has_tips:
            self.pick_multi_tips(lw)
        elif self.change_tips and self.has_tips:
            self.replace_multi_tips(lw)
        elif not self.has_tips:
            raise ValueError("No tips loaded. Pick tips first.")

    def check_col_row(self, col_row: Union[tuple[int, int], List[tuple[int, int]]], lw: Labware) -> None:
        """
        Raises ValueError if (col, row) are out of bounds of the labware.
        """

        # checks if labware has _columns & _rows
        if not (hasattr(lw, "_columns") and hasattr(lw, "_rows")):
            raise ValueError(
                f"Invalid Labware {lw}. Labware lacks _rows or _columns attributes. "
                f"Check implementation for ReservoirHolder, PipetteHolder, or Plate.")

        # coverts col_row types to list
        if isinstance(col_row, tuple):
            coordinates = [col_row]
        elif isinstance(col_row, list):
            coordinates = col_row
        else:
            raise TypeError(f"col_row must be a tuple or list of tuples, got {type(col_row)}")

        for coord in coordinates:
            # loops through each col, row. Raising value error if out of bound.
            col, row = coord
            if col < 0 or col >= lw._columns:
                raise ValueError(f"columns in ({coord}) must be between 0 and {lw._columns - 1}. Columns are 0 indexed")

            if row < 0 or row >= lw._rows:
                raise ValueError(f"rows in ({coord}) must be between 0 and {lw._rows - 1}. rows are 0 indexed")

    def find_labware_by_type(self, labware_type: str) -> list[Labware]:
        """
        Find a labware instance by its type name (case-sensitive).

        Parameters
        ----------
        labware_type : str
            The class name of the labware to find (e.g., "Plate", "ReservoirHolder", "PipetteHolder")
            Case-sensitive.

        Returns list of Labwares
            Any Labware instance of the specified type, placed in deck and slot.

        Raises ValueError
            If no labware of the specified type is found in the deck and placed in a slot.
        """
        # Iterate through all labware in the deck
        lw = []
        for labware_id, labware in self.deck.labware.items():
            # Check if the labware's class name matches the requested type (case-sensitive)
            if labware.__class__.__name__ == labware_type:
                # Check if this labware is placed in a slot
                slot_id = self.deck.get_slot_for_labware(labware_id)
                if slot_id is not None:
                    lw.append(labware)

        if not lw:
            raise ValueError(f"No labware found for type '{labware_type}'.")
        else:
            return lw