import sys
sys.path.append(r"/src/biohit_pipettor_plus")

from src.biohit_pipettor_plus.deck_structure import *
from src.biohit_pipettor_plus.deck_structure.control_json import read_json, write_json, save_deck_for_gui
from src.biohit_pipettor_plus.pipettor_plus.pipettor_plus import PipettorPlus

# Create deck
deck1 = Deck((0, 265), (0, 244), range_z=141, deck_id="deck")

# Add slots
slot1 = Slot((0, 118.25), (0, 36.75), 141, "slot1")
slot2 = Slot((128, 246.25), (0, 36.75), 141, "slot2")
slot3 = Slot((0, 118.25), (46, 125.75), 141, "slot3")
slot4 = Slot((128, 246.25), (46, 125.75), 141, "slot4")
slot5 = Slot((0, 118.25), (135, 214.75), 141, "slot5")
slot6 = Slot((128, 246.25), (135, 214.75), 141, "slot6")
deck1.add_slots([slot1, slot2, slot3, slot4, slot5, slot6])

example_stack = Stack( size_x=18.9,
    size_y=7.5,
    size_z=10,
    offset=(-8.5, 0.5))

ex=example_stack.to_dict()
#print(ex)
#print(ex._from_dict().to_dict())
#deck1.add_labware(example_stack, slot_id ="slot6", min_z=0)
# Create plate with wells
example_well = Well(
    size_x=18.9,
    size_y=7.5,
    size_z=10,
    offset=(-8.5, 0.5),
    content={"water": 500},
    capacity=1000,
)

plate1 = Plate(
    113.4, 65, 55, 6, 8,
    well=example_well,
    offset=(12.2, 1),
    add_height=3,
    remove_height=2
)
deck1.add_labware(plate1, slot_id="slot4", min_z=0, x_spacing=18, y_spacing=9)

# Create reservoir holder
thirty_ml_res = Reservoir(
    size_x=16.5, size_y=79, size_z=45,
    capacity=30000,
    content={"water": 20000}
)

hundred_ml_res = Reservoir(
    size_x=16.5, size_y=75, size_z=85, capacity=100000,content={"water": 100000}, shape="rectangular"
)

reservoirHolder = ReservoirHolder(
    size_x=115.5,
    size_y=79,
    size_z=90,
    offset=(4, 0),
    hooks_across_x=7,
    hooks_across_y=1,
    add_height=70,
    remove_height=20,
    reservoir_template=hundred_ml_res,
)

deck1.add_labware(reservoirHolder, slot_id="slot5", min_z=0, x_spacing=17.25)

# Create pipette holder
ExamplePipetteHolder = IndividualPipetteHolder(0.8, 0.8, 1)
pipette_holder = PipetteHolder(
    size_x=102, size_y=65, size_z=49,
    offset=(12.85, 6.1),
    holders_across_x=12, holders_across_y=8,
    remove_height=9,
    add_height=-14,
    individual_holder=ExamplePipetteHolder
)
deck1.add_labware(pipette_holder, slot_id="slot3", min_z=0, x_spacing=9, y_spacing=9)

# Create tip dropzone
tip_dropzone = TipDropzone(
    size_x=40,
    size_y=30,
    size_z=20,
    offset=(10, 5),
    labware_id="dropzone_1",
    drop_height_relative=60
)
deck1.add_labware(tip_dropzone, slot_id="slot1", min_z=0)

# Save and verify
print("📦 Saving deck...")
write_json(deck1)

# Load back to verify
print("📂 Loading deck...")
loaded_deck = read_json("deck")


print("\nSaving deck to GUI-compatible file...")
output_filename = "deck1_for_gui.json"
save_deck_for_gui(deck1, "deck1")

save_deck_for_gui(
    deck1,
    "deck1",
    available_wells=[example_well],
    available_reservoirs=[thirty_ml_res, hundred_ml_res],
    available_individual_holders=[ExamplePipetteHolder],
)
