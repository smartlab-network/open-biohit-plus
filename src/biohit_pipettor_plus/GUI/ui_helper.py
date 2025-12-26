import tkinter as tk
from tkinter import ttk

class ScrollableDialog(tk.Toplevel):
    """Base class providing scrollable content and standard exit protocols."""
    def __init__(self, parent, title="Dialog", size="500x600"):
        super().__init__(parent)
        self.title(title)
        self.geometry(size)
        self.result = None

        # Modal setup
        self.transient(parent)
        self.grab_set()

        # Handle the "X" button in the title bar
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)

        # Scrollable Setup
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scroll_frame = ttk.Frame(self.canvas, padding="10")

        self.scroll_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

    def add_button_bar(self, create_cmd, create_text="Create", cancel_text="Cancel"):
        """Standardizes the button bar for all child dialogs."""
        btn_frame = ttk.Frame(self.scroll_frame)
        btn_frame.pack(fill=tk.X, pady=10)

        # 'create_cmd' is passed from the child (e.g., self.on_create)
        ttk.Button(btn_frame, text=create_text, command=create_cmd).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text=cancel_text, command=self.on_cancel).pack(side=tk.RIGHT)

    def get_inputs(self, input_dict, numeric_keys=None, optional_keys=None):
        """
            Processes a dictionary of tkinter variables.

            numeric_keys: List of keys that MUST be converted to float/int.
            optional_keys: List of keys that can be empty (defaults to 0.0 or None).
        """

        numeric_keys = numeric_keys or []
        optional_keys = optional_keys or []
        clean_data = {}

        for key, var in input_dict.items():
            val = var.get()
            raw_val = str(val).strip() if isinstance(val, str) else val

            # Check for empty fields
            if raw_val == "" or raw_val is None:
                if key in optional_keys:
                    clean_data[key] = None
                    continue
                raise ValueError(f"'{key.replace('_', ' ').title()}' is required.")

            if key in numeric_keys:
                try:
                    clean_data[key] = float(raw_val)
                except ValueError:
                    raise ValueError(f"'{key.replace('_', ' ').title()}' must be a number.")
            else:
                clean_data[key] = raw_val

        return clean_data

    def on_cancel(self):
        """Standard exit: ensures result is None and window is closed."""
        self.result = None
        self.destroy()

def create_form(container, fields, field_width = 25, return_widgets=False):
    variables = {}
    widgets = {}
    vcmd = (container.register(validate_numeric), '%P')

    for i, (label_text, key, field_type, default, options, v_type) in enumerate(fields):
        # 1. Create Label
        ttk.Label(container, text=label_text).grid(row=i, column=0, sticky='w', padx=5, pady=5)

        # 2. Initialize the correct variable type
        if field_type == "checkbox":
            var = tk.BooleanVar(value=default)
            widget = ttk.Checkbutton(container, variable=var)
        else:
            var = tk.StringVar(value=str(default))

            if field_type == "entry":
                # Only apply numeric validation if requested
                if v_type == "numeric":
                    widget = ttk.Entry(container, textvariable=var, width=field_width,
                                       validate="key", validatecommand=vcmd)
                else:
                    widget = ttk.Entry(container, textvariable=var, width=field_width)

            elif field_type == "combo":
                widget = ttk.Combobox(container, textvariable=var, values=options,
                                      state="readonly", width=field_width -5 )

        # 3. Placement and Storage
        widget.grid(row=i, column=1, padx=5, pady=5, sticky='we')
        variables[key] = var
        if return_widgets:  # NEW
            widgets[key] = widget


    return (variables, widgets) if return_widgets else variables

def create_scrolled_listbox(parent, items, label_text="Available Items", height=10, double_click_cmd=None):
    """
    Creates a scrollable listbox inside a Labelframe.
    Optional: double_click_cmd
    Returns: (listbox_object, frame_object)
    """
    frame = ttk.Labelframe(parent, text=label_text, padding="10")
    frame.pack(fill="both", expand=True, pady=5)

    scrollbar = ttk.Scrollbar(frame, orient="vertical")

    listbox = tk.Listbox(
        frame,
        yscrollcommand=scrollbar.set,
        font=("Consolas", 10),
        height=height,
        exportselection=False # Prevents losing selection when clicking other widgets
    )
    scrollbar.config(command=listbox.yview)

    listbox.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    if double_click_cmd:
        listbox.bind("<Double-1>", lambda event: double_click_cmd())

    for item in items:
        listbox.insert("end", item)

    return listbox, frame

def create_button_bar(parent, button_configs, orientation="horizontal", align="center", fill=False):
    """
    Enhanced helper for button layouts.

    orientation: "horizontal" or "vertical"
    align: "left", "right", "center" (for horizontal) or "top", "bottom" (for vertical)
    fill: If True, buttons expand to fill the available space.
    """
    btn_frame = ttk.Frame(parent)
    # If fill is True, we want the frame to take all width
    btn_frame.pack(fill="x" if orientation == "horizontal" or fill else "none", pady=5)

    buttons = {}

    # Determine packing side based on orientation and alignment
    if orientation == "horizontal":
        side = align if align in ["left", "right"] else "left"
    else:
        side = "top"

    for config in button_configs:
        name = config.get("text", "Button")
        btn = ttk.Button(
            btn_frame,
            text=name,
            command=config.get("command"),
            state=config.get("state", "normal"),
            style=config.get("style", "TButton")
        )

        pack_kwargs = {"side": side, "padx": 5, "pady": 2}
        if fill:
            pack_kwargs.update({"expand": True, "fill": "x"})

        btn.pack(**pack_kwargs)
        buttons[name] = btn

    return btn_frame, buttons

