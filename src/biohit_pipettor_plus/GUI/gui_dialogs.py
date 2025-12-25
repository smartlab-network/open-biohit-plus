#todo combine code to repeat duplication.  speed reduction & easier to maintain

import tkinter as tk
from tkinter import messagebox
from ..deck_structure import *
from .ui_helper import create_form, ScrollableDialog, create_button_bar, create_scrolled_listbox, update_detailed_info_text, draw_labware_grid
import ttkbootstrap as ttk
import copy

class LabwareDialog(ScrollableDialog):
    """Refactored Manager Dialog for all Labware types."""

    def __init__(self, parent, available_wells, available_reservoirs, available_individual_holders):
        super().__init__(parent, title="Create New Labware", size="700x750")

        self.repo = {
            "Well": available_wells,
            "Reservoir": available_reservoirs,
            "Holder": available_individual_holders
        }

        # Selection State
        self.selected_well = None
        self.selected_holder = None
        self.res_template = None

        self.create_widgets()

    def create_widgets(self):
        # 1. Type Selection
        type_frame = ttk.Labelframe(self.scroll_frame, text="Labware Type", padding="10")
        type_frame.pack(fill=tk.X, pady=5)

        self.labware_type = tk.StringVar(value="Plate")
        types = ["Plate", "ReservoirHolder", "PipetteHolder", "TipDropzone", "Stack"]
        for t in types:
            ttk.Radiobutton(type_frame, text=t, variable=self.labware_type,
                            value=t, command=self.refresh_ui).pack(side=tk.LEFT, padx=10)

        # 2. Basic Parameters
        basic_frame = ttk.Labelframe(self.scroll_frame, text="Basic Geometry", padding="10")
        basic_frame.pack(fill=tk.X, pady=5)
        self.basic_inputs = create_form(basic_frame, [
            ("Labware ID:", "id", "entry", "", None, "text"),
            ("Size X (mm):", "sx", "entry", "", None, "numeric"),
            ("Size Y (mm):", "sy", "entry", "", None, "numeric"),
            ("Size Z (mm):", "sz", "entry", "", None, "numeric"),
            ("Offset X (mm):", "off_x", "entry", "0.0", None, "numeric"),
            ("Offset Y (mm):", "off_y", "entry", "0.0", None, "numeric"),
            ("Stackable:", "stackable", "checkbox", False, None, None)
        ])

        # 3. Dynamic Specific Parameters Area
        self.spec_area = ttk.Frame(self.scroll_frame)
        self.spec_area.pack(fill=tk.BOTH, expand=True)

        # 4. Global Button Bar
        self.add_button_bar(create_cmd=self.on_create)

        self.refresh_ui()

    def refresh_ui(self):
        """Rebuilds type-specific fields when the Radiobutton changes."""
        for w in self.spec_area.winfo_children(): w.destroy()
        lw_type = self.labware_type.get()
        spec_frame = ttk.Labelframe(self.spec_area, text=f"{lw_type} Settings", padding="10")
        spec_frame.pack(fill=tk.X, pady=5)

        if lw_type == "Plate":
            self.spec_inputs = create_form(spec_frame, [
                ("Rows (Y):", "ry", "entry", "8", None, "numeric"),
                ("Cols (X):", "cx", "entry", "12", None, "numeric"),
                ("Add Height:", "add", "entry", "0.0", None, "numeric"),
                ("Rem Height:", "rem", "entry", "0.0", None, "numeric")
            ])
            self.create_selection_row(spec_frame, "Well", self.select_well)

        elif lw_type == "ReservoirHolder":
            self.spec_inputs = create_form(spec_frame, [
                ("Hooks X:", "hx", "entry", "7", None, "numeric"),
                ("Hooks Y:", "hy", "entry", "1", None, "numeric"),
                ("Add Height:", "add", "entry", "0.0", None, "numeric"),
                ("Rem Height:", "rem", "entry", "20.0", None, "numeric")
            ])
            self.create_selection_row(spec_frame, "Mapping", self.launch_mapping_dialog)

        elif lw_type == "PipetteHolder":
            self.spec_inputs = create_form(spec_frame, [
                ("Holders X:", "hx", "entry", "1", None, "numeric"),
                ("Holders Y:", "hy", "entry", "1", None, "numeric"),
                ("Add Height:", "add", "entry", "0.0", None, "numeric"),
                ("Rem Height:", "rem", "entry", "0.0", None, "numeric")
            ])
            self.create_selection_row(spec_frame, "IndividualHolder", self.select_holder)

        elif lw_type == "TipDropzone":
            self.spec_inputs = create_form(spec_frame, [("Drop Height:", "dh", "entry", "0", None, "numeric")])

        elif lw_type == "Stack":

            ttk.Label(
                spec_frame,
                text="No additional parameters required for Stack.",
                font=('Arial', 10, 'italic'),
                foreground='gray'
            ).pack(pady=20)
            # Ensure spec_inputs is an empty dict so on_create doesn't crash
            self.spec_inputs = {}

    def create_selection_row(self, parent, key, cmd):
        """Helper to create the selection layout using grid to avoid manager conflicts."""
        # Find the next empty row in the parent grid
        current_rows = parent.grid_size()[1]

        row_frame = ttk.Frame(parent)
        row_frame.grid(row=current_rows, column=0, columnspan=2, sticky='ew', pady=10)

        label = ttk.Label(row_frame, text=f"{key}: Not selected", foreground="red")
        label.pack(side=tk.LEFT)

        setattr(self, f"{key.lower()}_label", label)
        ttk.Button(row_frame, text="Select/Create", command=cmd).pack(side=tk.RIGHT)

    def select_well(self):
        dialog = SelectOrCreateComponentDialog(self, "Well", self.repo["Well"])
        self.wait_window(dialog)
        if dialog.result:
            self.selected_well = dialog.result
            self.well_label.config(text=f"Well: {self.selected_well.labware_id}", foreground="green")

    def select_holder(self):
        dialog = SelectOrCreateComponentDialog(self, "IndividualPipetteHolder", self.repo["Holder"])
        self.wait_window(dialog)
        if dialog.result:
            self.selected_holder = dialog.result
            self.individualholder_label.config(text=f"Holder: {self.selected_holder.labware_id}", foreground="green")

    def launch_mapping_dialog(self):
        dialog = ConfigureReservoirTemplateDialog(self, self.repo["Reservoir"])
        self.wait_window(dialog)
        if dialog.result:
            self.res_template = dialog.result
            self.mapping_label.config(text="Mapping Configured", foreground="green")

    def on_create(self):
        try:

            basic_numeric = ["sx", "sy", "sz", "off_x", "off_y"]
            basic_optional = ["id", "off_x", "off_y"]

            b = self.get_inputs(
                self.basic_inputs,
                numeric_keys=basic_numeric,
                optional_keys=basic_optional
            )

            args = {
                "size_x": b['sx'],
                "size_y": b['sy'],
                "size_z": b['sz'],
                "offset": (b['off_x'], b['off_y']),
                "labware_id": b['id'],
                "can_be_stacked_upon": b['stackable']
            }

            # Handle Specific Inputs (Plate, Holder, etc.)
            spec_numeric = ["ry", "cx", "hx", "hy", "add", "rem", "dh"]

            # id and shape are optional strings
            s = self.get_inputs(self.spec_inputs, numeric_keys=spec_numeric) if hasattr(self, 'spec_inputs') else {}

            lw_type = self.labware_type.get()

            # 5. Object Dispatching
            if lw_type == "Plate":
                if not self.selected_well: raise ValueError("Select a Well type.")
                self.result = Plate(
                    **args,
                    wells_x=int(s['cx']),
                    wells_y=int(s['ry']),
                    well=self.selected_well,
                    add_height=s['add'],
                    remove_height=s['rem']
                )

            elif lw_type == "ReservoirHolder":
                if not self.res_template: raise ValueError("Configure Reservoir mapping.")
                self.result = ReservoirHolder(
                    **args,
                    hooks_across_x=int(s['hx']),
                    hooks_across_y=int(s['hy']),
                    reservoir_template=self.res_template,
                    add_height=s['add'],
                    remove_height=s['rem']
                )

            elif lw_type == "PipetteHolder":
                if not self.selected_holder: raise ValueError("Select a Holder type.")
                self.result = PipetteHolder(
                    **args,
                    holders_across_x=int(s['hx']),
                    holders_across_y=int(s['hy']),
                    individual_holder=self.selected_holder,
                    add_height=s['add'],
                    remove_height=s['rem']
                )

            elif lw_type == "TipDropzone":
                self.result = TipDropzone(**args, drop_height_relative=s['dh'])

            elif lw_type == "Stack":
                self.result = Stack(**args)

            self.destroy()

        except ValueError as e:
            messagebox.showerror("Validation Error", str(e))
        except Exception as e:
            messagebox.showerror("System Error", f"Could not create labware: {e}")

