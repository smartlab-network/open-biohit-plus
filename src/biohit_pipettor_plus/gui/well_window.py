import ttkbootstrap as ttk
import string

class WellWindow:
    """
    Used inside of Gui. Creates a Window of multiple Wells, depending on row, columns. Works with multiple Labware classes
    Used to set specific well settings. Each Well is represented as a Button, which can be toggled to "activate" the Well.
    After saving a list of tuples, of 2 integers which represent the Wells inside the Labware Grid.
    """
    def __init__(self, rows: int, columns: int, labware_id: str, title: str = "", master: ttk.Window = None,
                 wells_list: list[tuple[int, int]] = None):

        if master:
            self.__root = ttk.Toplevel(master = master, title= title)
        else:
            self.__root = ttk.Window(title = f"Select Wells from Labware: {labware_id}", themename="vapor")

        self.__root.geometry("1600x1200")
        self.is_well_window = True

        self.rows = rows
        self.columns = columns
        self.plate_data = None
        self.wells_list = wells_list

        self.safe_var = ttk.BooleanVar(value = False)

        #list of all generric Buttoons
        self.buttons: list[list[ttk.Button]] |list[list[None]] = [[None for _ in range(self.columns)] for _ in range(self.rows)]

        #Each Well can either be True or False
        self.well_state = [[False for _ in range(self.columns)] for _ in range(self.rows)]

        self.row_vars = [ttk.BooleanVar() for _ in range(self.rows)]
        self.col_vars = [ttk.BooleanVar() for _ in range(self.columns)]

        self.button_save = ttk.Button(self.__root, text="Save", command = self.callback_save)
        self.button_save.grid(column = 1, row = self.rows + 1, sticky = "nsew", columnspan = self.columns)

        self.is_check_all = ttk.BooleanVar()
        self.checkbutton_all = ttk.Checkbutton(self.__root, command = self.callback_check_all, variable = self.is_check_all)
        self.checkbutton_all.grid(row = 0, column = 0, sticky = "ns")

        self.set_grid()
        self.create_well_buttons()
        self.create_check_boxes()

        if self.wells_list:
            self.update_all_button_states()

    def get_root(self):
        return self.__root

    def set_grid(self):
        """
        sets the tkinter grid settings
        """
        for i in range(self.rows + 2):
            self.__root.rowconfigure(i, weight=1)

        for i in range(self.columns + 1):
            self.__root.columnconfigure(i, weight=1)

    def show_well_window(self):
        """
        """
        if self.is_well_window:
            self.__root.withdraw()
            self.is_well_window = False

        else:
            self.__root.deiconify()
            self.is_well_window = True

    def create_well_buttons(self):
        """
        Creates self.rows * self.columns buttons which represent the Wells
        """
        for r in range(self.rows):
            for c in range(self.columns):
                cur_button =  ttk.Button(self.__root,
                                         text = f"{string.ascii_uppercase[r]}{c+1}",
                                         command= lambda c=c, r=r: self.callback_well_button(row = r, column= c),
                                         style = "light")
                cur_button.grid(row = r+1, column = c+1, sticky='nsew', ipadx=20, ipady=10)
                print(r,c)
                self.buttons[r][c] = cur_button

    def create_check_boxes(self):
        """
        creates one check box for each column and one for each row, to make toggeling multiple Wells easier.
        """
        for r in range(self.rows):
            cur_check = ttk.Checkbutton(self.__root,
                                        command=lambda r=r: self.toggle_row(r),
                                        variable=self.row_vars[r])

            cur_check.grid(row = r+1, column = 0, sticky='ns')


        for c in range(self.columns):
            curr_check = ttk.Checkbutton(self.__root,
                                        command = lambda c=c: self.toggle_column(c),
                                        variable=self.col_vars[c])

            curr_check.grid(row = 0, column = c + 1, sticky='ns', ipady = 10)

    def callback_well_button(self, row: int, column: int):
        """
        Callback for each well Button. Params are stored in the ttk.Button variables with lambda functions.
        Changes the Well state in the list, for given row, column.
        And updates the Button Style.

        Parameters
        ----------
        row
        column
        """
        well_state = not self.well_state[row][column]
        self.well_state[row][column] = well_state

        if well_state:
            style = "success"

        else:
            style = "light"

        self.buttons[row][column].configure(bootstyle = style)

    def toggle_row(self, row: int):
        """
        Callback For Each row Checkbutton, stores param with functions as a lambda func.
        Loops through every column, for given row and calls toggles each Well.

        Parameters
        ----------
        row
        """
        #update vor checkvars and check boxes
        if self.row_vars[row].get():
            check_var = True
            style = "success"
        else:
            check_var = False
            style = "light"

        for c in range(self.columns):
            self.well_state[row][c] = check_var
            self.buttons[row][c].configure(bootstyle = style)
            #update db

    def toggle_column(self, column: int):
        """
        Callback For Each column Checkbutton, stores param with functions as a lambda func.
        Loops through every column, for given row and calls toggles each Well.

        Parameters
        ----------
        column
        """
        if self.col_vars[column].get():
            check_var = True
            style = "success"
        else:
            check_var = False
            style = "light"

        for r in range(self.rows):
            self.well_state[r][column] = check_var
            self.buttons[r][column].configure(bootstyle=style)


    def callback_check_all(self):
        """
        Calls every toggle_column und call_row

        Returns
        -------

        """
        if self.is_check_all.get():
            check_var = True
        else:
            check_var = False

        for i in range(self.rows):
            self.row_vars[i].set(check_var)
            self.toggle_row(i)

        for i in range(self.columns):
            self.col_vars[i].set(check_var)

    def update_all_button_states(self):
        print("test")

    def update_single_button_state(self):
        pass

    def define_callback(self):
        pass

    def callback_save(self):
        self.safe_var.set(True)
        self.show_well_window()