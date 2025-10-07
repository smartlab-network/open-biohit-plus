from biohit_pipettor import Pipettor
from typing import Literal, List, Optional, Union
from math import ceil

from .deck import Deck
from .slot import Slot
from .labware import Labware, Plate, Well, ReservoirHolder, Reservoir, PipetteHolder, IndividualPipetteHolder, \
    TipDropzone, Pipettors_in_Multi


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
        self.has_tips = False
        self.tip_content: dict = {}  # Current content in tip as dict {content_type: volume}
        self.tip_volume_remaining: float = 0.0  # Volume remaining in tip

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

        if self.multichannel:
            self.return_multi_tips(pipette_holder_id)
            self.pick_multi_tips(pipette_holder_id)

    def suck(self, volume: float, height: float, reservoir_holder_id: str = None,
             hook_id: int = None) -> None:
        """
        Aspirate liquid and track volume in reservoir if specified
        
        Parameters
        ----------
        volume : float
            Volume to aspirate (µL)
        height : float
            Aspiration height (mm)
        reservoir_holder_id : str, optional
            ReservoirHolder ID for volume tracking
        hook_id : int, optional
            Hook ID in reservoir holder
        """
        max_vol_per_go = 200  # Conservative aspirate volume per step. allows for both 200 & 1000ul tips
        total_steps = ceil(volume / max_vol_per_go)
        
        source_content = None

        # If tracking reservoir, remove volume first (validates availability)
        if reservoir_holder_id and hook_id is not None:
            for slot in self.slots.values():
                if slot.labware and slot.labware.labware_id == reservoir_holder_id:
                    holder = slot.labware
                    if isinstance(holder, ReservoirHolder):
                        # Get content from reservoir at hook
                        hook_to_reservoir = holder.get_hook_to_reservoir_map()
                        if hook_id in hook_to_reservoir and hook_to_reservoir[hook_id]:
                            reservoir = hook_to_reservoir[hook_id]
                            source_content = reservoir.content
                        
                        # Multiply by Pipettors_in_Multi if multichannel
                        total_volume = volume * (Pipettors_in_Multi if self.multichannel else 1)
                        holder.remove_volume(hook_id, total_volume)
                        break

        for step in range(total_steps):
            vol = min(max_vol_per_go, volume - step * max_vol_per_go)
            self.move_z(height)
            self._aspirate_with_content_tracking(vol, source_content)

        self.move_z(0)

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
        """
        Dispense volume to a specific labware with content tracking.
        
        Parameters
        ----------
        volume : float
            Volume to dispense (µL)
        height : float
            Dispense height (mm)
        labware_id : str, optional
            ID of target labware for content tracking
        """
        self.move_z(height)
        self._dispense_with_content_tracking(volume, labware_id)
        self.move_z(0)


    def home(self):
        self.move_z(0)
        self.move_xy(0, 0)
        pass

    # Helper functions. Not necessarily available for GUI
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
        self.tip_content = {}
        self.tip_volume_remaining = 0.0
        print(f"  → Tips discarded, content cleared")

    def _aspirate_with_content_tracking(self, volume: float, source_content: Optional[str] = None) -> None:
        """
        Aspirate volume and update tip content tracking.
        
        Parameters
        ----------
        volume : float
            Volume to aspirate (µL)
        source_content : str, optional
            Content of the source labware. If None, no content tracking is performed.
        """
        self.aspirate(volume)
        
        if source_content:
            # Add content to tip dictionary
            if source_content in self.tip_content:
                self.tip_content[source_content] += volume
            else:
                self.tip_content[source_content] = volume
                
            self.tip_volume_remaining += volume
            print(f"  → Tip content updated: added {volume}µl of '{source_content}'")
            print(f"  → Current tip content: {self._get_tip_content_summary()}")

    def _dispense_with_content_tracking(self, volume: float, target_labware=None) -> None:
        """
        Dispense volume and update tip content tracking.
        
        Parameters
        ----------
        volume : float
            Volume to dispense (µL)
        target_labware : Labware or str, optional
            Target labware object or labware_id string to update content. If None, no target tracking is performed.
        """
        self.dispense(volume)
        
        # Handle both labware objects and labware_id strings
        labware_obj = None
        if isinstance(target_labware, str):
            try:
                labware_obj = self._find_labware(target_labware, Labware)
            except ValueError:
                print(f"  → Warning: Labware '{target_labware}' not found for content tracking")
        elif target_labware is not None:
            labware_obj = target_labware
        
        # Update target labware content if it has content tracking methods
        if labware_obj and hasattr(labware_obj, 'add_content') and self.tip_content:
            # Calculate proportion to dispense
            if self.tip_volume_remaining > 0:
                proportion = volume / self.tip_volume_remaining
                
                # Add each content type from tip to target and update tip content
                content_types = list(self.tip_content.keys())
                for content_type in content_types:
                    content_volume = self.tip_content[content_type]
                    dispensed_volume = content_volume * proportion
                    labware_obj.add_content(content_type, dispensed_volume)
                    
                    # Update tip content (remove dispensed amount)
                    self.tip_content[content_type] -= dispensed_volume
                    
                    # Clean up zero or negative volumes
                    if self.tip_content[content_type] <= 0:
                        del self.tip_content[content_type]
            
            print(f"  → Target content updated (dispensed {volume}µl)")
            
        # Update remaining tip volume
        self.tip_volume_remaining -= volume
        
        # Clear tip content if fully dispensed
        if self.tip_volume_remaining <= 0:
            self.tip_content = {}
            self.tip_volume_remaining = 0.0
            print(f"  → Tip emptied, content cleared")

    def _get_tip_content_summary(self) -> str:
        """
        Get a readable summary of tip content.
        Returns
        -------
        str
            Summary string like "PBS: 150µL, water: 100µL" or "empty"
        """
        if not self.tip_content or self.tip_volume_remaining <= 0:
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
            "volume_remaining": self.tip_volume_remaining,
            "is_empty": self.tip_volume_remaining <= 0,
            "content_summary": self._get_tip_content_summary()
        }