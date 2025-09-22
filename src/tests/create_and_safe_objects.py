from ..biohit_pipettor_plus.control_json import create_json_file, write_json, read_json, list_ids
from ..biohit_pipettor_plus.labware import Plate, TipDropzone
from ..biohit_pipettor_plus.slot import Slot
from ..biohit_pipettor_plus.deck import Deck

def test_json_storage():
    # Ensure JSON file exists
    create_json_file()

    # Create some labware
    plate1 = Plate(size_x=200, size_y=100, size_z=50, wells_x=8, wells_y=12, first_well_xy=(10, 20), labware_id="plate1")
    dropzone = TipDropzone(size_x=50, size_y=50, size_z=50, drop_x=10, drop_y=10, labware_id="tip_dropzone1")
    slot1 = Slot(range_x=(0, 250), range_y=(0, 250), slot_id="slot1", range_z=500)
    slot2 = Slot(range_x=(250, 350), range_y=(250, 400), slot_id="slot2", range_z=500)

    slot1.place_labware(plate1, min_z=0)
    slot2.place_labware(dropzone, min_z=0)

    deck = Deck(range_x=(0, 500), range_y=(0, 500), deck_id="deck1")
    deck.add_slot(slot1)
    deck.add_slot(slot2)

    write_json(deck)

test_json_storage()