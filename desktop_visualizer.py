"""
Desktop Music Visualizer - Seamless Wallpaper Integration
- Dynamic color palette: Muted cyan, teal, soft icy blue, charcoal shadows, white glowing particles
- Desktop-wide flowing neon ribbon waves extending across the entire screen
- Smoothly blended glassmorphism player with zero harsh box appearance
- Clean user-friendly search modal (zero presets)
- Desktop level (never overlaps other apps)
"""
import tkinter as tk
import ctypes
import math
import time
import json
import threading
import subprocess
import os
import sys
import random
import urllib.request
import io
import yt_dlp
from PIL import Image, ImageTk, ImageDraw

AUDIO_SERVICE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio_service.py")
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio_state.json")
CMD_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio_cmd.json")

user32 = ctypes.windll.user32
SCREEN_W = user32.GetSystemMetrics(0)
SCREEN_H = user32.GetSystemMetrics(1)

CANVAS_W = SCREEN_W
CANVAS_H = 260
CANVAS_Y = SCREEN_H - CANVAS_H - 45

# Palette from user's Jujutsu Kaisen / Megumi Mahoraga wallpaper:
# Muted cyan, teal, soft icy blue, charcoal/black shadows, white glowing particles
COLOR_TRANS = "#010203"
COLOR_CHARCOAL = "#161c24"
COLOR_TEAL_DARK = "#1a464c"
COLOR_TEAL = "#2d7a82"
COLOR_CYAN = "#4aa3a8"
COLOR_ICY_BLUE = "#9cd5d6"
COLOR_WHITE = "#f1f5f9"
COLOR_CARD_FILL = "#151b22"

class Particle:
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.reset()
        self.x = random.uniform(0, w)

    def reset(self):
        self.x = random.uniform(0, self.w)
        self.y = random.uniform(self.h * 0.25, self.h * 0.85)
        self.vx = random.uniform(0.3, 1.1)
        self.vy = random.uniform(-0.25, 0.25)
        self.size = random.uniform(1.2, 3.2)
        self.alpha = random.uniform(0.3, 0.85)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        if self.x > self.w or self.y < 0 or self.y > self.h:
            self.reset()
            self.x = 0

def create_rounded_rect(canvas, x1, y1, x2, y2, radius=20, **kwargs):
    points = [
        x1 + radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)

