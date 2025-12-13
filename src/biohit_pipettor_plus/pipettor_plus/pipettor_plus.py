class AbortException(Exception):
    """Raised when user aborts an operation"""
    pass

try:
    from biohit_pipettor import Pipettor
    from biohit_pipettor.errors import CommandFailed

    HARDWARE_AVAILABLE = True

except ImportError:
    print("⚠️ Hardware not available - running in simulation mode")
    HARDWARE_AVAILABLE = False


    # Create a mock Pipettor class for testing
    class Pipettor:
        def __init__(self, *args, **kwargs):
            print("Mock Pipettor initialized")

        def move_xy(self, x, y):
            print(f"Mock: move_xy({x}, {y})")

        def move_x(self, x):
            print(f"Mock: move_x({x})")

        def move_y(self, y):
                print(f"Mock: move_y({y})")
        def move_z(self, z):
            print(f"Mock: move_z({z})")

        def aspirate(self, volume):
            print(f"Mock: aspirate({volume})")

        def dispense(self, volume):
            print(f"Mock: dispense({volume})")

        def pick_tip(self, z):
            print(f"Mock: pick_tip({z})")

        def eject_tip(self):
            print("Mock: eject_tip()")


    # Mock the CommandFailed exception too
    class CommandFailed(Exception):
        """Mock exception for when hardware commands fail"""
        pass

#from biohit_pipettor import Pipettor
from ..deck_structure import *
from .pipettor_constants import Pipettors_in_Multi, MAX_BATCH_SIZE, Change_Tips, TIP_LENGTHS, Z_MAX
from .geometry import (calculate_liquid_height, calculate_dynamic_remove_height)

import time
import os
import subprocess
from typing import Literal, List
from math import ceil