class EditLabwareDialog(ScrollableDialog):
    """
    Refactored Dialog for editing labware using ScrollableDialog
    and unified GUI helpers.
    """

    def __init__(self, parent, labware, available_reservoirs=None):
        # Initialize ScrollableDialog (sets up self.scroll_frame)
        title = f"Edit Labware: {labware.labware_id}"
        super().__init__(parent, title=title, size="550x700")

        # Store references
        self.original_labware = labware
        self.labware = copy.deepcopy(labware)
        self.available_reservoirs = available_reservoirs or []
        self.result = None
        self.selected_reservoir = None

        self.create_widgets()

    def create_widgets(self):
        # 1. Header Info Section
        header = ttk.Labelframe(self.scroll_frame, text="System Information", padding=10)
        header.pack(fill=tk.X, pady=5)

        ttk.Label(header, text=f"Type: {self.labware.__class__.__name__}", font=('Arial', 10, 'bold')).pack(
            side=tk.LEFT)
        ttk.Label(header, text=f" | ID: {self.labware.labware_id}").pack(side=tk.LEFT)

        # 2. Main Tabbed Interface
        self.notebook = ttk.Notebook(self.scroll_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=5)

        self.create_basic_properties_tab()

        if isinstance(self.labware, ReservoirHolder):
            self.create_reservoir_management_tab()
            self.notebook.bind('<<NotebookTabChanged>>', self.on_tab_changed)

        # 3. Footer Action Buttons
        self.add_button_bar( create_cmd=self.on_save, create_text="Save Changes", cancel_text="Cancel")

    def on_tab_changed(self, event):
        current_tab = self.notebook.select()
        tab_text = self.notebook.tab(current_tab, "text")

        # If we're on the Manage Reservoirs tab, draw the grid
        if tab_text == "Manage Reservoirs":
            self.after(100, self.refresh_grid)

    def create_basic_properties_tab(self):
        """Basic properties tab with organized sections"""
        tab = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(tab, text="Physical Properties")

        # --- Dimensions ---
        dim_frame = ttk.Labelframe(tab, text="Dimensions & Offsets", padding=10)
        dim_frame.pack(fill=tk.X, pady=5)

        # Helper to create rows quickly in the grid
        def add_row(parent, label, row, var_val):
            ttk.Label(parent, text=label).grid(row=row, column=0, sticky='w', pady=2)
            var = tk.StringVar(value=str(var_val))
            ttk.Entry(parent, textvariable=var, width=15).grid(row=row, column=1, sticky='w', padx=5)
            return var

        self.size_x_var = add_row(dim_frame, "Size X (mm):", 0, self.labware.size_x)
        self.size_y_var = add_row(dim_frame, "Size Y (mm):", 1, self.labware.size_y)
        self.size_z_var = add_row(dim_frame, "Size Z (mm):", 2, self.labware.size_z)
        self.offset_x_var = add_row(dim_frame, "Offset X (mm):", 3, self.labware.offset[0])
        self.offset_y_var = add_row(dim_frame, "Offset Y (mm):", 4, self.labware.offset[1])

        # --- Stacking ---
        self.can_be_stacked_upon_var = tk.BooleanVar(value=self.labware.can_be_stacked_upon)
        ttk.Checkbutton(dim_frame, text="Can be stacked upon",
                        variable=self.can_be_stacked_upon_var).grid(row=5, column=0, columnspan=2, pady=10, sticky='w')

        # --- Specialized Heights ---
        if any(hasattr(self.labware, attr) for attr in ['add_height', 'remove_height', 'drop_height']):
            h_frame = ttk.Labelframe(tab, text="Process Heights", padding=10)
            h_frame.pack(fill=tk.X, pady=5)

            self.add_height_var = self.remove_height_var = self.drop_height_var = None

            if hasattr(self.labware, 'add_height'):
                self.add_height_var = add_row(h_frame, "Add Liquid Height:", 0, self.labware.add_height)
            if hasattr(self.labware, 'remove_height'):
                self.remove_height_var = add_row(h_frame, "Remove Liquid Height:", 1, self.labware.remove_height)
            if hasattr(self.labware, 'drop_height'):
                self.drop_height_var = add_row(h_frame, "Tip Drop Height:", 2, self.labware.drop_height)

    def create_reservoir_management_tab(self):
        """Management tab using unified draw_labware_grid function"""
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="Manage Reservoirs")

        # Visual Grid Area
        canvas_frame = ttk.Labelframe(tab, text="Visual Hook Layout", padding=10)
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.hook_canvas = tk.Canvas(canvas_frame, bg='white', height=250)
        self.hook_canvas.pack(fill=tk.BOTH, expand=True)
        self.hook_canvas.bind('<Button-1>', self.on_grid_click)

        self.hook_canvas.update_idletasks()
        # Controls Area
        ctrl_frame = ttk.Frame(tab, padding=(0, 10))
        ctrl_frame.pack(fill=tk.X)

        action_configs = [
            {"text": "➕ Place Reservoir", "command": self.add_reservoir_dialog},
            {"text": "🗑️ Remove Selected", "command": self.remove_selected_reservoir}
        ]
        create_button_bar(ctrl_frame, action_configs, fill=True)

        self.info_label = ttk.Label(tab, text="Click a reservoir to select it", foreground="gray")
        self.info_label.pack()

    def refresh_grid(self):
        """Triggers the unified drawing helper"""
        draw_labware_grid(self.hook_canvas, self.labware, self.selected_reservoir)

    def on_grid_click(self, event):
        """Selection logic compatible with draw_labware_grid tags"""
        item = self.hook_canvas.find_closest(event.x, event.y)
        tags = self.hook_canvas.gettags(item)

        for tag in tags:
            if "_" in tag and tag != "child":
                c, r = map(int, tag.split("_"))
                res = self.labware.get_child_at(c, r)
                if res:
                    self.selected_reservoir = res
                    self.info_label.config(text=f"Selected: {res.labware_id} (Hooks: {res.hook_ids})",
                                           foreground="blue")
                else:
                    self.selected_reservoir = None
                    self.info_label.config(text="No reservoir selected", foreground="gray")
                self.refresh_grid()
                break

    def add_reservoir_dialog(self):
        """Reuse existing dialog logic"""
        dialog = PlaceReservoirDialog(self, self.available_reservoirs, self.labware)
        self.wait_window(dialog)
        if dialog.result:
            try:
                tmpl, hooks = dialog.result
                res_copy = copy.deepcopy(tmpl)
                res_copy.hook_ids = hooks
                self.labware.place_reservoir(hooks, res_copy)
                self.refresh_grid()
            except ValueError as e:
                messagebox.showerror("Error", str(e))

    def remove_selected_reservoir(self):
        if not self.selected_reservoir: return
        if messagebox.askyesno("Confirm", "Remove this reservoir?"):
            self.labware.remove_reservoir(self.selected_reservoir.hook_ids[0])
            self.selected_reservoir = None
            self.refresh_grid()

    def on_save(self):
        """
        Save logic that reconstructs the object for validation,
        then copies back to original.
        """
        try:
            # 1. Collect Data
            data = {
                "size_x": float(self.size_x_var.get()),
                "size_y": float(self.size_y_var.get()),
                "size_z": float(self.size_z_var.get()),
                "offset": (float(self.offset_x_var.get()), float(self.offset_y_var.get())),
                "labware_id": self.labware.labware_id,
                "can_be_stacked_upon": self.can_be_stacked_upon_var.get()
            }

            # 2. Add Heights to data if they exist
            if self.add_height_var: data["add_height"] = float(self.add_height_var.get())
            if self.remove_height_var: data["remove_height"] = float(self.remove_height_var.get())
            if self.drop_height_var: data["drop_height"] = float(self.drop_height_var.get())

            # 3. Instantiate temporary object to trigger class-level validation
            cls = self.labware.__class__

            # Specialized construction based on type
            if isinstance(self.labware, Plate):
                temp_obj = cls(**data, wells_x=self.labware._columns, wells_y=self.labware._rows,
                               well=self.labware.well)
            elif isinstance(self.labware, PipetteHolder):
                temp_obj = cls(**data, holders_across_x=self.labware._columns, holders_across_y=self.labware._rows,
                               individual_holder=self.labware.individual_holder)
            elif isinstance(self.labware, ReservoirHolder):
                temp_obj = cls(**data, hooks_across_x=self.labware._columns, hooks_across_y=self.labware._rows)
                # Re-place reservoirs from working copy
                for r in self.labware.get_reservoirs():
                    temp_obj.place_reservoir(r.hook_ids, copy.deepcopy(r))
            else:
                temp_obj = cls(**data)

            # 4. If successful, update the ORIGINAL reference
            for key, value in data.items():
                setattr(self.original_labware, key, value)

            # Handle ReservoirHolder internal dict specifically
            if isinstance(self.labware, ReservoirHolder):
                self.original_labware._ReservoirHolder__hook_to_reservoir = copy.deepcopy(
                    temp_obj._ReservoirHolder__hook_to_reservoir)

            self.result = True
            self.destroy()

        except ValueError as e:
            messagebox.showerror("Validation Error", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"Save failed: {str(e)}")

    def on_cancel(self):
        self.result = False
        self.destroy()

