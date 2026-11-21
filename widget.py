"""
YouTube Desktop Music Player Widget
- 100% Transparent Frosted Glassmorphism card (wallpaper shows through)
- Prominent animated music sound waves
- Clean user-friendly search with selectable results list
- ZERO hardcoded presets
- Desktop level (on_top=False, never overlaps other apps)
- Centered on desktop
"""
import webview
import yt_dlp
import threading
import json
import ctypes
import os
import sys

# Screen Metrics for perfect center positioning
user32 = ctypes.windll.user32
SCREEN_W = user32.GetSystemMetrics(0)
SCREEN_H = user32.GetSystemMetrics(1)

WIDGET_W = 460
WIDGET_H = 150

POS_X = (SCREEN_W - WIDGET_W) // 2
POS_Y = (SCREEN_H - WIDGET_H) // 2

HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>YouTube Desktop Widget</title>
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
    background: transparent !important;
  }

  /* 100% Frosted Transparent Glass Card */
  .glass-card {
    width: 100%;
    height: 100%;
    background: rgba(18, 22, 32, 0.42);
    backdrop-filter: blur(28px) saturate(190%);
    -webkit-backdrop-filter: blur(28px) saturate(190%);
    border: 1px solid rgba(255, 255, 255, 0.18);
    border-radius: 16px;
    box-shadow: 0 16px 38px rgba(0, 0, 0, 0.45), inset 0 1px 1px rgba(255, 255, 255, 0.28);
    display: flex;
    align-items: center;
    padding: 14px 18px;
    gap: 16px;
    position: relative;
    cursor: grab;
    transition: background 0.25s ease, border-color 0.25s ease;
  }

  .glass-card:active {
    cursor: grabbing;
  }

  .glass-card:hover {
    background: rgba(22, 28, 40, 0.52);
    border-color: rgba(255, 255, 255, 0.26);
    box-shadow: 0 20px 44px rgba(0, 0, 0, 0.55), 0 0 20px rgba(56, 189, 248, 0.2);
  }

  /* Glass Top Light Edge */
  .glass-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 16px;
    right: 16px;
    height: 1px;
    background: linear-gradient(90deg, transparent 0%, rgba(255, 255, 255, 0.45) 50%, transparent 100%);
    pointer-events: none;
  }

  /* Album Art */
  .album-wrap {
    width: 96px;
    height: 96px;
    border-radius: 12px;
    overflow: hidden;
    position: relative;
    flex-shrink: 0;
    box-shadow: 0 8px 22px rgba(0, 0, 0, 0.55), 0 0 0 1px rgba(255, 255, 255, 0.12);
    background: rgba(0, 0, 0, 0.3);
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

  /* Info & Controls Column */
  .info-controls {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 2px;
  }

  .track-info {
    display: flex;
    flex-direction: column;
  }

  .track-title {
    font-size: 16px;
    font-weight: 600;
    color: #ffffff;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    letter-spacing: -0.2px;
    text-shadow: 0 2px 6px rgba(0, 0, 0, 0.6);
  }

  .track-artist {
    font-size: 12px;
    font-weight: 400;
    color: #cbd5e1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-top: 1px;
    text-shadow: 0 1px 3px rgba(0, 0, 0, 0.6);
  }

  /* PROMINENT AUDIO SOUND WAVES */
  .waves-visualizer {
    display: flex;
    align-items: center;
    gap: 3px;
    height: 20px;
    margin: 5px 0 3px 0;
  }

  .wave-bar {
    width: 3.5px;
    height: 4px;
    background: #38bdf8;
    border-radius: 3px;
    transition: height 0.15s ease, background-color 0.2s ease;
    box-shadow: 0 0 6px rgba(56, 189, 248, 0.6);
  }

  /* Animated waves dancing to music */
  .playing .wave-bar {
    animation: soundWave 0.9s ease-in-out infinite alternate;
  }

  .playing .wave-bar:nth-child(1)  { animation-duration: 0.60s; animation-delay: 0.10s; }
  .playing .wave-bar:nth-child(2)  { animation-duration: 0.80s; animation-delay: 0.25s; }
  .playing .wave-bar:nth-child(3)  { animation-duration: 0.50s; animation-delay: 0.05s; }
  .playing .wave-bar:nth-child(4)  { animation-duration: 0.95s; animation-delay: 0.20s; }
  .playing .wave-bar:nth-child(5)  { animation-duration: 0.65s; animation-delay: 0.40s; }
  .playing .wave-bar:nth-child(6)  { animation-duration: 0.85s; animation-delay: 0.15s; }
  .playing .wave-bar:nth-child(7)  { animation-duration: 0.55s; animation-delay: 0.30s; }
  .playing .wave-bar:nth-child(8)  { animation-duration: 0.90s; animation-delay: 0.10s; }
  .playing .wave-bar:nth-child(9)  { animation-duration: 0.70s; animation-delay: 0.35s; }
  .playing .wave-bar:nth-child(10) { animation-duration: 0.60s; animation-delay: 0.05s; }
  .playing .wave-bar:nth-child(11) { animation-duration: 0.85s; animation-delay: 0.20s; }
  .playing .wave-bar:nth-child(12) { animation-duration: 0.50s; animation-delay: 0.30s; }
  .playing .wave-bar:nth-child(13) { animation-duration: 0.75s; animation-delay: 0.15s; }
  .playing .wave-bar:nth-child(14) { animation-duration: 0.95s; animation-delay: 0.25s; }

  @keyframes soundWave {
    0%   { height: 4px;  background: #38bdf8; }
    50%  { height: 19px; background: #67e8f9; }
    100% { height: 7px;  background: #0284c7; }
  }

  /* Progress Bar */
  .progress-wrap {
    width: 100%;
    height: 3px;
    background: rgba(255, 255, 255, 0.16);
    border-radius: 2px;
    cursor: pointer;
    position: relative;
    margin-bottom: 6px;
  }

  .progress-bar {
    height: 100%;
    width: 0%;
    background: linear-gradient(90deg, #38bdf8, #67e8f9);
    border-radius: 2px;
    box-shadow: 0 0 8px rgba(56, 189, 248, 0.7);
    transition: width 0.1s linear;
  }

  /* Controls Row */
  .controls-row {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  /* Tailwind Icon Buttons */
  .btn-icon {
    background: transparent;
    border: none;
    color: #cbd5e1;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 6px;
    border-radius: 8px;
    transition: color 0.15s ease, transform 0.1s ease, background 0.15s ease;
  }

  .btn-icon:hover {
    color: #ffffff;
    background: rgba(255, 255, 255, 0.12);
    transform: scale(1.1);
  }

  .btn-icon:active {
    transform: scale(0.92);
  }

  .btn-icon svg {
    width: 18px;
    height: 18px;
    fill: currentColor;
    display: block;
  }

  /* Cyan Play/Pause Button */
  .btn-play-pause {
    width: 38px;
    height: 38px;
    background: linear-gradient(135deg, #38bdf8 0%, #06b6d4 100%);
    border-radius: 10px;
    border: none;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    box-shadow: 0 4px 14px rgba(6, 182, 212, 0.5), inset 0 1px 1px rgba(255, 255, 255, 0.4);
    transition: transform 0.15s ease, box-shadow 0.15s ease, filter 0.15s ease;
  }

  .btn-play-pause:hover {
    transform: scale(1.08);
    box-shadow: 0 6px 18px rgba(6, 182, 212, 0.7);
    filter: brightness(1.1);
  }

  .btn-play-pause:active {
    transform: scale(0.94);
  }

  .btn-play-pause svg {
    width: 18px;
    height: 18px;
    fill: #09131f;
    display: block;
  }

  /* YouTube Music Badge */
  .yt-badge {
    margin-left: auto;
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    color: #cbd5e1;
    font-weight: 500;
  }

  .yt-badge svg {
    width: 14px;
    height: 14px;
    display: block;
  }

  /* Top Right Action Icons */
  .top-actions {
    position: absolute;
    top: 8px;
    right: 12px;
    display: flex;
    gap: 4px;
    z-index: 10;
  }

  .action-btn {
    background: transparent;
    border: none;
    color: #94a3b8;
    width: 24px;
    height: 24px;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
  }

  .action-btn svg {
    width: 15px;
    height: 15px;
    fill: currentColor;
    display: block;
  }

  .action-btn:hover {
    background: rgba(255, 255, 255, 0.15);
    color: #ffffff;
  }

  .action-btn.btn-close:hover {
    background: rgba(239, 68, 68, 0.4);
    color: #ef4444;
  }

  /* USER-FRIENDLY SEARCH MODAL OVERLAY (NO PRESETS) */
  .search-overlay {
    position: absolute;
    inset: 8px;
    background: rgba(16, 20, 28, 0.92);
    backdrop-filter: blur(36px);
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 12px;
    padding: 10px;
    display: none;
    flex-direction: column;
    gap: 8px;
    z-index: 30;
    box-shadow: 0 16px 36px rgba(0, 0, 0, 0.7);
  }

  .search-overlay.open {
    display: flex;
  }

  .search-header {
    display: flex;
    gap: 6px;
    align-items: center;
  }

  .search-input {
    flex: 1;
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.16);
    border-radius: 8px;
    color: #fff;
    padding: 7px 10px;
    font-size: 12px;
    outline: none;
  }

  .search-input:focus {
    border-color: #38bdf8;
    background: rgba(255, 255, 255, 0.15);
  }

  .search-go-btn {
    background: linear-gradient(135deg, #38bdf8, #06b6d4);
    border: none;
    border-radius: 8px;
    color: #09131f;
    font-size: 11px;
    font-weight: 700;
    padding: 7px 12px;
    cursor: pointer;
  }

  /* SELECTABLE RESULTS LIST */
  .results-list {
    flex: 1;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 4px;
    max-height: 85px;
  }

  .results-list::-webkit-scrollbar { width: 4px; }
  .results-list::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.2); border-radius: 4px; }

  .song-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 5px 8px;
    border-radius: 6px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid transparent;
    cursor: pointer;
    transition: background 0.15s ease, border-color 0.15s ease;
  }

  .song-item:hover {
    background: rgba(56, 189, 248, 0.15);
    border-color: rgba(56, 189, 248, 0.4);
  }

  .song-thumb {
    width: 28px;
    height: 28px;
    border-radius: 4px;
    object-fit: cover;
    flex-shrink: 0;
  }

  .song-details {
    flex: 1;
    min-width: 0;
  }

  .song-item-title {
    font-size: 11px;
    font-weight: 600;
    color: #ffffff;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .song-item-artist {
    font-size: 9px;
    color: #94a3b8;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  /* Loading Spinner */
  .loading-ring {
    display: none;
    width: 16px;
    height: 16px;
    border: 2px solid rgba(9, 19, 31, 0.25);
    border-top: 2px solid #09131f;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin { to { transform: rotate(360deg); } }

  .loading .loading-ring { display: block; }
  .loading .play-icon { display: none; }
  .loading .pause-icon { display: none; }
</style>
</head>
<body>

<div class="glass-card" id="card">
  <!-- Top Right Actions -->
  <div class="top-actions">
    <!-- Tailwind Search (Magnifying Glass) Icon -->
    <button class="action-btn" id="btn-search-toggle" title="Search Song">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill-rule="evenodd" d="M10.5 3.75a6.75 6.75 0 1 0 4.298 11.968l4.492 4.493a.75.75 0 1 0 1.06-1.06l-4.493-4.493A6.75 6.75 0 0 0 10.5 3.75Zm-5.25 6.75a5.25 5.25 0 1 1 10.5 0 5.25 5.25 0 0 1-10.5 0Z" clip-rule="evenodd" /></svg>
    </button>
    <!-- Tailwind Close (X Mark) Icon -->
    <button class="action-btn btn-close" id="btn-close" title="Close Widget">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill-rule="evenodd" d="M5.47 5.47a.75.75 0 0 1 1.06 0L12 10.94l5.47-5.47a.75.75 0 1 1 1.06 1.06L13.06 12l5.47 5.47a.75.75 0 1 1-1.06 1.06L12 13.06l-5.47 5.47a.75.75 0 0 1-1.06-1.06L10.94 12 5.47 6.53a.75.75 0 0 1 0-1.06Z" clip-rule="evenodd" /></svg>
    </button>
  </div>

  <!-- Album Art -->
  <div class="album-wrap" id="album-wrap">
    <img id="album-art" class="album-art" src="https://i.ytimg.com/vi/dX3k_QDnzHE/hqdefault.jpg" alt="Cover">
  </div>

  <!-- Info & Controls -->
  <div class="info-controls">
    <div class="track-info">
      <div class="track-title" id="track-title">Midnight City</div>
      <div class="track-artist" id="track-artist">M83</div>
    </div>

    <!-- PROMINENT AUDIO SOUND WAVES -->
    <div class="waves-visualizer" id="waveform">
      <div class="wave-bar"></div>
      <div class="wave-bar"></div>
      <div class="wave-bar"></div>
      <div class="wave-bar"></div>
      <div class="wave-bar"></div>
      <div class="wave-bar"></div>
      <div class="wave-bar"></div>
      <div class="wave-bar"></div>
      <div class="wave-bar"></div>
      <div class="wave-bar"></div>
      <div class="wave-bar"></div>
      <div class="wave-bar"></div>
      <div class="wave-bar"></div>
      <div class="wave-bar"></div>
    </div>

    <!-- Progress Bar -->
    <div class="progress-wrap" id="progress-wrap">
      <div class="progress-bar" id="progress-bar"></div>
    </div>

    <!-- Controls Row with Tailwind Icons -->
    <div class="controls-row">
      <!-- Previous Track (Tailwind Backward Icon) -->
      <button class="btn-icon" id="btn-prev" title="Previous Track">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M9.195 18.44c1.25.714 2.805-.189 2.805-1.629v-2.34l6.945 3.968c1.25.715 2.805-.188 2.805-1.628V7.189c0-1.44-1.555-2.343-2.805-1.628L12 9.529v-2.34c0-1.44-1.555-2.343-2.805-1.628l-7.108 4.061c-1.26.72-1.26 2.536 0 3.256l7.108 4.061Z" /></svg>
      </button>

      <!-- Play / Pause Cyan Button (Tailwind Play/Pause Icons) -->
      <button class="btn-play-pause" id="btn-play-pause" title="Play / Pause">
        <div class="loading-ring"></div>
        <svg class="play-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill-rule="evenodd" d="M4.5 5.653c0-1.427 1.529-2.33 2.779-1.643l11.54 6.347c1.295.712 1.295 2.573 0 3.286L7.28 19.99c-1.25.687-2.779-.217-2.779-1.643V5.653Z" clip-rule="evenodd" /></svg>
        <svg class="pause-icon" style="display:none;" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill-rule="evenodd" d="M6.75 5.25a.75.75 0 0 1 .75.75v12a.75.75 0 0 1-1.5 0v-12a.75.75 0 0 1 .75-.75Zm9 0a.75.75 0 0 1 .75.75v12a.75.75 0 0 1-1.5 0v-12a.75.75 0 0 1 .75-.75Z" clip-rule="evenodd" /></svg>
      </button>

      <!-- Next Track (Tailwind Forward Icon) -->
      <button class="btn-icon" id="btn-next" title="Next Track">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M5.055 7.06C3.805 6.347 2.25 7.25 2.25 8.69v8.622c0 1.44 1.555 2.343 2.805 1.628L12 14.971v2.341c0 1.44 1.555 2.343 2.805 1.628l7.108-4.061c1.26-.72 1.26-2.536 0-3.256L14.805 7.562V5.22c0-1.44-1.555-2.343-2.805-1.628L5.055 7.06Z" /></svg>
      </button>

      <!-- YouTube Music Badge with SVG Logo -->
      <div class="yt-badge">
        <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" fill="#ef4444"/><polygon points="10 8 16 12 10 16" fill="#ffffff"/></svg>
        <span>YouTube Music</span>
      </div>
    </div>
  </div>

  <!-- USER-FRIENDLY SEARCH DRAWER (NO PRESETS, PURE USER SEARCH) -->
  <div class="search-overlay" id="search-overlay">
    <div class="search-header">
      <input type="text" class="search-input" id="search-input" placeholder="Search any song or artist on YouTube...">
      <button class="search-go-btn" id="search-go-btn">SEARCH</button>
      <button class="action-btn" id="search-close-btn" title="Close Search">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill-rule="evenodd" d="M5.47 5.47a.75.75 0 0 1 1.06 0L12 10.94l5.47-5.47a.75.75 0 1 1 1.06 1.06L13.06 12l5.47 5.47a.75.75 0 1 1-1.06 1.06L12 13.06l-5.47 5.47a.75.75 0 0 1-1.06-1.06L10.94 12 5.47 6.53a.75.75 0 0 1 0-1.06Z" clip-rule="evenodd" /></svg>
      </button>
    </div>
    <!-- SELECTABLE RESULTS LIST -->
    <div class="results-list" id="results-list">
      <div style="color:#94a3b8;font-size:11px;padding:12px;text-align:center;">Type a song above and press Search</div>
    </div>
  </div>
</div>

<audio id="audio-player" preload="auto"></audio>

<script>
  const audio = document.getElementById('audio-player');
  const card = document.getElementById('card');
  const btnPlayPause = document.getElementById('btn-play-pause');
  const playIcon = btnPlayPause.querySelector('.play-icon');
  const pauseIcon = btnPlayPause.querySelector('.pause-icon');
  const btnPrev = document.getElementById('btn-prev');
  const btnNext = document.getElementById('btn-next');
  const btnClose = document.getElementById('btn-close');
  const albumArt = document.getElementById('album-art');
  const trackTitle = document.getElementById('track-title');
  const trackArtist = document.getElementById('track-artist');
  const progressBar = document.getElementById('progress-bar');
  const progressWrap = document.getElementById('progress-wrap');
  const waveform = document.getElementById('waveform');
  const btnSearchToggle = document.getElementById('btn-search-toggle');
  const searchOverlay = document.getElementById('search-overlay');
  const searchInput = document.getElementById('search-input');
  const searchGoBtn = document.getElementById('search-go-btn');
  const searchCloseBtn = document.getElementById('search-close-btn');
  const resultsList = document.getElementById('results-list');

  let isPlaying = false;
  let currentSongId = 'dX3k_QDnzHE';

  // Toggle Wave animation & play/pause icon
  function updatePlayState(playing) {
    isPlaying = playing;
    if (playing) {
      playIcon.style.display = 'none';
      pauseIcon.style.display = 'block';
      waveform.classList.add('playing');
    } else {
      playIcon.style.display = 'block';
      pauseIcon.style.display = 'none';
      waveform.classList.remove('playing');
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
      playSong(currentSongId, trackTitle.textContent, trackArtist.textContent, albumArt.src);
    }
  });

  audio.addEventListener('play', () => updatePlayState(true));
  audio.addEventListener('pause', () => updatePlayState(false));
  audio.addEventListener('ended', () => {
    window.pywebview && window.pywebview.api.next_track();
  });

  audio.addEventListener('timeupdate', () => {
    if (audio.duration) {
      const pct = (audio.currentTime / audio.duration) * 100;
      progressBar.style.width = pct + '%';
    }
  });

  progressWrap.addEventListener('click', (e) => {
    e.stopPropagation();
    if (audio.duration) {
      const rect = progressWrap.getBoundingClientRect();
      const clickX = e.clientX - rect.left;
      const pct = clickX / rect.width;
      audio.currentTime = pct * audio.duration;
    }
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
    searchOverlay.classList.toggle('open');
    if (searchOverlay.classList.contains('open')) {
      searchInput.focus();
    }
  });

  searchCloseBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    searchOverlay.classList.remove('open');
  });

  searchGoBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    const q = searchInput.value.trim();
    if (q) doSearch(q);
  });

  searchInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      const q = searchInput.value.trim();
      if (q) doSearch(q);
    }
  });

  function doSearch(q) {
    resultsList.innerHTML = '<div style="color:#94a3b8;font-size:11px;padding:12px;text-align:center;">Searching YouTube...</div>';
    window.pywebview && window.pywebview.api.search_songs(q);
  }

  // Called from Python when search results arrive
  window.renderSearchResults = function(resultsJson) {
    const results = JSON.parse(resultsJson);
    resultsList.innerHTML = '';
    if (!results || results.length === 0) {
      resultsList.innerHTML = '<div style="color:#94a3b8;font-size:11px;padding:12px;text-align:center;">No results found.</div>';
      return;
    }

    results.forEach(item => {
      const row = document.createElement('div');
      row.className = 'song-item';
      row.innerHTML = `
        <img class="song-thumb" src="${item.thumb}" alt="thumb">
        <div class="song-details">
          <div class="song-item-title">${item.title}</div>
          <div class="song-item-artist">${item.artist}</div>
        </div>
      `;
      row.addEventListener('click', () => {
        searchOverlay.classList.remove('open');
        playSong(item.id, item.title, item.artist, item.thumb);
      });
      resultsList.appendChild(row);
    });
  };

  function playSong(id, title, artist, thumb) {
    currentSongId = id;
    btnPlayPause.classList.add('loading');
    trackTitle.textContent = title;
    trackArtist.textContent = artist;
    if (thumb) albumArt.src = thumb;
    window.pywebview && window.pywebview.api.play_selected_song(id, title, artist, thumb);
  }

  // Called from Python when direct stream is ready
  window.setStreamUrl = function(streamUrl) {
    btnPlayPause.classList.remove('loading');
    if (streamUrl) {
      audio.src = streamUrl;
      audio.play().then(() => updatePlayState(true)).catch(err => console.log(err));
    }
  };

  // Dragging support
  let isDragging = false;
  let startX = 0, startY = 0;

  card.addEventListener('mousedown', (e) => {
    if (e.target.closest('button') || e.target.closest('input') || e.target.closest('.results-list')) return;
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
    isDragging = false;
  });
