"""
Pomodoro Timer — Modern Rounded UI (Final)

Place your tomato image at TOMATO_PATH or change the path variable.
Dependencies: Pillow
Run: python main.py
"""

import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import math
import time
import platform
import threading
import os

# ---------------- Configuration ----------------
TOMATO_PATH = "assets/tomato.png"

# Default durations (minutes)
WORK_MIN_DEFAULT = 25
SHORT_BREAK_MIN_DEFAULT = 5
LONG_BREAK_MIN_DEFAULT = 20

# Animation config
PULSE_MIN = 0.985
PULSE_MAX = 1.045
PULSE_SPEED_MS = 60  # smaller = faster pulse

# ---------------- Globals ----------------
WORK_MIN = WORK_MIN_DEFAULT
SHORT_BREAK_MIN = SHORT_BREAK_MIN_DEFAULT
LONG_BREAK_MIN = LONG_BREAK_MIN_DEFAULT

reps = 0
timer_job = None
paused = False
remaining_seconds = 0
current_session_total = 0
is_running = False

# Stats
work_sessions_completed = 0
break_sessions_completed = 0
total_focus_seconds = 0

# ---------------- Themed colors (modern rounded) ----------------
BG_DARK = "#0f1115"
BG_LIGHT = "#f6f6ef"
CARD_DARK = "#15171b"
CARD_LIGHT = "#ffffff"
ACCENT = "#00d28a"
BUTTON_DARK = "#1f2628"
BUTTON_LIGHT = "#e6eef0"
TEXT_DARK = "#e6eef0"
TEXT_LIGHT = "#0b0b0b"
ARC_ACCENT = "#00d28a"
ERR_COLOR = "#ff6b6b"
OK_COLOR = "#00d28a"

# Button styling constants
BTN_WIDTH = 12
BTN_FONT = ("Segoe UI", 11, "bold")
ENTRY_FONT = ("Segoe UI", 10)

# ---------------- Utility: sound ----------------
def play_alert():
    """Play a short multi-tone alert. Cross-platform fallback."""
    try:
        if platform.system() == "Windows":
            import winsound
            winsound.Beep(900, 220)
            winsound.Beep(1200, 180)
            winsound.Beep(1500, 120)
        else:
            for _ in range(3):
                print('\a', end='', flush=True)
                time.sleep(0.18)
    except Exception:
        try:
            root.bell()
        except Exception:
            pass

# ---------------- Timer helpers ----------------
def seconds_to_mmss(s):
    m = s // 60
    sec = s % 60
    return f"{m:02d}:{sec:02d}"

def finalize_session_stats(session, total_seconds):
    global work_sessions_completed, break_sessions_completed, total_focus_seconds
    if session == "Work":
        work_sessions_completed += 1
        total_focus_seconds += total_seconds
        animate_stat_increment(work_count_label)
    else:
        break_sessions_completed += 1
        animate_stat_increment(break_count_label)
    update_stats_labels()

# ---------------- Stats UI helpers ----------------
def update_stats_labels():
    work_count_label.config(text=f"Work: {work_sessions_completed}")
    break_count_label.config(text=f"Breaks: {break_sessions_completed}")
    focus_label.config(text=f"Focus min: {total_focus_seconds // 60}")

def animate_stat_increment(label):
    # small bounce animation
    def bounce(step=0):
        if step > 6:
            label.config(font=("Segoe UI", 10))
            return
        size = 10 + (2 if step % 2 == 0 else 0)
        label.config(font=("Segoe UI", size, "bold"))
        root.after(80, bounce, step + 1)
    bounce()

# ---------------- Progress arc ----------------
ARC_WIDTH = 10
arc_id = None

def update_progress_arc(progress_fraction):
    global arc_id
    if arc_id:
        canvas.delete(arc_id)
        arc_id = None
    if progress_fraction <= 0:
        return
    start_angle = -90
    extent = int(360 * progress_fraction)
    bbox = (30, 25, 320, 305)  # tuned for tomato placement
    arc_id = canvas.create_arc(bbox, start=start_angle, extent=extent,
                               style="arc", width=ARC_WIDTH, outline=ARC_ACCENT)

# ---------------- Pulse animation ----------------
pulse_scale = 1.0
pulse_dir = 1

