"""Base labware class and shared helpers for the Biohit Roboline deck.

open-biohit (the ``biohit_pipettor`` package) only wraps the machine control
DLL. The lab-logic layer on top of it lives in one file per class:

- :class:`src.Labware.Labware`       -- this file: base class + shared helpers
- :class:`src.Plate.Plate`           -- multi-well plates
- :class:`src.Adapter.Adapter`       -- carriers holding a child labware at an offset
- :class:`src.TipRack.TipRack`       -- racks of :class:`src.Tip.Tip` objects
- :class:`src.Reservoir.Reservoir`   -- reagent troughs / waste with volume tracking

All labware is described by JSON files (see the ``labware/`` folder). Well
coordinates are *relative to the labware origin* (the corner of the deck slot
the labware is placed in), in millimeters. The absolute machine position of a
well is ``slot_position + well_offset`` (see :class:`src.deck.Deck`).

JSON format (all keys except ``labware_name`` are optional)::

    {
        "type": "plate",                  # plate | adapter | tip_rack | reservoir
        "labware_name": "96 Well Flat",   # human readable name
        "z_height_mm": 14.35,             # height of the labware
        "grid": {"rows": 8, "columns": 12},
        "well_a1_offset": {"x": 14.38, "y": 11.24},
        "spacing": {"x": 9.0, "y": 9.0},
        "col_x": [...], "row_y": [...],   # optional: explicit per-column/row offsets
        "well_properties": {"depth_mm": 10.8, "radius_mm": 3.43, "max_volume_ul": 360.0},
        "z_limits": {"recommended_aspirate_z": 92.0, "recommended_dispense_z": 85.0,
                     "max_safe_bottom_z": 94.0},
        "wells": {"A1": {"x_rel": 14.38, "y_rel": 11.24}, ...}   # optional explicit wells
    }

If ``wells`` is given it wins over the grid definition. ``z_limits`` values
are absolute machine Z positions (on the Biohit, z=0 is the top, larger z is
lower).
"""

from __future__ import annotations

import importlib
import json
import os
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple, Type

try:  # imported as part of the ``src`` package
    from .baseclass import Baseclass
except ImportError:  # src/ itself is on sys.path
    from baseclass import Baseclass  # type: ignore

WellOffset = Tuple[float, float]

#: default labware library location (overridable via the LABWARE_DIR env var)
DEFAULT_LABWARE_FOLDER = r"C:\Labhub\Import\Labware"
LABWARE_ENV = "LABWARE_DIR"


def default_labware_folder() -> Path:
    """The labware library folder: $LABWARE_DIR, else the repo's ``labware/``, else the default path."""
    env_dir = os.environ.get(LABWARE_ENV)
    if env_dir:
        return Path(env_dir)
    repo_labware = Path(__file__).resolve().parent.parent / "labware"
    if repo_labware.is_dir():
        return repo_labware
    return Path(DEFAULT_LABWARE_FOLDER)


def well_id(row: int, column: int) -> str:
    """Well id from 0-based row/column, e.g. ``well_id(0, 0) == "A1"``."""
    return f"{chr(65 + row)}{column + 1}"


def _well_sort_key(wid: str) -> Tuple[int, int]:
    # column-major order (like Opentrons tip racks): A1, B1, ..., H1, A2, ...
    return int(wid[1:]), ord(wid[0]) - 65


def _build_grid_wells(
    grid: dict,
    a1_offset: dict,
    spacing: dict,
    col_x: Optional[List[float]] = None,
    row_y: Optional[List[float]] = None,
) -> Dict[str, WellOffset]:
    """Generate ``{well_id: (x_rel, y_rel)}`` from a grid definition.

    ``col_x``/``row_y`` (explicit per-column x / per-row y values) take
    precedence over ``a1_offset + index * spacing``. Negative spacing can be
    used for plates whose columns run in -x direction.
    """
    rows = int(grid.get("rows", 0))
    columns = int(grid.get("columns", 0))
    wells: Dict[str, WellOffset] = {}
    for r in range(rows):
        for c in range(columns):
            if col_x is not None and row_y is not None:
                x, y = float(col_x[c]), float(row_y[r])
            else:
                x = float(a1_offset.get("x", 0.0)) + c * float(spacing.get("x", 0.0))
                y = float(a1_offset.get("y", 0.0)) + r * float(spacing.get("y", 0.0))
            wells[well_id(r, c)] = (x, y)
    return wells


def _parse_explicit_wells(wells: dict) -> Dict[str, WellOffset]:
    return {wid: (float(w.get("x_rel", 0.0)), float(w.get("y_rel", 0.0))) for wid, w in wells.items()}


