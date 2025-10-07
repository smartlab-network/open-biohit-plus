from ..biohit_pipettor_plus.deck import Deck
from ..biohit_pipettor_plus.slot import Slot
from ..biohit_pipettor_plus.labware import Plate, PipetteHolder, TipDropzone, ReservoirHolder, IndividualPipetteHolder
from ..biohit_pipettor_plus.labware import Well
from ..biohit_pipettor_plus.serializable import Serializable
import json
from ..biohit_pipettor_plus.control_json import read_json, write_json

deck1 = Deck((0,500), (0,500), "deck1")

slot1 = Slot((100, 200), (0, 50), 500, "slot1")
slot2 = Slot( (200, 300), (100,200), 25, "slot2")
slot3 = Slot((300, 400), (200, 250), 500, "slot3")
slot4 = Slot((400, 450), (50, 100), 500, "slot4")
slot5 = Slot((450, 500), (50, 100), 500, "slot5")
slot6 = Slot((100, 300), (50, 100), 500, "slot6")


deck1.add_slots([slot1, slot2, slot3, slot4, slot5])

#plate & well creating and checking
example_well = Well(size_x=2, size_y=1, size_z=5, content={"water": "750", "pbs" : "250"})
plate1 = Plate(20, 50, 50, 6, 9, (3, 5), well=example_well)
deck1.add_labware(plate1, slot_id="slot1", min_z=2)
print(plate1.to_dict())

"""write_json(slot2)
# Serialisierung

write_json(deck1)
print(deck1.to_dict())

# Deserialisierung
restored_deck = read_json("deck1")

print(type(restored_deck))
print(restored_deck.slots)
print(restored_deck.labware)
"""

reservoirs_data = {
    1: {"size_x": 10, "size_y": 20, "size_z": 10, "capacity": 30000,
        "filled_volume": 0, "content": "waste"},

    2: {"size_x": 10, "size_y": 20, "size_z": 12, "capacity": 30000,
        "filled_volume": 30000, "content": "0 conc"},

    3: {"size_x": 15, "size_y": 20, "size_z": 15, "capacity": 30000,
        "filled_volume": 100, "content": "1.8 conc"},

    4: {"size_x": 15, "size_y": 30, "size_z": 15, "capacity": 30000,
        "filled_volume": 100, "content": "5 conc"},

    5: {"size_x": 15, "size_y": 20, "size_z": 15, "capacity": 30000,
        "filled_volume": 100, "content": "15 conc"},

    6: {"size_x": 15, "size_y": 20, "size_z": 15, "capacity": 30000,
        "filled_volume": 100, "content": "0 conc"},

    7: {"size_x": 35, "size_y": 20, "size_z": 15, "capacity": 30000,
        "filled_volume": 100, "content": "waste"},

}

reservoirHolder = ReservoirHolder(
    size_x= 100,
    size_y=50,
    size_z= 20,
    offset=(4,4),
    hooks_across_x = 6,
    hooks_across_y=2,
    reservoir_dict = reservoirs_data,
)

deck1.add_labware(reservoirHolder, slot_id="slot3", min_z=2)
print(reservoirHolder.to_dict())

ExamplePipetteHolder = IndividualPipetteHolder(1,1,1)
pipette_holder = PipetteHolder(labware_id="pipette_holder_1", size_x = 10, size_y = 20, size_z=20, holders_across_x=6, holders_across_y=8, individual_holder= ExamplePipetteHolder)
deck1.add_labware(pipette_holder, slot_id="slot5", min_z=2)

# col and row are zero indexed
print(pipette_holder.to_dict())


#TODO understand drop zone and see how to implement it.
tip_dropzone = TipDropzone(
    size_x=50,
    size_y=50,
    size_z=20,
    offset=(54,15),  # Center of the dropzone in X and Y (relative to slot)
    labware_id="dropzone_1",
    drop_height_relative=15  # Drop height 15mm above the dropzone base
)
deck1.add_labware(tip_dropzone, slot_id="slot2", min_z=2)
print(tip_dropzone.to_dict())
print(deck1.to_dict())