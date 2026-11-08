"""Tip racks: grids of :class:`src.Tip.Tip` objects with pick/return bookkeeping."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

try:  # imported as part of the ``src`` package
    from .Plate import Plate
    from .Tip import Tip
except ImportError:  # src/ itself is on sys.path
    from Plate import Plate  # type: ignore
    from Tip import Tip  # type: ignore


class TipRack(Plate):
    """A rack of pipette tips.

    Each well of the rack holds one :class:`src.Tip.Tip`. The rack tracks which
    tips are still available, so a protocol can pick them one by one.
    """

    labware_type = "tip_rack"

    def __init__(self, name: str, *, tip_volume_ul: Optional[float] = None, **kwargs):
        super().__init__(name, **kwargs)
        self.tip_volume_ul = float(tip_volume_ul) if tip_volume_ul is not None else self.well_max_volume_ul
        self.tips: Dict[str, Tip] = {
            wid: Tip(wid, x, y, max_volume_ul=self.tip_volume_ul, pick_z=self.pick_z, rack=self)
            for wid, (x, y) in self.wells.items()
        }

    @classmethod
    def _from_data(cls, data: dict, *, source: Optional[Path] = None, labware_folder: Optional[Path] = None):
        obj = super()._from_data(data, source=source, labware_folder=labware_folder)
        if "tip_volume_ul" in data:
            obj.tip_volume_ul = float(data["tip_volume_ul"])
        for tip in obj.tips.values():
            tip.max_volume_ul = obj.tip_volume_ul
            tip.pick_z = obj.pick_z
        return obj

    @property
    def pick_z(self) -> Optional[float]:
        """Recommended absolute machine z for picking up a tip"""
        return self.z_limits.get("recommended_pickup_z") or self.z_limits.get("pickup_limit_z")

    @property
    def pickup_limit_z(self) -> Optional[float]:
        """Absolute machine z limit to pass to ``Pipettor.pick_tip(limit)``"""
        return self.z_limits.get("pickup_limit_z")

    @property
    def discard_z(self) -> Optional[float]:
        """Recommended absolute machine z for discarding a tip"""
        return self.z_limits.get("recommended_discard_z")

    def available_tips(self) -> List[Tip]:
        """All tips still in the rack, in column-major order"""
        return [self.tips[wid] for wid in self.well_ids if self.tips[wid].is_available]

    @property
    def available_count(self) -> int:
        """Number of tips still available"""
        return len(self.available_tips())

    def next_tip(self) -> Optional[Tip]:
        """The next available tip (column-major order), or None if the rack is empty"""
        available = self.available_tips()
        return available[0] if available else None

    def pick_next(self) -> Tip:
        """Take the next available tip: marks it used and returns it

        :raises RuntimeError: if no tips are left in the rack
        """
        tip = self.next_tip()
        if tip is None:
            raise RuntimeError(f"tip rack {self.name!r} is empty")
        tip.mark_used()
        return tip

    def return_tip(self, tip_id: str) -> Tip:
        """Return a tip to the rack (marks it available again)"""
        if tip_id not in self.tips:
            raise KeyError(f"tip rack {self.name!r} has no tip {tip_id!r}")
        tip = self.tips[tip_id]
        tip.mark_available()
        return tip

    def reset(self) -> None:
        """Mark all tips as available (e.g. after refilling the rack)"""
        for tip in self.tips.values():
            tip.mark_available()

    def to_dict(self) -> dict:
        data = super().to_dict()
        if self.tip_volume_ul is not None:
            data["tip_volume_ul"] = self.tip_volume_ul
        return data
