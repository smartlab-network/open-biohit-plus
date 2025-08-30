import pytest

from biohit_pipettor import PipettorSimulator


def test_require_context_manager():
    with pytest.raises(RuntimeError):
        p = PipettorSimulator(200, multichannel=False, initialize=True)
        p.move_x(10)

    with PipettorSimulator(200, multichannel=False, initialize=True) as p:
        p.move_x(10)


def test_require_initialize():
    with pytest.raises(RuntimeError):
        with PipettorSimulator(200, multichannel=False, initialize=False) as p:
            p.move_x(10)


def test_multichannel_requires_1000uL():
    with pytest.raises(RuntimeError):
        with PipettorSimulator(200, multichannel=True, initialize=True):
            pass


def test_constants():
    with PipettorSimulator(1000, multichannel=True, initialize=True) as p:
        assert p.is_multichannel is True
        assert p.is_connected is True
        p.wait_until_stopped()  # does nothing
    with PipettorSimulator(1000, multichannel=False, initialize=True) as p:
        assert p.is_multichannel is False
        assert p.is_connected is True
        p.wait_until_stopped()  # does nothing


def test_liquid_handling_requires_tip():
    with PipettorSimulator(200, multichannel=False, initialize=True) as p:
        with pytest.raises(RuntimeError):
            p.aspirate(10)
        with pytest.raises(RuntimeError):
            p.dispense(10)
        with pytest.raises(RuntimeError):
            p.dispense_all()


def test_volume_tracking():
    with PipettorSimulator(200, multichannel=False, initialize=True) as p:
        p.pick_tip(70)
        p.aspirate(100)
        p.aspirate(100)

        with pytest.raises(RuntimeError):
            p.aspirate(5)  # tip can only hold 200

        p.dispense(100)
        p.dispense(100.00001)  # floating point imprecisions
        assert p._volume == 0

        p.aspirate(100)
        assert p._volume == 100
        p.dispense_all()
        assert p._volume == 0

        with pytest.raises(RuntimeError):
            p.dispense(5)  # tip is empty

        p.eject_tip()


def test_tip_handling():
    with pytest.warns(UserWarning, match="not ejected"):
        with PipettorSimulator(200, multichannel=False, initialize=True) as p:
            p.pick_tip(80)

    with PipettorSimulator(200, multichannel=False, initialize=True) as p:
        p.pick_tip(80)
        with pytest.raises(RuntimeError):
            p.pick_tip(70)

        p.aspirate(100)

        with pytest.warns(UserWarning):
            p.eject_tip()  # tip not empty

        with pytest.raises(RuntimeError):
            p.eject_tip()  # no tip


def test_sensor():
    with pytest.warns(UserWarning):
        with PipettorSimulator(200, multichannel=False, initialize=True) as p:
            _ = p.sensor_value


def test_movements():
    with PipettorSimulator(200, multichannel=False, initialize=True) as p:
        assert p.xyz_position == (p.x_position, p.y_position, p.z_position) == (0, 0, 0)

        p.move_xy(20, 30.5)
        assert p.xy_position == (p.x_position, p.y_position) == (20, 30.5)

        p.move_z(15)
        assert p.xyz_position == (p.x_position, p.y_position, p.z_position) == (20, 30.5, 15)


def test_speeds():
    with PipettorSimulator(200, multichannel=False, initialize=True) as p:
        p.aspirate_speed = 3
        assert p.aspirate_speed == 3
        p.dispense_speed = 4
        assert p.dispense_speed == 4

        p.x_speed = 2
        p.y_speed = 3
        p.z_speed = 4
        assert p.x_speed == 2
        assert p.y_speed == 3
        assert p.z_speed == 4


def test_initialize():
    with PipettorSimulator(200, multichannel=False, initialize=True) as p:
        p.pick_tip(70)
        with pytest.raises(RuntimeError):
            p.initialize()  # has tip

    with PipettorSimulator(200, multichannel=False, initialize=True) as p:
        p.move_xy(10, 20)
        p.initialize()
        assert p.xy_position == (0, 0)


def test_move_to_surface():
    with PipettorSimulator(200, multichannel=False, initialize=True) as p:
        with pytest.raises(RuntimeError):
            p.move_to_surface(70, 10)  # no tip
        p.pick_tip(80)
        with pytest.warns(UserWarning):
            p.move_to_surface(70, 10)  # warn: requires sensor
        p.eject_tip()

    with PipettorSimulator(1000, multichannel=True, initialize=True) as p:
        p.pick_tip(80)
        with pytest.raises(RuntimeError):
            p.move_to_surface(80, 10)  # multi-channel can't have sensor
        p.eject_tip()
