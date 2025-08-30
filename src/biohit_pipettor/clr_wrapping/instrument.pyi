from typing import Literal, Union, overload

MovementActuatorAddress = Literal["X", "Y", "Z"]
PistonActuatorAddress = Literal["P"]
ActuatorAddress = Union[MovementActuatorAddress, PistonActuatorAddress]
MovementActuatorSpeed = Literal[1, 2, 3, 4, 5, 6, 7, 8, 9]
PistonActuatorSpeed = Literal[1, 2, 3, 4, 5, 6]

class CommunicationCls:
    def __init__(self, systemPath: str = "") -> None:
        """
        Constructor

        :param systemPath: Path for logging
        """
    def IsConnected(self) -> bool:
        """
        Checks if connection is open or not

        :return: True if connected, else False
        """
    @property
    def ClearToReceive(self) -> bool:
        """
        Returns True when the previous message is written to the serial port.

        :return: True if the device is ready to receive a message
        """
    @property
    def usbConnected(self) -> int:
        """
        True if the connection is open, False otherwise.

        :return: True if the connection is open, False otherwise.
        """
    @property
    def ErrorCode(self) -> int:
        """
        Returns possible communication error. Set to 0 when the port is closed.

        0: No error
        1: Failed to open serial port
        2: Failed to receive data (timeout)
        3: Checksum mismatch
        4: Busy processing previous message
        9: Unable to close port

        :return: The error code
        """
    @property
    def TheException(self) -> str:
        """
        Error message, in case of a .NET exception

        :return: Error message
        """
    @property
    def DataLogOnOff(self) -> bool:
        """
        True if data logging is on, False otherwise

        :return: True if data logging is on, False otherwise
        """

