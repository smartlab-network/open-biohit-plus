# gui2.py - Enhanced Tkinter GUI for Deck Editor with Low-Level Labware Support

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import json

import copy
# Import your existing classes
from deck import Deck
from slot import Slot
from serializable import Serializable
from labware import (
     Well, Reservoir, Plate, ReservoirHolder,
    PipetteHolder, TipDropzone, IndividualPipetteHolder
)
from pipettor_plus import PipettorPlus
class CreateLowLevelLabwareDialog(tk.Toplevel):
    """Dialog for creating low-level labware components (Well, Reservoir, IndividualPipetteHolder)"""
    def __init__(self, parent, initial_type=None):
        super().__init__(parent)
        self.title("Create Low-Level Labware")
        self.geometry("550x800")
        self.result = None

        # Make dialog modal
        self.transient(parent)
        self.grab_set()

        self.initial_type = initial_type
        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Type Selection
        type_frame = ttk.LabelFrame(main_frame, text="Component Type", padding="10")
        type_frame.pack(fill=tk.X, pady=5)

        all_types = ["Well", "Reservoir", "IndividualPipetteHolder"]

        if self.initial_type and self.initial_type in all_types:
            # Lock the options if a type was passed in (e.g., from Plate creation)
            types_to_show = [self.initial_type]
            default_type = self.initial_type
            type_frame.config(text=f"Component Type (Locked to {self.initial_type})")
        else:
            # Show all options if opening independently
            types_to_show = all_types
            default_type = self.initial_type if self.initial_type in all_types else "Well"

        self.component_type = tk.StringVar(value=default_type)

        for comp_type in types_to_show:  # Use the restricted list
            ttk.Radiobutton(
                type_frame,
                text=comp_type,
                variable=self.component_type,
                value=comp_type,
                command=self.on_type_change
            ).pack(anchor='w')

        # Basic Parameters
        basic_frame = ttk.LabelFrame(main_frame, text="Basic Parameters", padding="10")
        basic_frame.pack(fill=tk.X, pady=5)

        # ID
        ttk.Label(basic_frame, text="Labware ID:").grid(row=0, column=0, sticky='w', pady=2)
        self.id_var = tk.StringVar()
        ttk.Entry(basic_frame, textvariable=self.id_var, width=30).grid(row=0, column=1, pady=2)
        ttk.Label(basic_frame, text="(optional)", font=('Arial', 12, 'italic'), foreground='gray').grid(row=0, column=2,
                                                                                                        sticky='w',
                                                                                                        padx=5)

        # Dimensions
        ttk.Label(basic_frame, text="Size X (mm):").grid(row=1, column=0, sticky='w', pady=2)
        self.size_x_var = tk.StringVar()
        ttk.Entry(basic_frame, textvariable=self.size_x_var, width=30).grid(row=1, column=1, pady=2)

        ttk.Label(basic_frame, text="Size Y (mm):").grid(row=2, column=0, sticky='w', pady=2)
        self.size_y_var = tk.StringVar()
        ttk.Entry(basic_frame, textvariable=self.size_y_var, width=30).grid(row=2, column=1, pady=2)

        ttk.Label(basic_frame, text="Size Z (mm):").grid(row=3, column=0, sticky='w', pady=2)
        self.size_z_var = tk.StringVar()
        ttk.Entry(basic_frame, textvariable=self.size_z_var, width=30).grid(row=3, column=1, pady=2)

        # Offset
        ttk.Label(basic_frame, text="Offset X (mm):").grid(row=4, column=0, sticky='w', pady=2)
        self.offset_x_var = tk.StringVar(value="0.0")
        ttk.Entry(basic_frame, textvariable=self.offset_x_var, width=30).grid(row=4, column=1, pady=2)

        ttk.Label(basic_frame, text="Offset Y (mm):").grid(row=5, column=0, sticky='w', pady=2)
        self.offset_y_var = tk.StringVar(value="0.0")
        ttk.Entry(basic_frame, textvariable=self.offset_y_var, width=30).grid(row=5, column=1, pady=2)

        # Type-Specific Parameters Frame
        self.specific_frame = ttk.LabelFrame(main_frame, text="Type-Specific Parameters", padding="10")
        self.specific_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # Initialize type-specific fields
        self.create_specific_fields()

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)

        ttk.Button(btn_frame, text="Create", command=self.on_create).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.on_cancel).pack(side=tk.RIGHT)

    def create_specific_fields(self):
        """Create fields specific to the selected component type"""
        # Clear existing widgets
        for widget in self.specific_frame.winfo_children():
            widget.destroy()

        comp_type = self.component_type.get()

        if comp_type == "Well":
            ttk.Label(self.specific_frame, text="Capacity (µL):").grid(row=0, column=0, sticky='w', pady=2)
            self.capacity_var = tk.StringVar(value="1000")
            ttk.Entry(self.specific_frame, textvariable=self.capacity_var, width=20).grid(row=0, column=1, pady=2)
            ttk.Label(self.specific_frame, text="(optional, default: 1000)",font=('Arial', 12, 'italic'), foreground='gray').grid(row=0, column=2, sticky='w', padx=5)

            ttk.Label(self.specific_frame, text="Shape:").grid(row=1, column=0, sticky='w', pady=2)
            self.shape_var = tk.StringVar()
            shape_combo = ttk.Combobox(self.specific_frame, textvariable=self.shape_var,
                                       values=["", "rectangular", "circular", "conical", "u_bottom"],
                                       state='readonly', width=17)
            shape_combo.grid(row=1, column=1, pady=2)
            ttk.Label(self.specific_frame, text="(optional)",font=('Arial', 12, 'italic'), foreground='gray').grid(row=1, column=2, sticky='w', padx=5)

            # Content section
            ttk.Separator(self.specific_frame, orient='horizontal').grid(row=2, column=0, columnspan=3, sticky='ew',
                                                                         pady=10)

            ttk.Label(self.specific_frame, text="Initial Content (Optional):",
                      font=('Arial', 12, 'bold')).grid(row=3, column=0, columnspan=3, sticky='w', pady=(5, 2))
            ttk.Label(self.specific_frame, text="Add up to 4 content types:",
                      font=('Arial', 12, 'italic'), foreground='gray').grid(row=4, column=0, columnspan=3, sticky='w')

            # Header
            ttk.Label(self.specific_frame, text="Content Type",
                      font=('Arial', 12, 'bold')).grid(row=5, column=0, sticky='w', padx=(0, 5))
            ttk.Label(self.specific_frame, text="Volume (µL)",
                      font=('Arial', 12, 'bold')).grid(row=5, column=1, sticky='w')

            # Create 4 content entry rows
            self.well_content_types = []
            self.well_content_volumes = []

            for i in range(4):
                content_type_var = tk.StringVar()
                volume_var = tk.StringVar()

                ttk.Entry(self.specific_frame, textvariable=content_type_var, width=15).grid(
                    row=6 + i, column=0, sticky='w', pady=2, padx=(0, 5))
                ttk.Entry(self.specific_frame, textvariable=volume_var, width=15).grid(
                    row=6 + i, column=1, sticky='w', pady=2)

                self.well_content_types.append(content_type_var)
                self.well_content_volumes.append(volume_var)

        elif comp_type == "Reservoir":
            ttk.Label(self.specific_frame, text="Capacity (µL):").grid(row=0, column=0, sticky='w', pady=2)
            self.capacity_var = tk.StringVar(value="30000")
            ttk.Entry(self.specific_frame, textvariable=self.capacity_var, width=20).grid(row=0, column=1, pady=2)
            ttk.Label(self.specific_frame, text="(optional, default: 30000µL)", font=('Arial', 12, 'italic'),
                      foreground='gray').grid(row=0, column=2, sticky='w', padx=5)

            ttk.Label(self.specific_frame, text="Shape:").grid(row=1, column=0, sticky='w', pady=2)
            self.shape_var = tk.StringVar()
            shape_combo = ttk.Combobox(self.specific_frame, textvariable=self.shape_var,
                                       values=["", "rectangular", "circular", "conical", "u_bottom"],
                                       state='readonly', width=17)
            shape_combo.grid(row=1, column=1, pady=2)
            ttk.Label(self.specific_frame, text="(optional)", font=('Arial', 12, 'italic'), foreground='gray').grid(
                row=1, column=2, sticky='w', padx=5)

            # Content section
            ttk.Separator(self.specific_frame, orient='horizontal').grid(row=2, column=0, columnspan=3, sticky='ew',
                                                                         pady=10)

            ttk.Label(self.specific_frame, text="Initial Content (Optional):",
                      font=('Arial', 12, 'bold')).grid(row=3, column=0, columnspan=3, sticky='w', pady=(5, 2))
            ttk.Label(self.specific_frame, text="Add up to 4 content types:",
                      font=('Arial', 12, 'italic'), foreground='gray').grid(row=4, column=0, columnspan=3, sticky='w')

            # Header
            ttk.Label(self.specific_frame, text="Content Type",
                      font=('Arial', 12, 'bold')).grid(row=5, column=0, sticky='w', padx=(0, 5))
            ttk.Label(self.specific_frame, text="Volume (µL)",
                      font=('Arial', 12, 'bold')).grid(row=5, column=1, sticky='w')

            # Create 4 content entry rows
            self.reservoir_content_types = []
            self.reservoir_content_volumes = []

            for i in range(4):
                content_type_var = tk.StringVar()
                volume_var = tk.StringVar()

                ttk.Entry(self.specific_frame, textvariable=content_type_var, width=15).grid(
                    row=6 + i, column=0, sticky='w', pady=2, padx=(0, 5))
                ttk.Entry(self.specific_frame, textvariable=volume_var, width=15).grid(
                    row=6 + i, column=1, sticky='w', pady=2)

                self.reservoir_content_types.append(content_type_var)
                self.reservoir_content_volumes.append(volume_var)

        elif comp_type == "IndividualPipetteHolder":
            ttk.Label(self.specific_frame, text="Is Occupied:").grid(row=0, column=0, sticky='w', pady=2)
            self.is_occupied_var = tk.BooleanVar(value=True)
            ttk.Checkbutton(self.specific_frame, variable=self.is_occupied_var).grid(row=0, column=1, sticky='w', pady=2)
            ttk.Label(
                self.specific_frame,
                text="(optional, default: true)",
                font=('Arial', 12, 'italic'),
                foreground='gray'
            ).grid(row=0, column=2, sticky='w', padx=5)

    def on_type_change(self):
        """Handle component type change"""
        self.create_specific_fields()

    def on_create(self):
        """Create the low-level labware component"""
        try:
            # Get basic parameters
            labware_id = self.id_var.get() or None
            size_x = float(self.size_x_var.get())
            size_y = float(self.size_y_var.get())
            size_z = float(self.size_z_var.get())
            offset_x = float(self.offset_x_var.get() or "0.0")
            offset_y = float(self.offset_y_var.get() or "0.0")
            offset = (offset_x, offset_y)

            # Create component based on type
            comp_type = self.component_type.get()

            if comp_type == "Well":
                capacity = float(self.capacity_var.get() or 1000)
                shape = self.shape_var.get() or None

                # Build content dictionary from user inputs
                content = {}
                for i in range(4):
                    content_type = self.well_content_types[i].get().strip()
                    volume_str = self.well_content_volumes[i].get().strip()

                    if content_type and volume_str:  # Both must be filled
                        try:
                            volume = float(volume_str)
                            if volume < 0:
                                messagebox.showerror("Error", f"Volume for '{content_type}' cannot be negative")
                                return
                            content[content_type] = volume
                        except ValueError:
                            messagebox.showerror("Error", f"Invalid volume for '{content_type}': {volume_str}")
                            return
                    elif content_type or volume_str:  # Only one filled
                        messagebox.showerror("Error", "Both content type and volume must be provided together")
                        return

                # Validate total volume doesn't exceed capacity
                total_volume = sum(content.values())
                if total_volume > capacity:
                    messagebox.showerror("Error",
                                         f"Total content volume ({total_volume}µL) exceeds capacity ({capacity}µL)")
                    return

                self.result = Well(
                    size_x=size_x,
                    size_y=size_y,
                    size_z=size_z,
                    offset=offset,
                    labware_id=labware_id,
                    capacity=capacity,
                    shape=shape,
                    content=content if content else None
                )

            elif comp_type == "Reservoir":
                capacity = float(self.capacity_var.get() or 30000)
                shape = self.shape_var.get() or None

                # Build content dictionary from user inputs
                content = {}
                for i in range(4):
                    content_type = self.reservoir_content_types[i].get().strip()
                    volume_str = self.reservoir_content_volumes[i].get().strip()

                    if content_type and volume_str:  # Both must be filled
                        try:
                            volume = float(volume_str)
                            if volume < 0:
                                messagebox.showerror("Error", f"Volume for '{content_type}' cannot be negative")
                                return
                            content[content_type] = volume
                        except ValueError:
                            messagebox.showerror("Error", f"Invalid volume for '{content_type}': {volume_str}")
                            return
                    elif content_type or volume_str:  # Only one filled
                        messagebox.showerror("Error", "Both content type and volume must be provided together")
                        return

                # Validate total volume doesn't exceed capacity
                total_volume = sum(content.values())
                if total_volume > capacity:
                    messagebox.showerror("Error",
                                         f"Total content volume ({total_volume}µL) exceeds capacity ({capacity}µL)")
                    return

                self.result = Reservoir(
                    size_x=size_x,
                    size_y=size_y,
                    size_z=size_z,
                    offset=offset,
                    labware_id=labware_id,
                    capacity=capacity,
                    shape=shape,
                    content=content if content else None
                )

            elif comp_type == "IndividualPipetteHolder":
                is_occupied = self.is_occupied_var.get()

                self.result = IndividualPipetteHolder(
                    size_x=size_x,
                    size_y=size_y,
                    size_z=size_z,
                    offset=offset,
                    labware_id=labware_id,
                    is_occupied=is_occupied
                )
            print(self.result.to_dict())
            self.destroy()

        except ValueError as e:
            messagebox.showerror("Invalid Input", f"Please check your inputs:\n{str(e)}")

    def on_cancel(self):
        """Cancel dialog"""
        self.result = None
        self.destroy()

class SelectOrCreateComponentDialog(tk.Toplevel):
    """Dialog for selecting or creating a low-level component """

    def __init__(self, parent, component_type, available_components):
        super().__init__(parent)
        self.title(f"Select or Create {component_type}")
        self.geometry("400x500")
        self.result = None
        self.component_type = component_type
        self.available_components = available_components

        # Make dialog modal
        self.transient(parent)
        self.grab_set()

        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Instructions
        ttk.Label(
            main_frame,
            text=f"Select an existing {self.component_type} or create a new one:",
            wraplength=380
        ).pack(pady=(0, 10))

        # List frame
        list_frame = ttk.LabelFrame(main_frame, text=f"Available {self.component_type}s", padding="10")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # Listbox with scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        self.listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.listbox.yview)

        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Populate listbox
        for comp in self.available_components:
            display_text = f"{comp.labware_id} ({comp.size_x}x{comp.size_y}x{comp.size_z})"
            self.listbox.insert(tk.END, display_text)

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)

        ttk.Button(btn_frame, text="Select", command=self.on_select).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Create New", command=self.on_create_new).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.on_cancel).pack(side=tk.RIGHT)

    def on_select(self):
        """Select an existing component"""
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", f"Please select a {self.component_type}")
            return

        self.result = self.available_components[selection[0]]
        self.destroy()

    def on_create_new(self):
        """Create a new component"""
        # 1. Open the component creation dialog
        dialog = CreateLowLevelLabwareDialog(self, initial_type=self.component_type)
        self.wait_window(dialog)

        if dialog.result:
            # A new component was successfully created.
            new_comp = dialog.result

            # 2. Add the new component to the available list (for future dialogs)
            self.available_components.append(new_comp)

            # 3. Set the result of THIS (SelectOrCreate) dialog to the new component
            self.result = new_comp

            # This returns the result to the main application's wait_window().
            self.destroy()

    def on_cancel(self):
        """Cancel dialog"""
        self.result = None
        self.destroy()

