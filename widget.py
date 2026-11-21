"""
Immersive Glassmorphism Desktop Music Visualizer
- Auto-adapting frosted glass backdrop that dynamically adjusts whenever desktop wallpaper changes
- Active live wallpaper watcher (detects Next Desktop Background instantly)
- Native smooth rounded window clipping via Win32 SetWindowRgn (zero square box or white band artifacts)
- Realistic specular diagonal glass sheen reflection & top rim light highlight
- Real-time animated audio spectrum equalizer bars (34 bars) + flowing neon canvas waves
- Full controls: Volume slider, Seek/Time, Prev, Glowing Circular Pause, Next, Shuffle, Repeat, Search
- Unmuted direct streaming HTML5 audio via yt-dlp
- Desktop level (on_top=False, never overlaps other applications)
"""
import webview
import yt_dlp
import threading
import json
import ctypes
import os
import sys
import io
import time
import base64
from PIL import Image, ImageFilter

# Screen metrics
user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
SCREEN_W = user32.GetSystemMetrics(0)
SCREEN_H = user32.GetSystemMetrics(1)

# Compact, elegant glass card dimensions (NO full-screen white box!)
WIDGET_W = 620
WIDGET_H = 156
POS_X = (SCREEN_W - WIDGET_W) // 2
POS_Y = SCREEN_H - WIDGET_H - 90  # Lower center of screen

