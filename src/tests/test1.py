from src.biohit_pipettor_plus.deck import Deck
from src.biohit_pipettor_plus.slot import Slot
from src.biohit_pipettor_plus.labware import Labware, Plate, IndividualPipetteHolder, PipetteHolder, Well, TipDropzone, ReservoirHolder
from src.biohit_pipettor_plus.control_json import write_json


deck = Deck(
    range_x=(0, 800),
    range_y=(0, 600),
    deck_id="MainDeck_01",
    range_z=500
)
slot_width = 120.0
slot_depth = 100.0
for i in range(6):
    slot = Slot(
        range_x=(i % 2 * slot_width, (i % 2 + 1) * slot_width),
        range_y=(i % 2 * slot_depth, (i % 2 + 1) * slot_depth),
        range_z=100.0,
        slot_id=f"Slot_{i+1}"
    )
    deck.slots[slot.slot_id] = slot

# --- Well-Template für Plates ---
well_template = Well(
    size_x=18,
    size_y=9,
    size_z=12.0,
    capacity=200.0,           # µL
    add_height=1.0,
    remove_height=1.0,
    suck_offset_xy=(0.0, 0.0),
    row=0,
    column=0,
    shape="circular"
)

# --- Drei Plates erstellen ---
plate2 = Plate(
    size_x=108,
    size_y=72,
    size_z=14.0,
    wells_x=6,
    wells_y=8,
    well=well_template,
    labware_id="Plate_6x8",
    position=(0.0, 0.0)
)


plate1 = Plate(
    size_x=72,
    size_z=14.0,
    size_y=45,
    wells_x=4,
    wells_y=5,
    well=well_template,
    labware_id="Plate_4x5",
    position=(0.0, 0.0))

plate3 = Plate(
    size_x=126,
    size_y=81.0,
    size_z=14.0,
    wells_x=7,
    wells_y=9,
    well=well_template,
    labware_id="Plate_7x9",
    position=(0.0, 0.0)
)

reservoir_holder = ReservoirHolder(
    size_x=126,
    size_y=81.0,
    size_z=14.0,
    hooks_across_x=6,
    hooks_across_y=4,
    add_height=20,
    remove_height=20,
    labware_id = "reservoir_holder_1")

# --- IndividualPipetteHolder-Template ---
individual_holder = IndividualPipetteHolder(
    size_x=10.0,
    size_y=10.0,
    size_z=30.0,
    labware_id="IndividualHolder_Template"
)

# --- PipetteHolder erstellen ---
pipette_holder = PipetteHolder(
    size_x=120.0,
    size_y=80.0,
    size_z=40.0,
    holders_across_x=3,
    holders_across_y=8,
    individual_holder=individual_holder,
    add_height=5.0,
    remove_height=3.0,
    offset=(0.0, 0.0),
    labware_id="PipetteHolder_1",
    position=(0.0, 0.0)
)

pipette_holder_2 = PipetteHolder(
    size_x=120.0,
    size_y=80.0,
    size_z=40.0,
    holders_across_x=6,
    holders_across_y=7,
    individual_holder=individual_holder,
    add_height=5.0,
    remove_height=3.0,
    offset=(0.0, 0.0),
    labware_id="PipetteHolder_2",
    position=(0.0, 0.0)
)

tip_dropzone = TipDropzone(size_x= 100, size_y = 120, size_z=50, labware_id = "tip_dropzone_1")

# --- Labware zu Slots hinzufügen ---
# --- Labware in Slots platzieren (mit Höhenprüfung) ---
deck.slots["Slot_1"]._place_labware(plate1, min_z=0.0)
deck.slots["Slot_2"]._place_labware(plate2, min_z=0.0)
deck.slots["Slot_3"]._place_labware(reservoir_holder, min_z=0.0)
deck.slots["Slot_4"]._place_labware(pipette_holder, min_z=0.0)
deck.slots["Slot_5"]._place_labware(pipette_holder_2, min_z=0.0)
deck.slots["Slot_6"]._place_labware(tip_dropzone, min_z=0)


# --- Übersicht ausgeben ---
print(f"Deck: {deck.deck_id}")
for slot_id, slot in deck.slots.items():
    print(f"\n{slot_id} | Range X: {slot.range_x}, Y: {slot.range_y}")
    for lw_id, (lw, z_range) in slot.labware_stack.items():
        print(f"  - {lw_id} ({lw.__class__.__name__}) Z-Range: {z_range}")

write_json(deck)