class CreateLabwareDialog(tk.Toplevel):
    """Dialog for creating new labware (Plate, ReservoirHolder, PipetteHolder, TipDropzone)"""

    def __init__(self, parent, available_wells, available_reservoirs, available_individual_holders):
        super().__init__(parent)
        self.title("Create New Labware")
        self.geometry("600x700")
        self.result = None

        # Store available low-level components
        self.available_wells = available_wells
        self.available_reservoirs = available_reservoirs
        self.available_individual_holders = available_individual_holders

        # Selected components
        self.selected_well = None
        self.selected_reservoir = None
        self.selected_individual_holder = None
        self.configured_reservoir_template = None

        # Make dialog modal
        self.transient(parent)
        self.grab_set()

        self.create_widgets()

    def launch_mapping_dialog(self):
        """Open the template configuration dialog."""
        # No need to check hooks_x/y here; the holder takes those separately.

        # Use the new dialog
        dialog = ConfigureReservoirTemplateDialog(self, self.available_reservoirs)
        self.wait_window(dialog)

        if dialog.result:
            self.configured_reservoir_template = dialog.result  # Store the template OBJECT

            # The template object may have num_hooks_x/y or hook_ids set for auto-allocation

            is_explicit = hasattr(self.configured_reservoir_template,
                                  'hook_ids') and self.configured_reservoir_template.hook_ids

            if is_explicit:
                config_summary = f"Explicit Hooks: {len(self.configured_reservoir_template.hook_ids)} specified"
            else:
                hx = getattr(self.configured_reservoir_template, 'num_hooks_x', 'Auto-size')
                hy = getattr(self.configured_reservoir_template, 'num_hooks_y', 'Auto-size')
                config_summary = f"Auto-allocate: {hx}x{hy} hooks"

            self.reservoir_config_label.config(text=config_summary, foreground='green')
        else:
            self.configured_reservoir_template = None
            self.reservoir_config_label.config(text="None configured", foreground='red')

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Labware Type Selection
        type_frame = ttk.LabelFrame(main_frame, text="Labware Type", padding="10")
        type_frame.pack(fill=tk.X, pady=5)

        self.labware_type = tk.StringVar(value="Plate")
        types = ["Plate", "ReservoirHolder", "PipetteHolder", "TipDropzone"]

        for lw_type in types:
            ttk.Radiobutton(
                type_frame,
                text=lw_type,
                variable=self.labware_type,
                value=lw_type,
                command=self.on_type_change
            ).pack(anchor='w')

        # Basic Parameters
        basic_frame = ttk.LabelFrame(main_frame, text="Basic Parameters", padding="10")
        basic_frame.pack(fill=tk.X, pady=5)

        # Labware ID
        ttk.Label(basic_frame, text="Labware ID:").grid(row=0, column=0, sticky='w', pady=2)
        self.id_var = tk.StringVar()
        ttk.Entry(basic_frame, textvariable=self.id_var, width = 20).grid(row=0, column=1, pady=2)
        ttk.Label(basic_frame, text="(optional)", font=('Arial', 12, 'italic'), foreground='gray').grid(row=0, column=2,
                                                                                                        sticky='w',
                                                                                                        padx=5)
        # Dimensions
        ttk.Label(basic_frame, text="Size X (mm):").grid(row=1, column=0, sticky='w', pady=2)
        self.size_x_var = tk.StringVar()
        ttk.Entry(basic_frame, textvariable=self.size_x_var, width = 20).grid(row=1, column=1, pady=2)

        ttk.Label(basic_frame, text="Size Y (mm):").grid(row=2, column=0, sticky='w', pady=2)
        self.size_y_var = tk.StringVar()
        ttk.Entry(basic_frame, textvariable=self.size_y_var, width = 20).grid(row=2, column=1, pady=2)

        ttk.Label(basic_frame, text="Size Z (mm):").grid(row=3, column=0, sticky='w', pady=2)
        self.size_z_var = tk.StringVar()
        ttk.Entry(basic_frame, textvariable=self.size_z_var, width = 20).grid(row=3, column=1, pady=2)

        # Offset
        ttk.Label(basic_frame, text="Offset X (mm):").grid(row=4, column=0, sticky='w', pady=2)
        self.offset_x_var = tk.StringVar(value="0.0")
        ttk.Entry(basic_frame, textvariable=self.offset_x_var, width = 20).grid(row=4, column=1, pady=2)

        ttk.Label(basic_frame, text="Offset Y (mm):").grid(row=5, column=0, sticky='w', pady=2)
        self.offset_y_var = tk.StringVar(value="0.0")
        ttk.Entry(basic_frame, textvariable=self.offset_y_var, width = 20).grid(row=5, column=1, pady=2)

        ttk.Label(basic_frame, text="Can be stacked upon:").grid(row=6, column=0, sticky='w', pady=2)
        self.can_be_stacked_upon_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(basic_frame, variable=self.can_be_stacked_upon_var).grid(row=6, column=1, sticky='w', pady=2)
        ttk.Label(basic_frame, text="(optional, default: Unselected = False)", font=('Arial', 12, 'italic'),foreground='gray').grid(row=6, column=2, sticky='w', padx=5)

        # Type-Specific Parameters Frame
        self.specific_frame = ttk.LabelFrame(main_frame, text="Type-Specific Parameters", padding="10")
        self.specific_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # Initialize type-specific fields
        self.create_specific_fields()

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)

        ttk.Button(btn_frame, text="Create", command=self.on_create).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.on_cancel).pack(side=tk.RIGHT)

    def create_specific_fields(self):
        """Create fields specific to the selected labware type"""
        # Clear existing widgets
        for widget in self.specific_frame.winfo_children():
            widget.destroy()

        lw_type = self.labware_type.get()

        if lw_type == "Plate":
            ttk.Label(self.specific_frame, text="Rows (wells in Y):").grid(row=0, column=0, sticky='w', pady=2)
            self.rows_var = tk.StringVar()
            ttk.Entry(self.specific_frame, textvariable=self.rows_var, width=20).grid(row=0, column=1, pady=2)

            ttk.Label(self.specific_frame, text="Columns (wells in X):").grid(row=1, column=0, sticky='w', pady=2)
            self.cols_var = tk.StringVar()
            ttk.Entry(self.specific_frame, textvariable=self.cols_var, width=20).grid(row=1, column=1, pady=2)

            ttk.Label(self.specific_frame, text="Add Height (mm):").grid(row=2, column=0, sticky='w', pady=2)
            self.add_height_var = tk.StringVar()
            ttk.Entry(self.specific_frame, textvariable=self.add_height_var, width=20).grid(row=2, column=1, pady=2)

            ttk.Label(self.specific_frame, text="Remove Height (mm):").grid(row=3, column=0, sticky='w', pady=2)
            self.remove_height_var = tk.StringVar()
            ttk.Entry(self.specific_frame, textvariable=self.remove_height_var, width=20).grid(row=3, column=1, pady=2)

            # Well selection
            well_frame = ttk.Frame(self.specific_frame)
            well_frame.grid(row=4, column=0, columnspan=2, pady=(10, 0), sticky='ew')

            self.well_label = ttk.Label(well_frame, text="Well: Not selected", foreground='red')
            self.well_label.pack(side=tk.LEFT)

            ttk.Button(well_frame, text="Select/Create Well",
                       command=self.select_well).pack(side=tk.RIGHT)

        elif lw_type == "ReservoirHolder":
            # ... (Existing fields for Hooks X, Hooks Y, Add Height, Remove Height) ...
            ttk.Label(self.specific_frame, text="Hooks Across X:").grid(row=0, column=0, sticky='w', pady=2)
            self.hooks_x_var = tk.StringVar(value="7")
            ttk.Entry(self.specific_frame, textvariable=self.hooks_x_var, width=20).grid(row=0, column=1, pady=2)

            ttk.Label(self.specific_frame, text="Hooks Across Y:").grid(row=1, column=0, sticky='w', pady=2)
            self.hooks_y_var = tk.StringVar(value="1")
            ttk.Entry(self.specific_frame, textvariable=self.hooks_y_var, width=20).grid(row=1, column=1, pady=2)

            ttk.Label(self.specific_frame, text="Add Height (mm):").grid(row=2, column=0, sticky='w', pady=2)
            self.add_height_var = tk.StringVar(value="0.0")
            ttk.Entry(self.specific_frame, textvariable=self.add_height_var, width=20).grid(row=2, column=1, pady=2)

            ttk.Label(self.specific_frame, text="Remove Height (mm):").grid(row=3, column=0, sticky='w', pady=2)
            self.remove_height_var = tk.StringVar(value="20.0")
            ttk.Entry(self.specific_frame, textvariable=self.remove_height_var, width=20).grid(row=3, column=1, pady=2)

            # ADDED: Configuration button
            config_frame = ttk.Frame(self.specific_frame)
            config_frame.grid(row=4, column=0, columnspan=3, pady=(10, 0), sticky='ew')

            self.reservoir_config_label = ttk.Label(config_frame, text="None mapped", foreground='red')
            self.reservoir_config_label.pack(side=tk.LEFT, padx=(0, 10))

            ttk.Button(config_frame, text="Map/Configure Reservoirs",
                       command=self.launch_mapping_dialog).pack(side=tk.RIGHT)

        elif lw_type == "PipetteHolder":
            ttk.Label(self.specific_frame, text="Holders Across X:").grid(row=0, column=0, sticky='w', pady=2)
            self.holders_x_var = tk.StringVar()
            ttk.Entry(self.specific_frame, textvariable=self.holders_x_var, width=20).grid(row=0, column=1, pady=2)

            ttk.Label(self.specific_frame, text="Holders Across Y:").grid(row=1, column=0, sticky='w', pady=2)
            self.holders_y_var = tk.StringVar()
            ttk.Entry(self.specific_frame, textvariable=self.holders_y_var, width=20).grid(row=1, column=1, pady=2)

            ttk.Label(self.specific_frame, text="Add Height (mm):").grid(row=2, column=0, sticky='w', pady=2)
            self.add_height_var = tk.StringVar()
            ttk.Entry(self.specific_frame, textvariable=self.add_height_var, width=20).grid(row=2, column=1, pady=2)

            ttk.Label(self.specific_frame, text="Remove Height (mm):").grid(row=3, column=0, sticky='w', pady=2)
            self.remove_height_var = tk.StringVar()
            ttk.Entry(self.specific_frame, textvariable=self.remove_height_var, width=20).grid(row=3, column=1, pady=2)

            # Individual holder selection
            holder_frame = ttk.Frame(self.specific_frame)
            holder_frame.grid(row=4, column=0, columnspan=2, pady=(10, 0), sticky='ew')

            self.holder_label = ttk.Label(holder_frame, text="IndividualPipetteHolder: Not selected", foreground='red')
            self.holder_label.pack(side=tk.LEFT)

            ttk.Button(holder_frame, text="Select/Create Holder",
                       command=self.select_individual_holder).pack(side=tk.RIGHT)

        elif lw_type == "TipDropzone":
            ttk.Label(self.specific_frame, text="Drop Height (mm):").grid(row=0, column=0, sticky='w', pady=2)
            self.drop_height_var = tk.StringVar()
            ttk.Entry(self.specific_frame, textvariable=self.drop_height_var, width=20).grid(row=0, column=1, pady=2)

    def on_type_change(self):
        """Handle labware type change"""
        self.create_specific_fields()

    def select_well(self):
        """Open dialog to select or create a Well"""
        dialog = SelectOrCreateComponentDialog(self, "Well", self.available_wells)
        self.wait_window(dialog)

        if dialog.result:
            self.selected_well = dialog.result
            self.well_label.config(text=f"Well: {self.selected_well.labware_id}", foreground='green')

    def select_individual_holder(self):
        """Open dialog to select or create an IndividualPipetteHolder"""
        dialog = SelectOrCreateComponentDialog(self, "IndividualPipetteHolder", self.available_individual_holders)
        self.wait_window(dialog)

        if dialog.result:
            self.selected_individual_holder = dialog.result
            self.holder_label.config(text=f"Holder: {self.selected_individual_holder.labware_id}", foreground='green')

    def on_create(self):
        """Create the labware"""
        try:
            # Get basic parameters
            labware_id = self.id_var.get() or None
            size_x = float(self.size_x_var.get())
            size_y = float(self.size_y_var.get())
            size_z = float(self.size_z_var.get())
            offset_x = float(self.offset_x_var.get() or "0.0")
            offset_y = float(self.offset_y_var.get() or "0.0")
            offset = (offset_x, offset_y)
            can_be_stacked_upon = self.can_be_stacked_upon_var.get()

            lw_type = self.labware_type.get()

            if lw_type == "Plate":
                if not self.selected_well:
                    messagebox.showerror("Error", "Please select or create a Well")
                    return

                rows = int(self.rows_var.get())
                cols = int(self.cols_var.get())
                add_height = float(self.add_height_var.get())
                remove_height = float(self.remove_height_var.get())

                self.result = Plate(
                    wells_y=rows,
                    wells_x=cols,
                    size_x=size_x,
                    size_y=size_y,
                    size_z=size_z,
                    offset=offset,
                    labware_id=labware_id,
                    well=self.selected_well,
                    add_height=add_height,
                    can_be_stacked_upon=can_be_stacked_upon,
                    remove_height=remove_height
                )

            elif lw_type == "ReservoirHolder":
                # 1. Enforce validation: Must have a configured template
                if self.configured_reservoir_template is None:
                    messagebox.showerror("Error",
                                         "ReservoirHolder must have a configured template. Please click 'Map/Configure Reservoirs'.")
                    return

                # 2. Parse geometry
                hooks_x = int(self.hooks_x_var.get())
                hooks_y = int(self.hooks_y_var.get())
                add_height = float(self.add_height_var.get())
                remove_height = float(self.remove_height_var.get())

                # 3. Instantiate the object
                self.result = ReservoirHolder(
                    hooks_across_x=hooks_x,
                    hooks_across_y=hooks_y,
                    size_x=size_x,
                    size_y=size_y,
                    size_z=size_z,
                    offset=offset,
                    labware_id=labware_id,
                    add_height=add_height,
                    remove_height=remove_height,
                    can_be_stacked_upon=can_be_stacked_upon,
                    # Pass the fully configured template OBJECT
                    reservoir_template=self.configured_reservoir_template
                )

            elif lw_type == "PipetteHolder":
                if not self.selected_individual_holder:
                    messagebox.showerror("Error", "Please select or create an IndividualPipetteHolder")
                    return

                holders_x = int(self.holders_x_var.get())
                holders_y = int(self.holders_y_var.get())
                add_height = float(self.add_height_var.get())
                remove_height = float(self.remove_height_var.get())

                self.result = PipetteHolder(
                    holders_across_x=holders_x,
                    holders_across_y=holders_y,
                    size_x=size_x,
                    size_y=size_y,
                    size_z=size_z,
                    offset=offset,
                    labware_id=labware_id,
                    individual_holder=self.selected_individual_holder,
                    add_height=add_height,
                    remove_height=remove_height,
                    can_be_stacked_upon=can_be_stacked_upon
                )

            elif lw_type == "TipDropzone":
                drop_height = float(self.drop_height_var.get())

                self.result = TipDropzone(
                    size_x=size_x,
                    size_y=size_y,
                    size_z=size_z,
                    offset=offset,
                    labware_id=labware_id,
                    drop_height_relative=drop_height,
                    can_be_stacked_upon=can_be_stacked_upon
                )

            self.destroy()

        except ValueError as e:
            messagebox.showerror("Invalid Input", f"Please check your inputs:\n{str(e)}")

    def on_cancel(self):
        """Cancel dialog"""
        self.result = None
        self.destroy()

class ConfigureReservoirTemplateDialog(tk.Toplevel):
    """
    Dialog to select a single Reservoir template and specify its placement
    parameters (auto-size, specific hooks, or N x M block size).
    """

    def __init__(self, parent, available_reservoirs):
        super().__init__(parent)
        self.title("Select or Create Reservoir")
        self.geometry("500x500")
        self.result = None  # Will hold the fully configured Reservoir object

        self.available_reservoirs = available_reservoirs
        self.selected_reservoir_template = None

        self.transient(parent)
        self.grab_set()

        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- 1. Reservoir Template Selection ---
        ttk.Label(main_frame, text="1. Select an existing Reservoir or create new one",
                  font=('Arial', 14, 'bold')).pack(anchor='w', pady=(0, 5))

        select_frame = ttk.Frame(main_frame)
        select_frame.pack(fill='x', pady=5)

        self.template_label = ttk.Label(select_frame, text="Reservoir: None selected", width=30, relief=tk.SUNKEN,
                                        foreground='red')
        self.template_label.pack(side=tk.LEFT, fill='x', expand=True, padx=(0, 10))
        ttk.Button(select_frame, text="Select/Create Reservoir", command=self.select_reservoir).pack(side=tk.RIGHT)

        # --- 2. Placement Options (Template Overrides) ---
        ttk.Label(main_frame, text="2. Specific Placement (Optional)",
                  font=('Arial', 14, 'bold')).pack(anchor='w', pady=(15, 5))

        placement_frame = ttk.Frame(main_frame, padding="10")
        placement_frame.pack(fill=tk.X, pady=(0, 15))

        # A) Explicit Hook IDs (for fixed, non-repeating placement)
        ttk.Label(placement_frame, text="Explicit Hook IDs (optional, comma-separated for multi-hook reservoirs):",
                  font=('Arial', 12, 'bold')).grid(row=0, column=0, sticky='w', pady=5, columnspan=2)
        self.hook_ids_var = tk.StringVar()
        ttk.Entry(placement_frame, textvariable=self.hook_ids_var).grid(row=1, column=0, columnspan=2, sticky='ew',
                                                                        padx=5, pady=(0, 10))

        ttk.Label(placement_frame, text="* If hook id is provided, the reservoir is only added to the specified hook.\n Otherwise, copies of reservoir populate the entire reservoirHolder * \n").grid(row=2, column=0, columnspan=2,
                                                                               sticky='w', padx=5)
        ttk.Label(placement_frame,
                  text="** Hook Numbering: Right to left, top to bottom.\n" \
                       "Example - 5×2 Reservoir Holder:\n" \
                       "  5   4   3   2   1     (Row 1)\n" \
                       " 10   9   8   7   6     (Row 2) **"
                  ).grid(row=4, column=0, columnspan=2,
            sticky='w', padx=5)

        # --- Control Buttons ---
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x', pady=20, side=tk.BOTTOM)
        ttk.Button(button_frame, text="Save Template Configuration", command=self.on_ok).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.destroy).pack(side=tk.RIGHT)

    def select_reservoir(self):
        """Open dialog to select or create a Reservoir component."""
        # Assume SelectOrCreateComponentDialog exists
        dialog = SelectOrCreateComponentDialog(self.master.master, "Reservoir", self.available_reservoirs)
        self.wait_window(dialog)

        if dialog.result and isinstance(dialog.result, Reservoir):
            self.selected_reservoir_template = dialog.result
            self.template_label.config(text=f"Template: {self.selected_reservoir_template.labware_id}",
                                       foreground='blue')

    def on_ok(self):
        """Process inputs and return the fully configured template object."""
        if not self.selected_reservoir_template:
            messagebox.showerror("Error", "Please select a base Reservoir template.")
            return

        # 1. Start with a deep copy of the template
        final_template = copy.deepcopy(self.selected_reservoir_template)

        # 2. Apply placement overrides/rules to the copy
        try:
            # Explicit hook IDs take precedence
            hook_ids_str = self.hook_ids_var.get().strip()
            if hook_ids_str:
                # Set explicit hook IDs and clear block size variables
                hook_ids = [int(x.strip()) for x in hook_ids_str.split(',') if x.strip()]
                final_template.hook_ids = hook_ids
                # Remove num_hooks attributes to ensure only hook_ids are used
                if hasattr(final_template, 'num_hooks_x'): del final_template.num_hooks_x
                if hasattr(final_template, 'num_hooks_y'): del final_template.num_hooks_y
            else:
                final_template.hook_ids = []  # Ensure it's empty list if not specified

        except ValueError:
            messagebox.showerror("Invalid Input", "Hooks X, Hooks Y, or Hook IDs must be valid integers.")
            return

        # Result is the fully modified template object
        self.result = final_template
        self.destroy()

