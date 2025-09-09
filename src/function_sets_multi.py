"""
Classes and functions to be used with biohit_pipettor
p = Pipettor() in all cases
"""
import time
from typing import List

from biohit_pipettor import Pipettor
from biohit_pipettor.errors import CommandFailed


class EHMPlatePos:
    def __init__(self, x_corner, y_corner):
        self.x_corner = x_corner + 13.5
        self.y_corner = y_corner + 9.5
        self.x_step = 18
        self.y_step = 9
        self.x_tight = x_corner + 11
        self.y_tight = y_corner + 8
        self.x_corner_multi = x_corner + 12
        self.y_corner_multi = y_corner + 43
        self.add_height = 30
        self.remove_height = 38
        self.cols = 6


class Reservoirs:
    def __init__(self, x_corner, y_corner):
        self.well1_x  = x_corner + 6 * 18 + 3    #1
        self.medium_x = x_corner + 5 * 18 + 3    #2
        self.waste_x  = x_corner + 4 * 18 + 3    #3
        self.well4_x  = x_corner + 3 * 18 + 3    #4
        self.well5_x  = x_corner + 2 * 18 + 3
        self.well6_x  = x_corner + 1 * 18 + 3
        self.well7_x  = x_corner  + 3
        self.y_corner = y_corner + 40
        self.add_height = 65
        self.remove_height = 90


class RoundContainers:  # TODO: adjust to 6-well setup once that�s printed
    def __init__(self, x_corner, y_corner):
        self.medium_x = x_corner + 104.5
        self.waste_x = x_corner + 62.5
        self.well3_x = x_corner + 20.5
        self.y_corner = y_corner + 15


class PipetteTips:
    def __init__(self, x_corner, y_corner, x_drop, y_drop):
        self.x_corner = x_corner + 105
        self.y_corner = y_corner + 10.5
        self.x_corner_multi = x_corner + 105
        self.y_corner_multi = y_corner + 42
        self.x_step = 9
        self.change_tips = 1
        self.return_height = 85
        self.pick_height   = 75
        self.x_drop   = x_drop+50
        self.y_drop   = y_drop+50


class TipDropzone:
    def __init__(self, x_corner, y_corner):
        self.x_corner = x_corner + 50
        self.y_corner = y_corner + 40


"""Functions"""


def pick_multi_tips(p: Pipettor, pipette_tips):
    """
    Picks tips going through tip box left to right
    :param p: Pipettor, multichannel = True
    :param pipette_tips:
    """
    print("pick_multi_tips: start")
    p.move_xy(pipette_tips.x_corner_multi, pipette_tips.y_corner_multi)    
    
    for i in range(1, 13, 1):
        try:
            p.pick_tip(pipette_tips.pick_height)
            print("Picked up pipette tip")
            break
        except CommandFailed:
            print(f"Found no tips, moving on to x {pipette_tips.x_corner - i * 9}")
            p.move_x(pipette_tips.x_corner_multi - i * 9)
            continue
        finally:
            p.move_z(0)
    else:
        raise RuntimeError(f"Failed to pick tips from {i} pipette box columns")

def return_multi_tips(p: Pipettor, pipette_tips):
    """
    Return Tips to tip box left to right
    :param p: Pipettor, multichannel = True
    :param pipette_tips:
    """
    p.move_xy(pipette_tips.x_corner_multi,pipette_tips.y_corner_multi)    
    p.move_z(85)
    p.eject_tip()
    p.move_z(0)
    


