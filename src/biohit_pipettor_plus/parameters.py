#These can be converted to GUI later if needed.
#TODO write a position.py that takes in parameter.py and then assign labware positions.

from ..biohit_pipettor_plus.deck import Deck
from ..biohit_pipettor_plus.slot import Slot
from ..biohit_pipettor_plus.labware import Plate, PipetteHolder, TipDropzone, Reservoirs
from ..biohit_pipettor_plus.labware import Well
from ..biohit_pipettor_plus.serializable import Serializable
import json
from ..biohit_pipettor_plus.control_json import read_json, write_json

deck1 = Deck((0,500), (0,500), "deck1")

#See the manual for more precise locations of slot. Slot 1 and 2 are not fully accessible via multipipette.
#slot1 = Slot((100, 300), (50, 100), 500, "slot1")
#slot2 = Slot((100, 300), (50, 100), 500, "slot2")
slot3 = Slot((-10, 119), (10, 95), 500, "slot3")
slot4 = Slot((129, 249), (50, 100), 500, "slot4")
slot5 = Slot((-10, 119), (50, 100), 500, "slot5")
slot6 = Slot((129, 249), (50, 100), 500, "slot6")

#TODO 48 well plate dimension and wells, maps
example_well = Well(size_x=2, size_y=1, size_z=5)
plate1 = Plate(20, 10, 50, 7, 8, (30, 50), well = example_well)
#print(plate1.get_containers())

#TODO add reservoirs dimensions
reservoirs = Reservoirs(
    size_x= 20,size_y= 20,size_z= 20,
    x_corner=10.0,
    y_corner=20.0,
    container_ids=[1, 2, 3, 4, 5, 6, 7, 8],
    capacities={3: 50000, 4: 50000},
    filled_vol={2: 20000, 4: 15000, 5: 25000, 6: 10000},  # Custom initial volumes
    waste_containers={8},
    disabled_containers={7},
    equivalent_groups={
        2: [2, 6], 6: [2, 6],
        1: [1, 7], 7: [1, 7],
    }
)

#TODO define pipette pick up and drop zone
pipette_holder = PipetteHolder(labware_id="pipette_holder_1")


#TODO understand drop zone and see how to implement it.
tip_dropzone = TipDropzone(
    size_x=50,
    size_y=50,
    size_z=20,
    drop_x=25,  # Center of the dropzone in X (relative to slot)
    drop_y=25,  # Center of the dropzone in Y (relative to slot)
    labware_id="dropzone_1",
    drop_height_relative=15  # Drop height 15mm above the dropzone base
)

prep_table = [
    {"µl": 500, "mM": 0},
    {"µl": 500, "mM": 0},
    {"µl": 94, "mM": 1.8},
    {"µl": 107, "mM": 1.8},
    {"µl": 125, "mM": 1.8},
    {"µl": 150, "mM": 1.8},
    {"µl": 188, "mM": 1.8},
    {"µl": 250, "mM": 1.8},
    {"µl": 375, "mM": 1.8},
    {"µl": 44, "mM": 5},
    {"µl": 47, "mM": 5},
    {"µl": 125, "mM": 5},
    {"µl": 150, "mM": 5},
    {"µl": 188, "mM": 5},
    {"µl": 250, "mM": 5},
    {"µl": 375, "mM": 5},
    {"µl": 36, "mM": 15},
    {"µl": 75, "mM": 15},
    {"µl": 167.0, "mM": 15},
    {"µl": 214, "mM": 15},
    {"µl": 375, "mM": 0},
    {"µl": 480, "mM": 0},
]





