import tkinter as tk
import ttkbootstrap as ttk
from tkinter import messagebox
from typing import Optional


class CollapsibleFrame(ttk.Frame):
    """A frame that can be collapsed/expanded by clicking on its title."""

    def __init__(self, parent, text, collapsed=True, **kw):

        super().__init__(parent, **kw)

        # Title bar
        self.title_frame = ttk.Frame(self)
        self.title_frame.pack(fill="x", expand=False)

        self.toggle_btn = ttk.Label(self.title_frame, text="▶", width=2)
        self.toggle_btn.pack(side="left", padx=5)

        self.title_lbl = ttk.Label(self.title_frame, text=text, font=("Arial", 12, "bold"))
        self.title_lbl.pack(side="left", pady=2)

        # Content frame (initially hidden)
        self.content_frame = ttk.Frame(self)
        self.content_frame.pack(fill="both", expand=True)
        if collapsed:
            self.content_frame.pack_forget()  # start collapsed
            self.is_expanded = False
        else:
            self.is_expanded = True
        # Bind click
        self.title_frame.bind("<Button-1>", self.toggle)
        self.toggle_btn.bind("<Button-1>", self.toggle)
        self.title_lbl.bind("<Button-1>", self.toggle)

    def toggle(self, event=None):
        if self.is_expanded:
            self.content_frame.pack_forget()
            self.toggle_btn.config(text="▶")
        else:
            self.content_frame.pack(fill="both", expand=True)
            self.toggle_btn.config(text="▼")
        self.is_expanded = not self.is_expanded

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

class ScrollableTab:
    """
    Self-contained scrollable content area for notebook tabs.

    Provides automatic scrollbar management, mousewheel support,
    and helper methods for content management.

    Usage:
        tab_container = ttk.Frame(notebook)
        notebook.add(tab_container, text="My Tab")

        scrollable = ScrollableTab(tab_container)
        ttk.Label(scrollable.content_frame, text="Content").pack()
    """

    def __init__(self, parent, enable_mousewheel=True, bg='#f0f0f0'):
        """
        Initialize a scrollable tab.

        Args:
            parent: The parent widget (typically a Frame inside a Notebook)
            enable_mousewheel: If True, bind mousewheel scrolling
            bg: Background color for the canvas
        """
        self.parent = parent
        self._mousewheel_enabled = enable_mousewheel
        self._mousewheel_bound = False

        # Create canvas and scrollbar
        self.canvas = tk.Canvas(parent, bg=bg, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.canvas.yview)

        # Create the content frame that will hold all widgets
        self.content_frame = ttk.Frame(self.canvas)

        # Configure canvas scrolling
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # Pack scrollbar and canvas
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Create window in canvas to hold the content frame
        self.canvas_window = self.canvas.create_window(
            (0, 0),
            window=self.content_frame,
            anchor='nw'
        )

        # Bind configuration events for auto-resizing
        self.content_frame.bind('<Configure>', self._on_frame_configure)
        self.canvas.bind('<Configure>', self._on_canvas_configure)

        # Setup mousewheel if enabled
        if enable_mousewheel:
            self._setup_mousewheel()

    def _on_frame_configure(self, event=None):
        """Update scroll region when content frame size changes."""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event=None):
        """Update content frame width when canvas is resized."""
        canvas_width = self.canvas.winfo_width()
        if canvas_width > 1:  # Only update if canvas has been drawn
            self.canvas.itemconfig(self.canvas_window, width=canvas_width)

    def _setup_mousewheel(self):
        """Setup mousewheel scrolling (binds on mouse enter, unbinds on leave)."""

        def on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def bind_mousewheel(event):
            if not self._mousewheel_bound:
                self.canvas.bind_all("<MouseWheel>", on_mousewheel)
                self._mousewheel_bound = True

        def unbind_mousewheel(event):
            if self._mousewheel_bound:
                self.canvas.unbind_all("<MouseWheel>")
                self._mousewheel_bound = False

        self.canvas.bind('<Enter>', bind_mousewheel)
        self.canvas.bind('<Leave>', unbind_mousewheel)

    def clear_content(self):
        """Destroy all widgets in the content frame."""
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def get_frame(self):
        """
        Get the content frame for adding widgets.

        Returns:
            The content frame (ttk.Frame)
        """
        return self.content_frame

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
        widgets[key] = widget

    if return_widgets:
        return variables, widgets
    return variables

