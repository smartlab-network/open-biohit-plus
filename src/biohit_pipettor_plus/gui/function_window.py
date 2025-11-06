import ttkbootstrap as ttk
import tkinter as tk
import uuid
from typing import Callable
from .well_window import WellWindow
from src.biohit_pipettor_plus.deck import Deck
from src.biohit_pipettor_plus.slot import Slot
from src.biohit_pipettor_plus.labware import Labware, PipetteHolder, Plate, TipDropzone, ReservoirHolder
from src.biohit_pipettor_plus.pipettor_plus import PipettorPlus

MULTI_CHANNEL_NUMBER = 6

class FunctionWindow:
    def __init__(self, deck: Deck, master: ttk.Window = None, pipettor: PipettorPlus = None):
        if isinstance(master, ttk.Window):
            self.window_build_func = ttk.Toplevel(master)

        else:
            self.window_build_func = ttk.Window(themename="solar")

        self.window_build_func.geometry("1400x800")

        self.deck = deck
        #self.pipettor = PipettorPlus(deck = self.deck, multichannel=False, tip_volume=200)

        """if self.pipettor.multichannel:
            self.channels = 8
        else: 
            self.channels = 1"""

        self.channels = 8

        self.set_grid_settings_func_win()
        self.create_window_build_func()

        self.custom_funcs_dict: dict[str, list[Callable]] = {}
        self.current_func_list: list[Callable] = []

        self.dict_top_labware = self.get_top_labwares()

    def get_top_labwares(self) -> dict[str, Labware]:
        """
        Return a dict with the Top Labware of each slot.
        Only the labware with the largest max_z is considered.

        Returns
        -------
        dict[str, Labware]
            {slot_id: oberste_Labware}
        """
        top_labwares = {}

        for slot_id, slot in self.deck.slots.items():
            if not slot.labware_stack:
                continue

            #find Labware with highest max_z
            top_lw_id, (top_lw, (min_z, max_z)) = max(
                slot.labware_stack.items(),
                key=lambda item: item[1][1][1]
            )

            top_labwares[slot_id] = top_lw
        return top_labwares

    def create_window_build_func(self):
        """
        This method fills the TopLevel window self.window_build_func with the given commands.
        And has the logic to build custom functions chains on the Pipettor.
        """

        self.label_header = ttk.Label(self.window_build_func, text="Functions to choose", anchor="center", font=('Helvetica', 18))
        self.label_header.grid(row = 0, column = 0, sticky="nsew")

        # Frame, name Entry and safe Button
        self.frame_name = ttk.Frame(self.window_build_func)
        self.frame_name.grid(row = 11, column = 2, sticky="nsew")

        self.frame_name.columnconfigure(0, weight=1)
        self.frame_name.columnconfigure(1, weight=1)
        self.frame_name.columnconfigure(2, weight=1)
        self.frame_name.rowconfigure(0, weight=1)

        self.entry_name = ttk.Entry(self.frame_name, text = "name")
        self.entry_name.grid(sticky="nsew", row = 0, column = 0, columnspan=2)

        self.safe_button = ttk.Button(self.frame_name, text="Save", command=self.callback_save_button)
        self.safe_button.grid(row = 0, column=2, sticky="nsew")
        #
        self.second_column_frame = ttk.Frame(self.window_build_func)
        self.second_column_frame.grid(row = 1, column=1, sticky="nsew", rowspan=10)

        self.second_column_frame.columnconfigure(0, weight = 1)
        for i in range(10):
            self.second_column_frame.rowconfigure(i, weight=1)
        #
        self.third_column_frame = ttk.Frame(self.window_build_func)
        self.third_column_frame.grid(row = 1, column=2, rowspan=9, sticky="nsew")
        self.third_column_frame.columnconfigure(0, weight=1)
        for i in range(20):
            self.third_column_frame.rowconfigure(i, weight=1)
        #
        self.place_buttons()

    def place_buttons(self):
        """
        Places the buttons on the TopLevel window
        """
        self.button_pick_tips = ttk.Button(self.window_build_func, text="Pick Tips",
                                           command=lambda: self.callback_pick_tips(func_str = "pick_tips"))
        self.button_pick_tips.grid(row=1, column=0, sticky="nsew", pady = 2, padx  = 5)

        self.button_return_tips = ttk.Button(self.window_build_func, text="Return Tips",
                                             command=lambda: self.callback_return_tips(func_str = "return_tips"))
        self.button_return_tips.grid(row=2, column=0, sticky="nsew", pady = 2, padx  = 5)

        self.button_replace_tip = ttk.Button(self.window_build_func, text="Replace Tip",
                                             command=lambda: self.callback_replace_tips(func_str = "replace_tip"))
        self.button_replace_tip.grid(row=3, column=0, sticky="nsew", pady = 2, padx  = 5)

        self.button_discard_tips = ttk.Button(self.window_build_func, text="Discard Tips",
                                              command=lambda: self.callback_discard_tips(func_str = "discard_tips"))
        self.button_discard_tips.grid(row=4, column=0, sticky="nsew", pady = 2, padx  = 5)

        self.button_add_medium = ttk.Button(self.window_build_func, text="Add Medium",
                                            command=lambda: self.callback_add_medium(func_str = "add_medium"))
        self.button_add_medium.grid(row=5, column=0, sticky="nsew", pady = 2, padx  = 5)

        self.button_remove_medium = ttk.Button(self.window_build_func, text="Remove Medium",
                                               command=lambda: self.callback_remove_medium(func_str = "remove_medium"))
        self.button_remove_medium.grid(row=6, column=0, sticky="nsew", pady = 2, padx  = 5)

        self.button_transfer_plate_to_plate = ttk.Button(self.window_build_func, text="Transfer Plate to  Plate",
                                                         command=lambda: self.callback_transfer_plate_to_plate(func_str = "transfer_plate_to_plate"))
        self.button_transfer_plate_to_plate.grid(row=7, column=0, sticky="nsew", pady = 2, padx  = 5)

        self.button_home = ttk.Button(self.window_build_func, text="Home",
                                      command=lambda: self.callback_home(func_str = "home"))
        self.button_home.grid(row=8, column=0, sticky="nsew", pady = 2, padx  = 5)

        self.button_suck = ttk.Button(self.window_build_func, text="Suck",
                                      command=lambda: self.callback_suck(func_str = "suck"))
        self.button_suck.grid(row=9, column=0, sticky="nsew", pady = 2, padx  = 5)

        self.button_spit = ttk.Button(self.window_build_func, text="spit",
                                      command=lambda: self.callback_spit(func_str = "spit"))
        self.button_spit.grid(row=10, column=0, sticky="nsew", pady = 2, padx  = 5)

        self.button_spit_all = ttk.Button(self.window_build_func, text="spit all",
                                          command=lambda: self.callback_spit_all(func_str = "spit_all"))
        self.button_spit_all.grid(row=11, column=0, sticky="nsew", pady=2, padx=5)

    def set_grid_settings_func_win(self):
        self.window_build_func.columnconfigure(0, weight=1)
        self.window_build_func.columnconfigure(1, weight=1)
        self.window_build_func.columnconfigure(2, weight=1)
        for i in range(12):
            self.window_build_func.rowconfigure(i, weight=1)


    def callback_save_button(self):
        name = self.entry_name.get()
        if not name:
            name = uuid.uuid4()

        i = 1
        while name in self.custom_funcs_dict.keys():
            i += 1
            name = f"{name}_{i}"

        self.custom_funcs_dict[name] = self.current_func_list
        self.current_func_list = []
        self.third_column_frame.grid_remove()
        print(self.custom_funcs_dict)

    def display_possible_labware(self, labware_type, next_callback, func_str, part="first", start_row=0, **kwargs):
        """Display selectable labware of a given type and call `next_callback` with selected labware."""
        for slot_id, labware in self.dict_top_labware.items():
            if not isinstance(labware, labware_type):
                continue

            label = ttk.Label(self.second_column_frame, text=slot_id)
            label.grid(column=0, row=start_row, sticky="nsew", pady=5, padx=5)
            start_row += 1

            button = ttk.Button(
                self.second_column_frame,
                text=labware.labware_id,
                bootstyle="warning",
                command=lambda lw=labware: next_callback(
                    func_str=func_str,
                    part=part,
                    labware_obj=lw,
                    **kwargs
                )
            )
            button.grid(column=0, row=start_row, sticky="nsew", pady=5, padx=5)
            start_row += 1

    def add_current_function(self, func: Callable, func_str: str, labware_id: str):
        self.current_func_list.append(func)

        label_func = ttk.Label(self.third_column_frame, text=f"{func_str}: {labware_id}", font=("Helvetica", 16), anchor="center")
        label_func.grid(row=len(self.current_func_list) - 1, column=0, sticky="nsew")

        self.clear_grid(self.second_column_frame)

    def clear_grid(self, frame: ttk.Frame):
        for widget in frame.grid_slaves():
            widget.destroy()

    """
    callback functions for buttons
    """

    def callback_pick_tips(self, func_str: str, part: str = "first", labware_obj: PipetteHolder = None, **kwargs):
        """
        Handle the 'Pick Tips' process.

        Parameters
        ----------
        func_str : str
            The string identifier of the function.
        part : str, optional
            Which part of the callback is currently active ("first", "second").
        labware_obj : PipetteHolder, optional
            The selected PipetteHolder object.
        **kwargs : dict
            Additional context information passed between recursive callback calls.
        """
        if part == "first":
            self.clear_grid(self.second_column_frame)
            self.display_possible_labware(
                labware_type=PipetteHolder,
                next_callback=self.callback_pick_tips,
                func_str=func_str,
                part="second",
                **kwargs
            )

        elif part == "second" and labware_obj is not None:
            window = WellWindow(
                rows=labware_obj.holders_across_y,
                columns=labware_obj.holders_across_x,
                labware_id=labware_obj.labware_id,
                max_selected = self.channels,
                master=self.window_build_func,
                title=f"Pick tips from: {labware_obj.labware_id}",
                wells_list=self.get_wells_list_from_labware(labware_obj=labware_obj, source=True)
            )
            self.window_build_func.wait_variable(window.safe_var)
            list_return = [(r, c) for r, row in enumerate(window.well_state) for c, active in enumerate(row) if active]
            del window

            func = lambda lw=labware_obj, lr=list_return: self.pipettor.pick_tips(pipette_holder=lw, list_col_row=lr)
            self.add_current_function(func_str=func_str, func=func, labware_id=labware_obj.labware_id)

    def callback_return_tips(self, func_str: str, part: str = "first", labware_obj: PipetteHolder = None, **kwargs):
        """
        Handle the 'Return Tips' process.

        Parameters
        ----------
        func_str : str
        part : str
        labware_obj : PipetteHolder
        **kwargs : dict
        """
        if part == "first":
            self.clear_grid(self.second_column_frame)
            self.display_possible_labware(
                labware_type=PipetteHolder,
                next_callback=self.callback_return_tips,
                func_str=func_str,
                part="second",
                **kwargs
            )
        elif part == "second" and labware_obj is not None:

            window = WellWindow(
                rows=labware_obj.holders_across_y,
                columns=labware_obj.holders_across_x,
                labware_id=labware_obj.labware_id,
                max_selected=self.channels,
                master=self.window_build_func,
                title=f"Return tips to: {labware_obj.labware_id}",
                wells_list=self.get_wells_list_from_labware(labware_obj=labware_obj)
            )
            self.window_build_func.wait_variable(window.safe_var)
            list_return = [(r, c) for r, row in enumerate(window.well_state) for c, active in enumerate(row) if active]
            del window

            #func = lambda lw=labware_obj, lr=list_return: self.pipettor.return_tips(labware_obj=lw, list_return=lr)
            func = lambda: print(2)
            self.add_current_function(func_str=func_str, func=func, labware_id=labware_obj.labware_id)

    def callback_replace_tips(self, func_str: str, part: str = "first", labware_obj: PipetteHolder = None, **kwargs):
        """
        Handle 'Replace Tips' process.

        Requires selection of both pick and return wells.

        Parameters
        ----------
        func_str : str
        part : str
        labware_obj : PipetteHolder
        **kwargs : dict
        """
        if part == "first":
            self.clear_grid(self.second_column_frame)
            self.display_possible_labware(
                labware_type=PipetteHolder,
                next_callback=self.callback_replace_tips,
                func_str=func_str,
                part="second",
                **kwargs
            )
        elif part == "second" and labware_obj is not None:
            window = WellWindow(
                rows=labware_obj.holders_across_y,
                columns=labware_obj.holders_across_x,
                labware_id=labware_obj.labware_id,
                max_selected=self.channels,
                master=self.window_build_func,
                title=f"Return tips to: {labware_obj.labware_id}",
                wells_list=self.get_wells_list_from_labware(labware_obj=labware_obj, soruce=False)
            )
            self.window_build_func.wait_variable(window.safe_var)
            list_return = [(r, c) for r, row in enumerate(window.well_state) for c, active in enumerate(row) if active]
            del window

            # Return wells
            window = WellWindow(
                rows=labware_obj.holders_across_y,
                columns=labware_obj.holders_across_x,
                labware_id=labware_obj.labware_id,
                max_selected=self.channels,
                master=self.window_build_func,
                title=f"Pick tips from: {labware_obj.labware_id}",
                wells_list=self.get_wells_list_from_labware(labware_obj=labware_obj, soruce=True)
            )
            self.window_build_func.wait_variable(window.safe_var)
            list_pick = [(r, c) for r, row in enumerate(window.well_state) for c, active in enumerate(row) if active]
            del window

            """func = lambda lw=labware_obj, lr=list_return, lp=list_pick: self.pipettor.replace_tips(
                labware_obj=lw, return_list_col_row=lr, pick_list_col_row=lp
            )"""
            func = lambda: print(2)
            self.add_current_function(func_str=func_str, func=func, labware_id=labware_obj.labware_id)

    def callback_discard_tips(self, func_str: str, part: str = "first", labware_obj: TipDropzone = None, **kwargs):
        """
        Handle 'Discard Tips' process.

        Parameters
        ----------
        func_str : str
        part : str
        labware_obj : TipDropzone
        **kwargs : dict
        """
        if part == "first":
            self.clear_grid(self.second_column_frame)
            self.display_possible_labware(
                labware_type=TipDropzone,
                next_callback=self.callback_discard_tips,
                func_str=func_str,
                part="second",
                **kwargs
            )
        elif part == "second" and labware_obj is not None:
            """func = lambda lw=labware_obj: print(
                f"Discarding tips into {lw.labware_id}")  # replace with self.pipettor method"""
            func = lambda: print(2)
            self.add_current_function(func_str=func_str, func=func, labware_id=labware_obj.labware_id)

    def callback_add_medium(self, func_str: str, part: str = "first", labware_obj: ReservoirHolder or Plate = None,
                            **kwargs):
        """
        Handle 'Add Medium' process: select source reservoir, destination plate, and wells.

        Parameters
        ----------
        func_str : str
        part : str
        labware_obj : ReservoirHolder or Plate
        **kwargs : dict
        """
        if part == "first":
            self.clear_grid(self.second_column_frame)
            self.display_possible_labware(
                labware_type=ReservoirHolder,
                next_callback=self.callback_add_medium,
                func_str=func_str,
                part="second",
                **kwargs
            )
        elif part == "second" and labware_obj is not None:

            window = WellWindow(
                rows=labware_obj.hooks_across_y,
                columns=labware_obj.hooks_across_x,
                labware_id=labware_obj.labware_id,
                master=self.window_build_func,
                title=f"Choose source wells: {labware_obj.labware_id}",
                wells_list=self.get_wells_list_from_labware(labware_obj=labware_obj, source=True)
            )


            self.window_build_func.wait_variable(window.safe_var)


            kwargs["source_labware"] = labware_obj
            kwargs["source_positions"] = [
                (r, c)
                for r, row in enumerate(window.well_state)
                for c, v in enumerate(row)
                if v
            ]
            del window

            self.clear_grid(self.second_column_frame)
            self.display_possible_labware(
                labware_type=Plate,
                next_callback=self.callback_add_medium,
                func_str=func_str,
                part="third",
                **kwargs
            )
        elif part == "third" and labware_obj is not None:
            # Pick destination wells and volume
            window = WellWindow(
                rows=labware_obj._rows,
                columns=labware_obj._columns,
                labware_id=labware_obj.labware_id,
                max_selected=self.channels,
                master=self.window_build_func,
                title=f"Choose destination wells: {labware_obj.labware_id}",
                wells_list=self.get_wells_list_from_labware(labware_obj=labware_obj, soruce=False)
            )
            self.window_build_func.wait_variable(window.safe_var)
            kwargs["dest_labware"] = labware_obj
            kwargs["dest_positions"] = [(r, c) for r, row in enumerate(window.well_state) for c, v in enumerate(row) if
                                        v]
            del window

            self.clear_grid(self.second_column_frame)
            # volume entry
            label = ttk.Label(self.second_column_frame, text="Enter Volume per Well")
            label.grid(column=0, row=0, sticky="nsew", pady=5, padx=5)
            text_var = ttk.StringVar(value="5")
            entry = ttk.Entry(self.second_column_frame, textvariable=text_var)
            entry.grid(row=1, column=0, sticky="nsew", pady=5, padx=5)

            def callback_enter_button():
                try:
                    volume = float(text_var.get())
                except ValueError:
                    return

                """func = lambda kwargs=kwargs, vol=volume: self.pipettor.add_medium(
                    source=kwargs["source_labware"],
                    source_col_row=kwargs["source_positions"],
                    destination=kwargs["dest_labware"],
                    dest_col_row=kwargs["dest_positions"]
                )"""
                func = lambda: print(2)

                self.add_current_function(func_str=func_str, func=func, labware_id=kwargs["dest_labware"].labware_id)
                self.clear_grid(self.second_column_frame)

            button = ttk.Button(self.second_column_frame, text="Enter", command=callback_enter_button)
            button.grid(row=2, column=0, sticky="nsew", pady=5, padx=5)

    def callback_remove_medium(self, func_str: str, part: str = "first", labware_obj: Plate = None, **kwargs):
        """
        Handle 'Remove Medium' process: select source plate, destination reservoir, wells, and volume.

        Parameters
        ----------
        func_str : str
        part : str
        labware_obj : Plate
        **kwargs : dict
        """
        if part == "first":
            self.clear_grid(self.second_column_frame)
            self.display_possible_labware(
                labware_type=Plate,
                next_callback=self.callback_remove_medium,
                func_str=func_str,
                part="second",
                **kwargs
            )
        elif part == "second" and labware_obj is not None:
            window = WellWindow(
                rows=labware_obj._rows,
                columns=labware_obj._columns,
                labware_id=labware_obj.labware_id,
                max_selected=self.channels,
                master=self.window_build_func,
                title=f"Select source wells: {labware_obj.labware_id}",
                wells_list=self.get_wells_list_from_labware(labware_obj=labware_obj, soruce=True)
            )
            self.window_build_func.wait_variable(window.safe_var)
            kwargs["source_labware"] = labware_obj
            kwargs["source_positions"] = [(r, c) for r, row in enumerate(window.well_state) for c, v in enumerate(row)
                                          if v]
            del window

            self.clear_grid(self.second_column_frame)
            self.display_possible_labware(
                labware_type=ReservoirHolder,
                next_callback=self.callback_remove_medium,
                func_str=func_str,
                part="third",
                **kwargs
            )
        elif part == "third" and labware_obj is not None:
            window = WellWindow(
                rows=labware_obj.hooks_across_y,
                columns=labware_obj.hooks_across_x,
                labware_id=labware_obj.labware_id,
                max_selected=self.channels,
                master=self.window_build_func,
                title=f"Select destination Reservoir: {labware_obj.labware_id}",
                wells_list=self.get_wells_list_from_labware(labware_obj=labware_obj)
            )
            self.window_build_func.wait_variable(window.safe_var)
            kwargs["dest_labware"] = labware_obj
            kwargs["dest_positions"] = [(r, c) for r, row in enumerate(window.well_state) for c, v in enumerate(row) if
                                        v]
            del window

            self.clear_grid(self.second_column_frame)
            label = ttk.Label(self.second_column_frame, text="Enter Volume per Well")
            label.grid(column=0, row=0, sticky="nsew", pady=5, padx=5)
            text_var = ttk.StringVar(value="5")
            entry = ttk.Entry(self.second_column_frame, textvariable=text_var)
            entry.grid(row=1, column=0, sticky="nsew", pady=5, padx=5)

            def callback_enter_button():
                try:
                    volume = float(text_var.get())
                except ValueError:
                    return
                """func = lambda kwargs=kwargs, vol=volume: self.pipettor.remove_medium(
                    source=kwargs["source_labware"],
                    destination=kwargs["dest_labware"],
                    source_col_row=kwargs["source_positions"],
                    destination_col_row=kwargs["dest_positions"],
                    volume_per_well=vol
                )"""
                func = lambda: print(2)
                self.add_current_function(func_str=func_str, func=func, labware_id=kwargs["dest_labware"].labware_id)
                self.clear_grid(self.second_column_frame)

            button = ttk.Button(self.second_column_frame, text="Enter", command=callback_enter_button)
            button.grid(row=2, column=0, sticky="nsew", pady=5, padx=5)

    def callback_transfer_plate_to_plate(self, func_str: str, part: str = "first", labware_obj: Plate = None, **kwargs):
        """
        Handle 'Transfer Plate to Plate': select source plate, destination plate, wells, and volume.

        Parameters
        ----------
        func_str : str
        part : str
        labware_obj : Plate
        **kwargs : dict
        """
        if part == "first":
            self.clear_grid(self.second_column_frame)
            self.display_possible_labware(
                labware_type=Plate,
                next_callback=self.callback_transfer_plate_to_plate,
                func_str=func_str,
                part="second",
                **kwargs
            )
        elif part == "second" and labware_obj is not None:
            window = WellWindow(
                rows=labware_obj._rows,
                columns=labware_obj._columns,
                labware_id=labware_obj.labware_id,
                max_selected=self.channels,
                master=self.window_build_func,
                title=f"Select source wells: {labware_obj.labware_id}",
                wells_list=self.get_wells_list_from_labware(labware_obj=labware_obj, soruce=True)
            )
            self.window_build_func.wait_variable(window.safe_var)
            kwargs["source_labware"] = labware_obj
            kwargs["source_positions"] = [(r, c) for r, row in enumerate(window.well_state) for c, v in enumerate(row)
                                          if v]
            del window

            self.clear_grid(self.second_column_frame)
            self.display_possible_labware(
                labware_type=Plate,
                next_callback=self.callback_transfer_plate_to_plate,
                func_str=func_str,
                part="third",
                **kwargs
            )
        elif part == "third" and labware_obj is not None:
            window = WellWindow(
                rows=labware_obj._rows,
                columns=labware_obj._columns,
                labware_id=labware_obj.labware_id,
                max_selected=self.channels,
                master=self.window_build_func,
                title=f"Select destination wells: {labware_obj.labware_id}",
                wells_list=self.get_wells_list_from_labware(labware_obj=labware_obj)
            )
            self.window_build_func.wait_variable(window.safe_var)
            kwargs["dest_labware"] = labware_obj
            kwargs["dest_positions"] = [(r, c) for r, row in enumerate(window.well_state) for c, v in enumerate(row) if
                                        v]
            del window

            self.clear_grid(self.second_column_frame)
            label = ttk.Label(self.second_column_frame, text="Enter Volume per Well")
            label.grid(column=0, row=0, sticky="nsew", pady=5, padx=5)
            text_var = ttk.StringVar(value="5")
            entry = ttk.Entry(self.second_column_frame, textvariable=text_var)
            entry.grid(row=1, column=0, sticky="nsew", pady=5, padx=5)

            def callback_enter_button():
                try:
                    volume = float(text_var.get())
                except ValueError:
                    return
                """func = lambda kwargs=kwargs, vol=volume: self.pipettor.transfer_plate_to_plate(
                    source=kwargs["source_labware"],
                    source_col_row=kwargs["source_positions"],
                    destination=kwargs["dest_labware"],
                    dest_col_row=kwargs["dest_positions"],
                    volume_per_well=vol
                )"""
                func = lambda: print(2)
                self.add_current_function(func_str=func_str, func=func, labware_id=kwargs["dest_labware"].labware_id)
                self.clear_grid(self.second_column_frame)

            button = ttk.Button(self.second_column_frame, text="Enter", command=callback_enter_button)
            button.grid(row=2, column=0, sticky="nsew", pady=5, padx=5)

    def callback_suck(self, func_str: str, part: str = "first", labware_obj: Labware = None, **kwargs):
        """
        Handle pipettor 'suck' operation: select labware wells and volume.

        Parameters
        ----------
        func_str : str
        part : str
        labware_obj : Labware
        **kwargs : dict
        """
        if part == "first":
            self.clear_grid(self.second_column_frame)
            self.display_possible_labware(
                labware_type=Labware,
                next_callback=self.callback_suck,
                func_str=func_str,
                part="second",
                **kwargs
            )
        elif part == "second" and labware_obj is not None:
            # Determine rows/columns based on labware type
            if isinstance(labware_obj, ReservoirHolder):
                rows, columns = labware_obj.hooks_across_y, labware_obj.hooks_across_x
            elif isinstance(labware_obj, PipetteHolder):
                rows, columns = labware_obj.holders_across_y, labware_obj.holders_across_x
            elif isinstance(labware_obj, Plate):
                rows, columns = labware_obj._rows, labware_obj._columns
            else:
                return

            window = WellWindow(
                rows=rows,
                columns=columns,
                labware_id=labware_obj.labware_id,
                max_selected=self.channels,
                master=self.window_build_func,
                title=f"Select wells to suck from: {labware_obj.labware_id}",
                wells_list=self.get_wells_list_from_labware(labware_obj=labware_obj, soruce=True)
            )
            self.window_build_func.wait_variable(window.safe_var)
            kwargs["labware_obj"] = labware_obj
            kwargs["positions"] = [(r, c) for r, row in enumerate(window.well_state) for c, v in enumerate(row) if v]
            del window

            self.clear_grid(self.second_column_frame)
            label = ttk.Label(self.second_column_frame, text="Enter Volume per Well")
            label.grid(column=0, row=0, sticky="nsew", pady=5, padx=5)
            text_var = ttk.StringVar(value="5")
            entry = ttk.Entry(self.second_column_frame, textvariable=text_var)
            entry.grid(row=1, column=0, sticky="nsew", pady=5, padx=5)

            def callback_enter_button():
                try:
                    volume = float(text_var.get())
                except ValueError:
                    return
                """func = lambda kwargs=kwargs, vol=volume: self.pipettor.suck(
                    source=kwargs["labware_obj"],
                    source_col_row=kwargs["positions"],
                    volume=vol
                )"""
                func = lambda: print(2)
                self.add_current_function(func_str=func_str, func=func, labware_id=kwargs["labware_obj"].labware_id)
                self.clear_grid(self.second_column_frame)

            button = ttk.Button(self.second_column_frame, text="Enter", command=callback_enter_button)
            button.grid(row=2, column=0, sticky="nsew", pady=5, padx=5)

    def callback_spit(self, func_str: str, part: str = "first", labware_obj: Labware = None, **kwargs):
        """
        Handle pipettor 'spit' operation: select labware wells and volume.

        Parameters
        ----------
        func_str : str
        part : str
        labware_obj : Labware
        **kwargs : dict
        """
        if part == "first":
            self.clear_grid(self.second_column_frame)
            self.display_possible_labware(
                labware_type=Labware,
                next_callback=self.callback_spit,
                func_str=func_str,
                part="second",
                **kwargs
            )
        elif part == "second" and labware_obj is not None:
            # Determine rows/columns based on labware type
            if isinstance(labware_obj, ReservoirHolder):
                rows, columns = labware_obj.hooks_across_y, labware_obj.hooks_across_x
            elif isinstance(labware_obj, PipetteHolder):
                rows, columns = labware_obj.holders_across_y, labware_obj.holders_across_x
            elif isinstance(labware_obj, Plate):
                rows, columns = labware_obj._rows, labware_obj._columns
            else:
                return

            window = WellWindow(
                rows=rows,
                columns=columns,
                max_selected = self.channels,
                labware_id=labware_obj.labware_id,
                master=self.window_build_func,
                title=f"Select wells to spit into: {labware_obj.labware_id}",
                wells_list=self.get_wells_list_from_labware(labware_obj=labware_obj)
            )
            self.window_build_func.wait_variable(window.safe_var)
            kwargs["labware_obj"] = labware_obj
            kwargs["positions"] = [(r, c) for r, row in enumerate(window.well_state) for c, v in enumerate(row) if v]
            del window

            self.clear_grid(self.second_column_frame)
            label = ttk.Label(self.second_column_frame, text="Enter Volume per Well")
            label.grid(column=0, row=0, sticky="nsew", pady=5, padx=5)
            text_var = ttk.StringVar(value="5")
            entry = ttk.Entry(self.second_column_frame, textvariable=text_var)
            entry.grid(row=1, column=0, sticky="nsew", pady=5, padx=5)

            def callback_enter_button():
                try:
                    volume = float(text_var.get())
                except ValueError:
                    return
                """func = lambda kwargs=kwargs, vol=volume: self.pipettor.spit(
                    destination=kwargs["labware_obj"],
                    dest_col_row=kwargs["positions"],
                    volume=vol
                )"""
                func = lambda: print(2)
                self.add_current_function(func_str=func_str, func=func, labware_id=kwargs["labware_obj"].labware_id)
                self.clear_grid(self.second_column_frame)

            button = ttk.Button(self.second_column_frame, text="Enter", command=callback_enter_button)
            button.grid(row=2, column=0, sticky="nsew", pady=5, padx=5)

    def callback_spit_all(self, func_str: str, part: str = "first", labware_obj: Labware = None, **kwargs):
        """
        Handle pipettor 'spit all' operation: select labware wells.

        Parameters
        ----------
        func_str : str
        part : str
        labware_obj : Labware
        **kwargs : dict
        """
        if part == "first":
            self.clear_grid(self.second_column_frame)
            self.display_possible_labware(
                labware_type=Labware,
                next_callback=self.callback_spit_all,
                func_str=func_str,
                part="second",
                **kwargs
            )
        elif part == "second" and labware_obj is not None:
            if isinstance(labware_obj, ReservoirHolder):
                rows, columns = labware_obj.hooks_across_y, labware_obj.hooks_across_x
            elif isinstance(labware_obj, PipetteHolder):
                rows, columns = labware_obj.holders_across_y, labware_obj.holders_across_x
            elif isinstance(labware_obj, Plate):
                rows, columns = labware_obj._rows, labware_obj._columns
            else:
                return

            window = WellWindow(
                rows=rows,
                columns=columns,
                labware_id=labware_obj.labware_id,
                max_selected=self.channels,
                master=self.window_build_func,
                title=f"Select wells to spit all into: {labware_obj.labware_id}",
                wells_list=self.get_wells_list_from_labware(labware_obj=labware_obj)
            )
            self.window_build_func.wait_variable(window.safe_var)
            kwargs["labware_obj"] = labware_obj
            kwargs["positions"] = [(r, c) for r, row in enumerate(window.well_state) for c, v in enumerate(row) if v]
            del window

            """func = lambda kwargs=kwargs: self.pipettor.spit_all(
                destination=kwargs["labware_obj"],
                dest_col_row=kwargs["positions"]
            )"""
            func = lambda: print(2)
            self.add_current_function(func_str=func_str, func=func, labware_id=kwargs["labware_obj"].labware_id)
            self.clear_grid(self.second_column_frame)

    def get_wells_list_from_labware(self, labware_obj, source: bool = False)-> list[tuple[int,int]]:
        """
        Liefert wells_list passend zum Labware-Typ.

        - Für Plate: wie bisher (Medium vorhanden oder leer)
        - Für ReservoirHolder: nur Reservoirs mit Inhalt (source=True) oder Platz (source=False)
        - Für PipetteHolder: belegt oder frei
        """

        # Plate
        if isinstance(labware_obj, Plate):
            rows, columns = labware_obj._rows, labware_obj._columns
            wells_list = [(r, c) for r in range(rows) for c in range(columns)]

            if source:
                wells_list = [
                    (r, c)
                    for (r, c) in wells_list
                    if hasattr(labware_obj, "medium_state")
                       and labware_obj.medium_state[r][c]
                ]

        # ReservoirHolder
        elif isinstance(labware_obj, ReservoirHolder):
            rows, columns = labware_obj.hooks_across_y, labware_obj.hooks_across_x
            wells_list = []

            for res in labware_obj.get_reservoirs():
                if res is None:
                    continue

                # Quelle: Reservoir mit Inhalt
                if source and res.get_total_volume() > 0:
                    wells_list.append((res.row, res.column))

                # Ziel: Reservoir mit Platz
                elif not source and res.get_available_volume() > 0:
                    wells_list.append((res.row, res.column))

        #  PipetteHolder
        elif isinstance(labware_obj, PipetteHolder):
            rows, columns = labware_obj.holders_across_y, labware_obj.holders_across_x

            if source:
                wells_list = [
                    (holder.row, holder.column)
                    for holder in labware_obj.get_occupied_holders()
                    if holder.is_occupied
                ]
            else:
                wells_list = [
                    (holder.row, holder.column)
                    for holder in labware_obj.get_available_holders()
                    if holder.is_available()
                ]

        else:
            raise TypeError(f"Unsupported labware type: {type(labware_obj)}")

        return wells_list

    def callback_home(self, func_str: str):
        """Send pipettor to home position."""
        self.clear_grid(self.second_column_frame)
        #func = lambda: self.pipettor.home()
        func = lambda: print(2)
        self.add_current_function(
            func_str=func_str,
            func=func,
            labware_id="Home"
        )