def validate_numeric(text):
    """Allows only numbers, decimal points, and minus signs."""
    if text == "" or text == "-": return True # Allow empty or start of negative
    try:
        float(text)
        return True
    except ValueError:
        return False

def update_detailed_info_text(text_widget, obj=None, modules=None):
    """
    Modular helper that displays all data returned by the object's methods.
    Does not filter or guess object types.
    """
    # Default to showing everything
    if modules is None:
        modules = ['basic', 'physical', 'content']

    # Reset Text Widget
    text_widget.config(state='normal')
    text_widget.delete(1.0, tk.END)

    if not obj:
        text_widget.insert(tk.END, "\n\n   [No Selection]")
        text_widget.config(state='disabled')
        return

    full_text = []

    # --- 1. BASIC INFO (ID & Location) ---
    if 'children' in modules:
        full_text.append(f"Grid:  Col {obj.column}, Row {obj.row}\n")

    if 'basic' in modules:
        full_text.append("--- BASIC INFO ---")
        full_text.append(f"ID:    {obj.labware_id}")
        full_text.append(f"Type:  {obj.__class__.__name__}")
        full_text.append(f"Position: {getattr(obj, 'position', 'N/A')}")
        full_text.append("")



    # --- 2. PHYSICAL INFO (Dimensions) ---
    if 'physical' in modules:
        full_text.append("--- PHYSICAL ---")
        full_text.append(f"Size X: {obj.size_x} mm")
        full_text.append(f"Size Y: {obj.size_y} mm")
        full_text.append(f"Size Z: {obj.size_z} mm")
        full_text.append("")

    # --- 3. CONTENT INFO (Dynamic Dictionary Dump) ---
    if 'content' in modules and hasattr(obj, 'get_content_info'):
        full_text.append("--- CONTENT STATUS ---")

        # Get the raw dictionary from the object
        data = obj.get_content_info()

        # Loop through WHATEVER keys are returned
        for key, value in data.items():
            # Format Key: "total_volume" -> "Total Volume"
            clean_key = key.replace("_", " ").title()

            # Special formatting for nested dictionaries (like content_dict)
            if isinstance(value, dict):
                full_text.append(f"{clean_key}:")
                if not value:
                    full_text.append("  (Empty)")
                for sub_k, sub_v in value.items():
                    full_text.append(f"  • {sub_k}: {sub_v}")

            # Special formatting for floats to avoid 10.00000001
            elif isinstance(value, float):
                full_text.append(f"{clean_key}: {value:.2f}")

            # Default print for everything else (bools, strings, ints)
            else:
                full_text.append(f"{clean_key}: {value}")

    # Write to widget
    text_widget.insert(tk.END, "\n".join(full_text))
    text_widget.config(state='disabled')

def draw_labware_grid(canvas, labware, selected_child=None, pad=40, min_cell=40, max_cell=150):
    """
    Unified grid drawer for any labware with children.
    Handles cell scaling, coloring, and selection highlighting.
    """
    canvas.delete("all")

    c_w, c_h = canvas.winfo_width(), canvas.winfo_height()
    if c_w < 10: return  # Guard for unrendered canvas

    # Calculate scale
    grid_x = getattr(labware, 'grid_x', 1)
    grid_y = getattr(labware, 'grid_y', 1)

    cell_size = min((c_w - 2 * pad) / grid_x, (c_h - 2 * pad) / grid_y)
    cell_size = max(min_cell, min(cell_size, max_cell))

    for row in range(grid_y):
        for col in range(grid_x):
            x1 = pad + col * cell_size
            y1 = pad + row * cell_size
            x2 = x1 + cell_size
            y2 = y1 + cell_size

            # Draw soft cell outline
            canvas.create_rectangle(
                x1, y1, x2, y2,
                outline='#dddddd',  # Soft gray lines
                width=1,
                state='disabled',
                tags='grid_outline'
            )
        total_width = grid_x * cell_size
        total_height = grid_y * cell_size
        canvas.create_rectangle(
            pad, pad,
            pad + total_width, pad + total_height,
            outline='#333333',  # Dark boundary
            width=4,
            state='disabled',
            tags='grid_boundary'
        )

    for child in labware.get_all_children():
        # 1. Geometry
        w_span = getattr(child, 'grid_width', 1)
        h_span = getattr(child, 'grid_height', 1)

        x1 = pad + child.column * cell_size
        y1 = pad + child.row * cell_size
        x2 = x1 + (w_span * cell_size)
        y2 = y1 + (h_span * cell_size)

        is_sel = (selected_child == child)

        # 2. Visuals (Color logic moved here)
        if hasattr(child, 'is_occupied'):
            color = '#00D4AA' if child.is_occupied else '#FFCCCC'
            label = "✓" if child.is_occupied else "✗"
        else:
            vol = getattr(child, 'get_total_volume', lambda: 0)()
            color = '#00D4AA' if vol > 0 else '#808080'
            label = f"{vol:.0f}µL"

        # 3. Render
        canvas.create_rectangle(
            x1, y1, x2, y2, fill=color,
            outline='red' if is_sel else 'black',  # Bright Magenta for selection
            width=3 if is_sel else 1,
            tags=('clickable_child', f"{child.column}_{child.row}")
        )

        if label:
            canvas.create_text(
                (x1 + x2) / 2, (y1 + y2) / 2,
                text=label,
                font=('Arial', int(cell_size /8), 'bold'),
                state='disabled',
                tags=('child', f"{child.column}_{child.row}")
            )
        canvas.create_text(
            x1 + 5, y1 + 5,
            text=f"[{child.row},{child.column}]",
            font=('Arial', max(8, int(cell_size / 10)), 'normal'),
            anchor='nw',
            fill='#666666',
            state='disabled',
            tags=('child', f"{child.column}_{child.row}")
        )

    return cell_size

