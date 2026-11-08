"""open-biohit-plus: deck layout and labware model on top of ``biohit_pipettor``.

- open-biohit (``biohit_pipettor``) wraps the machine control DLL (hardware only)
- this package adds the lab logic, one file per class in ``src/``:
  :class:`deck.Deck` / :class:`deck.Slot` (deck layout) and the labware types
  :class:`Plate.Plate`, :class:`Adapter.Adapter`, :class:`TipRack.TipRack`
  (holding :class:`Tip.Tip` objects) and :class:`Reservoir.Reservoir`,
  with :class:`Labware.Labware` as their base class.
"""

try:  # imported as a package
    from .Adapter import Adapter
    from .deck import Deck, Position, Position3D, Slot
    from .Labware import Labware, WellOffset, default_labware_folder
    from .Plate import Plate
    from .Reservoir import Reservoir
    from .Tip import Tip
    from .TipRack import TipRack
except ImportError:  # src/ itself is on sys.path
    from Adapter import Adapter  # type: ignore
    from deck import Deck, Position, Position3D, Slot  # type: ignore
    from Labware import Labware, WellOffset, default_labware_folder  # type: ignore
    from Plate import Plate  # type: ignore
    from Reservoir import Reservoir  # type: ignore
    from Tip import Tip  # type: ignore
    from TipRack import TipRack  # type: ignore

__all__ = [
    "Adapter",
    "Deck",
    "Labware",
    "Plate",
    "Position",
    "Position3D",
    "Reservoir",
    "Slot",
    "Tip",
    "TipRack",
    "WellOffset",
    "default_labware_folder",
]
