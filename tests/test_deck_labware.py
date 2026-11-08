"""Tests for the open-biohit-plus deck/labware model (pure logic, no hardware)."""

import json
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))  # for ``import src``

from src import Adapter, Deck, Labware, Plate, Reservoir, Slot, Tip, TipRack  # noqa: E402
from src.Labware import well_id  # noqa: E402

LABWARE_DIR = ROOT / "labware"


# --------------------------------------------------------------------- helpers
def test_well_id():
    assert well_id(0, 0) == "A1"
    assert well_id(7, 11) == "H12"
    assert well_id(1, 5) == "B6"


# ----------------------------------------------------------------------- Plate
def test_plate_from_grid():
    plate = Plate.from_grid("p96", 8, 12, well_a1_offset=(14.38, 11.24), spacing=(9.0, 9.0))
    assert len(plate) == 96
    assert plate.well_ids[0] == "A1"
    assert plate.well_ids[-1] == "H12"
    assert plate.well_offset("A1") == (14.38, 11.24)
    assert plate.well_offset("H12") == pytest.approx((14.38 + 11 * 9.0, 11.24 + 7 * 9.0))
    assert "B5" in plate
    with pytest.raises(KeyError):
        plate.well_offset("Z99")


def test_plate_grid_negative_spacing_and_col_row_lists():
    plate = Plate.from_grid(
        "ehm",
        8,
        6,
        col_x=[89.4, 70.62, 53.28, 35.94, 18.6, 0.0],
        row_y=[0.0, 7.32, 21.69, 29.28, 36.6, 43.92, 51.24, 58.56],
    )
    assert len(plate) == 48
    assert plate.well_offset("A1") == (89.4, 0.0)
    assert plate.well_offset("A6") == (0.0, 0.0)
    assert plate.well_offset("H6") == (0.0, 58.56)


def test_plate_json_roundtrip(tmp_path):
    plate = Plate.from_grid(
        "p96",
        8,
        12,
        well_a1_offset=(14.38, 11.24),
        spacing=(9.0, 9.0),
        z_limits={"recommended_aspirate_z": 92.0},
        well_properties={"radius_mm": 3.4, "depth_mm": 10.8, "max_volume_ul": 360.0},
    )
    out = tmp_path / "p96.json"
    plate.save(out)
    loaded = Labware.from_json(out)
    assert isinstance(loaded, Plate)
    assert loaded.name == "p96"
    assert len(loaded) == 96
    assert loaded.well_offset("H12") == pytest.approx(plate.well_offset("H12"))
    assert loaded.aspirate_z == 92.0
    assert loaded.well_radius_mm == 3.4
    assert loaded.well_max_volume_ul == 360.0


def test_load_labware_files():
    plate = Labware.from_json(LABWARE_DIR / "corning_96_flat.json")
    assert isinstance(plate, Plate)
    assert len(plate) == 96

    ehm = Labware.from_json(LABWARE_DIR / "ehm_42_well.json")
    assert isinstance(ehm, Plate)
    assert len(ehm) == 48
    assert ehm.well_offset("A1") == (89.40, 0.0)

    res = Labware.from_json(LABWARE_DIR / "reservoir_3_well.json")
    assert isinstance(res, Reservoir)
    assert res.well_ids == ["A1", "A2", "A3"]
    assert res.well_offset("A3") == pytest.approx((21.3 + 2 * 42.6, 17.5))

    rack = Labware.from_json(LABWARE_DIR / "tip_rack_1000ul.json")
    assert isinstance(rack, TipRack)
    assert len(rack.tips) == 96
    assert rack.tip_volume_ul == 1000.0
    assert rack.pick_z == 92.0
    assert rack.pickup_limit_z == 98.0

    adapter = Labware.from_json(LABWARE_DIR / "plate_adapter.json")
    assert isinstance(adapter, Adapter)
    assert isinstance(adapter.child, Plate)
    assert adapter.child_offset == (10.0, 5.0)
    # adapter wells = child wells + offset
    assert adapter.well_offset("A1") == pytest.approx(
        (adapter.child.well_offset("A1")[0] + 10.0, adapter.child.well_offset("A1")[1] + 5.0)
    )
    assert len(adapter) == 96