class PipettorPlus(Pipettor):

    def __init__(self, tip_volume: Literal[200, 1000], *, multichannel: bool,  initialize: bool = True, deck: Deck, tip_length: float = None):
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
        super().__init__(tip_volume=tip_volume, multichannel=multichannel, initialize=initialize)
        self.multichannel = multichannel
        self._deck = deck
        self._slots: dict[str, Slot] = deck.slots
        self._simulation_mode = False
        self.abort_requested = False
        self.pause_requested = False

        #creates a dict of all tips, each tips having its own dict where content and volume in tip can be stored.
        self.tip_length = tip_length if tip_length is not None else TIP_LENGTHS[tip_volume]
        self.tip_count = Pipettors_in_Multi if self.multichannel else 1
        self.tip_dict = {i: {} for i in range(0, self.tip_count)}
        self.has_tips = False
        self.tip_volume = tip_volume
        self.change_tips = Change_Tips  # control if tips are to be changed

        self.foc_bat_script_path = None

    def push_state(self):
        """Save complete state snapshot for later restoration."""

        snapshot = {}

        for slot_id, slot in self._slots.items():
            if not slot.labware_stack:
                continue

            # Get topmost labware (highest max_z)
            top_lw_id, (top_lw, (min_z, max_z)) = max(
                slot.labware_stack.items(),
                key=lambda item: item[1][1][1]  # item[1][1][1] = max_z
            )

            snapshot[top_lw.labware_id] = top_lw.get_state_snapshot()

        return {
            'has_tips': self.has_tips,
            'tip_dict': {k: v.copy() for k, v in self.tip_dict.items()},
            'deck_state': snapshot
        }

    def pop_state(self, snapshot):
        """Restore pipettor and deck state from snapshot."""
        self.has_tips = snapshot['has_tips']
        self.tip_dict = {k: v.copy() for k, v in snapshot['tip_dict'].items()}

        deck_state_data = snapshot['deck_state']

        for slot_id, slot in self._slots.items():
            if not slot.labware_stack:
                continue

            # Get topmost labware
            top_lw_id, (top_lw, (min_z, max_z)) = max(
                slot.labware_stack.items(),
                key=lambda item: item[1][1][1]
            )

            if top_lw.labware_id in deck_state_data:
                top_lw.restore_state_snapshot(deck_state_data[top_lw.labware_id])

    def set_simulation_mode(self, enabled: bool) -> None:
        """Enable or disable simulation mode."""
        self._simulation_mode = enabled
        if enabled:
            print("  → Simulation mode ENABLED (hardware calls will be skipped)")
        else:
            print("  → Simulation mode DISABLED (hardware calls will execute)")

    def _check_abort_and_pause(self):
        """Check for abort or pause requests at safe checkpoints"""

        # Check abort first (highest priority)
        if self.abort_requested:
            self.abort_requested = False  # Reset
            self.home()
            raise AbortException("Operation aborted by user")

        # Check pause
        while self.pause_requested:
            time.sleep(0.1)  # Wait 100ms, check again

            # Allow abort even while paused
            if self.abort_requested:
                self.pause_requested = False  # Unpause
                self.abort_requested = False
                self.home()
                raise AbortException("Operation aborted by user")

    def pick_tips(self, pipette_holder: PipetteHolder, list_col_row: List[tuple[int, int]] = None,) -> List[tuple[int, int]]:
        """
                Pick tips from a PipetteHolder.

                Parameters
                ----------
                pipette_holder : PipetteHolder
                    PipetteHolder labware containing tips
                list_col_row : List[tuple[int, int]], optional
                    List of (column, row) grid indices to try.
                    If None, automatically finds occupied grid locations.

                Returns
                -------
                List[tuple[int, int]]
                    Actual (column, row) positions where tips were picked

                Raises
                ------
                ValueError
                    If pipettor already has tips or pipette holder not found
                """

        #check if tips already exist.
        if self.has_tips:
            raise ValueError("pipettor already has tips")

        if self.multichannel:
            return self.pick_multi_tips(pipette_holder, list_col_row)
        else:
            return self.pick_single_tip(pipette_holder, list_col_row)

    def pick_multi_tips(self, pipette_holder: PipetteHolder, list_col_row: List[tuple[int, int]] = None) ->  List[tuple[int, int]]:
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

        Returns
        -------
        List[tuple[int, int]]
            Actual (column, start_row) position where tips were picked

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
                if not self._simulation_mode:
                    self._check_abort_and_pause()
                first_holder = holders_to_use[0]
                if first_holder.position is None:
                    raise ValueError(f"Holder at grid location ({col}, {start_row}) has no position set")

                # FIXED: Calculate center position
                x, y = self._get_robot_xy_position(holders_to_use)

                # Pick tips at the specified height
                first_holder = holders_to_use[0]
                relative_z = getattr(pipette_holder, 'remove_height', pipette_holder.size_z)
                pipettor_z = self._get_pipettor_z_coord(pipette_holder, relative_z, child_item=first_holder)

                if not self._simulation_mode:
                    self.move_xy(x, y)
                    self.pick_tip(pipettor_z)

                # Mark all 8 tips in this column as removed
                pipette_holder.remove_consecutive_pipettes_multi([col], start_row)
                self.has_tips = True

                print(f"✓ Successfully picked 8 tips from column {col}, rows {start_row} to {start_row + 7}")
                return [(col, start_row)]

            except CommandFailed as e:
                print(f"✗ Failed to pick tips from column {col}, row {start_row}: {e}")
                continue
            finally:
                if not self._simulation_mode:
                    self.move_z(0)

        # If we got here, all attempts failed
        raise RuntimeError(
            f"Failed to pick tips from any of the specified locations {list_col_row}. "
        )

    def pick_single_tip(self, pipette_holder: PipetteHolder, list_col_row: List[tuple[int, int]] = None) ->  List[tuple[int, int]]:
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
                if not self._simulation_mode:
                    self._check_abort_and_pause()
                if holder.position is None:
                    print(f"Holder at grid location ({col}, {row}) has no position set, skipping")
                    continue

                x, y = holder.position

                relative_z = getattr(pipette_holder, 'remove_height', pipette_holder.size_z)
                pipettor_z = self._get_pipettor_z_coord(pipette_holder, relative_z, child_item=holder)
                if not self._simulation_mode:
                    self.move_xy(x, y)
                    self.pick_tip(pipettor_z)

                holder.is_occupied = False
                self.has_tips = True

                print(f"✓ Successfully picked tip from column {col}, row {row}")
                return [(col, row)]

            except CommandFailed as e:
                print(f"✗ Failed to pick tip from column {col}, row {row}: {e}")
                holder.is_occupied = False
                continue
            finally:
                if not self._simulation_mode:
                    self.move_z(0)

        raise RuntimeError(
            f"Failed to pick tip from any of the specified locations {list_col_row}."
        )

    def return_tips(self, pipette_holder: PipetteHolder, list_col_row: List[tuple[int, int]] = None) -> List[tuple[int, int]]:
        """ return tips to PipetteHolder. """

        if not self.has_tips:
            raise ValueError("pipettor have no tips to return")

        if self.multichannel:
            return self.return_multi_tips(pipette_holder, list_col_row)
        else:
            return self.return_single_tip(pipette_holder, list_col_row)

    def return_multi_tips(self, pipette_holder: PipetteHolder, list_col_row: List[tuple[int, int]] = None) -> List[tuple[int, int]]:
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
                if not self._simulation_mode:
                    self._check_abort_and_pause()
                first_holder = holders_to_use[0]
                if first_holder.position is None:
                    print(f"Holder at grid location ({col}, {start_row}) has no position set, skipping")
                    continue

                x, y = self._get_robot_xy_position(holders_to_use)

                # Return tips at the specified height
                first_holder = holders_to_use[0]
                relative_z = getattr(pipette_holder, 'add_height', pipette_holder.size_z)
                pipettor_z = self._get_pipettor_z_coord(pipette_holder, relative_z, child_item=first_holder)

                if not self._simulation_mode:
                    self.move_xy(x, y)
                    self.move_z(pipettor_z)
                    self.eject_tip()
                # Mark all 8 positions in this column as occupied
                pipette_holder.place_consecutive_pipettes_multi([col], start_row)
                self.initialize_tips()

                print(f"✓ Successfully returned 8 tips to column {col}, rows {start_row} to {start_row + 7}")
                return [(col, start_row)]

            except CommandFailed as e:
                print(f"✗ Failed to return tips to column {col}, row {start_row}: {e}")
                continue
            finally:
                if not self._simulation_mode:
                    self.move_z(0)

        # If we got here, all attempts failed
        raise RuntimeError(
            f"Failed to return tips to any of the specified locations {list_col_row}. "
            f"Tips still attached to pipettor."
        )

    def return_single_tip(self, pipette_holder: PipetteHolder, list_col_row: List[tuple[int, int]] = None) -> List[tuple[int, int]]:
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
                if not self._simulation_mode:
                    self._check_abort_and_pause()
                if holder.position is None:
                    print(f"Holder at grid location ({col}, {row}) has no position set, skipping")
                    continue

                x, y = holder.position
                relative_z = getattr(pipette_holder, 'add_height', pipette_holder.size_z)
                pipettor_z = self._get_pipettor_z_coord(pipette_holder, relative_z, child_item=holder)

                if not self._simulation_mode:
                    self.move_xy(x, y)
                    self.move_z(pipettor_z)  # return_height
                    self.eject_tip()

                holder.is_occupied = True
                self.initialize_tips()

                print(f"✓ Successfully returned tip to column {col}, row {row}")
                return [(col, row)]

            except CommandFailed as e:
                print(f"✗ Failed to return tip to column {col}, row {row}: {e}")
                continue
            finally:
                if not self._simulation_mode:
                    self.move_z(0)

        raise RuntimeError(
            f"Failed to return tip to any of the specified locations {list_col_row}. "
            f"Tip still attached to pipettor."
        )

    def replace_tips(self, pipette_holder: PipetteHolder, pick_pipette_holder:PipetteHolder = None,
                     return_list_col_row: List[tuple[int, int]] = None,
                     pick_list_col_row: List[tuple[int, int]] = None ) -> dict:

        if not pick_pipette_holder:
            pick_pipette_holder = pipette_holder

        if not self._simulation_mode:
            self._check_abort_and_pause()

        if self.multichannel:
            # get list of available holders
            if not return_list_col_row:
                return_list_col_row = pipette_holder.get_available_holder_multi()
            # get list of occupied holders
            if not pick_list_col_row:
                pick_list_col_row = pick_pipette_holder.get_occupied_holder_multi()

        else:
            if not return_list_col_row:
                available_holders = pipette_holder.get_available_holders()
                return_list_col_row = [(h.column, h.row) for h in available_holders]  # Convert to list of available_holders !
            if not pick_list_col_row:
                occupied_holders = pick_pipette_holder.get_occupied_holders()
                pick_list_col_row = [(h.column, h.row) for h in occupied_holders]  # Convert to list of occupied_holders!

        actual_return_pos = self.return_tips(pipette_holder, list_col_row=return_list_col_row)
        actual_pick_pos = self.pick_tips(pick_pipette_holder, list_col_row=pick_list_col_row)

        return {
            'return': actual_return_pos,
            'pick': actual_pick_pos
        }

    def discard_tips(self, tip_dropzone: Labware) -> None:
        """
        Discard tips to a TipDropzone.

        Parameters
        ----------
        tip_dropzone : labware
            TipDropzone labware
        """

        if not self._simulation_mode:
            self._check_abort_and_pause()

        if not self.has_tips:
            raise RuntimeError("No tips to discard")

        if not isinstance(tip_dropzone, TipDropzone):
            raise ValueError("discard_tips only works with TipDropzone")

        x, y = tip_dropzone.position
        relative_z = tip_dropzone.drop_height_relative
        pipettor_z = self._get_pipettor_z_coord(tip_dropzone, relative_z, child_item=None)

        if not self._simulation_mode:
            self.move_xy(x, y)
            self.move_z(pipettor_z)
            self.eject_tip()
            self.move_z(0)

        self.initialize_tips()

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
            difference = volume - total_available
            if difference <= 0.01:
                volume = total_available
            else:
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
                difference = volume - current_volume
                if difference <= 0.01:
                    volume = current_volume
                else:
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

    def home(self):

        if not self._simulation_mode:
            self._check_abort_and_pause()
            self.move_z(0)
            self.move_xy(0, 0)

    def move_xy(self, x: float, y: float):
        """Override parent to add simulation mode check"""
        if self._simulation_mode:
            return
        self._check_abort_and_pause()
        super().move_z(0)
        super().move_xy(x, y)

    def move_z(self, z: float):
        """Override parent to add simulation mode check"""
        if self._simulation_mode:
            return
        self._check_abort_and_pause()
        super().move_z(z)
    # Helper Functions. Not necessarily available for GUI
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

    def _aspirate_with_content_tracking(self, source: Labware, col: int, row: int, volume: float) -> None:
        """Aspirate with content tracking."""

        if not self._simulation_mode:
            self._check_abort_and_pause()
        # Check if each tip needs separate item
        if self.multichannel and source.each_tip_needs_separate_item():
            items = [self._get_content_item(source, col, row + i)
                     for i in range(self.tip_count)]
            volume_per_item = volume / self.tip_count
        else:
            items = [self._get_content_item(source, col, row)]
            volume_per_item = volume

        # Validate items exist
        if any(item is None for item in items):
            raise ValueError(f"Content item not found at position ({col}, {row})")

        # Check total available volume
        total_available = sum(item.get_total_volume() for item in items if item)
        if total_available < volume:
            difference = volume - total_available
            if difference <= 0.01:
                volume = total_available
            else:
                raise ValueError(
                    f"Insufficient volume. Available: {total_available}µL, Requested: {volume}µL"
                )

        # Remove content from source and add to tips
        for tip_idx, item in enumerate(items):
            if item and volume_per_item > 0:
                removed_content = item.remove_content(volume_per_item, return_dict=True)

                if len(items) == 1 and self.multichannel:
                    # Distribute to all tips
                    for tip_i in range(self.tip_count):
                        for content_type, vol in removed_content.items():
                            if vol > 0:
                                self.add_content(content_type, vol / self.tip_count, tip_index=tip_i)
                else:
                    # Each tip gets from its own item
                    for content_type, vol in removed_content.items():
                        if vol > 0:
                            self.add_content(content_type, vol, tip_index=tip_idx)

        self._move_to_and_aspirate(items, volume)

    def _aspirate_physical_only(self, source: Labware, col: int, row: int, volume: float) -> None:
        """Aspirate without content tracking."""

        # Get items (same logic as content tracking)
        if self.multichannel and source.each_tip_needs_separate_item():
            items = [self._get_content_item(source, col, row + i)
                     for i in range(self.tip_count)]
        else:
            item = self._get_content_item(source, col, row)
            items = [item if item else source]

        self._move_to_and_aspirate(items, volume)
        print(f"  → Note: Content tracking not available for {type(source).__name__}")

    def _dispense_with_content_tracking(self, destination: Labware, col: int, row: int, volume: float) -> None:
        """Dispense with content tracking."""

        if not self._simulation_mode:
            self._check_abort_and_pause()
        # Check if each tip needs separate destination item. get item/items
        if self.multichannel and destination.each_tip_needs_separate_item():
            items = [self._get_content_item(destination, col, row + i)
                     for i in range(self.tip_count)]
            volume_per_item = volume / self.tip_count
        else:
            items = [self._get_content_item(destination, col, row)]
            volume_per_item = volume

        # Validate items exist
        if any(item is None for item in items):
            raise ValueError(f"Content item not found at position ({col}, {row})")

        # Transfer content from tips to destination
        if len(items) == 1 and self.multichannel:
            # All tips dispense to one item (like Reservoir)
            item = items[0]
            for tip_idx in range(self.tip_count):
                tip_content = self.tip_dict[tip_idx]
                tip_total = sum(tip_content.values()) if tip_content else 0.0

                if tip_total > 0:
                    tip_volume_to_dispense = volume / self.tip_count
                    removal_ratio = tip_volume_to_dispense / tip_total

                    for content_type in list(tip_content.keys()):
                        remove_amount = tip_content[content_type] * removal_ratio
                        item.add_content(content_type, remove_amount)
                        tip_content[content_type] -= remove_amount
                        if tip_content[content_type] <= 1e-6:
                            del tip_content[content_type]
        else:
            # Each tip dispenses to its own item (like wells in plate)
            for tip_idx, item in enumerate(items):
                if item and volume_per_item > 0:
                    tip_content = self.tip_dict[tip_idx]
                    tip_total = sum(tip_content.values()) if tip_content else 0.0

                    if tip_total <= 0:
                        continue

                    removal_ratio = volume_per_item / tip_total

                    for content_type in list(tip_content.keys()):
                        remove_amount = tip_content[content_type] * removal_ratio
                        item.add_content(content_type, remove_amount)
                        tip_content[content_type] -= remove_amount
                        if tip_content[content_type] <= 1e-6:
                            del tip_content[content_type]

        self._move_to_and_dispense(items, volume)

    def _dispense_physical_only(self, destination: Labware, col: int, row: int, volume: float) -> None:
        """Dispense without content tracking."""

        # Get items
        if self.multichannel and destination.each_tip_needs_separate_item():
            items = [self._get_content_item(destination, col, row + i)
                     for i in range(self.tip_count)]
        else:
            item = self._get_content_item(destination, col, row)
            items = [item if item else destination]

        self._move_to_and_dispense(items, volume)
        print(f"  → Note: Content tracking not available for {type(destination).__name__}")

    def _move_to_and_aspirate(self, items: List[Labware], volume: float) -> None:
        """
        Move to position and perform aspiration.

        For multichannel, moves to the CENTER of all tip positions.

        Parameters
        ----------
        items : List[Labware]
            List of items to aspirate from (1 for single channel, 8 for multichannel)
        volume : float
            Total volume to aspirate
        """


        if not items:
            raise ValueError("No items provided")

        # Calculate center position for robot movement
        x, y = self._get_robot_xy_position(items)

        # Use first item for height calculation (all items should be at same Z level)
        item = items[0]
        parent_labware = self._find_parent_labware(item)

        # Determine RELATIVE height from labware top
        if hasattr(item, 'shape') and item.shape:
            volume_per_tip = volume / self.tip_count
            if parent_labware.each_tip_needs_separate_item():
                relative_z = calculate_dynamic_remove_height(item, volume_per_tip)
            else:
                relative_z = calculate_dynamic_remove_height(item, volume)
            liquid_height = calculate_liquid_height(item)

            print(f"  → Dynamic aspiration: {relative_z:.1f}mm from bottom "
                  f"(liquid: {liquid_height:.1f}mm, shape: {item.shape})")

        elif hasattr(parent_labware, 'remove_height'):
            relative_z = parent_labware.remove_height
            print(f"  → Fixed aspiration: {relative_z:.1f}mm from bottom")

        else:
            relative_z = item.size_z * 0.75
            print(f"  → Fallback aspiration: 5 mm above bottom")

        pipettor_z = self._get_pipettor_z_coord(parent_labware, relative_z, child_item=item)
        print(f"x, y, z = {x}, {y}, {pipettor_z}")
        if not self._simulation_mode:
            self._check_abort_and_pause()
            self.move_xy(x, y)
            self.move_z(pipettor_z)
            self.aspirate(volume / self.tip_count)
            self.move_z(0)

    def _move_to_and_dispense(self, items: List[Labware], volume: float) -> None:
        """
        Move to position and perform dispense.

        For multichannel, moves to the CENTER of all tip positions.

        Parameters
        ----------
        items : List[Labware]
            List of items to dispense to (1 for single channel, 8 for multichannel)
        volume : float
            Total volume to dispense
        """

        if not items:
            raise ValueError("No items provided")

        # Calculate center position for robot movement
        x, y = self._get_robot_xy_position(items)

        # Use first item for height calculation
        item = items[0]
        parent_labware = self._find_parent_labware(item)

        # Determine RELATIVE height from labware BOTTOM
        if hasattr(item, 'shape') and item.shape:
            volume_per_tip = volume / self.tip_count
            if parent_labware.each_tip_needs_separate_item():
                relative_z = calculate_dynamic_remove_height(item, -volume_per_tip) + 5
            else:
                relative_z = calculate_dynamic_remove_height(item, -volume) + 5
            liquid_height = calculate_liquid_height(item)

            print(f"  → Dynamic dispensing: {relative_z:.1f}mm from bottom "
                  f"(liquid: {liquid_height:.1f}mm, shape: {item.shape})")

        elif hasattr(parent_labware, 'add_height'):
            relative_z = parent_labware.add_height
            print(f"  → Fixed dispensing: {relative_z:.1f}mm from bottom")
        else:
            relative_z = item.size_z
            print(f"  → Fallback dispensing: item.size_z")

        pipettor_z = self._get_pipettor_z_coord(parent_labware, relative_z, child_item=item)
        print(f"x, y, z = {x}, {y}, {pipettor_z}")
        if not self._simulation_mode:
            self._check_abort_and_pause()
            self.move_xy(x, y)
            self.move_z(pipettor_z)
            self.dispense(volume / self.tip_count)
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

    def initialize_tips(self) -> None:
        """Clear tip content when tips are discarded."""
        self.has_tips = False
        self.tip_dict = {i: {} for i in range(self.tip_count)}
        print(f"  → Tips discarded, content cleared")

    def _calculate_volumes(self, volume_per_well: float) -> tuple[int, int]:
        """Helper: Calculate volume per position and max volume per aspirate."""
        volume_per_position = int(volume_per_well * self.tip_count)
        max_vol_per_aspirate = int(self.tip_volume * self.tip_count)

        if volume_per_position <= 0:
            raise ValueError("volume_per_well must be > 0")

        return volume_per_position, max_vol_per_aspirate

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
            self.pick_tips(lw)
        elif self.change_tips and self.has_tips:
            self.replace_tips(lw)
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

    def _find_parent_labware(self, item: Labware) -> Labware:
        """
        Find the parent labware that contains this item.

        For a Well, the parent is the Plate.
        For a Reservoir, the parent is the ReservoirHolder.
        For standalone labware, returns the item itself.
        """
        # Check if this item IS the top-level labware
        if item.labware_id in self._deck.labware:
            return item

        # Otherwise, search through all labware to find which one contains this item
        for labware_id, labware in self._deck.labware.items():
            # Check if it's a Plate containing this well
            if hasattr(labware, 'get_wells'):
                wells = labware.get_wells()
                for well in wells.values():
                    if well and well.labware_id == item.labware_id:
                        return labware

            # Check if it's a ReservoirHolder containing this reservoir
            if hasattr(labware, 'get_reservoirs'):
                reservoirs = labware.get_reservoirs()
                for reservoir in reservoirs:
                    if reservoir.labware_id == item.labware_id:
                        return labware

            # Check if it's a PipetteHolder containing this individual holder
            if hasattr(labware, 'get_individual_holders'):
                holders = labware.get_individual_holders()
                for holder in holders.values():
                    if holder and holder.labware_id == item.labware_id:
                        return labware

        raise ValueError(f"Could not find parent labware for item {item.labware_id}")

    def _get_pipettor_z_coord(self, labware:Labware, relative_z: float, child_item: Labware = None) -> float:
        """
        Convert relative height to absolute height, passable to pipettor with and without tips.

        If child_item is provided, the calculation is based on the child's bottom position.
        Otherwise, it's based on the labware's bottom.

        Parameters
         ----------
        labware : Labware
            The parent labware (Plate, ReservoirHolder, PipetteHolder, etc.)
        relative_z : float
            Height relative to the BOTTOM of the child item (or labware if no child):
            - 0 = bottom of well/reservoir/holder
            - Positive values = higher up from bottom
        child_item : Labware, optional
            The specific child item being accessed (Well, Reservoir, IndividualPipetteHolder).
            If None, uses labware's bottom as reference.

        Returns
        -------
        float
            Pipettor Z coordinate (how far down pipettor moves from home position)

        """

        # Find the slot that contains this labware. essential to get min_z and max_z
        slot_id = self._deck.get_slot_for_labware(labware.labware_id)

        if slot_id is None:
            raise ValueError(f"Labware {labware.labware_id} is not placed in any slot")

        slot = self._slots[slot_id]

        if labware.labware_id not in slot.labware_stack:
            raise ValueError(f"Labware {labware.labware_id} not found in slot {slot_id}")

        _, (min_z, max_z) = slot.labware_stack[labware.labware_id]

        # Determine child depth
        child_depth = 0.0

        if child_item is not None:
            child_depth = child_item.size_z


        reference_bottom = max_z - child_depth
        absolute_height = reference_bottom + relative_z
        #print(f"reference_bottom({reference_bottom}) = max_z({max_z}) - child_depth ({child_depth})")
        #print(f"absolute_height ({absolute_height}) = reference_bottom ({reference_bottom})+ liquid_height({relative_z}) ")

        if absolute_height < reference_bottom:
            #print(f"absolute_height({absolute_height}) cannot be less than reference_bottom({reference_bottom}). New Absolute height = {reference_bottom} + 1")
            absolute_height = reference_bottom + 1

        deck_range_z = self._deck.range_z

        if self.has_tips:
            pipettor_z = deck_range_z - absolute_height - self.tip_length
            print(f"pipettor_z({pipettor_z}) = deck_range_z({deck_range_z}) - absolute_height ({absolute_height}) - self.tip_length({self.tip_length})")
            # Validation with tips
            if pipettor_z < 0:
                raise ValueError(
                    f"Cannot reach pipettor_z={pipettor_z:.1f}mm with tips attached "
                    f"Maximum reachable height: {deck_range_z - self.tip_length:.1f}mm "
                )
            elif pipettor_z > Z_MAX:
                raise ValueError(f"pipettor_z cannot be higher than Z_MAX: {pipettor_z:.1f}mm ")


        else:
            # No tips - full range available
            pipettor_z = deck_range_z - absolute_height
            print(f"No Tips: pipettor_z({pipettor_z}) = deck_range_z({deck_range_z}) - absolute_height ({absolute_height})")

            # Validation without tips
            if pipettor_z < 0:
                raise ValueError(
                    f"Invalid height: absolute_z={absolute_height:.1f}mm exceeds deck range={deck_range_z:.1f}mm"
                )
            elif pipettor_z > Z_MAX:
                raise ValueError(f"pipettor_z cannot be higher than Z_MAX: {pipettor_z:.1f}mm ")
        print(f"{labware.labware_id}: {pipettor_z}mm")
        return pipettor_z

    def _get_robot_xy_position(self, items: List[Labware]) -> tuple[float, float]:
        """
        Calculate where the robot arm should move to access the given items.

        The robot arm position depends on the pipettor configuration:

        Single channel (1 tip):
            Robot moves directly to the item's position.
            Robot arm = Tip position

        Multichannel (8 tips):
            Robot moves to the CENTER of all items.
            Robot arm is at geometric center, tips span from first to last item.

        Parameters
        ----------
        items : List[Labware]
            Items to access. Must have 1 item for single channel,
            or tip_count items for multichannel.

        Returns
        -------
        tuple[float, float]
            (x, y) coordinates for robot arm movement

        Examples
        --------
        Single channel accessing well (0,0) at position (10, 20):
            items = [well_0_0]
            Returns: (10, 20)

        Multichannel accessing wells (0,0) to (0,7):
            items = [well_0_0, well_0_1, ..., well_0_7]
            Well (0,0) at (10, 10), Well (0,7) at (10, 73)
            Returns: (10, 41.5) - the midpoint
        """
        if not items:
            raise ValueError("No items provided for positioning")

        # Single channel: use item position directly
        if not self.multichannel:
            if items[0].position is None:
                raise ValueError(f"Item {items[0].labware_id} has no position set")
            return items[0].position

        # Multichannel: calculate center of span
        if len(items) != self.tip_count and items[0].each_tip_needs_separate_item() == False:
            raise ValueError(
                f"Multichannel requires {self.tip_count} items, got {len(items)}"
            )

        # Get first and last positions
        first_pos = items[0].position
        last_pos = items[-1].position

        if first_pos is None or last_pos is None:
            raise ValueError("Items must have positions set")

        x_first, y_first = first_pos
        x_last, y_last = last_pos

        # Calculate center
        x_center = (x_first + x_last) / 2
        y_center = (y_first + y_last) / 2

        if self.multichannel:
            print(f"  → Multichannel positioning: center ({x_center:.1f}, {y_center:.1f}) "
                  f"spanning ({x_first:.1f},{y_first:.1f}) to ({x_last:.1f},{y_last:.1f})")

        return x_center, y_center

    def measure_foc(self, seconds: int, platename: str = None, bat_script_path: str = None):
        """
        Wait for specified seconds, then run FOC measurement script.
        """

        # Use provided path or stored path
        if bat_script_path is not None:
            self.foc_bat_script_path = bat_script_path

        # Use provided plate name or stored plate name
        if platename is not None:
            plate_to_use = platename
        elif hasattr(self, 'foc_plate_name') and self.foc_plate_name:
            plate_to_use = self.foc_plate_name
        else:
            raise ValueError("Plate name not provided and no plate name configured")

        # Check if we have a script path
        if not hasattr(self, 'foc_bat_script_path') or self.foc_bat_script_path is None:
            raise ValueError("FOC bat script path not set. Please configure FOC first.")

        # Verify file exists
        if not os.path.exists(self.foc_bat_script_path):
            raise FileNotFoundError(f"FOC bat script not found at: {self.foc_bat_script_path}")

        if self._simulation_mode:
            print(f"[SIMULATION] Would wait {seconds} seconds, then run FOC for plate '{plate_to_use}'")
            return  # Exit early - don't run the actual script

        # Wait for specified time
        print(f"Waiting {seconds} seconds before FOC measurement...")
        time.sleep(seconds)

        # Run the bat script
        self.home()
        print(f"Running FOC measurement for plate: {plate_to_use}")
        try:
            subprocess.call([self.foc_bat_script_path, plate_to_use])
            print(f"FOC measurement completed for {plate_to_use}")
        except Exception as e:
            print(f"[ERROR] Failed to run FOC measurement: {str(e)}")
