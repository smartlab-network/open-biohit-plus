from ..biohit_pipettor_plus.deck import Deck
from ..biohit_pipettor_plus.slot import Slot
from ..biohit_pipettor_plus.labware import Plate, PipetteHolder, TipDropzone, ReservoirHolder
from ..biohit_pipettor_plus.labware import Well
from ..biohit_pipettor_plus.serializable import Serializable
import json
from ..biohit_pipettor_plus.control_json import read_json, write_json

deck1 = Deck((0,500), (0,500), "deck1")

slot1 = Slot((100, 300), (50, 100), 500, "slot1")
slot2 = Slot( (300, 400), (100,200), 25, "slot2")
slot3 = Slot((400, 500), (200, 250), 500, "slot3")
slot4 = Slot((100, 300), (50, 100), 500, "slot4")
slot5 = Slot((100, 300), (50, 100), 500, "slot5")
slot6 = Slot((100, 300), (50, 100), 500, "slot6")


deck1.add_slots([slot1, slot2, slot3])

example_well = Well(size_x=2, size_y=1, size_z=5, media="water")
plate1 = Plate(20, 10, 50, 7, 8, (30, 50), well = example_well)
deck1.add_labware(plate1, slot_id="slot1", min_z=2)
slot1.allocate_position(plate1, (5,5), 1.25,2.5, plate1.wells_x, plate1.wells_y)
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

    4: {"size_x": 15, "size_y": 20, "size_z": 15, "capacity": 30000,
        "filled_volume": 100, "content": "5 conc"},

    5: {"size_x": 15, "size_y": 20, "size_z": 15, "capacity": 30000,
        "filled_volume": 100, "content": "15 conc"},

    6: {"size_x": 15, "size_y": 20, "size_z": 15, "capacity": 30000,
        "filled_volume": 100, "content": "0 conc"},

    7: {"size_x": 15, "size_y": 20, "size_z": 15, "capacity": 30000,
        "filled_volume": 100, "content": "waste"},

}

reservoirHolder = ReservoirHolder(
    size_x= 80,
    size_y= 50,
    size_z= 20,
    hooks_across_x = 4,
    hooks_across_y=2,
    reservoir_dict = reservoirs_data,
)

deck1.add_labware(reservoirHolder, slot_id="slot3", min_z=2)
slot3.allocate_position(
        reservoirHolder,
        (8,8),
        2.5,
        2.5,
        reservoirHolder.hooks_across_x,
        reservoirHolder.hooks_across_y,
        )

data = reservoirHolder.to_dict()
print(data)
"""
print(reservoirHolder.position)
print(reservoirHolder.hook_id_to_position(6))
print(reservoirHolder.position_to_hook_id(1,1))
print((reservoirHolder.get_reservoirs()))
print(f"get_hook_to_reservoir_map: {reservoirHolder.get_hook_to_reservoir_map()}")
print(reservoirHolder.get_occupied_hooks())
print(reservoirHolder.get_available_hooks())
print(reservoirHolder.get_waste_containers())
print(f"water: {reservoirHolder.get_equivalent_containers("water")}")
print(reservoirHolder.get_reservoir_by_content("15 conc"))
reservoirHolder.add_volume(1,20000)
#reservoirHolder.remove_volume(4,1000)
#new_reservoir = ReservoirHolder.from_dict(data)
#print(new_reservoir.to_dict())

"""

#TODO define pipette pick up and drop zone
pipette_holder = PipetteHolder(labware_id="pipette_holder_1", size_x = 10, size_y = 20, size_z=20)


#TODO understand drop zone and see how to implement it.
tip_dropzone = TipDropzone(
    size_x=50,
    size_y=50,
    size_z=20,
    drop_x=25,  # Center of the dropzone in X (relative to slot)
    drop_y=25,  # Center of the dropzone in Y (relative to slot)
    labware_id="dropzone_1",
    drop_height_relative=15  # Drop height 15mm above the dropzone base
)