from tempfile import TemporaryDirectory

from biohit_pipettor import clr_instrumentcls
from biohit_pipettor.clr_wrapping.clr_wrappers import ClrObject


class InstrumentCls(ClrObject):
    def __init__(self):
        self.__tmp_dir = TemporaryDirectory()
        super().__init__(clr_instrumentcls(self.__tmp_dir.name))
        self.Control = ClrObject(self._wrapped_instance.Control)
        self.Control.Comm = ClrObject(self.Control._wrapped_instance.Comm)

    def __del__(self):
        self.__tmp_dir.cleanup()
        self.Dispose()
