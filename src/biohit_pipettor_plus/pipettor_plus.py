from biohit_pipettor import Pipettor
from typing import Literal

class PipettorPlus(Pipettor):
    def __init__(self, tip_volume: Literal[200, 1000], *, multichannel: bool, initialize: bool = True):
        """
                Interface to the Biohit Roboline pipettor

                :param tip_volume: The tip volume (must be 1000 if multichannel is True)
                :param multichannel: If True, it is assumed the device uses a multichannel pipet
                :param initialize: If True, the device will be initialized
                """
        super().__init__(tip_volume=tip_volume, multichannel=multichannel, initialize=initialize)