class EditSlotDialog(tk.Toplevel):
    """Dialog for editing an existing slot"""

    def __init__(self, parent, slot):
        super().__init__(parent)
        self.title(f"Edit Slot: {slot.slot_id}")
        self.geometry("400x400")
        self.slot = slot
        self.result = None

        # Make dialog modal
        self.transient(parent)
        self.grab_set()

        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Parameters frame
        params_frame = ttk.LabelFrame(main_frame, text="Slot Parameters", padding="10")
        params_frame.pack(fill=tk.BOTH, expand=True)

        # Slot ID (read-only display)
        ttk.Label(params_frame, text="Slot ID:").grid(row=0, column=0, sticky='w', pady=5)
        ttk.Label(params_frame, text=self.slot.slot_id, font=('Arial', 10, 'bold')).grid(row=0, column=1, sticky='w',
                                                                                         pady=5)

        # Range X
        ttk.Label(params_frame, text="Range X Min (mm):").grid(row=1, column=0, sticky='w', pady=5)
        self.x_min_var = tk.StringVar(value=str(self.slot.range_x[0]))
        ttk.Entry(params_frame, textvariable=self.x_min_var, width=25).grid(row=1, column=1, pady=5)

        ttk.Label(params_frame, text="Range X Max (mm):").grid(row=2, column=0, sticky='w', pady=5)
        self.x_max_var = tk.StringVar(value=str(self.slot.range_x[1]))
        ttk.Entry(params_frame, textvariable=self.x_max_var, width=25).grid(row=2, column=1, pady=5)

        # Range Y
        ttk.Label(params_frame, text="Range Y Min (mm):").grid(row=3, column=0, sticky='w', pady=5)
        self.y_min_var = tk.StringVar(value=str(self.slot.range_y[0]))
        ttk.Entry(params_frame, textvariable=self.y_min_var, width=25).grid(row=3, column=1, pady=5)

        ttk.Label(params_frame, text="Range Y Max (mm):").grid(row=4, column=0, sticky='w', pady=5)
        self.y_max_var = tk.StringVar(value=str(self.slot.range_y[1]))
        ttk.Entry(params_frame, textvariable=self.y_max_var, width=25).grid(row=4, column=1, pady=5)

        # Range Z
        ttk.Label(params_frame, text="Range Z (mm):").grid(row=5, column=0, sticky='w', pady=5)
        self.z_var = tk.StringVar(value=str(self.slot.range_z))
        ttk.Entry(params_frame, textvariable=self.z_var, width=25).grid(row=5, column=1, pady=5)

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)

        ttk.Button(btn_frame, text="Save", command=self.on_save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.on_cancel).pack(side=tk.RIGHT)

    def on_save(self):
        """Save changes to slot"""
        try:
            x_min = float(self.x_min_var.get())
            x_max = float(self.x_max_var.get())
            y_min = float(self.y_min_var.get())
            y_max = float(self.y_max_var.get())
            z = float(self.z_var.get())

            if x_max <= x_min or y_max <= y_min:
                messagebox.showerror("Error", "Max values must be greater than min values")
                return

            # Update slot
            self.slot.range_x = (x_min, x_max)
            self.slot.range_y = (y_min, y_max)
            self.slot.range_z = z

            self.result = True
            self.destroy()

        except ValueError as e:
            messagebox.showerror("Invalid Input", f"Please check your inputs:\n{str(e)}")

    def on_cancel(self):
        """Cancel dialog"""
        self.result = False
        self.destroy()

class EditLabwareDialog(tk.Toplevel):
    """Enhanced dialog for editing labware with simplified reservoir management"""

    def __init__(self, parent, labware, available_reservoirs=None):
        super().__init__(parent)
        self.title(f"Edit Labware: {labware.labware_id}")
        self.geometry("750x750")

        # Store reference to ORIGINAL labware
        self.original_labware = labware
        self.labware = copy.deepcopy(labware)

        self.available_reservoirs = available_reservoirs or []
        self.result = None

        # Track selected reservoir for removal
        self.selected_reservoir = None
        self.reservoir_widgets = {}  # reservoir -> canvas items

        # Make dialog modal
        self.transient(parent)
        self.grab_set()

        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Info
        info_frame = ttk.LabelFrame(main_frame, text="Labware Info", padding="10")
        info_frame.pack(fill=tk.X, pady=5)

        ttk.Label(info_frame, text=f"ID: {self.labware.labware_id}").pack(anchor='w')
        ttk.Label(info_frame, text=f"Type: {self.labware.__class__.__name__}").pack(anchor='w')

        # Create Notebook (Tabs)
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=5)

        # Tab 1: Basic Properties
        self.create_basic_properties_tab()

        # Tab 2: Manage Reservoirs (only for ReservoirHolder)
        if isinstance(self.labware, ReservoirHolder):
            self.create_reservoir_management_tab()

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)

        ttk.Button(btn_frame, text="Save", command=self.on_save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.on_cancel).pack(side=tk.RIGHT)

    def calculate_requirements_text(self, labware):
        """Calculate and display minimum dimensional requirements"""
        if isinstance(labware, Plate):
            well = labware.well
            offset = labware.offset

            # ✅ Include offsets (matches labware.py validation)
            min_x = round((well.size_x * labware._columns) + (2 * abs(offset[0])), 2)
            min_y = round((well.size_y * labware._rows) + (2 * abs(offset[1])), 2)

            return (f"Minimum dimensions for {labware._columns}×{labware._rows} wells:\n"
                    f"  X: ≥ {min_x}mm ({labware._columns} × {well.size_x}mm + 2×{abs(offset[0])}mm offset)\n"
                    f"  Y: ≥ {min_y}mm ({labware._rows} × {well.size_y}mm + 2×{abs(offset[1])}mm offset)\n"
                    f"  Z: ≥ {well.size_z}mm (well height)")

        elif isinstance(labware, PipetteHolder):
            holder = labware.individual_holder
            offset = labware.offset

            # ✅ Include offsets (matches labware.py validation)
            min_x = round((holder.size_x * labware._columns) + (2 * abs(offset[0])), 2)
            min_y = round((holder.size_y * labware._rows) + (2 * abs(offset[1])), 2)

            return (f"Minimum dimensions for {labware._columns}×{labware._rows} holders:\n"
                    f"  X: ≥ {min_x}mm ({labware._columns} × {holder.size_x}mm + 2×{abs(offset[0])}mm offset)\n"
                    f"  Y: ≥ {min_y}mm ({labware._rows} × {holder.size_y}mm + 2×{abs(offset[1])}mm offset)\n"
                    f"  Z: ≥ {holder.size_z}mm (holder height)")

        elif isinstance(labware, ReservoirHolder):
            reservoirs = labware.get_reservoirs()
            if reservoirs:
                # Find the largest reservoir dimensions
                max_res_x = max(r.size_x for r in reservoirs)
                max_res_y = max(r.size_y for r in reservoirs)
                max_res_z = max(r.size_z for r in reservoirs)

                # Find maximum hook span (how many hooks each reservoir needs)
                max_span_x = 0
                max_span_y = 0
                for r in reservoirs:
                    positions = [labware.hook_id_to_position(hid) for hid in r.hook_ids]
                    cols = [pos[0] for pos in positions]
                    rows = [pos[1] for pos in positions]
                    span_x = max(cols) - min(cols) + 1
                    span_y = max(rows) - min(rows) + 1
                    max_span_x = max(max_span_x, span_x)
                    max_span_y = max(max_span_y, span_y)

                # Calculate minimum hook spacing needed
                min_hook_spacing_x = max_res_x / max_span_x if max_span_x > 0 else 0
                min_hook_spacing_y = max_res_y / max_span_y if max_span_y > 0 else 0

                # Calculate minimum holder dimensions
                min_holder_x = min_hook_spacing_x * labware._columns
                min_holder_y = min_hook_spacing_y * labware._rows

                return (f"Based on placed reservoirs:\n"
                        f"  Minimum hook spacing: {min_hook_spacing_x:.1f}×{min_hook_spacing_y:.1f}mm\n"
                        f"  Minimum holder size: ≥ {min_holder_x:.1f}×{min_holder_y:.1f}mm\n"
                        f"  Z: ≥ {max_res_z}mm (largest reservoir height)")
            else:
                return "No reservoirs placed yet"

        elif isinstance(labware, TipDropzone):
            return "TipDropzone has no child component constraints"

        return "No specific requirements"

    def create_basic_properties_tab(self):
        """Basic properties tab (same as before)"""
        basic_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(basic_tab, text="Basic Properties")

        ttk.Label(basic_tab, text="Size X (mm):").grid(row=0, column=0, sticky='w', pady=5)
        self.size_x_var = tk.StringVar(value=str(self.labware.size_x))
        ttk.Entry(basic_tab, textvariable=self.size_x_var, width=25).grid(row=0, column=1, pady=5)

        ttk.Label(basic_tab, text="Size Y (mm):").grid(row=1, column=0, sticky='w', pady=5)
        self.size_y_var = tk.StringVar(value=str(self.labware.size_y))
        ttk.Entry(basic_tab, textvariable=self.size_y_var, width=25).grid(row=1, column=1, pady=5)

        ttk.Label(basic_tab, text="Size Z (mm):").grid(row=2, column=0, sticky='w', pady=5)
        self.size_z_var = tk.StringVar(value=str(self.labware.size_z))
        ttk.Entry(basic_tab, textvariable=self.size_z_var, width=25).grid(row=2, column=1, pady=5)

        ttk.Label(basic_tab, text="Offset X (mm):").grid(row=3, column=0, sticky='w', pady=5)
        self.offset_x_var = tk.StringVar(value=str(self.labware.offset[0]))
        ttk.Entry(basic_tab, textvariable=self.offset_x_var, width=25).grid(row=3, column=1, pady=5)

        ttk.Label(basic_tab, text="Offset Y (mm):").grid(row=4, column=0, sticky='w', pady=5)
        self.offset_y_var = tk.StringVar(value=str(self.labware.offset[1]))
        ttk.Entry(basic_tab, textvariable=self.offset_y_var, width=25).grid(row=4, column=1, pady=5)

        ttk.Label(basic_tab, text="Can be stacked upon:").grid(row=5, column=0, sticky='w', pady=2)
        self.can_be_stacked_upon_var = tk.BooleanVar(value=self.labware.can_be_stacked_upon)
        ttk.Checkbutton(basic_tab, variable=self.can_be_stacked_upon_var).grid(row=5, column=1, sticky='w', pady=2)

        separator = ttk.Separator(basic_tab, orient='horizontal')
        separator.grid(row=6, column=0, columnspan=2, sticky='ew', pady=10)

        req_frame = ttk.LabelFrame(basic_tab, text="⚠️ Dimensional Requirements", padding="10")
        req_frame.grid(row=7, column=0, columnspan=2, sticky='ew', pady=5)

        req_text = self.calculate_requirements_text(self.labware)
        req_label = ttk.Label(
            req_frame,
            text=req_text,
            justify=tk.LEFT,
            foreground='red',
            font=('Arial',11)
        )
        req_label.pack(anchor='w')

    def create_reservoir_management_tab(self):
        """Simplified reservoir management with visual grid"""
        reservoir_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(reservoir_tab, text="Manage Reservoirs")

        # Top: Canvas with visual hook grid
        canvas_frame = ttk.LabelFrame(reservoir_tab, text="Hook Layout (Click reservoir to select)", padding="10")
        canvas_frame.pack(fill=tk.X, expand=False, pady=(0, 10))

        # Create canvas for drawing with fixed dimensions
        self.hook_canvas = tk.Canvas(canvas_frame, bg='white', height=250, width=650)
        self.hook_canvas.pack(fill=tk.NONE, expand=False)

        # Force canvas to update its size before drawing
        self.hook_canvas.update_idletasks()

        # Draw the hook grid with reservoirs
        self.draw_hook_grid()

        # Bottom: Control buttons
        control_frame = ttk.LabelFrame(reservoir_tab, text="Actions", padding="10")
        control_frame.pack(fill=tk.X)

        btn_container = ttk.Frame(control_frame)
        btn_container.pack(fill=tk.X)

        ttk.Button(
            btn_container,
            text="➕ Place Reservoir at Hook(s)",
            command=self.add_reservoir_dialog
        ).pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        ttk.Button(
            btn_container,
            text="🗑️ Remove Selected Reservoir",
            command=self.remove_selected_reservoir
        ).pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        # Info label
        self.info_label = ttk.Label(control_frame, text="No reservoir selected", foreground='gray')
        self.info_label.pack(pady=(10, 0))

    def draw_hook_grid(self):
        """Draw the hook grid with reservoirs as colored blocks"""
        self.hook_canvas.delete("all")
        self.reservoir_widgets.clear()

        holder = self.labware

        # Calculate dimensions - use explicit canvas size
        canvas_width = self.hook_canvas.winfo_width()
        canvas_height = self.hook_canvas.winfo_height()

        # If canvas not properly rendered yet, use the dimensions we set
        if canvas_width < 100:  # Canvas not ready yet
            canvas_width = 650
        if canvas_height < 100:  # Canvas not ready yet
            canvas_height = 250

        padding = 30
        available_width = canvas_width - 2 * padding
        available_height = canvas_height - 2 * padding

        cell_width = available_width / holder.hooks_across_x
        cell_height = available_height / holder.hooks_across_y

        # Draw empty hook grid first (outlines)
        for row in range(holder.hooks_across_y):
            for col in range(holder.hooks_across_x):
                x1 = padding + col * cell_width
                y1 = padding + row * cell_height
                x2 = x1 + cell_width
                y2 = y1 + cell_height

                # Draw cell outline
                self.hook_canvas.create_rectangle(
                    x1, y1, x2, y2,
                    outline='lightgray',
                    width=1,
                    tags='grid'
                )

                # Draw hook ID (right to left numbering)
                hook_id = holder.position_to_hook_id(holder.hooks_across_x - 1 - col, row)
                self.hook_canvas.create_text(
                    (x1 + x2) / 2, (y1 + y2) / 2,
                    text=str(hook_id),
                    font=('Arial', 10),
                    fill='lightgray',
                    tags='grid'
                )

        # Draw reservoirs as colored blocks
        reservoirs = holder.get_reservoirs()
        colors = ['#FFB6C1', '#87CEEB', '#98FB98', '#FFD700', '#FFA07A', '#DDA0DD', '#F0E68C']

        for idx, reservoir in enumerate(reservoirs):
            color = colors[idx % len(colors)]
            self.draw_reservoir_block(reservoir, color, cell_width, cell_height, padding)

    def draw_reservoir_block(self, reservoir, color, cell_width, cell_height, padding):
        """Draw a reservoir as a colored block spanning its hooks"""
        holder = self.labware

        # Get all hook positions
        positions = [holder.hook_id_to_position(hid) for hid in reservoir.hook_ids]
        cols = [pos[0] for pos in positions]
        rows = [pos[1] for pos in positions]

        min_col, max_col = min(cols), max(cols)
        min_row, max_row = min(rows), max(rows)

        # Calculate bounding box (accounting for right-to-left display)
        # Display col: holder.hooks_across_x - 1 - actual_col
        display_min_col = holder.hooks_across_x - 1 - max_col
        display_max_col = holder.hooks_across_x - 1 - min_col

        x1 = padding + display_min_col * cell_width
        y1 = padding + min_row * cell_height
        x2 = padding + (display_max_col + 1) * cell_width
        y2 = padding + (max_row + 1) * cell_height

        # Draw reservoir block
        rect_id = self.hook_canvas.create_rectangle(
            x1, y1, x2, y2,
            fill=color,
            outline='black',
            width=2,
            tags=('reservoir', f'res_{id(reservoir)}')
        )

        # Draw reservoir label
        text_id = self.hook_canvas.create_text(
            (x1 + x2) / 2, (y1 + y2) / 2,
            text=f"{reservoir.labware_id}\n({len(reservoir.hook_ids)} hooks)",
            font=('Arial', 9, 'bold'),
            tags=('reservoir', f'res_{id(reservoir)}')
        )

        # Store references
        self.reservoir_widgets[reservoir] = (rect_id, text_id)

        # Bind click event
        self.hook_canvas.tag_bind(f'res_{id(reservoir)}', '<Button-1>',
                                  lambda e, r=reservoir: self.select_reservoir(r))

    def select_reservoir(self, reservoir):
        """Select a reservoir for removal"""
        # Clear previous selection
        if self.selected_reservoir and self.selected_reservoir in self.reservoir_widgets:
            rect_id, text_id = self.reservoir_widgets[self.selected_reservoir]
            self.hook_canvas.itemconfig(rect_id, width=2)

        # Set new selection
        self.selected_reservoir = reservoir

        if reservoir in self.reservoir_widgets:
            rect_id, text_id = self.reservoir_widgets[reservoir]
            self.hook_canvas.itemconfig(rect_id, width=4, outline='black')

        # Update info label
        hook_ids_str = ', '.join(map(str, sorted(reservoir.hook_ids)))
        self.info_label.config(
            text=f"Selected: {reservoir.labware_id} at hooks {hook_ids_str}",
            foreground='red'
        )

    def add_reservoir_dialog(self):
        """Open dialog to add reservoir at specific hooks"""
        dialog = PlaceReservoirDialog(self, self.available_reservoirs, self.labware)
        self.wait_window(dialog)

        if dialog.result:
            try:
                reservoir, hook_ids = dialog.result

                # Add the reservoir
                reservoir_copy = copy.deepcopy(reservoir)
                reservoir_copy.hook_ids = hook_ids

                self.labware.place_reservoir(hook_ids, reservoir_copy)

                # Redraw
                self.draw_hook_grid()

                messagebox.showinfo("Success", f"Reservoir '{reservoir_copy.labware_id}' placed at hooks {hook_ids}!")

            except ValueError as e:
                messagebox.showerror("Error", f"Failed to place reservoir:\n{str(e)}")

    def remove_selected_reservoir(self):
        """Remove the currently selected reservoir"""
        if not self.selected_reservoir:
            messagebox.showwarning("No Selection", "Please click on a reservoir to select it first")
            return

        if not messagebox.askyesno(
                "Confirm Remove",
                f"Remove reservoir '{self.selected_reservoir.labware_id}'?"
        ):
            return

        try:
            # Remove using any hook
            self.labware.remove_reservoir(self.selected_reservoir.hook_ids[0])

            self.selected_reservoir = None
            self.info_label.config(text="No reservoir selected", foreground='gray')

            # Redraw
            self.draw_hook_grid()

            messagebox.showinfo("Success", "Reservoir removed!")

        except ValueError as e:
            messagebox.showerror("Error", f"Failed to remove reservoir:\n{str(e)}")

    def validate_labware_dimensions(self, labware, new_size_x, new_size_y, new_size_z, new_offset):
        """Validate that child components still fit after dimension changes"""
        errors = []
        warnings = []

        if isinstance(labware, Plate):
            errors, warnings = self.validate_plate_dimensions(
                labware, new_size_x, new_size_y, new_size_z, new_offset  # ✅ Added new_size_z
            )

        elif isinstance(labware, PipetteHolder):
            errors, warnings = self.validate_pipette_holder_dimensions(
                labware, new_size_x, new_size_y, new_size_z, new_offset  # ✅ Added new_size_z
            )

        elif isinstance(labware, ReservoirHolder):
            errors, warnings = self.validate_reservoir_holder_dimensions(
                labware, new_size_x, new_size_y, new_size_z, new_offset  # ✅ Added new_size_z
            )

        return errors, warnings

    def validate_plate_dimensions(self, plate, new_size_x, new_size_y, new_size_z, new_offset):
        """Validate Plate dimensions against well configuration"""
        errors = []
        warnings = []

        well = plate.well  # Template well
        n_cols = plate._columns
        n_rows = plate._rows

        # ✅ Match labware.py validation exactly
        min_required_x = round((well.size_x * n_cols) + (2 * abs(new_offset[0])), 2)
        min_required_y = round((well.size_y * n_rows) + (2 * abs(new_offset[1])), 2)

        if new_size_x < min_required_x:
            errors.append(
                f"❌ Plate width too small!\n"
                f"   Current: {new_size_x}mm\n"
                f"   Required: {min_required_x:.1f}mm\n"
                f"   ({n_cols} wells × {well.size_x}mm + offsets)"
            )

        if new_size_y < min_required_y:
            errors.append(
                f"❌ Plate length too small!\n"
                f"   Current: {new_size_y}mm\n"
                f"   Required: {min_required_y:.1f}mm\n"
                f"   ({n_rows} wells × {well.size_y}mm + offsets)"
            )

        # ✅ Z-height validation - now new_size_z is available
        if well.size_z > new_size_z:
            errors.append(
                f"❌ Well height exceeds plate height!\n"
                f"   Well height: {well.size_z}mm\n"
                f"   Plate height: {new_size_z}mm"
            )

        # ✅ Warn if wells will be widely spaced
        if new_size_x >= min_required_x and new_size_y >= min_required_y:
            new_spacing_x = (new_size_x - 2 * abs(new_offset[0])) / n_cols
            new_spacing_y = (new_size_y - 2 * abs(new_offset[1])) / n_rows

            if new_spacing_x > well.size_x * 1.5 or new_spacing_y > well.size_y * 1.5:
                warnings.append(
                    f"⚠️ Wells will be widely spaced:\n"
                    f"   X spacing: {new_spacing_x:.1f}mm (well size: {well.size_x}mm)\n"
                    f"   Y spacing: {new_spacing_y:.1f}mm (well size: {well.size_y}mm)"
                )

        return errors, warnings

    def validate_pipette_holder_dimensions(self, holder, new_size_x, new_size_y, new_size_z, new_offset):
        """Validate PipetteHolder dimensions against individual holder configuration"""
        errors = []
        warnings = []

        individual = holder.individual_holder  # Template
        n_x = holder._columns
        n_y = holder._rows

        # ✅ Match labware.py validation exactly
        min_required_x = round((individual.size_x * n_x) + (2 * abs(new_offset[0])), 2)
        min_required_y = round((individual.size_y * n_y) + (2 * abs(new_offset[1])), 2)

        if new_size_x < min_required_x:
            errors.append(
                f"❌ PipetteHolder width too small!\n"
                f"   Current: {new_size_x}mm\n"
                f"   Required: {min_required_x:.1f}mm\n"
                f"   ({n_x} holders × {individual.size_x}mm + offsets)"
            )

        if new_size_y < min_required_y:
            errors.append(
                f"❌ PipetteHolder length too small!\n"
                f"   Current: {new_size_y}mm\n"
                f"   Required: {min_required_y:.1f}mm\n"
                f"   ({n_y} holders × {individual.size_y}mm + offsets)"
            )

        # ✅ Z-height validation - now new_size_z is available
        if individual.size_z > new_size_z:
            errors.append(
                f"❌ Individual holder height exceeds PipetteHolder height!\n"
                f"   Holder height: {individual.size_z}mm\n"
                f"   PipetteHolder height: {new_size_z}mm"
            )

        return errors, warnings

    def validate_reservoir_holder_dimensions(self, holder, new_size_x, new_size_y, new_size_z, new_offset):
        """Validate ReservoirHolder dimensions against placed reservoirs"""
        errors = []
        warnings = []

        hooks_x = holder._columns
        hooks_y = holder._rows

        if hooks_x == 0 or hooks_y == 0:
            return errors, warnings

        # Calculate new hook spacing
        new_hook_spacing_x = new_size_x / hooks_x
        new_hook_spacing_y = new_size_y / hooks_y

        # Check each placed reservoir
        reservoirs = holder.get_reservoirs()
        for reservoir in reservoirs:
            # Get dimensions of area this reservoir occupies
            positions = [holder.hook_id_to_position(hid) for hid in reservoir.hook_ids]
            cols = [pos[0] for pos in positions]
            rows = [pos[1] for pos in positions]

            width_in_hooks = max(cols) - min(cols) + 1
            length_in_hooks = max(rows) - min(rows) + 1

            # Calculate space available for this reservoir with new dimensions
            available_x = width_in_hooks * new_hook_spacing_x
            available_y = length_in_hooks * new_hook_spacing_y

            # Check if reservoir fits
            if reservoir.size_x > available_x:
                errors.append(
                    f"❌ Reservoir '{reservoir.labware_id}' won't fit!\n"
                    f"   Reservoir width: {reservoir.size_x}mm\n"
                    f"   Available space: {available_x:.1f}mm\n"
                    f"   (spans {width_in_hooks} hooks × {new_hook_spacing_x:.1f}mm spacing)"
                )

            if reservoir.size_y > available_y:
                errors.append(
                    f"❌ Reservoir '{reservoir.labware_id}' won't fit!\n"
                    f"   Reservoir length: {reservoir.size_y}mm\n"
                    f"   Available space: {available_y:.1f}mm\n"
                    f"   (spans {length_in_hooks} hooks × {new_hook_spacing_y:.1f}mm spacing)"
                )

            # ✅ Z-height validation - now new_size_z is available
            if reservoir.size_z > new_size_z:
                errors.append(
                    f"❌ Reservoir '{reservoir.labware_id}' height exceeds holder height!\n"
                    f"   Reservoir height: {reservoir.size_z}mm\n"
                    f"   Holder height: {new_size_z}mm"
                )

        return errors, warnings

    def on_save(self):
        """Save changes with validation"""
        try:
            # Get new values
            new_size_x = float(self.size_x_var.get())
            new_size_y = float(self.size_y_var.get())
            new_size_z = float(self.size_z_var.get())
            new_offset = (float(self.offset_x_var.get()), float(self.offset_y_var.get()))
            new_can_be_stacked = bool(self.can_be_stacked_upon_var.get())

            # ⭐ VALIDATE BEFORE SAVING ⭐
            errors, warnings = self.validate_labware_dimensions(
                self.labware, new_size_x, new_size_y, new_size_z, new_offset
            )

            # Show errors and prevent saving
            if errors:
                error_msg = "Cannot save changes:\n\n" + "\n\n".join(errors)
                messagebox.showerror("Validation Error", error_msg)
                return

            # Show warnings and ask for confirmation
            if warnings:
                warning_msg = "Warnings detected:\n\n" + "\n\n".join(warnings)
                warning_msg += "\n\nDo you want to proceed anyway?"

                if not messagebox.askyesno("Validation Warning", warning_msg, icon='warning'):
                    return

            # Apply changes to the WORKING COPY first
            self.labware.size_x = new_size_x
            self.labware.size_y = new_size_y
            self.labware.size_z = new_size_z
            self.labware.offset = new_offset
            self.labware.can_be_stacked_upon = new_can_be_stacked

            # NOW copy all changes back to the ORIGINAL labware
            self.original_labware.size_x = self.labware.size_x
            self.original_labware.size_y = self.labware.size_y
            self.original_labware.size_z = self.labware.size_z
            self.original_labware.offset = self.labware.offset
            self.original_labware.can_be_stacked_upon = self.labware.can_be_stacked_upon

            # For ReservoirHolder, copy the reservoir configuration
            if isinstance(self.labware, ReservoirHolder):
                self.original_labware._ReservoirHolder__hook_to_reservoir = copy.deepcopy(
                    self.labware._ReservoirHolder__hook_to_reservoir
                )

            self.result = True
            self.destroy()

        except ValueError as e:
            messagebox.showerror("Invalid Input", f"Please check your inputs:\n{str(e)}")

    def on_cancel(self):
        """Cancel without saving"""
        self.result = False
        self.destroy()