class ControlCls:
    def __init__(self, systemPath: str = "") -> None:
        """
        Constructor

        :param systemPath: Path for logging
        """
    @property
    def PipetType(self) -> Literal[1, 2]:
        """
        The pipet type: 1=200 ul, 2=1000 ul
        """
    @PipetType.setter
    def PipetType(self, pipet_type: Literal[1, 2]): ...
    @property
    def Comm(self) -> CommunicationCls:
        """
        The underlying CommunicationCls
        """
    @property
    def ErrorCode(self) -> int:
        """
        Error during serial communication

        0: No error
        1: Invalid address
        2: Invalid parameter
        3: Error during serial communication

        :return: The error code
        """
    @property
    def TheException(self) -> str:
        """
        Error message in case of a .NET exception

        :return: Error message
        """
    @property
    def DataLogOnOff(self) -> bool:
        """
        True if data logging is on, False otherwise

        :return: True if data logging is on, False otherwise
        """
    def Aspirate(self, volume: float, steps: bool = False, wait: bool = False) -> bool:
        """
        Aspirates the given volume.

        :param volume: The volume to aspirate, in microliters or steps
        :param steps: Volume unit: False - Microliters, True - Steps
        :param wait: If True, this method returns after completion, else after the command was sent to the instrument
        :return: If wait was True: returning True if command was accepted.
            It wait was False: returning True if command was executed successfully.
        """
    def Dispense(self, volume: float, steps: bool = False, wait: bool = False) -> bool:
        """
        Dispenses the given volume.

        :param volume: The volume to dispense, in microliters or steps
        :param steps: Volume unit: False - Microliters, True - Steps
        :param wait: If True, this method returns after completion, else after the command was sent to the instrument
        :return: If wait was True: returning True if command was accepted.
            It wait was False: returning True if command was executed successfully.
        """
    def DispenseAll(self, wait: bool = False) -> bool:
        """
        Dispenses everything out of the tip.

        :param wait: If True, this method returns after completion, else after the command was sent to the instrument
        :return: If wait was True: returning True if command was accepted.
            It wait was False: returning True if command was executed successfully.
        """
    def DriveEdge(self, address: MovementActuatorAddress, wait: bool = False) -> bool:
        """
        Drives the given actuator to mechanical hard stop.

        :param address: Address of the actuator: "X", "Y", or "Z"
        :param wait: If True, this method returns after completion, else after the command was sent to the instrument
        :return: If wait was True: returning True if command was accepted.
            It wait was False: returning True if command was executed successfully.
        """
    def DriveHome(self, address: MovementActuatorAddress, wait: bool = False) -> bool:
        """
        Drives the given actuator to its home position. To home all actuators, use Initialize() instead.

        :param address: Address of the actuator: "X", "Y", or "Z"
        :param wait: If True, this method returns after completion, else after the command was sent to the instrument
        :return: If wait was True: returning True if command was accepted.
            It wait was False: returning True if command was executed successfully.
        """
    def EjectTip(self, wait: bool = False) -> bool:
        """
        Ejects the tip.

        :param wait: If True, this method returns after completion, else after the command was sent to the instrument
        :return: If wait was True: returning True if command was accepted.
            It wait was False: returning True if command was executed successfully.
        """
    @overload
    def Initialize(self, wait: bool = False) -> bool:
        """
        Initialized all actuators to the 0 position.

        :param wait: If True, this method returns after completion, else after the command was sent to the instrument
        :return: If wait was True: returning True if command was accepted.
            It wait was False: returning True if command was executed successfully.
        """
    @overload
    def Initialize(self, address: ActuatorAddress, wait: bool = False) -> bool:
        """
        Initialized the given actuator to the 0 position.

        :param address: Address of the actuator: "X", "Y", "Z", or "P"
        :param wait: If True, this method returns after completion, else after the command was sent to the instrument
        :return: If wait was True: returning True if command was accepted.
            It wait was False: returning True if command was executed successfully.
        """
    def IsDriveOn(self, address: ActuatorAddress) -> bool:
        """
        Checks if the given actuator is in motion.

        :param address: Address of the actuator: "X", "Y", "Z", or "P"
        :return: True if the actuator is in motion. False if not, or if the communication failed (check ErrorCode)
        """
    def IsDriveOff(self, address: ActuatorAddress) -> bool:
        """
        Checks if the given actuator is in motion.

        :param address: Address of the actuator: "X", "Y", "Z", or "P"
        :return: True if the actuator is not in motion. False if it is, or if the communication failed (check ErrorCode)
        """
    def Move(self, address: ActuatorAddress, position: float, steps: bool = False, wait: bool = False) -> bool:
        """
        Moves the given actuator to the given position

        :param address: Address of the actuator: "X", "Y", "Z", or "P"
        :param position: The target position, in millimeters, microliters, or steps
        :param steps: Position unit: False - Millimeters (X, Y, Z) or Microliters (P), True - Steps
        :param wait: If True, this method returns after completion, else after the command was sent to the instrument
        :return: If wait was True: returning True if command was accepted.
            It wait was False: returning True if command was executed successfully.
        """
    def MoveToSurface(self, limit: float, wait: bool = False) -> bool:
        """
        Moves the Z actuator in direction of the limit until the surface has been detected.

        If moving downwards: Stops just below the surface, or at the limit.
        If moving upwards: Stops just above the surface, or at the limit.

        :param limit: max. position in millimeters
        :param wait: If True, this method returns after completion, else after the command was sent to the instrument
        :return: If wait was True: returning True if command was accepted.
            It wait was False: returning True if command was executed successfully.
        """
    def PickTip(self, wait: bool = False) -> bool:
        """
        Pick up a tip.

        :param wait: If True, this method returns after completion, else after the command was sent to the instrument
        :return: If wait was True: returning True if command was accepted.
            It wait was False: returning True if command was executed successfully.
        """
    def PollPosition(self, address: ActuatorAddress, steps: bool) -> float:
        """
        Poll the position of the given actuator.

        :param address: Address of the actuator: "X", "Y", "Z", or "P"
        :param steps: Position unit: False - Millimeters (X, Y, Z) or Microliters (P), True - Steps
        :return: Position, or -1000
        """
    @overload
    def PollSpeed(self, address: PistonActuatorAddress, inwards: bool) -> PistonActuatorSpeed:
        """
        Poll the piston speed.

        :param address: Piston actuator address, always "P"
        :param inwards: Piston direction
        :return: Piston speed, or -1
        """
    @overload
    def PollSpeed(self, address: MovementActuatorAddress, inwards: bool = False) -> MovementActuatorSpeed:
        """
        Poll the speed of the given actuator

        :param address: Address of the actuator
        :param inwards: Irrelevant
        :return: Speed, or -1
        """
    def PollSensorReading(self) -> int:
        """
        Poll the oscillation frequency sensor

        :return: Sensor reading (unscaled), or -1
        """
    def RefreshSlaves(self) -> bool:
        """
        Checks communication with all actuators.

        :return: True on success, False otherwise
        """
    @overload
    def SetSpeed(self, address: PistonActuatorAddress, speed: PistonActuatorSpeed, inwards: bool) -> bool:
        """
        Sets the piston speed (default: 3).

        :param address: Address of the piston actuator: "P"
        :param speed: The target speed (1 to 6)
        :param inwards: Piston direction
        :return:
        """
    @overload
    def SetSpeed(self, address: MovementActuatorAddress, speed: MovementActuatorSpeed, inwards: bool = False) -> bool:
        """
        Sets the speed for the given actuator (default: 8 for X/Y, 9 for Z).

        :param address: Address of the actuator: "X", "Y", "Z"
        :param speed: The target speed (1 to 9)
        :param inwards: Irrelevant
        :return: True on success, False otherwise
        """
    @overload
    def WaitArmToStop(self, address: ActuatorAddress) -> bool:
        """
        Waits until given actuator is not moving.

        :param address: Address of the actuator: "X", "Y", "Z", or "P"
        :return: True on success, False otherwise
        """
    @overload
    def WaitArmToStop(self) -> bool:
        """
        Wait until all positional actuators (X, Y, Z) are not moving.

        :return: True on success, False otherwise
        """
    def WaitPistonToStop(self) -> bool:
        """
        Wait until piston actuator (P) is not moving.

        :return: True on success, False otherwise
        """
    def Dispose(self) -> None:
        """
        Release all unmanaged resources

        :return:
        """

