import ttkbootstrap as ttk
import tkinter as tk
import uuid
from typing import Callable
from .well_window import WellWindow
from src.biohit_pipettor_plus.deck import Deck
from src.biohit_pipettor_plus.slot import Slot
from src.biohit_pipettor_plus.labware import Labware, PipetteHolder, Plate, TipDropzone, ReservoirHolder
from src.biohit_pipettor_plus.pipettor_plus import PipettorPlus

class Gui:
    def __init__(self, deck: Deck, master: ttk.Window = None):
        if isinstance(master, ttk.Window):
            self.root = ttk.Toplevel(master)
        else:
            self.root = ttk.Window(themename="solar")
            self.root.geometry("1400x800")

        self.deck = deck
        #TODO review self.pipettor
        self.pipettor = PipettorPlus(deck = self.deck, multichannel=False, tip_volume=200)

        #window for creating custom functions
        #self.window_build_func = ttk.Toplevel(self.root)
        self.window_build_func = self.root
        self.window_build_func.geometry("1400x800")
        self.set_grid_settings_func_win()
        self.create_window_build_func()
        #self.window_build_func.withdraw()

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
                                           command=lambda: self.callback_button_func_win("pick_tips"))
        self.button_pick_tips.grid(row=1, column=0, sticky="nsew", pady = 2, padx  = 5)

        self.button_return_tips = ttk.Button(self.window_build_func, text="Return Tips",
                                             command=lambda: self.callback_button_func_win("return_tips"))
        self.button_return_tips.grid(row=2, column=0, sticky="nsew", pady = 2, padx  = 5)

        self.button_replace_tip = ttk.Button(self.window_build_func, text="Replace Tip",
                                             command=lambda: self.callback_button_func_win("replace_tip"))
        self.button_replace_tip.grid(row=3, column=0, sticky="nsew", pady = 2, padx  = 5)

        self.button_discard_tips = ttk.Button(self.window_build_func, text="Discard Tips",
                                              command=lambda: self.callback_button_func_win("discard_tips"))
        self.button_discard_tips.grid(row=4, column=0, sticky="nsew", pady = 2, padx  = 5)

        self.button_add_medium = ttk.Button(self.window_build_func, text="Add Medium",
                                            command=lambda: self.callback_button_func_win("add_medium"))
        self.button_add_medium.grid(row=5, column=0, sticky="nsew", pady = 2, padx  = 5)

        self.button_remove_medium = ttk.Button(self.window_build_func, text="Remove Medium",
                                               command=lambda: self.callback_button_func_win("remove_medium"))
        self.button_remove_medium.grid(row=6, column=0, sticky="nsew", pady = 2, padx  = 5)

        self.button_transfer_plate_to_plate = ttk.Button(self.window_build_func, text="Transfer Plate to  Plate",
                                                         command=lambda: self.callback_button_func_win("transfer_plate_to_plate"))
        self.button_transfer_plate_to_plate.grid(row=7, column=0, sticky="nsew", pady = 2, padx  = 5)

        self.button_home = ttk.Button(self.window_build_func, text="Home",
                                      command=lambda: self.callback_button_func_win("home"))
        self.button_home.grid(row=8, column=0, sticky="nsew", pady = 2, padx  = 5)

        self.button_suck = ttk.Button(self.window_build_func, text="Suck",
                                      command=lambda: self.callback_button_func_win("suck"))
        self.button_suck.grid(row=9, column=0, sticky="nsew", pady = 2, padx  = 5)

        self.button_spit = ttk.Button(self.window_build_func, text="spit",
                                      command=lambda: self.callback_button_func_win("spit"))
        self.button_spit.grid(row=10, column=0, sticky="nsew", pady = 2, padx  = 5)

        self.button_pick_tips = ttk.Button(self.window_build_func, text="Pick Tips",
                                           command=lambda: self.callback_button_func_win("pick_tips"))
        self.button_pick_tips.grid(row=1, column=0, sticky="nsew", pady = 2, padx  = 5)

        self.button_return_tips = ttk.Button(self.window_build_func, text="Return Tips",
                                             command=lambda: self.callback_button_func_win("return_tips"))
        self.button_return_tips.grid(row=2, column=0, sticky="nsew", pady = 2, padx  = 5)

        self.button_replace_tip = ttk.Button(self.window_build_func, text="Replace Tip",
                                             command=lambda: self.callback_button_func_win("replace_tip"))
        self.button_replace_tip.grid(row=3, column=0, sticky="nsew", pady = 2, padx  = 5)

        self.button_discard_tips = ttk.Button(self.window_build_func, text="Discard Tips",
                                              command=lambda: self.callback_button_func_win("discard_tips"))
        self.button_discard_tips.grid(row=4, column=0, sticky="nsew", pady = 2, padx  = 5)

        self.button_add_medium = ttk.Button(self.window_build_func, text="Add Medium",
                                            command=lambda: self.callback_button_func_win("add_medium"))
        self.button_add_medium.grid(row=5, column=0, sticky="nsew", pady = 2, padx  = 5)

        self.button_remove_medium = ttk.Button(self.window_build_func, text="Remove Medium",
                                               command=lambda: self.callback_button_func_win("remove_medium"))
        self.button_remove_medium.grid(row=6, column=0, sticky="nsew", pady = 2, padx  = 5)

        self.button_transfer_plate_to_plate = ttk.Button(self.window_build_func, text="Transfer Plate to  Plate",
                                                         command=lambda: self.callback_button_func_win("transfer_plate_to_plate"))
        self.button_transfer_plate_to_plate.grid(row=7, column=0, sticky="nsew", pady = 2, padx  = 5)

        self.button_home = ttk.Button(self.window_build_func, text="Home",
                                      command=lambda: self.callback_button_func_win("home"))
        self.button_home.grid(row=8, column=0, sticky="nsew", pady = 2, padx  = 5)

        self.button_suck = ttk.Button(self.window_build_func, text="Suck",
                                      command=lambda: self.callback_button_func_win("suck"))
        self.button_suck.grid(row=9, column=0, sticky="nsew", pady = 2, padx  = 5)

        self.button_spit = ttk.Button(self.window_build_func, text="spit",
                                      command=lambda: self.callback_button_func_win("spit"))
        self.button_spit.grid(row=10, column=0, sticky="nsew", pady = 2, padx  = 5)

        self.button_spit_all = ttk.Button(self.window_build_func, text="spit all",
                                          command=lambda: self.callback_button_func_win("spit_all"))
        self.button_spit_all.grid(row=11, column=0, sticky="nsew", pady = 2, padx  = 5)

        self.button_spit_all = ttk.Button(self.window_build_func, text="spit all",
                                          command=lambda: self.callback_button_func_win("spit_all"))
        self.button_spit_all.grid(row=11, column=0, sticky="nsew", pady = 2, padx  = 5)

    def set_grid_settings_func_win(self):
        self.window_build_func.columnconfigure(0, weight=1)
        self.window_build_func.columnconfigure(1, weight=1)
        self.window_build_func.columnconfigure(2, weight=1)
        for i in range(12):
            self.window_build_func.rowconfigure(i, weight=1)

    def build_function_list(self):
        pass

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

    def display_possible_labware(self, labware_type: any, func_str: str, start_row: int, part: str = "second"):
        row = start_row
        for slot_id in self.dict_top_labware.keys():
            labware = self.dict_top_labware[slot_id]
            if not isinstance(labware, labware_type):
                continue

            label = ttk.Label(self.second_column_frame, text=slot_id)
            label.grid(column=0, row=row, sticky="nsew", pady=5, padx=5)
            row += 1

            button = ttk.Button(self.second_column_frame, text=self.dict_top_labware[slot_id].labware_id,
                                command=lambda lw=labware: self.callback_button_params(func_str=func_str, labware_obj=lw, part = part), bootstyle="warning")
            button.grid(row=row, column=0, sticky="nsew", pady=5, padx=5)
            row += 1

    def callback_button_func_win(self, func: str):
        """
        Dispatcher for button click events.
        Depending on the button name, the corresponding callback is called.
        """
        match func:
            case "pick_tips":
                self.callback_pick_tips(func)
            case "return_tips":
                self.callback_return_tips(func)
            case "replace_tip":
                self.callback_replace_tips(func)
            case "discard_tips":
                self.callback_discard_tips(func)
            case "add_medium":
                self.callback_add_medium(func)
            case "remove_medium":
                self.callback_remove_medium(func)
            case "transfer_plate_to_plate":
                self.callback_transfer_plate_to_plate(func)
            case "home":
                self.callback_home(func)
            case "suck":
                self.callback_suck(func)
            case "spit":
                self.callback_spit(func)
            case "spit_all":
                self.callback_spit_all(func)

    def callback_button_params(self, func_str: str, labware_obj: Labware, part: str = "second", **kwargs):
        """
        Handle user-selected labware and delegate to the appropriate callback.

        Parameters
        ----------
        func_str : str
            The name of the selected function (e.g., "pick_tips", "add_medium").
        labware_obj : Labware
            The Labware object chosen by the user (e.g., Plate, PipetteHolder).
        **kwargs : dict
            Additional parameters required by specific functions (e.g., volume, destination lists).
        """

        # --- Dispatcher pattern for different functions ---
        if func_str == "pick_tips":
            self.callback_pick_tips(
                func_str=func_str,
                part=part,
                labware_obj=labware_obj,
                **kwargs
            )

        elif func_str == "return_tips":
            self.callback_return_tips(
                func_str=func_str,
                part=part,
                labware_obj=labware_obj,
                **kwargs
            )

        elif func_str == "replace_tip":
            self.callback_replace_tips(
                func_str=func_str,
                part=part,
                labware_obj=labware_obj,
                **kwargs
            )

        elif func_str == "discard_tips":
            self.callback_discard_tips(
                func_str=func_str,
                part=part,
                labware_obj=labware_obj,
                **kwargs
            )

        elif func_str == "add_medium":
            self.callback_add_medium(
                func_str=func_str,
                part=part,
                labware_obj=labware_obj,
                **kwargs
            )

        elif func_str == "remove_medium":
            self.callback_remove_medium(
                func_str=func_str,
                part=part,
                labware_obj=labware_obj,
                **kwargs
            )

        elif func_str == "transfer_plate_to_plate":
            self.callback_transfer_plate_to_plate(
                func_str=func_str,
                first_part=False,
                labware_obj=labware_obj,
                **kwargs
            )

        elif func_str == "home":
            self.callback_home(**kwargs)

        elif func_str == "suck":
            self.callback_suck(**kwargs)

        elif func_str == "spit":
            self.callback_spit(**kwargs)

        elif func_str == "spit_all":
            self.callback_spit_all(**kwargs)

        else:
            print(f"[WARN] Unknown function: {func_str}")

    def add_current_function(self, func: Callable, func_str: str, labware_id):
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
    def callback_pick_tips(self, func_str: str, part: str = "first", labware_obj: PipetteHolder = None):
        if part == "first":
            self.clear_grid(self.second_column_frame)
            self.display_possible_labware(labware_type=PipetteHolder, func_str = func_str, start_row=0)
        else:
            window = WellWindow(rows = labware_obj.holders_across_x,
                                columns=labware_obj.holders_across_y,
                                labware_id=labware_obj.labware_id, master = self.window_build_func,
                                title=f"pick specific tips from: {labware_obj.labware_id}")

            self.window_build_func.wait_variable(window.safe_var)
            well_states = window.well_state
            list_return = []

            #interpret well states from WellWindow as list of tuple(represent Well grid) for PipettorPlus
            for row in range(len(well_states)):
                for column in range(len(well_states[row])):
                    if well_states[row][column]:
                        list_return.append((row, column))
            del window

            #func = self.pipettor.pick_tips(pipette_holder=labware_obj, list_col_row=list_return)
            self.add_current_function(func_str = func_str, func = lambda: print("test"),
                                      labware_id = labware_obj.labware_id)

    def callback_return_tips(self, func_str: str, part: bool = "first", labware_obj: PipetteHolder = None):
        """
        Handle the 'Return Tips' function selection.
        Essentially mirrors 'Pick Tips' but returns tips instead.
        """
        if part == "first":
            self.clear_grid(self.second_column_frame)
            self.display_possible_labware(labware_type=PipetteHolder, func_str=func_str, start_row=0)
        else:
            window = WellWindow(
                rows=labware_obj.holders_across_x,
                columns=labware_obj.holders_across_y,
                labware_id=labware_obj.labware_id,
                master=self.window_build_func,
                title=f"return specific tips tok: {labware_obj.labware_id}")

            self.window_build_func.wait_variable(window.safe_var)
            well_states = window.well_state
            #interpret well states from WellWindow as list of tuple(represent Well grid) for PipettorPlus
            list_return = [
                (r, c)
                for r, row in enumerate(well_states)
                for c, active in enumerate(row)
                if active
            ]
            del window

            #func = self.pipettor.return_tips(labware_obj, list_return)
            self.add_current_function(
                func_str=func_str,
                func=lambda: print("Returning tips to", labware_obj.labware_id, list_return),
                labware_id=labware_obj.labware_id
            )

    def callback_replace_tips(self, func_str: str, part: str = "first", labware_obj: PipetteHolder = None):
        """
        Handle the 'Replace Tips' function selection.
        Requires a PipetteHolder and generates both pick- and return-lists.
        """
        if part == "first":
            self.clear_grid(self.second_column_frame)
            self.display_possible_labware(labware_type=PipetteHolder, func_str=func_str, start_row=0)

        elif part == "second":
            window = WellWindow(
                rows=labware_obj.holders_across_x,
                columns=labware_obj.holders_across_y,
                labware_id=labware_obj.labware_id,
                master=self.window_build_func,
                title=f"pick from: {labware_obj.labware_id}"
            )
            self.window_build_func.wait_variable(window.safe_var)
            wells = window.well_state
            list_pick = [(r, c) for r, row in enumerate(wells) for c, v in enumerate(row) if v]
            del window

            window = WellWindow(
                rows=labware_obj.holders_across_x,
                columns=labware_obj.holders_across_y,
                labware_id=labware_obj.labware_id,
                master=self.window_build_func,
                title=f"return to: {labware_obj.labware_id}"
            )
            self.window_build_func.wait_variable(window.safe_var)
            wells = window.well_state
            list_return = [(r, c) for r, row in enumerate(wells) for c, v in enumerate(row) if v]

            del window

            #func = self.pipettor.replace_tips(labware_obj, return_list_col_row=list_return, pick_list_col_row=list_pick)
            self.add_current_function(
                func_str=func_str,
                func=lambda: print("Replacing tips on", labware_obj.labware_id, list_return, list_pick),
                labware_id=labware_obj.labware_id
            )

    def callback_discard_tips(self, func_str: str, part: str = "first", labware_obj: Labware = None):
        """
        Handle the 'Discard Tips' function.
        Requires selecting a TipDropzone labware.
        """
        if part == "first":
            self.clear_grid(self.second_column_frame)
            self.display_possible_labware(labware_type=TipDropzone, func_str=func_str, start_row=0)

        else:
            self.add_current_function(
                func_str=func_str,
                func=lambda: print("Discarding tips into", labware_obj.labware_id),
                labware_id=labware_obj.labware_id
            )

    # --------------------------------------------------------------------------
    # LIQUID HANDLING FUNCTIONS
    # --------------------------------------------------------------------------

    def callback_add_medium(self, func_str: str, part: str = "first", labware_obj: ReservoirHolder or Plate = None):
        """
        Handle the 'Add Medium' function.
        Requires selecting Reservoir, destination plate, and well lists.
        """
        if part == "first":
            self.clear_grid(self.second_column_frame)
            self.display_possible_labware(labware_type=ReservoirHolder, func_str=func_str, start_row=0, part = "second")

        elif part == "second":
            window = WellWindow(
                rows=labware_obj.hooks_across_x,
                columns=labware_obj.hooks_across_y,
                labware_id=labware_obj.labware_id,
                master=self.window_build_func,
                title=f"Choos Reservoir source: {labware_obj.labware_id}"
            )

            self.window_build_func.wait_variable(window.safe_var)
            wells = window.well_state
            self.curr_reservoir_holder = labware_obj
            self.curr_list_source = [(r, c) for r, row in enumerate(wells) for c, v in enumerate(row) if v]

            del window

            self.clear_grid(self.second_column_frame)
            self.display_possible_labware(labware_type=Plate, func_str=func_str, start_row=0, part="third")

        elif part == "third":
            self.curr_plate = labware_obj

            window = WellWindow(
                rows=labware_obj.hooks_across_x,
                columns=labware_obj.hooks_across_y,
                labware_id=labware_obj.labware_id,
                master=self.window_build_func,
                title=f"Choos Reservoir source: {labware_obj.labware_id}"
            )

            self.window_build_func.wait_variable(window.safe_var)
            wells = window.well_state
            self.curr_list_destination = [(r, c) for r, row in enumerate(wells) for c, v in enumerate(row) if v]
            del window

            self.clear_grid(self.second_column_frame)

            #creater enter Entry, for entering Volume per Well

            label = ttk.Label(self.second_column_frame, text="Enter Volume per Well")
            label.grid(column=0, row=0, sticky="nsew", pady=5, padx=5)

            text_var = ttk.StringVar(value = "5")
            entry = ttk.Entry(self.second_column_frame, textvariable=text_var)
            entry.grid(row=1, column=0, sticky="nsew", pady=5, padx=5)

            def callback_enter_button():
                if not text_var.get().isdigit():
                    return
                #TODO rewatch this self.pipettor function, source_col_row is supposed to be a tuple.

                self.pipettor.add_medium(source = self.curr_reservoir_holder, source_col_row=self.curr_list_source,
                                         destination=self.curr_plate,
                                         dest_col_row=self.curr_list_destination)
                self.add_current_function(
                    func_str=func_str,
                    func=lambda: print("Discarding tips into", labware_obj.labware_id),
                    labware_id=labware_obj.labware_id
                )


            button = ttk.Button(self.second_column_frame, text="Enter", command=callback_enter_button)
            button.grid(row = 2, column = 0, sticky="nsew", pady=5, padx=5)

    def callback_remove_medium(self, func_str: str, first_part: bool = True, labware_obj: ReservoirHolder = None):
        """
        Handle the 'Remove Medium' function.
        Similar to add_medium but reverses source and destination lists.
        """
        if first_part:
            self.clear_grid(self.second_column_frame)
            self.display_possible_labware(labware_type=ReservoirHolder, func_str=func_str, start_row=0)
        else:
            self.add_current_function(
                func_str=func_str,
                func=lambda: print("Removing medium using", labware_obj.labware_id),
                labware_id=labware_obj.labware_id
            )

    def callback_transfer_plate_to_plate(self, func_str: str, first_part: bool = True, labware_obj: Plate = None):
        """
        Handle 'Transfer Plate to Plate' function.
        Requires source plate, destination plate, and corresponding well lists.
        """
        if first_part:
            self.clear_grid(self.second_column_frame)
            self.display_possible_labware(labware_type=Plate, func_str=func_str, start_row=0)
        else:
            self.add_current_function(
                func_str=func_str,
                func=lambda: print("Transferring plate data from", labware_obj.labware_id),
                labware_id=labware_obj.labware_id
            )

    # --------------------------------------------------------------------------
    # BASIC MOTION / HOME FUNCTIONS
    # --------------------------------------------------------------------------

    def callback_home(self, func_str: str):
        """Send pipettor to home position."""
        self.clear_grid(self.second_column_frame)
        self.add_current_function(
            func_str=func_str,
            func=lambda: print("Homing pipettor"),
            labware_id=None
        )

    def callback_suck(self, func_str: str):
        """Perform pipettor suction."""
        self.clear_grid(self.second_column_frame)
        self.add_current_function(
            func_str=func_str,
            func=lambda: print("Sucking liquid"),
            labware_id=None
        )

    def callback_spit(self, func_str: str):
        """Perform pipettor dispense."""
        self.clear_grid(self.second_column_frame)
        self.add_current_function(
            func_str=func_str,
            func=lambda: print("Spitting liquid"),
            labware_id=None
        )

    def callback_spit_all(self, func_str: str):
        """Perform pipettor dispense (spit all)."""
        self.clear_grid(self.second_column_frame)
        self.add_current_function(
            func_str=func_str,
            func=lambda: print("Spitting all liquid"),
            labware_id=None
        )