"""
Classes and functions to be used with biohit_pipettor
p = Pipettor() in all cases


To do fix height parameter and position parameters.
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
       self.x_corner_multi = x_corner + 12
       self.y_corner_multi = y_corner + 43
       self.add_height = 58
       self.remove_height = 58
       self.cols = 6
       self.rows = 8




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


class Grid:
    def __init__(self, cols, rows):
        self.cols = cols
        self.rows = rows
        self.table = {f"{col}:{row}": False for col in range(self.cols) for row in range(self.rows)}

    def set_grid_values(self, positions: list[tuple[int, int]], value: bool) -> None:
        """
        Set multiple (col, row) positions in the grid to the same value.

        Parameters
        ----------
        positions : list[tuple[int, int]]
            List of (col, row) pairs to modify.
        value : bool
            The value to assign (True or False).
        """
        for col, row in positions:
            key = f"{col}:{row}"
            if key in self.table:
                self.table[key] = value
            else:
                raise KeyError(f"Invalid position ({col}, {row}).")

    def is_grid_position_active(self, col: int, row: int) -> bool:
        """Check if a grid position is active (True)."""
        key = f"{col}:{row}"
        if key not in self.table:
            raise KeyError(f"Invalid position ({col}, {row}).")
        return self.table[key]


class TipDropzone:
   def __init__(self, x_corner, y_corner):
       self.x_corner = x_corner + 50
       self.y_corner = y_corner + 40


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
       self.add_height = 35
       self.remove_height = 38


       """
       set 30000ul is the default well capacity which is also set to be current volume for all but waste.
       Reservoir class has parameter to input variable capacities if needed.
       Remember to edit dimension in ReservoirGeometry if changing wells to adjust height calculations. #Store wells geometry in class maybe
       """
       default_capacities = {
           1: 30000,  # 1 Waste
           2: 30000,  # 2 0mM
           3: 30000,  # 3 1.8mM
           4: 30000,  # 4 5 mM
           5: 30000,  # 5 15mM
           6: 30000,  # 6 0mM
           7: 30000,  # 7 Waste
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
       if self.current_volume[well] + volume > self.capacities[well]:
           raise ValueError(f"Reservoir {well} overflow! Capacity: {self.capacities[well]} µl")
       self.current_volume[well] += volume


   def remove_volume(self, well: int, volume: float):
       """Remove liquid from a well if enough is available."""
       if self.current_volume[well]  < volume:
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




def pick_tip(p: Pipettor, pipette_tips):
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


def pick_next_tip(p: Pipettor, pipette_tips):
   """
   :param p: Pipettor, multichannel= False
   :param pipette_tips: location of tip box, PipetteTips class
   Picks up a tip going through whole box starting top left corner
   """
   for column in reversed(range(12)):
       tip_x = column * 9 + 6
       for row in range(8):
           tip_y = row * 9 + pipette_tips.y_corner
           print(f"Moving to tip {column}, {row}; position {tip_x}, {tip_y}")
           p.move_xy(tip_x, tip_y)
           try:
               p.pick_tip(75)
               print("Picked tip")
               return
           except CommandFailed:
               print("No tip found")
               pass
           finally:
               p.move_z(0)
   raise RuntimeError("No tips left")




def return_tip(p: Pipettor, pipette_tips):
   """
   Return Tips to tip box left to right
   :param p: Pipettor, multichannel = True
   :param pipette_tips:
   """
   p.move_xy(pipette_tips.x_corner, pipette_tips.y_corner)
   p.move_z(55)
   p.eject_tip()
   p.move_z(0)


def drop_tip(p: Pipettor, pipette_tips: PipetteTips):
   p.move_z(0)
   # p.move_xy(pipette_tips.drop_x, pipette_tips.drop_y)
   p.move_xy(pipette_tips.x_drop, pipette_tips.y_drop)
   p.eject_tip()


def home(p: Pipettor):
   p.move_z(0)
   p.move_xy(0, 0)
   print("Device in startup position")


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


def spit_all(p: Pipettor, height: float, volume: float = None, reservoirs: Reservoirs = None, well: int = None,
             use_surface_detection: bool = False, distance_from_surface: float = 2.0):
    """
    Dispenses (empties) all liquid currently inside the pipette, then returns to z=0 (safe height).

    CRITICAL: The pipette will NEVER go deeper than the specified height limit, regardless of
    surface detection results or distance_from_surface settings.

    :param p: Pipettor object
    :param height: MAXIMUM dispense depth - pipette will never exceed this (mm)
    :param volume: (optional) volume to record in reservoir tracking (µl)
    :param reservoirs: (optional) Reservoirs object to track liquid usage
    :param well: (optional) specific well index in the reservoir
    :param use_surface_detection: if True, uses move_to_surface instead of move_z
    :param distance_from_surface: distance to maintain above the detected surface (mm)
    """
    if reservoirs and well is not None and volume is not None:
        reservoirs.add_volume(well, volume)

    if use_surface_detection:
        try:
            print(f"Attempting surface detection with HARD LIMIT={height} mm, distance={distance_from_surface} mm")
            # move_to_surface with limit ensures pipette STOPS at height if surface not found
            p.move_to_surface(limit=height, distance_from_surface=distance_from_surface)
            current_z = p.z_position

            # SAFETY CHECK: Verify we didn't exceed the height limit
            if current_z > height:
                print(f"⚠️ WARNING: Position {current_z} mm exceeds limit {height} mm. Correcting to {height} mm")
                p.move_z(height)
                current_z = height

            print(f"✓ Surface detected at Z={current_z} mm (distance from surface: {distance_from_surface} mm)")
        except CommandFailed:
            print(f"⚠️ Surface detection failed. Using safe fallback height: {height} mm")
            p.move_z(height)
            print(f"Manual position set to Z={height} mm")
    else:
        p.move_z(height)
        print(f"Manual position set to Z={height} mm")

    p.dispense_all()
    p.move_z(0)


def spit(p: Pipettor, volume: float, height: float, reservoirs: Reservoirs = None, well: int = None,
         use_surface_detection: bool = False, distance_from_surface: float = 2.0):
    """
    Dispenses (spits out) a given volume and returns pipette to z=0 (safe height).

    CRITICAL: The pipette will NEVER go deeper than the specified height limit, regardless of
    surface detection results or distance_from_surface settings.

    :param p: Pipettor object
    :param volume: volume to dispense (µl)
    :param height: MAXIMUM dispense depth - pipette will never exceed this (mm)
    :param reservoirs: (optional) Reservoirs object to track liquid usage
    :param well: (optional) specific well index in the reservoir
    :param use_surface_detection: if True, uses move_to_surface instead of move_z
    :param distance_from_surface: distance to maintain above the detected surface (mm)
    """
    if reservoirs and well is not None:
        reservoirs.add_volume(well, volume)

    if use_surface_detection:
        try:
            print(f"Attempting surface detection with HARD LIMIT={height} mm, distance={distance_from_surface} mm")
            p.move_to_surface(limit=height, distance_from_surface=distance_from_surface)
            current_z = p.z_position

            # SAFETY CHECK: Verify we didn't exceed the height limit
            if current_z > height:
                print(f"⚠️ WARNING: Position {current_z} mm exceeds limit {height} mm. Correcting to {height} mm")
                p.move_z(height)
                current_z = height

            print(f"✓ Surface detected at Z={current_z} mm (distance from surface: {distance_from_surface} mm)")
        except CommandFailed:
            print(f"⚠️ Surface detection failed. Using safe fallback height: {height} mm")
            p.move_z(height)
            print(f"Manual position set to Z={height} mm")
    else:
        p.move_z(height)
        print(f"Manual position set to Z={height} mm")

    p.dispense(volume)
    p.move_z(0)


def suck(p: Pipettor, volume: float, height: float, reservoirs: Reservoirs = None, well: int = None,
         use_surface_detection: bool = False, distance_from_surface: float = 3.0):
    """
    Aspirates (sucks up) a given volume and returns pipette to z=0 (safe height).

    CRITICAL: The pipette will NEVER go deeper than the specified height limit, regardless of
    surface detection results or distance_from_surface settings.

    :param p: Pipettor object
    :param volume: volume to aspirate (µl)
    :param height: MAXIMUM aspiration depth - pipette will never exceed this (mm)
    :param reservoirs: (optional) Reservoirs object to track liquid usage
    :param well: (optional) specific well index in the reservoir
    :param use_surface_detection: if True, uses move_to_surface instead of move_z
    :param distance_from_surface: distance to maintain from the detected surface (mm).
                                   Positive value = above surface, Negative value = into liquid
                                   (default: 3.0 mm into liquid)
    """
    max_vol_per_go = 100
    total_steps_required = ceil(volume / max_vol_per_go)
    steps_done = 0

    if reservoirs and well is not None:
        reservoirs.remove_volume(well, volume)

    while steps_done < total_steps_required:

        if use_surface_detection:
            try:
                # For aspiration, typically want to go INTO the liquid (negative distance)
                print(f"Attempting surface detection with HARD LIMIT={height} mm, distance={-distance_from_surface} mm")
                p.move_to_surface(limit=height, distance_from_surface=-distance_from_surface)
                current_z = p.z_position

                # SAFETY CHECK: Verify we didn't exceed the height limit
                if current_z > height:
                    print(f"⚠️ WARNING: Position {current_z} mm exceeds limit {height} mm. Correcting to {height} mm")
                    p.move_z(height)
                    current_z = height

                print(f"✓ Surface detected at Z={current_z} mm (distance into liquid: {distance_from_surface} mm)")
            except CommandFailed:
                print(f"⚠️ Surface detection failed. Using safe fallback height: {height} mm")
                p.move_z(height)
                print(f"Manual position set to Z={height} mm")
        else:
            p.move_z(height)
            print(f"Manual position set to Z={height} mm")

        vol = min(max_vol_per_go, (volume - (steps_done * max_vol_per_go)))
        p.aspirate(vol)
        steps_done += 1

    p.move_z(0)


def fill_single(p: Pipettor, ehm_plate: EHMPlatePos, containers: Reservoirs, pipette_tips,
              volume: float, grid: Grid, stock_well: int = None, use_surface_detection: bool = True):
    """
    Using a single-channel pipette, fills a specified volume into the given positions of a plate.

    :param p: Pipettor object (single-channel pipette)
    :param ehm_plate: Plate position object with dimensions and coordinates
    :param containers: Reservoirs object that holds stock solutions
    :param pipette_tips: PipetteTips object (handles picking/dropping tips)
    :param grid: Grid object defining which positions should be filled
    :param volume: Volume to dispense per position (µl)
    :param stock_well: (optional) index of a specific stock well to aspirate from.
                       Supports equivalent wells in the same group.
    :param use_surface_detection: if True, uses surface detection for aspiration and dispensing
    """

    if pipette_tips.change_tips:
        pick_tip(p, pipette_tips)

    # --- Step 1: Iterate over each column and row that needs to be filled ---
    for row in range(grid.rows):
        for col in range(grid.cols):
            if grid.is_grid_position_active(col, row):
                max_vol_per_go = p.tip_volume
                volume_to_fill = volume
                # in case volume to pipette is more than capacity. like pipette 2ml by 1ml pipettor. loops over then.
                total_steps_required = ceil(volume / max_vol_per_go)
                steps_done = 0

                # --- Step 2: Loop until full volume for this position is dispensed ---
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
                            suck(p, vol, containers.remove_height, reservoirs=containers, well=candidate,
                                 use_surface_detection=use_surface_detection, distance_from_surface=2.0)
                            print(f"Aspirated {vol} µl from well {candidate}")
                            break
                        except ValueError as e:
                            print(f"⚠️ Well {candidate} failed: {e}")  # aspiration from the candidate is not possible.
                    else:
                        raise RuntimeError(f"No available equivalent wells for {stock_well}")

                    # --- Step 4: Move pipette to target position in the plate ---
                    x_pos = ehm_plate.x_corner + (col * ehm_plate.x_step)
                    y_pos = ehm_plate.y_corner + (row * ehm_plate.y_step)
                    print(f"Filling position ({col}, {row}) at x={x_pos} mm, y={y_pos} mm")
                    p.move_xy(x_pos, y_pos)

                    # --- Step 5: Dispense the aspirated volume using surface detection ---
                    spit_all(p, ehm_plate.add_height, vol, use_surface_detection=use_surface_detection, distance_from_surface=3.0)
                    volume_to_fill -= vol
                    steps_done += 1
                    p.move_z(0)

    if pipette_tips.change_tips:
        drop_tip(p, pipette_tips)


def remove_single(p: Pipettor, ehm_plate: EHMPlatePos, containers: Reservoirs, pipette_tips, grid: Grid,
                  volume: float, use_surface_detection: bool = True):
    """
    Removes medium from specified positions of a plate using a single-channel pipette.

    The removed liquid is transferred to designated waste wells. Works in multiple aspiration
    steps if the required volume exceeds pipette capacity.

    :param p: Pipettor object (single-channel pipette)
    :param ehm_plate: Plate position object with dimensions and coordinates
    :param containers: Reservoirs object (tracks volumes, waste wells, disabled wells)
    :param pipette_tips: PipetteTips object (handles tip usage)
    :param grid: Grid object defining which positions to remove liquid from
    :param volume: Volume to remove from each position (µl)
    :param use_surface_detection: if True, uses surface detection for aspiration and dispensing
    """

    # --- Step 1: Pick tips if needed ---
    if pipette_tips.change_tips:
        pick_tip(p, pipette_tips)

    # --- Step 2: Loop over all grid positions ---
    for row in range(grid.rows):
        for col in range(grid.cols):
            if grid.is_grid_position_active(col, row):

                max_vol_per_go = p.tip_volume
                # This is done in case pipette capacity is less than volume to remove
                total_steps_required = ceil(volume / max_vol_per_go)
                steps_done = 0

                # Calculate target position in the plate
                x_pos = ehm_plate.x_corner + (col * ehm_plate.x_step)
                y_pos = ehm_plate.y_corner + (row * ehm_plate.y_step)

                # --- Step 3: Loop until full volume is removed from this position ---
                while steps_done < total_steps_required:
                    # Move to the well position
                    p.move_z(0)
                    p.move_xy(x_pos, y_pos)
                    print(f"Moving to position ({col}, {row}) at x={x_pos} mm, y={y_pos} mm")

                    # Decide how much to aspirate this step (don't exceed pipette capacity)
                    vol = min(max_vol_per_go, (volume - (steps_done * max_vol_per_go)))
                    suck(p, vol, ehm_plate.remove_height,
                         use_surface_detection=use_surface_detection, distance_from_surface=2.0)

                    # --- Step 4: Transfer aspirated liquid to waste well (group 1) ---
                    for candidate in containers.get_equivalent_group(1):  # 1 = waste group
                        if candidate in containers.disabled_wells:
                            continue  # skip disabled wells
                        try:
                            p.move_xy(getattr(containers, f"well{candidate}_x"), containers.y_corner)
                            # Spit function includes checks if dispense is possible or not to prevent overflow
                            spit_all(p, containers.add_height, vol, reservoirs=containers, well=candidate,
                                 use_surface_detection=use_surface_detection, distance_from_surface=2.0)
                            print(f"Dispensed {vol} µl to waste well {candidate}")
                            break
                        except ValueError as e:
                            print(f"⚠️ Waste well {candidate} full: {e}")
                    else:
                        # If no waste wells are available → stop execution
                        raise RuntimeError("All waste wells are full. Empty before continuing.")

                    steps_done += 1

    # --- Step 5: Drop tips if needed ---
    if pipette_tips.change_tips:
        drop_tip(p, pipette_tips)