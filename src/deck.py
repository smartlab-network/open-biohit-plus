"""Deck layout for the Biohit Roboline pipettor.

The :class:`Deck` knows the slots of the machine bed (their absolute x/y
positions) and which :class:`src.Labware.Labware` is placed in each slot. It
turns relative labware well offsets into absolute machine coordinates::

    absolute well position = slot position + labware well offset

A deck layout is stored as JSON (see ``labware/biohit_deck.json``)::

    {
        "deck_name": "Biohit Roboline deck",
        "machine": {"brand": "Biohit / Custom", "max_x_mm": 300.0, ...},
        "slots": {
            "Slot_1": {"x_abs": 265.60, "y_abs": 0.09, "width_mm": 127.76, "height_mm": 42.74,
                       "slot_type": "half_sbs", "position": "back",
                       "labware_file": "ehm_42_well.json", "description": "EHM plate"},
            "Slot_4": {"x_abs": 127.80, "y_abs": 52.75, "slot_type": "sbs", "position": "front",
                       "labware_file": "tip_rack_1000ul.json"},
            ...
        },
        "_tip_slot": "Slot_4",
        "_ref_points": {"P1": [239.49, 43.0, 6.8], ...}
    }

The Biohit deck has two half-SBS slots in the back (Slot_1, Slot_2) and a
2x2 block of SBS slots in the front (Slot_3..Slot_6). Plain flat layouts
(``"Slot_1": {"x_abs": ..., "y_abs": ...}`` or ``"Slot_1": [x, y]``) are
accepted as well. Reference points (P1..P3, used for deck calibration) are
stored under the special ``"_ref_points"`` key.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterator, List, Mapping, Optional, Tuple, Union

try:  # imported as part of the ``src`` package
    from .baseclass import Baseclass
    from .Labware import Labware, default_labware_folder
    from .TipRack import TipRack
except ImportError:  # src/ itself is on sys.path
    from baseclass import Baseclass  # type: ignore
    from Labware import Labware, default_labware_folder  # type: ignore
    from TipRack import TipRack  # type: ignore

Position = Tuple[float, float]
Position3D = Tuple[float, float, float]


@dataclass
class Slot:
    """One slot of the deck bed.

    :param name: slot name, e.g. ``"Slot_1"``
    :param x_abs: absolute machine x of the slot corner, in mm
    :param y_abs: absolute machine y of the slot corner, in mm
    :param width_mm: slot width in x direction, in mm
    :param height_mm: slot height in y direction, in mm
    :param z_offset: height offset of the slot surface, in mm
    :param description: free text
    :param slot_type: footprint type of the slot, e.g. ``"sbs"`` (127.76 x 85.48 mm)
        or ``"half_sbs"`` (127.76 x 42.74 mm)
    :param metadata: any other descriptive attributes from the JSON entry
        (e.g. ``position``: back/front, ``row``, ``column``)
    :param labware: the :class:`~src.Labware.Labware` placed in this slot (if any)
    :param labware_file: file name of the labware placed in this slot (if loaded from JSON)
    """

    name: str
    x_abs: float
    y_abs: float
    width_mm: float = 127.76
    height_mm: float = 85.48
    z_offset: float = 0.0
    description: str = ""
    slot_type: str = "sbs"
    metadata: Dict[str, object] = field(default_factory=dict)
    labware: Optional[Labware] = None
    labware_file: Optional[str] = None

    @property
    def position(self) -> Position:
        """Absolute machine (x, y) of the slot corner"""
        return self.x_abs, self.y_abs

    @property
    def is_placed(self) -> bool:
        """True if a labware is placed in this slot"""
        return self.labware is not None

    @classmethod
    def from_dict(cls, name: str, data: Union[dict, list, tuple]) -> "Slot":
        """Build a slot from a JSON entry (dict with x_abs/y_abs, or a plain [x, y] pair)"""
        if isinstance(data, (list, tuple)):
            return cls(name, float(data[0]), float(data[1]))
        known = {
            "name",
            "x_abs",
            "y_abs",
            "width_mm",
            "height_mm",
            "z_offset",
            "description",
            "labware_file",
            "slot_type",
            "is_placed",
        }
        metadata = {k: v for k, v in data.items() if k not in known}
        return cls(
            name,
            float(data["x_abs"]),
            float(data["y_abs"]),
            width_mm=float(data.get("width_mm", 127.76)),
            height_mm=float(data.get("height_mm", 85.48)),
            z_offset=float(data.get("z_offset", 0.0)),
            description=str(data.get("description", "")),
            slot_type=str(data.get("slot_type", "sbs")),
            metadata=metadata,
            labware_file=data.get("labware_file"),
        )

    def to_dict(self) -> dict:
        data: dict = {
            "name": self.name,
            "x_abs": self.x_abs,
            "y_abs": self.y_abs,
            "width_mm": self.width_mm,
            "height_mm": self.height_mm,
            "z_offset": self.z_offset,
            "slot_type": self.slot_type,
            "is_placed": self.is_placed,
        }
        data.update(self.metadata)
        if self.description:
            data["description"] = self.description
        if self.labware is not None and self.labware.source is not None:
            data["labware_file"] = self.labware.source.name
        elif self.labware_file:
            data["labware_file"] = self.labware_file
        return data


class Deck(Baseclass):
    """The deck (machine bed) of the Biohit Roboline: its slots and what is placed in them.

    :param slots: optional ``{slot_name: Slot | (x, y)}``; if None, the default
        Biohit layout is used: two half-SBS slots in the back (Slot_1, Slot_2)
        and a 2x2 block of SBS slots in the front (Slot_3..Slot_6)
    :param name: deck name (e.g. ``"Biohit Roboline deck"``)
    :param machine: optional machine description dict (travel limits, brand, ...)
    :param labware_folder: folder with labware JSON files (default: $LABWARE_DIR,
        else the repo's ``labware/`` folder, else ``C:\\Labhub\\Import\\Labware``)
    :param tip_slot: name of the slot the tip rack is placed in (default ``"Slot_4"``)
    :param ref_points: optional ``{name: (x, y, z)}`` calibration reference points
    """

    #: default slot positions of the machine bed: {slot: (x_abs, y_abs)} in mm
    DEFAULT_SLOT_POSITIONS: Dict[str, Position] = {
        "Slot_1": (265.60, 0.09),  # back row, half-SBS
        "Slot_2": (127.80, 0.00),  # back row, half-SBS
        "Slot_3": (265.60, 52.75),  # front 2x2 block, SBS
        "Slot_4": (127.80, 52.75),  # front 2x2 block, SBS
        "Slot_5": (265.60, 148.25),  # front 2x2 block, SBS
        "Slot_6": (127.80, 148.25),  # front 2x2 block, SBS
    }

    #: default slot footprint types
    DEFAULT_SLOT_TYPES: Dict[str, str] = {
        "Slot_1": "half_sbs",
        "Slot_2": "half_sbs",
        "Slot_3": "sbs",
        "Slot_4": "sbs",
        "Slot_5": "sbs",
        "Slot_6": "sbs",
    }

    #: default calibration reference points: {name: (x, y, z)} in mm
    DEFAULT_REF_POINTS: Dict[str, Position3D] = {
        "P1": (239.49, 43.00, 6.80),
        "P2": (26.11, 43.00, 6.80),
        "P3": (132.80, 170.50, 41.40),
    }

    DEFAULT_TIP_SLOT = "Slot_4"
    DEFAULT_NAME = "Biohit Roboline deck"

    def __init__(
        self,
        slots: Optional[Mapping[str, Union[Slot, Position]]] = None,
        *,
        name: Optional[str] = None,
        machine: Optional[dict] = None,
        labware_folder=None,
        tip_slot: Optional[str] = None,
        ref_points: Optional[Dict[str, Position3D]] = None,
    ):
        super().__init__()
        self.name = name or self.DEFAULT_NAME
        self.machine: dict = dict(machine or {})
        self.labware_folder = Path(labware_folder) if labware_folder is not None else default_labware_folder()
        self._slots: Dict[str, Slot] = {}
        if slots is None:
            for slot_name, (x, y) in self.DEFAULT_SLOT_POSITIONS.items():
                self._slots[slot_name] = Slot(slot_name, x, y, slot_type=self.DEFAULT_SLOT_TYPES.get(slot_name, "sbs"))
        else:
            for slot_name, s in slots.items():
                self._slots[slot_name] = s if isinstance(s, Slot) else Slot(slot_name, s[0], s[1])
        self._tip_slot = tip_slot or self.DEFAULT_TIP_SLOT
        self.ref_points: Dict[str, Position3D] = dict(ref_points or self.DEFAULT_REF_POINTS)

    # ------------------------------------------------------------------ slots
    def add_slot(
        self,
        slot: Union[str, Slot],
        x_abs: Optional[float] = None,
        y_abs: Optional[float] = None,
        **kwargs,
    ) -> Slot:
        """Add a slot to the deck

        :param slot: a :class:`Slot`, or a slot name (then ``x_abs``/``y_abs`` are required)
        """
        if isinstance(slot, Slot):
            self._slots[slot.name] = slot
            return slot
        if x_abs is None or y_abs is None:
            raise ValueError("x_abs and y_abs are required when adding a slot by name")
        s = Slot(slot, float(x_abs), float(y_abs), **kwargs)
        self._slots[s.name] = s
        return s

    def slot(self, name: str) -> Slot:
        """The slot with the given name

        :raises KeyError: if there is no such slot
        """
        try:
            return self._slots[name]
        except KeyError:
            raise KeyError(f"deck has no slot {name!r} (slots: {sorted(self._slots)})") from None

    @property
    def slots(self) -> Dict[str, Slot]:
        """All slots: ``{slot_name: Slot}``"""
        return dict(self._slots)

    @property
    def slot_names(self) -> list:
        """All slot names"""
        return list(self._slots)

    def __iter__(self) -> Iterator[str]:
        return iter(self._slots)

    def __len__(self) -> int:
        return len(self._slots)

    def __contains__(self, name: str) -> bool:
        return name in self._slots

    def slot_position(self, name: str) -> Position:
        """Absolute machine (x, y) of a slot corner, in mm"""
        return self.slot(name).position

    def slots_of_type(self, slot_type: str) -> List[Slot]:
        """All slots with the given footprint type, e.g. ``"half_sbs"`` or ``"sbs"``"""
        return [s for s in self._slots.values() if s.slot_type == slot_type]

    @property
    def back_slots(self) -> List[Slot]:
        """The slots in the back row (metadata ``position == "back"``, else the half-SBS slots)"""
        back = [s for s in self._slots.values() if s.metadata.get("position") == "back"]
        return back or self.slots_of_type("half_sbs")

    @property
    def front_slots(self) -> List[Slot]:
        """The slots in the front block (metadata ``position == "front"``, else the SBS slots)"""
        front = [s for s in self._slots.values() if s.metadata.get("position") == "front"]
        return front or self.slots_of_type("sbs")

    # ------------------------------------------------------- placing labware
    def place(self, slot_name: str, labware: Labware) -> Labware:
        """Place a labware into a slot; sets the labware origin to the slot corner

        :param slot_name: name of the deck slot
        :param labware: the :class:`~src.Labware.Labware` to place
        :return: the placed labware
        """
        slot = self.slot(slot_name)
        slot.labware = labware
        labware.origin = slot.position
        if labware.source is not None:
            slot.labware_file = labware.source.name
        return labware

    def unplace(self, slot_name: str) -> None:
        """Remove the labware from a slot (the slot itself stays)"""
        slot = self.slot(slot_name)
        if slot.labware is not None:
            slot.labware.origin = (0.0, 0.0)
        slot.labware = None
        slot.labware_file = None

    def labware_at(self, slot_name: str) -> Optional[Labware]:
        """The labware placed in a slot, or None"""
        return self.slot(slot_name).labware

    # ------------------------------------------------------ absolute positions
    def well_position(self, slot_name: str, wid: str) -> Position:
        """Absolute machine (x, y) of a well: ``slot position + labware well offset``

        :param slot_name: name of the deck slot the labware is placed in
        :param wid: well id inside the labware, e.g. ``"A1"``
        :raises ValueError: if the slot has no labware
        :raises KeyError: if the labware has no such well
        """
        slot = self.slot(slot_name)
        if slot.labware is None:
            raise ValueError(f"slot {slot_name!r} has no labware placed")
        x_rel, y_rel = slot.labware.well_offset(wid)
        return slot.x_abs + x_rel, slot.y_abs + y_rel

    def well_position_xyz(self, slot_name: str, wid: str, z: Optional[float] = None) -> Position3D:
        """Absolute machine (x, y, z) of a well.

        :param z: absolute machine z; if None, the labware's ``aspirate_z`` is
            used (falling back to its ``z_height_mm``)
        """
        slot = self.slot(slot_name)
        x, y = self.well_position(slot_name, wid)
        if z is None:
            lw = slot.labware
            assert lw is not None  # well_position() already raised if the slot is empty
            z = lw.aspirate_z if lw.aspirate_z is not None else lw.z_height_mm
        return x, y, float(z)

    # --------------------------------------------------------------- tip rack
    @property
    def tip_rack_slot(self) -> str:
        """Name of the slot the tip rack is placed in"""
        return self._tip_slot

    @tip_rack_slot.setter
    def tip_rack_slot(self, name: str) -> None:
        self._tip_slot = name

    @property
    def tip_rack(self) -> Optional[TipRack]:
        """The :class:`~src.TipRack.TipRack` placed in the tip slot (None if absent or not a rack)"""
        lw = self.labware_at(self._tip_slot)
        return lw if isinstance(lw, TipRack) else None

    # legacy API of the old deck.py (kept for backward compatibility)
    @property
    def tipPosition(self) -> str:
        """Legacy alias of :attr:`tip_rack_slot`"""
        return self._tip_slot

    @tipPosition.setter
    def tipPosition(self, name: str) -> None:
        self._tip_slot = name

    def tipCoordinates(self) -> Position:
        """Legacy alias of ``slot_position(tip_rack_slot)``"""
        return self.slot_position(self._tip_slot)

    # ------------------------------------------------------------- (de)serial
    @classmethod
    def from_json(cls, path, labware_folder=None, *, load_labware: bool = True) -> "Deck":
        """Load a deck layout from a JSON file

        :param path: path to the deck JSON file
        :param labware_folder: folder with the labware JSON files referenced by
            ``labware_file`` entries; defaults to the folder containing ``path``
        :param load_labware: if True, immediately load and place all referenced labware
        """
        path = Path(path)
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        folder = Path(labware_folder) if labware_folder is not None else path.parent
        ref_points = data.pop("_ref_points", None)
        tip_slot = data.pop("_tip_slot", None)
        name = data.get("deck_name") or data.get("name") or path.stem
        machine = data.get("machine")
        if "slots" in data:
            slots_data = data["slots"]
        else:  # flat layout: top-level entries that look like slots
            slots_data = {
                k: v for k, v in data.items() if isinstance(v, (list, tuple)) or (isinstance(v, dict) and "x_abs" in v)
            }
        slots = {
            slot_name: Slot.from_dict(slot_name, entry)
            for slot_name, entry in slots_data.items()
            if isinstance(entry, (dict, list, tuple))
        }
        deck = cls(slots, name=name, machine=machine, labware_folder=folder, tip_slot=tip_slot, ref_points=ref_points)
        if load_labware:
            deck.load_labware()
        return deck

    def load_labware(self, folder=None) -> int:
        """Load and place the labware referenced by the slots' ``labware_file`` entries

        :return: number of slots that got labware placed
        """
        folder = Path(folder) if folder is not None else self.labware_folder
        placed = 0
        for slot in self._slots.values():
            if slot.labware is None and slot.labware_file:
                lw = Labware.from_json(folder / slot.labware_file, labware_folder=folder)
                self.place(slot.name, lw)
                placed += 1
        return placed

    def to_dict(self) -> dict:
        """Serialize the deck layout (incl. slot types, machine info and placed labware
        file names) to a JSON dict in the ``biohit_deck.json`` format"""
        data: dict = {
            "deck_name": self.name,
            "slots": {name: slot.to_dict() for name, slot in self._slots.items()},
            "_tip_slot": self._tip_slot,
            "_ref_points": {k: list(v) for k, v in self.ref_points.items()},
        }
        if self.machine:
            data["machine"] = dict(self.machine)
        return data

    def save(self, path) -> None:
        """Write the deck layout to a JSON file"""
        with Path(path).open("w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=4)

    def __repr__(self) -> str:
        placed = sum(1 for s in self._slots.values() if s.is_placed)
        return f"Deck(slots={len(self._slots)}, placed={placed}, tip_slot={self._tip_slot!r})"
