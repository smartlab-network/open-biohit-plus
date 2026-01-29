from biohit_pipettor import Pipettor
import subprocess
import time

import sys


#sys.path.append(r"C:\labhub\Repos\smartlab-network\open-biohit-plus\src")


from ..src.action import EHMPlatePos, Reservoirs, PipetteTips, TipDropzone,  \
    discard_tips, home

# on bottom plate with thin wells towards back, top right corner of each lot
A1 = (130.5,   0)
A2 = (0    ,   0)
B1 = (130.5,  42)
B2 = (0    ,  42)
C1 = (130.5, 140)
C2 = (0    , 140)



p= Pipettor(tip_volume=1000, multichannel=True)

#python -m biohit-pipettor-python.examples.Ca_crc_full_multi
p.x_speed = 7
p.y_speed = 7
p.z_speed = 8
p.tip_pickup_force = 20
p.aspirate_speed = 1


ehm_plate = EHMPlatePos(B1[0], B1[1])
ehm_plate.add_height=30
ehm_plate.remove_height=38

#                            pick_zone    drop_zone
pipette_tips = PipetteTips(B2[0], B2[1], C1[0], C1[1])

pipette_tips.change_tips=0    #as default keep tips

containers = Reservoirs(C2[0], C2[1])


incubation_time = 300     #seconds
platename       = '20250101x'

incubation_time = 3


#
# Turn on/off FOC MEasurement
#
bDoFoc = 0

print("Starting Ca-force curve measurement")
print("Starting with 1.8mM default")

if bDoFoc:
    subprocess.call([r'C:\labhub\Import\FOC48.bat', platename]) # 0.2mM

print("Initial measurement completed")

cols=[1,3,6]

#remove_multi(p, ehm_plate, containers, pipette_tips, cols, 600)

if pipette_tips.change_tips==0:
    #pick tips once    
    print("pick tips once")    
    pick_multi_tips(p, pipette_tips)
    

#remove calcium
# remove down to 250µl

calcium_0_mM = containers.well4_x
calcium_18_mM = containers.well5_x
calcium_10_mM = containers.well6_x


remove_multi(p, ehm_plate, containers, pipette_tips, cols, 600)
fill_multi(p, ehm_plate, containers, pipette_tips, calcium_0_mM, cols, 450)  # 1.973mM

remove_multi(p, ehm_plate, containers, pipette_tips, cols, 600)
fill_multi(p, ehm_plate, containers, pipette_tips, calcium_0_mM, cols, 450)  # 1.973mM


    
#ef remove_multi(p: Pipettor, ehm_plate, containers, pipette_tips,  total_row: float, 
#            volume: float, height: float, start_x=None, start_y=None,bChangeTips=1):

    
for volume in [50]:  # 0.2- 1mM
    remove_multi(p, ehm_plate, containers, pipette_tips, 6, volume)
    fill_multi(p, ehm_plate, containers, pipette_tips, containers.well5_x, 6, volume)  # 1.973mM

    print(f"Filled well with {volume} medium")
    if bDoFoc:
        p.move_xy(0, 0)
        time.sleep(incubation_time)
        print(f"Incubation time {incubation_time/60} minutes. Turn measurement ON")        
        subprocess.call([r'C:\labhub\Import\FOC48.bat', platename])
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
        subprocess.call([r'C:\labhub\Import\FOC48.bat', platename])
        print(f"Completed measurement")
        p.move_z(0)


print("Fill cycle to 4mM complete")

#Return from 10 to 1.8mM

remove_multi(p, ehm_plate, containers, pipette_tips, cols, 600)
fill_multi(p, ehm_plate, containers, pipette_tips, calcium_0_mM, 6, 450)  # 1.973mM

remove_multi(p, ehm_plate, containers, pipette_tips, cols, 600)
fill_multi(p, ehm_plate, containers, pipette_tips, calcium_0_mM, 6, 450)  # 1.973mM



    
if pipette_tips.change_tips==0:
    return_multi_tips(p, pipette_tips)
    
    
home(p)
print("Completed Ca-force curve measurement. Replace plate, fill medium and discard waste before continuing")
