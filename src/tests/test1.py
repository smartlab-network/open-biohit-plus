from biohit_pipettor import Deck
from biohit_pipettor_plus.slot import Slot
from biohit_pipettor_plus.labware import Plate, PipetteHolder, TipDropzone, ReservoirHolder, IndividualPipetteHolder, Well

deck1 = Deck((0, 500), (0, 500), "deck1")

slot1 = Slot((100, 200), (0, 50), 500, "slot1")
slot2 = Slot((200, 300), (100, 200), 25, "slot2")
slot3 = Slot((300, 400), (200, 280), 500, "slot3")
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
    capacity=1000
)
print(f"Template well capacity: {example_well.capacity}µL")
print(f"Template well content: {example_well.get_content_summary()}")
print(f"Template well available volume: {example_well.get_available_volume()}µL")

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

print("\n" + "=" * 60)
print("VERIFICATION TESTS")
print("=" * 60)

# Test 1: Check Plate Well Positions and Content
print("\n1. Checking Plate Well Positions and Content:")

# ✅ Use tuple positions instead of string IDs
sample_positions = [
    (0, 0),  # First well
    (5, 8),  # Last well
    (2, 4)   # Middle well
]

for col, row in sample_positions:
    well = plate1.get_well_at(col, row)  # ✅ Use helper method
    if well:
        print(f"\n   Well at position ({col}, {row}):")
        print(f"   Labware ID: {well.labware_id}")
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
        print(f"   ❌ Well at ({col}, {row}): NOT FOUND (ERROR!)")

# Test 1b: Test Well Content Methods
print("\n1b. Testing Well Content Methods:")
test_well = plate1.get_well_at(0, 0)  # ✅ Use helper method
if test_well:
    print(f"   Testing well at position (0, 0): {test_well.labware_id}")

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
else:
    print(f"   ❌ Could not get test well at (0, 0)")

# Test 1c: Test content_by_type
print("\n1c. Testing get_content_by_type:")
test_well = plate1.get_well_at(1, 1)  # ✅ Use helper method
if test_well:
    print(f"   Testing well at position (1, 1): {test_well.labware_id}")
    print(f"   Water volume: {test_well.get_content_by_type('water')}µL")
    print(f"   PBS volume: {test_well.get_content_by_type('pbs')}µL")
    print(f"   Has water: {test_well.has_content_type('water')}")
    print(f"   Has ethanol: {test_well.has_content_type('ethanol')}")
else:
    print(f"   ❌ Could not get test well at (1, 1)")

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

# ✅ Use tuple positions instead of string IDs
test_positions = [
    (0, 0),
    (3, 0),
    (5, 7)
]

for col, row in test_positions:
    holder = pipette_holder.get_holder_at(col, row)  # ✅ Use helper method
    if holder:
        if holder.position:
            print(f"   ✓ Holder at ({col}, {row}): position = {holder.position}, occupied = {holder.is_occupied}")
        else:
            print(f"   ❌ Holder at ({col}, {row}): position = None (ERROR!)")
    else:
        print(f"   ❌ Holder at ({col}, {row}): NOT FOUND (ERROR!)")

# Test 4: Check Tip Dropzone Position
print("\n4. Checking Tip Dropzone Position:")
if tip_dropzone.position:
    print(f"   ✓ dropzone_1: position = {tip_dropzone.position}")
else:
    print(f"   ❌ dropzone_1: position = None (ERROR!)")

# Test 5: Simulate Pipettor Access
print("\n5. Simulating Pipettor Access:")
print("   Testing if pipettor can access holders using helper method...")

col = 3
row = 0
holder = pipette_holder.get_holder_at(col, row)  # ✅ Use helper method
if holder:
    print(f"   ✓ Found holder at column={col}, row={row}")
    print(f"     Labware ID: {holder.labware_id}")
    if holder.position:
        print(f"     Position: {holder.position}")
        print(f"     Is occupied: {holder.is_occupied}")
    else:
        print(f"     ❌ ERROR: Position not set!")
else:
    print(f"   ❌ ERROR: Holder at ({col}, {row}) NOT found!")

# Test 6: Check Occupied Columns
print("\n6. Checking Occupied Columns:")
occupied = pipette_holder.get_occupied_holder_multi()
print(f"   Occupied multi-channel positions: {occupied}")
print(f"   Expected: [(3, 0), (5, 0)]")
# ✅ Updated expectation - returns list of (column, start_row) tuples
if occupied == [(3, 0), (5, 0)]:
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

    # Check if capacity was restored - ✅ Use helper method
    restored_well = restored_plate.get_well_at(0, 0)
    if restored_well:
        print(f"   Restored well capacity: {restored_well.capacity}µL")
        print(f"   Restored well content: {restored_well.get_content_summary()}")
        if restored_well.capacity == example_well.capacity:
            print(f"   ✓ Capacity correctly restored!")
        else:
            print(f"   ❌ Capacity mismatch!")
    else:
        print(f"   ❌ Could not retrieve restored well at (0, 0)")
except Exception as e:
    print(f"   ❌ Deserialization failed: {e}")