def _infer_type(data: dict, source: Optional[Path]) -> str:
    """Infer the labware type from the JSON content / file name if no ``type`` key is present."""
    name = str(data.get("labware_name", "")).lower()
    fname = source.stem.lower() if source is not None else ""
    haystack = f"{name} {fname}"
    if "tip" in haystack:
        return "tip_rack"
    if "reservoir" in haystack or "trough" in haystack or "waste" in haystack:
        return "reservoir"
    if "adapter" in haystack:
        return "adapter"
    return "plate"


class Labware(Baseclass):
    """Base class for everything that can be placed on the deck.

    Subclasses (one file per class) register themselves in
    :attr:`Labware._registry` via ``labware_type``:
    :class:`src.Plate.Plate`, :class:`src.Adapter.Adapter`,
    :class:`src.TipRack.TipRack`, :class:`src.Reservoir.Reservoir`.

    :param name: human readable name of the labware
    :param z_height_mm: height of the labware, in mm
    :param z_limits: absolute machine z limits (aspirate/dispense/pickup z, ...)
    :param well_properties: shared well properties (radius_mm, depth_mm, max_volume_ul, ...)
    :param wells: ``{well_id: (x_rel, y_rel)}`` relative to the labware origin, in mm
    :param origin: absolute machine (x, y) of the labware origin (set by :meth:`src.deck.Deck.place`)
    :param extra: raw extra keys from the JSON file (kept for forward compatibility)
    :param source: path of the JSON file this labware was loaded from
    """

    labware_type = "labware"

    _registry: Dict[str, Type["Labware"]] = {}

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        Labware._registry[cls.labware_type] = cls

    def __init__(
        self,
        name: str,
        *,
        z_height_mm: float = 0.0,
        z_limits: Optional[dict] = None,
        well_properties: Optional[dict] = None,
        wells: Optional[Dict[str, WellOffset]] = None,
        origin: WellOffset = (0.0, 0.0),
        extra: Optional[dict] = None,
        source: Optional[Path] = None,
    ):
        super().__init__()
        self.name = name
        self.z_height_mm = float(z_height_mm)
        self.z_limits: Dict[str, float] = {k: float(v) for k, v in (z_limits or {}).items()}
        self.well_properties: Dict[str, float] = dict(well_properties or {})
        self._wells: Dict[str, WellOffset] = dict(wells or {})
        self._origin: WellOffset = (float(origin[0]), float(origin[1]))
        self.extra: dict = dict(extra or {})
        self.source = Path(source) if source is not None else None

    # ------------------------------------------------------------------ wells
    @property
    def wells(self) -> Dict[str, WellOffset]:
        """``{well_id: (x_rel, y_rel)}`` of this labware, relative to its origin, in mm"""
        return self._wells

    @property
    def well_ids(self) -> List[str]:
        """All well ids in column-major order (A1, B1, ..., H1, A2, ...)"""
        return sorted(self.wells, key=_well_sort_key)

    def __iter__(self) -> Iterator[str]:
        return iter(self.well_ids)

    def __len__(self) -> int:
        return len(self.wells)

    def __contains__(self, wid: str) -> bool:
        return wid in self.wells

    def well_offset(self, wid: str) -> WellOffset:
        """The (x_rel, y_rel) offset of a well, in mm

        :param wid: well id, e.g. ``"A1"``
        :raises KeyError: if the labware has no such well
        """
        try:
            return self.wells[wid]
        except KeyError:
            raise KeyError(f"labware {self.name!r} has no well {wid!r}") from None

    # --------------------------------------------------------------- position
    @property
    def origin(self) -> WellOffset:
        """Absolute machine (x, y) of the labware origin (the deck slot corner)"""
        return self._origin

    @origin.setter
    def origin(self, value: WellOffset) -> None:
        self._origin = (float(value[0]), float(value[1]))

    def absolute_xy(self, wid: str) -> WellOffset:
        """Absolute machine (x, y) of a well: ``origin + well_offset``"""
        x_rel, y_rel = self.well_offset(wid)
        return self._origin[0] + x_rel, self._origin[1] + y_rel

    # --------------------------------------------------------------------- z
    def _z(self, limit_key: str, z_key: str) -> Optional[float]:
        if limit_key in self.z_limits:
            return self.z_limits[limit_key]
        z = self.extra.get("z", {})
        if z_key in z:
            return float(z[z_key])
        return None

    @property
    def aspirate_z(self) -> Optional[float]:
        """Recommended absolute machine z for aspirating (``z_limits``, else the ``z`` block)"""
        return self._z("recommended_aspirate_z", "aspirate")

    @property
    def dispense_z(self) -> Optional[float]:
        """Recommended absolute machine z for dispensing"""
        return self._z("recommended_dispense_z", "dispense")

    @property
    def max_safe_bottom_z(self) -> Optional[float]:
        """Maximum absolute machine z the tip may reach inside a well (safety limit)"""
        return self.z_limits.get("max_safe_bottom_z")

    # ------------------------------------------------------- well properties
    @property
    def well_radius_mm(self) -> Optional[float]:
        """Well radius in mm (from ``radius_mm``, or half of ``diameter_mm``)"""
        if "radius_mm" in self.well_properties:
            return float(self.well_properties["radius_mm"])
        if "diameter_mm" in self.well_properties:
            return float(self.well_properties["diameter_mm"]) / 2.0
        return None

    @property
    def well_depth_mm(self) -> Optional[float]:
        """Well depth in mm"""
        return float(self.well_properties["depth_mm"]) if "depth_mm" in self.well_properties else None

    @property
    def well_max_volume_ul(self) -> Optional[float]:
        """Max volume per well in microliters (``max_volume_ul``), if defined"""
        return float(self.well_properties["max_volume_ul"]) if "max_volume_ul" in self.well_properties else None

    # ------------------------------------------------------------- (de)serial
    def to_dict(self) -> dict:
        """Serialize back to the JSON dict format"""
        data = dict(self.extra)
        data["type"] = self.labware_type
        data["labware_name"] = self.name
        data["z_height_mm"] = self.z_height_mm
        if self.z_limits:
            data["z_limits"] = dict(self.z_limits)
        if self.well_properties:
            data["well_properties"] = dict(self.well_properties)
        data["wells"] = {wid: {"x_rel": x, "y_rel": y} for wid, (x, y) in self.wells.items()}
        return data

    def save(self, path) -> None:
        """Write this labware to a JSON file"""
        with Path(path).open("w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=4)

    @classmethod
    def _from_data(cls, data: dict, *, source: Optional[Path] = None, labware_folder: Optional[Path] = None):
        name = data.get("labware_name") or (Path(source).stem if source is not None else cls.labware_type)
        if "wells" in data:
            wells = _parse_explicit_wells(data["wells"])
        else:
            wells = _build_grid_wells(
                data.get("grid", {}),
                data.get("well_a1_offset", {}),
                data.get("spacing", {}),
                data.get("col_x"),
                data.get("row_y"),
            )
        return cls(
            name,
            z_height_mm=data.get("z_height_mm", 0.0),
            z_limits=data.get("z_limits"),
            well_properties=data.get("well_properties"),
            wells=wells,
            extra=data,
            source=source,
        )

    @staticmethod
    def _load_type(type_name: str) -> Optional[Type["Labware"]]:
        """Lazily import the module of a labware subclass (one file per class) so it
        registers itself in :attr:`_registry`, e.g. ``tip_rack`` -> ``TipRack.py``."""
        cls_name = "".join(part.capitalize() for part in type_name.split("_"))
        try:
            if __package__:
                importlib.import_module(f".{cls_name}", package=__package__)
            else:
                importlib.import_module(cls_name)
        except ImportError:
            pass
        return Labware._registry.get(type_name)

    @classmethod
    def from_dict(cls, data: dict, *, source: Optional[Path] = None, labware_folder: Optional[Path] = None):
        """Build a labware object from a parsed JSON dict.

        When called on :class:`Labware` itself, the concrete class is chosen
        via the ``type`` key (or inferred from the content/file name); when
        called on a subclass, that subclass is used.
        """
        if cls is Labware:
            type_name = data.get("type") or _infer_type(data, source)
            target = Labware._registry.get(type_name) or Labware._load_type(type_name) or Labware
        else:
            target = cls
        return target._from_data(data, source=source, labware_folder=labware_folder)

    @classmethod
    def from_json(cls, path, labware_folder=None) -> "Labware":
        """Load a labware definition from a JSON file

        :param path: path to the labware JSON file
        :param labware_folder: folder used to resolve referenced files (e.g. an
            adapter's child); defaults to the folder containing ``path``
        """
        path = Path(path)
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data, source=path, labware_folder=labware_folder or path.parent)

    @classmethod
    def load_library(cls, folder=None) -> Dict[str, "Labware"]:
        """Load all labware ``*.json`` definitions in a folder into ``{name: Labware}``.

        Deck layout files (``deck*.json``) are skipped. Broken files are
        skipped with a warning.
        """
        folder = Path(folder) if folder is not None else default_labware_folder()
        library: Dict[str, Labware] = {}
        if folder.is_dir():
            for f in sorted(folder.glob("*.json")):
                if "deck" in f.stem.lower():
                    continue  # deck layouts (e.g. biohit_deck.json) are not labware
                try:
                    with f.open(encoding="utf-8") as fh:
                        head = json.load(fh)
                    if not isinstance(head, dict) or "labware_name" not in head:
                        continue  # e.g. a single tip definition (tip.json) is not labware
                    lw = cls.from_dict(head, source=f, labware_folder=folder)
                except (OSError, json.JSONDecodeError, KeyError, ValueError) as e:
                    print(f"warning: skipping labware file {f}: {e}")
                    continue
                library[lw.name] = lw
        return library

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.name!r}, wells={len(self)})"
