# gui2.py - Enhanced Tkinter GUI for Deck Editor

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import json

# Import your existing classes
from .deck import Deck
from .slot import Slot
from .labware import (
    Labware, Well, Reservoir, Plate, ReservoirHolder,
    PipetteHolder, TipDropzone
)


class EditSlotDialog(tk.Toplevel):
    """Dialog for editing existing slots"""

    def __init__(self, parent, slot):
        super().__init__(parent)
        self.title(f"Edit Slot - {slot.slot_id}")
        self.geometry("400x300")
        self.result = None
        self.slot = slot

        # Make dialog modal
        self.transient(parent)
        self.grab_set()

        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Slot Parameters
        params_frame = ttk.LabelFrame(main_frame, text="Slot Parameters", padding="10")
        params_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # Slot ID (read-only)
        ttk.Label(params_frame, text="Slot ID:").grid(row=0, column=0, sticky='w', pady=5)
        ttk.Label(params_frame, text=self.slot.slot_id, font=('Arial', 10, 'bold')).grid(row=0, column=1, sticky='w',
                                                                                         pady=5)
        ttk.Label(params_frame, text="(Cannot change ID)", font=('Arial', 8, 'italic'), foreground='gray').grid(row=0,
                                                                                                                column=2,
                                                                                                                sticky='w',
                                                                                                                padx=5)

        # Range X
        ttk.Label(params_frame, text="Range X Min (mm):").grid(row=1, column=0, sticky='w', pady=5)
        self.x_min_var = tk.StringVar(value=str(self.slot.range_x[0]))
        ttk.Entry(params_frame, textvariable=self.x_min_var, width=25).grid(row=1, column=1, pady=5, columnspan=2)

        ttk.Label(params_frame, text="Range X Max (mm):").grid(row=2, column=0, sticky='w', pady=5)
        self.x_max_var = tk.StringVar(value=str(self.slot.range_x[1]))
        ttk.Entry(params_frame, textvariable=self.x_max_var, width=25).grid(row=2, column=1, pady=5, columnspan=2)

        # Range Y
        ttk.Label(params_frame, text="Range Y Min (mm):").grid(row=3, column=0, sticky='w', pady=5)
        self.y_min_var = tk.StringVar(value=str(self.slot.range_y[0]))
        ttk.Entry(params_frame, textvariable=self.y_min_var, width=25).grid(row=3, column=1, pady=5, columnspan=2)

        ttk.Label(params_frame, text="Range Y Max (mm):").grid(row=4, column=0, sticky='w', pady=5)
        self.y_max_var = tk.StringVar(value=str(self.slot.range_y[1]))
        ttk.Entry(params_frame, textvariable=self.y_max_var, width=25).grid(row=4, column=1, pady=5, columnspan=2)

        # Range Z
        ttk.Label(params_frame, text="Range Z (mm):").grid(row=5, column=0, sticky='w', pady=5)
        self.z_var = tk.StringVar(value=str(self.slot.range_z))
        ttk.Entry(params_frame, textvariable=self.z_var, width=25).grid(row=5, column=1, pady=5, columnspan=2)

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)

        ttk.Button(btn_frame, text="Save Changes", command=self.on_save).pack(side=tk.RIGHT, padx=5)
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

            # Update slot in place
            self.slot.range_x = (x_min, x_max)
            self.slot.range_y = (y_min, y_max)
            self.slot.range_z = z

            self.result = True
            self.destroy()

        except ValueError as e:
            messagebox.showerror("Invalid Input", f"Please check your inputs:\n{str(e)}")

    def on_cancel(self):
        """Cancel dialog"""
        self.result = None
        self.destroy()


