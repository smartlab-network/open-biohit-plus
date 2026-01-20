"""
Classes and functions to be used with biohit_pipettor
p = Pipettor() in all cases
"""

import time
from typing import List
from biohit_pipettor import Pipettor
from biohit_pipettor.errors import CommandFailed
from math import ceil


class EHMPlatePos:
    def __init__(self, x_corner, y_corner):
        self.x_corner = x_corner + 13.5
        self.y_corner = y_corner + 9.5
        self.x_step = 18
        self.y_step = 9
        self.x_tight = x_corner + 11
        self.y_tight = y_corner + 8
        self.x_corner_multi = x_corner + 15.5
        self.y_corner_multi = y_corner + 43
        self.add_height = 30
        self.remove_height = 38.5
        self.cols = 6



class Reservoirs:
    def __init__(self, x_corner, y_corner, capacities=None, disabled_wells=None):

        #position of wells'''
        self.well1_x = x_corner + 6 * 18 + 3
        self.well2_x = x_corner + 5 * 18 + 3
        self.well3_x = x_corner + 4 * 18 + 3  # 3 1.8mM
        self.well4_x = x_corner + 3 * 18 + 3  # 4 5mM
        self.well5_x = x_corner + 2 * 18 + 3  # 5 15mM
        self.well6_x = x_corner + 1 * 18 + 3
        self.well7_x = x_corner + 3

        #wells containing same solution can be listed together. see get_equivalent_group & stock_well in fill_multi and remove_multi
        self.conc0_wells = [2, 6]  # 0 mM equivalents
        self.waste_wells = [1, 7]  # waste equivalents

        self.y_corner = y_corner + 40
        self.add_height = 65
        self.remove_height = 103

        """
        set 30000ul is the default well capacity which is also set to be current volume for all but waste. 
        Reservoir class has parameter to input variable capacities if needed. 
        Remember to edit dimension in ReservoirGeometry if changing wells to adjust height calculations. #Store wells geometry in class maybe
        """
        default_capacities = {
            1: 35000,  # 1 Waste
            2: 30000,  # 2 0mM
            3: 30000,  # 3 1.8mM
            4: 30000,  # 4 5 mM
            5: 30000,  # 5 10mM
            6: 30000,  # 6 0mM
            7: 35000,  # 7 Waste
        }

        if capacities is not None:
            merged_capacities = default_capacities.copy()
            merged_capacities.update(capacities)
            self.capacities = merged_capacities
        else:
            self.capacities = default_capacities


        """ 
        Disabled wells: Some reservoirs may no longer be usable. Instead of rewriting all pipetting
        logic, a list of disabled wells is kept. Any well added here is treated as "non-existent":
          - Its capacity & current volume is set to 0
          - It is automatically skipped in suck/spit operations and get_equivalent_group() lookups.
          """

        if disabled_wells is None:
            disabled_wells = set()
        else:
            disabled_wells = set(disabled_wells)

        for well in disabled_wells:
            self.capacities[well] = 0


        """assumes every reservoir is filled to the capacity expect for waste and disabled.
        Errors are calculated by current volume, capacity and aspiration/dispense volume  
        """
        self.current_volume = {k: 0 if k in (1, 7) else (self.capacities[k] if k not in disabled_wells else 0) for k in
                               self.capacities.keys()}

        self.disabled_wells = disabled_wells

    # The following two functions keep track of reservoir volume when dispensing and aspirating  liquid, raising error if necessary
    def add_volume(self, well: int, volume: float):
        """Add liquid to a well if capacity allows."""
        if self.current_volume[well] + volume > self.capacities[well]:  # +5ml coz overflow only possible if volume added is highly above limit
            raise ValueError(f"Reservoir {well} overflow! Capacity: {self.capacities[well]} µl")
        self.current_volume[well] += volume

    def remove_volume(self, well: int, volume: float):
        """Remove liquid from a well if enough is available."""
        if self.current_volume[well]  < volume:  # -5ml coz its way difficult to reach the bottom and take all liquid out
            raise ValueError(f"Reservoir {well} underflow! Only {self.current_volume[well]} µl available.")
        self.current_volume[well] -= volume

    # This is done to loop through suck/spit function for equivalent wells containing same solution. hence avoiding error and handling more volume.
    def get_equivalent_group(self, well: int):
        if well in self.conc0_wells:
            return [w for w in self.conc0_wells if w not in self.disabled_wells]
        if well in self.waste_wells:
            return [w for w in self.waste_wells if w not in self.disabled_wells]
        if well in self.disabled_wells:
            return []
        return [well]


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
        self.pick_height = 75
        self.x_drop = x_drop + 50
        self.y_drop = y_drop + 50


