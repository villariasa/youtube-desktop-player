"""
Desktop-Wide Transparent Neon Wave Layer
- 100% transparent background (wallpaper completely visible)
- 100% click-through (never blocks desktop interaction or icons)
- Multi-layered flowing neon ribbons in pink, magenta, violet, and electric-blue
- Audio-reactive: expands amplitude and speed when music is playing, idles calmly when paused
"""
import tkinter as tk
import ctypes
import math
import time
import json
import os
import sys

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "player_state.json")

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020

user32 = ctypes.windll.user32

def run_wave_layer():
    root = tk.Tk()
    root.overrideredirect(True)
    
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    
    layer_w = screen_w
    layer_h = 220
    layer_y = screen_h - layer_h - 40
    
    root.geometry(f"{layer_w}x{layer_h}+0+{layer_y}")
    
    # 100% Transparent Background on Windows
    TRANS_COLOR = "#010203"
    root.config(bg=TRANS_COLOR)
    root.wm_attributes("-transparentcolor", TRANS_COLOR)
    root.wm_attributes("-topmost", False)
    
    # Click-through: mouse clicks pass directly to desktop/icons
    hwnd = user32.GetParent(root.winfo_id())
    if not hwnd:
        hwnd = root.winfo_id()
    styles = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, styles | WS_EX_LAYERED | WS_EX_TRANSPARENT)
    
    canvas = tk.Canvas(root, width=layer_w, height=layer_h, bg=TRANS_COLOR, highlightthickness=0)
    canvas.pack(fill="both", expand=True)
    
    state = {"playing": True, "energy": 0.7}
    
    phase = 0.0
    current_amp = 30.0
    
    def update_state():
        nonlocal state
        try:
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE, "r") as f:
                    state = json.load(f)
        except Exception:
            pass
        root.after(300, update_state)
    
    root.after(100, update_state)
    
    def animate():
        nonlocal phase, current_amp
        
        is_playing = state.get("playing", True)
        target_amp = 48.0 if is_playing else 10.0
        current_amp += (target_amp - current_amp) * 0.08
        
        speed = 0.038 if is_playing else 0.012
        phase += speed
        
        canvas.delete("wave")
        
        base_y = layer_h * 0.52
        
        # 1. Electric Blue / Cyan Deep Ribbon
        pts_blue = []
        for x in range(0, layer_w + 16, 16):
            envelope = math.exp(-pow(((x / layer_w) * 2 - 1) * 1.2, 2))
            amp = (current_amp * 0.75 + 6) * (0.45 + envelope * 0.9)
            y = base_y + math.sin(x * 0.007 + phase * 0.9) * amp
            pts_blue.extend([x, y])
        if len(pts_blue) >= 4:
            canvas.create_line(pts_blue, fill="#38bdf8", width=2, smooth=True, tags="wave")
        
        # 2. Deep Violet Ambient Flow
        pts_violet = []
        for x in range(0, layer_w + 16, 16):
            envelope = math.exp(-pow(((x / layer_w) * 2 - 1) * 1.2, 2))
            amp = (current_amp * 0.9 + 8) * (0.45 + envelope * 0.9)
            y = base_y + 4 + math.sin(x * 0.009 + phase * 1.15 + 1.2) * amp
            pts_violet.extend([x, y])
        if len(pts_violet) >= 4:
            canvas.create_line(pts_violet, fill="#a855f7", width=3, smooth=True, tags="wave")
        
        # 3. Vibrant Neon Magenta Main Ribbon
        pts_magenta = []
        for x in range(0, layer_w + 14, 14):
            envelope = math.exp(-pow(((x / layer_w) * 2 - 1) * 1.2, 2))
            amp = (current_amp * 1.15 + 10) * (0.45 + envelope * 0.9)
            y = base_y - 2 + math.sin(x * 0.011 + phase * 1.4 + 2.4) * amp
            pts_magenta.extend([x, y])
        if len(pts_magenta) >= 4:
            canvas.create_line(pts_magenta, fill="#ec4899", width=4, smooth=True, tags="wave")
            # Glowing Core Highlight
            canvas.create_line(pts_magenta, fill="#f472b6", width=2, smooth=True, tags="wave")
        
        root.after(25, animate)
    
    animate()
    root.mainloop()

if __name__ == "__main__":
    run_wave_layer()