class EditLabwareDialog(tk.Toplevel):
    """Dialog for editing existing labware"""

    def __init__(self, parent, labware):
        super().__init__(parent)
        self.title(f"Edit Labware - {labware.labware_id}")
        self.geometry("500x650")
        self.result = None
        self.labware = labware

        # Make dialog modal
        self.transient(parent)
        self.grab_set()

        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Labware Type (read-only)
        type_frame = ttk.LabelFrame(main_frame, text="Labware Type (Cannot Change)", padding="10")
        type_frame.pack(fill=tk.X, pady=5)

        ttk.Label(type_frame, text=self.labware.__class__.__name__,
                  font=('Arial', 12, 'bold')).pack(anchor='w')

        # Basic Parameters
        basic_frame = ttk.LabelFrame(main_frame, text="Basic Parameters", padding="10")
        basic_frame.pack(fill=tk.X, pady=5)

        # Labware ID (read-only)
        ttk.Label(basic_frame, text="Labware ID:").grid(row=0, column=0, sticky='w', pady=2)
        id_label = ttk.Label(basic_frame, text=self.labware.labware_id, font=('Arial', 9, 'bold'))
        id_label.grid(row=0, column=1, sticky='w', pady=2)

        # Dimensions
        ttk.Label(basic_frame, text="Size X (mm):").grid(row=1, column=0, sticky='w', pady=2)
        self.size_x_var = tk.StringVar(value=str(self.labware.size_x))
        ttk.Entry(basic_frame, textvariable=self.size_x_var, width=30).grid(row=1, column=1, pady=2)

        ttk.Label(basic_frame, text="Size Y (mm):").grid(row=2, column=0, sticky='w', pady=2)
        self.size_y_var = tk.StringVar(value=str(self.labware.size_y))
        ttk.Entry(basic_frame, textvariable=self.size_y_var, width=30).grid(row=2, column=1, pady=2)

        ttk.Label(basic_frame, text="Size Z (mm):").grid(row=3, column=0, sticky='w', pady=2)
        self.size_z_var = tk.StringVar(value=str(self.labware.size_z))
        ttk.Entry(basic_frame, textvariable=self.size_z_var, width=30).grid(row=3, column=1, pady=2)

        # Offset
        ttk.Label(basic_frame, text="Offset X (mm):").grid(row=4, column=0, sticky='w', pady=2)
        self.offset_x_var = tk.StringVar(value=str(self.labware.offset[0]))
        ttk.Entry(basic_frame, textvariable=self.offset_x_var, width=30).grid(row=4, column=1, pady=2)

        ttk.Label(basic_frame, text="Offset Y (mm):").grid(row=5, column=0, sticky='w', pady=2)
        self.offset_y_var = tk.StringVar(value=str(self.labware.offset[1]))
        ttk.Entry(basic_frame, textvariable=self.offset_y_var, width=30).grid(row=5, column=1, pady=2)

        # Type-Specific Parameters Frame
        self.specific_frame = ttk.LabelFrame(main_frame, text="Type-Specific Parameters", padding="10")
        self.specific_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # Create type-specific fields
        self.create_specific_fields()

        # Warning label
        warning_frame = ttk.Frame(main_frame)
        warning_frame.pack(fill=tk.X, pady=5)
        warning_label = ttk.Label(
            warning_frame,
            text="⚠ Warning: Changing parameters may cause validation errors\nif labware no longer fits in its slot.",
            foreground='orange',
            font=('Arial', 8)
        )
        warning_label.pack()

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)

        ttk.Button(btn_frame, text="Save Changes", command=self.on_save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.on_cancel).pack(side=tk.RIGHT)

    def create_specific_fields(self):
        """Create fields specific to the labware type"""
        # Clear existing widgets
        for widget in self.specific_frame.winfo_children():
            widget.destroy()

        lw = self.labware

        if isinstance(lw, Plate):
            ttk.Label(self.specific_frame, text="Rows:").grid(row=0, column=0, sticky='w', pady=2)
            self.rows_var = tk.StringVar(value=str(lw._rows))
            rows_entry = ttk.Entry(self.specific_frame, textvariable=self.rows_var, width=20)
            rows_entry.grid(row=0, column=1, pady=2)
            rows_entry.config(state='readonly')  # Don't allow changing grid structure

            ttk.Label(self.specific_frame, text="Columns:").grid(row=1, column=0, sticky='w', pady=2)
            self.cols_var = tk.StringVar(value=str(lw._columns))
            cols_entry = ttk.Entry(self.specific_frame, textvariable=self.cols_var, width=20)
            cols_entry.grid(row=1, column=1, pady=2)
            cols_entry.config(state='readonly')  # Don't allow changing grid structure

            ttk.Label(self.specific_frame, text="(Grid structure cannot be changed)",
                      font=('Arial', 8, 'italic'), foreground='gray').grid(row=2, column=0, columnspan=2, pady=2)

        elif isinstance(lw, ReservoirHolder):
            ttk.Label(self.specific_frame, text="Hooks Across X:").grid(row=0, column=0, sticky='w', pady=2)
            self.hooks_x_var = tk.StringVar(value=str(lw.hooks_across_x))
            hooks_x_entry = ttk.Entry(self.specific_frame, textvariable=self.hooks_x_var, width=20)
            hooks_x_entry.grid(row=0, column=1, pady=2)
            hooks_x_entry.config(state='readonly')

            ttk.Label(self.specific_frame, text="Hooks Across Y:").grid(row=1, column=0, sticky='w', pady=2)
            self.hooks_y_var = tk.StringVar(value=str(lw.hooks_across_y))
            hooks_y_entry = ttk.Entry(self.specific_frame, textvariable=self.hooks_y_var, width=20)
            hooks_y_entry.grid(row=1, column=1, pady=2)
            hooks_y_entry.config(state='readonly')

            ttk.Label(self.specific_frame, text="(Grid structure cannot be changed)",
                      font=('Arial', 8, 'italic'), foreground='gray').grid(row=2, column=0, columnspan=2, pady=2)

        elif isinstance(lw, PipetteHolder):
            ttk.Label(self.specific_frame, text="Zones Across X:").grid(row=0, column=0, sticky='w', pady=2)
            self.zones_x_var = tk.StringVar(value=str(lw.zones_across_x))
            zones_x_entry = ttk.Entry(self.specific_frame, textvariable=self.zones_x_var, width=20)
            zones_x_entry.grid(row=0, column=1, pady=2)
            zones_x_entry.config(state='readonly')

            ttk.Label(self.specific_frame, text="Zones Across Y:").grid(row=1, column=0, sticky='w', pady=2)
            self.zones_y_var = tk.StringVar(value=str(lw.zones_across_y))
            zones_y_entry = ttk.Entry(self.specific_frame, textvariable=self.zones_y_var, width=20)
            zones_y_entry.grid(row=1, column=1, pady=2)
            zones_y_entry.config(state='readonly')

            ttk.Label(self.specific_frame, text="(Grid structure cannot be changed)",
                      font=('Arial', 8, 'italic'), foreground='gray').grid(row=2, column=0, columnspan=2, pady=2)

        elif isinstance(lw, TipDropzone):
            ttk.Label(self.specific_frame, text="Drop Height (mm):").grid(row=0, column=0, sticky='w', pady=2)
            self.drop_height_var = tk.StringVar(value=str(lw.drop_height_relative))
            ttk.Entry(self.specific_frame, textvariable=self.drop_height_var, width=20).grid(row=0, column=1, pady=2)

    def on_save(self):
        """Save changes to the labware object"""
        try:
            # Get basic parameters
            size_x = float(self.size_x_var.get())
            size_y = float(self.size_y_var.get())
            size_z = float(self.size_z_var.get())
            offset_x = float(self.offset_x_var.get())
            offset_y = float(self.offset_y_var.get())
            offset = (offset_x, offset_y)

            # Update labware in place
            self.labware.size_x = size_x
            self.labware.size_y = size_y
            self.labware.size_z = size_z
            self.labware.offset = offset

            # Update type-specific parameters
            if isinstance(self.labware, TipDropzone):
                self.labware.drop_height_relative = float(self.drop_height_var.get())

            # Note: Grid structure (rows/columns/hooks/zones) cannot be changed

            self.result = True
            self.destroy()

        except ValueError as e:
            messagebox.showerror("Invalid Input", f"Please check your inputs:\n{str(e)}")

    def on_cancel(self):
        """Cancel dialog"""
        self.result = None
        self.destroy()


