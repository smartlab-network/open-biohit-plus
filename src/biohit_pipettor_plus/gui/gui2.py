from tkinter import messagebox, filedialog, simpledialog
import json
import os
import datetime
import string

from biohit_pipettor_plus.deck_structure import *
from biohit_pipettor_plus.gui.function_window import FunctionWindow
from biohit_pipettor_plus.pipettor_plus.pipettor_plus import PipettorPlus
from biohit_pipettor_plus.gui.gui_dialogs import EditLabwareDialog, AddLabwareToSlotDialog, LabwareDialog, SlotDialog,CreateLowLevelLabwareDialog, ViewChildrenLabwareDialog
from biohit_pipettor_plus.gui.ui_helper import *

class DeckGUI:
    def __init__(self, deck=None):
        self.root = tk.Tk()
        self.root.title("Deck Editor")
        self.root.geometry("1200x1000")

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

        # (Label, Key, Type, Default, Options, Validation)
        self.runtime_param_definitions = [
            ("X Speed (1-8):", "x_speed", "entry", "7", None, "numeric"),
            ("Y Speed (1-8):", "y_speed", "entry", "7", None, "numeric"),
            ("Z Speed (1-8):", "z_speed", "entry", "5", None, "numeric"),
            ("Aspirate (1-6):", "aspirate_speed", "entry", "1", None, "numeric"),
            ("Dispense (1-6):", "dispense_speed", "entry", "1", None, "numeric"),
        ]

        self.lll_mapping = {
            "Well": self.available_wells,
            "Reservoir": self.available_reservoirs,
            "IndividualPipetteHolder": self.available_individual_holders,
            # map the actual Classes for dialog results
            Well: self.available_wells,
            Reservoir: self.available_reservoirs,
            IndividualPipetteHolder: self.available_individual_holders
        }

        # Initialize a dictionary to hold the StringVars for these parameters
        self.runtime_vars = {}


        self.setup_ui()
        # Delay initial draw until window is fully rendered
        self.root.after(500, lambda: self.draw_deck(auto_scale=True))

    def setup_ui(self):
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self._create_menubar()

        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Left Panel: Canvas ---
        self._create_canvas_area(main_frame)

        # --- Right Panel: Notebook ---
        right_panel = ttk.Frame(main_frame, width=400)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, padx=5, pady=5)
        right_panel.pack_propagate(False)

        self.right_panel_notebook = ttk.Notebook(right_panel)
        self.right_panel_notebook.pack(fill=tk.BOTH, expand=True)

        # ===== TAB 1: DECK EDITOR =====
        deck_tab = ttk.Frame(self.right_panel_notebook)
        self.right_panel_notebook.add(deck_tab, text="Deck Editor")

        scroll_view = ScrollableTab(deck_tab)
        root = scroll_view.content_frame

        # 1. Deck Info (Collapsible)
        self.deck_info_collapsible = CollapsibleFrame(root, text="Deck Info")
        self.deck_info_collapsible.pack(fill=tk.X, pady=5, padx=5)
        self.deck_info_label = ttk.Label(self.deck_info_collapsible.content_frame, text="", padding=10)
        self.deck_info_label.pack(fill=tk.X)

        # 2. Selection Info (Standardized)
        self.info_panel, self.info_text = create_info_panel(
            root,
            title="Selection Info",
            clear_cmd=self.clear_selection
        )

        #refresh button
        refresh_button_configs = [
            {"text": "Refresh Deck", "command": lambda: self.draw_deck(auto_scale=True)}
        ]
        create_button_bar(root, refresh_button_configs, fill=True, btns_per_row=1)

        # 3. Slots Section (Modularized)
        create_managed_list_section(
            instance=self,
            parent=root,
            title="Slots",
            var=self.slot_view_mode,
            list_attr="slots_listbox",
            btn_frame_attr="slots_button_frame",
            select_cmd=lambda e: self.on_item_select('slot'),
            update_cmd=lambda: self.update_item_list('slot')
        )

        # 4. Labware Section (Modularized)
        create_managed_list_section(
            instance=self,
            parent=root,
            title="Labware",
            var=self.labware_view_mode,
            list_attr="labware_listbox",
            btn_frame_attr="labware_button_frame",
            select_cmd=lambda e: self.on_item_select('labware'),
            update_cmd=lambda: self.update_item_list('labware')
        )

        self.slots_listbox.bind('<Double-Button-1>', lambda e: self.on_item_double_click(e, 'slot'))
        self.labware_listbox.bind('<Double-Button-1>', lambda e: self.on_item_double_click(e, 'labware'))

        # Initialize Other Tabs
        self.create_low_level_para_tab()
        self.create_operations_tab()

    def create_low_level_para_tab(self):
        """Create the Low Level Parameters tab using helper components."""
        tab_container = ttk.Frame(self.right_panel_notebook)
        self.right_panel_notebook.add(tab_container, text="Low level parameters")

        # 1. Initialize the ScrollableTab (Replaces ~40 lines of manual canvas code)
        scroll_view = ScrollableTab(tab_container)
        root = scroll_view.content_frame

        # 2. Selection Info Section (Using a standardized layout)
        self.info_panel, self.create_info_text = create_info_panel(
            root,
            title="Selection Info",
            clear_cmd=self.clear_selection,
            collapsed=True
        )
        # 3. Low-Level Labware Section
        self.low_level_collapsible = CollapsibleFrame(root, text="Low-Level Labware", collapsed=False)
        self.low_level_collapsible.pack(fill=tk.X, pady=5, padx=5)

        lll_inner = ttk.Frame(self.low_level_collapsible.content_frame, padding=10)
        lll_inner.pack(fill=tk.X)

        # Radio Selection using a loop
        self.lll_type = tk.StringVar(value="")
        for lll_t in ["Well", "Reservoir", "IndividualPipetteHolder"]:
            ttk.Radiobutton(lll_inner, text=lll_t, variable=self.lll_type,
                            value=lll_t, command= lambda : self.update_item_list('lll')).pack(anchor=tk.W, pady=2)

        self.lll_listbox, lll_container = create_scrolled_listbox(lll_inner, [], label_text="", height=6)
        self.lll_listbox.bind('<<ListboxSelect>>', lambda e: self.on_item_select('lll'))

        self.lll_button_frame = ttk.Frame(lll_inner)
        self.lll_button_frame.pack(fill=tk.X, pady=5)
        self.update_item_buttons('lll')

        # 4. FOC Configuration
        foc_section = ttk.Labelframe(root, text="FOC Configuration", padding=15)
        foc_section.pack(fill=tk.X, pady=5, padx=5)

        self.foc_config_status_label = ttk.Label(foc_section, text="Status: Not configured", foreground='gray')
        self.foc_config_status_label.pack(anchor='w', pady=5)

        ttk.Button(foc_section, text="Open FOC Script Location", command=self.configure_foc_script).pack(fill=tk.X)

        # 5. Pipettor Configuration
        pip_section = ttk.Labelframe(root, text="Pipettor Configuration", padding=15)
        pip_section.pack(fill=tk.X, pady=5, padx=5)

        # Tip Volume Frame
        vol_frame = ttk.Frame(pip_section)
        vol_frame.pack(fill=tk.X)
        ttk.Label(vol_frame, text="Tip Volume:").pack(side=tk.LEFT)
        self.tip_volume_var = tk.IntVar(value=200)
        for v in [200, 1000]:
            ttk.Radiobutton(vol_frame, text=f"{v} µL", variable=self.tip_volume_var, value=v).pack(side=tk.LEFT, padx=5)

        length_frame = ttk.Frame(pip_section)
        length_frame.pack(fill=tk.X, pady=5)
        ttk.Label(length_frame, text="Tip Length (mm) [Optional]:").pack(side=tk.LEFT)
        self.tip_length_var = tk.StringVar()
        ttk.Entry(length_frame, textvariable=self.tip_length_var, width=10).pack(side=tk.LEFT, padx=5)

        # Checkboxes
        self.multichannel_var = tk.BooleanVar(value=False)
        self.initialize_hw_var = tk.BooleanVar(value=False)
        self.simulate_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(pip_section, text="Multichannel", variable=self.multichannel_var).pack(anchor='w', pady=5)
        ttk.Checkbutton(pip_section, text="Initialize on connect", variable=self.initialize_hw_var).pack(anchor='w',
                                                                                                         pady=5)
        ttk.Checkbutton(pip_section, text="Use mock pipettor", variable=self.simulate_var).pack(anchor='w',
                                                                                                         pady=5)

        self.pipettor_status_label = ttk.Label(pip_section, text="", foreground="gray")
        self.pipettor_status_label.pack(pady=5)
        ttk.Button(pip_section, text="Connect to Pipettor", command=self.initialize_pipettor).pack(fill=tk.X, pady=5)

        # 6. Runtime Parameters
        self.runtime_collapsible = CollapsibleFrame(root, text="Runtime Parameters")
        self.runtime_collapsible.pack(fill=tk.X, pady=5, padx=5)

        # Get the internal container for our widgets
        runtime_inner = self.runtime_collapsible.content_frame

        self.runtime_vars, self.runtime_widgets = create_form(
            runtime_inner,
            self.runtime_param_definitions,
            field_width=10,
            return_widgets=True
        )

        self.set_params_button = ttk.Button(
            runtime_inner,
            text="Set Parameters",
            command=self.set_runtime_parameters,
            state='disabled'
        )

        self.set_params_button.grid(
            row=len(self.runtime_param_definitions),
            column=0,
            columnspan=2,
            sticky='ew',
            pady=10
        )

    def _create_menubar(self):
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
        view_menu.add_command(label="Zoom In", command=lambda: (setattr(self, 'scale', self.scale * 1.2)
                                                                    , self.draw_deck()))
        view_menu.add_command(label="Zoom Out", command=lambda: (setattr(self, 'scale', self.scale * 0.8),
                                                                 self.draw_deck()))

    def _create_canvas_area(self, parent):
        """Creates the left-side canvas with scrollbars."""
        canvas_frame = ttk.Frame(parent)
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 1. Create the Canvas
        self.canvas = tk.Canvas(
            canvas_frame,
            bg='white',
            scrollregion=(0, 0, 2000, 2000)
        )

        # 2. Add Scrollbars
        h_scroll = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        v_scroll = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)

        # 3. Connect Canvas to Scrollbars
        self.canvas.configure(xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)

        # 4. Layout using Grid (better for scrollbar alignment)
        self.canvas.grid(row=0, column=0, sticky='nsew')
        h_scroll.grid(row=1, column=0, sticky='ew')
        v_scroll.grid(row=0, column=1, sticky='ns')

        # Ensure the canvas expands to fill the frame
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)

        # 5. Canvas bindings
        self.canvas.bind("<Triple-Button-1>", self.on_canvas_triple_click)

    def get_context(self, category):
        """Returns the correct variables and lists for 'slot' or 'labware'."""
        if category == 'slot':
            return {
                'view_mode': self.slot_view_mode.get(),
                'listbox': self.slots_listbox,
                'btn_frame': self.slots_button_frame,
                'unplaced_list': self.unplaced_slots,
                'deck_dict': self.deck.slots,
                'id_attr': 'slot_id',
                'prefix': 'slot_',
                'modules': ['slot']
            }
        elif category == 'lll':
            return {
                'view_mode': 'unplaced',  # LLL is always unplaced
                'listbox': self.lll_listbox,
                'btn_frame': self.lll_button_frame,
                'unplaced_list': self.get_target_lll_list(),  # Dynamic based on radio
                'deck_dict': {},  # LLL never placed on deck
                'id_attr': 'labware_id',
                'prefix': 'lll_',
                'modules': ['basic', 'physical', 'content']  # Info display modules for LLL
            }
        else:
            return {
                'view_mode': self.labware_view_mode.get(),
                'listbox': self.labware_listbox,
                'btn_frame': self.labware_button_frame,
                'unplaced_list': self.unplaced_labware,
                'deck_dict': self.deck.labware,
                'id_attr': 'labware_id',
                'prefix': 'labware_',
                'modules': ['basic','physical', 'content', 'parent']
            }

    def unplace_item(self, category, item_id=None):
        ctx = self.get_context(category)

        # 1. Get ID from listbox if not provided by canvas
        if item_id is None:
            selection = ctx['listbox'].curselection()
            if not selection: return
            item_id = ctx['listbox'].get(selection[0]).split(' (')[0]

        # 2. Safety Check: Is it actually on the deck?
        if item_id not in ctx['deck_dict']:
            return

        # 3. Use the Deck's own logic to remove it
        try:
            if category == 'slot':
                # Slots are special because they might contain labware
                obj, released_children = self.deck.remove_slot(item_id, unplace_labware=True)
                self.unplaced_slots.append(obj)
                self.unplaced_labware.extend(released_children)
            else:
                obj = self.deck.remove_labware(item_id)
                self.unplaced_labware.append(obj)

            # 4. Global UI Refresh (Much more efficient than manual canvas deletes)
            self.draw_deck()
            self.update_item_list('slot')
            self.update_item_list('labware')

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def update_item_list(self, category):
        """Unified method to update list boxes and buttons for slots or labware or lll."""
        ctx = self.get_context(category)

        # For LLL, refresh the dynamic list
        if category == 'lll':
            ctx['unplaced_list'] = self.get_target_lll_list()

        lb = ctx['listbox']

        # 1. Clear the listbox
        lb.delete(0, tk.END)

        # 2. Update the dynamic buttons
        self.update_item_buttons(category)

        # 3. Populate based on mode
        if ctx['view_mode'] == "placed":
            # Sort and insert keys from self.deck.slots or self.deck.labware
            for item_id in sorted(ctx['deck_dict'].keys()):
                lb.insert(tk.END, item_id)
        else:
            # Insert IDs from self.unplaced_slots or self.unplaced_labware
            id_attr = ctx['id_attr']
            for item in ctx['unplaced_list']:
                lb.insert(tk.END, getattr(item, id_attr))

        if lb.size() > 0:  # If listbox has any items
            lb.selection_set(0)  # Visually highlight the first item (index 0)
            self.root.after_idle(lambda: self.select_item(category))
        else:
            # Clear info panel if no items
            update_detailed_info_text(self.create_info_text, obj=None)
            update_detailed_info_text(self.info_text, obj=None)

    def delete_item(self, category):
        """Unified delete for unplaced Slots or Labware or lll."""
        ctx = self.get_context(category)

        if category == 'lll':
            ctx['unplaced_list'] = self.get_target_lll_list()

        selection = ctx['listbox'].curselection()

        if not selection:
            messagebox.showwarning("No Selection", f"Please select a {category} to delete")
            return

        if not ctx['unplaced_list']:
            return

        obj = ctx['unplaced_list'][selection[0]]
        obj_id = getattr(obj, ctx['id_attr'])

        if messagebox.askyesno("Confirm", f"Delete {category} '{obj_id}'?"):
            ctx['unplaced_list'].remove(obj)
            self.update_item_list(category)

        # Clear info panel
        update_detailed_info_text(self.create_info_text, obj=None)
        update_detailed_info_text(self.info_text, obj=None)

    def select_item(self, category, item_id=None, event=None):
        """Unified selection handler for canvas clicks AND listbox selections."""
        ctx = self.get_context(category)

        # Refresh LLL list if needed
        if category == 'lll':
            ctx['unplaced_list'] = self.get_target_lll_list()

        # === CANVAS CLICK PATH (item_id provided) ===
        if item_id is not None:

            # switch to deck editor
            self.right_panel_notebook.select(0)

            # Switch to placed view ONLY if needed (prevents loop!)
            self.clear_selection()
            needs_mode_switch = False
            if category == 'slot' and self.slot_view_mode.get() != "placed":
                self.slot_view_mode.set("placed")
                needs_mode_switch = True
            elif category == 'labware' and self.labware_view_mode.get() != "placed":
                self.labware_view_mode.set("placed")
                needs_mode_switch = True

            # Only update list if we switched modes
            if needs_mode_switch:
                self.update_item_list(category)
                # Re-fetch context after update
                ctx = self.get_context(category)

            # Get object and highlight
            obj = ctx['deck_dict'].get(item_id)
            if not obj:
                return

            # Highlight on canvas
            self.selected_item = (category, item_id)
            color = 'darkblue' if category == 'slot' else 'darkred'
            tag = f"{ctx['prefix']}{item_id}"

            for item in self.canvas.find_withtag(tag):
                itype = self.canvas.type(item)
                if itype in ('rectangle', 'oval', 'polygon', 'line'):
                    self.canvas.itemconfig(item, width=4, outline=color)
                elif itype == 'text':
                    self.canvas.itemconfig(item, fill=color, font=('Arial', 10, 'bold'))

            # Sync listbox
            lb = ctx['listbox']
            lb.selection_clear(0, tk.END)
            for i in range(lb.size()):
                if lb.get(i).split(' (')[0] == item_id:
                    lb.selection_set(i)
                    lb.activate(i)
                    lb.see(i)
                    break

        # === LISTBOX SELECTION PATH (no item_id) ===
        else:
            selection = ctx['listbox'].curselection()

            if not selection:
                update_detailed_info_text(self.create_info_text, obj=None)
                update_detailed_info_text(self.info_text, obj=None)
                return

            # Get item based on view mode
            if ctx['view_mode'] == "placed":
                # Recursively call ourselves with the item_id
                item_id = ctx['listbox'].get(selection[0]).split(' (')[0]
                self.select_item(category, item_id=item_id)
                return
            else:
                # Unplaced item - just show info
                if not ctx['unplaced_list']:  # ← Add safety check
                    update_detailed_info_text(self.create_info_text, obj=None)
                    update_detailed_info_text(self.info_text, obj=None)
                    return
                obj = ctx['unplaced_list'][selection[0]]

        # === COMMON: Update Info Panel ===
        modules = ctx.get('modules', ['basic', 'physical', 'content'])
        update_detailed_info_text(self.create_info_text, obj=obj, modules=modules)
        update_detailed_info_text(self.info_text, obj=obj, modules=modules)

    def place_selected_item(self, category):
        """Unified method to place unplaced Slots or Labware onto the deck."""
        ctx = self.get_context(category)
        selection = ctx['listbox'].curselection()

        if not selection:
            messagebox.showwarning("No Selection", f"Please select a {category} to place")
            return

        # 1. Get the object from the correct unplaced list
        obj = ctx['unplaced_list'][selection[0]]
        obj_id = getattr(obj, ctx['id_attr'])

        # 2. Category-Specific Placement Logic
        try:
            if category == 'slot':
                # Check if slot ID already exists
                if obj_id in self.deck.slots:
                    raise ValueError(f"Slot '{obj_id}' already exists on deck")

                self.deck.add_slots([obj])
                self.unplaced_slots.remove(obj)
            else:
                self.place_labware(obj)

            # 3. Global Refresh
            self.draw_deck()
            self.update_item_list(category)
            if hasattr(self, 'update_operations_tab'):
                self.update_operations_tab()

        except Exception as e:
            messagebox.showerror("Placement Error", str(e))

    def update_item_buttons(self, category):
        """Unified method to refresh ALL buttons for Slots or Labware based on view mode."""
        ctx = self.get_context(category)
        mode = ctx['view_mode']

        # 1. Define configurations including ALL original buttons
        if category == 'slot':
            if mode == "placed":
                configs = [
                    {"text": "Unplace Slot", "command": lambda: self.unplace_item('slot'), "style": "Action.TButton"}
                ]
            else:
                configs = [
                    {"text": "Place on Deck", "command": lambda: self.place_selected_item('slot')},
                    {"text": "Edit", "command": lambda: self.edit_selected_item('slot')},
                    {"text": "Create Slot", "command": self.create_slot},
                    {"text": "Delete", "command": lambda: self.delete_item('slot'), "style": "Danger.TButton"}
                ]
        elif category == 'lll':  # ← ADD THIS CASE
            configs = [
                {"text": "Create Low-Level Lw", "command": self.create_low_level_labware},
                {"text": "Delete", "command": lambda: self.delete_item('lll'), "style": "Danger.TButton"}
            ]

        else:  # labware
            if mode == "placed":
                configs = [
                    {"text": "Unplace Lw", "command": lambda: self.unplace_item('labware')},
                    {"text": "Edit Children Lw", "command": self.view_children_labware}
                ]
            else:
                configs = [
                    {"text": "Place on Slot on Deck", "command": lambda: self.place_selected_item('labware')},
                    {"text": "Edit", "command": lambda: self.edit_selected_item('labware')},
                    {"text": "View Children Labware", "command": self.view_children_labware},
                    {"text": "Create", "command": self.create_labware},
                    {"text": "Delete", "command": lambda: self.delete_item('labware'), "style": "Danger.TButton"}
                ]

        # 2. Refresh the UI
        # Clear the specific frame created by create_managed_list_section
        for child in ctx['btn_frame'].winfo_children():
            child.destroy()

        # 3. Create the buttons using your flexible helper
        _, buttons_dict = create_button_bar(
            parent=ctx['btn_frame'],
            button_configs=configs,
            fill=True,
            btns_per_row=2
        )

    def edit_selected_item(self, category):
        """Unified method to edit unplaced Slots or Labware."""
        ctx = self.get_context(category)
        selection = ctx['listbox'].curselection()

        if not selection:
            messagebox.showwarning("No Selection", f"Please select a {category} to edit")
            return

        # 1. Identify the object
        index = selection[0]
        obj = ctx['unplaced_list'][index]

        # 2. Determine which Dialog to open
        if category == 'slot':
            dialog = SlotDialog(self.root, slot=obj)
        else:
            # Labware editing often needs the available reservoirs list for mapping
            dialog = EditLabwareDialog(self.root, obj, self.available_reservoirs)

        self.root.wait_window(dialog)

        # 3. Handle the result
        if dialog.result:
            # Refresh the  list and reselect item
            self.update_item_list(category)
            self.root.after_idle(lambda: self.select_item(category, getattr(obj, ctx['id_attr'])))

    def on_item_select(self, category, event=None):
        """Unified selection handler for slot, labware, and LLL list boxes"""
        self.select_item(category, event=event)

    def get_target_lll_list(self):
        """Helper to return the list based on the current radio selection."""
        return self.lll_mapping.get(self.lll_type.get(), [])

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
        if not hasattr(labware, "_rows") and not hasattr(labware, "_cols"):
            messagebox.showinfo("Not Applicable",
                                f"{labware.__class__.__name__} doesn't have child items to view")
            return

        dialog = ViewChildrenLabwareDialog(self.root, labware, pipettor=getattr(self, 'pipettor', None))
        self.root.wait_window(dialog)
        self.draw_deck()

    def create_low_level_labware(self):
        """Open dialog to create low-level labware components and update UI."""

        # Get the currently selected type from radio buttons
        selected_type = self.lll_type.get()
        dialog = CreateLowLevelLabwareDialog(self.root, initial_type=selected_type)
        self.root.wait_window(dialog)

        if dialog.result:
            target_list = self.lll_mapping.get(type(dialog.result))
            if target_list is not None:
                target_list.append(dialog.result)
                self.update_item_list('lll')

    def create_slot(self):
        """Open dialog to create a new slot"""
        dialog = SlotDialog(self.root)
        self.root.wait_window(dialog)

        if dialog.result:
            new_slot = dialog.result
            self.unplaced_slots.append(new_slot)

            if self.slot_view_mode.get() == "unplaced":
                self.update_item_list('slot')

    def create_labware(self):
        """Open dialog to create new labware"""
        dialog = LabwareDialog(self.root, self.available_wells, self.available_reservoirs,
                                     self.available_individual_holders)
        self.root.wait_window(dialog)

        if dialog.result:
            new_labware = dialog.result
            # Store newly created component if needed
            if isinstance(dialog.result, Plate) and dialog.selected_well:
                if dialog.selected_well not in self.available_wells:
                    self.available_wells.append(dialog.selected_well)
                elif isinstance(dialog.result, PipetteHolder) and dialog.selected_holder:  # ← Fix here
                    if dialog.selected_holder not in self.available_individual_holders:  # ← And here
                        self.available_individual_holders.append(dialog.selected_holder)  # ← And here


            self.unplaced_labware.append(dialog.result)
            self.labware_view_mode.set("unplaced")
            self.update_item_list('labware')

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

    def ask_plate_id(self, parent):
        """
        Opens a custom dialog to select Year, Month, Day, and Alphabet.
        Returns a string in format YYYYMMDDX (e.g., 20231201A) or None if cancelled.
        """
        dialog = tk.Toplevel(parent)
        dialog.title("Plate Configuration")
        dialog.geometry("350x200")
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

        # --- gui Layout ---
        frame = ttk.Frame(dialog, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        # Labels
        ttk.Label(frame, text="Year").grid(row=0, column=0, padx=5)
        ttk.Label(frame, text="Month").grid(row=0, column=1, padx=5)
        ttk.Label(frame, text="Day").grid(row=0, column=2, padx=5)
        ttk.Label(frame, text="Suffix").grid(row=0, column=3, padx=5)

        # Combo boxes
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

            #update buttons in function window
            if hasattr(self, 'function_window') and self.function_window:
                self.function_window.update_foc_section()

    def initialize_pipettor(self):
        """Initialize the pipettor with basic parameters"""
        try:
            # Get basic parameters
            tip_volume = self.tip_volume_var.get()
            multichannel = self.multichannel_var.get()
            initialize = self.initialize_hw_var.get()
            use_simulator = self.simulate_var.get()

            # Get tip length (set once during connection)
            tip_length_str = self.tip_length_var.get().strip()
            tip_length = float(tip_length_str) if tip_length_str else None

            # Validate deck exists
            if not hasattr(self, 'deck') or self.deck is None:
                messagebox.showerror("Error", "Deck must be created before initializing pipettor")
                return

            # Close existing pipettor if any
            if hasattr(self, 'pipettor') and self.pipettor:
                if hasattr(self.pipettor, 'show_plot'):
                    self.pipettor.show_plot()
                self.pipettor.close()

            # Create pipettor
            self.pipettor = PipettorPlus(
                tip_volume=tip_volume,
                multichannel=multichannel,
                initialize=initialize,
                deck=self.deck,
                tip_length=tip_length,
                mock_pipettor = use_simulator
            )


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
            tip_length_info = f",\n tip length: {tip_length}mm" if tip_length else ""
            hw_status = "initialized" if initialize else "not initialized"

            status_text = f"✓ {mode}, {tip_info}{tip_length_info}\nHardware: {hw_status}"

            self.pipettor_status_label.config(
                text=status_text,
                foreground='green'
            )

            # Enable runtime parameters section
            self.toggle_runtime_ui()

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

    def toggle_runtime_ui(self, enabled=True):
        """
        Toggle the runtime parameters section based on pipettor connection state.
        """
        # 1. Determine state and styling
        state = 'normal' if enabled else 'disabled'

        # handle expansion
        if enabled != self.runtime_collapsible.is_expanded:
            self.runtime_collapsible.toggle()

        # 3. Update all Entry/Combo widgets
        # .values() because self.runtime_widgets is a dict: {key: widget}
        for widget in self.runtime_widgets.values():
            widget.config(state=state)

        # 2. Update the Action Button
        self.set_params_button.config(state=state)

    def set_runtime_parameters(self):
        """Set runtime parameters on the connected pipettor"""
        try:
            # Check if pipettor exists
            if not hasattr(self, 'pipettor') or self.pipettor is None:
                messagebox.showerror("Error", "Pipettor is not connected")
                return

            # Validation rules for each parameter type
            validation_rules = {
                'x_speed': (1, 8, "X Speed"),
                'y_speed': (1, 8, "Y Speed"),
                'z_speed': (1, 8, "Z Speed"),
                'aspirate_speed': (1, 6, "Aspirate Speed"),
                'dispense_speed': (1, 6, "Dispense Speed"),
            }

            updated_params = []

            # Process each runtime parameter
            for key, var in self.runtime_vars.items():
                value_str = var.get().strip()

                if not value_str:
                    continue  # Skip empty values

                # Validate based on parameter type
                if key in validation_rules:
                    min_val, max_val, display_name = validation_rules[key]
                    try:
                        value = int(value_str)
                        if value < min_val or value > max_val:
                            raise ValueError(f"{display_name} must be between {min_val} and {max_val}")

                        # Set the value on pipettor
                        setattr(self.pipettor, key, value)
                        updated_params.append(f"{display_name}: {value}")

                    except ValueError as e:
                        raise ValueError(f"Invalid {display_name}: {str(e)}")

            if not updated_params:
                messagebox.showinfo("Info", "No parameters were changed (all fields empty)")

        except ValueError as e:
            messagebox.showerror("Invalid Input", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to set parameters:\n{str(e)}")

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
        if hasattr(self, 'pipettor_status_label'):
            status_text = self.get_pipettor_status_text()

            if hasattr(self, 'pipettor') and self.pipettor is not None:
                if self.pipettor.has_tips:
                    tip_content = self.pipettor.get_tip_status()
                    status_text += f"\nContent: {tip_content['content_summary']}"

                self.pipettor_status_label.config(text=status_text, foreground='green')
            else:
                self.pipettor_status_label.config(text=status_text, foreground='gray')

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
        self.update_item_list('slot')
        self.update_item_list('labware')
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
            offset = 15
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
            text="X-axis",
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
                             lambda e, sid=slot_id: self.select_item('slot', slot_id))

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
                             lambda e, lid=lw_id: self.select_item('labware', lid))
    # Event handlers

    def on_canvas_triple_click(self, event):
        """Show context menu on canvas (FIXED)"""
        item = self.canvas.find_closest(event.x, event.y)[0]
        tags = self.canvas.gettags(item)

        # 1. Initialize variables
        lw_id = None
        slot_id = None

        # 2. Extract ID based on known prefixes
        for t in tags:
            if t.startswith('labware_'):
                # Extract the ID after the first underscore
                lw_id = t.split('_', 1)[1]
            elif t.startswith('slot_'):
                # Extract the ID after the first underscore
                slot_id = t.split('_', 1)[1]


        if lw_id:
            self.unplace_item('labware', lw_id)

        elif slot_id:
            slot = self.deck.slots.get(slot_id)
            if slot and slot.labware_stack:
                confirmed = messagebox.askyesno(
                    "Confirm Unplace Slot",
                    f"Unplacing this slot will also unplace all contained labware. Continue?"
                )
                if confirmed:
                    self.unplace_item('slot', slot_id)
            else:
                self.unplace_item('slot', slot_id)

    def on_item_double_click(self, event, category):
        """Unified double-click handler for Slots and Labware."""
        ctx = self.get_context(category)

        # Only trigger placement if we are currently in 'unplaced' view mode
        if ctx['view_mode'] == "unplaced":
            self.place_selected_item(category)

    def update_deck_info(self):
        """Update deck info display"""
        info = f"ID: {self.deck.deck_id}\n"
        info += f"Range X: {self.deck.range_x}\n"
        info += f"Range Y: {self.deck.range_y}\n"
        info += f"Range Z: {self.deck.range_z}\n"
        info += f"Slots: {len(self.deck.slots)}\n"
        info += f"Labware: {len(self.deck.labware)}"
        self.deck_info_label.config(text=info)

    def clear_selection(self):
        """
        Clears the current selection on the canvas, list boxes, and resets item styles.
        It ensures the information panel is cleared by explicitly calling the update function.
        """

        # --- 1. Canvas Selection (Handles Placed Items) ---
        if self.selected_item:
            item_type, item_id = self.selected_item
            tag = f'{item_type}_{item_id}'

            # Find all canvas items associated with the previously selected tag and reset style
            for item in self.canvas.find_withtag(tag):
                canvas_item_type = self.canvas.type(item)  # ← Renamed to avoid shadowing

                # Reset SHAPE items (Rectangle, Oval, Polygon)
                if canvas_item_type in ('rectangle', 'oval', 'polygon'):
                    self.canvas.itemconfig(item, width=2, outline='blue')

                # Reset TEXT items (The label)
                elif canvas_item_type == 'text':
                    self.canvas.itemconfig(item, fill='black', font=('Arial', 10, 'normal'))

                # Optional: handle line items if present
                elif canvas_item_type == 'line':
                    self.canvas.itemconfig(item, width=2, fill='blue')

            # Clear the internal canvas selection tracking state
            self.selected_item = None

        # --- 2. Clear ALL list boxes ---
        self.slots_listbox.selection_clear(0, tk.END)
        self.labware_listbox.selection_clear(0, tk.END)
        if hasattr(self, 'lll_listbox'):
            self.lll_listbox.selection_clear(0, tk.END)

        # --- 3. Clear BOTH info panels ---
        # Main deck editor info panel
        for widget in [self.info_text, self.create_info_text]:
            widget.config(state='normal')
            widget.delete(1.0, tk.END)
            widget.config(state='disabled')

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
                self.available_wells.clear()
                if 'available_wells' in data:
                    for well_data in data['available_wells']:
                        self.available_wells.append(Serializable.from_dict(well_data))

                self.available_reservoirs.clear()
                if 'available_reservoirs' in data:
                    for res_data in data['available_reservoirs']:
                        self.available_reservoirs.append(Serializable.from_dict(res_data))

                self.available_individual_holders.clear()
                if 'available_individual_holders' in data:
                    for holder_data in data['available_individual_holders']:
                        self.available_individual_holders.append(Serializable.from_dict(holder_data))

                self.draw_deck()

                if hasattr(self, 'rebuild_operations_tab'):
                    self.rebuild_operations_tab()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load: {str(e)}")

    def run(self):
        """Start the gui"""
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
            if hasattr(self, 'pipettor') and self.pipettor:
                self.pipettor.close()
            self.root.destroy()


def main():
    # Create a sample deck for testing
    deck = Deck(range_x=(0, 265), range_y=(0, 244), deck_id="test_deck", range_z=141)

    # Run gui
    gui = DeckGUI(deck)
    gui.run()


# Main entry point
if __name__ == "__main__":
    main()
