"""
Immersive Glassmorphism Desktop Music Visualizer
- Zero white boxes: solid frameless window matching card dimensions
- Full audio playback: HTML5 Audio without CORS mute
- Flowing neon ribbon waves + spectrum visualizer (pink, magenta, violet, electric-blue)
- Pure glassmorphism card matching reference image
- Desktop level (on_top=False, never overlaps other applications)
- User-friendly search modal with zero presets
"""
import webview
import yt_dlp
import threading
import json
import ctypes
import os
import sys

# Screen resolution
user32 = ctypes.windll.user32
SCREEN_W = user32.GetSystemMetrics(0)
SCREEN_H = user32.GetSystemMetrics(1)

WIDGET_W = 620
WIDGET_H = 156

POS_X = (SCREEN_W - WIDGET_W) // 2
POS_Y = SCREEN_H - WIDGET_H - 90  # Lower center of screen matching reference

HTML_CONTENT = """
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
    background: #12071a;
  }

  /* GLASSMORPHISM CARD CONTAINER */
  .player-card {
    width: 100%;
    height: 100%;
    background: linear-gradient(135deg, rgba(32, 14, 46, 0.94) 0%, rgba(18, 7, 28, 0.98) 100%);
    border: 1.5px solid rgba(236, 72, 153, 0.45);
    box-shadow: 
      0 0 35px rgba(217, 70, 239, 0.35),
      0 16px 40px rgba(0, 0, 0, 0.7),
      inset 0 1px 1px rgba(255, 255, 255, 0.35);
    display: flex;
    align-items: center;
    padding: 14px 18px;
    gap: 16px;
    position: relative;
    cursor: grab;
    border-radius: 0;
  }

  .player-card:active {
    cursor: grabbing;
  }

  /* Neon Waves Canvas Background inside card */
  #waves-canvas {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    z-index: 1;
    opacity: 0.65;
  }

  /* Glass Top Light Edge */
  .player-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent 0%, rgba(244, 114, 182, 0.6) 50%, transparent 100%);
    pointer-events: none;
    z-index: 2;
  }

  /* Album Artwork */
  .album-wrap {
    width: 98px;
    height: 98px;
    border-radius: 14px;
    overflow: hidden;
    position: relative;
    flex-shrink: 0;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.6), 0 0 0 1px rgba(236, 72, 153, 0.3);
    background: #0d0612;
    z-index: 10;
  }

  .album-art {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
    transition: transform 0.3s ease;
  }

  .album-wrap:hover .album-art {
    transform: scale(1.05);
  }

  /* Card Main Info & Controls */
  .card-main {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    height: 100%;
    padding: 2px 0;
    z-index: 10;
  }

  /* Title & Source */
  .track-meta {
    display: flex;
    flex-direction: column;
  }

  .track-title {
    font-size: 15px;
    font-weight: 600;
    color: #ffffff;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    letter-spacing: -0.2px;
    text-shadow: 0 2px 8px rgba(0, 0, 0, 0.7);
  }

  .track-source {
    font-size: 11px;
    font-weight: 400;
    color: #cbd5e1;
    margin-top: 1px;
    opacity: 0.85;
  }

  /* AUDIO SPECTRUM BARS */
  .spectrum-bar-wrap {
    display: flex;
    align-items: center;
    gap: 3px;
    height: 22px;
    margin: 4px 0;
  }

  .spec-bar {
    flex: 1;
    height: 4px;
    border-radius: 2px;
    background: linear-gradient(180deg, #f472b6 0%, #c084fc 100%);
    box-shadow: 0 0 6px rgba(244, 114, 182, 0.65);
    transition: height 0.08s ease;
  }

  /* CONTROLS BAR */
  .controls-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  /* Left: Volume */
  .controls-left {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .vol-btn {
    background: transparent;
    border: none;
    color: #cbd5e1;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 2px;
    transition: color 0.15s ease;
  }

  .vol-btn svg { width: 15px; height: 15px; fill: currentColor; }
  .vol-btn:hover { color: #f472b6; }

  .vol-slider {
    width: 60px;
    height: 3px;
    -webkit-appearance: none;
    background: rgba(255, 255, 255, 0.22);
    border-radius: 2px;
    outline: none;
    cursor: pointer;
  }

  .vol-slider::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 9px;
    height: 9px;
    border-radius: 50%;
    background: #f472b6;
    box-shadow: 0 0 6px rgba(244, 114, 182, 0.8);
    cursor: pointer;
  }

  /* Center: Playback Buttons */
  .controls-center {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .ctrl-btn {
    background: transparent;
    border: none;
    color: #e2e8f0;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 4px;
    border-radius: 50%;
    transition: color 0.15s ease, transform 0.1s ease;
  }

  .ctrl-btn svg { width: 17px; height: 17px; fill: currentColor; }
  .ctrl-btn:hover { color: #f472b6; transform: scale(1.14); }
  .ctrl-btn:active { transform: scale(0.92); }

  /* Circular Glowing Play/Pause */
  .play-pause-btn {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: rgba(236, 72, 153, 0.25);
    border: 1.5px solid rgba(244, 114, 182, 0.65);
    box-shadow: 0 0 16px rgba(236, 72, 153, 0.55), inset 0 1px 1px rgba(255, 255, 255, 0.4);
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    color: #ffffff;
    transition: transform 0.15s ease, box-shadow 0.15s ease, background 0.15s ease;
  }

  .play-pause-btn svg { width: 16px; height: 16px; fill: currentColor; }

  .play-pause-btn:hover {
    transform: scale(1.1);
    background: rgba(236, 72, 153, 0.4);
    box-shadow: 0 0 24px rgba(236, 72, 153, 0.8);
  }

  /* Right: Time, Shuffle, Repeat */
  .controls-right {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .time-display {
    font-size: 11px;
    color: #cbd5e1;
    font-variant-numeric: tabular-nums;
    margin-right: 2px;
  }

  .mini-btn {
    background: transparent;
    border: none;
    color: #94a3b8;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 3px;
    transition: color 0.15s ease;
  }

  .mini-btn svg { width: 14px; height: 14px; fill: currentColor; }
  .mini-btn:hover, .mini-btn.active { color: #f472b6; }

  /* Top Right Action Icons */
  .card-top-actions {
    position: absolute;
    top: 8px;
    right: 12px;
    display: flex;
    gap: 4px;
    z-index: 20;
  }

  .top-btn {
    background: transparent;
    border: none;
    color: #94a3b8;
    width: 22px;
    height: 22px;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: color 0.15s, background 0.15s;
  }

  .top-btn svg { width: 14px; height: 14px; fill: currentColor; }
  .top-btn:hover { background: rgba(255, 255, 255, 0.12); color: #fff; }
  .top-btn.close-btn:hover { background: rgba(239, 68, 68, 0.4); color: #ef4444; }

  /* SEARCH MODAL OVERLAY (Pure search, ZERO presets) */
  .search-modal {
    position: absolute;
    inset: 8px;
    background: rgba(18, 7, 26, 0.96);
    backdrop-filter: blur(36px);
    border: 1px solid rgba(236, 72, 153, 0.45);
    border-radius: 14px;
    padding: 10px;
    display: none;
    flex-direction: column;
    gap: 8px;
    z-index: 30;
    box-shadow: 0 16px 40px rgba(0, 0, 0, 0.8), 0 0 30px rgba(217, 70, 239, 0.35);
  }

  .search-modal.open { display: flex; }

  .search-bar {
    display: flex;
    gap: 8px;
  }

  .search-input {
    flex: 1;
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.18);
    border-radius: 8px;
    color: #fff;
    padding: 6px 12px;
    font-size: 12px;
    outline: none;
  }

  .search-input:focus {
    border-color: #ec4899;
  }

  .search-submit-btn {
    background: linear-gradient(135deg, #ec4899, #a855f7);
    border: none;
    border-radius: 8px;
    color: #fff;
    padding: 6px 14px;
    font-size: 11px;
    font-weight: 700;
    cursor: pointer;
  }

  .search-results-list {
    flex: 1;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 4px;
    max-height: 85px;
  }

  .search-results-list::-webkit-scrollbar { width: 4px; }
  .search-results-list::-webkit-scrollbar-thumb { background: rgba(236, 72, 153, 0.4); border-radius: 4px; }

  .result-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 5px 8px;
    border-radius: 6px;
    background: rgba(255, 255, 255, 0.05);
    cursor: pointer;
    transition: background 0.15s ease;
  }

  .result-item:hover {
    background: rgba(236, 72, 153, 0.22);
  }

  .result-thumb {
    width: 28px;
    height: 28px;
    border-radius: 4px;
    object-fit: cover;
  }

  .result-title {
    font-size: 11px;
    font-weight: 600;
    color: #fff;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .result-artist {
    font-size: 9px;
    color: #cbd5e1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
</style>
</head>
<body>

<div class="player-card" id="card">
  <!-- Glowing Neon Wave Canvas Background -->
  <canvas id="waves-canvas"></canvas>

  <!-- Top Right Actions -->
  <div class="card-top-actions">
    <button class="top-btn" id="btn-search-toggle" title="Search Any Song">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill-rule="evenodd" d="M10.5 3.75a6.75 6.75 0 1 0 4.298 11.968l4.492 4.493a.75.75 0 1 0 1.06-1.06l-4.493-4.493A6.75 6.75 0 0 0 10.5 3.75Zm-5.25 6.75a5.25 5.25 0 1 1 10.5 0 5.25 5.25 0 0 1-10.5 0Z" clip-rule="evenodd" /></svg>
    </button>
    <button class="top-btn close-btn" id="btn-close" title="Close">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill-rule="evenodd" d="M5.47 5.47a.75.75 0 0 1 1.06 0L12 10.94l5.47-5.47a.75.75 0 1 1 1.06 1.06L13.06 12l5.47 5.47a.75.75 0 1 1-1.06 1.06L12 13.06l-5.47 5.47a.75.75 0 0 1-1.06-1.06L10.94 12 5.47 6.53a.75.75 0 0 1 0-1.06Z" clip-rule="evenodd" /></svg>
    </button>
  </div>

  <!-- Album Artwork -->
  <div class="album-wrap">
    <img id="album-art" class="album-art" src="https://i.ytimg.com/vi/oC6brLXQe4I/hqdefault.jpg" alt="Cover">
  </div>

  <!-- Card Main Content -->
  <div class="card-main">
    <!-- Title & Source -->
    <div class="track-meta">
      <div class="track-title" id="track-title">BABYMONSTER - 'DESERVE' M/V</div>
      <div class="track-source" id="track-source">YouTube</div>
    </div>

    <!-- Real-Time Spectrum Equalizer Bars -->
    <div class="spectrum-bar-wrap" id="spectrum-bars"></div>

    <!-- Controls Row -->
    <div class="controls-bar">
      <!-- Left: Volume -->
      <div class="controls-left">
        <button class="vol-btn" id="btn-mute" title="Mute/Unmute">
          <svg viewBox="0 0 24 24"><path d="M14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77zm-2.5 9L7 8H3v8h4.5l4.5 4.23V3.77z"/></svg>
        </button>
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

  <!-- SEARCH MODAL OVERLAY (Pure search, ZERO presets) -->
  <div class="search-modal" id="search-modal">
    <div class="search-bar">
      <input type="text" class="search-input" id="search-input" placeholder="Search any song or artist on YouTube...">
      <button class="search-submit-btn" id="search-submit-btn">FIND</button>
      <button class="top-btn" id="btn-search-close">
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
  const btnClose = document.getElementById('btn-close');
  const volSlider = document.getElementById('vol-slider');
  const btnMute = document.getElementById('btn-mute');
  const btnShuffle = document.getElementById('btn-shuffle');
  const btnRepeat = document.getElementById('btn-repeat');
  const searchModal = document.getElementById('search-modal');
  const btnSearchToggle = document.getElementById('btn-search-toggle');
  const btnSearchClose = document.getElementById('btn-search-close');
  const searchInput = document.getElementById('search-input');
  const searchSubmitBtn = document.getElementById('search-submit-btn');
  const searchResultsList = document.getElementById('search-results-list');
  const spectrumContainer = document.getElementById('spectrum-bars');

  let isPlaying = false;
  let isMuted = false;
  let isRepeat = false;
  let isShuffle = false;
  let currentSongId = 'oC6brLXQe4I';

  // 1. Generate 34 spectrum bars
  const NUM_BARS = 34;
  const specBars = [];
  for (let i = 0; i < NUM_BARS; i++) {
    const b = document.createElement('div');
    b.className = 'spec-bar';
    spectrumContainer.appendChild(b);
    specBars.push(b);
  }

  // 2. Animated Flowing Neon Waves on Canvas
  const canvas = document.getElementById('waves-canvas');
  const ctx = canvas.getContext('2d');

  function resizeCanvas() {
    canvas.width = card.clientWidth;
    canvas.height = card.clientHeight;
  }
  window.addEventListener('resize', resizeCanvas);
  setTimeout(resizeCanvas, 50);

  let waveOffset = 0;

  function renderWaves() {
    requestAnimationFrame(renderWaves);

    // Dynamic wave animation speed & amplitude
    const speed = isPlaying ? 0.035 : 0.008;
    waveOffset += speed;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const W = canvas.width;
    const H = canvas.height;
    const centerY = H * 0.52;

    ctx.save();
    ctx.globalCompositeOperation = 'screen';

    // Layer 1: Electric Blue Ribbon
    drawNeonWave(ctx, W, centerY, waveOffset * 0.9, isPlaying ? 22 : 6, 0.007, 'rgba(56, 189, 248, 0.35)', 16);

    // Layer 2: Deep Violet Flow
    drawNeonWave(ctx, W, centerY + 4, waveOffset * 1.2 + 1.5, isPlaying ? 28 : 8, 0.009, 'rgba(168, 85, 247, 0.45)', 20);

    // Layer 3: Vibrant Magenta Core Ribbon
    drawNeonWave(ctx, W, centerY - 3, waveOffset * 1.5 + 3.0, isPlaying ? 35 : 10, 0.011, 'rgba(236, 72, 153, 0.65)', 24);

    ctx.restore();

    // Animate spectrum bars
    const t = waveOffset * 2.5;
    for (let i = 0; i < NUM_BARS; i++) {
      let h = 4;
      if (isPlaying) {
        // Multi-frequency harmonic motion
        const v = 0.35 + 0.35 * Math.sin(t + i * 0.35) + 0.30 * Math.cos(t * 1.7 - i * 0.5);
        h = Math.max(3, Math.min(22, v * 22));
      }
      specBars[i].style.height = h + 'px';
    }
  }

  function drawNeonWave(context, width, baseY, offset, amp, freq, color, blur) {
    context.save();
    context.beginPath();
    context.shadowColor = color;
    context.shadowBlur = blur;
    context.strokeStyle = color;
    context.lineWidth = 2.5;

    for (let x = 0; x <= width; x += 6) {
      const y = baseY + Math.sin(x * freq + offset) * amp + Math.cos(x * freq * 1.5 - offset * 0.7) * (amp * 0.4);
      if (x === 0) context.moveTo(x, y);
      else context.lineTo(x, y);
    }
    context.stroke();
    context.restore();
  }

  requestAnimationFrame(renderWaves);

  // 3. PLAYBACK CONTROLS
  function updatePlayState(playing) {
    isPlaying = playing;
    if (playing) {
      playIcon.style.display = 'none';
      pauseIcon.style.display = 'block';
    } else {
      playIcon.style.display = 'block';
      pauseIcon.style.display = 'none';
    }
  }

  btnPlayPause.addEventListener('click', (e) => {
    e.stopPropagation();
    if (audio.src) {
      if (audio.paused) {
        audio.play().then(() => updatePlayState(true)).catch(() => {});
      } else {
        audio.pause();
        updatePlayState(false);
      }
    } else {
      window.pywebview && window.pywebview.api.play_id(currentSongId);
    }
  });

  audio.addEventListener('play', () => updatePlayState(true));
  audio.addEventListener('pause', () => updatePlayState(false));
  audio.addEventListener('ended', () => {
    if (isRepeat) {
      audio.currentTime = 0;
      audio.play();
    } else {
      window.pywebview && window.pywebview.api.next_track();
    }
  });

  function formatTime(s) {
    if (!s || isNaN(s)) return '0:00';
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return m + ':' + (sec < 10 ? '0' : '') + sec;
  }

  audio.addEventListener('timeupdate', () => {
    timeDisplay.textContent = formatTime(audio.currentTime) + ' / ' + formatTime(audio.duration);
  });

  // Volume
  volSlider.addEventListener('input', (e) => {
    audio.volume = parseFloat(e.target.value);
    audio.muted = false;
    isMuted = false;
  });

  btnMute.addEventListener('click', (e) => {
    e.stopPropagation();
    isMuted = !isMuted;
    audio.muted = isMuted;
    btnMute.style.color = isMuted ? '#ef4444' : '#cbd5e1';
  });

  btnShuffle.addEventListener('click', (e) => {
    e.stopPropagation();
    isShuffle = !isShuffle;
    btnShuffle.classList.toggle('active', isShuffle);
  });

  btnRepeat.addEventListener('click', (e) => {
    e.stopPropagation();
    isRepeat = !isRepeat;
    btnRepeat.classList.toggle('active', isRepeat);
  });

  btnNext.addEventListener('click', (e) => {
    e.stopPropagation();
    window.pywebview && window.pywebview.api.next_track();
  });

  btnPrev.addEventListener('click', (e) => {
    e.stopPropagation();
    window.pywebview && window.pywebview.api.prev_track();
  });

  btnClose.addEventListener('click', (e) => {
    e.stopPropagation();
    window.pywebview && window.pywebview.api.close_window();
  });

  // Search Toggle
  btnSearchToggle.addEventListener('click', (e) => {
    e.stopPropagation();
    searchModal.classList.toggle('open');
    if (searchModal.classList.contains('open')) searchInput.focus();
  });

  btnSearchClose.addEventListener('click', (e) => {
    e.stopPropagation();
    searchModal.classList.remove('open');
  });

  function triggerSearch() {
    const q = searchInput.value.trim();
    if (q) {
      searchResultsList.innerHTML = '<div style="color:#94a3b8;font-size:11px;padding:12px;text-align:center;">Searching YouTube...</div>';
      window.pywebview && window.pywebview.api.search_songs(q);
    }
  }

  searchSubmitBtn.addEventListener('click', (e) => { e.stopPropagation(); triggerSearch(); });
  searchInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') triggerSearch(); });

  window.renderSearchResults = function(jsonStr) {
    const list = JSON.parse(jsonStr);
    searchResultsList.innerHTML = '';
    if (!list || list.length === 0) {
      searchResultsList.innerHTML = '<div style="color:#94a3b8;font-size:11px;padding:12px;text-align:center;">No songs found.</div>';
      return;
    }
    list.forEach(item => {
      const row = document.createElement('div');
      row.className = 'result-item';
      row.innerHTML = `
        <img class="result-thumb" src="${item.thumb}" alt="thumb">
        <div style="flex:1;min-width:0;">
          <div class="result-title">${item.title}</div>
          <div class="result-artist">${item.artist}</div>
        </div>
      `;
      row.addEventListener('click', () => {
        searchModal.classList.remove('open');
        playSelectedSong(item.id, item.title, item.artist, item.thumb);
      });
      searchResultsList.appendChild(row);
    });
  };

  function playSelectedSong(id, title, artist, thumb) {
    currentSongId = id;
    trackTitle.textContent = title;
    trackSource.textContent = artist || 'YouTube';
    if (thumb) albumArt.src = thumb;
    window.pywebview && window.pywebview.api.play_id(id);
  }

  window.setStreamUrl = function(streamUrl) {
    if (streamUrl) {
      audio.src = streamUrl;
      audio.volume = parseFloat(volSlider.value);
      audio.play().then(() => updatePlayState(true)).catch(e => console.log(e));
    }
  };

  // Dragging support
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

  document.addEventListener('mouseup', () => { isDragging = false; });
</script>
</body>
</html>
"""