def pulse_step():
    global pulse_scale, pulse_dir
    step = 0.007
    pulse_scale += step * pulse_dir
    if pulse_scale > PULSE_MAX:
        pulse_scale = PULSE_MAX
        pulse_dir = -1
    elif pulse_scale < PULSE_MIN:
        pulse_scale = PULSE_MIN
        pulse_dir = 1
    try:
        w = int(tomato_orig.width * pulse_scale)
        h = int(tomato_orig.height * pulse_scale)
        resized = tomato_orig.resize((w, h), Image.LANCZOS)
        tkimg = ImageTk.PhotoImage(resized)
        canvas.itemconfig(tomato_image_id, image=tkimg)
        canvas.image_ref = tkimg
        # position timer a touch upward for visual center
        canvas.coords(timer_text, 175, 175)
    except Exception:
        pass
    if is_running and not paused:
        root.after(PULSE_SPEED_MS, pulse_step)
    else:
        # restore to normal
        if abs(pulse_scale - 1.0) > 0.002:
            pulse_scale += (1.0 - pulse_scale) * 0.22
            try:
                w = int(tomato_orig.width * pulse_scale)
                h = int(tomato_orig.height * pulse_scale)
                resized = tomato_orig.resize((w, h), Image.LANCZOS)
                tkimg = ImageTk.PhotoImage(resized)
                canvas.itemconfig(tomato_image_id, image=tkimg)
                canvas.image_ref = tkimg
                canvas.coords(timer_text, 175, 175)
            except Exception:
                pass
            root.after(80, pulse_step)

# ---------------- Core timer functions ----------------
def start_timer():
    global reps, is_running, paused, remaining_seconds, current_session_total
    if is_running and not paused:
        return
    if not is_running:
        reps += 1
    paused = False
    is_running = True
    session_type = ""
    if reps % 8 == 0:
        remaining_seconds = LONG_BREAK_MIN * 60
        session_type = "Long Break"
    elif reps % 2 == 0:
        remaining_seconds = SHORT_BREAK_MIN * 60
        session_type = "Break"
    else:
        remaining_seconds = WORK_MIN * 60
        session_type = "Work"
    # set globals properly
    globals()['remaining_seconds'] = remaining_seconds
    globals()['current_session_total'] = remaining_seconds
    title_label.config(text=session_type)
    pause_button.config(text="Pause", bg=BTN_ACTIVE)
    run_countdown()
    # start pulse
    root.after(80, pulse_step)

def pause_resume_timer():
    global paused
    if not is_running:
        return
    paused = not paused
    if paused:
        pause_button.config(text="Resume", bg=BTN_PAUSE)
    else:
        pause_button.config(text="Pause", bg=BTN_ACTIVE)
        run_countdown()
        root.after(80, pulse_step)

def reset_timer():
    global reps, is_running, paused, remaining_seconds, timer_job, current_session_total
    if timer_job:
        try:
            root.after_cancel(timer_job)
        except Exception:
            pass
    reps = 0
    paused = False
    is_running = False
    remaining_seconds = 0
    current_session_total = 0
    title_label.config(text="Timer")
    canvas.itemconfig(timer_text, text="00:00")
    update_progress_arc(0)
    pause_button.config(text="Pause", bg=BTN_ACTIVE)

def run_countdown():
    global remaining_seconds, timer_job, paused, is_running
    if paused or not is_running:
        return
    session = title_label.cget("text")
    total = WORK_MIN * 60 if session == "Work" else SHORT_BREAK_MIN * 60 if session == "Break" else LONG_BREAK_MIN * 60
    if total <= 0:
        total = max(1, globals().get('current_session_total', 1))
    # display
    canvas.itemconfig(timer_text, text=seconds_to_mmss(remaining_seconds))
    update_progress_arc(1 - (remaining_seconds / total))
    if remaining_seconds > 0:
        remaining_seconds -= 1
        timer_job = root.after(1000, run_countdown)
    else:
        # finalize stats
        finalize_session_stats(session, total)
        # play sound
        threading.Thread(target=play_alert, daemon=True).start()
        is_running = False
        # small delay and auto start next session
        root.after(900, start_timer)

# ---------------- Apply custom times ----------------
def apply_custom():
    global WORK_MIN, SHORT_BREAK_MIN, LONG_BREAK_MIN
    try:
        w = int(work_var.get())
        b = int(break_var.get())
        l = int(long_var.get())
        if w <= 0 or b <= 0 or l <= 0:
            raise ValueError
        WORK_MIN, SHORT_BREAK_MIN, LONG_BREAK_MIN = w, b, l
        status_label.config(text="Custom times applied", fg=OK_COLOR)
    except Exception:
        status_label.config(text="Invalid values — enter positive integers", fg=ERR_COLOR)
    root.after(2500, lambda: status_label.config(text=""))

