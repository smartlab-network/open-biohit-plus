from biohit_pipettor import Pipettor
from typing import Literal, List, Optional, Union
from math import ceil

from .cursor import total_volume
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
        self.change_tips = 0    #control if tips are to be changed

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

                #TODO understand height attribute
                self.move_z(22)  # pick_height
                self.pick_tip()

                # Mark all tips in this column as removed
                pipette_holder.remove_pipettes_from_columns([col])
                self.has_tips = True
                print(f"Picked up tips from column {col}")
                break

            except CommandFailed:
                print(f"Failed to pick tips from column {col}: {e}")
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
            raise ValueError("Pick tips only work on pipette_holders")

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
                #TODO Fix height
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

    def discard_tips(self, tip_dropzone_id: Labware) -> None:
        """
               Discard tips to a TipDropzone.
               Parameters
               ----------
               tip_dropzone_id : str
                   ID of the TipDropzone labware
               """

        if not self.has_tips:
            print("Warning: No tips to discard")
            return

        tip_dropzone = self._find_labware(tip_dropzone_id, TipDropzone)
        x, y = tip_dropzone.position
        self.move_xy(x, y)
        self.move_z(tip_dropzone.drop_height_relative)
        self.eject_tip()
        self.initialize_tips()
        self.move_z(0)

    def replace_multi_tips(self, pipette_holder_id: str) -> None:

        if self.multichannel:
            self.return_multi_tips(pipette_holder_id)
            self.pick_multi_tips(pipette_holder_id)

    def suck(self, volume: float, height: float) -> None:
        pass

    def replace_multi(self):
        #remove and fill
        pass

    def remove_multi(self):
        pass


    def fill_multi(self, source_lw : Labware, source_columns: list[int], source_volume_per_column, destination_lw : Labware, destination_columns: list[int], destination_volume_per_column:float) -> None:
        """
        Fill_multi aspirates liquid (source volume) from source column, found at source labware.
        Then it dispenses destination volume  to destination columns, found at destination labware.

        source_column can be a list, meaning destination volume can be aspirated from various source_columns. check to see if column is in place
        Destination_columns can be a list meaning volume can be dispensed to multiple columns. Check to see if column is in place

        let's say a source column is [1,3] and source_volume_per_column is 500. dispense volume is 250ul per column for columns [1,2,3,4]. Since tip volume is 1000, the pipette will aspirate 500ul from 1 and 500 from 3.  Since total volume aspriated is >= than total to dispense, then it will dispense 250 to remaining columns. Lastly it will go to waste and dispense everything
             If source_volume_per_column was 550 for col[1,3] and dispense volume is 275. Since tip volume is 550, it will aspirate from 1. dispense , finish the loop(dispense) and do it again.

            tip content and volume_remaining will be tracked during this time

        If tip_volume allows, the pipettor will aspirate for several columns at once.
        """

        if not self.multichannel:
            raise ValueError("fill_multi_tips requires multichannel pipettor")

        total_vol_to_aspirate = source_volume_per_column * len(source_columns) * self.tip_count
        total_vol_to_dispense = destination_volume_per_column * len(destination_columns) * self.tip_count

        if total_vol_to_aspirate != total_vol_to_dispense:
            raise ValueError("total_vol_to_aspirate should be equal to total_vol_to_dispense.")

        source_lw.id = source_lw.labware_id
        destination_lw.id = destination_lw.labware_id

        # any parent labware that contain labware in them has rows and cols attribute. Only columns change are physically possible due to nature of multi Pipettor.
        if hasattr(source_lw, "_rows") and hasattr(source_lw, "_columns") and hasattr(destination_lw, "_rows") and hasattr(destination_lw, "_columns") :
            if not isinstance(source_lw, (Plate, ReservoirHolder)) or not isinstance(destination_lw, (Plate, ReservoirHolder)):
                raise ValueError("Only (plate & reservoir) contain labware within them (wells, reservoirs) with volume attribute. Please Update the code for your labware")

            # write a check to see if i and j is in range of _cols attribute.
            source_columns_id =[f'{self.source_labware_id}_{i}:0' for i in source_columns]
            destination_columns_id = [f'{self.destination_labware_id}_{j}:0' for j in destination_columns]

            #get access to each labware position attribute


            print(destination_columns_id)
            print(source_columns_id)

    def labware_suck(self, lw: Labware, columns: list[int], vol_per_column: float):

        if not self.multichannel:
            raise ValueError("fill_multi_tips requires multichannel pipettor")

        total_vol_to_aspirate = vol_per_column * len(columns)
        lw.id = lw.labware_id

        if hasattr(lw, "_rows") and hasattr(lw, "_columns"):
            if not isinstance(lw, (Plate, ReservoirHolder)):
                raise ValueError(
                    "Only (plate & reservoir) contain volume attribute. Please Update the code for your labware")

            # Validate column indices are in range
            for col in columns:
                if col < 0 or col >= lw._columns:
                    raise ValueError(
                        f"Source column {col} out of range (0 to {lw._columns - 1})"
                    )

            column_labware_ids = [f'{lw.id}_{i}:0' for i in columns]

            #move z to 0. start aspiration as said





    def change_medium_multi(self):
        pass

    def dilute_multi(self):
        pass

    def spit(self):
        pass

    def spit_all(self):
        pass

    def home(self):
        self.move_z(0)
        self.move_xy(0, 0)

    # Helper functions. Not necessarily available for GUI
    def _find_labware(self, labware_id: str, expected_type: type = None) -> Labware:
        """Find labware by ID, verify it's the expected type, and confirm it's placed in a slot."""
        # Check if labware exists in deck's global dictionary
        if labware_id not in self.deck.labware:
            raise ValueError(f"Labware '{labware_id}' not found in deck")

        labware = self.deck.labware[labware_id]

        # Verify labware is the expected type (if specified)
        if expected_type is not None and not isinstance(labware, expected_type):
            raise ValueError(f"Labware '{labware_id}' is not of type {expected_type.__name__}")

        # Verify labware is actually placed in a slot
        labware_placed = False
        for slot_id, slot in self.slots.items():
            if labware_id in slot.labware_stack:
                labware_placed = True
                print(f" ✓ Labware '{labware_id}' found in slot '{slot_id}'")
                break

        if not labware_placed:
            raise ValueError(f"Labware '{labware_id}' exists in deck but is not placed in any slot")

        return labware

    def initialize_tips(self) -> None:
        """Clear tip content when tips are discarded."""
        self.has_tips = False
        self.tip_content = {}
        self.volume_present_in_tip = 0.0
        print(f"  → Tips discarded, content cleared")


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

    def find_labware_location(self):
        pass

