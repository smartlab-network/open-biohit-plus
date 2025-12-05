#todo combine code to repeat duplication.  speed reduction & easier to maintain
import tkinter as tk
from tkinter import messagebox
from ..deck_structure import *
import ttkbootstrap as ttk
import copy

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
        type_frame = ttk.Labelframe(main_frame, text="Component Type", padding="10")
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
        basic_frame = ttk.Labelframe(main_frame, text="Basic Parameters", padding="10")
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
        self.specific_frame = ttk.Labelframe(main_frame, text="Type-Specific Parameters", padding="10")
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
            #print(self.result.to_dict())
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
        list_frame = ttk.Labelframe(main_frame, text=f"Available {self.component_type}s", padding="10")
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
        type_frame = ttk.Labelframe(main_frame, text="Labware Type", padding="10")
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
        basic_frame = ttk.Labelframe(main_frame, text="Basic Parameters", padding="10")
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
        self.specific_frame = ttk.Labelframe(main_frame, text="Type-Specific Parameters", padding="10")
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

        ttk.Label(placement_frame, text="* If hook id is provided, the reservoir is only added to the specified hook.\n Otherwise, copies of reservoir populate the entire reservoirHolder. \n This can be changed later on in edit when unplaced  * \n").grid(row=2, column=0, columnspan=2,
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

class EditContainerContentDialog(tk.Toplevel):
    """Generic dialog for editing content in Wells or Reservoirs"""

    def __init__(self, parent, container):
        super().__init__(parent)
        self.title(f"Edit {container.__class__.__name__} Content")
        self.geometry("500x500")
        self.container = container  # Can be Well or Reservoir
        self.result = False

        self.transient(parent)
        self.grab_set()

        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(
            main_frame,
            text=f"Edit: {self.container.labware_id}",
            font=('Arial', 12, 'bold')
        )
        title_label.pack(pady=(0, 15))

        # Add content section
        add_frame = ttk.Labelframe(main_frame, text="Add Content", padding="15")
        add_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(add_frame, text="Content Type:").grid(row=0, column=0, sticky='w', pady=5)
        self.add_type_var = tk.StringVar()
        ttk.Entry(add_frame, textvariable=self.add_type_var, width=25).grid(row=0, column=1, pady=5, padx=(10, 0))

        ttk.Label(add_frame, text="Volume (µL):").grid(row=1, column=0, sticky='w', pady=5)
        self.add_volume_var = tk.StringVar()
        ttk.Entry(add_frame, textvariable=self.add_volume_var, width=25).grid(row=1, column=1, pady=5, padx=(10, 0))

        ttk.Button(add_frame, text="➕ Add", command=self.add_content).grid(
            row=2, column=0, columnspan=2, pady=(10, 0), sticky='ew'
        )

        # Remove content section
        remove_frame = ttk.Labelframe(main_frame, text="Remove Content", padding="15")
        remove_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(remove_frame, text="Volume to Remove (µL):").grid(row=0, column=0, sticky='w', pady=5)
        self.remove_volume_var = tk.StringVar()
        ttk.Entry(remove_frame, textvariable=self.remove_volume_var, width=25).grid(
            row=0, column=1, pady=5, padx=(10, 0)
        )

        ttk.Button(remove_frame, text="Remove (proportional)", command=self.remove_content).grid(
            row=1, column=0, columnspan=2, pady=(10, 5), sticky='ew'
        )

        ttk.Button(remove_frame, text="Clear All Content", command=self.clear_all).grid(
            row=2, column=0, columnspan=2, pady=(0, 0), sticky='ew'
        )

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(15, 0))

        ttk.Button(btn_frame, text="Save", command=self.on_done).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side=tk.RIGHT)

    def add_content(self):
        """Add content to container"""
        try:
            content_type = self.add_type_var.get().strip()
            volume = float(self.add_volume_var.get())

            if not content_type:
                messagebox.showerror("Error", "Please enter content type")
                return

            if volume <= 0:
                messagebox.showerror("Error", "Volume must be positive")
                return

            self.container.add_content(content_type, volume)

            # Clear inputs
            self.add_type_var.set("")
            self.add_volume_var.set("")

        except ValueError as e:
            messagebox.showerror("Error", str(e))

    def remove_content(self):
        """Remove content from container proportionally"""
        try:
            volume = float(self.remove_volume_var.get())

            if volume <= 0:
                messagebox.showerror("Error", "Volume must be positive")
                return

            self.container.remove_content(volume)
            self.remove_volume_var.set("")

        except ValueError as e:
            messagebox.showerror("Error", str(e))

    def clear_all(self):
        """Clear all content"""
        if messagebox.askyesno("Confirm", f"Clear all content from this {self.container.__class__.__name__.lower()}?", default="yes"):
            self.container.clear_content()

    def on_done(self):
        """Close dialog"""
        self.result = True
        self.destroy()

