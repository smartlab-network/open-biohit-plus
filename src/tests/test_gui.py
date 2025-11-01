from src.biohit_pipettor_plus.control_json import read_json
from src.biohit_pipettor_plus.gui.function_window import FunctionWindow
from src.biohit_pipettor_plus.deck import Deck

deck_1: Deck = read_json("MainDeck_01")
print(deck_1)
gui = FunctionWindow(deck=deck_1)

root = gui.root
root.mainloop()