class PlaceReservoirDialog(tk.Toplevel):
    """Dialog to select reservoir and specify hook IDs for placement"""

    def __init__(self, parent, available_reservoirs, holder):
        super().__init__(parent)
        self.title("Place Reservoir at Hook(s)")
        self.geometry("500x650")
        self.result = None

        self.available_reservoirs = available_reservoirs
        self.holder = holder

        self.transient(parent)
        self.grab_set()

        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)


        # Reservoir selection
        reservoir_frame = ttk.LabelFrame(main_frame, text="Step 1: Select Reservoir", padding="10")
        reservoir_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # Listbox with scrollbar
        list_container = ttk.Frame(reservoir_frame)
        list_container.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_container, orient=tk.VERTICAL)
        self.reservoir_listbox = tk.Listbox(list_container, yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.reservoir_listbox.yview)

        self.reservoir_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Populate
        for res in self.available_reservoirs:
            display = f"{res.labware_id} ({res.size_x}×{res.size_y}×{res.size_z} mm, {res.capacity}µL)"
            self.reservoir_listbox.insert(tk.END, display)

        self.reservoir_listbox.bind('<<ListboxSelect>>', self.on_reservoir_select)

        # Create new button
        ttk.Button(reservoir_frame, text="➕ Create New Reservoir",
                   command=self.create_new_reservoir).pack(fill=tk.X, pady=(5, 0))

        # Preview
        preview_frame = ttk.LabelFrame(main_frame, text="Reservoir Preview", padding="10")
        preview_frame.pack(fill=tk.X, pady=5)

        self.preview_text = tk.Text(preview_frame, height=5, wrap=tk.WORD)
        self.preview_text.pack(fill=tk.BOTH, expand=True)

        # Hook IDs input
        hooks_frame = ttk.LabelFrame(main_frame, text="Step 2: Enter Hook ID(s)", padding="10")
        hooks_frame.pack(fill=tk.X, pady=5)

        ttk.Label(hooks_frame, text="Hook ID(s) (comma-separated):").pack(anchor='w')
        self.hook_ids_var = tk.StringVar()

        ttk.Entry(hooks_frame, textvariable=self.hook_ids_var, width=40).pack(fill=tk.X, pady=(5, 5))
        ttk.Label(
            hooks_frame,
            text="Examples:\n"
                 "  • Single hook: 7\n"
                 "  • Multiple hooks: 7,6,5",
            font=('Arial', 12, 'italic'),
            foreground='white'
        ).pack(anchor='w')

        # Available hooks info
        available_hooks = self.holder.get_available_hooks()
        ttk.Label(
            hooks_frame,
            text=f"Available hooks: {sorted(available_hooks)}",
            font=('Arial', 12),
            foreground='white'
        ).pack(anchor='w', pady=(5, 0))

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)

        ttk.Button(btn_frame, text="Place", command=self.on_place).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.on_cancel).pack(side=tk.RIGHT)

    def on_reservoir_select(self, event=None):
        """Update preview when selection changes"""
        selection = self.reservoir_listbox.curselection()
        if not selection:
            return

        reservoir = self.available_reservoirs[selection[0]]

        info = f"ID: {reservoir.labware_id}\n"
        info += f"Size: {reservoir.size_x} × {reservoir.size_y} × {reservoir.size_z} mm\n"
        info += f"Capacity: {reservoir.capacity} µL\n"
        info += f"Content: {reservoir.get_content_summary()}\n"
        if reservoir.shape:
            info += f"Shape: {reservoir.shape}"

        self.preview_text.delete(1.0, tk.END)
        self.preview_text.insert(1.0, info)

    def create_new_reservoir(self):
        """Open dialog to create new reservoir"""
        dialog = CreateLowLevelLabwareDialog(self, initial_type="Reservoir")
        self.wait_window(dialog)

        if dialog.result:
            # Add to list
            self.available_reservoirs.append(dialog.result)

            # Update listbox
            display = f"{dialog.result.labware_id} ({dialog.result.size_x}×{dialog.result.size_y}×{dialog.result.size_z} mm)"
            self.reservoir_listbox.insert(tk.END, display)

            # Select it
            self.reservoir_listbox.selection_clear(0, tk.END)
            self.reservoir_listbox.selection_set(tk.END)
            self.reservoir_listbox.see(tk.END)
            self.on_reservoir_select()

    def on_place(self):
        """Validate and place reservoir"""
        # Check reservoir selection
        selection = self.reservoir_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Reservoir", "Please select a reservoir")
            return

        reservoir = self.available_reservoirs[selection[0]]

        # Parse hook IDs
        hook_ids_str = self.hook_ids_var.get().strip()
        if not hook_ids_str:
            messagebox.showwarning("No Hooks", "Please enter hook ID(s)")
            return

        try:
            # Parse comma-separated hook IDs
            hook_ids = [int(h.strip()) for h in hook_ids_str.split(',') if h.strip()]

            if not hook_ids:
                messagebox.showwarning("Invalid Input", "Please enter at least one valid hook ID")
                return

            # Validate hook IDs
            for hid in hook_ids:
                if hid < 1 or hid > self.holder.total_hooks:
                    messagebox.showerror(
                        "Invalid Hook ID",
                        f"Hook ID {hid} is out of range (1-{self.holder.total_hooks})"
                    )
                    return

            # Check if hooks are available
            occupied_hooks = [h for h in hook_ids if self.holder.get_hook_to_reservoir_map()[h] is not None]
            if occupied_hooks:
                messagebox.showerror(
                    "Hooks Occupied",
                    f"The following hooks are already occupied: {occupied_hooks}\n\n"
                    f"Available hooks: {sorted(self.holder.get_available_hooks())}"
                )
                return

            # Success
            self.result = (reservoir, hook_ids)
            self.destroy()

        except ValueError:
            messagebox.showerror("Invalid Input", "Hook IDs must be numbers separated by commas")

    def on_cancel(self):
        """Cancel"""
        self.result = None
        self.destroy()

