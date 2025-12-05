import sys
from os.path import dirname, join

if sys.version_info[:2] < (3, 8):
    import importlib_metadata as metadata
else:
    from importlib import metadata
    from importlib.metadata import version

firmware_path = join(dirname(__file__), "include")
sys.path.append(firmware_path)

try:
    import clr
    clr.AddReference("InstrumentLib")
    from InstrumentLib import InstrumentCls
    clr_instrumentcls = InstrumentCls
finally:
    sys.path.remove(firmware_path)

from .pipettor_plus import Pipettor  # noqa: E402 cannot be imported earlier, depends on this file

__version__ = metadata.version(__name__)

__all__ = ["__version__", "Pipettor"]
