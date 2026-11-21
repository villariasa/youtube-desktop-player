"""
Immersive Glassmorphism Desktop Music Visualizer
- Desktop-wide audio-reactive flowing ribbon waves in cyan, teal, and white
- Atmospheric spectrum equalizer bars on left and right sides of desktop
- Centered ultra-transparent glassmorphism player card
- Live dynamic wallpaper watcher: automatically adapts and blends into whatever wallpaper is active (even when switching Next Desktop Background)
- Direct streaming unmuted HTML5 audio via yt-dlp
- Full controls: Volume, Seek/Time, Prev, Glowing Circular Pause, Next, Shuffle, Repeat, Search
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
SCREEN_W = user32.GetSystemMetrics(0)
SCREEN_H = user32.GetSystemMetrics(1)

# Full-desktop width visualization bar just above Windows taskbar
TASKBAR_H = 48
VIS_H = 210
VIS_W = SCREEN_W
POS_X = 0
POS_Y = SCREEN_H - VIS_H - TASKBAR_H

def get_wallpaper_slice_b64(x=POS_X, y=POS_Y, w=VIS_W, h=VIS_H):
    """Crops and returns base64 JPEG of the desktop wallpaper for seamless blending."""
    try:
        wp_path = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Themes\TranscodedWallpaper")
        if not os.path.exists(wp_path):
            return ""
        img = Image.open(wp_path).convert("RGB")
        img_screen = img.resize((SCREEN_W, SCREEN_H), Image.Resampling.LANCZOS)
        crop = img_screen.crop((x, y, x + w, y + h))
        buf = io.BytesIO()
        crop.save(buf, format="JPEG", quality=95)
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
    position: relative;
    background: #0f141c;
  }

  /* FULL DESKTOP WALLPAPER BLENDING LAYER (Dynamically adapts to wallpaper changes) */
  .wallpaper-blend {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-size: 100% 100%;
    background-repeat: no-repeat;
    background-position: center;
    z-index: 0;
    pointer-events: none;
    transition: background-image 0.4s ease, opacity 0.3s ease;
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
    background: rgba(13, 23, 33, 0.42);
    backdrop-filter: blur(22px) saturate(160%);
    -webkit-backdrop-filter: blur(22px) saturate(160%);
    border: 1.2px solid rgba(103, 232, 249, 0.48);
    border-radius: 16px;
    box-shadow: 
      0 0 28px rgba(6, 182, 212, 0.28),
      0 12px 36px rgba(0, 0, 0, 0.65),
      inset 0 1px 1.5px rgba(255, 255, 255, 0.4),
      inset 0 -1px 1.5px rgba(34, 211, 238, 0.2);
    display: flex;
    align-items: center;
    padding: 12px 16px;
    gap: 14px;
    position: relative;
    overflow: hidden;
    pointer-events: auto;
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
      rgba(34, 211, 238, 0.08) 72%,
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
    background: linear-gradient(90deg, transparent 0%, rgba(255, 255, 255, 0.85) 40%, rgba(103, 232, 249, 0.9) 60%, transparent 100%);
    box-shadow: 0 0 8px rgba(103, 232, 249, 0.7);
    pointer-events: none;
    z-index: 6;
  }

  /* Album Artwork */
  .album-wrap {
    width: 80px;
    height: 80px;
    border-radius: 10px;
    overflow: hidden;
    position: relative;
    flex-shrink: 0;
    box-shadow: 0 4px 18px rgba(0, 0, 0, 0.6), 0 0 12px rgba(34, 211, 238, 0.3);
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

  /* Spectrum Waveform Equalizer (34 Bars in Card) */
  .spectrum-container {
    width: 100%;
    height: 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 2px;
  }

  .spectrum-bar {
    flex: 1;
    min-width: 2px;
    max-width: 5px;
    height: 3px;
    border-radius: 999px;
    background: linear-gradient(180deg, #67e8f9 0%, #22d3ee 50%, #0891b2 100%);
    box-shadow: 0 0 6px rgba(34, 211, 238, 0.6);
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
    background: #22d3ee;
    box-shadow: 0 0 6px #22d3ee;
    cursor: pointer;
    transition: transform 0.15s ease;
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

  /* Glowing Circular Play / Pause Button */
  .play-pause-btn {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: linear-gradient(135deg, rgba(6, 182, 212, 0.25) 0%, rgba(34, 211, 238, 0.35) 100%);
    border: 1.5px solid rgba(103, 232, 249, 0.8);
    box-shadow: 0 0 14px rgba(34, 211, 238, 0.7), inset 0 0 6px rgba(255, 255, 255, 0.35);
    display: flex;
    align-items: center;
    justify-content: center;
    color: #ffffff;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .play-pause-btn:hover {
    transform: scale(1.12);
    box-shadow: 0 0 20px rgba(34, 211, 238, 0.95), inset 0 0 10px rgba(255, 255, 255, 0.5);
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
    color: #22d3ee;
    text-shadow: 0 0 6px #22d3ee;
  }

  .mini-btn svg {
    width: 11px;
    height: 11px;
    fill: currentColor;
  }

  /* Search Modal */
  .search-modal {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(10, 18, 28, 0.95);
    backdrop-filter: blur(20px);
    border-radius: 16px;
    display: none;
    flex-direction: column;
    padding: 10px 12px;
    z-index: 50;
  }

  .search-modal.active {
    display: flex;
  }

  .search-bar {
    display: flex;
    align-items: center;
    gap: 6px;
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(103, 232, 249, 0.4);
    border-radius: 8px;
    padding: 5px 8px;
  }

  .search-input {
    flex: 1;
    background: transparent;
    border: none;
    outline: none;
    color: #ffffff;
    font-size: 11px;
  }

  .search-input::placeholder {
    color: rgba(255, 255, 255, 0.4);
  }

  .search-submit-btn {
    background: linear-gradient(135deg, #06b6d4, #0891b2);
    border: none;
    border-radius: 5px;
    color: #ffffff;
    font-size: 9.5px;
    font-weight: 700;
    padding: 3px 8px;
    cursor: pointer;
    box-shadow: 0 0 8px rgba(6, 182, 212, 0.4);
  }

  .search-results-list {
    flex: 1;
    overflow-y: auto;
    margin-top: 6px;
    display: flex;
    flex-direction: column;
    gap: 3px;
  }

  .search-results-list::-webkit-scrollbar {
    width: 3px;
  }

  .search-results-list::-webkit-scrollbar-thumb {
    background: rgba(34, 211, 238, 0.4);
    border-radius: 2px;
  }

  .search-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 6px;
    border-radius: 6px;
    background: rgba(255, 255, 255, 0.04);
    cursor: pointer;
    transition: background 0.15s ease;
  }

  .search-item:hover {
    background: rgba(34, 211, 238, 0.2);
  }

  .search-item img {
    width: 24px;
    height: 24px;
    border-radius: 4px;
    object-fit: cover;
  }

  .search-item-info {
    flex: 1;
    min-width: 0;
  }

  .search-item-title {
    font-size: 10px;
    font-weight: 600;
    color: #ffffff;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .search-item-artist {
    font-size: 8.5px;
    color: #94a3b8;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
</style>
</head>
<body>

<!-- Dynamic Desktop Wallpaper Blending Layer (Smoothly updates when wallpaper changes) -->
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
          <div class="track-title" id="track-title">BAYMONSTER - DESERVE MV</div>
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

      <!-- Real-time Equalizer (34 Bars in Card) -->
      <div class="spectrum-container" id="spectrum-container">
        <!-- Bars generated by JS -->
      </div>

      <!-- Controls Row -->
      <div class="controls-row">
        <!-- Left: Volume Slider -->
        <div class="controls-left">
          <svg class="vol-icon" viewBox="0 0 24 24"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/></svg>
          <input type="range" class="vol-slider" id="vol-slider" min="0" max="1" step="0.02" value="0.9">
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
          <button class="mini-btn" id="btn-repeat" title="Repeat">
            <svg viewBox="0 0 24 24"><path d="M7 7h10v3l4-4-4-4v3H5v6h2V7zm10 10H7v-3l-4 4 4 4v-3h12v-6h-2v4z"/></svg>
          </button>
          <button class="mini-btn" id="btn-playlist" title="Playlist">
            <svg viewBox="0 0 24 24"><path d="M4 10h12v2H4zm0-4h12v2H4zm0 8h8v2H4zm10 0v6l5-3z"/></svg>
          </button>
        </div>
      </div>
    </div>

    <!-- Search Modal -->
    <div class="search-modal" id="search-modal">
      <div class="search-bar">
        <input type="text" class="search-input" id="search-input" placeholder="Search any song or artist on YouTube...">
        <button class="search-submit-btn" id="search-submit-btn">FIND</button>
        <button class="icon-btn" id="btn-search-close">
          <svg viewBox="0 0 24 24"><path fill-rule="evenodd" d="M5.47 5.47a.75.75 0 0 1 1.06 0L12 10.94l5.47-5.47a.75.75 0 1 1 1.06 1.06L13.06 12l5.47 5.47a.75.75 0 1 1-1.06 1.06L12 13.06l-5.47 5.47a.75.75 0 0 1-1.06-1.06L10.94 12 5.47 6.53a.75.75 0 0 1 0-1.06Z" clip-rule="evenodd" /></svg>
        </button>
      </div>
      <div class="search-results-list" id="search-results-list">
        <div style="color:#94a3b8;font-size:10px;padding:10px;text-align:center;">Type any song above and hit Find</div>
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
  const btnSearchClose = document.getElementById('btn-search-close');
  const searchModal = document.getElementById('search-modal');
  const searchInput = document.getElementById('search-input');
  const searchSubmitBtn = document.getElementById('search-submit-btn');
  const searchResultsList = document.getElementById('search-results-list');
  const spectrumContainer = document.getElementById('spectrum-container');
  const canvas = document.getElementById('desktop-waves');
  const ctx = canvas.getContext('2d');
  const wallpaperBlend = document.getElementById('wallpaper-blend');

  let isPlaying = false;
  let isShuffle = false;
  let isRepeat = false;

  // Dynamic Live Wallpaper Update Function called by Python watcher
  window.updateLiveWallpaper = function(newB64) {
    if (wallpaperBlend && newB64) {
      wallpaperBlend.style.backgroundImage = `url("${newB64}")`;
    }
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

  function resizeCanvas() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  }
  resizeCanvas();
  window.addEventListener('resize', resizeCanvas);

  // Floating Particles
  const particles = [];
  for (let p = 0; p < 45; p++) {
    particles.push({
      x: Math.random() * window.innerWidth,
      y: 70 + Math.random() * 110,
      radius: Math.random() * 2 + 1,
      speedX: Math.random() * 0.8 + 0.3,
      alpha: Math.random() * 0.6 + 0.2
    });
  }

  // Desktop-Wide Flowing Ribbon Waves & Atmospheric Spectrum
  let waveTime = 0;
  function renderDesktopWaves() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const w = canvas.width;
    const h = canvas.height;

    waveTime += isPlaying ? 0.025 : 0.008;
    const baseAmp = isPlaying ? 22 : 7;

    const cardLeft = (w - 590) / 2;
    const cardRight = cardLeft + 590;

    // Atmospheric Spectrum Bars
    for (let lx = cardLeft - 180; lx < cardLeft - 20; lx += 9) {
      const dist = 1 - Math.abs(lx - (cardLeft - 100)) / 90;
      const hBar = Math.max(4, (Math.sin(waveTime * 3.5 + lx * 0.08) + 1) * (isPlaying ? 18 : 6) * dist);
      ctx.fillStyle = 'rgba(34, 211, 238, 0.45)';
      ctx.shadowBlur = 8;
      ctx.shadowColor = '#06b6d4';
      ctx.fillRect(lx, h - 35 - hBar, 3.5, hBar);
    }

    for (let rx = cardRight + 20; rx < cardRight + 180; rx += 9) {
      const dist = 1 - Math.abs(rx - (cardRight + 100)) / 90;
      const hBar = Math.max(4, (Math.cos(waveTime * 3.2 - rx * 0.07) + 1) * (isPlaying ? 16 : 5) * dist);
      ctx.fillStyle = 'rgba(34, 211, 238, 0.45)';
      ctx.shadowBlur = 8;
      ctx.shadowColor = '#06b6d4';
      ctx.fillRect(rx, h - 35 - hBar, 3.5, hBar);
    }

    // Ribbon Wave 1
    ctx.beginPath();
    ctx.moveTo(0, h * 0.68);
    for (let x = 0; x <= w; x += 6) {
      const y = h * 0.66 + Math.sin(x * 0.005 + waveTime) * baseAmp + Math.sin(x * 0.012 - waveTime * 0.8) * (baseAmp * 0.4);
      ctx.lineTo(x, y);
    }
    ctx.lineTo(w, h);
    ctx.lineTo(0, h);
    ctx.closePath();
    const grad1 = ctx.createLinearGradient(0, h * 0.5, 0, h);
    grad1.addColorStop(0, 'rgba(6, 182, 212, 0.22)');
    grad1.addColorStop(0.5, 'rgba(15, 23, 42, 0.28)');
    grad1.addColorStop(1, 'rgba(15, 23, 42, 0.0)');
    ctx.fillStyle = grad1;
    ctx.shadowBlur = 18;
    ctx.shadowColor = 'rgba(34, 211, 238, 0.6)';
    ctx.fill();

    ctx.beginPath();
    ctx.moveTo(0, h * 0.68);
    for (let x = 0; x <= w; x += 6) {
      const y = h * 0.66 + Math.sin(x * 0.005 + waveTime) * baseAmp + Math.sin(x * 0.012 - waveTime * 0.8) * (baseAmp * 0.4);
      ctx.lineTo(x, y);
    }
    ctx.strokeStyle = 'rgba(103, 232, 249, 0.75)';
    ctx.lineWidth = 2;
    ctx.shadowBlur = 14;
    ctx.shadowColor = '#22d3ee';
    ctx.stroke();

    // Ribbon Wave 2
    ctx.beginPath();
    ctx.moveTo(0, h * 0.78);
    for (let x = 0; x <= w; x += 6) {
      const y = h * 0.74 + Math.cos(x * 0.006 - waveTime * 1.1) * (baseAmp * 0.9) + Math.sin(x * 0.015 + waveTime * 0.6) * (baseAmp * 0.35);
      ctx.lineTo(x, y);
    }
    ctx.strokeStyle = 'rgba(224, 242, 254, 0.65)';
    ctx.lineWidth = 1.8;
    ctx.shadowBlur = 12;
    ctx.shadowColor = '#e0f2fe';
    ctx.stroke();

    // Ribbon Wave 3
    ctx.beginPath();
    ctx.moveTo(0, h * 0.86);
    for (let x = 0; x <= w; x += 6) {
      const y = h * 0.84 + Math.sin(x * 0.007 + waveTime * 0.9) * (baseAmp * 0.6);
      ctx.lineTo(x, y);
    }
    ctx.strokeStyle = 'rgba(34, 211, 238, 0.4)';
    ctx.lineWidth = 1.5;
    ctx.shadowBlur = 8;
    ctx.shadowColor = '#0891b2';
    ctx.stroke();

    // Drifting particles
    particles.forEach(p => {
      p.x += p.speedX * (isPlaying ? 1.4 : 0.6);
      if (p.x > w) p.x = 0;
      ctx.beginPath();
      ctx.arc(p.x, p.y + Math.sin(p.x * 0.01 + waveTime) * 10, p.radius, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(165, 243, 252, ${p.alpha})`;
      ctx.shadowBlur = 6;
      ctx.shadowColor = '#67e8f9';
      ctx.fill();
    });

    requestAnimationFrame(renderDesktopWaves);
  }
  requestAnimationFrame(renderDesktopWaves);

  // Equalizer in card
  let simTime = 0;
  function updateEqualizer() {
    simTime += 0.12;
    for (let i = 0; i < NUM_BARS; i++) {
      let targetHeight = 3;
      if (isPlaying) {
        const centerDist = 1 - Math.abs(i - NUM_BARS / 2) / (NUM_BARS / 2);
        const wave1 = Math.sin(simTime * 2.4 + i * 0.45);
        const wave2 = Math.cos(simTime * 1.8 - i * 0.3);
        const rand = (Math.sin(simTime * 4.2 + i * 1.6) + 1) * 0.5;
        const energy = Math.max(0.1, (wave1 + wave2 + rand * 1.6) / 3.6);
        targetHeight = Math.max(3, Math.min(18, 3 + energy * 15 * centerDist + (rand * 3.5)));
      }
      bars[i].style.height = targetHeight + 'px';
      bars[i].style.filter = isPlaying ? `drop-shadow(0 0 6px rgba(34, 211, 238, 0.75))` : 'none';
    }
    requestAnimationFrame(updateEqualizer);
  }
  requestAnimationFrame(updateEqualizer);

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

  btnPlaylist.addEventListener('click', () => {
    searchModal.classList.add('active');
    searchInput.focus();
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
    searchResultsList.innerHTML = '<div style="color:#94a3b8;font-size:10px;padding:10px;text-align:center;">Searching YouTube...</div>';
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
        searchResultsList.innerHTML = '<div style="color:#94a3b8;font-size:10px;padding:10px;text-align:center;">No results found.</div>';
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

  btnMinimize.addEventListener('click', () => {
    window.pywebview && window.pywebview.api.minimize_window();
  });
</script>
</body>
</html>
"""

