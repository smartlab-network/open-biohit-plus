"""
Headless workflow execution - no GUI required
Run saved workflows automatically from command line with validation
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from src.biohit_pipettor_plus.deck_structure import Deck, Serializable
from src.biohit_pipettor_plus.pipettor_plus.pipettor_plus import PipettorPlus
from src.biohit_pipettor_plus.operations.workflow import Workflow
from src.biohit_pipettor_plus.operations.operation_logger import OperationLogger


def load_deck(deck_path: str) -> Deck:
    """Load deck from JSON file"""
    print(f"Loading deck from: {deck_path}")
    with open(deck_path, 'r') as f:
        data = json.load(f)

    # Handle both formats (deck directly or nested in 'deck' key)
    if 'deck' in data:
        deck_data = data['deck']
    else:
        deck_data = data

    deck = Serializable.from_dict(deck_data)
    print(f"✓ Deck loaded: {deck.deck_id}")
    return deck


def initialize_pipettor(deck: Deck, config: dict) -> PipettorPlus:
    """Initialize pipettor with given configuration"""
    print("\nInitializing pipettor...")

    tip_volume = config.get('tip_volume', 1000)
    multichannel = config.get('multichannel', True)
    initialize_hw = config.get('initialize', True)
    tip_length = config.get('tip_length', None)

    # Optional speed settings
    x_speed = config.get('x_speed', None)
    y_speed = config.get('y_speed', None)
    z_speed = config.get('z_speed', None)
    aspirate_speed = config.get('aspirate_speed', None)
    dispense_speed = config.get('dispense_speed', None)

    pipettor = PipettorPlus(
        tip_volume=tip_volume,
        multichannel=multichannel,
        initialize=initialize_hw,
        deck=deck,
        tip_length=tip_length
    )

    # Set speeds if provided
    if x_speed is not None:
        pipettor.x_speed = x_speed
    if y_speed is not None:
        pipettor.y_speed = y_speed
    if z_speed is not None:
        pipettor.z_speed = z_speed
    if aspirate_speed is not None:
        pipettor.aspirate_speed = aspirate_speed
    if dispense_speed is not None:
        pipettor.dispense_speed = dispense_speed

    # Configure FOC if provided
    foc_script = config.get('foc_bat_script_path', None)
    foc_plate = config.get('foc_plate_name', None)

    if foc_script:
        pipettor.foc_bat_script_path = foc_script
        print(f"✓ FOC script configured: {foc_script}")

    if foc_plate:
        pipettor.foc_plate_name = foc_plate
        print(f"✓ FOC plate name: {foc_plate}")

    mode = "Multichannel" if multichannel else "Single channel"
    hw_status = "initialized" if initialize_hw else "not initialized"
    print(f"✓ Pipettor ready: {mode}, {tip_volume}µL tips, hardware {hw_status}")

    return pipettor


def load_workflow(workflow_path: str) -> Workflow:
    """Load workflow from JSON file"""
    print(f"\nLoading workflow from: {workflow_path}")
    workflow = Workflow.load_from_file(workflow_path)
    print(f"✓ Workflow loaded: {workflow.name}")
    print(f"  {len(workflow.operations)} operations")
    return workflow


def validate_workflow(pipettor: PipettorPlus, deck: Deck, workflow: Workflow) -> bool:
    """
    Validate workflow by simulating execution.

    Returns
    -------
    bool
        True if workflow is valid, False otherwise
    """
    print("\n" + "=" * 60)
    print("VALIDATING WORKFLOW")
    print("=" * 60)

    # Save current state
    state_snapshot = pipettor.push_state()

    # Enable simulation mode
    pipettor.set_simulation_mode(True)

    try:
        for i, operation in enumerate(workflow.operations, 1):
            print(f"Validating operation {i}/{len(workflow.operations)}: {operation.operation_type.value}")

            try:
                operation.execute(pipettor, deck)
                print(f"  ✓ Operation {i} valid")

            except Exception as e:
                print(f"\n❌ VALIDATION FAILED at operation {i}")
                print(f"Operation: {operation.operation_type.value}")
                print(f"Error: {str(e)}")

                # Restore state
                pipettor.pop_state(state_snapshot)

                return False

        # All operations valid
        print("\n" + "=" * 60)
        print("✓ WORKFLOW VALIDATION PASSED")
        print(f"  All {len(workflow.operations)} operations are valid")
        print("=" * 60)

        # Restore state
        pipettor.pop_state(state_snapshot)

        return True

    except Exception as e:
        print(f"\n❌ VALIDATION ERROR: {str(e)}")
        pipettor.pop_state(state_snapshot)
        return False


def execute_workflow(pipettor: PipettorPlus, deck: Deck, workflow: Workflow,
                     logger: OperationLogger, dry_run: bool = False):
    """Execute workflow with validation and logging"""

    # ALWAYS validate first
    print("\nValidating workflow before execution...")
    if not validate_workflow(pipettor, deck, workflow):
        raise ValueError("Workflow validation failed. Aborting execution.")
    print("\n✓ Validation successful - proceeding with execution\n")

    if dry_run:
        print("\n" + "=" * 60)
        print("DRY RUN MODE - Simulating workflow execution")
        print("=" * 60)
        pipettor.set_simulation_mode(True)
    else:
        print("\n" + "=" * 60)
        print("EXECUTING WORKFLOW")
        print("=" * 60)

    logger.log_workflow_start(workflow.name, len(workflow.operations))

    try:
        for i, operation in enumerate(workflow.operations, 1):
            print(f"\nOperation {i}/{len(workflow.operations)}: {operation.operation_type.value}")

            try:
                operation.execute(pipettor, deck)
                logger.log_success(
                    mode="automated",
                    operation=operation,
                    workflow_name=workflow.name
                )
                print(f"✓ Operation {i} complete")

            except Exception as op_error:
                # Log failed operation
                logger.log_failure(
                    mode="automated",
                    operation=operation,
                    error_message=str(op_error),
                    workflow_name=workflow.name
                )

                # Log workflow failure
                logger.log_workflow_failed(
                    workflow_name=workflow.name,
                    failed_at=i - 1,
                    total_operations=len(workflow.operations),
                    error_message=str(op_error)
                )

                print(f"\n❌ WORKFLOW FAILED at operation {i}")
                print(f"Error: {str(op_error)}")
                raise

        # All operations succeeded
        logger.log_workflow_complete(
            workflow_name=workflow.name,
            num_completed=len(workflow.operations),
            total_operations=len(workflow.operations)
        )

        print("\n" + "=" * 60)
        print(f"✓ WORKFLOW COMPLETE: {workflow.name}")
        print(f"  {len(workflow.operations)} operations executed successfully")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n\n⚠️ Workflow interrupted by user")
        logger.log_workflow_failed(
            workflow_name=workflow.name,
            failed_at=i - 1,
            total_operations=len(workflow.operations),
            error_message="User interrupted"
        )
        raise


def main():
    parser = argparse.ArgumentParser(
        description='Execute Biohit Pipettor Plus workflows without GUI (with validation)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""

Examples:
  # Validate and execute (real hardware)
  python run_workflow.py --deck deck.json --config pipettor_config.json --workflow my_workflow.json

  # Validate only (don't execute on hardware)
  python run_workflow.py --deck deck.json --config pipettor_config.json --workflow my_workflow.json --validate-only

  # Validate and dry run (simulation mode)
  python run_workflow.py --deck deck.json --config pipettor_config.json --workflow my_workflow.json --dry-run

Notes:
  - Validation ALWAYS runs before execution
  - Use --validate-only to check workflow without running hardware
  - Use --dry-run to simulate execution after validation
        """
    )

    parser.add_argument('--deck', required=True, help='Path to deck JSON file')
    parser.add_argument('--config', required=True, help='Path to pipettor configuration JSON file')
    parser.add_argument('--workflow', required=True, help='Path to workflow JSON file')
    parser.add_argument('--dry-run', action='store_true', help='Validate then simulate execution (no hardware)')
    parser.add_argument('--validate-only', action='store_true', help='Only validate workflow, do not execute')

    args = parser.parse_args()

    # Validate files exist
    for path_arg, path_val in [('deck', args.deck), ('config', args.config), ('workflow', args.workflow)]:
        if not Path(path_val).exists():
            print(f"ERROR: {path_arg} file not found: {path_val}")
            sys.exit(1)

    try:
        # Create logs directory in project root
        project_root = Path(__file__).parent
        log_dir = project_root / "logs"
        log_dir.mkdir(exist_ok=True)

        # Initialize logger with absolute path
        logger = OperationLogger(log_dir=str(log_dir))
        print(f"✓ Logger initialized - logs will be saved to: {log_dir}")

        # Load deck
        deck = load_deck(args.deck)

        # Load pipettor config
        print(f"\nLoading pipettor config from: {args.config}")
        with open(args.config, 'r') as f:
            pipettor_config = json.load(f)

        # Initialize pipettor
        pipettor = initialize_pipettor(deck, pipettor_config)

        # Load workflow
        workflow = load_workflow(args.workflow)

        # Validate only mode
        if args.validate_only:
            if validate_workflow(pipettor, deck, workflow):
                print("\n✓ Workflow is valid and ready for execution")
                return 0
            else:
                print("\n❌ Workflow validation failed")
                return 1

        # Validate and execute
        execute_workflow(pipettor, deck, workflow, logger, dry_run=args.dry_run)

        print("✓ Execution complete - check logs")
        return 0

    except KeyboardInterrupt:
        print("\n\n⚠️ Execution interrupted by user")
        return 130

    except Exception as e:
        print(f"\n❌ FATAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())