class TipDropzone:
    def __init__(self, x_corner, y_corner):
        self.x_corner = x_corner + 50
        self.y_corner = y_corner + 40



class ReservoirGeometry:
    """
    .top signifies the cuboidal part.
    .lower signifies the triangular part
    """

    class Geometry30ml:
        """Hardcoded geometry for 30 mL reservoir"""
        top_w = 1.2
        top_l = 9.0
        top_h = 0.85
        lower_h = 3.25

        # volume of triangular prism - volume = 0.5 * b * h * length,
        # volume of cuboidal = b * h * length
        top_vol_ul = int(round(top_h * top_l * top_w * 1000))        # *1000 coz we use ul across the code and not ml
        lower_vol_ul = int(round((top_l * top_w * lower_h / 2 * 1000)))
        total_vol_ul = top_vol_ul + lower_vol_ul

    def __init__(self, total_volume_ml: int = 30):
        # Ensure parameter is integer
        if not isinstance(total_volume_ml, int):
            raise ValueError("total_volume_ml must be an integer (mL)")

        self.total_volume_ml = total_volume_ml
        self.default_height = 66 # safe height
        # Assign geometry if predefined, else None
        if total_volume_ml == 30:
            self.geometry = self.Geometry30ml
        else:
            self.geometry = None

    def calc_height(self, vol_ul: float) -> float:
        """
        Returns pipette aspiration height (mm) based on current liquid volume.
        - Uses predefined geometry if available
        - Else returns default safe height
        """
        if self.geometry is None:
            print(
                f"No predefined geometry for {self.total_volume_ml} mL, using default height {self.default_height} mm")
            return self.default_height

        if vol_ul <= 0:
            print("Volume <= 0, returning height 0.0 mm")
            return 0.0

        g = self.geometry

        """
           Returns pipette aspiration height (mm) based on current liquid volume.
           - If volume exceeds lower triangular part → calculate height in top cuboid.
           - Else → calculate height within triangular bottom by using the unfilled volume to determine unused & actual height .
           - Final pipette height is clamped between 98–103 mm for safety especially against measurement errors.
       """

        if vol_ul > g.lower_vol_ul:
            # Top cuboidal region
            vol_top = vol_ul - g.lower_vol_ul
            h_top = round(vol_top / (g.top_l * g.top_w * 1000), 2)
            liquid_h = g.lower_h + min(h_top, g.top_h)
        else:
            # Bottom triangular prism. found by finding height of unfilled well and subtracting from total.
            remaining_volume = g.lower_vol_ul - vol_ul
            remaining_height = round(2 * remaining_volume / (g.top_w * g.top_l * 1000), 2)
            liquid_h = g.lower_h - remaining_height

        # Clamp height
        max_pip_height = 72
        min_pip_height = 60
        pip_height = max(min_pip_height, min(max_pip_height, max_pip_height - liquid_h))

        print(f"Calculated pipette height: {pip_height} mm")
        return pip_height

"""Functions"""

def pick_multi_tips(p: Pipettor, pipette_tips):
    """
    Picks tips going through tip box left to right
    :param p: Pipettor, multichannel = True
    :param pipette_tips:
    """
    print("pick_multi_tips: start")
    p.move_xy(pipette_tips.x_corner, pipette_tips.y_corner)
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
    p.move_xy(pipette_tips.x_corner_multi, pipette_tips.y_corner_multi)
    p.move_z(85)
    p.eject_tip()
    p.move_z(0)


