import sys
import warnings
from os.path import dirname, join

# __all__ = []

# package version
if sys.version_info[:2] < (3, 8):
    import importlib_metadata as metadata
else:
    from importlib import metadata
__version__ = metadata.version(__name__)

from .abstract_pipettor import AbstractPipettor

# PipettorSimulator (requires matplotlib)
try:
    from .pipettor_simulator import PipettorSimulator

except ImportError:
    warnings.warn(ImportWarning("matplotlib not installed, PipettorSimulator not available"))
    pass

firmware_path = join(dirname(__file__), "include")
sys.path.append(firmware_path)

# Pipettor (requires libmono)
try:
    import clr

    clr.AddReference("InstrumentLib")
    from InstrumentLib import InstrumentCls

    clr_instrumentcls = InstrumentCls
    from .pipettor import Pipettor

except ImportError:
    warnings.warn(ImportWarning("pythonnet not installed, Pipettor not available"))
    pass
finally:
    sys.path.remove(firmware_path)

__all__ = ["__version__", "Pipettor", "AbstractPipettor", "PipettorSimulator"]
