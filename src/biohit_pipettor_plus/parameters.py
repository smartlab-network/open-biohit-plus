#These can be converted to GUI later if needed.
#TODO write a position.py that takes in parameter.py and then assign labware positions.

from ..biohit_pipettor_plus.deck import Deck
from ..biohit_pipettor_plus.slot import Slot
from ..biohit_pipettor_plus.labware import Plate, PipetteHolder, TipDropzone, ReservoirHolder
from ..biohit_pipettor_plus.labware import Well
from ..biohit_pipettor_plus.position import PositionCalculator
from ..biohit_pipettor_plus.serializable import Serializable
import json
from ..biohit_pipettor_plus.position import Position
from ..biohit_pipettor_plus.control_json import read_json, write_json

deck1 = Deck((0,500), (0,500), "deck1")


# Todo find range_z. See the manual for more precise locations of slot.
#Slot 1 and 2 are not fully accessible via multipipette. Their range y needs to be updated.
slot1 = Slot((0, 1), (0, 10), 500, "slot1")
slot2 = Slot((0, 1), (0, 10), 500, "slot2")
slot3 = Slot((0, 119), (10, 95), 500, "slot3")
slot4 = Slot((129, 248), (10, 95), 500, "slot4")
slot5 = Slot((0, 119), (105,190), 500, "slot5")
slot6 = Slot((129, 248), (105, 190), 500, "slot6")

#adding all used stock to deck1
deck1.add_slots([slot3, slot4, slot5, slot6])

#TODO 48 well plate dimension and wells, maps
example_well = Well(size_x=2, size_y=1, size_z=5)
plate1 = Plate(20, 10, 50, 7, 8, (30, 50), well = example_well)
deck1.add_labware(plate1, slot_id="slot3", min_z=2)

#TODO add reservoirs dimensions
reservoirs_data = {
    1: {"size_x": 10, "size_y": 20, "size_z": 10, "capacity": 30000,
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

    7: {"size_x": 15, "size_y": 20, "size_z": 15, "capacity": 30000,
        "filled_volume": 100, "content": "waste"},

}

reservoirs = ReservoirHolder(
    size_x= 119,
    size_y= 70,
    size_z= 200,
    hook_count = 7,
    reservoir_dict = reservoirs_data,
)

deck1.add_labware(reservoirs, slot_id="slot4", min_z=2)

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


#for cid, reservoir in reservoirs.containers.items():
  # print(f"Container {cid} → labware_id: {reservoir.labware_id}")


pos_calc = PositionCalculator(x_corner=20, y_corner=50)

# Compute positions for 8 reservoirs in a row,
# each 22 mm apart (example spacing), first reservoir shifted by (5, 10)
#positions = pos_calc.position_multi(
 #   count=len(reservoirs.containers),
  #  step_x=22.0,
   # offset=(5.0, 10.0)