# ---------------- Button hover helpers ----------------
def on_enter(e):
    e.widget.config(bg=BTN_HOVER)

def on_leave(e):
    # restore depending on which theme currently applied
    e.widget.config(bg=BTN_ACTIVE)

# ---------------- Theme apply (Modern Rounded) ----------------
def apply_theme(is_dark=True):
    # colors
    if is_dark:
        root.config(bg=BG_DARK)
        title_label.config(bg=BG_DARK, fg=ACCENT)
        canvas.config(bg=BG_DARK)
        status_label.config(bg=BG_DARK)
        stats_frame.config(bg=BG_DARK)
        controls_frame.config(bg=BG_DARK)
        settings_frame.config(bg=BG_DARK)
        for lbl in [work_label, break_label, long_label]:
            lbl.config(bg=BG_DARK, fg=TEXT_DARK)
        for ent in [work_entry, break_entry_widget, long_entry_widget]:
            ent.config(bg=CARD_DARK, fg=TEXT_DARK, insertbackground=TEXT_DARK)
        for btn in [start_btn, pause_button, reset_btn, apply_btn, theme_btn]:
            btn.config(bg=BTN_ACTIVE, fg=TEXT_DARK, activebackground=BTN_HOVER)
    else:
        root.config(bg=BG_LIGHT)
        title_label.config(bg=BG_LIGHT, fg="#2b7a3a")
        canvas.config(bg=BG_LIGHT)
        status_label.config(bg=BG_LIGHT)
        stats_frame.config(bg=BG_LIGHT)
        controls_frame.config(bg=BG_LIGHT)
        settings_frame.config(bg=BG_LIGHT)
        for lbl in [work_label, break_label, long_label]:
            lbl.config(bg=BG_LIGHT, fg=TEXT_LIGHT)
        for ent in [work_entry, break_entry_widget, long_entry_widget]:
            ent.config(bg=CARD_LIGHT, fg=TEXT_LIGHT, insertbackground=TEXT_LIGHT)
        for btn in [start_btn, pause_button, reset_btn, apply_btn, theme_btn]:
            btn.config(bg=BTN_LIGHT, fg=TEXT_LIGHT, activebackground="#d6eae1")

# ---------------- Build UI ----------------
root = tk.Tk()
root.title("Pomodoro — Modern UI")
root.resizable(False, False)
root.geometry("")  # let it size

# Button color variables set once for theme usage
BTN_ACTIVE = "#2f8f6a"   # green active
BTN_HOVER = "#47b78f"
BTN_PAUSE = "#b84b4b"
BTN_LIGHT = BUTTON_LIGHT
# Arc accent color set earlier as ARC_ACCENT

# Title
title_label = tk.Label(root, text="Timer", font=("Segoe UI", 26, "bold"))
title_label.grid(column=1, row=0, pady=(8, 4))

# Canvas
canvas = tk.Canvas(root, width=350, height=320, bg=BG_DARK, highlightthickness=0)
canvas.grid(column=1, row=1, padx=12, pady=6)

# Load tomato image and place exactly centered
try:
    tomato_orig = Image.open(TOMATO_PATH).convert("RGBA")
    # Resize to desired display size (260x260)
    tomato_orig = tomato_orig.resize((260, 260), Image.LANCZOS)
    tomato_tk = ImageTk.PhotoImage(tomato_orig)
    tomato_image_id = canvas.create_image(175, 150, image=tomato_tk)
    canvas.image_ref = tomato_tk
except Exception:
    tomato_orig = None
    tomato_image_id = canvas.create_text(175, 150, text="POMODORO", font=("Segoe UI", 24), fill=TEXT_DARK)

# Timer text slightly up inside tomato
timer_text = canvas.create_text(175, 200, text="00:00", fill=TEXT_DARK, font=("Courier", 28, "bold"))

# Controls frame (buttons)
controls_frame = tk.Frame(root, bg=BG_DARK)
controls_frame.grid(column=1, row=2, pady=(12, 6))

start_btn = tk.Button(controls_frame, text="Start", width=BTN_WIDTH, font=BTN_FONT, bd=0, command=start_timer)
start_btn.grid(column=0, row=0, padx=8)

pause_button = tk.Button(controls_frame, text="Pause", width=BTN_WIDTH, font=BTN_FONT, bd=0, command=pause_resume_timer)
pause_button.grid(column=1, row=0, padx=8)