# Test 8: Comprehensive Serialization/Deserialization Test
print("\n8. Testing Serialization/Deserialization:")

print("\n   === PLATE SERIALIZATION ===")
print("   Serializing plate...")
plate_dict = plate1.to_dict()
print(f"   ✓ Plate serialized")

# Verify serialized structure
print(f"   Checking serialized structure...")
print(f"   - Wells count in dict: {len(plate_dict['wells'])}")
print(f"   - Expected wells: {plate1.wells_x * plate1.wells_y}")
if len(plate_dict['wells']) == plate1.wells_x * plate1.wells_y:
    print(f"   ✓ All wells serialized")
else:
    print(f"   ❌ Wells count mismatch!")

# Check a sample well's data
sample_well_data = plate_dict['wells']['0:0']
if sample_well_data:
    print(f"   Sample well (0:0) data:")
    print(f"   - Has capacity: {'capacity' in sample_well_data}")
    print(f"   - Has content: {'content' in sample_well_data}")
    print(f"   - Has position: {'position' in sample_well_data}")
    print(f"   - Capacity value: {sample_well_data.get('capacity')}µL")
    print(f"   - Content: {sample_well_data.get('content')}")
else:
    print(f"   ❌ Sample well data not found!")

# Deserialize plate
print("\n   Deserializing plate...")
try:
    restored_plate = Plate._from_dict(plate_dict)
    print(f"   ✓ Plate deserialized successfully")

    # Verify ALL wells were restored
    print(f"\n   Verifying restored plate:")
    print(f"   - Restored wells count: {len(restored_plate.get_wells())}")
    print(f"   - Original wells count: {len(plate1.get_wells())}")

    if len(restored_plate.get_wells()) == len(plate1.get_wells()):
        print(f"   ✓ All wells restored")
    else:
        print(f"   ❌ Wells count mismatch!")

    # Check several wells for correctness
    test_positions = [(0, 0), (2, 4), (5, 8)]
    all_correct = True

    for col, row in test_positions:
        original_well = plate1.get_well_at(col, row)
        restored_well = restored_plate.get_well_at(col, row)

        if not restored_well:
            print(f"   ❌ Well at ({col}, {row}) not restored!")
            all_correct = False
            continue

        # Check capacity
        if restored_well.capacity != original_well.capacity:
            print(f"   ❌ Well ({col}, {row}): Capacity mismatch!")
            all_correct = False

        # Check content
        if restored_well.content != original_well.content:
            print(f"   ❌ Well ({col}, {row}): Content mismatch!")
            print(f"      Original: {original_well.content}")
            print(f"      Restored: {restored_well.content}")
            all_correct = False

        # Check position
        if restored_well.position != original_well.position:
            print(f"   ❌ Well ({col}, {row}): Position mismatch!")
            all_correct = False

        # Check row/column attributes
        if restored_well.row != row or restored_well.column != col:
            print(f"   ❌ Well ({col}, {row}): Row/Column mismatch!")
            all_correct = False

    if all_correct:
        print(f"   ✓ All checked wells restored correctly!")

except Exception as e:
    print(f"   ❌ Plate deserialization failed: {e}")
    import traceback

    traceback.print_exc()

print("\n   === PIPETTE HOLDER SERIALIZATION ===")
print("   Serializing pipette holder...")
holder_dict = pipette_holder.to_dict()
print(f"   ✓ PipetteHolder serialized")

print(f"   Checking serialized structure...")
print(f"   - Holders count in dict: {len(holder_dict['individual_holders'])}")
print(f"   - Expected holders: {pipette_holder.holders_across_x * pipette_holder.holders_across_y}")

if len(holder_dict['individual_holders']) == pipette_holder.holders_across_x * pipette_holder.holders_across_y:
    print(f"   ✓ All holders serialized")
else:
    print(f"   ❌ Holders count mismatch!")

# Check occupied status is in serialized data
sample_holder_data = holder_dict['individual_holders']['3:0']
if sample_holder_data:
    print(f"   Sample holder (3:0) data:")
    print(f"   - Is occupied in dict: {sample_holder_data.get('is_occupied')}")
    print(f"   - Expected (occupied): True")
else:
    print(f"   ❌ Sample holder data not found!")