class SlotDialog(ScrollableDialog):
    """Unified Dialog for creating or editing a slot with locked ID on edit."""

    def __init__(self, parent, slot=None):
        self.slot = slot
        title = f"Edit Slot: {slot.slot_id}" if slot else "Create New Slot"
        super().__init__(parent, title=title, size="500x550")

        self.inputs = {}
        self.create_widgets()

    def create_widgets(self):
        params_frame = ttk.Labelframe(self.scroll_frame, text="Slot Parameters", padding="10")
        params_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 1. Prepare Data
        if self.slot:
            defaults = {
                "id": self.slot.slot_id,
                "xmin": str(self.slot.range_x[0]), "xmax": str(self.slot.range_x[1]),
                "ymin": str(self.slot.range_y[0]), "ymax": str(self.slot.range_y[1]),
                "z": str(self.slot.range_z)
            }
        else:
            defaults = {"id": "", "xmin": "0", "xmax": "150", "ymin": "0", "ymax": "100", "z": "100"}

        # 2. Define Fields
        slot_fields = [
            ("Slot ID:", "id", "entry", defaults["id"], None, "text"),
            ("Range X Min (mm):", "xmin", "entry", defaults["xmin"], None, "numeric"),
            ("Range X Max (mm):", "xmax", "entry", defaults["xmax"], None, "numeric"),
            ("Range Y Min (mm):", "ymin", "entry", defaults["ymin"], None, "numeric"),
            ("Range Y Max (mm):", "ymax", "entry", defaults["ymax"], None, "numeric"),
            ("Range Z (mm):", "z", "entry", defaults["z"], None, "numeric")
        ]

        # 3. Build Form
        self.inputs = create_form(params_frame, slot_fields)

        # 4. LOCK THE ID (If editing)
        if self.slot:
            id_var = self.inputs.get("id")
            for child in params_frame.winfo_children():
                # Check if the widget is an Entry and uses our ID variable
                if isinstance(child, (ttk.Entry, tk.Entry)):
                    if child.cget("textvariable") == str(id_var):
                        child.configure(state="readonly")


        btn_text = "Save Changes" if self.slot else "Create Slot"
        self.add_button_bar(create_cmd=self.on_submit, create_text=btn_text)

    def on_submit(self):
        """Logic for both Save and Create."""
        # Validate required fields
        for key, var in self.inputs.items():
            if not var.get().strip():
                messagebox.showerror("Error", f"Field '{key}' is required.")
                return

        try:
            vals = {k: v.get() for k, v in self.inputs.items()}
            d = {k: float(vals[k]) for k in ["xmin", "xmax", "ymin", "ymax", "z"]}

            if d["xmax"] <= d["xmin"] or d["ymax"] <= d["ymin"]:
                messagebox.showerror("Error", "Max values must be greater than min values.")
                return

            if self.slot:
                # Update existing (ID remains same as it's readonly)
                self.slot.range_x = (d["xmin"], d["xmax"])
                self.slot.range_y = (d["ymin"], d["ymax"])
                self.slot.range_z = d["z"]
                self.result = True
            else:
                # Create new
                self.result = Slot(
                    range_x=(d["xmin"], d["xmax"]),
                    range_y=(d["ymin"], d["ymax"]),
                    range_z=d["z"],
                    slot_id=vals["id"]
                )

            self.destroy()

        except ValueError:
            messagebox.showerror("Error", "Check your inputs. Coordinates must be numbers.")

