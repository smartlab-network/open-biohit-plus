import time
from typing import Callable, Literal, Tuple, overload

from biohit_pipettor.abstract_pipettor import AbstractPipettor, MovementSpeed, PistonSpeed, TipVolume
from biohit_pipettor.clr_wrapping.instrument import InstrumentCls
from biohit_pipettor.errors import CommandFailed, CommandNotAccepted, NotConnected, OperationNotSupported


class Pipettor(AbstractPipettor):
    __instrument: InstrumentCls

    def __init__(self, tip_volume: Literal[200, 1000], *, multichannel: bool, initialize: bool = True):
        """
        Interface to the Biohit Roboline pipettor

        :param tip_volume: The tip volume (must be 1000 if multichannel is True)
        :param multichannel: If True, it is assumed the device uses a multichannel pipet
        :param initialize: If True, the device will be initialized
        """
        super().__init__(tip_volume=tip_volume, multichannel=multichannel, initialize=initialize)
        self.__instrument = InstrumentCls()

        # wait until connection is established
        for _ in range(20):
            time.sleep(0.1)
            if self.is_connected:
                break
        else:
            raise NotConnected

        self.tip_volume = tip_volume

        if initialize:
            self.initialize()

    @property
    def is_connected(self) -> bool:
        """True if the device is connected, False otherwise"""
        return self.__instrument.IsConnected() != 0

    @property
    def tip_volume(self) -> TipVolume:
        """The tip volume (200 or 1000 uL, can be set)"""
        pipet_type = self.__instrument.Control.PipetType
        if pipet_type == 1:
            return 200
        return 1000

    @tip_volume.setter
    def tip_volume(self, volume: TipVolume) -> None:
        if volume == 200:
            if self.is_multichannel:
                raise OperationNotSupported("Multi-channel pipet can only be used with 1000 uL tips")
            self.__instrument.Control.PipetType = 1
        elif volume == 1000:
            self.__instrument.Control.PipetType = 2
        else:
            raise ValueError("Tip volume must be 200 or 1000 uL")

    @property
    def tip_pickup_force(self) -> int:
        force = self.__instrument.Control.PollPickUpForce()
        if force == -1:
            raise CommandFailed
        return force

    @tip_pickup_force.setter
    def tip_pickup_force(self, force: int) -> None:
        self.__run(lambda: self.__instrument.SetPickUpForce(force))

    @property
    def aspirate_speed(self) -> PistonSpeed:
        """The aspirate speed (1 to 6)"""
        return self.__poll_speed("P", inwards=True)

    @aspirate_speed.setter
    def aspirate_speed(self, aspirate_speed: PistonSpeed) -> None:
        self.__run(lambda: self.__instrument.SetAspirateSpeed(aspirate_speed))

    @property
    def dispense_speed(self) -> PistonSpeed:
        """The dispense speed (1 to 6)"""
        return self.__poll_speed("P", inwards=False)

    @dispense_speed.setter
    def dispense_speed(self, dispense_speed: PistonSpeed) -> None:
        self.__run(lambda: self.__instrument.SetDispenseSpeed(dispense_speed))

    @property
    def x_speed(self) -> MovementSpeed:
        """The X speed (1 to 9)"""
        return self.__poll_speed("X", False)

    @x_speed.setter
    def x_speed(self, x_speed: Literal[1, 2, 3, 4, 5, 6, 7, 8, 9]):
        self.__run(lambda: self.__instrument.SetActuatorSpeed("X", x_speed))

    @property
    def y_speed(self) -> MovementSpeed:
        """The Y speed (1 to 9)"""
        return self.__poll_speed("Y", False)

    @y_speed.setter
    def y_speed(self, y_speed: Literal[1, 2, 3, 4, 5, 6, 7, 8, 9]):
        self.__run(lambda: self.__instrument.SetActuatorSpeed("Y", y_speed))

    @property
    def z_speed(self) -> MovementSpeed:
        """The Z speed (1 to 9)"""
        return self.__poll_speed("Z", False)

    @z_speed.setter
    def z_speed(self, z_speed: Literal[1, 2, 3, 4, 5, 6, 7, 8, 9]):
        self.__run(lambda: self.__instrument.SetActuatorSpeed("Z", z_speed))

    @property
    def x_position(self) -> float:
        """The X position, in millimeters"""
        return self.__poll_position("X")

    @property
    def y_position(self) -> float:
        """The Y position, in millimeters"""
        return self.__poll_position("Y")

    @property
    def z_position(self) -> float:
        """The Z position, in millimeters"""
        return self.__poll_position("Z")

    @property
    def xy_position(self) -> Tuple[float, float]:
        """The X and Y position, in millimeters"""
        return self.x_position, self.y_position

    @property
    def xyz_position(self) -> Tuple[float, float, float]:
        """The X, Y and Z position, in millimeters"""
        return self.x_position, self.y_position, self.z_position

    def initialize(self) -> None:
        """
        Initializes the instrument:

            - move to z=0
            - move x=0, y=0
            - drop tip, if present
            - move piston to volume=0
            - reset errors
            - refresh slaves
        """
        self.__run(self.__instrument.InitializeInstrument)

    def move_z(self, z: float, wait: bool = True) -> None:
        """
        Move to the given Z position.

        :param z: The target Z position, in millimeters
        :param wait: if False, returns after sending the command to the device,
            else waits until target position is reached.
        """
        self.__run_with_wait(lambda wait_: self.__instrument.MoveZ(z, wait_), wait)

    def move_xy(self, x: float, y: float, wait: bool = True) -> None:
        """
        Move to the given X and Y position.

        :param x: The target X position, in millimeters
        :param y: The target Y position, in millimeters
        :param wait: if False, returns after sending the command to the device,
            else waits until target position is reached.
        """
        self.__run_with_wait(lambda wait_: self.__instrument.MoveXY(x, y, wait_), wait)

    def move_x(self, x: float, wait: bool = True) -> None:
        """
        Move to the given X position.

        :param x: The target X position, in millimeters
        :param wait: if False, returns after sending the command to the device,
            else waits until target position is reached.
        """
        self.move_xy(x, self.y_position, wait)

    def move_y(self, y: float, wait: bool = True) -> None:
        """
        Move to the given Y position.

        :param y: The target Y position, in millimeters
        :param wait: if False, returns after sending the command to the device,
            else waits until target position is reached.
        """
        self.move_xy(self.x_position, y, wait)

    def move_to_surface(self, limit: float, distance_from_surface: float) -> None:
        """
        Move Z in direction of `limit`, until either a surface was detected, or the `limit` was reached.
        If moving upwards, stops below the surface, else above it.

        Note: This is only possible with single-channel pipets that have a tip sensor.

        :param limit: Direction and target position if no surface was detected
        :param distance_from_surface: Target distance from detected surface
        """
        if self.is_multichannel:
            raise OperationNotSupported(
                "Command 'MoveToSurface' requires a tip sensor, which is only available for single-channel pipets"
            )
        self.__run(lambda: self.__instrument.MoveToSurface(limit, distance_from_surface))

    @property
    def __ul_to_steps(self) -> float:
        if self.is_multichannel:  # multi-channel can only be 1000 uL
            return 0.2
        elif self.tip_volume == 200:
            return 2
        else:  # single-channel, 1000 uL
            return 0.4

    def aspirate(self, volume: float, wait: bool = True) -> None:
        """
        Aspirate the given volume

        :param volume: Volume, in microliters
        :param wait: if False, returns after sending the command to the device,
            else waits until target position is reached.
        """
        self.__run_with_wait(
            lambda wait_: self.__instrument.Control.Aspirate(volume * self.__ul_to_steps, True, wait_), wait
        )

    def dispense(self, volume: float, wait: bool = True) -> None:
        """
        Dispense the given volume

        :param volume: Volume, in microliters
        :param wait: if False, returns after sending the command to the device,
            else waits until target position is reached.
        """
        self.__run_with_wait(
            lambda wait_: self.__instrument.Control.Dispense(volume * self.__ul_to_steps, True, wait_), wait
        )

    def dispense_all(self) -> None:
        """Dispense all liquid from the tip"""
        self.__run(self.__instrument.DispenseAll)

    def pick_tip(self, limit: float) -> None:
        """
        Move downwards until a tip is picked up, or the `limit` is reached

        :param limit: Z limit
        """
        self.__run(lambda: self.__instrument.PickTip(limit))

    def eject_tip(self) -> None:
        """Eject the current tip"""
        self.__run(self.__instrument.EjectTip)

    def wait_until_stopped(self) -> None:
        """Block the thread until all motors stopped (X, Y, Z, Piston)"""
        self.__run(self.__instrument.Control.WaitArmToStop)
        self.__run(self.__instrument.Control.WaitPistonToStop)

    @property
    def sensor_value(self) -> int:
        """The raw value read by the oscillation frequency sensor. Value range 11400-60000 corresponds to 526-100 Hz."""
        raw_value = self.__instrument.Control.PollSensorReading()
        if raw_value < 0:
            raise NotConnected
        return raw_value

    def __run_with_wait(self, func: Callable[[bool], bool], wait: bool) -> None:
        """
        Run a InstrumentLib method with the wait parameter that returns True on success and False otherwise.

        :param func: The method, usually wrapped in a lambda
        :param wait: The wait parameter
        :raises NotConnected: If the device is not connected
        :raises CommandNotAccepted: If wait was False and the wrapped method returned False
        :raises CommandFailed: If wait was True and the wrapped method returned False
        """
        if not self.is_connected:
            raise NotConnected
        if func(wait):
            return
        if wait:
            raise CommandFailed
        raise CommandNotAccepted

    def __run(self, func: Callable[[], bool]) -> None:
        """
        Run a InstrumentLib method that returns True on success and False otherwise.

        :param func: The method, usually wrapped in a lambda
        :raises NotConnected: If the device is not connected
        :raises CommandFailed: If the wrapped method returned False
        """
        if not self.is_connected:
            raise NotConnected
        if not func():
            raise CommandFailed

    def __poll_position(self, address: Literal["X", "Y", "Z", "P"]) -> float:
        """
        Poll the position of the given actuator.

        :param address: The actuator address ("X", "Y", or "Z")
        :return: The actuator position
        :raises: NotConnected: If the device is not connected
        """
        position = self.__instrument.PollPosition(address)
        if position < 0:
            raise NotConnected
        return position

    @overload
    def __poll_speed(self, address: Literal["P"], inwards: bool = False) -> Literal[1, 2, 3, 4, 5, 6]:
        ...

    @overload
    def __poll_speed(
        self, address: Literal["X", "Y", "Z"], inwards: bool = False
    ) -> Literal[1, 2, 3, 4, 5, 6, 7, 8, 9]:
        ...

    def __poll_speed(self, address, inwards=False):
        """
        Poll the speed of the given actuator in the given direction.

        :param address: The actuator address ("X", "Y", "Z", or "P")
        :param inwards: The actuator direction (only relevant for the piston)
        :return: The requested speed
        :raises: NotConnected
        """
        speed = self.__instrument.Control.PollSpeed(address, inwards)
        if speed < 0:
            raise NotConnected
        return speed

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # when no exceptions occur, no explicit deletion is required
        # when a exception occurs, it has a reference to `self`, so the wrapped instrument is not disposed
        # by removing the instrument reference from `self`, its __del__ is called, and thus its Dispose() method
        del self.__instrument
