# gui2.py - Enhanced Tkinter GUI for Deck Editor with Low-Level Labware Support

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import json

# Import your existing classes
from deck import Deck
from slot import Slot
from labware import (
    Labware, Well, Reservoir, Plate, ReservoirHolder,
    PipetteHolder, TipDropzone, IndividualPipetteHolder
)


class CreateLowLevelLabwareDialog(tk.Toplevel):
    """Dialog for creating low-level labware components (Well, Reservoir, IndividualPipetteHolder)"""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Create Low-Level Labware")
        self.geometry("550x800")
        self.result = None

        # Make dialog modal
        self.transient(parent)
        self.grab_set()

        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Type Selection
        type_frame = ttk.LabelFrame(main_frame, text="Component Type", padding="10")
        type_frame.pack(fill=tk.X, pady=5)

        self.component_type = tk.StringVar(value="Well")
        types = ["Well", "Reservoir", "IndividualPipetteHolder"]

        for comp_type in types:
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
                capacity = float(self.capacity_var.get())
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
    """Dialog for selecting or creating a low-level component"""

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
        dialog = CreateLowLevelLabwareDialog(self)
        self.wait_window(dialog)

        if dialog.result:
            # Add to available components and return it
            self.available_components.append(dialog.result)
            self.result = dialog.result
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
        self.geometry("500x700")
        self.result = None

        # Store available low-level components
        self.available_wells = available_wells
        self.available_reservoirs = available_reservoirs
        self.available_individual_holders = available_individual_holders

        # Selected components
        self.selected_well = None
        self.selected_reservoir = None
        self.selected_individual_holder = None

        # Make dialog modal
        self.transient(parent)
        self.grab_set()

        self.create_widgets()

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
            ttk.Label(self.specific_frame, text="Hooks Across X:").grid(row=0, column=0, sticky='w', pady=2)
            self.hooks_x_var = tk.StringVar()
            ttk.Entry(self.specific_frame, textvariable=self.hooks_x_var, width=20).grid(row=0, column=1, pady=2)

            ttk.Label(self.specific_frame, text="Hooks Across Y:").grid(row=1, column=0, sticky='w', pady=2)
            self.hooks_y_var = tk.StringVar(value="1")
            ttk.Entry(self.specific_frame, textvariable=self.hooks_y_var, width=20).grid(row=1, column=1, pady=2)

            ttk.Label(self.specific_frame, text="Add Height (mm):").grid(row=2, column=0, sticky='w', pady=2)
            self.add_height_var = tk.StringVar()
            ttk.Entry(self.specific_frame, textvariable=self.add_height_var, width=20).grid(row=2, column=1, pady=2)

            ttk.Label(self.specific_frame, text="Remove Height (mm):").grid(row=3, column=0, sticky='w', pady=2)
            self.remove_height_var = tk.StringVar()
            ttk.Entry(self.specific_frame, textvariable=self.remove_height_var, width=20).grid(row=3, column=1, pady=2)

            # Note about reservoirs
            ttk.Label(self.specific_frame, text="Note: Reservoirs can be added after creation",
                      font=('Arial', 8, 'italic'), foreground='gray').grid(row=4, column=0, columnspan=2, pady=(10, 0))

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
                    remove_height=remove_height
                )

            elif lw_type == "ReservoirHolder":
                hooks_x = int(self.hooks_x_var.get())
                hooks_y = int(self.hooks_y_var.get())
                add_height = float(self.add_height_var.get())
                remove_height = float(self.remove_height_var.get())

                self.result = ReservoirHolder(
                    hooks_across_x=hooks_x,
                    hooks_across_y=hooks_y,
                    size_x=size_x,
                    size_y=size_y,
                    size_z=size_z,
                    offset=offset,
                    labware_id=labware_id,
                    add_height=add_height,
                    remove_height=remove_height
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
                    remove_height=remove_height
                )

            elif lw_type == "TipDropzone":
                drop_height = float(self.drop_height_var.get())

                self.result = TipDropzone(
                    size_x=size_x,
                    size_y=size_y,
                    size_z=size_z,
                    offset=offset,
                    labware_id=labware_id,
                    drop_height_relative=drop_height
                )

            self.destroy()

        except ValueError as e:
            messagebox.showerror("Invalid Input", f"Please check your inputs:\n{str(e)}")

    def on_cancel(self):
        """Cancel dialog"""
        self.result = None
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
    """Dialog for editing labware dimensions and offset"""

    def __init__(self, parent, labware):
        super().__init__(parent)
        self.title(f"Edit Labware: {labware.labware_id}")
        self.geometry("400x400")
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

        # Parameters frame
        params_frame = ttk.LabelFrame(main_frame, text="Edit Parameters", padding="10")
        params_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # Dimensions
        ttk.Label(params_frame, text="Size X (mm):").grid(row=0, column=0, sticky='w', pady=5)
        self.size_x_var = tk.StringVar(value=str(self.labware.size_x))
        ttk.Entry(params_frame, textvariable=self.size_x_var, width=25).grid(row=0, column=1, pady=5)

        ttk.Label(params_frame, text="Size Y (mm):").grid(row=1, column=0, sticky='w', pady=5)
        self.size_y_var = tk.StringVar(value=str(self.labware.size_y))
        ttk.Entry(params_frame, textvariable=self.size_y_var, width=25).grid(row=1, column=1, pady=5)

        ttk.Label(params_frame, text="Size Z (mm):").grid(row=2, column=0, sticky='w', pady=5)
        self.size_z_var = tk.StringVar(value=str(self.labware.size_z))
        ttk.Entry(params_frame, textvariable=self.size_z_var, width=25).grid(row=2, column=1, pady=5)

        # Offset
        ttk.Label(params_frame, text="Offset X (mm):").grid(row=3, column=0, sticky='w', pady=5)
        self.offset_x_var = tk.StringVar(value=str(self.labware.offset[0]))
        ttk.Entry(params_frame, textvariable=self.offset_x_var, width=25).grid(row=3, column=1, pady=5)

        ttk.Label(params_frame, text="Offset Y (mm):").grid(row=4, column=0, sticky='w', pady=5)
        self.offset_y_var = tk.StringVar(value=str(self.labware.offset[1]))
        ttk.Entry(params_frame, textvariable=self.offset_y_var, width=25).grid(row=4, column=1, pady=5)

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)

        ttk.Button(btn_frame, text="Save", command=self.on_save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.on_cancel).pack(side=tk.RIGHT)

    def on_save(self):
        """Save changes to labware"""
        try:
            size_x = float(self.size_x_var.get())
            size_y = float(self.size_y_var.get())
            size_z = float(self.size_z_var.get())
            offset_x = float(self.offset_x_var.get())
            offset_y = float(self.offset_y_var.get())

            # Update labware
            self.labware.size_x = size_x
            self.labware.size_y = size_y
            self.labware.size_z = size_z
            self.labware.offset = (offset_x, offset_y)

            self.result = True
            self.destroy()

        except ValueError as e:
            messagebox.showerror("Invalid Input", f"Please check your inputs:\n{str(e)}")

    def on_cancel(self):
        """Cancel dialog"""
        self.result = False
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
        self.slot_view_mode = tk.StringVar(value="placed")  # "placed" or "unplaced"
        self.labware_view_mode = tk.StringVar(value="placed")  # "placed" or "unplaced"

        self.setup_ui()
        self.draw_deck()

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
        view_menu.add_command(label="Refresh", command=self.draw_deck)
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
        right_panel_container = ttk.Frame(main_frame, width=300)
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
        self.deck_info_collapsible.toggle()

        # Info panel
        self.info_frame = ttk.LabelFrame(control_frame, text="Selection Info", padding=10)
        self.info_frame.pack(fill=tk.BOTH, expand=True, pady=5, padx=5)

        self.info_text = tk.Text(self.info_frame, height=10, wrap=tk.WORD)
        self.info_text.pack(fill=tk.BOTH, expand=True)

        # Control buttons
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(fill=tk.X, pady=5, padx=5)

        ttk.Button(btn_frame, text="Refresh", command=self.draw_deck).pack(fill=tk.X, pady=2)
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
        self.slots_listbox.bind('<Button-3>', self.on_slot_right_click)
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
        self.labware_listbox.bind('<Button-3>', self.on_labware_right_click)
        self.labware_listbox.bind('<Double-Button-1>', self.on_labware_double_click)

        # Buttons frame that changes based on view mode
        self.labware_button_frame = ttk.Frame(labware_main_frame)
        self.labware_button_frame.pack(fill=tk.X, pady=(5, 0))

        # We'll update this dynamically
        self.update_labware_buttons()

        # Zoom controls
        zoom_frame = ttk.Frame(control_frame)
        zoom_frame.pack(fill=tk.X, pady=5, padx=5)

        ttk.Button(zoom_frame, text="Zoom In", command=self.zoom_in).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        ttk.Button(zoom_frame, text="Zoom Out", command=self.zoom_out).pack(side=tk.LEFT, expand=True, fill=tk.X,
                                                                            padx=2)

        # Canvas bindings
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<Button-3>", self.on_canvas_right_click)

        # Create the Create tab in the right panel
        self.create_create_tab()

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
                text="Place Slot",
                command=self.place_selected_unplaced_slot
            ).pack(fill=tk.X, pady=2)
            ttk.Button(
                self.slots_button_frame,
                text="Edit",
                command=self.edit_selected_unplaced_slot
            ).pack(fill=tk.X, pady=2)
            ttk.Button(
                self.slots_button_frame,
                text="Delete",
                command=self.delete_selected_unplaced_slot
            ).pack(fill=tk.X, pady=2)
            ttk.Button(
                self.slots_button_frame,
                text="Create Slot",
                command=self.create_slot
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
                text="Place on Slot",
                command=self.place_selected_unplaced
            ).pack(fill=tk.X, pady=2)
            ttk.Button(
                self.labware_button_frame,
                text="Edit",
                command=self.edit_selected_unplaced_labware
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

    def create_create_tab(self):
        """Create the Create tab"""
        create_tab = ttk.Frame(self.right_panel_notebook)
        self.right_panel_notebook.add(create_tab, text="Labware")

        # Create tab content
        create_content = ttk.Frame(create_tab, padding=20)
        create_content.pack(fill=tk.BOTH, expand=True)

        # Title
        ttk.Label(create_content, text="Create New Labware", font=('Arial', 14, 'bold')).pack(pady=(0, 20))

        # Create Low-Level Labware section
        low_level_section = ttk.LabelFrame(create_content, text="Low-Level Labware", padding=15)
        low_level_section.pack(fill=tk.X, pady=10)

        ttk.Label(low_level_section,
                  text="Create components used in labware\n like Well, Individual Pipette Holder, and Reservoir)",
                  wraplength=250, justify=tk.LEFT).pack(pady=(0, 10))
        ttk.Button(low_level_section, text="Create Low-Level Lw", command=self.create_low_level_labware,
                   width=20).pack()

        # Create Labware section
        labware_section = ttk.LabelFrame(create_content, text="Labware", padding=15)
        labware_section.pack(fill=tk.X, pady=10)

        ttk.Label(labware_section,
                  text="Create labware like Plate, ReservoirHolder, PipetteHolder, TipDropzone",
                  wraplength=250, justify=tk.LEFT).pack(pady=(0, 10))
        ttk.Button(labware_section, text="Create Labware", command=self.create_labware,
                   width=20).pack()

    def create_low_level_labware(self):
        """Open dialog to create low-level labware components"""
        dialog = CreateLowLevelLabwareDialog(self.root)
        self.root.wait_window(dialog)

        if dialog.result:
            component = dialog.result

            # Add to appropriate list
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

    def create_labware(self):
        """Open dialog to create new labware"""
        dialog = CreateLabwareDialog(self.root, self.available_wells, self.available_reservoirs,
                                     self.available_individual_holders)
        self.root.wait_window(dialog)

        if dialog.result:
            # Store newly created component if needed
            if isinstance(dialog.result, Plate) and dialog.selected_well:
                if dialog.selected_well not in self.available_wells:
                    self.available_wells.append(dialog.selected_well)
            elif isinstance(dialog.result, PipetteHolder) and dialog.selected_individual_holder:
                if dialog.selected_individual_holder not in self.available_individual_holders:
                    self.available_individual_holders.append(dialog.selected_individual_holder)

            self.unplaced_labware.append(dialog.result)
            self.update_labware_list()
            messagebox.showinfo("Success",
                                f"Labware '{dialog.result.labware_id}' created!\nSwitch to 'Unplaced' view to place it on a slot.")

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
            self.unplaced_slots.append(dialog.result)
            if self.slot_view_mode.get() == "unplaced":
                self.update_slots_list()
            messagebox.showinfo("Success",
                                f"Slot created!\nclick 'Place Slot' to add it to the deck.")

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
        """Auto-calculate scale to fit deck in canvas"""
        canvas_width = self.canvas.winfo_width() or 800
        canvas_height = self.canvas.winfo_height() or 600

        deck_width = self.deck.range_x[1] - self.deck.range_x[0]
        deck_height = self.deck.range_y[1] - self.deck.range_y[0]

        scale_x = (canvas_width - 100) / deck_width
        scale_y = (canvas_height - 100) / deck_height

        self.scale = min(scale_x, scale_y, 2.0)
        self.offset_x = 50
        self.offset_y = 50

    def mm_to_canvas(self, x, y):
        """Convert mm coordinates to canvas pixels"""
        return (x * self.scale + self.offset_x,
                y * self.scale + self.offset_y)

    def canvas_to_mm(self, cx, cy):
        """Convert canvas pixels to mm coordinates"""
        return ((cx - self.offset_x) / self.scale,
                (cy - self.offset_y) / self.scale)

    def draw_deck(self):
        """Draw the entire deck"""
        self.canvas.delete("all")
        self.calculate_scale()

        # Draw grid
        self.draw_grid()

        # Draw deck boundary
        x1, y1 = self.mm_to_canvas(self.deck.range_x[0], self.deck.range_y[0])
        x2, y2 = self.mm_to_canvas(self.deck.range_x[1], self.deck.range_y[1])
        self.canvas.create_rectangle(x1, y1, x2, y2, outline='black', width=3, tags='deck_boundary')

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
    def on_canvas_click(self, event):
        """Handle canvas click"""
        item = self.canvas.find_closest(event.x, event.y)[0]
        tags = self.canvas.gettags(item)

        if 'slot' in tags:
            slot_id = [t for t in tags if t != 'slot' and not t.startswith('slot_') and t != 'current'][0]
            self.select_slot(slot_id)
        elif 'labware' in tags:
            lw_id = [t for t in tags if t != 'labware' and not t.startswith('labware_') and t != 'current'][0]
            self.select_labware(lw_id)
            self.dragging = lw_id
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y
        else:
            self.clear_selection()

    def on_canvas_drag(self, event):
        """Handle dragging labware"""
        if self.dragging and self.dragging in self.deck.labware:
            dx = event.x - self.drag_data["x"]
            dy = event.y - self.drag_data["y"]

            items = self.canvas.find_withtag(f'labware_{self.dragging}')
            for item in items:
                self.canvas.move(item, dx, dy)

            labels = self.canvas.find_withtag(self.dragging)
            for label in labels:
                if 'labware_label' in self.canvas.gettags(label):
                    self.canvas.move(label, dx, dy)

            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y

    def on_canvas_release(self, event):
        """Handle mouse release"""
        if self.dragging:
            lw = self.deck.labware[self.dragging]
            items = self.canvas.find_withtag(f'labware_{self.dragging}')
            if items:
                coords = self.canvas.coords(items[0])
                new_x, new_y = self.canvas_to_mm(coords[0], coords[1])
                lw.position = (new_x, new_y)
                print(f"Moved {self.dragging} to {lw.position}")

            self.dragging = None

    def on_canvas_right_click(self, event):
        """Show context menu on canvas"""
        item = self.canvas.find_closest(event.x, event.y)[0]
        tags = self.canvas.gettags(item)

        menu = tk.Menu(self.root, tearoff=0)

        if 'labware' in tags:
            lw_id = [t for t in tags if t != 'labware' and not t.startswith('labware_') and t != 'current'][0]
            menu.add_command(label=f"Edit {lw_id}",
                             command=lambda: self.edit_labware_dialog(lw_id))
            menu.add_command(label=f"Remove {lw_id}",
                             command=lambda: self.remove_labware_dialog(lw_id))
            menu.add_separator()
            menu.add_command(label=f"Info",
                             command=lambda: self.select_labware(lw_id))
        elif 'slot' in tags:
            slot_id = [t for t in tags if t != 'slot' and not t.startswith('slot_') and t != 'current'][0]
            menu.add_command(label=f"Edit Slot {slot_id}",
                             command=lambda: self.edit_slot_dialog(slot_id))
            menu.add_command(label=f"Remove Slot {slot_id}",
                             command=lambda: self.remove_slot_dialog(slot_id))

        menu.post(event.x_root, event.y_root)

    def on_slot_select(self, event):
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

    def on_slot_right_click(self, event):
        """Handle right click on slot"""
        # Get selection
        selection = self.slots_listbox.curselection()
        if not selection:
            return

        # Create context menu based on view mode
        menu = tk.Menu(self.root, tearoff=0)

        if self.slot_view_mode.get() == "placed":
            menu.add_command(label="Unplace Slot", command=self.unplace_selected_slot)
        else:
            menu.add_command(label="Place Slot", command=self.place_selected_unplaced_slot)
            menu.add_command(label="Edit", command=self.edit_selected_unplaced_slot)
            menu.add_command(label="Delete", command=self.delete_selected_unplaced_slot)

        menu.post(event.x_root, event.y_root)

    def on_slot_double_click(self, event):
        """Handle double click on slot"""
        if self.slot_view_mode.get() == "unplaced":
            self.place_selected_unplaced_slot()

    def on_labware_select(self, event):
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

    def on_labware_right_click(self, event):
        """Handle right click on labware"""
        # Get selection
        selection = self.labware_listbox.curselection()
        if not selection:
            return

        # Create context menu based on view mode
        menu = tk.Menu(self.root, tearoff=0)

        if self.labware_view_mode.get() == "placed":
            menu.add_command(label="Unplace Labware", command=self.unplace_selected_labware)
        else:
            menu.add_command(label="Place on Slot", command=self.place_selected_unplaced)
            menu.add_command(label="Edit", command=self.edit_selected_unplaced_labware)
            menu.add_command(label="Delete", command=self.delete_selected_unplaced_labware)

        menu.post(event.x_root, event.y_root)

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

        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(1.0, info)

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

        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(1.0, info)

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

    def unplace_selected_slot(self):
        """Remove selected placed slot from deck"""
        selection = self.slots_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a slot to unplace")
            return

        slot_id = self.slots_listbox.get(selection[0])

        # Check if slot has labware
        slot = self.deck.slots[slot_id]

        # First, unplace all labware in this slot
        labware_in_slot = list(slot.labware_stack.keys())  # Make a copy of the keys
        if labware_in_slot:
            for lw_id in labware_in_slot:
                lw = self.deck.labware[lw_id]
                # Remove from deck
                self.deck.remove_labware(lw, slot_id)
                # Add to unplaced
                self.unplaced_labware.append(lw)

            messagebox.showinfo("Info",
                                f"Automatically unplaced {len(labware_in_slot)} labware item(s) from slot '{slot_id}'.")

        # Remove from deck and add to unplaced
        self.unplaced_slots.append(slot)
        del self.deck.slots[slot_id]

        self.draw_deck()
        messagebox.showinfo("Success", f"Slot '{slot_id}' removed from deck!")

    def edit_selected_unplaced_slot(self):
        """Edit selected unplaced slot"""
        selection = self.slots_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a slot to edit")
            return

        slot = self.unplaced_slots[selection[0]]

        dialog = EditSlotDialog(self.root, slot)
        self.root.wait_window(dialog)

        if dialog.result:
            self.update_slots_list()
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

    def unplace_selected_labware(self):
        """Remove selected placed labware from deck"""
        selection = self.labware_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select labware to unplace")
            return

        lw_id = self.labware_listbox.get(selection[0])
        labware = self.deck.labware[lw_id]

        # Remove from deck
        slot_id = self.deck.get_slot_for_labware(lw_id)
        if slot_id:
            self.deck.slots[slot_id]._remove_labware(lw_id)

        del self.deck.labware[lw_id]
        labware.position = None

        # Add to unplaced
        self.unplaced_labware.append(labware)

        self.draw_deck()
        messagebox.showinfo("Success", f"Labware '{lw_id}' removed from deck!")

    def edit_selected_unplaced_labware(self):
        """Edit selected unplaced labware"""
        selection = self.labware_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select labware to edit")
            return

        labware = self.unplaced_labware[selection[0]]

        dialog = EditLabwareDialog(self.root, labware)
        self.root.wait_window(dialog)

        if dialog.result:
            self.update_labware_list()
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
        self.selected_item = ('slot', slot_id)

        items = self.canvas.find_withtag(f'slot_{slot_id}')
        for item in items:
            self.canvas.itemconfig(item, width=4, outline='darkblue')

        slot = self.deck.slots[slot_id]
        info = f"Slot: {slot_id}\n\n"
        info += f"Range X: {slot.range_x}\n"
        info += f"Range Y: {slot.range_y}\n"
        info += f"Range Z: {slot.range_z}\n\n"
        info += f"Labware in slot:\n"
        for lw_id in slot.labware_stack.keys():
            info += f"  - {lw_id}\n"

        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(1.0, info)

    def select_labware(self, lw_id):
        """Highlight and show info for labware"""
        self.clear_selection()
        self.selected_item = ('labware', lw_id)

        items = self.canvas.find_withtag(f'labware_{lw_id}')
        for item in items:
            self.canvas.itemconfig(item, width=4, outline='darkred')

        lw = self.deck.labware[lw_id]
        slot_id = self.deck.get_slot_for_labware(lw_id)

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

        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(1.0, info)

    def clear_selection(self):
        """Clear selection"""
        if self.selected_item:
            item_type, item_id = self.selected_item
            if item_type == 'slot':
                items = self.canvas.find_withtag(f'slot_{item_id}')
                for item in items:
                    self.canvas.itemconfig(item, width=2, outline='blue')
            elif item_type == 'labware':
                items = self.canvas.find_withtag(f'labware_{item_id}')
                for item in items:
                    self.canvas.itemconfig(item, width=2, outline='red')

        self.selected_item = None
        self.info_text.delete(1.0, tk.END)

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

                from serializable import Serializable

                # Load deck
                if 'deck' in data:
                    self.deck = Serializable.from_dict(data['deck'])
                else:
                    # Old format - just deck
                    self.deck = Serializable.from_dict(data)

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
    deck = Deck(range_x=(0, 500), range_y=(0, 400), deck_id="test_deck", range_z=500)

    # Run GUI
    gui = DeckGUI(deck)
    gui.run()

    # Draw slot label
    cx = (x1 + x2) / 2