class CreateLowLevelLabwareDialog(ScrollableDialog):
    """
    Dialog for creating Well, Reservoir, or PipetteHolder components.
    """

    def __init__(self, parent, initial_type=None, fixed_type=False):
        super().__init__(parent, "Create Low-Level Labware", "550x750")

        self.initial_type = initial_type
        self.fixed_type = fixed_type

        self.basic_inputs = {}
        self.spec_inputs = {}
        self.content_rows = []

        self.create_widgets()

    def create_widgets(self):
        # --- 1. Type Selection ---
        type_frame = ttk.Labelframe(self.scroll_frame, text="Component Category", padding="10")
        type_frame.pack(fill=tk.X, pady=5)

        all_types = ["Well", "Reservoir", "IndividualPipetteHolder"]
        self.component_type = tk.StringVar(value=self.initial_type or "Well")

        for t in all_types:
            rb = ttk.Radiobutton(type_frame, text=t, variable=self.component_type,
                                 value=t, command=self.refresh_spec_fields)
            rb.pack(anchor='w', pady = 5)

            # Lock selection if fixed_type is True
            if self.fixed_type and t != self.initial_type:
                rb.configure(state="disabled")

        # --- 2. Basic Parameters ---
        basic_frame = ttk.Labelframe(self.scroll_frame, text="Geometry (mm)", padding="10")
        basic_frame.pack(fill=tk.X, pady=5)

        # Using your create_form helper
        self.basic_inputs = create_form(basic_frame, [
            ("Labware ID:", "id", "entry", "", None, "text"),
            ("Size X:", "size_x", "entry", "", None, "numeric"),
            ("Size Y:", "size_y", "entry", "", None, "numeric"),
            ("Size Z:", "size_z", "entry", "", None, "numeric"),
            ("Offset X:", "off_x", "entry", "0.0", None, "numeric"),
            ("Offset Y:", "off_y", "entry", "0.0", None, "numeric")
        ])

        # --- 3. Dynamic Section ---
        self.spec_area = ttk.Frame(self.scroll_frame)
        self.spec_area.pack(fill=tk.X)
        self.refresh_spec_fields()

        self.add_button_bar(create_cmd=self.on_create, create_text="Create Component")

    def refresh_spec_fields(self):
        """Clears and rebuilds the type-specific section of the form."""
        for w in self.spec_area.winfo_children():
            w.destroy()

        comp_type = self.component_type.get()
        spec_frame = ttk.Labelframe(self.spec_area, text=f"{comp_type} Specifications", padding="10")
        spec_frame.pack(fill=tk.X, pady=5)
        spec_frame.columnconfigure(1, weight=1)

        if comp_type in ["Well", "Reservoir"]:
            self.spec_inputs = create_form(spec_frame, [
                ("Capacity (µL):", "cap", "entry", "", None, "numeric"),
                ("Shape:", "shape", "combo", "",
                 ["", "rectangular", "circular", "conical", "u_bottom"], None)
            ])

            # --- Content Section (Grid) ---
            start_r = spec_frame.grid_size()[1]  # Get next available row

            ttk.Separator(spec_frame, orient='horizontal').grid(
                row=start_r, column=0, columnspan=2, sticky='ew', pady=10)

            header_font = ('Arial', 9, 'bold')
            ttk.Label(spec_frame, text="Initial Content (Optional)", font=header_font).grid(row=start_r + 1, column=0,
                                                                                            sticky='w')
            ttk.Label(spec_frame, text="Volume (µL)", font=header_font).grid(row=start_r + 1, column=1, sticky='w')

            self.content_rows = []
            for i in range(3):
                row_idx = start_r + 2 + i
                t_v, v_v = tk.StringVar(), tk.StringVar()

                ttk.Entry(spec_frame, textvariable=t_v, placeholder="Liquid Type").grid(
                    row=row_idx, column=0, pady=2, padx=5, sticky='ew')
                ttk.Entry(spec_frame, textvariable=v_v, placeholder="0.0").grid(
                    row=row_idx, column=1, pady=2, padx=5, sticky='ew')

                self.content_rows.append((t_v, v_v))
        else:
            # For Pipette Holders
            self.spec_inputs = create_form(spec_frame, [
                ("Is Occupied:", "occ", "checkbox", True, None, None)
            ])

    def get_content_data(self):
        """Parses the 3-row content grid into a dictionary."""
        content = {}
        for t_var, v_var in self.content_rows:
            liquid = t_var.get().strip()
            vol_str = v_var.get().strip()

            if liquid and vol_str:
                try:
                    content[liquid] = float(vol_str)
                except ValueError:
                    raise ValueError(f"Volume for '{liquid}' must be a number.")

        return content if content else None

    def on_create(self):
        """Validates all inputs and instantiates the specific class."""
        try:
            #define float values
            basic_nums = ["size_x", "size_y", "size_z", "off_x", "off_y"]
            spec_nums = ["cap"]

            clean_basic = self.get_inputs(self.basic_inputs, numeric_keys=basic_nums, optional_keys=["id"])
            clean_spec = self.get_inputs(self.spec_inputs, numeric_keys=spec_nums, optional_keys=["shape"])

            # Build Base Args
            args = {
                "size_x": clean_basic['size_x'],
                "size_y": clean_basic['size_y'],
                "size_z": clean_basic['size_z'],
                "offset": (clean_basic['off_x'], clean_basic['off_y']),
                "labware_id": clean_basic['id']
            }

            # Handle Type-Specific Logic
            comp_type = self.component_type.get()

            if comp_type in ["Well", "Reservoir"]:
                args.update({
                    "capacity": clean_spec['cap'],
                    "shape": clean_spec['shape'],
                    "content": self.get_content_data()
                })
                self.result = Well(**args) if comp_type == "Well" else Reservoir(**args)

            else:
                self.result = IndividualPipetteHolder(
                    **args,
                    is_occupied=self.spec_inputs['occ'].get()
                )

            self.destroy()

        except ValueError as e:
            messagebox.showerror("Validation Error", f"Please check your entries:\n{e}")
        except Exception as e:
            messagebox.showerror("System Error", f"Could not create labware: {e}")

