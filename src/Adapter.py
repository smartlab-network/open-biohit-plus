"""Adapters: carriers that hold another labware (the *child*) at an offset."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

try:  # imported as part of the ``src`` package
    from .Labware import Labware, WellOffset
except ImportError:  # src/ itself is on sys.path
    from Labware import Labware, WellOffset  # type: ignore


class Adapter(Labware):
    """A carrier/adapter that holds another labware (its *child*) at an offset.

    The adapter's wells are the child's wells shifted by ``child_offset``, so
    ``well_offset("A1")`` gives the position of the child's A1 relative to the
    adapter origin (the deck slot corner the adapter is placed in).

    JSON format::

        {
            "type": "adapter",
            "labware_name": "Plate Adapter",
            "child": {"labware_file": "corning_96_flat.json", "x_offset": 10.0, "y_offset": 5.0}
        }
    """

    labware_type = "adapter"

    def __init__(
        self,
        name: str,
        *,
        child: Optional[Labware] = None,
        child_offset: WellOffset = (0.0, 0.0),
        **kwargs,
    ):
        kwargs.pop("wells", None)  # an adapter's wells come from its child
        super().__init__(name, wells={}, **kwargs)
        self.child = child
        self.child_offset: WellOffset = (float(child_offset[0]), float(child_offset[1]))

    @classmethod
    def _from_data(cls, data: dict, *, source: Optional[Path] = None, labware_folder: Optional[Path] = None):
        obj = super()._from_data(data, source=source, labware_folder=labware_folder)
        folder = Path(labware_folder) if labware_folder is not None else (source.parent if source else Path("."))
        child_spec = data.get("child", {})
        child: Optional[Labware] = None
        if isinstance(child_spec, str):
            child = Labware.from_json(folder / child_spec, labware_folder=folder)
        elif isinstance(child_spec, dict):
            if "labware_file" in child_spec:
                child = Labware.from_json(folder / child_spec["labware_file"], labware_folder=folder)
            elif child_spec:
                child = Labware.from_dict(child_spec, labware_folder=folder)
        obj.child = child
        if isinstance(child_spec, dict) and "x_offset" in child_spec:
            obj.child_offset = (float(child_spec["x_offset"]), float(child_spec.get("y_offset", 0.0)))
        else:
            offset = data.get("child_offset", (0.0, 0.0))
            obj.child_offset = (float(offset[0]), float(offset[1]))
        return obj

    def set_child(self, child: Labware, x_offset: float = 0.0, y_offset: float = 0.0) -> None:
        """Place a labware onto this adapter at the given offset (mm, relative to the adapter origin)"""
        self.child = child
        self.child_offset = (float(x_offset), float(y_offset))

    @property
    def wells(self) -> Dict[str, WellOffset]:
        if self.child is None:
            return {}
        ox, oy = self.child_offset
        return {wid: (x + ox, y + oy) for wid, (x, y) in self.child.wells.items()}

    def to_dict(self) -> dict:
        data = super().to_dict()
        if self.child is not None:
            child: dict = {"labware_name": self.child.name}
            if self.child.source is not None:
                child["labware_file"] = self.child.source.name
            data["child"] = child
            data["child_offset"] = [self.child_offset[0], self.child_offset[1]]
        return data
