import ttkbootstrap as ttk
import tkinter as tk
import uuid
from typing import Callable, Optional
from tkinter import messagebox

from well_window import WellWindow
from deck import Deck
from labware import Labware, PipetteHolder, Plate, TipDropzone, ReservoirHolder
from pipettor_plus import PipettorPlus


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
            parent_frame: ttk.Frame = None
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

        # Determine channels
        if self.pipettor and self.pipettor.multichannel:
            self.channels = 8
        else:
            self.channels = 1

        # Workflow state
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
            self.window_build_func.geometry("1400x800")
            self.window_build_func.title("Workflow Builder")
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
        ).pack(pady=10)

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
        action_frame.columnconfigure(2, weight=0, minsize=80)  # Fixed minimum width for Clear

        self.execute_button = ttk.Button(
            action_frame,
            text="Execute Now",
            command=self.execute_staged_operation,
            state='disabled',
            bootstyle="success"
        )
        self.execute_button.grid(row=0, column=0, sticky='ew', padx=5)

        self.add_to_workflow_button = ttk.Button(
            action_frame,
            text="Add to Workflow",
            command=self.add_staged_to_workflow,
            state='disabled',
            bootstyle="info"
        )
        self.add_to_workflow_button.grid(row=0, column=1, sticky='ew', padx=5)

        self.clear_button = ttk.Button(
            action_frame,
            text="Clear",
            command=self.clear_staged_operation,
            state='disabled',
            bootstyle="secondary"
        )
        self.clear_button.grid(row=0, column=2, sticky='ew', padx=5)

        # === CUSTOM WORKFLOWS SECTION ===
        custom_frame = ttk.Labelframe(
            self.control_frame,
            text="Custom Workflows",
            padding=10
        )
        custom_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(
            custom_frame,
            text="Open Workflow Builder",
            command=self.open_workflow_builder,
            bootstyle="warning"
        ).pack(fill=tk.X, pady=5)

        # Saved workflows will appear here
        self.saved_workflows_frame = ttk.Frame(custom_frame)
        self.saved_workflows_frame.pack(fill=tk.X, pady=5)

        # Initialize display
        self.update_staged_display()

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
            font=('Helvetica', 18)
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
            font=('Helvetica', 14, 'bold')
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

        self.save_button = ttk.Button(
            self.frame_name,
            text="💾 Save Workflow",
            command=self.callback_save_button,
            bootstyle="success"
        )
        self.save_button.grid(row=1, column=1, sticky="ew", padx=5)

        self.clear_queue_button = ttk.Button(
            self.frame_name,
            text="🗑️ Clear Queue",
            command=self.clear_workflow_queue,
            bootstyle="danger"
        )
        self.clear_queue_button.grid(row=1, column=2, sticky="ew")

    def place_operation_buttons(self, parent_frame):
        """Place all operation buttons (shared between modes)"""
        # Tip Operations
        tip_frame = ttk.Labelframe(parent_frame, text="Tip Management", padding=10)
        tip_frame.pack(fill=tk.X, pady=5, padx=5)

        ttk.Button(
            tip_frame, text=" Pick Tips",
            command=lambda: self.callback_pick_tips(func_str="Pick Tips"),
            bootstyle="primary"
        ).pack(fill=tk.X, pady=2)

        ttk.Button(
            tip_frame, text=" Return Tips",
            command=lambda: self.callback_return_tips(func_str="Return Tips"),
            bootstyle="primary"
        ).pack(fill=tk.X, pady=2)

        ttk.Button(
            tip_frame, text=" Replace Tips",
            command=lambda: self.callback_replace_tips(func_str="Replace Tips"),
            bootstyle="primary"
        ).pack(fill=tk.X, pady=2)

        ttk.Button(
            tip_frame, text="🗑️ Discard Tips",
            command=lambda: self.callback_discard_tips(func_str="Discard Tips"),
            bootstyle="primary"
        ).pack(fill=tk.X, pady=2)

        # Liquid Handling
        liquid_frame = ttk.Labelframe(parent_frame, text="Liquid Handling", padding=10)
        liquid_frame.pack(fill=tk.X, pady=5, padx=5)

        ttk.Button(
            liquid_frame, text=" Add Medium",
            command=lambda: self.callback_add_medium(func_str="Add Medium"),
            bootstyle="success"
        ).pack(fill=tk.X, pady=2)

        ttk.Button(
            liquid_frame, text=" Remove Medium",
            command=lambda: self.callback_remove_medium(func_str="Remove Medium"),
            bootstyle="success"
        ).pack(fill=tk.X, pady=2)

        ttk.Button(
            liquid_frame, text=" Transfer Plate to Plate",
            command=lambda: self.callback_transfer_plate_to_plate(func_str="Transfer Plate to Plate"),
            bootstyle="success"
        ).pack(fill=tk.X, pady=2)

        # Low-level Operations
        lowlevel_frame = ttk.Labelframe(parent_frame, text="Low-Level", padding=10)
        lowlevel_frame.pack(fill=tk.X, pady=5, padx=5)

        ttk.Button(
            lowlevel_frame, text=" Suck",
            command=lambda: self.callback_suck(func_str="Suck"),
            bootstyle="info"
        ).pack(fill=tk.X, pady=2)

        ttk.Button(
            lowlevel_frame, text=" Spit",
            command=lambda: self.callback_spit(func_str="Spit"),
            bootstyle="info"
        ).pack(fill=tk.X, pady=2)

        ttk.Button(
            lowlevel_frame, text=" Spit All",
            command=lambda: self.callback_spit_all(func_str="Spit All"),
            bootstyle="info"
        ).pack(fill=tk.X, pady=2)

        # System
        system_frame = ttk.Labelframe(parent_frame, text="System", padding=10)
        system_frame.pack(fill=tk.X, pady=5, padx=5)

        ttk.Button(
            system_frame, text="🏠 Home",
            command=lambda: self.callback_home(func_str="Home"),
            bootstyle="secondary"
        ).pack(fill=tk.X, pady=2)

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
            self.clear_staged_operation()
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Operation '{self.staged_operation_name}' failed:\n\n{str(e)}"
            )

    def add_staged_to_workflow(self):
        """Add staged operation to workflow builder"""
        if self.staged_operation is None:
            return

        # Open workflow builder
        builder = FunctionWindow(
            deck=self.deck,
            pipettor=self.pipettor,
            mode="builder",
            master=self.container.winfo_toplevel()
        )

        # Add the staged operation
        builder.current_func_list.append(self.staged_operation)
        builder.current_func_details.append(f"{self.staged_operation_name}")
        builder.display_workflow_queue()

        messagebox.showinfo(
            "Added",
            f"Operation '{self.staged_operation_name}' added to workflow builder.\n\n"
            "Add more operations and save your workflow."
        )

        self.clear_staged_operation()

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

        if not self.current_func_list:
            ttk.Label(
                self.third_column_frame,
                text="No operations in queue\n\nClick operation buttons to add",
                font=("Helvetica", 12),
                foreground="gray"
            ).pack(pady=20)
            return

        # Display each operation
        for idx, detail in enumerate(self.current_func_details):
            frame = ttk.Frame(self.third_column_frame)
            frame.grid(row=idx, column=0, sticky="ew", pady=2, padx=5)
            frame.columnconfigure(0, weight=1)

            # Operation label
            label = ttk.Label(
                frame,
                text=f"{idx + 1}. {detail}",
                font=("Helvetica", 11)
            )
            label.grid(row=0, column=0, sticky="w")

            # Remove button
            remove_btn = ttk.Button(
                frame,
                text="✖",
                width=3,
                command=lambda i=idx: self.remove_from_queue(i),
                bootstyle="danger-outline"
            )
            remove_btn.grid(row=0, column=1, sticky="e", padx=5)

    def remove_from_queue(self, index: int):
        """Remove operation from workflow queue"""
        if 0 <= index < len(self.current_func_list):
            del self.current_func_list[index]
            del self.current_func_details[index]
            self.display_workflow_queue()

    def clear_workflow_queue(self):
        """Clear all operations from queue"""
        if not self.current_func_list:
            return

        if messagebox.askyesno("Confirm", "Clear all operations from queue?"):
            self.current_func_list = []
            self.current_func_details = []
            self.display_workflow_queue()

    def callback_save_button(self):
        """Save workflow"""
        if not self.current_func_list:
            messagebox.showwarning("Empty Workflow", "Please add operations to the workflow first")
            return

        name = self.entry_name.get().strip()
        if not name:
            name = f"Workflow_{uuid.uuid4().hex[:8]}"

        # Ensure unique name
        i = 1
        original_name = name
        while name in self.custom_funcs_dict:
            name = f"{original_name}_{i}"
            i += 1

        # Save workflow
        self.custom_funcs_dict[name] = self.current_func_list.copy()

        # Clear queue
        self.current_func_list = []
        self.current_func_details = []
        self.display_workflow_queue()
        self.entry_name.delete(0, tk.END)

        messagebox.showinfo(
            "Saved",
            f"Workflow '{name}' saved with {len(self.custom_funcs_dict[name])} operations!"
        )

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
            dialog.title(f"Select {labware_type.__name__}")
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
                    text=f"No {labware_type.__name__} found on deck",
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
            source: bool = False
    ) -> list[tuple[int, int]]:
        """Get available wells from labware based on type and context"""
        if isinstance(labware_obj, Plate):
            rows, columns = labware_obj._rows, labware_obj._columns
            wells_list = [(r, c) for r in range(rows) for c in range(columns)]

            if source:
                # Filter to wells with content
                wells_list = [
                    (r, c) for (r, c) in wells_list
                    if labware_obj.get_well_at(c, r).get_total_volume() > 0
                ]

        elif isinstance(labware_obj, ReservoirHolder):
            wells_list = []
            for res in labware_obj.get_reservoirs():
                if res is None:
                    continue
                if source and res.get_total_volume() > 0:
                    wells_list.append((res.row, res.column))
                elif not source and res.get_available_volume() > 0:
                    wells_list.append((res.row, res.column))

        elif isinstance(labware_obj, PipetteHolder):
            if source:
                wells_list = [
                    (holder.row, holder.column)
                    for holder in labware_obj.get_occupied_holders()
                ]
            else:
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
            window = WellWindow(
                rows=labware_obj.holders_across_y,
                columns=labware_obj.holders_across_x,
                labware_id=labware_obj.labware_id,
                max_selected=None,
                master=self.get_master_window(),
                multichannel_mode=(self.channels == 8),
                title=f"Pick tips from: {labware_obj.labware_id}",
                wells_list=self.get_wells_list_from_labware(labware_obj=labware_obj, source=True)
            )
            self.get_master_window().wait_window(window.get_root())

            # ✅ UNIFIED: Get start positions (works for both modes!)
            start_positions = window.get_start_positions()
            if not start_positions:
                return

            # Convert from (row, col) to (col, row) format for pipettor
            list_col_row = [(c, r) for r, c in start_positions]

            # Create function
            func = lambda lw=labware_obj, lr=list_col_row: self.pipettor.pick_tips(
                pipette_holder=lw, list_col_row=lr
            )

            # Create details
            details = f"Labware: {labware_obj.labware_id}\n"
            if self.channels == 8:
                details += f"Multichannel groups: {len(list_col_row)}\n"
                details += f"Start positions (col:row): {', '.join([f'({c}:{r})' for c, r in list_col_row[:5]])}"
            else:
                details += f"Positions: {len(list_col_row)} tips\n"
                details += f"Wells (Col:Row): {', '.join([f'({c}:{r})' for c, r in list_col_row[:5]])}"

            if len(list_col_row) > 5:
                details += f"... (+{len(list_col_row) - 5} more)"

            if self.mode == "direct":
                self.stage_operation(func, func_str, details)
            elif self.mode == "builder":
                self.add_current_function(func_str=func_str, func=func, labware_id=labware_obj.labware_id)

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
            window = WellWindow(
                rows=labware_obj.holders_across_y,
                columns=labware_obj.holders_across_x,
                labware_id=labware_obj.labware_id,
                max_selected=None,
                master=self.get_master_window(),
                multichannel_mode=(self.channels == 8),
                title=f"Return tips to: {labware_obj.labware_id}",
                wells_list=self.get_wells_list_from_labware(labware_obj=labware_obj, source=False)
            )
            self.get_master_window().wait_window(window.get_root())

            # ✅ UNIFIED: Get start positions (works for both modes!)
            start_positions = window.get_start_positions()
            if not start_positions:
                return

            # Convert from (row, col) to (col, row) format for pipettor
            list_col_row = [(c, r) for r, c in start_positions]

            # Create function
            func = lambda lw=labware_obj, lr=list_col_row: self.pipettor.return_tips(
                pipette_holder=lw, list_col_row=lr
            )

            # Create details
            details = f"Labware: {labware_obj.labware_id}\n"
            if self.channels == 8:
                details += f"Multichannel groups: {len(list_col_row)}\n"
                details += f"Start positions (col:row): {', '.join([f'({c}:{r})' for c, r in list_col_row[:5]])}"
            else:
                details += f"Positions: {len(list_col_row)} tips\n"
                details += f"Wells (Col:Row): {', '.join([f'({c}:{r})' for c, r in list_col_row[:5]])}"

            if len(list_col_row) > 5:
                details += f"... (+{len(list_col_row) - 5} more)"

            if self.mode == "direct":
                self.stage_operation(func, func_str, details)
            elif self.mode == "builder":
                self.add_current_function(func_str=func_str, func=func, labware_id=labware_obj.labware_id)

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
            # ===== STEP 1: Return old tips =====
            window_return = WellWindow(
                rows=labware_obj.holders_across_y,
                columns=labware_obj.holders_across_x,
                labware_id=labware_obj.labware_id,
                max_selected=None,
                master=self.get_master_window(),
                multichannel_mode=(self.channels == 8),
                title=f"Return tips to: {labware_obj.labware_id}",
                wells_list=self.get_wells_list_from_labware(labware_obj=labware_obj, source=False)
            )
            self.get_master_window().wait_window(window_return.get_root())

            # ✅ Get start positions for return
            start_positions_return = window_return.get_start_positions()
            if not start_positions_return:
                return

            # Convert to (col, row) format
            list_return = [(c, r) for r, c in start_positions_return]

            # ===== STEP 2: Pick new tips =====
            window_pick = WellWindow(
                rows=labware_obj.holders_across_y,
                columns=labware_obj.holders_across_x,
                labware_id=labware_obj.labware_id,
                max_selected=None,
                master=self.get_master_window(),
                multichannel_mode=(self.channels == 8),
                title=f"Pick new tips from: {labware_obj.labware_id}",
                wells_list=self.get_wells_list_from_labware(labware_obj=labware_obj, source=True)
            )
            self.get_master_window().wait_window(window_pick.get_root())

            # ✅ Get start positions for pick
            start_positions_pick = window_pick.get_start_positions()
            if not start_positions_pick:
                return

            # Convert to (col, row) format
            list_pick = [(c, r) for r, c in start_positions_pick]

            # Create function
            func = lambda lw=labware_obj, lr=list_return, lp=list_pick: self.pipettor.replace_tips(
                pipette_holder=lw, return_list_col_row=lr, pick_list_col_row=lp
            )

            # Create details
            details = f"Labware: {labware_obj.labware_id}\n"

            if self.channels == 8:
                # Return details
                details += f"Return - Multichannel groups: {len(list_return)}\n"
                details += f"  Positions (col:row): {', '.join([f'({c}:{r})' for c, r in list_return[:5]])}"
                if len(list_return) > 5:
                    details += f"... (+{len(list_return) - 5} more)"
                details += "\n"

                # Pick details
                details += f"Pick - Multichannel groups: {len(list_pick)}\n"
                details += f"  Positions (col:row): {', '.join([f'({c}:{r})' for c, r in list_pick[:5]])}"
                if len(list_pick) > 5:
                    details += f"... (+{len(list_pick) - 5} more)"
            else:
                # Return details
                details += f"Return - Positions: {len(list_return)} tips\n"
                details += f"  Wells (Col:Row): {', '.join([f'({c}:{r})' for c, r in list_return[:5]])}"
                if len(list_return) > 5:
                    details += f"... (+{len(list_return) - 5} more)"
                details += "\n"

                # Pick details
                details += f"Pick - Positions: {len(list_pick)} tips\n"
                details += f"  Wells (Col:Row): {', '.join([f'({c}:{r})' for c, r in list_pick[:5]])}"
                if len(list_pick) > 5:
                    details += f"... (+{len(list_pick) - 5} more)"

            if self.mode == "direct":
                self.stage_operation(func, func_str, details)
            elif self.mode == "builder":
                self.add_current_function(func_str=func_str, func=func, labware_id=labware_obj.labware_id)

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
            func = lambda lw=labware_obj: self.pipettor.discard_tips(lw)

            details = f"Dropzone: {labware_obj.labware_id}\n"
            details += "Action: Discard all tips"

            if self.mode == "direct":
                self.stage_operation(func, func_str, details)
            elif self.mode == "builder":
                self.add_current_function(func_str=func_str, func=func, labware_id=labware_obj.labware_id)

    def callback_add_medium(
            self,
            func_str: str,
            part: str = "first",
            labware_obj=None,
            **kwargs
    ):
        """Handle Add Medium operation"""
        if part == "first":
            if self.mode == "builder":
                self.clear_grid(self.second_column_frame)
            self.display_possible_labware(
                labware_type=ReservoirHolder,
                next_callback=self.callback_add_medium,
                func_str=func_str,
                part="second",
                **kwargs
            )

        elif part == "second" and labware_obj is not None:
            window = WellWindow(
                rows=labware_obj.hooks_across_y,
                columns=labware_obj.hooks_across_x,
                labware_id=labware_obj.labware_id,
                master=self.get_master_window(),
                title=f"Choose source reservoir: {labware_obj.labware_id}",
                wells_list=self.get_wells_list_from_labware(labware_obj=labware_obj, source=True)
            )
            self.get_master_window().wait_variable(window.safe_var)

            kwargs["source_labware"] = labware_obj
            kwargs["source_positions"] = [
                (r, c) for r, row in enumerate(window.well_state) for c, v in enumerate(row) if v
            ]
            window.show_well_window()
            del window

            if not kwargs["source_positions"]:
                return

            if self.mode == "builder":
                self.clear_grid(self.second_column_frame)
            self.display_possible_labware(
                labware_type=Plate,
                next_callback=self.callback_add_medium,
                func_str=func_str,
                part="third",
                **kwargs
            )

        elif part == "third" and labware_obj is not None:
            window = WellWindow(
                rows=labware_obj._rows,
                columns=labware_obj._columns,
                labware_id=labware_obj.labware_id,
                max_selected=self.channels,
                master=self.get_master_window(),
                title=f"Choose destination wells: {labware_obj.labware_id}",
                wells_list=self.get_wells_list_from_labware(labware_obj=labware_obj, source=False)
            )
            self.get_master_window().wait_variable(window.safe_var)
            kwargs["dest_labware"] = labware_obj
            kwargs["dest_positions"] = [
                (r, c) for r, row in enumerate(window.well_state) for c, v in enumerate(row) if v
            ]
            window.show_well_window()
            del window

            if not kwargs["dest_positions"]:
                return

            # Get volume
            if self.mode == "builder":
                self.clear_grid(self.second_column_frame)
                label = ttk.Label(self.second_column_frame, text="Enter Volume per Well (µL)")
                label.grid(column=0, row=0, sticky="nsew", pady=5, padx=5)
                text_var = ttk.StringVar(value="100")
                entry = ttk.Entry(self.second_column_frame, textvariable=text_var)
                entry.grid(row=1, column=0, sticky="nsew", pady=5, padx=5)

                def callback_enter_button():
                    try:
                        volume = float(text_var.get())
                    except ValueError:
                        messagebox.showerror("Error", "Invalid volume")
                        return

                    func = lambda kwargs=kwargs, vol=volume: self.pipettor.add_medium(
                        source=kwargs["source_labware"],
                        source_col_row=kwargs["source_positions"],
                        destination=kwargs["dest_labware"],
                        dest_col_row=kwargs["dest_positions"],
                        volume_per_well=vol
                    )

                    self.add_current_function(func_str=func_str, func=func,
                                              labware_id=kwargs["dest_labware"].labware_id)
                    self.clear_grid(self.second_column_frame)

                button = ttk.Button(self.second_column_frame, text="Confirm", command=callback_enter_button)
                button.grid(row=2, column=0, sticky="nsew", pady=5, padx=5)

            else:  # direct mode
                volume = tk.simpledialog.askfloat(
                    "Volume",
                    "Enter volume per well (µL):",
                    initialvalue=100,
                    minvalue=1,
                    maxvalue=10000
                )
                if not volume:
                    return

                func = lambda kwargs=kwargs, vol=volume: self.pipettor.add_medium(
                    source=kwargs["source_labware"],
                    source_col_row=kwargs["source_positions"],
                    destination=kwargs["dest_labware"],
                    dest_col_row=kwargs["dest_positions"],
                    volume_per_well=vol
                )

                details = f"Source: {kwargs['source_labware'].labware_id}\n"
                details += f"  Reservoir: {kwargs['source_positions']}\n"
                details += f"Destination: {kwargs['dest_labware'].labware_id}\n"
                details += f"  Wells: {len(kwargs['dest_positions'])} wells\n"
                details += f"Volume: {volume} µL per well\n"
                details += f"Total: {volume * len(kwargs['dest_positions'])} µL"

                self.stage_operation(func, func_str, details)

    def callback_remove_medium(
            self,
            func_str: str,
            part: str = "first",
            labware_obj=None,
            **kwargs
    ):
        """Handle Remove Medium operation"""
        if part == "first":
            if self.mode == "builder":
                self.clear_grid(self.second_column_frame)
            self.display_possible_labware(
                labware_type=Plate,
                next_callback=self.callback_remove_medium,
                func_str=func_str,
                part="second",
                **kwargs
            )

        elif part == "second" and labware_obj is not None:
            window = WellWindow(
                rows=labware_obj._rows,
                columns=labware_obj._columns,
                labware_id=labware_obj.labware_id,
                max_selected=self.channels,
                master=self.get_master_window(),
                title=f"Select source wells: {labware_obj.labware_id}",
                wells_list=self.get_wells_list_from_labware(labware_obj=labware_obj, source=True)
            )
            self.get_master_window().wait_variable(window.safe_var)
            kwargs["source_labware"] = labware_obj
            kwargs["source_positions"] = [
                (r, c) for r, row in enumerate(window.well_state) for c, v in enumerate(row) if v
            ]
            window.show_well_window()
            del window

            if not kwargs["source_positions"]:
                return

            if self.mode == "builder":
                self.clear_grid(self.second_column_frame)
            self.display_possible_labware(
                labware_type=ReservoirHolder,
                next_callback=self.callback_remove_medium,
                func_str=func_str,
                part="third",
                **kwargs
            )

        elif part == "third" and labware_obj is not None:
            window = WellWindow(
                rows=labware_obj.hooks_across_y,
                columns=labware_obj.hooks_across_x,
                labware_id=labware_obj.labware_id,
                max_selected=self.channels,
                master=self.get_master_window(),
                title=f"Select destination reservoir: {labware_obj.labware_id}",
                wells_list=self.get_wells_list_from_labware(labware_obj=labware_obj, source=False)
            )
            self.get_master_window().wait_variable(window.safe_var)
            kwargs["dest_labware"] = labware_obj
            kwargs["dest_positions"] = [
                (r, c) for r, row in enumerate(window.well_state) for c, v in enumerate(row) if v
            ]
            window.show_well_window()
            del window

            if not kwargs["dest_positions"]:
                return

            # Get volume
            if self.mode == "builder":
                self.clear_grid(self.second_column_frame)
                label = ttk.Label(self.second_column_frame, text="Enter Volume per Well (µL)")
                label.grid(column=0, row=0, sticky="nsew", pady=5, padx=5)
                text_var = ttk.StringVar(value="100")
                entry = ttk.Entry(self.second_column_frame, textvariable=text_var)
                entry.grid(row=1, column=0, sticky="nsew", pady=5, padx=5)

                def callback_enter_button():
                    try:
                        volume = float(text_var.get())
                    except ValueError:
                        messagebox.showerror("Error", "Invalid volume")
                        return

                    func = lambda kwargs=kwargs, vol=volume: self.pipettor.remove_medium(
                        source=kwargs["source_labware"],
                        destination=kwargs["dest_labware"],
                        source_col_row=kwargs["source_positions"],
                        destination_col_row=kwargs["dest_positions"],
                        volume_per_well=vol
                    )

                    self.add_current_function(func_str=func_str, func=func,
                                              labware_id=kwargs["dest_labware"].labware_id)
                    self.clear_grid(self.second_column_frame)

                button = ttk.Button(self.second_column_frame, text="Confirm", command=callback_enter_button)
                button.grid(row=2, column=0, sticky="nsew", pady=5, padx=5)

            else:  # direct mode
                volume = tk.simpledialog.askfloat(
                    "Volume",
                    "Enter volume per well (µL):",
                    initialvalue=100,
                    minvalue=1,
                    maxvalue=10000
                )
                if not volume:
                    return

                func = lambda kwargs=kwargs, vol=volume: self.pipettor.remove_medium(
                    source=kwargs["source_labware"],
                    destination=kwargs["dest_labware"],
                    source_col_row=kwargs["source_positions"],
                    destination_col_row=kwargs["dest_positions"],
                    volume_per_well=vol
                )

                details = f"Source: {kwargs['source_labware'].labware_id}\n"
                details += f"  Wells: {len(kwargs['source_positions'])} wells\n"
                details += f"Destination: {kwargs['dest_labware'].labware_id}\n"
                details += f"  Reservoir: {kwargs['dest_positions']}\n"
                details += f"Volume: {volume} µL per well\n"
                details += f"Total: {volume * len(kwargs['source_positions'])} µL"

                self.stage_operation(func, func_str, details)

    def callback_transfer_plate_to_plate(
            self,
            func_str: str,
            part: str = "first",
            labware_obj: Plate = None,
            **kwargs
    ):
        """Handle Transfer Plate to Plate operation"""
        if part == "first":
            if self.mode == "builder":
                self.clear_grid(self.second_column_frame)
            self.display_possible_labware(
                labware_type=Plate,
                next_callback=self.callback_transfer_plate_to_plate,
                func_str=func_str,
                part="second",
                **kwargs
            )

        elif part == "second" and labware_obj is not None:
            window = WellWindow(
                rows=labware_obj._rows,
                columns=labware_obj._columns,
                labware_id=labware_obj.labware_id,
                max_selected=self.channels,
                master=self.get_master_window(),
                title=f"Select source wells: {labware_obj.labware_id}",
                wells_list=self.get_wells_list_from_labware(labware_obj=labware_obj, source=True)
            )
            self.get_master_window().wait_variable(window.safe_var)
            kwargs["source_labware"] = labware_obj
            kwargs["source_positions"] = [
                (r, c) for r, row in enumerate(window.well_state) for c, v in enumerate(row) if v
            ]
            window.show_well_window()
            del window

            if not kwargs["source_positions"]:
                return

            if self.mode == "builder":
                self.clear_grid(self.second_column_frame)
            self.display_possible_labware(
                labware_type=Plate,
                next_callback=self.callback_transfer_plate_to_plate,
                func_str=func_str,
                part="third",
                **kwargs
            )

        elif part == "third" and labware_obj is not None:
            window = WellWindow(
                rows=labware_obj._rows,
                columns=labware_obj._columns,
                labware_id=labware_obj.labware_id,
                max_selected=self.channels,
                master=self.get_master_window(),
                title=f"Select destination wells: {labware_obj.labware_id}",
                wells_list=self.get_wells_list_from_labware(labware_obj=labware_obj, source=False)
            )
            self.get_master_window().wait_variable(window.safe_var)
            kwargs["dest_labware"] = labware_obj
            kwargs["dest_positions"] = [
                (r, c) for r, row in enumerate(window.well_state) for c, v in enumerate(row) if v
            ]
            window.show_well_window()
            del window

            if not kwargs["dest_positions"]:
                return

            # Get volume
            if self.mode == "builder":
                self.clear_grid(self.second_column_frame)
                label = ttk.Label(self.second_column_frame, text="Enter Volume per Well (µL)")
                label.grid(column=0, row=0, sticky="nsew", pady=5, padx=5)
                text_var = ttk.StringVar(value="100")
                entry = ttk.Entry(self.second_column_frame, textvariable=text_var)
                entry.grid(row=1, column=0, sticky="nsew", pady=5, padx=5)

                def callback_enter_button():
                    try:
                        volume = float(text_var.get())
                    except ValueError:
                        messagebox.showerror("Error", "Invalid volume")
                        return

                    func = lambda kwargs=kwargs, vol=volume: self.pipettor.transfer_plate_to_plate(
                        source=kwargs["source_labware"],
                        source_col_row=kwargs["source_positions"],
                        destination=kwargs["dest_labware"],
                        dest_col_row=kwargs["dest_positions"],
                        volume_per_well=vol
                    )

                    self.add_current_function(func_str=func_str, func=func,
                                              labware_id=kwargs["dest_labware"].labware_id)
                    self.clear_grid(self.second_column_frame)

                button = ttk.Button(self.second_column_frame, text="Confirm", command=callback_enter_button)
                button.grid(row=2, column=0, sticky="nsew", pady=5, padx=5)

            else:  # direct mode
                volume = tk.simpledialog.askfloat(
                    "Volume",
                    "Enter volume per well (µL):",
                    initialvalue=100,
                    minvalue=1,
                    maxvalue=10000
                )
                if not volume:
                    return

                func = lambda kwargs=kwargs, vol=volume: self.pipettor.transfer_plate_to_plate(
                    source=kwargs["source_labware"],
                    source_col_row=kwargs["source_positions"],
                    destination=kwargs["dest_labware"],
                    dest_col_row=kwargs["dest_positions"],
                    volume_per_well=vol
                )

                details = f"Source: {kwargs['source_labware'].labware_id}\n"
                details += f"  Wells: {len(kwargs['source_positions'])} wells\n"
                details += f"Destination: {kwargs['dest_labware'].labware_id}\n"
                details += f"  Wells: {len(kwargs['dest_positions'])} wells\n"
                details += f"Volume: {volume} µL per well\n"
                details += f"Total: {volume * len(kwargs['source_positions'])} µL"

                self.stage_operation(func, func_str, details)

    def callback_suck(
            self,
            func_str: str,
            part: str = "first",
            labware_obj: Labware = None,
            **kwargs
    ):
        """Handle Suck operation"""
        if part == "first":
            if self.mode == "builder":
                self.clear_grid(self.second_column_frame)
            self.display_possible_labware(
                labware_type=Labware,
                next_callback=self.callback_suck,
                func_str=func_str,
                part="second",
                **kwargs
            )

        elif part == "second" and labware_obj is not None:
            # Determine dimensions
            if isinstance(labware_obj, ReservoirHolder):
                rows, columns = labware_obj.hooks_across_y, labware_obj.hooks_across_x
            elif isinstance(labware_obj, PipetteHolder):
                rows, columns = labware_obj.holders_across_y, labware_obj.holders_across_x
            elif isinstance(labware_obj, Plate):
                rows, columns = labware_obj._rows, labware_obj._columns
            else:
                return

            window = WellWindow(
                rows=rows,
                columns=columns,
                labware_id=labware_obj.labware_id,
                max_selected=self.channels,
                master=self.get_master_window(),
                title=f"Select wells to suck from: {labware_obj.labware_id}",
                wells_list=self.get_wells_list_from_labware(labware_obj=labware_obj, source=True)
            )
            self.get_master_window().wait_variable(window.safe_var)
            kwargs["labware_obj"] = labware_obj
            kwargs["positions"] = [
                (r, c) for r, row in enumerate(window.well_state) for c, v in enumerate(row) if v
            ]
            window.show_well_window()
            del window

            if not kwargs["positions"]:
                return

            # Get volume
            if self.mode == "builder":
                self.clear_grid(self.second_column_frame)
                label = ttk.Label(self.second_column_frame, text="Enter Volume per Well (µL)")
                label.grid(column=0, row=0, sticky="nsew", pady=5, padx=5)
                text_var = ttk.StringVar(value="100")
                entry = ttk.Entry(self.second_column_frame, textvariable=text_var)
                entry.grid(row=1, column=0, sticky="nsew", pady=5, padx=5)

                def callback_enter_button():
                    try:
                        volume = float(text_var.get())
                    except ValueError:
                        messagebox.showerror("Error", "Invalid volume")
                        return

                    func = lambda kwargs=kwargs, vol=volume: self.pipettor.suck(
                        source=kwargs["labware_obj"],
                        source_col_row=kwargs["positions"],
                        volume=vol
                    )

                    self.add_current_function(func_str=func_str, func=func,
                                              labware_id=kwargs["labware_obj"].labware_id)
                    self.clear_grid(self.second_column_frame)

                button = ttk.Button(self.second_column_frame, text="Confirm", command=callback_enter_button)
                button.grid(row=2, column=0, sticky="nsew", pady=5, padx=5)

            else:  # direct mode
                volume = tk.simpledialog.askfloat(
                    "Volume",
                    "Enter volume per well (µL):",
                    initialvalue=100,
                    minvalue=1,
                    maxvalue=10000
                )
                if not volume:
                    return

                func = lambda kwargs=kwargs, vol=volume: self.pipettor.suck(
                    source=kwargs["labware_obj"],
                    source_col_row=kwargs["positions"],
                    volume=vol
                )

                details = f"Labware: {kwargs['labware_obj'].labware_id}\n"
                details += f"Wells: {len(kwargs['positions'])} positions\n"
                details += f"Volume: {volume} µL per well\n"
                details += f"Total: {volume * len(kwargs['positions'])} µL"

                self.stage_operation(func, func_str, details)

    def callback_spit(
            self,
            func_str: str,
            part: str = "first",
            labware_obj: Labware = None,
            **kwargs
    ):
        """Handle Spit operation"""
        if part == "first":
            if self.mode == "builder":
                self.clear_grid(self.second_column_frame)
            self.display_possible_labware(
                labware_type=Labware,
                next_callback=self.callback_spit,
                func_str=func_str,
                part="second",
                **kwargs
            )

        elif part == "second" and labware_obj is not None:
            # Determine dimensions
            if isinstance(labware_obj, ReservoirHolder):
                rows, columns = labware_obj.hooks_across_y, labware_obj.hooks_across_x
            elif isinstance(labware_obj, PipetteHolder):
                rows, columns = labware_obj.holders_across_y, labware_obj.holders_across_x
            elif isinstance(labware_obj, Plate):
                rows, columns = labware_obj._rows, labware_obj._columns
            else:
                return

            window = WellWindow(
                rows=rows,
                columns=columns,
                max_selected=self.channels,
                labware_id=labware_obj.labware_id,
                master=self.get_master_window(),
                title=f"Select wells to spit into: {labware_obj.labware_id}",
                wells_list=self.get_wells_list_from_labware(labware_obj=labware_obj, source=False)
            )
            self.get_master_window().wait_variable(window.safe_var)
            kwargs["labware_obj"] = labware_obj
            kwargs["positions"] = [
                (r, c) for r, row in enumerate(window.well_state) for c, v in enumerate(row) if v
            ]
            window.show_well_window()
            del window

            if not kwargs["positions"]:
                return

            # Get volume
            if self.mode == "builder":
                self.clear_grid(self.second_column_frame)
                label = ttk.Label(self.second_column_frame, text="Enter Volume per Well (µL)")
                label.grid(column=0, row=0, sticky="nsew", pady=5, padx=5)
                text_var = ttk.StringVar(value="100")
                entry = ttk.Entry(self.second_column_frame, textvariable=text_var)
                entry.grid(row=1, column=0, sticky="nsew", pady=5, padx=5)

                def callback_enter_button():
                    try:
                        volume = float(text_var.get())
                    except ValueError:
                        messagebox.showerror("Error", "Invalid volume")
                        return

                    func = lambda kwargs=kwargs, vol=volume: self.pipettor.spit(
                        destination=kwargs["labware_obj"],
                        dest_col_row=kwargs["positions"],
                        volume=vol
                    )

                    self.add_current_function(func_str=func_str, func=func,
                                              labware_id=kwargs["labware_obj"].labware_id)
                    self.clear_grid(self.second_column_frame)

                button = ttk.Button(self.second_column_frame, text="Confirm", command=callback_enter_button)
                button.grid(row=2, column=0, sticky="nsew", pady=5, padx=5)

            else:  # direct mode
                volume = tk.simpledialog.askfloat(
                    "Volume",
                    "Enter volume per well (µL):",
                    initialvalue=100,
                    minvalue=1,
                    maxvalue=10000
                )
                if not volume:
                    return

                func = lambda kwargs=kwargs, vol=volume: self.pipettor.spit(
                    destination=kwargs["labware_obj"],
                    dest_col_row=kwargs["positions"],
                    volume=vol
                )

                details = f"Labware: {kwargs['labware_obj'].labware_id}\n"
                details += f"Wells: {len(kwargs['positions'])} positions\n"
                details += f"Volume: {volume} µL per well\n"
                details += f"Total: {volume * len(kwargs['positions'])} µL"

                self.stage_operation(func, func_str, details)

    def callback_spit_all(
            self,
            func_str: str,
            part: str = "first",
            labware_obj: Labware = None,
            **kwargs
    ):
        """Handle Spit All operation"""
        if part == "first":
            if self.mode == "builder":
                self.clear_grid(self.second_column_frame)
            self.display_possible_labware(
                labware_type=Labware,
                next_callback=self.callback_spit_all,
                func_str=func_str,
                part="second",
                **kwargs
            )

        elif part == "second" and labware_obj is not None:
            # Determine dimensions
            if isinstance(labware_obj, ReservoirHolder):
                rows, columns = labware_obj.hooks_across_y, labware_obj.hooks_across_x
            elif isinstance(labware_obj, PipetteHolder):
                rows, columns = labware_obj.holders_across_y, labware_obj.holders_across_x
            elif isinstance(labware_obj, Plate):
                rows, columns = labware_obj._rows, labware_obj._columns
            else:
                return

            window = WellWindow(
                rows=rows,
                columns=columns,
                labware_id=labware_obj.labware_id,
                max_selected=self.channels,
                master=self.get_master_window(),
                title=f"Select wells to spit all into: {labware_obj.labware_id}",
                wells_list=self.get_wells_list_from_labware(labware_obj=labware_obj, source=False)
            )
            self.get_master_window().wait_variable(window.safe_var)
            kwargs["labware_obj"] = labware_obj
            kwargs["positions"] = [
                (r, c) for r, row in enumerate(window.well_state) for c, v in enumerate(row) if v
            ]
            window.show_well_window()
            del window

            if not kwargs["positions"]:
                return

            func = lambda kwargs=kwargs: self.pipettor.spit_all(
                destination=kwargs["labware_obj"],
                dest_col_row=kwargs["positions"]
            )

            details = f"Labware: {kwargs['labware_obj'].labware_id}\n"
            details += f"Wells: {len(kwargs['positions'])} positions\n"
            details += "Action: Spit all remaining liquid"

            if self.mode == "direct":
                self.stage_operation(func, func_str, details)
            elif self.mode == "builder":
                self.add_current_function(func_str=func_str, func=func,
                                          labware_id=kwargs["labware_obj"].labware_id)

    def callback_home(self, func_str: str):
        """Handle Home operation"""
        func = lambda: self.pipettor.home()
        details = "Action: Move pipettor to home position"

        if self.mode == "direct":
            self.stage_operation(func, func_str, details)
        elif self.mode == "builder":
            self.add_current_function(func_str=func_str, func=func, labware_id="Home")