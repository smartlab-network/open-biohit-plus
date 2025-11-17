import ttkbootstrap as ttk
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
    master : ttk.Window, optional
        Parent window.
    wells_list : list[tuple[int, int]], optional
        List of (row, column) tuples for wells that contain culture.
        Wells not in this list are disabled.
    max_selected : int, optional
        Maximum number of simultaneously selected wells.
    """

    def __init__(self, rows: int, columns: int, labware_id: str, title: str = "",
                 master: ttk.Window = None, wells_list: list[tuple[int, int]] = None,
                 max_selected: int = None):
        print("test")
        # --- Window setup ---
        if master:
            self.__root = ttk.Toplevel(master=master, title=title)
        else:
            self.__root = ttk.Window(title=f"Select Wells from Labware: {labware_id}",
                                     themename="vapor")

        self.__root.geometry("1600x1200")
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
        self.button_save = ttk.Button(self.__root, text="Save", command=self.callback_save)
        self.button_save.grid(column=1, row=self.rows + 1, sticky="nsew", columnspan=self.columns)

        self.checkbutton_all = ttk.Checkbutton(
            self.__root,
            command=self.callback_check_all,
            variable=self.is_check_all
        )
        self.checkbutton_all.grid(row=0, column=0, sticky="ns")


        self.set_grid()
        self.create_well_buttons()
        self.create_check_boxes()

        if self.wells_list:
            self.update_all_button_states()

    def set_grid(self):
        """Configure Tkinter grid layout for the window."""
        for i in range(self.rows + 2):
            self.__root.rowconfigure(i, weight=1)
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
        """
        Create a grid of well buttons.

        Wells not in `wells_list` are disabled and styled differently.
        """
        for r in range(self.rows):
            for c in range(self.columns):
                well_name = f"{string.ascii_uppercase[r]}{c + 1}"

                if (r, c) in self.wells_list:
                    # Active well
                    state = "normal"
                    style = "light"
                    command = lambda c=c, r=r: self.callback_well_button(r, c)
                else:
                    # Disabled well
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
                cur_button.grid(row=r + 1, column=c + 1, sticky='nsew', ipadx=20, ipady=10)
                self.buttons[r][c] = cur_button

    def create_check_boxes(self):
        """Create row and column checkboxes for easier multi-selection."""
        for r in range(self.rows):
            cur_check = ttk.Checkbutton(
                self.__root,
                command=lambda r=r: self.toggle_row(r),
                variable=self.row_vars[r]
            )
            cur_check.grid(row=r + 1, column=0, sticky='ns')

        for c in range(self.columns):
            curr_check = ttk.Checkbutton(
                self.__root,
                command=lambda c=c: self.toggle_column(c),
                variable=self.col_vars[c]
            )
            curr_check.grid(row=0, column=c + 1, sticky='ns', ipady=10)


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

    def callback_well_button(self, row: int, column: int):
        """
        Toggle a single well button.

        Parameters
        ----------
        row : int
            Row index of the well.
        column : int
            Column index of the well.
        """
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
