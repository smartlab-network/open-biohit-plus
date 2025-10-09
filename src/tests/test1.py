from ..biohit_pipettor_plus.deck import Deck
from ..biohit_pipettor_plus.slot import Slot
from ..biohit_pipettor_plus.labware import Plate, PipetteHolder, TipDropzone, ReservoirHolder, IndividualPipetteHolder, Well
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
    1: {"size_x": 30, "size_y": 20, "size_z": 10, "capacity": 30000,
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
pipette_holder = PipetteHolder(size_x = 10, size_y = 20, size_z=20, holders_across_x=6, holders_across_y=8, individual_holder= ExamplePipetteHolder)
deck1.add_labware(pipette_holder, slot_id="slot5", min_z=2)

# col and row are zero indexed
print(pipette_holder.to_dict())
pipette_holder.place_pipettes_in_columns([3,5])
print(pipette_holder.get_occupied_columns())

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

print("\n" + "="*60)
print("VERIFICATION TESTS")
print("="*60)

# Test 1: Check Plate Well Positions
print("\n1. Checking Plate Well Positions:")
wells = plate1.get_wells()
sample_well_ids = [
    f"{plate1.labware_id}_0:0",  # First well
    f"{plate1.labware_id}_5:8",  # Last well
    f"{plate1.labware_id}_2:4"   # Middle well
]

for well_id in sample_well_ids:
    if well_id in wells and wells[well_id]:
        well = wells[well_id]
        if well.position:
            print(f"   ✓ {well_id}: position = {well.position}")
        else:
            print(f"   ❌ {well_id}: position = None (ERROR!)")
    else:
        print(f"   ❌ {well_id}: NOT FOUND (ERROR!)")

# Test 2: Check Reservoir Positions
print("\n2. Checking Reservoir Positions:")
reservoirs = reservoirHolder.get_reservoirs()
for res in reservoirs:
    if res.position:
        print(f"   ✓ {res.labware_id} ({res.content}): position = {res.position}")
    else:
        print(f"   ❌ {res.labware_id}: position = None (ERROR!)")

# Test 3: Check Pipette Holder Positions
print("\n3. Checking Pipette Holder Positions:")
holders = pipette_holder.get_individual_holders()

# Test specific holder IDs that should exist
test_holder_ids = [
    f"{pipette_holder.labware_id}_0:0",
    f"{pipette_holder.labware_id}_3:0",  # Column 3, row 0
    f"{pipette_holder.labware_id}_5:7"   # Column 5, row 7
]

for holder_id in test_holder_ids:
    if holder_id in holders:
        holder = holders[holder_id]
        if holder and holder.position:
            print(f"   ✓ {holder_id}: position = {holder.position}")
        else:
            print(f"   ❌ {holder_id}: position = None (ERROR!)")
    else:
        print(f"   ❌ {holder_id}: NOT FOUND (ERROR!)")
        print(f"      Available samples: {list(holders.keys())[:3]}...")

# Test 4: Check Tip Dropzone Position
print("\n4. Checking Tip Dropzone Position:")
if tip_dropzone.position:
    print(f"   ✓ dropzone_1: position = {tip_dropzone.position}")
else:
    print(f"   ❌ dropzone_1: position = None (ERROR!)")

# Test 5: Simulate Pipettor Access (Mock Test)
print("\n5. Simulating Pipettor Access:")
print("   Testing if pipettor can access holders with correct ID format...")

# This simulates what pick_multi_tips will do
col = 3
row = 0
holder_id = f'{pipette_holder.labware_id}_{col}:{row}'
print(f"   Looking for holder: '{holder_id}'")

holder = pipette_holder.get_individual_holders().get(holder_id)
if holder:
    print(f"   ✓ Found holder at column={col}, row={row}")
    if holder.position:
        print(f"     Position: {holder.position}")
        print(f"     Is occupied: {holder.is_occupied}")
    else:
        print(f"     ❌ ERROR: Position not set!")
else:
    print(f"   ❌ ERROR: Holder NOT found!")
    # Show what IDs actually exist
    all_ids = list(pipette_holder.get_individual_holders().keys())
    print(f"   First 5 actual IDs: {all_ids[:5]}")

# Test 6: Check Occupied Columns
print("\n6. Checking Occupied Columns:")
occupied = pipette_holder.get_occupied_columns()
print(f"   Occupied columns: {occupied}")
print(f"   Expected: [3, 5]")
if occupied == [3, 5]:
    print("   ✓ Matches expected!")
else:
    print("   ❌ Does not match expected!")

# Test 7: Verify all labware are in deck
print("\n7. Verifying Labware in Deck:")
expected_labware = [
    plate1.labware_id,
    reservoirHolder.labware_id,
    pipette_holder.labware_id,
    tip_dropzone.labware_id
]

for lw_id in expected_labware:
    if lw_id in deck1.labware:
        print(f"   ✓ {lw_id} found in deck")
        # Also check if it's in a slot
        slot_id = deck1.get_slot_for_labware(lw_id)
        if slot_id:
            print(f"     Located in: {slot_id}")
        else:
            print(f"     ❌ Not found in any slot!")
    else:
        print(f"   ❌ {lw_id} NOT in deck!")

print("\n" + "="*60)
print("TESTS COMPLETE")
print("="*60)

