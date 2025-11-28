import ttkbootstrap as ttk
import tkinter as tk
import uuid
from typing import Callable, Optional
from tkinter import messagebox

from well_window import WellWindow
from deck import Deck
from labware import Labware, PipetteHolder, Plate, TipDropzone, ReservoirHolder
from pipettor_plus import PipettorPlus
from workflow import Workflow, WorkflowState, Operation, OperationType
from workflow_executor import WorkflowExecutor, ExecutionResult, ExecutionStatus
from operation_builder import OperationBuilder
import os


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

        # Workflow state
        if mode == "builder":
            self.workflow = Workflow(name="New Workflow")
            self.workflow_state = WorkflowState(deck)
            self.saved_workflows: dict[str, Workflow] = {}
        else:
            self.workflow = None
            self.workflow_state = None
            self.saved_workflows = {}

        #for direct mode
        self.custom_funcs_dict: dict[str, list[Callable]] = {}
        self.current_func_list: list[Callable] = []
        self.current_func_details: list[str] = []  # For display

        # Staging state (direct mode)
        self.staged_operation: Optional[Callable] = None
        self.staged_operation_name: Optional[str] = None
        self.staged_operation_details: Optional[str] = None

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

    def load_saved_workflows(self) -> None:
        """Load all saved workflows from disk"""
        if not os.path.exists(self.workflows_dir):
            return

        for filename in os.listdir(self.workflows_dir):
            if filename.endswith('.json'):
                try:
                    filepath = os.path.join(self.workflows_dir, filename)
                    workflow = Workflow.load_from_file(filepath)
                    self.saved_workflows[workflow.name] = workflow
                except Exception as e:
                    print(f"Error loading workflow {filename}: {e}")

    def save_workflow_to_disk(self, workflow: Workflow) -> None:
        """Save workflow to disk"""
        filename = f"{workflow.name.replace(' ', '_')}_{workflow.workflow_id[:8]}.json"
        filepath = os.path.join(self.workflows_dir, filename)
        workflow.save_to_file(filepath)

    def delete_workflow_from_disk(self, workflow: Workflow) -> None:
        """Delete workflow file from disk"""
        for filename in os.listdir(self.workflows_dir):
            if workflow.workflow_id in filename:
                filepath = os.path.join(self.workflows_dir, filename)
                os.remove(filepath)
                break

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

        # Top buttons: Create New and Load from File
        top_buttons_frame = ttk.Frame(workflows_frame)
        top_buttons_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Button(
            top_buttons_frame,
            text=" Create New Workflow",
            command=self.open_workflow_builder,
            bootstyle="success"
        ).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)

        ttk.Button(
            top_buttons_frame,
            text=" Load from File",
            command=self.load_workflow_from_file,
            bootstyle="info"
        ).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)

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
            text=" Execute",
            command=self.execute_selected_workflow,
            bootstyle="primary"
        ).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)

        ttk.Button(
            workflow_buttons_frame,
            text=" Save to File",
            command=self.save_selected_workflow_to_file,
            bootstyle="warning"
        ).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)

        ttk.Button(
            workflow_buttons_frame,
            text=" Delete",
            command=self.delete_selected_workflow,
            bootstyle="danger"
        ).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)

        # Initialize with empty workflow dict
        self.workflows_in_memory = {}  # Stores workflows created in this session
        self.refresh_workflows_list()

        # Operation buttons
        self.place_operation_buttons(self.control_frame)
        # Operation buttons
        self.place_operation_buttons(self.control_frame)

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
            text="Execute Now",
            command=self.execute_staged_operation,
            state='disabled',
            bootstyle="success"
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

    def create_builder_mode_ui(self):
        """Create full UI for workflow builder in separate window"""
        # Grid configuration
        self.window_build_func.columnconfigure(0, weight=1)  # Left: buttons
        self.window_build_func.columnconfigure(1, weight=1)  # Middle: selection
        self.window_build_func.columnconfigure(2, weight=1)  # Right: workflow queue

        for i in range(12):
            self.window_build_func.rowconfigure(i, weight=1)

        # Header
        self.label_header = ttk.Label(
            self.window_build_func,
            text="Build Custom Workflow",
            anchor="center",
            font=('Helvetica', 14)
        )
        self.label_header.grid(row=0, column=0, columnspan=3, sticky="nsew", pady=10)

        # Left column: Operation buttons
        button_container = ttk.Frame(self.window_build_func)
        button_container.grid(row=1, column=0, rowspan=10, sticky="nsew", padx=5)
        self.place_operation_buttons(button_container)

        # Middle column: Selection area
        self.second_column_frame = ttk.Frame(self.window_build_func)
        self.second_column_frame.grid(row=1, column=1, rowspan=10, sticky="nsew")
        self.second_column_frame.columnconfigure(0, weight=1)
        for i in range(10):
            self.second_column_frame.rowconfigure(i, weight=1)

        # Right column: Workflow queue
        queue_label = ttk.Label(
            self.window_build_func,
            text="Workflow Queue",
            font=('Helvetica', 14)
        )
        queue_label.grid(row=0, column=2, sticky="ew", padx=10)

        self.third_column_frame = ttk.Frame(self.window_build_func)
        self.third_column_frame.grid(row=1, column=2, rowspan=9, sticky="nsew", padx=5)
        self.third_column_frame.columnconfigure(0, weight=1)
        for i in range(20):
            self.third_column_frame.rowconfigure(i, weight=1)

        # Bottom: Save workflow controls
        self.frame_name = ttk.Frame(self.window_build_func)
        self.frame_name.grid(row=11, column=0, columnspan=3, sticky="nsew", padx=10, pady=5)

        self.frame_name.columnconfigure(0, weight=3)
        self.frame_name.columnconfigure(1, weight=1)
        self.frame_name.columnconfigure(2, weight=1)

        ttk.Label(self.frame_name, text="Workflow Name:", font=('Arial', 11)).grid(
            row=0, column=0, sticky='w', padx=(0, 10)
        )

        self.entry_name = ttk.Entry(self.frame_name)
        self.entry_name.grid(row=1, column=0, sticky="ew", padx=(0, 10))

        self.create_button = ttk.Button(
            self.frame_name,
            text="Create Workflow",
            command=self.callback_create_button,
            bootstyle="success"
        )
        self.create_button.grid(row=1, column=1, sticky="ew", padx=5)

        self.clear_queue_button = ttk.Button(
            self.frame_name,
            text="Clear Queue",
            command=self.clear_workflow_queue,
            bootstyle="danger"
        )
        self.clear_queue_button.grid(row=1, column=2, sticky="ew")
        self.update_operation_button_states()

    def refresh_workflows_list(self):
        """Reload workflows from disk and update listbox"""
        if self.mode != "direct":
            return

        # Reload workflows from disk
        self.saved_workflows = {}
        self.load_saved_workflows()

        # Clear listbox
        self.workflows_listbox.delete(0, tk.END)

        # Populate with workflow names
        if self.saved_workflows:
            for workflow_name in sorted(self.saved_workflows.keys()):
                workflow = self.saved_workflows[workflow_name]
                display_text = f"{workflow_name} ({len(workflow.operations)} ops)"
                self.workflows_listbox.insert(tk.END, display_text)
        else:
            self.workflows_listbox.insert(tk.END, "(No saved workflows)")

    def execute_selected_workflow(self):
        """Execute the workflow selected in the listbox"""
        selection = self.workflows_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a workflow to execute")
            return

        # Get workflow name
        selected_text = self.workflows_listbox.get(selection[0])
        if selected_text == "(No saved workflows)":
            return

        # Extract workflow name (before the " (X ops)" part)
        workflow_name = selected_text.split(" (")[0]
        workflow = self.saved_workflows.get(workflow_name)

        if not workflow:
            messagebox.showerror("Error", f"Workflow '{workflow_name}' not found")
            return

        # Confirm execution
        if not messagebox.askyesno(
                "Execute Workflow",
                f"Execute workflow '{workflow_name}' with {len(workflow.operations)} operations?"
        ):
            return

        # Create progress window
        progress_window = tk.Toplevel(self.get_master_window())
        progress_window.title("Executing Workflow")
        progress_window.geometry("400x200")
        progress_window.transient(self.get_master_window())
        progress_window.grab_set()

        progress_label = ttk.Label(
            progress_window,
            text=f"Executing: {workflow_name}",
            font=("Helvetica", 12, "bold")
        )
        progress_label.pack(pady=10)

        progress_bar = ttk.Progressbar(
            progress_window,
            mode='determinate',
            length=300
        )
        progress_bar.pack(pady=10)

        status_label = ttk.Label(progress_window, text="Starting...")
        status_label.pack(pady=5)

        # Execute
        executor = WorkflowExecutor(self.pipettor, self.deck)

        def on_progress(completed, total):
            progress_bar['value'] = (completed / total) * 100
            status_label.config(text=f"Operation {completed}/{total}")
            progress_window.update()

        executor.on_progress = on_progress

        try:
            result = executor.execute_workflow(workflow)
            progress_window.destroy()

            if result.success:
                messagebox.showinfo(
                    "Success",
                    f"Workflow '{workflow_name}' completed!\n"
                    f"{result.operations_completed} operations executed."
                )

                # Call completion callback if set
                if self.on_operation_complete:
                    self.on_operation_complete()
            else:
                messagebox.showerror(
                    "Workflow Failed",
                    f"Workflow failed at operation {result.failed_operation_index + 1}:\n\n"
                    f"{result.error_message}"
                )
        except Exception as e:
            progress_window.destroy()
            messagebox.showerror("Error", f"Workflow execution failed:\n\n{str(e)}")

    def edit_selected_workflow(self):
        """Open workflow builder to edit the selected workflow"""
        selection = self.workflows_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a workflow to edit")
            return

        # Get workflow name
        selected_text = self.workflows_listbox.get(selection[0])
        if selected_text == "(No saved workflows)":
            return

        workflow_name = selected_text.split(" (")[0]
        workflow = self.saved_workflows.get(workflow_name)

        if not workflow:
            messagebox.showerror("Error", f"Workflow '{workflow_name}' not found")
            return

        # Open workflow builder with this workflow loaded
        builder = FunctionWindow(
            deck=self.deck,
            pipettor=self.pipettor,
            mode="builder",
            master=self.container.winfo_toplevel()
        )

        # Load the workflow into the builder
        builder.workflow = workflow
        builder.entry_name.delete(0, tk.END)
        builder.entry_name.insert(0, workflow.name)

        # Rebuild virtual state
        builder.workflow_state.reset()
        for op in workflow.operations:
            builder.workflow_state.apply_operation(op)

        # Display operations
        builder.display_workflow_queue()
        builder.update_operation_button_states()

    def delete_selected_workflow(self):
        """Delete the selected workflow"""
        selection = self.workflows_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a workflow to delete")
            return

        # Get workflow name
        selected_text = self.workflows_listbox.get(selection[0])
        if selected_text == "(No saved workflows)":
            return

        workflow_name = selected_text.split(" (")[0]
        workflow = self.saved_workflows.get(workflow_name)

        if not workflow:
            messagebox.showerror("Error", f"Workflow '{workflow_name}' not found")
            return

        # Confirm deletion
        if not messagebox.askyesno(
                "Confirm Delete",
                f"Are you sure you want to delete workflow '{workflow_name}'?\n\n"
                f"This action cannot be undone."
        ):
            return

        # Delete from disk
        try:
            self.delete_workflow_from_disk(workflow)

            # Remove from memory
            del self.saved_workflows[workflow_name]

            # Refresh listbox
            self.refresh_workflows_list()

            messagebox.showinfo("Deleted", f"Workflow '{workflow_name}' has been deleted.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete workflow:\n\n{str(e)}")

    def execute_workflow_in_builder(self):
        """Execute the current workflow from builder mode"""
        if not self.workflow or not self.workflow.operations:
            messagebox.showwarning("Empty Workflow", "No operations to execute")
            return

        if not self.pipettor:
            messagebox.showerror("Error", "No pipettor connected")
            return

        # Confirm
        if not messagebox.askyesno(
                "Execute Workflow",
                f"Execute workflow with {len(self.workflow.operations)} operations?"
        ):
            return

        # Create progress window
        progress_window = ttk.Toplevel(self.window_build_func)
        progress_window.title("Executing Workflow")
        progress_window.geometry("400x200")
        progress_window.transient(self.window_build_func)
        progress_window.grab_set()

        progress_label = ttk.Label(
            progress_window,
            text=f"Executing: {self.workflow.name}",
            font=("Helvetica", 12, "bold")
        )
        progress_label.pack(pady=10)

        progress_bar = ttk.Progressbar(
            progress_window,
            mode='determinate',
            length=300
        )
        progress_bar.pack(pady=10)

        status_label = ttk.Label(progress_window, text="Starting...")
        status_label.pack(pady=5)

        # Execute
        executor = WorkflowExecutor(self.pipettor, self.deck)

        def on_progress(completed, total):
            progress_bar['value'] = (completed / total) * 100
            status_label.config(text=f"Operation {completed}/{total}")
            progress_window.update()

        executor.on_progress = on_progress

        try:
            result = executor.execute_workflow(self.workflow)
            progress_window.destroy()

            if result.success:
                messagebox.showinfo(
                    "Success",
                    f"Workflow completed successfully!\\n"
                    f"{result.operations_completed} operations executed."
                )
            else:
                messagebox.showerror(
                    "Workflow Failed",
                    f"Workflow failed at operation {result.failed_operation_index + 1}:\\n\\n"
                    f"{result.error_message}"
                )
        except Exception as e:
            progress_window.destroy()
            messagebox.showerror("Error", f"Workflow execution failed:\\n\\n{str(e)}")

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

        # Low-level Operations
        low_level_frame = ttk.Labelframe(parent_frame, text="Low-Level", padding=10)
        low_level_frame.pack(fill=tk.X, pady=5, padx=5)

        self.suck_btn = ttk.Button(
            low_level_frame, text=" Suck",
            command=lambda: self.callback_suck(func_str="Suck"),
            bootstyle="info"
        )
        self.suck_btn.pack(fill=tk.X, pady=2)

        self.spit_btn = ttk.Button(
            low_level_frame, text=" Spit",
            command=lambda: self.callback_spit(func_str="Spit"),
            bootstyle="info"
        )
        self.spit_btn.pack(fill=tk.X, pady=2)

        # System
        system_frame = ttk.Labelframe(parent_frame, text="System", padding=10)
        system_frame.pack(fill=tk.X, pady=5, padx=5)

        self.home_btn = ttk.Button(
            system_frame, text=" Home",
            command=lambda: self.callback_home(func_str="Home"),
            bootstyle="secondary"
        )
        self.home_btn.pack(fill=tk.X, pady=2)

        self.move_xy_btn = ttk.Button(
            system_frame, text=" Move X, Y",
            command=lambda: self.callback_move_xy(func_str="Move X, Y"),
            bootstyle="secondary"
        )
        self.move_xy_btn.pack(fill=tk.X, pady=2)

        self.move_z_btn = ttk.Button(
            system_frame, text=" Move Z",
            command=lambda: self.callback_move_z(func_str="Move Z"),
            bootstyle="secondary"
        )
        self.move_z_btn.pack(fill=tk.X, pady=2)

    def update_operation_button_states(self):
        """Enable/disable operation buttons based on workflow state"""
        if self.mode != "builder":
            return

        if self.workflow_state.has_tips:
            # Tips attached - DISABLE pick, ENABLE everything else
            self.pick_tips_btn.config(state='disabled')

            self.return_tips_btn.config(state='normal')
            self.replace_tips_btn.config(state='normal')
            self.discard_tips_btn.config(state='normal')
            self.add_medium_btn.config(state='normal')
            self.remove_medium_btn.config(state='normal')
            self.transfer_plate_btn.config(state='normal')
            self.suck_btn.config(state='normal')
            self.spit_btn.config(state='normal')

        else:
            # No tips - ENABLE pick, DISABLE everything else
            self.pick_tips_btn.config(state='normal')
            self.return_tips_btn.config(state='disabled')
            self.replace_tips_btn.config(state='disabled')
            self.discard_tips_btn.config(state='disabled')
            self.add_medium_btn.config(state='disabled')
            self.remove_medium_btn.config(state='disabled')
            self.transfer_plate_btn.config(state='disabled')
            self.suck_btn.config(state='disabled')
            self.spit_btn.config(state='disabled')

    # ========== STAGING OPERATIONS (DIRECT MODE) ==========

    def stage_operation(self, func: Callable, func_str: str, details: str):
        """
        Stage an operation for execution or workflow addition.

        Parameters
        ----------
        func : Callable
            The function to execute
        func_str : str
            Display name
        details : str
            Human-readable description
        """
        self.staged_operation = func
        self.staged_operation_name = func_str
        self.staged_operation_details = details
        self.update_staged_display()

    def update_staged_display(self):
        """Update the staging area display"""
        if self.mode != "direct":
            return

        self.staged_op_text.config(state='normal')
        self.staged_op_text.delete(1.0, tk.END)

        if self.staged_operation is None:
            self.staged_op_text.insert(
                1.0,
                "No operation staged.\n\n"
            )
            self.execute_button.config(state='disabled')
            self.add_to_workflow_button.config(state='disabled')
            self.clear_button.config(state='disabled')
        else:
            # Show operation details
            header = f"OPERATION: {self.staged_operation_name}\n"

            display_text = header + self.staged_operation_details
            self.staged_op_text.insert(1.0, display_text)

            self.execute_button.config(state='normal')
            self.add_to_workflow_button.config(state='normal')
            self.clear_button.config(state='normal')

        self.staged_op_text.config(state='disabled')

    def execute_staged_operation(self):
        """Execute the currently staged operation"""
        if self.staged_operation is None:
            return

        try:
            self.staged_operation()
            messagebox.showinfo(
                "Success",
                f"Operation '{self.staged_operation_name}' completed successfully!"
            )

            if self.on_operation_complete:
                self.on_operation_complete()

            self.clear_staged_operation()
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Operation '{self.staged_operation_name}' failed:\n\n{str(e)}"
            )

    def clear_staged_operation(self):
        """Clear the staging area"""
        self.staged_operation = None
        self.staged_operation_name = None
        self.staged_operation_details = None
        self.update_staged_display()

    # ========== WORKFLOW QUEUE (BUILDER MODE) ==========

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
                text="No operations in queue\\n\\nClick operation buttons to add",
                font=("Helvetica", 12),
                foreground="gray"
            ).pack(pady=20)
            return

        # Display each operation
        for idx, operation in enumerate(self.workflow.operations):
            frame = ttk.Frame(self.third_column_frame)
            frame.grid(row=idx, column=0, sticky="ew", pady=2, padx=5)
            frame.columnconfigure(0, weight=1)

            # Operation label - show type and brief description
            op_text = f"{idx + 1}. {operation.operation_type.value}"
            # Add key parameter info
            if 'labware_id' in operation.parameters:
                op_text += f": {operation.parameters['labware_id']}"

            label = ttk.Label(
                frame,
                text=op_text,
                font=("Helvetica", 11)
            )
            label.grid(row=0, column=0, sticky="w")

            # Remove button
            remove_btn = ttk.Button(
                frame,
                text="🗑",
                width=3,
                command=lambda i=idx: self.remove_operation_from_workflow(i),
                bootstyle="danger-outline"
            )
            remove_btn.grid(row=0, column=1, sticky="e", padx=2)

            # Info button to show full details
            info_btn = ttk.Button(
                frame,
                text="ℹ",
                width=3,
                command=lambda op=operation: self.show_operation_details(op),
                bootstyle="info-outline"
            )
            info_btn.grid(row=0, column=2, sticky="e", padx=2)
        self.update_operation_button_states()

    def remove_operation_from_workflow(self, index: int):
        """Remove operation and rebuild virtual state with detailed error reporting"""
        if 0 <= index < len(self.workflow.operations):
            removed_op = self.workflow.operations[index]
            self.workflow.remove_operation(index)

            # Rebuild virtual state from scratch
            self.workflow_state.reset()

            failed_at_index = None
            error_message = None

            try:
                for i, op in enumerate(self.workflow.operations):
                    try:
                        self.workflow_state.apply_operation(op)
                    except ValueError as e:
                        # Track which operation failed
                        failed_at_index = i
                        error_message = str(e)
                        raise  # Re-raise to exit the loop

                # Success - display updated queue
                self.display_workflow_queue()
                self.update_operation_button_states()

            except ValueError:
                # Build detailed error message
                error_details = f"Removing operation #{index + 1} ({removed_op.operation_type.value}) "
                error_details += f"creates an invalid workflow.\n\n"
                error_details += f"❌ Operation #{failed_at_index + 2} fails:\n"
                error_details += f"   Type: {self.workflow.operations[failed_at_index].operation_type.value}\n"
                error_details += f"   Error: {error_message}\n\n"

                messagebox.showerror(
                    "Invalid Workflow",
                    error_details
                )

                # Restore the operation
                self.workflow.operations.insert(index, removed_op)

                # Rebuild state with restored operation
                self.workflow_state.reset()
                for op in self.workflow.operations:
                    self.workflow_state.apply_operation(op)

                self.display_workflow_queue()
                self.update_operation_button_states()

    def show_operation_details(self, operation: Operation):
        """Show detailed information about an operation"""
        details_window = ttk.Toplevel(self.window_build_func)
        details_window.title(f"Operation Details")
        details_window.geometry("500x400")
        details_window.transient(self.window_build_func)

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

    def remove_from_queue(self, index: int):
        """Remove operation from workflow queue"""
        if 0 <= index < len(self.current_func_list):
            del self.current_func_list[index]
            del self.current_func_details[index]
            self.display_workflow_queue()

    def clear_workflow_queue(self):
        """Clear all operations from queue"""
        if not self.workflow or not self.workflow.operations:
            return

        if messagebox.askyesno("Confirm", "Clear all operations from queue?", default="yes"):
            # Clear workflow operations
            self.workflow.operations.clear()

            # Reset virtual state
            self.workflow_state.reset()

            # Refresh display
            self.display_workflow_queue()
            self.update_operation_button_states()

    def callback_create_button(self):
        """Save workflow to disk and close builder"""
        if not self.workflow or not self.workflow.operations:
            messagebox.showwarning("Empty Workflow", "Please add operations to the workflow first")
            return

        # Get name from entry
        name = self.entry_name.get().strip()
        if not name:
            name = f"Workflow_{uuid.uuid4().hex[:8]}"

        # Update workflow name
        self.workflow.name = name

        # Save to disk
        self.save_workflow_to_disk(self.workflow)

        # Update in-memory cache
        self.saved_workflows[self.workflow.name] = self.workflow

        messagebox.showinfo(
            "Saved",
            f"Workflow '{self.workflow.name}' saved with {len(self.workflow.operations)} operations!\n"
            f"File: saved_workflows/{self.workflow.name.replace(' ', '_')}_{self.workflow.workflow_id[:8]}.json"
        )

        # Close the builder window
        if self.is_toplevel and hasattr(self, 'window_build_func'):
            self.window_build_func.destroy()

    def open_workflow_builder(self):
        """Open workflow builder window from direct mode"""
        FunctionWindow(
            deck=self.deck,
            pipettor=self.pipettor,
            mode="builder",
            master=self.container.winfo_toplevel()
        )

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
            workflow_state: WorkflowState = None
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
        workflow_state : WorkflowState, optional
            If provided, use virtual state instead of actual labware state

        Returns
        -------
        list[tuple[int, int]]
            List of (row, col) positions that are available for selection
        """
        use_virtual = workflow_state is not None

        if isinstance(labware_obj, Plate):
            if use_virtual:
                # Use virtual state
                labware_state = workflow_state.get_labware_state(labware_obj.labware_id)
                if labware_state and labware_state['type'] == 'plate':
                    wells_list = []
                    for well_id, well_state in labware_state['wells'].items():
                        row = well_state['row']
                        col = well_state['column']

                        if source:
                            # Source: need wells with volume > 0
                            total_volume = sum(well_state['content'].values())
                            if total_volume > 0:
                                wells_list.append((row, col))
                        else:
                            # Destination: all wells available (volume check happens elsewhere)
                            wells_list.append((row, col))
                else:
                    wells_list = []
            else:
                # Use actual state
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
            if use_virtual:
                # Use virtual state
                labware_state = workflow_state.get_labware_state(labware_obj.labware_id)
                if labware_state and labware_state['type'] == 'reservoir_holder':
                    wells_list = []
                    for res_id, res_state in labware_state['reservoirs'].items():
                        row = res_state['row']
                        col = res_state['column']
                        wells_list.append((row, col))
                else:
                    wells_list = []
            else:
                # Use actual state - show all reservoirs
                wells_list = []
                for res in labware_obj.get_reservoirs():
                    if res is not None:
                        wells_list.append((res.row, res.column))

        elif isinstance(labware_obj, PipetteHolder):
            if use_virtual:
                # Use virtual state
                labware_state = workflow_state.get_labware_state(labware_obj.labware_id)
                if labware_state and labware_state['type'] == 'pipette_holder':
                    wells_list = []
                    for tip_id, tip_state in labware_state['tips'].items():
                        row = tip_state['row']
                        col = tip_state['column']

                        if source:
                            if tip_state['is_occupied']:
                                wells_list.append((row, col))
                        else:
                            if not tip_state['is_occupied']:
                                wells_list.append((row, col))
                else:
                    wells_list = []
            else:
                # Use actual state
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

    def callback_pick_tips(
            self,
            func_str: str,
            part: str = "first",
            labware_obj: PipetteHolder = None,
            **kwargs
    ):
        """Handle Pick Tips operation"""
        if part == "first":
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
            # Get virtual state if in builder mode
            vf_state = self.workflow_state if self.mode == "builder" else None

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
                    workflow_state=vf_state  # Pass virtual state
                )
            )
            self.get_master_window().wait_window(window.get_root())

            start_positions = window.get_start_positions()
            if not start_positions or not window.confirmed:
                return

            # Convert from (row, col) to (col, row) format for pipettor
            list_col_row = [(c, r) for r, c in start_positions]

            # Create details string
            details = f"Labware: {labware_obj.labware_id}\n"
            details += f"Start positions (col:row): {', '.join([f'({c}:{r})' for c, r in list_col_row[:5]])}"
            if len(list_col_row) > 5:
                details += f"... (+{len(list_col_row) - 5} more)"

            if self.mode == "direct":
                # Direct mode: create lambda for immediate execution
                func = lambda lw=labware_obj, lr=list_col_row: self.pipettor.pick_tips(
                    pipette_holder=lw, list_col_row=lr
                )
                self.stage_operation(func, func_str, details)

            elif self.mode == "builder":
                # Builder mode: create Operation object
                operation = OperationBuilder.build_pick_tips(
                    labware_id=labware_obj.labware_id,
                    positions=list_col_row,
                    channels=self.channels
                )
                self.builder_config(operation)

    def callback_return_tips(
            self,
            func_str: str,
            part: str = "first",
            labware_obj: PipetteHolder = None,
            **kwargs
    ):
        """Handle Return Tips operation"""
        if part == "first":
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
            # Get virtual state if in builder mode
            vf_state = self.workflow_state if self.mode == "builder" else None

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
                    workflow_state=vf_state
                )
            )
            self.get_master_window().wait_window(window.get_root())

            start_positions = window.get_start_positions()
            if not start_positions or not window.confirmed:
                return

            # Convert from (row, col) to (col, row) format for pipettor
            list_col_row = [(c, r) for r, c in start_positions]

            # Create details
            details = f"Labware: {labware_obj.labware_id}\n"
            details += f"Start positions (col:row): {', '.join([f'({c}:{r})' for c, r in list_col_row[:5]])}"
            if len(list_col_row) > 5:
                details += f"... (+{len(list_col_row) - 5} more)"

            if self.mode == "direct":
                # Direct mode: lambda
                func = lambda lw=labware_obj, lr=list_col_row: self.pipettor.return_tips(
                    pipette_holder=lw, list_col_row=lr
                )
                self.stage_operation(func, func_str, details)

            elif self.mode == "builder":

                operation = OperationBuilder.build_return_tips(
                    labware_id=labware_obj.labware_id,
                    positions=list_col_row,
                    channels=self.channels
                )
                self.builder_config(operation)

    def callback_replace_tips(
            self,
            func_str: str,
            part: str = "first",
            labware_obj: PipetteHolder = None,
            **kwargs
    ):
        """Handle Replace Tips operation"""
        if part == "first":
            if self.mode == "builder":
                self.clear_grid(self.second_column_frame)
            self.display_possible_labware(
                labware_type=PipetteHolder,
                next_callback=self.callback_replace_tips,
                func_str=func_str,
                part="second",
                **kwargs
            )

        elif part == "second" and labware_obj is not None:
            # Get virtual state if in builder mode
            vf_state = self.workflow_state if self.mode == "builder" else None

            # ===== STEP 1: Return old tips =====
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
                    workflow_state=vf_state
                )
            )
            self.get_master_window().wait_window(window_return.get_root())

            # Get start positions for return
            start_positions_return = window_return.get_start_positions()
            if not start_positions_return or not window_return.confirmed:
                return

            # Convert to (col, row) format
            list_return = [(c, r) for r, c in start_positions_return]

            # ===== STEP 2: Pick new tips =====
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
                    workflow_state=vf_state
                )
            )
            self.get_master_window().wait_window(window_pick.get_root())

            # Get start positions for pick
            start_positions_pick = window_pick.get_start_positions()
            if not start_positions_pick or not window_pick.confirmed:
                return

            # Convert to (col, row) format
            list_pick = [(c, r) for r, c in start_positions_pick]

            # Create details
            details = f"Labware: {labware_obj.labware_id}\n"
            details += f"Return positions (col:row): {', '.join([f'({c}:{r})' for c, r in list_return[:5]])}"
            if len(list_return) > 5:
                details += f"... (+{len(list_return) - 5} more)"
            details += "\n"
            details += f"Pick positions (col:row): {', '.join([f'({c}:{r})' for c, r in list_pick[:5]])}"
            if len(list_pick) > 5:
                details += f"... (+{len(list_pick) - 5} more)"

            if self.mode == "direct":
                # Direct mode: lambda
                func = lambda lw=labware_obj, lr=list_return, lp=list_pick: self.pipettor.replace_tips(
                    pipette_holder=lw, return_list_col_row=lr, pick_list_col_row=lp
                )
                self.stage_operation(func, func_str, details)

            elif self.mode == "builder":
                # Builder mode: create Operation object
                operation = OperationBuilder.build_replace_tips(
                    return_labware_id=labware_obj.labware_id,
                    return_positions=list_return,
                    pick_labware_id=labware_obj.labware_id,
                    pick_positions=list_pick,
                    channels=self.channels
                )
                self.builder_config(operation)

    def callback_discard_tips(
            self,
            func_str: str,
            part: str = "first",
            labware_obj: TipDropzone = None,
            **kwargs
    ):
        """Handle Discard Tips operation"""
        if part == "first":
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
            details = f"Dropzone: {labware_obj.labware_id}\n"
            details += "Action: Discard all tips"

            if self.mode == "direct":
                # Direct mode: lambda
                func = lambda lw=labware_obj: self.pipettor.discard_tips(lw)
                self.stage_operation(func, func_str, details)

            elif self.mode == "builder":
                # Builder mode: create Operation object
                operation = OperationBuilder.build_discard_tips(
                    labware_id=labware_obj.labware_id,
                )
                self.builder_config(operation)

    def builder_config(self, operation: Operation) -> None:
        # Add the operation to workflow
        self.workflow.add_operation(operation)

        # Update virtual state
        self.workflow_state.apply_operation(operation)

        # Refresh display
        self.display_workflow_queue()
        self.clear_grid(self.second_column_frame)

    def ask_position_dialog(self, axis: str, min_val: float, max_val: float, initial_value: float = 0.0):
        """
        Create a focused dialog for position input.

        Parameters
        ----------
        axis : str
            Axis name ('X', 'Y', or 'Z')
        min_val : float
            Minimum valid position
        max_val : float
            Maximum valid position
        initial_value : float
            Initial value to display

        Returns
        -------
        float or None
            Position entered by user, or None if cancelled
        """
        dialog = tk.Toplevel(self.get_master_window())
        dialog.title(f"Move {axis}")
        dialog.geometry("350x180")
        dialog.resizable(False, False)
        dialog.transient(self.get_master_window())
        dialog.grab_set()

        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (350 // 2)
        y = (dialog.winfo_screenheight() // 2) - (180 // 2)
        dialog.geometry(f"350x180+{x}+{y}")

        result = {'position': None}

        # Main frame with padding
        main_frame = ttk.Frame(dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Label with range info
        label_text = f"{axis} Position (mm):"
        ttk.Label(
            main_frame,
            text=label_text,
            font=('Arial', 11, 'bold')
        ).pack(pady=(0, 5))

        # Range info
        range_text = f"Valid range: {min_val} to {max_val} mm"
        if axis == 'Z':
            range_text += "\n(0 = home/top position)"

        ttk.Label(
            main_frame,
            text=range_text,
            font=('Arial', 9),
            foreground='gray'
        ).pack(pady=(0, 10))

        # Entry
        position_var = tk.StringVar(value=str(initial_value))
        entry = ttk.Entry(main_frame, textvariable=position_var, font=('Arial', 12), justify='center')
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
                pos = float(position_var.get())
                if not (min_val <= pos <= max_val):
                    messagebox.showerror(
                        "Invalid Input",
                        f"{axis} position must be between {min_val} and {max_val} mm",
                        parent=dialog
                    )
                    return
                result['position'] = pos
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
        return result['position']

    def ask_volume_dialog(self, title="Enter Volume", initial_value=000):
        """
        Create a simple, focused dialog for volume input.

        Returns
        -------
        float or None
            Volume entered by user, or None if cancelled
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

        result = {'volume': None}

        # Main frame with padding
        main_frame = ttk.Frame(dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Label
        ttk.Label(
            main_frame,
            text="Volume per well (ul):",
            font=('Arial', 11)
        ).pack(pady=(0, 10))

        # Entry
        volume_var = tk.StringVar(value=str(initial_value))
        entry = ttk.Entry(main_frame, textvariable=volume_var, font=('Arial', 12), justify='center')
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
                vol = float(volume_var.get())
                if vol <= 0:
                    messagebox.showerror("Invalid Input", "Volume must be greater than 0", parent=dialog)
                    return
                result['volume'] = vol
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
        return result['volume']

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
            print(f"{labware_obj} multichannel mode turned off")

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

                if is_multichannel:
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
                else:
                    # For single channel, simply check if well meets constraint
                    if has_constraint:
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

    def callback_add_medium(
            self,
            func_str: str,
            part: str = "first",
            labware_obj=None,
            **kwargs
    ):
        """
        Handle Add Medium operation.
        Order: Volume -> Destination (Plate) -> Source (Reservoir)
        """
        # --- PART 1: GET VOLUME ---
        if part == "first":
            if self.mode == "builder":
                self.clear_grid(self.second_column_frame)
                label = ttk.Label(self.second_column_frame, text="Step 1: Enter Volume (ul)")
                label.grid(column=0, row=0, sticky="nsew", pady=5, padx=5)
                text_var = ttk.StringVar(value="100")
                entry = ttk.Entry(self.second_column_frame, textvariable=text_var)
                entry.grid(row=1, column=0, sticky="nsew", pady=5, padx=5)

                def next_step():
                    try:
                        vol = float(text_var.get())
                        if vol <= 0: raise ValueError
                        self.callback_add_medium(func_str, part="second", volume=vol, **kwargs)
                    except ValueError:
                        messagebox.showerror("Error", "Invalid volume")

                ttk.Button(self.second_column_frame, text="Next", command=next_step).grid(row=2, column=0,
                                                                                          sticky="nsew", pady=5, padx=5)

            else:  # Direct mode - USE NEW DIALOG
                volume = self.ask_volume_dialog(title="Add Medium Volume", initial_value=100)
                if volume:
                    self.callback_add_medium(func_str, part="second", volume=volume, **kwargs)

        # --- PART 2: SELECT DESTINATION (PLATE) ---
        elif part == "second":
            if self.mode == "builder": self.clear_grid(self.second_column_frame)

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
                volume_constraints=volume_constraints
            )
            self.get_master_window().wait_variable(window.safe_var)

            kwargs["dest_labware"] = labware_obj
            if self.multichannel:
                kwargs["dest_positions"] = [(c, r) for r, c in window.get_start_positions()]
            else:
                kwargs["dest_positions"] = [(c, r) for r, row in enumerate(window.well_state) for c, v in enumerate(row)
                                            if v]
            del window

            if not kwargs["dest_positions"]: return

            if self.mode == "builder": self.clear_grid(self.second_column_frame)

            self.display_possible_labware(
                labware_type=ReservoirHolder,
                next_callback=self.callback_add_medium,
                func_str=func_str,
                part="fourth",
                **kwargs
            )

        # --- PART 4: HANDLE RESERVOIR SELECTION & EXECUTE ---
        elif part == "fourth" and labware_obj is not None:
            # Compute volume constraints for source reservoir (insufficient volume check)
            volume = kwargs.get('volume')
            num_dest_positions = len(kwargs['dest_positions'])
            total_wells = num_dest_positions * self.channels
            volume_constraints = self.compute_volume_constraints(
                labware_obj, volume * total_wells, self.multichannel, operation='removal'
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
                volume_constraints=volume_constraints
            )
            self.get_master_window().wait_variable(window.safe_var)

            kwargs["source_labware"] = labware_obj
            selected = [(c, r) for r, row in enumerate(window.well_state) for c, v in enumerate(row) if v]
            kwargs["source_positions"] = selected[0] if selected else None
            del window

            if not kwargs["source_positions"]: return

            volume = kwargs['volume']
            num_positions = len(kwargs['dest_positions'])
            total_wells = num_positions * self.channels
            total_vol = volume * total_wells

            func = lambda kwargs=kwargs, vol=volume: self.pipettor.add_medium(
                source=kwargs["source_labware"],
                source_col_row=kwargs["source_positions"],
                destination=kwargs["dest_labware"],
                dest_col_row=kwargs["dest_positions"],
                volume_per_well=vol
            )

            if self.mode == "builder":
                self.add_current_function(func_str=func_str, func=func, labware_id=kwargs["dest_labware"].labware_id)
                self.clear_grid(self.second_column_frame)
            else:
                details = f"Source: {kwargs['source_labware'].labware_id}\n  Reservoir: {kwargs['source_positions']}\n"
                details += f"Destination: {kwargs['dest_labware'].labware_id}\n"
                details += f"  Columns: {kwargs['dest_positions']}\n" if self.multichannel else f"  Wells: {kwargs['dest_positions']}\n"
                details += f"  Total Wells: {total_wells}\nVolume: {volume} ul per well\nTotal Volume: {total_vol} ul"
                self.stage_operation(func, func_str, details)

    def callback_remove_medium(
            self,
            func_str: str,
            part: str = "first",
            labware_obj=None,
            **kwargs
    ):
        """
        Handle Remove Medium operation.
        Order: Volume -> Source (Plate) -> Destination (Reservoir)
        """
        # --- PART 1: GET VOLUME ---
        if part == "first":
            if self.mode == "builder":
                self.clear_grid(self.second_column_frame)
                label = ttk.Label(self.second_column_frame, text="Step 1: Enter Volume (ul)")
                label.grid(column=0, row=0, sticky="nsew", pady=5, padx=5)
                text_var = ttk.StringVar(value="100")
                entry = ttk.Entry(self.second_column_frame, textvariable=text_var)
                entry.grid(row=1, column=0, sticky="nsew", pady=5, padx=5)

                def next_step():
                    try:
                        vol = float(text_var.get())
                        if vol <= 0: raise ValueError
                        self.callback_remove_medium(func_str, part="second", volume=vol, **kwargs)
                    except ValueError:
                        messagebox.showerror("Error", "Invalid volume")

                ttk.Button(self.second_column_frame, text="Next", command=next_step).grid(row=2, column=0,
                                                                                          sticky="nsew", pady=5, padx=5)

            else:  # Direct mode - USE NEW DIALOG
                volume = self.ask_volume_dialog(title="Remove Medium Volume", initial_value=100)
                if volume:
                    self.callback_remove_medium(func_str, part="second", volume=volume, **kwargs)

        # --- PART 2: SELECT SOURCE (PLATE) ---
        elif part == "second":
            if self.mode == "builder": self.clear_grid(self.second_column_frame)

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
                volume_constraints=volume_constraints
            )
            self.get_master_window().wait_variable(window.safe_var)

            kwargs["source_labware"] = labware_obj
            if self.multichannel:
                kwargs["source_positions"] = [(c, r) for r, c in window.get_start_positions()]
            else:
                kwargs["source_positions"] = [(c, r) for r, row in enumerate(window.well_state) for c, v in
                                              enumerate(row) if v]
            del window

            if not kwargs["source_positions"]: return

            if self.mode == "builder": self.clear_grid(self.second_column_frame)

            self.display_possible_labware(
                labware_type=ReservoirHolder,
                next_callback=self.callback_remove_medium,
                func_str=func_str,
                part="fourth",
                **kwargs
            )

        # --- PART 4: HANDLE RESERVOIR SELECTION & EXECUTE ---
        elif part == "fourth" and labware_obj is not None:
            # Compute volume constraints for reservoir (overflow check)
            volume = kwargs.get('volume')
            num_source_positions = len(kwargs['source_positions'])
            total_wells = num_source_positions * self.channels
            volume_constraints = self.compute_volume_constraints(
                labware_obj, volume * total_wells, self.multichannel, operation='addition'
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
                volume_constraints=volume_constraints
            )
            self.get_master_window().wait_variable(window.safe_var)

            kwargs["dest_labware"] = labware_obj
            selected = [(c, r) for r, row in enumerate(window.well_state) for c, v in enumerate(row) if v]
            kwargs["dest_positions"] = selected[0] if selected else None
            del window

            if not kwargs["dest_positions"]: return

            volume = kwargs['volume']
            num_positions = len(kwargs['source_positions'])
            total_wells = num_positions * self.channels
            total_vol = volume * total_wells

            func = lambda kwargs=kwargs, vol=volume: self.pipettor.remove_medium(
                source=kwargs["source_labware"],
                destination=kwargs["dest_labware"],
                source_col_row=kwargs["source_positions"],
                destination_col_row=kwargs["dest_positions"],
                volume_per_well=vol
            )

            if self.mode == "builder":
                self.add_current_function(func_str=func_str, func=func, labware_id=kwargs["dest_labware"].labware_id)
                self.clear_grid(self.second_column_frame)
            else:
                details = f"Source: {kwargs['source_labware'].labware_id}\n"
                details += f"  Columns: {kwargs['source_positions']}\n" if self.multichannel else f"  Wells: {kwargs['source_positions']}\n"
                details += f"Destination: {kwargs['dest_labware'].labware_id}\n  Reservoir: {kwargs['dest_positions']}\n"
                details += f"  Total Wells: {total_wells}\nVolume: {volume} ul per well\nTotal Volume: {total_vol} ul"
                self.stage_operation(func, func_str, details)

    def callback_transfer_plate_to_plate(
            self,
            func_str: str,
            part: str = "first",
            labware_obj=None,
            **kwargs
    ):
        """
        Handle Transfer Plate to Plate operation.
        Order: Volume -> Source (Plate) -> Destination (Plate)
        Validates: Source count == Destination count
        """
        # --- PART 1: GET VOLUME ---
        if part == "first":
            if self.mode == "builder":
                self.clear_grid(self.second_column_frame)
                label = ttk.Label(self.second_column_frame, text="Step 1: Enter Volume (ul)")
                label.grid(column=0, row=0, sticky="nsew", pady=5, padx=5)
                text_var = ttk.StringVar(value="100")
                entry = ttk.Entry(self.second_column_frame, textvariable=text_var)
                entry.grid(row=1, column=0, sticky="nsew", pady=5, padx=5)

                def next_step():
                    try:
                        vol = float(text_var.get())
                        if vol <= 0: raise ValueError
                        self.callback_transfer_plate_to_plate(func_str, part="second", volume=vol, **kwargs)
                    except ValueError:
                        messagebox.showerror("Error", "Invalid volume")

                ttk.Button(self.second_column_frame, text="Next", command=next_step).grid(row=2, column=0,
                                                                                          sticky="nsew", pady=5, padx=5)

            else:  # Direct mode - USE NEW DIALOG
                volume = self.ask_volume_dialog(title="Transfer Volume", initial_value=100)
                if volume:
                    self.callback_transfer_plate_to_plate(func_str, part="second", volume=volume, **kwargs)

        # --- PART 2: SELECT SOURCE (PLATE) ---
        elif part == "second":
            if self.mode == "builder": self.clear_grid(self.second_column_frame)

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
                volume_constraints=volume_constraints
            )
            self.get_master_window().wait_variable(window.safe_var)

            kwargs["source_labware"] = labware_obj
            if self.multichannel:
                kwargs["source_positions"] = [(c, r) for r, c in window.get_start_positions()]
            else:
                kwargs["source_positions"] = [(c, r) for r, row in enumerate(window.well_state) for c, v in
                                              enumerate(row) if v]
            del window

            if not kwargs["source_positions"]: return

            if self.mode == "builder": self.clear_grid(self.second_column_frame)

            self.display_possible_labware(
                labware_type=Plate,
                next_callback=self.callback_transfer_plate_to_plate,
                func_str=func_str,
                part="fourth",
                **kwargs
            )

        # --- PART 4: HANDLE DESTINATION SELECTION & EXECUTE ---
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
                volume_constraints=volume_constraints
            )
            self.get_master_window().wait_variable(window.safe_var)

            kwargs["dest_labware"] = labware_obj
            if self.multichannel:
                kwargs["dest_positions"] = [(c, r) for r, c in window.get_start_positions()]
            else:
                kwargs["dest_positions"] = [(c, r) for r, row in enumerate(window.well_state) for c, v in enumerate(row)
                                            if v]
            del window

            if not kwargs["dest_positions"]: return

            # Validation check
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

            volume = kwargs['volume']
            num_positions = len(kwargs['dest_positions'])
            total_wells = num_positions * self.channels
            total_vol = volume * total_wells

            func = lambda kwargs=kwargs, vol=volume: self.pipettor.transfer_plate_to_plate(
                source=kwargs["source_labware"],
                source_col_row=kwargs["source_positions"],
                destination=kwargs["dest_labware"],
                dest_col_row=kwargs["dest_positions"],
                volume_per_well=vol
            )

            if self.mode == "builder":
                self.add_current_function(func_str=func_str, func=func, labware_id=kwargs["dest_labware"].labware_id)
                self.clear_grid(self.second_column_frame)
            else:
                details = f"Source: {kwargs['source_labware'].labware_id}\n"
                details += f"  Columns: {kwargs['source_positions']}\n" if self.multichannel else f"  Wells: {kwargs['source_positions']}\n"
                details += f"Destination: {kwargs['dest_labware'].labware_id}\n"
                details += f"  Columns: {kwargs['dest_positions']}\n" if self.multichannel else f"  Wells: {kwargs['dest_positions']}\n"
                details += f"  Total Wells: {total_wells}\nVolume: {volume} ul per well\nTotal Volume: {total_vol} ul"
                self.stage_operation(func, func_str, details)

    def callback_suck(
            self,
            func_str: str,
            part: str = "first",
            labware_obj: Labware = None,
            **kwargs
    ):
        """Handle Suck operation"""

        if part == "first" and not self.pipettor.has_tips:
            messagebox.showerror("Error", "Pick tips first")
            return

        # --- PART 1: GET VOLUME ---
        if part == "first":
            if self.mode == "builder":
                self.clear_grid(self.second_column_frame)
                label = ttk.Label(self.second_column_frame, text="Step 1: Enter Volume (ul)")
                label.grid(column=0, row=0, sticky="nsew", pady=5, padx=5)
                text_var = ttk.StringVar(value="100")
                entry = ttk.Entry(self.second_column_frame, textvariable=text_var)
                entry.grid(row=1, column=0, sticky="nsew", pady=5, padx=5)

                def next_step():
                    try:
                        vol = float(text_var.get())
                        if vol <= 0: raise ValueError
                        self.callback_suck(func_str, part="second", volume=vol, **kwargs)
                    except ValueError:
                        messagebox.showerror("Error", "Invalid volume")

                ttk.Button(self.second_column_frame, text="Next", command=next_step).grid(
                    row=2, column=0, sticky="nsew", pady=5, padx=5
                )

            else:  # Direct mode
                volume = self.ask_volume_dialog(title="Suck Volume", initial_value=100)
                if volume:
                    self.callback_suck(func_str, part="second", volume=volume, **kwargs)

        # --- PART 2: SELECT LABWARE ---
        elif part == "second":
            if self.mode == "builder":
                self.clear_grid(self.second_column_frame)

            kwargs['volume'] = kwargs.get('volume')
            self.display_possible_labware(
                labware_type=(Plate, ReservoirHolder),
                next_callback=self.callback_suck,
                func_str=func_str,
                part="third",
                **kwargs
            )

        # --- PART 3: HANDLE LABWARE SELECTION & EXECUTE ---
        elif part == "third" and labware_obj is not None:
            # Determine dimensions
            if isinstance(labware_obj, ReservoirHolder):
                rows, columns = labware_obj.hooks_across_y, labware_obj.hooks_across_x
            elif isinstance(labware_obj, Plate):
                rows, columns = labware_obj._rows, labware_obj._columns
            else:
                messagebox.showerror("Error", "Invalid labware type for suck operation")
                return

            # Compute volume constraints for removal (insufficient volume check)
            volume = kwargs.get('volume')

            if volume > (self.pipettor.tip_volume - (self.pipettor.get_total_tip_volume()/self.channels)):
                messagebox.showerror("Error", "Volume too high")
                return

            total_volume = volume * self.channels

            volume_constraints = self.compute_volume_constraints(
                labware_obj, volume, self.multichannel, operation='removal'
            )

            window = WellWindow(
                rows=rows,
                columns=columns,
                labware_id=labware_obj.labware_id,
                max_selected=1,  # Only ONE position allowed
                master=self.get_master_window(),
                multichannel_mode=False if not labware_obj.each_tip_needs_separate_item() else self.multichannel,
                title=f"Select position to suck from: {labware_obj.labware_id}",
                wells_list=self.get_wells_list_from_labware(labware_obj=labware_obj, source=True),
                volume_constraints=volume_constraints
            )
            self.get_master_window().wait_window(window.get_root())

            # Get the single position
            if isinstance(labware_obj, Plate) and self.multichannel:
                # For multichannel plate operations
                start_positions = window.get_start_positions()
                if not start_positions:
                    return
                position = (start_positions[0][1], start_positions[0][0])  # Convert (row, col) to (col, row)
            else:
                # For single-channel or reservoir operations
                selected = [(c, r) for r, row in enumerate(window.well_state) for c, v in enumerate(row) if v]
                if not selected:
                    return
                position = selected[0]

            # Create function, volume is total_volume according to definition of suck in pipettor_plus
            func = lambda lw=labware_obj, pos=position, vol=total_volume: self.pipettor.suck(
                source=lw,
                source_col_row=pos,
                volume=vol
            )

            # Create details
            details = f"Labware: {labware_obj.labware_id}\n"
            details += f"Position (Col:Row): {position}\n"
            details += f"Total Volume: {total_volume} ul"
            if self.multichannel and isinstance(labware_obj, Plate):
                details += f"\nVolume per tip: {volume} ul"

            if self.mode == "direct":
                self.stage_operation(func, func_str, details)
            elif self.mode == "builder":
                self.add_current_function(func_str=func_str, func=func, labware_id=labware_obj.labware_id)

    def callback_spit(
            self,
            func_str: str,
            part: str = "first",
            labware_obj: Labware = None,
            **kwargs
    ):

        """Handle Spit operation"""

        if part == "first" and not self.pipettor.has_tips:
            messagebox.showerror("Error", "Pick tips first")
            return

        # --- PART 1: GET VOLUME ---
        if part == "first":
            if self.mode == "builder":
                self.clear_grid(self.second_column_frame)
                label = ttk.Label(self.second_column_frame, text="Step 1: Enter Volume (ul)")
                label.grid(column=0, row=0, sticky="nsew", pady=5, padx=5)
                text_var = ttk.StringVar(value="100")
                entry = ttk.Entry(self.second_column_frame, textvariable=text_var)
                entry.grid(row=1, column=0, sticky="nsew", pady=5, padx=5)

                def next_step():
                    try:
                        vol = float(text_var.get())
                        if vol <= 0: raise ValueError
                        self.callback_spit(func_str, part="second", volume=vol, **kwargs)
                    except ValueError:
                        messagebox.showerror("Error", "Invalid volume")

                ttk.Button(self.second_column_frame, text="Next", command=next_step).grid(
                    row=2, column=0, sticky="nsew", pady=5, padx=5
                )

            else:  # Direct mode
                volume = self.ask_volume_dialog(title="Spit Volume", initial_value=100)
                if volume:
                    self.callback_spit(func_str, part="second", volume=volume, **kwargs)

        # --- PART 2: SELECT LABWARE ---
        elif part == "second":
            if self.mode == "builder":
                self.clear_grid(self.second_column_frame)

            kwargs['volume'] = kwargs.get('volume')
            self.display_possible_labware(
                labware_type=(Plate, ReservoirHolder),
                next_callback=self.callback_spit,
                func_str=func_str,
                part="third",
                **kwargs
            )

        # --- PART 3: HANDLE LABWARE SELECTION & EXECUTE ---
        elif part == "third" and labware_obj is not None:
            # Determine dimensions
            if isinstance(labware_obj, ReservoirHolder):
                rows, columns = labware_obj.hooks_across_y, labware_obj.hooks_across_x
            elif isinstance(labware_obj, Plate):
                rows, columns = labware_obj._rows, labware_obj._columns
            else:
                messagebox.showerror("Error", "Invalid labware type for spit operation")
                return

            # Compute volume constraints for addition (overflow check)
            volume = kwargs.get('volume')
            if volume > (self.pipettor.get_total_tip_volume()/self.channels):
                messagebox.showerror("Error", "Not enough liquid in tip")
                return

            total_volume = volume * self.channels

            volume_constraints = self.compute_volume_constraints(
                labware_obj, volume, self.multichannel, operation='addition'
            )

            window = WellWindow(
                rows=rows,
                columns=columns,
                labware_id=labware_obj.labware_id,
                max_selected=1,  # Only ONE position allowed
                master=self.get_master_window(),
                multichannel_mode=False if not labware_obj.each_tip_needs_separate_item() else self.multichannel,
                # Multichannel only for Plate
                title=f"Select position to spit into: {labware_obj.labware_id}",
                wells_list=self.get_wells_list_from_labware(labware_obj=labware_obj, source=False),
                volume_constraints=volume_constraints
            )
            self.get_master_window().wait_window(window.get_root())

            # Get the single position
            if isinstance(labware_obj, Plate) and self.multichannel:
                # For multichannel plate operations
                start_positions = window.get_start_positions()
                if not start_positions:
                    return
                position = (start_positions[0][1], start_positions[0][0])  # Convert (row, col) to (col, row)
            else:
                # For single-channel or reservoir operations
                selected = [(c, r) for r, row in enumerate(window.well_state) for c, v in enumerate(row) if v]
                if not selected:
                    return
                position = selected[0]

            # Create function
            func = lambda lw=labware_obj, pos=position, vol=total_volume: self.pipettor.spit(
                destination=lw,
                dest_col_row=pos,
                volume=vol
            )

            # Create details
            details = f"Labware: {labware_obj.labware_id}\n"
            details += f"Position (Col:Row): {position}\n"
            details += f"Total Volume: {total_volume} ul"
            if self.multichannel and isinstance(labware_obj, Plate):
                details += f"\nVolume per tip: {volume} ul"

            if self.mode == "direct":
                self.stage_operation(func, func_str, details)
            elif self.mode == "builder":
                self.add_current_function(func_str=func_str, func=func, labware_id=labware_obj.labware_id)

    def callback_move_xy(self, func_str: str):
        """Handle Move X and Y operation"""
        if self.mode == "builder":
            self.clear_grid(self.second_column_frame)

            # Create input UI for X position
            x_label = ttk.Label(
                self.second_column_frame,
                text="Enter X Position (mm):",
                font=('Arial', 11, 'bold')
            )
            x_label.grid(column=0, row=0, sticky="nsew", pady=5, padx=5)

            # X Range info
            x_info_label = ttk.Label(
                self.second_column_frame,
                text=f"Valid range: {self.deck.range_x[0]} to {self.deck.range_x[1]} mm",
                font=('Arial', 9),
                foreground='gray'
            )
            x_info_label.grid(row=1, column=0, sticky="nsew", pady=2, padx=5)

            x_text_var = ttk.StringVar(value="0.0")
            x_entry = ttk.Entry(self.second_column_frame, textvariable=x_text_var, font=('Arial', 12))
            x_entry.grid(row=2, column=0, sticky="nsew", pady=5, padx=5)

            # Create input UI for Y position
            y_label = ttk.Label(
                self.second_column_frame,
                text="Enter Y Position (mm):",
                font=('Arial', 11, 'bold')
            )
            y_label.grid(column=0, row=3, sticky="nsew", pady=(15, 5), padx=5)

            # Y Range info
            y_info_label = ttk.Label(
                self.second_column_frame,
                text=f"Valid range: {self.deck.range_y[0]} to {self.deck.range_y[1]} mm",
                font=('Arial', 9),
                foreground='gray'
            )
            y_info_label.grid(row=4, column=0, sticky="nsew", pady=2, padx=5)

            y_text_var = ttk.StringVar(value="0.0")
            y_entry = ttk.Entry(self.second_column_frame, textvariable=y_text_var, font=('Arial', 12))
            y_entry.grid(row=5, column=0, sticky="nsew", pady=5, padx=5)

            def confirm_movement():
                try:
                    x_pos = float(x_text_var.get())
                    y_pos = float(y_text_var.get())

                    # Validate X range
                    if not (self.deck.range_x[0] <= x_pos <= self.deck.range_x[1]):
                        messagebox.showerror(
                            "Invalid Position",
                            f"X position must be between {self.deck.range_x[0]} and {self.deck.range_x[1]} mm"
                        )
                        return

                    # Validate Y range
                    if not (self.deck.range_y[0] <= y_pos <= self.deck.range_y[1]):
                        messagebox.showerror(
                            "Invalid Position",
                            f"Y position must be between {self.deck.range_y[0]} and {self.deck.range_y[1]} mm"
                        )
                        return

                    func = lambda x=x_pos, y=y_pos: self.pipettor.move_xy(x, y)
                    self.add_current_function(func_str=func_str, func=func, labware_id=f"X={x_pos}mm, Y={y_pos}mm")
                    self.clear_grid(self.second_column_frame)

                except ValueError:
                    messagebox.showerror("Error", "Invalid position value")

            ttk.Button(
                self.second_column_frame,
                text="Confirm",
                command=confirm_movement,
                bootstyle="success"
            ).grid(row=6, column=0, sticky="nsew", pady=(10, 5), padx=5)

        else:  # Direct mode - USE CUSTOM DIALOG
            x_pos, y_pos = self.ask_xy_position_dialog(
                x_min=self.deck.range_x[0],
                x_max=self.deck.range_x[1],
                y_min=self.deck.range_y[0],
                y_max=self.deck.range_y[1],
                x_initial=0.0,
                y_initial=0.0
            )

            if x_pos is not None and y_pos is not None:
                func = lambda x=x_pos, y=y_pos: self.pipettor.move_xy(x, y)
                details = f"Move to X: {x_pos} mm, Y: {y_pos} mm\n"
                details += f"X Range: {self.deck.range_x[0]} to {self.deck.range_x[1]} mm\n"
                details += f"Y Range: {self.deck.range_y[0]} to {self.deck.range_y[1]} mm"
                self.stage_operation(func, func_str, details)

    def ask_xy_position_dialog(self, x_min, x_max, y_min, y_max, x_initial=0.0, y_initial=0.0):
        """Show dialog to get both X and Y positions"""
        dialog = tk.Toplevel(self.get_master_window())
        dialog.title("Move X & Y Position")
        dialog.geometry("400x350")
        dialog.transient(self.get_master_window())
        dialog.grab_set()

        result = {'x': None, 'y': None}

        # X Position section
        ttk.Label(dialog, text="X Position (mm):", font=('Arial', 11, 'bold')).pack(pady=(20, 5))
        ttk.Label(dialog, text=f"Range: {x_min} to {x_max} mm", font=('Arial', 9), foreground='gray').pack()

        x_var = tk.StringVar(value=str(x_initial))
        x_entry = ttk.Entry(dialog, textvariable=x_var, font=('Arial', 12), width=20)
        x_entry.pack(pady=5)

        # Y Position section
        ttk.Label(dialog, text="Y Position (mm):", font=('Arial', 11, 'bold')).pack(pady=(20, 5))
        ttk.Label(dialog, text=f"Range: {y_min} to {y_max} mm", font=('Arial', 9), foreground='gray').pack()

        y_var = tk.StringVar(value=str(y_initial))
        y_entry = ttk.Entry(dialog, textvariable=y_var, font=('Arial', 12), width=20)
        y_entry.pack(pady=5)

        def on_ok():
            try:
                x_val = float(x_var.get())
                y_val = float(y_var.get())

                if not (x_min <= x_val <= x_max):
                    messagebox.showerror("Invalid Input", f"X position must be between {x_min} and {x_max} mm")
                    return

                if not (y_min <= y_val <= y_max):
                    messagebox.showerror("Invalid Input", f"Y position must be between {y_min} and {y_max} mm")
                    return

                result['x'] = x_val
                result['y'] = y_val
                dialog.destroy()
            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter valid numeric values")

        def on_cancel():
            dialog.destroy()

        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=20)

        ttk.Button(button_frame, text="OK", command=on_ok, bootstyle="success", width=10).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Cancel", command=on_cancel, bootstyle="secondary", width=10).pack(side='left',
                                                                                                         padx=5)

        dialog.wait_window()
        return result['x'], result['y']

    def callback_move_z(self, func_str: str):
        """Handle Move Z operation"""
        if self.mode == "builder":
            self.clear_grid(self.second_column_frame)

            # Create input UI
            label = ttk.Label(
                self.second_column_frame,
                text="Enter Z Position (mm):",
                font=('Arial', 11, 'bold')
            )
            label.grid(column=0, row=0, sticky="nsew", pady=5, padx=5)

            # Range info with Z-specific note
            info_label = ttk.Label(
                self.second_column_frame,
                text=f"Valid range: 0 to {self.deck.range_z} mm\n(0 = home/top position)",
                font=('Arial', 9),
                foreground='gray'
            )
            info_label.grid(row=1, column=0, sticky="nsew", pady=2, padx=5)

            text_var = ttk.StringVar(value="0.0")
            entry = ttk.Entry(self.second_column_frame, textvariable=text_var, font=('Arial', 12))
            entry.grid(row=2, column=0, sticky="nsew", pady=5, padx=5)

            def confirm_movement():
                try:
                    z_pos = float(text_var.get())

                    # Validate range
                    if not (0 <= z_pos <= self.deck.range_z):
                        messagebox.showerror(
                            "Invalid Position",
                            f"Z position must be between 0 and {self.deck.range_z} mm"
                        )
                        return

                    func = lambda z=z_pos: self.pipettor.move_z(z)
                    self.add_current_function(func_str=func_str, func=func, labware_id=f"Z={z_pos}mm")
                    self.clear_grid(self.second_column_frame)

                except ValueError:
                    messagebox.showerror("Error", "Invalid position value")

            ttk.Button(
                self.second_column_frame,
                text="Confirm",
                command=confirm_movement,
                bootstyle="success"
            ).grid(row=3, column=0, sticky="nsew", pady=5, padx=5)

        else:  # Direct mode - USE NEW DIALOG
            z_pos = self.ask_position_dialog(
                axis='Z',
                min_val=0.0,
                max_val=self.deck.range_z,
                initial_value=0.0
            )

            if z_pos is not None:
                func = lambda z=z_pos: self.pipettor.move_z(z)
                details = f"Move to Z position: {z_pos} mm\n"
                details += f"Range: 0 to {self.deck.range_z} mm\n"
                details += "(0 = home/top position)"
                self.stage_operation(func, func_str, details)

    def callback_home(self, func_str: str):
        """Handle Home operation"""
        func = lambda: self.pipettor.home()
        details = "Action: Move pipettor to home position"

        if self.mode == "direct":
            self.stage_operation(func, func_str, details)
        elif self.mode == "builder":
            self.add_current_function(func_str=func_str, func=func, labware_id="Home")