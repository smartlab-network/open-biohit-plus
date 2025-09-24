from ..biohit_pipettor_plus.control_json import read_json
from ..biohit_pipettor_plus.deck import Deck
from ..biohit_pipettor_plus.slot import Slot
from ..biohit_pipettor_plus.labware import *

deck1:Deck = read_json("deck_1")

slots = deck1.slots

for slot in slots.keys():
    for labware in slots[slot].labware_stack.items():
        labware_obj = labware[1][0]
        print(type(labware[1][0]), labware[1][0])
        if isinstance(labware[1][0], Plate):
            labware_obj.plate = labware[1][0]
