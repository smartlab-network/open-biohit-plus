from src.biohit_pipettor_plus.deck_structure.control_json import read_json
from src.biohit_pipettor_plus.gui2 import Gui
restored_deck = read_json("deck1")

gui = Gui(deck=restored_deck)
root = gui.get_root()
root.mainloop()