class SelectOrCreateComponentDialog(ScrollableDialog):
    """Dialog for selecting or creating a low-level component """
    def __init__(self, parent, component_type, available_components):
        super().__init__(parent, title=f"Select or Create {component_type}", size="450x550")
        self.component_type = component_type
        self.available_components = available_components
        self.create_widgets()

    def create_widgets(self):

        # Transform component objects into display strings
        display_list = [
            f"{c.labware_id or 'Unnamed'}: {c.size_x}x{c.size_y}mm"
            for c in self.available_components
        ]

        self.listbox, _ = create_scrolled_listbox(
            self.scroll_frame,
            display_list,
            label_text=f"Available {self.component_type}s",
            double_click_cmd=self.on_select
        )

        button_schema = [
            {"text": "Cancel", "command": self.on_cancel},
            {"text": "Create New", "command": self.on_create_new},
            {"text": "Select", "command": self.on_select, "state": "normal"}
        ]
        _, self.btns = create_button_bar(self.scroll_frame, button_schema, fill=True)

        #disable selection if nothing to select
        if not self.available_components:
            self.btns["Select"].config(state="disabled")

    def on_select(self):
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select an item.")
            return
        self.result = self.available_components[selection[0]]
        self.destroy()

    def on_create_new(self):
        """Jump to the creation dialog."""

        dialog = CreateLowLevelLabwareDialog(self, initial_type=self.component_type, fixed_type=True)
        self.wait_window(dialog)

        if dialog.result:
            self.result = dialog.result
            self.available_components.append(dialog.result)  # Add to library
            self.destroy()

    def on_cancel(self):
        """Cancel dialog"""
        self.result = None
        self.destroy()

