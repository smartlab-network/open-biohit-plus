
import ttkbootstrap as ttk

class CollapsibleFrame(ttk.Frame):
    """A frame that can be collapsed/expanded by clicking on its title."""
    def __init__(self, parent, text, **kw):
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
        self.content_frame.pack_forget()  # start collapsed

        # Bind click
        self.title_frame.bind("<Button-1>", self.toggle)
        self.toggle_btn.bind("<Button-1>", self.toggle)
        self.title_lbl.bind("<Button-1>", self.toggle)

        self.is_expanded = False

    def toggle(self, event=None):
        if self.is_expanded:
            self.content_frame.pack_forget()
            self.toggle_btn.config(text="▶")
        else:
            self.content_frame.pack(fill="both", expand=True)
            self.toggle_btn.config(text="▼")
        self.is_expanded = not self.is_expanded