class CreateSlotDialog(tk.Toplevel):
    """Dialog for creating new slots"""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Create New Slot")
        self.geometry("400x300")
        self.result = None

        # Make dialog modal
        self.transient(parent)
        self.grab_set()

        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Slot Parameters
        params_frame = ttk.LabelFrame(main_frame, text="Slot Parameters", padding="10")
        params_frame.pack(fill=tk.BOTH, expand=True, pady=5)

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


class CreateLabwareDialog(tk.Toplevel):
    """Dialog for creating new labware"""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Create New Labware")
        self.geometry("500x600")
        self.result = None

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

        self.labware_type = tk.StringVar(value="Labware")
        types = ["Labware", "Plate", "ReservoirHolder", "PipetteHolder", "TipDropzone"]

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

        # Dimensions
        ttk.Label(basic_frame, text="Size X (mm):").grid(row=1, column=0, sticky='w', pady=2)
        self.size_x_var = tk.StringVar(value="127.76")
        ttk.Entry(basic_frame, textvariable=self.size_x_var, width=30).grid(row=1, column=1, pady=2)

        ttk.Label(basic_frame, text="Size Y (mm):").grid(row=2, column=0, sticky='w', pady=2)
        self.size_y_var = tk.StringVar(value="85.48")
        ttk.Entry(basic_frame, textvariable=self.size_y_var, width=30).grid(row=2, column=1, pady=2)

        ttk.Label(basic_frame, text="Size Z (mm):").grid(row=3, column=0, sticky='w', pady=2)
        self.size_z_var = tk.StringVar(value="14.22")
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
            ttk.Label(self.specific_frame, text="Rows:").grid(row=0, column=0, sticky='w', pady=2)
            self.rows_var = tk.StringVar(value="8")
            ttk.Entry(self.specific_frame, textvariable=self.rows_var, width=20).grid(row=0, column=1, pady=2)

            ttk.Label(self.specific_frame, text="Columns:").grid(row=1, column=0, sticky='w', pady=2)
            self.cols_var = tk.StringVar(value="12")
            ttk.Entry(self.specific_frame, textvariable=self.cols_var, width=20).grid(row=1, column=1, pady=2)

            ttk.Label(self.specific_frame, text="Well Capacity (µL):").grid(row=2, column=0, sticky='w', pady=2)
            self.capacity_var = tk.StringVar(value="1000")
            ttk.Entry(self.specific_frame, textvariable=self.capacity_var, width=20).grid(row=2, column=1, pady=2)

        elif lw_type == "ReservoirHolder":
            ttk.Label(self.specific_frame, text="Hooks Across X:").grid(row=0, column=0, sticky='w', pady=2)
            self.hooks_x_var = tk.StringVar(value="12")
            ttk.Entry(self.specific_frame, textvariable=self.hooks_x_var, width=20).grid(row=0, column=1, pady=2)

            ttk.Label(self.specific_frame, text="Hooks Across Y:").grid(row=1, column=0, sticky='w', pady=2)
            self.hooks_y_var = tk.StringVar(value="1")
            ttk.Entry(self.specific_frame, textvariable=self.hooks_y_var, width=20).grid(row=1, column=1, pady=2)

        elif lw_type == "PipetteHolder":
            ttk.Label(self.specific_frame, text="Zones Across X:").grid(row=0, column=0, sticky='w', pady=2)
            self.zones_x_var = tk.StringVar(value="12")
            ttk.Entry(self.specific_frame, textvariable=self.zones_x_var, width=20).grid(row=0, column=1, pady=2)

            ttk.Label(self.specific_frame, text="Zones Across Y:").grid(row=1, column=0, sticky='w', pady=2)
            self.zones_y_var = tk.StringVar(value="1")
            ttk.Entry(self.specific_frame, textvariable=self.zones_y_var, width=20).grid(row=1, column=1, pady=2)

        elif lw_type == "TipDropzone":
            ttk.Label(self.specific_frame, text="Drop Height (mm):").grid(row=0, column=0, sticky='w', pady=2)
            self.drop_height_var = tk.StringVar(value="20")
            ttk.Entry(self.specific_frame, textvariable=self.drop_height_var, width=20).grid(row=0, column=1, pady=2)

    def on_type_change(self):
        """Handle labware type change"""
        self.create_specific_fields()

    def on_create(self):
        """Create the labware object"""
        try:
            # Get basic parameters
            labware_id = self.id_var.get() or None
            size_x = float(self.size_x_var.get())
            size_y = float(self.size_y_var.get())
            size_z = float(self.size_z_var.get())
            offset_x = float(self.offset_x_var.get())
            offset_y = float(self.offset_y_var.get())
            offset = (offset_x, offset_y)

            # Create labware based on type
            lw_type = self.labware_type.get()

            if lw_type == "Labware":
                self.result = Labware(
                    size_x=size_x,
                    size_y=size_y,
                    size_z=size_z,
                    offset=offset,
                    labware_id=labware_id
                )

            elif lw_type == "Plate":
                rows = int(self.rows_var.get())
                cols = int(self.cols_var.get())
                capacity = float(self.capacity_var.get())

                self.result = Plate(
                    size_x=size_x,
                    size_y=size_y,
                    size_z=size_z,
                    offset=offset,
                    rows=rows,
                    columns=cols,
                    labware_id=labware_id,
                    well_capacity=capacity
                )

            elif lw_type == "ReservoirHolder":
                hooks_x = int(self.hooks_x_var.get())
                hooks_y = int(self.hooks_y_var.get())

                self.result = ReservoirHolder(
                    size_x=size_x,
                    size_y=size_y,
                    size_z=size_z,
                    offset=offset,
                    hooks_across_x=hooks_x,
                    hooks_across_y=hooks_y,
                    labware_id=labware_id
                )

            elif lw_type == "PipetteHolder":
                zones_x = int(self.zones_x_var.get())
                zones_y = int(self.zones_y_var.get())

                self.result = PipetteHolder(
                    size_x=size_x,
                    size_y=size_y,
                    size_z=size_z,
                    offset=offset,
                    zones_across_x=zones_x,
                    zones_across_y=zones_y,
                    labware_id=labware_id
                )

            elif lw_type == "TipDropzone":
                drop_height = float(self.drop_height_var.get())

                self.result = TipDropzone(
                    size_x=size_x,
                    size_y=size_y,
                    size_z=size_z,
                    offset=offset,
                    drop_height_relative=drop_height,
                    labware_id=labware_id
                )

            self.destroy()

        except ValueError as e:
            messagebox.showerror("Invalid Input", f"Please check your inputs:\n{str(e)}")

    def on_cancel(self):
        """Cancel dialog"""
        self.result = None
        self.destroy()