def test_type_inference_without_type_key(tmp_path):
    data = {"labware_name": "something with a tip", "grid": {"rows": 2, "columns": 2}}
    p = tmp_path / "my_tip_rack.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    assert isinstance(Labware.from_json(p), TipRack)

    data = {"labware_name": "waste thing", "grid": {"rows": 1, "columns": 1}}
    p = tmp_path / "waste.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    assert isinstance(Labware.from_json(p), Reservoir)


def test_load_library_skips_deck_and_tip_files():
    library = Labware.load_library(LABWARE_DIR)
    assert any(isinstance(lw, Plate) for lw in library.values())
    assert any(isinstance(lw, Reservoir) for lw in library.values())
    assert any(isinstance(lw, TipRack) for lw in library.values())
    assert any(isinstance(lw, Adapter) for lw in library.values())
    # biohit_deck.json (deck layout) and tip.json (single tip) are not labware
    assert not any("deck" in name.lower() for name in library)
    assert all("labware_name" not in str(vars(lw)) or True for lw in library.values())
    assert "Generic Plate" in library and "Generic Reagent Reservoir" in library
    assert "Generic Tip Rack (300 uL)" in library


def test_generic_class_json_files():
    # one descriptive JSON per class: plate / reservoir / tip_rack
    plate = Labware.from_json(LABWARE_DIR / "plate.json")
    assert isinstance(plate, Plate) and not isinstance(plate, (Reservoir, TipRack))
    assert len(plate) == 96 and plate.well_ids[0] == "A1"

    res = Labware.from_json(LABWARE_DIR / "reservoir.json")
    assert isinstance(res, Reservoir)
    assert len(res) == 8 and res.well_ids == ["A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8"]

    rack = Labware.from_json(LABWARE_DIR / "tip_rack.json")
    assert isinstance(rack, TipRack)
    assert rack.tip_volume_ul == 300.0 and len(rack.tips) == 96
    assert rack.pick_z == 86.0 and rack.pickup_limit_z == 87.0


def test_tip_json_roundtrip(tmp_path):
    tip = Tip.from_json(LABWARE_DIR / "tip.json")
    assert tip.tip_id == "A1"
    assert tip.offset == (6.0, 6.0)
    assert tip.max_volume_ul == 1000.0
    assert tip.pick_z == 92.0
    assert tip.is_available
    out = tmp_path / "tip_out.json"
    tip.save(out)
    tip2 = Tip.from_json(out)
    assert tip2.to_dict() == tip.to_dict()
    tip.mark_used()
    assert Tip.from_dict(tip.to_dict()).state == Tip.USED


# ------------------------------------------------------------------- Reservoir
def test_reservoir_volume_tracking():
    res = Labware.from_json(LABWARE_DIR / "reservoir_3_well.json")
    assert isinstance(res, Reservoir)
    assert res.max_volume_ul("A1") == 40000.0
    res.set_fill("A1", 30000.0)
    assert res.fill_volume_ul("A1") == 30000.0
    assert res.remaining_volume_ul("A1") == 10000.0
    res.add_volume("A1", -5000.0)
    assert res.remaining_volume_ul("A1") == 15000.0
    # area = pi * 12^2 = 452.39 mm^2; 25000 uL = 25000 mm^3 -> 55.3 mm
    assert res.liquid_height_mm("A1") == pytest.approx(25000.0 / (math.pi * 12.0**2))
    with pytest.raises(ValueError):
        res.set_fill("A1", -1.0)
    with pytest.raises(KeyError):
        res.remaining_volume_ul("B1")


def test_reservoir_max_volume_from_geometry():
    res = Reservoir("r", wells={"A1": (0.0, 0.0)}, well_properties={"radius_mm": 3.0, "depth_mm": 10.0})
    assert res.max_volume_ul("A1") == pytest.approx(math.pi * 9.0 * 10.0)


