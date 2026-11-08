"""Demo of the open-biohit-plus deck/labware model (no hardware needed).

Builds a :class:`src.deck.Deck` from ``labware/biohit_deck.json`` (two half-SBS
slots in the back, 2x2 SBS slots in the front), places the labware, resolves
absolute machine coordinates of wells/tips and simulates picking tips from
the tip rack.

Run from the repo root:

    python examples/deck_layout.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root, for ``import src``

from src import Adapter, Deck, Labware, Plate, Reservoir, TipRack  # noqa: E402


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    labware_dir = root / "labware"

    # --- labware library -------------------------------------------------
    library = Labware.load_library(labware_dir)
    print(f"labware library ({labware_dir}):")
    for name, lw in library.items():
        print(f"  {lw!r}")

    # --- deck -------------------------------------------------------------
    deck = Deck.from_json(labware_dir / "biohit_deck.json")
    print(f"\n{deck}  (name={deck.name!r}, machine={deck.machine})")
    print(f"  back slots:  {[s.name + ':' + s.slot_type for s in deck.back_slots]}")
    print(f"  front slots: {[s.name + ':' + s.slot_type for s in deck.front_slots]}")
    for name in deck:
        slot = deck.slot(name)
        lw = slot.labware
        print(f"  slot {name} at {slot.position}: {lw!r}" if lw else f"  slot {name} at {slot.position}: empty")

    # --- absolute well positions ------------------------------------------
    plate_slot = "Slot_1"
    plate = deck.labware_at(plate_slot)
    x, y = deck.well_position(plate_slot, "A1")
    x3, y3, z3 = deck.well_position_xyz(plate_slot, "H6")
    print(f"\nplate {plate.name!r} well A1 at absolute ({x:.2f}, {y:.2f}) mm")
    print(f"plate {plate.name!r} well H6 at absolute ({x3:.2f}, {y3:.2f}, z={z3:.2f}) mm")

    # --- adapter: wells of the child, shifted by the child offset ---------
    adapter = deck.labware_at("Slot_3")
    if isinstance(adapter, Adapter):
        print(f"\nadapter {adapter.name!r} holds child {adapter.child!r} at offset {adapter.child_offset}")
        print(f"  adapter well A1 (child A1 + offset) at {deck.well_position('Slot_3', 'A1')}")

    # --- reservoir volume tracking -----------------------------------------
    reservoir = deck.labware_at("Slot_2")
    if isinstance(reservoir, Reservoir):
        reservoir.set_fill("A1", 30_000)  # 30 mL of medium
        print(
            f"\nreservoir {reservoir.name!r} A1: fill={reservoir.fill_volume_ul('A1'):.0f} uL, "
            f"remaining={reservoir.remaining_volume_ul('A1'):.0f} uL, "
            f"liquid height={reservoir.liquid_height_mm('A1'):.1f} mm"
        )

    # --- tip rack -----------------------------------------------------------
    rack = deck.tip_rack
    if isinstance(rack, TipRack):
        print(
            f"\ntip rack {rack.name!r} in slot {deck.tip_rack_slot}: "
            f"{rack.available_count}/{len(rack)} tips available, pick_z={rack.pick_z}, "
            f"pickup_limit_z={rack.pickup_limit_z}"
        )
        tip = rack.pick_next()
        print(f"  picked {tip}, absolute xy={tip.absolute_xy()}")
        print(f"  now {rack.available_count} tips left; next: {rack.next_tip()}")
        rack.return_tip(tip.tip_id)
        print(f"  returned {tip.tip_id}; available again: {rack.available_count}/{len(rack)}")

    # --- build a plate programmatically -------------------------------------
    plate96 = Plate.from_grid("My 96-well plate", 8, 12, well_a1_offset=(14.38, 11.24), spacing=(9.0, 9.0))
    deck.place("Slot_5", plate96)
    print(
        f"\nplaced {plate96!r} in slot Slot_5; well A1 at {deck.well_position('Slot_5', 'A1')}, "
        f"well H12 at {deck.well_position('Slot_5', 'H12')}"
    )


if __name__ == "__main__":
    main()