class AddLabwareToSlotDialog(ScrollableDialog):
    """Adding labware to slot."""

    def __init__(self, parent, deck, labware):
        super().__init__(parent, title=f"Add {labware.labware_id} to Slot", size="480x500")
        self.deck = deck
        self.labware = labware
        self.form_vars = {}
        self.create_widgets()

        if not deck.slots:
            messagebox.showwarning("Warning", "No slots available on this deck!")
            self.destroy()
            return

    def create_widgets(self):
        # 1. Info Header (Static)
        info_frame = ttk.Labelframe(self.scroll_frame, text="Labware Details", padding="10")
        info_frame.pack(fill=tk.X, pady=5)
        ttk.Label(info_frame, text=f"ID: {self.labware.labware_id}").pack(anchor='w')
        ttk.Label(info_frame, text=f"Type: {self.labware.__class__.__name__}").pack(anchor='w')

        # 2. Dynamic Form Section
        params_frame = ttk.Labelframe(self.scroll_frame, text="Placement Settings", padding="10")
        params_frame.pack(fill=tk.X, pady=5)

        # Definition: (label, key, field_type, default, options, v_type)
        field_definitions = [
            ("Target Slot:", "slot_id", "combo", list(self.deck.slots.keys())[0], list(self.deck.slots.keys()), None),
            ("Min Z Height (mm):", "min_z", "entry", "0", None, "numeric"),
            ("X Spacing (mm):", "x_spacing", "entry", "", None, "numeric"),
            ("Y Spacing (mm):", "y_spacing", "entry", "", None, "numeric"),
        ]

        # Use the helper to generate the widgets and capture variables
        self.form_vars = create_form(params_frame, field_definitions)

        # 3. Add the dynamic logic for min_z
        slot_combo = None
        for widget in params_frame.winfo_children():
            if isinstance(widget, ttk.Combobox):
                slot_combo = widget
                break

        if slot_combo:
            slot_combo.bind("<<ComboboxSelected>>", self.update_default_z)

        ttk.Label(params_frame, text="* Leave spacing blank for auto-calculation",
                  font=('Arial', 8, 'italic'), foreground="gray").grid(row=len(field_definitions), column=0,
                                                                       columnspan=2, pady=5)
        self.add_button_bar(create_cmd=self.on_add, create_text="Add Labware")

    def update_default_z(self, event=None):
        """Update the min_z entry based on the selected slot's current stack."""
        slot_id = self.form_vars['slot_id'].get()
        if slot_id in self.deck.slots:
            target_slot = self.deck.slots[slot_id]
            highest_z = target_slot.get_highest_z()

            # Format to remove trailing zeros if it's a whole number (e.g., 10.0 -> 10)
            formatted_z = int(highest_z) if highest_z.is_integer() else highest_z
            self.form_vars['min_z'].set(str(formatted_z))

    def on_add(self):
        """Processes form data using the base class get_inputs helper."""
        try:

            # 1. Define your schema
            numeric_keys = ['min_z', 'x_spacing', 'y_spacing']
            optional_keys = ['x_spacing', 'y_spacing']

            clean_data = self.get_inputs(
                self.form_vars,
                numeric_keys=numeric_keys,
                optional_keys=optional_keys
            )
            self.result = clean_data
            self.destroy()

        except ValueError as e:
            messagebox.showerror("Input Error", str(e))

