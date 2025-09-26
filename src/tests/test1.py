from ..biohit_pipettor_plus.deck import Deck
from ..biohit_pipettor_plus.slot import Slot
from ..biohit_pipettor_plus.labware import Plate, Reservoir, Reservoirs
from ..biohit_pipettor_plus.serializable import Serializable
import json
from ..biohit_pipettor_plus.control_json import read_json, write_json

plate1 = Plate(200, 100, 50, 7, 8, (30, 50), labware_id="plate1")
slot1 = Slot((100, 300), (50, 100), "slot1", plate1)
deck1 = Deck((0,500), (0,500), "deck1")
deck1.add_slot(slot1)

slot2 = Slot(range_x=(300, 400), range_y=(100,200), range_z=25, slot_id="slot2")
write_json(slot2)
# Serialisierung

write_json(deck1)
print(deck1.to_dict())

# Deserialisierung
restored_deck = read_json("deck1")

print(type(restored_deck))
print(restored_deck.slots)
print(restored_deck.labware)

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