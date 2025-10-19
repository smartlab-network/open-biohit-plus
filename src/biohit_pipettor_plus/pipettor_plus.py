from .pipettor import Pipettor
from typing import Literal, List, Optional
from math import ceil

from .deck import Deck
from .slot import Slot
from .labware import Labware, Plate, Well, ReservoirHolder, Reservoir, PipetteHolder, IndividualPipetteHolder, \
    TipDropzone, Pipettors_in_Multi
from .errors import CommandFailed


Change_Tips = 0
MAX_BATCH_SIZE = 5

class PipettorPlus(Pipettor):
    def __init__(self, tip_volume: Literal[200, 1000], *, multichannel: bool,  initialize: bool = True, deck: Deck):
        """
        Interface to the Biohit Robo pipettor with deck/slot/labware structure

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
        super().__init__(tip_volume=tip_volume, multichannel = multichannel, initialize=initialize)
        #super().__init__(tip_volume=tip_volume, initialize=initialize)  # ✅ Fixed
        #self.multichannel = multichannel  # ✅ Set it on self instead
        self._deck = deck
        self._slots: dict[str, Slot] = deck.slots

        #creates a dict of all tips, each tips having its own dict where content and volume in tip can be stored.
        self.tip_count = Pipettors_in_Multi if self.multichannel else 1
        self.tip_dict = {i: {} for i in range(0, self.tip_count)}
        self.has_tips = False
        self.change_tips = Change_Tips  # control if tips are to be changed

    def pick_tips(self, pipette_holder: PipetteHolder, list_col_row: List[tuple[int, int]] = None,) -> None:
        """
                Pick tips from a PipetteHolder.

                Parameters
                ----------
                pipette_holder : PipetteHolder
                    PipetteHolder labware containing tips
                list_col_row : List[tuple[int, int]], optional
                    List of (column, row) grid indices to try.
                    If None, automatically finds occupied grid locations.

                Raises
                ------
                ValueError
                    If pipettor already has tips or pipette holder not found
                """

        #check if tips already exist.
        if self.has_tips:
            raise ValueError("pipettor already has tips")

        if self.multichannel:
            self.pick_multi_tips(pipette_holder, list_col_row)
        else:
            self.pick_single_tip(pipette_holder, list_col_row)

    def pick_multi_tips(self, pipette_holder: PipetteHolder, list_col_row: List[tuple[int, int]] = None) -> None:
        """
        Pick tips from a PipetteHolder using multichannel pipettor.

        For multichannel, 8 consecutive tips are picked vertically.

        Parameters
        ----------
        pipette_holder : PipetteHolder
            PipetteHolder labware containing tips
        list_col_row : List[tuple[int, int]], optional
            List of (column, start_row) grid indices to try.
            start_row indicates where the first pipettor in multichannel would be positioned.
            If None, automatically finds all grid locations with 8 consecutive occupied tips.

        Raises
        ------
        ValueError
            If not a multichannel pipettor or no tips available
        RuntimeError
            If failed to pick tips from any specified grid location
        """
        if not self.multichannel:
            raise ValueError("pick_multi_tips requires multichannel pipettor")

        if list_col_row is None:
            occupied_col_row = pipette_holder.get_occupied_holder_multi()
            if not occupied_col_row:
                raise ValueError(
                    f"No occupied multichannel grid locations found in pipette holder {pipette_holder.labware_id}")
            list_col_row = occupied_col_row
            print(f"Auto-detected {len(list_col_row)} multichannel grid locations: {list_col_row}")

        if not list_col_row:
            raise ValueError(f"No col_row specified. list_col_row given : {list_col_row}")

        print(f"pick_multi_tips: start, trying grid locations {list_col_row}")

        for col, start_row in list_col_row:
            #checks the status of Individual pipette holders at  col_row
            status = pipette_holder.check_col_start_row_multi(col, start_row)

            if status == "INVALID":
                print(f"Grid location ({col}, {start_row}) is invalid, skipping")
                continue

            if status != "FULLY_OCCUPIED":
                print(f"Grid location ({col}, {start_row}) is not fully occupied (status: {status}), skipping")
                continue

            # All positions valid and occupied - get holders
            holders_to_use = [pipette_holder.get_holder_at(col, start_row + i)
                              for i in range(self.tip_count)]

            # All 8 holders are valid, attempt to pick tips
            try:
                # Move to the deck position of the first holder
                #todo
                first_holder = holders_to_use[0]
                if first_holder.position is None:
                    raise ValueError(f"Holder at grid location ({col}, {start_row}) has no position set")

                x, y = first_holder.position  #  position = deck coordinates
                self.move_xy(x, y)

                # Pick tips at the specified height
                # todo
                self.pick_tip(22)  # pick_height

                # Mark all 8 tips in this column as removed
                pipette_holder.remove_consecutive_pipettes_multi([col], start_row)
                self.has_tips = True

                print(f"✓ Successfully picked 8 tips from column {col}, rows {start_row} to {start_row + 7}")
                return  # Successfully picked, exit function

            except CommandFailed as e:
                print(f"✗ Failed to pick tips from column {col}, row {start_row}: {e}")
                continue
            finally:
                self.move_z(0)

        # If we got here, all attempts failed
        raise RuntimeError(
            f"Failed to pick tips from any of the specified locations {list_col_row}. "
        )

    def pick_single_tip(self, pipette_holder: PipetteHolder, list_col_row: List[tuple[int, int]] = None) -> None:
        """Pick a single tip from a PipetteHolder using single-channel pipettor."""
        if self.multichannel:
            raise ValueError("pick_single_tip requires single-channel pipettor")

        if list_col_row is None:
            # Use existing method!
            occupied_holders = pipette_holder.get_occupied_holders()
            if not occupied_holders:
                raise ValueError(
                    f"No occupied tips found in pipette holder {pipette_holder.labware_id}")

            list_col_row = [(h.column, h.row) for h in occupied_holders]
            print(f"Auto-detected {len(list_col_row)} occupied tip positions")

        if not list_col_row:
            raise ValueError(f"No col_row specified. list_col_row given: {list_col_row}")

        print(f"pick_single_tip: start, trying grid locations {list_col_row}")

        for col, row in list_col_row:
            holder = pipette_holder.get_holder_at(col, row)

            if holder is None:
                print(f"Grid location ({col}, {row}) has no holder, skipping")
                continue

            if not holder.is_occupied:
                print(f"Grid location ({col}, {row}) is empty, skipping")
                continue

            try:
                if holder.position is None:
                    print(f"Holder at grid location ({col}, {row}) has no position set, skipping")
                    continue

                x, y = holder.position
                self.move_xy(x, y)
                self.pick_tip(22)

                holder.is_occupied = False
                self.has_tips = True

                print(f"✓ Successfully picked tip from column {col}, row {row}")
                return

            except CommandFailed as e:
                print(f"✗ Failed to pick tip from column {col}, row {row}: {e}")
                continue
            finally:
                self.move_z(0)

        raise RuntimeError(
            f"Failed to pick tip from any of the specified locations {list_col_row}."
        )

    def return_tips(self, pipette_holder: PipetteHolder, list_col_row: List[tuple[int, int]] = None) -> None:
        """
                        return tips to PipetteHolder.
        """

        if not self.has_tips:
            raise ValueError("pipettor have no tips to return")

        if self.multichannel:
            self.return_multi_tips(pipette_holder, list_col_row)
        else:
            self.return_single_tip(pipette_holder, list_col_row)

    def return_multi_tips(self, pipette_holder: PipetteHolder, list_col_row: List[tuple[int, int]] = None) -> None:
        """
        Return tips to a PipetteHolder using multichannel pipettor.

        For multichannel, 8 consecutive tips are returned vertically.

        Parameters
        ----------
        pipette_holder : PipetteHolder
            PipetteHolder labware to return tips to
        list_col_row : List[tuple[int, int]], optional
            List of (column, start_row) grid indices to try.
            start_row indicates where the first pipettor in multichannel would be positioned.
            If None, automatically finds all grid locations with 8 consecutive empty positions.

        Raises
        ------
        ValueError
            If not a multichannel pipettor or no tips to return
        RuntimeError
            If failed to return tips to any specified grid location
        """
        if not self.multichannel:
            raise ValueError("return_multi_tips requires multichannel pipettor")

        if not self.has_tips:
            raise ValueError("No tips to return - pipettor is empty")

        if list_col_row is None:
            available_col_row = pipette_holder.get_available_holder_multi()
            if not available_col_row:
                raise ValueError(
                    f"No available multichannel grid locations found in pipette holder {pipette_holder.labware_id}")
            list_col_row = available_col_row
            print(f"Auto-detected {len(list_col_row)} available multichannel grid locations: {list_col_row}")

        if not list_col_row:
            raise ValueError(f"No col_row specified. list_col_row given: {list_col_row}")

        print(f"return_multi_tips: start, trying grid locations {list_col_row}")

        for col, start_row in list_col_row:
            # Check the status of positions
            status = pipette_holder.check_col_start_row_multi(col, start_row)

            if status == "INVALID":
                print(f"Grid location ({col}, {start_row}) is invalid, skipping")
                continue

            if status != "FULLY_AVAILABLE":
                print(f"Grid location ({col}, {start_row}) is not fully available (status: {status}), skipping")
                continue

            # All positions valid and available - get holders
            holders_to_use = [pipette_holder.get_holder_at(col, start_row + i)
                              for i in range(self.tip_count)]

            # Attempt to return tips
            try:
                first_holder = holders_to_use[0]
                if first_holder.position is None:
                    print(f"Holder at grid location ({col}, {start_row}) has no position set, skipping")
                    continue

                x, y = first_holder.position  # deck coordinates
                self.move_xy(x, y)

                # Return tips at the specified height
                self.move_z(22)  # return_height
                self.eject_tip()

                # Mark all 8 positions in this column as occupied
                pipette_holder.place_consecutive_pipettes_multi([col], start_row)
                self.initialize_tips()

                print(f"✓ Successfully returned 8 tips to column {col}, rows {start_row} to {start_row + 7}")
                return  # Successfully returned, exit function

            except CommandFailed as e:
                print(f"✗ Failed to return tips to column {col}, row {start_row}: {e}")
                continue
            finally:
                self.move_z(0)

        # If we got here, all attempts failed
        raise RuntimeError(
            f"Failed to return tips to any of the specified locations {list_col_row}. "
            f"Tips still attached to pipettor."
        )

    def return_single_tip(self, pipette_holder: PipetteHolder, list_col_row: List[tuple[int, int]] = None) -> None:
        """Return a single tip to a PipetteHolder using single-channel pipettor."""
        if self.multichannel:
            raise ValueError("return_single_tip requires single-channel pipettor")

        if not self.has_tips:
            raise ValueError("No tip to return - pipettor is empty")

        if list_col_row is None:
            # Use existing method!
            available_holders = pipette_holder.get_available_holders()
            if not available_holders:
                raise ValueError(
                    f"No available positions found in pipette holder {pipette_holder.labware_id}")

            list_col_row = [(h.column, h.row) for h in available_holders]
            print(f"Auto-detected {len(list_col_row)} available tip positions")

        if not list_col_row:
            raise ValueError(f"No col_row specified. list_col_row given: {list_col_row}")

        print(f"return_single_tip: start, trying grid locations {list_col_row}")

        for col, row in list_col_row:
            holder = pipette_holder.get_holder_at(col, row)

            if holder is None:
                print(f"Grid location ({col}, {row}) has no holder, skipping")
                continue

            if holder.is_occupied:
                print(f"Grid location ({col}, {row}) is already occupied, skipping")
                continue

            try:
                if holder.position is None:
                    print(f"Holder at grid location ({col}, {row}) has no position set, skipping")
                    continue

                x, y = holder.position
                self.move_xy(x, y)
                self.move_z(22)
                self.eject_tip()

                holder.is_occupied = True
                self.initialize_tips()

                print(f"✓ Successfully returned tip to column {col}, row {row}")
                return

            except CommandFailed as e:
                print(f"✗ Failed to return tip to column {col}, row {row}: {e}")
                continue
            finally:
                self.move_z(0)

        raise RuntimeError(
            f"Failed to return tip to any of the specified locations {list_col_row}. "
            f"Tip still attached to pipettor."
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

        # understand drop height
        x, y = tip_dropzone.position
        self.move_xy(x, y)
        self.move_z(tip_dropzone.drop_height_relative)
        self.eject_tip()
        self.initialize_tips()
        self.move_z(0)

    def add_medium(self, source: ReservoirHolder, source_col_row: tuple[int, int],
                   volume_per_well: float, destination: Plate,
                   dest_col_row: List[tuple[int, int]]) -> None:
        """
        Transfer medium from a reservoir to destination plate column(s).
        Works for both single-channel and multichannel pipettors.

        Parameters
        ----------
        source : ReservoirHolder
            ReservoirHolder containing the medium to transfer
        source_col_row : tuple[int, int]
            (Column, Row) position of reservoir.
        volume_per_well : float
            Volume (µL) to dispense into each destination well
        destination : Plate
            Target plate to receive the medium
        dest_col_row : List[tuple[int, int]]
            List of (Column, Row) positions in destination plate.
            Row is start row for multichannel pipettor.
        """
        # Validate (source needs 1 row, destinations need tip_count rows)
        self._validate_transfer(source, [source_col_row], destination, dest_col_row, 1, self.tip_count)

        # Calculate volumes
        volume_per_destination, max_vol = self._calculate_volumes(volume_per_well)

        # Choose strategy
        if volume_per_destination > max_vol:
            self._multi_trip_transfer(dest_col_row, volume_per_destination, max_vol,
                                      source, source_col_row, destination, None, is_one_to_many=True)
        else:
            self._batch_transfer(dest_col_row, volume_per_destination, max_vol,
                                 source, source_col_row, destination, None, is_one_to_many=True)

    def remove_medium(self, source: Plate, source_col_row: List[tuple[int, int]],
                      volume_per_well: float, destination: ReservoirHolder,
                      destination_col_row: tuple[int, int]) -> None:
        """
        Remove medium from plate wells to a destination reservoir.
        Works for both single-channel and multichannel pipettors.

        Parameters
        ----------
        source : Plate
            Plate to remove medium from
        source_col_row : List[tuple[int, int]]
            List of (Column, Row) positions to remove from.
            Row is start row for multichannel pipettor.
        volume_per_well : float
            Volume (µL) to remove from each well
        destination : ReservoirHolder
            ReservoirHolder to receive the liquid
        destination_col_row : tuple[int, int]
            (Column, Row) position of destination reservoir.
        """
        # Validate (sources need tip_count rows, destination needs 1 row)
        self._validate_transfer(source, source_col_row, destination, [destination_col_row], self.tip_count, 1)

        # Calculate volumes
        volume_per_source, max_vol = self._calculate_volumes(volume_per_well)

        # Choose strategy
        if volume_per_source > max_vol:
            self._multi_trip_transfer(source_col_row, volume_per_source, max_vol,
                                      source, None, destination, destination_col_row, is_one_to_many=False)
        else:
            self._batch_transfer(source_col_row, volume_per_source, max_vol,
                                 source, None, destination, destination_col_row, is_one_to_many=False)

    def transfer_plate_to_plate(self, source: Plate, source_col_row: List[tuple[int, int]],
                                destination: Plate, dest_col_row: List[tuple[int, int]],
                                volume_per_well: float) -> None:
        """
        Transfer liquid from source plate to destination plate (one-to-one mapping).
        Works for both single-channel and multichannel pipettors.

        Each source position is transferred to the corresponding destination position.
        source_col_row[i] → dest_col_row[i]

        Parameters
        ----------
        source : Plate
            Source plate
        source_col_row : List[tuple[int, int]]
            List of source (Column, Row) positions.
            Row is start row for multichannel pipettor.
        destination : Plate
            Destination plate
        dest_col_row : List[tuple[int, int]]
            List of destination (Column, Row) positions.
            Must be same length as source_col_row.
        volume_per_well : float
            Volume (µL) to transfer from each well

        Raises
        ------
        ValueError
            If source and destination lists have different lengths
        """
        # Validate list lengths match
        if len(source_col_row) != len(dest_col_row):
            raise ValueError(
                f"Source and destination lists must be same length. "
                f"Got {len(source_col_row)} sources and {len(dest_col_row)} destinations."
            )

        # Validate all positions (both need tip_count rows)
        self._validate_transfer(source, source_col_row, destination, dest_col_row,
                               self.tip_count, self.tip_count)

        # Calculate volumes
        volume_per_transfer, max_vol = self._calculate_volumes(volume_per_well)

        print(f"\n{'=' * 60}")
        print(f"Plate-to-plate transfer (one-to-one)")
        print(f"{'=' * 60}")
        print(f"Number of transfers: {len(source_col_row)}")
        print(f"Volume per well: {volume_per_well}µL")
        print(f"Volume per transfer: {volume_per_transfer}µL")
        print(f"Max volume per aspirate: {max_vol}µL\n")

        # Process each source → destination pair
        for idx, (src_pos, dst_pos) in enumerate(zip(source_col_row, dest_col_row), 1):
            src_col, src_row = src_pos
            dst_col, dst_row = dst_pos

            print(f"Transfer {idx}/{len(source_col_row)}: ({src_col},{src_row}) → ({dst_col},{dst_row})")

            # Check if multi-trip needed
            if volume_per_transfer > max_vol:
                # Multi-trip for this pair
                num_trips = ceil(volume_per_transfer / max_vol)
                base_volume = volume_per_transfer // num_trips
                remainder = volume_per_transfer % num_trips

                print(f"  {num_trips} trips needed")

                for trip_num in range(num_trips):
                    trip_volume = base_volume + (1 if trip_num < remainder else 0)
                    self.suck(source, src_pos, trip_volume)
                    self.spit(destination, dst_pos, trip_volume)
                    print(f"    Trip {trip_num + 1}/{num_trips}: {trip_volume}µL")
            else:
                # Single transfer
                self.suck(source, src_pos, volume_per_transfer)
                self.spit(destination, dst_pos, volume_per_transfer)
                print(f"  ✓ {volume_per_transfer}µL transferred")

            print()

        print(f"{'=' * 60}")
        print("✓ Plate-to-plate transfer complete\n")


        # These are helper methods for the PipettorPlus class
        # Add them to your class definition

    def suck(self, source: Labware, source_col_row: tuple[int, int], volume: float) -> None:
        """
        Aspirate from a source labware.

        Works with any labware type. If labware supports content tracking, content is tracked.
        If not, only physical movement is performed.

        Parameters
        ----------
        source : Labware
            Source labware (Plate, ReservoirHolder, or any other labware)
        source_col_row : tuple[int, int]
            (Column, Row) position in source labware
        volume : float
            Total volume to aspirate across all tips (µL)
        """
        source_col, source_row = source_col_row

        if volume <= 0:
            raise ValueError("Volume must be positive")

        # Validate based on whether it's a reservoir or not
        if not source.each_tip_needs_separate_item():
            # like for Reservoir: all tips access same reservoir
            source.validate_col_row_or_raise([source_col], source_row, 1)
        else:
            # Plate or other grid labware: each tip accesses different position
            source.validate_col_row_or_raise([source_col], source_row, self.tip_count)

        if self._supports_content_management(source, source_col, source_row):
            # Track content if supported
            self._aspirate_with_content_tracking(source, source_col, source_row, volume)
            print(f"  → Aspirated {volume}µL from {source.labware_id} at {source_col_row}")
            print(f"  → Tip content now: {self._get_tip_content_summary()}")
        else:
            # Just do physical movement without content tracking
            self._aspirate_physical_only(source, source_col, source_row, volume)
            print(f"  → Aspirated {volume}µL from {source.labware_id} at {source_col_row}")

    def add_content(self, content_type: str, volume: float, tip_index: int = None) -> None:
        """
        Add content to specific tip(s).

        Parameters
        ----------
        content_type : str
            Content to add (e.g., "PBS", "water")
        volume : float
            Volume to add (µL)
        tip_index : int, optional
            Which tip to add to (0-7 for multichannel, 0 for single).
            If None, adds to all tips equally.
        """
        if volume <= 0:
            raise ValueError("Volume to add must be positive")

        if not content_type:
            raise ValueError("Content type cannot be empty")

        # Determine which tips to update
        if tip_index is not None:
            if tip_index not in self.tip_dict:
                raise ValueError(f"Invalid tip index {tip_index}. Valid range: 0-{self.tip_count - 1}")
            tip_indices = [tip_index]
        else:
            # Add to all tips
            tip_indices = list(self.tip_dict.keys())

        # Add content to each specified tip
        for idx in tip_indices:
            if content_type in self.tip_dict[idx]:
                self.tip_dict[idx][content_type] += volume
            else:
                self.tip_dict[idx][content_type] = volume

    def remove_content(self, volume: float, tip_index: int = None) -> None:
        """
        Remove content from tip(s) proportionally.

        Parameters
        ----------
        volume : float
            Volume to remove (µL)
        tip_index : int, optional
            Which tip to remove from. If None, removes from all tips.
        """
        if volume <= 0:
            raise ValueError("Volume to remove must be positive")

        # Determine which tips to update
        if tip_index is not None:
            if tip_index not in self.tip_dict:
                raise ValueError(f"Invalid tip index {tip_index}")
            tip_indices = [tip_index]
        else:
            tip_indices = list(self.tip_dict.keys())

        # Remove from each tip
        for idx in tip_indices:
            tip_content = self.tip_dict[idx]
            current_volume = sum(tip_content.values()) if tip_content else 0.0

            if current_volume <= 0:
                raise ValueError(f"Cannot remove from empty tip {idx}")

            if volume > current_volume:
                raise ValueError(
                    f"Underflow in tip {idx}! Cannot remove {volume}µL, only {current_volume}µL available"
                )

            # Remove proportionally
            removal_ratio = volume / current_volume
            content_types = list(tip_content.keys())

            for content_type in content_types:
                remove_amount = tip_content[content_type] * removal_ratio
                tip_content[content_type] -= remove_amount

                if tip_content[content_type] <= 1e-6:
                    del tip_content[content_type]

    def get_total_tip_volume(self, tip_index: int = None) -> float:
        """
        Get total volume in tip(s).

        Parameters
        ----------
        tip_index : int, optional
            Specific tip. If None, returns total across all tips.

        Returns
        -------
        float
            Total volume in µL
        """
        if tip_index is not None:
            return sum(self.tip_dict[tip_index].values()) if self.tip_dict[tip_index] else 0.0
        else:
            # Sum across all tips
            total = 0.0
            for tip_content in self.tip_dict.values():
                total += sum(tip_content.values()) if tip_content else 0.0
            return total

    def home(self):
        self.move_z(0)
        self.move_xy(0, 0)

    # Helper functions. Not necessarily available for GUI

    def _aspirate_with_content_tracking(self, source: Labware, col: int, row: int, volume: float) -> None:
        """Aspirate with content tracking (works for any labware with content management)."""

        # Check if each tip needs separate item
        if self.multichannel and source.each_tip_needs_separate_item():
            # Small items: each tip accesses different item (e.g., Plate)
            items = [self._get_content_item(source, col, row + i)
                     for i in range(self.tip_count)]
            volume_per_item = volume / self.tip_count
        else:
            # Large items: all tips access same item (e.g., Reservoir), or single channel
            items = [self._get_content_item(source, col, row)]
            volume_per_item = volume

        # Validate items exist
        if any(item is None for item in items):
            raise ValueError(f"Content item not found at position ({col}, {row})")

        # Check total available volume
        total_available = sum(item.get_total_volume() for item in items if item)
        if total_available < volume:
            raise ValueError(
                f"Insufficient volume. Available: {total_available}µL, Requested: {volume}µL"
            )

        # Remove content from source and add to tips (WITH TIP INDEX!)
        for tip_idx, item in enumerate(items):
            if item and volume_per_item > 0:  # Properly indented
                removed_content = item.remove_content(volume_per_item, return_dict=True)

                # If single item for multichannel, distribute to all tips
                if len(items) == 1 and self.multichannel:
                    # Distribute to all tips
                    for tip_i in range(self.tip_count):
                        for content_type, vol in removed_content.items():
                            if vol > 0:
                                # Each tip gets equal share
                                self.add_content(content_type, vol / self.tip_count, tip_index=tip_i)
                else:
                    # Each tip gets from its own item
                    for content_type, vol in removed_content.items():
                        if vol > 0:
                            self.add_content(content_type, vol, tip_index=tip_idx)

        # Physical movement
        self._move_to_and_aspirate(items[0], volume)

    def _aspirate_physical_only(self, source: Labware, col: int, row: int, volume: float) -> None:
        """Aspirate without content tracking (for labware without content management)."""

        # Get position - try to get item first, fallback to labware itself
        item = self._get_content_item(source, col, row)
        if item is None:
            item = source

        # Physical movement
        self._move_to_and_aspirate(item, volume)
        print(f"  → Note: Content tracking not available for {type(source).__name__}")

    def _move_to_and_aspirate(self, item: Labware, volume: float) -> None:
        """Move to item position and perform aspiration."""
        if not item or not item.position:
            raise ValueError("Item has no position set")

        x, y = item.position
        self.move_xy(x, y)

        #todo
        # Determine height (duck typing!)
        if hasattr(item, 'remove_height'):
            z = item.remove_height
        elif hasattr(item, 'size_z'):
            z = item.size_z * 0.8
        else:
            z = 5  # Default

        self.move_z(z)
        self.aspirate(volume/self.tip_count)
        self.move_z(0)

    def _supports_content_management(self, labware: Labware, col: int, row: int) -> bool:
        """Check if labware supports content tracking at this position."""
        item = self._get_content_item(labware, col, row)

        return (item is not None and
                hasattr(item, 'content') and
                hasattr(item, 'remove_content') and
                hasattr(item, 'add_content') and
                hasattr(item, 'get_total_volume'))

    def _get_content_item(self, labware: Labware, col: int, row: int):
        """
        Get the actual item that holds content at a position.

        Uses duck typing to work with any labware structure:
        - If it has get_well_at(), it's a Plate-like structure
        - If it has reservoir mapping methods, it's a ReservoirHolder-like structure
        - Otherwise, the labware itself might hold content
        """

        # Try Plate-like: get_well_at(col, row)
        if hasattr(labware, 'get_well_at'):
            return labware.get_well_at(col, row)

        # Try ReservoirHolder-like: position_to_hook_id + get_hook_to_reservoir_map
        if hasattr(labware, 'position_to_hook_id') and hasattr(labware, 'get_hook_to_reservoir_map'):
            hook_id = labware.position_to_hook_id(col, row)
            return labware.get_hook_to_reservoir_map().get(hook_id)

        # Direct content holder: the labware itself has content
        return labware

    def initialize_tips(self) -> None:
        """Clear tip content when tips are discarded."""
        self.has_tips = False
        self.tip_dict = {i: {} for i in range(self.tip_count)}
        print(f"  → Tips discarded, content cleared")

    def _validate_transfer(self, source, source_positions, destination, destination_positions,
                           source_consecutive_rows: int, dest_consecutive_rows: int) -> None:
        """Helper: Validate source and destination positions."""
        self.check_tips()

        # Validate source positions
        if not isinstance(source_positions, list):
            source_positions = [source_positions]
        for source_col, source_row in source_positions:
            source.validate_col_row_or_raise([source_col], source_row, source_consecutive_rows)

        # Validate destination positions
        if not isinstance(destination_positions, list):
            destination_positions = [destination_positions]
        for dest_col, dest_row in destination_positions:
            destination.validate_col_row_or_raise([dest_col], dest_row, dest_consecutive_rows)

    def _calculate_volumes(self, volume_per_well: float) -> tuple[int, int]:
        """Helper: Calculate volume per position and max volume per aspirate."""
        volume_per_position = int(volume_per_well * self.tip_count)
        max_vol_per_aspirate = int(self.tip_volume * self.tip_count)

        if volume_per_position <= 0:
            raise ValueError("volume_per_well must be > 0")

        return volume_per_position, max_vol_per_aspirate

    def _multi_trip_transfer(self, positions: List[tuple[int, int]],
                             volume_per_position: int, max_vol_per_aspirate: int,
                             source, source_pos, destination, dest_positions,
                             is_one_to_many: bool) -> None:
        """
        Helper: Handle multi-trip transfers when volume exceeds capacity.

        Parameters
        ----------
        is_one_to_many : bool
            True for add_medium (1 source → many dests), False for remove_medium (many sources → 1 dest)
        """
        print(f"\n→ Strategy: MULTI-TRIP (volume exceeds tip capacity)")
        print(f"{'=' * 60}\n")

        for pos in positions:
            col, row = pos

            num_trips = ceil(volume_per_position / max_vol_per_aspirate)
            print(f"Position ({col}, {row}): {num_trips} trips needed")

            # Distribute volume evenly across trips
            base_volume = volume_per_position // num_trips
            remainder = volume_per_position % num_trips

            for trip_num in range(num_trips):
                trip_volume = base_volume + (1 if trip_num < remainder else 0)

                if is_one_to_many:
                    # add_medium: same source, different destinations
                    self.suck(source, source_pos, trip_volume)
                    self.spit(destination, pos, trip_volume)
                else:
                    # remove_medium: different sources, same destination
                    self.suck(source, pos, trip_volume)
                    self.spit(destination, dest_positions, trip_volume)

        print("✓ Multi-trip transfer complete\n")

    def _batch_transfer(self, positions: List[tuple[int, int]],
                        volume_per_position: int, max_vol_per_aspirate: int,
                        source, source_pos, destination, dest_pos,
                        is_one_to_many: bool) -> None:
        """
        Helper: Handle batch transfers for multiple positions.

        Parameters
        ----------
        is_one_to_many : bool
            True for add_medium (1 source → many dests), False for remove_medium (many sources → 1 dest)
        """
        print(f"\n→ Strategy: BATCH MODE")
        print(f"{'=' * 60}\n")

        # Calculate optimal batch size
        max_positions_by_volume = max_vol_per_aspirate // volume_per_position
        batch_size = min(MAX_BATCH_SIZE, max_positions_by_volume)

        if batch_size < 1:
            batch_size = 1

        num_batches = ceil(len(positions) / batch_size)
        print(f"Batch size: {batch_size} position(s) per aspirate")
        print(f"Total batches: {num_batches}\n")

        # Process positions in batches
        idx = 0
        batch_num = 1

        while idx < len(positions):
            batch_end = min(idx + batch_size, len(positions))
            batch = positions[idx:batch_end]
            total_batch_volume = len(batch) * volume_per_position

            print(f"Batch {batch_num}/{num_batches}:")
            print(f"  Positions: {batch}")
            print(f"  Total volume: {total_batch_volume}µL")

            if is_one_to_many:
                # add_medium: aspirate once, dispense multiple times
                self.suck(source, source_pos, total_batch_volume)
                for pos in batch:
                    self.spit(destination, pos, volume_per_position)
                    print(f"  ✓ Dispensed to {pos}: {volume_per_position}µL")
            else:
                # remove_medium: aspirate multiple times, dispense once
                for pos in batch:
                    self.suck(source, pos, volume_per_position)
                    print(f"  ✓ Aspirated from {pos}: {volume_per_position}µL")
                self.spit(destination, dest_pos, total_batch_volume)
                print(f"  ✓ Dispensed to destination: {total_batch_volume}µL")

            print()
            idx = batch_end
            batch_num += 1

        print(f"{'=' * 60}")
        print("✓ Batch transfer complete\n")

    def _get_tip_content_summary(self) -> str:
        """Get a readable summary of tip content across all tips."""
        total_volume = self.get_total_tip_volume()
        if not self.tip_dict or total_volume <= 0:
            return "empty"

        # Aggregate content across all tips
        aggregated_content = {}
        for tip_content in self.tip_dict.values():
            for content_type, volume in tip_content.items():
                if content_type in aggregated_content:
                    aggregated_content[content_type] += volume
                else:
                    aggregated_content[content_type] = volume

        parts = []
        for content_type, volume in aggregated_content.items():
            parts.append(f"{content_type}: {volume:.1f}µL")

        return ", ".join(parts)

    def get_tip_status(self) -> dict:
        """Get current tip status."""
        total_volume = self.get_total_tip_volume()
        return {
            "content_dict": self.tip_dict.copy(),
            "volume_remaining": total_volume,
            "is_empty": total_volume <= 0,
            "content_summary": self._get_tip_content_summary()
        }

    def check_tips(self) -> None:
        """
        Check if tip change is required. if yes, do it.
        """

        lw = self.find_labware_by_type("PipetteHolder")[0]  # Gets first PipetteHolder found
        if self.change_tips and not self.has_tips:
            self.pick_multi_tips(lw)
        elif self.change_tips and self.has_tips:
            self.replace_multi_tips(lw)
        elif not self.has_tips:
            raise ValueError("No tips loaded. Pick tips first.")

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
        for labware_id, labware in self._deck.labware.items():
            # Check if the labware's class name matches the requested type (case-sensitive)
            if labware.__class__.__name__ == labware_type:
                # Check if this labware is placed in a slot ( in all slots placed in deck)
                slot_id = self._deck.get_slot_for_labware(labware_id)
                if slot_id is not None:
                    lw.append(labware)

        if not lw:
            raise ValueError(f"No labware found for type '{labware_type}'.")
        else:
            return lw

    def spit(self, destination: Labware, dest_col_row: tuple[int, int], volume: float) -> None:
        """
        Dispense from tips to a destination labware.

        Works with any labware type. If labware supports content tracking, content is tracked.
        If not, only physical movement is performed.

        Parameters
        ----------
        destination : Labware
            Destination labware (Plate, ReservoirHolder, or any other labware)
        dest_col_row : tuple[int, int]
            (Column, Row) position in destination labware
        volume : float
            Total volume to dispense across all tips (µL)
        """
        dest_col, dest_row = dest_col_row

        if volume <= 0:
            raise ValueError("Volume must be positive")

        # Check we have enough volume in tips
        total_available = self.get_total_tip_volume()
        if total_available < volume:
            raise ValueError(
                f"Insufficient volume in tips. Available: {total_available}µL, Requested: {volume}µL"
            )

        # Validate based on whether destination needs separate items per tip
        if not destination.each_tip_needs_separate_item():
            # Reservoir: all tips dispense to same item
            destination.validate_col_row_or_raise([dest_col], dest_row, 1)
        else:
            # Plate: each tip dispenses to different item
            destination.validate_col_row_or_raise([dest_col], dest_row, self.tip_count)

        if self._supports_content_management(destination, dest_col, dest_row):
            # Track content if supported
            self._dispense_with_content_tracking(destination, dest_col, dest_row, volume)
            print(f"  → Dispensed {volume}µL to {destination.labware_id} at {dest_col_row}")
            print(f"  → Tip content now: {self._get_tip_content_summary()}")
        else:
            # Just do physical movement without content tracking
            self._dispense_physical_only(destination, dest_col, dest_row, volume)
            print(f"  → Dispensed {volume}µL to {destination.labware_id} at {dest_col_row}")

    def spit_all(self, destination: Labware, dest_col_row: tuple[int, int]) -> None:
        """
        Dispense ALL content from tips to a destination labware.

        Parameters
        ----------
        destination : Labware
            Destination labware
        dest_col_row : tuple[int, int]
            (Column, Row) position in destination labware
        """
        total_volume = self.get_total_tip_volume()

        if total_volume <= 0:
            raise ValueError("No content in tips to dispense")

        print(f"  → Dispensing all content: {total_volume}µL")
        self.spit(destination, dest_col_row, total_volume)

    def _dispense_with_content_tracking(self, destination: Labware, col: int, row: int, volume: float) -> None:
        """Dispense with content tracking (works for any labware with content management)."""

        # Check if each tip needs separate destination item
        if self.multichannel and destination.each_tip_needs_separate_item():
            # Small items: each tip dispenses to different item (e.g., Plate)
            items = [self._get_content_item(destination, col, row + i)
                     for i in range(self.tip_count)]
            volume_per_item = volume / self.tip_count
        else:
            # Large items: all tips dispense to same item (e.g., Reservoir), or single channel
            items = [self._get_content_item(destination, col, row)]
            volume_per_item = volume

        # Validate items exist
        if any(item is None for item in items):
            raise ValueError(f"Content item not found at position ({col}, {row})")

        # Transfer content from tips to destination
        if len(items) == 1 and self.multichannel:
            # All tips dispense to ONE item (Reservoir)
            # Aggregate content from all tips
            item = items[0]

            # Collect content from all tips proportionally
            for tip_idx in range(self.tip_count):
                tip_content = self.tip_dict[tip_idx]
                tip_total = sum(tip_content.values()) if tip_content else 0.0

                if tip_total > 0:
                    # Calculate this tip's share of total volume to dispense
                    tip_volume_to_dispense = volume / self.tip_count

                    # Remove proportionally from this tip and add to destination
                    removal_ratio = tip_volume_to_dispense / tip_total

                    for content_type in list(tip_content.keys()):
                        remove_amount = tip_content[content_type] * removal_ratio

                        # Add to destination
                        item.add_content(content_type, remove_amount)

                        # Remove from tip
                        tip_content[content_type] -= remove_amount
                        if tip_content[content_type] <= 1e-6:
                            del tip_content[content_type]

        else:
            # Each tip dispenses to its own item (Plate) OR single channel
            for tip_idx, item in enumerate(items):
                if item and volume_per_item > 0:
                    tip_content = self.tip_dict[tip_idx]
                    tip_total = sum(tip_content.values()) if tip_content else 0.0

                    if tip_total <= 0:
                        continue

                    # Remove proportionally from this tip and add to destination
                    removal_ratio = volume_per_item / tip_total

                    for content_type in list(tip_content.keys()):
                        remove_amount = tip_content[content_type] * removal_ratio

                        # Add to destination
                        item.add_content(content_type, remove_amount)

                        # Remove from tip
                        tip_content[content_type] -= remove_amount
                        if tip_content[content_type] <= 1e-6:
                            del tip_content[content_type]

        # Physical movement
        self._move_to_and_dispense(items[0], volume)

    def _dispense_physical_only(self, destination: Labware, col: int, row: int, volume: float) -> None:
        """Dispense without content tracking (for labware without content management)."""

        # Get position - try to get item first, fallback to labware itself
        item = self._get_content_item(destination, col, row)
        if item is None:
            item = destination

        # Physical movement
        self._move_to_and_dispense(item, volume)
        print(f"  → Note: Content tracking not available for {type(destination).__name__}")

    def _move_to_and_dispense(self, item: Labware, volume: float) -> None:
        """Move to item position and perform dispense."""
        if not item or not item.position:
            raise ValueError("Item has no position set")

        x, y = item.position
        self.move_xy(x, y)

        # Determine height (duck typing!)
        if hasattr(item, 'add_height'):
            z = item.add_height
        elif hasattr(item, 'size_z'):
            z = item.size_z * 0.2  # 20% height for dispensing
        else:
            z = 5  # Default

        self.move_z(z)
        self.dispense(volume / self.tip_count)  # Volume per tip
        self.move_z(0)