class CreateSlotDialog(tk.Toplevel):
    """Dialog for creating new slots"""

    def __init__(self, parent, slot=None):
        super().__init__(parent)
        self.title("Edit Slot" if slot else "Create New Slot")
        self.geometry("400x300")
        self.result = None
        self.slot = slot  # If editing existing slot

        # Make dialog modal
        self.transient(parent)
        self.grab_set()

        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Slot Parameters
        params_frame = ttk.LabelFrame(main_frame, text="Slot Parameters", padding="10")
        params_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # Slot ID
        ttk.Label(params_frame, text="Slot ID:").grid(row=0, column=0, sticky='w', pady=5)
        self.id_var = tk.StringVar(value=self.slot.slot_id if self.slot else "")
        id_entry = ttk.Entry(params_frame, textvariable=self.id_var, width=25)
        id_entry.grid(row=0, column=1, pady=5)
        if self.slot:
            id_entry.config(state='readonly')  # Can't change ID when editing

        # Range X
        ttk.Label(params_frame, text="Range X Min (mm):").grid(row=1, column=0, sticky='w', pady=5)
        self.x_min_var = tk.StringVar(value=str(self.slot.range_x[0]) if self.slot else "0")
        ttk.Entry(params_frame, textvariable=self.x_min_var, width=25).grid(row=1, column=1, pady=5)

        ttk.Label(params_frame, text="Range X Max (mm):").grid(row=2, column=0, sticky='w', pady=5)
        self.x_max_var = tk.StringVar(value=str(self.slot.range_x[1]) if self.slot else "150")
        ttk.Entry(params_frame, textvariable=self.x_max_var, width=25).grid(row=2, column=1, pady=5)

        # Range Y
        ttk.Label(params_frame, text="Range Y Min (mm):").grid(row=3, column=0, sticky='w', pady=5)
        self.y_min_var = tk.StringVar(value=str(self.slot.range_y[0]) if self.slot else "0")
        ttk.Entry(params_frame, textvariable=self.y_min_var, width=25).grid(row=3, column=1, pady=5)

        ttk.Label(params_frame, text="Range Y Max (mm):").grid(row=4, column=0, sticky='w', pady=5)
        self.y_max_var = tk.StringVar(value=str(self.slot.range_y[1]) if self.slot else "100")
        ttk.Entry(params_frame, textvariable=self.y_max_var, width=25).grid(row=4, column=1, pady=5)

        # Range Z
        ttk.Label(params_frame, text="Range Z (mm):").grid(row=5, column=0, sticky='w', pady=5)
        self.z_var = tk.StringVar(value=str(self.slot.range_z) if self.slot else "100")
        ttk.Entry(params_frame, textvariable=self.z_var, width=25).grid(row=5, column=1, pady=5)

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)

        btn_text = "Save" if self.slot else "Create"
        ttk.Button(btn_frame, text=btn_text, command=self.on_create).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.on_cancel).pack(side=tk.RIGHT)

    def on_create(self):
        """Create or update the slot object"""
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

            if self.slot:
                # Editing existing slot - update in place
                self.slot.range_x = (x_min, x_max)
                self.slot.range_y = (y_min, y_max)
                self.slot.range_z = z
                self.result = self.slot
            else:
                # Creating new slot
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


