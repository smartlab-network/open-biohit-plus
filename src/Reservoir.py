"""Reagent reservoirs / troughs / waste containers with fill-volume tracking."""

from __future__ import annotations

import math
from typing import Dict, Optional

try:  # imported as part of the ``src`` package
    from .Plate import Plate
except ImportError:  # src/ itself is on sys.path
    from Plate import Plate  # type: ignore


class Reservoir(Plate):
    """A reagent reservoir / trough / waste container.

    Usually has few, large wells (e.g. a 3-well reservoir or a 6-column
    trough). Tracks the fill volume per well, so a protocol can check how
    much reagent is left.
    """

    labware_type = "reservoir"

    def __init__(self, name: str, **kwargs):
        super().__init__(name, **kwargs)
        self._fill_ul: Dict[str, float] = {wid: 0.0 for wid in self.wells}

    @property
    def cross_section_area_mm2(self) -> Optional[float]:
        """Cross-section area of a well in mm^2 (pi * r^2); note 1 uL = 1 mm^3"""
        r = self.well_radius_mm
        return math.pi * r * r if r is not None else None

    def max_volume_ul(self, wid: str) -> float:
        """Max volume of a well in microliters (``max_volume_ul``, else computed from radius x depth)"""
        self.well_offset(wid)  # validates the well id
        if self.well_max_volume_ul is not None:
            return self.well_max_volume_ul
        r, d = self.well_radius_mm, self.well_depth_mm
        if r is not None and d is not None:
            return math.pi * r * r * d  # mm^3 == uL
        raise ValueError(f"labware {self.name!r} defines neither max_volume_ul nor radius/depth")

    def fill_volume_ul(self, wid: str) -> float:
        """Currently tracked fill volume of a well, in microliters"""
        self.well_offset(wid)
        return self._fill_ul[wid]

    def set_fill(self, wid: str, volume_ul: float) -> None:
        """Set the fill volume of a well, in microliters"""
        self.well_offset(wid)
        if volume_ul < 0:
            raise ValueError("fill volume must be >= 0")
        self._fill_ul[wid] = float(volume_ul)

    def add_volume(self, wid: str, volume_ul: float) -> None:
        """Add (or remove, if negative) volume to/from a well, in microliters"""
        self.set_fill(wid, self.fill_volume_ul(wid) + volume_ul)

    def remaining_volume_ul(self, wid: str) -> float:
        """Remaining capacity of a well, in microliters (never negative)"""
        return max(0.0, self.max_volume_ul(wid) - self.fill_volume_ul(wid))

    def liquid_height_mm(self, wid: str) -> Optional[float]:
        """Current liquid height in a well, in mm (fill volume / cross-section area)"""
        area = self.cross_section_area_mm2
        if area is None:
            return None
        return self.fill_volume_ul(wid) / area  # 1 uL = 1 mm^3
