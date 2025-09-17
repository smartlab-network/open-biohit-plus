from ..control_json import read_json
from ..labware import Labware, Plate
from ..serializable import Serializable
from ..deck import Deck
from ..slot import Slot

restored_deck = read_json("deck1")
restored_slot = read_json("slot2")
print(type(restored_deck), 1)
print(restored_deck.slots, 2)
print(restored_deck.labware, 3)
print("-----------------")
print(type(restored_slot))
print(restored_slot.labware)