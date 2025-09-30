from biohit_pipettor import Pipettor
from typing import Literal

from .deck import Deck


class PipettorPlus(Pipettor):
    def __init__(self, tip_volume: Literal[200, 1000], *, multichannel: bool, initialize: bool = True, deck: Deck):
        """
                Interface to the Biohit Roboline pipettor

                :param tip_volume: The tip volume (must be 1000 if multichannel is True)
                :param multichannel: If True, it is assumed the device uses a multichannel pipet
                :param initialize: If True, the device will be initialized
                """
        super().__init__(tip_volume=tip_volume, multichannel=multichannel, initialize=initialize)
        self.deck = deck
        self.slots: dict[str, Slot] = deck.slots


    def fill_medium(self, plate_id: str):
        pass

    def remove_medium(self, plate_id: str):
        pass

    def discard_tips(self) -> None:
        pass

    def  pick_multi_tips(self) -> None:
        pass

    def replace_tips(self) -> None:
        pass

    def replace_multi(self):
        pass

    def  remove_multi(self):
        pass

    def fill_multi(self):
        pass

    def change_medium_multi(self):
        pass

    def dilute_multi(self):
        pass

    def spite_all(self):
        pass

    def spit(self):
        pass

    def home(self):
        pass