class EditLabwareDialog(tk.Toplevel):
    """Dialog for editing existing labware"""

    def __init__(self, parent, labware):
        super().__init__(parent)
        self.title(f"Edit Labware - {labware.labware_id}")
        self.geometry("500x600")
        self.result = None
        self.labware = labware

        # Make dialog modal
        self.transient(parent)
        self.grab_set()

        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Labware Type (read-only)
        type_frame = ttk.LabelFrame(main_frame, text="Labware Type (Cannot Change)", padding="10")
        type_frame.pack(fill=tk.X, pady=5)

        ttk.Label(type_frame, text=self.labware.__class__.__name__,
                  font=('Arial', 12, 'bold')).pack(anchor='w')

        # Basic Parameters
        basic_frame = ttk.LabelFrame(main_frame, text="Basic Parameters", padding="10")
        basic_frame.pack(fill=tk.X, pady=5)

        # Labware ID (read-only)
        ttk.Label(basic_frame, text="Labware ID:").grid(row=0, column=0, sticky='w', pady=2)
        id_label = ttk.Label(basic_frame, text=self.labware.labware_id, font=('Arial', 9, 'bold'))
        id_label.grid(row=0, column=1, sticky='w', pady=2)

        # Dimensions
        ttk.Label(basic_frame, text="Size X (mm):").grid(row=1, column=0, sticky='w', pady=2)
        self.size_x_var = tk.StringVar(value=str(self.labware.size_x))
        ttk.Entry(basic_frame, textvariable=self.size_x_var, width=30).grid(row=1, column=1, pady=2)

        ttk.Label(basic_frame, text="Size Y (mm):").grid(row=2, column=0, sticky='w', pady=2)
        self.size_y_var = tk.StringVar(value=str(self.labware.size_y))
        ttk.Entry(basic_frame, textvariable=self.size_y_var, width=30).grid(row=2, column=1, pady=2)

        ttk.Label(basic_frame, text="Size Z (mm):").grid(row=3, column=0, sticky='w', pady=2)
        self.size_z_var = tk.StringVar(value=str(self.labware.size_z))
        ttk.Entry(basic_frame, textvariable=self.size_z_var, width=30).grid(row=3, column=1, pady=2)

        # Offset
        ttk.Label(basic_frame, text="Offset X (mm):").grid(row=4, column=0, sticky='w', pady=2)
        self.offset_x_var = tk.StringVar(value=str(self.labware.offset[0]))
        ttk.Entry(basic_frame, textvariable=self.offset_x_var, width=30).grid(row=4, column=1, pady=2)

        ttk.Label(basic_frame, text="Offset Y (mm):").grid(row=5, column=0, sticky='w', pady=2)
        self.offset_y_var = tk.StringVar(value=str(self.labware.offset[1]))
        ttk.Entry(basic_frame, textvariable=self.offset_y_var, width=30).grid(row=5, column=1, pady=2)

        # Type-Specific Parameters Frame
        self.specific_frame = ttk.LabelFrame(main_frame, text="Type-Specific Parameters", padding="10")
        self.specific_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # Create type-specific fields
        self.create_specific_fields()

        # Warning label
        warning_frame = ttk.Frame(main_frame)
        warning_frame.pack(fill=tk.X, pady=5)
        warning_label = ttk.Label(
            warning_frame,
            text="⚠ Warning: Changing parameters may cause validation errors\nif labware no longer fits in its slot.",
            foreground='orange',
            font=('Arial', 8)
        )
        warning_label.pack()

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)

        ttk.Button(btn_frame, text="Save Changes", command=self.on_save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.on_cancel).pack(side=tk.RIGHT)

    def create_specific_fields(self):
        """Create fields specific to the labware type"""
        # Clear existing widgets
        for widget in self.specific_frame.winfo_children():
            widget.destroy()

        lw = self.labware

        if isinstance(lw, Plate):
            ttk.Label(self.specific_frame, text="Rows:").grid(row=0, column=0, sticky='w', pady=2)
            self.rows_var = tk.StringVar(value=str(lw._rows))
            rows_entry = ttk.Entry(self.specific_frame, textvariable=self.rows_var, width=20)
            rows_entry.grid(row=0, column=1, pady=2)
            rows_entry.config(state='readonly')  # Don't allow changing grid structure

            ttk.Label(self.specific_frame, text="Columns:").grid(row=1, column=0, sticky='w', pady=2)
            self.cols_var = tk.StringVar(value=str(lw._columns))
            cols_entry = ttk.Entry(self.specific_frame, textvariable=self.cols_var, width=20)
            cols_entry.grid(row=1, column=1, pady=2)
            cols_entry.config(state='readonly')  # Don't allow changing grid structure

            ttk.Label(self.specific_frame, text="(Grid structure cannot be changed)",
                      font=('Arial', 8, 'italic'), foreground='gray').grid(row=2, column=0, columnspan=2, pady=2)

        elif isinstance(lw, ReservoirHolder):
            ttk.Label(self.specific_frame, text="Hooks Across X:").grid(row=0, column=0, sticky='w', pady=2)
            self.hooks_x_var = tk.StringVar(value=str(lw.hooks_across_x))
            hooks_x_entry = ttk.Entry(self.specific_frame, textvariable=self.hooks_x_var, width=20)
            hooks_x_entry.grid(row=0, column=1, pady=2)
            hooks_x_entry.config(state='readonly')

            ttk.Label(self.specific_frame, text="Hooks Across Y:").grid(row=1, column=0, sticky='w', pady=2)
            self.hooks_y_var = tk.StringVar(value=str(lw.hooks_across_y))
            hooks_y_entry = ttk.Entry(self.specific_frame, textvariable=self.hooks_y_var, width=20)
            hooks_y_entry.grid(row=1, column=1, pady=2)
            hooks_y_entry.config(state='readonly')

            ttk.Label(self.specific_frame, text="(Grid structure cannot be changed)",
                      font=('Arial', 8, 'italic'), foreground='gray').grid(row=2, column=0, columnspan=2, pady=2)

        elif isinstance(lw, PipetteHolder):
            ttk.Label(self.specific_frame, text="Zones Across X:").grid(row=0, column=0, sticky='w', pady=2)
            self.zones_x_var = tk.StringVar(value=str(lw.zones_across_x))
            zones_x_entry = ttk.Entry(self.specific_frame, textvariable=self.zones_x_var, width=20)
            zones_x_entry.grid(row=0, column=1, pady=2)
            zones_x_entry.config(state='readonly')

            ttk.Label(self.specific_frame, text="Zones Across Y:").grid(row=1, column=0, sticky='w', pady=2)
            self.zones_y_var = tk.StringVar(value=str(lw.zones_across_y))
            zones_y_entry = ttk.Entry(self.specific_frame, textvariable=self.zones_y_var, width=20)
            zones_y_entry.grid(row=1, column=1, pady=2)
            zones_y_entry.config(state='readonly')

            ttk.Label(self.specific_frame, text="(Grid structure cannot be changed)",
                      font=('Arial', 8, 'italic'), foreground='gray').grid(row=2, column=0, columnspan=2, pady=2)

        elif isinstance(lw, TipDropzone):
            ttk.Label(self.specific_frame, text="Drop Height (mm):").grid(row=0, column=0, sticky='w', pady=2)
            self.drop_height_var = tk.StringVar(value=str(lw.drop_height_relative))
            ttk.Entry(self.specific_frame, textvariable=self.drop_height_var, width=20).grid(row=0, column=1, pady=2)

    def on_save(self):
        """Save changes to the labware object"""
        try:
            # Get basic parameters
            size_x = float(self.size_x_var.get())
            size_y = float(self.size_y_var.get())
            size_z = float(self.size_z_var.get())
            offset_x = float(self.offset_x_var.get())
            offset_y = float(self.offset_y_var.get())
            offset = (offset_x, offset_y)

            # Update labware in place
            self.labware.size_x = size_x
            self.labware.size_y = size_y
            self.labware.size_z = size_z
            self.labware.offset = offset

            # Update type-specific parameters
            if isinstance(self.labware, TipDropzone):
                self.labware.drop_height_relative = float(self.drop_height_var.get())

            # Note: Grid structure (rows/columns/hooks/zones) cannot be changed

            self.result = True
            self.destroy()

        except ValueError as e:
            messagebox.showerror("Invalid Input", f"Please check your inputs:\n{str(e)}")

    def on_cancel(self):
        """Cancel dialog"""
        self.result = None
        self.destroy()