class MusicAPI:
    def __init__(self, win_holder):
        self.win_holder = win_holder
        self.history = [
            {"id": "oC6brLXQe4I", "title": "BABYMONSTER - 'DESERVE' M/V", "artist": "YouTube", "thumb": "https://i.ytimg.com/vi/oC6brLXQe4I/hqdefault.jpg"},
            {"id": "dX3k_QDnzHE", "title": "Midnight City", "artist": "M83", "thumb": "https://i.ytimg.com/vi/dX3k_QDnzHE/hqdefault.jpg"}
        ]
        self.history_index = 0
        self.ydl_opts_search = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
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
                w.move(w.x + int(dx), w.y + int(dy))
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


def main():
    win_holder = [None]
    api = MusicAPI(win_holder)

    # Clean widget dimensions: NO outer white band!
    # on_top=False ensures it NEVER overlaps other applications
    w = webview.create_window(
        title='Desktop Music Visualizer',
        html=HTML_CONTENT,
        width=WIDGET_W,
        height=WIDGET_H,
        x=POS_X,
        y=POS_Y,
        frameless=True,
        resizable=False,
        on_top=False,
        js_api=api,
        background_color='#12071a'
    )
    win_holder[0] = w

    def auto_start():
        import time
        time.sleep(1.2)
        api.play_id("oC6brLXQe4I")

    threading.Thread(target=auto_start, daemon=True).start()
    webview.start()

if __name__ == '__main__':
    main()