class CreateSlotDialog(tk.Toplevel):
    """Dialog for creating a new slot"""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Create New Slot")
        self.geometry("400x400")
        self.result = None

        # Make dialog modal
        self.transient(parent)
        self.grab_set()

        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Parameters frame
        params_frame = ttk.LabelFrame(main_frame, text="Slot Parameters", padding="10")
        params_frame.pack(fill=tk.BOTH, expand=True)

        # Slot ID
        ttk.Label(params_frame, text="Slot ID:").grid(row=0, column=0, sticky='w', pady=5)
        self.id_var = tk.StringVar()
        ttk.Entry(params_frame, textvariable=self.id_var, width=25).grid(row=0, column=1, pady=5)

        # Range X
        ttk.Label(params_frame, text="Range X Min (mm):").grid(row=1, column=0, sticky='w', pady=5)
        self.x_min_var = tk.StringVar(value="0")
        ttk.Entry(params_frame, textvariable=self.x_min_var, width=25).grid(row=1, column=1, pady=5)

        ttk.Label(params_frame, text="Range X Max (mm):").grid(row=2, column=0, sticky='w', pady=5)
        self.x_max_var = tk.StringVar(value="150")
        ttk.Entry(params_frame, textvariable=self.x_max_var, width=25).grid(row=2, column=1, pady=5)

        # Range Y
        ttk.Label(params_frame, text="Range Y Min (mm):").grid(row=3, column=0, sticky='w', pady=5)
        self.y_min_var = tk.StringVar(value="0")
        ttk.Entry(params_frame, textvariable=self.y_min_var, width=25).grid(row=3, column=1, pady=5)

        ttk.Label(params_frame, text="Range Y Max (mm):").grid(row=4, column=0, sticky='w', pady=5)
        self.y_max_var = tk.StringVar(value="100")
        ttk.Entry(params_frame, textvariable=self.y_max_var, width=25).grid(row=4, column=1, pady=5)

        # Range Z
        ttk.Label(params_frame, text="Range Z (mm):").grid(row=5, column=0, sticky='w', pady=5)
        self.z_var = tk.StringVar(value="100")
        ttk.Entry(params_frame, textvariable=self.z_var, width=25).grid(row=5, column=1, pady=5)

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)

        ttk.Button(btn_frame, text="Create", command=self.on_create).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.on_cancel).pack(side=tk.RIGHT)

    def on_create(self):
        """Create the slot object"""
        try:
            slot_id = self.id_var.get()
            if not slot_id:
                messagebox.showerror("Error", "Slot ID is required")
                return

            x_min = float(self.x_min_var.get())
            x_max = float(self.x_max_var.get())
            y_min = float(self.y_min_var.get())
            y_max = float(self.y_max_var.get())
            z = float(self.z_var.get())

            if x_max <= x_min or y_max <= y_min:
                messagebox.showerror("Error", "Max values must be greater than min values")
                return

            self.result = Slot(
                range_x=(x_min, x_max),
                range_y=(y_min, y_max),
                range_z=z,
                slot_id=slot_id
            )

            self.destroy()

        except ValueError as e:
            messagebox.showerror("Invalid Input", f"Please check your inputs:\n{str(e)}")

    def on_cancel(self):
        """Cancel dialog"""
        self.result = None
        self.destroy()

class AddLabwareToSlotDialog(tk.Toplevel):
    """Dialog for adding labware to a slot"""

    def __init__(self, parent, deck, labware):
        super().__init__(parent)
        self.title(f"Add {labware.labware_id} to Slot")
        self.geometry("450x450")
        self.deck = deck
        self.labware = labware
        self.result = None

        # Make dialog modal
        self.transient(parent)
        self.grab_set()

        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Info
        info_frame = ttk.LabelFrame(main_frame, text="Labware Info", padding="10")
        info_frame.pack(fill=tk.X, pady=5)

        ttk.Label(info_frame, text=f"ID: {self.labware.labware_id}").pack(anchor='w')
        ttk.Label(info_frame, text=f"Type: {self.labware.__class__.__name__}").pack(anchor='w')
        ttk.Label(info_frame, text=f"Size: {self.labware.size_x} x {self.labware.size_y} x {self.labware.size_z}").pack(
            anchor='w')

        # Placement parameters
        params_frame = ttk.LabelFrame(main_frame, text="Placement", padding="10")
        params_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # Slot selection
        ttk.Label(params_frame, text="Select Slot:").grid(row=0, column=0, sticky='w', pady=5)
        self.slot_var = tk.StringVar()
        slot_combo = ttk.Combobox(
            params_frame,
            textvariable=self.slot_var,
            values=list(self.deck.slots.keys()),
            state='readonly',
            width=22
        )
        slot_combo.grid(row=0, column=1, pady=5)
        if self.deck.slots:
            slot_combo.current(0)

        # Min Z
        ttk.Label(params_frame, text="Min Z (mm):").grid(row=1, column=0, sticky='w', pady=5)
        self.min_z_var = tk.StringVar(value="0")
        ttk.Entry(params_frame, textvariable=self.min_z_var, width=25).grid(row=1, column=1, pady=5)

        # Optional spacing for grid-based labware
        ttk.Label(params_frame, text="X Spacing (mm):").grid(row=2, column=0, sticky='w', pady=5)
        self.x_spacing_var = tk.StringVar()
        ttk.Entry(params_frame, textvariable=self.x_spacing_var, width=25).grid(row=2, column=1, pady=5)

        ttk.Label(params_frame, text="Y Spacing (mm):").grid(row=3, column=0, sticky='w', pady=5)
        self.y_spacing_var = tk.StringVar()
        ttk.Entry(params_frame, textvariable=self.y_spacing_var, width=25).grid(row=3, column=1, pady=5)

        ttk.Label(params_frame, text="(Leave spacing blank for auto)", font=('Arial', 8, 'italic')).grid(
            row=4, column=0, columnspan=2, pady=2
        )

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)

        ttk.Button(btn_frame, text="Add", command=self.on_add).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.on_cancel).pack(side=tk.RIGHT)

    def on_add(self):
        """Add labware to slot"""
        try:
            slot_id = self.slot_var.get()
            if not slot_id:
                messagebox.showerror("Error", "Please select a slot")
                return

            min_z = float(self.min_z_var.get())

            x_spacing = None
            y_spacing = None

            if self.x_spacing_var.get():
                x_spacing = float(self.x_spacing_var.get())
            if self.y_spacing_var.get():
                y_spacing = float(self.y_spacing_var.get())

            self.result = {
                'slot_id': slot_id,
                'min_z': min_z,
                'x_spacing': x_spacing,
                'y_spacing': y_spacing
            }

            self.destroy()

        except ValueError as e:
            messagebox.showerror("Invalid Input", f"Please check your inputs:\n{str(e)}")

    def on_cancel(self):
        """Cancel dialog"""
        self.result = None
        self.destroy()

class CollapsibleFrame(ttk.Frame):
    """A frame that can be collapsed/expanded by clicking on its title."""
    def __init__(self, parent, text, **kw):
        super().__init__(parent, **kw)

        # Title bar
        self.title_frame = ttk.Frame(self)
        self.title_frame.pack(fill="x", expand=False)

        self.toggle_btn = ttk.Label(self.title_frame, text="▶", width=2)
        self.toggle_btn.pack(side="left", padx=5)

        self.title_lbl = ttk.Label(self.title_frame, text=text, font=("Arial", 14, "bold"))
        self.title_lbl.pack(side="left", pady=2)

        # Content frame (initially hidden)
        self.content_frame = ttk.Frame(self)
        self.content_frame.pack(fill="both", expand=True)
        self.content_frame.pack_forget()  # start collapsed

        # Bind click
        self.title_frame.bind("<Button-1>", self.toggle)
        self.toggle_btn.bind("<Button-1>", self.toggle)
        self.title_lbl.bind("<Button-1>", self.toggle)

        self.is_expanded = False

    def toggle(self, event=None):
        if self.is_expanded:
            self.content_frame.pack_forget()
            self.toggle_btn.config(text="▶")
        else:
            self.content_frame.pack(fill="both", expand=True)
            self.toggle_btn.config(text="▼")
        self.is_expanded = not self.is_expanded

