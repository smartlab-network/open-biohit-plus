
import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog
import ttkbootstrap as ttk
import json
import os
import datetime
import string

from .collapsible_frame import CollapsibleFrame
from ..deck_structure import *
from .function_window import FunctionWindow
from ..pipettor_plus.pipettor_plus import PipettorPlus
from .gui_dialogs import EditSlotDialog, EditLabwareDialog, AddLabwareToSlotDialog, CreateLabwareDialog, CreateSlotDialog,CreateLowLevelLabwareDialog, ViewChildrenLabwareDialog


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
        self.foc_bat_script_path = None

        self.setup_ui()
        # Delay initial draw until window is fully rendered
        self.root.after(500, lambda: self.draw_deck(auto_scale=True))

    def setup_ui(self):
        # Menu bar
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

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
        self.info_frame = ttk.Labelframe(control_frame, text="Selection Info", padding=10)
        self.info_frame.pack(fill=tk.BOTH, pady=5, padx=5)

        self.info_text = tk.Text(self.info_frame, height=10, wrap=tk.WORD)
        self.info_text.pack(fill=tk.BOTH, expand=True)

        # Control buttons
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(fill=tk.X, pady=5, padx=5)

        ttk.Button(btn_frame, text="Refresh", command=lambda: self.draw_deck(auto_scale=True)).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="Clear Selection", command=self.clear_selection).pack(fill=tk.X, pady=2)

        # ===== SLOTS SECTION WITH TOGGLE =====
        slots_main_frame = ttk.Labelframe(control_frame, text="Slots", padding=10)
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
        labware_main_frame = ttk.Labelframe(control_frame, text="Labware", padding=10)
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

    def view_children_labware(self):
        """Open viewer for child labware items (works for both placed and unplaced)"""
        selection = self.labware_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a labware first")
            return

        # Get labware based on current view mode
        if self.labware_view_mode.get() == "placed":
            lw_id = self.labware_listbox.get(selection[0])
            labware = self.deck.labware.get(lw_id)
        else:
            labware = self.unplaced_labware[selection[0]]

        if not labware:
            return

        # Only works for composite labware
        if not isinstance(labware, (Plate, ReservoirHolder, PipetteHolder)):
            messagebox.showinfo("Not Applicable",
                                f"{labware.__class__.__name__} doesn't have child items to view")
            return

        dialog = ViewChildrenLabwareDialog(self.root, labware)
        self.root.wait_window(dialog)

        # Refresh main display after editing
        if self.labware_view_mode.get() == "placed":
            self.draw_deck()

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
            ttk.Button(
                self.labware_button_frame,
                text=" View and Edit Children Labware",
                command=self.view_children_labware
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
                text=" View Children Labware",
                command=self.view_children_labware
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
        self.create_info_frame = CollapsibleFrame(create_control_frame, text="Selection Info")
        self.create_info_frame.pack(fill=tk.BOTH, pady=5, padx=5)

        # Text box inside content_frame
        self.create_info_text = tk.Text(self.create_info_frame.content_frame, height=10, wrap=tk.WORD)
        self.create_info_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 5))

        # Button also inside content_frame
        create_btn_frame = ttk.Frame(self.create_info_frame.content_frame)
        create_btn_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        ttk.Button(create_btn_frame, text="Clear Selection", command=self.clear_selection).pack(fill=tk.X)

        # === CREATE SECTIONS ===
        # Low-Level Labware section
        low_level_section = ttk.Labelframe(create_control_frame, text="Low-Level Labware", padding=15)
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

        ttk.Button(lll_btn_frame, text="Create Low-Level Lw", command=self.create_low_level_labware).pack( expand=True, fill=tk.X, padx=5, pady=5)
        ttk.Button(lll_btn_frame, text="Delete Selected", command=self.delete_selected_lll).pack( expand=True, fill=tk.X, padx=5, pady=5)

        # FOC Configuration Section
        foc_section = ttk.Labelframe(create_control_frame, text="FOC Measurement Configuration", padding=15)
        foc_section.pack(fill=tk.X, pady=10, padx=5)

        ttk.Label(
            foc_section,
            text="Configure the path to the FOC measurement batch script:",
            font=('Arial', 10),
            wraplength=350
        ).pack(anchor='w', pady=(0, 10))

        # Status Display
        self.foc_config_status_frame = ttk.Labelframe(foc_section, text="FOC Status", padding=10)
        self.foc_config_status_frame.pack(fill=tk.X, pady=5)

        self.foc_config_status_label = ttk.Label(
            self.foc_config_status_frame,
            text="Not configured",
            foreground='gray'
        )
        self.foc_config_status_label.pack(anchor='w')

        # Configure Button
        ttk.Button(
            foc_section,
            text="Open FOC Script Location",
            command=self.configure_foc_script
        ).pack(fill=tk.X, pady=5)

        pipettor_section = ttk.Labelframe(create_control_frame, text="Pipettor Configuration", padding=15)
        pipettor_section.pack(fill=tk.X, pady=10, padx=5)

        # Tip Volume Selection
        tip_vol_frame = ttk.Frame(pipettor_section)
        tip_vol_frame.pack(fill=tk.X, pady=5)

        ttk.Label(tip_vol_frame, text="Tip Volume:", font=('Arial', 13, 'bold')).pack(side=tk.LEFT, padx=(0, 10))

        self.tip_volume_var = tk.IntVar(value=200)
        ttk.Radiobutton(tip_vol_frame, text="200 µL", variable=self.tip_volume_var, value=200).pack(side=tk.LEFT,
                                                                                                    padx=5)
        ttk.Radiobutton(tip_vol_frame, text="1000 µL", variable=self.tip_volume_var, value=1000).pack(side=tk.LEFT,
                                                                                                      padx=5)

        # Multichannel Checkbox
        multichannel_frame = ttk.Frame(pipettor_section)
        multichannel_frame.pack(fill=tk.X, pady=5)

        self.multichannel_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            multichannel_frame,
            text="Multichannel (consecutive tips)",
            variable=self.multichannel_var
        ).pack(side=tk.LEFT)

        # Initialize Hardware Checkbox
        init_frame = ttk.Frame(pipettor_section)
        init_frame.pack(fill=tk.X, pady=5)

        self.initialize_hw_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            init_frame,
            text="initialize",
            variable=self.initialize_hw_var
        ).pack(side=tk.LEFT)

        # Separator
        separator = ttk.Separator(pipettor_section, orient='horizontal')
        separator.pack(fill=tk.X, pady=10)

        # Optional Parameters - Collapsible
        self.pipettor_params_collapsible = CollapsibleFrame(pipettor_section, text="Optional Parameters")
        self.pipettor_params_collapsible.pack(fill=tk.X, pady=5, padx=5)

        # Parameters content inside collapsible frame
        params_content = self.pipettor_params_collapsible.content_frame

        # Create a frame with padding for better layout
        params_inner = ttk.Frame(params_content, padding="10")
        params_inner.pack(fill=tk.BOTH, expand=True)

        # Info text
        info_label = ttk.Label(
            params_inner,
            text="Leave fields empty to use defaults",
            font=('Arial', 9, 'italic'),
            foreground='gray'
        )
        info_label.pack(anchor='w', pady=(0, 10))

        # Parameters grid
        params_grid = ttk.Frame(params_inner)
        params_grid.pack(fill=tk.X)

        # Configure column weights so entries don't overflow
        params_grid.columnconfigure(1, weight=1)
        params_grid.columnconfigure(3, weight=1)

        # Movement Speeds Section
        ttk.Label(
            params_grid,
            text="Movement Speeds (1-8, default: 7):",
            font=('Arial', 10, 'bold')
        ).grid(row=0, column=0, columnspan=4, sticky='w', pady=(0, 5))

        # X Speed
        ttk.Label(params_grid, text="X Speed:").grid(row=1, column=0, sticky='w', pady=3)
        self.x_speed_var = tk.StringVar(value="7")
        ttk.Entry(params_grid, textvariable=self.x_speed_var, width=8).grid(row=1, column=1, sticky='ew', pady=3,
                                                                            padx=(5, 10))

        # Y Speed
        ttk.Label(params_grid, text="Y Speed:").grid(row=1, column=2, sticky='w', pady=3, padx=(10, 0))
        self.y_speed_var = tk.StringVar(value="7")
        ttk.Entry(params_grid, textvariable=self.y_speed_var, width=8).grid(row=1, column=3, sticky='ew', pady=3,
                                                                            padx=(5, 0))

        # Z Speed
        ttk.Label(params_grid, text="Z Speed:").grid(row=2, column=0, sticky='w', pady=3)
        self.z_speed_var = tk.StringVar(value="5")
        ttk.Entry(params_grid, textvariable=self.z_speed_var, width=8).grid(row=2, column=1, sticky='ew', pady=3,
                                                                            padx=(5, 10))

        # Separator
        ttk.Separator(params_grid, orient='horizontal').grid(row=3, column=0, columnspan=4, sticky='ew', pady=10)

        # Piston Speeds Section
        ttk.Label(
            params_grid,
            text="Piston Speeds (1-6, default: 1):",
            font=('Arial', 10, 'bold')
        ).grid(row=4, column=0, columnspan=4, sticky='w', pady=(0, 5))

        # Aspirate Speed
        ttk.Label(params_grid, text="Aspirate:").grid(row=5, column=0, sticky='w', pady=3)
        self.aspirate_speed_var = tk.StringVar(value="1")
        ttk.Entry(params_grid, textvariable=self.aspirate_speed_var, width=8).grid(row=5, column=1, sticky='ew', pady=3,
                                                                                   padx=(5, 10))

        # Dispense Speed
        ttk.Label(params_grid, text="Dispense:").grid(row=5, column=2, sticky='w', pady=3, padx=(10, 0))
        self.dispense_speed_var = tk.StringVar(value="1")
        ttk.Entry(params_grid, textvariable=self.dispense_speed_var, width=8).grid(row=5, column=3, sticky='ew', pady=3,
                                                                                   padx=(5, 0))

        # Separator
        ttk.Separator(params_grid, orient='horizontal').grid(row=6, column=0, columnspan=4, sticky='ew', pady=10)

        # Tip Length Section
        ttk.Label(
            params_grid,
            text="Tip Length (mm, Leave blank if unsure):",
            font=('Arial', 10, 'bold')
        ).grid(row=7, column=0, columnspan=4, sticky='w', pady=(0, 5))

        # Tip Length
        ttk.Label(params_grid, text="Length:").grid(row=8, column=0, sticky='w', pady=3)
        self.tip_length_var = tk.StringVar(value="")
        ttk.Entry(params_grid, textvariable=self.tip_length_var, width=8).grid(row=8, column=1, sticky='ew', pady=3,
                                                                               padx=(5, 10))

        # Separator
        separator2 = ttk.Separator(pipettor_section, orient='horizontal')
        separator2.pack(fill=tk.X, pady=10)

        # Initialize Button
        ttk.Button(
            pipettor_section,
            text="Connect to Pipettor",
            command=self.initialize_pipettor
        ).pack(fill=tk.X, pady=5)

        # Status Display
        self.pipettor_status_frame = ttk.Labelframe(pipettor_section, text="Pipettor Status", padding=10)
        self.pipettor_status_frame.pack(fill=tk.X, pady=5)

        self.pipettor_status_label = ttk.Label(
            self.pipettor_status_frame,
            text="Not initialized",
            foreground='gray'
        )
        self.pipettor_status_label.pack(anchor='w')

    def ask_plate_id(self, parent):
        """
        Opens a custom dialog to select Year, Month, Day, and Alphabet.
        Returns a string in format YYYYMMDDX (e.g., 20231201A) or None if cancelled.
        """
        dialog = tk.Toplevel(parent)
        dialog.title("Plate Configuration")
        dialog.geometry("350x150")
        dialog.transient(parent)  # Make it float on top of parent
        dialog.grab_set()  # Modal (disable main window)

        # Storage for the result
        result = {"value": None}

        # --- Data Setup ---
        today = datetime.date.today()
        current_year = today.year
        years = [str(y) for y in range(current_year - 1, current_year + 5)]
        months = [str(m).zfill(2) for m in range(1, 13)]
        days = [str(d).zfill(2) for d in range(1, 32)]
        alphabets = list(string.ascii_uppercase)  # ['A', 'B', 'C'...]

        # --- GUI Layout ---
        frame = ttk.Frame(dialog, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        # Labels
        ttk.Label(frame, text="Year").grid(row=0, column=0, padx=5)
        ttk.Label(frame, text="Month").grid(row=0, column=1, padx=5)
        ttk.Label(frame, text="Day").grid(row=0, column=2, padx=5)
        ttk.Label(frame, text="Suffix").grid(row=0, column=3, padx=5)

        # Comboboxes
        cb_year = ttk.Combobox(frame, values=years, width=5, state="readonly")
        cb_year.set(current_year)
        cb_year.grid(row=1, column=0, padx=5)

        cb_month = ttk.Combobox(frame, values=months, width=3, state="readonly")
        cb_month.set(str(today.month).zfill(2))
        cb_month.grid(row=1, column=1, padx=5)

        cb_day = ttk.Combobox(frame, values=days, width=3, state="readonly")
        cb_day.set(str(today.day).zfill(2))
        cb_day.grid(row=1, column=2, padx=5)

        cb_alpha = ttk.Combobox(frame, values=alphabets, width=3, state="readonly")
        cb_alpha.set("A")  # Default to A
        cb_alpha.grid(row=1, column=3, padx=5)

        # --- Logic ---
        def on_ok():
            # format: YYYYMMDD + Letter
            final_str = f"{cb_year.get()}{cb_month.get()}{cb_day.get()}{cb_alpha.get()}"
            result["value"] = final_str
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        # Buttons
        btn_frame = ttk.Frame(dialog, padding=(0, 20, 0, 0))
        btn_frame.pack()
        ttk.Button(btn_frame, text="OK", command=on_ok).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="Cancel", command=on_cancel).pack(side=tk.LEFT, padx=10)

        # Wait for window to close
        parent.wait_window(dialog)
        return result["value"]

    def configure_foc_script(self):
        """Open file dialog to configure FOC measurement script path"""

        # Browse for BAT file
        filename = filedialog.askopenfilename(
            title="Select FOC48.bat Script",
            filetypes=[("Batch files", "*.bat"), ("All files", "*.*")],
            initialdir="C:\\labhub\\Import\\" if os.path.exists("C:\\labhub\\Import\\") else None
        )

        if filename:

            plate_name = self.ask_plate_id(self.root)

            if not plate_name:
                # This handles both "Cancel" and closing the window
                messagebox.showwarning("Warning", "Plate configuration was cancelled.")
                return

            self.foc_bat_script_path = filename
            self.foc_plate_name = plate_name

            self.foc_config_status_label.config(
                text=f"✓ Configured: {plate_name} ({os.path.basename(filename)})",
                foreground='green'
            )

            if hasattr(self, 'pipettor') and self.pipettor:
                self.pipettor.foc_bat_script_path = filename
                self.pipettor.foc_plate_name = plate_name

            #udpate buttons in function window
            if hasattr(self, 'function_window') and self.function_window:
                self.function_window.update_foc_section()

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

    def initialize_pipettor(self):
        """Initialize the pipettor with selected parameters"""
        try:
            # Get basic parameters
            tip_volume = self.tip_volume_var.get()
            multichannel = self.multichannel_var.get()
            initialize = self.initialize_hw_var.get()

            # Validate deck exists
            if not hasattr(self, 'deck') or self.deck is None:
                messagebox.showerror("Error", "Deck must be created before initializing pipettor")
                return

            # Helper function to get and validate speed parameters
            def get_speed_param(var, param_name, min_val, max_val, default=None):
                """Helper to get and validate speed parameters"""
                value_str = var.get().strip()
                if not value_str:
                    return default
                try:
                    value = int(value_str)
                    if value < min_val or value > max_val:
                        raise ValueError(f"{param_name} must be between {min_val} and {max_val}")
                    return value
                except ValueError as e:
                    raise ValueError(f"Invalid {param_name}: {str(e)}")

            # Get movement speeds (1-9)
            x_speed = get_speed_param(self.x_speed_var, "X Speed", 1, 8)
            y_speed = get_speed_param(self.y_speed_var, "Y Speed", 1, 8)
            z_speed = get_speed_param(self.z_speed_var, "Z Speed", 1, 8)

            # Get piston speeds (1-6)
            aspirate_speed = get_speed_param(self.aspirate_speed_var, "Aspirate Speed", 1, 6)
            dispense_speed = get_speed_param(self.dispense_speed_var, "Dispense Speed", 1, 6)

            # Get tip length
            tip_length_str = self.tip_length_var.get().strip()
            tip_length = float(tip_length_str) if tip_length_str else None

            # Create pipettor
            self.pipettor = PipettorPlus(
                tip_volume=tip_volume,
                multichannel=multichannel,
                initialize=initialize,
                deck=self.deck,
                tip_length=tip_length
            )

            # Set speeds if specified
            if x_speed is not None:
                self.pipettor.x_speed = x_speed
            if y_speed is not None:
                self.pipettor.y_speed = y_speed
            if z_speed is not None:
                self.pipettor.z_speed = z_speed
            if aspirate_speed is not None:
                self.pipettor.aspirate_speed = aspirate_speed
            if dispense_speed is not None:
                self.pipettor.dispense_speed = dispense_speed

            if hasattr(self, 'foc_bat_script_path'):
                self.pipettor.foc_bat_script_path = self.foc_bat_script_path
            if hasattr(self, 'foc_plate_name'):
                self.pipettor.foc_plate_name = self.foc_plate_name

            # Update FOC section in Operations tab
            if hasattr(self, 'function_window') and self.function_window:
                self.function_window.update_foc_section()

            # Build status message
            mode = "Multichannel (consecutive tips)" if multichannel else "Single channel"
            tip_info = f"{tip_volume}µL tips"
            tip_length_info = f", tip length: {tip_length}mm" if tip_length else ""
            hw_status = "initialized" if initialize else "not initialized"

            speed_info = []
            if x_speed or y_speed or z_speed:
                speed_info.append(f"Movement: X={x_speed or 7}, Y={y_speed or 7}, Z={z_speed or 7}")
            if aspirate_speed or dispense_speed:
                speed_info.append(f"Piston: Asp={aspirate_speed or 1}, Disp={dispense_speed or 1}")

            status_text = f"✓ {mode}, {tip_info}{tip_length_info}\nHardware: {hw_status}"
            if speed_info:
                status_text += "\n" + ", ".join(speed_info)

            self.pipettor_status_label.config(
                text=status_text,
                foreground='green'
            )

            if hasattr(self, 'rebuild_operations_tab'):
                self.rebuild_operations_tab()

        except ValueError as e:
            messagebox.showerror("Invalid Input", str(e))
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
        """Create the Operations tab - always create the frame"""
        operations_tab = ttk.Frame(self.right_panel_notebook)
        self.right_panel_notebook.add(operations_tab, text="Operations")

        # Store reference to the tab frame
        self.operations_tab_frame = operations_tab

        # Initialize FunctionWindow to None
        self.function_window = None

        # Build or rebuild the content
        self.rebuild_operations_tab()

    def on_operation_complete(self):
        """Called when an operation completes in Operations tab"""
        # Update pipettor status display
        self.update_pipettor_status()

    def update_operations_tab(self):

        """
        Update operations tab without destroying it.
        Only rebuild if absolutely necessary (pipettor changed).
        """
        if not hasattr(self, 'function_window') or self.function_window is None:
            # First time or pipettor was just initialized
            self.rebuild_operations_tab()
            return

        if hasattr(self.function_window, 'refresh_labware_lists'):
            self.function_window.refresh_labware_lists()

    def rebuild_operations_tab(self):
        """
        Rebuild the operations tab content.
        Call this whenever pipettor or deck state changes.
        """
        # Clear existing content
        for widget in self.operations_tab_frame.winfo_children():
            widget.destroy()

        # Check pipettor status
        if not hasattr(self, 'pipettor') or self.pipettor is None:
            # Show warning with retry button
            warning_frame = ttk.Frame(
                self.operations_tab_frame,
                relief=tk.RIDGE,
                borderwidth=2
            )
            warning_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            ttk.Label(
                warning_frame,
                text="Initialize Pipettor ",
                font=('Arial', 16, 'bold'),
                foreground='red'
            ).pack(pady=(20, 10))
            return

        self.function_window = FunctionWindow(
            deck=self.deck,
            pipettor=self.pipettor,
            mode="direct",
            parent_frame=self.operations_tab_frame,
            on_operation_complete=self.on_operation_complete
        )

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

        elif lll_type == "Reservoir":
            component = self.available_reservoirs[index]
            if messagebox.askyesno("Confirm Delete",
                                   f"Are you sure you want to delete Reservoir '{component.labware_id or 'Unnamed'}'?"):
                del self.available_reservoirs[index]

        elif lll_type == "IndividualPipetteHolder":
            component = self.available_individual_holders[index]
            if messagebox.askyesno("Confirm Delete",
                                   f"Are you sure you want to delete IndividualPipetteHolder '{component.labware_id or 'Unnamed'}'?"):
                del self.available_individual_holders[index]
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

            # Auto-select first item if list is not empty
            if self.lll_listbox.size() > 0:
                self.lll_listbox.selection_set(0)
                self.lll_listbox.activate(0)
                self.lll_listbox.see(0)
                # Trigger the selection event to update info panel
                self.on_lll_select()

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

    def update_selection_info(self, text):
        """Update info text in both Deck Editor and Create Labware tabs"""
        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(1.0, text)

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
            elif isinstance(component, Reservoir):
                self.available_reservoirs.append(component)
            elif isinstance(component, IndividualPipetteHolder):
                self.available_individual_holders.append(component)

            # 3. Update the listbox in the main 'Create Labware' tab
            # This function will clear and repopulate self.lll_listbox
            self.update_lll_list()

    def create_labware(self):
        """Open dialog to create new labware"""
        dialog = CreateLabwareDialog(self.root, self.available_wells, self.available_reservoirs,
                                     self.available_individual_holders)
        self.root.wait_window(dialog)

        if dialog.result:
            new_labware = dialog.result
            #print(new_labware.to_dict())
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
            if hasattr(self, 'rebuild_operations_tab'):
                self.rebuild_operations_tab()

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
                self.update_operations_tab()
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
        x2, y2 = self.mm_to_canvas(lw.position[0] - lw.size_x, lw.position[1] + lw.size_y)

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

        self.update_selection_info(info)

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

        if hasattr(lw, 'add_height'):
            info += f"Add Height: {lw.add_height} mm\n"
        if hasattr(lw, 'remove_height'):
            info += f"Remove Height: {lw.remove_height} mm\n"

        if hasattr(lw, 'drop_height'):
            info += f"\nDrop Height: {lw.drop_height} mm\n"
        self.update_selection_info(info)

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
        self.update_operations_tab()

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
        self.update_operations_tab()

        if unplaced_labware_list:
            lw_list = ", ".join([lw.labware_id for lw in unplaced_labware_list])
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
            labware = self.deck.remove_labware(lw_id)

        except ValueError as e:
            messagebox.showerror("Removal Error", str(e))
            return  # Exit if removal fails

        # 3. Final GUI Updates
        self.unplaced_labware.append(labware)
        self.canvas.delete(f'labware_{lw_id}')
        self.clear_selection()
        self.update_labware_list()
        self.update_operations_tab()

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

        # switch panel
        self.right_panel_notebook.select(0)
        self.clear_selection()
        self.labware_listbox.selection_clear(0, tk.END)

        if slot_id in self.deck.slots:
            self.slot_view_mode.set("placed")
            self.update_slots_list()

        tag = f'slot_{slot_id}'
        self.selected_item = ('slot', slot_id)

        items = self.canvas.find_withtag(tag)
        listbox = self.slots_listbox  # Correctly assigns the single listbox
        listbox.selection_clear(0, tk.END)

        # --- SELECTION LOOP ---
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

        self.update_selection_info(info)

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

        self.right_panel_notebook.select(0)
        self.clear_selection()
        self.slots_listbox.selection_clear(0, tk.END)
        self.selected_item = ('labware', lw_id)

        if lw_id in self.deck.labware:
            self.labware_view_mode.set("placed")
            self.update_labware_list()
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
        info += f"Slot: {slot_id if slot_id else 'None'}\n\n"

        # Add type-specific info
        if isinstance(lw, Plate):
            info += f"Rows: {lw._rows}\n"
            info += f"Columns: {lw._columns}\n"
        elif isinstance(lw, ReservoirHolder):
            info += f"Hooks X: {lw.hooks_across_x}\n"
            info += f"Hooks Y: {lw.hooks_across_y}\n"
        elif isinstance(lw, PipetteHolder):
            info += f"Holders X: {lw.holders_across_x}\n"
            info += f"Holders Y: {lw.holders_across_y}\n"

        if hasattr(lw, 'add_height'):
            info += f"Add Height: {lw.add_height} mm\n"
        if hasattr(lw, 'remove_height'):
            info += f"Remove Height: {lw.remove_height} mm\n"

        if hasattr(lw, 'drop_height'):
            info += f"\nDrop Height: {lw.drop_height} mm\n"

        self.update_selection_info(info)

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
        # guaranteeing the info panel is cleared regardless of selection origin
        self.update_selection_info("")

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
                #print(data)
                with open(filename, 'w') as f:
                    json.dump(data, f, indent=2)
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
                if hasattr(self, 'rebuild_operations_tab'):
                    self.rebuild_operations_tab()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load: {str(e)}")

    def run(self):
        """Start the GUI"""
        self.root.mainloop()

    def on_closing(self):
        """Handle window close event with save prompt"""
        response = messagebox.askyesnocancel(
            "Save Deck?",
            "Do you want to save the current deck before closing?"
        )

        if response is True:  # Yes - save and close
            self.save_deck()
            self.root.destroy()
        elif response is False:  # No - close without saving
            self.root.destroy()
        # None (Cancel) - do nothing, keep window open

# Main entry point
if __name__ == "__main__":
    # Create a sample deck for testing
    deck = Deck(range_x=(0, 265), range_y=(0, 244), deck_id="test_deck", range_z=141)

    # Run GUI
    gui = DeckGUI(deck)
    gui.run()
"""
if __name__ == "__main__":

    # Load deck from Downloads
    deck_file = os.path.expanduser("~/Downloads/deck1.json")

    with open(deck_file, "r") as f:
        data = json.load(f)

    deck = Serializable.from_dict(data['deck'])

    # Initialize pipettor as multichannel with 1000µL capacity
    pipettor = PipettorPlus(
        tip_volume=1000, multichannel=True, deck=deck,
    )

    # Run GUI
    gui = DeckGUI(deck)
    gui.pipettor = pipettor

    if hasattr(gui, 'rebuild_operations_tab'):
        gui.rebuild_operations_tab()

    gui.run()
"""