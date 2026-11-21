"""
YouTube Desktop Music Player Widget
Windows 11 Acrylic Desktop Widget with:
- Desktop level (on_top=False so it never overlaps other apps)
- Animated waveform audio visualizer (waves)
- User-friendly search with selectable song list
- Official Tailwind / Heroicons SVGs
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
WIDGET_H = 360

POS_X = (SCREEN_W - WIDGET_W) // 2
POS_Y = (SCREEN_H - WIDGET_H) // 2

PRESET_TRACKS = [
    {"id": "dX3k_QDnzHE", "title": "Midnight City", "artist": "M83", "thumb": "https://i.ytimg.com/vi/dX3k_QDnzHE/hqdefault.jpg"},
    {"id": "2wA_b644DaQ", "title": "SHEESH", "artist": "BABYMONSTER", "thumb": "https://i.ytimg.com/vi/2wA_b644DaQ/hqdefault.jpg"},
    {"id": "olDWbQeT3Q8", "title": "BATTER UP", "artist": "BABYMONSTER", "thumb": "https://i.ytimg.com/vi/olDWbQeT3Q8/hqdefault.jpg"},
    {"id": "8Q9PjM2o3_E", "title": "DARK ARIA", "artist": "SawanoHiroyuki[nZk] (Solo Leveling)", "thumb": "https://i.ytimg.com/vi/8Q9PjM2o3_E/hqdefault.jpg"},
    {"id": "fhzKLfZq6gs", "title": "SPECIALZ", "artist": "King Gnu (Jujutsu Kaisen)", "thumb": "https://i.ytimg.com/vi/fhzKLfZq6gs/hqdefault.jpg"},
    {"id": "Kynt3hQ28lM", "title": "Blue Bird", "artist": "Ikimonogakari (Naruto)", "thumb": "https://i.ytimg.com/vi/Kynt3hQ28lM/hqdefault.jpg"},
    {"id": "1lsn2tT5yTc", "title": "Number One", "artist": "Hazel Fernandes (Bleach)", "thumb": "https://i.ytimg.com/vi/1lsn2tT5yTc/hqdefault.jpg"},
    {"id": "uY5s2W3u3sI", "title": "HIGHEST", "artist": "OxT (Eminence in Shadow)", "thumb": "https://i.ytimg.com/vi/uY5s2W3u3sI/hqdefault.jpg"},
    {"id": "faqmNf_fZlE", "title": "Departure!", "artist": "Masatoshi Ono (Hunter x Hunter)", "thumb": "https://i.ytimg.com/vi/faqmNf_fZlE/hqdefault.jpg"},
]

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
    background: #0d1117;
  }

  /* Main Container */
  .widget-container {
    width: 100%;
    height: 100%;
    background: linear-gradient(145deg, rgba(28, 33, 46, 0.96) 0%, rgba(15, 18, 25, 0.98) 100%);
    border: 1px solid rgba(255, 255, 255, 0.14);
    box-shadow: inset 0 1px 1px rgba(255, 255, 255, 0.22), 0 20px 45px rgba(0, 0, 0, 0.7);
    display: flex;
    flex-direction: column;
    padding: 14px 16px;
    gap: 12px;
    position: relative;
    cursor: grab;
  }

  .widget-container:active {
    cursor: grabbing;
  }

  /* Glass Top Highlight */
  .widget-container::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent 0%, rgba(255, 255, 255, 0.35) 40%, rgba(56, 189, 248, 0.5) 60%, transparent 100%);
    pointer-events: none;
  }

  /* TOP ROW: Album + Info + Controls */
  .now-playing-card {
    display: flex;
    align-items: center;
    gap: 14px;
    position: relative;
    flex-shrink: 0;
  }

  /* Album Art */
  .album-wrap {
    width: 88px;
    height: 88px;
    border-radius: 10px;
    overflow: hidden;
    position: relative;
    flex-shrink: 0;
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.6), 0 0 0 1px rgba(255, 255, 255, 0.1);
    background: #111;
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
    margin-bottom: 2px;
  }

  .track-title {
    font-size: 15px;
    font-weight: 600;
    color: #ffffff;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    letter-spacing: -0.2px;
    line-height: 1.25;
  }

  .track-artist {
    font-size: 12px;
    font-weight: 400;
    color: #94a3b8;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-top: 2px;
  }

  /* Waveform Audio Visualizer (WAVES) */
  .waveform-container {
    display: flex;
    align-items: center;
    gap: 3px;
    height: 16px;
    margin: 3px 0;
  }

  .wave-bar {
    width: 3px;
    height: 4px;
    background: #38bdf8;
    border-radius: 2px;
    transition: height 0.15s ease, background-color 0.2s ease;
  }

  /* Animated waves when playing */
  .playing .wave-bar {
    animation: wavePulse 1s ease-in-out infinite alternate;
  }

  .playing .wave-bar:nth-child(1)  { animation-duration: 0.65s; animation-delay: 0.1s; }
  .playing .wave-bar:nth-child(2)  { animation-duration: 0.85s; animation-delay: 0.3s; }
  .playing .wave-bar:nth-child(3)  { animation-duration: 0.55s; animation-delay: 0.05s; }
  .playing .wave-bar:nth-child(4)  { animation-duration: 0.95s; animation-delay: 0.2s; }
  .playing .wave-bar:nth-child(5)  { animation-duration: 0.70s; animation-delay: 0.4s; }
  .playing .wave-bar:nth-child(6)  { animation-duration: 0.60s; animation-delay: 0.15s; }
  .playing .wave-bar:nth-child(7)  { animation-duration: 0.80s; animation-delay: 0.25s; }
  .playing .wave-bar:nth-child(8)  { animation-duration: 0.50s; animation-delay: 0.35s; }
  .playing .wave-bar:nth-child(9)  { animation-duration: 0.90s; animation-delay: 0.1s; }
  .playing .wave-bar:nth-child(10) { animation-duration: 0.75s; animation-delay: 0.05s; }
  .playing .wave-bar:nth-child(11) { animation-duration: 0.65s; animation-delay: 0.3s; }
  .playing .wave-bar:nth-child(12) { animation-duration: 0.85s; animation-delay: 0.2s; }

  @keyframes wavePulse {
    0%   { height: 4px;  background: #38bdf8; }
    50%  { height: 16px; background: #67e8f9; }
    100% { height: 7px;  background: #0284c7; }
  }

  /* Progress Bar */
  .progress-wrap {
    width: 100%;
    height: 3px;
    background: rgba(255, 255, 255, 0.12);
    border-radius: 2px;
    cursor: pointer;
    position: relative;
    margin-bottom: 4px;
  }

  .progress-bar {
    height: 100%;
    width: 0%;
    background: linear-gradient(90deg, #38bdf8, #67e8f9);
    border-radius: 2px;
    box-shadow: 0 0 8px rgba(56, 189, 248, 0.6);
    transition: width 0.1s linear;
  }

  /* Controls Row */
  .controls-row {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .btn-icon {
    background: transparent;
    border: none;
    color: #cbd5e1;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 5px;
    border-radius: 8px;
    transition: color 0.15s ease, transform 0.1s ease, background 0.15s ease;
  }

  .btn-icon:hover {
    color: #ffffff;
    background: rgba(255, 255, 255, 0.08);
    transform: scale(1.1);
  }

  .btn-icon:active {
    transform: scale(0.92);
  }

  .btn-icon svg {
    width: 17px;
    height: 17px;
    fill: currentColor;
    display: block;
  }

  /* Cyan Play/Pause Button */
  .btn-play-pause {
    width: 36px;
    height: 36px;
    background: linear-gradient(135deg, #38bdf8 0%, #06b6d4 100%);
    border-radius: 10px;
    border: none;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    box-shadow: 0 4px 14px rgba(6, 182, 212, 0.45), inset 0 1px 1px rgba(255, 255, 255, 0.4);
    transition: transform 0.15s ease, box-shadow 0.15s ease, filter 0.15s ease;
  }

  .btn-play-pause:hover {
    transform: scale(1.08);
    box-shadow: 0 6px 18px rgba(6, 182, 212, 0.65);
    filter: brightness(1.08);
  }

  .btn-play-pause:active {
    transform: scale(0.94);
  }

  .btn-play-pause svg {
    width: 17px;
    height: 17px;
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
    color: #94a3b8;
    font-weight: 500;
  }

  .yt-badge svg {
    width: 13px;
    height: 13px;
    display: block;
  }

  /* Top Right Close Button */
  .top-close {
    position: absolute;
    top: -2px;
    right: 0;
  }

  .action-btn {
    background: transparent;
    border: none;
    color: #64748b;
    width: 22px;
    height: 22px;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
  }

  .action-btn svg {
    width: 14px;
    height: 14px;
    fill: currentColor;
    display: block;
  }

  .action-btn:hover {
    background: rgba(239, 68, 68, 0.35);
    color: #ef4444;
  }

  /* SECTION 2: USER-FRIENDLY SEARCH & SELECTION */
  .search-section {
    display: flex;
    flex-direction: column;
    gap: 8px;
    flex: 1;
    min-height: 0;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
    padding-top: 10px;
  }

  .search-input-wrap {
    display: flex;
    gap: 6px;
    align-items: center;
  }

  .search-input {
    flex: 1;
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.14);
    border-radius: 8px;
    color: #fff;
    padding: 6px 10px;
    font-size: 12px;
    outline: none;
  }

  .search-input:focus {
    border-color: #38bdf8;
    background: rgba(255, 255, 255, 0.12);
  }

  .search-btn {
    background: linear-gradient(135deg, #38bdf8, #06b6d4);
    border: none;
    border-radius: 8px;
    color: #09131f;
    padding: 6px 12px;
    font-size: 11px;
    font-weight: 700;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .search-btn svg {
    width: 12px;
    height: 12px;
    fill: currentColor;
  }

  /* Quick Pills */
  .tag-pills {
    display: flex;
    gap: 5px;
    overflow-x: auto;
    padding-bottom: 2px;
    scrollbar-width: none;
  }

  .tag-pills::-webkit-scrollbar { display: none; }

  .tag-pill {
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: #94a3b8;
    font-size: 10px;
    padding: 3px 8px;
    border-radius: 12px;
    cursor: pointer;
    white-space: nowrap;
    transition: all 0.15s ease;
  }

  .tag-pill:hover, .tag-pill.active {
    border-color: #38bdf8;
    color: #38bdf8;
    background: rgba(56, 189, 248, 0.12);
  }

  /* SELECTABLE RESULTS LIST */
  .results-list {
    flex: 1;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding-right: 2px;
  }

  .results-list::-webkit-scrollbar { width: 4px; }
  .results-list::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.2); border-radius: 4px; }

  .song-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 6px 8px;
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid transparent;
    cursor: pointer;
    transition: background 0.15s ease, border-color 0.15s ease;
  }

  .song-item:hover {
    background: rgba(255, 255, 255, 0.09);
    border-color: rgba(56, 189, 248, 0.3);
  }

  .song-item.active {
    background: rgba(56, 189, 248, 0.14);
    border-color: rgba(56, 189, 248, 0.5);
  }

  .song-thumb {
    width: 34px;
    height: 34px;
    border-radius: 6px;
    object-fit: cover;
    flex-shrink: 0;
  }

  .song-details {
    flex: 1;
    min-width: 0;
  }

  .song-item-title {
    font-size: 12px;
    font-weight: 600;
    color: #ffffff;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .song-item-artist {
    font-size: 10px;
    color: #94a3b8;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .song-item-play-btn {
    width: 24px;
    height: 24px;
    border-radius: 50%;
    background: rgba(56, 189, 248, 0.2);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    color: #38bdf8;
  }

  .song-item-play-btn svg {
    width: 12px;
    height: 12px;
    fill: currentColor;
    margin-left: 1px;
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

<div class="widget-container" id="widget-container">
  <!-- TOP ROW: NOW PLAYING -->
  <div class="now-playing-card">
    <div class="top-close">
      <button class="action-btn" id="btn-close" title="Close Widget">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill-rule="evenodd" d="M5.47 5.47a.75.75 0 0 1 1.06 0L12 10.94l5.47-5.47a.75.75 0 1 1 1.06 1.06L13.06 12l5.47 5.47a.75.75 0 1 1-1.06 1.06L12 13.06l-5.47 5.47a.75.75 0 0 1-1.06-1.06L10.94 12 5.47 6.53a.75.75 0 0 1 0-1.06Z" clip-rule="evenodd" /></svg>
      </button>
    </div>

    <!-- Album Art -->
    <div class="album-wrap" id="album-wrap">
      <img id="album-art" class="album-art" src="https://i.ytimg.com/vi/dX3k_QDnzHE/hqdefault.jpg" alt="Cover">
    </div>

    <!-- Info & Controls Column -->
    <div class="info-controls">
      <div class="track-info">
        <div class="track-title" id="track-title">Midnight City</div>
        <div class="track-artist" id="track-artist">M83</div>
      </div>

      <!-- Animated Waveform Audio Visualizer (WAVES) -->
      <div class="waveform-container" id="waveform">
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

      <!-- Controls Row -->
      <div class="controls-row">
        <!-- Previous Track -->
        <button class="btn-icon" id="btn-prev" title="Previous Track">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M9.195 18.44c1.25.714 2.805-.189 2.805-1.629v-2.34l6.945 3.968c1.25.715 2.805-.188 2.805-1.628V7.189c0-1.44-1.555-2.343-2.805-1.628L12 9.529v-2.34c0-1.44-1.555-2.343-2.805-1.628l-7.108 4.061c-1.26.72-1.26 2.536 0 3.256l7.108 4.061Z" /></svg>
        </button>

        <!-- Play / Pause Cyan Button -->
        <button class="btn-play-pause" id="btn-play-pause" title="Play / Pause">
          <div class="loading-ring"></div>
          <svg class="play-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill-rule="evenodd" d="M4.5 5.653c0-1.427 1.529-2.33 2.779-1.643l11.54 6.347c1.295.712 1.295 2.573 0 3.286L7.28 19.99c-1.25.687-2.779-.217-2.779-1.643V5.653Z" clip-rule="evenodd" /></svg>
          <svg class="pause-icon" style="display:none;" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill-rule="evenodd" d="M6.75 5.25a.75.75 0 0 1 .75.75v12a.75.75 0 0 1-1.5 0v-12a.75.75 0 0 1 .75-.75Zm9 0a.75.75 0 0 1 .75.75v12a.75.75 0 0 1-1.5 0v-12a.75.75 0 0 1 .75-.75Z" clip-rule="evenodd" /></svg>
        </button>

        <!-- Next Track -->
        <button class="btn-icon" id="btn-next" title="Next Track">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M5.055 7.06C3.805 6.347 2.25 7.25 2.25 8.69v8.622c0 1.44 1.555 2.343 2.805 1.628L12 14.971v2.341c0 1.44 1.555 2.343 2.805 1.628l7.108-4.061c1.26-.72 1.26-2.536 0-3.256L14.805 7.562V5.22c0-1.44-1.555-2.343-2.805-1.628L5.055 7.06Z" /></svg>
        </button>

        <!-- YouTube Music Badge -->
        <div class="yt-badge">
          <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" fill="#ef4444"/><polygon points="10 8 16 12 10 16" fill="#ffffff"/></svg>
          <span>YouTube Music</span>
        </div>
      </div>
    </div>
  </div>

  <!-- SECTION 2: USER-FRIENDLY SEARCH & SONG SELECTION -->
  <div class="search-section">
    <!-- Search Bar -->
    <div class="search-input-wrap">
      <input type="text" class="search-input" id="search-input" placeholder="Search song or artist on YouTube...">
      <button class="search-btn" id="search-btn">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill-rule="evenodd" d="M10.5 3.75a6.75 6.75 0 1 0 4.298 11.968l4.492 4.493a.75.75 0 1 0 1.06-1.06l-4.493-4.493A6.75 6.75 0 0 0 10.5 3.75Zm-5.25 6.75a5.25 5.25 0 1 1 10.5 0 5.25 5.25 0 0 1-10.5 0Z" clip-rule="evenodd" /></svg>
        FIND
      </button>
    </div>

    <!-- Quick Anime & K-Pop Pills -->
    <div class="tag-pills">
      <span class="tag-pill" data-q="BABYMONSTER">BABYMONSTER</span>
      <span class="tag-pill" data-q="Solo Leveling OST">Solo Leveling</span>
      <span class="tag-pill" data-q="Jujutsu Kaisen OST">Jujutsu Kaisen</span>
      <span class="tag-pill" data-q="Naruto OST">Naruto</span>
      <span class="tag-pill" data-q="Bleach OST">Bleach</span>
      <span class="tag-pill" data-q="Eminence in Shadow OST">Eminence</span>
      <span class="tag-pill" data-q="Hunter x Hunter OST">HxH</span>
      <span class="tag-pill" data-q="M83 Midnight City">M83</span>
    </div>

    <!-- SELECTABLE RESULTS LIST (User can click to select and play!) -->
    <div class="results-list" id="results-list">
      <!-- Populated dynamically via JS -->
    </div>
  </div>
</div>

<audio id="audio-player" preload="auto"></audio>

<script>
  const audio = document.getElementById('audio-player');
  const widget = document.getElementById('widget-container');
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
  const searchInput = document.getElementById('search-input');
  const searchBtn = document.getElementById('search-btn');
  const resultsList = document.getElementById('results-list');

  let isPlaying = false;
  let currentSongId = 'dX3k_QDnzHE';

  // Toggle Wave animation and play/pause icon
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
      selectAndPlay(currentSongId, trackTitle.textContent, trackArtist.textContent, albumArt.src);
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

  // Search input & button
  searchBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    const q = searchInput.value.trim();
    if (q) performSearch(q);
  });

  searchInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      const q = searchInput.value.trim();
      if (q) performSearch(q);
    }
  });

  // Tag pills
  document.querySelectorAll('.tag-pill').forEach(pill => {
    pill.addEventListener('click', (e) => {
      e.stopPropagation();
      document.querySelectorAll('.tag-pill').forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      searchInput.value = pill.dataset.q;
      performSearch(pill.dataset.q);
    });
  });

  function performSearch(q) {
    resultsList.innerHTML = '<div style="color:#94a3b8;font-size:12px;padding:10px;text-align:center;">Searching YouTube...</div>';
    window.pywebview && window.pywebview.api.search_songs(q);
  }

  // Called from Python with search results list
  window.renderSearchResults = function(resultsJson) {
    const results = JSON.parse(resultsJson);
    resultsList.innerHTML = '';
    if (!results || results.length === 0) {
      resultsList.innerHTML = '<div style="color:#94a3b8;font-size:12px;padding:10px;text-align:center;">No songs found.</div>';
      return;
    }

    results.forEach(item => {
      const el = document.createElement('div');
      el.className = 'song-item' + (item.id === currentSongId ? ' active' : '');
      el.innerHTML = `
        <img class="song-thumb" src="${item.thumb}" alt="thumb">
        <div class="song-details">
          <div class="song-item-title">${item.title}</div>
          <div class="song-item-artist">${item.artist}</div>
        </div>
        <div class="song-item-play-btn">
          <svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
        </div>
      `;
      el.addEventListener('click', () => {
        document.querySelectorAll('.song-item').forEach(s => s.classList.remove('active'));
        el.classList.add('active');
        selectAndPlay(item.id, item.title, item.artist, item.thumb);
      });
      resultsList.appendChild(el);
    });
  };

  function selectAndPlay(id, title, artist, thumb) {
    currentSongId = id;
    btnPlayPause.classList.add('loading');
    trackTitle.textContent = title;
    trackArtist.textContent = artist;
    if (thumb) albumArt.src = thumb;
    window.pywebview && window.pywebview.api.play_selected_song(id, title, artist, thumb);
  }

  // Called from Python when stream URL is ready
  window.setStreamUrl = function(streamUrl) {
    btnPlayPause.classList.remove('loading');
    if (streamUrl) {
      audio.src = streamUrl;
      audio.play().then(() => updatePlayState(true)).catch(err => console.log(err));
    }
  };

  // Dragging window
  let isDragging = false;
  let startX = 0, startY = 0;

  widget.addEventListener('mousedown', (e) => {
    if (e.target.closest('button') || e.target.closest('input') || e.target.closest('.results-list') || e.target.closest('.tag-pills')) return;
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

  // Render presets initially
  window.addEventListener('DOMContentLoaded', () => {
    const initial = PRESET_TRACKS_PLACEHOLDER;
    window.renderSearchResults(JSON.stringify(initial));
  });
</script>
</body>
</html>
""".replace("PRESET_TRACKS_PLACEHOLDER", json.dumps(PRESET_TRACKS))

