from src.biohit_pipettor_plus.labware import Well, Plate, PipetteHolder, TipDropzone
from src.biohit_pipettor_plus.slot import Slot
from src.biohit_pipettor_plus.deck import Deck
from src.biohit_pipettor_plus.control_json import write_json, create_json_file

def main():
    create_json_file()

    well = Well(size_x=8, size_y=8, size_z=40, media="Buffer A")

    plate = Plate(
        size_x=20, size_y=20, size_z=15,
        wells_x=2, wells_y=2, first_well_xy=(0, 0),
        well=well
    )

    pipette_holder = PipetteHolder()
    dropzone = TipDropzone(size_x=30, size_y=30, size_z=5, drop_x=10, drop_y=15)

    # === Step 2: Slots erstellen ===
    slot1 = Slot(range_x=(0, 50), range_y=(0, 50), range_z=100, slot_id="slot_A1")
    slot2 = Slot(range_x=(50, 100), range_y=(0, 50), range_z=100, slot_id="slot_A2")

    # Labware auf Slots platzieren
    slot1.place_labware(plate, min_z=0)
    slot2.place_labware(pipette_holder, min_z=0)
    slot2.place_labware(dropzone, min_z=60)

    # === Step 3: Deck erstellen ===
    deck = Deck(range_x=(0, 100), range_y=(0, 100), deck_id="deck_1")

    # Slots auf Deck platzieren
    deck.add_slot(slot1)
    deck.add_slot(slot2)

    # === Step 4: Alles abspeichern ===
    write_json(deck)
main()