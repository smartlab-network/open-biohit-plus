"""Multi-well plates (e.g. 96-well plates, 42/48-well EHM plates)."""

from __future__ import annotations

from typing import List, Optional

try:  # imported as part of the ``src`` package
    from .Labware import Labware, WellOffset, _build_grid_wells
except ImportError:  # src/ itself is on sys.path
    from Labware import Labware, WellOffset, _build_grid_wells  # type: ignore


class Plate(Labware):
    """A multi-well plate (e.g. a 96-well plate or a 48-well EHM plate)."""

    labware_type = "plate"

    @classmethod
    def from_grid(
        cls,
        name: str,
        rows: int,
        columns: int,
        *,
        well_a1_offset: WellOffset = (0.0, 0.0),
        spacing: WellOffset = (9.0, 9.0),
        col_x: Optional[List[float]] = None,
        row_y: Optional[List[float]] = None,
        **kwargs,
    ) -> "Plate":
        """Create a plate from a regular grid

        :param rows: number of rows (A, B, ...)
        :param columns: number of columns (1, 2, ...)
        :param well_a1_offset: (x, y) offset of well A1 relative to the plate origin, in mm
        :param spacing: (x, y) pitch between neighboring wells, in mm (may be negative)
        :param col_x: optional explicit x offset per column (overrides a1/spacing math)
        :param row_y: optional explicit y offset per row
        """
        wells = _build_grid_wells(
            {"rows": rows, "columns": columns},
            {"x": well_a1_offset[0], "y": well_a1_offset[1]},
            {"x": spacing[0], "y": spacing[1]},
            col_x,
            row_y,
        )
        return cls(name, wells=wells, **kwargs)