class MusicAPI:
    def __init__(self, win_holder):
        self.win_holder = win_holder
        self.current_index = 0
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
                info = ydl.extract_info(f"ytsearch8:{query}", download=False)
                for entry in info.get('entries', []):
                    title = entry.get('title', 'Unknown Title')
                    # Clean title
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
        except Exception as e:
            w.evaluate_js(f"window.setStreamUrl('');")

    def next_track(self):
        self.current_index = (self.current_index + 1) % len(PRESET_TRACKS)
        track = PRESET_TRACKS[self.current_index]
        self.play_selected_song(track['id'], track['title'], track['artist'], track['thumb'])

    def prev_track(self):
        self.current_index = (self.current_index - 1) % len(PRESET_TRACKS)
        track = PRESET_TRACKS[self.current_index]
        self.play_selected_song(track['id'], track['title'], track['artist'], track['thumb'])


def main():
    win_holder = [None]
    api = MusicAPI(win_holder)

    # on_top=False ensures it will NOT overlap other active apps
    # Solid dark acrylic background (#0d1117) ensures it's 100% visible on desktop
    w = webview.create_window(
        title='YouTube Desktop Widget',
        html=HTML_CONTENT,
        width=WIDGET_W,
        height=WIDGET_H,
        x=POS_X,
        y=POS_Y,
        frameless=True,
        resizable=False,
        on_top=False,    # <--- DOES NOT OVERLAP OTHER APPS!
        js_api=api,
        background_color='#0d1117'
    )
    win_holder[0] = w

    # Autoplay first track (Midnight City)
    def auto_start():
        import time
        time.sleep(1.2)
        api.play_selected_song(PRESET_TRACKS[0]['id'], PRESET_TRACKS[0]['title'], PRESET_TRACKS[0]['artist'], PRESET_TRACKS[0]['thumb'])

    threading.Thread(target=auto_start, daemon=True).start()
    webview.start()

if __name__ == '__main__':
    main()