class PlaceReservoirDialog(ScrollableDialog):
    """Dialog to select reservoir and specify hook IDs for placement."""

    def __init__(self, parent, available_reservoirs, holder):
        super().__init__(parent, title="Place Reservoir at Hook(s)", size="700x650")

        self.available_reservoirs = available_reservoirs
        self.holder = holder

        # Initialize Variables
        self.hook_ids_var = tk.StringVar()
        self.form_vars = {"hook_ids": self.hook_ids_var}

        self.create_widgets()

    def create_widgets(self):
        # 1. Reservoir Selection Section
        res_frame = ttk.Labelframe(self.scroll_frame, text="Step 1: Select Reservoir", padding="10")
        res_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # Using a helper for the listbox
        self.reservoir_listbox, _ = self.create_scrolled_listbox(res_frame)
        self.reservoir_listbox.config(height=8)
        self.reservoir_listbox.bind('<<ListboxSelect>>', self.on_reservoir_select)

        # Populate initial list
        self.update_listbox_data()
        configs = [{"text": "➕ Create New Reservoir", "command": self.create_new_reservoir}]
        create_button_bar(res_frame, configs, orientation="vertical", fill=True)

        # 2. Preview Section
        preview_frame = ttk.Labelframe(self.scroll_frame, text="Reservoir Preview", padding="10")
        preview_frame.pack(fill=tk.X, pady=5)

        self.preview_text = tk.Text(preview_frame, height=6, wrap=tk.WORD,
                                    font=('Arial', 9), bg="#f0f0f0")
        self.preview_text.pack(fill=tk.BOTH, expand=True)

        # 3. Hook Configuration Section
        hooks_frame = ttk.Labelframe(self.scroll_frame, text="Step 2: Hook Configuration", padding="10")
        hooks_frame.pack(fill=tk.X, pady=5)

        # Dynamic Hook Info
        avail = sorted(self.holder.get_available_hooks())
        ttk.Label(hooks_frame, text=f"Available Hooks: {avail}",
                  font=('Arial', 9, 'bold')).pack(anchor='w', pady=(0, 5))

        ttk.Label(hooks_frame, text="Hook ID(s) (comma-separated):").pack(anchor='w')
        ttk.Entry(hooks_frame, textvariable=self.hook_ids_var).pack(fill=tk.X, pady=5)

        ttk.Label(hooks_frame, text="Example: 7 or 7,6,5",
                  font=('Arial', 8, 'italic'), foreground="gray").pack(anchor='w')

        # 4. Standard Button Bar
        self.add_button_bar(create_cmd=self.on_place, create_text="Place Reservoir")

    def create_scrolled_listbox(self, parent):
        """Helper to create a listbox with a scrollbar."""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL)
        listbox = tk.Listbox(frame, yscrollcommand=scrollbar.set, exportselection=False)

        scrollbar.config(command=listbox.yview)
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        return listbox, frame

    def update_listbox_data(self):
        """Populates or refreshes the reservoir listbox."""
        self.reservoir_listbox.delete(0, tk.END)
        for res in self.available_reservoirs:
            display = f"{res.labware_id} ({res.size_x}×{res.size_y} mm, {res.capacity}µL)"
            self.reservoir_listbox.insert(tk.END, display)

    def on_reservoir_select(self, event=None):
        selection = self.reservoir_listbox.curselection()
        if not selection: return

        res = self.available_reservoirs[selection[0]]
        info = (f"ID: {res.labware_id}\n"
                f"Dimensions: {res.size_x}×{res.size_y}×{res.size_z} mm\n"
                f"Capacity: {res.capacity} µL\n"
                f"Content: {res.get_content_summary()}")

        self.preview_text.config(state=tk.NORMAL)
        self.preview_text.delete(1.0, tk.END)
        self.preview_text.insert(1.0, info)
        self.preview_text.config(state=tk.DISABLED)

    def create_new_reservoir(self):
        """Open dialog to create new reservoir, locked to 'Reservoir' type."""
        dialog = CreateLowLevelLabwareDialog(self, initial_type="Reservoir", fixed_type=True)
        self.wait_window(dialog)

        if dialog.result:
            self.available_reservoirs.append(dialog.result)
            self.update_listbox_data()
            self.reservoir_listbox.selection_set(tk.END)
            self.on_reservoir_select()

    def on_place(self):
        selection = self.reservoir_listbox.curselection()
        if not selection:
            return messagebox.showwarning("Selection Missing", "Please select a reservoir.")

        raw_hooks = self.hook_ids_var.get().strip()
        if not raw_hooks:
            return messagebox.showwarning("Input Missing", "Please enter at least one Hook ID.")

        try:
            # Parse and validate
            hook_ids = [int(h.strip()) for h in raw_hooks.split(',') if h.strip()]

            # Range check
            for hid in hook_ids:
                if not (1 <= hid <= self.holder.total_hooks):
                    raise ValueError(f"Hook {hid} is out of range (1-{self.holder.total_hooks}).")

            # Availability check
            mapping = self.holder.get_hook_to_reservoir_map()
            occupied = [h for h in hook_ids if mapping.get(h) is not None]

            if occupied:
                raise ValueError(f"Hooks {occupied} are already occupied.")

            self.result = (self.available_reservoirs[selection[0]], hook_ids)
            self.destroy()

        except ValueError as e:
            messagebox.showerror("Invalid Input", str(e))

class ConfigureReservoirTemplateDialog(ScrollableDialog):
    """
        Dialog to select a single Reservoir template and specify its placement
        parameters (auto-size, specific hooks, or N x M block size).
        """

    def __init__(self, parent, available_reservoirs):
        super().__init__(parent, title="Configure Reservoir Template", size="500x550")

        self.available_reservoirs = available_reservoirs
        self.selected_reservoir_template = None
        self.create_widgets()

    def create_widgets(self):
        # --- 1. Reservoir Selection ---
        template_frame = ttk.Labelframe(self.scroll_frame, text="Base Reservoir Selection", padding="10")
        template_frame.pack(fill=tk.X, pady=10)

        self.template_label = ttk.Label(template_frame, text="No Reservoir Selected", foreground='red')
        self.template_label.pack(side=tk.LEFT, padx=5)

        ttk.Button(template_frame, text="Select/Create", command=self.select_reservoir).pack(side=tk.RIGHT)

        # --- 2. Placement Geometry ---
        placement_frame = ttk.Labelframe(self.scroll_frame, text="Placement Overrides", padding="10")
        placement_frame.pack(fill=tk.X, pady=10)

        # Use create_form for consistent styling
        self.form_vars = create_form(placement_frame, [
            ("Explicit Hook IDs:", "hooks", "entry", "", None, "text")
        ])

        # Informational Label
        info_text = ("Leave Hook IDs empty to populate entire holder.\n"
                     "Use commas for multiple hooks (e.g. 1, 2, 5).")
        ttk.Label(placement_frame, text=info_text, font=('Arial', 9, 'italic')).grid(row=1, column=0, columnspan=2,
                                                                                     pady=10)

        # 3. Use the base class button bar
        self.add_button_bar(create_cmd=self.on_ok, create_text="Save Configuration")

    def select_reservoir(self):
        dialog = SelectOrCreateComponentDialog(self, "Reservoir", self.available_reservoirs)
        self.wait_window(dialog)

        if dialog.result:
            self.selected_reservoir_template = dialog.result
            self.template_label.config(text=f"Selected: {self.selected_reservoir_template.labware_id}",
                                       foreground='blue')

    def on_ok(self):
        if not self.selected_reservoir_template:
            messagebox.showerror("Selection Required", "Please select a Reservoir template first.")
            return

        try:
            # Use get_inputs to handle the trimming of the string
            # Hook IDs is optional, so we add it to optional_keys
            clean_data = self.get_inputs(self.form_vars, optional_keys=["hooks"])

            # Deep copy to avoid modifying the original library object
            final_template = copy.deepcopy(self.selected_reservoir_template)

            # Parse Hook IDs if provided
            hook_str = clean_data["hooks"]
            if hook_str:
                # Efficient list comprehension with error handling
                try:
                    hook_ids = [int(x.strip()) for x in hook_str.split(',') if x.strip()]
                    final_template.hook_ids = hook_ids
                except ValueError:
                    raise ValueError("Hook IDs must be a list of integers separated by commas.")

                # Clean up mutually exclusive attributes
                for attr in ['num_hooks_x', 'num_hooks_y']:
                    if hasattr(final_template, attr):
                        delattr(final_template, attr)
            else:
                final_template.hook_ids = []

            self.result = final_template
            self.destroy()

        except ValueError as e:
            messagebox.showerror("Input Error", str(e))

