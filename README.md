[![docs](https://img.shields.io/badge/docs-passing-brightgreen.svg)](https://umg-pharma-lab-automation.pages.gwdg.de/biohit-pipettor-python/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

# Biohit Roboline Python Interface
Please visit the [documentation](https://umg-pharma-lab-automation.pages.gwdg.de/biohit-pipettor-python/).

## Division of responsibilities

- **open-biohit** (`biohit_pipettor` package): wraps the machine control DLL
  (`InstrumentLib.dll` via pythonnet). Hardware only: `Pipettor` with
  `move_xy/move_z/aspirate/dispense/pick_tip/eject_tip/...`.
- **open-biohit-plus** (this repo, `src/`): adds the lab logic on top —
  deck layout and labware:

  | class            | module           | purpose                                             |
  |------------------|------------------|-----------------------------------------------------|
  | `Deck`, `Slot`   | `src/deck.py`    | deck slots (absolute x/y), what is placed where, `well_position(slot, well)` → absolute machine coordinates |
  | `Labware`        | `src/Labware.py` | base class + shared helpers: wells relative to the labware origin, z limits, JSON load/save (`from_json`, `load_library`) |
  | `Plate`          | `src/Plate.py`   | multi-well plates (`Plate.from_grid(...)`)          |
  | `Adapter`        | `src/Adapter.py` | carrier holding a child labware at an offset        |
  | `TipRack`        | `src/TipRack.py` | rack of `Tip` objects with pick/return bookkeeping  |
  | `Reservoir`      | `src/Reservoir.py` | reagent troughs / waste with fill-volume tracking |
  | `Tip`            | `src/Tip.py`     | a single tip (position, volume, available/used)     |

  Labware and deck layouts are JSON files in [`labware/`](labware); the folder
  is `$LABWARE_DIR` if set, else this repo's `labware/`. There is one
  descriptive JSON per class: `biohit_deck.json` (deck layout: two half-SBS
  slots in the back — Slot_1, Slot_2 — and a 2x2 block of SBS slots in the
  front — Slot_3..Slot_6), `plate.json`, `reservoir.json`, `tip_rack.json`,
  `tip.json`, plus concrete labware (e.g. `corning_96_flat.json`,
  `ehm_42_well.json`, `tip_rack_1000ul.json`, `plate_adapter.json`).
  See `examples/deck_layout.py` for a hardware-free demo and
  `tests/test_deck_labware.py` for the test suite (`python -m pytest tests/`).
