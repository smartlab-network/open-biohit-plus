from src.biohit_pipettor_plus.control_json import read_json
from src.biohit_pipettor_plus.gui_old import Gui
restored_deck = read_json("deck1")

gui = Gui(deck=restored_deck)
root = gui.get_root()
root.mainloop()

