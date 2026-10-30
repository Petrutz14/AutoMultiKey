import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import keyboard
import mouse

# --- Custom Scrollable Container ---
class ScrollableFrame(ttk.Frame):
    def __init__(self, container, bg_color, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.canvas = tk.Canvas(self, bg=bg_color, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=bg_color)
        
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")


class MacroApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Roblox DirectInput Presser")
        self.root.geometry("600x620")
        self.root.resizable(False, False)
        
        # UI Colors
        self.bg_color = "#1e1e2e"       
        self.fg_color = "#cdd6f4"       
        self.input_bg = "#313244"       
        self.accent_color = "#89b4fa"   
        self.stop_color = "#f38ba8"     
        self.run_color = "#a6e3a1"
        self.panel_bg = "#181825"
        self.cassette_bg = "#45475a"

        self.root.configure(bg=self.bg_color)

        # States
        self.kb_running = False
        self.mouse_running = False
        self.kb_thread = None
        self.mouse_thread = None
        self.active_key = None 
        self.active_mouse_btn = None
        
        # Debounce timers so hotkeys don't double-trigger
        self.last_kb_toggle = 0.0
        self.last_m_toggle = 0.0
        
        self.sequence_commands = [] 
        self.cassettes = [] 
        
        self.common_keys = ["w", "a", "s", "d", "space", "e", "f", "r", "q", "enter", "shift", "ctrl", "tab"]
        self.f_keys = [f"F{i}" for i in range(1, 13)]

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.setup_styles()
        self.create_widgets()
        
        # The Master Router: Intercepts all keys without creating risky UI hooks
        keyboard.on_press(self.global_key_router)

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('default')
        style.configure("TNotebook", background=self.bg_color, borderwidth=0)
        style.configure("TNotebook.Tab", background=self.panel_bg, foreground=self.fg_color, padding=[20, 10], font=("Segoe UI", 10, "bold"), borderwidth=0)
        style.map("TNotebook.Tab", background=[("selected", self.input_bg)], foreground=[("selected", self.accent_color)])
        style.configure("TFrame", background=self.bg_color)
        style.configure("TCombobox", fieldbackground=self.input_bg, background=self.input_bg, foreground="black")

    def create_widgets(self):
        font_main = ("Segoe UI", 10)
        font_bold = ("Segoe UI", 10, "bold")

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill="both", padx=10, pady=10)

        # --- KEYBOARD TAB ---
        self.kb_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.kb_frame, text="⌨ Keyboard Sequencer")

        kb_top = tk.Frame(self.kb_frame, bg=self.bg_color)
        kb_top.pack(fill="x", pady=10)
        
        tk.Button(kb_top, text="+ Add Action Cassette", bg=self.accent_color, fg="black", font=font_bold, relief="flat", command=self.add_cassette).pack(side="left", padx=15)
        
        tk.Label(kb_top, text="Hotkey:", bg=self.bg_color, fg=self.fg_color, font=font_main).pack(side="left", padx=(40, 5))
        self.kb_hotkey_var = tk.StringVar(value="F9")
        kb_hk_menu = ttk.Combobox(kb_top, textvariable=self.kb_hotkey_var, values=self.f_keys, width=5, state="readonly")
        kb_hk_menu.pack(side="left")

        self.seq_container = ScrollableFrame(self.kb_frame, self.panel_bg)
        self.seq_container.pack(expand=True, fill="both", padx=15, pady=5)

        self.add_cassette()

        self.kb_status = tk.Label(self.kb_frame, text="STATUS: STOPPED", bg=self.bg_color, fg=self.stop_color, font=("Segoe UI", 12, "bold"))
        self.kb_status.pack(pady=10)

        # --- MOUSE TAB ---
        self.mouse_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.mouse_frame, text="🖱 Mouse Autoclicker")

        m_settings = tk.Frame(self.mouse_frame, bg=self.bg_color)
        m_settings.pack(pady=30)

        tk.Label(m_settings, text="Mouse Button:", bg=self.bg_color, fg=self.fg_color, font=font_main).grid(row=0, column=0, padx=10, pady=15, sticky="e")
        self.mouse_btn_var = tk.StringVar(value="left")
        btn_menu = ttk.Combobox(m_settings, textvariable=self.mouse_btn_var, values=["left", "right", "middle"], state="readonly", width=12)
        btn_menu.grid(row=0, column=1, padx=10, pady=15, sticky="w")

        tk.Label(m_settings, text="Hold duration (sec):", bg=self.bg_color, fg=self.fg_color, font=font_main).grid(row=1, column=0, padx=10, pady=15, sticky="e")
        self.m_hold_entry = tk.Entry(m_settings, width=15, bg=self.input_bg, fg=self.fg_color, insertbackground="white", relief="flat", font=font_main)
        self.m_hold_entry.insert(0, "0.0")
        self.m_hold_entry.grid(row=1, column=1, padx=10, pady=15, sticky="w")

        tk.Label(m_settings, text="Delay (sec):", bg=self.bg_color, fg=self.fg_color, font=font_main).grid(row=2, column=0, padx=10, pady=15, sticky="e")
        self.m_delay_entry = tk.Entry(m_settings, width=15, bg=self.input_bg, fg=self.fg_color, insertbackground="white", relief="flat", font=font_main)
        self.m_delay_entry.insert(0, "0.05")
        self.m_delay_entry.grid(row=2, column=1, padx=10, pady=15, sticky="w")

        mouse_ctrl = tk.Frame(self.mouse_frame, bg=self.bg_color)
        mouse_ctrl.pack(pady=10)

        tk.Label(mouse_ctrl, text="Hotkey:", bg=self.bg_color, fg=self.fg_color, font=font_main).grid(row=0, column=0, padx=5)
        self.mouse_hotkey_var = tk.StringVar(value="F10")
        m_hk_menu = ttk.Combobox(mouse_ctrl, textvariable=self.mouse_hotkey_var, values=self.f_keys, width=5, state="readonly")
        m_hk_menu.grid(row=0, column=1, padx=5)

        self.mouse_status = tk.Label(self.mouse_frame, text="STATUS: STOPPED", bg=self.bg_color, fg=self.stop_color, font=("Segoe UI", 12, "bold"))
        self.mouse_status.pack(pady=10)

        # --- GLOBAL CONTROLS ---
        global_ctrl = tk.Frame(self.root, bg=self.bg_color)
        global_ctrl.pack(pady=(0, 15))

        self.apply_btn = tk.Button(global_ctrl, text="Confirm Hotkey Selection", bg=self.accent_color, fg="#000000", font=font_bold, relief="flat", command=self.confirm_hotkeys, width=22)
        self.apply_btn.grid(row=0, column=0, padx=10)
        
        self.estop_btn = tk.Button(global_ctrl, text="EMERGENCY STOP ALL", bg=self.stop_color, fg="#000000", font=font_bold, relief="flat", command=self.emergency_stop, width=22)
        self.estop_btn.grid(row=0, column=1, padx=10)

    # --- GUI DYNAMIC BUILDER ---
    def add_cassette(self):
        font_main = ("Segoe UI", 9)
        cassette_frame = tk.Frame(self.seq_container.scrollable_frame, bg=self.cassette_bg, bd=0, padx=10, pady=10)
        cassette_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(cassette_frame, text="Key:", bg=self.cassette_bg, fg=self.fg_color, font=font_main).grid(row=0, column=0, padx=(0,5))
        key_var = tk.StringVar(value="e")
        key_cb = ttk.Combobox(cassette_frame, textvariable=key_var, values=self.common_keys, width=8)
        key_cb.grid(row=0, column=1, padx=5)

        tk.Label(cassette_frame, text="Hold:", bg=self.cassette_bg, fg=self.fg_color, font=font_main).grid(row=0, column=2, padx=(15,5))
        hold_entry = tk.Entry(cassette_frame, width=8, bg=self.input_bg, fg=self.fg_color, insertbackground="white", relief="flat", justify="center")
        hold_entry.insert(0, "0.2")
        hold_entry.grid(row=0, column=3, padx=5)

        tk.Label(cassette_frame, text="Delay:", bg=self.cassette_bg, fg=self.fg_color, font=font_main).grid(row=0, column=4, padx=(15,5))
        delay_entry = tk.Entry(cassette_frame, width=8, bg=self.input_bg, fg=self.fg_color, insertbackground="white", relief="flat", justify="center")
        delay_entry.insert(0, "0.5")
        delay_entry.grid(row=0, column=5, padx=5)

        del_btn = tk.Button(cassette_frame, text="X", bg=self.stop_color, fg="black", font=("Arial", 8, "bold"), relief="flat", command=lambda f=cassette_frame: self.remove_cassette(f))
        del_btn.grid(row=0, column=6, padx=(15, 0))

        self.cassettes.append({'frame': cassette_frame, 'key_var': key_var, 'hold_entry': hold_entry, 'delay_entry': delay_entry})

    def remove_cassette(self, frame_to_remove):
        frame_to_remove.destroy()
        self.cassettes = [c for c in self.cassettes if c['frame'] != frame_to_remove]

    # --- BULLETPROOF ENGINE ---
    def safe_float(self, string_val, default=0.0):
        try:
            return max(0.0, float(string_val.strip()))
        except ValueError:
            return default

    def smart_sleep(self, duration, running_flag_name):
        """Micro-sleep yields CPU to OS to prevent lag, ensuring hardware inputs execute smoothly."""
        if duration <= 0: return
        end_time = time.perf_counter() + duration
        while getattr(self, running_flag_name) and time.perf_counter() < end_time:
            remaining = end_time - time.perf_counter()
            if remaining > 0.02: time.sleep(0.01)       
            else: time.sleep(0.001)

    # ==============================================================
    # THE MASTER ROUTER: Safe, passive listening that ignores simulated inputs
    # ==============================================================
    def global_key_router(self, event):
        # We only care about key presses, not releases
        if event.event_type != keyboard.KEY_DOWN: 
            return
            
        key_pressed = str(event.name).lower()
        target_kb = self.kb_hotkey_var.get().lower()
        target_mouse = self.mouse_hotkey_var.get().lower()
        
        now = time.time()
        
        if key_pressed == target_kb:
            if now - getattr(self, 'last_kb_toggle', 0) > 0.3:
                self.last_kb_toggle = now
                self.root.after(0, self.safe_kb_toggle)
                
        elif key_pressed == target_mouse:
            if now - getattr(self, 'last_m_toggle', 0) > 0.3:
                self.last_m_toggle = now
                self.root.after(0, self.safe_mouse_toggle)

    def confirm_hotkeys(self):
        self.root.focus_set() 
        kb = self.kb_hotkey_var.get().upper()
        m = self.mouse_hotkey_var.get().upper()
        messagebox.showinfo("Success", f"Hotkeys Active!\n\nKeyboard Trigger: {kb}\nMouse Trigger: {m}\n\nYou do not need to pause to change these, they update instantly.", parent=self.root)

    def emergency_stop(self):
        self.kb_running = False
        self.mouse_running = False
        self.kb_status.config(text="STATUS: STOPPED", fg=self.stop_color)
        self.mouse_status.config(text="STATUS: STOPPED", fg=self.stop_color)
        
        # Force hardware release if macro is stopped midway
        if self.active_key:
            try: keyboard.release(self.active_key)
            except: pass
            self.active_key = None
        if self.active_mouse_btn:
            try: mouse.release(button=self.active_mouse_btn)
            except: pass
            self.active_mouse_btn = None


    # --- HARDWARE-LEVEL KEYBOARD THREADING ---
    def parse_cassettes(self):
        self.sequence_commands = []
        if len(self.cassettes) == 0: return False

        for cass in self.cassettes:
            key = cass['key_var'].get().strip().lower()
            if not key: continue
            
            hold = self.safe_float(cass['hold_entry'].get(), default=0.1)
            delay = self.safe_float(cass['delay_entry'].get(), default=0.5)
            
            if key == self.kb_hotkey_var.get().lower():
                messagebox.showwarning("Warning", f"You cannot set the macro to press its own Hotkey ({key.upper()}).", parent=self.root)
                continue
                
            self.sequence_commands.append((key, hold, delay))
        return len(self.sequence_commands) > 0

    def safe_kb_toggle(self):
        if self.kb_running:
            self.kb_running = False
            self.kb_status.config(text="STATUS: STOPPED", fg=self.stop_color)
        else:
            if not self.parse_cassettes(): return
            self.kb_running = True
            self.kb_status.config(text="STATUS: RUNNING", fg=self.run_color)
            self.kb_thread = threading.Thread(target=self.kb_loop, daemon=True)
            self.kb_thread.start()

    def kb_loop(self):
        while self.kb_running:
            for key, hold_time, delay_time in self.sequence_commands:
                if not self.kb_running: break
                
                try:
                    self.active_key = key
                    # Inject hardware scan code via keyboard.press
                    keyboard.press(self.active_key)
                    try:
                        self.smart_sleep(hold_time, "kb_running")
                    finally:
                        # Guaranteed release even if lag occurs
                        keyboard.release(self.active_key)
                        self.active_key = None

                    if not self.kb_running: break
                    self.smart_sleep(delay_time, "kb_running")
                        
                except Exception:
                    self.kb_running = False
                    self.root.after(0, lambda k=key: self.kb_status.config(text=f"STATUS: ERROR ({k})", fg=self.stop_color))
                    break

        if self.active_key:
            try: keyboard.release(self.active_key)
            except: pass
            self.active_key = None


    # --- HARDWARE-LEVEL MOUSE THREADING ---
    def safe_mouse_toggle(self):
        if self.mouse_running:
            self.mouse_running = False
            self.mouse_status.config(text="STATUS: STOPPED", fg=self.stop_color)
        else:
            self.m_hold = self.safe_float(self.m_hold_entry.get(), default=0.0)
            self.m_delay = self.safe_float(self.m_delay_entry.get(), default=0.05)
            self.m_btn = self.mouse_btn_var.get()
            
            self.mouse_running = True
            self.mouse_status.config(text="STATUS: RUNNING", fg=self.run_color)
            self.mouse_thread = threading.Thread(target=self.mouse_loop, daemon=True)
            self.mouse_thread.start()

    def mouse_loop(self):
        while self.mouse_running:
            try:
                self.active_mouse_btn = self.m_btn
                if self.m_hold <= 0:
                    mouse.click(button=self.active_mouse_btn)
                else:
                    mouse.press(button=self.active_mouse_btn)
                    try:
                        self.smart_sleep(self.m_hold, "mouse_running")
                    finally:
                        mouse.release(button=self.active_mouse_btn)
                
                self.active_mouse_btn = None
                
                if not self.mouse_running: break
                self.smart_sleep(self.m_delay, "mouse_running")

            except Exception:
                self.mouse_running = False
                break
        
        if self.active_mouse_btn:
            try: mouse.release(button=self.active_mouse_btn)
            except: pass
            self.active_mouse_btn = None

    def on_closing(self):
        self.emergency_stop()
        try: keyboard.unhook_all()
        except: pass
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = MacroApp(root)
    root.mainloop()
