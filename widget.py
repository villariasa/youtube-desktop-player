#!/usr/bin/env python3
"""
Immersive Glassmorphism Desktop Music Visualizer
- Real-time dynamic glass dragging: wallpaper flows smoothly through glass during drag
- Active live wallpaper watcher: auto-adapts instantly to Next Desktop Background
- YouTube Auto-Next: automatically plays next related songs from artist/playlist when song ends
- YouTube Non-Stop: continuous uninterrupted playback with automatic error recovery
- Desktop-wide audio-reactive flowing ribbon waves in cyan, teal, and white
- Atmospheric spectrum equalizer bars on left and right sides of desktop
- Centered ultra-transparent glassmorphism player card
- Direct streaming unmuted HTML5 audio via yt-dlp on play button click
- Full controls: Click-to-seek, Volume slider, Prev/Next, Glowing Circular Play/Pause, Shuffle, Repeat, Search
- Desktop level (on_top=False, never overlaps other applications)
"""
import os
import sys

if sys.platform.startswith('linux'):
    if '/usr/lib/x86_64-linux-gnu/girepository-1.0' not in os.environ.get('GI_TYPELIB_PATH', ''):
        os.environ['GI_TYPELIB_PATH'] = '/usr/lib/x86_64-linux-gnu/girepository-1.0:' + os.environ.get('GI_TYPELIB_PATH', '')

import webview
import yt_dlp
import threading
import json
import ctypes
import io
import time
import base64
import asyncio
import websockets
import numpy as np
import soundcard as sc
import warnings
import colorsys

IS_WINDOWS = sys.platform == 'win32'
IS_LINUX = sys.platform.startswith('linux')

if IS_WINDOWS:
    sys.coinit_flags = 0
    try:
        from pycaw.pycaw import AudioUtilities
    except Exception:
        AudioUtilities = None
else:
    AudioUtilities = None

from PIL import Image

warnings.filterwarnings('ignore')

AUDIO_WS_PORT = 8765

def extract_aesthetic_palette(img_path):
    """
    Extracts the most aesthetic vibrant accent palette from the active desktop wallpaper.
    Samples dominant hues, evaluates color harmony, and enhances neon vibrance for the
    glassmorphism player, flowing waves, particles, and spectrum equalizer bars.
    """
    default_palette = {
        'primary': '#22d3ee',
        'secondary': '#a5f3fc',
        'glow': 'rgba(34, 211, 238, 0.7)',
        'glow_subtle': 'rgba(34, 211, 238, 0.28)',
        'glass': 'rgba(13, 23, 33, 0.42)',
        'border': 'rgba(103, 232, 249, 0.48)',
        'rgb': [34, 211, 238],
        'sec_rgb': [165, 243, 252]
    }
    if not os.path.exists(img_path):
        return default_palette
    try:
        img = Image.open(img_path).convert('RGB')
        small = img.resize((100, 100))
        palette_img = small.quantize(colors=24, method=Image.Quantize.MEDIANCUT)
        palette = palette_img.getpalette()[:72]
        colors = [(palette[i*3], palette[i*3+1], palette[i*3+2]) for i in range(24)]
        
        scored_colors = []
        for r, g, b in colors:
            h, s, v = colorsys.rgb_to_hsv(r/255.0, g/255.0, b/255.0)
            # Score favors rich, luminous vibrant tones (saturation > 0.2, brightness 0.25 - 0.9)
            score = (s ** 1.25) * (1.0 - abs(v - 0.6) * 1.3)
            scored_colors.append((score, (r, g, b), (h, s, v)))
        
        scored_colors.sort(key=lambda x: x[0], reverse=True)
        best_score, (br, bg, bb), (bh, bs, bv) = scored_colors[0]
        
        # If the image is completely monochrome/grayscale, default to clean cool cyan
        if bs < 0.12:
            return default_palette
            
        # Boost saturation and brightness for luminous futuristic neon appearance
        neon_s = min(1.0, bs * 1.35 + 0.15)
        neon_v = max(0.8, min(0.98, bv * 1.3))
        pr, pg, pb = [int(c * 255) for c in colorsys.hsv_to_rgb(bh, neon_s, neon_v)]
        
        # Secondary highlight (brighter, lighter tint)
        sec_s = max(0.18, neon_s * 0.38)
        sec_v = 0.98
        sr, sg, sb = [int(c * 255) for c in colorsys.hsv_to_rgb((bh + 0.02) % 1.0, sec_s, sec_v)]
        
        # Subtle dark glass tint from wallpaper hue
        dr, dg, db = [int(c * 255) for c in colorsys.hsv_to_rgb(bh, 0.45, 0.11)]
        
        return {
            'primary': f'#{pr:02x}{pg:02x}{pb:02x}',
            'secondary': f'#{sr:02x}{sg:02x}{sb:02x}',
            'glow': f'rgba({pr}, {pg}, {pb}, 0.7)',
            'glow_subtle': f'rgba({pr}, {pg}, {pb}, 0.28)',
            'glass': f'rgba({dr}, {dg}, {db}, 0.42)',
            'border': f'rgba({sr}, {sg}, {sb}, 0.48)',
            'rgb': [pr, pg, pb],
            'sec_rgb': [sr, sg, sb]
        }
    except Exception:
        return default_palette

def get_system_volume():
    """Reads the current active device master volume (0.0 to 1.0) on Windows or Linux."""
    if IS_WINDOWS and AudioUtilities:
        try:
            dev = AudioUtilities.GetSpeakers()
            return round(float(dev.EndpointVolume.GetMasterVolumeLevelScalar()), 2)
        except Exception:
            return 0.28
    elif IS_LINUX:
        try:
            import subprocess
            out = subprocess.check_output(['amixer', 'sget', 'Master'], text=True, stderr=subprocess.DEVNULL)
            import re
            m = re.search(r'\[(\d+)%\]', out)
            if m:
                return round(int(m.group(1)) / 100.0, 2)
        except Exception:
            pass
    return 0.28

