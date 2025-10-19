from .pipettor import Pipettor
from typing import Literal, List, Optional, Union, Callable
from math import ceil

# from .cursor import total_volume
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
        super().__init__(tip_volume=tip_volume, multichannel = multichannel, initialize=initialize)
        self.deck = deck
        self.slots: dict[str, Slot] = deck.slots

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

    def spit_all(self):
        pass

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

    def home(self):
        self.move_z(0)
        self.move_xy(0, 0)

    # Helper functions. Not necessarily available for GUI
    def initialize_tips(self) -> None:
        """Clear tip content when tips are discarded."""
        self.has_tips = False
        self.tip_dict = {}
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
        for labware_id, labware in self.deck.labware.items():
            # Check if the labware's class name matches the requested type (case-sensitive)
            if labware.__class__.__name__ == labware_type:
                # Check if this labware is placed in a slot ( in all slots placed in deck)
                slot_id = self.deck.get_slot_for_labware(labware_id)
                if slot_id is not None:
                    lw.append(labware)

        if not lw:
            raise ValueError(f"No labware found for type '{labware_type}'.")
        else:
            return lw
