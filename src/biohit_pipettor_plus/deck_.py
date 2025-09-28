class Deck:
    """
    Defines the Deck
    :param initialize: If True, the device will be initialized
    """
    labware_folder: str = r"C:\Labhub\Import\Labware"
    deck_filename:     str = r"biohit_deck_default.json"

    lDir:str='LABWARE_DIR'

    #range_x = 246
    #range_y = 210

    if env(lDir) is not None:
        labware_folder= env(lDir)


    _tipPosition: str = "B2"
    _deckPosition = {   "A1" : [265.60,  0.09], "A2" : [127.80,  0.00],
                        "B1" : [265.60, 52.75], "B2" : [127.80, 52.75],
                        "C1" : [265.60,148.25], "C2" : [127.80,148.25] }

    _refPosition = {    "P1" : [239.49, 43.00, 6.80],
                        "P2" : [26.11, 43.00, 6.80], 
                        "P3" :[132.8,170.5, 41.40]}

    def __init__(self):    


        @property
        def tipPosition(self) -> str:
            """True if the device is connected, False otherwise"""
            return self._tipPosition

        @tipPosition.setter
        def tipPosition(self, sPosition):
            self._tipPosition=sPosition

        def tipCoordinates(self):
            return self._deckPosition[self._tipPosition]
     #   pass