def set_system_volume(vol):
    """Sets the system master volume to match the widget slider on Windows or Linux."""
    if IS_WINDOWS and AudioUtilities:
        try:
            dev = AudioUtilities.GetSpeakers()
            dev.EndpointVolume.SetMasterVolumeLevelScalar(max(0.0, min(1.0, float(vol))), None)
        except Exception:
            pass
    elif IS_LINUX:
        try:
            import subprocess
            pct = int(max(0.0, min(1.0, float(vol))) * 100)
            subprocess.run(['amixer', 'sset', 'Master', f'{pct}%'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

def get_active_wallpaper_path():
    """Returns the absolute path to the active desktop wallpaper on Windows or Linux."""
    if IS_WINDOWS:
        wp_path = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Themes\TranscodedWallpaper")
        if os.path.exists(wp_path):
            return wp_path
        return ""
    elif IS_LINUX:
        try:
            import subprocess
            clean_env = os.environ.copy()
            clean_env.pop("GSETTINGS_SCHEMA_DIR", None)
            clean_env.pop("GIO_EXTRA_MODULES", None)
            gsettings_bin = "/usr/bin/gsettings" if os.path.isfile("/usr/bin/gsettings") else "gsettings"
            out = subprocess.check_output([gsettings_bin, 'get', 'org.gnome.desktop.background', 'picture-uri'], text=True, stderr=subprocess.DEVNULL, env=clean_env).strip()
            path = out.strip("'\"").replace("file://", "")
            if os.path.exists(path):
                return path
        except Exception:
            pass
        try:
            import subprocess
            out = subprocess.check_output(['dconf', 'read', '/org/gnome/desktop/background/picture-uri'], text=True, stderr=subprocess.DEVNULL).strip()
            path = out.strip("'\"").replace("file://", "")
            if os.path.exists(path):
                return path
        except Exception:
            pass
        kde_cfg = os.path.expanduser('~/.config/plasma-org.kde.plasma.desktop-appletsrc')
        if os.path.exists(kde_cfg):
            try:
                with open(kde_cfg, 'r', errors='ignore') as f:
                    for line in f:
                        if 'Image=' in line:
                            p = line.split('Image=')[1].strip().replace("file://", "")
                            if os.path.exists(p):
                                return p
            except Exception:
                pass
        for p in ['/usr/share/backgrounds/default.jpg', '/usr/share/backgrounds/default.png']:
            if os.path.exists(p):
                return p
    return ""

class AudioEngine:
    """
    Real-time Native Windows WASAPI Loopback Audio Capture & FFT Frequency Analyzer.
    Captures live desktop/system audio (YouTube, browser, Spotify, or local player),
    computes FFT frequency bands, RMS volume, transient beat detection, and 64-point
    time-domain waveform, broadcasting to WebView2 via local WebSocket at 60 FPS.
    """
    def __init__(self, port=AUDIO_WS_PORT):
        self.port = port
        self.running = True
        self.latest_payload = json.dumps({
            'vol': 0.0,
            'bass': 0.0,
            'vocal_mid': 0.0,
            'vocal_high': 0.0,
            'treble': 0.0,
            'beat': 0.0,
            'bars': [0.0] * 34,
            'wave': [0.0] * 64
        })

    async def ws_handler(self, websocket):
        try:
            while self.running:
                await websocket.send(self.latest_payload)
                await asyncio.sleep(0.016)  # 60 FPS broadcast
        except Exception:
            pass

    def start(self):
        def run_ws():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            async def _serve():
                async with websockets.serve(self.ws_handler, '127.0.0.1', self.port, ping_interval=None):
                    while self.running:
                        await asyncio.sleep(1.0)
            loop.run_until_complete(_serve())

        def run_capture():
            # 34 logarithmic frequency bands between 30Hz and 16kHz
            freq_bins = np.logspace(np.log10(30), np.log10(16000), 35)
            smooth_bars = np.zeros(34, dtype=np.float32)
            prev_energy = 0.0

            while self.running:
                try:
                    spk = sc.default_speaker()
                    mic = sc.get_microphone(id=str(spk.name), include_loopback=True)
                    with mic.recorder(samplerate=44100, blocksize=1024) as rec:
                        while self.running:
                            data = rec.record(numframes=1024)
                            if len(data) == 0:
                                time.sleep(0.01)
                                continue

                            mono = data.mean(axis=1) if data.ndim > 1 else data

                            # 1. Real time-domain waveform (64 points, normalized -1.0 to 1.0)
                            step = max(1, len(mono) // 64)
                            wave = mono[::step][:64]
                            if len(wave) < 64:
                                wave = np.pad(wave, (0, 64 - len(wave)))
                            # Amplitude scaling for speech/singing nuances
                            wave = np.clip(wave * 3.5, -1.0, 1.0)
                            wave_list = [round(float(v), 3) for v in wave]

                            # 2. RMS Volume
                            rms = float(np.sqrt(np.mean(mono**2)))
                            vol = min(1.0, rms * 5.5)

                            # 3. FFT Frequency analysis
                            windowed = mono * np.hanning(len(mono))
                            fft = np.abs(np.fft.rfft(windowed))
                            freqs = np.fft.rfftfreq(len(mono), 1.0 / 44100)

                            # Bass: 20 - 250 Hz (sub-bass, kicks, 808s)
                            b_mask = (freqs >= 20) & (freqs <= 250)
                            bass = min(1.0, float(np.mean(fft[b_mask])) * 3.8) if np.any(b_mask) else 0.0

                            # Vocal Mid: 250 - 1500 Hz (vocal fundamentals, vowel speech formants)
                            vm_mask = (freqs >= 250) & (freqs <= 1500)
                            vocal_mid = min(1.0, float(np.mean(fft[vm_mask])) * 4.8) if np.any(vm_mask) else 0.0

                            # Vocal High: 1500 - 4500 Hz (speech consonants, syllables, vocal rasp)
                            vh_mask = (freqs >= 1500) & (freqs <= 4500)
                            vocal_high = min(1.0, float(np.mean(fft[vh_mask])) * 5.8) if np.any(vh_mask) else 0.0

                            # Treble: 4500 - 16000 Hz (cymbals, sparkle, acoustic air)
                            tr_mask = (freqs >= 4500) & (freqs <= 16000)
                            treble = min(1.0, float(np.mean(fft[tr_mask])) * 7.5) if np.any(tr_mask) else 0.0

                            # Beat / transient attack jump
                            curr_energy = bass * 0.7 + vol * 0.3
                            beat = min(1.0, max(0.0, curr_energy - prev_energy * 0.94) * 2.8)
                            prev_energy = curr_energy

                            # 34 frequency bars for the equalizer
                            current_bars = np.zeros(34, dtype=np.float32)
                            for b in range(34):
                                m = (freqs >= freq_bins[b]) & (freqs < freq_bins[b+1])
                                if np.any(m):
                                    weight = 1.0 + (b / 34.0) * 1.8
                                    current_bars[b] = min(1.0, float(np.mean(fft[m])) * 4.2 * weight)

                            # Fast attack, smooth decay
                            smooth_bars = np.where(
                                current_bars > smooth_bars,
                                smooth_bars * 0.25 + current_bars * 0.75,
                                smooth_bars * 0.82 + current_bars * 0.18
                            )

                            self.latest_payload = json.dumps({
                                'vol': round(vol, 3),
                                'bass': round(bass, 3),
                                'vocal_mid': round(vocal_mid, 3),
                                'vocal_high': round(vocal_high, 3),
                                'treble': round(treble, 3),
                                'beat': round(beat, 3),
                                'bars': [round(float(v), 3) for v in smooth_bars],
                                'wave': wave_list
                            })
                except Exception:
                    # Gracefully handle audio device changes or temporary unavailability
                    time.sleep(1.0)

        threading.Thread(target=run_ws, daemon=True).start()
        threading.Thread(target=run_capture, daemon=True).start()

# Screen metrics & dynamic desktop work area
if IS_WINDOWS:
    user32 = ctypes.windll.user32
    import ctypes.wintypes
    SCREEN_W = user32.GetSystemMetrics(0)
    SCREEN_H = user32.GetSystemMetrics(1)

    # Dynamically query active desktop work area (handles taskbar visible or auto-hidden)
    rect = ctypes.wintypes.RECT()
    user32.SystemParametersInfoW(48, 0, ctypes.byref(rect), 0)
    WORK_BOTTOM = rect.bottom if rect.bottom > 0 else SCREEN_H
else:
    try:
        screens = webview.screens
        if screens:
            SCREEN_W = screens[0].width
            SCREEN_H = screens[0].height
        else:
            SCREEN_W, SCREEN_H = 1920, 1080
    except Exception:
        SCREEN_W, SCREEN_H = 1920, 1080
    WORK_BOTTOM = SCREEN_H

VIS_H = 210
VIS_W = SCREEN_W
POS_X = 0
POS_Y = max(0, WORK_BOTTOM - VIS_H)

def get_full_wallpaper_b64():
    """Generates a high-quality resized base64 JPEG of the entire desktop wallpaper."""
    try:
        wp_path = get_active_wallpaper_path()
        if not wp_path or not os.path.exists(wp_path):
            return ""
        img = Image.open(wp_path).convert("RGB")
        img_screen = img.resize((SCREEN_W, SCREEN_H), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img_screen.save(buf, format="JPEG", quality=92)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode('ascii')
    except Exception:
        return ""

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Desktop Music Visualizer</title>
<style>
  :root {
    --accent-primary: __ACCENT_PRIMARY__;
    --accent-secondary: __ACCENT_SECONDARY__;
    --accent-glow: __ACCENT_GLOW__;
    --accent-glow-subtle: __ACCENT_GLOW_SUBTLE__;
    --accent-glass: __ACCENT_GLASS__;
    --accent-border: __ACCENT_BORDER__;
  }

  * {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
    user-select: none;
    -webkit-user-select: none;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI Variable Text", "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  }

  html, body {
    width: 100%;
    height: 100%;
    overflow: hidden;
    position: relative;
    background: #0f141c;
  }

  /* FULL DESKTOP WALLPAPER BLENDING LAYER (Flows dynamically during drag) */
  .wallpaper-blend {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-repeat: no-repeat;
    z-index: 0;
    pointer-events: none;
  }

  /* FULL-SCREEN AUDIO REACTIVE WAVES CANVAS */
  #desktop-waves {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: 2;
    pointer-events: none;
  }

  /* CENTERED ULTRA-TRANSPARENT GLASSMORPHISM PLAYER CARD */
  .player-card-container {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 10;
    pointer-events: none;
  }

  .player-card {
    width: 590px;
    height: 124px;
    background: var(--accent-glass);
    backdrop-filter: blur(22px) saturate(160%);
    -webkit-backdrop-filter: blur(22px) saturate(160%);
    border: 1.2px solid var(--accent-border);
    border-radius: 16px;
    box-shadow: 
      0 0 28px var(--accent-glow-subtle),
      0 12px 36px rgba(0, 0, 0, 0.65),
      inset 0 1px 1.5px rgba(255, 255, 255, 0.4),
      inset 0 -1px 1.5px var(--accent-glow-subtle);
    display: flex;
    align-items: center;
    padding: 12px 16px;
    gap: 14px;
    position: relative;
    overflow: hidden;
    pointer-events: auto;
    cursor: grab;
    transition: height 0.28s cubic-bezier(0.16, 1, 0.3, 1), background 0.6s ease, border-color 0.6s ease, box-shadow 0.6s ease;
  }

  .player-card.expanded {
    height: 196px;
  }

  .player-card:active {
    cursor: grabbing;
  }

  /* DIAGONAL GLASS SPECULAR REFLECTION SHEEN */
  .player-card::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(
      126deg,
      rgba(255, 255, 255, 0.22) 0%,
      rgba(255, 255, 255, 0.06) 24%,
      transparent 48%,
      var(--accent-glow-subtle) 72%,
      transparent 100%
    );
    pointer-events: none;
    border-radius: 15px;
    z-index: 5;
  }

  /* TOP CURVED SPECULAR RIM LIGHT */
  .player-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 20px;
    right: 20px;
    height: 1.5px;
    background: linear-gradient(90deg, transparent 0%, rgba(255, 255, 255, 0.85) 40%, var(--accent-secondary) 60%, transparent 100%);
    box-shadow: 0 0 8px var(--accent-glow);
    pointer-events: none;
    z-index: 6;
    transition: background 0.6s ease, box-shadow 0.6s ease;
  }

  /* Album Artwork */
  .album-wrap {
    width: 80px;
    height: 80px;
    border-radius: 10px;
    overflow: hidden;
    position: relative;
    flex-shrink: 0;
    box-shadow: 0 4px 18px rgba(0, 0, 0, 0.6), 0 0 12px var(--accent-glow-subtle);
    border: 1px solid rgba(255, 255, 255, 0.25);
    z-index: 8;
  }

  .album-img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }

  /* Main Info Column */
  .main-column {
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    height: 80px;
    min-width: 0;
    position: relative;
    z-index: 8;
  }

  /* Track Title & Top Actions */
  .track-row {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 8px;
  }

  .track-meta {
    min-width: 0;
    flex: 1;
  }

  .track-title {
    font-size: 13.5px;
    font-weight: 700;
    color: #ffffff;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    text-shadow: 0 2px 8px rgba(0, 0, 0, 0.8);
    letter-spacing: -0.2px;
  }

  .track-source {
    font-size: 10.5px;
    color: #94a3b8;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-top: 1.5px;
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .top-actions {
    display: flex;
    align-items: center;
    gap: 5px;
    flex-shrink: 0;
  }

  .icon-btn {
    background: transparent;
    border: none;
    color: rgba(255, 255, 255, 0.65);
    cursor: pointer;
    padding: 2px 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 4px;
    transition: all 0.2s ease;
  }

  .icon-btn:hover {
    color: #ffffff;
    background: rgba(255, 255, 255, 0.15);
  }

  .icon-btn svg {
    width: 13px;
    height: 13px;
    fill: currentColor;
  }

  /* Spectrum Waveform Equalizer (34 Bars in Card) - Clickable to seek */
  .spectrum-container {
    width: 100%;
    height: 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 2px;
    cursor: pointer;
    padding: 2px 0;
  }

  .spectrum-bar {
    flex: 1;
    min-width: 2px;
    max-width: 5px;
    height: 3px;
    border-radius: 999px;
    background: linear-gradient(180deg, var(--accent-secondary) 0%, var(--accent-primary) 100%);
    box-shadow: 0 0 6px var(--accent-glow-subtle);
    transition: height 0.08s ease, filter 0.15s ease, background 0.6s ease;
  }

  /* Controls Row */
  .controls-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  /* Left: Volume */
  .controls-left {
    display: flex;
    align-items: center;
    gap: 5px;
    width: 95px;
  }

  .vol-icon {
    width: 12px;
    height: 12px;
    fill: rgba(255, 255, 255, 0.65);
    flex-shrink: 0;
  }

  .vol-slider {
    -webkit-appearance: none;
    width: 100%;
    height: 3px;
    background: rgba(255, 255, 255, 0.2);
    border-radius: 2px;
    outline: none;
    cursor: pointer;
  }

  .vol-slider::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 9px;
    height: 9px;
    border-radius: 50%;
    background: var(--accent-primary);
    box-shadow: 0 0 6px var(--accent-primary);
    cursor: pointer;
    transition: transform 0.15s ease, background 0.6s ease;
  }

  .vol-slider::-webkit-slider-thumb:hover {
    transform: scale(1.3);
  }

  /* Center: Prev, Glowing Circular Pause, Next */
  .controls-center {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .ctrl-btn {
    background: transparent;
    border: none;
    color: rgba(255, 255, 255, 0.85);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 2px;
    transition: all 0.2s ease;
  }

  .ctrl-btn:hover {
    color: #ffffff;
    transform: scale(1.15);
  }

  .ctrl-btn svg {
    width: 13px;
    height: 13px;
    fill: currentColor;
  }

  /* Glowing Circular Play / Pause Button with Loading Spinner */
  .play-pause-btn {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: linear-gradient(135deg, var(--accent-glow-subtle) 0%, var(--accent-glow) 100%);
    border: 1.5px solid var(--accent-secondary);
    box-shadow: 0 0 14px var(--accent-glow), inset 0 0 6px rgba(255, 255, 255, 0.35);
    display: flex;
    align-items: center;
    justify-content: center;
    color: #ffffff;
    cursor: pointer;
    transition: all 0.2s ease;
    position: relative;
  }

  .play-pause-btn:hover {
    transform: scale(1.12);
    box-shadow: 0 0 20px var(--accent-glow), inset 0 0 10px rgba(255, 255, 255, 0.5);
  }

  .play-pause-btn.loading {
    animation: pulse-ring 1s infinite alternate ease-in-out;
  }

  @keyframes pulse-ring {
    0% { box-shadow: 0 0 8px var(--accent-glow-subtle); }
    100% { box-shadow: 0 0 24px var(--accent-glow); }
  }

  .play-pause-btn svg {
    width: 13px;
    height: 13px;
    fill: #ffffff;
  }

  /* Right: Time, Shuffle, Repeat, Playlist */
  .controls-right {
    display: flex;
    align-items: center;
    gap: 5px;
    width: 120px;
    justify-content: flex-end;
  }

  .time-display {
    font-size: 9.5px;
    color: rgba(255, 255, 255, 0.7);
    font-variant-numeric: tabular-nums;
  }

  .mini-btn {
    background: transparent;
    border: none;
    color: rgba(255, 255, 255, 0.55);
    cursor: pointer;
    padding: 2px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s ease;
  }

  .mini-btn:hover {
    color: #ffffff;
  }

  .mini-btn.active {
    color: var(--accent-primary);
    text-shadow: 0 0 6px var(--accent-primary);
  }

  .mini-btn svg {
    width: 11px;
    height: 11px;
    fill: currentColor;
  }

  /* Modal, Queue & Search Styles */
  .playlist-modal {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(10, 18, 28, 0.95);
    backdrop-filter: blur(24px) saturate(180%);
    -webkit-backdrop-filter: blur(24px) saturate(180%);
    border-radius: 16px;
    border: 1px solid var(--accent-border);
    display: none;
    flex-direction: column;
    padding: 8px 12px;
    z-index: 50;
    box-shadow: inset 0 1px 1.5px rgba(255, 255, 255, 0.3), 0 8px 32px rgba(0, 0, 0, 0.8);
  }

  .playlist-modal.active {
    display: flex;
  }

  .modal-top-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    padding-bottom: 6px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  }

  .modal-tabs {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .modal-tab-btn {
    background: transparent;
    border: 1px solid transparent;
    color: rgba(255, 255, 255, 0.6);
    font-size: 10px;
    font-weight: 700;
    padding: 3px 8px;
    border-radius: 6px;
    cursor: pointer;
    transition: all 0.2s ease;
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .modal-tab-btn:hover {
    color: #ffffff;
    background: rgba(255, 255, 255, 0.06);
  }

  .modal-tab-btn.active {
    background: var(--accent-glow-subtle);
    color: var(--accent-primary);
    border: 1px solid var(--accent-border);
    text-shadow: 0 0 6px var(--accent-glow);
  }

  /* Official Tailwind Heroicons sizing utilities */
  .h-icon {
    width: 14px;
    height: 14px;
    display: inline-block;
    flex-shrink: 0;
    vertical-align: middle;
  }
  .h-icon-sm {
    width: 12px;
    height: 12px;
    display: inline-block;
    flex-shrink: 0;
    vertical-align: middle;
  }
  .h-icon-xs {
    width: 11px;
    height: 11px;
    display: inline-block;
    flex-shrink: 0;
    vertical-align: middle;
  }

  .modal-top-actions {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .loop-pill {
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.16);
    border-radius: 12px;
    color: rgba(255, 255, 255, 0.7);
    font-size: 8.5px;
    font-weight: 700;
    padding: 2px 7px;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 4px;
    transition: all 0.2s ease;
  }

  .loop-pill:hover {
    color: #ffffff;
    border-color: rgba(255, 255, 255, 0.3);
  }

  .loop-pill.active {
    background: var(--accent-glow-subtle);
    border-color: var(--accent-primary);
    color: var(--accent-secondary);
    box-shadow: 0 0 8px var(--accent-glow-subtle);
  }

  .tab-content {
    flex: 1;
    display: none;
    flex-direction: column;
    overflow: hidden;
    margin-top: 5px;
  }

  .tab-content.active {
    display: flex;
  }

  /* Quick Add Bar */
  .quick-add-bar {
    display: flex;
    align-items: center;
    gap: 4px;
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 6px;
    padding: 2px 5px;
    margin-bottom: 5px;
  }

  .quick-add-input-wrap {
    flex: 1;
    display: flex;
    align-items: center;
    gap: 4px;
    min-width: 0;
  }

  .quick-add-icon {
    color: rgba(255, 255, 255, 0.4);
    flex-shrink: 0;
  }

  .quick-add-input {
    flex: 1;
    background: transparent;
    border: none;
    outline: none;
    color: #ffffff;
    font-size: 9.5px;
    min-width: 0;
  }

  .quick-add-input::placeholder {
    color: rgba(255, 255, 255, 0.35);
  }

  /* Now Playing Hero inside Queue */
  .now-playing-hero {
    display: flex;
    align-items: center;
    gap: 7px;
    padding: 3px 6px;
    margin-bottom: 4px;
    background: rgba(255, 255, 255, 0.045);
    border: 1px solid var(--accent-border);
    border-radius: 7px;
    box-shadow: 0 2px 8px var(--accent-glow-subtle);
    flex-shrink: 0;
  }

  .now-playing-hero img {
    width: 24px;
    height: 24px;
    border-radius: 4px;
    object-fit: cover;
    flex-shrink: 0;
    border: 1px solid rgba(255, 255, 255, 0.15);
  }

  .now-playing-hero-info {
    flex: 1;
    min-width: 0;
  }

  .now-playing-badge {
    display: inline-flex;
    align-items: center;
    gap: 3.5px;
    font-size: 7.5px;
    font-weight: 800;
    letter-spacing: 0.5px;
    color: var(--accent-primary);
    text-transform: uppercase;
    margin-bottom: 1px;
  }

  /* Mini animated equalizer wave bars for live playing state */
  .mini-bars {
    display: inline-flex;
    align-items: flex-end;
    gap: 1.5px;
    height: 7px;
    width: 8px;
  }

  .mini-bar {
    flex: 1;
    background: var(--accent-primary);
    border-radius: 1px;
    animation: miniWave 0.75s ease-in-out infinite alternate;
  }
  .mini-bar:nth-child(1) { height: 35%; animation-delay: 0s; }
  .mini-bar:nth-child(2) { height: 95%; animation-delay: 0.22s; }
  .mini-bar:nth-child(3) { height: 55%; animation-delay: 0.44s; }

  @keyframes miniWave {
    0% { height: 25%; }
    100% { height: 100%; }
  }

  .now-playing-hero-title {
    font-size: 9px;
    font-weight: 700;
    color: #ffffff;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    line-height: 1.15;
  }

  .now-playing-hero-artist {
    font-size: 7.5px;
    color: #94a3b8;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  /* Queue View */
  .queue-header-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 3px 3px 3px;
    font-size: 8.5px;
    color: rgba(255, 255, 255, 0.65);
    font-weight: 600;
  }

  .queue-list {
    flex: 1;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 2.5px;
    padding-right: 2px;
  }

  .queue-list::-webkit-scrollbar {
    width: 3px;
  }

  .queue-list::-webkit-scrollbar-thumb {
    background: var(--accent-border);
    border-radius: 2px;
  }

  .queue-item {
    display: flex;
    align-items: center;
    gap: 5px;
    padding: 2.5px 5px;
    border-radius: 5px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.06);
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .queue-item:hover {
    background: rgba(255, 255, 255, 0.08);
    border-color: rgba(255, 255, 255, 0.18);
  }

  .queue-item.active-item {
    background: var(--accent-glow-subtle);
    border-color: var(--accent-border);
    box-shadow: 0 0 8px var(--accent-glow-subtle);
  }

  .queue-item-idx {
    font-size: 8px;
    font-weight: 700;
    color: rgba(255, 255, 255, 0.4);
    width: 13px;
    text-align: center;
    flex-shrink: 0;
  }

  .queue-item img {
    width: 20px;
    height: 20px;
    border-radius: 3px;
    object-fit: cover;
    flex-shrink: 0;
  }

  .queue-item-info {
    flex: 1;
    min-width: 0;
  }

  .queue-item-title {
    font-size: 8.5px;
    font-weight: 600;
    color: #ffffff;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    line-height: 1.15;
  }

  .queue-item-artist {
    font-size: 7.5px;
    color: #94a3b8;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .queue-actions {
    display: flex;
    align-items: center;
    gap: 2px;
    flex-shrink: 0;
  }

  .btn-icon-sm {
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 4px;
    color: rgba(255, 255, 255, 0.8);
    width: 17px;
    height: 17px;
    padding: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .btn-icon-sm:hover {
    background: var(--accent-primary);
    color: #0b1118;
    border-color: var(--accent-primary);
  }

  .btn-icon-sm.btn-del:hover {
    background: #ef4444;
    color: #ffffff;
    border-color: #ef4444;
  }

  .btn-sm-action {
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.14);
    border-radius: 4px;
    color: rgba(255, 255, 255, 0.85);
    font-size: 8px;
    font-weight: 700;
    padding: 2px 6px;
    cursor: pointer;
    transition: all 0.15s ease;
    display: inline-flex;
    align-items: center;
    gap: 3px;
  }

  .btn-sm-action:hover {
    background: var(--accent-primary);
    color: #0b1118;
    border-color: var(--accent-primary);
    box-shadow: 0 0 6px var(--accent-glow);
  }

  .btn-sm-del:hover {
    background: #ef4444;
    color: #ffffff;
    border-color: #ef4444;
    box-shadow: 0 0 6px rgba(239, 68, 68, 0.6);
  }

  /* Empty state */
  .queue-empty-state {
    text-align: center;
    padding: 12px 10px;
    color: rgba(255, 255, 255, 0.55);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 3px;
  }

  .queue-empty-icon {
    width: 26px;
    height: 26px;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    display: flex;
    align-items: center;
    justify-content: center;
    color: rgba(255, 255, 255, 0.45);
    margin-bottom: 2px;
  }

  /* Search Bar & Results */
  .search-bar {
    display: flex;
    align-items: center;
    gap: 6px;
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid var(--accent-border);
    border-radius: 7px;
    padding: 4px 8px;
  }

  .search-input {
    flex: 1;
    background: transparent;
    border: none;
    outline: none;
    color: #ffffff;
    font-size: 10.5px;
  }

  .search-input::placeholder {
    color: rgba(255, 255, 255, 0.4);
  }

  .search-submit-btn {
    background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
    border: none;
    border-radius: 4px;
    color: #0b1118;
    font-size: 9px;
    font-weight: 800;
    padding: 3px 8px;
    cursor: pointer;
    box-shadow: 0 0 8px var(--accent-glow-subtle);
  }

  .search-results-list {
    flex: 1;
    overflow-y: auto;
    margin-top: 6px;
    display: flex;
    flex-direction: column;
    gap: 3px;
    padding-right: 3px;
  }

  .search-results-list::-webkit-scrollbar {
    width: 3px;
  }

  .search-results-list::-webkit-scrollbar-thumb {
    background: var(--accent-border);
    border-radius: 2px;
  }

  .search-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 6px;
    border-radius: 5px;
    background: rgba(255, 255, 255, 0.035);
    border: 1px solid rgba(255, 255, 255, 0.05);
    transition: background 0.15s ease;
  }

  .search-item:hover {
    background: rgba(255, 255, 255, 0.08);
  }

  .search-item img {
    width: 24px;
    height: 24px;
    border-radius: 3px;
    object-fit: cover;
    flex-shrink: 0;
  }

  .search-item-info {
    flex: 1;
    min-width: 0;
  }

  .search-item-title {
    font-size: 9.5px;
    font-weight: 600;
    color: #ffffff;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .search-item-artist {
    font-size: 8px;
    color: #94a3b8;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .search-item-btns {
    display: flex;
    align-items: center;
    gap: 3px;
    flex-shrink: 0;
  }

  /* Toast & Badges */
  .toast-box {
    position: absolute;
    top: 8px;
    left: 50%;
    transform: translate(-50%, -14px);
    background: rgba(13, 23, 33, 0.94);
    backdrop-filter: blur(16px);
    border: 1px solid var(--accent-border);
    box-shadow: 0 0 16px var(--accent-glow-subtle), 0 4px 12px rgba(0, 0, 0, 0.6);
    color: #ffffff;
    font-size: 9px;
    font-weight: 700;
    padding: 3px 12px;
    border-radius: 16px;
    z-index: 100;
    pointer-events: none;
    opacity: 0;
    transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  }

  .toast-box.show {
    opacity: 1;
    transform: translate(-50%, 0);
  }

  .queue-badge {
    position: absolute;
    top: -4px;
    right: -5px;
    background: var(--accent-primary);
    color: #0b1118;
    font-size: 7px;
    font-weight: 900;
    border-radius: 6px;
    padding: 0 3px;
    min-width: 10px;
    height: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 0 6px var(--accent-glow);
  }

  .now-playing-tag {
    font-size: 7px;
    font-weight: 800;
    color: var(--accent-primary);
    background: rgba(34, 211, 238, 0.12);
    border: 1px solid var(--accent-border);
    border-radius: 3px;
    padding: 0 3px;
    margin-left: 4px;
    display: inline-block;
  }
</style>
</head>
<body>

<!-- Dynamic Desktop Wallpaper Blending Layer (Smoothly updates when wallpaper changes or widget is moved) -->
<div class="wallpaper-blend" id="wallpaper-blend" style="background-image: url('__WALLPAPER_BACKDROP__');"></div>

<!-- Desktop-Wide Flowing Waves & Spectrum Canvas -->
<canvas id="desktop-waves"></canvas>

<!-- Centered Glassmorphism Card -->
<div class="player-card-container">
  <div class="player-card" id="card">
    <!-- Album Artwork -->
    <div class="album-wrap">
      <img id="album-art" class="album-img" src="https://i.ytimg.com/vi/oC6brLXQe4I/hqdefault.jpg" alt="Art">
    </div>

    <!-- Main Content -->
    <div class="main-column">
      <!-- Title & Action Buttons -->
      <div class="track-row">
        <div class="track-meta">
          <div class="track-title" id="track-title">BABYMONSTER - DESERVE MV</div>
          <div class="track-source" id="track-source">
            <svg style="width:10px;height:10px;fill:#ef4444;" viewBox="0 0 24 24"><path d="M10 15l5.19-3L10 9v6m11.56-7.83c.13.47.22 1.1.28 1.9.07.8.1 1.49.1 2.09L22 12c0 2.19-.16 3.8-.44 4.83-.25.9-.83 1.48-1.73 1.73-.47.13-1.33.22-2.65.28-1.3.07-2.49.1-3.59.1L12 19c-4.19 0-6.8-.16-7.83-.44-.9-.25-1.48-.83-1.73-1.73-.13-.47-.22-1.1-.28-1.9-.07-.8-.1-1.49-.1-2.09L2 12c0-2.19.16-3.8.44-4.83.25-.9.83-1.48 1.73-1.73.47-.13 1.33-.22 2.65-.28 1.3-.07 2.49-.1 3.59-.1L12 5c4.19 0 6.8.16 7.83.44.9.25 1.48.83 1.73 1.73z"/></svg>
            <span>YouTube</span>
          </div>
        </div>
        <div class="top-actions">
          <button class="icon-btn" id="btn-search-toggle" title="Search Any Song">
            <svg viewBox="0 0 24 24"><path fill-rule="evenodd" d="M10.5 3.75a6.75 6.75 0 1 0 4.298 11.968l4.492 4.493a.75.75 0 1 0 1.06-1.06l-4.493-4.493A6.75 6.75 0 0 0 10.5 3.75Zm-5.25 6.75a5.25 5.25 0 1 1 10.5 0 5.25 5.25 0 0 1-10.5 0Z" clip-rule="evenodd" /></svg>
          </button>
          <button class="icon-btn" id="btn-minimize" title="Minimize">
            <svg viewBox="0 0 24 24"><path d="M5 12h14v2H5z"/></svg>
          </button>
          <button class="icon-btn" id="btn-close" title="Close">
            <svg viewBox="0 0 24 24"><path fill-rule="evenodd" d="M5.47 5.47a.75.75 0 0 1 1.06 0L12 10.94l5.47-5.47a.75.75 0 1 1 1.06 1.06L13.06 12l5.47 5.47a.75.75 0 1 1-1.06 1.06L12 13.06l-5.47 5.47a.75.75 0 0 1-1.06-1.06L10.94 12 5.47 6.53a.75.75 0 0 1 0-1.06Z" clip-rule="evenodd" /></svg>
          </button>
        </div>
      </div>

      <!-- Real-time Equalizer (34 Bars in Card) - Clickable to seek -->
      <div class="spectrum-container" id="spectrum-container" title="Click to seek">
        <!-- Bars generated by JS -->
      </div>

      <!-- Controls Row -->
      <div class="controls-row">
        <!-- Left: Volume Slider -->
        <div class="controls-left">
          <svg class="vol-icon" viewBox="0 0 24 24"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/></svg>
          <input type="range" class="vol-slider" id="vol-slider" min="0" max="1" step="0.01" value="__DEVICE_VOL__">
        </div>

        <!-- Center: Controls -->
        <div class="controls-center">
          <button class="ctrl-btn" id="btn-prev" title="Previous Track">
            <svg viewBox="0 0 24 24"><path d="M6 6h2v12H6zm3.5 6l8.5 6V6z"/></svg>
          </button>
          <button class="play-pause-btn" id="btn-play-pause" title="Play / Pause">
            <svg class="play-icon" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
            <svg class="pause-icon" style="display:none;" viewBox="0 0 24 24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>
          </button>
          <button class="ctrl-btn" id="btn-next" title="Next Track">
            <svg viewBox="0 0 24 24"><path d="M6 18l8.5-6L6 6v12zM16 6v12h2V6h-2z"/></svg>
          </button>
        </div>

        <!-- Right: Time, Shuffle, Repeat, Playlist -->
        <div class="controls-right">
          <span class="time-display" id="time-display">0:00 / 0:00</span>
          <button class="mini-btn" id="btn-shuffle" title="Shuffle">
            <svg viewBox="0 0 24 24"><path d="M10.59 9.17L5.41 4 4 5.41l5.17 5.17 1.42-1.41zM14.5 4l2.04 2.04L4 18.59 5.41 20 17.96 7.46 20 9.5V4h-5.5zm.33 9.41l-1.41 1.41 3.13 3.13L14.5 20H20v-5.5l-2.04 2.04-3.13-3.13z"/></svg>
          </button>
          <button class="mini-btn" id="btn-repeat" title="Repeat: Off">
            <svg id="repeat-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99" /></svg>
          </button>
          <button class="mini-btn" id="btn-playlist" title="Queue & Playlist" style="position:relative;">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 0 1 0 3.75H5.625a1.875 1.875 0 0 1 0-3.75Z" /></svg>
            <span class="queue-badge" id="queue-badge" style="display:none;">0</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Toast Notification -->
    <div class="toast-box" id="toast-box"></div>

    <!-- Glassmorphism Queue & Search Modal -->
    <div class="playlist-modal" id="playlist-modal">
      <div class="modal-top-bar">
        <div class="modal-tabs">
          <button class="modal-tab-btn active" id="tab-queue-btn">
            <svg class="h-icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 0 1 0 3.75H5.625a1.875 1.875 0 0 1 0-3.75Z" /></svg>
            <span>Queue</span>
            <span id="queue-tab-count">(0)</span>
          </button>
          <button class="modal-tab-btn" id="tab-search-btn">
            <svg class="h-icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>
            <span>Search & Add</span>
          </button>
        </div>
        <div class="modal-top-actions">
          <button class="loop-pill" id="btn-modal-loop" title="Toggle Looping Playlist">
            <svg class="h-icon-xs" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99" /></svg>
            <span id="modal-loop-text">Loop: OFF</span>
          </button>
          <button class="icon-btn" id="btn-modal-close" title="Close">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 18 18 6M6 6l12 12" /></svg>
          </button>
        </div>
      </div>

      <!-- Tab 1: Queue / Playlist -->
      <div class="tab-content active" id="view-queue">
        <div class="quick-add-bar">
          <div class="quick-add-input-wrap">
            <svg class="h-icon-xs quick-add-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>
            <input type="text" class="quick-add-input" id="quick-add-input" placeholder="Paste link or song name...">
          </div>
          <button class="btn-sm-action" id="btn-quick-next" title="Add as next to play">
            <svg class="h-icon-xs" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m5.25 4.5 7.5 7.5-7.5 7.5m6-15 7.5 7.5-7.5 7.5" /></svg>
            <span>Next</span>
          </button>
          <button class="btn-sm-action" id="btn-quick-queue" title="Add to end of queue">
            <svg class="h-icon-xs" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 4.5v15m7.5-7.5h-15" /></svg>
            <span>Queue</span>
          </button>
        </div>
        <div id="queue-now-playing-container"></div>
        <div class="queue-header-row">
          <span id="queue-count-display">Upcoming in Queue (0)</span>
          <button class="btn-sm-action btn-sm-del" id="btn-clear-queue" title="Clear all upcoming tracks">
            <svg class="h-icon-xs" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" /></svg>
            <span>Clear</span>
          </button>
        </div>
        <div class="queue-list" id="queue-list">
          <!-- Rendered via JS -->
        </div>
      </div>

      <!-- Tab 2: Search YouTube -->
      <div class="tab-content" id="view-search">
        <div class="search-bar">
          <input type="text" class="search-input" id="search-input" placeholder="Search any song, artist, or paste YouTube link...">
          <button class="search-submit-btn" id="search-submit-btn">FIND</button>
        </div>
        <div class="search-results-list" id="search-results-list">
          <div style="color:#94a3b8;font-size:10px;padding:15px;text-align:center;">Type a song or artist and hit Find</div>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- Standalone HTML5 Audio -->
<audio id="audio-player" preload="auto"></audio>

<script>
  const audio = document.getElementById('audio-player');
  const card = document.getElementById('card');
  const albumArt = document.getElementById('album-art');
  const trackTitle = document.getElementById('track-title');
  const trackSource = document.getElementById('track-source');
  const timeDisplay = document.getElementById('time-display');
  const btnPlayPause = document.getElementById('btn-play-pause');
  const playIcon = btnPlayPause.querySelector('.play-icon');
  const pauseIcon = btnPlayPause.querySelector('.pause-icon');
  const btnPrev = document.getElementById('btn-prev');
  const btnNext = document.getElementById('btn-next');
  const btnShuffle = document.getElementById('btn-shuffle');
  const btnRepeat = document.getElementById('btn-repeat');
  const btnPlaylist = document.getElementById('btn-playlist');
  const volSlider = document.getElementById('vol-slider');
  const btnClose = document.getElementById('btn-close');
  const btnMinimize = document.getElementById('btn-minimize');
  const btnSearchToggle = document.getElementById('btn-search-toggle');
  const playlistModal = document.getElementById('playlist-modal');
  const btnModalClose = document.getElementById('btn-modal-close');
  const btnModalLoop = document.getElementById('btn-modal-loop');
  const modalLoopText = document.getElementById('modal-loop-text');
  const tabQueueBtn = document.getElementById('tab-queue-btn');
  const tabSearchBtn = document.getElementById('tab-search-btn');
  const viewQueue = document.getElementById('view-queue');
  const viewSearch = document.getElementById('view-search');
  const queueNowPlayingContainer = document.getElementById('queue-now-playing-container');
  const queueList = document.getElementById('queue-list');
  const queueCountDisplay = document.getElementById('queue-count-display');
  const queueTabCount = document.getElementById('queue-tab-count');
  const queueBadge = document.getElementById('queue-badge');
  const btnClearQueue = document.getElementById('btn-clear-queue');
  const quickAddInput = document.getElementById('quick-add-input');
  const btnQuickNext = document.getElementById('btn-quick-next');
  const btnQuickQueue = document.getElementById('btn-quick-queue');
  const searchInput = document.getElementById('search-input');
  const searchSubmitBtn = document.getElementById('search-submit-btn');
  const searchResultsList = document.getElementById('search-results-list');
  const toastBox = document.getElementById('toast-box');
  const repeatIcon = document.getElementById('repeat-icon');
  const spectrumContainer = document.getElementById('spectrum-container');
  const canvas = document.getElementById('desktop-waves');
  const ctx = canvas.getContext('2d');
  const wallpaperBlend = document.getElementById('wallpaper-blend');

  let isPlaying = false;
  let isShuffle = false;
  let loopMode = 'off'; // 'off' | 'playlist' | 'track'
  let currentVidId = 'oC6brLXQe4I';
  let queue = [
    {
      id: 'oC6brLXQe4I',
      title: 'BABYMONSTER - DESERVE MV',
      artist: 'BABYMONSTER',
      thumb: 'https://i.ytimg.com/vi/oC6brLXQe4I/hqdefault.jpg'
    }
  ];
  let currentQueueIndex = 0;

  // Screen resolution for 1:1 background alignment
  const SCREEN_W = window.innerWidth;
  const SCREEN_H = __SCREEN_H__;

  let currentWindowX = __POS_X__;
  let currentWindowY = __POS_Y__;

  // Initialize 1:1 wallpaper alignment
  wallpaperBlend.style.backgroundSize = `${SCREEN_W}px ${SCREEN_H}px`;
  wallpaperBlend.style.backgroundPosition = `-${currentWindowX}px -${currentWindowY}px`;

  // Dynamic Live Wallpaper Update Function (called when Windows background changes)
  window.updateLiveWallpaper = function(newB64) {
    if (wallpaperBlend && newB64) {
      wallpaperBlend.style.backgroundImage = `url("${newB64}")`;
    }
  };

  // Sync exact position from Python
  window.syncPosition = function(x, y) {
    currentWindowX = x;
    currentWindowY = y;
    wallpaperBlend.style.backgroundPosition = `-${currentWindowX}px -${currentWindowY}px`;
  };

  // 34 Equalizer Bars in Card
  const NUM_BARS = 34;
  const bars = [];
  for (let i = 0; i < NUM_BARS; i++) {
    const bar = document.createElement('div');
    bar.className = 'spectrum-bar';
    spectrumContainer.appendChild(bar);
    bars.push(bar);
  }

  // Click on equalizer to seek
  spectrumContainer.addEventListener('click', (e) => {
    if (!audio.duration) return;
    const rect = spectrumContainer.getBoundingClientRect();
    const pos = (e.clientX - rect.left) / rect.width;
    audio.currentTime = pos * audio.duration;
  });

  function resizeCanvas() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  }
  resizeCanvas();
  window.addEventListener('resize', resizeCanvas);

  // Floating Aesthetic Particles & Audio Sparkles
  const particles = [];
  for (let p = 0; p < 60; p++) {
    particles.push({
      x: Math.random() * window.innerWidth,
      y: 60 + Math.random() * 125,
      radius: Math.random() * 2.2 + 0.8,
      speedX: Math.random() * 0.7 + 0.25,
      speedY: (Math.random() - 0.5) * 0.25,
      alpha: Math.random() * 0.65 + 0.25,
      sparklePhase: Math.random() * Math.PI * 2
    });
  }

  // Real-time Peak-Meter Gravity Arrays for Equalizer Bars
  const peakLevelsLeft = new Array(14).fill(0);
  const peakLevelsRight = new Array(20).fill(0);

  // REAL-TIME AUDIO-REACTIVE DATA & INTERPOLATION (via Native WASAPI Loopback WebSocket)
  let audioData = {
    vol: 0,
    bass: 0,
    vocal_mid: 0,
    vocal_high: 0,
    treble: 0,
    beat: 0,
    bars: new Array(34).fill(0),
    wave: new Array(64).fill(0)
  };

  let smoothVol = 0;
  let smoothBass = 0;
  let smoothVocalMid = 0;
  let smoothVocalHigh = 0;
  let smoothTreble = 0;
  let smoothBeat = 0;
  const smoothWave = new Array(64).fill(0);
  const smoothBars = new Array(34).fill(0);

  // Dynamic Live Palette Transition (Smoothly morphs colors when wallpaper changes)
  let currentPalette = __PALETTE_JSON__;
  let curPrimaryRGB = [...currentPalette.rgb];
  let targetPrimaryRGB = [...currentPalette.rgb];
  let curSecRGB = [...currentPalette.sec_rgb];
  let targetSecRGB = [...currentPalette.sec_rgb];

  window.updateLivePalette = function(newPalette) {
    if (!newPalette) return;
    currentPalette = newPalette;
    targetPrimaryRGB = [...newPalette.rgb];
    targetSecRGB = [...newPalette.sec_rgb];

    const root = document.documentElement;
    root.style.setProperty('--accent-primary', newPalette.primary);
    root.style.setProperty('--accent-secondary', newPalette.secondary);
    root.style.setProperty('--accent-glow', newPalette.glow);
    root.style.setProperty('--accent-glow-subtle', newPalette.glow_subtle);
    root.style.setProperty('--accent-glass', newPalette.glass);
    root.style.setProperty('--accent-border', newPalette.border);
  };

  function connectAudioWS() {
    const ws = new WebSocket('ws://127.0.0.1:8765');
    ws.onmessage = (e) => {
      try {
        const d = JSON.parse(e.data);
        if (d) audioData = d;
      } catch (_) {}
    };
    ws.onerror = () => { ws.close(); };
    ws.onclose = () => { setTimeout(connectAudioWS, 1000); };
  }
  connectAudioWS();

  // Helper: Traces a silky smooth continuous spline through points using midpoint quadratic curves
  function traceSmoothSpline(pts) {
    if (pts.length < 2) return;
    ctx.moveTo(pts[0].x, pts[0].y);
    for (let i = 0; i < pts.length - 1; i++) {
      const mx = (pts[i].x + pts[i + 1].x) / 2;
      const my = (pts[i].y + pts[i + 1].y) / 2;
      ctx.quadraticCurveTo(pts[i].x, pts[i].y, mx, my);
    }
    ctx.lineTo(pts[pts.length - 1].x, pts[pts.length - 1].y);
  }

  // Desktop-Wide Flowing Ribbon Waves & Atmospheric Spectrum
  let wavePhase = 0;
  function renderDesktopWaves() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const w = canvas.width;
    const h = canvas.height;

    // Smooth LERP of audio analysis parameters at 60 FPS
    smoothVol += (audioData.vol - smoothVol) * 0.24;
    smoothBass += (audioData.bass - smoothBass) * 0.30;
    smoothVocalMid += (audioData.vocal_mid - smoothVocalMid) * 0.34;
    smoothVocalHigh += (audioData.vocal_high - smoothVocalHigh) * 0.36;
    smoothTreble += (audioData.treble - smoothTreble) * 0.30;
    smoothBeat += (audioData.beat - smoothBeat) * 0.38;

    for (let i = 0; i < 64; i++) {
      const targetW = audioData.wave ? (audioData.wave[i] || 0) : 0;
      smoothWave[i] += (targetW - smoothWave[i]) * 0.44;
    }
    for (let i = 0; i < 34; i++) {
      const targetB = audioData.bars ? (audioData.bars[i] || 0) : 0;
      smoothBars[i] += (targetB - smoothBars[i]) * 0.32;
    }

    // Smoothly morph canvas RGB colors towards the wallpaper's target palette
    for (let c = 0; c < 3; c++) {
      curPrimaryRGB[c] += (targetPrimaryRGB[c] - curPrimaryRGB[c]) * 0.08;
      curSecRGB[c] += (targetSecRGB[c] - curSecRGB[c]) * 0.08;
    }
    const pR = Math.round(curPrimaryRGB[0]);
    const pG = Math.round(curPrimaryRGB[1]);
    const pB = Math.round(curPrimaryRGB[2]);

    const sR = Math.round(curSecRGB[0]);
    const sG = Math.round(curSecRGB[1]);
    const sB = Math.round(curSecRGB[2]);

    const pColor = `rgb(${pR}, ${pG}, ${pB})`;
    const sColor = `rgb(${sR}, ${sG}, ${sB})`;

    // Dynamic wave phase (calm breathing speed when quiet, energetic flow when playing)
    wavePhase += 0.012 + smoothVol * 0.042;

    const cardLeft = (w - 590) / 2;
    const cardRight = cardLeft + 590;

    // --- LAYER 0: ATMOSPHERIC AMBIENT WALLPAPER GLOW ---
    // Emits a soft, diffused celestial underglow that breathes with the bass and overall volume
    if (smoothVol > 0.015 || isPlaying) {
      const glowRadius = Math.min(w * 0.5, 320 + smoothBass * 220);
      const glowGrad = ctx.createRadialGradient(w / 2, h * 0.76, 30, w / 2, h * 0.76, glowRadius);
      const glowAlpha = Math.min(0.35, 0.06 + smoothVol * 0.22 + smoothBass * 0.14);
      glowGrad.addColorStop(0, `rgba(${pR}, ${pG}, ${pB}, ${glowAlpha})`);
      glowGrad.addColorStop(0.45, `rgba(${sR}, ${sG}, ${sB}, ${glowAlpha * 0.5})`);
      glowGrad.addColorStop(1, 'rgba(0, 0, 0, 0.0)');
      ctx.fillStyle = glowGrad;
      ctx.fillRect(0, 0, w, h);
    }

    // --- LAYER 1: ATMOSPHERIC STUDIO EQUALIZER BARS (With Floating Peak-Hold Beads) ---
    // Left side: Sub-Bass, 808s, & Low-Mids (bars 0 to 11)
    let bIdx = 0;
    for (let lx = cardLeft - 180; lx < cardLeft - 20; lx += 11) {
      const barVal = smoothBars[bIdx % 12] || 0;
      const dist = 1 - Math.abs(lx - (cardLeft - 100)) / 90;
      const hBar = Math.max(3.5, barVal * 36 * dist + (smoothVol > 0.02 ? 2.5 : 0));
      
      // Update floating peak-meter bead gravity
      if (hBar >= peakLevelsLeft[bIdx]) {
        peakLevelsLeft[bIdx] = hBar;
      } else {
        peakLevelsLeft[bIdx] = Math.max(3.5, peakLevelsLeft[bIdx] - 0.75);
      }

      // Rounded pill bar with dual-accent gradient
      const barGrad = ctx.createLinearGradient(0, h - 35, 0, h - 35 - hBar);
      barGrad.addColorStop(0, `rgba(${pR}, ${pG}, ${pB}, ${0.28 + barVal * 0.55})`);
      barGrad.addColorStop(1, `rgba(${sR}, ${sG}, ${sB}, ${0.75 + barVal * 0.25})`);
      ctx.fillStyle = barGrad;
      ctx.shadowBlur = 8 + barVal * 14;
      ctx.shadowColor = pColor;
      
      ctx.beginPath();
      if (ctx.roundRect) {
        ctx.roundRect(lx, h - 35 - hBar, 3.5, hBar, [2, 2, 0, 0]);
      } else {
        ctx.rect(lx, h - 35 - hBar, 3.5, hBar);
      }
      ctx.fill();

      // Floating luminous peak bead
      const peakY = h - 35 - peakLevelsLeft[bIdx] - 2.5;
      ctx.beginPath();
      ctx.arc(lx + 1.75, peakY, 1.6, 0, Math.PI * 2);
      ctx.fillStyle = '#ffffff';
      ctx.shadowBlur = 6;
      ctx.shadowColor = sColor;
      ctx.fill();

      bIdx++;
    }

    // Right side: Vocals, High-Mids & Treble (bars 16 to 29)
    bIdx = 16;
    for (let rx = cardRight + 20; rx < cardRight + 180; rx += 11) {
      const barVal = smoothBars[bIdx % 34] || 0;
      const dist = 1 - Math.abs(rx - (cardRight + 100)) / 90;
      const hBar = Math.max(3.5, barVal * 32 * dist + (smoothVol > 0.02 ? 2.5 : 0));

      const rIdx = bIdx - 16;
      if (hBar >= peakLevelsRight[rIdx]) {
        peakLevelsRight[rIdx] = hBar;
      } else {
        peakLevelsRight[rIdx] = Math.max(3.5, peakLevelsRight[rIdx] - 0.75);
      }

      const barGrad = ctx.createLinearGradient(0, h - 35, 0, h - 35 - hBar);
      barGrad.addColorStop(0, `rgba(${sR}, ${sG}, ${sB}, ${0.28 + barVal * 0.55})`);
      barGrad.addColorStop(1, `rgba(${pR}, ${pG}, ${pB}, ${0.75 + barVal * 0.25})`);
      ctx.fillStyle = barGrad;
      ctx.shadowBlur = 8 + barVal * 14;
      ctx.shadowColor = sColor;

      ctx.beginPath();
      if (ctx.roundRect) {
        ctx.roundRect(rx, h - 35 - hBar, 3.5, hBar, [2, 2, 0, 0]);
      } else {
        ctx.rect(rx, h - 35 - hBar, 3.5, hBar);
      }
      ctx.fill();

      // Floating luminous peak bead
      const peakY = h - 35 - peakLevelsRight[rIdx] - 2.5;
      ctx.beginPath();
      ctx.arc(rx + 1.75, peakY, 1.6, 0, Math.PI * 2);
      ctx.fillStyle = '#ffffff';
      ctx.shadowBlur = 6;
      ctx.shadowColor = pColor;
      ctx.fill();

      bIdx++;
    }

    // Horizontal Screen Gradient for all flowing ribbons (luminous white crest in center, neon wings)
    const ribbonGrad = ctx.createLinearGradient(0, 0, w, 0);
    ribbonGrad.addColorStop(0.0, `rgba(${pR}, ${pG}, ${pB}, 0.25)`);
    ribbonGrad.addColorStop(0.25, `rgba(${pR}, ${pG}, ${pB}, 0.85)`);
    ribbonGrad.addColorStop(0.5, '#ffffff');
    ribbonGrad.addColorStop(0.75, `rgba(${sR}, ${sG}, ${sB}, 0.85)`);
    ribbonGrad.addColorStop(1.0, `rgba(${sR}, ${sG}, ${sB}, 0.25)`);

    // --- LAYER 2: SUB-BASS & 808 TECTONIC PULSE SWELL ---
    // Deep rolling fluid undercurrent that expands powerfully during 808s and beat drops
    const bassAmp = (smoothBass * 42.0 + smoothBeat * 28.0 + 3.5);
    const bassBaseY = h * 0.77;
    const bassPts = [];
    const stepBass = Math.max(12, Math.floor(w / 55));
    for (let x = 0; x <= w + stepBass; x += stepBass) {
      const normX = x / w;
      const swell = Math.sin(normX * 4.2 - wavePhase * 1.1) * bassAmp;
      const octave = Math.cos(normX * 9.5 + wavePhase * 0.7) * (bassAmp * 0.32);
      const shockwave = Math.sin(normX * 13.0 - wavePhase * 1.8) * (smoothBeat * 14.0);
      bassPts.push({ x: x, y: bassBaseY + swell + octave + shockwave });
    }

    // Volumetric gradient underfill for bass
    ctx.beginPath();
    traceSmoothSpline(bassPts);
    ctx.lineTo(w, h);
    ctx.lineTo(0, h);
    ctx.closePath();
    const bassFillGrad = ctx.createLinearGradient(0, bassBaseY - 30, 0, h);
    const bassAlpha = Math.min(0.42, 0.06 + smoothVol * 0.26 + smoothBass * 0.22);
    bassFillGrad.addColorStop(0, `rgba(${pR}, ${pG}, ${pB}, ${bassAlpha})`);
    bassFillGrad.addColorStop(0.5, `rgba(10, 18, 30, ${bassAlpha * 0.65})`);
    bassFillGrad.addColorStop(1, 'rgba(10, 18, 30, 0.0)');
    ctx.fillStyle = bassFillGrad;
    ctx.shadowBlur = 18 + smoothBass * 22;
    ctx.shadowColor = `rgba(${pR}, ${pG}, ${pB}, 0.7)`;
    ctx.fill();

    // Smooth bass stroke
    ctx.beginPath();
    traceSmoothSpline(bassPts);
    ctx.strokeStyle = `rgba(${sR}, ${sG}, ${sB}, ${Math.min(0.9, 0.4 + smoothBass * 0.55)})`;
    ctx.lineWidth = 1.6 + smoothBeat * 2.4;
    ctx.shadowBlur = 12 + smoothBass * 20;
    ctx.shadowColor = pColor;
    ctx.stroke();

    // --- LAYER 3: INTERWOVEN COUNTER-HARMONIC SILK RIBBON ---
    // Braids dynamically over and under the vocal line with geometric fluidity
    const harmAmp = (smoothTreble * 22.0 + smoothVocalMid * 20.0 + 3.0);
    const harmBaseY = h * 0.72;
    const harmPts = [];
    const stepHarm = Math.max(10, Math.floor(w / 65));
    for (let x = 0; x <= w + stepHarm; x += stepHarm) {
      const normX = x / w;
      const counterWeave = Math.cos(normX * 8.0 + wavePhase * 1.6) * (harmAmp * 0.9);
      const subRipples = Math.sin(normX * 18.0 - wavePhase * 2.2) * (harmAmp * 0.38);
      harmPts.push({ x: x, y: harmBaseY + counterWeave + subRipples });
    }

    ctx.beginPath();
    traceSmoothSpline(harmPts);
    ctx.strokeStyle = `rgba(${sR}, ${sG}, ${sB}, ${Math.min(0.75, 0.3 + smoothVocalMid * 0.5)})`;
    ctx.lineWidth = 1.2 + smoothVocalHigh * 1.2;
    ctx.shadowBlur = 10 + smoothVocalMid * 16;
    ctx.shadowColor = sColor;
    ctx.stroke();

    // --- LAYER 4: PRIMARY VOCAL SPEECH & SINGING ENERGY RIBBON ---
    // Reacts dynamically to real time-domain vibrations, vocal formants, syllables, and words!
    const vocalAmp = (smoothVocalMid * 48.0 + smoothVocalHigh * 36.0 + smoothVol * 16.0);
    const speechBaseY = h * 0.67;
    const vocalPts = [];
    const peakCrests = [];
    const stepVocal = Math.max(8, Math.floor(w / 90));

    for (let x = 0; x <= w + stepVocal; x += stepVocal) {
      const normX = x / w;
      const waveIdx = Math.min(63, Math.floor(normX * 64));
      const nextIdx = Math.min(63, waveIdx + 1);
      const frac = (normX * 64) - waveIdx;
      const rawWave = smoothWave[waveIdx] * (1 - frac) + smoothWave[nextIdx] * frac;

      // Real time-domain voice oscillations + harmonic traveling wave + vocal flutter
      const voiceOscillation = rawWave * vocalAmp * 1.65;
      const flowingEnergy = Math.sin(normX * 8.5 - wavePhase * 1.4) * (vocalAmp * 0.32 + 3.8);
      const vocalFlutter = Math.sin(normX * 24.0 + wavePhase * 3.2) * (smoothVocalHigh * 5.5);
      const y = speechBaseY + voiceOscillation + flowingEnergy + vocalFlutter;
      vocalPts.push({ x: x, y: y });

      // Detect notable peaks for crest light beads
      if (vocalPts.length > 2) {
        const prev = vocalPts[vocalPts.length - 2];
        const prevPrev = vocalPts[vocalPts.length - 3];
        if (prev.y < prevPrev.y && prev.y < y && (speechBaseY - prev.y) > 12) {
          peakCrests.push({ x: prev.x, y: prev.y, energy: (speechBaseY - prev.y) });
        }
      }
    }

    // Luminous volumetric ambient fill under vocal line
    ctx.beginPath();
    traceSmoothSpline(vocalPts);
    ctx.lineTo(w, h);
    ctx.lineTo(0, h);
    ctx.closePath();
    const vocalFillGrad = ctx.createLinearGradient(0, speechBaseY - 25, 0, h);
    const vFillAlpha = Math.min(0.48, 0.08 + smoothVol * 0.30 + smoothBass * 0.22);
    vocalFillGrad.addColorStop(0, `rgba(${pR}, ${pG}, ${pB}, ${vFillAlpha})`);
    vocalFillGrad.addColorStop(0.4, `rgba(${sR}, ${sG}, ${sB}, ${vFillAlpha * 0.55})`);
    vocalFillGrad.addColorStop(1, 'rgba(10, 18, 30, 0.0)');
    ctx.fillStyle = vocalFillGrad;
    ctx.shadowBlur = 20 + smoothVocalMid * 24;
    ctx.shadowColor = `rgba(${pR}, ${pG}, ${pB}, 0.8)`;
    ctx.fill();

    // Dual-pass Neon Render for Vocal Ribbon:
    // Pass 1: Outer soft luminous aura
    ctx.beginPath();
    traceSmoothSpline(vocalPts);
    ctx.strokeStyle = `rgba(${pR}, ${pG}, ${pB}, ${Math.min(0.55, 0.2 + smoothVocalMid * 0.35)})`;
    ctx.lineWidth = 4.2 + smoothVocalHigh * 2.2;
    ctx.shadowBlur = 22 + smoothVocalMid * 26;
    ctx.shadowColor = pColor;
    ctx.stroke();

    // Pass 2: Razor-sharp fiber-optic core with horizontal gradient & luminous highlights
    ctx.beginPath();
    traceSmoothSpline(vocalPts);
    ctx.strokeStyle = ribbonGrad;
    ctx.lineWidth = 1.8 + smoothVocalHigh * 1.4;
    ctx.shadowBlur = 10 + smoothVocalMid * 18;
    ctx.shadowColor = '#ffffff';
    ctx.stroke();

    // Wave Crest Light Beads (Magical glowing stardust orbs on voice peaks)
    peakCrests.forEach(crest => {
      const beadRadius = Math.min(4.5, 1.8 + (crest.energy / 35) * 2.5 + smoothBeat * 1.5);
      ctx.beginPath();
      ctx.arc(crest.x, crest.y, beadRadius, 0, Math.PI * 2);
      ctx.fillStyle = '#ffffff';
      ctx.shadowBlur = 12 + smoothBeat * 10;
      ctx.shadowColor = sColor;
      ctx.fill();

      // Outer faint halo around crest bead
      ctx.beginPath();
      ctx.arc(crest.x, crest.y, beadRadius * 2.2, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(${sR}, ${sG}, ${sB}, 0.45)`;
      ctx.lineWidth = 0.8;
      ctx.stroke();
    });

    // --- LAYER 5: HIGH-TREBLE BRILLIANCE & AIR SHIMMER RIBBON ---
    // Micro-ripples reacting instantly to hi-hats, vocal sibilance ("s", "sh"), and acoustic air
    const trebleAmp = (smoothTreble * 18.0 + smoothVocalHigh * 14.0 + 2.0);
    const trebleBaseY = h * 0.85;
    const treblePts = [];
    const stepTreble = Math.max(9, Math.floor(w / 70));
    for (let x = 0; x <= w + stepTreble; x += stepTreble) {
      const normX = x / w;
      const shimmer1 = Math.sin(normX * 16.0 + wavePhase * 2.4) * (trebleAmp * 0.62);
      const shimmer2 = Math.sin(normX * 34.0 - wavePhase * 3.4) * (trebleAmp * 0.38);
      treblePts.push({ x: x, y: trebleBaseY + shimmer1 + shimmer2 });
    }

    ctx.beginPath();
    traceSmoothSpline(treblePts);
    ctx.strokeStyle = `rgba(${pR}, ${pG}, ${pB}, ${Math.min(0.85, 0.25 + smoothTreble * 0.65)})`;
    ctx.lineWidth = 1.0 + smoothTreble * 1.4;
    ctx.shadowBlur = 6 + smoothTreble * 14;
    ctx.shadowColor = pColor;
    ctx.stroke();

    // --- LAYER 6: LIVING AUDIO PARTICLES & CELESTIAL STARDUST ---
    // Particles drift smoothly across desktop, riding vertical acoustic tides and pulsing with the beat
    particles.forEach(p => {
      // Speed reacts to live volume and beats
      p.x += p.speedX * (0.6 + smoothVol * 2.6 + smoothBeat * 1.8);
      p.y += p.speedY;
      p.sparklePhase += 0.05 + smoothTreble * 0.12;

      // Wrap around screen boundaries seamlessly
      if (p.x > w + 10) p.x = -10;
      if (p.y < 40) p.y = h - 40;
      if (p.y > h - 20) p.y = 50;

      // Vertical wave tide oscillation
      const pY = p.y + Math.sin(p.x * 0.012 + wavePhase) * (6 + smoothBass * 14);
      const dynamicRadius = Math.max(0.6, p.radius + smoothBeat * 1.4 + Math.sin(p.sparklePhase) * 0.5);
      const dynamicAlpha = Math.min(1.0, p.alpha * (0.7 + Math.sin(p.sparklePhase) * 0.3) + smoothVol * 0.45);

      ctx.beginPath();
      ctx.arc(p.x, pY, dynamicRadius, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${sR}, ${sG}, ${sB}, ${dynamicAlpha})`;
      ctx.shadowBlur = 4 + smoothVol * 14;
      ctx.shadowColor = sColor;
      ctx.fill();

      // On beat peaks, draw mini sparkle cross on larger particles
      if (smoothBeat > 0.45 && p.radius > 1.8) {
        ctx.beginPath();
        ctx.moveTo(p.x - dynamicRadius * 1.8, pY);
        ctx.lineTo(p.x + dynamicRadius * 1.8, pY);
        ctx.moveTo(p.x, pY - dynamicRadius * 1.8);
        ctx.lineTo(p.x, pY + dynamicRadius * 1.8);
        ctx.strokeStyle = `rgba(255, 255, 255, ${dynamicAlpha * 0.8})`;
        ctx.lineWidth = 0.8;
        ctx.stroke();
      }
    });

    requestAnimationFrame(renderDesktopWaves);
  }
  requestAnimationFrame(renderDesktopWaves);

  // Equalizer in card (Driven 100% by live FFT audio frequency bands)
  function updateEqualizer() {
    const pR = Math.round(curPrimaryRGB[0]);
    const pG = Math.round(curPrimaryRGB[1]);
    const pB = Math.round(curPrimaryRGB[2]);
    const pColor = `rgba(${pR}, ${pG}, ${pB}, 0.85)`;

    for (let i = 0; i < NUM_BARS; i++) {
      const freqVal = smoothBars[i] || 0;
      const targetHeight = Math.max(3, Math.min(18, 3 + freqVal * 15));
      bars[i].style.height = targetHeight + 'px';
      bars[i].style.filter = freqVal > 0.08 ? `drop-shadow(0 0 ${4 + freqVal * 6}px ${pColor})` : 'none';
    }
    requestAnimationFrame(updateEqualizer);
  }
  requestAnimationFrame(updateEqualizer);

  // Instant Play / Pause toggle
  function togglePlay() {
    if (!audio.src) {
      btnPlayPause.classList.add('loading');
      window.pywebview && window.pywebview.api.play_id(currentVidId);
      return;
    }
    if (audio.paused) {
      audio.play().then(() => {
        isPlaying = true;
        playIcon.style.display = 'none';
        pauseIcon.style.display = 'block';
      }).catch(err => {
        console.log('Play error:', err);
      });
    } else {
      audio.pause();
      isPlaying = false;
      playIcon.style.display = 'block';
      pauseIcon.style.display = 'none';
    }
  }

  btnPlayPause.addEventListener('click', togglePlay);

  // Toast Notifications
  let toastTimer = null;
  function showToast(msg) {
    if (!toastBox) return;
    toastBox.textContent = msg;
    toastBox.classList.add('show');
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      toastBox.classList.remove('show');
    }, 2200);
  }
  window.showToast = showToast;

  // Repeat & Playlist Looping Modes
  function updateRepeatUI() {
    if (loopMode === 'playlist') {
      btnRepeat.classList.add('active');
      btnRepeat.title = 'Loop Playlist: ON (Continuous Loop)';
      btnModalLoop.classList.add('active');
      if (modalLoopText) modalLoopText.textContent = 'Loop: ON';
      repeatIcon.innerHTML = '<path d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99" />';
      audio.loop = false;
    } else if (loopMode === 'track') {
      btnRepeat.classList.add('active');
      btnRepeat.title = 'Repeat Current Track';
      btnModalLoop.classList.remove('active');
      if (modalLoopText) modalLoopText.textContent = 'Loop: OFF';
      repeatIcon.innerHTML = '<path d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99" /><circle cx="12" cy="12" r="2.8" fill="currentColor" stroke="none" />';
      audio.loop = true;
    } else {
      btnRepeat.classList.remove('active');
      btnRepeat.title = 'Repeat: Off';
      btnModalLoop.classList.remove('active');
      if (modalLoopText) modalLoopText.textContent = 'Loop: OFF';
      repeatIcon.innerHTML = '<path d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99" />';
      audio.loop = false;
    }
  }

  function cycleRepeatMode() {
    if (loopMode === 'off') {
      loopMode = 'playlist';
      showToast('Loop Playlist: ON');
    } else if (loopMode === 'playlist') {
      loopMode = 'track';
      showToast('Repeat Current Track');
    } else {
      loopMode = 'off';
      showToast('Repeat: OFF');
    }
    updateRepeatUI();
  }

  btnRepeat.addEventListener('click', cycleRepeatMode);

  btnModalLoop.addEventListener('click', () => {
    if (loopMode === 'playlist') {
      loopMode = 'off';
      showToast('Loop Playlist: OFF');
    } else {
      loopMode = 'playlist';
      showToast('Loop Playlist: ON');
    }
    updateRepeatUI();
  });

  btnShuffle.addEventListener('click', () => {
    isShuffle = !isShuffle;
    btnShuffle.classList.toggle('active', isShuffle);
    showToast(isShuffle ? 'Shuffle: ON' : 'Shuffle: OFF');
  });

  // Queue & Playlist Management
  function updateQueueBadge() {
    const upcomingCount = Math.max(0, queue.length - 1);
    queueTabCount.textContent = `(${queue.length})`;
    if (upcomingCount > 0) {
      queueBadge.style.display = 'flex';
      queueBadge.textContent = upcomingCount > 9 ? '9+' : upcomingCount;
    } else {
      queueBadge.style.display = 'none';
    }
  }

  function renderQueue() {
    updateQueueBadge();

    // 1. Render Dedicated Now Playing Hero Card inside Queue View
    if (currentQueueIndex >= 0 && currentQueueIndex < queue.length) {
      const curItem = queue[currentQueueIndex];
      queueNowPlayingContainer.innerHTML = `
        <div class="now-playing-hero">
          <img src="${curItem.thumb || 'https://i.ytimg.com/vi/' + curItem.id + '/hqdefault.jpg'}" alt="">
          <div class="now-playing-hero-info">
            <div class="now-playing-badge">
              <span class="mini-bars">
                <span class="mini-bar"></span>
                <span class="mini-bar"></span>
                <span class="mini-bar"></span>
              </span>
              Now Playing
            </div>
            <div class="now-playing-hero-title">${curItem.title}</div>
            <div class="now-playing-hero-artist">${curItem.artist || 'YouTube'}</div>
          </div>
        </div>
      `;
    } else {
      queueNowPlayingContainer.innerHTML = '';
    }

    // 2. Render Queue List
    queueList.innerHTML = '';

    if (queue.length === 0) {
      queueCountDisplay.textContent = 'Upcoming in Queue (0)';
      queueList.innerHTML = `
        <div class="queue-empty-state">
          <div class="queue-empty-icon">
            <svg class="h-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 0 1 0 3.75H5.625a1.875 1.875 0 0 1 0-3.75Z" /></svg>
          </div>
          <div style="font-size:9.5px;font-weight:700;color:#ffffff;">Queue is Empty</div>
          <div style="font-size:8px;color:#94a3b8;line-height:1.3;">Add songs using Quick Add or Search</div>
          <button class="btn-sm-action" id="btn-empty-search" style="margin-top:4px;padding:2px 8px;">
            <svg class="h-icon-xs" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>
            <span>Search Songs</span>
          </button>
        </div>
      `;
      const btnEmptySearch = document.getElementById('btn-empty-search');
      if (btnEmptySearch) {
        btnEmptySearch.addEventListener('click', () => switchTab('search'));
      }
      return;
    }

    const upcoming = Math.max(0, queue.length - 1);
    queueCountDisplay.textContent = `Upcoming in Queue (${upcoming} track${upcoming !== 1 ? 's' : ''})`;

    queue.forEach((item, idx) => {
      const isCur = (idx === currentQueueIndex);
      const div = document.createElement('div');
      div.className = `queue-item ${isCur ? 'active-item' : ''}`;
      
      div.innerHTML = `
        <div class="queue-item-idx">${idx + 1}</div>
        <img src="${item.thumb || 'https://i.ytimg.com/vi/' + item.id + '/hqdefault.jpg'}" alt="">
        <div class="queue-item-info">
          <div class="queue-item-title">${item.title}</div>
          <div class="queue-item-artist">${item.artist || 'YouTube'}</div>
        </div>
        <div class="queue-actions">
          ${!isCur ? `
            <button class="btn-icon-sm" title="Play Now" data-act="play" data-idx="${idx}">
              <svg class="h-icon-xs" viewBox="0 0 24 24" fill="currentColor"><path fill-rule="evenodd" d="M4.5 5.653c0-1.427 1.529-2.33 2.779-1.643l11.54 6.347c1.295.712 1.295 2.573 0 3.286L7.28 19.99c-1.25.687-2.779-.217-2.779-1.643V5.653Z" clip-rule="evenodd" /></svg>
            </button>
          ` : ''}
          ${idx > 0 ? `
            <button class="btn-icon-sm" title="Move Up" data-act="up" data-idx="${idx}">
              <svg class="h-icon-xs" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m4.5 15.75 7.5-7.5 7.5 7.5" /></svg>
            </button>
          ` : ''}
          ${idx < queue.length - 1 ? `
            <button class="btn-icon-sm" title="Move Down" data-act="down" data-idx="${idx}">
              <svg class="h-icon-xs" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m19.5 8.25-7.5 7.5-7.5-7.5" /></svg>
            </button>
          ` : ''}
          <button class="btn-icon-sm btn-del" title="Remove from queue" data-act="del" data-idx="${idx}">
            <svg class="h-icon-xs" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M6 18 18 6M6 6l12 12" /></svg>
          </button>
        </div>
      `;

      div.addEventListener('click', (e) => {
        const btn = e.target.closest('button');
        if (!btn) {
          if (!isCur) playQueueItem(idx);
          return;
        }
        e.stopPropagation();
        const act = btn.getAttribute('data-act');
        if (act === 'play') {
          playQueueItem(idx);
        } else if (act === 'up') {
          moveQueueItem(idx, -1);
        } else if (act === 'down') {
          moveQueueItem(idx, 1);
        } else if (act === 'del') {
          removeFromQueue(idx);
        }
      });

      queueList.appendChild(div);
    });
  }

  function addToQueue(item, playNext = false) {
    if (!item || !item.id) return;
    if (playNext) {
      const insertIdx = currentQueueIndex + 1;
      queue.splice(insertIdx, 0, item);
      showToast(`Play Next: ${item.title}`);
    } else {
      queue.push(item);
      showToast(`Added to Queue: ${item.title}`);
    }
    if (currentQueueIndex === -1) {
      currentQueueIndex = 0;
    }
    renderQueue();
  }

  function removeFromQueue(idx) {
    if (idx < 0 || idx >= queue.length) return;
    queue.splice(idx, 1);
    if (idx === currentQueueIndex) {
      if (currentQueueIndex >= queue.length) {
        currentQueueIndex = 0;
      }
      if (queue.length > 0) {
        playQueueItem(currentQueueIndex);
      }
    } else if (idx < currentQueueIndex) {
      currentQueueIndex--;
    }
    renderQueue();
    showToast('Removed from queue');
  }

  function clearQueue() {
    if (queue.length <= 1) {
      queue = [];
      currentQueueIndex = -1;
    } else if (currentQueueIndex >= 0 && currentQueueIndex < queue.length) {
      queue = [queue[currentQueueIndex]];
      currentQueueIndex = 0;
    } else {
      queue = [];
      currentQueueIndex = -1;
    }
    renderQueue();
    showToast('Queue cleared');
  }

  function moveQueueItem(idx, dir) {
    const targetIdx = idx + dir;
    if (targetIdx < 0 || targetIdx >= queue.length) return;
    const temp = queue[idx];
    queue[idx] = queue[targetIdx];
    queue[targetIdx] = temp;
    if (currentQueueIndex === idx) {
      currentQueueIndex = targetIdx;
    } else if (currentQueueIndex === targetIdx) {
      currentQueueIndex = idx;
    }
    renderQueue();
  }

  function playQueueItem(idx) {
    if (idx < 0 || idx >= queue.length) return;
    currentQueueIndex = idx;
    const item = queue[idx];
    currentVidId = item.id;
    window.updateTrackInfo(item.title, item.artist, item.thumb || `https://i.ytimg.com/vi/${item.id}/hqdefault.jpg`);
    btnPlayPause.classList.add('loading');
    window.pywebview && window.pywebview.api.play_id(item.id);
    renderQueue();
  }

  function playNextSong() {
    if (loopMode === 'track') {
      audio.currentTime = 0;
      audio.play();
      return;
    }

    if (isShuffle && queue.length > 1) {
      let randIdx = Math.floor(Math.random() * queue.length);
      if (randIdx === currentQueueIndex) randIdx = (randIdx + 1) % queue.length;
      playQueueItem(randIdx);
      return;
    }

    if (queue.length > 0) {
      if (currentQueueIndex + 1 < queue.length) {
        playQueueItem(currentQueueIndex + 1);
        return;
      } else if (loopMode === 'playlist') {
        // Continuous loop of custom playlist
        playQueueItem(0);
        showToast('Looping Playlist from start');
        return;
      }
    }

    // Queue finished and loop not active: fall back to YouTube Auto-Next related songs
    btnPlayPause.classList.add('loading');
    window.pywebview && window.pywebview.api.auto_next();
  }

  function playPrevSong() {
    if (audio.currentTime > 4) {
      audio.currentTime = 0;
      return;
    }

    if (queue.length > 0) {
      if (currentQueueIndex > 0) {
        playQueueItem(currentQueueIndex - 1);
        return;
      } else if (loopMode === 'playlist') {
        playQueueItem(queue.length - 1);
        return;
      }
    }

    btnPlayPause.classList.add('loading');
    window.pywebview && window.pywebview.api.prev_track();
  }

  btnNext.addEventListener('click', playNextSong);
  btnPrev.addEventListener('click', playPrevSong);
  btnClearQueue.addEventListener('click', clearQueue);

  btnQuickNext.addEventListener('click', () => {
    const q = quickAddInput.value.trim();
    if (!q) return;
    showToast('Fetching track...');
    window.pywebview && window.pywebview.api.search_and_queue(q, true);
    quickAddInput.value = '';
  });

  btnQuickQueue.addEventListener('click', () => {
    const q = quickAddInput.value.trim();
    if (!q) return;
    showToast('Fetching track...');
    window.pywebview && window.pywebview.api.search_and_queue(q, false);
    quickAddInput.value = '';
  });

  quickAddInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      btnQuickQueue.click();
    }
  });

  window.addTrackToQueueFromPython = function(item, playNext) {
    if (!item) return;
    addToQueue(item, playNext);
  };

  // Two-way device volume sync: widget slider <-> Windows master volume
  audio.volume = parseFloat(volSlider.value);

  volSlider.addEventListener('input', (e) => {
    const val = parseFloat(e.target.value);
    audio.volume = val;
    window.pywebview && window.pywebview.api.set_system_volume(val);
  });

  window.syncDeviceVolume = function(vol) {
    if (Math.abs(parseFloat(volSlider.value) - vol) > 0.015) {
      volSlider.value = vol;
      audio.volume = vol;
    }
  };

  audio.addEventListener('timeupdate', () => {
    const cur = formatTime(audio.currentTime);
    const dur = formatTime(audio.duration || 0);
    timeDisplay.textContent = `${cur} / ${dur}`;
  });

  // YOUTUBE AUTO-NEXT & NONSTOP PLAYBACK
  audio.addEventListener('ended', playNextSong);

  // Nonstop error recovery: if a stream fails, automatically move to next song
  audio.addEventListener('error', () => {
    console.log('Audio playback error, auto-recovering next song...');
    setTimeout(playNextSong, 1200);
  });

  function formatTime(sec) {
    if (isNaN(sec) || sec === 0) return '0:00';
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  }

  window.setStreamUrl = function(url) {
    btnPlayPause.classList.remove('loading');
    if (!url) return;
    audio.src = url;
    audio.volume = parseFloat(volSlider.value);
    audio.play().then(() => {
      isPlaying = true;
      playIcon.style.display = 'none';
      pauseIcon.style.display = 'block';
    }).catch(err => {
      console.log('Playback error:', err);
    });
  };

  // Called when song changes (auto-next or search select)
  window.updateTrackInfo = function(title, artist, thumb) {
    if (title) trackTitle.textContent = title;
    if (artist) trackSource.querySelector('span').textContent = artist;
    if (thumb) albumArt.src = thumb;
  };

  // Modal Navigation & Tabs
  let activeTab = 'queue';
  function switchTab(tab) {
    activeTab = tab;
    if (tab === 'queue') {
      tabQueueBtn.classList.add('active');
      tabSearchBtn.classList.remove('active');
      viewQueue.classList.add('active');
      viewSearch.classList.remove('active');
      renderQueue();
    } else {
      tabSearchBtn.classList.add('active');
      tabQueueBtn.classList.remove('active');
      viewSearch.classList.add('active');
      viewQueue.classList.remove('active');
      setTimeout(() => searchInput.focus(), 80);
    }
  }

  tabQueueBtn.addEventListener('click', () => switchTab('queue'));
  tabSearchBtn.addEventListener('click', () => switchTab('search'));

  function openModal(tab = 'queue') {
    card.classList.add('expanded');
    playlistModal.classList.add('active');
    switchTab(tab);
  }

  function closeModal() {
    playlistModal.classList.remove('active');
    card.classList.remove('expanded');
  }

  btnPlaylist.addEventListener('click', () => {
    if (playlistModal.classList.contains('active') && activeTab === 'queue') {
      closeModal();
    } else {
      openModal('queue');
    }
  });

  btnSearchToggle.addEventListener('click', () => {
    if (playlistModal.classList.contains('active') && activeTab === 'search') {
      closeModal();
    } else {
      openModal('search');
    }
  });

  btnModalClose.addEventListener('click', closeModal);

  searchSubmitBtn.addEventListener('click', () => {
    const query = searchInput.value.trim();
    if (!query) return;
    searchResultsList.innerHTML = '<div style="color:#94a3b8;font-size:10px;padding:15px;text-align:center;">Searching YouTube...</div>';
    window.pywebview && window.pywebview.api.search_songs(query);
  });

  searchInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      searchSubmitBtn.click();
    }
  });

  window.renderSearchResults = function(resultsJson) {
    try {
      const results = JSON.parse(resultsJson);
      searchResultsList.innerHTML = '';
      if (!results || results.length === 0) {
        searchResultsList.innerHTML = '<div style="color:#94a3b8;font-size:10px;padding:15px;text-align:center;">No results found. Try another query or paste URL.</div>';
        return;
      }
      results.forEach(item => {
        const div = document.createElement('div');
        div.className = 'search-item';
        div.innerHTML = `
          <img src="${item.thumb || 'https://i.ytimg.com/vi/' + item.id + '/hqdefault.jpg'}" alt="">
          <div class="search-item-info">
            <div class="search-item-title">${item.title}</div>
            <div class="search-item-artist">${item.artist || 'YouTube'}</div>
          </div>
          <div class="search-item-btns">
            <button class="btn-sm-action" data-act="play" title="Play Immediately">
              <svg class="h-icon-xs" viewBox="0 0 24 24" fill="currentColor"><path fill-rule="evenodd" d="M4.5 5.653c0-1.427 1.529-2.33 2.779-1.643l11.54 6.347c1.295.712 1.295 2.573 0 3.286L7.28 19.99c-1.25.687-2.779-.217-2.779-1.643V5.653Z" clip-rule="evenodd" /></svg>
              <span>Play</span>
            </button>
            <button class="btn-sm-action" data-act="next" title="Play Next after current song">
              <svg class="h-icon-xs" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m5.25 4.5 7.5 7.5-7.5 7.5m6-15 7.5 7.5-7.5 7.5" /></svg>
              <span>Next</span>
            </button>
            <button class="btn-sm-action" data-act="queue" title="Add to Queue">
              <svg class="h-icon-xs" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 4.5v15m7.5-7.5h-15" /></svg>
              <span>Queue</span>
            </button>
          </div>
        `;
        div.addEventListener('click', (e) => {
          const btn = e.target.closest('button');
          const act = btn ? btn.getAttribute('data-act') : 'play';
          if (act === 'play') {
            const insertIdx = currentQueueIndex + 1;
            queue.splice(insertIdx, 0, item);
            playQueueItem(insertIdx);
            showToast(`Now Playing: ${item.title}`);
          } else if (act === 'next') {
            addToQueue(item, true);
          } else if (act === 'queue') {
            addToQueue(item, false);
          }
        });
        searchResultsList.appendChild(div);
      });
    } catch(err) {
      console.error(err);
    }
  };

  // Initialize Repeat and Queue Display
  updateRepeatUI();
  renderQueue();

  btnClose.addEventListener('click', () => {
    window.pywebview && window.pywebview.api.close_window();
  });

  btnMinimize.addEventListener('click', () => {
    window.pywebview && window.pywebview.api.minimize_window();
  });

  // REAL-TIME DYNAMIC GLASS DRAGGING
  // As you drag, the background wallpaper position slides in real-time at 60 FPS!
  let isDragging = false;
  let startX = 0, startY = 0;
  let movePending = false;
  let targetDx = 0, targetDy = 0;

  card.addEventListener('mousedown', (e) => {
    if (e.target.closest('button') || e.target.closest('input') || e.target.closest('.search-modal') || e.target.closest('.spectrum-container')) return;
    isDragging = true;
    startX = e.screenX;
    startY = e.screenY;
  });

  document.addEventListener('mousemove', (e) => {
    if (!isDragging) return;
    const dx = e.screenX - startX;
    const dy = e.screenY - startY;
    if (dx === 0 && dy === 0) return;
    startX = e.screenX;
    startY = e.screenY;

    // 1. Real-time background flow: shift wallpaper background in perfect lockstep with desktop!
    currentWindowX += dx;
    currentWindowY += dy;
    wallpaperBlend.style.backgroundPosition = `-${currentWindowX}px -${currentWindowY}px`;

    // 2. Move OS window with RAF batching
    targetDx += dx;
    targetDy += dy;

    if (!movePending) {
      movePending = true;
      requestAnimationFrame(() => {
        if (targetDx !== 0 || targetDy !== 0) {
          window.pywebview && window.pywebview.api.move_window(targetDx, targetDy);
          targetDx = 0;
          targetDy = 0;
        }
        movePending = false;
      });
    }
  });

  document.addEventListener('mouseup', () => {
    if (isDragging) {
      isDragging = false;
      if (targetDx !== 0 || targetDy !== 0) {
        window.pywebview && window.pywebview.api.move_window(targetDx, targetDy);
        targetDx = 0;
        targetDy = 0;
      }
      setTimeout(() => {
        window.pywebview && window.pywebview.api.on_drag_end();
      }, 40);
    }
  });