# Deserialize pipette holder
print("\n   Deserializing pipette holder...")
try:
    restored_holder = PipetteHolder._from_dict(holder_dict)
    print(f"   ✓ PipetteHolder deserialized successfully")

    # Verify ALL holders were restored
    print(f"\n   Verifying restored pipette holder:")
    print(f"   - Restored holders count: {len(restored_holder.get_individual_holders())}")
    print(f"   - Original holders count: {len(pipette_holder.get_individual_holders())}")

    if len(restored_holder.get_individual_holders()) == len(pipette_holder.get_individual_holders()):
        print(f"   ✓ All holders restored")
    else:
        print(f"   ❌ Holders count mismatch!")

    # Check occupied status is preserved
    test_positions = [(3, 0), (5, 0), (0, 0), (4, 0)]  # Mix of occupied and empty
    all_correct = True

    for col, row in test_positions:
        original_holder = pipette_holder.get_holder_at(col, row)
        restored_holder_item = restored_holder.get_holder_at(col, row)

        if not restored_holder_item:
            print(f"   ❌ Holder at ({col}, {row}) not restored!")
            all_correct = False
            continue

        # Check occupied status
        if restored_holder_item.is_occupied != original_holder.is_occupied:
            print(f"   ❌ Holder ({col}, {row}): Occupied status mismatch!")
            print(f"      Original: {original_holder.is_occupied}")
            print(f"      Restored: {restored_holder_item.is_occupied}")
            all_correct = False

        # Check position
        if restored_holder_item.position != original_holder.position:
            print(f" ❌ Holder ({col}, {row}): Position mismatch!")
            all_correct = False

    if all_correct:
        print(f" ✓ All checked holders restored correctly!")

    # Verify occupied columns match
    original_occupied = pipette_holder.get_occupied_holder_multi()
    restored_occupied = restored_holder.get_occupied_holder_multi()

    print(f"\n   Checking occupied columns:")
    print(f"   - Original: {original_occupied}")
    print(f"   - Restored: {restored_occupied}")

    if original_occupied == restored_occupied:
        print(f"   ✓ Occupied columns match!")
    else:
        print(f"   ❌ Occupied columns don't match!")

except Exception as e:
    print(f"   ❌ PipetteHolder deserialization failed: {e}")
    import traceback

    traceback.print_exc()

print("\n   === RESERVOIR HOLDER SERIALIZATION ===")
print("   Serializing reservoir holder...")
reservoir_dict = reservoirHolder.to_dict()
print(f"   ✓ ReservoirHolder serialized")

print(f"   Checking serialized structure...")
print(f"   - Reservoirs count in dict: {len(reservoir_dict['reservoirs'])}")
print(f"   - Expected reservoirs: {len(reservoirHolder.get_reservoirs())}")

if len(reservoir_dict['reservoirs']) == len(reservoirHolder.get_reservoirs()):
    print(f"   ✓ All reservoirs serialized")
else:
    print(f"   ❌ Reservoirs count mismatch!")

# Deserialize reservoir holder
print("\n   Deserializing reservoir holder...")
try:
    restored_res_holder = ReservoirHolder._from_dict(reservoir_dict)
    print(f"   ✓ ReservoirHolder deserialized successfully")

    # Verify reservoirs were restored
    print(f"\n   Verifying restored reservoir holder:")
    print(f"   - Restored reservoirs count: {len(restored_res_holder.get_reservoirs())}")
    print(f"   - Original reservoirs count: {len(reservoirHolder.get_reservoirs())}")

    if len(restored_res_holder.get_reservoirs()) == len(reservoirHolder.get_reservoirs()):
        print(f"   ✓ All reservoirs restored")
    else:
        print(f"   ❌ Reservoirs count mismatch!")

    # Check reservoir content is preserved
    original_reservoirs = {res.labware_id: res for res in reservoirHolder.get_reservoirs()}
    restored_reservoirs = {res.labware_id: res for res in restored_res_holder.get_reservoirs()}

    all_correct = True
    for labware_id, original_res in original_reservoirs.items():
        if labware_id not in restored_reservoirs:
            print(f"   ❌ Reservoir {labware_id} not restored!")
            all_correct = False
            continue

        restored_res = restored_reservoirs[labware_id]

        # Check content
        if restored_res.content != original_res.content:
            print(f"   ❌ Reservoir {labware_id}: Content mismatch!")
            print(f"      Original: {original_res.content}")
            print(f"      Restored: {restored_res.content}")
            all_correct = False

        # Check capacity
        if restored_res.capacity != original_res.capacity:
            print(f"   ❌ Reservoir {labware_id}: Capacity mismatch!")
            all_correct = False

        # Check hook_ids
        if restored_res.hook_ids != original_res.hook_ids:
            print(f"   ❌ Reservoir {labware_id}: Hook IDs mismatch!")
            all_correct = False

    if all_correct:
        print(f"   ✓ All reservoirs restored correctly!")

except Exception as e:
    print(f"   ❌ ReservoirHolder deserialization failed: {e}")
    import traceback

    traceback.print_exc()

print("\n   === TIP DROPZONE SERIALIZATION ===")
print("   Serializing tip dropzone...")
dropzone_dict = tip_dropzone.to_dict()
print(f"   ✓ TipDropzone serialized")

print("\n   Deserializing tip dropzone...")
try:
    restored_dropzone = TipDropzone._from_dict(dropzone_dict)
    print(f"   ✓ TipDropzone deserialized successfully")

    # Verify attributes
    if (restored_dropzone.drop_height_relative == tip_dropzone.drop_height_relative and
            restored_dropzone.position == tip_dropzone.position and
            restored_dropzone.labware_id == tip_dropzone.labware_id):
        print(f"   ✓ TipDropzone attributes restored correctly!")
    else:
        print(f"   ❌ TipDropzone attributes mismatch!")

except Exception as e:
    print(f"   ❌ TipDropzone deserialization failed: {e}")
    import traceback

    traceback.print_exc()

print("\n" + "=" * 60)
print("SERIALIZATION TESTS COMPLETE")
print("=" * 60)