class EditHolderOccupancyDialog(tk.Toplevel):
    """Simplified dialog for editing pipette holder occupancy"""

    def __init__(self, parent, holder):
        super().__init__(parent)
        self.title(f"Edit Holder")
        self.geometry("300x300")
        self.holder = holder
        self.result = False

        self.transient(parent)
        self.grab_set()

        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(main_frame, text=f"Edit: {self.holder.labware_id}",
                                font=('Arial', 12, 'bold'))
        title_label.pack(pady=(0, 20))

        # Current status display
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(pady=(0, 20))

        ttk.Label(status_frame, text="Current Status:",
                  font=('Arial', 11, 'bold')).pack(side=tk.LEFT, padx=(0, 10))

        status_text = "Has Tip ✓" if self.holder.is_occupied else "Empty ✗"
        status_color = "green" if self.holder.is_occupied else "red"

        ttk.Label(status_frame, text=status_text,
                  font=('Arial', 13, 'bold'), foreground=status_color).pack(side=tk.LEFT)

        # Action buttons frame
        action_frame = ttk.Labelframe(main_frame, text="Actions", padding="15")
        action_frame.pack(fill=tk.X, pady=(0, 20))

        ttk.Button(action_frame, text="✓ Place Tip",
                   command=self.place_tip).pack(fill=tk.X, pady=5)

        ttk.Button(action_frame, text="✗ Remove Tip",
                   command=self.remove_tip).pack(fill=tk.X, pady=5)

        # Bottom buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X)

        ttk.Button(btn_frame, text="Save", command=self.on_done).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side=tk.RIGHT)

    def place_tip(self):
        """Place a tip"""
        try:
            self.holder.place_pipette()
            # Update dialog to show new status
            self.destroy()
            # Reopen with updated status
            self.result = True
        except ValueError as e:
            messagebox.showerror("Error", str(e))

    def remove_tip(self):
        """Remove a tip"""
        try:
            self.holder.remove_pipette()
            # Update dialog to show new status
            self.destroy()
            # Reopen with updated status
            self.result = True
        except ValueError as e:
            messagebox.showerror("Error", str(e))

    def on_done(self):
        """Close dialog"""
        self.result = True
        self.destroy()