</script>
</body>
</html>
"""

class MusicAPI:
    def __init__(self, win_holder):
        self.win_holder = win_holder
        self.current_artist = "BABYMONSTER"
        self.current_title = "DESERVE"
        self.history = [
            {"id": "oC6brLXQe4I", "title": "BABYMONSTER - DESERVE MV", "artist": "BABYMONSTER", "thumb": "https://i.ytimg.com/vi/oC6brLXQe4I/hqdefault.jpg"}
        ]
        self.history_index = 0
        self.played_ids = set(["oC6brLXQe4I"])
        
        extractor_args = {
            'youtube': {
                'player_client': ['android', 'ios', 'web']
            }
        }
        self.ydl_opts_search = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'extractor_args': extractor_args,
        }
        self.ydl_opts_stream = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'extractor_args': extractor_args,
        }

    def set_system_volume(self, vol):
        set_system_volume(vol)

    def close_window(self):
        w = self.win_holder[0]
        if w:
            w.destroy()

    def minimize_window(self):
        w = self.win_holder[0]
        if w:
            try:
                w.minimize()
            except Exception:
                pass

    def move_window(self, dx, dy):
        w = self.win_holder[0]
        if w:
            try:
                w.move(w.x + int(dx), w.y + int(dy))
            except Exception:
                pass

    def on_drag_end(self):
        w = self.win_holder[0]
        if w:
            w.evaluate_js(f"window.syncPosition({w.x}, {w.y});")

    def search_songs(self, query):
        threading.Thread(target=self._search_async, args=(query,), daemon=True).start()

    def search_and_queue(self, query, play_next=False):
        threading.Thread(target=self._search_and_queue_async, args=(query, play_next), daemon=True).start()

    def _search_and_queue_async(self, query, play_next):
        w = self.win_holder[0]
        if not w:
            return
        try:
            is_url = ("youtube.com" in query or "youtu.be" in query or query.startswith("http"))
            target = query if is_url else f"ytsearch1:{query}"
            with yt_dlp.YoutubeDL(self.ydl_opts_search) as ydl:
                info = ydl.extract_info(target, download=False)
                entry = info.get('entries', [info])[0] if 'entries' in info and info['entries'] else info
                title = entry.get('title', 'YouTube Track').replace(' (Official Video)', '').replace(' [Official Audio]', '').replace(' (Official Music Video)', '')
                artist = entry.get('uploader') or entry.get('channel') or 'YouTube'
                vid_id = entry.get('id', '')
                thumb = f"https://i.ytimg.com/vi/{vid_id}/hqdefault.jpg" if vid_id else ''
                track_data = {"id": vid_id, "title": title, "artist": artist, "thumb": thumb}
                w.evaluate_js(f"window.addTrackToQueueFromPython({json.dumps(track_data)}, {json.dumps(play_next)});")
        except Exception:
            w.evaluate_js("window.showToast('Could not resolve link');")

    def _search_async(self, query):
        w = self.win_holder[0]
        if not w:
            return
        results = []
        try:
            is_url = ("youtube.com" in query or "youtu.be" in query or query.startswith("http"))
            target = query if is_url else f"ytsearch8:{query}"
            opts = dict(self.ydl_opts_search)
            if is_url and "list=" in query:
                opts['noplaylist'] = False
                opts['playlist_items'] = '1-15'
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(target, download=False)
                entries = info.get('entries', [info]) if 'entries' in info else [info]
                for entry in entries:
                    if not entry:
                        continue
                    title = entry.get('title', 'Unknown Title')
                    title = title.replace(' (Official Video)', '').replace(' [Official Audio]', '').replace(' (Official Music Video)', '')
                    artist = entry.get('uploader') or entry.get('channel') or 'YouTube'
                    vid_id = entry.get('id', '')
                    thumb = f"https://i.ytimg.com/vi/{vid_id}/hqdefault.jpg" if vid_id else ''
                    results.append({"id": vid_id, "title": title, "artist": artist, "thumb": thumb})
        except Exception:
            pass
        
        js = f"window.renderSearchResults({json.dumps(json.dumps(results))});"
        w.evaluate_js(js)

    def play_id(self, vid_id):
        threading.Thread(target=self._resolve_and_play, args=(vid_id,), daemon=True).start()

    def _resolve_and_play(self, vid_id):
        w = self.win_holder[0]
        if not w:
            return
        try:
            url = f"https://www.youtube.com/watch?v={vid_id}"
            with yt_dlp.YoutubeDL(self.ydl_opts_stream) as ydl:
                info = ydl.extract_info(url, download=False)
                stream_url = info.get('url', '')
                title = info.get('title', 'YouTube Music')
                title = title.replace(' (Official Video)', '').replace(' [Official Audio]', '').replace(' (Official Music Video)', '')
                artist = info.get('uploader') or info.get('channel') or 'YouTube'
                thumb = f"https://i.ytimg.com/vi/{vid_id}/hqdefault.jpg"
                self.current_title = title
                self.current_artist = artist
                self.played_ids.add(vid_id)
                w.evaluate_js(f"window.updateTrackInfo({json.dumps(title)}, {json.dumps(artist)}, {json.dumps(thumb)});")
                w.evaluate_js(f"window.setStreamUrl({json.dumps(stream_url)});")
        except Exception as e:
            print(f"[yt-dlp] Stream error for {vid_id}: {e}")
            w.evaluate_js("window.showToast('Could not stream track');")
            w.evaluate_js("window.setStreamUrl('');")

    def auto_next(self):
        """Automatically selects and plays the next related YouTube track (Autoplay Non-stop)."""
        threading.Thread(target=self._auto_next_async, daemon=True).start()

    def _auto_next_async(self):
        w = self.win_holder[0]
        if not w:
            return
        # Query YouTube for related tracks based on current artist/title
        search_query = f"{self.current_artist} songs"
        next_track = None
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts_search) as ydl:
                info = ydl.extract_info(f"ytsearch10:{search_query}", download=False)
                for entry in info.get('entries', []):
                    eid = entry.get('id')
                    if eid and eid not in self.played_ids:
                        next_track = entry
                        break
                # If all played, pick any
                if not next_track and info.get('entries'):
                    next_track = info['entries'][0]
        except Exception:
            pass

        if next_track:
            nid = next_track.get('id')
            title = next_track.get('title', 'Next Track').replace(' (Official Video)', '').replace(' [Official Audio]', '')
            artist = next_track.get('uploader') or self.current_artist
            thumb = f"https://i.ytimg.com/vi/{nid}/hqdefault.jpg"
            self.history.append({"id": nid, "title": title, "artist": artist, "thumb": thumb})
            self.history_index = len(self.history) - 1
            self.play_id(nid)

    def next_track(self):
        if self.history and self.history_index < len(self.history) - 1:
            self.history_index += 1
            s = self.history[self.history_index]
            self.play_id(s['id'])
        else:
            self.auto_next()

    def prev_track(self):
        if self.history and self.history_index > 0:
            self.history_index -= 1
            s = self.history[self.history_index]
            self.play_id(s['id'])


def wallpaper_watcher(api):
    """Monitors active desktop wallpaper changes and updates full wallpaper image & dynamic aesthetic palette."""
    last_wp_path = ""
    last_mtime = 0

    while True:
        try:
            wp_path = get_active_wallpaper_path()
            if wp_path and os.path.exists(wp_path):
                mtime = os.path.getmtime(wp_path)
                if wp_path != last_wp_path or mtime != last_mtime:
                    last_wp_path = wp_path
                    last_mtime = mtime
                    b64 = ""
                    for _ in range(3):
                        time.sleep(0.2)
                        b64 = get_full_wallpaper_b64()
                        if b64:
                            break
                    palette = extract_aesthetic_palette(wp_path)
                    w = api.win_holder[0]
                    if w:
                        if b64:
                            w.evaluate_js(f"window.updateLiveWallpaper({json.dumps(b64)});")
                        if palette:
                            w.evaluate_js(f"window.updateLivePalette({json.dumps(palette)});")
        except Exception:
            pass
        time.sleep(0.5)


def volume_watcher(api):
    """Monitors Windows master volume and updates the visualizer slider in real time."""
    try:
        import comtypes
        comtypes.CoInitialize()
    except Exception:
        pass
    last_vol = -1.0
    while True:
        try:
            cur = get_system_volume()
            if abs(cur - last_vol) > 0.015:
                last_vol = cur
                w = api.win_holder[0]
                if w:
                    w.evaluate_js(f"window.syncDeviceVolume({cur});")
        except Exception:
            pass
        time.sleep(0.35)


def main():
    win_holder = [None]
    api = MusicAPI(win_holder)

    # Start real-time native WASAPI loopback audio engine & FFT analyzer
    audio_engine = AudioEngine(port=AUDIO_WS_PORT)
    audio_engine.start()

    # Query active Windows device master volume to match user's exact system level
    dev_vol = get_system_volume()

    # Sample and extract the best aesthetic color palette from the current wallpaper
    wp_path = get_active_wallpaper_path()
    palette = extract_aesthetic_palette(wp_path)

    # Load high-quality full resized wallpaper image
    wp_b64 = get_full_wallpaper_b64()
    final_html = (HTML_TEMPLATE
                  .replace('__WALLPAPER_BACKDROP__', wp_b64)
                  .replace('__SCREEN_H__', str(SCREEN_H))
                  .replace('__POS_X__', str(POS_X))
                  .replace('__POS_Y__', str(POS_Y))
                  .replace('__DEVICE_VOL__', str(dev_vol))
                  .replace('__ACCENT_PRIMARY__', palette['primary'])
                  .replace('__ACCENT_SECONDARY__', palette['secondary'])
                  .replace('__ACCENT_GLOW__', palette['glow'])
                  .replace('__ACCENT_GLOW_SUBTLE__', palette['glow_subtle'])
                  .replace('__ACCENT_GLASS__', palette['glass'])
                  .replace('__ACCENT_BORDER__', palette['border'])
                  .replace('__PALETTE_JSON__', json.dumps(palette)))

    # Desktop-wide visualizer window: on_top=False ensures it NEVER overlaps working apps
    w = webview.create_window(
        title='Desktop Music Visualizer',
        html=final_html,
        width=VIS_W,
        height=VIS_H,
        x=POS_X,
        y=POS_Y,
        frameless=True,
        resizable=False,
        on_top=False,
        js_api=api,
        background_color='#0f141c'
    )
    win_holder[0] = w

    threading.Thread(target=wallpaper_watcher, args=(api,), daemon=True).start()
    threading.Thread(target=volume_watcher, args=(api,), daemon=True).start()

    webview.start()

if __name__ == '__main__':
    main()
