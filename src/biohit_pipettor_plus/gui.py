import ttkbootstrap as ttk
import tkinter as tk
from typing import Callable
from .deck import Deck
from .slot import Slot
from .labware import Labware
from .pipettor_plus import PipettorPlus

class Gui:
    def __init__(self, deck: Deck = None, master: ttk.Window = None):
        if isinstance(master, ttk.Window):
            self.root = ttk.Toplevel(master)
        else:
            self.root = ttk.Window(themename="solar")
            self.root.geometry("1400x800")

        self.deck = deck
        #TODO review self.pipettor
        #self.pipettor = PipettorPlus(deck = self.deck, multichannel=False, tip_volume=200)

        #window for creating custom functions
        #self.window_build_func = ttk.Toplevel(self.root)
        self.window_build_func = self.root
        self.window_build_func.geometry("1400x800")
        self.set_grid_settings_func_win()
        self.create_window_build_func()
        #self.window_build_func.withdraw()

        self.custom_funcs_lists: list[list[Callable]] = []
        self.current_func_list: list[Callable] = []



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

        self.safe_button = ttk.Button(self.frame_name, text="Safe", command=self.callback_safe_button)
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

    def callback_button_func_win(self, func: str):


        match func:
            case "pick_tips":
                self.callback_pick_tips(func)

    def callback_safe_button(self):
        pass

    def callback_pick_tips(self, func: str):
        button_1 = ttk.Button(self.second_column_frame, text = "test1", command = lambda: self.callback_button_params(func), bootstyle = "warning")
        button_1.grid(row = 0, column=0, sticky="nsew", pady = 5, padx = 5)

        button_1 = ttk.Button(self.second_column_frame, text="test2", command=lambda: self.callback_button_params(func), bootstyle = "info")
        button_1.grid(row=1, column=0, sticky="nsew", pady = 5, padx = 5)

        button_1 = ttk.Button(self.second_column_frame, text="test3", command=lambda: self.callback_button_params(func), bootstyle = "danger")
        button_1.grid(row=2, column=0, sticky="nsew", pady = 5, padx = 5)

        button_1 = ttk.Button(self.second_column_frame, text="test4", command=lambda: self.callback_button_params(func), bootstyle = "succes")
        button_1.grid(row=3, column=0, sticky="nsew", pady = 5, padx = 5)

    def callback_button_params(self, func: str):
        self.current_func_list.append(func)
        label_func = ttk.Label(self.third_column_frame, text = func, font = ("Helvetica", 16), anchor = "center")
        label_func.grid(row = len(self.current_func_list) - 1, column=0, sticky="nsew")

gui = Gui()
gui.root.mainloop()