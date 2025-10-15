from ..biohit_pipettor_plus.deck import Deck
from ..biohit_pipettor_plus.slot import Slot
from ..biohit_pipettor_plus.labware import Plate, PipetteHolder, TipDropzone, ReservoirHolder, IndividualPipetteHolder, \
    Well
from ..biohit_pipettor_plus.serializable import Serializable
import json
from ..biohit_pipettor_plus.control_json import read_json, write_json

deck1 = Deck((0, 500), (0, 500), "deck1")

slot1 = Slot((100, 200), (0, 50), 500, "slot1")
slot2 = Slot((200, 300), (100, 200), 25, "slot2")
slot3 = Slot((300, 400), (200, 250), 500, "slot3")
slot4 = Slot((400, 450), (50, 100), 500, "slot4")
slot5 = Slot((450, 500), (50, 100), 500, "slot5")
slot6 = Slot((100, 300), (50, 100), 500, "slot6")

deck1.add_slots([slot1, slot2, slot3, slot4, slot5])

# plate & well creating and checking
print("=" * 60)
print("CREATING PLATE WITH WELLS")
print("=" * 60)

example_well = Well(
    size_x=1,
    size_y=1,
    size_z=1,
    content={"water": 750, "pbs": 250},
    capacity=1000  # Add capacity to template well
)
print(f"Template well capacity: {example_well.capacity}µL")
print(f"Template well content: {example_well.get_content_summary()}")
print(f"Template well available volume: {example_well.get_available_volume()}µL")

plate1 = Plate(20, 50, 50, 6, 9, (3, 5), well=example_well)
deck1.add_labware(plate1, slot_id="slot1", min_z=2)
print(f"\nPlate created with {plate1.wells_x} x {plate1.wells_y} wells")

# Updated reservoirs_data to use content as dictionary
reservoirs_data = {
    1: {"size_x": 30, "size_y": 20, "size_z": 10, "capacity": 30000,
        "content": {}},  # Empty waste reservoir

    2: {"size_x": 10, "size_y": 20, "size_z": 12, "capacity": 30000,
        "content": {"0 conc": 10000}},

    3: {"size_x": 15, "size_y": 20, "size_z": 15, "capacity": 30000,
        "content": {"1.8 conc": 100}},

    4: {"size_x": 15, "size_y": 20, "size_z": 15, "capacity": 30000,
        "content": {"5 conc": 100}},

    5: {"size_x": 15, "size_y": 20, "size_z": 15, "capacity": 30000,
        "content": {"15 conc": 100}},

    6: {"size_x": 15, "size_y": 20, "size_z": 15, "capacity": 30000,
        "content": {"0 conc": 100}},

    7: {"size_x": 35, "size_y": 20, "size_z": 15, "capacity": 30000,
        "content": {}},  # Empty waste reservoir
}

reservoirHolder = ReservoirHolder(
    size_x=100,
    size_y=50,
    size_z=20,
    offset=(4, 4),
    hooks_across_x=6,
    hooks_across_y=2,
    reservoir_dict=reservoirs_data,
)

deck1.add_labware(reservoirHolder, slot_id="slot3", min_z=2)

ExamplePipetteHolder = IndividualPipetteHolder(1, 1, 1)
pipette_holder = PipetteHolder(size_x=10, size_y=20, size_z=20, holders_across_x=6, holders_across_y=8,
                               individual_holder=ExamplePipetteHolder)
deck1.add_labware(pipette_holder, slot_id="slot5", min_z=2)
pipette_holder.place_pipettes_in_columns([3, 5])

tip_dropzone = TipDropzone(
    size_x=50,
    size_y=50,
    size_z=20,
    offset=(54, 15),
    labware_id="dropzone_1",
    drop_height_relative=15
)
deck1.add_labware(tip_dropzone, slot_id="slot2", min_z=2)

print("\n" + "=" * 60)
print("VERIFICATION TESTS")
print("=" * 60)

