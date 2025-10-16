    """
    Classes and functions to be used with biohit_pipettor
    p = Pipettor() in all cases
    """

    import time
    from typing import List
    from ..biohit_pipettor import Pipettor
    from ..biohit_pipettor.errors import CommandFailed
    from math import ceil
    from .labware import PipetteHolder, Plate, Well, ReservoirHolder, Reservoir, Pipettors_in_Multi

    from src.tests.test1 import pipette_holder
    def pick_multi_tips(p: Pipettor, pipetteHolder):
        """
        Picks tips going through PipetteHolder right to left
        :param p: Pipettor, multichannel = True
        :param PipetteHolder:


        #todo nothing like this exisit
        p.move_xy(pipette_tips.x_corner_multi, pipette_tips.y_corner_multi)
                p.pick_tip(pipette_tips.pick_height)
                print("Picked up pipette tip")
                print(f"Found no tips, moving on to x {pipette_tips.x_corner - i * 9}")
                p.move_x(pipette_tips.x_corner_multi - i * 9)
            """
        print("pick_multi_tips: start")
        cols = pipetteHolder.get_occupied_columns()
        for col in cols:
            p.move_xy()
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
    #        initial_vol remains unchanged
        return prep_table