class ViewChildrenLabwareDialog(tk.Toplevel):
    """Standalone dialog for viewing and editing child labware items"""

    def __init__(self, parent, labware):
        super().__init__(parent)
        self.title(f"View Children: {labware.labware_id}")
        self.geometry("1000x750")
        self.labware = labware
        self.selected_item = None

        self.transient(parent)
        self.grab_set()

        self.create_widgets()
        # Delay drawing until window is fully rendered
        self.after(100, self.draw_grid)

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Top info
        info_frame = ttk.Labelframe(main_frame, text="Labware Info", padding="10")
        info_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(info_frame, text=f"Type: {self.labware.__class__.__name__}",
                  font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=10)
        ttk.Label(info_frame, text=f"ID: {self.labware.labware_id}",
                  font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=10)

        if isinstance(self.labware, Plate):
            ttk.Label(info_frame, text=f"Grid: {self.labware._columns} × {self.labware._rows}",
                      font=('Arial', 10)).pack(side=tk.LEFT, padx=10)
        elif isinstance(self.labware, ReservoirHolder):
            ttk.Label(info_frame, text=f"Hooks: {self.labware._columns} × {self.labware._rows}",
                      font=('Arial', 10)).pack(side=tk.LEFT, padx=10)
        elif isinstance(self.labware, PipetteHolder):
            ttk.Label(info_frame, text=f"Holders: {self.labware._columns} × {self.labware._rows}",
                      font=('Arial', 10)).pack(side=tk.LEFT, padx=10)

        # Main split: Canvas on left, Info on right
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)

        # Left: Canvas with grid
        canvas_container = ttk.Labelframe(content_frame,
                                          text="Grid View (Click item to select)", padding="5")
        canvas_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        # Create canvas WITHOUT scrollbars (we'll fit everything to view)
        self.canvas = tk.Canvas(canvas_container, bg='white')
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.canvas.bind('<Button-1>', self.on_canvas_click)

        # Right: Item details and edit controls
        right_frame = ttk.Frame(content_frame, width=350)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(5, 0))
        right_frame.pack_propagate(False)

        # Item info display
        self.info_frame = ttk.Labelframe(right_frame, text="Selected Item Info", padding="10")
        self.info_frame.pack(fill=tk.BOTH, expand=True)

        self.info_text = tk.Text(self.info_frame, height=20, wrap=tk.WORD, width=35)
        scrollbar = ttk.Scrollbar(self.info_frame, orient=tk.VERTICAL, command=self.info_text.yview)
        self.info_text.configure(yscrollcommand=scrollbar.set)

        self.info_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Edit buttons
        btn_frame = ttk.Frame(right_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        if isinstance(self.labware, PipetteHolder):
            ttk.Button(btn_frame, text=" Place / Remove",
                       command=self.edit_selected_item).pack(fill=tk.X, pady=2)
        elif isinstance(self.labware, ReservoirHolder) or isinstance(self.labware, Plate):
            ttk.Button(btn_frame, text=" Manage content",
                      command=self.edit_selected_item).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text=" Refresh View",
                   command=self.refresh_view).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="Clear Selection",
                   command=self.clear_selection).pack(fill=tk.X, pady=2)

        # Legend
        legend_frame = ttk.Labelframe(right_frame, text="Legend", padding="10")
        legend_frame.pack(fill=tk.X, pady=(10, 0))

        if isinstance(self.labware, Plate):
            self.create_well_legend(legend_frame)
        elif isinstance(self.labware, PipetteHolder):
            self.create_holder_legend(legend_frame)

        # Bottom: Close button
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(bottom_frame, text="Close", command=self.destroy).pack(side=tk.RIGHT)

    def create_well_legend(self, parent):
        """Create legend for well colors"""
        colors = [
            ('#FFB6B6', 'Empty'),
            ('#ADD8E6', 'Has Content')
        ]

        for color, label in colors:
            row = ttk.Frame(parent)
            row.pack(fill=tk.X, pady=2)

            canvas = tk.Canvas(row, width=20, height=15, bg=color, highlightthickness=1, highlightbackground='black')
            canvas.pack(side=tk.LEFT, padx=(0, 5))

            ttk.Label(row, text=label).pack(side=tk.LEFT)

    def create_holder_legend(self, parent):
        """Create legend for holder colors"""
        colors = [
            ('#90EE90', 'Has Tip (✓)'),
            ('#FFE4E4', 'Empty (✗)')
        ]

        for color, label in colors:
            row = ttk.Frame(parent)
            row.pack(fill=tk.X, pady=2)

            canvas = tk.Canvas(row, width=20, height=15, bg=color, highlightthickness=1, highlightbackground='black')
            canvas.pack(side=tk.LEFT, padx=(0, 5))

            ttk.Label(row, text=label).pack(side=tk.LEFT)

    def calculate_scale(self):
        """Calculate the scale to fit all items in the canvas without scrolling"""
        # Get canvas dimensions
        self.canvas.update_idletasks()
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        # Get grid dimensions
        if isinstance(self.labware, Plate):
            cols = self.labware._columns
            rows = self.labware._rows
        elif isinstance(self.labware, ReservoirHolder):
            cols = self.labware._columns
            rows = self.labware._rows
        elif isinstance(self.labware, PipetteHolder):
            cols = self.labware._columns
            rows = self.labware._rows
        else:
            return 60  # Default

        # Calculate padding
        padding = 40
        label_space = 25  # Space for row/column labels

        # Calculate available space
        available_width = canvas_width - 2 * padding - label_space
        available_height = canvas_height - 2 * padding - label_space

        # Calculate cell size that fits
        cell_width = available_width / cols if cols > 0 else 60
        cell_height = available_height / rows if rows > 0 else 60

        # Use the smaller dimension to ensure everything fits
        cell_size = min(cell_width, cell_height)

        # Set minimum and maximum bounds
        cell_size = max(40, min(cell_size, 150))  # Between 40 and 150 pixels

        return cell_size

    def draw_grid(self):
        """Draw grid representation of items"""
        self.canvas.delete("all")

        if isinstance(self.labware, Plate):
            self.draw_plate_grid()
        elif isinstance(self.labware, ReservoirHolder):
            self.draw_reservoir_grid()
        elif isinstance(self.labware, PipetteHolder):
            self.draw_pipette_holder_grid()

    def draw_plate_grid(self):
        """Draw well grid for Plate with RIGHT-TO-LEFT layout (column 0 at right)"""
        plate = self.labware
        rows = plate._rows
        cols = plate._columns

        # Calculate scale to fit
        cell_size = self.calculate_scale()
        padding = 40

        # Draw column labels (RIGHT TO LEFT - col 0 is rightmost)
        for col in range(cols):
            x = padding + col * cell_size + cell_size / 2
            self.canvas.create_text(
                x, padding - 15,
                text=str(col),
                font=('Arial', 10, 'bold'),
                fill='blue'
            )

        # Draw row labels
        for row in range(rows):
            y = padding + row * cell_size + cell_size / 2
            self.canvas.create_text(
                padding - 15, y,
                text=str(row),
                font=('Arial', 10, 'bold'),
                fill='blue'
            )

        # Draw wells (RIGHT TO LEFT)
        for row in range(rows):
            for col in range(cols):
                well = plate.get_well_at(col, row)
                if not well:
                    continue

                x1 = padding + col * cell_size
                y1 = padding + row * cell_size
                x2 = x1 + cell_size
                y2 = y1 + cell_size

                # Simple color: light blue if has content, light red if empty
                fill_color = self.get_well_color(well)

                # Draw well
                self.canvas.create_rectangle(
                    x1, y1, x2, y2,
                    fill=fill_color,
                    outline='black',
                    width=2,
                    tags=('item', f'well_{col}_{row}')
                )

                # Draw label - scale font based on cell size
                font_size = max(7, min(int(cell_size / 8), 11))
                vol = well.get_total_volume()
                if vol > 0:
                    if vol >= 1000:
                        vol_text = f"{vol / 1000:.1f}mL"
                    else:
                        vol_text = f"{vol:.0f}µL"
                else:
                    vol_text = "Empty"

                self.canvas.create_text(
                    (x1 + x2) / 2, (y1 + y2) / 2,
                    text=vol_text,
                    font=('Arial', font_size),
                    tags=('item', f'well_{col}_{row}')
                )

    def draw_reservoir_grid(self):
        """Draw reservoir grid for ReservoirHolder (already RIGHT-TO-LEFT)"""
        holder = self.labware
        hooks_x = holder._columns
        hooks_y = holder._rows

        # Calculate scale to fit
        cell_size = self.calculate_scale()
        padding = 40

        # Draw hook labels (numbering right to left, top to bottom)
        for row in range(hooks_y):
            for col in range(hooks_x):
                hook_id = holder.position_to_hook_id(col, row)

                x = padding + col * cell_size + cell_size / 2
                y = padding + row * cell_size + cell_size / 2

                # Draw background
                x1 = padding + col * cell_size
                y1 = padding + row * cell_size
                x2 = x1 + cell_size
                y2 = y1 + cell_size

                self.canvas.create_rectangle(
                    x1, y1, x2, y2,
                    outline='lightgray',
                    fill='white',
                    width=1
                )

                font_size = max(7, min(int(cell_size / 10), 10))
                self.canvas.create_text(
                    x, y,
                    text=str(hook_id),
                    font=('Arial', font_size),
                    fill='lightgray'
                )

        # Draw reservoirs on top
        reservoirs = holder.get_reservoirs()
        colors = ['#FFB6C1', '#87CEEB', '#98FB98', '#FFD700', '#FFA07A', '#DDA0DD', '#F0E68C', '#E6E6FA']

        for idx, reservoir in enumerate(reservoirs):
            color = colors[idx % len(colors)]

            positions = [holder.hook_id_to_position(hid) for hid in reservoir.hook_ids]
            cols = [pos[0] for pos in positions]
            rows = [pos[1] for pos in positions]

            min_col, max_col = min(cols), max(cols)
            min_row, max_row = min(rows), max(rows)

            x1 = padding + min_col * cell_size
            y1 = padding + min_row * cell_size
            x2 = padding + (max_col + 1) * cell_size
            y2 = padding + (max_row + 1) * cell_size

            # Draw reservoir
            self.canvas.create_rectangle(
                x1, y1, x2, y2,
                fill=color,
                outline='black',
                width=3,
                tags=('item', f'reservoir_{reservoir.column}_{reservoir.row}')
            )

            # Label - scale font
            font_size = max(8, min(int(cell_size / 8), 12))
            label = f"Pos: ({reservoir.column},{reservoir.row})\n"
            vol = reservoir.get_total_volume()
            if vol >= 1000:
                label += f"{vol / 1000:.1f}mL"
            else:
                label += f"{vol:.0f}µL"

            self.canvas.create_text(
                (x1 + x2) / 2, (y1 + y2) / 2,
                text=label,
                font=('Arial', font_size, 'bold'),
                tags=('item', f'reservoir_{reservoir.column}_{reservoir.row}')
            )

    def draw_pipette_holder_grid(self):
        """Draw holder grid for PipetteHolder with RIGHT-TO-LEFT layout (column 0 at right)"""
        holder = self.labware
        holders_x = holder._columns
        holders_y = holder._rows

        # Calculate scale to fit
        cell_size = self.calculate_scale()
        padding = 40

        # Draw column labels (RIGHT TO LEFT - col 0 is rightmost)
        for col in range(holders_x):
            x = padding + col * cell_size + cell_size / 2
            self.canvas.create_text(
                x, padding - 15,
                text=str(col),
                font=('Arial', 10, 'bold'),
                fill='blue'
            )

        # Draw row labels
        for row in range(holders_y):
            y = padding + row * cell_size + cell_size / 2
            self.canvas.create_text(
                padding - 15, y,
                text=str(row),
                font=('Arial', 10, 'bold'),
                fill='blue'
            )

        # Draw individual holders (RIGHT TO LEFT)
        for row in range(holders_y):
            for col in range(holders_x):
                individual = holder.get_holder_at(col, row)
                if not individual:
                    continue

                x1 = padding + col * cell_size
                y1 = padding + row * cell_size
                x2 = x1 + cell_size
                y2 = y1 + cell_size

                # Color based on occupancy
                fill_color = '#90EE90' if individual.is_occupied else '#FFE4E4'

                # Draw holder
                self.canvas.create_rectangle(
                    x1, y1, x2, y2,
                    fill=fill_color,
                    outline='black',
                    width=2,
                    tags=('item', f'holder_{col}_{row}')
                )

                # Label - use tick marks with scaled font
                status = "✓" if individual.is_occupied else "✗"
                status_color = "darkgreen" if individual.is_occupied else "darkred"
                font_size = max(16, min(int(cell_size / 3), 28))

                self.canvas.create_text(
                    (x1 + x2) / 2, (y1 + y2) / 2,
                    text=status,
                    font=('Arial', font_size, 'bold'),
                    fill=status_color,
                    tags=('item', f'holder_{col}_{row}')
                )

    def get_well_color(self, well):
        """Get color for well - light blue if has content, light red if empty"""
        volume = well.get_total_volume()

        if volume == 0:
            return '#FFB6B6'  # Empty - light red
        else:
            return '#ADD8E6'  # Has content - light blue

    def on_canvas_click(self, event):
        """Handle click on canvas item"""
        item = self.canvas.find_closest(event.x, event.y)[0]
        tags = self.canvas.gettags(item)

        # Find the item tag
        item_tag = None
        for tag in tags:
            if tag.startswith(('well_', 'reservoir_', 'holder_')):
                item_tag = tag
                break

        if item_tag:
            self.select_item(item_tag)

    def select_item(self, item_tag):
        """Select and highlight an item"""
        # Clear previous selection
        for item in self.canvas.find_withtag('item'):
            if self.canvas.type(item) in ('rectangle', 'oval'):
                # Reset to original width
                orig_tags = self.canvas.gettags(item)
                if 'reservoir_' in str(orig_tags):
                    self.canvas.itemconfig(item, width=3, outline='black')
                else:
                    self.canvas.itemconfig(item, width=2, outline='black')

        # Highlight new selection
        items = self.canvas.find_withtag(item_tag)
        for item in items:
            if self.canvas.type(item) in ('rectangle', 'oval'):
                self.canvas.itemconfig(item, width=4, outline='red')

        self.selected_item = item_tag
        self.show_item_info(item_tag)

    def show_item_info(self, item_tag):
        """Display info for selected item"""
        self.info_text.delete(1.0, tk.END)

        if item_tag.startswith('well_'):
            _, col_str, row_str = item_tag.split('_')
            col, row = int(col_str), int(row_str)
            well = self.labware.get_well_at(col, row)

            info = f"WELL at Grid ({col}, {row})\n"
            info += "=" * 35 + "\n\n"
            info += f"ID: {well.labware_id}\n"
            info += f"Position (mm): {well.position}\n\n"
            info += f"Dimensions:\n"
            info += f"  {well.size_x} × {well.size_y} × {well.size_z} mm\n\n"
            info += f"Volume:\n"
            info += f"  Capacity: {well.capacity} µL\n"
            info += f"  Current: {well.get_total_volume():.1f} µL\n"
            info += f"  Available: {well.get_available_volume():.1f} µL\n"
            info += f"  Fill: {(well.get_total_volume() / well.capacity * 100):.1f}%\n\n"

            if well.shape:
                info += f"Shape: {well.shape}\n\n"

            info += f"Content:\n"
            if well.content:
                for content_type, vol in well.content.items():
                    info += f"  • {content_type}: {vol:.1f} µL\n"
            else:
                info += "  (empty)\n"

        elif item_tag.startswith('reservoir_'):
            _, col_str, row_str = item_tag.split('_')
            col, row = int(col_str), int(row_str)

            # Find reservoir at this position
            reservoir = None
            for res in self.labware.get_reservoirs():
                if res.column == col and res.row == row:
                    reservoir = res
                    break

            if reservoir:
                info = f"RESERVOIR at Grid ({col}, {row})\n"
                info += "=" * 35 + "\n\n"
                info += f"ID: {reservoir.labware_id}\n"
                info += f"Position (mm): {reservoir.position}\n\n"
                info += f"Dimensions:\n"
                info += f"  {reservoir.size_x} × {reservoir.size_y} × {reservoir.size_z} mm\n\n"
                info += f"Hook IDs: {reservoir.hook_ids}\n"
                info += f"Spans: {len(reservoir.hook_ids)} hooks\n\n"
                info += f"Volume:\n"
                info += f"  Capacity: {reservoir.capacity} µL\n"
                info += f"  Current: {reservoir.get_total_volume():.1f} µL\n"
                info += f"  Available: {reservoir.get_available_volume():.1f} µL\n"
                info += f"  Fill: {(reservoir.get_total_volume() / reservoir.capacity * 100):.1f}%\n\n"

                if reservoir.shape:
                    info += f"Shape: {reservoir.shape}\n\n"

                info += f"Content:\n"
                if reservoir.content:
                    for content_type, vol in reservoir.content.items():
                        info += f"  • {content_type}: {vol:.1f} µL\n"
                else:
                    info += "  (empty)\n"
            else:
                info = "Reservoir not found"

        elif item_tag.startswith('holder_'):
            _, col_str, row_str = item_tag.split('_')
            col, row = int(col_str), int(row_str)
            holder = self.labware.get_holder_at(col, row)

            info = f"PIPETTE HOLDER at Grid ({col}, {row})\n"
            info += "=" * 35 + "\n\n"
            info += f"ID: {holder.labware_id}\n"
            info += f"Position (mm): {holder.position}\n\n"
            info += f"Dimensions:\n"
            info += f"  {holder.size_x} × {holder.size_y} × {holder.size_z} mm\n\n"
            info += f"Status:\n"
            info += f"  Is Occupied: {holder.is_occupied}\n"
            info += f"  {'✓ Has Tip' if holder.is_occupied else '✗ Empty'}\n"

        self.info_text.insert(1.0, info)

    def edit_selected_item(self):
        """Open edit dialog for selected item"""
        if not self.selected_item:
            messagebox.showwarning("No Selection", "Please click on an item in the grid first")
            return

        if self.selected_item.startswith('well_'):
            _, col_str, row_str = self.selected_item.split('_')
            col, row = int(col_str), int(row_str)
            well = self.labware.get_well_at(col, row)

            dialog = EditContainerContentDialog(self, well)
            self.wait_window(dialog)

            if dialog.result:
                self.refresh_view()

        elif self.selected_item.startswith('reservoir_'):
            _, col_str, row_str = self.selected_item.split('_')
            col, row = int(col_str), int(row_str)

            reservoir = None
            for res in self.labware.get_reservoirs():
                if res.column == col and res.row == row:
                    reservoir = res
                    break

            if reservoir:
                dialog = EditContainerContentDialog(self, reservoir)
                self.wait_window(dialog)

                if dialog.result:
                    self.refresh_view()

        elif self.selected_item.startswith('holder_'):
            _, col_str, row_str = self.selected_item.split('_')
            col, row = int(col_str), int(row_str)
            holder = self.labware.get_holder_at(col, row)

            dialog = EditHolderOccupancyDialog(self, holder)
            self.wait_window(dialog)

            if dialog.result:
                self.refresh_view()

    def refresh_view(self):
        """Refresh the grid view and reselect item if it exists"""
        current_selection = self.selected_item
        self.draw_grid()
        if current_selection:
            # Try to reselect the same item
            try:
                self.select_item(current_selection)
            except:
                self.clear_selection()

    def clear_selection(self):
        """Clear item selection"""
        for item in self.canvas.find_withtag('item'):
            if self.canvas.type(item) in ('rectangle', 'oval'):
                orig_tags = self.canvas.gettags(item)
                if 'reservoir_' in str(orig_tags):
                    self.canvas.itemconfig(item, width=3, outline='black')
                else:
                    self.canvas.itemconfig(item, width=2, outline='black')
        self.selected_item = None
        self.info_text.delete(1.0, tk.END)

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
        params_frame = ttk.Labelframe(main_frame, text="Slot Parameters", padding="10")
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
        info_frame = ttk.Labelframe(main_frame, text="Labware Info", padding="10")
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
        """Basic properties tab"""
        basic_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(basic_tab, text="Basic Properties")

        # Existing basic properties...
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

        # ✅ ADD HEIGHT PROPERTIES SECTION
        current_row = 6

        # Add separator before height properties
        separator = ttk.Separator(basic_tab, orient='horizontal')
        separator.grid(row=current_row, column=0, columnspan=2, sticky='ew', pady=10)
        current_row += 1

        # Height Properties Section
        height_label = ttk.Label(basic_tab, text="Height Properties:", font=('Arial', 10, 'bold'))
        height_label.grid(row=current_row, column=0, columnspan=2, sticky='w', pady=5)
        current_row += 1

        # Initialize height property variables
        self.add_height_var = None
        self.remove_height_var = None
        self.drop_height_var = None

        # Add height (for Plate, PipetteHolder, ReservoirHolder)
        if hasattr(self.labware, 'add_height'):
            ttk.Label(basic_tab, text="Add Height (mm):").grid(row=current_row, column=0, sticky='w', pady=5)
            self.add_height_var = tk.StringVar(value=str(self.labware.add_height))
            entry = ttk.Entry(basic_tab, textvariable=self.add_height_var, width=25)
            entry.grid(row=current_row, column=1, pady=5)

            # Add tooltip/help
            help_label = ttk.Label(basic_tab, text="(Height for adding liquid)",
                                   font=('Arial', 9, 'italic'), foreground='gray')
            help_label.grid(row=current_row, column=2, sticky='w', padx=5)
            current_row += 1

        # Remove height (for Plate, PipetteHolder, ReservoirHolder)
        if hasattr(self.labware, 'remove_height'):
            ttk.Label(basic_tab, text="Remove Height (mm):").grid(row=current_row, column=0, sticky='w', pady=5)
            self.remove_height_var = tk.StringVar(value=str(self.labware.remove_height))
            entry = ttk.Entry(basic_tab, textvariable=self.remove_height_var, width=25)
            entry.grid(row=current_row, column=1, pady=5)

            # Add tooltip/help
            help_label = ttk.Label(basic_tab, text="(Height for removing liquid/tips)",
                                   font=('Arial', 9, 'italic'), foreground='gray')
            help_label.grid(row=current_row, column=2, sticky='w', padx=5)
            current_row += 1

        # Drop height (for TipDropzone)
        if hasattr(self.labware, 'drop_height'):
            ttk.Label(basic_tab, text="Drop Height (mm):").grid(row=current_row, column=0, sticky='w', pady=5)
            self.drop_height_var = tk.StringVar(value=str(self.labware.drop_height))
            entry = ttk.Entry(basic_tab, textvariable=self.drop_height_var, width=25)
            entry.grid(row=current_row, column=1, pady=5)

            # Add tooltip/help
            help_label = ttk.Label(basic_tab, text="(Height for dropping tips)",
                                   font=('Arial', 9, 'italic'), foreground='gray')
            help_label.grid(row=current_row, column=2, sticky='w', padx=5)
            current_row += 1

        # Continue with existing code (dimensional requirements)
        separator2 = ttk.Separator(basic_tab, orient='horizontal')
        separator2.grid(row=current_row, column=0, columnspan=2, sticky='ew', pady=10)
        current_row += 1

        req_frame = ttk.Labelframe(basic_tab, text="⚠️ Dimensional Requirements", padding="10")
        req_frame.grid(row=current_row, column=0, columnspan=2, sticky='ew', pady=5)

        req_text = self.calculate_requirements_text(self.labware)
        req_label = ttk.Label(
            req_frame,
            text=req_text,
            justify=tk.LEFT,
            foreground='red',
            font=('Arial', 11)
        )
        req_label.pack(anchor='w')

    def create_reservoir_management_tab(self):
        """Simplified reservoir management with visual grid"""
        reservoir_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(reservoir_tab, text="Manage Reservoirs")

        # Top: Canvas with visual hook grid
        canvas_frame = ttk.Labelframe(reservoir_tab, text="Hook Layout (Click reservoir to select)", padding="10")
        canvas_frame.pack(fill=tk.X, expand=False, pady=(0, 10))

        # Create canvas for drawing with fixed dimensions
        self.hook_canvas = tk.Canvas(canvas_frame, bg='white', height=250, width=650)
        self.hook_canvas.pack(fill=tk.NONE, expand=False)

        # Force canvas to update its size before drawing
        self.hook_canvas.update_idletasks()

        # Draw the hook grid with reservoirs
        self.draw_hook_grid()

        # Bottom: Control buttons
        control_frame = ttk.Labelframe(reservoir_tab, text="Actions", padding="10")
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

                # Draw hook ID
                hook_id = holder.position_to_hook_id(col, row)
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
        x1 = padding + min_col * cell_width
        y1 = padding + min_row * cell_height
        x2 = padding + (max_col + 1) * cell_width
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
        hook_str = ','.join(map(str, reservoir.hook_ids))
        text_id = self.hook_canvas.create_text(
            (x1 + x2) / 2, (y1 + y2) / 2,
            text=f"{hook_str}\n",
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

        except ValueError as e:
            messagebox.showerror("Error", f"Failed to remove reservoir:\n{str(e)}")

    def validate_labware_dimensions(self, labware, new_size_x, new_size_y, new_size_z, new_offset):
        """Validate that child components still fit after dimension changes"""
        errors = []
        warnings = []

        if isinstance(labware, Plate):
            errors, warnings = self.validate_plate_dimensions(
                labware, new_size_x, new_size_y, new_size_z, new_offset
            )

        elif isinstance(labware, PipetteHolder):
            errors, warnings = self.validate_pipette_holder_dimensions(
                labware, new_size_x, new_size_y, new_size_z, new_offset
            )

        elif isinstance(labware, ReservoirHolder):
            errors, warnings = self.validate_reservoir_holder_dimensions(
                labware, new_size_x, new_size_y, new_size_z, new_offset
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

    def validate_height_properties(self, add_height, remove_height, drop_height, size_z):
        """Validate height properties don't exceed labware height"""
        errors = []

        if add_height is not None:
            if add_height > size_z:
                errors.append(
                    f"❌ Add height ({add_height}mm) exceeds labware height ({size_z}mm)"
                )

        if remove_height is not None:
            if remove_height > size_z:
                errors.append(
                    f"❌ Remove height ({remove_height}mm) exceeds labware height ({size_z}mm)"
                )

        if drop_height is not None:
            if drop_height > size_z:
                errors.append(
                    f"❌ Drop height ({drop_height}mm) exceeds labware height ({size_z}mm)"
                )

        return errors

    def on_save(self):
        """Save changes with validation"""
        try:
            # Get new values
            new_size_x = float(self.size_x_var.get())
            new_size_y = float(self.size_y_var.get())
            new_size_z = float(self.size_z_var.get())
            new_offset = (float(self.offset_x_var.get()), float(self.offset_y_var.get()))
            new_can_be_stacked = bool(self.can_be_stacked_upon_var.get())

            # ✅ GET HEIGHT PROPERTIES
            new_add_height = None
            new_remove_height = None
            new_drop_height = None

            if self.add_height_var is not None:
                new_add_height = float(self.add_height_var.get())
            if self.remove_height_var is not None:
                new_remove_height = float(self.remove_height_var.get())
            if self.drop_height_var is not None:
                new_drop_height = float(self.drop_height_var.get())

            #  VALIDATE BEFORE SAVING
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

            #  APPLY HEIGHT PROPERTIES
            if new_add_height is not None and hasattr(self.labware, 'add_height'):
                self.labware.add_height = new_add_height
            if new_remove_height is not None and hasattr(self.labware, 'remove_height'):
                self.labware.remove_height = new_remove_height
            if new_drop_height is not None and hasattr(self.labware, 'drop_height'):
                self.labware.drop_height = new_drop_height

            # NOW copy all changes back to the ORIGINAL labware
            self.original_labware.size_x = self.labware.size_x
            self.original_labware.size_y = self.labware.size_y
            self.original_labware.size_z = self.labware.size_z
            self.original_labware.offset = self.labware.offset
            self.original_labware.can_be_stacked_upon = self.labware.can_be_stacked_upon

            #  COPY HEIGHT PROPERTIES
            if hasattr(self.labware, 'add_height'):
                self.original_labware.add_height = self.labware.add_height
            if hasattr(self.labware, 'remove_height'):
                self.original_labware.remove_height = self.labware.remove_height
            if hasattr(self.labware, 'drop_height'):
                self.original_labware.drop_height = self.labware.drop_height

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
        reservoir_frame = ttk.Labelframe(main_frame, text="Step 1: Select Reservoir", padding="10")
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
        preview_frame = ttk.Labelframe(main_frame, text="Reservoir Preview", padding="10")
        preview_frame.pack(fill=tk.X, pady=5)

        self.preview_text = tk.Text(preview_frame, height=5, wrap=tk.WORD)
        self.preview_text.pack(fill=tk.BOTH, expand=True)

        # Hook IDs input
        hooks_frame = ttk.Labelframe(main_frame, text="Step 2: Enter Hook ID(s)", padding="10")
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
        params_frame = ttk.Labelframe(main_frame, text="Slot Parameters", padding="10")
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
        info_frame = ttk.Labelframe(main_frame, text="Labware Info", padding="10")
        info_frame.pack(fill=tk.X, pady=5)

        ttk.Label(info_frame, text=f"ID: {self.labware.labware_id}").pack(anchor='w')
        ttk.Label(info_frame, text=f"Type: {self.labware.__class__.__name__}").pack(anchor='w')
        ttk.Label(info_frame, text=f"Size: {self.labware.size_x} x {self.labware.size_y} x {self.labware.size_z}").pack(
            anchor='w')

        # Placement parameters
        params_frame = ttk.Labelframe(main_frame, text="Placement", padding="10")
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