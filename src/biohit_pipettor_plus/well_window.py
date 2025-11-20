import ttkbootstrap as ttk
import tkinter as tk
import string
from collections import deque


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
                 max_selected: int = None, multichannel_mode: bool = False):

        #print("test")

        # --- Window setup ---
        if master:
            # Create as a dialog
            self.__root = ttk.Toplevel(master=master)
            self.__root.title(title if title else f"Select Wells from: {labware_id}")
            self.__root.transient(master)  #  Stay on top of parent
            self.__root.grab_set()  # Make modal

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
            self.__root.geometry("1200x900")  # Reasonable default size

        self.is_well_window = True

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

        if self.multichannel_mode:
            self.channels = 8
        else:
            self.max_selected = max_selected if max_selected else self.rows * self.columns

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
        self.button_save = ttk.Button(
            self.__root,
            text="✓ Confirm Selection",
            command=self.callback_save,
            bootstyle="success"
        )
        self.button_save.grid(
            column=1,
            row=self.rows + 2,
            sticky="nsew",
            columnspan=self.columns,
            padx=10,
            pady=10
        )

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

    def create_well_buttons(self):
        """Create a grid of well buttons with multichannel awareness."""
        for r in range(self.rows):
            for c in range(self.columns):
                well_name = f"{string.ascii_uppercase[r]}{c + 1}"
                well_available = (r, c) in self.wells_list

                if well_available:
                    if self.multichannel_mode:
                        # ✅ Check if valid starting position (has 8 consecutive rows below)
                        if r + 8 <= self.rows:  # Has room for 8 tips
                            # Check all 8 positions are available
                            all_available = all((r + i, c) in self.wells_list for i in range(8))
                            if all_available:
                                # ✅ VALID STARTING POSITION - make clickable
                                state = "normal"
                                style = "light"
                                command = lambda c=c, r=r: self.callback_well_button(r, c)
                            else:
                                # Some positions missing - not valid
                                state = "disabled"
                                style = "secondary"
                                command = None
                        else:
                            # ✅ Not enough room for 8 tips below - disabled
                            # But can be part of a selection from above
                            state = "disabled"
                            style = "secondary"
                            command = None
                    else:
                        # Single-channel mode - all available wells are clickable
                        state = "normal"
                        style = "light"
                        command = lambda c=c, r=r: self.callback_well_button(r, c)
                else:
                    # Well not available at all
                    state = "disabled"
                    style = "secondary"
                    command = None

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

                # ✅ ADD HOVER BINDINGS TO ALL VALID START POSITIONS
                if self.multichannel_mode and state == "normal":
                    cur_button.bind('<Enter>', lambda e, r=r, c=c: self.show_multichannel_preview(r, c))
                    cur_button.bind('<Leave>', lambda e: self.hide_multichannel_preview())
                    cur_button.configure(cursor="crosshair")

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
                row=r + 2,  # ✅ Offset by 2
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
                row=1,  # ✅ Row 1 (after info)
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

    def show_multichannel_preview(self, row: int, col: int):
        """Highlight all 8 wells that will be selected with preview colors."""
        for i in range(8):
            r = row + i
            if r < self.rows and self.buttons[r][col] is not None:
                if not self.well_state[r][col]:  # Only preview unselected wells
                    if i == 0:
                        # ✅ Start row - orange/warning outline
                        self.buttons[r][col].configure(bootstyle="warning-outline")
                    else:
                        # ✅ Other rows - lighter outline
                        self.buttons[r][col].configure(bootstyle="secondary-outline")

    def hide_multichannel_preview(self):
        """Remove preview highlighting."""
        for r in range(self.rows):
            for c in range(self.columns):
                if self.buttons[r][c] is not None and not self.well_state[r][c]:
                    # ✅ Restore to original state based on whether it's a valid start position
                    if (r, c) in self.wells_list and r + 8 <= self.rows:
                        if all((r + i, c) in self.wells_list for i in range(8)):
                            # Valid start position
                            self.buttons[r][c].configure(bootstyle="light")
                        else:
                            self.buttons[r][c].configure(bootstyle="secondary")
                    else:
                        self.buttons[r][c].configure(bootstyle="secondary")

    def callback_well_button(self, row: int, column: int):
        """Toggle a well button with multichannel awareness."""

        # Helper to update a well's UI state (assuming 'well' is the button object)
        def _update_well_ui(r, c, is_selected):
            if self.buttons[r][c] is not None:
                # Only change the color of non-start rows if the row is actually selected
                # Start rows handle their own color (success/light/secondary)
                if not is_selected and (r != row or self.multichannel_mode is False):
                    # When deselecting, restore to 'primary' (or whatever unselected color is)
                    # In multichannel mode, non-start rows are visually 'unselected'
                    self.buttons[r][c].configure(bootstyle="light")  # Assuming 'light' is the unselected background
                # For simplicity, we'll let the main logic handle the start-row color change

        if self.multichannel_mode:

            # --- Helper for clearing an 8-well block ---
            def clear_block(start_row, col):
                for i in range(8):
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
                                is_valid = (start_row, col) in self.wells_list and start_row + 8 <= self.rows and \
                                           all((start_row + j, col) in self.wells_list for j in range(8))
                                self.buttons[start_row][col].configure(bootstyle="light" if is_valid else "secondary")

            # ✅ STEP 1: Check if this is a valid starting position
            is_valid_start_pos = (row + 8 <= self.rows and
                                  all((row + i, column) in self.wells_list for i in range(8)))

            if not is_valid_start_pos:
                # Not a valid start position - ignore click
                return

            # ✅ STEP 2: Check if THIS specific start row is already selected (i.e., this column is currently selected starting at 'row')
            # We assume that in multichannel mode, a well is selected *only* if it's part of an 8-well block
            is_this_block_selected = self.well_state[row][column]
            # Also check if the whole block is actually selected (safer check)
            is_full_selection_at_start = all(
                self.well_state[row + i][column]
                for i in range(8)
                if row + i < self.rows
            )

            if is_this_block_selected and is_full_selection_at_start:
                # ✅ DESELECT this specific 8-tip selection
                clear_block(row, column)

            else:
                # ✅ STEP 3 & 4: Check for and Auto-clear any overlapping selections

                # Find the START ROW of any currently selected 8-well block in this column.
                # A well is part of a selection if self.well_state[r][c] is True.
                # A row 'r' is a start row if self.well_state[r][c] is True AND
                # self.well_state[r-1][c] is False (or r=0)

                existing_start_rows = []
                for r in range(self.rows):
                    # Is it the start of a selection?
                    is_start = self.well_state[r][column] and \
                               (r == 0 or not self.well_state[r - 1][column])

                    # Check if it's a valid 8-tip starting position
                    is_valid_8_tip = (r + 8 <= self.rows and
                                      all((r + i, column) in self.wells_list for i in range(8)))

                    if is_start and is_valid_8_tip:
                        existing_start_rows.append(r)

                # Calculate which rows the new selection would occupy
                new_selection_rows = set(range(row, min(row + 8, self.rows)))

                # Auto-clear any overlapping selections
                for existing_start in existing_start_rows:
                    existing_rows = set(range(existing_start, min(existing_start + 8, self.rows)))

                    if new_selection_rows & existing_rows:  # Overlap detected!
                        clear_block(existing_start, column)  # Use the new helper function

                # ✅ STEP 5: Add new selection (internal state)
                for i in range(8):
                    r = row + i
                    if r < self.rows:
                        self.well_state[r][column] = True
                        if (r, column) not in self.selected_queue:
                            self.selected_queue.append((r, column))

                # ✅ STEP 6: Highlight only the start row (green 'success')
                if self.buttons[row][column] is not None:
                    self.buttons[row][column].configure(bootstyle="success")

                # Update UI for the *rest* of the newly selected wells (rows +1 through +7)
                for i in range(1, 8):
                    r = row + i
                    if r < self.rows and self.buttons[r][column] is not None:
                        # You may want to set a different style here if non-start selected wells
                        # need a distinct look, e.g., 'secondary' instead of 'light'
                        self.buttons[r][column].configure(bootstyle="light")

        else:
            # Single-channel mode (unchanged)
            if self.well_state[row][column]:
                self.deactivate_well(row, column)
            else:
                self.activate_well(row, column)

    def toggle_row(self, row: int):
        """
        Toggle all wells in a given row.

        Parameters
        ----------
        row : int
            Row index to toggle.
        """
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
        """
        Toggle all wells in a given column.

        Parameters
        ----------
        column : int
            Column index to toggle.
        """
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
        """
        Toggle all wells in the grid using the master checkbox.
        """
        check_var = self.is_check_all.get()

        for i in range(self.rows):
            self.row_vars[i].set(check_var)
            self.toggle_row(i)

        for i in range(self.columns):
            self.col_vars[i].set(check_var)

    def update_all_button_states(self):
        """(Placeholder) Update all button states from external data."""
        pass

    def callback_save(self):
        """Save and close the window."""
        self.safe_var.set(True)
        self.__root.destroy()