from ..biohit_pipettor_plus.deck import Deck
from ..biohit_pipettor_plus.slot import Slot
from ..biohit_pipettor_plus.labware import Plate
from ..biohit_pipettor_plus.serializable import Serializable
import json
from ..biohit_pipettor_plus.control_json import read_json, write_json

plate1 = Plate(200, 100, 50, 7, 8, (30, 50), labware_id="plate1")
slot1 = Slot((100, 300), (50, 100), "slot1", plate1)
deck1 = Deck((0,500), (0,500), "deck1")
deck1.add_slot(slot1)

slot2 = Slot(range_x=(300, 400), range_y=(100,200), slot_id="slot2")
write_json(slot2)
# Serialisierung
write_json(deck1)
print(deck1.to_dict())

# Deserialisierung
restored_deck = read_json("deck1")

print(type(restored_deck))
print(restored_deck.slots)
print(restored_deck.labware)

