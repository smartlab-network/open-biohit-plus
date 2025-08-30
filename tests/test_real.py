from biohit_pipettor import Pipettor
from biohit_pipettor.errors import NotConnected


def test_abstract_methods_are_implemented():
    try:
        with Pipettor(200, multichannel=False, initialize=False):
            pass
    except NotConnected:
        pass
