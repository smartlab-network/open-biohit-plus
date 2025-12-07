
import ttkbootstrap as ttk
import tkinter as tk

class ExecutionControlOverlay:
    """Modal overlay that blocks all GUI interaction except Pause/Abort"""

    def __init__(self, parent_window, pipettor):
        self.pipettor = pipettor

        # Create toplevel window
        self.overlay = tk.Toplevel(parent_window)
        self.overlay.title("Operation in Progress")

        # Make it modal (blocks parent)
        self.overlay.transient(parent_window)
        self.overlay.grab_set()

        # Center on parent
        parent_window.update_idletasks()
        x = parent_window.winfo_x() + (parent_window.winfo_width() // 2) - 150
        y = parent_window.winfo_y() + (parent_window.winfo_height() // 2) - 100
        self.overlay.geometry(f"400x200+{x}+{y}")

        # Prevent closing
        self.overlay.protocol("WM_DELETE_WINDOW", lambda: None)
        self.overlay.attributes('-topmost', True)

        self.create_ui()

    def create_ui(self):
        main_frame = ttk.Frame(self.overlay, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Status
        self.status_label = ttk.Label(
            main_frame,
            text="⚙ OPERATION IN PROGRESS",
            font=('Arial', 14, 'bold'),
            foreground='orange'
        )
        self.status_label.pack(pady=(0, 15))

        # Progress
        self.progress_label = ttk.Label(
            main_frame,
            text="",
            font=('Arial', 10),
            foreground='gray'
        )
        self.progress_label.pack(pady=(0, 15))

        ttk.Separator(main_frame, orient='horizontal').pack(fill=tk.X, pady=10)

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)

        self.pause_button = ttk.Button(
            button_frame,
            text="⏸ Pause",
            command=self.on_pause_clicked,
            bootstyle="warning"
        )
        self.pause_button.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        self.abort_button = ttk.Button(
            button_frame,
            text="🛑 Abort & Home",
            command=self.on_abort_clicked,
            bootstyle="danger"
        )
        self.abort_button.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

    def on_pause_clicked(self):
        if self.pipettor.pause_requested:
            self.pipettor.pause_requested = False
            self.pause_button.config(text="⏸ Pause", bootstyle="warning")
            self.status_label.config(text="⚙ OPERATION IN PROGRESS", foreground='orange')
        else:
            self.pipettor.pause_requested = True
            self.pause_button.config(text="▶ Resume", bootstyle="success")
            self.status_label.config(text="⏸ PAUSED", foreground='blue')

    def on_abort_clicked(self):
        self.pipettor.abort_requested = True
        self.abort_button.config(state='disabled', text="Aborting...")

    def update_progress(self, message):
        self.progress_label.config(text=message)

    def close(self):
        self.overlay.grab_release()
        self.overlay.destroy()