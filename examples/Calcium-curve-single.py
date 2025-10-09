from biohit_pipettor import Pipettor
import subprocess
import time
import sys

from upload_myrimager import upload_foc_file
sys.path.append(r"C:\labhub\Repos\smartlab-network\open-biohit-plus\src")
config_file = "c:\\Labhub\\Import\\contractiondb2_gwdg.json"
sys.path.append(r"C:\labhub\Repos\smartlab-network\open-biohit-plus\src")


from function_set_single import EHMPlatePos, Reservoirs, PipetteTips, TipDropzone, \
   remove_single, fill_single, pick_tip, return_tip, home, calc_concentration, Grid


# on bottom plate with thin wells towards back, top right corner of each lot
A1 = (130.5, 0)
A2 = (0, 0)
B1 = (130.5, 42)
B2 = (0, 42)
C1 = (130.5, 140)
C2 = (0, 140)


p = Pipettor(tip_volume=200, multichannel=False)


# python -m biohit-pipettor-python.examples.Ca_crcr_full_multi
p.x_speed = 7
p.y_speed = 7
p.z_speed = 8
p.tip_pickup_force = 20
p.aspirate_speed = 1


ehm_plate = EHMPlatePos(B1[0], B1[1])
ehm_plate.add_height = 58
ehm_plate.remove_height =58


#                            pick_zone    drop_zone
pipette_tips = PipetteTips(B2[0], B2[1], C1[0], C1[1])
pipette_tips.change_tips = 0  # as default keep tips


containers = Reservoirs(C2[0], C2[1])


"""
Define custom capacities (µl) and set disabled wells
my_caps = {1: 40000, 2: 50000, 3: 25000}
containers = Reservoirs(x_corner=100, y_corner=200, capacities=my_caps, disabled wells = [7,4])
"""


incubation_time = 300  #seconds
platename = 'single-pipettor-test'


# Create a dictionary for replacement vol and conc as per desired concentration goal.
# Do not enter initial concentration adn volume.
prep_table = [
   {"µl": 50, "mM": 0},
   {"µl": 500, "mM": 0},
   {"µl": 94, "mM": 1.8},
   {"µl": 107, "mM": 1.8},
   {"µl": 125, "mM": 1.8},
   {"µl": 150, "mM": 1.8},
   {"µl": 188, "mM": 1.8},
   {"µl": 250, "mM": 1.8},
   {"µl": 375, "mM": 1.8},
   {"µl": 88, "mM": 5},
   {"µl": 75, "mM": 0},
   {"µl": 164, "mM": 5},
   {"µl": 150, "mM": 5},
   {"µl": 188, "mM": 5},
   {"µl": 250, "mM": 5},
   {"µl": 375, "mM": 5},
   {"µl": 107, "mM": 15},
   {"µl": 125, "mM": 0},
   {"µl": 225, "mM": 15},
   {"µl": 214, "mM": 15},
   {"µl": 375, "mM": 0},
   {"µl": 480, "mM": 0},
]


#makes a dictionary setting all values to null. For those set to true, the function will take place
grid = Grid(cols=6, rows=8)

# Set multiple positions at once
positions_to_activate = [(0, 0), (5,7)]
grid.set_grid_values(positions_to_activate, True)


#this creates another dictionary with calculated concentrations. Initial conc and volume has to be entered.
concentration_table =  calc_concentration(prep_table, 1.8, 750)


# Turn on/off FOC Measurement
bDoFoc = 0


print("Starting Ca-force curve measurement")
print("Starting with 1.8mM default")


if bDoFoc:
   subprocess.call([r'C:\labhub\Import\FOC48.bat', platename])  # 0.2mM
print("Initial measurement completed")


cols = [1]

if pipette_tips.change_tips == 0:
   # pick tips once
   print("pick tips once")
   pick_tip(p, pipette_tips)


calcium_0_mM = containers.well2_x
calcium_1p8_mM = containers.well3_x
calcium_5_mM = containers.well4_x
calcium_15_mM = containers.well5_x


# to check proper initialisation
for well, volume in containers.current_volume.items():
   print(f"Well {well}: {volume} µl")


# loop over the conc_prep_table and take measurements.
# loop over the conc_prep_table and take measurements.
for row in prep_table:
    replacement_vol = row["µl"]
    mM = row["mM"]

    remove_single(p, ehm_plate, containers, pipette_tips, grid, replacement_vol)
    if mM == 0:
        fill_single(p, ehm_plate, containers, pipette_tips, replacement_vol, grid, stock_well=2)
    elif mM == 1.8:
        fill_single(p, ehm_plate, containers, pipette_tips, replacement_vol, grid, stock_well=3)
    elif mM == 5:
        fill_single(p, ehm_plate, containers, pipette_tips, replacement_vol, grid, stock_well=4)
    elif mM == 15:
        fill_single(p, ehm_plate, containers, pipette_tips, replacement_vol, grid, stock_well=5)
    else:
        print(f"Invalid Concentration in prep table i.e. not 0, 1.8, 5, 15")

    print(f"Filled well with {replacement_vol} medium")
    if bDoFoc:
        p.move_xy(0, 0)
        time.sleep(incubation_time)
        print(f"Incubation time {incubation_time * 60} seconds. Turn measurement ON")
        subprocess.call([r'C:\labhub\Import\FOC48.bat', platename])
        print(f"Completed measurement")
        p.move_z(0)

        upload_foc_file()
        print("Uploading results into contractiondb...")
        print("Upload finished")


if pipette_tips.change_tips == 0:
   return_multi_tips(p, pipette_tips)


# To check proper accounting of solutions.
for well, volume in containers.current_volume.items():
   print(f"Well {well}: {volume} µl")


home(p)
print("Completed Ca-force curve measurement. Replace plate, fill medium and discard waste before continuing")