class InstrumentCls:
    def __init__(self, systemPath: str = ".") -> None:
        """
        Constructor

        :param systemPath: Path for logging
        """
    def __del__(self) -> None: ...
    def Dispose(self) -> None:
        """
        Release all unmanaged resources

        :return:
        """
    @property
    def Control(self) -> ControlCls:
        """
        The underlying ControlCls object
        """
    @property
    def TheError(self) -> str:
        """
        Last error
        """
    @property
    def TheException(self) -> str:
        """
        Last exception
        """
    def IsConnected(self) -> bool:
        """
        True if robot is connected via USB, False otherwise

        :return: True if robot is connected via USB, False otherwise
        """
    def InitializeInstrument(self) -> bool:
        """
        Initializes the instrument: reset errors, refresh slaves, initialize actuators

        :return: True on success, False otherwise
        """
    def MoveZ(self, fZ: float, wait: bool = True) -> bool:
        """
        Moves Z actuator to given position.

        :param fZ: Z target position, in millimeters
        :param wait: If True, this method returns after completion, else after the command was sent to the instrument
        :return: If wait was True: returning True if command was accepted.
            It wait was False: returning True if command was executed successfully.
        """
    def MoveXY(self, fX: float, fY: float, wait: bool = True) -> bool:
        """
        Moves X and Y actuators to given position.

        :param fX: X target position, in millimeters
        :param fY: Y target position, in millimeters
        :param wait: If True, this method returns after completion, else after the command was sent to the instrument
        :return: If wait was True: returning True if command was accepted.
            It wait was False: returning True if command was executed successfully.
        """
    def MoveToSurface(self, fBottom: float, fDepth: float) -> bool:
        """
        Moves to the surface, in direction of fBottom.

        If moving downwards: Stops below the surface, or at fBottom.
        If moving upwards: Stops above the surface, or at fBottom.

        :param fBottom: Limit and direction of movement, in millimeters
        :param fDepth: Distance from surface, in millimeters
        :return: True on success, False otherwise
        """
    def DispenseAll(self) -> bool:
        """
        Dispense all.

        :return: True on success, False otherwise
        """
    def MovePistonToPosition(self, position: int) -> bool:
        """
        Move piston to the given position.

        :param position: Target position, in steps
        :return: True on success, False otherwise
        """
    def Aspirate(self, fVol: float, wait: bool = True) -> bool:
        """
        Aspirate the given volume.

        :param fVol: Volume, in microliters
        :param wait: If True, this method returns after completion, else after the command was sent to the instrument
        :return: If wait was True: returning True if command was accepted.
            It wait was False: returning True if command was executed successfully.
        """
    def Dispense(self, fVol: float, wait: bool = True) -> bool:
        """
        Dispense the given volume.

        :param fVol: Volume, in microliters
        :param wait: If True, this method returns after completion, else after the command was sent to the instrument
        :return: If wait was True: returning True if command was accepted.
            It wait was False: returning True if command was executed successfully.
        """
    def SetAspirateSpeed(self, nSpd: PistonActuatorSpeed) -> bool:
        """
        Set the aspirate speed.

        :param nSpd: The target aspirate speed (1 to 6)
        :return: True on success, False otherwise
        """
    def SetDispenseSpeed(self, nSpd: PistonActuatorSpeed) -> bool:
        """
        Set the dispense speed.

        :param nSpd: The target dispense speed (1 to 6)
        :return: True on success, False otherwise
        """
    def SetActuatorSpeed(self, address: MovementActuatorAddress, speed: MovementActuatorSpeed) -> bool:
        """
        Set the dispense speed.

        :param address: Actuator address: "X", "Y", or "Z"
        :param speed: The target speed (1 to 9)
        :return: True on success, False otherwise
        """
    def SetPickUpForce(self, force: int) -> bool:
        """
        Set the pick up force.

        :param force: The target force (4 to 26)
        :return: True on success, False otherwise
        """
    def SetPickUpDistance(self, distance: int) -> bool:
        """
        Set the pick up distance.

        :param distance: The target distance, in millimeters (13 to 124)
        :return: True on success, False otherwise
        """
    def GetPickupDistance(self) -> int:
        """
        Get the pick up distance.

        :return: The pick up distance
        """
    def PickTip(self, lowLimit: float) -> bool:
        """
        Pick up a tip at the current XY location.

        :param lowLimit: Lowest position before action is aborted
        :return: True on success, False otherwise
        """
    def EjectTip(self) -> bool:
        """
        Eject the tip.

        :return: True on success, False otherwise
        """
    def PollPosition(self, address: ActuatorAddress) -> float:
        """
        Poll the actuator position.

        :param address: The actuator address: "X", "Y", "Z", or "P"
        :return: The actuator position, in millimeters or microliters
        """
    def GetErrors(self) -> str:
        """
        Get error codes of all parts, like this (N is the respective error code):

        "St:N Pr:N Er:N X:N Y:N Z:N P:N"

        St: Status
        Pr: Present
        Er: Error
        X/Y/Z/P: Actuators

        :return: The error codes as a string
        """
    def GetCommErrors(self) -> str:
        """
        Get error codes of communication interface, like this (N is the respective error code):

        "MO:N MI:N ECode:N EReceived:N Exception:N"

        MO: Message Out
        MI: Message In
        ECode: Error Code
        EReceived: Error Received
        Exception: Exception

        :return:
        """
