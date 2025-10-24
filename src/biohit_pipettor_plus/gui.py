import ttkbootstrap as ttk
from .deck import Deck
from .slot import Slot
from .labware import Labware


class Gui:
    def __init__(self, deck: Deck, master: ttk.Window = None):
        if isinstance(master, ttk.Window):
            self.root = ttk.Toplevel(master)
        else:
            self.root = ttk.Window(themename="superhero")

            self.root.geometry("1400x800")