def create_scrolled_listbox(parent, items, label_text="Available Items", height=15, width=50, double_click_cmd=None):
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
        width=width,
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

def create_button_bar(parent, button_configs, btns_per_row=1,  fill=False, padx=5, pady=2):
    frame = ttk.Frame(parent)
    frame.pack(fill="x", pady=5)

    buttons = {}

    # GRID MODE (btns_per_row > 1)
    if btns_per_row > 1:
        for c in range(btns_per_row):
            frame.columnconfigure(c, weight=1)

        for i, cfg in enumerate(button_configs):
            if isinstance(cfg, tuple):
                cfg = {"text": cfg[0], "command": cfg[1]}

            r, c = divmod(i, btns_per_row)

            btn = ttk.Button(
                frame,
                text=cfg.get("text", "Button"),
                command=cfg.get("command"),
                state=cfg.get("state", "normal"),
                style=cfg.get("style", "TButton"),
            )

            btn.grid(
                row=r,
                column=c,
                sticky="ew" if fill else "",
                padx=padx,
                pady=pady
            )

            buttons[cfg["text"]] = btn

    # PACK MODE (vertical stack)
    else:
        for cfg in button_configs:
            if isinstance(cfg, tuple):
                cfg = {"text": cfg[0], "command": cfg[1]}

            btn = ttk.Button(
                frame,
                text=cfg.get("text", "Button"),
                command=cfg.get("command"),
                state=cfg.get("state", "normal"),
                style=cfg.get("style", "TButton"),
            )

            btn.pack(
                side=tk.TOP,
                fill="x" if fill else None,
                expand=fill,
                padx=padx,
                pady=pady
            )

            buttons[cfg["text"]] = btn

    return frame, buttons

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
        modules = ['basic', 'physical', 'content', 'parent']

    # Reset Text Widget
    text_widget.config(state='normal')
    text_widget.delete(1.0, tk.END)

    if not obj:
        text_widget.insert(tk.END, "")
        text_widget.config(state='disabled')
        return

    full_text = []

    # --- 1. BASIC INFO (ID & Location) ---
    if 'children' in modules:
        full_text.append(f"Grid:  Col {obj.column}, Row {obj.row}\n")

    if 'basic' in modules:
        full_text.append(f"ID:    {obj.labware_id}")
        full_text.append(f"Type:  {obj.__class__.__name__}")
        full_text.append(f"Position: {getattr(obj, 'position', 'N/A')}")

    # --- 2. PHYSICAL INFO (Dimensions) ---
    if 'physical' in modules:
        full_text.append(f"Size X, Y, Z: {obj.size_x}, {obj.size_y},{obj.size_z} mm")

        attributes = {
            'offset': 'Offset_x, Offset_y',
            'can_be_stacked_upon': 'can_be_stacked_upon',
            'shape': 'shape',
        }

        for attr, label in attributes.items():
            if hasattr(obj, attr):
                value = getattr(obj, attr)
                full_text.append(f"{label}: {value}")

    # --- 3. CONTENT INFO (Dynamic Dictionary Dump) ---
    if 'content' in modules and hasattr(obj, 'get_content_info'):
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

    if 'parent' in modules:
        attributes = {
            '_rows': 'Row',
            '_columns': 'Column',
            'add_height': 'Add_height',
            'remove_height': 'remove_height',
            'drop_height_relative': 'drop_height_relative',
        }

        for attr, label in attributes.items():
            if hasattr(obj, attr):
                value = getattr(obj, attr)
                full_text.append(f"{label}: {value}")

    if 'slot' in modules:
        full_text.append(f"Slot: {obj.slot_id}")
        full_text.append(f"Range X: {obj.range_x}")
        full_text.append(f"Range Y: {obj.range_y}")
        full_text.append(f"Range Z: (0, {obj.range_z})")

    # Write to widget
    text_widget.insert(tk.END, "\n".join(full_text))
    text_widget.config(state='disabled')

