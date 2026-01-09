from biohit_pipettor_plus.deck_structure.labware_classes import *


# ========== STEP TEMPLATES ==========
def labware_step(labware_type, label, source_mode=False, constraint_operation=None):
    """Generate labware step config"""
    config = {
        'type': labware_type,
        'label': label,
        'source_mode': source_mode
    }
    if constraint_operation:
        config['constraint_operation'] = constraint_operation
    return config


def positions_step(labware_key, max_selected=None, allow_auto_select=False):
    """Generate positions step config"""
    config = {
        'labware_key': labware_key,
        'max_selected': max_selected
    }
    if allow_auto_select:
        config['allow_auto_select'] = True
    return config


# ========== OPERATION TEMPLATES ==========

def liquid_transfer_operation(
        operation_key,
        display_name,
        source_type,
        dest_type,
        source_label,
        dest_label,
        needs_mixing=False,
        validate_count_match=False
):
    """Template for liquid transfer operations"""
    return {
        'display_name': display_name,
        'parts': ['volume', 'source_labware', 'source_positions', 'dest_labware', 'dest_positions'],
        'builder_method': f'build_{operation_key}',
        'needs_tip_change': True,
        'needs_mixing': needs_mixing,
        'needs_channels': True,
        'validate_count_match': validate_count_match,
        'source_labware': labware_step(source_type, source_label, source_mode=True, constraint_operation='removal'),
        'dest_labware': labware_step(dest_type, dest_label, source_mode=False, constraint_operation='addition'),
        'source_positions': positions_step('source_labware',  max_selected=1
                                if source_type == ReservoirHolder else None),
        'dest_positions': positions_step('dest_labware',
                                         max_selected=1 if dest_type == ReservoirHolder else None)
    }


def tip_operation(operation_key, display_name, label, source_mode):
    """Template for tip operations (pick/return)"""
    return {
        'display_name': display_name,
        'parts': ['labware', 'positions'],
        'builder_method': f'build_{operation_key}',
        'needs_channels': True,
        'labware': labware_step(PipetteHolder, label, source_mode=source_mode),
        'positions': positions_step('labware', max_selected=1, allow_auto_select=True)
    }


def movement_operation(operation_key, display_name, axes):
    """Template for movement operations"""
    return {
        'display_name': display_name,
        'parts': ['position'],
        'builder_method': f'build_{operation_key}',
        'axes': axes
    }


# ========== GENERATED CONFIG ==========

OPERATION_CONFIGS = {
    # === LIQUID OPERATIONS ===
    'add_medium': liquid_transfer_operation(
        'add_medium',
        'Add Medium',
        source_type=ReservoirHolder,
        dest_type=Plate,
        source_label='reservoir to aspirate from',
        dest_label='plate to dispense to',
        needs_mixing=True
    ),

    'remove_medium': liquid_transfer_operation(
        'remove_medium',
        'Remove Medium',
        source_type=Plate,
        dest_type=ReservoirHolder,
        source_label='plate to aspirate from',
        dest_label='reservoir to dispense to',
        needs_mixing=False
    ),

    'transfer_plate_to_plate': liquid_transfer_operation(
        'transfer_plate_to_plate',
        'Transfer Plate to Plate',
        source_type=Plate,
        dest_type=Plate,
        source_label='source plate',
        dest_label='destination plate',
        needs_mixing=True,
        validate_count_match=True
    ),

    # === TIP OPERATIONS ===
    'pick_tips': tip_operation('pick_tips', 'Pick Tips', 'tip holder to pick from', source_mode=True),
    'return_tips': tip_operation('return_tips', 'Return Tips', 'tip holder to return to', source_mode=False),

    'discard_tips': {
        'display_name': 'Discard Tips',
        'parts': ['labware'],
        'builder_method': 'build_discard_tips',
        'labware': labware_step(TipDropzone, 'dropzone to discard to')
    },

    'replace_tips': {
        'display_name': 'Replace Tips',
        'parts': ['return_labware', 'return_positions', 'pick_labware', 'pick_positions'],
        'builder_method': 'build_replace_tips',
        'needs_channels': True,
        'return_labware': labware_step(PipetteHolder, 'tip holder to return to', source_mode=False),
        'return_positions': positions_step('return_labware', max_selected=1, allow_auto_select=True),
        'pick_labware': labware_step(PipetteHolder, 'tip holder to pick from', source_mode=True),
        'pick_positions': positions_step('pick_labware', max_selected=1, allow_auto_select=True)
    },

    # === MOVEMENT OPERATIONS ===
    'move_xy': movement_operation('move_xy', 'Move X, Y', [
        ('X', 'range_x', 'x_position'),
        ('Y', 'range_y', 'y_position')
    ]),

    'move_z': movement_operation('move_z', 'Move Z', [
        ('Z', 'range_z', 'z_position')
    ]),

    'home': {
        'display_name': 'Home',
        'parts': [],
        'builder_method': 'build_home'
    },

    # === SPECIALIZED OPERATIONS ===
    'measure_foc': {
        'display_name': 'Measure FOC',
        'parts': ['wait_time'],
        'builder_method': 'build_measure_foc',
        'wait_time_label': 'Incubation time (sec):'
    },

    'remove_and_add': {
        'display_name': 'Remove & Add',
        'parts': ['volume', 'plate_labware', 'plate_positions', 'remove_reservoir', 'remove_positions',
                  'source_reservoir', 'source_positions'],
        'builder_method': 'build_remove_and_add',
        'needs_tip_change': True,
        'needs_mixing': True,
        'needs_channels': True,

        'plate_labware': labware_step(Plate, 'plate to work with', source_mode=True, constraint_operation='removal'),
        'plate_positions': positions_step('plate_labware', max_selected=None),
        'remove_reservoir': labware_step(ReservoirHolder, 'reservoir to remove to (old medium)', source_mode=False,
                                         constraint_operation='addition'),
        'remove_positions': positions_step('remove_reservoir', max_selected=1),
        'source_reservoir': labware_step(ReservoirHolder, 'reservoir to add from (fresh medium)', source_mode=True,
                                         constraint_operation='removal'),
        'source_positions': positions_step('source_reservoir', max_selected=1)
    }
}