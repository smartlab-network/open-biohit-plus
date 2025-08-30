from abc import ABC, abstractmethod
from typing import Literal, Tuple

MovementSpeed = Literal[1, 2, 3, 4, 5, 6, 7, 8, 9]
PistonSpeed = Literal[1, 2, 3, 4, 5, 6]
TipVolume = Literal[200, 1000]


class AbstractPipettor(ABC):
    def __init__(self, tip_volume: Literal[200, 1000], *, multichannel: bool, initialize: bool = True):
        """
        Interface to the Biohit Roboline pipettor

        :param tip_volume: The tip volume (must be 1000 if multichannel is True)
        :param multichannel: If True, it is assumed the device uses a multichannel pipet
        :param initialize: If True, the device will be initialized
        """
        self.__multichannel = multichannel

    @property
    def is_multichannel(self) -> bool:
        """True if the device uses a multi-channel pipette"""
        return self.__multichannel

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """True if the device is connected, False otherwise"""
        pass

    @property
    @abstractmethod
    def tip_volume(self) -> TipVolume:
        """The tip volume (200 or 1000 uL, can be set)"""
        pass

    @property
    @abstractmethod
    def tip_pickup_force(self) -> int:
        """The tip pickup force (8 to 26, can be set)"""
        pass

    @property
    @abstractmethod
    def aspirate_speed(self) -> PistonSpeed:
        """The aspirate speed (1 to 6)"""

    @property
    @abstractmethod
    def dispense_speed(self) -> PistonSpeed:
        """The dispense speed (1 to 6)"""
        pass

    @property
    @abstractmethod
    def x_speed(self) -> MovementSpeed:
        """The X speed (1 to 9)"""

    @property
    @abstractmethod
    def y_speed(self) -> MovementSpeed:
        """The Y speed (1 to 9)"""

    @property
    @abstractmethod
    def z_speed(self) -> MovementSpeed:
        """The Z speed (1 to 9)"""

    @property
    @abstractmethod
    def x_position(self) -> float:
        """The X position, in millimeters"""

    @property
    @abstractmethod
    def y_position(self) -> float:
        """The Y position, in millimeters"""

    @property
    @abstractmethod
    def z_position(self) -> float:
        """The Z position, in millimeters"""

    @property
    def xy_position(self) -> Tuple[float, float]:
        """The X and Y position, in millimeters"""
        return self.x_position, self.y_position

    @property
    def xyz_position(self) -> Tuple[float, float, float]:
        """The X, Y and Z position, in millimeters"""
        return self.x_position, self.y_position, self.z_position

    @abstractmethod
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

    @abstractmethod
    def move_z(self, z: float, wait: bool = True) -> None:
        """
        Move to the given Z position.

        :param z: The target Z position, in millimeters
        :param wait: if False, returns after sending the command to the device,
            else waits until target position is reached.
        """

    @abstractmethod
    def move_xy(self, x: float, y: float, wait: bool = True) -> None:
        """
        Move to the given X and Y position.

        :param x: The target X position, in millimeters
        :param y: The target Y position, in millimeters
        :param wait: if False, returns after sending the command to the device,
            else waits until target position is reached.
        """

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

    @abstractmethod
    def move_to_surface(self, limit: float, distance_from_surface: float) -> None:
        """
        Move Z in direction of `limit`, until either a surface was detected, or the `limit` was reached.
        If moving upwards, stops below the surface, else above it.

        Note: This is only possible with single-channel pipets that have a tip sensor.

        :param limit: Direction and target position if no surface was detected
        :param distance_from_surface: Target distance from detected surface
        """

    @abstractmethod
    def aspirate(self, volume: float, wait: bool = True) -> None:
        """
        Aspirate the given volume

        :param volume: Volume, in microliters
        :param wait: if False, returns after sending the command to the device,
            else waits until target position is reached.
        """

    @abstractmethod
    def dispense(self, volume: float, wait: bool = True) -> None:
        """
        Dispense the given volume

        :param volume: Volume, in microliters
        :param wait: if False, returns after sending the command to the device,
            else waits until target position is reached.
        """

    @abstractmethod
    def dispense_all(self) -> None:
        """Dispense all liquid from the tip"""

    @abstractmethod
    def pick_tip(self, limit: float) -> None:
        """
        Move downwards until a tip is picked up, or the `limit` is reached

        :param limit: Z limit
        """

    @abstractmethod
    def eject_tip(self) -> None:
        """Eject the current tip"""

    @abstractmethod
    def wait_until_stopped(self) -> None:
        """Block the thread until all motors stopped (X, Y, Z, Piston)"""

    @property
    @abstractmethod
    def sensor_value(self) -> int:
        """The raw value read by the oscillation frequency sensor. Value range 11400-60000 corresponds to 526-100 Hz."""
