"""
Operation builders for FunctionWindow.

These helper functions convert UI inputs into Operation objects,
separating the UI logic from operation creation logic.
"""

from .operation import Operation
from .operationtype import OperationType
from ..pipettor_plus.pipettor_constants import Pipettors_in_Multi

class OperationBuilder:
    """Helper class to build Operation objects from UI inputs"""

    @staticmethod
    def build_pick_tips(labware_id: str, positions: list[tuple[int, int]], channels: int) -> Operation:
        """
        Build a PICK_TIPS operation.

        Parameters
        ----------
        labware_id : str
            ID of the tip holder
        positions : list[tuple[int, int]]
            List of (col, row) positions
        channels : int
            Number of channels

        Returns
        -------
        Operation
        """
        description = f"Pick tips from {labware_id} at {positions}"
        return Operation(
            operation_type=OperationType.PICK_TIPS,
            parameters={
                'labware_id': labware_id,
                'positions': positions,
                'channels': channels,
            },
            description=description
        )

    @staticmethod
    def build_return_tips(labware_id: str, positions: list[tuple[int, int]], channels: int) -> Operation:
        """Build a RETURN_TIPS operation"""
        description = f"Return tips to {labware_id} at {positions}"
        return Operation(
            operation_type=OperationType.RETURN_TIPS,
            parameters={
                'labware_id': labware_id,
                'positions': positions,
                'channels': channels
            },
            description=description
        )

    @staticmethod
    def build_replace_tips(
            return_labware_id: str,
            return_positions: list[tuple[int, int]],
            pick_labware_id: str,
            pick_positions: list[tuple[int, int]],
            channels: int
    ) -> Operation:
        """Build a REPLACE_TIPS operation"""
        description = (f"Replace tips: return to {return_labware_id} at {return_positions} "
                       f"& pick from {pick_labware_id} at {pick_positions}")

        return Operation(
            operation_type=OperationType.REPLACE_TIPS,
            parameters={
                'return_labware_id': return_labware_id,
                'return_positions': return_positions,
                'pick_labware_id': pick_labware_id,
                'pick_positions': pick_positions,
                'channels': channels,
            },
            description=description
        )

    @staticmethod
    def build_discard_tips(labware_id: str, positions: list[tuple[int, int]] = None) -> Operation:
        """Build a DISCARD_TIPS operation"""
        description = f"Discard tips to {labware_id}"
        params = {'labware_id': labware_id}

        return Operation(
            operation_type=OperationType.DISCARD_TIPS,
            parameters=params,
            description=description
        )

    @staticmethod
    def build_add_medium(
            source_labware_id: str,
            source_positions: list,
            dest_labware_id: str,
            dest_positions: list[tuple[int, int]],
            volume: float,
            channels: int,
            change_tips: bool = False
    ) -> Operation:
        """Build an ADD_MEDIUM operation"""
        total_wells = len(dest_positions) * (Pipettors_in_Multi if channels == Pipettors_in_Multi else 1)
        total_volume = volume * total_wells

        description = (
            f"Add medium: {source_labware_id} → {dest_labware_id} "
            f"({volume}µL/well, {total_wells} wells, {total_volume}µL total)"
        )

        params = {
            'source_labware_id': source_labware_id,
            'source_positions': source_positions,
            'dest_labware_id': dest_labware_id,
            'dest_positions': dest_positions,
            'volume': volume,
            'channels': channels,
            'change_tips': change_tips
        }

        return Operation(
            operation_type=OperationType.ADD_MEDIUM,
            parameters=params,
            description=description
        )

    @staticmethod
    def build_remove_medium(
            source_labware_id: str,
            source_positions: list[tuple[int, int]],
            dest_labware_id: str,
            dest_positions: list,
            volume: float,
            channels: int,
            change_tips: bool = False,
    ) -> Operation:
        """Build a REMOVE_MEDIUM operation"""
        total_wells = len(source_positions) * (Pipettors_in_Multi if channels == Pipettors_in_Multi else 1)
        total_volume = volume * total_wells

        description = (
            f"Remove medium: {source_labware_id} → {dest_labware_id} "
            f"({volume}µL/well, {total_wells} wells, {total_volume}µL total)"
        )

        params = {
            'source_labware_id': source_labware_id,
            'source_positions': source_positions,
            'dest_labware_id': dest_labware_id,
            'dest_positions': dest_positions,
            'volume': volume,
            'channels': channels,
            'change_tips': change_tips
        }

        return Operation(
            operation_type=OperationType.REMOVE_MEDIUM,
            parameters=params,
            description=description
        )

    @staticmethod
    def build_transfer_plate_to_plate(
            source_labware_id: str,
            source_positions: list[tuple[int, int]],
            dest_labware_id: str,
            dest_positions: list[tuple[int, int]],
            volume: float,
            channels: int,
            change_tips: bool = False
    ) -> Operation:
        """Build a TRANSFER_PLATE_TO_PLATE operation"""
        total_wells = len(source_positions) * (Pipettors_in_Multi if channels == Pipettors_in_Multi else 1)
        total_volume = volume * total_wells

        description = (
            f"Transfer: {source_labware_id} → {dest_labware_id} "
            f"({volume}µL/well, {total_wells} wells, {total_volume}µL total)"
        )

        params = {
            'source_labware_id': source_labware_id,
            'source_positions': source_positions,
            'dest_labware_id': dest_labware_id,
            'dest_positions': dest_positions,
            'volume': volume,
            'channels': channels,
            'change_tips': change_tips
        }


        return Operation(
            operation_type=OperationType.TRANSFER_PLATE_TO_PLATE,
            parameters=params,
            description=description
        )

    @staticmethod
    def build_suck(labware_id: str, position: tuple[int, int], volume: float, channels: int) -> Operation:
        """Build suck operation"""
        return Operation(
            operation_type=OperationType.SUCK,
            description=f"Suck {volume}µL from {labware_id}",
            parameters={
                'labware_id': labware_id,
                'position': position,
                'volume': volume,
                'channels': channels
            }
        )

    @staticmethod
    def build_spit(labware_id: str, position: tuple[int, int], volume: float, channels: int) -> Operation:
        """Build spit operation"""
        return Operation(
            operation_type=OperationType.SPIT,
            description=f"Spit {volume}µL to {labware_id}",
            parameters={
                'labware_id': labware_id,
                'position': position,
                'volume': volume,
                'channels': channels
            }
        )

    @staticmethod
    def build_home() -> Operation:
        """Build home operation"""
        return Operation(
            operation_type=OperationType.HOME,
            description="Move pipettor to home position",
            parameters={}
        )

    @staticmethod
    def build_move_xy(x: float, y: float) -> Operation:
        """Build move XY operation"""
        return Operation(
            operation_type=OperationType.MOVE_XY,
            description=f"Move to X={x}mm, Y={y}mm",
            parameters={
                'x': x,
                'y': y
            }
        )

    @staticmethod
    def build_move_z(z: float) -> Operation:
        """Build move Z operation"""
        return Operation(
            operation_type=OperationType.MOVE_Z,
            description=f"Move to Z={z}mm",
            parameters={
                'z': z
            }
        )

    @staticmethod
    def build_measure_foc(wait_seconds: int, plate_name: str) -> Operation:
        """Build a MEASURE_FOC operation"""
        return Operation(
            operation_type=OperationType.MEASURE_FOC,
            description=f"FOC measurement: wait {wait_seconds}s, measure plate '{plate_name}'",
            parameters={
                'wait_seconds': wait_seconds,
                'plate_name': plate_name
            }
        )

    @staticmethod
    def build_remove_and_add(
            plate_labware_id: str,
            plate_positions: list[tuple[int, int]],
            remove_reservoir_id: str,
            remove_position: tuple[int, int],
            source_reservoir_id: str,
            source_position: tuple[int, int],
            volume: float,
            channels: int,
            change_tips: bool = False,
    ) -> Operation:
        """
        Remove medium from plate positions to reservoir, then add fresh medium from source (BATCHED).
        Handles positions in batches based on tip capacity to avoid pipettor timeout."""
        return Operation(
            operation_type=OperationType.REMOVE_AND_ADD,
            description=f"Remove {volume}µL from {len(plate_positions)} positions, add fresh from source (batched)",
            parameters={
                'plate_labware_id': plate_labware_id,
                'plate_positions': plate_positions,
                'remove_reservoir_id': remove_reservoir_id,
                'remove_position': remove_position,
                'source_reservoir_id': source_reservoir_id,
                'source_position': source_position,
                'volume': volume,
                'channels': channels,
                'change_tips': change_tips
            }
        )