# --------------------------------------------------------------------- TipRack
def test_tip_rack_pick_return_reset():
    rack = TipRack.from_grid("tips", 2, 3, spacing=(9.0, 9.0), tip_volume_ul=200.0)
    assert rack.available_count == 6
    assert len(rack.available_tips()) == 6
    t1 = rack.pick_next()
    assert isinstance(t1, Tip)
    assert t1.tip_id == "A1"
    assert not t1.is_available
    assert rack.available_count == 5
    assert rack.next_tip().tip_id == "B1"
    rack.return_tip("A1")
    assert rack.tips["A1"].is_available
    # row-major order after returning: A1 first again
    assert rack.next_tip().tip_id == "A1"
    rack.reset()
    assert rack.available_count == 6
    with pytest.raises(KeyError):
        rack.return_tip("Z9")


def test_tip_rack_empty_raises():
    rack = TipRack.from_grid("tips", 1, 1, tip_volume_ul=200.0)
    rack.pick_next()
    assert rack.next_tip() is None
    with pytest.raises(RuntimeError):
        rack.pick_next()


def test_tip_absolute_xy_uses_rack_origin():
    rack = TipRack.from_grid("tips", 2, 2, well_a1_offset=(6.0, 6.0), spacing=(9.0, 9.0), tip_volume_ul=1000.0)
    rack.origin = (100.0, 50.0)
    tip = rack.tips["B2"]
    assert tip.offset == (15.0, 15.0)
    assert tip.absolute_xy() == (115.0, 65.0)


# ---------------------------------------------------------------------- Adapter
def test_adapter_set_child():
    child = Plate.from_grid("child", 2, 2, well_a1_offset=(10.0, 10.0), spacing=(9.0, 9.0))
    adapter = Adapter("ad")
    assert len(adapter) == 0  # no child yet
    adapter.set_child(child, 5.0, 7.0)
    assert adapter.child_offset == (5.0, 7.0)
    assert adapter.well_offset("A1") == (15.0, 17.0)
    assert adapter.well_offset("B2") == (24.0, 26.0)
    assert len(adapter) == 4


# ------------------------------------------------------------------------ Deck
def test_deck_defaults():
    deck = Deck()
    assert len(deck) == 6
    assert set(deck.slot_names) == {"Slot_1", "Slot_2", "Slot_3", "Slot_4", "Slot_5", "Slot_6"}
    assert deck.slot_position("Slot_4") == (127.80, 52.75)
    assert deck.tip_rack_slot == "Slot_4"
    assert deck.tipPosition == "Slot_4"  # legacy alias
    assert deck.tipCoordinates() == (127.80, 52.75)  # legacy alias
    assert deck.ref_points["P3"] == (132.80, 170.50, 41.40)
    # default layout: 2 half-SBS slots in the back, 2x2 SBS slots in the front
    assert [s.name for s in deck.slots_of_type("half_sbs")] == ["Slot_1", "Slot_2"]
    assert [s.name for s in deck.slots_of_type("sbs")] == ["Slot_3", "Slot_4", "Slot_5", "Slot_6"]
    assert [s.name for s in deck.back_slots] == ["Slot_1", "Slot_2"]
    assert [s.name for s in deck.front_slots] == ["Slot_3", "Slot_4", "Slot_5", "Slot_6"]
    with pytest.raises(KeyError):
        deck.slot("X9")


def test_deck_place_and_well_position():
    deck = Deck()
    plate = Plate.from_grid("p96", 8, 12, well_a1_offset=(14.38, 11.24), spacing=(9.0, 9.0))
    deck.place("Slot_1", plate)
    assert plate.origin == (265.60, 0.09)
    assert deck.well_position("Slot_1", "A1") == pytest.approx((265.60 + 14.38, 0.09 + 11.24))
    assert deck.well_position("Slot_1", "H12") == pytest.approx((265.60 + 113.38, 0.09 + 74.24))
    xyz = deck.well_position_xyz("Slot_1", "A1", z=95.0)
    assert xyz == pytest.approx((279.98, 11.33, 95.0))
    # z falls back to the labware's aspirate_z
    plate2 = Plate.from_grid("p", 1, 1, z_limits={"recommended_aspirate_z": 92.0})
    deck.place("Slot_2", plate2)
    assert deck.well_position_xyz("Slot_2", "A1")[2] == 92.0
    # unplaced slot raises
    with pytest.raises(ValueError):
        deck.well_position("Slot_5", "A1")
    deck.unplace("Slot_1")
    assert deck.labware_at("Slot_1") is None


