from biohit_pipettor import Pipettor
import subprocess
import time

import sys

from types import SimpleNamespace

from ..src.action import dilute_multi, remove_multi, fill_multi, discard_tips, home, pick_tip_multi, return_tip_multi

# sys.path.append(r"C:\Labhub\Repos\smartlab-network\contractiondb-python")
# from examples import upload_myrimager, analyzeMeasurement

from ..src.deck import Deck

# on bottom plate with thin wells towards back, top right corner of each lot
A1 = (130.5, 0)
A2 = (0, 0)
B1 = (130.5, 42)
B2 = (0, 42)
C1 = (130.5, 140)
C2 = (0, 140)


p = Pipettor(tip_volume=1000, multichannel=True)

# python -m biohit-pipettor-python.examples.Ca_crc_full_multi
p.x_speed = 7
p.y_speed = 7
p.z_speed = 8
p.tip_pickup_force = 20
p.aspirate_speed = 1


# legacy deck geometry as plain attribute bags (the action functions are duck-typed;
# the canonical labware classes are src.Plate / src.Reservoir / src.TipRack, loaded
# from labware/*.json and placed via src.deck.Deck)
ehm_plate = SimpleNamespace(
    x_corner=B1[0] + 13.5,
    y_corner=B1[1] + 9.5,
    x_step=18,
    y_step=9,
    x_tight=B1[0] + 11,
    y_tight=B1[1] + 8,
    x_corner_multi=B1[0] + 12,
    y_corner_multi=B1[1] + 43,
    add_height=30,
    remove_height=38,
    cols=6,
)

#                            pick_zone    drop_zone
pipette_tips = SimpleNamespace(
    x_corner=B2[0] + 105,
    y_corner=B2[1] + 10.5,
    x_corner_multi=B2[0] + 105,
    y_corner_multi=B2[1] + 42,
    x_step=9,
    change_tips=0,
    return_height=85,
    pick_height=75,  # as default keep tips
    x_drop=C1[0] + 50,
    y_drop=C1[1] + 50,
)

containers = SimpleNamespace(
    well1_x=C2[0] + 6 * 18 + 3,
    medium_x=C2[0] + 5 * 18 + 3,
    waste_x=C2[0] + 4 * 18 + 3,
    well4_x=C2[0] + 3 * 18 + 3,
    well5_x=C2[0] + 2 * 18 + 3,
    well6_x=C2[0] + 18 + 3,
    well7_x=C2[0] + 3,
    y_corner=C2[1] + 40,
    add_height=65,
    remove_height=90,
)


incubation_time = 300  # seconds
platename = "20250101x"

incubation_time = 3


#
# Turn on/off FOC MEasurement
#
bDoFoc = 0

print("Starting Ca-force curve measurement")
print("Starting with 1.8mM default")

if bDoFoc:
    subprocess.call([r"C:\labhub\Import\FOC48.bat", platename])  # 0.2mM

print("Initial measurement completed")

cols = [1, 3, 6]

# remove_multi(p, ehm_plate, containers, pipette_tips, cols, 600)

if pipette_tips.change_tips == 0:
    # pick tips once
    print("pick tips once")
    pick_multi_tips(p, pipette_tips)


# remove calcium
# remove down to 250µl

calcium_0_mM = containers.well4_x
calcium_18_mM = containers.well5_x
calcium_10_mM = containers.well6_x


remove_multi(p, ehm_plate, containers, pipette_tips, cols, 600)
fill_multi(p, ehm_plate, containers, pipette_tips, calcium_0_mM, cols, 450)  # 1.973mM

remove_multi(p, ehm_plate, containers, pipette_tips, cols, 600)
fill_multi(p, ehm_plate, containers, pipette_tips, calcium_0_mM, cols, 450)  # 1.973mM


# ef remove_multi(p: Pipettor, ehm_plate, containers, pipette_tips,  total_row: float,
#            volume: float, height: float, start_x=None, start_y=None,bChangeTips=1):


for volume in [50]:  # 0.2- 1mM
    remove_multi(p, ehm_plate, containers, pipette_tips, cols, volume)
    fill_multi(p, ehm_plate, containers, pipette_tips, containers.well5_x, cols, volume)  # 1.973mM

    print(f"Filled well with {volume} medium")
    if bDoFoc:
        p.move_xy(0, 0)
        time.sleep(incubation_time)
        print(f"Incubation time {incubation_time/60} minutes. Turn measurement ON")
        subprocess.call([r"C:\labhub\Import\FOC48.bat", platename])
        print(f"Completed measurement")
        p.move_z(0)

print("Fill cycle to 1mM complete")


for volume in [30]:  # 2- 10mM
    remove_multi(p, ehm_plate, containers, pipette_tips, cols, volume)
    fill_multi(p, ehm_plate, containers, pipette_tips, calcium_18_mM, cols, volume)  # 1.973mM
    print(f"Replaced {volume} ul medium")
    if bDoFoc:
        p.move_xy(0, 0)
        time.sleep(incubation_time)
        print(f"Incubation time {incubation_time/60} minutes. Turn measurement ON")
        subprocess.call([r"C:\labhub\Import\FOC48.bat", platename])
        print(f"Completed measurement")
        p.move_z(0)


print("Fill cycle to 4mM complete")

# Return from 10 to 1.8mM

remove_multi(p, ehm_plate, containers, pipette_tips, cols, 600)
fill_multi(p, ehm_plate, containers, pipette_tips, calcium_0_mM, 6, 450)  # 1.973mM

remove_multi(p, ehm_plate, containers, pipette_tips, cols, 600)
fill_multi(p, ehm_plate, containers, pipette_tips, calcium_0_mM, 6, 450)  # 1.973mM


if pipette_tips.change_tips == 0:
    return_multi_tips(p, pipette_tips)


home(p)
print("Completed Ca-force curve measurement. Replace plate, fill medium and discard waste before continuing")
