import ttkbootstrap as ttk
from .deck import Deck
from .slot import Slot
from .labware import Labware

class Gui:
    def __init__(self,deck: Deck, master: ttk.Window = None):
        if isinstance(master, ttk.Window):
            self.root = ttk.Toplevel(master)
        else:
            self.root = ttk.Window(themename="superhero")

        self.deck = deck
        self.root.geometry("1400x800")

        self.slots: dict[str, Slot] = deck.slots
        self.slot_frames: dict[str, ttk.Frame] = {}

        self.canvas_corners_deck = [(deck.range_x[0]*2, deck.range_y[0]*2),
                                    (deck.range_x[1]*2, deck.range_y[1]*2)]

        self.deck_canvas = ttk.Canvas(self.root,
                                      width=abs(self.canvas_corners_deck[0][0]-self.canvas_corners_deck[1][0]),
                                      height=abs(self.canvas_corners_deck[0][1]-self.canvas_corners_deck[1][1]),
                                      background = "lightgray")

        self.deck_canvas.create_rectangle(self.canvas_corners_deck[0][0],
                                          self.canvas_corners_deck[0][1],
                                          self.canvas_corners_deck[1][0],
                                          self.canvas_corners_deck[1][1],
                                          outline = "black", width=2)

        self.deck_canvas.grid(row=0, column=0, sticky="nsew")

        self.actions_windows: dict[str, LabawareActionsWin] = {}

        self.place_slots()
        self.fill_slot_frames()

    def get_root(self):
        return self.root

    def place_slots(self):
        for slot_id, slot in self.slots.items():
            canvas_corners_slot = [(slot.range_x[0] * 2, slot.range_y[0] * 2),
                                   (slot.range_x[1] * 2, slot.range_y[1] * 2)]

            print("slot: ",slot_id,"range x, y: ",slot.range_x, slot.range_y, canvas_corners_slot)


            frame = ttk.Frame(self.root,
                              width=abs(canvas_corners_slot[0][0] - canvas_corners_slot[1][0]),
                              height=abs(canvas_corners_slot[0][1] - canvas_corners_slot[1][1]))

            frame.propagate = False
            frame.columnconfigure(0, weight=1)
            frame.columnconfigure(1, weight=1)
            frame.columnconfigure(2, weight=1)
            frame.rowconfigure(0, weight=1)
            frame.rowconfigure(1, weight=1)
            frame.rowconfigure(2, weight=1)
            frame.rowconfigure(3, weight=1)
            frame.rowconfigure(4, weight=1)

            title = ttk.Label(frame,text=slot_id, anchor="center", font=("Arial", 18))
            title.grid(row=0, column=0, sticky="nsew", columnspan=3)


            rect = self.deck_canvas.create_rectangle(   canvas_corners_slot[0][0],
                                                        canvas_corners_slot[0][1],
                                                        canvas_corners_slot[1][0],
                                                        canvas_corners_slot[1][1],
                                                        outline="red", width=2,
                                                        fill = "lightgrey")

            self.deck_canvas.create_window(canvas_corners_slot[0][0]+1,
                                           canvas_corners_slot[0][1]+1,
                                           window=frame,
                                           anchor="nw",
                                           width=abs(canvas_corners_slot[0][0]- canvas_corners_slot[1][0])-2,
                                           height=abs(canvas_corners_slot[0][1]-canvas_corners_slot[1][1])-2)

            self.deck_canvas.tag_raise(rect)
            self.slot_frames[slot_id] = frame


    def fill_slot_frames(self):
        for slot_id, frame in self.slot_frames.items():
            slot: Slot = self.slots[slot_id]
            add_labware_button = ttk.Button(frame, command=lambda: self.callback_add_labware(slot_id), text="add labware")
            add_labware_button.grid(row=1, column=0, sticky="nsew", columnspan=3)
            row = 2
            print(slot.labware_stack.items())
            for labware_id, labware_list in slot.labware_stack.items():
                labware_label = ttk.Label(frame,
                                          text=f"{labware_id}: {labware_list[1]}",
                                          anchor="center")

                labware_label.grid(row=row, column=0, sticky="nsew", columnspan=2)

                labware_button = ttk.Button(frame,
                                            text="actions",
                                            command=lambda: self.callback_actions(labware_id))
                labware_button.grid(row = row, column=2)

                self.actions_windows[labware_id] = LabawareActionsWin(labware=labware_list[0], top_level = ttk.Toplevel(self.root))

                row += 1


    def callback_actions(self, labware_id: str):
        self.actions_windows[labware_id].show_window()

    def slot_button_press(self, slot_id: str):
        pass

    def callback_add_labware(self, slot_id: str):
        pass


class LabawareActionsWin:
    def __init__(self, labware: Labware, top_level: ttk.Toplevel):
        self.root = top_level
        self.labware = labware
        self.root.title(f"Labware actions for: {self.labware.labware_id}")
        self.root.geometry("900x600")
        self.is_window = True
        self.show_window()

        self.root.protocol("WM_DELETE_WINDOW", self.show_window)

    def show_window(self):
        if self.is_window:
            self.root.withdraw()
            self.is_window = False
        else:
            self.root.deiconify()
            self.is_window = True