</script>
</body>
</html>
"""

class MusicAPI:
    def __init__(self, win_holder):
        self.win_holder = win_holder
        self.history = []
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

    def play_selected_song(self, vid_id, title, artist, thumb):
        song = {"id": vid_id, "title": title, "artist": artist, "thumb": thumb}
        if not self.history or self.history[-1].get('id') != vid_id:
            self.history.append(song)
            self.history_index = len(self.history) - 1
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
            self.play_selected_song(s['id'], s['title'], s['artist'], s['thumb'])

    def prev_track(self):
        if self.history and self.history_index > 0:
            self.history_index -= 1
            s = self.history[self.history_index]
            self.play_selected_song(s['id'], s['title'], s['artist'], s['thumb'])


def main():
    win_holder = [None]
    api = MusicAPI(win_holder)

    # 100% transparent frameless window - only the frosted glass card is visible
    # on_top=False ensures it NEVER overlaps other apps!
    w = webview.create_window(
        title='YouTube Desktop Widget',
        html=HTML_CONTENT,
        width=WIDGET_W,
        height=WIDGET_H,
        x=POS_X,
        y=POS_Y,
        frameless=True,
        resizable=False,
        transparent=True,  # <--- TRANSPARENT FROSTED GLASS!
        on_top=False,      # <--- WILL NOT OVERLAP APPS!
        js_api=api
    )
    win_holder[0] = w

    # Start initial track (Midnight City)
    def auto_start():
        import time
        time.sleep(1.2)
        api.play_selected_song("dX3k_QDnzHE", "Midnight City", "M83", "https://i.ytimg.com/vi/dX3k_QDnzHE/hqdefault.jpg")

    threading.Thread(target=auto_start, daemon=True).start()
    webview.start()

if __name__ == '__main__':
    main()