class CreateSlotDialog(tk.Toplevel):
    """Dialog for creating new slots"""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Create New Slot")
        self.geometry("400x300")
        self.result = None

        # Make dialog modal
        self.transient(parent)
        self.grab_set()

        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Slot Parameters
        params_frame = ttk.LabelFrame(main_frame, text="Slot Parameters", padding="10")
        params_frame.pack(fill=tk.BOTH, expand=True, pady=5)

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
        self.geometry("350x250")
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

        # Created but not yet placed labware
        self.unplaced_labware = []

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

        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Create Slot", command=self.create_slot)
        edit_menu.add_command(label="Create Labware", command=self.create_labware)

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

        # Right panel - Controls
        control_frame = ttk.Frame(main_frame, width=300)
        control_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        control_frame.pack_propagate(False)

        # Title
        ttk.Label(control_frame, text="Deck Editor", font=('Arial', 14, 'bold')).pack(pady=10)

        # Action Buttons
        action_frame = ttk.LabelFrame(control_frame, text="Actions", padding=10)
        action_frame.pack(fill=tk.X, pady=5)

        ttk.Button(action_frame, text="Create Slot", command=self.create_slot).pack(fill=tk.X, pady=2)
        ttk.Button(action_frame, text="Create Labware", command=self.create_labware).pack(fill=tk.X, pady=2)

        # Deck info
        info_frame = ttk.LabelFrame(control_frame, text="Deck Info", padding=10)
        info_frame.pack(fill=tk.X, pady=5)

        self.deck_info_label = ttk.Label(info_frame, text="", justify=tk.LEFT)
        self.deck_info_label.pack(anchor='w')

        # Slots list
        slots_frame = ttk.LabelFrame(control_frame, text="Slots", padding=10)
        slots_frame.pack(fill=tk.X, pady=5)

        self.slots_listbox = tk.Listbox(slots_frame, height=6)
        self.slots_listbox.pack(fill=tk.X)
        self.slots_listbox.bind('<<ListboxSelect>>', self.on_slot_select)
        self.slots_listbox.bind('<Button-3>', self.on_slot_right_click)

        # Placed Labware list
        labware_frame = ttk.LabelFrame(control_frame, text="Placed Labware", padding=10)
        labware_frame.pack(fill=tk.X, pady=5)

        self.labware_listbox = tk.Listbox(labware_frame, height=6)
        self.labware_listbox.pack(fill=tk.X)
        self.labware_listbox.bind('<<ListboxSelect>>', self.on_labware_select)
        self.labware_listbox.bind('<Button-3>', self.on_labware_right_click)

        # Unplaced Labware list
        unplaced_frame = ttk.LabelFrame(control_frame, text="Unplaced Labware", padding=10)
        unplaced_frame.pack(fill=tk.X, pady=5)

        self.unplaced_listbox = tk.Listbox(unplaced_frame, height=4)
        self.unplaced_listbox.pack(fill=tk.X)
        self.unplaced_listbox.bind('<Button-3>', self.on_unplaced_right_click)
        self.unplaced_listbox.bind('<Double-Button-1>', self.on_unplaced_double_click)

        # Add Place button
        ttk.Button(unplaced_frame, text="Place on Slot", command=self.place_selected_unplaced).pack(fill=tk.X,
                                                                                                    pady=(5, 0))

        # Info panel
        self.info_frame = ttk.LabelFrame(control_frame, text="Selection Info", padding=10)
        self.info_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.info_text = tk.Text(self.info_frame, height=10, wrap=tk.WORD)
        self.info_text.pack(fill=tk.BOTH, expand=True)

        # Control buttons
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(fill=tk.X, pady=5)

        ttk.Button(btn_frame, text="Refresh", command=self.draw_deck).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="Clear Selection", command=self.clear_selection).pack(fill=tk.X, pady=2)

        # Zoom controls
        zoom_frame = ttk.Frame(control_frame)
        zoom_frame.pack(fill=tk.X, pady=5)

        ttk.Button(zoom_frame, text="Zoom In", command=self.zoom_in).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        ttk.Button(zoom_frame, text="Zoom Out", command=self.zoom_out).pack(side=tk.LEFT, expand=True, fill=tk.X,
                                                                            padx=2)

        # Canvas bindings
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<Button-3>", self.on_canvas_right_click)

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
            self.draw_deck()
            messagebox.showinfo("Success", "New deck created!")

    def create_slot(self):
        """Open dialog to create a new slot"""
        dialog = CreateSlotDialog(self.root)
        self.root.wait_window(dialog)

        if dialog.result:
            try:
                self.deck.add_slots([dialog.result])
                self.draw_deck()
                messagebox.showinfo("Success", f"Slot '{dialog.result.slot_id}' created!")
            except ValueError as e:
                messagebox.showerror("Error", str(e))

    def create_labware(self):
        """Open dialog to create new labware"""
        dialog = CreateLabwareDialog(self.root)
        self.root.wait_window(dialog)

        if dialog.result:
            self.unplaced_labware.append(dialog.result)
            self.update_unplaced_list()
            messagebox.showinfo("Success",
                                f"Labware '{dialog.result.labware_id}' created!\nRight-click to place it on a slot.")

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

        # Update lists
        self.update_listboxes()
        self.update_deck_info()

    def draw_grid(self):
        """Draw background grid"""
        step = 50  # mm

        x = self.deck.range_x[0]
        while x <= self.deck.range_x[1]:
            x1, y1 = self.mm_to_canvas(x, self.deck.range_y[0])
            x2, y2 = self.mm_to_canvas(x, self.deck.range_y[1])
            self.canvas.create_line(x1, y1, x2, y2, fill='lightgray', tags='grid')
            x += step

        y = self.deck.range_y[0]
        while y <= self.deck.range_y[1]:
            x1, y1 = self.mm_to_canvas(self.deck.range_x[0], y)
            x2, y2 = self.mm_to_canvas(self.deck.range_x[1], y)
            self.canvas.create_line(x1, y1, x2, y2, fill='lightgray', tags='grid')
            y += step

    def draw_slot(self, slot_id, slot):
        """Draw a single slot"""
        x1, y1 = self.mm_to_canvas(slot.range_x[0], slot.range_y[0])
        x2, y2 = self.mm_to_canvas(slot.range_x[1], slot.range_y[1])

        rect_id = self.canvas.create_rectangle(
            x1, y1, x2, y2,
            fill='lightblue', outline='blue', width=2,
            tags=('slot', slot_id)
        )

        # Label
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        self.canvas.create_text(
            cx, cy, text=slot_id,
            font=('Arial', 10, 'bold'),
            tags=('slot_label', slot_id)
        )

        self.canvas.addtag_withtag(f'slot_{slot_id}', rect_id)

    def draw_labware(self, lw_id, lw):
        """Draw a single labware"""
        if not lw.position:
            return

        x, y = lw.position
        x1, y1 = self.mm_to_canvas(x, y)
        x2, y2 = self.mm_to_canvas(x + lw.size_x, y + lw.size_y)

        rect_id = self.canvas.create_rectangle(
            x1, y1, x2, y2,
            fill='lightcoral', outline='red', width=2,
            tags=('labware', lw_id)
        )

        # Label
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        self.canvas.create_text(
            cx, cy, text=lw_id,
            font=('Arial', 9),
            tags=('labware_label', lw_id)
        )

        self.canvas.addtag_withtag(f'labware_{lw_id}', rect_id)

    def update_listboxes(self):
        """Update all listboxes"""
        # Slots
        self.slots_listbox.delete(0, tk.END)
        for slot_id in self.deck.slots.keys():
            self.slots_listbox.insert(tk.END, slot_id)

        # Placed labware
        self.labware_listbox.delete(0, tk.END)
        for lw_id in self.deck.labware.keys():
            self.labware_listbox.insert(tk.END, lw_id)

        # Unplaced labware
        self.update_unplaced_list()

    def update_unplaced_list(self):
        """Update unplaced labware list"""
        self.unplaced_listbox.delete(0, tk.END)
        for lw in self.unplaced_labware:
            self.unplaced_listbox.insert(tk.END, f"{lw.labware_id} ({lw.__class__.__name__})")

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

    def on_slot_right_click(self, event):
        """Handle right-click on slot list"""
        selection = self.slots_listbox.curselection()
        if not selection:
            return

        slot_id = self.slots_listbox.get(selection[0])

        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label=f"Edit Slot", command=lambda: self.edit_slot_dialog(slot_id))
        menu.add_command(label=f"Remove Slot", command=lambda: self.remove_slot_dialog(slot_id))
        menu.post(event.x_root, event.y_root)

    def on_labware_right_click(self, event):
        """Handle right-click on placed labware list"""
        selection = self.labware_listbox.curselection()
        if not selection:
            return

        lw_id = self.labware_listbox.get(selection[0])

        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label=f"Edit Labware", command=lambda: self.edit_labware_dialog(lw_id))
        menu.add_command(label=f"Remove Labware", command=lambda: self.remove_labware_dialog(lw_id))
        menu.post(event.x_root, event.y_root)

    def on_unplaced_right_click(self, event):
        """Handle right-click on unplaced labware list"""
        selection = self.unplaced_listbox.curselection()
        if not selection:
            return

        labware = self.unplaced_labware[selection[0]]

        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Place on Slot", command=lambda: self.place_labware(labware))
        menu.add_command(label="Delete", command=lambda: self.delete_unplaced_labware(labware))
        menu.post(event.x_root, event.y_root)

    def on_unplaced_double_click(self, event):
        """Handle double-click on unplaced labware list"""
        selection = self.unplaced_listbox.curselection()
        if selection:
            labware = self.unplaced_labware[selection[0]]
            self.place_labware(labware)

    def place_selected_unplaced(self):
        """Place the selected unplaced labware"""
        selection = self.unplaced_listbox.curselection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select an unplaced labware to place.")
            return

        labware = self.unplaced_labware[selection[0]]
        self.place_labware(labware)

    def delete_unplaced_labware(self, labware):
        """Delete unplaced labware"""
        result = messagebox.askyesno("Confirm", f"Delete labware '{labware.labware_id}'?")
        if result:
            self.unplaced_labware.remove(labware)
            self.update_unplaced_list()

    def remove_slot_dialog(self, slot_id):
        """Remove slot from deck"""
        # Check if slot has labware
        slot = self.deck.slots[slot_id]
        if slot.labware_stack:
            messagebox.showerror("Error", f"Slot '{slot_id}' contains labware. Remove labware first.")
            return

        result = messagebox.askyesno("Confirm", f"Remove slot '{slot_id}'?")
        if result:
            del self.deck.slots[slot_id]
            self.draw_deck()

    def remove_labware_dialog(self, lw_id):
        """Remove labware from deck"""
        result = messagebox.askyesno("Confirm", f"Remove labware '{lw_id}'?")
        if result:
            slot_id = self.deck.get_slot_for_labware(lw_id)
            if slot_id:
                lw = self.deck.labware[lw_id]
                self.deck.remove_labware(lw, slot_id)
                self.draw_deck()

    def edit_slot_dialog(self, slot_id):
        """Edit an existing slot"""
        if slot_id not in self.deck.slots:
            messagebox.showerror("Error", f"Slot '{slot_id}' not found")
            return

        slot = self.deck.slots[slot_id]
        dialog = EditSlotDialog(self.root, slot)
        self.root.wait_window(dialog)

        if dialog.result:
            # Validate the edited slot
            errors = self.validate_slot_edit(slot)

            if errors:
                # Restore would require keeping old values, so show error and let user try again
                error_msg = "Cannot save changes:\n\n" + "\n".join(errors)
                error_msg += "\n\nPlease adjust the parameters and try again."
                messagebox.showerror("Validation Error", error_msg)
                # Re-open dialog for corrections
                self.edit_slot_dialog(slot_id)
            else:
                # Success! Redraw
                self.draw_deck()
                messagebox.showinfo("Success", f"Slot '{slot_id}' updated successfully!")

    def edit_labware_dialog(self, lw_id):
        """Edit an existing labware"""
        if lw_id not in self.deck.labware:
            messagebox.showerror("Error", f"Labware '{lw_id}' not found")
            return

        labware = self.deck.labware[lw_id]

        # Store old values for restoration if validation fails
        old_size_x = labware.size_x
        old_size_y = labware.size_y
        old_size_z = labware.size_z
        old_offset = labware.offset
        old_drop_height = labware.drop_height_relative if isinstance(labware, TipDropzone) else None

        dialog = EditLabwareDialog(self.root, labware)
        self.root.wait_window(dialog)

        if dialog.result:
            # Validate the edited labware
            errors = self.validate_labware_edit(labware)

            if errors:
                # Restore old values
                labware.size_x = old_size_x
                labware.size_y = old_size_y
                labware.size_z = old_size_z
                labware.offset = old_offset
                if old_drop_height is not None:
                    labware.drop_height_relative = old_drop_height

                error_msg = "Cannot save changes:\n\n" + "\n".join(errors)
                error_msg += "\n\nChanges have been reverted."
                messagebox.showerror("Validation Error", error_msg)
            else:
                # Success! Recalculate position and redraw
                slot_id = self.deck.get_slot_for_labware(lw_id)
                if slot_id:
                    slot = self.deck.slots[slot_id]
                    # Reallocate position with new dimensions
                    slot._allocate_position(labware, None, None)

                self.draw_deck()
                messagebox.showinfo("Success", f"Labware '{lw_id}' updated successfully!")

    def validate_slot_edit(self, slot):
        """Validate edited slot - returns list of error messages"""
        errors = []

        # Check if slot is still within deck boundaries
        if not (self.deck.range_x[0] <= slot.range_x[0] and
                slot.range_x[1] <= self.deck.range_x[1] and
                self.deck.range_y[0] <= slot.range_y[0] and
                slot.range_y[1] <= self.deck.range_y[1]):
            errors.append(f"⚠ Slot extends outside deck boundaries\n"
                          f"   Deck: X{self.deck.range_x}, Y{self.deck.range_y}\n"
                          f"   Slot: X{slot.range_x}, Y{slot.range_y}")

        # Check overlap with other slots
        for other_id, other_slot in self.deck.slots.items():
            if other_id == slot.slot_id:
                continue
            if self.deck._overlaps(slot, other_slot):
                errors.append(f"⚠ Slot overlaps with slot '{other_id}'")

        # Check if all labware in this slot still fit
        for lw_id, (lw, z_range) in slot.labware_stack.items():
            min_z, max_z = z_range

            # Check XY fit
            fits_xy = (abs(slot.range_x[1] - slot.range_x[0]) >= lw.size_x and
                       abs(slot.range_y[1] - slot.range_y[0]) >= lw.size_y)
            if not fits_xy:
                errors.append(f"⚠ Labware '{lw_id}' no longer fits in X/Y dimensions\n"
                              f"   Slot: {abs(slot.range_x[1] - slot.range_x[0]):.1f} x {abs(slot.range_y[1] - slot.range_y[0]):.1f} mm\n"
                              f"   Labware: {lw.size_x:.1f} x {lw.size_y:.1f} mm")

            # Check Z fit
            if max_z > slot.range_z:
                errors.append(f"⚠ Labware '{lw_id}' exceeds slot Z height\n"
                              f"   Slot Z: {slot.range_z} mm\n"
                              f"   Labware needs: {max_z} mm")

        return errors

    def validate_labware_edit(self, labware):
        """Validate edited labware - returns list of error messages"""
        errors = []

        # Find which slot this labware is in
        slot_id = self.deck.get_slot_for_labware(labware.labware_id)

        if slot_id:
            slot = self.deck.slots[slot_id]
            lw_data = slot.labware_stack[labware.labware_id]
            lw, z_range = lw_data
            min_z, max_z = z_range

            # Check XY fit
            fits_xy = (abs(slot.range_x[1] - slot.range_x[0]) >= labware.size_x and
                       abs(slot.range_y[1] - slot.range_y[0]) >= labware.size_y)
            if not fits_xy:
                errors.append(f"⚠ Labware no longer fits in slot '{slot_id}' (X/Y too large)\n"
                              f"   Slot: {abs(slot.range_x[1] - slot.range_x[0]):.1f} x {abs(slot.range_y[1] - slot.range_y[0]):.1f} mm\n"
                              f"   Labware: {labware.size_x:.1f} x {labware.size_y:.1f} mm")

            # Check Z fit
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
            info += f"\nZones X: {lw.zones_across_x}\n"
            info += f"Zones Y: {lw.zones_across_y}\n"

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

    def on_slot_select(self, event):
        """Handle slot listbox selection"""
        selection = self.slots_listbox.curselection()
        if selection:
            slot_id = self.slots_listbox.get(selection[0])
            self.select_slot(slot_id)

    def on_labware_select(self, event):
        """Handle labware listbox selection"""
        selection = self.labware_listbox.curselection()
        if selection:
            lw_id = self.labware_listbox.get(selection[0])
            self.select_labware(lw_id)

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
                # Save both deck and unplaced labware
                data = {
                    'deck': self.deck.to_dict(),
                    'unplaced_labware': [lw.to_dict() for lw in self.unplaced_labware]
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

    # You can add some initial slots if desired
    # slot1 = Slot(range_x=(50, 200), range_y=(50, 200), range_z=100, slot_id="A1")
    # deck.add_slots([slot1])

    # Run GUI
    gui = DeckGUI(deck)
    gui.run()