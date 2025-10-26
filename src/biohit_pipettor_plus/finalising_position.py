import subprocess
import time
import sys

sys.path.append(r"/src/biohit_pipettor_plus")

from pipettor_plus import PipettorPlus
from deck import Deck
from slot import Slot
from labware import Labware, Plate, ReservoirHolder, Reservoir, PipetteHolder, TipDropzone, Well, IndividualPipetteHolder


#to troubleshoot
"""
HASTIP = True
tip_length = 38
def _get_pipettor_z_coord(deck, labware: Labware, relative_z: float) -> float:

    # Find the slot that contains this labware. essential to get min_z and max_z
    slot_id = deck.get_slot_for_labware(labware.labware_id)

    if slot_id is None:
        raise ValueError(f"Labware {labware.labware_id} is not placed in any slot")

    slot = deck.slots[slot_id]

    if labware.labware_id not in slot.labware_stack:
        raise ValueError(f"Labware {labware.labware_id} not found in slot {slot_id}")

    _, (min_z, max_z) = slot.labware_stack[labware.labware_id]

    absolute_height = max_z + relative_z
    deck_range_z = deck.range_z

    if absolute_height < min_z:
        raise ValueError(f"absolute_height{absolute_height} cannot be less than min_z of labware. "
                         f"Access to another labware denied")

    if HASTIP:
        pipettor_z = deck_range_z - absolute_height - tip_length

        # Validation with tips
        if pipettor_z < 0:
            raise ValueError(
                f"Cannot reach pipettor_z={pipettor_z:.1f}mm with tips attached "
                f"(tip_length={tip_length:.1f}mm). "
                f"deck range : {deck.range_z:.1f} "
                f"Maximum reachable height: {deck_range_z - tip_length:.1f}mm "
            )

    else:
        # No tips - full range available
        pipettor_z = deck_range_z - absolute_height
        print(f"No Tips: deck_range_z {deck_range_z} - absolute_z {absolute_height}")

        # Validation without tips
        if pipettor_z < 0:
            raise ValueError(
                f"Invalid height: absolute_z={absolute_height:.1f}mm exceeds deck range={deck_range_z:.1f}mm"
            )

    return pipettor_z
    """
deck1 = Deck((0, 265), (0, 244), range_z=141, deck_id="trial")

#todo add deck offset and mirror image
slot1 = Slot((0, 118.25), (0,36.75), 141, "slot1")
slot2 = Slot((128, 246.25), (0, 36.75), 141, "slot2")
slot3 = Slot((0, 118.25), (46, 125.75), 141, "slot3")
slot4 = Slot((128, 246.25), (46, 125.75), 141, "slot4")
slot5 = Slot((0, 118.25), (135, 214.75), 141, "slot5")
slot6 = Slot((128, 246.25), (135, 214.75), 141, "slot6")

deck1.add_slots([slot1, slot2, slot3, slot4, slot5])

example_well = Well(
    size_x=18.9,
    size_y=8,
    size_z=10,
    offset = (-8.5, 0.5),
    content={ "water" : 500},
    capacity=1000,
    shape = "u_bottom",
)

plate1 = Plate(118.1, 65, 53, 6, 8,well=example_well, offset=(14.05, 1),  add_height= -3, remove_height = -10)
deck1.add_labware(plate1, slot_id="slot4", min_z=0)

# Updated reservoirs_data to use content as dictionary
reservoirs_data = {
    1: {"size_x": 16.5, "size_y": 79, "size_z": 66, "capacity": 30000, "content": {}, "shape": "u_bottom"},
    2: {"size_x": 16.5, "size_y": 79, "size_z": 66, "capacity": 30000, "content": {"0 conc": 10000}, "shape": "rectangular"},
    3: {"size_x": 16.5, "size_y": 79, "size_z": 66, "capacity": 30000, "content": {"1.8 conc": 100}},
    4: {"size_x": 16.5, "size_y": 79, "size_z": 66, "capacity": 30000, "content": {"5 conc": 100}},
    5: {"size_x": 16.5, "size_y": 79, "size_z": 66, "capacity": 30000, "content": {"15 conc": 100}},
    6: {"size_x": 16.5, "size_y": 79, "size_z": 66, "capacity": 30000, "content": {"0 conc": 100}},
    7: {"size_x": 16.5, "size_y": 79, "size_z": 66, "capacity": 30000, "content": {}},
}

reservoirHolder = ReservoirHolder(
    size_x=118,
    size_y=79,
    size_z=66,
    offset=(-5.75,0),
    hooks_across_x=7,
    hooks_across_y=1,
    add_height=-10,
    remove_height=-51,
    reservoir_dict=reservoirs_data,
)

deck1.add_labware(reservoirHolder, slot_id="slot5", min_z=0, x_spacing=17.25)


ExamplePipetteHolder = IndividualPipetteHolder(0.8, 0.8, 1)
pipette_holder = PipetteHolder(
    size_x=110.2, size_y=75.2, size_z=49,
    offset=(5.6,6.1),
    holders_across_x=12, holders_across_y=8,
    remove_height= 10,
    add_height= -15,
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

print(plate1.to_dict())
print(reservoirHolder.to_dict())
print(pipette_holder.to_dict())
print(deck1.to_dict())




p = PipettorPlus(tip_volume=200, multichannel=False, deck=deck1)
pipette_holder.place_pipette_at(0,0)

p.pick_tips(pipette_holder)
p.add_medium(reservoirHolder, (1,0), 50, plate1, dest_col_row=[(0,1), (5,5)])
p.remove_medium(plate1,[(1,1), (5,6)], 50, reservoirHolder, (0,0))
p.transfer_plate_to_plate(plate1,[(1,1), (5,6)], plate1, [(5,6), (1,2)] , 100)
p.return_single_tip(pipette_holder)




