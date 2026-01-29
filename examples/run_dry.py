import time
import sys
import json
import os
import os.path
from envs import env

from biohit_pipettor import Pipettor

p = Pipettor(1000)



# path_file = os.sep.join([path_dir, filename])

calib_filename:    str = r"biohit_calibration.json"

tips_filename:     str = r"sartorius_96_tiprack_1200ul.json"
myrPlate_filename: str = r"myriamed_48_wellplate_750ul.json"

# Protocol
prot_filename: str = "simple_dispense_annotated.json"

sFile : str=os.sep.join([labware_folder, prot_filename])

prot_data=json.load(open(sFile))




