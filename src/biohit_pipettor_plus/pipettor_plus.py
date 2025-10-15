from .pipettor import Pipettor
from typing import Literal, List, Optional, Union, Tuple
from math import ceil

#from .cursor import total_volume
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

        #Todo understand drop height
        x, y = tip_dropzone.position
        self.move_xy(x, y)
        self.move_z(tip_dropzone.drop_height_relative)
        self.eject_tip()
        self.initialize_tips()
        self.move_z(0)

    def replace_multi_tips(self, pipette_holder: Labware) -> None:
        """ Replace multiple tips. By return current tips to and picking new ones from the pipette_holder.
            Does not take tips from the column it returned to """
        if  not isinstance(pipette_holder, PipetteHolder):
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
                   source_col_row: Tuple[int, int],
                   destination: Plate,
                   volume_per_well: float,
                   dest_col_row: List[Tuple[int, int]]) -> None:
        """
        Add medium from reservoir to plate wells.

        Parameters
        ----------
        source : ReservoirHolder
            Source reservoir holder
        source_col_row : Tuple[int, int]
            Column index in reservoir holder (which reservoir to use)
        destination : Plate
            Destination plate
        volume_per_well : float
            Volume to add per well (µL)
        dest_col_row : Tuple[int, int]
            Destination column and row to aspirate.

        Example
        -------
        # Add 200µL medium from reservoir column 0 to plate columns 0, 1, 2
        pipettor.add_medium(reservoir_holder, 0, plate1, 200, [0, 1, 2])
        """

        if not self.multichannel:
            raise ValueError("add_medium requires multichannel pipettor")

        #todo write find labware by type
        self.check_tips()

        self.check_col_row(source_col_row, source)
        self.check_col_row(dest_col_row, destination)

        # Calculate volumes
        volume_per_column = volume_per_well * self.tip_count  # Total for all 8 tips
        max_vol_per_aspirate = self.tip_volume * self.tip_count  # Max tips can hold

        for dest_col in dest_columns:
            volume_remaining = volume_per_column

            while volume_remaining > 0:
                # Aspirate as much as tips can hold
                vol_to_transfer = min(volume_remaining, max_vol_per_aspirate)

                # Aspirate from reservoir
                self.suck(source, vol_to_transfer, source_column)

                # Dispense to plate
                self.spit(destination, dest_col, vol_to_transfer)

                volume_remaining -= vol_to_transfer

                print(f"  Transferred {vol_to_transfer}µL to column {dest_col}, "
                      f"{volume_remaining}µL remaining for this column")


    def change_medium_multi(self):
        pass

    def dilute_multi(self):
        pass

    def spit_all(self):
        pass

    def home(self):
        self.move_z(0)
        self.move_xy(0, 0)

    def initialize_tips(self) -> None:
        """Clear tip content when tips are discarded."""
        self.has_tips = False
        self.tip_content = {}
        self.volume_present_in_tip = 0.0
        print(f"  → Tips discarded, content cleared")

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
        if self.change_tips and not self.has_tips:
            self.pick_multi_tips()
        elif self.change_tips and self.has_tips:
            self.replace_multi_tips()
        elif not self.has_tips:
            raise ValueError("No tips loaded. Pick tips first.")

    def check_col_row(self, col_row: Union[Tuple[int, int], List[Tuple[int, int]]], lw: Labware) -> None:
        """
        Raises ValueError if (col, row) are out of bounds of the labware.
        """

        #checks if labware has _columns & _rows
        if not (hasattr(lw, "_columns") and  hasattr(lw, "_rows")):
            raise ValueError(
                f"Invalid Labware {lw}. Labware lacks _rows or _columns attributes. "
                f"Check implementation for ReservoirHolder, PipetteHolder, or Plate.")

        #coverts col_row types to list
        if isinstance(col_row, tuple):
            coordinates = [col_row]
        elif isinstance(col_row, list):
            coordinates = col_row
        else:
            raise TypeError(f"col_row must be a tuple or list of tuples, got {type(col_row)}")

        for coord in coordinates:
            #loops through each col, row. Raising value error if out of bound.
            col, row = coord
            if col < 0 or col >= lw._columns:
                raise ValueError(f"columns in ({coord}) must be between 0 and {lw._columns - 1}. Columns are 0 indexed")

            if row < 0 or row >= lw._rows:
                raise ValueError(f"rows in ({coord}) must be between 0 and {lw._row - 1}. rows are 0 indexed")