#fill_multi(p, ehm_plate, containers, pipette_tips, tip_dropzone, containers.well5_x, 6, 
#            volume, 48, None, None, bChangeTips)  # 1.973mM
def fill_multi(p: Pipettor, ehm_plate: EHMPlatePos, containers: Reservoirs, pipette_tips, stock_x, cols: List[float], volume: float):
    """
    Using multichannel ,fills specified amount of volume into specified columns at desired height
    :param p: Pipettor, multichannel
    :param stock_x: location of stock, give full location of reservoir
    :param total_row: total length of column (nr in wells)
    :param volume:
    :param fill_height:
    :param start_x: default = ehm_plate.x_corner, skip columns to start of fill
    :param start_y: default = ehm_plate.y_corner_multi, NOT advised to change
    :param bChangeTips: default = TRUE, Keep Tips or not
    :return:
    """
    tip_content = 0

    if pipette_tips.change_tips :
        pick_multi_tips(p, pipette_tips)
        
    for col in cols:
        if tip_content < volume:
            p.move_xy(stock_x, containers.y_corner)
            #p.move_x(stock_x)
            #p.move_y(containers.y_corner)
            suck(p, 1000, containers.remove_height)
            tip_content = 1000
        else:
            pass
        x_pos = ehm_plate.x_corner + (ehm_plate.cols - col) * ehm_plate.x_step
        p.move_xy(x_pos, ehm_plate.y_corner_multi)
        spit(p, volume, ehm_plate.add_height)
        tip_content = tip_content - volume
    p.move_z(0)
    p.move_xy(stock_x, containers.y_corner)
    spit_all(p, containers.add_height)
    if pipette_tips.change_tips:
        drop_multi_tips(p, pipette_tips)
    p.move_z(0)


def remove_multi(p: Pipettor, ehm_plate: EHMPlatePos, containers: Reservoirs, pipette_tips,  cols: List[float] , volume: float):
    """Removes medium from whole 48well plate
    Adjustments possible by altering total number of columns and rows
    :param total_row: total length of a row (in wells)
    :param total_column: total length of a column (in wells)
    :param height: height of EHM plate, mind sufficient distance from plate floor
    :param volume: amount ot be removed
    :param start_x: default = ehm_plate_x.corner, skip columns to start of fill
    :param start_y: default = ehm_plate_y.corner, skip columns to start of fill
    :param bChangeTips: default = TRUE, Keep Tips or not
    """
    print(f"x corner {ehm_plate.x_corner} and step {ehm_plate.x_step}")

    for col in cols:
        print(f"do col {col}")
        x_col = ehm_plate.cols - col
        x_pos = ehm_plate.x_corner + (x_col * ehm_plate.x_step)
        print(f"move to col {x_col} of {ehm_plate.cols} mm {x_pos} and y_mm{ehm_plate.y_corner_multi}")



    tip_content = 0

    if pipette_tips.change_tips:
        pick_multi_tips(p, pipette_tips)
    
    for col in cols:
        if 1000 - tip_content < volume:
            p.move_xy(containers.waste_x, containers.y_corner)
            spit(p, tip_content, containers.add_height)
            tip_content = 0
        else:
            pass
        p.move_z(0)
        x_col =ehm_plate.cols - col
        x_pos =ehm_plate.x_corner + (x_col * ehm_plate.x_step)
        print(f"move to col {x_col} of {ehm_plate.cols} mm {x_pos} and y_mm{ehm_plate.y_corner_multi}")
        p.move_xy(x_pos, ehm_plate.y_corner_multi)
        suck(p, volume, ehm_plate.remove_height)
        tip_content = tip_content + volume

    p.move_z(0)
    p.move_xy(containers.waste_x, containers.y_corner)
    spit(p, tip_content, containers.add_height)    
    print(f"Removed {volume} ul medium from plate")
    if pipette_tips.change_tips:
        drop_multi_tips(p,pipette_tips)
        
    
def drop_multi_tips(p: Pipettor, pipette_tips: PipetteTips):
    p.move_z(0)
    p.move_xy(pipette_tips.drop_x, pipette_tips.drop_y)
    p.eject_tip()
       


def suck(p: Pipettor, volume: float, height: float):
    """
    Aspirates given volume and returns to position z=0
    :param volume: volume to aspirate
    :param height: height from which to aspirate
    """
    p.move_z(height)
    p.aspirate(volume)
    p.move_z(0)


def spit(p: Pipettor, volume: float, height: float):
    """
    Dispenses given volume and returns to position z=0
    :param volume: volume to dispense
    :param height: height from which to dispense
    """
    p.move_z(height)
    p.dispense(volume)
    p.move_z(0)


def spit_all(p: Pipettor, height: float):
    """
    Dispenses all volume from pipette and returns to position z=0
    :param height: height from which to aspirate
    """
    p.move_z(height)
    p.dispense_all()
    p.move_z(0)


def home(p: Pipettor):
    p.move_z(0)
    p.move_xy(0, 0)
    print("Device in startup position")