class MusicAPI:
    def __init__(self, win_holder):
        self.win_holder = win_holder
        self.history = [
            {"id": "oC6brLXQe4I", "title": "BAYMONSTER - DESERVE MV", "artist": "YouTube"}
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

    def minimize_window(self):
        w = self.win_holder[0]
        if w:
            try:
                w.minimize()
            except Exception:
                pass

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
    """Monitors Windows desktop wallpaper changes and instantly updates the visualizer blend."""
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
                    # Wait briefly for Windows to complete saving wallpaper
                    time.sleep(0.35)
                    b64 = get_wallpaper_slice_b64(POS_X, POS_Y, VIS_W, VIS_H)
                    w = api.win_holder[0]
                    if b64 and w:
                        w.evaluate_js(f"window.updateLiveWallpaper({json.dumps(b64)});")
        except Exception:
            pass
        time.sleep(0.6)


def main():
    win_holder = [None]
    api = MusicAPI(win_holder)

    # Sample current active desktop wallpaper across the visualizer width
    wp_b64 = get_wallpaper_slice_b64(POS_X, POS_Y, VIS_W, VIS_H)
    final_html = HTML_TEMPLATE.replace('__WALLPAPER_BACKDROP__', wp_b64)

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

    def auto_start():
        time.sleep(1.2)
        api.play_id("oC6brLXQe4I")

    threading.Thread(target=auto_start, daemon=True).start()
    webview.start()

if __name__ == '__main__':
    main()
