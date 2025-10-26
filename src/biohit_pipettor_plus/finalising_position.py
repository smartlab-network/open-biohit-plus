import subprocess
import time
import sys

sys.path.append(r"/src/biohit_pipettor_plus")

from pipettor_plus import PipettorPlus
from deck import Deck
from slot import Slot
from labware import Plate, ReservoirHolder, Reservoir, PipetteHolder, TipDropzone, Well, IndividualPipetteHolder

# Initialize Deck300
deck1 = Deck((0, 265), (0, 244), range_z=145, deck_id="trial")

#todo add deck offset and mirror image
slot1 = Slot((0, 118.25), (0,36.75), 145, "slot1")
slot2 = Slot((128, 246.25), (0, 36.75), 145, "slot2")
slot3 = Slot((0, 118.25), (46, 125.75), 145, "slot3")
slot4 = Slot((128, 246.25), (46, 125.75), 145, "slot4")
slot5 = Slot((0, 118.25), (135, 214.75), 145, "slot5")
slot6 = Slot((128, 246.25), (135, 214.75), 145, "slot6")

deck1.add_slots([slot1, slot2, slot3, slot4, slot5])

example_well = Well(
    size_x=18.9,
    size_y=8,
    size_z=10,
    offset = (-8.5, 0.5),
    content={ "water" : 500},
    capacity=1000
)

plate1 = Plate(118.1, 65, 50, 6, 8,well=example_well, offset=(14.05, 1),  add_height= 46, remove_height = 36)
deck1.add_labware(plate1, slot_id="slot4", min_z=0)

# Updated reservoirs_data to use content as dictionary
reservoirs_data = {
    1: {"size_x": 16.5, "size_y": 79, "size_z": 70, "capacity": 30000, "content": {}},
    2: {"size_x": 16.5, "size_y": 79, "size_z": 70, "capacity": 30000, "content": {"0 conc": 10000}},
    3: {"size_x": 16.5, "size_y": 79, "size_z": 70, "capacity": 30000, "content": {"1.8 conc": 100}},
    4: {"size_x": 16.5, "size_y": 79, "size_z": 70, "capacity": 30000, "content": {"5 conc": 100}},
    5: {"size_x": 16.5, "size_y": 79, "size_z": 70, "capacity": 30000, "content": {"15 conc": 100}},
    6: {"size_x": 16.5, "size_y": 79, "size_z": 70, "capacity": 30000, "content": {"0 conc": 100}},
    7: {"size_x": 16.5, "size_y": 79, "size_z": 70, "capacity": 30000, "content": {}},
}

reservoirHolder = ReservoirHolder(
    size_x=118,
    size_y=79,
    size_z=70,
    offset=(-5.75,0),
    hooks_across_x=7,
    hooks_across_y=1,
    add_height=51,
    remove_height=19,
    reservoir_dict=reservoirs_data,
)

deck1.add_labware(reservoirHolder, slot_id="slot5", min_z=0, x_spacing=17.25)


ExamplePipetteHolder = IndividualPipetteHolder(0.8, 0.8, 1)
pipette_holder = PipetteHolder(
    size_x=110.2, size_y=75.2, size_z=46,
    offset=(5.6,6.1),
    holders_across_x=12, holders_across_y=8,
    remove_height=55,
    add_height= 38,
    individual_holder=ExamplePipetteHolder
)
deck1.add_labware(pipette_holder, slot_id="slot3", min_z=0)
print(f"Slot3 labware_stack: {slot3.labware_stack}")

tip_dropzone = TipDropzone(
    size_x=50,
    size_y=30,
    size_z=20,
    offset=(30, 10),
    labware_id="dropzone_1",
    drop_height_relative=15
)
deck1.add_labware(tip_dropzone, slot_id="slot1", min_z=0)
"""
print(plate1.to_dict())
print(reservoirHolder.to_dict())
print(pipette_holder.to_dict())
print(deck1.to_dict())
"""
print(plate1.to_dict())
print(reservoirHolder.to_dict())
p = PipettorPlus(tip_volume=200, multichannel=False, deck=deck1)
pipette_holder.place_pipette_at(0,1)

p.pick_tips(pipette_holder)
#p.add_medium(reservoirHolder, (1,0), 250, plate1, dest_col_row=[(0,1), (5,5)])
#p.remove_medium(plate1,[(1,1), (5,6)], 50, reservoirHolder, (0,0))
#p.transfer_plate_to_plate(plate1,[(1,1), (5,6)], plate1, [(5,6), (1,2)] , 100)
p.return_single_tip(pipette_holder)