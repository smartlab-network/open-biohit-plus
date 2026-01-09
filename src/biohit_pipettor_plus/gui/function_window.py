import ttkbootstrap as ttk
import tkinter as tk
import uuid
import threading
from typing import Callable, Optional
from tkinter import messagebox, filedialog

from biohit_pipettor_plus.gui.well_window import WellWindow
from biohit_pipettor_plus.gui.ui_helper import *
from biohit_pipettor_plus.pipettor_plus.pipettor_plus import PipettorPlus
from biohit_pipettor_plus.deck_structure import *
from biohit_pipettor_plus.operations.workflow import Workflow
from biohit_pipettor_plus.operations.operation import Operation
from biohit_pipettor_plus.operations.operation_builder import OperationBuilder
from biohit_pipettor_plus.operations.operation_logger import OperationLogger
from biohit_pipettor_plus.gui.executioncontroloverlay import ExecutionControlOverlay
from biohit_pipettor_plus.gui.operationconfig import OPERATION_CONFIGS
from biohit_pipettor_plus.gui.operationsession import OperationSession

import os
import copy

class FunctionWindow:
    """
    Dual-mode operations interface.

    Modes
    -----
    direct : Embedded in main gui, operations staged for execution
    builder : Separate window for creating custom workflows
    """

    def __init__(
            self,
            deck: Deck,
            pipettor: PipettorPlus = None,
            mode: str = "direct",
            master: tk.Tk = None,
            parent_frame: ttk.Frame = None,
            on_operation_complete: Callable = None
    ):
        """
        Initialize FunctionWindow.

        Parameters
        ----------
        deck : Deck
            The deck containing labware
        pipettor : PipettorPlus
            Pipettor instance
        mode : str
            "direct" for immediate staging, "builder" for workflow creation
        master : tk.Tk
            Parent window (for builder mode)
        parent_frame : ttk.Frame
            Parent frame to embed in (for direct mode)
        """
        self.deck = deck
        self.pipettor = pipettor
        self.mode = mode
        self.on_operation_complete = on_operation_complete
        self.channels = self.pipettor.tip_count
        self.multichannel = self.pipettor.multichannel
        self.current_session: Optional[OperationSession] = None

        if mode == "builder":
            self._state_snapshot = self.pipettor.push_state()
            self.pipettor.set_simulation_mode(True)
            self.workflow = Workflow(name="New Workflow")
            self.parent_function_window = None
            self.workflow_validated = False
            self.workflow_modified = False
            self.edit_mode = False
            self.edit_index = None
            self.selected_operations = set()  # Set of indices
            self.clipboard_operations = []  # List of Operation objects
        else:
            self.workflow = None
            self.workflows_in_memory = {}
            self.workflows_dir = "../saved_workflows"
            os.makedirs(self.workflows_dir, exist_ok=True)

            self.operation_logger = OperationLogger()

        #for direct mode
        self.custom_funcs_dict: dict[str, list[Callable]] = {}
        self.current_func_list: list[Callable] = []
        self.current_func_details: list[str] = []  # For display

        # Staging state (direct mode)
        self.staged_operation: Optional[Callable] = None
        self.staged_operation_name: Optional[str] = None
        self.staged_operation_details: Optional[str] = None
        self.staged_operation_validated: bool = False

        # Get available labware
        self.dict_top_labware = self.get_top_labwares()

        # wrapper for all operations
        for op_key in OPERATION_CONFIGS.keys():
            setattr(self, f'callback_{op_key}',
                    lambda e=False, k=op_key: self._start_operation(k, e))

        # Create UI based on mode
        if mode == "direct":
            self.container = parent_frame
            self.is_toplevel = False
            self.create_direct_mode_ui()

        elif mode == "builder":
            if isinstance(master, (ttk.Window, tk.Tk)):
                self.window_build_func = ttk.Toplevel(master)
            else:
                self.window_build_func = ttk.Window(themename="darkly")

            self.window_build_func.geometry("1300x900")
            self.window_build_func.title("Workflow Builder")
            self.window_build_func.attributes('-topmost', False)

            self.window_build_func.transient(master)  # Tells window manager this belongs to 'master'
            self.window_build_func.grab_set()  # Freezes interaction with other windows
            self.window_build_func.focus_set()  # Moves keyboard focus here

            self.container = self.window_build_func
            self.is_toplevel = True
            self.create_builder_mode_ui()


    # ========== UI CREATION ==========
    def create_direct_mode_ui(self):
        """Create embedded UI for direct execution with staging area"""

        scrollable = ScrollableTab(self.container)
        self.control_frame = scrollable.content_frame

        # Title
        ttk.Label( self.control_frame, text="Operations",
            font=('Arial', 14, 'bold')).pack(pady=5)

        # === CUSTOM WORKFLOWS SECTION ===
        workflows_frame = ttk.Labelframe(self.control_frame, text="Custom Workflows", padding=10)
        workflows_frame.pack(fill=tk.X, padx=10, pady=5)

        # Workflow listbox
        self.workflows_listbox, _ = create_scrolled_listbox(
            workflows_frame, items=[],
            label_text="", height=5
        )

        # Workflow buttons
        button_configs = [
            {"text": "Create", "command": self.open_workflow_builder},
            {"text": "Open", "command": self.open_selected_workflow},
            {"text": "Delete", "command": self.delete_selected_workflow},
            {"text": "Save to File", "command": self.save_selected_workflow_to_file},
            {"text": "Load from File", "command": self.load_workflow_from_file},
        ]
        create_button_bar(workflows_frame, button_configs, fill=True, btns_per_row=3)

        # Initialize workflows
        self.workflows_in_memory = {}
        self.refresh_workflows_list()

        # === STAGING AREA ===
        staging_frame, self.staged_op_text = create_info_panel(
            parent=self.control_frame,  title="Validate & Execute ",
            height=8, clear_cmd=None, collapsed=False)

        # Custom staging buttons
        button_configs = [
        {"text": "Validate", "command": self.validate_staged_operation, "state": "disabled"},
        {"text": "Clear", "command": self.clear_staged_operation, "state": "disabled"}
        ]

        action_frame, buttons = create_button_bar(staging_frame.content_frame,
            button_configs, fill=True,  btns_per_row=2)

        self.execute_button = buttons["Validate"]
        self.clear_button = buttons["Clear"]

        # Operation buttons
        self.place_operation_buttons(self.control_frame)

    def validate_staged_operation(self):
        """Validate the staged operation in simulation mode"""
        if self.staged_operation is None:
            return

        try:
            # Save current state
            state_snapshot = self.pipettor.push_state()

            # Enable simulation mode
            self.pipettor.set_simulation_mode(True)

            # Try to execute in simulation
            self.staged_operation.execute(self.pipettor, self.deck)

            # Restore state
            self.pipettor.pop_state(state_snapshot)
            self.pipettor.set_simulation_mode(False)

            # Mark as validated
            self.staged_operation_validated = True
            self.update_staged_display()

        except Exception as e:
            # Restore state on error
            self.pipettor.pop_state(state_snapshot)
            self.pipettor.set_simulation_mode(False)
            messagebox.showerror(
                "Validation Failed",
                f"Operation validation failed:\n\n{str(e)}"
            )

    def create_builder_mode_ui(self):
        """Create full UI for workflow builder in separate window with scrolling"""

        scrollable = ScrollableTab(self.window_build_func)
        content_frame = scrollable.content_frame

        # Grid configuration
        for i in range(3):
            content_frame.columnconfigure(i, weight=1, uniform="equal")
        for i in range(12):
            content_frame.rowconfigure(i, weight=1)

        # Header
        self.label_header = ttk.Label(
            content_frame,
            text="",
            anchor="center",
            font=('Helvetica', 14)
        )
        self.label_header.grid(row=0, column=0, columnspan=3, sticky="nsew", pady=10)

        # Left column: Operation buttons
        button_container = ttk.Frame(content_frame)
        button_container.grid(row=1, column=0, rowspan=10, sticky="nsew", padx=5)
        self.place_operation_buttons(button_container)

        # Middle column: Selection area
        self.stage_label = ttk.Label(content_frame, text="", foreground="gray",
                                     wraplength=350,anchor="w",justify="left")
        self.stage_label.grid(row=1, column=1, sticky="ew", padx=5, pady=2)

        self.edit_info_label = ttk.Label(content_frame, text="", font=('Arial', 10, 'bold'), foreground="orange",
                                         wraplength=350,anchor="w",justify="left")
        self.edit_info_label.grid(row=2, column=1, sticky="ew", padx=5, pady=2)


        self.second_column_frame = ttk.Frame(content_frame)
        self.second_column_frame.grid(row=3, column=1, rowspan=9, sticky="nsew")
        self.second_column_frame.columnconfigure(0, weight=1)
        for i in range(10):
            self.second_column_frame.rowconfigure(i, weight=1)

        # Right column: Queue header
        queue_header_frame = ttk.Frame(content_frame)
        queue_header_frame.grid(row=0, column=2, sticky="ew", padx=10, pady=5)
        queue_header_frame.columnconfigure(0, weight=1)

        ttk.Label(queue_header_frame, text="Workflow Queue", font=('Helvetica', 14)).grid(row=0, column=0, sticky="w")

        controls_frame = ttk.Frame(queue_header_frame)
        controls_frame.grid(row=0, column=1, sticky="e")

        button_configs = [
            {"text": "Copy", "command": self.copy_selected_operations, "state": "disabled"},
            {"text": "Paste", "command": self.paste_operations, "state": "disabled",}
        ]
        _, buttons = create_button_bar(controls_frame, button_configs, btns_per_row=2)
        self.copy_btn = buttons["Copy"]
        self.paste_btn = buttons["Paste"]

        self.paste_position_var = tk.StringVar(value="End")
        self.paste_position_menu = ttk.Combobox(controls_frame, textvariable=self.paste_position_var,
                                                values=["End", "Top", "Or enter index..."], width=12, state='disabled')
        self.paste_position_menu.pack(side=tk.LEFT, padx=3)

        # Right column: Queue display
        self.third_column_frame = ttk.Frame(content_frame)
        self.third_column_frame.grid(row=1, column=2, rowspan=9, sticky="nsew", padx=5)
        self.third_column_frame.columnconfigure(0, weight=1)
        for i in range(20):
            self.third_column_frame.rowconfigure(i, weight=1)

        # Bottom: Workflow controls
        self.frame_name = ttk.Frame(content_frame)
        self.frame_name.grid(row=11, column=0, columnspan=3, sticky="nsew", padx=10, pady=5)

        self.frame_name.columnconfigure(0, weight=3)
        for i in range(1, 6):
            self.frame_name.columnconfigure(i, weight=1)

        ttk.Label(self.frame_name, text="Workflow Name:", font=('Arial', 11)).grid(row=0, column=0, sticky='w',
                                                                                   padx=(0, 10))

        self.entry_name = ttk.Entry(self.frame_name)
        self.entry_name.grid(row=1, column=0, sticky="ew", padx=(0, 10))

        # Workflow control buttons
        buttons = [
            ("Create", self.callback_create_button, "success"),
            ("Clear", self.clear_workflow_queue, "danger"),
            ("Remap", self.callback_remap_labware, "info"),
            ("Validate", self.callback_validate_workflow, "warning"),
            ("Close", self.callback_close_builder, "secondary")
        ]

        for i, (text, cmd, style) in enumerate(buttons, start=1):
            btn = ttk.Button(self.frame_name, text=text, command=cmd, bootstyle=style)
            btn.grid(row=1, column=i, sticky="ew", padx=2)
            if text == "Validate":
                self.validate_execute_btn = btn

    def set_stage(self, text: str):
        """Update stage indicator"""
        if self.mode == "builder" and hasattr(self, 'stage_label'):
            self.stage_label.config(text=text)

    def place_operation_buttons(self, parent_frame):
        """Place all operation buttons (shared between modes)"""

        # === TIP MANAGEMENT ===
        tip_frame = ttk.Labelframe(parent_frame, text="Tip Management", padding=10)
        tip_frame.pack(fill=tk.X, pady=5, padx=5)

        tip_buttons = [
            {"text": "Pick Tips", "command": self.callback_pick_tips},
            {"text": "Return Tips", "command": self.callback_return_tips},
            {"text": "Replace Tips", "command": self.callback_replace_tips},
            {"text": "Discard Tips", "command": self.callback_discard_tips}
        ]

        create_button_bar(tip_frame, tip_buttons, fill=True)

        # === LIQUID HANDLING ===
        liquid_frame = ttk.Labelframe(parent_frame, text="Liquid Handling", padding=10)
        liquid_frame.pack(fill=tk.X, pady=5, padx=5)

        # Change tips checkbox
        self.change_tips_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            liquid_frame,
            text="Auto change tips between Wells",
            variable=self.change_tips_var,
            bootstyle="round-toggle"
        ).pack(fill=tk.X, pady=(0, 5), padx=5)

        ttk.Separator(liquid_frame, orient='horizontal').pack(fill=tk.X, pady=5)

        # Mixing controls
        self.enable_mixing_var = tk.BooleanVar(value=False)
        mixing_frame = ttk.Frame(liquid_frame)
        mixing_frame.pack(fill=tk.X, pady=(0, 10), padx=5)

        ttk.Checkbutton(
            mixing_frame,
            text="Enable mixing after dispense",
            variable=self.enable_mixing_var,
            bootstyle="round-toggle",
            command=self._toggle_mixing_controls
        ).pack(side=tk.LEFT)

        ttk.Label(mixing_frame, text="Volume:", font=('Arial', 9)).pack(side=tk.LEFT, padx=(10, 5))

        self.mix_volume_var = tk.StringVar(value="100")
        self.mix_volume_entry = ttk.Entry(mixing_frame, textvariable=self.mix_volume_var, width=8, state='disabled')
        self.mix_volume_entry.pack(side=tk.LEFT)

        ttk.Label(mixing_frame, text="µL", font=('Arial', 9)).pack(side=tk.LEFT, padx=(2, 5))

        ttk.Separator(liquid_frame, orient='horizontal').pack(fill=tk.X, pady=5)

        # Liquid operation buttons
        liquid_buttons = [
            {"text": "Add Medium", "command": self.callback_add_medium},
            {"text": "Remove Medium", "command": self.callback_remove_medium},
            {"text": "Transfer Plate to Plate", "command": self.callback_transfer_plate_to_plate},
            {"text": "Remove & Add (Batched)", "command": self.callback_remove_and_add},
        ]

        create_button_bar(liquid_frame, liquid_buttons, fill=True)

        # === FOC MEASUREMENT ===
        self.foc_frame = ttk.Labelframe(parent_frame, text="FOC Measurement", padding=5)
        self.foc_frame.pack(fill=tk.X, pady=5, padx=5)
        self.update_foc_section()

        # === SYSTEM OPERATIONS (COLLAPSIBLE) ===
        self.system_collapsible = CollapsibleFrame(parent_frame, text="System", collapsed=False)
        self.system_collapsible.pack(fill=tk.X, pady=5, padx=5)

        system_buttons = [
            {"text": "Home", "command": lambda: self.callback_home(),},
            {"text": "Move X, Y", "command": lambda: self.callback_move_xy()},
            {"text": "Move Z", "command": lambda: self.callback_move_z()}
        ]

        if self.mode == "direct":
            system_buttons.extend([
                {"text": "⚠ Force Eject Tips", "command": self.callback_force_eject},
                {"text": "⚠ Force Aspirate", "command": self.callback_force_aspirate},
                {"text": "⚠ Force Dispense", "command": self.callback_force_dispense}
            ])

        create_button_bar(self.system_collapsible.content_frame, system_buttons, fill=True)

    def run_operation_wizard(self):
        """Main wizard controller - routes to appropriate step handler"""
        if not self.current_session:
            return

        session = self.current_session
        step_key = session.current_step()

        # Check if complete
        if session.is_complete():
            self._finalize_operation(session)
            self.current_session = None
            return

        # Update stage label (for builder mode)
        if self.mode == "builder" and hasattr(self, 'stage_label'):
            progress = session.get_progress()
            self.stage_label.config(text=f"{progress}: {session.config['display_name']}")

        # Route to appropriate handler
        if step_key == 'volume':
            self._handle_volume_step(session)
        elif step_key == 'wait_time':
            self._handle_wait_time_step(session)
        elif step_key == 'position':
            self._handle_position_step(session)
        elif 'labware' in step_key or 'reservoir' in step_key:
            self._handle_labware_step(step_key, session)
        elif 'wells' in step_key or 'positions' in step_key:
            self._handle_wells_step(step_key, session)
        else:
            raise ValueError(f"Unknown step type: {step_key}")

    # ========== STEP HANDLERS ==========
    def _handle_volume_step(self, session: OperationSession):
        """Handle volume input step"""
        self.set_stage("")
        volume = self.ask_volume_dialog(
            title=f"{session.config['display_name']} Volume",
            initial_value=100
        )

        if volume is not None:
            session.store('volume', volume)
            session.advance()
            self.run_operation_wizard()
        # If cancelled, session stays at current step (user can try again or cancel operation)

    def _handle_wait_time_step(self, session: OperationSession):
        """Handle wait time input step (for FOC measurement)"""
        self.set_stage("")
        label = session.config.get('wait_time_label', 'Wait time (sec):')

        wait_time = self.ask_volume_dialog(
            title=f"{session.config['display_name']}",
            initial_value=0,
            label_text=label
        )

        if wait_time is not None:
            session.store('wait_seconds', int(wait_time))
            session.advance()
            self.run_operation_wizard()

    def _handle_position_step(self, session: OperationSession):
        """Handle X/Y/Z position input step"""
        self.set_stage("")

        # Build axes config from session config
        axes_config = []
        for axis_name, range_attr, position_attr in session.config['axes']:
            deck_range = getattr(self.deck, range_attr)
            current_pos = getattr(self.pipettor, position_attr, 0.0)

            if axis_name == 'Z':
                min_val, max_val = 0.0, deck_range
            else:
                min_val, max_val = deck_range[0], deck_range[1]

            axes_config.append((axis_name, min_val, max_val, current_pos))

        result = self.ask_position_dialog(axes_config)

        if result is not None:
            # Store based on number of axes
            if len(axes_config) == 1:
                session.store(session.config['axes'][0][0].lower(), result)
            else:
                for i, (axis_name, _, _, _) in enumerate(axes_config):
                    session.store(axis_name.lower(), result[i])

            session.advance()
            self.run_operation_wizard()

    def _handle_labware_step(self, step_key: str, session: OperationSession):
        """Handle labware selection step"""
        labware_config = session.config.get(step_key, {})

        if not labware_config:
            raise ValueError(f"No config found for step: {step_key}")

        labware_type = labware_config['type']
        label = labware_config['label']

        if self.mode == "builder":
            self.clear_grid(self.second_column_frame)

        self.set_stage(f"choose {label}")

        # Check if user came back to this step (don't auto-select)
        auto_select = not session.came_from_back

        # Show labware selection UI
        self.display_possible_labware(
            labware_type=labware_type,
            next_callback=lambda labware_obj: self._on_labware_selected(step_key, labware_obj, session),
            auto_select_single=auto_select
        )

    def _on_labware_selected(self, step_key: str, labware_obj: Labware, session: OperationSession):
        """Callback when user selects a labware"""
        session.store(step_key, labware_obj)
        session.advance()
        self.run_operation_wizard()

    def _handle_wells_step(self, step_key: str, session: OperationSession):
        """Handle well/position selection step"""
        wells_config = session.config.get(step_key, {})

        if not wells_config:
            raise ValueError(f"No config found for step: {step_key}")

        # Get the associated labware object
        labware_key = wells_config['labware_key']
        labware_obj = session.selections.get(labware_key)

        if not labware_obj:
            raise ValueError(f"Labware not selected yet for {labware_key}")

        # Get labware config for constraints
        labware_config = session.config.get(labware_key, {})

        # Determine multichannel mode based on labware type
        if isinstance(labware_obj, ReservoirHolder) and not labware_obj.each_tip_needs_separate_item():
            # Shared reservoirs don't need multichannel selection
            multichannel_mode = False
        else:
            # Use the pipettor's current configuration
            multichannel_mode = self.multichannel  # ← CHANGED: Always use pipettor's mode

        # Get dimensions
        if isinstance(labware_obj, Plate):
            rows, cols = labware_obj._rows, labware_obj._columns
        elif isinstance(labware_obj, ReservoirHolder):
            rows, cols = labware_obj.hooks_across_y, labware_obj.hooks_across_x
        elif isinstance(labware_obj, PipetteHolder):
            rows, cols = labware_obj.holders_across_y, labware_obj.holders_across_x
        else:
            raise TypeError(f"Unsupported labware type: {type(labware_obj)}")

        # Get available wells
        source_mode = labware_config.get('source_mode', False)
        wells_list = self.get_wells_list_from_labware(labware_obj, source=source_mode)

        # For builder mode, show all positions. max_selected for tip_operation is none if in direct mode
        if self.mode == "builder":
            wells_list = [(r, c) for r in range(rows) for c in range(cols)]
            max_selected = wells_config.get('max_selected',1)
        else:
            # Direct mode: check if this is a tip operation on PipetteHolder
            if isinstance(labware_obj, PipetteHolder):
                max_selected = None
            else:
                max_selected = wells_config.get('max_selected', None)

        # Show well selection window
        window = WellWindow(
            rows=rows,
            columns=cols,
            labware_id=labware_obj.labware_id,
            max_selected=max_selected,
            multichannel_mode=multichannel_mode,
            master=self.get_master_window(),
            title=f"Select wells on {labware_obj.labware_id}",
            wells_list=wells_list,
            allow_auto_select=wells_config.get('allow_auto_select', False)
        )

        self.get_master_window().wait_window(window.get_root())

        if window.back_requested:
            if session.go_back():
                self.run_operation_wizard()
            else:
                # Already at first step - cancel operation
                self.current_session = None
                if self.mode == "builder":
                    self.clear_grid(self.second_column_frame)
                    self.stage_label.config(text="Select an operation to continue")
            return

        # Process selection
        if window.auto_selected:
            positions = None
        elif window.confirmed:
            if multichannel_mode:
                positions = [(c, r) for r, c in window.get_start_positions()]
            else:
                positions = [(c, r) for r, row in enumerate(window.well_state)
                             for c, v in enumerate(row) if v]
        else:
            # User cancelled
            self.current_session = None  # ← ADD THIS: Clear the session
            if self.mode == "builder":
                self.clear_grid(self.second_column_frame)
                self.stage_label.config(text="Select an operation to continue")
            return

        # handles edge case of empty selection:
        if window.auto_selected or (positions is not None and len(positions) > 0):
            session.store(step_key, positions)
            session.advance()
            self.run_operation_wizard()
        else:
            # Safety: User confirmed but has no selection (shouldn't happen with disabled button)
            self.current_session = None
            if self.mode == "builder":
                self.clear_grid(self.second_column_frame)
                self.stage_label.config(text="Select an operation to continue")

    def _finalize_operation(self, session: OperationSession):
        """Build and execute/stage the completed operation"""

        # Special validation for operations that need it
        if session.config.get('validate_count_match'):
            source_positions = session.selections.get('source_wells') or session.selections.get('source_positions')
            dest_positions = session.selections.get('dest_wells') or session.selections.get('dest_positions')

            if source_positions and dest_positions:
                if len(source_positions) != len(dest_positions):
                    messagebox.showerror(
                        "Selection Error",
                        f"Mismatch in selected positions!\n\n"
                        f"Source Count: {len(source_positions)}\n"
                        f"Destination Count: {len(dest_positions)}\n\n"
                        f"Please ensure counts match.",
                        parent=self.get_master_window()
                    )
                    return

        # Build operation using OperationBuilder
        builder_method_name = session.config['builder_method']
        builder_method = getattr(OperationBuilder, builder_method_name)

        # Extract parameters
        params = self._extract_builder_params(session)

        # Build operation
        operation = builder_method(**params)

        # Mode-specific handling
        self.mode_dependent_action(operation)

    def _extract_builder_params(self, session: OperationSession) -> dict:
        """Convert session selections to OperationBuilder parameters"""
        params = {}

        # Handle labware objects - extract id and type
        for key, value in session.selections.items():
            if isinstance(value, Labware):
                # Map to builder parameter names
                params[f'{key}_id'] = value.labware_id
                params[f'{key}_type'] = value.__class__.__name__
            else:
                # Direct mapping for simple types (volume, positions, etc.)
                params[key] = value

        # Add channels if required
        if session.config.get('needs_channels'):
            params['channels'] = self.channels

        # Add optional parameters based on config
        if session.config.get('needs_tip_change'):
            params['change_tips'] = self.change_tips_var.get()

        if session.config.get('needs_mixing'):
            params['mix_volume'] = self._get_mix_volume()

        # Special handling for specific operations
        if session.operation_key == 'measure_foc':
            params['plate_name'] = self.pipettor.foc_plate_name

        # Map parameter names that don't match builder expectations
        # (e.g., 'wells' -> 'positions')
        renamed_params = {}
        for key, value in params.items():
            if key.endswith('_wells'):
                # Rename source_wells -> source_positions, etc.
                new_key = key.replace('_wells', '_positions')
                renamed_params[new_key] = value
            else:
                renamed_params[key] = value

        return renamed_params

    def _toggle_mixing_controls(self):
        """Enable/disable mixing volume entry based on checkbox state"""
        if self.enable_mixing_var.get():
            self.mix_volume_entry.config(state='normal')
        else:
            self.mix_volume_entry.config(state='disabled')

    def _get_mix_volume(self) -> float:
        """
        Get mix volume from controls.

        Returns  float
            Mix volume in µL, or 0 if mixing is disabled or invalid
        """
        if not self.enable_mixing_var.get():
            return 0

        try:
            mix_vol = float(self.mix_volume_var.get())
            if mix_vol < 0:
                print("⚠️ Mix volume cannot be negative, using 0")
                return 0
            return mix_vol
        except ValueError:
            print("⚠️ Invalid mix volume, using 0")
            return 0

    def reorder_operation(self, current_index: int):
        """
        Ask user for new position and reorder the operation - NO VALIDATION.

        Parameters
        ----------
        current_index : int
            Current 0-based index of the operation to move
        """
        self.clear_edit_mode()
        if current_index >= len(self.workflow.operations):
            return

        operation = self.workflow.operations[current_index]
        total_ops = len(self.workflow.operations)

        # Ask for new position in second frame
        new_position = self.ask_position_in_second_frame(
            total_ops=total_ops,
            default_position=current_index,
            operation_name=f"#{current_index + 1}: {operation.operation_type.value}"
        )

        for widget in self.second_column_frame.winfo_children():
            widget.destroy()

        if new_position is None or new_position == current_index:
            return  # Cancelled or same position

        # Update selection if this operation was selected
        if current_index in self.selected_operations:
            self.selected_operations.discard(current_index)
            self.selected_operations.add(new_position)

        # Perform the reorder - NO VALIDATION
        operation = self.workflow.operations.pop(current_index)
        self.workflow.operations.insert(new_position, operation)

        # Mark as unvalidated
        self.workflow_validated = False
        self.workflow_modified = True
        self.validate_execute_btn.config(
            text="Validate",
            bootstyle="warning",
            command=self.callback_validate_workflow
        )

        # Update display
        self.display_workflow_queue()

    def show_unified_mapping_dialog(self, labware_info, missing_ids, present_ids):
        """Show dialog with two sections: missing labware (required) and present labware (optional)"""

        # Create dialog using ScrollableDialog base
        dialog = ScrollableDialog(
            parent=self.get_master_window(),
            title="Remap Labware",
            size="700x600"
        )

        result = {'mapping': {}, 'cancelled': False}
        dropdown_vars = {}

        # Section 1: Missing labware
        if missing_ids:
            ttk.Label(
                dialog.scroll_frame,
                text="⚠️ Missing Labware (Recommended)",
                font=('Arial', 12, 'bold'),
                foreground='orange'
            ).pack(pady=(0, 10), anchor='w')

            for lw_id in sorted(missing_ids):
                lw_type = labware_info[lw_id]
                frame = ttk.Labelframe(dialog.scroll_frame, text=f"{lw_id} ({lw_type})", padding=10)
                frame.pack(fill=tk.X, pady=5)

                compatible = [
                    (lw.labware_id, f"{lw.labware_id} ({lw.__class__.__name__})")
                    for lw in self.dict_top_labware.values()
                    if lw.__class__.__name__ == lw_type and lw.labware_id != lw_id
                ]

                options = ["[Recommended"
                           " - Select labware]"] + [display for _, display in compatible]
                var = tk.StringVar(value=options[0])
                dropdown_vars[lw_id] = (var, dict(compatible), False)

                ttk.Combobox(frame, textvariable=var, values=options, state='readonly', width=50).pack(fill=tk.X)

        # Section 2: Present labware (OPTIONAL)
        if present_ids:
            ttk.Separator(dialog.scroll_frame, orient='horizontal').pack(fill=tk.X, pady=20)
            ttk.Label(
                dialog.scroll_frame,
                text="✓ Current Labware (Optional Remap)",
                font=('Arial', 12, 'bold'),
                foreground='green'
            ).pack(pady=(0, 10), anchor='w')

            for lw_id in sorted(present_ids):
                lw_type = labware_info[lw_id]
                frame = ttk.Labelframe(dialog.scroll_frame, text=f"{lw_id} ({lw_type})", padding=10)
                frame.pack(fill=tk.X, pady=5)

                compatible = [
                    (lw.labware_id, f"{lw.labware_id} ({lw.__class__.__name__})")
                    for lw in self.dict_top_labware.values()
                    if lw.__class__.__name__ == lw_type and lw.labware_id != lw_id
                ]

                options = ["[Keep current]"] + [display for _, display in compatible]
                var = tk.StringVar(value=options[0])
                dropdown_vars[lw_id] = (var, dict(compatible), False)

                ttk.Combobox(frame, textvariable=var, values=options, state='readonly', width=50).pack(fill=tk.X)

        # Button handlers
        def on_apply():
            for lw_id, (var, id_map, required) in dropdown_vars.items():
                selection = var.get()

                if "[" not in selection:
                    for labware_id, display in id_map.items():
                        if display == selection:
                            result['mapping'][lw_id] = labware_id
                            break

            dialog.result = result['mapping']
            dialog.destroy()

        def on_cancel():
            dialog.result = None
            dialog.destroy()

        # Add button bar using helper
        dialog.add_button_bar(
            create_cmd=on_apply,
            create_text="Apply",
            cancel_text="Cancel"
        )

        # Wait for dialog to close
        self.get_master_window().wait_window(dialog)

        return dialog.result

    # ========== STAGING OPERATIONS (DIRECT MODE) ==========
    def stage_operation(self, operation: Operation):
        """Stage an operation for immediate execution"""
        self.staged_operation = operation  # Operation object
        self.staged_operation_validated = False
        self.update_staged_display()

    def update_staged_display(self):
        """Update staging area with operation details"""
        self.staged_op_text.config(state='normal')
        self.staged_op_text.delete(1.0, tk.END)

        if self.staged_operation is None:
            self.staged_op_text.insert(1.0, " ---- \n")
            self.execute_button.config(state='disabled')
            self.clear_button.config(state='disabled')
        else:

            op = self.staged_operation
            header = f"OPERATION: {op.operation_type.value}\n"
            params = "Parameter:\n"
            for key, value in op.parameters.items():
                params += f"  {key}: {value}\n"

            display_text = header  + params
            self.staged_op_text.insert(1.0, display_text)

            if self.staged_operation_validated:
                self.execute_button.config(
                    text="Execute",
                    state='normal',
                    bootstyle="success",
                    command=self.execute_staged_operation
                )
            else:
                self.execute_button.config(
                    text="Validate",
                    state='normal',
                    bootstyle="warning",
                    command=self.validate_staged_operation
                )

            self.clear_button.config(state='normal')
            self.execute_button.focus_set()  # Set focus to execute button
            self.execute_button.bind('<Return>', lambda e: self.execute_button.invoke())

        self.staged_op_text.config(state='disabled')

    def execute_staged_operation(self):
        """Execute the staged operation with modal overlay and threading"""
        if self.staged_operation is None:
            return

        # Require validation first
        if not self.staged_operation_validated:
            messagebox.showwarning(
                "Not Validated",
                "Please validate the operation before executing."
            )
            return

        # Create modal overlay - blocks all gui interaction
        overlay = ExecutionControlOverlay(
            self.get_master_window(),
            self.pipettor
        )

        # Update progress text
        overlay.update_progress(f"Executing: {self.staged_operation.operation_type.value}")

        def run_operation():
            """Runs in background thread"""
            try:
                # Execute operation
                self.staged_operation.execute(self.pipettor, self.deck)

                # Log success
                self.operation_logger.log_success(
                    mode="direct",
                    operation=self.staged_operation
                )

                # Success callback in main thread
                self.container.winfo_toplevel().after(
                    0,
                    lambda: self.on_execution_success(overlay)
                )

            except Exception as e:
                # Error callback in main thread
                error_msg = str(e)
                is_abort = "abort" in error_msg.lower()

                if self.staged_operation is not None:
                    self.operation_logger.log_failure(
                        mode="direct",
                        operation=self.staged_operation,
                        error_message=error_msg
                    )

                self.container.winfo_toplevel().after(
                    0,
                    lambda: self.on_execution_failed(overlay, error_msg, is_abort)
                )

        # Start in background thread
        thread = threading.Thread(target=run_operation, daemon=True)
        thread.start()

    def callback_execute_workflow(self):
        """Execute workflow with modal overlay and threading"""
        if not self.workflow or not self.workflow.operations:
            messagebox.showwarning("Empty Workflow", "Please add operations")
            return

        # Get name
        name = self.entry_name.get().strip()
        if not name:
            name = f"Workflow_{uuid.uuid4().hex[:8]}"

        self.workflow.name = name
        self.pipettor.set_simulation_mode(False)

        # Add to parent's memory
        if hasattr(self, 'parent_function_window') and self.parent_function_window:
            self.parent_function_window.workflows_in_memory[name] = self.workflow
            self.parent_function_window.refresh_workflows_list()

        # Exit simulation mode and restore pipettor
        self.pipettor.pop_state(self._state_snapshot)

        # Close builder window
        self.window_build_func.destroy()

        # Execute workflow on parent's pipettor
        if not hasattr(self, 'parent_function_window') or not self.parent_function_window:
            return

        parent = self.parent_function_window

        # Create modal overlay on PARENT window
        overlay = ExecutionControlOverlay(
            parent.get_master_window(),
            parent.pipettor
        )

        def run_workflow():
            """Runs in background thread"""
            # Log workflow start
            parent.operation_logger.log_workflow_start(
                workflow_name=name,
                num_operations=len(self.workflow.operations)
            )

            try:
                for i, operation in enumerate(self.workflow.operations):
                    # Update progress in main thread
                    progress_msg = f"Operation {i + 1}/{len(self.workflow.operations)}: {operation.operation_type.value}"
                    parent.container.winfo_toplevel().after(
                        0,
                        lambda msg=progress_msg: overlay.update_progress(msg)
                    )

                    try:
                        operation.execute(parent.pipettor, parent.deck)

                        # Log each successful operation
                        parent.operation_logger.log_success(
                            mode="builder",
                            operation=operation,
                            workflow_name=name
                        )

                    except Exception as op_error:
                        # Log the failed operation
                        parent.operation_logger.log_failure(
                            mode="builder",
                            operation=operation,
                            error_message=str(op_error),
                            workflow_name=name
                        )

                        # Log workflow failure
                        parent.operation_logger.log_workflow_failed(
                            workflow_name=name,
                            failed_at=i,
                            total_operations=len(self.workflow.operations),
                            error_message=str(op_error)
                        )

                        # Show error in main thread
                        error_msg = str(op_error)
                        is_abort = "abort" in error_msg.lower()

                        parent.container.winfo_toplevel().after(
                            0,
                            lambda: self.on_workflow_failed(overlay, i, error_msg, is_abort, name)
                        )
                        return

                # All operations succeeded
                parent.operation_logger.log_workflow_complete(
                    workflow_name=name,
                    num_completed=len(self.workflow.operations),
                    total_operations=len(self.workflow.operations)
                )

                # Success callback in main thread
                parent.container.winfo_toplevel().after(
                    0,
                    lambda: self.on_workflow_success(overlay, name, len(self.workflow.operations), parent)
                )

            except Exception as e:
                # Unexpected error
                parent.container.winfo_toplevel().after(
                    0,
                    lambda: self.on_workflow_error(overlay, str(e))
                )

        # Start in background thread
        import threading
        thread = threading.Thread(target=run_workflow, daemon=True)
        thread.start()

    def on_execution_success(self, overlay):
        """Called in main thread when operation succeeds"""
        overlay.close()

        if self.on_operation_complete:
            self.on_operation_complete()

        self.clear_staged_operation()
        self.container.winfo_toplevel().focus_force()

    def on_execution_failed(self, overlay, error_msg, is_abort):
        """Called in main thread when operation fails"""
        overlay.close()

        if is_abort:
            messagebox.showwarning("Aborted", f"Operation aborted:\n\n{error_msg}")
        else:
            messagebox.showerror("Error", f"Operation failed:\n\n{error_msg}")

    def clear_staged_operation(self):
        """Clear the staging area"""
        self.staged_operation = None
        self.staged_operation_name = None
        self.staged_operation_details = None
        self.staged_operation_validated = False
        if hasattr(self, 'execute_button'):
            self.execute_button.unbind('<Return>')
        self.update_staged_display()

    def callback_close_builder(self):
        """Close builder with confirmation if operations exist"""
        if self.workflow_modified:
            msg = f"You have unsaved changes to '{self.workflow.name}'.\n"
            msg += "Close anyway?"

            if not messagebox.askyesno("Unsaved Changes", msg, default="no"):
                return

        if self.mode == "builder":
            self.pipettor.pop_state(self._state_snapshot)
        self.window_build_func.destroy()

    def on_workflow_success(self, overlay, name, num_ops, parent):
        """Called in main thread when workflow succeeds"""
        overlay.close()

        messagebox.showinfo(
            "Success",
            f"Workflow '{name}' completed!\n{num_ops} operations executed."
        )

        if parent.on_operation_complete:
            parent.on_operation_complete()

    def on_workflow_failed(self, overlay, failed_index, error_msg, is_abort, name):
        """Called in main thread when workflow fails"""
        overlay.close()

        if is_abort:
            messagebox.showwarning(
                "Workflow Aborted",
                f"Workflow '{name}' aborted at operation {failed_index + 1}:\n\n{error_msg}"
            )
        else:
            messagebox.showerror(
                "Workflow Failed",
                f"Workflow '{name}' failed at operation {failed_index + 1}:\n\n{error_msg}"
            )

    def on_workflow_error(self, overlay, error_msg):
        """Called in main thread on unexpected error"""
        overlay.close()
        messagebox.showerror("Execution Error", f"Failed to execute workflow:\n\n{error_msg}")

    # ========== WORKFLOW QUEUE (BUILDER MODE) ==========

    def open_workflow_builder(self):
        """Open workflow builder window from direct mode"""
        builder = FunctionWindow(
            deck=self.deck,
            pipettor=self.pipettor,
            mode="builder",
            master=self.container.winfo_toplevel()
        )

        # Give builder a reference to this direct mode window
        builder.parent_function_window = self

        if hasattr(builder, 'window_build_func'):
            builder.window_build_func.protocol("WM_DELETE_WINDOW", builder.callback_close_builder)

    def display_workflow_queue(self):
        """Display the current workflow queue"""
        if self.mode != "builder":
            return

        # Clear existing
        for widget in self.third_column_frame.winfo_children():
            widget.destroy()

        if not self.workflow or not self.workflow.operations:
            ttk.Label(
                self.third_column_frame,
                text="No operations in queue\nClick operation buttons to add",
                font=("Helvetica", 12),
                foreground="gray"
            ).pack(pady=20)
            return

        # Display each operation
        for idx, operation in enumerate(self.workflow.operations):
            frame = ttk.Frame(self.third_column_frame, relief=tk.RAISED, borderwidth=1)
            frame.grid(row=idx, column=0, sticky="ew", pady=2, padx=5)
            frame.columnconfigure(1, weight=1)  # Label column expands

            # Checkbox
            var = tk.BooleanVar(value=(idx in self.selected_operations))
            checkbox = ttk.Checkbutton(
                frame,
                variable=var,
                command=lambda i=idx, v=var: self.toggle_operation_selection(i, v),
                bootstyle="round-toggle"
            )
            checkbox.grid(row=0, column=0, sticky="w", padx=(5, 2))

            # Operation label
            op_text = f"{idx + 1}. {operation.operation_type.value}"
            if 'labware_id' in operation.parameters:
                op_text += f": {operation.parameters['labware_id']}"

            label = ttk.Label(frame, text=op_text, font=("Helvetica", 11))
            label.grid(row=0, column=1, sticky="w", padx=5)

            # Action buttons using create_button_bar
            button_configs = [
                {"text": "↕", "command": lambda i=idx: self.reorder_operation(i), "style": "info-outline"},
                {"text": "✏", "command": lambda i=idx: self.launch_edit_callback(i), "style": "warning-outline"},
                {"text": "🗑", "command": lambda i=idx: self.remove_operation_from_workflow(i),
                 "style": "danger-outline"}
            ]

            # Create button container in frame
            btn_container = ttk.Frame(frame)
            btn_container.grid(row=0, column=2, sticky="e", padx=2)

            # Create buttons with fixed width
            for col, config in enumerate(button_configs):
                btn = ttk.Button(
                    btn_container,
                    text=config["text"],
                    command=config["command"],
                    bootstyle=config["style"],
                    width=3
                )
                btn.grid(row=0, column=col, padx=1)

        self.update_copy_paste_buttons()

    # --- Helper Methods ---
    def launch_edit_callback(self, index: int):
        """Launch the appropriate callback for editing this operation"""

        if index >= len(self.workflow.operations):
            return

        operation = self.workflow.operations[index]

        # Store edit context
        self.edit_mode = True
        self.edit_index = index

        # Clear middle column
        self.clear_grid(self.second_column_frame)

        # Show current parameters
        info_lines = [f"Description: {operation.description}"]
        info_lines.extend([f"{key}: {value}" for key, value in operation.parameters.items()])
        formatted_text = "\n".join(info_lines)
        self.edit_info_label.config(text=formatted_text)

        operation_key = operation.operation_type.value

        # Launch wizard for this operation type
        self._start_operation(operation_key, edit_mode=True)

    def clear_edit_mode(self):
        """Clear edit mode when starting a fresh operation"""
        if hasattr(self, 'edit_mode'):
            self.edit_mode = False
        if hasattr(self, 'edit_index'):
            self.edit_index = None
        # Clear edit info label
        if hasattr(self, 'edit_info_label'):
            self.edit_info_label.config(text="")

    def toggle_operation_selection(self, index: int, var: tk.BooleanVar):
        """Toggle selection state of an operation"""
        if var.get():
            self.selected_operations.add(index)
        else:
            self.selected_operations.discard(index)

        self.update_copy_paste_buttons()

    def update_copy_paste_buttons(self):
        """Update copy/paste button and combobox states"""
        # Enable copy button if selections exist
        if self.selected_operations:
            self.copy_btn.config(state='normal')
        else:
            self.copy_btn.config(state='disabled')

        # Enable paste button and combobox if clipboard has operations
        if self.clipboard_operations:
            self.paste_btn.config(state='normal')
            self.paste_position_menu.config(state='normal')
        else:
            self.paste_btn.config(state='disabled')
            self.paste_position_menu.config(state='disabled')

    def update_foc_section(self):
        if not hasattr(self, 'foc_frame'):
            return

        # Clear fraame
        for w in self.foc_frame.winfo_children():
            w.destroy()

        # Check config
        foc_configured = (
                hasattr(self.pipettor, 'foc_bat_script_path')
                and self.pipettor.foc_bat_script_path
                and os.path.exists(self.pipettor.foc_bat_script_path)
                and hasattr(self.pipettor, 'foc_plate_name')
                and self.pipettor.foc_plate_name
        )

        if foc_configured:
            # Show configured status
            ttk.Label(
                self.foc_frame,
                text=f"✓ Plate: {self.pipettor.foc_plate_name}",
                foreground='green',
                font=('Arial', 9, 'bold')
            ).pack(anchor='w', pady=(0, 5))

            # Run button - opens dialog when clicked
            ttk.Button(
                self.foc_frame,
                text="▶ Run FOC Measurement",
                command=self.callback_measure_foc,
                bootstyle="success"
            ).pack(fill=tk.X, pady=5)
        else:
            # Not configured
            ttk.Button(
                self.foc_frame,
                text="Measure FOC",
                command=None,
                state="disabled"
            ).pack(fill="x", pady=(0, 5))

            ttk.Label(
                self.foc_frame,
                text="Configure FOC script and plate name\nin 'Low level parameters' tab.",
                foreground="gray",
                font=('Arial', 9, 'italic'),
                justify=tk.LEFT
            ).pack(anchor="w")

    def copy_selected_operations(self):
        """Copy selected operations to clipboard"""
        if not self.selected_operations:
            return

        # Sort indices to maintain order
        sorted_indices = sorted(self.selected_operations)

        # Deep copy the selected operations
        self.clipboard_operations = [
            copy.deepcopy(self.workflow.operations[i])
            for i in sorted_indices
        ]

        # Clear selection
        self.selected_operations.clear()

        # Update display
        self.display_workflow_queue()

    def paste_operations(self):
        """Paste operations from clipboard at specified position"""
        if not self.clipboard_operations:
            return

        # Get paste position value
        position_str = self.paste_position_var.get().strip()

        # Determine insert position
        if position_str.lower() == "end":
            insert_pos = len(self.workflow.operations)

        elif position_str.lower() == "top":
            insert_pos = 0

        elif position_str.lower() == "or enter index...":
            # User didn't change from hint - default to end
            insert_pos = len(self.workflow.operations)

        else:
            # Try to parse as integer index
            try:
                # Convert to 0-based index (user enters 1-based)
                insert_pos = int(position_str) - 1

                # Clamp to valid range
                insert_pos = max(0, min(insert_pos, len(self.workflow.operations)))

            except ValueError:
                # Invalid input - default to end silently
                insert_pos = len(self.workflow.operations)

        # Deep copy from clipboard and insert at position
        num_pasted = len(self.clipboard_operations)

        for i, op in enumerate(self.clipboard_operations):
            new_op = copy.deepcopy(op)
            self.workflow.operations.insert(insert_pos + i, new_op)

        # Update selection indices (shift operations after insert point)
        new_selection = set()
        for idx in self.selected_operations:
            if idx >= insert_pos:
                new_selection.add(idx + num_pasted)
            else:
                new_selection.add(idx)
        self.selected_operations = new_selection

        # Mark as unvalidated
        self.workflow_validated = False
        self.workflow_modified = True
        self.validate_execute_btn.config(
            text="Validate",
            bootstyle="warning",
            command=self.callback_validate_workflow
        )

        # Update display
        self.display_workflow_queue()

        # Reset to "End" for next paste
        self.paste_position_var.set("End")

    def remove_operation_from_workflow(self, index: int):
        """Remove operation - NO VALIDATION"""
        self.clear_edit_mode()
        if 0 <= index < len(self.workflow.operations):
            self.workflow.remove_operation(index)

            #update selection indices
            new_selection = set()
            for i in self.selected_operations:
                if i < index:
                    new_selection.add(i)
                elif i > index:
                    new_selection.add(i - 1)
            self.selected_operations = new_selection

            # Mark as unvalidated
            self.workflow_validated = False
            self.workflow_modified = True
            self.validate_execute_btn.config(text="Validate", bootstyle="warning",
                                             command=self.callback_validate_workflow)

            self.display_workflow_queue()

    def clear_workflow_queue(self):
        """Clear all operations from queue"""
        if not self.workflow or not self.workflow.operations:
            return

        if messagebox.askyesno("Confirm", "Clear all operations from queue?", default="yes"):
            # Clear workflow operations
            self.workflow.operations.clear()
            self.workflow_modified = True

            # Reset pipettor to clean state
            self.pipettor.pop_state(self._state_snapshot)
            self._state_snapshot = self.pipettor.push_state()
            self.pipettor.set_simulation_mode(True)

            # Refresh display
            self.display_workflow_queue()

    def callback_create_button(self):
        """Create workflow and add to memory (like adding labware to deck)"""
        if not self.workflow or not self.workflow.operations:
            messagebox.showwarning("Empty Workflow", "Please add operations")
            return

        # Get name from entry
        name = self.entry_name.get().strip()
        if not name:
            name = f"Workflow_{uuid.uuid4().hex[:8]}"

        # Update workflow name
        self.workflow.name = name

        # Store workflow in memory (like labware is added to deck)
        created_workflow = self.workflow

        # Add to parent's workflows_in_memory dict (if opened from direct mode)
        if hasattr(self, 'parent_function_window') and self.parent_function_window:
            self.parent_function_window.workflows_in_memory[name] = created_workflow
            self.parent_function_window.refresh_workflows_list()

        messagebox.showinfo(
            "Workflow  Created",
            f"Workflow '{name}' created with {len(created_workflow.operations)} operations!\n\n"
        )

        # Clear the builder for next workflow
        self.workflow = Workflow(name="New Workflow")

        # Reset pipettor to clean state
        self.pipettor.pop_state(self._state_snapshot)
        self._state_snapshot = self.pipettor.push_state()
        self.pipettor.set_simulation_mode(True)


        self.entry_name.delete(0, tk.END)
        self.display_workflow_queue()

        # Close builder window
        if self.is_toplevel and hasattr(self, 'window_build_func'):
            self.window_build_func.destroy()

    def refresh_workflows_list(self):
        """Update listbox with workflows in memory"""
        if self.mode != "direct":
            return

        # Clear listbox
        self.workflows_listbox.delete(0, tk.END)

        if self.workflows_in_memory:
            for workflow_name, workflow in sorted(self.workflows_in_memory.items()):
                display_text = f"{workflow_name} ({len(workflow.operations)} ops)"
                self.workflows_listbox.insert(tk.END, display_text)

    def load_workflow_from_file(self):
        """Load a workflow from JSON file into memory"""
        filepath = filedialog.askopenfilename(
            title="Load Workflow",
            initialdir=self.workflows_dir,
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if not filepath:
            return

        try:
            workflow = Workflow.load_from_file(filepath)

            # Check if already in memory
            if workflow.name in self.workflows_in_memory:
                if not messagebox.askyesno(
                        "Workflow Exists",
                        f"Workflow '{workflow.name}' is already loaded.\n\nReplace it?"
                ):
                    return

            # Add to memory
            self.workflows_in_memory[workflow.name] = workflow
            self.refresh_workflows_list()

            messagebox.showinfo(
                "Loaded",
                f"Workflow '{workflow.name}' loaded successfully!\n"
                f"{len(workflow.operations)} operations"
            )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load workflow:\n\n{str(e)}")

    def open_selected_workflow(self):
        """Open the selected workflow in builder mode for editing/validation/execution"""
        selection = self.workflows_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a workflow to open")
            return

        # Get workflow name
        selected_text = self.workflows_listbox.get(selection[0])
        if selected_text == "(No workflows loaded)":
            return

        workflow_name = selected_text.split(" (")[0]
        workflow = self.workflows_in_memory.get(workflow_name)

        if not workflow:
            messagebox.showerror("Error", f"Workflow '{workflow_name}' not found in memory")
            return

        # Extract labware info from workflow

        labware_info = {}
        for op in workflow.operations:
            for param_value in op.parameters.values():
                if isinstance(param_value, dict) and 'id' in param_value and 'type' in param_value:
                    labware_info[param_value['id']] = param_value['type']

        current_ids = {lw.labware_id for lw in self.dict_top_labware.values()}
        missing_ids = set(labware_info.keys()) - current_ids
        present_ids = set(labware_info.keys()) & current_ids

        if missing_ids:
            mapping = self.show_unified_mapping_dialog(labware_info, missing_ids, present_ids)
            if mapping is None:
                return  # User cancelled

            mapped_workflow = copy.deepcopy(workflow)
            for op in mapped_workflow.operations:
                for param_value in op.parameters.values():
                    if isinstance(param_value, dict) and 'id' in param_value:
                        if param_value['id'] in mapping:
                            param_value['id'] = mapping[param_value['id']]
        else:
            mapped_workflow = copy.deepcopy(workflow)

        # Open workflow builder with this workflow loaded
        builder = FunctionWindow(
            deck=self.deck,
            pipettor=self.pipettor,
            mode="builder",
            master=self.container.winfo_toplevel()
        )

        # Give builder a reference to this direct mode window
        builder.parent_function_window = self

        # Load the mapped_workflow into the builder without executing operations
        builder.workflow = mapped_workflow
        builder.entry_name.delete(0, tk.END)
        builder.entry_name.insert(0, workflow.name)

        # Just display the operations - don't replay them
        builder.workflow_modified = False
        builder.display_workflow_queue()

        # Mark as unvalidated since it needs fresh validation
        builder.workflow_validated = False
        builder.validate_execute_btn.config(
            text="Validate",
            bootstyle="warning",
            command=builder.callback_validate_workflow
        )

        # Set up close handler
        if hasattr(builder, 'window_build_func'):
            builder.window_build_func.protocol("WM_DELETE_WINDOW", builder.callback_close_builder)

    def save_selected_workflow_to_file(self):
        """Save the selected workflow to a JSON file (with file dialog)"""
        selection = self.workflows_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a workflow to save")
            return

        selected_text = self.workflows_listbox.get(selection[0])
        if selected_text == "(No workflows loaded)":
            return

        workflow_name = selected_text.split(" (")[0]
        workflow = self.workflows_in_memory.get(workflow_name)

        if not workflow:
            messagebox.showerror("Error", f"Workflow '{workflow_name}' not found")
            return

        # Ask user where to save with file dialog
        default_filename = f"{workflow.name.replace(' ', '_')}_{workflow.workflow_id[:8]}.json"

        filepath = filedialog.asksaveasfilename(
            title="Save Workflow",
            initialdir=self.workflows_dir,
            initialfile=default_filename,
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if not filepath:
            return  # User cancelled

        try:
            workflow.save_to_file(filepath)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save workflow:\n\n{str(e)}")

    def delete_selected_workflow(self):
        """Delete the selected workflow from memory"""
        selection = self.workflows_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a workflow to delete")
            return

        selected_text = self.workflows_listbox.get(selection[0])
        if selected_text == "(No workflows loaded)":
            return

        workflow_name = selected_text.split(" (")[0]

        if workflow_name not in self.workflows_in_memory:
            messagebox.showerror("Error", f"Workflow '{workflow_name}' not found")
            return

        # Confirm deletion
        if not messagebox.askyesno(
                "Confirm Delete",
                f"Delete workflow '{workflow_name}' from memory?\n\n"
                f"Note: This does not delete saved files."
        ):
            return

        # Remove from memory
        del self.workflows_in_memory[workflow_name]
        self.refresh_workflows_list()

        messagebox.showinfo("Deleted", f"Workflow '{workflow_name}' removed from memory.")

    # ========== HELPER METHODS ==========
    def callback_remap_labware(self):
        """Manual remap button - remap all labware in current workflow"""
        if not self.workflow or not self.workflow.operations:
            messagebox.showwarning("Empty Workflow", "No operations to remap")
            return

        # Get all labware IDs used in workflow
        labware_info = {}  # {labware_id: labware_type}
        for op in self.workflow.operations:
            for param_value in op.parameters.values():
                if isinstance(param_value, dict) and 'id' in param_value and 'type' in param_value:
                    labware_info[param_value['id']] = param_value['type']

        if not labware_info:
            messagebox.showinfo("No Labware", "No labware found in workflow")
            return

        # Split into missing and present
        current_ids = {lw.labware_id for lw in self.dict_top_labware.values()}
        missing_ids = set(labware_info.keys()) - current_ids
        present_ids = set(labware_info.keys()) & current_ids

        # Show unified mapping dialog
        mapping = self.show_unified_mapping_dialog(labware_info, missing_ids, present_ids)
        if not mapping:
            return

        # Apply mapping
        for op in self.workflow.operations:
            for param_value in op.parameters.values():
                if isinstance(param_value, dict) and 'id' in param_value:
                    if param_value['id'] in mapping:
                        param_value['id'] = mapping[param_value['id']]

        self.workflow_modified = True
        self.workflow_validated = False
        self.validate_execute_btn.config(text="Validate", bootstyle="warning", command=self.callback_validate_workflow)
        self.display_workflow_queue()

        messagebox.showinfo("Remapped", f"Applied {len(mapping)} remapping(s)")

    def get_top_labwares(self) -> dict[str, Labware]:
        """Get the topmost labware from each slot"""
        top_labwares = {}
        for slot_id, slot in self.deck.slots.items():
            if not slot.labware_stack:
                continue
            top_lw_id, (top_lw, (min_z, max_z)) = max(
                slot.labware_stack.items(),
                key=lambda item: item[1][1][1]
            )
            top_labwares[slot_id] = top_lw
        return top_labwares

    def refresh_labware_lists(self):
        """Update labware lists from current deck state"""
        self.dict_top_labware = self.get_top_labwares()

    def get_master_window(self):
        """Get the master window for dialogs"""
        if self.is_toplevel:
            return self.window_build_func
        else:
            return self.container.winfo_toplevel()

    def clear_grid(self, frame: ttk.Frame):
        """Clear all widgets from a frame"""
        for widget in frame.grid_slaves():
            widget.destroy()

    def display_possible_labware(self, labware_type, next_callback, start_row=0, auto_select_single=True):
        """Display selectable labware buttons - optionally auto-select if only one"""

        # Get matching labware
        matching_labware = [
            (slot_id, labware) for slot_id, labware in self.dict_top_labware.items()
            if isinstance(labware, labware_type)
        ]

        # BUILDER MODE - show in second column frame
        if self.mode == "builder":
            target_frame = self.second_column_frame

            if hasattr(self, 'edit_mode') and self.edit_mode:
                start_row = 1

            for slot_id, labware in matching_labware:
                label = ttk.Label(target_frame, text=f"Slot: {slot_id}")
                label.grid(column=0, row=start_row, sticky="nsew", pady=5, padx=5)
                start_row += 1

                button = ttk.Button(
                    target_frame,
                    text=labware.labware_id,
                    bootstyle="warning",
                    command=lambda lw=labware: next_callback(lw)
                )
                button.grid(column=0, row=start_row, sticky="nsew", pady=5, padx=5)
                start_row += 1

            # Auto-select if only one option and auto_select enabled
            if len(matching_labware) == 1 and auto_select_single:
                self.get_master_window().after(100, lambda: next_callback(matching_labware[0][1]))

        # DIRECT MODE - show dialog with ScrollableDialog
        else:
            dialog = ScrollableDialog(
                parent=self.get_master_window(),
                title="Select Labware",
                size="400x500"
            )

            if not matching_labware:
                # No labware found
                ttk.Label(
                    dialog.scroll_frame,
                    text=f"No {labware_type.__name__} found on deck",
                    font=('Arial', 12),
                    foreground='red'
                ).pack(pady=20, padx=20)

                button_configs = [{"text": "Close", "command": dialog.destroy}]
                create_button_bar(dialog.scroll_frame, button_configs, fill=True)
            else:
                # Add slot labels and build button configs
                button_configs = []

                for slot_id, labware in matching_labware:
                    # Create a frame for this labware item
                    item_frame = ttk.Frame(dialog.scroll_frame)
                    item_frame.pack(fill=tk.X, pady=5, padx=10)

                    # Slot label
                    ttk.Label(
                        item_frame,
                        text=f"Slot: {slot_id}",
                        font=('Arial', 11, 'bold')
                    ).pack(anchor="w", pady=(0, 2))

                    # Create callback
                    def make_callback(lw=labware):
                        def callback():
                            dialog.destroy()
                            next_callback(lw)

                        return callback

                    # Button
                    ttk.Button(
                        item_frame,
                        text=f"{labware.labware_id} ({labware.__class__.__name__})",
                        command=make_callback(labware),
                        bootstyle="primary"
                    ).pack(fill=tk.X)

                # Add cancel button at bottom
                ttk.Button(
                    dialog.scroll_frame,
                    text="Cancel",
                    command=dialog.destroy,
                    bootstyle="secondary"
                ).pack(fill=tk.X, pady=10, padx=10)

                # Auto-click if only one option and auto_select enabled
                if len(matching_labware) == 1 and auto_select_single:
                    # Find the first primary button (it's in item_frame)
                    for widget in dialog.scroll_frame.winfo_children():
                        if isinstance(widget, ttk.Frame):
                            for btn in widget.winfo_children():
                                if isinstance(btn, ttk.Button):
                                    dialog.after(100, lambda b=btn: b.invoke())
                                    break
                            break

    def get_wells_list_from_labware(
            self,
            labware_obj: Labware,
            source: bool = False,
    ) -> list[tuple[int, int]]:
        """
        Get available wells from labware based on type and context.

        Parameters
        ----------
        labware_obj : Labware
            The labware to get wells from
        source : bool
            True if selecting source positions (occupied/filled)
            False if selecting destination positions (empty/available)

        Returns
        -------
        list[tuple[int, int]]
            List of (row, col) positions that are available for selection
        """
        if isinstance(labware_obj, Plate):
            rows, columns = labware_obj._rows, labware_obj._columns
            wells_list = []

            for r in range(rows):
                for c in range(columns):
                    if source:
                        # Source: check if well has content
                        well = labware_obj.get_well_at(c, r)
                        if well and well.get_total_volume() > 0:
                            wells_list.append((r, c))
                    else:
                        # Destination: all wells available
                        wells_list.append((r, c))

        elif isinstance(labware_obj, ReservoirHolder):
            # Show all reservoirs
            wells_list = []
            for res in labware_obj.get_reservoirs():
                if res is not None:
                    wells_list.append((res.row, res.column))

        elif isinstance(labware_obj, PipetteHolder):
            if source:
                # Source: get occupied holders (tips present)
                wells_list = [
                    (holder.row, holder.column)
                    for holder in labware_obj.get_occupied_holders()
                ]
            else:
                # Destination: get available holders (no tips)
                wells_list = [
                    (holder.row, holder.column)
                    for holder in labware_obj.get_available_holders()
                ]
        else:
            raise TypeError(f"Unsupported labware type: {type(labware_obj)}")

        return wells_list

    def builder_config(self, operation: Operation) -> None:
        """Add or replace operation in workflow - NO VALIDATION"""

        if hasattr(self, 'edit_mode') and self.edit_mode:
            # Replace operation
            self.workflow.operations[self.edit_index] = operation
            self.edit_mode = False
            self.edit_index = None

            if hasattr(self, 'edit_info_label'):
                self.edit_info_label.config(text="")

        else:
            # NORMAL MODE
            new_position = len(self.workflow.operations)

            if new_position is None:
                self.clear_grid(self.second_column_frame)
                return

            # Insert at position - NO VALIDATION
            self.workflow.operations.insert(new_position, operation)

        # Mark as unvalidated
        self.workflow_validated = False
        self.workflow_modified = True
        self.validate_execute_btn.config(text="Validate", bootstyle="warning", command=self.callback_validate_workflow)

        # Refresh display
        self.display_workflow_queue()
        self.clear_grid(self.second_column_frame)
        self.stage_label.config(text="Select an operation to continue")

    def callback_validate_workflow(self):
        """Validate the current workflow by simulating execution"""
        if not self.workflow or not self.workflow.operations:
            messagebox.showwarning("Empty Workflow", "Please add operations first")
            return

        # Reset pipettor to clean state
        self.pipettor.pop_state(self._state_snapshot)
        self._state_snapshot = self.pipettor.push_state()
        self.pipettor.set_simulation_mode(True)

        try:
            # Try to execute all operations
            for i, op in enumerate(self.workflow.operations):
                try:
                    op.execute(self.pipettor, self.deck)
                except Exception as e:
                    # Validation failed at operation i
                    messagebox.showerror(
                        "Validation Failed",
                        f"❌ Operation #{i + 1} is invalid:\n\n"
                        f"Type: {op.operation_type.value}\n"
                        f"Error: {str(e)}\n\n"
                        f"Please fix this operation or remove it."
                    )

                    # Reset to clean state
                    self.pipettor.pop_state(self._state_snapshot)
                    self._state_snapshot = self.pipettor.push_state()
                    self.pipettor.set_simulation_mode(True)

                    self.workflow_validated = False
                    self.validate_execute_btn.config(text="Validate", bootstyle="warning")
                    return



            self.workflow_validated = True
            self.validate_execute_btn.config(text="Execute", bootstyle="primary",
                                             command=self.callback_execute_workflow)
        except Exception as e:
            messagebox.showerror("Validation Error", f"Unexpected error:\n\n{str(e)}")
            self.workflow_validated = False
            self.validate_execute_btn.config(text="Validate", bootstyle="warning")

    def ask_position_in_second_frame(self, total_ops: int, default_position: int, operation_name: str) -> int:
        """
        Display position selector in second frame.

        Returns
        -------
        int
            0-based position, or None if cancelled
        """
        self.clear_grid(self.second_column_frame)

        result = {'position': None, 'done': False}

        # Title
        ttk.Label(
            self.second_column_frame,
            text=f"Position for: {operation_name}",
            font=('Arial', 12, 'bold')
        ).grid(row=0, column=0, pady=10, padx=10, sticky='w')

        # Instructions
        ttk.Label(
            self.second_column_frame,
            text="Select where to insert this operation:",
            font=('Arial', 10)
        ).grid(row=1, column=0, pady=5, padx=10, sticky='w')

        # Position frame
        pos_frame = ttk.Frame(self.second_column_frame)
        pos_frame.grid(row=2, column=0, pady=10, padx=10, sticky='ew')

        ttk.Label(
            pos_frame,
            text="Position:",
            font=('Arial', 11)
        ).pack(side=tk.LEFT, padx=(0, 10))

        # Spinbox
        position_var = tk.IntVar(value=default_position + 1)  # 1-based for display
        spinbox = ttk.Spinbox(
            pos_frame,
            from_=1,
            to=total_ops + 1,
            textvariable=position_var,
            width=8,
            font=('Arial', 12)
        )
        spinbox.pack(side=tk.LEFT, padx=5)

        # Buttons
        button_frame = ttk.Frame(self.second_column_frame)
        button_frame.grid(row=4, column=0, pady=20, padx=10, sticky='ew')
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)

        # Create a BooleanVar to wait on
        wait_var = tk.BooleanVar(value=False)

        def on_confirm():
            result['position'] = position_var.get() - 1  # Convert to 0-based
            result['done'] = True
            wait_var.set(True)  # Trigger the wait to end

        def on_cancel():
            result['position'] = None
            result['done'] = True
            wait_var.set(True)  # Trigger the wait to end

        btn_config =[{'text': 'confirm', 'command': on_confirm},
                     {'text': 'cancel', 'command': on_cancel},]
        create_button_bar(button_frame,btn_config, btns_per_row=2)


        # Focus and select
        spinbox.focus()
        spinbox.selection_range(0, tk.END)

        # Bind Enter key
        spinbox.bind('<Return>', lambda e: on_confirm())

        # Wait for user decision using wait_variable on the BooleanVar
        self.get_master_window().wait_variable(wait_var)

        return result['position']

    def ask_position_dialog(self, axes_config: list[tuple[str, float, float, float]]):
        """
        Open a dialog to request position input for one or multiple axes.

        Parameters
        ----------
        axes_config : list[tuple]
            A list of configuration tuples.
            Format: [(Name, Min, Max, Initial), ...]
            Example: [('X', 0, 200, 10.0), ('Y', 0, 200, 25.0)]

        Returns
        -------
        float | tuple[float] | None
            Returns a single float if 1 axis was requested.
            Returns a tuple of floats if >1 axis was requested.
            Returns None if cancelled.
        """
        # --- 1. Window Setup ---
        dialog = tk.Toplevel(self.get_master_window())
        dialog.withdraw()  # Hide initially to calculate size invisible

        # Dynamic Title
        names = [cfg[0] for cfg in axes_config]
        if len(names) == 1:
            dialog.title(f"Move {names[0]}")
        else:
            dialog.title(f"Move {' & '.join(names)}")

        dialog.resizable(False, False)
        dialog.transient(self.get_master_window())
        dialog.grab_set()

        # --- 2. Build UI ---
        main_frame = ttk.Frame(dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        input_data = []  # Stores (var, min, max, name, entry_widget) for validation

        for i, (name, min_v, max_v, init_v) in enumerate(axes_config):
            # Container for this axis row
            row = ttk.Frame(main_frame)
            row.pack(fill=tk.X, pady=(0, 15))

            # Header: Name + Range Note
            header = ttk.Frame(row)
            header.pack(fill=tk.X, pady=(0, 5))

            ttk.Label(
                header,
                text=f"Current: {init_v:.1f} mm",
                font=('Arial', 9, 'italic'),
                foreground='blue'
            ).pack(side=tk.LEFT, padx=(10, 0))

            range_txt = f"({min_v} - {max_v} mm)"
            if name == 'Z': range_txt += " (0=Home)"

            ttk.Label(
                header,
                text=range_txt,
                font=('Arial', 9),
                foreground='gray'
            ).pack(side=tk.RIGHT)

            # Entry
            var = tk.StringVar(value=str(init_v))
            entry = ttk.Entry(row, textvariable=var, font=('Arial', 12), justify='center')
            entry.pack(fill=tk.X)

            # Store metadata for the OK logic
            input_data.append({
                'name': name,
                'var': var,
                'min': min_v,
                'max': max_v,
                'entry': entry
            })

            # Focus first input automatically
            if i == 0:
                entry.focus()
                entry.select_range(0, tk.END)

        # --- 3. Logic ---
        final_values = []  # Container to capture result

        def on_ok(_=None):
            temp_results = []
            try:
                for item in input_data:
                    val = float(item['var'].get())

                    # Range Validation
                    if not (item['min'] <= val <= item['max']):
                        messagebox.showerror(
                            "Invalid Input",
                            f"{item['name']} must be in deck range",
                            parent=dialog
                        )
                        item['entry'].focus()
                        item['entry'].select_range(0, tk.END)
                        return

                    temp_results.append(val)

                # If loop finishes without return, all data is valid
                final_values.extend(temp_results)
                dialog.destroy()

            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter valid numeric values", parent=dialog)

        def on_cancel(_=None):
            dialog.destroy()

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(5, 0))
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)

        ttk.Button(btn_frame, text="OK", command=on_ok, bootstyle="success").grid(row=0, column=0, sticky='ew',
                                                                                  padx=(0, 5))
        ttk.Button(btn_frame, text="Cancel", command=on_cancel, bootstyle="secondary").grid(row=0, column=1,
                                                                                            sticky='ew', padx=(5, 0))

        dialog.bind('<Return>', on_ok)
        dialog.bind('<Escape>', on_cancel)

        # --- 4. Auto-Center and Show ---
        dialog.update_idletasks()  # Draw widgets virtually to measure size

        width = 380
        height = dialog.winfo_reqheight()

        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)

        dialog.geometry(f"{width}x{height}+{x}+{y}")
        dialog.deiconify()  # Show window now that it's ready

        dialog.wait_window()

        # --- 5. Return Results ---
        if not final_values:
            return None

        # If single axis, return float. If multiple, return tuple.
        return final_values[0] if len(final_values) == 1 else tuple(final_values)

    def ask_volume_dialog(self, title="Enter Volume", initial_value=0, label_text="Volume per well (ul):")-> Optional[float]:


        """
        Create a simple, focused dialog for numeric input.

        Returns
        -------
            Value entered by user(float), or None if cancelled
        """
        dialog = tk.Toplevel(self.get_master_window())
        dialog.title(title)
        dialog.geometry("300x150")
        dialog.resizable(False, False)
        dialog.transient(self.get_master_window())
        dialog.grab_set()

        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (300 // 2)
        y = (dialog.winfo_screenheight() // 2) - (150 // 2)
        dialog.geometry(f"300x150+{x}+{y}")

        result = {'value': None}

        # Main frame with padding
        main_frame = ttk.Frame(dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Label
        ttk.Label(
            main_frame,
            text=label_text,
            font=('Arial', 11)
        ).pack(pady=(0, 10))

        # Entry
        value_var = tk.StringVar(value=str(initial_value))
        entry = ttk.Entry(main_frame, textvariable=value_var, font=('Arial', 12), justify='center')
        entry.pack(fill=tk.X, pady=(0, 15))
        entry.select_range(0, tk.END)
        entry.focus()

        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)

        def on_ok():
            try:
                val = float(value_var.get())
                if val < 0:
                    messagebox.showerror("Invalid Input", "Value must be non-negative", parent=dialog)
                    return
                result['value'] = val
                dialog.destroy()
            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter a valid number", parent=dialog)

        def on_cancel():
            dialog.destroy()

        ttk.Button(
            button_frame,
            text="OK",
            command=on_ok,
            bootstyle="success"
        ).grid(row=0, column=0, sticky='ew', padx=(0, 5))

        ttk.Button(
            button_frame,
            text="Cancel",
            command=on_cancel,
            bootstyle="secondary"
        ).grid(row=0, column=1, sticky='ew', padx=(5, 0))

        # Bind Enter key to OK
        entry.bind('<Return>', lambda e: on_ok())
        dialog.bind('<Escape>', lambda e: on_cancel())

        dialog.wait_window()
        return result['value']

    def mode_dependent_action(self, operation):
        if self.mode == "direct":
            self.stage_operation(operation)
        elif self.mode == "builder":
            self.builder_config(operation)

    # ========== callback functions ==========

    def _start_operation(self, operation_key: str, edit_mode: bool = False):
        """Generic operation starter - works for all operations"""
        if not edit_mode:
            self.clear_edit_mode()

        config = OPERATION_CONFIGS[operation_key]
        self.current_session = OperationSession(operation_key, config)
        self.run_operation_wizard()

    def callback_force_eject(self):
        self.pipettor.eject_tip()
        self.pipettor.has_tips = False

    def callback_force_aspirate(self):
        volume = self.ask_volume_dialog(title="Aspirate Volume", initial_value=0)
        if volume:
            self.pipettor.aspirate(volume)

    def callback_force_dispense(self):
        volume = self.ask_volume_dialog(title="Dispense Volume", initial_value=0)
        if volume:
            self.pipettor.dispense(volume)