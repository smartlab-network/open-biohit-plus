from src.biohit_pipettor_plus.control_json import read_json
from src.biohit_pipettor_plus.deck import Deck
from src.biohit_pipettor_plus.slot import Slot
from src.biohit_pipettor_plus.labware import *
from src.biohit_pipettor_plus.gui import Gui
deck1:Deck = read_json("deck_1")

print(deck1)

"""slots = deck1.slots

gui = Gui(deck=deck1)


gui.root.mainloop()"""