def fill_multi(p: Pipettor, ehm_plate: EHMPlatePos, containers: Reservoirs, pipette_tips, stock_x, cols: List[float],
               volume: float, stock_well: int = None, ):
    """
      Using a multichannel pipette, fills a specified volume into the given columns of a plate.

      :param p: Pipettor object (multichannel pipette)
      :param ehm_plate: Plate position object with dimensions and coordinates
      :param containers: Reservoirs object that holds stock solutions
      :param pipette_tips: PipetteTips object (handles picking/dropping tips)
      :param stock_x: X-position of the stock solution (not used directly here)
      :param cols: List of column indices to be filled
      :param volume: Volume to dispense per column (µl)
      :param stock_well: (optional) index of a specific stock well to aspirate from.
                         Supports equivalent wells in the same group.
      """

    if pipette_tips.change_tips:
        pick_multi_tips(p, pipette_tips)

    # --- Step 1: Iterate over each column that needs to be filled ---
    for col in cols:
        max_vol_per_go = p.tip_volume
        volume_to_fill = volume
        # in case volume to pipette is more than capacity. like pipette 2ml by 1ml pipettor. loops over then.
        total_steps_required = ceil(volume / max_vol_per_go)
        steps_done = 0

        # --- Step 2: Loop until full volume for this column is dispensed --
        while steps_done < total_steps_required:
            vol = min(volume_to_fill, max_vol_per_go)

            # --- Step 3: Try to aspirate from stock_well or equivalent wells ---
            for candidate in containers.get_equivalent_group(stock_well):
                if candidate in containers.disabled_wells:
                    continue  # skip disabled wells
                try:
                    # Move pipette to the candidate reservoir position and try to aspirate.
                    # Suck function includes checks if aspiration is possible or not.
                    p.move_xy(getattr(containers, f"well{candidate}_x"), containers.y_corner)
                    suck(p, vol, containers.remove_height, reservoirs=containers, well=candidate)
                    print(f"Aspirated {vol} µl from well {candidate}")
                    break
                except ValueError as e:
                    print(f"⚠️ Well {candidate} failed: {e}") #aspiration from the candidate is not possible.
            else:
                raise RuntimeError(f"No available equivalent wells for {stock_well}")

            # --- Step 4: Move pipette to target column in the plate ---
            x_pos = ehm_plate.x_corner + (ehm_plate.cols - col) * ehm_plate.x_step
            p.move_xy(x_pos, ehm_plate.y_corner_multi)

            # --- Step 5: Dispense the aspirated volume into all tips simultaneously
            # more accurate than spit(p, vol, ehm_plate.add_height).
            # if filling multiple wells from each pipette, use spit and maybe a for loop.
            spit_all(p, ehm_plate.add_height)
            volume_to_fill -= vol
            steps_done += 1
    p.move_z(0)

    if pipette_tips.change_tips:
        drop_multi_tips(p, pipette_tips)


def remove_multi(p: Pipettor, ehm_plate: EHMPlatePos, containers: Reservoirs, pipette_tips, cols: List[float],
                 volume: float, ):
    """
        Removes medium from specified columns of a 48-well plate using a multichannel pipette.

        The removed liquid is transferred to designated waste wells. Works in multiple aspiration steps if the required volume exceeds pipette capacity.
        :param p: Pipettor object (multichannel pipette)
        :param ehm_plate: Plate position object with dimensions and coordinates
        :param containers: Reservoirs object (tracks volumes, waste wells, disabled wells)
        :param pipette_tips: PipetteTips object (handles tip usage)
        :param cols: List of column indices to remove liquid from
        :param volume: Volume to remove from each column (µl)
        """

    # --- Step 1: Pick tips if needed ---
    if pipette_tips.change_tips:
        pick_multi_tips(p, pipette_tips)

    # --- Step 2: Loop over all specified columns ---
    for col in cols:
        max_vol_per_go = p.tip_volume
        # this is done in case pipette capacity is less than volume_to_fill
        total_steps_required = ceil(volume / max_vol_per_go)
        steps_done = 0

        x_col = ehm_plate.cols - col
        x_pos = ehm_plate.x_corner + (x_col * ehm_plate.x_step)

        # --- Step 3: Loop until full volume is removed from this column ---
        while steps_done < total_steps_required:
            p.move_z(0)
            p.move_xy(x_pos, ehm_plate.y_corner_multi)
            print(f"move to col {x_col} of {ehm_plate.cols} mm {x_pos} and y_mm{ehm_plate.y_corner_multi}")

            # Decide how much to aspirate this step (don’t exceed pipette capacity)
            vol = min(max_vol_per_go, (volume - (steps_done * max_vol_per_go)))
            suck(p, vol, ehm_plate.remove_height)

            # --- Step 4: Transfer aspirated liquid to appropriate waste well ---
            for candidate in containers.get_equivalent_group(1):  # 1 = waste group
                if candidate in containers.disabled_wells:
                    continue  # skip disabled wells
                try:
                    p.move_xy(getattr(containers, f"well{candidate}_x"), containers.y_corner)
                    # spit function includes checks if dispense is possible or not to prevent overflow.
                    spit_all(p, containers.add_height, vol, reservoirs=containers, well=candidate)
                    print(f"Dispensed {vol} µl to waste well {candidate}")
                    break
                except ValueError as e:
                    print(f"⚠️ Waste well {candidate} full: {e}")
            else:
                # If no waste wells are available → stop execution
                raise RuntimeError("Both waste wells (1 & 7) are full. Empty before continuing.")

            steps_done += 1

    if pipette_tips.change_tips:
        drop_multi_tips(p, pipette_tips)


