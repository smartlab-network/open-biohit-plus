"""
Operation builders for FunctionWindow.

These helper functions convert UI inputs into Operation objects,
separating the UI logic from operation creation logic.
"""

from biohit_pipettor_plus.gui.operations.operation import Operation
from biohit_pipettor_plus.gui.operations.operationtype import OperationType
from biohit_pipettor_plus.pipettor_plus.pipettor_constants import Pipettors_in_Multi

class OperationBuilder:
    """Helper class to build Operation objects from UI inputs"""

    @staticmethod
    def build_pick_tips(labware_id: str, labware_type: str, positions: list[tuple[int, int]], channels: int) -> Operation:
        """
        Build a PICK_TIPS operation.
        """
        description = f"Pick tips from {labware_id} at {positions}"
        return Operation(
            operation_type=OperationType.PICK_TIPS,
            parameters={
                'labware': {'id': labware_id, 'type': labware_type},
                'positions': positions,
                'channels': channels,
            },
            description=description
        )

    @staticmethod
    def build_return_tips(labware_id: str, labware_type: str, positions: list[tuple[int, int]], channels: int) -> Operation:
        """Build a RETURN_TIPS operation"""
        description = f"Return tips to {labware_id} at {positions}"
        return Operation(
            operation_type=OperationType.RETURN_TIPS,
            parameters={
                'labware': {'id': labware_id, 'type': labware_type},
                'positions': positions,
                'channels': channels
            },
            description=description
        )

    @staticmethod
    def build_replace_tips(
            return_labware_id: str,
            return_labware_type: str,
            return_positions: list[tuple[int, int]],
            pick_labware_id: str,
            pick_labware_type: str,
            pick_positions: list[tuple[int, int]],
            channels: int
    ) -> Operation:
        """Build a REPLACE_TIPS operation"""
        description = (f"Replace tips: return to {return_labware_id} at {return_positions} "
                       f"& pick from {pick_labware_id} at {pick_positions}")

        return Operation(
            operation_type=OperationType.REPLACE_TIPS,
            parameters={
                'return_labware': {'id': return_labware_id, 'type': return_labware_type},
                'return_positions': return_positions,
                'pick_labware': {'id': pick_labware_id, 'type': pick_labware_type},
                'pick_positions': pick_positions,
                'channels': channels,
            },
            description=description
        )

    @staticmethod
    def build_discard_tips(labware_id: str, labware_type: str) -> Operation:
        """Build a DISCARD_TIPS operation"""
        description = f"Discard tips to {labware_id}"
        params = {'labware': {'id': labware_id, 'type': labware_type}}

        return Operation(
            operation_type=OperationType.DISCARD_TIPS,
            parameters=params,
            description=description
        )

    @staticmethod
    def build_add_medium(
            source_labware_id: str,
            source_labware_type: str,
            source_positions: list,
            dest_labware_id: str,
            dest_labware_type: str,
            dest_positions: list[tuple[int, int]],
            volume: float,
            channels: int,
            change_tips: bool = False,
            mix_volume: float = 0,
    ) -> Operation:
        """Build an ADD_MEDIUM operation"""

        total_wells = len(dest_positions) * (Pipettors_in_Multi if channels == Pipettors_in_Multi else 1)
        total_volume = volume * total_wells

        description = (
            f"Add medium: {source_labware_id} → {dest_labware_id} "
            f"({volume}µL/well, {total_wells} wells, {total_volume}µL total)"
        )

        params = {
            'source_labware': {'id': source_labware_id, 'type': source_labware_type},
            'source_positions': source_positions,
            'dest_labware': {'id': dest_labware_id, 'type': dest_labware_type},
            'dest_positions': dest_positions,
            'volume': volume,
            'channels': channels,
            'change_tips': change_tips,
            'mix_volume': mix_volume
        }

        return Operation(
            operation_type=OperationType.ADD_MEDIUM,
            parameters=params,
            description=description
        )

    @staticmethod
    def build_remove_medium(
            source_labware_id: str,
            source_labware_type: str,
            source_positions: list[tuple[int, int]],
            dest_labware_id: str,
            dest_labware_type: str,
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
            'source_labware': {'id': source_labware_id, 'type': source_labware_type},
            'source_positions': source_positions,
            'dest_labware': {'id': dest_labware_id, 'type': dest_labware_type},
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
            source_labware_type: str,
            source_positions: list[tuple[int, int]],
            dest_labware_id: str,
            dest_labware_type: str,
            dest_positions: list[tuple[int, int]],
            volume: float,
            channels: int,
            change_tips: bool = False,
            mix_volume: float = 0
    ) -> Operation:
        """Build a TRANSFER_PLATE_TO_PLATE operation"""
        total_wells = len(source_positions) * (Pipettors_in_Multi if channels == Pipettors_in_Multi else 1)
        total_volume = volume * total_wells

        description = (
            f"Transfer: {source_labware_id} → {dest_labware_id} "
            f"({volume}µL/well, {total_wells} wells, {total_volume}µL total)"
        )

        params = {
            'source_labware': {'id': source_labware_id, 'type': source_labware_type},
            'source_positions': source_positions,
            'dest_labware': {'id': dest_labware_id, 'type': dest_labware_type},
            'dest_positions': dest_positions,
            'volume': volume,
            'channels': channels,
            'change_tips': change_tips,
            'mix_volume': mix_volume
        }


        return Operation(
            operation_type=OperationType.TRANSFER_PLATE_TO_PLATE,
            parameters=params,
            description=description
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
            plate_labware_type: str,
            plate_positions: list[tuple[int, int]],
            remove_reservoir_id: str,
            remove_reservoir_type: str,
            remove_positions: tuple[int, int],
            source_reservoir_id: str,
            source_reservoir_type: str,
            source_positions: tuple[int, int],
            volume: float,
            channels: int,
            change_tips: bool = False,
            mix_volume: float = 0
    ) -> Operation:
        """
        Remove medium from plate positions to reservoir, then add fresh medium from source (BATCHED).
        Handles positions in batches based on tip capacity to avoid pipettor timeout."""
        return Operation(
            operation_type=OperationType.REMOVE_AND_ADD,
            description=f"Remove {volume}µL from {len(plate_positions)} positions, add fresh from source (batched)",
            parameters={
                'plate_labware': {'id': plate_labware_id, 'type': plate_labware_type},
                'plate_positions': plate_positions,
                'remove_reservoir': {'id': remove_reservoir_id, 'type': remove_reservoir_type},
                'remove_positions': remove_positions,
                'source_reservoir': {'id': source_reservoir_id, 'type': source_reservoir_type},
                'source_positions': source_positions,
                'volume': volume,
                'channels': channels,
                'change_tips': change_tips,
                'mix_volume': mix_volume,
            }
        )