# Test 1: Check Plate Well Positions and Content
print("\n1. Checking Plate Well Positions and Content:")
wells = plate1.get_wells()
sample_well_ids = [
    f"{plate1.labware_id}_0:0",  # First well
    f"{plate1.labware_id}_5:8",  # Last well
    f"{plate1.labware_id}_2:4"  # Middle well
]

for well_id in sample_well_ids:
    if well_id in wells and wells[well_id]:
        well = wells[well_id]
        print(f"\n   Well: {well_id}")
        print(f"   Row: {well.row}, Column: {well.column}")
        if well.position:
            print(f"   ✓ Position: {well.position}")
        else:
            print(f"   ❌ Position: None (ERROR!)")
        print(f"   Capacity: {well.capacity}µL")
        print(f"   Content: {well.get_content_summary()}")
        print(f"   Total volume: {well.get_total_volume()}µL")
        print(f"   Available volume: {well.get_available_volume()}µL")
        print(f"   Is full: {well.get_content_info()['is_full']}")
    else:
        print(f"   ❌ {well_id}: NOT FOUND (ERROR!)")

# Test 1b: Test Well Content Methods
print("\n1b. Testing Well Content Methods:")
test_well_id = f"{plate1.labware_id}_0:0"
if test_well_id in wells and wells[test_well_id]:
    test_well = wells[test_well_id]
    print(f"   Testing well: {test_well_id}")

    # Test adding content
    print(f"\n   Adding 100µL of 'buffer' to well...")
    try:
        test_well.add_content("buffer", 100)
        print(f"   ✓ Successfully added content")
        print(f"   New content: {test_well.get_content_summary()}")
        print(f"   New total: {test_well.get_total_volume()}µL")
        print(f"   Available: {test_well.get_available_volume()}µL")
    except ValueError as e:
        print(f"   ❌ Error adding content: {e}")

    # Test removing content
    print(f"\n   Removing 50µL from well...")
    try:
        test_well.remove_content(50)
        print(f"   ✓ Successfully removed content")
        print(f"   New content: {test_well.get_content_summary()}")
        print(f"   New total: {test_well.get_total_volume()}µL")
    except ValueError as e:
        print(f"   ❌ Error removing content: {e}")

    # Test overflow prevention
    print(f"\n   Testing overflow prevention (trying to add 2000µL to {test_well.capacity}µL well)...")
    try:
        test_well.add_content("overflow_test", 2000)
        print(f"   ❌ ERROR: Overflow was not prevented!")
    except ValueError as e:
        print(f"   ✓ Overflow prevented: {e}")

    # Test underflow prevention
    print(f"\n   Testing underflow prevention (trying to remove more than available)...")
    try:
        test_well.remove_content(10000)
        print(f"   ❌ ERROR: Underflow was not prevented!")
    except ValueError as e:
        print(f"   ✓ Underflow prevented: {e}")

    # Test empty well removal
    print(f"\n   Clearing well and testing empty well removal...")
    test_well.clear_content()
    print(f"   Content after clear: {test_well.get_content_summary()}")
    try:
        test_well.remove_content(10)
        print(f"   ❌ ERROR: Removal from empty well was not prevented!")
    except ValueError as e:
        print(f"   ✓ Empty well removal prevented: {e}")

# Test 1c: Test content_by_type
print("\n1c. Testing get_content_by_type:")
test_well_id = f"{plate1.labware_id}_1:1"
if test_well_id in wells and wells[test_well_id]:
    test_well = wells[test_well_id]
    print(f"   Testing well: {test_well_id}")
    print(f"   Water volume: {test_well.get_content_by_type('water')}µL")
    print(f"   PBS volume: {test_well.get_content_by_type('pbs')}µL")
    print(f"   Has water: {test_well.has_content_type('water')}")
    print(f"   Has ethanol: {test_well.has_content_type('ethanol')}")

