import subprocess
import time
import sys

sys.path.append(r"/src/biohit_pipettor_plus")

from pipettor_plus import PipettorPlus
from deck import Deck
from slot import Slot
from labware import Plate, ReservoirHolder, Reservoir, PipetteHolder, TipDropzone, Well, IndividualPipetteHolder

# Initialize Deck300
deck1 = Deck((0, 265), (0, 244), range_z=188, deck_id="trial")

#todo add deck offset and mirror image
slot1 = Slot((0, 120), (0,36), 188, "slot1")
slot2 = Slot((130, 240), (0, 36), 188, "slot2")
slot3 = Slot((0, 120), (46, 125), 188, "slot3")
slot4 = Slot((130, 240), (46, 125), 188, "slot4")
slot5 = Slot((0, 120), (135, 214), 188, "slot5")
slot6 = Slot((130, 240), (135, 214), 188, "slot6")

deck1.add_slots([slot1, slot2, slot3, slot4, slot5])

example_well = Well(
    size_x=1,
    size_y=1,
    size_z=1,
    content={"water": 750, "pbs": 250},
    capacity=1000
)


plate1 = Plate(20, 50, 50, 6, 9, well=example_well, offset=(3, 5))
deck1.add_labware(plate1, slot_id="slot1", min_z=2)
print(f"\nPlate created with {plate1.wells_x} x {plate1.wells_y} wells")

# Updated reservoirs_data to use content as dictionary
reservoirs_data = {
    1: {"size_x": 10, "size_y": 40, "size_z": 10, "capacity": 30000, "content": {}},
    2: {"size_x": 10, "size_y": 40, "size_z": 12, "capacity": 30000, "content": {"0 conc": 10000}},
    3: {"size_x": 15, "size_y": 40, "size_z": 15, "capacity": 30000, "content": {"1.8 conc": 100}},
    4: {"size_x": 15, "size_y": 40, "size_z": 15, "capacity": 30000, "content": {"5 conc": 100}},
    5: {"size_x": 15, "size_y": 40, "size_z": 15, "capacity": 30000, "content": {"15 conc": 100}},
    6: {"size_x": 15, "size_y": 40, "size_z": 15, "capacity": 30000, "content": {"0 conc": 100}},
    7: {"size_x": 15, "size_y": 40, "size_z": 15, "capacity": 30000, "content": {}},
}

reservoirHolder = ReservoirHolder(
    size_x=100,
    size_y=80,
    size_z=20,
    offset=(4, 4),
    hooks_across_x=6,
    hooks_across_y=2,
    add_height=2,
    remove_height=2,
    reservoir_dict=reservoirs_data,
)

deck1.add_labware(reservoirHolder, slot_id="slot3", min_z=2)

ExamplePipetteHolder = IndividualPipetteHolder(1, 1, 1)
pipette_holder = PipetteHolder(
    size_x=10, size_y=20, size_z=20,
    holders_across_x=6, holders_across_y=8,
    individual_holder=ExamplePipetteHolder
)
deck1.add_labware(pipette_holder, slot_id="slot5", min_z=2)
pipette_holder.place_consecutive_pipettes_multi([3, 5])

tip_dropzone = TipDropzone(
    size_x=50,
    size_y=50,
    size_z=20,
    offset=(54, 15),
    labware_id="dropzone_1",
    drop_height_relative=15
)
deck1.add_labware(tip_dropzone, slot_id="slot2", min_z=2)
print(plate1.to_dict())
print(reservoirHolder.to_dict())
print(pipette_holder.to_dict())
print(deck1.to_dict())

p = PipettorPlus(tip_volume=1000, multichannel=False, deck=deck1, tip_length = 12)
p.pick_tips(pipette_holder)