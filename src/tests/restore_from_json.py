from ..biohit_pipettor_plus.control_json import read_json
from ..biohit_pipettor_plus.deck import Deck
from ..biohit_pipettor_plus.slot import Slot
from ..biohit_pipettor_plus.labware import *

deck1:Deck = read_json("deck1")

print(deck1.slots)