import ttkbootstrap as ttk
import tkinter as tk
import string
from collections import deque
from biohit_pipettor_plus.pipettor_plus.pipettor_constants import Pipettors_in_Multi

class WellWindow:
    """
    A window representing a grid of wells (e.g., a cell culture plate),
    where each well is represented as a button.

    Disabled wells cannot be interacted with. A maximum number of active
    wells is enforced — if the limit is reached, the oldest selected well
    is automatically deselected (FIFO behavior via deque).

    Parameters
    ----------
    rows : int
        Number of rows in the well grid.
    columns : int
        Number of columns in the well grid.
    labware_id : str
        Identifier of the labware (plate).
    title : str, optional
        Title for the window.
    master : ttk.Window or tk.Tk, optional
        Parent window. If provided, creates a modal dialog.
    wells_list : list[tuple[int, int]], optional
        List of (row, column) tuples for wells that contain culture.
        Wells not in this list are disabled.
    max_selected : int, optional
        Maximum number of simultaneously selected wells.
    """

    def __init__(self, rows: int, columns: int, labware_id: str, title: str = "",
                 master=None, wells_list: list[tuple[int, int]] = None,
                 max_selected: int = None, multichannel_mode: bool = False,
                 allow_auto_select: bool = False):


        # --- Window setup ---
        if master:
            # Create as a dialog
            self.__root = ttk.Toplevel(master=master)
            self.__root.title(title if title else f"Select Wells from: {labware_id}")
            self.__root.transient(master)
            self.__root.grab_set()

            # Calculate reasonable size based on grid dimensions
            cell_width = 80
            cell_height = 60
            padding = 100

            width = min(1400, (columns + 2) * cell_width + padding)
            height = min(900, (rows + 3) * cell_height + padding)

            self.__root.geometry(f"{width}x{height}")

            # Center on parent
            self.__root.update_idletasks()
            x = master.winfo_x() + (master.winfo_width() // 2) - (width // 2)
            y = master.winfo_y() + (master.winfo_height() // 2) - (height // 2)
            self.__root.geometry(f"{width}x{height}+{x}+{y}")

        else:
            # Create as standalone window
            self.__root = ttk.Window(
                title=f"Select Wells from Labware: {labware_id}",
                themename="darkly"
            )
            self.__root.geometry("1200x900")

        self.confirmed = False
        self.auto_selected = False
        self.allow_auto_select = allow_auto_select
        self.is_well_window = True
        self.back_requested = False

        # --- Core attributes ---
        self.rows = rows
        self.columns = columns
        self.labware_id = labware_id
        self.wells_list = wells_list if wells_list else []

        if max_selected:
            self.max_selected = max_selected
        else:
            self.max_selected = self.rows * self.columns

        self.well_state = [[False for _ in range(self.columns)] for _ in range(self.rows)]
        self.selected_queue = deque()

        self.safe_var = ttk.BooleanVar(value=False)
        self.row_vars = [ttk.BooleanVar() for _ in range(self.rows)]
        self.col_vars = [ttk.BooleanVar() for _ in range(self.columns)]
        self.is_check_all = ttk.BooleanVar()

        self.buttons = [[None for _ in range(self.columns)] for _ in range(self.rows)]
        self.multichannel_mode = multichannel_mode
        self.channels = Pipettors_in_Multi if self.multichannel_mode else 1
        self.max_selected = max_selected if max_selected else self.rows * self.columns

        # Handle OS window close button (X)
        self.__root.protocol("WM_DELETE_WINDOW", self.on_window_close)

        # Add info label at top
        info_frame = ttk.Frame(self.__root)
        info_frame.grid(row=0, column=0, columnspan=self.columns + 1, sticky="ew", pady=5)

        ttk.Label(
            info_frame,
            text=f"Select wells from: {labware_id}",
            font=('Arial', 12, 'bold')
        ).pack(side=tk.LEFT, padx=10)

        if self.max_selected < self.rows * self.columns:
            ttk.Label(
                info_frame,
                text=f"(Max: {self.max_selected} wells)",
                font=('Arial', 10),
                foreground='orange'
            ).pack(side=tk.LEFT, padx=5)

        # Buttons
        button_row = self.rows + 2

        self.button_back = ttk.Button(
            self.__root,
            text="← Back",
            command=self.callback_back,
            bootstyle="danger"
        )
        self.button_back.grid(
            column=0,
            row=button_row,
            sticky="nsew",
            padx=10,
            pady=10
        )

        if self.allow_auto_select:
            # Single smart button with dynamic text
            self.button_confirm = ttk.Button(
                self.__root,
                text="✓ Auto-Select",
                command=self.callback_save,
                bootstyle="primary"
            )
            self.button_confirm.grid(
                column=1,
                row=button_row,
                sticky="nsew",
                columnspan=self.columns,
                padx=10,
                pady=10
            )

            self.__root.bind('<Return>', self.on_enter_key)
            self.button_confirm.focus_set()

            # Track selection state for button text updates
            self.has_manual_selection = False

        else:
            # No auto-select available: traditional confirm button
            self.button_save = ttk.Button(
                self.__root,
                text="✓ Confirm Selection",
                command=self.callback_save,
                bootstyle="success-outline",
                state = 'disabled'

            )
            self.button_save.grid(
                column=1,
                row=self.rows + 2,
                sticky="nsew",
                columnspan=self.columns,
                padx=10,
                pady=10
            )
            self.__root.bind('<Return>', self.on_enter_key)
            self.button_save.focus_set()


        if not self.multichannel_mode:
            self.checkbutton_all = ttk.Checkbutton(
                self.__root,
                command=self.callback_check_all,
                variable=self.is_check_all
            )
            self.checkbutton_all.grid(row=1, column=0, sticky="ns")

        self.set_grid()
        self.create_well_buttons()
        self.create_check_boxes()

        if self.wells_list:
            self.update_all_button_states()

        # Initialize button state based on current selection
        self.update_confirm_button_state()

    def set_grid(self):
        """Configure Tkinter grid layout for the window."""
        # Row 0: Info header
        self.__root.rowconfigure(0, weight=0)
        # Rows 1 to rows+1: Grid
        for i in range(1, self.rows + 2):
            self.__root.rowconfigure(i, weight=1)
        # Last row: Save button
        self.__root.rowconfigure(self.rows + 2, weight=0)

        for i in range(self.columns + 1):
            self.__root.columnconfigure(i, weight=1)

    def update_confirm_button_text(self):
        """Update confirm button text based on current selection state"""
        if not self.allow_auto_select or not hasattr(self, 'button_confirm'):
            return

        has_selection = any(any(row) for row in self.well_state)

        # Only update if state actually changed (avoid unnecessary UI updates)
        if has_selection != self.has_manual_selection:
            self.has_manual_selection = has_selection

            if has_selection:
                self.button_confirm.config(
                    text=" Select",
                    bootstyle="success"
                )
            else:
                self.button_confirm.config(
                    text="Auto-Select",
                    bootstyle="primary"
                )

    def get_root(self):
        """Return the underlying Tk root window."""
        return self.__root

    def show_well_window(self):
        """Show or hide the window."""
        if self.is_well_window:
            self.__root.withdraw()
            self.is_well_window = False
        else:
            self.__root.deiconify()
            self.is_well_window = True

    def callback_back(self):
        """Handle back button - go to previous wizard step"""
        self.back_requested = True
        self.__root.destroy()

    def create_well_buttons(self):
        """Create a grid of well buttons."""
        for r in range(self.rows):
            for c in range(self.columns):
                well_name = f"{string.ascii_uppercase[r]}{c}"
                well_available = (r, c) in self.wells_list

                if well_available:
                    # Well is available - make it clickable
                    if self.multichannel_mode:
                        # Check if valid starting position (has enough consecutive rows below)
                        if r + self.channels <= self.rows:
                            # Check all positions are available
                            all_available = all((r + i, c) in self.wells_list for i in range(self.channels))
                            if all_available:
                                # VALID STARTING POSITION - make clickable
                                state = "normal"
                                style = "light"
                                command = lambda c=c, r=r: self.callback_well_button(r, c)
                            else:
                                # Some positions missing
                                state = "disabled"
                                style = "light"
                                command = None
                        else:
                            # Not enough room for consecutive tips below
                            state = "disabled"
                            style = "light"
                            command = None
                    else:
                        # Single-channel mode - clickable
                        state = "normal"
                        style = "light"
                        command = lambda c=c, r=r: self.callback_well_button(r, c)

                    # Create button
                    cur_button = ttk.Button(
                        self.__root,
                        text=well_name,
                        command=command,
                        bootstyle=style,
                        state=state
                    )
                    cur_button.grid(
                        row=r + 2,
                        column=c + 1,
                        sticky='nsew',
                        ipadx=20,
                        ipady=10,
                        padx=2,
                        pady=2
                    )
                    self.buttons[r][c] = cur_button

                    # Add hover bindings for multichannel
                    if self.multichannel_mode and state == "normal":
                        cur_button.bind('<Enter>', lambda e, r=r, c=c: self.show_multichannel_preview(r, c))
                        cur_button.bind('<Leave>', lambda e: self.hide_multichannel_preview())
                        cur_button.configure(cursor="crosshair")

                else:
                    # Well not available - show as disabled label
                    cur_label = ttk.Label(
                        self.__root,
                        text=well_name,
                        bootstyle="danger-inverse",  # Red background
                        anchor="center",
                        font=('Arial', 10)
                    )
                    cur_label.grid(
                        row=r + 2,
                        column=c + 1,
                        sticky='nsew',
                        ipadx=20,
                        ipady=10,
                        padx=2,
                        pady=2
                    )
                    self.buttons[r][c] = cur_label

    def create_check_boxes(self):
        """Create row and column checkboxes for easier multi-selection."""
        if self.multichannel_mode:
            return
        for r in range(self.rows):
            cur_check = ttk.Checkbutton(
                self.__root,
                command=lambda r=r: self.toggle_row(r),
                variable=self.row_vars[r]
            )
            cur_check.grid(
                row=r + 2,
                column=0,
                sticky='ns'
            )

        for c in range(self.columns):
            curr_check = ttk.Checkbutton(
                self.__root,
                command=lambda c=c: self.toggle_column(c),
                variable=self.col_vars[c]
            )
            curr_check.grid(
                row=1,
                column=c + 1,
                sticky='ns',
                ipady=10
            )

    def activate_well(self, row: int, col: int):
        """
        Activate a well and add it to the queue.

        If the maximum number of selected wells is reached, the oldest
        selected well is automatically deselected.

        Parameters
        ----------
        row : int
            Row index of the well.
        col : int
            Column index of the well.
        """
        if len(self.selected_queue) >= self.max_selected:
            old_r, old_c = self.selected_queue.popleft()
            self.well_state[old_r][old_c] = False
            self.buttons[old_r][old_c].configure(bootstyle="light")

        self.well_state[row][col] = True
        self.buttons[row][col].configure(bootstyle="success")
        self.selected_queue.append((row, col))
        self.update_confirm_button_text()
        self.update_confirm_button_state()

    def deactivate_well(self, row: int, col: int):
        """
        Deactivate a well and remove it from the queue.

        Parameters
        ----------
        row : int
            Row index of the well.
        col : int
            Column index of the well.
        """
        if (row, col) in self.selected_queue:
            self.selected_queue.remove((row, col))
        self.well_state[row][col] = False
        self.buttons[row][col].configure(bootstyle="light")
        self.update_confirm_button_text()
        self.update_confirm_button_state()

    def show_multichannel_preview(self, row: int, col: int):
        """Highlight all consecutive wells that will be selected with preview colors."""
        for i in range(self.channels):
            r = row + i
            if r < self.rows and self.buttons[r][col] is not None:
                if not self.well_state[r][col]:
                    if i == 0:
                        self.buttons[r][col].configure(bootstyle="warning-outline")
                    else:
                        self.buttons[r][col].configure(bootstyle="secondary-outline")

    def hide_multichannel_preview(self):
        """Remove preview highlighting."""
        for r in range(self.rows):
            for c in range(self.columns):
                widget = self.buttons[r][c]

                if widget is None or self.well_state[r][c] or isinstance(widget, ttk.Label):
                    continue

                if (r, c) in self.wells_list:
                    widget.configure(bootstyle="light")

    def get_start_positions(self):
        """
        Extract start positions from current selections.

        Returns
        -------
        list[tuple[int, int]]
            List of (row, col) tuples representing start positions
        """
        if self.multichannel_mode:
            start_positions = []
            for r, c in self.selected_queue:
                if r == 0 or not self.well_state[r - 1][c]:
                    start_positions.append((r, c))
            return start_positions
        else:
            return list(self.selected_queue)

    def callback_well_button(self, row: int, column: int):
        """Toggle a well button with multichannel awareness."""

        if self.multichannel_mode:

            # --- Helper for clearing a well block ---
            def clear_block(start_row, col):
                for i in range(self.channels):
                    r = start_row + i
                    if r < self.rows:
                        # Clear internal state
                        self.well_state[r][col] = False
                        if (r, col) in self.selected_queue:
                            self.selected_queue.remove((r, col))

                        # Restore UI state for the wells in the block
                        if self.buttons[r][col] is not None:
                            # Restore non-start rows to unselected color
                            if i > 0:
                                self.buttons[r][col].configure(bootstyle="light")
                            # Restore the start row to its original/enabled color
                            else:
                                is_valid = (start_row, col) in self.wells_list and start_row + self.channels <= self.rows and \
                                           all((start_row + j, col) in self.wells_list for j in range(self.channels))
                                self.buttons[start_row][col].configure(bootstyle="light" if is_valid else "secondary")

            # ✅ STEP 1: Check if this is a valid starting position
            is_valid_start_pos = (row + self.channels <= self.rows and
                                  all((row + i, column) in self.wells_list for i in range(self.channels)))

            if not is_valid_start_pos:
                # Not a valid start position - ignore click
                return

            # ✅ STEP 2: Check if THIS specific start row is already selected
            is_this_block_selected = self.well_state[row][column]
            is_full_selection_at_start = all(
                self.well_state[row + i][column]
                for i in range(self.channels)
                if row + i < self.rows
            )

            if is_this_block_selected and is_full_selection_at_start:
                # ✅ DESELECT this specific multi-tip selection
                clear_block(row, column)

            else:
                # ✅ STEP 3: Check if max_selected limit reached - AUTO-DESELECT OLDEST (FIFO)
                current_start_positions = self.get_start_positions()
                if len(current_start_positions) >= self.max_selected:
                    # FIFO: Auto-deselect the OLDEST starting position
                    oldest_start_row, oldest_start_col = current_start_positions[0]
                    clear_block(oldest_start_row, oldest_start_col)

                # ✅ STEP 4 & 5: Check for and Auto-clear any overlapping selections

                existing_start_rows = []
                for r in range(self.rows):
                    is_start = self.well_state[r][column] and \
                               (r == 0 or not self.well_state[r - 1][column])

                    is_valid_multi_tip = (r + self.channels <= self.rows and
                                      all((r + i, column) in self.wells_list for i in range(self.channels)))

                    if is_start and is_valid_multi_tip:
                        existing_start_rows.append(r)

                new_selection_rows = set(range(row, min(row + self.channels, self.rows)))

                for existing_start in existing_start_rows:
                    existing_rows = set(range(existing_start, min(existing_start + self.channels, self.rows)))

                    if new_selection_rows & existing_rows:
                        clear_block(existing_start, column)

                # ✅ STEP 6: Add new selection (internal state)
                for i in range(self.channels):
                    r = row + i
                    if r < self.rows:
                        self.well_state[r][column] = True
                        if (r, column) not in self.selected_queue:
                            self.selected_queue.append((r, column))

                # ✅ STEP 7: Highlight only the start row (green 'success')
                if self.buttons[row][column] is not None:
                    self.buttons[row][column].configure(bootstyle="success")

                for i in range(1, self.channels):
                    r = row + i
                    if r < self.rows and self.buttons[r][column] is not None:
                        self.buttons[r][column].configure(bootstyle="light")

                # Update confirm button text (multichannel modifies state directly)
                self.update_confirm_button_text()


        else:
            # Single-channel mode
            if self.well_state[row][column]:
                self.deactivate_well(row, column)
            else:
                self.activate_well(row, column)
        self.update_confirm_button_state()

    def toggle_row(self, row: int):
        """Toggle all wells in a given row."""
        check_var = self.row_vars[row].get()

        for c in range(self.columns):
            if (row, c) not in self.wells_list:
                continue

            if check_var:
                if not self.well_state[row][c]:
                    self.activate_well(row, c)
            else:
                if self.well_state[row][c]:
                    self.deactivate_well(row, c)

    def toggle_column(self, column: int):
        """Toggle all wells in a given column."""
        check_var = self.col_vars[column].get()

        for r in range(self.rows):
            if (r, column) not in self.wells_list:
                continue

            if check_var:
                if not self.well_state[r][column]:
                    self.activate_well(r, column)
            else:
                if self.well_state[r][column]:
                    self.deactivate_well(r, column)

    def callback_check_all(self):
        """Toggle all wells in the grid using the master checkbox."""
        check_var = self.is_check_all.get()

        for i in range(self.rows):
            self.row_vars[i].set(check_var)
            self.toggle_row(i)

        for i in range(self.columns):
            self.col_vars[i].set(check_var)

    def update_all_button_states(self):
        """(Placeholder) Update all button states from external data."""
        pass

    def on_enter_key(self, event=None):
        """Handle Enter key - only proceed if confirm button is enabled"""
        if self.allow_auto_select:
            if hasattr(self, 'button_confirm'):
                button_state = str(self.button_confirm['state'])
                if button_state != 'disabled':
                    self.callback_save()
        else:
            if hasattr(self, 'button_save'):
                button_state = str(self.button_save['state'])
                if button_state != 'disabled':
                    self.callback_save()

    def update_confirm_button_state(self):
        """Enable/disable confirm button based on selection state"""
        if not hasattr(self, 'button_save') and not hasattr(self, 'button_confirm'):
            return

        has_selection = any(any(row) for row in self.well_state)

        if self.allow_auto_select:
            # Auto-select mode: always enabled (can auto-select if empty)
            if hasattr(self, 'button_confirm'):
                self.button_confirm.config(state='normal')
        else:
            # No auto-select: only enable if there's a selection
            if hasattr(self, 'button_save'):
                if has_selection:
                    self.button_save.config(state='normal')
                else:
                    self.button_save.config(state='disabled')

    def callback_save(self):
        """Save and close - auto-select if no manual selection made"""
        has_selection = any(any(row) for row in self.well_state)

        if has_selection:
            self.auto_selected = False
        else:
            self.auto_selected = True

        self.safe_var.set(True)
        self.confirmed = True
        self.__root.destroy()

    def on_window_close(self):
        """Handle OS window close button - treat as back navigation"""
        self.back_requested = True
        self.__root.destroy()
