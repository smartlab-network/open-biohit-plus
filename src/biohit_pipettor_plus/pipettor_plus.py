from biohit_pipettor import Pipettor
from typing import Literal, List, Optional, Union
from math import ceil

from .deck import Deck
from .slot import Slot
from .labware import Labware, Plate, Well, ReservoirHolder, Reservoir, PipetteHolder, IndividualPipetteHolder, \
    TipDropzone


class PipettorPlus(Pipettor):
    def __init__(self, tip_volume: Literal[200, 1000], *, multichannel: bool, initialize: bool = True, deck: Deck):
        """
        Interface to the Biohit Roboline pipettor with modern deck/slot/labware structure

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
        self.initalize_tips()
    def pick_multi_tips(self, pipette_holder_id: str, columns: Optional[List[int]] = None) -> None:
        """
        Pick tips from a PipetteHolder going through specified columns (right to left).

        Parameters
        ----------
        pipette_holder_id : str
            ID of the PipetteHolder labware
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
        pipette_holder = self._find_labware(pipette_holder_id, PipetteHolder)

        if columns is None:
            columns = pipette_holder.get_occupied_columns()

        if not columns:
            raise ValueError(f"No occupied columns found in pipette holder {pipette_holder_id}")

        print(f"pick_multi_tips: start, trying columns {columns}")

        for col in sorted(columns):  # ascending trys
            # Get the position for the first row of this column
            holder_id = f'holder_{col}:0'
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

            except Exception as e:
                print(f"Failed to pick tips from column {col}: {e}")

                continue
            finally:
                self.move_z(0)
        else:
            raise RuntimeError(f"Failed to pick tips from any of the specified columns {columns}")


    def return_multi_tips(self, pipette_holder_id: str, columns: Optional[List[int]] = None) -> None:
        """
        Return tips to PipetteHolder in available columns (left to right).

        Parameters
        ----------
        pipette_holder_id : str
            ID of the PipetteHolder labware
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

            # Find the pipette holder
        pipette_holder = self._find_labware(pipette_holder_id, PipetteHolder)

        if columns is None:
            columns = pipette_holder.get_available_columns()

        if not columns:
            raise ValueError(f"No empty columns found in pipette holder {pipette_holder_id}")

        print(f"return_multi_tips: start, trying columns {columns}")

        for col in sorted(columns, reverse=True):  # descending trys
            # Get the position for the first row of this column
            holder_id = f'holder_{col}:0'
            individual_holder = pipette_holder.get_individual_holders().get(holder_id)

            if individual_holder is None or individual_holder.is_occupied:
                continue

            try:
                # Move to the tip return position
                if individual_holder.position is None:
                    raise ValueError(f"Individual holder {holder_id} has no position set")

                x, y = individual_holder.position
                self.move_xy(x, y)
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

    def discard_tips(self, tip_dropzone_id: str) -> None:
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
        self.return_multi_tips(pipette_holder_id)
        self.pick_multi_tips(pipette_holder_id)

    def fill_medium(self, plate_id: str):
        pass

    def remove_medium(self, plate_id: str):
        pass

    def replace_multi(self):
        pass

    def remove_multi(self):
        pass

    def fill_multi(self):
        pass

    def change_medium_multi(self):
        pass

    def dilute_multi(self):
        pass

    def spit_all(self):
        pass

    def spit(self, volume: float, height: float, labware_id: str = None):
        if labware_id is not None:
            labware_id.volume

        p.move_z(height)
        p.dispense(volume)
        p.move_z(0)


    def home(self):
        self.move_z(0)
        self.move_xy(0, 0)
        pass

""" Helper functions. Not available for GUI"""
    def _find_labware(self, labware_id: str, expected_type: type) -> Labware:
        """Find labware by ID, verify it's the expected type, and confirm it's placed in a slot."""
        # Check if labware exists in deck's global dictionary
        if labware_id not in self.deck.labware:
            raise ValueError(f"Labware '{labware_id}' not found in deck")

        labware = self.deck.labware[labware_id]

        # Verify labware is the expected type
        if not isinstance(labware, expected_type):
            raise ValueError(f"Labware '{labware_id}' is not of type {expected_type.__name__}")

        # Verify labware is actually placed in a slot
        labware_placed = False
        for slot_id, slot in self.slots.items():
            if labware_id in slot.labware_stack:
                labware_placed = True
                print(f"  ✓ Labware '{labware_id}' found in slot '{slot_id}'")
                break

        if not labware_placed:
            raise ValueError(f"Labware '{labware_id}' exists in deck but is not placed in any slot")

        return labware


    def initialize_tips(self) -> None:
        """Clear tip content when tips are discarded."""
        self.has_tips = False
        self.tip_content = None
        self.tip_volume_remaining = 0.0
        print(f"  → Tips discarded, content cleared")