class ViewChildrenLabwareDialog(tk.Toplevel):
    """
    Fixed-layout manager for Labware children.
    Keeps the Grid View visible at all times while editing.
    """

    def __init__(self, parent, labware, pipettor=None):
        super().__init__(parent)
        self.title(f"Manage Labware: {labware.labware_id}")
        self.geometry("1100x800")

        self.labware = labware
        self.selected_child = None
        self.pipettor = pipettor
        self.vars = {}

        # Modal setup
        self.transient(parent)
        self.grab_set()

        self.setup_ui()
        # Delay drawing slightly to ensure canvas dimensions are registered
        self.after(500, self.refresh_view)

    def setup_ui(self):
        """Creates a side-by-side layout: Grid (Left) and Editor (Right)."""
        # Main container
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # LEFT SIDE: The Grid (Fixed)
        self.left_panel = ttk.Labelframe(main_frame, text="Grid View", padding="5")
        self.left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        self.canvas = tk.Canvas(self.left_panel, bg='white', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind('<Button-1>', self.on_canvas_click)

        # RIGHT SIDE: The Editor (Static width)
        self.right_panel = ttk.Labelframe(main_frame, text="Item Editor", padding="15", width=350)
        self.right_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
        self.right_panel.pack_propagate(False)  # Maintain width

        # Container for dynamic controls
        self.controls_container = ttk.Frame(self.right_panel)
        self.controls_container.pack(fill=tk.BOTH, expand=True)

        self.update_edit_panel()

    def refresh_view(self):
        """Redraws the grid based on labware children protocol."""
        draw_labware_grid(self.canvas, self.labware, self.selected_child)

    def on_canvas_click(self, event):
        """Identifies click and updates the right-hand panel."""
        item = self.canvas.find_closest(event.x, event.y)
        tags = self.canvas.gettags(item)
        for tag in tags:
            if "_" in tag and tag != "child":
                col, row = map(int, tag.split("_"))
                self.selected_child = self.labware.get_child_at(col, row)
                self.refresh_view()
                self.update_edit_panel()
                break

    #todo use create_panel
    def update_edit_panel(self):
        """Rebuilds editor panel with separate Add and Remove sections."""
        for widget in self.controls_container.winfo_children():
            widget.destroy()

        # INFO BOX
        info_text = tk.Text(self.controls_container, height=12, width=30,
                            bg="#F8F9FA", relief="flat", padx=10, pady=10)
        info_text.pack(fill=tk.X, pady=(0, 15))
        update_detailed_info_text(info_text, self.selected_child, modules=['basic', 'content'])

        if not self.selected_child:
            return

        child = self.selected_child

        #visit button
        visit_frame = ttk.Labelframe(self.controls_container, text="Navigation", padding="10")
        visit_frame.pack(fill=tk.X, pady=5)

        def do_visit():
            try:
                x, y = child.position
                self.pipettor.move_xy(x, y)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to visit position: {str(e)}")

        visit_btn = ttk.Button(visit_frame, text="Visit Position", command=do_visit)
        visit_btn.pack(fill=tk.X, pady=5)

        # Enable only if pipettor is connected
        if not self.pipettor:
            visit_btn.config(state='disabled')

        # DYNAMIC ACTION PANEL
        if hasattr(child, 'add_content'):
            # --- ADD SECTION ---
            add_frame = ttk.Labelframe(self.controls_container, text="Add Liquid", padding="10")
            add_frame.pack(fill=tk.X, pady=5)

            add_fields = [
                ("Type:", "type", "entry", "Water", None, "text"),
                ("Vol (µL):", "add_vol", "entry", "50", None, "numeric")
            ]

            self.add_vars = create_form(add_frame, add_fields, field_width = 10)

            def do_add():
                try:
                    t = self.add_vars['type'].get()
                    v = float(self.add_vars['add_vol'].get())
                    child.add_content(t, v)
                    self.refresh_view();
                except ValueError as e:
                    messagebox.showerror("Error", str(e))

            ttk.Button(add_frame, text="Add", command=do_add).grid(row=2, column=0, columnspan=2, sticky='we',
                                                                           pady=5)

            # --- REMOVE SECTION ---
            rem_frame = ttk.Labelframe(self.controls_container, text="Remove Liquid", padding="10")
            rem_frame.pack(fill=tk.X, pady=5)

            rem_fields = [("Vol (µL):", "rem_vol", "entry", "20", None, "numeric")]
            self.rem_vars = create_form(rem_frame, rem_fields, field_width = 10)

            def do_remove():
                try:
                    v = float(self.rem_vars['rem_vol'].get())
                    child.remove_content(v)
                    self.refresh_view();
                except ValueError as e:
                    messagebox.showerror("Error", str(e))

            ttk.Button(rem_frame, text="Remove", command=do_remove).grid(row=1, column=0, columnspan=2,
                                                                                  sticky='we', pady=5)

            # --- QUICK CLEAR ---
            ttk.Button(self.controls_container, text="Empty",
                       command=lambda: [child.clear_content(), self.refresh_view()]
                       ).pack(fill=tk.X, pady=5)

        elif hasattr(child, 'is_occupied'):
            action_frame = ttk.Labelframe(self.controls_container, text="Quick Actions", padding="10")
            action_frame.pack(fill=tk.X, pady=5)

            btn_text = "Remove Tip" if child.is_occupied else "Place Tip"

            def toggle():
                if child.is_occupied: child.remove_pipette()
                else: child.place_pipette()
                self.refresh_view()
                self.update_edit_panel()

            ttk.Button(action_frame, text=btn_text, command=toggle).pack(fill=tk.X, pady=10)

        # Footer
        ttk.Button(self.controls_container, text="Close", command=self.destroy).pack(side=tk.BOTTOM, pady=10)
