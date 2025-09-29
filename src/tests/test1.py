from cffi.cffi_opcode import PRIM_FLOAT

from ..biohit_pipettor_plus.deck import Deck
from ..biohit_pipettor_plus.slot import Slot
from ..biohit_pipettor_plus.labware import Plate, PipetteHolder, TipDropzone, Reservoirs, Reservoir
from ..biohit_pipettor_plus.labware import Well
from ..biohit_pipettor_plus.serializable import Serializable
import json
from ..biohit_pipettor_plus.control_json import read_json, write_json

deck1 = Deck((0,500), (0,500), "deck1")

slot1 = Slot((100, 300), (50, 100), 500, "slot1")
slot2 = Slot(range_x=(300, 400), range_y=(100,200), range_z=25, slot_id="slot2")
slot3 = Slot((400, 500), (200, 250), 500, "slot3")
slot4 = Slot((100, 300), (50, 100), 500, "slot4")
slot5 = Slot((100, 300), (50, 100), 500, "slot5")
slot6 = Slot((100, 300), (50, 100), 500, "slot6")


deck1.add_slots([slot1, slot2, slot3])

example_well = Well(size_x=2, size_y=1, size_z=5, media="water")
plate1 = Plate(20, 10, 50, 7, 8, (30, 50), well = example_well)
print(plate1.get_containers)

deck1.add_labware(plate1, slot_id="slot1", min_z=2)
#print(deck1.slots)
#print(slot1.labware_stack)

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
    1: {"size_x": 20, "size_y": 20, "size_z": 10, "capacity": 30000,
        "filled_volume": 15000, "content": "PBS"},

    2: {"size_x": 20, "size_y": 20, "size_z": 12, "capacity": 50000,
        "filled_volume": 45000, "content": "DMEM"},

    3: {"size_x": 25, "size_y": 20, "size_z": 15, "capacity": 50000,
        "filled_volume": 100, "content": "Water"},
}

reservoirs = Reservoirs(
    size_x= 200,
    size_y= 200,
    size_z= 200,
    hook_count = 7,
    reservoir_dict = reservoirs_data,
)

reservoir_4 = {5: {"size_x": 25, "size_y": 20, "size_z": 15, "capacity": 50000,
        "filled_volume": 10000, "content": "Water"},}

reservoirs.place_reservoirs(reservoir_4)


print(reservoirs.get_occupied_hooks())
print(reservoirs.get_available_hooks())
print(reservoirs.get_reservoirs())
reservoirs.add_volume(3, 5000)
reservoirs.remove_volume(3, 500)
print(reservoirs.get_waste_containers())
print(reservoirs.get_equivalent_containers("Water"))
print(reservoirs.get_reservoir_by_content("PBS"))

#checking if resrevoirs to_dict and from_dict works
data = reservoirs.to_dict()
print(f"data{data}")
new_reservoir = Reservoirs.from_dict(data)
print(new_reservoir.to_dict())


#TODO define pipette pick up and drop zone
pipette_holder = PipetteHolder(labware_id="pipette_holder_1")


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