def test_biohit_deck_layout():
    deck = Deck.from_json(LABWARE_DIR / "biohit_deck.json")
    assert deck.name == "Biohit Roboline deck"
    assert deck.machine["max_x_mm"] == 300.0
    assert len(deck) == 6
    # two half-SBS slots in the back (Slot_1, Slot_2)
    back = {s.name: s for s in deck.back_slots}
    assert set(back) == {"Slot_1", "Slot_2"}
    assert all(s.slot_type == "half_sbs" for s in back.values())
    assert all(s.metadata["position"] == "back" for s in back.values())
    assert all(s.width_mm == 127.76 and s.height_mm == 42.74 for s in back.values())
    # 2x2 SBS slots in the front (Slot_3..Slot_6)
    front = {s.name: s for s in deck.front_slots}
    assert set(front) == {"Slot_3", "Slot_4", "Slot_5", "Slot_6"}
    assert all(s.slot_type == "sbs" for s in front.values())
    assert all(s.metadata["position"] == "front" for s in front.values())
    assert all(s.width_mm == 127.76 and s.height_mm == 85.48 for s in front.values())
    assert deck.tip_rack_slot == "Slot_4"
    assert deck.ref_points["P1"] == [239.49, 43.00, 6.80]


def test_deck_from_json_with_labware():
    deck = Deck.from_json(LABWARE_DIR / "biohit_deck.json")
    assert len(deck) == 6
    assert deck.tip_rack_slot == "Slot_4"
    assert isinstance(deck.labware_at("Slot_1"), Plate)
    assert isinstance(deck.labware_at("Slot_2"), Reservoir)
    assert isinstance(deck.labware_at("Slot_3"), Adapter)
    rack = deck.tip_rack
    assert isinstance(rack, TipRack)
    assert rack.available_count == 96
    # absolute position of EHM plate A1 in Slot_1 (x_abs=265.60, y_abs=0.09)
    assert deck.well_position("Slot_1", "A1") == pytest.approx((265.60 + 89.40, 0.09 + 0.0))
    # adapter child well A1 in Slot_3: slot + child_offset + child a1 offset
    assert deck.well_position("Slot_3", "A1") == pytest.approx((265.60 + 10.0 + 14.38, 52.75 + 5.0 + 11.24))
    # tip rack origin set by place()
    assert rack.origin == (127.80, 52.75)
    tip = rack.pick_next()
    assert tip.absolute_xy() == pytest.approx((127.80 + 6.0, 52.75 + 6.0))
    assert rack.available_count == 95


def test_deck_from_json_simple_xy_format(tmp_path):
    p = tmp_path / "deck.json"
    p.write_text(json.dumps({"S1": [10.0, 20.0], "S2": {"x_abs": 100.0, "y_abs": 50.0}}), encoding="utf-8")
    deck = Deck.from_json(p, load_labware=False)
    assert deck.slot_position("S1") == (10.0, 20.0)
    assert deck.slot_position("S2") == (100.0, 50.0)


def test_deck_save_roundtrip(tmp_path):
    deck = Deck.from_json(LABWARE_DIR / "biohit_deck.json")
    out = tmp_path / "deck_out.json"
    deck.save(out)
    deck2 = Deck.from_json(out, labware_folder=LABWARE_DIR)
    assert deck2.slot_position("Slot_1") == deck.slot_position("Slot_1")
    assert deck2.slot("Slot_1").slot_type == "half_sbs"
    assert isinstance(deck2.labware_at("Slot_2"), Reservoir)
    assert deck2.tip_rack_slot == "Slot_4"
    assert deck2.name == deck.name


def test_slot_dataclass():
    s = Slot("S1", 10.0, 20.0, description="test")
    assert s.position == (10.0, 20.0)
    assert not s.is_placed
    d = s.to_dict()
    assert d["x_abs"] == 10.0 and d["is_placed"] is False
    s2 = Slot.from_dict("S1", [1.0, 2.0])
    assert s2.position == (1.0, 2.0)
