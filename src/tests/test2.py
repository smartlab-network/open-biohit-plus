from ..biohit_pipettor_plus.control_json import read_json
from ..biohit_pipettor_plus.labware import Labware, Plate
from ..biohit_pipettor_plus.serializable import Serializable
from ..biohit_pipettor_plus.deck import Deck
from ..biohit_pipettor_plus.slot import Slot

restored_deck = read_json("deck1")
restored_slot = read_json("slot2")
print(type(restored_deck), 1)
print(restored_deck.slots, 2)
print(restored_deck.labware, 3)
print("-----------------")
print(type(restored_slot))
print(restored_slot.labware)