class DeckGUI:
    def __init__(self, deck=None):
        self.root = tk.Tk()
        self.root.title("Deck Editor")
        self.root.geometry("1200x800")

        # Create or use provided deck
        if deck is None:
            self.deck = Deck(range_x=(0, 500), range_y=(0, 400), deck_id="default_deck")
        else:
            self.deck = deck

        # State
        self.selected_item = None
        self.dragging = None
        self.drag_data = {"x": 0, "y": 0}
        self.scale = 1.0
        self.offset_x = 50
        self.offset_y = 50

        # Created but not yet placed items
        self.unplaced_labware = []
        self.unplaced_slots = []

        # Storage for low-level labware components
        self.available_wells = []
        self.available_reservoirs = []
        self.available_individual_holders = []

        # View toggles for slots and labware
        self.slot_view_mode = tk.StringVar(value="unplaced")  # "placed" or "unplaced"
        self.labware_view_mode = tk.StringVar(value="unplaced")  # "placed" or "unplaced"

        self.setup_ui()
        # Delay initial draw until window is fully rendered
        self.root.after(100, lambda: self.draw_deck(auto_scale=True))

    def setup_ui(self):
        # Menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Deck", command=self.new_deck)
        file_menu.add_command(label="Save Deck", command=self.save_deck)
        file_menu.add_command(label="Load Deck", command=self.load_deck)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Refresh", command=lambda: self.draw_deck(auto_scale=True))
        view_menu.add_command(label="Zoom In", command=self.zoom_in)
        view_menu.add_command(label="Zoom Out", command=self.zoom_out)

        # Main layout
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Left panel - Canvas
        canvas_frame = ttk.Frame(main_frame)
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Canvas with scrollbars
        self.canvas = tk.Canvas(
            canvas_frame,
            bg='white',
            scrollregion=(0, 0, 2000, 2000)
        )

        h_scroll = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        v_scroll = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)

        self.canvas.configure(xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)

        self.canvas.grid(row=0, column=0, sticky='nsew')
        h_scroll.grid(row=1, column=0, sticky='ew')
        v_scroll.grid(row=0, column=1, sticky='ns')

        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)

        # Right panel - Tabbed interface
        right_panel_container = ttk.Frame(main_frame, width=400)
        right_panel_container.pack(side=tk.RIGHT, fill=tk.BOTH, padx=5, pady=5)
        right_panel_container.pack_propagate(False)

        # Create notebook (tabs) for right panel
        self.right_panel_notebook = ttk.Notebook(right_panel_container)
        self.right_panel_notebook.pack(fill=tk.BOTH, expand=True)

        # ===== TAB 1: DECK EDITOR =====
        deck_editor_tab = ttk.Frame(self.right_panel_notebook)
        self.right_panel_notebook.add(deck_editor_tab, text="Deck Editor")

        # Create canvas and scrollbar for deck editor tab
        deck_canvas = tk.Canvas(deck_editor_tab, bg='#f0f0f0', highlightthickness=0)
        deck_scrollbar = ttk.Scrollbar(deck_editor_tab, orient=tk.VERTICAL, command=deck_canvas.yview)

        # Create a frame inside the canvas to hold all the controls
        control_frame = ttk.Frame(deck_canvas)

        # Configure canvas scrolling
        deck_canvas.configure(yscrollcommand=deck_scrollbar.set)

        # Pack scrollbar and canvas
        deck_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        deck_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Create window in canvas to hold the frame
        deck_canvas_window = deck_canvas.create_window((0, 0), window=control_frame, anchor='nw')

        # Configure scrolling region when frame size changes
        def configure_deck_scroll_region(event=None):
            deck_canvas.configure(scrollregion=deck_canvas.bbox("all"))
            # Make sure the frame fills the canvas width
            canvas_width = deck_canvas.winfo_width()
            if canvas_width > 1:  # Only update if canvas has been drawn
                deck_canvas.itemconfig(deck_canvas_window, width=canvas_width)

        control_frame.bind('<Configure>', configure_deck_scroll_region)
        deck_canvas.bind('<Configure>', configure_deck_scroll_region)

        # Enable mousewheel scrolling
        def on_deck_mousewheel(event):
            deck_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def bind_deck_mousewheel(event):
            deck_canvas.bind_all("<MouseWheel>", on_deck_mousewheel)

        def unbind_deck_mousewheel(event):
            deck_canvas.unbind_all("<MouseWheel>")

        deck_canvas.bind('<Enter>', bind_deck_mousewheel)
        deck_canvas.bind('<Leave>', unbind_deck_mousewheel)

        # Deck info
        self.deck_info_collapsible = CollapsibleFrame(control_frame, text="Deck Info")
        self.deck_info_collapsible.pack(fill=tk.X, pady=5, padx=5)

        # Content inside collapsible frame
        self.deck_info_label = ttk.Label(
            self.deck_info_collapsible.content_frame,
            text="",
            justify=tk.LEFT,
            padding=10
        )
        self.deck_info_label.pack(fill=tk.X, anchor='w')
        # Info panel
        self.info_frame = ttk.LabelFrame(control_frame, text="Selection Info", padding=10)
        self.info_frame.pack(fill=tk.BOTH, pady=5, padx=5)

        self.info_text = tk.Text(self.info_frame, height=10, wrap=tk.WORD)
        self.info_text.pack(fill=tk.BOTH, expand=True)

        # Control buttons
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(fill=tk.X, pady=5, padx=5)

        ttk.Button(btn_frame, text="Refresh", command=lambda: self.draw_deck(auto_scale=True)).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="Clear Selection", command=self.clear_selection).pack(fill=tk.X, pady=2)

        # ===== SLOTS SECTION WITH TOGGLE =====
        slots_main_frame = ttk.LabelFrame(control_frame, text="Slots", padding=10)
        slots_main_frame.pack(fill=tk.X, pady=5, padx=5)

        # View mode selector
        view_selector_frame = ttk.Frame(slots_main_frame)
        view_selector_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Radiobutton(
            view_selector_frame,
            text="Placed",
            variable=self.slot_view_mode,
            value="placed",
            command=self.update_slots_list
        ).pack(side=tk.LEFT, padx=5)

        ttk.Radiobutton(
            view_selector_frame,
            text="Unplaced",
            variable=self.slot_view_mode,
            value="unplaced",
            command=self.update_slots_list
        ).pack(side=tk.LEFT, padx=5)

        # Single listbox for both placed and unplaced
        self.slots_listbox = tk.Listbox(slots_main_frame, height=6)
        self.slots_listbox.pack(fill=tk.X)
        self.slots_listbox.bind('<<ListboxSelect>>', self.on_slot_select)
        self.slots_listbox.bind('<Double-Button-1>', self.on_slot_double_click)

        # Buttons frame that changes based on view mode
        self.slots_button_frame = ttk.Frame(slots_main_frame)
        self.slots_button_frame.pack(fill=tk.X, pady=(5, 0))

        # We'll update this dynamically
        self.update_slots_buttons()


        # ===== LABWARE SECTION WITH TOGGLE =====
        labware_main_frame = ttk.LabelFrame(control_frame, text="Labware", padding=10)
        labware_main_frame.pack(fill=tk.X, pady=5, padx=5)

        # View mode selector
        labware_view_selector_frame = ttk.Frame(labware_main_frame)
        labware_view_selector_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Radiobutton(
            labware_view_selector_frame,
            text="Placed",
            variable=self.labware_view_mode,
            value="placed",
            command=self.update_labware_list
        ).pack(side=tk.LEFT, padx=5)

        ttk.Radiobutton(
            labware_view_selector_frame,
            text="Unplaced",
            variable=self.labware_view_mode,
            value="unplaced",
            command=self.update_labware_list
        ).pack(side=tk.LEFT, padx=5)

        # Single listbox for both placed and unplaced
        self.labware_listbox = tk.Listbox(labware_main_frame, height=6)
        self.labware_listbox.pack(fill=tk.X)
        self.labware_listbox.bind('<<ListboxSelect>>', self.on_labware_select)
        self.labware_listbox.bind('<Double-Button-1>', self.on_labware_double_click)

        # Buttons frame that changes based on view mode
        self.labware_button_frame = ttk.Frame(labware_main_frame)
        self.labware_button_frame.pack(fill=tk.X, pady=(5, 0))

        # update this dynamically
        self.update_labware_buttons()

        # Canvas bindings
        self.canvas.bind("<Button-1>", self.on_canvas_fallback_click)
        self.canvas.bind("<Triple-Button-1>", self.on_canvas_triple_click)

        # Create the Create tab in the right panel
        self.create_low_level_para_tab()
        self.create_operations_tab()

    def update_slots_buttons(self):
        """Update buttons based on current slot view mode"""
        # Clear existing buttons
        for widget in self.slots_button_frame.winfo_children():
            widget.destroy()

        if self.slot_view_mode.get() == "placed":
            # Show "Unplace Slot" button for placed slots
            ttk.Button(
                self.slots_button_frame,
                text="Unplace Slot",
                command=self.unplace_selected_slot
            ).pack(fill=tk.X, pady=2)
        else:
            # Show "Place Slot", "Edit", and "Delete" buttons for unplaced slots
            ttk.Button(
                self.slots_button_frame,
                text="Place on Deck",
                command=self.place_selected_unplaced_slot
            ).pack(fill=tk.X, pady=2)
            ttk.Button(
                self.slots_button_frame,
                text="Edit",
                command=self.edit_selected_unplaced_slot
            ).pack(fill=tk.X, pady=2)
            ttk.Button(
                self.slots_button_frame,
                text="Create Slot",
                command=self.create_slot
            ).pack(fill=tk.X, pady=2)
            ttk.Button(
                self.slots_button_frame,
                text="Delete",
                command=self.delete_selected_unplaced_slot
            ).pack(fill=tk.X, pady=2)

    def update_labware_buttons(self):
        """Update buttons based on current labware view mode"""
        # Clear existing buttons
        for widget in self.labware_button_frame.winfo_children():
            widget.destroy()

        if self.labware_view_mode.get() == "placed":
            # Show "Unplace Labware" button for placed labware
            ttk.Button(
                self.labware_button_frame,
                text="Unplace Labware",
                command=self.unplace_selected_labware
            ).pack(fill=tk.X, pady=2)
        else:
            # Show "Place on Slot", "Edit", and "Delete" buttons for unplaced labware
            ttk.Button(
                self.labware_button_frame,
                text="Place on Slot on Deck",
                command=self.place_selected_unplaced
            ).pack(fill=tk.X, pady=2)
            ttk.Button(
                self.labware_button_frame,
                text="Edit",
                command=self.edit_selected_unplaced_labware
            ).pack(fill=tk.X, pady=2)
            ttk.Button(
                self.labware_button_frame,
                text="Create",
                command=self.create_labware,
            ).pack(fill=tk.X, pady=2)
            ttk.Button(
                self.labware_button_frame,
                text="Delete",
                command=self.delete_selected_unplaced_labware
            ).pack(fill=tk.X, pady=2)

    def update_slots_list(self):
        """Update the slots listbox based on current view mode"""
        self.slots_listbox.delete(0, tk.END)
        self.update_slots_buttons()

        if self.slot_view_mode.get() == "placed":
            # Show placed slots
            for slot_id in sorted(self.deck.slots.keys()):
                self.slots_listbox.insert(tk.END, slot_id)
        else:
            # Show unplaced slots
            for slot in self.unplaced_slots:
                self.slots_listbox.insert(tk.END, slot.slot_id)

    def update_labware_list(self):
        """Update the labware listbox based on current view mode"""
        self.labware_listbox.delete(0, tk.END)
        self.update_labware_buttons()

        if self.labware_view_mode.get() == "placed":
            # Show placed labware
            for lw_id in sorted(self.deck.labware.keys()):
                self.labware_listbox.insert(tk.END, lw_id)
        else:
            # Show unplaced labware
            for lw in self.unplaced_labware:
                self.labware_listbox.insert(tk.END, lw.labware_id)

    def create_low_level_para_tab(self):
        """Create the Create tab"""

        create_tab = ttk.Frame(self.right_panel_notebook)
        self.right_panel_notebook.add(create_tab, text="Low level parameters")

        # Create canvas and scrollbar for create tab
        create_canvas = tk.Canvas(create_tab, bg='#f0f0f0', highlightthickness=0)
        create_scrollbar = ttk.Scrollbar(create_tab, orient=tk.VERTICAL, command=create_canvas.yview)

        # Create a frame inside the canvas to hold all the controls
        create_control_frame = ttk.Frame(create_canvas)

        # Configure canvas scrolling
        create_canvas.configure(yscrollcommand=create_scrollbar.set)

        # Pack scrollbar and canvas
        create_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        create_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Create window in canvas to hold the frame
        create_canvas_window = create_canvas.create_window((0, 0), window=create_control_frame, anchor='nw')

        # Configure scrolling region when frame size changes
        def configure_create_scroll_region(event=None):
            create_canvas.configure(scrollregion=create_canvas.bbox("all"))
            canvas_width = create_canvas.winfo_width()
            if canvas_width > 1:
                create_canvas.itemconfig(create_canvas_window, width=canvas_width)

        create_control_frame.bind('<Configure>', configure_create_scroll_region)
        create_canvas.bind('<Configure>', configure_create_scroll_region)

        # Enable mousewheel scrolling
        def on_create_mousewheel(event):
            create_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def bind_create_mousewheel(event):
            create_canvas.bind_all("<MouseWheel>", on_create_mousewheel)

        def unbind_create_mousewheel(event):
            create_canvas.unbind_all("<MouseWheel>")

        create_canvas.bind('<Enter>', bind_create_mousewheel)
        create_canvas.bind('<Leave>', unbind_create_mousewheel)

        # === SELECTION INFO PANEL ===
        self.create_info_frame = ttk.LabelFrame(create_control_frame, text="Selection Info", padding=10)
        self.create_info_frame.pack(fill=tk.BOTH, pady=5, padx=5)

        self.create_info_text = tk.Text(self.create_info_frame, height=10, wrap=tk.WORD)
        self.create_info_text.pack(fill=tk.BOTH, expand=True)

        # === CONTROL BUTTONS ===
        create_btn_frame = ttk.Frame(create_control_frame)
        create_btn_frame.pack(fill=tk.X, pady=5, padx=5)

        ttk.Button(create_btn_frame, text="Clear Selection", command=self.clear_selection).pack(fill=tk.X, pady=2)

        # === CREATE SECTIONS ===
        # Low-Level Labware section
        low_level_section = ttk.LabelFrame(create_control_frame, text="Low-Level Labware", padding=15)
        low_level_section.pack(fill=tk.X, pady=10, padx=5)

        # LLL type selector (radio buttons)
        lll_type_frame = ttk.Frame(low_level_section)
        lll_type_frame.pack(fill=tk.X, pady=(0, 5))

        separator = ttk.Separator(low_level_section, orient='horizontal')
        separator.pack(fill=tk.X, pady=5)

        self.lll_type = tk.StringVar(value="Well")
        types = ["Well", "Reservoir", "IndividualPipetteHolder"]

        for lll_type in types:
            ttk.Radiobutton(
                lll_type_frame,
                text=lll_type,
                variable=self.lll_type,
                value=lll_type,
                command=self.update_lll_list
            ).pack(fill=tk.X, anchor=tk.W, pady=2, padx=5)

        # Listbox for LLL
        self.lll_listbox = tk.Listbox(low_level_section, height=6)
        self.lll_listbox.pack(fill=tk.X)
        self.lll_listbox.bind('<<ListboxSelect>>', self.on_lll_select)

        # Buttons frame for LLL actions
        lll_btn_frame = ttk.Frame(low_level_section)
        lll_btn_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Button(lll_btn_frame, text="Create Low-Level Lw", command=self.create_low_level_labware).pack( expand=True, fill=tk.X, padx=2)
        ttk.Button(lll_btn_frame, text="Delete Selected", command=self.delete_selected_lll).pack( expand=True, fill=tk.X, padx=2)

        pipettor_section = ttk.LabelFrame(create_control_frame, text="Pipettor Configuration", padding=15)
        pipettor_section.pack(fill=tk.X, pady=10, padx=5)

        # Tip Volume Selection
        tip_vol_frame = ttk.Frame(pipettor_section)
        tip_vol_frame.pack(fill=tk.X, pady=5)

        ttk.Label(tip_vol_frame, text="Tip Volume:", font=('Arial', 13, 'bold')).pack(side=tk.LEFT, padx=(0, 10))

        self.tip_volume_var = tk.IntVar(value=1000)
        ttk.Radiobutton(tip_vol_frame, text="200 µL", variable=self.tip_volume_var, value=200).pack(side=tk.LEFT,
                                                                                                    padx=5)
        ttk.Radiobutton(tip_vol_frame, text="1000 µL", variable=self.tip_volume_var, value=1000).pack(side=tk.LEFT,
                                                                                                      padx=5)

        # Multichannel Checkbox
        multichannel_frame = ttk.Frame(pipettor_section)
        multichannel_frame.pack(fill=tk.X, pady=5)

        self.multichannel_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            multichannel_frame,
            text="Multichannel (8 tips)",
            variable=self.multichannel_var
        ).pack(side=tk.LEFT)

        # Initialize Hardware Checkbox
        init_frame = ttk.Frame(pipettor_section)
        init_frame.pack(fill=tk.X, pady=5)

        self.initialize_hw_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            init_frame,
            text="initialize",
            variable=self.initialize_hw_var
        ).pack(side=tk.LEFT)

        # Optional Tip Length
        tip_length_frame = ttk.Frame(pipettor_section)
        tip_length_frame.pack(fill=tk.X, pady=5)

        # First line: label and entry
        input_line = ttk.Frame(tip_length_frame)
        input_line.pack(fill=tk.X)

        ttk.Label(input_line, text="Tip Length (mm):").pack(side=tk.LEFT, padx=(0, 5))
        self.tip_length_var = tk.StringVar(value="")
        ttk.Entry(input_line, textvariable=self.tip_length_var, width=10).pack(side=tk.LEFT)

        # Second line: help text
        ttk.Label(tip_length_frame, text="(leave empty for default)",
                  foreground='gray', font=('Arial', 11)).pack(anchor='w', padx=(0, 0))

        # Separator
        separator = ttk.Separator(pipettor_section, orient='horizontal')
        separator.pack(fill=tk.X, pady=10)

        # Initialize Button
        ttk.Button(
            pipettor_section,
            text="🤖 Connect and Configure Pipettor",
            command=self.initialize_pipettor
        ).pack(fill=tk.X, pady=5)

        # Status Display
        self.pipettor_status_frame = ttk.LabelFrame(pipettor_section, text="Pipettor Status", padding=10)
        self.pipettor_status_frame.pack(fill=tk.X, pady=5)

        self.pipettor_status_label = ttk.Label(
            self.pipettor_status_frame,
            text="Not initialized",
            foreground='gray'
        )
        self.pipettor_status_label.pack(anchor='w')

    def update_pipettor_status(self):
        """Update the pipettor status display"""
        if hasattr(self, 'pipettor_status_label'):
            status_text = self.get_pipettor_status_text()

            if hasattr(self, 'pipettor') and self.pipettor is not None:
                if self.pipettor.has_tips:
                    tip_content = self.pipettor.get_tip_status()
                    status_text += f"\nContent: {tip_content['content_summary']}"

                self.pipettor_status_label.config(text=status_text, foreground='green')
            else:
                self.pipettor_status_label.config(text=status_text, foreground='gray')

    #todo
    def initialize_pipettor(self):
        """Initialize the pipettor with selected parameters"""
        try:
            # Get parameters
            tip_volume = self.tip_volume_var.get()
            multichannel = self.multichannel_var.get()
            initialize = self.initialize_hw_var.get()

            # Get optional tip length
            tip_length_str = self.tip_length_var.get().strip()
            tip_length = float(tip_length_str) if tip_length_str else None

            # Validate deck exists
            if not hasattr(self, 'deck') or self.deck is None:
                messagebox.showerror("Error", "Deck must be created before initializing pipettor")
                return

            # Create pipettor
            self.pipettor = PipettorPlus(
                tip_volume=tip_volume,
                multichannel=multichannel,
                initialize=initialize,
                deck=self.deck,
                tip_length=tip_length
            )

            # Update status display
            mode = "Multichannel (8 tips)" if multichannel else "Single channel"
            tip_info = f"{tip_volume}µL tips"
            tip_length_info = f", tip length: {tip_length}mm" if tip_length else ""
            hw_status = "initialized" if initialize else "not initialized"

            status_text = f"✓ {mode}, {tip_info}{tip_length_info}\nHardware: {hw_status}"

            self.pipettor_status_label.config(
                text=status_text,
                foreground='green'
            )

            messagebox.showinfo("Success", f"Pipettor initialized successfully!\n\n{status_text}")

        except ValueError as e:
            messagebox.showerror("Invalid Input", f"Invalid tip length value:\n{str(e)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to initialize pipettor:\n{str(e)}")
            self.pipettor_status_label.config(
                text=f"✗ Initialization failed: {str(e)}",
                foreground='red'
            )

    def get_pipettor_status_text(self) -> str:
        """Get a readable status string for the pipettor"""
        if not hasattr(self, 'pipettor') or self.pipettor is None:
            return "Not initialized"

        mode = "Multichannel" if self.pipettor.multichannel else "Single channel"
        tips = "Has tips" if self.pipettor.has_tips else "No tips"
        tip_volume = self.pipettor.tip_volume

        return f"{mode} ({tip_volume}µL) - {tips}"

    def create_operations_tab(self):
        """Create an empty Operations tab placeholder for future development."""
        operations_tab = ttk.Frame(self.right_panel_notebook)
        self.right_panel_notebook.add(operations_tab, text="Operations")

        # Add a simple label to confirm the tab is present and ready for code
        ttk.Label(
            operations_tab,
            text="Operations Tab\n(Code to be added by developer)",
            font=('Arial', 12),
            anchor=tk.CENTER,
            justify=tk.CENTER,
            padding=20
        ).pack(expand=True, fill=tk.BOTH)

    def delete_selected_lll(self):
        """Delete the selected low-level labware"""
        selection = self.lll_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a low-level labware to delete")
            return

        index = selection[0]
        lll_type = self.lll_type.get()
        if lll_type == "Well":
            component = self.available_wells[index]
            if messagebox.askyesno("Confirm Delete",
                                   f"Are you sure you want to delete Well '{component.labware_id or 'Unnamed'}'?"):
                del self.available_wells[index]
                messagebox.showinfo("Success", f"{lll_type} deleted!")

        elif lll_type == "Reservoir":
            component = self.available_reservoirs[index]
            if messagebox.askyesno("Confirm Delete",
                                   f"Are you sure you want to delete Reservoir '{component.labware_id or 'Unnamed'}'?"):
                del self.available_reservoirs[index]
                messagebox.showinfo("Success", f"{lll_type} deleted!")

        elif lll_type == "IndividualPipetteHolder":
            component = self.available_individual_holders[index]
            if messagebox.askyesno("Confirm Delete",
                                   f"Are you sure you want to delete IndividualPipetteHolder '{component.labware_id or 'Unnamed'}'?"):
                del self.available_individual_holders[index]
                messagebox.showinfo("Success", f"{lll_type} deleted!")
        else:
            return

        self.update_lll_list()
        self.create_info_text.delete(1.0, tk.END)

    def update_lll_list(self):
        """Update the LLL listbox based on selected type"""
        self.lll_listbox.delete(0, tk.END)
        lll_type = self.lll_type.get()

        if lll_type == "Well":
            for well in self.available_wells:
                self.lll_listbox.insert(tk.END, well.labware_id or f"Well {len(self.available_wells)}")
        elif lll_type == "Reservoir":
            for res in self.available_reservoirs:
                self.lll_listbox.insert(tk.END, res.labware_id or f"Reservoir {len(self.available_reservoirs)}")
        elif lll_type == "IndividualPipetteHolder":
            for holder in self.available_individual_holders:
                self.lll_listbox.insert(tk.END, holder.labware_id or f"Holder {len(self.available_individual_holders)}")

    def on_lll_select(self, event=None):
        """Handle LLL listbox selection"""
        selection = self.lll_listbox.curselection()
        if selection:
            index = selection[0]
            lll_type = self.lll_type.get()
            if lll_type == "Well":
                component = self.available_wells[index]
            elif lll_type == "Reservoir":
                component = self.available_reservoirs[index]
            elif lll_type == "IndividualPipetteHolder":
                component = self.available_individual_holders[index]
            else:
                return

            info = f"{lll_type}: {component.labware_id or 'Unnamed'}\n\n"
            info += f"Size X: {component.size_x} mm\n"
            info += f"Size Y: {component.size_y} mm\n"
            info += f"Size Z: {component.size_z} mm\n"
            info += f"Offset: {component.offset}\n"

            if hasattr(component, 'capacity'):
                info += f"Capacity: {component.capacity} µL\n"
            if hasattr(component, 'shape'):
                info += f"Shape: {component.shape or 'None'}\n"
            if hasattr(component, 'content'):
                info += f"Content: {component.content or 'None'}\n"
            if hasattr(component, 'is_occupied'):
                info += f"Occupied: {component.is_occupied}\n"

            self.create_info_text.delete(1.0, tk.END)
            self.create_info_text.insert(1.0, info)

    def update_info_in_both_tabs(self, text):
        """Update info text in both Deck Editor and Create Labware tabs"""
        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(1.0, text)
        self.create_info_text.delete(1.0, tk.END)
        self.create_info_text.insert(1.0, text)

    def create_low_level_labware(self):
        """Open dialog to create low-level labware components and update UI."""

        # Get the currently selected type from radio buttons
        selected_type = self.lll_type.get()

        # Pass it to the dialog as initial_type
        dialog = CreateLowLevelLabwareDialog(self.root, initial_type=selected_type)
        self.root.wait_window(dialog)

        if dialog.result:
            component = dialog.result
            # 2. Add to appropriate list and show success message
            if isinstance(component, Well):
                self.available_wells.append(component)
                messagebox.showinfo("Success",
                                    f"Well '{component.labware_id}' created!\nYou can now use it when creating a Plate.")
            elif isinstance(component, Reservoir):
                self.available_reservoirs.append(component)
                messagebox.showinfo("Success",
                                    f"Reservoir '{component.labware_id}' created!\nYou can now use it when creating a ReservoirHolder.")
            elif isinstance(component, IndividualPipetteHolder):
                self.available_individual_holders.append(component)
                messagebox.showinfo("Success",
                                    f"IndividualPipetteHolder '{component.labware_id}' created!\nYou can now use it when creating a PipetteHolder.")

            # 3. Update the listbox in the main 'Create Labware' tab
            # This function will clear and repopulate self.lll_listbox
            # using the now updated self.available_X lists based on self.lll_type.get().
            self.update_lll_list()

    def create_labware(self):
        """Open dialog to create new labware"""
        dialog = CreateLabwareDialog(self.root, self.available_wells, self.available_reservoirs,
                                     self.available_individual_holders)
        self.root.wait_window(dialog)

        if dialog.result:
            new_labware = dialog.result
            print(new_labware.to_dict())
            # Store newly created component if needed
            if isinstance(dialog.result, Plate) and dialog.selected_well:
                if dialog.selected_well not in self.available_wells:
                    self.available_wells.append(dialog.selected_well)
            elif isinstance(dialog.result, PipetteHolder) and dialog.selected_individual_holder:
                if dialog.selected_individual_holder not in self.available_individual_holders:
                    self.available_individual_holders.append(dialog.selected_individual_holder)

            self.unplaced_labware.append(dialog.result)
            self.labware_view_mode.set("unplaced")
            self.update_labware_list()
            self.select_newly_created_labware(new_labware)
            messagebox.showinfo("Success",
                                f"Labware '{dialog.result.labware_id}' created!\nSwitch to 'Unplaced' view to place it on a slot.")

    def select_newly_created_labware(self, labware_component):
        """Selects the newly created Labware in the main Labware listbox."""

        # 1. Build the text as it appears in self.labware_listbox (labware_id)
        # 2. Iterate through the listbox items to find a match
        # 3. Clear previous selection and select the new item
        # 4. Trigger the selection handler to update the info panel
        display_text = labware_component.labware_id

        list_items = self.labware_listbox.get(0, tk.END)
        for i, item in enumerate(list_items):
            if item == display_text:
                self.labware_listbox.selection_clear(0, tk.END)
                self.labware_listbox.selection_set(i)
                self.labware_listbox.see(i)  # Scroll to the item
                self.on_labware_select()
                break

    def update_deck_info(self):
        """Update deck info display"""
        info = f"ID: {self.deck.deck_id}\n"
        info += f"Range X: {self.deck.range_x}\n"
        info += f"Range Y: {self.deck.range_y}\n"
        info += f"Range Z: {self.deck.range_z}\n"
        info += f"Slots: {len(self.deck.slots)}\n"
        info += f"Labware: {len(self.deck.labware)}"
        self.deck_info_label.config(text=info)

    def new_deck(self):
        """Create a new deck"""
        deck_id = simpledialog.askstring("New Deck", "Enter Deck ID:", initialvalue="new_deck")
        if not deck_id:
            return

        # Ask for dimensions
        x_max = simpledialog.askfloat("Deck Size", "Enter X range (max mm):", initialvalue=500)
        y_max = simpledialog.askfloat("Deck Size", "Enter Y range (max mm):", initialvalue=400)
        z_max = simpledialog.askfloat("Deck Size", "Enter Z range (max mm):", initialvalue=500)

        if x_max and y_max and z_max:
            self.deck = Deck(range_x=(0, x_max), range_y=(0, y_max), range_z=z_max, deck_id=deck_id)
            self.unplaced_labware = []
            self.unplaced_slots = []
            self.available_wells = []
            self.available_reservoirs = []
            self.available_individual_holders = []
            self.draw_deck()
            messagebox.showinfo("Success", "New deck created!")

    def create_slot(self):
        """Open dialog to create a new slot"""
        dialog = CreateSlotDialog(self.root)
        self.root.wait_window(dialog)

        if dialog.result:
            new_slot = dialog.result
            self.unplaced_slots.append(new_slot)

            if self.slot_view_mode.get() == "unplaced":
                self.update_slots_list()
                self.select_newly_created_slot(new_slot)

            messagebox.showinfo("Success",
                                f"Slot created!\nclick 'Place Slot' to add it to the deck.")

    def select_newly_created_slot(self, slot_component):
        """Selects the newly created Slot in the main Slots listbox."""

        # 1. Build the text exactly as it appears in self.slots_listbox
        display_text = slot_component.slot_id

        # 2. Iterate through the listbox items to find a match
        list_items = self.slots_listbox.get(0, tk.END)
        for i, item in enumerate(list_items):
            if item == display_text:
                # 3. Clear previous selection and select the new item
                self.slots_listbox.selection_clear(0, tk.END)
                self.slots_listbox.selection_set(i)
                self.slots_listbox.see(i)  # Scroll to the item

                # 4. Trigger the selection handler to update the info panel
                # Assuming you have an on_slot_select method defined:
                self.on_slot_select()
                break

    def place_labware(self, labware):
        """Place unplaced labware on deck"""
        dialog = AddLabwareToSlotDialog(self.root, self.deck, labware)
        self.root.wait_window(dialog)

        if dialog.result:
            try:
                self.deck.add_labware(
                    labware,
                    dialog.result['slot_id'],
                    dialog.result['min_z'],
                    dialog.result['x_spacing'],
                    dialog.result['y_spacing']
                )
                self.unplaced_labware.remove(labware)
                self.draw_deck()
                messagebox.showinfo("Success",
                                    f"Labware '{labware.labware_id}' placed on slot '{dialog.result['slot_id']}'!")
            except ValueError as e:
                messagebox.showerror("Error", str(e))

    def calculate_scale(self):
        """Auto-calculate scale to maximize deck in canvas
        Coordinate system: (0,0) at top-right
        """
        canvas_width = self.canvas.winfo_width() or 800
        canvas_height = self.canvas.winfo_height() or 600

        deck_width = self.deck.range_x[1] - self.deck.range_x[0]
        deck_height = self.deck.range_y[1] - self.deck.range_y[0]

        # Adaptive margins
        margin = max(40, min(50, int(min(canvas_width, canvas_height) * 0.02)))

        scale_x = (canvas_width - 2 * margin) / deck_width
        scale_y = (canvas_height - 2 * margin) / deck_height

        self.scale = min(scale_x, scale_y)

        # For top-right origin, offset_x is from the right edge
        self.offset_x = margin
        self.offset_y = margin

    def mm_to_canvas(self, x, y):
        """Convert mm coordinates to canvas pixels
        Coordinate system: (0,0) at top-right
        X increases: right → left
        Y increases: top → bottom
        """
        canvas_width = self.canvas.winfo_width() or 300

        # Flip X-axis: subtract from right edge
        canvas_x = canvas_width - (x * self.scale + self.offset_x)
        canvas_y = y * self.scale + self.offset_y

        return (canvas_x, canvas_y)

    def canvas_to_mm(self, cx, cy):
        """Convert canvas pixels to mm coordinates
        Coordinate system: (0,0) at top-right
        """
        canvas_width = self.canvas.winfo_width() or 300

        # Reverse the X-axis flip
        mm_x = (canvas_width - cx - self.offset_x) / self.scale
        mm_y = (cy - self.offset_y) / self.scale

        return (mm_x, mm_y)

    def draw_deck(self, auto_scale = False):
        """Draw the entire deck"""
        self.canvas.delete("all")
        if auto_scale:
            self.calculate_scale()

        # Draw grid
        self.draw_grid()

        # Draw deck boundary
        x1, y1 = self.mm_to_canvas(self.deck.range_x[0], self.deck.range_y[0])
        x2, y2 = self.mm_to_canvas(self.deck.range_x[1], self.deck.range_y[1])
        self.canvas.create_rectangle(x1, y1, x2, y2, outline='black', width=3, tags='deck_boundary')

        self.draw_corner_labels()

        # Draw slots
        for slot_id, slot in self.deck.slots.items():
            self.draw_slot(slot_id, slot)

        # Draw labware
        for lw_id, lw in self.deck.labware.items():
            if lw.position:
                self.draw_labware(lw_id, lw)

        # Update lists and info
        self.update_slots_list()
        self.update_labware_list()
        self.update_deck_info()

    def draw_corner_labels(self):
        """Draw coordinate labels at the four corners of the deck with backgrounds"""
        x_min, x_max = self.deck.range_x
        y_min, y_max = self.deck.range_y

        corners = [
            # (mm_x, mm_y, label_text, anchor, color)
            (x_min, y_min, f"({x_min}, {y_min})\nORIGIN, right corner", 'se', 'red'),
            (x_max, y_min, f"({x_max}, {y_min})", 'sw', 'blue'),
            (x_min, y_max, f"({x_min}, {y_max})", 'ne', 'blue'),
            (x_max, y_max, f"({x_max}, {y_max})", 'nw', 'blue'),
        ]

        for mm_x, mm_y, label, anchor, color in corners:
            canvas_x, canvas_y = self.mm_to_canvas(mm_x, mm_y)

            # Draw corner marker circle
            r = 5
            self.canvas.create_oval(
                canvas_x - r, canvas_y - r,
                canvas_x + r, canvas_y + r,
                fill=color,
                outline='white',
                width=2,
                tags='corner_marker'
            )

            # Calculate text position with offset
            offset = 10
            anchor_offsets = {
                'se': (offset, -offset),  # move below-right corner (outside)
                'sw': (-offset, -offset),  # move below-left corner
                'ne': (offset, offset),  # move above-right corner
                'nw': (-offset, offset)  # move above-left corner
            }

            dx, dy = anchor_offsets[anchor]
            text_x, text_y = canvas_x + dx, canvas_y + dy

            # Draw background rectangle for text
            text_id = self.canvas.create_text(
                text_x, text_y,
                text=label,
                font=('Arial', 9, 'bold'),
                fill=color,
                anchor=anchor,
                tags='corner_label'
            )

            # Get text bounding box and draw background
            bbox = self.canvas.bbox(text_id)
            if bbox:
                padding = 3
                self.canvas.create_rectangle(
                    bbox[0] - padding, bbox[1] - padding,
                    bbox[2] + padding, bbox[3] + padding,
                    fill='white',
                    outline=color,
                    width=1,
                    tags='corner_label_bg'
                )
                # Raise text above background
                self.canvas.tag_raise(text_id)

        top_center_mm = ((x_min + x_max) / 2, y_min)
        top_center_canvas = self.mm_to_canvas(*top_center_mm)
        self.canvas.create_text(
            top_center_canvas[0], top_center_canvas[1] - 20,
            text="X-axis (right to left)",
            font=('Arial', 14, 'italic'),
            fill='green',
            tags='axis_label'
        )

        # Y-axis label (at right center)
        right_center_mm = (x_min, (y_min + y_max) / 2)
        right_center_canvas = self.mm_to_canvas(*right_center_mm)
        self.canvas.create_text(
            right_center_canvas[0] + 20, right_center_canvas[1],
            text="Y-axis\n(Top to Bottom)",
            font=('Arial', 14, 'italic'),
            fill='green',
            angle=270,  # Rotated text
            tags='axis_label'
        )

    def draw_grid(self):
        """Draw background grid"""
        grid_spacing = 50  # mm

        # Vertical lines
        x = self.deck.range_x[0]
        while x <= self.deck.range_x[1]:
            x1, y1 = self.mm_to_canvas(x, self.deck.range_y[0])
            x2, y2 = self.mm_to_canvas(x, self.deck.range_y[1])
            self.canvas.create_line(x1, y1, x2, y2, fill='lightgray', dash=(2, 4), tags='grid')
            x += grid_spacing

        # Horizontal lines
        y = self.deck.range_y[0]
        while y <= self.deck.range_y[1]:
            x1, y1 = self.mm_to_canvas(self.deck.range_x[0], y)
            x2, y2 = self.mm_to_canvas(self.deck.range_x[1], y)
            self.canvas.create_line(x1, y1, x2, y2, fill='lightgray', dash=(2, 4), tags='grid')
            y += grid_spacing

    def draw_slot(self, slot_id, slot):
        """Draw a slot"""
        x1, y1 = self.mm_to_canvas(slot.range_x[0], slot.range_y[0])
        x2, y2 = self.mm_to_canvas(slot.range_x[1], slot.range_y[1])

        # Draw slot rectangle
        self.canvas.create_rectangle(
            x1, y1, x2, y2,
            outline='blue',
            width=2,
            fill='lightblue',
            stipple='gray50',
            tags=f'slot_{slot_id}'
        )

        # Draw slot label
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        self.canvas.create_text(
            cx, cy,
            text=slot_id,
            font=('Arial', 10, 'bold'),
            tags=f'slot_{slot_id}'
        )

        # Make clickable
        self.canvas.tag_bind(f'slot_{slot_id}', '<Button-1>',
                             lambda e, sid=slot_id: self.select_slot(sid))

    def draw_labware(self, lw_id, lw):
        """Draw labware"""
        if not lw.position:
            return

        x1, y1 = self.mm_to_canvas(lw.position[0], lw.position[1])
        x2, y2 = self.mm_to_canvas(lw.position[0] + lw.size_x, lw.position[1] + lw.size_y)

        # Draw labware rectangle
        self.canvas.create_rectangle(
            x1, y1, x2, y2,
            outline='red',
            width=2,
            fill='lightcoral',
            stipple='gray25',
            tags=f'labware_{lw_id}'
        )

        # Draw labware label
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        self.canvas.create_text(
            cx, cy,
            text=f"{lw_id}\n{lw.__class__.__name__}",
            font=('Arial', 8),
            tags=f'labware_{lw_id}'
        )

        # Make clickable
        self.canvas.tag_bind(f'labware_{lw_id}', '<Button-1>',
                             lambda e, lid=lw_id: self.select_labware(lid))
    # Event handlers
    def on_canvas_fallback_click(self, event):
        """Used for clearing selection or starting drag on placed labware."""
        item = self.canvas.find_closest(event.x, event.y)[0]
        tags = self.canvas.gettags(item)

        # Check if the clicked item has *any* bound ID tag (slot or labware)
        is_identified_item = any(t.startswith('slot_') or t.startswith('labware_') for t in tags)

        if is_identified_item:
            # If the item has an ID tag, it means the binding in draw_X was already run.
            # We only need to check if it's placed labware to enable dragging.

            # Since you have the labware ID in the tag 'labware_ID', you can extract it:
            labware_tag = next((t for t in tags if t.startswith('labware_')), None)

            if labware_tag:
                lw_id = labware_tag.split('_', 1)[1]
                if lw_id in self.deck.labware:  # Ensure it is a placed item
                    self.dragging = lw_id
                    self.drag_data["x"] = event.x
                    self.drag_data["y"] = event.y
        else:
            # If no ID tag is present (clicked on grid, boundary, or background)
            self.clear_selection()

    def on_canvas_triple_click(self, event):
        """Show context menu on canvas (FIXED)"""
        item = self.canvas.find_closest(event.x, event.y)[0]
        tags = self.canvas.gettags(item)

        # 1. Initialize variables
        lw_id = None
        slot_id = None

        # 2. Extract ID based on known prefixes (Robust Logic)
        for t in tags:
            if t.startswith('labware_'):
                # Extract the ID after the first underscore
                lw_id = t.split('_', 1)[1]
            elif t.startswith('slot_'):
                # Extract the ID after the first underscore
                slot_id = t.split('_', 1)[1]

        menu = tk.Menu(self.root, tearoff=0)

        # 3. Populate Menu based on found ID
        if lw_id:
            menu.add_command(label=f"Info",
                             command=lambda: self.select_labware(lw_id))
            menu.add_separator()
            menu.add_command(label=f"Unplace {lw_id}",
                             command=lambda: self.unplace_selected_labware(lw_id))

        elif slot_id:
            menu.add_command(label=f"Info",
                             command=lambda: self.select_slot(slot_id))
            menu.add_separator()
            menu.add_command(label=f"Unplace Slot {slot_id}",
                             command=lambda: self.unplace_selected_slot(slot_id))

        # 4. Display Menu only if commands were added
        if menu.index(tk.END) is not None:
            menu.post(event.x_root, event.y_root)

    def on_slot_select(self, event = None):
        """Handle slot listbox selection"""
        selection = self.slots_listbox.curselection()
        if selection:
            slot_id_or_index = selection[0]
            if self.slot_view_mode.get() == "placed":
                # Get slot_id from placed slots
                slot_id = self.slots_listbox.get(slot_id_or_index)
                self.select_slot(slot_id)
            else:
                # Get slot from unplaced slots list
                if slot_id_or_index < len(self.unplaced_slots):
                    slot = self.unplaced_slots[slot_id_or_index]
                    self.show_unplaced_slot_info(slot)

    def on_slot_double_click(self, event):
        """Handle double click on slot"""
        if self.slot_view_mode.get() == "unplaced":
            self.place_selected_unplaced_slot()

    def on_labware_select(self, event = None):
        """Handle labware listbox selection"""
        selection = self.labware_listbox.curselection()
        if selection:
            lw_id_or_index = selection[0]
            if self.labware_view_mode.get() == "placed":
                # Get lw_id from placed labware
                lw_id = self.labware_listbox.get(lw_id_or_index)
                self.select_labware(lw_id)
            else:
                # Get labware from unplaced labware list
                if lw_id_or_index < len(self.unplaced_labware):
                    lw = self.unplaced_labware[lw_id_or_index]
                    self.show_unplaced_labware_info(lw)

    def on_labware_double_click(self, event):
        """Handle double click on labware"""
        if self.labware_view_mode.get() == "unplaced":
            self.place_selected_unplaced()

    def show_unplaced_slot_info(self, slot):
        """Show info for an unplaced slot"""
        info = f"Slot: {slot.slot_id}\n\n"
        info += f"Range X: {slot.range_x}\n"
        info += f"Range Y: {slot.range_y}\n"
        info += f"Range Z: {slot.range_z}\n\n"
        info += "Status: Unplaced"

        self.update_info_in_both_tabs(info)

    def show_unplaced_labware_info(self, lw):
        """Show info for unplaced labware"""
        info = f"Labware: {lw.labware_id}\n\n"
        info += f"Type: {lw.__class__.__name__}\n"
        info += f"Size X: {lw.size_x} mm\n"
        info += f"Size Y: {lw.size_y} mm\n"
        info += f"Size Z: {lw.size_z} mm\n"
        info += f"Offset: {lw.offset}\n\n"
        info += "Status: Unplaced"

        # Add type-specific info
        if isinstance(lw, Plate):
            info += f"\nRows: {lw._rows}\n"
            info += f"Columns: {lw._columns}\n"
        elif isinstance(lw, ReservoirHolder):
            info += f"\nHooks X: {lw.hooks_across_x}\n"
            info += f"Hooks Y: {lw.hooks_across_y}\n"
        elif isinstance(lw, PipetteHolder):
            info += f"\nHolders X: {lw.holders_across_x}\n"
            info += f"Holders Y: {lw.holders_across_y}\n"

        self.update_info_in_both_tabs(info)

    # Slot management methods
    def place_selected_unplaced_slot(self):
        """Place selected unplaced slot on deck"""
        selection = self.slots_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a slot to place")
            return

        slot = self.unplaced_slots[selection[0]]

        # Check if slot ID already exists
        if slot.slot_id in self.deck.slots:
            messagebox.showerror("Error", f"Slot '{slot.slot_id}' already exists on deck")
            return

        # Check if slot fits within deck boundaries
        errors = self.validate_slot_placement(slot)
        if errors:
            messagebox.showerror("Placement Error", "\n".join(errors))
            return

        # Add slot to deck
        self.deck.add_slots([slot])
        self.unplaced_slots.remove(slot)

        self.draw_deck()
        messagebox.showinfo("Success", f"Slot '{slot.slot_id}' placed on deck!")

    def unplace_selected_slot(self, slot_id=None):
        """
        Removes a placed slot from the deck and makes it an unplaced slot.
        Can be called by button (no ID) or by canvas menu (with ID).
        """
        # Check PLACED listbox selection first
        if slot_id is None:
            selection = self.slots_listbox.curselection()
            if not selection:
                messagebox.showwarning("Selection Error", "Please select a PLACED slot.")
                return

            item_text = self.slots_listbox.get(selection[0])
            slot_id = item_text.split(' (')[0]

        if slot_id not in self.deck.slots:
            messagebox.showwarning("Error", f"Slot {slot_id} not found on deck.")
            return

        #Ask for confirmation before removing
        if not messagebox.askyesno("Confirm Unplace Slot", f"Are you sure you want to unplace slot '{slot_id}'? "
                                                           f"Any labware inside will also be unplaced."):
            return
        # call deck function to remove the slot and all contained labware
        try:
            slot, unplaced_labware_list = self.deck.remove_slot(slot_id, unplace_labware=True)

        except ValueError as e:
            messagebox.showerror("Removal Error", str(e))
            return

        #Handle the unplaced labware returned from the deck
        for labware in unplaced_labware_list:
            self.unplaced_labware.append(labware)
            self.canvas.delete(f'labware_{labware.labware_id}')

        # B. Handle the unplaced slot
        self.unplaced_slots.append(slot)
        self.canvas.delete(f'slot_{slot_id}')

        # C. Update the GUI views
        self.clear_selection()
        self.update_labware_list()
        self.update_slots_list()

        # D. Show success message
        if unplaced_labware_list:
            lw_list = ", ".join([lw.labware_id for lw in unplaced_labware_list])
            messagebox.showinfo("Unplaced", f"Slot {slot_id} and contained labware ({lw_list}) unplaced successfully.")
        else:
            messagebox.showinfo("Unplaced", f"Slot {slot_id} unplaced successfully.")
        return

    def unplace_selected_labware(self, lw_id=None):
        """Removes a placed labware from the deck and makes it an unplaced labware."""

        if lw_id is None:
            selection = self.labware_listbox.curselection()
            if not selection:
                messagebox.showwarning("Selection Error", "Please select a PLACED labware.")
                return

            # Get item text (e.g., "Plate1 (Placed) - Plate")
            # CRITICAL: This line assumes the listbox content is correct.
            item_text = self.labware_listbox.get(selection[0])
            lw_id = item_text.split(' (')[0]  # Extracts "Plate1"

        if lw_id not in self.deck.labware:
            messagebox.showwarning("Selection Error", "Please select a PLACED labware.")
            return

        try:
            # ⭐ NEW: Use the updated deck function to perform the unplace operation
            labware = self.deck.remove_labware(lw_id)

        except ValueError as e:
            messagebox.showerror("Removal Error", str(e))
            return  # Exit if removal fails

        # 3. Final GUI Updates
        self.unplaced_labware.append(labware)
        self.canvas.delete(f'labware_{lw_id}')
        self.clear_selection()
        self.update_labware_list()
        messagebox.showinfo("Unplaced", f"Labware {lw_id} unplaced successfully.")
        return

    def edit_selected_unplaced_slot(self):
        """Edit selected unplaced slot and re-select it automatically."""
        selection = self.slots_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a slot to edit")
            return

        # Get the slot object being edited
        slot_index = selection[0]
        slot = self.unplaced_slots[slot_index]

        dialog = EditSlotDialog(self.root, slot)
        self.root.wait_window(dialog)

        if dialog.result:
            # 1. Update the listbox content to reflect changes (e.g., ID change)
            # 2. Re-select the edited slot
            self.update_slots_list()
            self.select_newly_created_slot(slot)
            messagebox.showinfo("Success", f"Slot '{slot.slot_id}' updated!")

    def delete_selected_unplaced_slot(self):
        """Delete selected unplaced slot"""
        selection = self.slots_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a slot to delete")
            return

        slot = self.unplaced_slots[selection[0]]

        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete slot '{slot.slot_id}'?"):
            self.unplaced_slots.remove(slot)
            self.update_slots_list()
            messagebox.showinfo("Success", f"Slot '{slot.slot_id}' deleted!")

    # Labware management methods
    def place_selected_unplaced(self):
        """Place selected unplaced labware"""
        selection = self.labware_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select labware to place")
            return

        labware = self.unplaced_labware[selection[0]]
        self.place_labware(labware)

    def edit_selected_unplaced_labware(self):
        """Edit selected unplaced labware"""
        selection = self.labware_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select labware to edit")
            return

        labware = self.unplaced_labware[selection[0]]

        dialog = EditLabwareDialog(self.root, labware, self.available_reservoirs)
        self.root.wait_window(dialog)

        if dialog.result:
            self.update_labware_list()
            self.show_unplaced_labware_info(labware)
            messagebox.showinfo("Success", f"Labware '{labware.labware_id}' updated!")

    def delete_selected_unplaced_labware(self):
        """Delete selected unplaced labware"""
        selection = self.labware_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select labware to delete")
            return

        labware = self.unplaced_labware[selection[0]]

        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete labware '{labware.labware_id}'?"):
            self.unplaced_labware.remove(labware)
            self.update_labware_list()
            messagebox.showinfo("Success", f"Labware '{labware.labware_id}' deleted!")

    def validate_slot_placement(self, slot):
        """Validate that a slot can be placed on the deck"""
        errors = []

        # Check if slot fits within deck boundaries
        if slot.range_x[0] < self.deck.range_x[0] or slot.range_x[1] > self.deck.range_x[1]:
            errors.append(f"⚠ Slot X range ({slot.range_x}) exceeds deck X range ({self.deck.range_x})")

        if slot.range_y[0] < self.deck.range_y[0] or slot.range_y[1] > self.deck.range_y[1]:
            errors.append(f"⚠ Slot Y range ({slot.range_y}) exceeds deck Y range ({self.deck.range_y})")

        if slot.range_z > self.deck.range_z:
            errors.append(f"⚠ Slot Z range ({slot.range_z}) exceeds deck Z range ({self.deck.range_z})")

        # Check for overlap with existing slots
        for existing_slot_id, existing_slot in self.deck.slots.items():
            if self.slots_overlap(slot, existing_slot):
                errors.append(f"⚠ Slot overlaps with existing slot '{existing_slot_id}'")

        return errors

    def slots_overlap(self, slot1, slot2):
        """Check if two slots overlap"""
        x_overlap = not (slot1.range_x[1] <= slot2.range_x[0] or slot1.range_x[0] >= slot2.range_x[1])
        y_overlap = not (slot1.range_y[1] <= slot2.range_y[0] or slot1.range_y[0] >= slot2.range_y[1])
        return x_overlap and y_overlap

    def validate_labware_placement(self, labware, slot_id, min_z):
        """Validate labware placement in a slot"""
        errors = []

        slot = self.deck.slots.get(slot_id)
        if not slot:
            errors.append(f"⚠ Slot '{slot_id}' does not exist")
            return errors

        # Check if labware exists in deck
        lw_id = labware.labware_id
        if lw_id not in self.deck.labware:
            return errors

        # Get labware data from slot
        lw_data = slot.labware_stack.get(lw_id)
        if lw_data:
            # Check Z height
            new_max_z = min_z + labware.size_z
            if new_max_z > slot.range_z:
                errors.append(f"⚠ Labware exceeds slot '{slot_id}' Z height\n"
                              f"   Slot Z: {slot.range_z} mm\n"
                              f"   Labware needs: {new_max_z} mm (min_z={min_z} + size_z={labware.size_z})")

            # Update the z_range in the slot
            if not errors:
                lw_data[1] = (min_z, new_max_z)

        return errors

    def select_slot(self, slot_id):
        """Highlight and show info for a slot"""
        self.clear_selection()
        self.labware_listbox.selection_clear(0, tk.END)

        tag = f'slot_{slot_id}'
        self.selected_item = ('slot', slot_id)

        items = self.canvas.find_withtag(tag)
        listbox = self.slots_listbox  # Correctly assigns the single listbox
        listbox.selection_clear(0, tk.END)

        # --- FIX THE SELECTION LOOP ---
        for item in items:
            item_type = self.canvas.type(item)

            # 1. Configuration for SHAPE items (The slot border/area)
            if item_type in ('rectangle', 'oval', 'polygon'):
                self.canvas.itemconfig(item, width=4, outline='darkblue')

            # 2. Configuration for TEXT items (The slot label)
            elif item_type == 'text':
                # Use 'fill' to change text color, not 'outline'
                self.canvas.itemconfig(item, fill='darkblue', font=('Arial', 10, 'bold'))

            # Optional: handle line items if your drawing logic uses them for slots
            elif item_type == 'line':
                self.canvas.itemconfig(item, width=4, fill='darkblue')


        slot = self.deck.slots.get(slot_id)
        if slot is None: return
        info = f"Slot: {slot_id}\n\n"
        info += f"Range X: {slot.range_x}\n"
        info += f"Range Y: {slot.range_y}\n"
        info += f"Range Z: {slot.range_z}\n\n"
        info += f"Labware in slot:\n"
        for lw_id in slot.labware_stack.keys():
            info += f"  - {lw_id}\n"

        self.update_info_in_both_tabs(info)

        listbox = self.slots_listbox
        listbox.selection_clear(0, tk.END)

         # 2. Find the index of the item (which is just the ID in your current update_slots_list)
        search_text = slot_id  # In placed mode, the list item is just 'A1'
        for i in range(listbox.size()):
            if listbox.get(i) == search_text:
                listbox.selection_set(i)
                listbox.activate(i)
                listbox.see(i)
                break

    def select_labware(self, lw_id):
        """Highlight and show info for placed labware."""
        self.clear_selection()
        self.slots_listbox.selection_clear(0, tk.END)
        self.selected_item = ('labware', lw_id)

        items = self.canvas.find_withtag(f'labware_{lw_id}')

        lw = self.deck.labware.get(lw_id)  # Use .get() for safety
        if lw is None: return

        # Iterate through all canvas items tagged with this labware ID
        for item in items:
            item_type = self.canvas.type(item)

            # 1. Configuration for SHAPE items (Rectangle, Oval, etc.)
            if item_type in ('rectangle', 'oval', 'polygon', 'line'):
                # Use 'outline' and 'width' to highlight the border
                self.canvas.itemconfig(item, width=4, outline='darkred')

            # 2. Configuration for TEXT items (The label)
            elif item_type == 'text':
                # Use 'fill' to change the text color
                self.canvas.itemconfig(item, fill='darkred', font=('Arial', 10, 'bold'))

        # Retrieve the labware object for detailed display
        slot_id = self.deck.get_slot_for_labware(lw_id)

        # Generate the detailed information string
        info = f"Labware: {lw_id}\n\n"
        info += f"Type: {lw.__class__.__name__}\n"
        info += f"Size X: {lw.size_x} mm\n"
        info += f"Size Y: {lw.size_y} mm\n"
        info += f"Size Z: {lw.size_z} mm\n"
        info += f"Offset: {lw.offset}\n"
        info += f"Position: {lw.position}\n"
        info += f"Slot: {slot_id if slot_id else 'None'}\n"

        # Add type-specific info
        if isinstance(lw, Plate):
            info += f"\nRows: {lw._rows}\n"
            info += f"Columns: {lw._columns}\n"
        elif isinstance(lw, ReservoirHolder):
            info += f"\nHooks X: {lw.hooks_across_x}\n"
            info += f"Hooks Y: {lw.hooks_across_y}\n"
        elif isinstance(lw, PipetteHolder):
            info += f"\nHolders X: {lw.holders_across_x}\n"
            info += f"\nHolders Y: {lw.holders_across_y}\n"

        self.update_info_in_both_tabs(info)

        listbox = self.labware_listbox

        # 1. Clear any old selections in the PLACED listbox
        listbox.selection_clear(0, tk.END)

        # 2. Find the index of the item
        search_text = lw_id  # In placed mode, the list item is just 'Plate1'
        for i in range(listbox.size()):
            if listbox.get(i) == search_text:
                listbox.selection_set(i)
                listbox.activate(i)
                listbox.see(i)
                break

    def clear_selection(self):
        """
        Clears the current selection on the canvas, listboxes, and resets item styles.
        It ensures the information panel is cleared by explicitly calling the update function.
        """

        # --- 1. Canvas Selection (Handles Placed Items) ---
        if self.selected_item:
            item_type, item_id = self.selected_item
            # The tag system here needs to be robust, but we'll use your existing pattern
            tag = f'{item_type}_{item_id}'

            # Find all canvas items associated with the previously selected tag and reset style
            for item in self.canvas.find_withtag(tag):
                item_type = self.canvas.type(item)

                # Reset SHAPE items (Rectangle, Oval, Polygon)
                if item_type in ('rectangle', 'oval', 'polygon'):
                    self.canvas.itemconfig(item, width=2, outline='blue')

                # Reset TEXT items (The label)
                elif item_type == 'text':
                    self.canvas.itemconfig(item, fill='black', font=('Arial', 10, 'normal'))

                # Optional: handle line items if present
                elif item_type == 'line':
                    self.canvas.itemconfig(item, width=2, fill='blue')

            # Clear the internal canvas selection tracking state
            self.selected_item = None

        # --- 2. Listbox Selections (Handles Unplaced Items) ---
        # This ensures that if an unplaced item was selected, it is unselected now.
        #self.slots_listbox.selection_clear(0, tk.END)
        #self.labware_listbox.selection_clear(0, tk.END)

        # --- 3. Clear Information Panel (MUST ALWAYS HAPPEN) ---
        # This call is now outside the 'if self.selected_item:' block,
        # guaranteeing the info panel is cleared regardless of selection origin.
        self.update_info_in_both_tabs("")

    def zoom_in(self):
        """Zoom in"""
        self.scale *= 1.2
        self.draw_deck()

    def zoom_out(self):
        """Zoom out"""
        self.scale *= 0.8
        self.draw_deck()

    def save_deck(self):
        """Save deck to JSON file"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                # Save deck and all unplaced items including low-level components
                data = {
                    'deck': self.deck.to_dict(),
                    'unplaced_labware': [lw.to_dict() for lw in self.unplaced_labware],
                    'unplaced_slots': [slot.to_dict() for slot in self.unplaced_slots],
                    'available_wells': [well.to_dict() for well in self.available_wells],
                    'available_reservoirs': [res.to_dict() for res in self.available_reservoirs],
                    'available_individual_holders': [holder.to_dict() for holder in self.available_individual_holders]
                }
                print(data)
                with open(filename, 'w') as f:
                    json.dump(data, f, indent=2)
                messagebox.showinfo("Success", f"Deck saved to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save: {str(e)}")

    def load_deck(self):
        """Load deck from JSON file"""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'r') as f:
                    data = json.load(f)

                # Load deck
                if 'deck' in data:
                    self.deck = Serializable.from_dict(data['deck'])
                else:
                    # Old format - just deck
                    self.deck = Serializable.from_dict(data)

                print(data)
                # Load unplaced labware if present
                self.unplaced_labware = []
                if 'unplaced_labware' in data:
                    for lw_data in data['unplaced_labware']:
                        self.unplaced_labware.append(Serializable.from_dict(lw_data))

                # Load unplaced slots if present
                self.unplaced_slots = []
                if 'unplaced_slots' in data:
                    for slot_data in data['unplaced_slots']:
                        self.unplaced_slots.append(Serializable.from_dict(slot_data))

                # Load low-level components if present
                self.available_wells = []
                if 'available_wells' in data:
                    for well_data in data['available_wells']:
                        self.available_wells.append(Serializable.from_dict(well_data))

                self.available_reservoirs = []
                if 'available_reservoirs' in data:
                    for res_data in data['available_reservoirs']:
                        self.available_reservoirs.append(Serializable.from_dict(res_data))

                self.available_individual_holders = []
                if 'available_individual_holders' in data:
                    for holder_data in data['available_individual_holders']:
                        self.available_individual_holders.append(Serializable.from_dict(holder_data))

                self.draw_deck()
                messagebox.showinfo("Success", f"Deck loaded from {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load: {str(e)}")

    def run(self):
        """Start the GUI"""
        self.root.mainloop()

# Main entry point
if __name__ == "__main__":
    # Create a sample deck for testing
    deck = Deck(range_x=(0, 265), range_y=(0, 244), deck_id="test_deck", range_z=141)

    # Run GUI
    gui = DeckGUI(deck)
    gui.run()