def draw_labware_grid(canvas, labware, selected_child=None, copy_source=None, paste_targets=None,
                      check_box=False, pad=40, min_cell=40, max_cell=150):
    """
    Unified grid drawer for any labware with children.
    Handles cell scaling, coloring, and selection highlighting.

    Args:
        copy_source: The child being copied from (green border)
        paste_targets: Set of children selected as paste targets (blue border)
    """
    canvas.delete("all")

    if paste_targets is None:
        paste_targets = set()

    c_w, c_h = canvas.winfo_width(), canvas.winfo_height()
    if c_w < 10: return

    # Calculate scale
    grid_x = getattr(labware, 'grid_x', 1)
    grid_y = getattr(labware, 'grid_y', 1)
    cell_size = min((c_w - 2 * pad) / grid_x, (c_h - 2 * pad) / grid_y)
    cell_size = max(min_cell, min(cell_size, max_cell))
    if hasattr(labware, "get_all_children"):
        all_children = labware.get_all_children() or []
    else:
        all_children = []


    #create all required checkbox
    if check_box:
        box_s = 15  # Size of the checkbox square
        # 1. Master Checkbox (Top-Left)
        is_all = len(paste_targets) == len(all_children) and len(all_children) > 0
        canvas.create_rectangle(
            pad - box_s - 5, pad - box_s - 5, pad - 5, pad - 5,
            fill="blue" if is_all else "white", outline="black",
            tags=("header", "master_header")
        )

        # 2. Column Checkboxes (at the top)
        for col in range(grid_x):
            x_mid = pad + col * cell_size + (cell_size / 2)
            col_children = [c for c in all_children if c.column == col]
            is_col_full = all(c in paste_targets for c in col_children) if col_children else False

            canvas.create_rectangle(
                x_mid - box_s / 2, pad - box_s - 5, x_mid + box_s / 2, pad - 5,
                fill="blue" if is_col_full else "white", outline="black",
                tags=("header", f"col_header_{col}")
            )
            # Optional: Label column
            canvas.create_text(x_mid, pad - box_s - 15, text=str(col + 1), font=('Arial', 8, 'bold'))

        # 3. Row Checkboxes (on the left)
        for row in range(grid_y):
            y_mid = pad + row * cell_size + (cell_size / 2)
            row_children = [c for c in all_children if c.row == row]
            is_row_full = all(c in paste_targets for c in row_children) if row_children else False

            canvas.create_rectangle(
                pad - box_s - 5, y_mid - box_s / 2, pad - 5, y_mid + box_s / 2,
                fill="blue" if is_row_full else "white", outline="black",
                tags=("header", f"row_header_{row}")
            )

    # Draw grid lines
    for row in range(grid_y):
        for col in range(grid_x):
            x1 = pad + col * cell_size
            y1 = pad + row * cell_size
            x2 = x1 + cell_size
            y2 = y1 + cell_size

            canvas.create_rectangle(
                x1, y1, x2, y2,
                outline='#dddddd',
                width=1,
                state='disabled',
                tags='grid_outline'
            )

    total_width = grid_x * cell_size
    total_height = grid_y * cell_size
    canvas.create_rectangle(
        pad, pad,
        pad + total_width, pad + total_height,
        outline='#333333',
        width=4,
        state='disabled',
        tags='grid_boundary'
    )

    # --- Fallback: draw a single box for labware (no children) ---
    if not all_children:
        x1, y1 = pad, pad
        x2 = pad + total_width
        y2 = pad + total_height

        canvas.create_rectangle(
            x1, y1, x2, y2,
            fill="#808080",
            outline="black",
            width=3,
            tags=("clickable_labware",)
        )

        canvas.create_text(
            (x1 + x2) / 2,
            (y1 + y2) / 2,
            text=getattr(labware, "labware_id", labware.__class__.__name__),
            font=("Arial", 14, "bold"),
            fill="white",
            state="disabled"
        )

        return cell_size

    # Draw children
    for child in all_children:
        # 1. Geometry
        w_span = getattr(child, 'grid_width', 1)
        h_span = getattr(child, 'grid_height', 1)

        x1 = pad + child.column * cell_size
        y1 = pad + child.row * cell_size
        x2 = x1 + (w_span * cell_size)
        y2 = y1 + (h_span * cell_size)

        # 2. Fill color based on content
        if hasattr(child, 'is_occupied'):
            color = '#00D4AA' if child.is_occupied else '#FFCCCC'
            label = "✓" if child.is_occupied else "✗"
        else:
            vol = getattr(child, 'get_total_volume', lambda: 0)()
            color = '#00D4AA' if vol > 0 else '#808080'
            label = f"{vol:.0f}µL"

        # 3. Border color/width based on state
        outline_color = 'black'  # Default
        outline_width = 1

        if child == copy_source:
            color ='blue'
        elif child in paste_targets:
            color = 'orange'  # Blue for paste targets
        elif child == selected_child:
            outline_color = 'red'  # Red for normal selection
            outline_width = 3

        # 4. Render
        canvas.create_rectangle(
            x1, y1, x2, y2,
            fill=color,
            outline=outline_color if outline_color else 'black',
            width=outline_width,
            tags=('clickable_child', f"{child.column}_{child.row}")
        )

        if label:
            canvas.create_text(
                (x1 + x2) / 2, (y1 + y2) / 2,
                text=label,
                font=('Arial', int(cell_size / 8), 'bold'),
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

def create_info_panel(parent, title="Selection Info", height=8, clear_cmd=None, collapsed=False):
    """
    Creates a static Labelframe with a text box and clear button.

    Returns:
        tuple: (labelframe_instance, text_widget)
    """
    # 1. Create a standard LabelFrame
    info_frame = CollapsibleFrame(parent, text=title, collapsed=collapsed)
    info_frame.pack(fill=tk.X, pady=5, padx=5)
    target_container = info_frame.content_frame

    # 2. Create the text display
    info_text = tk.Text(target_container, height=height, wrap=tk.WORD)
    info_text.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

    # 3. Create the clear button
    if clear_cmd:
        clear_btn = ttk.Button(
            target_container,
            text="Clear Selection",
            command=clear_cmd if clear_cmd else lambda: None
        )
        clear_btn.pack(fill=tk.X)

    return info_frame, info_text

def create_managed_list_section(instance, parent, title, var, list_attr, btn_frame_attr, select_cmd, update_cmd):
    """
    Global helper to create a Labelframe with Radiobuttons, a Scrolled Listbox,
    and a placeholder for dynamic buttons.
    """

    frame = ttk.Labelframe(parent, text=title, padding=10)
    frame.pack(fill=tk.X, pady=5, padx=5)

    # 1. View Mode Toggle (Placed/Unplaced)
    selector = ttk.Frame(frame)
    selector.pack(fill=tk.X, pady=(0, 5))
    for mode in ["placed", "unplaced"]:
        ttk.Radiobutton(
            selector,
            text=mode.title(),
            variable=var,
            value=mode,
            command=update_cmd
        ).pack(side=tk.LEFT, padx=5)

    # 2. Scrolled Listbox
    lb, container = create_scrolled_listbox(frame, [], height=6)

    # Store the listbox on the instance so the class can access it (e.g., self.slots_listbox)
    setattr(instance, list_attr, lb)
    lb.bind('<<ListboxSelect>>', select_cmd)

    # 3. Dynamic Button Frame
    btn_frame = ttk.Frame(frame)
    btn_frame.pack(fill=tk.X, pady=(5, 0))

    # Store the frame on the instance so it can be cleared/rebuilt later
    setattr(instance, btn_frame_attr, btn_frame)

    return frame

def ask_volume_dialog(parent, title="Enter Volume", initial_value=0, label_text="Volume per well (ul):")-> Optional[float]:


    """
    Create a simple, focused dialog for numeric input.

    Returns
    -------
        Value entered by user(float), or None if cancelled
    """
    dialog = tk.Toplevel(parent)
    dialog.title(title)
    dialog.geometry("300x150")
    dialog.resizable(False, False)
    dialog.transient(parent)
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
        font=('Arial', 13)
    ).pack(pady=(0, 10))

    # Entry
    value_var = tk.StringVar(value=str(initial_value))
    entry = ttk.Entry(main_frame, textvariable=value_var, font=('Arial', 13), justify='center')
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