def drop_multi_tips(p: Pipettor, pipette_tips: PipetteTips):
    p.move_z(0)
    # p.move_xy(pipette_tips.drop_x, pipette_tips.drop_y)
    p.move_xy(pipette_tips.x_drop, pipette_tips.y_drop)
    p.eject_tip()


def suck(p: Pipettor, volume: float, height: float, reservoirs: Reservoirs = None, well: int = None):
    """
    Aspirates (sucks up) a given volume and returns pipette to z=0 (safe height).

    :param p: Pipettor object
    :param volume: volume to aspirate (µl)
    :param height: aspiration height inside the well (mm)
    :param reservoirs: (optional) Reservoirs object to track liquid usage
    :param well: (optional) specific well index in the reservoir
    """
    # loop to alter height with every 0.2ml
    max_vol_per_go = 200
    total_steps_required = ceil(volume / max_vol_per_go)
    steps_done = 0

    if reservoirs and well is not None:
        geom = ReservoirGeometry(total_volume_ml=30)                  # geometry helper to calculate heights
        reservoirs.remove_volume(well, volume * 6)  # raises value error if remove volume is more than current.

    while steps_done < total_steps_required:

        if reservoirs and well is not None:
            height = geom.calc_height(reservoirs.current_volume[well])
            print(f"Height is: {height} mm")  # <-- print the actual height

        p.move_z(height)
        vol = min(max_vol_per_go, (volume - (steps_done * max_vol_per_go)))
        p.aspirate(vol)
        steps_done += 1
    p.move_z(0)


def spit(p: Pipettor, volume: float, height: float, reservoirs: Reservoirs = None, well: int = None):
    """
    Dispenses (spits out) a given volume and returns pipette to z=0 (safe height).

    :param p: Pipettor object
    :param volume: volume to dispense (µl)
    :param height: dispense height inside the well (mm)
    :param reservoirs: (optional) Reservoirs object to track liquid usage
    :param well: (optional) specific well index in the reservoir
    """

    if reservoirs and well is not None:
        reservoirs.add_volume(well, volume * 6)
    p.move_z(height)
    p.dispense(volume)
    p.move_z(0)


def spit_all(p: Pipettor,height: float, volume: float = None, reservoirs: Reservoirs = None, well: int = None):
    """
    Dispenses (empties) all liquid currently inside the pipette, then returns to z=0 (safe height).
    :param p: Pipettor object
    :param height: dispense height inside the well (mm)
    :param volume: (optional) volume to record in reservoir tracking (µl)
    :param reservoirs: (optional) Reservoirs object to track liquid usage
    :param well: (optional) specific well index in the reservoir
    """
    if reservoirs and well is not None:
        reservoirs.add_volume(well, volume * 6) # raises value error if remove volume leads to overflow.
    p.move_z(height)
    p.dispense_all()
    p.move_z(0)


def calc_concentration(prep_table, initial_conc, initial_vol):
    """ calculate concentration after each row and add result to the prep_table """
    for row in prep_table:
        replacement_vol = row["µl"]
        replacement_conc = row["mM"]
        remaining_moles = initial_conc * (initial_vol - replacement_vol)
        added_moles = replacement_vol * replacement_conc
        total_moles = added_moles + remaining_moles
        final_conc = round(total_moles / initial_vol, 2)
        row["final_conc"] = final_conc
        initial_conc = final_conc
        # initial_vol remains unchanged
    return prep_table


def home(p: Pipettor):
    p.move_z(0)
    p.move_xy(0, 0)
    print("Device in startup position")
