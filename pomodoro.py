import tkinter as tk
from tkinter import ttk
import json
import os
from datetime import datetime

# ── 配置 ──
WORK_MIN = 25
SHORT_BREAK_MIN = 5
LONG_BREAK_MIN = 15
LONG_BREAK_INTERVAL = 4

THEME = {
    "bg": "#2B2B2B",
    "fg": "#FFFFFF",
    "accent": "#E74C3C",
    "accent2": "#2ECC71",
    "gray": "#555555",
    "card": "#363636",
    "font": ("Segoe UI", 10),
    "font_bold": ("Segoe UI", 10, "bold"),
    "font_large": ("Segoe UI", 48, "bold"),
    "font_medium": ("Segoe UI", 14),
}

STATES = {
    "work":        {"label": "🍅 工作中", "color": THEME["accent"]},
    "break":       {"label": "☕ 休息中", "color": THEME["accent2"]},
    "idle_work":   {"label": "🍅 就绪",   "color": THEME["gray"]},
    "idle_break":  {"label": "☕ 就绪",   "color": THEME["gray"]},
}

WIDTH, HEIGHT = 380, 520
DATA_FILE = os.path.expanduser("~/.pomodoro_stats.json")


class PomodoroApp:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("🍅 番茄钟")
        self.window.geometry(f"{WIDTH}x{HEIGHT}")
        self.window.configure(bg=THEME["bg"])
        self.window.resizable(False, False)
        self.center_window()

        self.state = "idle"
        self.mode = "work"
        self.remaining = 0
        self.total = 0
        self.running = False
        self.completed_pomodoros = 0
        self.work_count = 0
        self.timer_id = None

        self.load_stats()
        self.build_ui()
        self.window.mainloop()

    # ── 窗口 ──

    def center_window(self):
        self.window.update_idletasks()
        sw = self.window.winfo_screenwidth()
        sh = self.window.winfo_screenheight()
        x = (sw - WIDTH) // 2
        y = (sh - HEIGHT) // 2
        self.window.geometry(f"{WIDTH}x{HEIGHT}+{x}+{y}")

    # ── UI ──

    def build_ui(self):
        self.window.columnconfigure(0, weight=1)

        self.title_label = tk.Label(
            self.window, text=STATES["idle_work"]["label"],
            font=THEME["font_bold"], bg=THEME["bg"], fg=THEME["fg"]
        )
        self.title_label.pack(pady=(20, 0))

        self.canvas = tk.Canvas(
            self.window, width=260, height=260,
            bg=THEME["bg"], highlightthickness=0
        )
        self.canvas.pack(pady=(10, 0))
        cx, cy, r = 130, 130, 100
        self.canvas.create_oval(
            cx - r, cy - r, cx + r, cy + r,
            outline=THEME["gray"], width=6, tags="bg_arc"
        )
        self.canvas.create_arc(
            cx - r, cy - r, cx + r, cy + r,
            start=90, extent=0, outline="", width=6, style="arc",
            tags="progress_arc"
        )
        self.canvas.create_text(
            cx, cy - 10,
            text="25:00", font=THEME["font_large"],
            fill=THEME["fg"], tags="time_text"
        )
        self.canvas.create_text(
            cx, cy + 35,
            text="点击开始", font=THEME["font_medium"],
            fill=THEME["gray"], tags="status_text"
        )

        btn_frame = tk.Frame(self.window, bg=THEME["bg"])
        btn_frame.pack(pady=(10, 0))

        self.start_btn = self._make_button(btn_frame, "▶ 开始", self.toggle, THEME["accent2"])
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.reset_btn = self._make_button(btn_frame, "↺ 重置", self.reset, THEME["gray"])
        self.reset_btn.pack(side=tk.LEFT, padx=5)

        self.stats_label = tk.Label(
            self.window,
            text=f"今日完成: {self.completed_pomodoros} 个番茄",
            font=THEME["font"], bg=THEME["bg"], fg=THEME["gray"]
        )
        self.stats_label.pack(pady=(15, 0))

        mode_frame = tk.Frame(self.window, bg=THEME["bg"])
        mode_frame.pack(pady=(5, 0))
        for text, cmd in [("25分", "work"), ("5分", "short_break"), ("15分", "long_break")]:
            btn = tk.Button(
                mode_frame, text=text,
                font=THEME["font"], bg=THEME["card"], fg=THEME["fg"],
                relief=tk.FLAT, padx=12, pady=4, cursor="hand2",
                activebackground=THEME["gray"], activeforeground=THEME["fg"],
                command=lambda m=cmd: self.set_mode(m)
            )
            btn.pack(side=tk.LEFT, padx=4)

        self.window.bind("<space>", lambda e: self.toggle())
        self.window.bind("<r>", lambda e: self.reset())
        self.window.bind("<Escape>", lambda e: self.reset())

    def _make_button(self, parent, text, command, color):
        return tk.Button(
            parent, text=text, font=THEME["font_bold"],
            bg=color, fg=THEME["fg"],
            relief=tk.FLAT, padx=16, pady=6, cursor="hand2",
            activebackground=color, activeforeground=THEME["fg"],
            command=command
        )

    def _idle_state_key(self):
        return f"idle_{self.mode}"

    # ── 模式切换 ──

    def set_mode(self, mode):
        if self.running:
            return
        self.mode = mode
        self.total = self._mode_seconds()
        self.remaining = self.total
        self.state = "idle"
        self.update_display()

    # ── 核心逻辑 ──

    def _mode_seconds(self):
        if self.mode == "work":
            return WORK_MIN * 60
        elif self.mode == "short_break":
            return SHORT_BREAK_MIN * 60
        else:
            return LONG_BREAK_MIN * 60

    def _cancel_timer(self):
        if self.timer_id:
            self.window.after_cancel(self.timer_id)
            self.timer_id = None

    def toggle(self):
        if self.remaining <= 0 and not self.running:
            self.reset()
            return
        if self.running:
            self.pause()
        else:
            self.start()

    def start(self):
        if self.remaining <= 0:
            self.total = self._mode_seconds()
            self.remaining = self.total
        self.running = True
        self.state = self.mode
        self.start_btn.config(text="⏸ 暂停")
        self.tick()

    def pause(self):
        self.running = False
        self._cancel_timer()
        self.start_btn.config(text="▶ 继续")

    def reset(self):
        self.running = False
        self._cancel_timer()
        self.remaining = self.total
        self.state = "idle"
        self.start_btn.config(text="▶ 开始")
        self.update_display()

    def tick(self):
        if not self.running:
            return
        if self.remaining > 0:
            self.remaining -= 1
            self.update_display()
            self.timer_id = self.window.after(1000, self.tick)
        else:
            self.running = False
            self.timer_id = None
            self._on_complete()

    def _on_work_complete(self):
        self.completed_pomodoros += 1
        self.work_count += 1
        self.save_stats()
        self.stats_label.config(text=f"今日完成: {self.completed_pomodoros} 个番茄")

        if self.work_count % LONG_BREAK_INTERVAL == 0:
            self.mode = "long_break"
        else:
            self.mode = "short_break"
        self.total = self._mode_seconds()
        self.remaining = self.total
        self.state = self.mode
        self.running = True
        self.start_btn.config(text="⏸ 暂停")
        self.update_display()
        self.tick()
        self.flash_window(f"🍅 完成! 休息 {self.total // 60} 分钟")

    def _on_break_complete(self):
        self.mode = "work"
        self.total = self._mode_seconds()
        self.remaining = self.total
        self.state = "idle"
        self.start_btn.config(text="▶ 开始")
        self.update_display()
        self.flash_window("☕ 休息结束，开始工作!")

    def _on_complete(self):
        if self.mode == "work":
            self._on_work_complete()
        else:
            self._on_break_complete()

    # ── 显示 ──

    def update_display(self):
        mins = self.remaining // 60
        secs = self.remaining % 60
        self.canvas.itemconfig("time_text", text=f"{mins:02d}:{secs:02d}")

        if self.total > 0:
            extent = -360 * (1 - self.remaining / self.total)
        else:
            extent = 0

        is_idle = self.state == "idle"
        state_key = self._idle_state_key() if is_idle else self.state
        state_info = STATES.get(state_key, STATES["work"])

        self.canvas.itemconfig("progress_arc", extent=extent, outline=state_info["color"])
        self.canvas.itemconfig("time_text", fill=state_info["color"])

        label = state_info["label"]
        status = "点击开始" if is_idle else ("工作中" if self.mode == "work" else "休息中")
        self.title_label.config(text=label)
        self.canvas.itemconfig("status_text", text=status)

    def flash_window(self, msg):
        top = tk.Toplevel(self.window)
        top.title("🍅 番茄钟")
        top.geometry("300x150")
        top.configure(bg=THEME["bg"])
        top.resizable(False, False)
        x = self.window.winfo_x() + (self.window.winfo_width() - 300) // 2
        y = self.window.winfo_y() + (self.window.winfo_height() - 150) // 2
        top.geometry(f"300x150+{x}+{y}")

        tk.Label(
            top, text=msg, font=THEME["font_medium"],
            bg=THEME["bg"], fg=THEME["fg"], wraplength=260
        ).pack(expand=True)

        ttk.Button(top, text="确定", command=top.destroy).pack(pady=(0, 20))
        top.after(5000, top.destroy)

    # ── 持久化统计 ──

    @staticmethod
    def _today_str():
        return datetime.now().strftime("%Y-%m-%d")

    def load_stats(self):
        try:
            with open(DATA_FILE) as f:
                data = json.load(f)
                if data.get("date") == self._today_str():
                    self.completed_pomodoros = data.get("count", 0)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def save_stats(self):
        data = {"date": self._today_str(), "count": self.completed_pomodoros}
        try:
            with open(DATA_FILE, "w") as f:
                json.dump(data, f)
        except OSError:
            pass


if __name__ == "__main__":
    PomodoroApp()
