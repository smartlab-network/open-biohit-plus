from enum import Enum

class OperationType(Enum):
    """Types of pipetting operations"""
    PICK_TIPS = "pick_tips"
    RETURN_TIPS = "return_tips"
    REPLACE_TIPS = "replace_tips"
    DISCARD_TIPS = "discard_tips"
    ADD_MEDIUM = "add_medium"
    REMOVE_MEDIUM = "remove_medium"
    TRANSFER_PLATE_TO_PLATE = "transfer_plate_to_plate"
    SUCK = "suck"
    SPIT = "spit"
    HOME = "home"
    MOVE_XY = "move_xy"
    MOVE_Z = "move_z"
    MEASURE_FOC = "measure_foc"
    REMOVE_AND_ADD = "remove_and_add"