def format_time(s):
    if not s or math.isnan(s): return "0:00"
    m = int(s // 60)
    sec = int(s % 60)
    return f"{m}:{sec:02d}"

def send_command(cmd_dict):
    try:
        with open(CMD_FILE, "w") as f:
            json.dump(cmd_dict, f)
    except Exception:
        pass

def run_desktop_app():
    # 1. Start background audio streaming service
    audio_proc = subprocess.Popen([sys.executable, AUDIO_SERVICE], cwd=os.path.dirname(os.path.abspath(__file__)))

    root = tk.Tk()
    root.overrideredirect(True)
    root.geometry(f"{CANVAS_W}x{CANVAS_H}+0+{CANVAS_Y}")

    # Set 100% native transparency - wallpaper is completely visible!
    root.config(bg=COLOR_TRANS)
    root.wm_attributes("-transparentcolor", COLOR_TRANS)
    root.wm_attributes("-topmost", False)

    canvas = tk.Canvas(root, width=CANVAS_W, height=CANVAS_H, bg=COLOR_TRANS, highlightthickness=0)
    canvas.pack(fill="both", expand=True)

    # Initialize 50 floating glowing particles
    particles = [Particle(CANVAS_W, CANVAS_H) for _ in range(50)]

    current_track = {
        "title": "BABYMONSTER - 'DESERVE' M/V",
        "artist": "YouTube",
        "thumb": "https://i.ytimg.com/vi/oC6brLXQe4I/hqdefault.jpg"
    }

    thumb_img_ref = [None]
    def load_thumb(url):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            data = urllib.request.urlopen(req, timeout=3).read()
            im = Image.open(io.BytesIO(data)).convert("RGBA")
            im = im.resize((92, 92), Image.Resampling.LANCZOS)
            mask = Image.new("L", (92, 92), 0)
            draw = ImageDraw.Draw(mask)
            draw.rounded_rectangle((0, 0, 92, 92), radius=14, fill=255)
            im.putalpha(mask)
            thumb_img_ref[0] = ImageTk.PhotoImage(im)
        except Exception:
            pass

    threading.Thread(target=load_thumb, args=(current_track["thumb"],), daemon=True).start()

    # Widget Card Dimensions (Centered horizontally)
    card_w = 600
    card_h = 142
    card_x1 = (CANVAS_W - card_w) // 2
    card_y1 = (CANVAS_H - card_h) // 2
    card_x2 = card_x1 + card_w
    card_y2 = card_y1 + card_h

    # State tracking
    audio_state = {"playing": True, "time": 0.0, "duration": 0.0}
    current_vol = [0.85]
    phase = 0.0
    current_amp = 28.0

    def poll_audio_state():
        nonlocal audio_state
        try:
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE, "r") as f:
                    audio_state = json.load(f)
        except Exception:
            pass
        root.after(250, poll_audio_state)

    root.after(200, poll_audio_state)

    # Controls interaction
    def on_click(e):
        x, y = e.x, e.y
        # Play/Pause
        play_btn_x = card_x1 + 330
        play_btn_y = card_y1 + 115
        if math.hypot(x - play_btn_x, y - play_btn_y) < 18:
            send_command({"action": "toggle"})
            return

        # Volume slider
        vol_x1 = card_x1 + 130
        vol_x2 = card_x1 + 200
        vol_y = card_y1 + 115
        if vol_x1 <= x <= vol_x2 and abs(y - vol_y) < 10:
            pct = max(0.0, min(1.0, (x - vol_x1) / (vol_x2 - vol_x1)))
            current_vol[0] = pct
            send_command({"action": "volume", "val": pct})
            return

        # Search icon
        if math.hypot(x - (card_x2 - 38), y - (card_y1 + 18)) < 12:
            open_search_dialog()
            return

        # Close button
        if math.hypot(x - (card_x2 - 16), y - (card_y1 + 18)) < 12:
            try: audio_proc.terminate()
            except Exception: pass
            root.destroy()
            return

    def open_search_dialog():
        dlg = tk.Toplevel(root)
        dlg.overrideredirect(True)
        dlg.geometry(f"460x280+{card_x1 + 70}+{CANVAS_Y + card_y1 - 70}")
        dlg.config(bg="#121820")
        dlg.wm_attributes("-topmost", True)

        header = tk.Frame(dlg, bg="#121820")
        header.pack(fill="x", padx=10, pady=8)

        entry = tk.Entry(header, bg="#1b222c", fg="#fff", font=("Segoe UI", 10), insertbackground="#4aa3a8", relief="flat")
        entry.pack(side="left", fill="x", expand=True, ipady=4, padx=(0, 6))
        entry.focus_set()

        results_box = tk.Listbox(dlg, bg="#161e27", fg="#9cd5d6", font=("Segoe UI", 9), selectbackground="#2d7a82", selectforeground="#fff", relief="flat", highlightthickness=0)
        results_box.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        def do_search():
            q = entry.get().strip()
            if not q: return
            results_box.delete(0, "end")
            results_box.insert("end", "Searching YouTube...")
            def search_thread():
                try:
                    ydl_opts_search = {'format': 'bestaudio/best', 'noplaylist': True, 'quiet': True, 'extract_flat': True}
                    with yt_dlp.YoutubeDL(ydl_opts_search) as ydl:
                        info = ydl.extract_info(f"ytsearch6:{q}", download=False)
                        items = []
                        for entry_item in info.get('entries', []):
                            t = entry_item.get('title', '').replace(' (Official Video)', '').replace(' [Official Audio]', '')
                            vid = entry_item.get('id', '')
                            th = f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg" if vid else ''
                            items.append((t, vid, th))
                        def update_ui():
                            results_box.delete(0, "end")
                            for title, vid, th in items:
                                results_box.insert("end", f"▶  {title}")
                            results_box.bind("<Double-Button-1>", lambda e: select_song(items))
                        dlg.after(0, update_ui)
                except Exception as ex:
                    dlg.after(0, lambda: results_box.insert("end", f"Error: {ex}"))
            threading.Thread(target=search_thread, daemon=True).start()

        def select_song(items):
            sel = results_box.curselection()
            if sel:
                idx = sel[0]
                title, vid, th = items[idx]
                current_track["title"] = title
                current_track["thumb"] = th
                threading.Thread(target=load_thumb, args=(th,), daemon=True).start()
                send_command({"action": "play", "id": vid, "volume": current_vol[0]})
                dlg.destroy()

        btn_find = tk.Button(header, text="Search", bg="#2d7a82", fg="#fff", font=("Segoe UI", 9, "bold"), relief="flat", command=do_search, cursor="hand2")
        btn_find.pack(side="left", padx=2)

        btn_close = tk.Button(header, text="✕", bg="#121820", fg="#94a3b8", font=("Segoe UI", 10), relief="flat", command=dlg.destroy, cursor="hand2")
        btn_close.pack(side="left", padx=2)

        entry.bind("<Return>", lambda e: do_search())

    canvas.bind("<Button-1>", on_click)

    # 60 FPS Animation Loop
    def render_frame():
        nonlocal phase, current_amp
        is_playing = audio_state.get("playing", True)
        target_amp = 46.0 if is_playing else 10.0
        current_amp += (target_amp - current_amp) * 0.08

        speed = 0.035 if is_playing else 0.010
        phase += speed

        canvas.delete("all")

        base_y = CANVAS_H * 0.52

        # 1. DESKTOP-WIDE FLOWING WAVES (Muted Cyan, Teal, Soft Icy Blue, Charcoal Shadows)
        # Layer 1: Charcoal Shadow Wave (flowing behind character)
        pts_shadow = []
        for x in range(0, CANVAS_W + 16, 16):
            envelope = math.exp(-pow(((x / CANVAS_W) * 2 - 1) * 1.1, 2))
            amp = (current_amp * 0.85 + 8) * (0.45 + envelope * 0.95)
            y = base_y + 6 + math.sin(x * 0.007 + phase * 0.85) * amp
            pts_shadow.extend([x, y])
        if len(pts_shadow) >= 4:
            canvas.create_line(pts_shadow, fill="#182028", width=5, smooth=True)

        # Layer 2: Muted Teal Wave
        pts_teal = []
        for x in range(0, CANVAS_W + 16, 16):
            envelope = math.exp(-pow(((x / CANVAS_W) * 2 - 1) * 1.1, 2))
            amp = (current_amp * 1.05 + 10) * (0.45 + envelope * 0.95)
            y = base_y + 2 + math.sin(x * 0.009 + phase * 1.1 + 1.2) * amp
            pts_teal.extend([x, y])
        if len(pts_teal) >= 4:
            canvas.create_line(pts_teal, fill="#245d63", width=3, smooth=True)

        # Layer 3: Muted Cyan Main Wave Ribbon
        pts_cyan = []
        for x in range(0, CANVAS_W + 14, 14):
            envelope = math.exp(-pow(((x / CANVAS_W) * 2 - 1) * 1.1, 2))
            amp = (current_amp * 1.25 + 12) * (0.45 + envelope * 0.95)
            y = base_y - 2 + math.sin(x * 0.011 + phase * 1.35 + 2.4) * amp
            pts_cyan.extend([x, y])
        if len(pts_cyan) >= 4:
            canvas.create_line(pts_cyan, fill="#3da5a8", width=3.5, smooth=True)

        # Layer 4: Soft Icy Blue Highlight Filament Wave
        pts_icy = []
        for x in range(0, CANVAS_W + 12, 12):
            envelope = math.exp(-pow(((x / CANVAS_W) * 2 - 1) * 1.1, 2))
            amp = (current_amp * 1.10 + 9) * (0.45 + envelope * 0.95)
            y = base_y - 1 + math.sin(x * 0.013 + phase * 1.5 + 3.2) * amp
            pts_icy.extend([x, y])
        if len(pts_icy) >= 4:
            canvas.create_line(pts_icy, fill="#9cd5d6", width=1.5, smooth=True)

        # 2. FLOATING GLOWING PARTICLES (White & Soft Icy Blue)
        for p in particles:
            p.update()
            color = "#ffffff" if p.alpha > 0.6 else "#9cd5d6"
            canvas.create_oval(p.x, p.y, p.x + p.size, p.y + p.size, fill=color, outline="")

        # 3. BLENDED GLASSMORPHISM WIDGET (Soft, non-rectangular silhouette)
        # Soft outer shadow
        create_rounded_rect(canvas, card_x1 - 2, card_y1 - 2, card_x2 + 2, card_y2 + 2, radius=22, fill="#10151c", outline="")
        # Translucent blended card body with soft icy-cyan border
        create_rounded_rect(canvas, card_x1, card_y1, card_x2, card_y2, radius=20, fill=COLOR_CARD_FILL, outline="#3da5a8", width=1)

        # Album Art
        if thumb_img_ref[0]:
            canvas.create_image(card_x1 + 16, card_y1 + 16, anchor="nw", image=thumb_img_ref[0])
        else:
            canvas.create_rectangle(card_x1 + 16, card_y1 + 16, card_x1 + 108, card_y1 + 108, fill="#1c242c", outline="#2d7a82")

        # Track Title (Crisp white with soft glow)
        title_txt = current_track["title"]
        if len(title_txt) > 38: title_txt = title_txt[:36] + "..."
        canvas.create_text(card_x1 + 124, card_y1 + 24, anchor="w", text=title_txt, fill="#ffffff", font=("Segoe UI Variable Text", 12, "bold"))

        # Track Source (YouTube in soft teal)
        canvas.create_text(card_x1 + 124, card_y1 + 42, anchor="w", text="YouTube", fill="#4aa3a8", font=("Segoe UI", 9))

        # Real-Time Spectrum Equalizer Bars in Muted Cyan / Teal / Icy Blue
        num_bars = 36
        spec_x_start = card_x1 + 124
        spec_w = 440
        bar_w = spec_w / num_bars - 2.5
        t = phase * 2.8
        for i in range(num_bars):
            if is_playing:
                v = 0.35 + 0.35 * math.sin(t + i * 0.38) + 0.30 * math.cos(t * 1.6 - i * 0.5)
                h = max(3.0, min(22.0, v * 22.0))
            else:
                h = 3.0
            bx = spec_x_start + i * (bar_w + 2.5)
            by1 = card_y1 + 78 - h
            by2 = card_y1 + 78
            bar_color = "#9cd5d6" if i % 3 == 0 else ("#4aa3a8" if i % 2 == 0 else "#2d7a82")
            canvas.create_rectangle(bx, by1, bx + bar_w, by2, fill=bar_color, outline="")

        # CONTROLS ROW
        ctrl_y = card_y1 + 115

        # Volume icon & slider
        canvas.create_text(card_x1 + 115, ctrl_y, text="🔈", fill="#9cd5d6", font=("Segoe UI", 9))
        vol_x1 = card_x1 + 128
        vol_x2 = card_x1 + 185
        canvas.create_line(vol_x1, ctrl_y, vol_x2, ctrl_y, fill="#24303c", width=3)
        vol_thumb_x = vol_x1 + (vol_x2 - vol_x1) * current_vol[0]
        canvas.create_line(vol_x1, ctrl_y, vol_thumb_x, ctrl_y, fill="#4aa3a8", width=3)
        canvas.create_oval(vol_thumb_x - 4, ctrl_y - 4, vol_thumb_x + 4, ctrl_y + 4, fill="#9cd5d6", outline="")

        # Prev Icon
        play_btn_x = card_x1 + 330
        canvas.create_text(play_btn_x - 32, ctrl_y, text="⏮", fill="#cbd5e1", font=("Segoe UI", 11))

        # Circular Play/Pause Button (Cyan Glowing)
        canvas.create_oval(play_btn_x - 16, ctrl_y - 16, play_btn_x + 16, ctrl_y + 16, fill="#2d7a82", outline="#4aa3a8", width=1.5)
        play_symbol = "⏸" if is_playing else "▶"
        canvas.create_text(play_btn_x, ctrl_y, text=play_symbol, fill="#ffffff", font=("Segoe UI", 10, "bold"))

        # Next Icon
        canvas.create_text(play_btn_x + 32, ctrl_y, text="⏭", fill="#cbd5e1", font=("Segoe UI", 11))

        # Time Display
        time_str = f"{format_time(audio_state.get('time', 0))} / {format_time(audio_state.get('duration', 0))}"
        canvas.create_text(card_x2 - 110, ctrl_y, text=time_str, fill="#9cd5d6", font=("Segoe UI", 9))

        # Shuffle & Repeat
        canvas.create_text(card_x2 - 55, ctrl_y, text="🔀", fill="#4aa3a8", font=("Segoe UI", 9))
        canvas.create_text(card_x2 - 35, ctrl_y, text="🔁", fill="#4aa3a8", font=("Segoe UI", 9))

        # Top Right Action Icons (Search & Close)
        canvas.create_text(card_x2 - 38, card_y1 + 18, text="🔍", fill="#9cd5d6", font=("Segoe UI", 10))
        canvas.create_text(card_x2 - 16, card_y1 + 18, text="✕", fill="#94a3b8", font=("Segoe UI", 10))

        root.after(16, render_frame)

    render_frame()

    try:
        root.mainloop()
    finally:
        try:
            audio_proc.terminate()
        except Exception:
            pass

if __name__ == "__main__":
    run_desktop_app()