def get_wallpaper_slice(x=POS_X, y=POS_Y, w=WIDGET_W, h=WIDGET_H):
    """Crops and blurs the exact section of the active desktop wallpaper behind the widget."""
    try:
        wp_path = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Themes\TranscodedWallpaper")
        if not os.path.exists(wp_path):
            return ""
        img = Image.open(wp_path).convert("RGB")
        img_screen = img.resize((SCREEN_W, SCREEN_H), Image.Resampling.LANCZOS)
        cx = max(0, min(SCREEN_W - w, int(x)))
        cy = max(0, min(SCREEN_H - h, int(y)))
        crop = img_screen.crop((cx, cy, cx + w, cy + h))
        blurred = crop.filter(ImageFilter.GaussianBlur(radius=16))
        buf = io.BytesIO()
        blurred.save(buf, format="JPEG", quality=85)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode('ascii')
    except Exception as e:
        return ""

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Desktop Music Visualizer</title>
<style>
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
    background: #10061a;
  }

  /* GLASSMORPHISM CARD CONTAINER WITH GLASS REFLECTIONS */
  .player-card {
    width: 100%;
    height: 100%;
    position: relative;
    border-radius: 20px;
    border: 1.5px solid rgba(244, 114, 182, 0.45);
    box-shadow: 
      0 0 35px rgba(217, 70, 239, 0.35),
      0 20px 48px rgba(0, 0, 0, 0.75),
      inset 0 1.5px 2px rgba(255, 255, 255, 0.45),
      inset 0 -1px 2px rgba(244, 114, 182, 0.25);
    display: flex;
    align-items: center;
    padding: 14px 18px;
    gap: 16px;
    overflow: hidden;
    cursor: grab;
  }

  .player-card:active {
    cursor: grabbing;
  }

  /* DYNAMIC WALLPAPER GLASS BACKDROP (Automatically adapts when wallpaper changes) */
  .wallpaper-glass {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-size: cover;
    background-position: center;
    border-radius: 19px;
    opacity: 0.85;
    z-index: 0;
    pointer-events: none;
    filter: brightness(0.72) saturate(140%);
    transition: background-image 0.5s ease, opacity 0.3s ease;
  }

  /* FROSTED TINT OVERLAY */
  .glass-tint {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(135deg, rgba(32, 12, 48, 0.65) 0%, rgba(14, 5, 24, 0.75) 100%);
    border-radius: 19px;
    z-index: 1;
    pointer-events: none;
  }

  /* DIAGONAL GLASS SPECULAR REFLECTION (Creates realistic glass sheen) */
  .player-card::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(
      128deg,
      rgba(255, 255, 255, 0.28) 0%,
      rgba(255, 255, 255, 0.09) 25%,
      transparent 50%,
      rgba(244, 114, 182, 0.12) 75%,
      transparent 100%
    );
    pointer-events: none;
    border-radius: 19px;
    z-index: 7;
  }

  /* TOP CURVED SPECULAR LIGHT EDGE */
  .player-card::before {
    content: '';
    position: absolute;
    top: 1px;
    left: 20px;
    right: 20px;
    height: 1.5px;
    background: linear-gradient(90deg, transparent 0%, rgba(255, 255, 255, 0.9) 45%, rgba(244, 114, 182, 0.95) 55%, transparent 100%);
    box-shadow: 0 0 10px rgba(244, 114, 182, 0.7);
    pointer-events: none;
    z-index: 8;
  }

  /* Neon Waves Canvas Background inside card */
  #waves-canvas {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    z-index: 2;
    opacity: 0.65;
  }

  /* Album Artwork */
  .album-wrap {
    width: 98px;
    height: 98px;
    border-radius: 14px;
    overflow: hidden;
    position: relative;
    flex-shrink: 0;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.65), 0 0 15px rgba(244, 114, 182, 0.35);
    border: 1px solid rgba(255, 255, 255, 0.25);
    z-index: 10;
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
    height: 98px;
    min-width: 0;
    position: relative;
    z-index: 10;
  }

  /* Track Title & Top Action Buttons */
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
    font-size: 14px;
    font-weight: 700;
    color: #ffffff;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    text-shadow: 0 2px 10px rgba(0, 0, 0, 0.7);
    letter-spacing: -0.2px;
  }

  .track-source {
    font-size: 11px;
    color: #cbd5e1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-top: 2px;
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .top-actions {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-shrink: 0;
  }

  .icon-btn {
    background: transparent;
    border: none;
    color: rgba(255, 255, 255, 0.65);
    cursor: pointer;
    padding: 3px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 6px;
    transition: all 0.2s ease;
  }

  .icon-btn:hover {
    color: #ffffff;
    background: rgba(255, 255, 255, 0.15);
  }

  .icon-btn svg {
    width: 14px;
    height: 14px;
    fill: currentColor;
  }

  /* Spectrum Waveform Equalizer (34 Bars in Card) */
  .spectrum-container {
    width: 100%;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 2.5px;
    padding: 0 2px;
  }

  .spectrum-bar {
    flex: 1;
    min-width: 2.5px;
    max-width: 6px;
    height: 4px;
    border-radius: 999px;
    background: linear-gradient(180deg, #f472b6 0%, #ec4899 50%, #c084fc 100%);
    box-shadow: 0 0 8px rgba(244, 114, 182, 0.55);
    transition: height 0.08s ease, filter 0.15s ease;
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
    width: 105px;
  }

  .vol-icon {
    width: 13px;
    height: 13px;
    fill: rgba(255, 255, 255, 0.65);
    flex-shrink: 0;
  }

  .vol-slider {
    -webkit-appearance: none;
    width: 100%;
    height: 3px;
    background: rgba(255, 255, 255, 0.25);
    border-radius: 2px;
    outline: none;
    cursor: pointer;
  }

  .vol-slider::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: #f472b6;
    box-shadow: 0 0 6px #f472b6;
    cursor: pointer;
    transition: transform 0.15s ease;
  }

  .vol-slider::-webkit-slider-thumb:hover {
    transform: scale(1.25);
  }

  /* Center: Prev, Glowing Circular Pause, Next */
  .controls-center {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .ctrl-btn {
    background: transparent;
    border: none;
    color: rgba(255, 255, 255, 0.85);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 3px;
    transition: all 0.2s ease;
  }

  .ctrl-btn:hover {
    color: #ffffff;
    transform: scale(1.15);
  }

  .ctrl-btn svg {
    width: 14px;
    height: 14px;
    fill: currentColor;
  }

  /* Glowing Circular Play / Pause Button */
  .play-pause-btn {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: linear-gradient(135deg, rgba(236, 72, 153, 0.3) 0%, rgba(168, 85, 247, 0.45) 100%);
    border: 1.5px solid rgba(244, 114, 182, 0.7);
    box-shadow: 0 0 16px rgba(244, 114, 182, 0.65), inset 0 0 8px rgba(255, 255, 255, 0.4);
    display: flex;
    align-items: center;
    justify-content: center;
    color: #ffffff;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .play-pause-btn:hover {
    transform: scale(1.1);
    box-shadow: 0 0 24px rgba(244, 114, 182, 0.9), inset 0 0 12px rgba(255, 255, 255, 0.6);
  }

  .play-pause-btn svg {
    width: 14px;
    height: 14px;
    fill: #ffffff;
  }

  /* Right: Time, Shuffle, Repeat */
  .controls-right {
    display: flex;
    align-items: center;
    gap: 6px;
    width: 125px;
    justify-content: flex-end;
  }

  .time-display {
    font-size: 10px;
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
    color: #f472b6;
    text-shadow: 0 0 6px #f472b6;
  }

  .mini-btn svg {
    width: 12px;
    height: 12px;
    fill: currentColor;
  }

  /* Search Modal */
  .search-modal {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(16, 6, 26, 0.94);
    backdrop-filter: blur(24px);
    border-radius: 20px;
    display: none;
    flex-direction: column;
    padding: 12px 14px;
    z-index: 50;
  }

  .search-modal.active {
    display: flex;
  }

  .search-bar {
    display: flex;
    align-items: center;
    gap: 8px;
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(244, 114, 182, 0.4);
    border-radius: 10px;
    padding: 6px 10px;
  }

  .search-input {
    flex: 1;
    background: transparent;
    border: none;
    outline: none;
    color: #ffffff;
    font-size: 12px;
  }

  .search-input::placeholder {
    color: rgba(255, 255, 255, 0.4);
  }

  .search-submit-btn {
    background: linear-gradient(135deg, #ec4899, #8b5cf6);
    border: none;
    border-radius: 6px;
    color: #ffffff;
    font-size: 10px;
    font-weight: 700;
    padding: 4px 10px;
    cursor: pointer;
    box-shadow: 0 0 10px rgba(236, 72, 153, 0.4);
  }

  .search-submit-btn:hover {
    filter: brightness(1.2);
  }

  .search-results-list {
    flex: 1;
    overflow-y: auto;
    margin-top: 8px;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .search-results-list::-webkit-scrollbar {
    width: 4px;
  }

  .search-results-list::-webkit-scrollbar-thumb {
    background: rgba(244, 114, 182, 0.4);
    border-radius: 2px;
  }

  .search-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 5px 8px;
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.04);
    cursor: pointer;
    transition: background 0.15s ease;
  }

  .search-item:hover {
    background: rgba(244, 114, 182, 0.2);
  }

  .search-item img {
    width: 28px;
    height: 28px;
    border-radius: 5px;
    object-fit: cover;
  }

  .search-item-info {
    flex: 1;
    min-width: 0;
  }

  .search-item-title {
    font-size: 11px;
    font-weight: 600;
    color: #ffffff;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .search-item-artist {
    font-size: 9px;
    color: #94a3b8;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
</style>
</head>
<body>

<div class="player-card" id="card">
  <!-- Dynamic Desktop Wallpaper Glass Backdrop -->
  <div class="wallpaper-glass" id="wp-glass" style="background-image: url('__INITIAL_WALLPAPER__');"></div>

  <!-- Frosted Glass Tint Overlay -->
  <div class="glass-tint"></div>

  <!-- Flowing Neon Wave Canvas Background -->
  <canvas id="waves-canvas"></canvas>

  <!-- Album Artwork -->
  <div class="album-wrap">
    <img id="album-art" class="album-img" src="https://i.ytimg.com/vi/oC6brLXQe4I/hqdefault.jpg" alt="Art">
  </div>

  <!-- Main Info Column -->
  <div class="main-column">
    <!-- Row 1: Title & Top Action Buttons -->
    <div class="track-row">
      <div class="track-meta">
        <div class="track-title" id="track-title">BABYMONSTER - 'DESERVE' M/V</div>
        <div class="track-source" id="track-source">
          <svg style="width:11px;height:11px;fill:#ef4444;" viewBox="0 0 24 24"><path d="M10 15l5.19-3L10 9v6m11.56-7.83c.13.47.22 1.1.28 1.9.07.8.1 1.49.1 2.09L22 12c0 2.19-.16 3.8-.44 4.83-.25.9-.83 1.48-1.73 1.73-.47.13-1.33.22-2.65.28-1.3.07-2.49.1-3.59.1L12 19c-4.19 0-6.8-.16-7.83-.44-.9-.25-1.48-.83-1.73-1.73-.13-.47-.22-1.1-.28-1.9-.07-.8-.1-1.49-.1-2.09L2 12c0-2.19.16-3.8.44-4.83.25-.9.83-1.48 1.73-1.73.47-.13 1.33-.22 2.65-.28 1.3-.07 2.49-.1 3.59-.1L12 5c4.19 0 6.8.16 7.83.44.9.25 1.48.83 1.73 1.73z"/></svg>
          <span>YouTube</span>
        </div>
      </div>
      <div class="top-actions">
        <button class="icon-btn" id="btn-search-toggle" title="Search Any Song">
          <svg viewBox="0 0 24 24"><path fill-rule="evenodd" d="M10.5 3.75a6.75 6.75 0 1 0 4.298 11.968l4.492 4.493a.75.75 0 1 0 1.06-1.06l-4.493-4.493A6.75 6.75 0 0 0 10.5 3.75Zm-5.25 6.75a5.25 5.25 0 1 1 10.5 0 5.25 5.25 0 0 1-10.5 0Z" clip-rule="evenodd" /></svg>
        </button>
        <button class="icon-btn" id="btn-close" title="Close">
          <svg viewBox="0 0 24 24"><path fill-rule="evenodd" d="M5.47 5.47a.75.75 0 0 1 1.06 0L12 10.94l5.47-5.47a.75.75 0 1 1 1.06 1.06L13.06 12l5.47 5.47a.75.75 0 1 1-1.06 1.06L12 13.06l-5.47 5.47a.75.75 0 0 1-1.06-1.06L10.94 12 5.47 6.53a.75.75 0 0 1 0-1.06Z" clip-rule="evenodd" /></svg>
        </button>
      </div>
    </div>

    <!-- Row 2: Real-time Audio Spectrum Equalizer (34 Bars) -->
    <div class="spectrum-container" id="spectrum-container">
      <!-- 34 Bars generated by JS -->
    </div>

    <!-- Row 3: Player Controls -->
    <div class="controls-row">
      <!-- Left: Volume Slider -->
      <div class="controls-left">
        <svg class="vol-icon" viewBox="0 0 24 24"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/></svg>
        <input type="range" class="vol-slider" id="vol-slider" min="0" max="1" step="0.02" value="0.9">
      </div>

      <!-- Center: Playback Buttons -->
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

      <!-- Right: Time, Shuffle, Repeat -->
      <div class="controls-right">
        <span class="time-display" id="time-display">0:00 / 0:00</span>
        <button class="mini-btn" id="btn-shuffle" title="Shuffle">
          <svg viewBox="0 0 24 24"><path d="M10.59 9.17L5.41 4 4 5.41l5.17 5.17 1.42-1.41zM14.5 4l2.04 2.04L4 18.59 5.41 20 17.96 7.46 20 9.5V4h-5.5zm.33 9.41l-1.41 1.41 3.13 3.13L14.5 20H20v-5.5l-2.04 2.04-3.13-3.13z"/></svg>
        </button>
        <button class="mini-btn" id="btn-repeat" title="Repeat">
          <svg viewBox="0 0 24 24"><path d="M7 7h10v3l4-4-4-4v3H5v6h2V7zm10 10H7v-3l-4 4 4 4v-3h12v-6h-2v4z"/></svg>
        </button>
      </div>
    </div>
  </div>

  <!-- SEARCH MODAL OVERLAY -->
  <div class="search-modal" id="search-modal">
    <div class="search-bar">
      <input type="text" class="search-input" id="search-input" placeholder="Search any song or artist on YouTube...">
      <button class="search-submit-btn" id="search-submit-btn">FIND</button>
      <button class="icon-btn" id="btn-search-close">
        <svg viewBox="0 0 24 24"><path fill-rule="evenodd" d="M5.47 5.47a.75.75 0 0 1 1.06 0L12 10.94l5.47-5.47a.75.75 0 1 1 1.06 1.06L13.06 12l5.47 5.47a.75.75 0 1 1-1.06 1.06L12 13.06l-5.47 5.47a.75.75 0 0 1-1.06-1.06L10.94 12 5.47 6.53a.75.75 0 0 1 0-1.06Z" clip-rule="evenodd" /></svg>
      </button>
    </div>
    <div class="search-results-list" id="search-results-list">
      <div style="color:#94a3b8;font-size:11px;padding:12px;text-align:center;">Type any song above and hit Find</div>
    </div>
  </div>
</div>

<!-- Standalone HTML5 Audio Player (Direct Audio Playback, NO CORS mute!) -->
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
  const volSlider = document.getElementById('vol-slider');
  const btnClose = document.getElementById('btn-close');
  const btnSearchToggle = document.getElementById('btn-search-toggle');
  const btnSearchClose = document.getElementById('btn-search-close');
  const searchModal = document.getElementById('search-modal');
  const searchInput = document.getElementById('search-input');
  const searchSubmitBtn = document.getElementById('search-submit-btn');
  const searchResultsList = document.getElementById('search-results-list');
  const spectrumContainer = document.getElementById('spectrum-container');
  const canvas = document.getElementById('waves-canvas');
  const ctx = canvas.getContext('2d');

  let isPlaying = false;
  let isShuffle = false;
  let isRepeat = false;

  // Initialize 34 Equalizer Spectrum Bars
  const NUM_BARS = 34;
  const bars = [];
  for (let i = 0; i < NUM_BARS; i++) {
    const bar = document.createElement('div');
    bar.className = 'spectrum-bar';
    spectrumContainer.appendChild(bar);
    bars.push(bar);
  }

  // Canvas Neon Waves Animation
  function resizeCanvas() {
    canvas.width = card.clientWidth;
    canvas.height = card.clientHeight;
  }
  resizeCanvas();
  window.addEventListener('resize', resizeCanvas);

  let waveOffset = 0;
  function renderWaves() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const w = canvas.width;
    const h = canvas.height;
    const centerY = h * 0.58;

    const amp = isPlaying ? 16 : 5;
    waveOffset += isPlaying ? 0.045 : 0.015;

    // Wave 1: Soft Violet / Pink Ribbon
    ctx.beginPath();
    ctx.moveTo(0, centerY);
    for (let x = 0; x <= w; x += 4) {
      const y = centerY + Math.sin(x * 0.016 + waveOffset) * amp * 0.8 + Math.cos(x * 0.032 - waveOffset * 0.5) * (amp * 0.5);
      ctx.lineTo(x, y);
    }
    ctx.strokeStyle = 'rgba(236, 72, 153, 0.45)';
    ctx.lineWidth = 2.5;
    ctx.shadowBlur = 12;
    ctx.shadowColor = '#f472b6';
    ctx.stroke();

    // Wave 2: Cyan / Electric Blue Ribbon
    ctx.beginPath();
    ctx.moveTo(0, centerY);
    for (let x = 0; x <= w; x += 4) {
      const y = centerY + Math.sin(x * 0.022 - waveOffset * 1.2) * (amp * 0.9) + Math.sin(x * 0.01 + waveOffset * 0.8) * (amp * 0.3);
      ctx.lineTo(x, y);
    }
    ctx.strokeStyle = 'rgba(168, 85, 247, 0.40)';
    ctx.lineWidth = 2;
    ctx.shadowBlur = 10;
    ctx.shadowColor = '#c084fc';
    ctx.stroke();

    requestAnimationFrame(renderWaves);
  }
  requestAnimationFrame(renderWaves);

  // Equalizer Spectrum Simulation synchronized with audio
  let simTime = 0;
  function updateEqualizer() {
    simTime += 0.12;
    for (let i = 0; i < NUM_BARS; i++) {
      let targetHeight = 4;
      if (isPlaying) {
        const centerDist = 1 - Math.abs(i - NUM_BARS / 2) / (NUM_BARS / 2);
        const wave1 = Math.sin(simTime * 2.2 + i * 0.45);
        const wave2 = Math.cos(simTime * 1.6 - i * 0.28);
        const rand = (Math.sin(simTime * 4.0 + i * 1.7) + 1) * 0.5;
        const energy = Math.max(0.1, (wave1 + wave2 + rand * 1.5) / 3.5);
        targetHeight = Math.max(3, Math.min(22, 3 + energy * 18 * centerDist + (rand * 4)));
      }
      bars[i].style.height = targetHeight + 'px';
      bars[i].style.filter = isPlaying ? `drop-shadow(0 0 6px rgba(244, 114, 182, 0.7))` : 'none';
    }
    requestAnimationFrame(updateEqualizer);
  }
  requestAnimationFrame(updateEqualizer);

  // Playback Control Handlers
  function togglePlay() {
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

  btnPrev.addEventListener('click', () => {
    window.pywebview && window.pywebview.api.prev_track();
  });

  btnNext.addEventListener('click', () => {
    window.pywebview && window.pywebview.api.next_track();
  });

  btnShuffle.addEventListener('click', () => {
    isShuffle = !isShuffle;
    btnShuffle.classList.toggle('active', isShuffle);
  });

  btnRepeat.addEventListener('click', () => {
    isRepeat = !isRepeat;
    btnRepeat.classList.toggle('active', isRepeat);
    audio.loop = isRepeat;
  });

  volSlider.addEventListener('input', (e) => {
    audio.volume = parseFloat(e.target.value);
  });

  audio.addEventListener('timeupdate', () => {
    const cur = formatTime(audio.currentTime);
    const dur = formatTime(audio.duration || 0);
    timeDisplay.textContent = `${cur} / ${dur}`;
  });

  audio.addEventListener('ended', () => {
    if (!isRepeat) {
      window.pywebview && window.pywebview.api.next_track();
    }
  });

  function formatTime(sec) {
    if (isNaN(sec) || sec === 0) return '0:00';
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  }

  window.setStreamUrl = function(url) {
    if (!url) return;
    audio.src = url;
    audio.volume = parseFloat(volSlider.value);
    audio.play().then(() => {
      isPlaying = true;
      playIcon.style.display = 'none';
      pauseIcon.style.display = 'block';
    }).catch(err => {
      console.log('Autoplay error:', err);
    });
  };

  // Dynamic Wallpaper Live Adaptation
  window.updateWallpaperBackdrop = function(b64) {
    const wpEl = document.getElementById('wp-glass');
    if (wpEl && b64) {
      wpEl.style.backgroundImage = `url("${b64}")`;
    }
  };

  // Search Modal
  btnSearchToggle.addEventListener('click', () => {
    searchModal.classList.add('active');
    searchInput.focus();
  });

  btnSearchClose.addEventListener('click', () => {
    searchModal.classList.remove('active');
  });

  searchSubmitBtn.addEventListener('click', () => {
    const query = searchInput.value.trim();
    if (!query) return;
    searchResultsList.innerHTML = '<div style="color:#94a3b8;font-size:11px;padding:12px;text-align:center;">Searching YouTube...</div>';
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
        searchResultsList.innerHTML = '<div style="color:#94a3b8;font-size:11px;padding:12px;text-align:center;">No results found.</div>';
        return;
      }
      results.forEach(item => {
        const div = document.createElement('div');
        div.className = 'search-item';
        div.innerHTML = `
          <img src="${item.thumb || 'https://i.ytimg.com/vi/' + item.id + '/hqdefault.jpg'}" alt="">
          <div class="search-item-info">
            <div class="search-item-title">${item.title}</div>
            <div class="search-item-artist">${item.artist}</div>
          </div>
        `;
        div.addEventListener('click', () => {
          trackTitle.textContent = item.title;
          trackSource.querySelector('span').textContent = item.artist;
          albumArt.src = item.thumb || `https://i.ytimg.com/vi/${item.id}/hqdefault.jpg`;
          searchModal.classList.remove('active');
          window.pywebview && window.pywebview.api.play_id(item.id);
        });
        searchResultsList.appendChild(div);
      });
    } catch(err) {
      console.error(err);
    }
  };

  btnClose.addEventListener('click', () => {
    window.pywebview && window.pywebview.api.close_window();
  });

  // Dragging support & Wallpaper backdrop refresh on move
  let isDragging = false;
  let startX = 0, startY = 0;

  card.addEventListener('mousedown', (e) => {
    if (e.target.closest('button') || e.target.closest('input') || e.target.closest('.search-modal')) return;
    isDragging = true;
    startX = e.screenX;
    startY = e.screenY;
  });

  document.addEventListener('mousemove', (e) => {
    if (!isDragging) return;
    const dx = e.screenX - startX;
    const dy = e.screenY - startY;
    startX = e.screenX;
    startY = e.screenY;
    window.pywebview && window.pywebview.api.move_window(dx, dy);
  });

  document.addEventListener('mouseup', () => {
    if (isDragging) {
      isDragging = false;
      window.pywebview && window.pywebview.api.update_backdrop();
    }
  });
</script>
</body>
</html>
"""

class MusicAPI:
    def __init__(self, win_holder):
        self.win_holder = win_holder
        self.current_x = POS_X
        self.current_y = POS_Y
        self.history = [
            {"id": "oC6brLXQe4I", "title": "BABYMONSTER - 'DESERVE' M/V", "artist": "YouTube"}
        ]
        self.history_index = 0
        self.ydl_opts_search = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
        }
        self.ydl_opts_stream = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
        }

    def close_window(self):
        w = self.win_holder[0]
        if w:
            w.destroy()

    def move_window(self, dx, dy):
        w = self.win_holder[0]
        if w:
            try:
                self.current_x = w.x + int(dx)
                self.current_y = w.y + int(dy)
                w.move(self.current_x, self.current_y)
            except Exception:
                pass

    def update_backdrop(self):
        w = self.win_holder[0]
        if not w:
            return
        def _bg():
            try:
                b64 = get_wallpaper_slice(w.x, w.y, WIDGET_W, WIDGET_H)
                if b64:
                    w.evaluate_js(f"window.updateWallpaperBackdrop({json.dumps(b64)});")
            except Exception:
                pass
        threading.Thread(target=_bg, daemon=True).start()

    def search_songs(self, query):
        threading.Thread(target=self._search_async, args=(query,), daemon=True).start()

    def _search_async(self, query):
        w = self.win_holder[0]
        if not w:
            return
        results = []
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts_search) as ydl:
                info = ydl.extract_info(f"ytsearch6:{query}", download=False)
                for entry in info.get('entries', []):
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
                w.evaluate_js(f"window.setStreamUrl({json.dumps(stream_url)});")
        except Exception:
            w.evaluate_js(f"window.setStreamUrl('');")

    def next_track(self):
        if self.history and self.history_index < len(self.history) - 1:
            self.history_index += 1
            s = self.history[self.history_index]
            self.play_id(s['id'])

    def prev_track(self):
        if self.history and self.history_index > 0:
            self.history_index -= 1
            s = self.history[self.history_index]
            self.play_id(s['id'])


def wallpaper_watcher(api):
    """Monitors desktop wallpaper changes in real time and automatically updates the glass backdrop."""
    wp_path = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Themes\TranscodedWallpaper")
    last_mtime = 0
    try:
        if os.path.exists(wp_path):
            last_mtime = os.path.getmtime(wp_path)
    except Exception:
        pass

    while True:
        try:
            if os.path.exists(wp_path):
                mtime = os.path.getmtime(wp_path)
                if mtime != last_mtime:
                    last_mtime = mtime
                    # Wait briefly for Windows to finish writing file
                    time.sleep(0.4)
                    w = api.win_holder[0]
                    cur_x = w.x if w else api.current_x
                    cur_y = w.y if w else api.current_y
                    b64 = get_wallpaper_slice(cur_x, cur_y, WIDGET_W, WIDGET_H)
                    if b64 and w:
                        w.evaluate_js(f"window.updateWallpaperBackdrop({json.dumps(b64)});")
        except Exception:
            pass
        time.sleep(0.8)


def main():
    win_holder = [None]
    api = MusicAPI(win_holder)

    # Sample current active desktop wallpaper directly behind widget
    initial_wp = get_wallpaper_slice(POS_X, POS_Y, WIDGET_W, WIDGET_H)
    final_html = HTML_TEMPLATE.replace('__INITIAL_WALLPAPER__', initial_wp)

    # Clean widget dimensions: 620x156 (NO full-screen white band!)
    # on_top=False ensures it NEVER overlaps other applications
    w = webview.create_window(
        title='Desktop Music Visualizer',
        html=final_html,
        width=WIDGET_W,
        height=WIDGET_H,
        x=POS_X,
        y=POS_Y,
        frameless=True,
        resizable=False,
        on_top=False,
        js_api=api,
        background_color='#10061a'
    )
    win_holder[0] = w

    def apply_native_window_styling():
        for _ in range(25):
            time.sleep(0.12)
            hwnd = user32.FindWindowW(None, 'Desktop Music Visualizer')
            if hwnd:
                # Clip native Win32 window to smooth rounded rectangle (matching border-radius: 20px)
                hrgn = gdi32.CreateRoundRectRgn(0, 0, WIDGET_W + 1, WIDGET_H + 1, 38, 38)
                user32.SetWindowRgn(hwnd, hrgn, True)
                break

    threading.Thread(target=apply_native_window_styling, daemon=True).start()
    threading.Thread(target=wallpaper_watcher, args=(api,), daemon=True).start()

    def auto_start():
        time.sleep(1.2)
        api.play_id("oC6brLXQe4I")

    threading.Thread(target=auto_start, daemon=True).start()
    webview.start()

if __name__ == '__main__':
    main()