# Test 2: Check Reservoir Positions and Content
print("\n2. Checking Reservoir Positions and Content:")
reservoirs = reservoirHolder.get_reservoirs()
for res in reservoirs:
    content_summary = res.get_content_summary()
    print(f"\n   Reservoir: {res.labware_id}")
    if res.position:
        print(f"   ✓ Position: {res.position}")
    else:
        print(f"   ❌ Position: None (ERROR!)")
    print(f"   Content: [{content_summary}]")
    print(f"   Capacity: {res.capacity}µL")
    print(f"   Total volume: {res.get_total_volume()}µL")
    print(f"   Available: {res.get_available_volume()}µL")

# Test 2b: Test reservoir content methods
print("\n2b. Testing Reservoir Content Methods:")
if reservoirs:
    test_res = reservoirs[1]  # Pick second reservoir
    print(f"   Testing reservoir: {test_res.labware_id}")
    print(f"   Total volume: {test_res.get_total_volume()}µL")
    print(f"   Available capacity: {test_res.get_available_volume()}µL")
    print(f"   Content info: {test_res.get_content_info()}")

    # Test adding content
    print(f"\n   Adding 500µL of 'buffer' to reservoir...")
    try:
        test_res.add_content("buffer", 500)
        test_res.add_content("buffer", 500)
        print(f"   ✓ Successfully added content")
        print(f"   New content summary: {test_res.get_content_summary()}")
    except ValueError as e:
        print(f"   ❌ Error adding content: {e}")

# Test 3: Check Pipette Holder Positions
print("\n3. Checking Pipette Holder Positions:")
holders = pipette_holder.get_individual_holders()

test_holder_ids = [
    f"{pipette_holder.labware_id}_0:0",
    f"{pipette_holder.labware_id}_3:0",
    f"{pipette_holder.labware_id}_5:7"
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

# Test 4: Check Tip Dropzone Position
print("\n4. Checking Tip Dropzone Position:")
if tip_dropzone.position:
    print(f"   ✓ dropzone_1: position = {tip_dropzone.position}")
else:
    print(f"   ❌ dropzone_1: position = None (ERROR!)")

# Test 5: Simulate Pipettor Access
print("\n5. Simulating Pipettor Access:")
print("   Testing if pipettor can access holders with correct ID format...")

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
        slot_id = deck1.get_slot_for_labware(lw_id)
        if slot_id:
            print(f"     Located in: {slot_id}")
        else:
            print(f"     ❌ Not found in any slot!")
    else:
        print(f"   ❌ {lw_id} NOT in deck!")

# Test 8: Test Serialization/Deserialization with new Well structure
print("\n8. Testing Serialization/Deserialization:")
print("   Serializing plate...")
plate_dict = plate1.to_dict()
print(f"   ✓ Plate serialized")

print("   Checking if capacity is in serialized data...")
sample_well_data = None
for wid, wdata in plate_dict['wells'].items():
    if wdata is not None:
        sample_well_data = wdata
        break

if sample_well_data and 'capacity' in sample_well_data:
    print(f"   ✓ Capacity found in well data: {sample_well_data['capacity']}µL")
else:
    print(f"   ❌ Capacity NOT found in well data!")

print("\n   Deserializing plate...")
try:
    restored_plate = Plate._from_dict(plate_dict)
    print(f"   ✓ Plate deserialized successfully")

    # Check if capacity was restored
    restored_wells = restored_plate.get_wells()
    test_well_id = f"{restored_plate.labware_id}_0:0"
    if test_well_id in restored_wells and restored_wells[test_well_id]:
        restored_well = restored_wells[test_well_id]
        print(f"   Restored well capacity: {restored_well.capacity}µL")
        print(f"   Restored well content: {restored_well.get_content_summary()}")
        if restored_well.capacity == example_well.capacity:
            print(f"   ✓ Capacity correctly restored!")
        else:
            print(f"   ❌ Capacity mismatch!")
except Exception as e:
    print(f"   ❌ Deserialization failed: {e}")

print("\n" + "=" * 60)
print("TESTS COMPLETE")
print("=" * 60)