reset_btn = tk.Button(controls_frame, text="Reset", width=BTN_WIDTH, font=BTN_FONT, bd=0, command=reset_timer)
reset_btn.grid(column=2, row=0, padx=8)

# Hover bindings
for b in [start_btn, pause_button, reset_btn]:
    b.bind("<Enter>", on_enter)
    b.bind("<Leave>", on_leave)

theme_btn = tk.Button(root, text="Light Mode", width=12, font=BTN_FONT, bd=0)
theme_btn.grid(column=1, row=3, pady=(2, 8))

def theme_toggle_action():
    # toggle theme and update appearance
    current_bg = root.cget("bg")
    if current_bg == BG_DARK:
        apply_theme(False)
        theme_btn.config(text="Dark Mode")
    else:
        apply_theme(True)
        theme_btn.config(text="Light Mode")
theme_btn.config(command=theme_toggle_action)

# Settings frame (custom times)
settings_frame = tk.Frame(root, bg=BG_DARK)
settings_frame.grid(column=1, row=4, pady=(6, 6))

work_label = tk.Label(settings_frame, text="Work (min):", font=ENTRY_FONT)
work_label.grid(row=0, column=0, padx=4)
work_var = tk.StringVar(value=str(WORK_MIN))
work_entry = tk.Entry(settings_frame, textvariable=work_var, width=6, justify="center", font=ENTRY_FONT)
work_entry.grid(row=0, column=1, padx=4)

break_label = tk.Label(settings_frame, text="Break (min):", font=ENTRY_FONT)
break_label.grid(row=0, column=2, padx=4)
break_var = tk.StringVar(value=str(SHORT_BREAK_MIN))
break_entry_widget = tk.Entry(settings_frame, textvariable=break_var, width=6, justify="center", font=ENTRY_FONT)
break_entry_widget.grid(row=0, column=3, padx=4)

long_label = tk.Label(settings_frame, text="Long (min):", font=ENTRY_FONT)
long_label.grid(row=0, column=4, padx=4)
long_var = tk.StringVar(value=str(LONG_BREAK_MIN))
long_entry_widget = tk.Entry(settings_frame, textvariable=long_var, width=6, justify="center", font=ENTRY_FONT)
long_entry_widget.grid(row=0, column=5, padx=4)

apply_btn = tk.Button(settings_frame, text="Apply", width=8, font=("Segoe UI", 10, "bold"), bd=0, command=apply_custom)
apply_btn.grid(row=0, column=6, padx=(10,0))
apply_btn.bind("<Enter>", on_enter); apply_btn.bind("<Leave>", on_leave)

status_label = tk.Label(root, text="", font=("Segoe UI", 10), bg=BG_DARK, fg=OK_COLOR)
status_label.grid(column=1, row=5)

# Stats
stats_frame = tk.Frame(root, bg=BG_DARK)
stats_frame.grid(column=1, row=6, pady=(8, 6))
work_count_label = tk.Label(stats_frame, text=f"Work: {work_sessions_completed}", font=("Segoe UI", 10), bg=BG_DARK, fg=TEXT_DARK)
work_count_label.grid(row=0, column=0, padx=8)
break_count_label = tk.Label(stats_frame, text=f"Breaks: {break_sessions_completed}", font=("Segoe UI", 10), bg=BG_DARK, fg=TEXT_DARK)
break_count_label.grid(row=0, column=1, padx=8)
focus_label = tk.Label(stats_frame, text=f"Focus min: {total_focus_seconds // 60}", font=("Segoe UI", 10), bg=BG_DARK, fg=TEXT_DARK)
focus_label.grid(row=0, column=2, padx=8)

# assign references used earlier
start_btn_ref = start_btn

# set initial colors/buttons for hover logic
BTN_ACTIVE = "#2f8f6a"
BTN_HOVER = "#47b78f"
BTN_PAUSE = "#b84b4b"
BTN_LIGHT = BUTTON_LIGHT

for btn in [start_btn, pause_button, reset_btn, apply_btn, theme_btn]:
    btn.config(bg=BTN_ACTIVE, fg=TEXT_DARK, activebackground=BTN_HOVER)

# bind hover for apply and theme buttons too
apply_btn.bind("<Enter>", on_enter); apply_btn.bind("<Leave>", on_leave)
theme_btn.bind("<Enter>", on_enter); theme_btn.bind("<Leave>", on_leave)

# initial theme
apply_theme(True)

# start pulse loop idle
root.after(200, pulse_step)

# Start mainloop
root.mainloop()
