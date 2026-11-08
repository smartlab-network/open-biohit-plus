"""A single pipette tip, stored in a :class:`src.TipRack.TipRack`.

A tip's descriptive attributes can be stored as JSON (see ``labware/tip.json``)::

    {
        "type": "tip",
        "tip_id": "A1",
        "x_rel": 6.0, "y_rel": 6.0,
        "max_volume_ul": 1000.0,
        "pick_z": 92.0,
        "state": "available"
    }
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Optional

try:  # imported as part of the ``src`` package
    from .Labware import WellOffset
except ImportError:  # src/ itself is on sys.path
    from Labware import WellOffset  # type: ignore

if TYPE_CHECKING:  # avoid a runtime circular import Tip <-> TipRack
    try:
        from .TipRack import TipRack
    except ImportError:
        from TipRack import TipRack  # type: ignore


class Tip:
    """A single pipette tip stored in a :class:`src.TipRack.TipRack`.

    :param tip_id: id of the tip (= the well id in the rack, e.g. ``"A1"``)
    :param x_rel: x offset of the tip inside the rack, in mm
    :param y_rel: y offset of the tip inside the rack, in mm
    :param max_volume_ul: max volume of the tip, in microliters
    :param pick_z: absolute machine z used when picking up this tip
    :param rack: the :class:`src.TipRack.TipRack` this tip belongs to
    """

    AVAILABLE = "available"
    USED = "used"

    def __init__(
        self,
        tip_id: str,
        x_rel: float,
        y_rel: float,
        *,
        max_volume_ul: Optional[float] = None,
        pick_z: Optional[float] = None,
        rack: Optional["TipRack"] = None,
    ):
        self.tip_id = tip_id
        self.x_rel = float(x_rel)
        self.y_rel = float(y_rel)
        self.max_volume_ul = max_volume_ul
        self.pick_z = pick_z
        self.rack = rack
        self.state = Tip.AVAILABLE

    @property
    def offset(self) -> WellOffset:
        """The (x_rel, y_rel) offset of the tip inside its rack, in mm"""
        return self.x_rel, self.y_rel

    @property
    def is_available(self) -> bool:
        """True if the tip is still in the rack and not used"""
        return self.state == Tip.AVAILABLE

    def mark_used(self) -> None:
        """Mark the tip as picked up / used"""
        self.state = Tip.USED

    def mark_available(self) -> None:
        """Mark the tip as returned to the rack / available again"""
        self.state = Tip.AVAILABLE

    def absolute_xy(self) -> WellOffset:
        """Absolute machine (x, y) of the tip, based on the rack origin"""
        if self.rack is None:
            return self.offset
        return self.rack.origin[0] + self.x_rel, self.rack.origin[1] + self.y_rel

    # ------------------------------------------------------------- (de)serial
    def to_dict(self) -> dict:
        """All descriptive attributes of this tip as a JSON-serializable dict"""
        return {
            "type": "tip",
            "tip_id": self.tip_id,
            "x_rel": self.x_rel,
            "y_rel": self.y_rel,
            "max_volume_ul": self.max_volume_ul,
            "pick_z": self.pick_z,
            "state": self.state,
        }

    def save(self, path) -> None:
        """Write this tip's descriptive attributes to a JSON file"""
        with Path(path).open("w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=4)

    @classmethod
    def from_dict(cls, data: dict) -> "Tip":
        """Build a tip from a parsed JSON dict (see ``labware/tip.json``)"""
        tip = cls(
            data["tip_id"],
            data.get("x_rel", 0.0),
            data.get("y_rel", 0.0),
            max_volume_ul=data.get("max_volume_ul"),
            pick_z=data.get("pick_z"),
        )
        if data.get("state") in (Tip.AVAILABLE, Tip.USED):
            tip.state = data["state"]
        return tip

    @classmethod
    def from_json(cls, path) -> "Tip":
        """Load a tip's descriptive attributes from a JSON file"""
        with Path(path).open(encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    def __repr__(self) -> str:
        return f"Tip({self.tip_id!r}, state={self.state!r}, max_volume_ul={self.max_volume_ul})"
