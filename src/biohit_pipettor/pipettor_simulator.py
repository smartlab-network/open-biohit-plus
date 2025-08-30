from __future__ import annotations

import math
import warnings
from typing import Literal

import matplotlib.pyplot as plt
from matplotlib import cm, colors
from matplotlib.markers import CARETDOWNBASE, CARETUPBASE

from biohit_pipettor.abstract_pipettor import AbstractPipettor, MovementSpeed, PistonSpeed, TipVolume

TIP_PLOT_COLOR = "blue"
VOLUME_PLOT_COLOR = "red"
Z_MAX = 150
Z_CMAP = "plasma"
ANNOTATION_FONTSIZE = "xx-small"


class PipettorSimulator:
    # required to enforce context manager usage
    def __init__(self, tip_volume: Literal[200, 1000], *, multichannel: bool, initialize: bool = True) -> None:
        self._simulator = _PipettorSimulator(tip_volume=tip_volume, multichannel=multichannel, initialize=initialize)

    def __enter__(self) -> _PipettorSimulator:
        return self._simulator

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._simulator._has_tip:
            warnings.warn("Tip was not ejected")

    def __getattr__(self, item):
        raise RuntimeError(f"Must be used with a context manager: `with {self.__class__.__name__}(...) as ...:`")


class _PipettorSimulator(AbstractPipettor):
    fig: plt.Figure
    """matplotlib figure used for plotting"""
    ax: plt.Axes
    """matplotlib axes used for plotting"""

    def __init__(self, tip_volume: Literal[200, 1000], *, multichannel: bool, initialize: bool = True) -> None:
        super().__init__(tip_volume, multichannel=multichannel, initialize=initialize)
        if not initialize:
            raise RuntimeError("Simulation requires initialize=True")
        if tip_volume not in [200, 1000]:
            raise RuntimeError("tip_volume must be 200 or 1000 (uL)")
        if multichannel and tip_volume != 1000:
            raise RuntimeError("Multi-channel pipette requires 1000 uL tips")
        self.__tip_volume: TipVolume = tip_volume
        self.__aspirate_speed: PistonSpeed = 5
        self.__dispense_speed: PistonSpeed = 5
        self.__x_speed: MovementSpeed = 5
        self.__y_speed: MovementSpeed = 5
        self.__z_speed: MovementSpeed = 5
        self.__x_position: float = 0
        self.__y_position: float = 0
        self.__z_position: float = 0
        self._has_tip: bool = False
        self._volume: float = 0

        self.fig, self.ax = plt.subplots(figsize=(8.27, 5.85))
        self.ax.set_xlim(0, 250)
        self.ax.set_ylim(0, 200)
        self.ax.invert_xaxis()
        self.ax.invert_yaxis()
        self.ax.set_aspect("equal")
        self.fig.colorbar(cm.ScalarMappable(colors.Normalize(0, Z_MAX), cmap=Z_CMAP))
        self.fig.legend(
            handles=[
                plt.Line2D([0], [0], linewidth=0, color=VOLUME_PLOT_COLOR, marker=CARETUPBASE),
                plt.Line2D([0], [0], linewidth=0, color=VOLUME_PLOT_COLOR, marker=CARETDOWNBASE),
                plt.Line2D([0], [0], linewidth=0, color=TIP_PLOT_COLOR, marker=CARETUPBASE),
                plt.Line2D([0], [0], linewidth=0, color=TIP_PLOT_COLOR, marker=CARETDOWNBASE),
            ],
            labels=["aspirate", "dispense", "pick tip", "eject tip"],
            ncol=4,
            loc="lower center",
            bbox_to_anchor=(0.4, 0),
        )

    @property
    def is_connected(self) -> bool:
        return True

    @property
    def tip_volume(self) -> TipVolume:
        return self.__tip_volume

    @property
    def tip_pickup_force(self) -> int:
        return 10

    @tip_pickup_force.setter
    def tip_pickup_force(self, force: int) -> None:
        return

    @property
    def aspirate_speed(self) -> PistonSpeed:
        return self.__aspirate_speed

    @aspirate_speed.setter
    def aspirate_speed(self, value: PistonSpeed) -> None:
        self.__aspirate_speed = value

    @property
    def dispense_speed(self) -> PistonSpeed:
        return self.__dispense_speed

    @dispense_speed.setter
    def dispense_speed(self, value: PistonSpeed) -> None:
        self.__dispense_speed = value

    @property
    def x_speed(self) -> MovementSpeed:
        return self.__x_speed

    @x_speed.setter
    def x_speed(self, value: MovementSpeed) -> None:
        self.__x_speed = value

    @property
    def y_speed(self) -> MovementSpeed:
        return self.__y_speed

    @y_speed.setter
    def y_speed(self, value: MovementSpeed) -> None:
        self.__y_speed = value

    @property
    def z_speed(self) -> MovementSpeed:
        return self.__z_speed

    @z_speed.setter
    def z_speed(self, value: MovementSpeed) -> None:
        self.__z_speed = value

    @property
    def x_position(self) -> float:
        return self.__x_position

    @property
    def y_position(self) -> float:
        return self.__y_position

    @property
    def z_position(self) -> float:
        return self.__z_position

    def initialize(self) -> None:
        if self._has_tip:
            self.eject_tip()
            raise RuntimeError("Eject tip before initializing (would drop the tip)")
        self._volume = 0
        self.move_y(0)
        self.move_x(0)
        self.move_z(0)

    def move_z(self, z: float, wait: bool = True) -> None:
        self.__z_position = z

    def move_xy(self, x: float, y: float, wait: bool = True) -> None:
        self.ax.arrow(
            x=self.x_position,
            y=self.y_position,
            dx=x - self.x_position,
            dy=y - self.y_position,
            head_width=1,
            length_includes_head=True,
            color=cm.get_cmap(Z_CMAP, Z_MAX)(self.z_position),
        )
        self.__x_position = x
        self.__y_position = y

    def move_to_surface(self, limit: float, distance_from_surface: float) -> None:
        if self.is_multichannel:
            raise RuntimeError("Multi-channel pipettes don't have a tip sensor and can't detect a surface")
        if not self._has_tip:
            raise RuntimeError("move_to_surface requires a tip")
        warnings.warn("move_to_surface only works with a working tip sensor. Make sure your device has one.")
        self.move_z(limit)

    def aspirate(self, volume: float, wait: bool = True) -> None:
        if not self._has_tip:
            raise RuntimeError("aspirate requires a tip")
        if self._volume + volume > self.tip_volume:
            raise RuntimeError(
                f"Can't aspirate {volume} uL. Current volume: {self._volume} uL, max volume: {self.tip_volume} uL"
            )
        self._volume += volume

        self.ax.plot(self.x_position, self.y_position, marker=CARETUPBASE, color=VOLUME_PLOT_COLOR)
        self.ax.annotate(
            text=self.__volume_to_str(volume),
            xy=(self.x_position, self.y_position),
            xytext=(1, 1),
            textcoords="offset points",
            fontsize=ANNOTATION_FONTSIZE,
        )

    def dispense(self, volume: float, wait: bool = True) -> None:
        if not self._has_tip:
            raise RuntimeError("dispense requires a tip")
        if math.isclose(self._volume, volume, abs_tol=0.001):
            self._volume = 0
        elif self._volume < volume:
            raise RuntimeError(f"Can't dispense {volume} uL. Current volume: {self._volume} uL")
        else:
            self._volume -= volume

        self.ax.plot(self.x_position, self.y_position, marker=CARETDOWNBASE, color=VOLUME_PLOT_COLOR)
        self.ax.annotate(
            text=self.__volume_to_str(-volume),
            xy=(self.x_position, self.y_position),
            xytext=(3, -5),
            textcoords="offset points",
            fontsize=ANNOTATION_FONTSIZE,
        )

    def dispense_all(self) -> None:
        if not self._has_tip:
            raise RuntimeError("dispense requires a tip")
        self.dispense(self._volume)

    def pick_tip(self, limit: float) -> None:
        if self._has_tip:
            raise RuntimeError("Eject the tip first before picking a second tip")
        self._has_tip = True
        self.move_z(0)
        self.ax.plot(self.x_position, self.y_position, marker=CARETUPBASE, color=TIP_PLOT_COLOR)

    def eject_tip(self) -> None:
        if not self._has_tip:
            raise RuntimeError("Pipette has no tip, can't eject it")
        if not math.isclose(self._volume, 0, abs_tol=0.001):
            warnings.warn(f"Ejecting non-empty tip ({self._volume} uL left)")
        self._has_tip = False
        self.ax.plot(self.x_position, self.y_position, marker=CARETDOWNBASE, color=TIP_PLOT_COLOR)

    def wait_until_stopped(self) -> None:
        pass

    @property
    def sensor_value(self) -> int:
        warnings.warn("Reading the tip sensor is not supported by the simulation. Returning 10_000.")
        return 10_000

    def show_plot(self) -> None:
        """Show the figure"""
        self.fig.tight_layout(rect=[0, 0.1, 1, 1])
        self.fig.show()

    def save_plot(self, filename: str) -> None:
        """Save the figure to the given file"""
        self.fig.savefig(filename)

    @staticmethod
    def __volume_to_str(volume: float) -> str:
        if isinstance(volume, int):
            return f"{volume:+}"
        return f"{volume:+.2f}"
