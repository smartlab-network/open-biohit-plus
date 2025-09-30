import ttkbootstrap as ttk
from .deck import Deck
from .slot import Slot

class Gui:
    def __init__(self,deck: Deck, master: ttk.Window = None):
        if isinstance(master, ttk.Window):
            self.root = ttk.Toplevel(master)
        else:
            self.root = ttk.Window()

        self.deck = deck
        self.root.geometry("1400x800")

        self.slots: dict[str, Slot] = deck.slots
        self.slot_frames: dict[str, ttk.Frame] = {}

        self.deck_canvas = ttk.Canvas(self.root,
                                      width=abs(deck.range_x[0]-deck.range_x[1]),
                                      height=abs(deck.range_y[0]-deck.range_y[1]),
                                      background = "lightgray")

        self.deck_canvas.create_rectangle(deck.range_x[0], deck.range_y[0], deck.range_x[1], deck.range_y[1], outline = "black", width=2)
        self.deck_canvas.grid(row=0, column=0, sticky="nsew")
        self.place_slots()
        self.fill_slot_frames()

    def get_root(self):
        return self.root

    def place_slots(self):
        for slot_id, slot in self.slots.items():
            frame = ttk.Frame(self.root,
                              width=abs(slot.range_x[0]-slot.range_x[1]),
                              height=abs(slot.range_y[0]-slot.range_y[1]))
            frame.propagate = False
            frame.columnconfigure(0, weight=1)
            frame.rowconfigure(0, weight=1)
            title = ttk.Label(frame,text=slot_id, anchor="center", font=("Arial", 18))
            title.grid(row=0, column=0, sticky="nsew")
            title.grid(row=0, column=0, sticky="nsew")

            self.deck_canvas.create_window(slot.range_x[0], slot.range_y[0], window=frame, anchor="nw")
            self.deck_canvas.create_rectangle(slot.range_x[0], slot.range_y[0], slot.range_x[1], slot.range_y[1], outline="red")

            self.slot_frames[slot_id] = frame



    def fill_slot_frames(self):
        for slot_id, frame in self.slot_frames.items():
            slot: Slot = self.slots[slot_id]
            add_labware_button = ttk.Button(frame, command=lambda: self.callback_add_labware(slot_id), text="add labware")
            add_labware_button.grid(row=1, column=0, sticky="nsew")
            row = 1
            for labware_id, labware_list in slot.labware_stack.items():
                labware_label = ttk.Label(frame,
                                          text=f"{labware_id}: {labware_list[1]}",
                                          anchor="center",
                                          font=("Arial", 18))
                row += 1
                labware_label.grid(row=row, column=0, sticky="nsew")


    def slot_button_press(self, slot_id: str):
        pass

    def callback_add_labware(self, slot_id: str):
        pass