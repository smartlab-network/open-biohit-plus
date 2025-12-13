import ttkbootstrap as ttk
import tkinter as tk
import uuid
import threading
from typing import Callable, Optional
from tkinter import messagebox, filedialog

from .well_window import WellWindow
from .collapsible_frame import CollapsibleFrame
from ..pipettor_plus.pipettor_plus import PipettorPlus
from ..deck_structure import *
from ..operations.workflow import Workflow
from ..operations.operation import Operation
from ..operations.operationtype import OperationType
from ..operations.operation_builder import OperationBuilder
from ..operations.operation_logger import OperationLogger
from .executioncontroloverlay import ExecutionControlOverlay

import os
import copy

class FunctionWindow:
    """
    Dual-mode pipetting operations interface.

    Modes
    -----
    direct : Embedded in main GUI, operations staged for execution
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

        if mode == "builder":
            self._state_snapshot = self.pipettor.push_state()
            self.pipettor.set_simulation_mode(True)
            self.workflow = Workflow(name="New Workflow")
            self.parent_function_window = None
            self.workflow_validated = False
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

            self.window_build_func.geometry("1300x750")
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
        # Create scrollable container
        canvas = tk.Canvas(self.container, bg='#f0f0f0', highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.container, orient=tk.VERTICAL, command=canvas.yview)

        self.control_frame = ttk.Frame(canvas)
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        canvas_window = canvas.create_window((0, 0), window=self.control_frame, anchor='nw')

        def configure_scroll(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas_width = canvas.winfo_width()
            if canvas_width > 1:
                canvas.itemconfig(canvas_window, width=canvas_width)

        self.control_frame.bind('<Configure>', configure_scroll)
        canvas.bind('<Configure>', configure_scroll)

        # Title
        ttk.Label(
            self.control_frame,
            text="Pipetting Operations",
            font=('Arial', 14, 'bold')
        ).pack(pady=5)

        # === CUSTOM WORKFLOWS SECTION ===
        workflows_frame = ttk.Labelframe(
            self.control_frame,
            text="Custom Workflows",
            padding=10
        )
        workflows_frame.pack(fill=tk.X, padx=10, pady=5)

        # Workflow listbox with scrollbar
        listbox_frame = ttk.Frame(workflows_frame)
        listbox_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.workflows_listbox = tk.Listbox(
            listbox_frame,
            font=('Arial', 10),
            height=5,
            yscrollcommand=scrollbar.set
        )
        self.workflows_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.workflows_listbox.yview)

        # Workflow action buttons
        workflow_buttons_frame = ttk.Frame(workflows_frame)
        workflow_buttons_frame.pack(fill=tk.X, pady=5)

        ttk.Button(
            workflow_buttons_frame,
            text=" Create",
            command=self.open_workflow_builder,
            bootstyle="success"
        ).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)

        ttk.Button(
            workflow_buttons_frame,
            text=" Open",
            command=self.open_selected_workflow,
            bootstyle="primary"
        ).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)

        ttk.Button(
            workflow_buttons_frame,
            text=" Delete",
            command=self.delete_selected_workflow,
            bootstyle="danger"
        ).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)

        from_file_frame = ttk.Frame(workflows_frame)
        from_file_frame.pack(fill=tk.X, pady=(5, 0))  # Padding at the bottom

        ttk.Button(
            from_file_frame,
            text=" Save to File",
            command=self.save_selected_workflow_to_file,
            bootstyle="primary"
        ).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)


        ttk.Button(
            from_file_frame,
            text=" Load from File",
            command=self.load_workflow_from_file,
            bootstyle="primary"
        ).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)

        # Initialize with empty workflow dict
        self.workflows_in_memory = {}  # Stores workflows created in this session
        self.refresh_workflows_list()

        # === STAGING AREA ===
        staging_frame = ttk.Labelframe(
            self.control_frame,
            text="Staged Operation - Review Before Execution",
            padding=10
        )
        staging_frame.pack(fill=tk.X, padx=10, pady=10)

        # Details display
        self.staged_op_text = tk.Text(
            staging_frame,
            height=8,
            wrap=tk.WORD,
            state='disabled',
            font=('Courier', 10)
        )
        self.staged_op_text.pack(fill=tk.BOTH, expand=True, pady=5)

        # Action buttons
        action_frame = ttk.Frame(staging_frame)
        action_frame.pack(fill=tk.X, pady=5)

        # Configure columns with specific weights
        action_frame.columnconfigure(0, weight=1)
        action_frame.columnconfigure(1, weight=1)
        action_frame.columnconfigure(2, weight=0, minsize=80)

        self.execute_button = ttk.Button(
            action_frame,
            text="Validate",
            command=self.validate_staged_operation,
            state='disabled',
            bootstyle="warning"
        )
        self.execute_button.grid(row=0, column=0, sticky='ew', padx=5)

        self.clear_button = ttk.Button(
            action_frame,
            text="Clear",
            command=self.clear_staged_operation,
            state='disabled',
            bootstyle="secondary"
        )
        self.clear_button.grid(row=0, column=1, sticky='ew', padx=5)

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

        # Create main container frame
        container = ttk.Frame(self.window_build_func)
        container.pack(fill=tk.BOTH, expand=True)

        # Create canvas and scrollbar
        canvas = tk.Canvas(container, bg='#f0f0f0', highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient=tk.VERTICAL, command=canvas.yview)

        # Create the actual content frame that will be scrolled
        content_frame = ttk.Frame(canvas)
        canvas.configure(yscrollcommand=scrollbar.set)

        # Pack scrollbar and canvas
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Create window inside canvas
        canvas_window = canvas.create_window((0, 0), window=content_frame, anchor='nw')

        # Configure scroll region
        def configure_scroll(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas_width = canvas.winfo_width()
            if canvas_width > 1:
                canvas.itemconfig(canvas_window, width=canvas_width)

        content_frame.bind('<Configure>', configure_scroll)
        canvas.bind('<Configure>', configure_scroll)

        # Enable mousewheel scrolling
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def on_mousewheel_linux_up(event):
            canvas.yview_scroll(-1, "units")

        def on_mousewheel_linux_down(event):
            canvas.yview_scroll(1, "units")

        # Bind to canvas ONLY (automatically unbinds when canvas is destroyed)
        canvas.bind("<MouseWheel>", on_mousewheel)  # Windows/MacOS
        canvas.bind("<Button-4>", on_mousewheel_linux_up)  # Linux scroll up
        canvas.bind("<Button-5>", on_mousewheel_linux_down)  # Linux scroll down

        # Also bind when mouse enters the canvas area
        content_frame.bind("<Enter>", lambda e: canvas.focus_set())

        # NOW use content_frame instead of self.window_build_func for grid layout
        # Grid configuration
        content_frame.columnconfigure(0, weight=1)  # Left: buttons
        content_frame.columnconfigure(1, weight=1)  # Middle: selection
        content_frame.columnconfigure(2, weight=1)  # Right: workflow queue

        for i in range(12):
            content_frame.rowconfigure(i, weight=1)

        # Header
        self.label_header = ttk.Label(
            content_frame,  # Changed from self.window_build_func
            text="",
            anchor="center",
            font=('Helvetica', 14)
        )
        self.label_header.grid(row=0, column=0, columnspan=3, sticky="nsew", pady=10)

        # Left column: Operation buttons
        button_container = ttk.Frame(content_frame)  # Changed
        button_container.grid(row=1, column=0, rowspan=10, sticky="nsew", padx=5)
        self.place_operation_buttons(button_container)

        # Middle column: Selection area
        self.stage_label = ttk.Label(
            content_frame,  # Changed
            text="",
            font=('Arial', 14),
            foreground="gray"
        )
        self.stage_label.grid(row=1, column=1, sticky="ew", padx=5, pady=2)

        self.edit_info_label = ttk.Label(
            content_frame,
            text="",
            font=('Arial', 10, 'bold'),
            foreground="orange"
        )
        self.edit_info_label.grid(row=2, column=1, sticky="ew", padx=5, pady=2)

        self.second_column_frame = ttk.Frame(content_frame)  # Changed
        self.second_column_frame.grid(row=3, column=1, rowspan=9, sticky="nsew")
        self.second_column_frame.columnconfigure(0, weight=1)
        for i in range(10):
            self.second_column_frame.rowconfigure(i, weight=1)

        # Right column
        queue_header_frame = ttk.Frame(content_frame)
        queue_header_frame.grid(row=0, column=2, sticky="ew", padx=10, pady=5)

        # Title (left)
        title_label = ttk.Label(
            queue_header_frame,
            text="Workflow Queue",
            font=('Helvetica', 14)
        )
        title_label.grid(row=0, column=0, sticky="w")

        # --- Controls container (right side) ---
        controls_frame = ttk.Frame(queue_header_frame)
        controls_frame.grid(row=0, column=1, sticky="e")

        # Copy button
        self.copy_btn = ttk.Button(
            controls_frame,
            text="Copy",
            command=self.copy_selected_operations,
            state='disabled',
            bootstyle="info-outline",
            width=8
        )
        self.copy_btn.grid(row=0, column=0, padx=3)

        # Paste button
        self.paste_btn = ttk.Button(
            controls_frame,
            text="Paste",
            command=self.paste_operations,
            state='disabled',
            bootstyle="success-outline",
            width=8
        )
        self.paste_btn.grid(row=0, column=1, padx=3)

        # Paste position entry
        self.paste_position_var = tk.StringVar(value="After selected")

        # Paste position entry
        self.paste_position_var = tk.StringVar(value="End")

        # Paste position entry
        self.paste_position_var = tk.StringVar(value="End")

        paste_position_menu = ttk.Combobox(
            controls_frame,
            textvariable=self.paste_position_var,
            values=["End", "Top", "Or enter index..."],
            width=12
        )
        paste_position_menu.grid(row=0, column=2, padx=3)

        paste_position_menu.config(state='disabled')
        self.paste_position_menu = paste_position_menu

        # Stretch title column
        queue_header_frame.columnconfigure(0, weight=1)

        self.third_column_frame = ttk.Frame(content_frame)  # Changed
        self.third_column_frame.grid(row=1, column=2, rowspan=9, sticky="nsew", padx=5)
        self.third_column_frame.columnconfigure(0, weight=1)
        for i in range(20):
            self.third_column_frame.rowconfigure(i, weight=1)

        # Bottom: Workflow controls
        self.frame_name = ttk.Frame(content_frame)  # Changed
        self.frame_name.grid(row=11, column=0, columnspan=3, sticky="nsew", padx=10, pady=5)

        self.frame_name.columnconfigure(0, weight=3)
        self.frame_name.columnconfigure(1, weight=1)
        self.frame_name.columnconfigure(2, weight=1)
        self.frame_name.columnconfigure(3, weight=1)
        self.frame_name.columnconfigure(4, weight=1)

        ttk.Label(self.frame_name, text="Workflow Name:", font=('Arial', 11)).grid(
            row=0, column=0, sticky='w', padx=(0, 10)
        )

        self.entry_name = ttk.Entry(self.frame_name)
        self.entry_name.grid(row=1, column=0, sticky="ew", padx=(0, 10))

        ttk.Button(
            self.frame_name,
            text="Create",
            command=self.callback_create_button,
            bootstyle="success"
        ).grid(row=1, column=1, sticky="ew", padx=2)

        ttk.Button(
            self.frame_name,
            text="Clear",
            command=self.clear_workflow_queue,
            bootstyle="danger"
        ).grid(row=1, column=2, sticky="ew", padx=2)

        self.validate_execute_btn = ttk.Button(
            self.frame_name,
            text="Validate",
            command=self.callback_validate_workflow,
            bootstyle="warning"
        )
        self.validate_execute_btn.grid(row=1, column=3, sticky="ew", padx=2)

        ttk.Button(
            self.frame_name,
            text="Close",
            command=self.callback_close_builder,
            bootstyle="secondary"
        ).grid(row=1, column=4, sticky="ew", padx=2)
    def set_stage(self, text: str):
        """Update stage indicator"""
        if self.mode == "builder" and hasattr(self, 'stage_label'):
            self.stage_label.config(text=text)

    def place_operation_buttons(self, parent_frame):
        """Place all operation buttons (shared between modes)"""
        # Tip Operations
        tip_frame = ttk.Labelframe(parent_frame, text="Tip Management", padding=10)
        tip_frame.pack(fill=tk.X, pady=5, padx=5)

        self.pick_tips_btn = ttk.Button(  
            tip_frame, text=" Pick Tips",
            command=lambda: self.callback_pick_tips(func_str="Pick Tips"),
            bootstyle="primary"
        )
        self.pick_tips_btn.pack(fill=tk.X, pady=2)

        self.return_tips_btn = ttk.Button(  
            tip_frame, text=" Return Tips",
            command=lambda: self.callback_return_tips(func_str="Return Tips"),
            bootstyle="primary"
        )
        self.return_tips_btn.pack(fill=tk.X, pady=2)

        self.replace_tips_btn = ttk.Button(  
            tip_frame, text=" Replace Tips",
            command=lambda: self.callback_replace_tips(func_str="Replace Tips"),
            bootstyle="primary"
        )
        self.replace_tips_btn.pack(fill=tk.X, pady=2)

        self.discard_tips_btn = ttk.Button(  
            tip_frame, text=" Discard Tips",
            command=lambda: self.callback_discard_tips(func_str="Discard Tips"),
            bootstyle="primary"
        )
        self.discard_tips_btn.pack(fill=tk.X, pady=2)

        # Liquid Handling
        liquid_frame = ttk.Labelframe(parent_frame, text="Liquid Handling", padding=10)
        liquid_frame.pack(fill=tk.X, pady=5, padx=5)

        self.add_medium_btn = ttk.Button(  
            liquid_frame, text=" Add Medium",
            command=lambda: self.callback_add_medium(func_str="Add Medium"),
            bootstyle="success"
        )
        self.add_medium_btn.pack(fill=tk.X, pady=2)

        self.remove_medium_btn = ttk.Button(  
            liquid_frame, text=" Remove Medium",
            command=lambda: self.callback_remove_medium(func_str="Remove Medium"),
            bootstyle="success"
        )
        self.remove_medium_btn.pack(fill=tk.X, pady=2)

        self.transfer_plate_btn = ttk.Button(  
            liquid_frame, text=" Transfer Plate to Plate",
            command=lambda: self.callback_transfer_plate_to_plate(func_str="Transfer Plate to Plate"),
            bootstyle="success"
        )
        self.transfer_plate_btn.pack(fill=tk.X, pady=2)

        self.remove_and_add_btn = ttk.Button(
            liquid_frame, text=" Remove & Add (Batched)",
            command=lambda: self.callback_remove_and_add(func_str="Remove & Add"),
            bootstyle="success"
        )
        self.remove_and_add_btn.pack(fill=tk.X, pady=2)

        self.foc_frame = ttk.Labelframe(parent_frame, text=" FOC Measurement", padding=5)
        self.foc_frame.pack(fill=tk.X, pady=5, padx=5)

        # Initial population of FOC section
        self.update_foc_section()

        self.low_level_collapsible = CollapsibleFrame(parent_frame, text="Low-Level")
        self.low_level_collapsible.pack(fill=tk.X, pady=5, padx=5)

        # Put buttons inside the content_frame
        self.suck_btn = ttk.Button(
            self.low_level_collapsible.content_frame, text=" Suck",
            command=lambda: self.callback_suck(func_str="Suck"),
            bootstyle="info"
        )
        self.suck_btn.pack(fill=tk.X, pady=2, padx=5)

        self.spit_btn = ttk.Button(
            self.low_level_collapsible.content_frame, text=" Spit",
            command=lambda: self.callback_spit(func_str="Spit"),
            bootstyle="info"
        )
        self.spit_btn.pack(fill=tk.X, pady=2, padx=5)

        # === SYSTEM OPERATIONS - COLLAPSIBLE ===
        self.system_collapsible = CollapsibleFrame(parent_frame, text="System")
        self.system_collapsible.pack(fill=tk.X, pady=5, padx=5)

        # Put buttons inside the content_frame
        self.home_btn = ttk.Button(
            self.system_collapsible.content_frame, text=" Home",
            command=lambda: self.callback_home(func_str="Home"),
            bootstyle="secondary"
        )
        self.home_btn.pack(fill=tk.X, pady=2, padx=5)

        self.move_xy_btn = ttk.Button(
            self.system_collapsible.content_frame, text=" Move X, Y",
            command=lambda: self.callback_move_xy(func_str="Move X, Y"),
            bootstyle="secondary"
        )
        self.move_xy_btn.pack(fill=tk.X, pady=2, padx=5)

        self.move_z_btn = ttk.Button(
            self.system_collapsible.content_frame, text=" Move Z",
            command=lambda: self.callback_move_z(func_str="Move Z"),
            bootstyle="secondary"
        )
        self.move_z_btn.pack(fill=tk.X, pady=2, padx=5)

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
        self.validate_execute_btn.config(
            text="Validate",
            bootstyle="warning",
            command=self.callback_validate_workflow
        )

        # Update display
        self.display_workflow_queue()

    def launch_edit_callback(self, index: int):
        """Launch the appropriate callback for editing this operation"""

        if index >= len(self.workflow.operations):
            return

        operation = self.workflow.operations[index]

        op_type = operation.operation_type

        # Store edit context
        self.edit_mode = True
        self.edit_index = index

        # Clear middle column
        self.clear_grid(self.second_column_frame)

        params = operation.parameters
        formatted_text = "\n".join([f"{key}: {value}" for key, value in params.items()])

        # Update the label
        self.edit_info_label.config(text=formatted_text)

        # Launch appropriate callback based on operation type
        if op_type == OperationType.PICK_TIPS:
            self.callback_pick_tips(func_str="Pick Tips", edit_mode=True)
        elif op_type == OperationType.RETURN_TIPS:
            self.callback_return_tips(func_str="Return Tips", edit_mode=True)
        elif op_type == OperationType.REPLACE_TIPS:
            self.callback_replace_tips(func_str="Replace Tips", edit_mode=True)
        elif op_type == OperationType.DISCARD_TIPS:
            self.callback_discard_tips(func_str="Discard Tips", edit_mode=True)
        elif op_type == OperationType.ADD_MEDIUM:
            self.callback_add_medium(func_str="Add Medium", edit_mode=True)
        elif op_type == OperationType.REMOVE_MEDIUM:
            self.callback_remove_medium(func_str="Remove Medium", edit_mode=True)
        elif op_type == OperationType.TRANSFER_PLATE_TO_PLATE:
            self.callback_transfer_plate_to_plate(func_str="Transfer Plate to Plate", edit_mode=True)
        elif op_type == OperationType.SUCK:
            self.callback_suck(func_str="Suck", edit_mode=True)
        elif op_type == OperationType.SPIT:
            self.callback_spit(func_str="Spit", edit_mode=True)
        elif op_type == OperationType.MOVE_XY:
            self.callback_move_xy(func_str="Move X, Y", edit_mode=True)
        elif op_type == OperationType.MOVE_Z:
            self.callback_move_z(func_str="Move Z", edit_mode=True)
        elif op_type == OperationType.HOME:
            self.callback_home(func_str="Home", edit_mode=True)
        elif op_type == OperationType.MEASURE_FOC:
            self.callback_measure_foc(func_str="Measure FOC", edit_mode=True)
        elif op_type == OperationType.REMOVE_AND_ADD:
            self.callback_remove_and_add(func_str="Remove and Add", edit_mode=True)



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

        # Create modal overlay - blocks all GUI interaction
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
        if self.workflow and self.workflow.operations:
            if not messagebox.askyesno(
                    "Unsaved Workflow",
                    "You have unsaved operations. Close anyway?",
                    default="no"
            ):
                return

        # Clean up and close
        if self.mode == "builder":
            self.pipettor.pop_state(self._state_snapshot)
        self.window_build_func.destroy()

    def callback_measure_foc(self, func_str: str, edit_mode: bool = False):
        """Handle FOC measurement operation"""
        if not edit_mode:
            self.clear_edit_mode()

        # Ask for wait time using the generic dialog
        wait_time = self.ask_volume_dialog(
            title="FOC Measurement Wait Time",
            initial_value=0,
            label_text="Incubation time (sec):"
        )

        if wait_time is None:
            return  # User cancelled

        # Convert to int
        wait_time = int(wait_time)

        if self.mode == "builder":
            plate_name = self.pipettor.foc_plate_name

            operation = OperationBuilder.build_measure_foc(
                wait_seconds=wait_time,
                plate_name=plate_name
            )

            self.builder_config(operation)

        else:  # direct mode
            try:
                self.pipettor.measure_foc(
                    seconds=wait_time,
                    platename=self.pipettor.foc_plate_name
                )

                if self.on_operation_complete:
                    self.on_operation_complete()

            except Exception as e:
                messagebox.showerror("Error", f"FOC measurement failed:\n{str(e)}")

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

    def add_current_function(self, func: Callable, func_str: str, labware_id: str):
        """Add function to workflow queue (builder mode)"""
        self.current_func_list.append(func)
        self.current_func_details.append(f"{func_str}: {labware_id}")
        self.display_workflow_queue()
        self.clear_grid(self.second_column_frame)

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
                text="No operations in queue\n\nClick operation buttons to add",
                font=("Helvetica", 12),
                foreground="gray"
            ).pack(pady=20)
            return

        # Display each operation
        for idx, operation in enumerate(self.workflow.operations):
            frame = ttk.Frame(self.third_column_frame, relief=tk.RAISED, borderwidth=1)
            frame.grid(row=idx, column=0, sticky="ew", pady=2, padx=5)
            frame.columnconfigure(0, weight=1)  # Label column expands

            # Operation label
            var = tk.BooleanVar(value=(idx in self.selected_operations))
            checkbox = ttk.Checkbutton(
                frame,
                variable=var,
                command=lambda i=idx, v=var: self.toggle_operation_selection(i, v),
                bootstyle="round-toggle"
            )
            checkbox.grid(row=0, column=0, sticky="w", padx=(5, 2))

            op_text = f"{idx + 1}. {operation.operation_type.value}"
            if 'labware_id' in operation.parameters:
                op_text += f": {operation.parameters['labware_id']}"

            label = ttk.Label(frame, text=op_text, font=("Helvetica", 11))
            label.grid(row=0, column=1, sticky="w", padx=5)

            # Move button (NEW)
            move_btn = ttk.Button(
                frame,
                text="↕",  # Up-down arrow
                width=3,
                command=lambda i=idx: self.reorder_operation(i),
                bootstyle="info-outline"
            )
            move_btn.grid(row=0, column=2, sticky="e", padx=2)

            # Edit button
            edit_btn = ttk.Button(
                frame,
                text="✏",
                width=3,
                command=lambda i=idx: self.launch_edit_callback(i),
                bootstyle="warning-outline"
            )
            edit_btn.grid(row=0, column=3, sticky="e", padx=2)

            # Info button
            info_btn = ttk.Button(
                frame,
                text="ℹ",
                width=3,
                command=lambda op=operation: self.show_operation_details(op),
                bootstyle="info-outline"
            )
            info_btn.grid(row=0, column=4, sticky="e", padx=2)

            # Remove button
            remove_btn = ttk.Button(
                frame,
                text="🗑",
                width=3,
                command=lambda i=idx: self.remove_operation_from_workflow(i),
                bootstyle="danger-outline"
            )
            remove_btn.grid(row=0, column=5, sticky="e", padx=2)
        self.update_copy_paste_buttons()
    # --- Helper Methods ---
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

        # Clear frame
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
                command=lambda: self.callback_measure_foc(func_str="Measure FOC"),
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

    def execute_foc_measurement(self):
        """Execute FOC measurement with parameters from input fields"""
        try:
            # Get and validate inputs
            wait_time = int(self.foc_wait_time_var.get())
            plate_name = self.pipettor.foc_plate_name

            if not plate_name:
                messagebox.showerror("Error", "Please enter a plate name")
                return

            if self.mode == "builder":
                # Create operation and add to workflow
                operation = OperationBuilder.build_measure_foc(
                    wait_seconds=wait_time,
                    plate_name=plate_name
                )
                self.builder_config(operation)

            else:
                # Execute
                self.pipettor.measure_foc(
                    seconds=wait_time,
                    platename=plate_name,
                )

                if self.on_operation_complete:
                    self.on_operation_complete()

        except ValueError:
            messagebox.showerror("Error", "Wait time must be a valid number")
        except Exception as e:
            messagebox.showerror("Error", f"FOC failed:\n{str(e)}")

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
        self.validate_execute_btn.config(
            text="Validate",
            bootstyle="warning",
            command=self.callback_validate_workflow
        )

        # Update display
        self.display_workflow_queue()

        # Reset to "End" for next paste
        self.paste_position_var.set("End")
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

        ttk.Button(
            button_frame,
            text="Confirm",
            command=on_confirm,
            bootstyle="success"
        ).grid(row=0, column=0, sticky='ew', padx=(0, 5))

        ttk.Button(
            button_frame,
            text="Cancel",
            command=on_cancel,
            bootstyle="secondary"
        ).grid(row=0, column=1, sticky='ew', padx=(5, 0))

        # Focus and select
        spinbox.focus()
        spinbox.selection_range(0, tk.END)

        # Bind Enter key
        spinbox.bind('<Return>', lambda e: on_confirm())

        # Wait for user decision using wait_variable on the BooleanVar
        self.get_master_window().wait_variable(wait_var)

        return result['position']

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
            self.validate_execute_btn.config(text="Validate", bootstyle="warning",
                                             command=self.callback_validate_workflow)

            self.display_workflow_queue()

    def show_operation_details(self, operation: Operation):
        """Show detailed information about an operation"""
        details_window = ttk.Toplevel(self.get_master_window())
        details_window.title(f"Operation Details")
        details_window.geometry("500x400")
        details_window.transient(self.get_master_window())

        # Details text
        text = tk.Text(details_window, wrap=tk.WORD, font=("Courier", 10))
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Format operation details
        details = f"Operation Type: {operation.operation_type.value}\n"
        details += f"Description: {operation.description}\n"
        details += "Parameters:\n"
        for key, value in operation.parameters.items():
            details += f"  {key}: {value}\n"

        text.insert(1.0, details)
        text.config(state='disabled')

        # Close button
        ttk.Button(
            details_window,
            text="Close",
            command=details_window.destroy
        ).pack(pady=10)

    def clear_workflow_queue(self):
        """Clear all operations from queue"""
        if not self.workflow or not self.workflow.operations:
            return

        if messagebox.askyesno("Confirm", "Clear all operations from queue?", default="yes"):
            # Clear workflow operations
            self.workflow.operations.clear()

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

        # Open workflow builder with this workflow loaded
        builder = FunctionWindow(
            deck=self.deck,
            pipettor=self.pipettor,
            mode="builder",
            master=self.container.winfo_toplevel()
        )

        # Give builder a reference to this direct mode window
        builder.parent_function_window = self

        # Load the workflow into the builder WITHOUT executing operations
        builder.workflow = workflow
        builder.entry_name.delete(0, tk.END)
        builder.entry_name.insert(0, workflow.name)

        # Just display the operations - don't replay them
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
            messagebox.showinfo(
                "Saved",
                f"Workflow '{workflow_name}' saved to:\n{filepath}"
            )
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

    def display_possible_labware(
            self,
            labware_type,
            next_callback,
            func_str,
            part="first",
            start_row=0,
            **kwargs
    ):
        """Display selectable labware buttons"""
        if self.mode == "builder":
            target_frame = self.second_column_frame

            #parameters are printed on start_row = 0
            if hasattr(self, 'edit_mode') and self.edit_mode:
                start_row = 1

            for slot_id, labware in self.dict_top_labware.items():
                if not isinstance(labware, labware_type):
                    continue

                label = ttk.Label(target_frame, text=f"Slot: {slot_id}")
                label.grid(column=0, row=start_row, sticky="nsew", pady=5, padx=5)
                start_row += 1

                button = ttk.Button(
                    target_frame,
                    text=labware.labware_id,
                    bootstyle="warning",
                    command=lambda lw=labware: next_callback(
                        func_str=func_str,
                        part=part,
                        labware_obj=lw,
                        **kwargs
                    )
                )
                button.grid(column=0, row=start_row, sticky="nsew", pady=5, padx=5)
                start_row += 1

        else:  # DIRECT MODE
            # Create selection dialog
            dialog = tk.Toplevel(self.get_master_window())
            #dialog.title(f"Select {labware_type.__name__}")
            dialog.title(f"Select labware")
            dialog.geometry("400x500")
            dialog.transient(self.get_master_window())
            dialog.grab_set()

            # Create scrollable frame
            canvas = tk.Canvas(dialog)
            scrollbar = ttk.Scrollbar(dialog, orient=tk.VERTICAL, command=canvas.yview)
            frame = ttk.Frame(canvas)

            canvas.configure(yscrollcommand=scrollbar.set)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            canvas_window = canvas.create_window((0, 0), window=frame, anchor='nw')

            # Configure scrolling
            def configure_scroll(event=None):
                canvas.configure(scrollregion=canvas.bbox("all"))
                canvas_width = canvas.winfo_width()
                if canvas_width > 1:
                    canvas.itemconfig(canvas_window, width=canvas_width)

            frame.bind('<Configure>', configure_scroll)
            canvas.bind('<Configure>', configure_scroll)

            # Add labware buttons
            row = 0
            found_labware = False

            for slot_id, labware in self.dict_top_labware.items():
                if not isinstance(labware, labware_type):
                    continue

                found_labware = True

                ttk.Label(
                    frame,
                    text=f"Slot: {slot_id}",
                    font=('Arial', 11, 'bold')
                ).grid(column=0, row=row, sticky="w", pady=(10, 2), padx=10)
                row += 1

                def make_callback(lw=labware):
                    def callback():
                        dialog.destroy()
                        next_callback(
                            func_str=func_str,
                            part=part,
                            labware_obj=lw,
                            **kwargs
                        )

                    return callback

                ttk.Button(
                    frame,
                    text=f"{labware.labware_id} ({labware.__class__.__name__})",
                    command=make_callback(labware),
                    bootstyle="primary"
                ).grid(column=0, row=row, sticky="ew", pady=2, padx=10)
                row += 1

            if not found_labware:
                ttk.Label(
                    frame,
                    #text=f"No {labware_type.__name__} found on deck",
                    text=f"No labware found on deck",
                    font=('Arial', 12),
                    foreground='red'
                ).grid(column=0, row=0, pady=20, padx=20)

                ttk.Button(
                    frame,
                    text="Close",
                    command=dialog.destroy,
                    bootstyle="secondary"
                ).grid(column=0, row=1, pady=10, padx=20)

            # Add cancel button at bottom
            ttk.Button(
                frame,
                text="Cancel",
                command=dialog.destroy,
                bootstyle="secondary"
            ).grid(column=0, row=row, sticky="ew", pady=10, padx=10)

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

        def on_ok(event=None):
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

        def on_cancel(event=None):
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

    def ask_volume_dialog(self, title="Enter Volume", initial_value=0, label_text="Volume per well (ul):"):
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

    def compute_volume_constraints(self, labware_obj, volume_per_well: float, is_multichannel: bool = False,
                                   operation: str = 'removal'):
        """
        Compute wells that should be deactivated based on volume requirements.

        Parameters
        ----------
        labware_obj : Labware
            The labware object (Plate or ReservoirHolder)
        volume_per_well : float
            Volume per well (µL) - to be removed or added
        is_multichannel : bool
            Whether this is for multichannel operation
        operation : str
            'removal' - check if wells have enough volume to remove
            'addition' - check if wells have enough space to add

        Returns
        -------
        dict[tuple[int, int], dict]
            Dictionary mapping (row, col) to constraint info for wells that should be deactivated
        """
        if not labware_obj.each_tip_needs_separate_item():
            is_multichannel = False

        constraints = {}

        if isinstance(labware_obj, Plate):
            wells = labware_obj.get_wells()
            for (col, row), well in wells.items():

                # Determine what to check based on operation
                if operation == 'removal':
                    check_volume = well.get_total_volume()
                    has_constraint = check_volume < volume_per_well
                    reason = 'insufficient_volume'
                    volume_key = 'current_volume'
                else:  # addition
                    check_volume = well.get_available_volume()
                    has_constraint = check_volume < volume_per_well
                    reason = 'overflow_risk'
                    volume_key = 'available_volume'


                # For multichannel, check if start position - need consecutive wells
                if row + self.channels <= labware_obj._rows:
                    # Check all wells in this column starting from this row
                    fails_constraint = False
                    for i in range(self.channels):
                        check_well = labware_obj.get_well_at(col, row + i)
                        if check_well:
                            if operation == 'removal':
                                if check_well.get_total_volume() < volume_per_well:
                                    fails_constraint = True
                                    break
                            else:  # addition
                                if check_well.get_available_volume() < volume_per_well:
                                    fails_constraint = True
                                    break

                    if fails_constraint:
                        constraints[(row, col)] = {
                            'reason': reason,
                            volume_key: check_volume,
                            'required_volume': volume_per_well
                        }

        elif isinstance(labware_obj, ReservoirHolder):
            # For reservoirs, check total volume for all wells it will serve/receive
            hook_to_reservoir = labware_obj.get_hook_to_reservoir_map()

            for hook_id, reservoir in hook_to_reservoir.items():
                if reservoir is not None:
                    col, row = labware_obj.hook_id_to_position(hook_id)

                    # Calculate total volume
                    total_volume = volume_per_well * self.channels

                    # Determine what to check based on operation
                    if operation == 'removal':
                        check_volume = reservoir.get_total_volume()
                        has_constraint = check_volume < total_volume
                        reason = 'insufficient_volume'
                        volume_key = 'current_volume'
                    else:  # addition
                        check_volume = reservoir.get_available_volume()
                        has_constraint = check_volume < total_volume
                        reason = 'overflow_risk'
                        volume_key = 'available_volume'

                    if has_constraint:
                        constraints[(row, col)] = {
                            'reason': reason,
                            volume_key: check_volume,
                            'required_volume': total_volume
                        }

        return constraints

    # ========== call back functions ==========

    def callback_pick_tips(
            self,
            func_str: str,
            part: str = "first",
            labware_obj: PipetteHolder = None,
            edit_mode: bool = False,
            **kwargs
    ):

        """Handle Pick Tips operation"""
        if part == "first":
            if not edit_mode:  # Only clear if not explicitly in edit mode
                self.clear_edit_mode()

            self.set_stage("choose labware to pick tip from")
            
            if self.mode == "builder":
                self.clear_grid(self.second_column_frame)
            self.display_possible_labware(
                labware_type=PipetteHolder,
                next_callback=self.callback_pick_tips,
                func_str=func_str,
                part="second",
                **kwargs
            )

        elif part == "second" and labware_obj is not None:

            window = WellWindow(
                rows=labware_obj.holders_across_y,
                columns=labware_obj.holders_across_x,
                labware_id=labware_obj.labware_id,
                max_selected=1 if self.mode == "builder" else None, # only way to allow tracking in the builder mode
                master=self.get_master_window(),
                multichannel_mode=self.multichannel,
                title=f"Pick tips from: {labware_obj.labware_id}",
                wells_list=self.get_wells_list_from_labware(
                    labware_obj=labware_obj,
                    source=True,
                ) if self.mode == "direct" else [(r, c) for r in range(labware_obj.holders_across_y)
                                               for c in range(labware_obj.holders_across_x)],
                allow_auto_select=True
            )
            self.get_master_window().wait_window(window.get_root())

            if window.auto_selected:  # ← NEW FLAG
                list_col_row = None  # Pass None to let pipettor auto-detect
            else:

                start_positions = window.get_start_positions()
                if not start_positions or not window.confirmed:
                    return

                # Convert from (row, col) to (col, row) format for pipettor
                list_col_row = [(c, r) for r, c in start_positions]

            operation = OperationBuilder.build_pick_tips(
                labware_id=labware_obj.labware_id,
                positions=list_col_row,
                channels=self.channels
            )

            # Mode-specific handling
            if self.mode == "direct":
                self.stage_operation(operation)
            elif self.mode == "builder":
                self.builder_config(operation)

    def callback_return_tips(
            self,
            func_str: str,
            part: str = "first",
            labware_obj: PipetteHolder = None,
            edit_mode: bool = False,
            **kwargs
    ):
        """Handle Return Tips operation"""
        if part == "first":
            if not edit_mode:  # Only clear if not explicitly in edit mode
                self.clear_edit_mode()
            self.set_stage("choose labware to return tip to")
            if self.mode == "builder":
                self.clear_grid(self.second_column_frame)
            self.display_possible_labware(
                labware_type=PipetteHolder,
                next_callback=self.callback_return_tips,
                func_str=func_str,
                part="second",
                **kwargs
            )

        elif part == "second" and labware_obj is not None:

            window = WellWindow(
                rows=labware_obj.holders_across_y,
                columns=labware_obj.holders_across_x,
                labware_id=labware_obj.labware_id,
                max_selected=1 if self.mode == "builder" else None,
                master=self.get_master_window(),
                multichannel_mode= self.multichannel,
                title=f"Return tips to: {labware_obj.labware_id}",
                wells_list=self.get_wells_list_from_labware(
                    labware_obj=labware_obj,
                    source=False,  # Empty positions
                ) if self.mode == "direct" else [(r, c) for r in range(labware_obj.holders_across_y)
                                               for c in range(labware_obj.holders_across_x)],
                allow_auto_select=True
            )
            self.get_master_window().wait_window(window.get_root())

            if window.auto_selected:
                list_col_row = None
            else:
                start_positions = window.get_start_positions()
                if not start_positions or not window.confirmed:
                    return
                list_col_row = [(c, r) for r, c in start_positions]

            # Create details
            operation = OperationBuilder.build_return_tips(
                labware_id=labware_obj.labware_id,
                positions=list_col_row,
                channels=self.channels
            )

            # Mode-specific handling
            if self.mode == "direct":
                self.stage_operation(operation)
            elif self.mode == "builder":
                self.builder_config(operation)

    def callback_replace_tips(
            self,
            func_str: str,
            part: str = "first",
            labware_obj: PipetteHolder = None,
            edit_mode: bool = False,
            **kwargs
    ):
        """Handle Replace Tips operation"""
        if part == "first":
            if not edit_mode:  # Only clear if not explicitly in edit mode
                self.clear_edit_mode()
            self.set_stage("")
            # Ask for RETURN labware
            if self.mode == "builder":
                self.clear_grid(self.second_column_frame)
            self.set_stage("choose labware to return tips to")
            self.display_possible_labware(
                labware_type=PipetteHolder,
                next_callback=self.callback_replace_tips,
                func_str=func_str,
                part="second",  # Go to part="second" to select return positions
                **kwargs
            )

        elif part == "second" and labware_obj is not None:
            # Store the RETURN labware
            kwargs['return_labware'] = labware_obj

            # ===== STEP 1: Select return positions =====
            window_return = WellWindow(
                rows=labware_obj.holders_across_y,
                columns=labware_obj.holders_across_x,
                labware_id=labware_obj.labware_id,
                max_selected=1 if self.mode == "builder" else None,
                master=self.get_master_window(),
                multichannel_mode=self.multichannel,
                title=f"Return tips to: {labware_obj.labware_id}",
                wells_list=self.get_wells_list_from_labware(
                    labware_obj=labware_obj,
                    source=False,  # Empty positions
                ) if self.mode == "direct" else [(r, c) for r in range(labware_obj.holders_across_y)
                                               for c in range(labware_obj.holders_across_x)],
                allow_auto_select=True
            )
            self.get_master_window().wait_window(window_return.get_root())

            if window_return.auto_selected:
                kwargs['return_positions'] = None
            else:
                start_positions_return = window_return.get_start_positions()
                if not start_positions_return or not window_return.confirmed:
                    return
                kwargs['return_positions'] = [(c, r) for r, c in start_positions_return]

            # Now ask for PICK labware
            if self.mode == "builder":
                self.clear_grid(self.second_column_frame)
            self.set_stage("choose labware to pick tip from")
            self.display_possible_labware(
                labware_type=PipetteHolder,
                next_callback=self.callback_replace_tips,
                func_str=func_str,
                part="third",  # Go to part="third" to select pick positions
                **kwargs
            )

        elif part == "third" and labware_obj is not None:
            # Store the PICK labware
            kwargs['pick_labware'] = labware_obj

            # ===== STEP 2: Select pick positions =====
            window_pick = WellWindow(
                rows=labware_obj.holders_across_y,
                columns=labware_obj.holders_across_x,
                labware_id=labware_obj.labware_id,
                max_selected=1 if self.mode == "builder" else None,
                master=self.get_master_window(),
                multichannel_mode=self.multichannel,
                title=f"Pick new tips from: {labware_obj.labware_id}",
                wells_list=self.get_wells_list_from_labware(
                    labware_obj=labware_obj,
                    source=True,
                ) if self.mode == "direct" else [(r, c) for r in range(labware_obj.holders_across_y)
                                               for c in range(labware_obj.holders_across_x)],
                allow_auto_select=True
            )
            self.get_master_window().wait_window(window_pick.get_root())

            if window_pick.auto_selected:
                list_pick = None
            else:
                start_positions_pick = window_pick.get_start_positions()
                if not start_positions_pick or not window_pick.confirmed:
                    return
                list_pick = [(c, r) for r, c in start_positions_pick]

            # Create operation with BOTH labware
            operation = OperationBuilder.build_replace_tips(
                return_labware_id=kwargs['return_labware'].labware_id,
                return_positions=kwargs['return_positions'],
                pick_labware_id=kwargs['pick_labware'].labware_id,  # Different labware!
                pick_positions=list_pick,
                channels=self.channels
            )

            # Mode-specific handling
            if self.mode == "direct":
                self.stage_operation(operation)
            elif self.mode == "builder":
                self.builder_config(operation)

    def callback_discard_tips(
            self,
            func_str: str,
            part: str = "first",
            labware_obj: TipDropzone = None,
            edit_mode: bool = False,
            **kwargs
    ):
        """Handle Discard Tips operation"""
        if part == "first":
            if not edit_mode:  # Only clear if not explicitly in edit mode
                self.clear_edit_mode()
            self.set_stage("choose labware to discard tips to")

            if self.mode == "builder":
                self.clear_grid(self.second_column_frame)

            self.display_possible_labware(
                labware_type=TipDropzone,
                next_callback=self.callback_discard_tips,
                func_str=func_str,
                part="second",
                **kwargs
            )

        elif part == "second" and labware_obj is not None:
            operation = OperationBuilder.build_discard_tips(
                labware_id=labware_obj.labware_id,
            )

            # Mode-specific handling
            if self.mode == "direct":
                self.stage_operation(operation)
            elif self.mode == "builder":
                self.builder_config(operation)

    def callback_add_medium(
            self,
            func_str: str,
            part: str = "first",
            labware_obj=None,
            edit_mode: bool = False,
            **kwargs
    ):
        """
        Handle Add Medium operation.
        Order: Volume -> Destination (Plate) -> Source (Reservoir)
        """
        # --- PART 1: GET VOLUME ---
        if part == "first":
            if not edit_mode:  # Only clear if not explicitly in edit mode
                self.clear_edit_mode()
            self.set_stage("")
            volume = self.ask_volume_dialog(title="Add Medium Volume", initial_value=100)
            if volume:
                self.callback_add_medium(func_str, part="second", volume=volume, **kwargs)

        # --- PART 2: SELECT DESTINATION (PLATE) ---
        elif part == "second":
            if self.mode == "builder":
                self.clear_grid(self.second_column_frame)
            self.set_stage("choose plate to dispense liquid to")
            kwargs['volume'] = kwargs.get('volume')
            self.display_possible_labware(
                labware_type=Plate,
                next_callback=self.callback_add_medium,
                func_str=func_str,
                part="third",
                **kwargs
            )

        # --- PART 3: HANDLE PLATE SELECTION & ASK RESERVOIR ---
        elif part == "third" and labware_obj is not None:
            # Compute volume constraints for addition (overflow check)
            volume = kwargs.get('volume')
            volume_constraints = self.compute_volume_constraints(
                labware_obj, volume, self.multichannel, operation='addition'
            )


            window = WellWindow(
                rows=labware_obj._rows,
                columns=labware_obj._columns,
                labware_id=labware_obj.labware_id,
                max_selected=None,
                multichannel_mode=self.multichannel,
                master=self.get_master_window(),
                title=f"DESTINATION: Select wells on {labware_obj.labware_id}",
                wells_list=self.get_wells_list_from_labware(labware_obj=labware_obj, source=False),
                volume_constraints= volume_constraints if self.mode == "direct" else {}
            )
            self.get_master_window().wait_variable(window.safe_var)

            kwargs["dest_labware"] = labware_obj
            if self.multichannel:
                kwargs["dest_positions"] = [(c, r) for r, c in window.get_start_positions()]
            else:
                kwargs["dest_positions"] = [(c, r) for r, row in enumerate(window.well_state)
                                            for c, v in enumerate(row) if v]
            del window

            if not kwargs["dest_positions"]:
                return

            if self.mode == "builder":
                self.clear_grid(self.second_column_frame)
            self.set_stage("choose reservoir to aspirate liquid from")
            self.display_possible_labware(
                labware_type=ReservoirHolder,
                next_callback=self.callback_add_medium,
                func_str=func_str,
                part="fourth",
                **kwargs
            )

        # --- PART 4: HANDLE RESERVOIR SELECTION & CREATE OPERATION ---
        elif part == "fourth" and labware_obj is not None:
            # Compute volume constraints for source reservoir (insufficient volume check)
            volume = kwargs.get('volume')
            num_dest_positions = len(kwargs['dest_positions'])
            volume_constraints = self.compute_volume_constraints(
                labware_obj, volume * num_dest_positions, self.multichannel, operation='removal'
            )

            window = WellWindow(
                rows=labware_obj.hooks_across_y,
                columns=labware_obj.hooks_across_x,
                labware_id=labware_obj.labware_id,
                max_selected=1,
                multichannel_mode=False if not labware_obj.each_tip_needs_separate_item() else self.multichannel,
                master=self.get_master_window(),
                title=f"SOURCE: Choose reservoir {labware_obj.labware_id}",
                wells_list=self.get_wells_list_from_labware(labware_obj=labware_obj, source=True),
                volume_constraints= volume_constraints if self.mode == "direct" else {}
            )
            self.get_master_window().wait_variable(window.safe_var)

            kwargs["source_labware"] = labware_obj
            selected = [(c, r) for r, row in enumerate(window.well_state) for c, v in enumerate(row) if v]
            kwargs["source_positions"] = selected[0] if selected else None
            del window

            if not kwargs["source_positions"]:
                return

            operation = OperationBuilder.build_add_medium(
                source_labware_id=kwargs["source_labware"].labware_id,
                source_positions=kwargs["source_positions"],
                dest_labware_id=kwargs["dest_labware"].labware_id,
                dest_positions=kwargs["dest_positions"],
                volume=kwargs['volume'],
                channels=self.channels
            )

            if self.mode == "direct":
                self.stage_operation(operation)
            elif self.mode == "builder":
                self.builder_config(operation)

    def callback_remove_medium(
            self,
            func_str: str,
            part: str = "first",
            labware_obj=None,
            edit_mode: bool = False,
            **kwargs
    ):
        """
        Handle Remove Medium operation.
        Order: Volume -> Source (Plate) -> Destination (Reservoir)
        """
        # --- PART 1: GET VOLUME ---
        if part == "first":
            if not edit_mode:  # Only clear if not explicitly in edit mode
                self.clear_edit_mode()
            self.set_stage("")
            volume = self.ask_volume_dialog(title="Remove Medium Volume", initial_value=100)
            if volume:
                self.callback_remove_medium(func_str, part="second", volume=volume, **kwargs)

        # --- PART 2: SELECT SOURCE (PLATE) ---
        elif part == "second":
            if self.mode == "builder":
                self.clear_grid(self.second_column_frame)
            self.set_stage("choose plate to aspirate liquid from")
            kwargs['volume'] = kwargs.get('volume')
            self.display_possible_labware(
                labware_type=Plate,
                next_callback=self.callback_remove_medium,
                func_str=func_str,
                part="third",
                **kwargs
            )

        # --- PART 3: HANDLE PLATE SELECTION & ASK RESERVOIR ---
        elif part == "third" and labware_obj is not None:
            # Compute volume constraints for removal (insufficient volume check)
            volume = kwargs.get('volume')
            volume_constraints = self.compute_volume_constraints(
                labware_obj, volume, self.multichannel, operation='removal'
            )

            window = WellWindow(
                rows=labware_obj._rows,
                columns=labware_obj._columns,
                labware_id=labware_obj.labware_id,
                max_selected=None,
                multichannel_mode=self.multichannel,
                master=self.get_master_window(),
                title=f"SOURCE: Select wells on {labware_obj.labware_id}",
                wells_list=self.get_wells_list_from_labware(labware_obj=labware_obj, source=True),
                volume_constraints= volume_constraints if self.mode == "direct" else {}
            )
            self.get_master_window().wait_variable(window.safe_var)

            kwargs["source_labware"] = labware_obj
            if self.multichannel:
                kwargs["source_positions"] = [(c, r) for r, c in window.get_start_positions()]
            else:
                kwargs["source_positions"] = [(c, r) for r, row in enumerate(window.well_state)
                                              for c, v in enumerate(row) if v]
            del window

            if not kwargs["source_positions"]:
                return

            if self.mode == "builder":
                self.clear_grid(self.second_column_frame)

            self.set_stage("choose reservoir to dispense liquid to")
            self.display_possible_labware(
                labware_type=ReservoirHolder,
                next_callback=self.callback_remove_medium,
                func_str=func_str,
                part="fourth",
                **kwargs
            )

        # --- PART 4: HANDLE RESERVOIR SELECTION & CREATE OPERATION ---
        elif part == "fourth" and labware_obj is not None:
            # Compute volume constraints for reservoir (overflow check)
            volume = kwargs.get('volume')
            num_source_positions = len(kwargs['source_positions'])
            volume_constraints = self.compute_volume_constraints(
                labware_obj, volume, self.multichannel, operation='addition'
            )

            window = WellWindow(
                rows=labware_obj.hooks_across_y,
                columns=labware_obj.hooks_across_x,
                labware_id=labware_obj.labware_id,
                max_selected=1,
                multichannel_mode=False if not labware_obj.each_tip_needs_separate_item() else self.multichannel,
                master=self.get_master_window(),
                title=f"DESTINATION: Select reservoir {labware_obj.labware_id}",
                wells_list=self.get_wells_list_from_labware(labware_obj=labware_obj, source=False),
                volume_constraints= volume_constraints if self.mode == "direct" else {}
            )
            self.get_master_window().wait_variable(window.safe_var)

            kwargs["dest_labware"] = labware_obj
            selected = [(c, r) for r, row in enumerate(window.well_state) for c, v in enumerate(row) if v]
            kwargs["dest_positions"] = selected[0] if selected else None
            del window

            if not kwargs["dest_positions"]:
                return

            # Create Operation object (unified for both modes)
            operation = OperationBuilder.build_remove_medium(
                source_labware_id=kwargs["source_labware"].labware_id,
                source_positions=kwargs["source_positions"],
                dest_labware_id=kwargs["dest_labware"].labware_id,
                dest_positions=kwargs["dest_positions"],
                volume=kwargs['volume'],
                channels=self.channels
            )

            # Mode-specific handling
            if self.mode == "direct":
                self.stage_operation(operation)
            elif self.mode == "builder":
                self.builder_config(operation)

    def callback_transfer_plate_to_plate(
            self,
            func_str: str,
            part: str = "first",
            labware_obj=None,
            edit_mode: bool = False,
            **kwargs
    ):
        """
        Handle Transfer Plate to Plate operation.
        Order: Volume -> Source (Plate) -> Destination (Plate)
        Validates: Source count == Destination count
        """
        # --- PART 1: GET VOLUME ---
        if part == "first":
            if not edit_mode:  # Only clear if not explicitly in edit mode
                self.clear_edit_mode()
            self.set_stage("")
            volume = self.ask_volume_dialog(title="Transfer Medium Volume", initial_value=100)
            if volume:
                self.callback_transfer_plate_to_plate(func_str, part="second", volume=volume, **kwargs)


        # --- PART 2: SELECT SOURCE (PLATE) ---
        elif part == "second":
            if self.mode == "builder":
                self.clear_grid(self.second_column_frame)

            self.set_stage("choose plate to aspirate liquid from")
            kwargs['volume'] = kwargs.get('volume')
            self.display_possible_labware(
                labware_type=Plate,
                next_callback=self.callback_transfer_plate_to_plate,
                func_str=func_str,
                part="third",
                **kwargs
            )

        # --- PART 3: HANDLE SOURCE SELECTION & ASK DESTINATION ---
        elif part == "third" and labware_obj is not None:
            # Compute volume constraints for removal (insufficient volume check)
            volume = kwargs.get('volume')
            volume_constraints = self.compute_volume_constraints(
                labware_obj, volume, self.multichannel, operation='removal'
            )

            window = WellWindow(
                rows=labware_obj._rows,
                columns=labware_obj._columns,
                labware_id=labware_obj.labware_id,
                max_selected=None,
                multichannel_mode=self.multichannel,
                master=self.get_master_window(),
                title=f"SOURCE: Select wells on {labware_obj.labware_id}",
                wells_list=self.get_wells_list_from_labware(labware_obj=labware_obj, source=True),
                volume_constraints= volume_constraints if self.mode == "direct" else {}
            )
            self.get_master_window().wait_variable(window.safe_var)

            kwargs["source_labware"] = labware_obj
            if self.multichannel:
                kwargs["source_positions"] = [(c, r) for r, c in window.get_start_positions()]
            else:
                kwargs["source_positions"] = [(c, r) for r, row in enumerate(window.well_state)
                                              for c, v in enumerate(row) if v]
            del window

            if not kwargs["source_positions"]:
                return

            if self.mode == "builder":
                self.clear_grid(self.second_column_frame)

            self.set_stage("choose plate to dispense liquid to")
            self.display_possible_labware(
                labware_type=Plate,
                next_callback=self.callback_transfer_plate_to_plate,
                func_str=func_str,
                part="fourth",
                **kwargs
            )

        # --- PART 4: HANDLE DESTINATION SELECTION & CREATE OPERATION ---
        elif part == "fourth" and labware_obj is not None:
            # Compute volume constraints for addition (overflow check)
            volume = kwargs.get('volume')
            volume_constraints = self.compute_volume_constraints(
                labware_obj, volume, self.multichannel, operation='addition'
            )

            window = WellWindow(
                rows=labware_obj._rows,
                columns=labware_obj._columns,
                labware_id=labware_obj.labware_id,
                max_selected=None,
                multichannel_mode=self.multichannel,
                master=self.get_master_window(),
                title=f"DESTINATION: Select wells on {labware_obj.labware_id}",
                wells_list=self.get_wells_list_from_labware(labware_obj=labware_obj, source=False),
                volume_constraints= volume_constraints if self.mode == "direct" else {}
            )
            self.get_master_window().wait_variable(window.safe_var)

            kwargs["dest_labware"] = labware_obj
            if self.multichannel:
                kwargs["dest_positions"] = [(c, r) for r, c in window.get_start_positions()]
            else:
                kwargs["dest_positions"] = [(c, r) for r, row in enumerate(window.well_state)
                                            for c, v in enumerate(row) if v]
            del window

            if not kwargs["dest_positions"]:
                return

            # Validation check - ensure counts match
            if len(kwargs["source_positions"]) != len(kwargs["dest_positions"]):
                messagebox.showerror(
                    "Selection Error",
                    f"Mismatch in selected positions!\n\n"
                    f"Source Count: {len(kwargs['source_positions'])}\n"
                    f"Destination Count: {len(kwargs['dest_positions'])}\n\n"
                    f"Please ensure counts match.",
                    parent=self.get_master_window()
                )
                return

            # Create Operation object (unified for both modes)
            operation = OperationBuilder.build_transfer_plate_to_plate(
                source_labware_id=kwargs["source_labware"].labware_id,
                source_positions=kwargs["source_positions"],
                dest_labware_id=kwargs["dest_labware"].labware_id,
                dest_positions=kwargs["dest_positions"],
                volume=kwargs['volume'],
                channels=self.channels
            )

            # Mode-specific handling
            if self.mode == "direct":
                self.stage_operation(operation)
            elif self.mode == "builder":
                self.builder_config(operation)

    def callback_remove_and_add(
            self,
            func_str: str,
            part: str = "first",
            labware_obj=None,
            edit_mode: bool = False,
            **kwargs
    ):
        """
        Handle Remove & Add operation (batched).
        1. Select wells on plate
        2. Remove medium to remove reservoir
        3. Add fresh medium from source reservoir
        """
        if part == "first":
            if not edit_mode:
                self.clear_edit_mode()
            self.set_stage("")
            volume = self.ask_volume_dialog(title="Remove & Add Volume", initial_value=100)
            if volume:
                self.callback_remove_and_add(func_str, part="second", volume=volume, **kwargs)

        elif part == "second":
            # Select plate and wells
            if self.mode == "builder":
                self.clear_grid(self.second_column_frame)
            self.set_stage("choose plate and wells to work with")
            kwargs['volume'] = kwargs.get('volume')
            self.display_possible_labware(
                labware_type=Plate,
                next_callback=self.callback_remove_and_add,
                func_str=func_str,
                part="third",
                **kwargs
            )

        elif part == "third" and labware_obj is not None:
            # Select wells on plate
            volume = kwargs.get('volume')
            volume_constraints = self.compute_volume_constraints(
                labware_obj, volume, self.multichannel, operation='removal'
            )

            window = WellWindow(
                rows=labware_obj._rows,
                columns=labware_obj._columns,
                labware_id=labware_obj.labware_id,
                max_selected=None,
                multichannel_mode=self.multichannel,
                master=self.get_master_window(),
                title=f"Select wells on {labware_obj.labware_id}",
                wells_list=self.get_wells_list_from_labware(labware_obj=labware_obj, source=True),
                volume_constraints=volume_constraints if self.mode == "direct" else {}
            )
            self.get_master_window().wait_variable(window.safe_var)

            kwargs["plate_labware"] = labware_obj
            if self.multichannel:
                kwargs["plate_positions"] = [(c, r) for r, c in window.get_start_positions()]
            else:
                kwargs["plate_positions"] = [(c, r) for r, row in enumerate(window.well_state)
                                             for c, v in enumerate(row) if v]
            del window

            if not kwargs["plate_positions"]:
                return

            if self.mode == "builder":
                self.clear_grid(self.second_column_frame)

            # Next: select remove reservoir
            self.set_stage("choose reservoir to remove medium to")
            self.display_possible_labware(
                labware_type=ReservoirHolder,
                next_callback=self.callback_remove_and_add,
                func_str=func_str,
                part="fourth",
                **kwargs
            )

        elif part == "fourth" and labware_obj is not None:
            #Select remove reservoir position
            volume = kwargs.get('volume')
            num_positions = len(kwargs['plate_positions'])
            volume_constraints = self.compute_volume_constraints(
                labware_obj, volume * num_positions, self.multichannel, operation='addition'
            )

            window = WellWindow(
                rows=labware_obj.hooks_across_y,
                columns=labware_obj.hooks_across_x,
                labware_id=labware_obj.labware_id,
                max_selected=1,
                multichannel_mode=False if not labware_obj.each_tip_needs_separate_item() else self.multichannel,
                master=self.get_master_window(),
                title=f"REMOVE TO: Select reservoir {labware_obj.labware_id} (old medium destination)",
                wells_list=self.get_wells_list_from_labware(labware_obj=labware_obj, source=False),
                volume_constraints=volume_constraints if self.mode == "direct" else {}
            )
            self.get_master_window().wait_variable(window.safe_var)

            kwargs["remove_reservoir"] = labware_obj
            selected = [(c, r) for r, row in enumerate(window.well_state) for c, v in enumerate(row) if v]
            kwargs["remove_position"] = selected[0] if selected else None
            del window

            if not kwargs["remove_position"]:
                return

            if self.mode == "builder":
                self.clear_grid(self.second_column_frame)

            # Next: select source reservoir
            self.set_stage("choose reservoir to add fresh medium from")
            self.display_possible_labware(
                labware_type=ReservoirHolder,
                next_callback=self.callback_remove_and_add,
                func_str=func_str,
                part="fifth",
                **kwargs
            )

        elif part == "fifth" and labware_obj is not None:
            # Select source reservoir position
            volume = kwargs.get('volume')
            num_positions = len(kwargs['plate_positions'])
            volume_constraints = self.compute_volume_constraints(
                labware_obj, volume * num_positions, self.multichannel, operation='removal'
            )

            window = WellWindow(
                rows=labware_obj.hooks_across_y,
                columns=labware_obj.hooks_across_x,
                labware_id=labware_obj.labware_id,
                max_selected=1,
                multichannel_mode=False if not labware_obj.each_tip_needs_separate_item() else self.multichannel,
                master=self.get_master_window(),
                title=f"ADD FROM: Select reservoir {labware_obj.labware_id} (fresh medium source)",
                wells_list=self.get_wells_list_from_labware(labware_obj=labware_obj, source=True),
                volume_constraints=volume_constraints if self.mode == "direct" else {}
            )
            self.get_master_window().wait_variable(window.safe_var)

            kwargs["source_reservoir"] = labware_obj
            selected = [(c, r) for r, row in enumerate(window.well_state) for c, v in enumerate(row) if v]
            kwargs["source_position"] = selected[0] if selected else None
            del window

            if not kwargs["source_position"]:
                return

                # BUILD THE OPERATION - THIS WAS MISSING!
            operation = OperationBuilder.build_remove_and_add(
                plate_labware_id=kwargs["plate_labware"].labware_id,
                plate_positions=kwargs["plate_positions"],
                remove_reservoir_id=kwargs["remove_reservoir"].labware_id,
                remove_position=kwargs["remove_position"],
                source_reservoir_id=kwargs["source_reservoir"].labware_id,
                source_position=kwargs["source_position"],
                volume=kwargs['volume'],
                channels=self.channels
            )

            if self.mode == "direct":
                self.stage_operation(operation)
            elif self.mode == "builder":
                self.builder_config(operation)


    def callback_suck(
            self,
            func_str: str,
            part: str = "first",
            labware_obj: Labware = None,
            edit_mode: bool = False,
            **kwargs
    ):
        """Handle Suck operation"""
        # Check for tips in direct mode only (builder mode uses virtual state)
        if part == "first" and self.mode == "direct" and not self.pipettor.has_tips:
            messagebox.showerror("Error", "Pick tips first")
            return

        # --- PART 1: GET VOLUME ---
        if part == "first":
            if not edit_mode:  # Only clear if not explicitly in edit mode
                self.clear_edit_mode()

            self.set_stage("")
            volume = self.ask_volume_dialog(title="Suck Volume", initial_value=100)
            if volume:
                self.callback_suck(func_str, part="second", volume=volume, **kwargs)

        # --- PART 2: SELECT LABWARE ---
        elif part == "second":
            if self.mode == "builder":
                self.clear_grid(self.second_column_frame)

            kwargs['volume'] = kwargs.get('volume')
            self.set_stage("choose reservoir/plate to aspirate liquid from")
            self.display_possible_labware(
                labware_type=(Plate, ReservoirHolder),
                next_callback=self.callback_suck,
                func_str=func_str,
                part="third",
                **kwargs
            )

        # --- PART 3: HANDLE LABWARE SELECTION & CREATE OPERATION ---
        elif part == "third" and labware_obj is not None:
            # Determine dimensions
            if isinstance(labware_obj, ReservoirHolder):
                rows, columns = labware_obj.hooks_across_y, labware_obj.hooks_across_x
            elif isinstance(labware_obj, Plate):
                rows, columns = labware_obj._rows, labware_obj._columns
            else:
                messagebox.showerror("Error", "Invalid labware type for suck operation")
                return

            volume = kwargs.get('volume')

            # Validate volume in direct mode
            if self.mode == "direct":
                if volume > (self.pipettor.tip_volume - self.pipettor.get_total_tip_volume(0)):
                    messagebox.showerror("Error", "Volume too high")
                    return

            is_multichannel = self.multichannel
            total_volume = volume * self.channels

            # Compute volume constraints
            if isinstance(labware_obj, ReservoirHolder):
                volume_constraints = self.compute_volume_constraints(
                    labware_obj, total_volume, is_multichannel=False, operation='removal'
                )
            else:
                volume_constraints = self.compute_volume_constraints(
                    labware_obj, volume, is_multichannel, operation='removal'
                )

            window = WellWindow(
                rows=rows,
                columns=columns,
                labware_id=labware_obj.labware_id,
                max_selected=1,
                master=self.get_master_window(),
                multichannel_mode=False if isinstance(labware_obj, ReservoirHolder) else is_multichannel,
                title=f"Select position to suck from: {labware_obj.labware_id}",
                wells_list=self.get_wells_list_from_labware(
                    labware_obj=labware_obj,
                    source=True,
                ),
                volume_constraints= volume_constraints if self.mode == "direct" else {}
            )
            self.get_master_window().wait_window(window.get_root())

            # Get the single position
            if isinstance(labware_obj, Plate) and is_multichannel:
                start_positions = window.get_start_positions()
                if not start_positions or not window.confirmed:
                    return
                position = (start_positions[0][1], start_positions[0][0])
            else:
                selected = [(c, r) for r, row in enumerate(window.well_state) for c, v in enumerate(row) if v]
                if not selected or not window.confirmed:
                    return
                position = selected[0]

            operation = OperationBuilder.build_suck(
                labware_id=labware_obj.labware_id,
                position=position,
                volume=total_volume,
                channels=self.channels
            )

            if self.mode == "direct":
                self.stage_operation(operation)
            elif self.mode == "builder":
                self.builder_config(operation)

    def callback_spit(
            self,
            func_str: str,
            part: str = "first",
            labware_obj: Labware = None,
            edit_mode: bool = False,
            **kwargs
    ):
        """Handle Spit operation"""
        # Check for tips in direct mode only
        if part == "first" and self.mode == "direct" and not self.pipettor.has_tips:
            messagebox.showerror("Error", "Pick tips first")
            return

        # --- PART 1: GET VOLUME ---
        if part == "first":
            if not edit_mode:  # Only clear if not explicitly in edit mode
                self.clear_edit_mode()
            self.set_stage("")
            volume = self.ask_volume_dialog(title="Spit Volume", initial_value=100)
            if volume:
                self.callback_spit(func_str, part="second", volume=volume, **kwargs)

        # --- PART 2: SELECT LABWARE ---
        elif part == "second":
            if self.mode == "builder":
                self.clear_grid(self.second_column_frame)

            kwargs['volume'] = kwargs.get('volume')
            self.set_stage("choose reservoir/plate to dispense liquid to")
            self.display_possible_labware(
                labware_type=(Plate, ReservoirHolder),
                next_callback=self.callback_spit,
                func_str=func_str,
                part="third",
                **kwargs
            )

        # --- PART 3: HANDLE LABWARE SELECTION & CREATE OPERATION ---
        elif part == "third" and labware_obj is not None:
            # Determine dimensions
            if isinstance(labware_obj, ReservoirHolder):
                rows, columns = labware_obj.hooks_across_y, labware_obj.hooks_across_x
            elif isinstance(labware_obj, Plate):
                rows, columns = labware_obj._rows, labware_obj._columns
            else:
                messagebox.showerror("Error", "Invalid labware type for spit operation")
                return

            volume = kwargs.get('volume')

            # Validate volume in direct mode
            if self.mode == "direct":
                if volume > (self.pipettor.get_total_tip_volume() / self.channels):
                    messagebox.showerror("Error", "Not enough liquid in tip")
                    return

            is_multichannel = self.multichannel
            total_volume = volume * self.channels

            # Compute volume constraints
            if isinstance(labware_obj, ReservoirHolder):
                volume_constraints = self.compute_volume_constraints(
                    labware_obj, total_volume, is_multichannel=False, operation='addition'
                )
            else:
                volume_constraints = self.compute_volume_constraints(
                    labware_obj, volume, is_multichannel, operation='addition'
                )

            window = WellWindow(
                rows=rows,
                columns=columns,
                labware_id=labware_obj.labware_id,
                max_selected=1,
                master=self.get_master_window(),
                multichannel_mode=False if isinstance(labware_obj, ReservoirHolder) else is_multichannel,
                title=f"Select position to spit into: {labware_obj.labware_id}",
                wells_list=self.get_wells_list_from_labware(
                    labware_obj=labware_obj,
                    source=False,
                ),
                volume_constraints= volume_constraints if self.mode == "direct" else {}
            )
            self.get_master_window().wait_window(window.get_root())

            # Get the single position
            if isinstance(labware_obj, Plate) and is_multichannel:
                start_positions = window.get_start_positions()
                if not start_positions or not window.confirmed:
                    return
                position = (start_positions[0][1], start_positions[0][0])
            else:
                selected = [(c, r) for r, row in enumerate(window.well_state) for c, v in enumerate(row) if v]
                if not selected or not window.confirmed:
                    return
                position = selected[0]

            # Create Operation (instead of lambda)
            operation = OperationBuilder.build_spit(
                labware_id=labware_obj.labware_id,
                position=position,
                volume=total_volume,
                channels=self.channels
            )

            # Mode-specific handling
            if self.mode == "direct":
                self.stage_operation(operation)
            elif self.mode == "builder":
                self.builder_config(operation)
    def callback_move_xy(self, func_str: str, edit_mode: bool = False):
        """Handle Move X and Y operation"""

        if not edit_mode:  # Only clear if not explicitly in edit mode
            self.clear_edit_mode()

        # Get current positions from pipettor
        current_x = self.pipettor.x_position if hasattr(self.pipettor, 'x_position') else 0.0
        current_y = self.pipettor.y_position if hasattr(self.pipettor, 'y_position') else 0.0

        xy_result = self.ask_position_dialog([
            ('X', self.deck.range_x[0], self.deck.range_x[1], current_x),
            ('Y', self.deck.range_y[0], self.deck.range_y[1], current_y)
        ])

        if xy_result:
            x_pos, y_pos = xy_result

            operation = OperationBuilder.build_move_xy(x=x_pos, y=y_pos)

            if self.mode == "direct":
                self.stage_operation(operation)
            elif self.mode == "builder":
                self.builder_config(operation)

    def callback_move_z(self, func_str: str, edit_mode: bool = False):
        """Handle Move Z operation"""

        if not edit_mode:
            self.clear_edit_mode()

        # Get current Z position from pipettor
        current_z = self.pipettor.z_position if hasattr(self.pipettor, 'z_position') else 0.0

        z_pos = self.ask_position_dialog([
            ('Z', 0.0, self.deck.range_z, current_z)
        ])

        if z_pos is not None:
            operation = OperationBuilder.build_move_z(z=z_pos)

            if self.mode == "direct":
                self.stage_operation(operation)
            elif self.mode == "builder":
                self.builder_config(operation)

    def callback_home(self, func_str: str, edit_mode: bool = False):
        """Handle Home operation"""
        if not edit_mode:
            self.clear_edit_mode()

        operation = OperationBuilder.build_home()

        if self.mode == "direct":
            self.stage_operation(operation)
        elif self.mode == "builder":
            self.builder_config(operation)
