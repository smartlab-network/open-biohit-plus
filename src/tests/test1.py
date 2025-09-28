from ..biohit_pipettor_plus.deck import Deck
from ..biohit_pipettor_plus.slot import Slot
from ..biohit_pipettor_plus.labware import Plate, PipetteHolder, TipDropzone, Reservoirs
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

example_well = Well(size_x=2, size_y=1, size_z=5)
plate1 = Plate(20, 10, 50, 7, 8, (30, 50), well = example_well)
print(plate1.get_containers())

deck1.add_labware(plate1, slot_id="slot1", min_z=2)
print(deck1.slots)
print(slot1.labware_stack)

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
reservoirs = Reservoirs(
    size_x= 20,
    size_y= 20,
    size_z= 20,
    x_corner=10.0,
    y_corner=20.0,
    container_ids=[1, 2, 3, 4, 5, 6, 7, 8],
    capacities={3: 50000, 4: 50000},
    filled_vol={2: 20000, 4: 15000, 5: 25000, 6: 10000},  # Custom initial volumes
    waste_containers={8},
    disabled_containers={7},
    equivalent_groups={
        2: [2, 6], 6: [2, 6],
        1: [1, 7], 7: [1, 7],
    }
)

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



"""
#Create a Reservoirs object with custom fill levels
# Check initial volumes
print(reservoirs.current_volume)

# Add volume
reservoirs.add_volume(2, 5000)
print(reservoirs.current_volume[2])
print(reservoirs.equivalent_groups)
print(reservoirs.waste_containers)

# Serialize and deserialize
data = reservoirs.to_dict()
new_reservoirs = Reservoirs.from_dict(data,size_x=20, size_y=20, size_z=20, x_corner=10.0, y_corner=20.0)
print(new_reservoirs.current_volume)  # Same as above
"""