"""
Smoke tests - Basic checks that the app can start and imports work
"""
import pytest


def test_core_package_import():
    """Test that core package can be imported"""
    import biohit_pipettor_plus
    assert biohit_pipettor_plus is not None


def test_gui_module_import():
    """Test that GUI module can be imported (no GUI launch)"""
    from biohit_pipettor_plus.gui import gui2
    assert gui2 is not None

def test_gui_main_exists():
    """Test that gui2.main() function exists"""
    from biohit_pipettor_plus.gui import gui2
    assert hasattr(gui2, "main"), "gui2.main() missing"

def test_dll_dependency_import():
    """Test that DLL-backed dependency (open_biohit) can be imported"""
    import biohit_pipettor
    assert biohit_pipettor is not None
