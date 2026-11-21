"""
YouTube Desktop Music Player Widget
Windows 11 Glassmorphism Floating Acrylic Music Card
Styled with pure Tailwind/Heroicons SVGs, centered on screen, draggable, always-on-top
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

WIDGET_W = 440
WIDGET_H = 142

POS_X = (SCREEN_W - WIDGET_W) // 2
POS_Y = (SCREEN_H - WIDGET_H) // 2

PRESET_TRACKS = [
    {"query": "M83 Midnight City official", "title": "Midnight City", "artist": "M83", "thumb": "https://i.ytimg.com/vi/dX3k_QDnzHE/hqdefault.jpg"},
    {"query": "BABYMONSTER SHEESH official music video", "title": "SHEESH", "artist": "BABYMONSTER", "thumb": "https://i.ytimg.com/vi/2wA_b644DaQ/hqdefault.jpg"},
    {"query": "BABYMONSTER BATTER UP official music video", "title": "BATTER UP", "artist": "BABYMONSTER", "thumb": "https://i.ytimg.com/vi/olDWbQeT3Q8/hqdefault.jpg"},
    {"query": "Solo Leveling Dark Aria SawanoHiroyuki", "title": "DARK ARIA", "artist": "SawanoHiroyuki[nZk] (Solo Leveling)", "thumb": "https://i.ytimg.com/vi/8Q9PjM2o3_E/hqdefault.jpg"},
    {"query": "King Gnu SPECIALZ Jujutsu Kaisen", "title": "SPECIALZ", "artist": "King Gnu (Jujutsu Kaisen)", "thumb": "https://i.ytimg.com/vi/fhzKLfZq6gs/hqdefault.jpg"},
    {"query": "Blue Bird Naruto Shippuden opening 3 Ikimonogakari", "title": "Blue Bird", "artist": "Ikimonogakari (Naruto)", "thumb": "https://i.ytimg.com/vi/Kynt3hQ28lM/hqdefault.jpg"},
    {"query": "Bleach Number One Hazel Fernandes", "title": "Number One", "artist": "Hazel Fernandes (Bleach)", "thumb": "https://i.ytimg.com/vi/1lsn2tT5yTc/hqdefault.jpg"},
    {"query": "OxT HIGHEST Eminence in Shadow", "title": "HIGHEST", "artist": "OxT (Eminence in Shadow)", "thumb": "https://i.ytimg.com/vi/uY5s2W3u3sI/hqdefault.jpg"},
    {"query": "Departure Masatoshi Ono Hunter x Hunter", "title": "Departure!", "artist": "Masatoshi Ono (Hunter x Hunter)", "thumb": "https://i.ytimg.com/vi/faqmNf_fZlE/hqdefault.jpg"},
]

HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Desktop Music Widget</title>
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
    background: #0f131a;
  }

  /* Glassmorphism Card Container */
  .music-card {
    width: 100%;
    height: 100%;
    background: linear-gradient(135deg, rgba(28, 33, 46, 0.95) 0%, rgba(16, 20, 28, 0.98) 100%);
    border: 1px solid rgba(255, 255, 255, 0.14);
    box-shadow: inset 0 1px 1px rgba(255, 255, 255, 0.22), 0 16px 36px rgba(0, 0, 0, 0.65);
    display: flex;
    align-items: center;
    padding: 16px 18px;
    gap: 16px;
    position: relative;
    cursor: grab;
    border-radius: 0;
  }

  .music-card:active {
    cursor: grabbing;
  }

  /* Glass Top Highlight */
  .music-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent 0%, rgba(255, 255, 255, 0.35) 40%, rgba(56, 189, 248, 0.5) 60%, transparent 100%);
    pointer-events: none;
  }

  /* Album Art */
  .album-wrap {
    width: 96px;
    height: 96px;
    border-radius: 10px;
    overflow: hidden;
    position: relative;
    flex-shrink: 0;
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.6), 0 0 0 1px rgba(255, 255, 255, 0.1);
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
    gap: 4px;
  }

  .track-info {
    display: flex;
    flex-direction: column;
    margin-bottom: 2px;
  }

  .track-title {
    font-size: 16px;
    font-weight: 600;
    color: #ffffff;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    letter-spacing: -0.2px;
    line-height: 1.25;
    text-shadow: 0 1px 3px rgba(0, 0, 0, 0.5);
  }

  .track-artist {
    font-size: 13px;
    font-weight: 400;
    color: #94a3b8;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-top: 2px;
  }

  /* Progress Bar */
  .progress-wrap {
    width: 100%;
    height: 3px;
    background: rgba(255, 255, 255, 0.12);
    border-radius: 2px;
    margin: 6px 0 4px 0;
    cursor: pointer;
    position: relative;
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
    margin-top: 2px;
  }

  /* Tailwind Icon Button */
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
    background: rgba(255, 255, 255, 0.08);
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

  /* Play/Pause Button - Cyan Rounded Square with Tailwind Icon */
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
    box-shadow: 0 4px 14px rgba(6, 182, 212, 0.45), inset 0 1px 1px rgba(255, 255, 255, 0.4);
    transition: transform 0.15s ease, box-shadow 0.15s ease, filter 0.15s ease;
  }

  .btn-play-pause:hover {
    transform: scale(1.08);
    box-shadow: 0 6px 18px rgba(6, 182, 212, 0.65), inset 0 1px 1px rgba(255, 255, 255, 0.5);
    filter: brightness(1.08);
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
    color: #94a3b8;
    font-weight: 500;
  }

  .yt-badge svg {
    width: 14px;
    height: 14px;
    display: block;
  }

  /* Top Right Actions (Search & Close) */
  .top-actions {
    position: absolute;
    top: 8px;
    right: 10px;
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
    background: rgba(255, 255, 255, 0.12);
    color: #f1f5f9;
  }

  .action-btn.btn-close:hover {
    background: rgba(239, 68, 68, 0.35);
    color: #ef4444;
  }

  /* Search Overlay inside card */
  .search-overlay {
    position: absolute;
    inset: 8px;
    background: rgba(18, 22, 32, 0.98);
    backdrop-filter: blur(32px);
    border: 1px solid rgba(255, 255, 255, 0.14);
    border-radius: 10px;
    padding: 10px;
    display: none;
    flex-direction: column;
    gap: 8px;
    z-index: 20;
    box-shadow: 0 12px 30px rgba(0, 0, 0, 0.8);
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
  }

  .search-go-btn {
    background: linear-gradient(135deg, #38bdf8, #06b6d4);
    border: none;
    border-radius: 8px;
    color: #09131f;
    font-size: 11px;
    font-weight: 700;
    padding: 6px 12px;
    cursor: pointer;
  }

  .tag-pills {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
    overflow-y: auto;
    max-height: 64px;
  }

  .tag-pill {
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: #94a3b8;
    font-size: 10px;
    padding: 3px 8px;
    border-radius: 12px;
    cursor: pointer;
    white-space: nowrap;
  }

  .tag-pill:hover {
    border-color: #38bdf8;
    color: #38bdf8;
    background: rgba(56, 189, 248, 0.12);
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

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .loading .loading-ring { display: block; }
  .loading .play-icon { display: none; }
  .loading .pause-icon { display: none; }
</style>
</head>
<body>

<div class="music-card" id="card">
  <!-- Top Right Actions with Tailwind Icons -->
  <div class="top-actions">
    <!-- Tailwind Search (Magnifying Glass) Icon -->
    <button class="action-btn" id="btn-search-toggle" title="Search Music">
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
        <!-- Tailwind Play Icon -->
        <svg class="play-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill-rule="evenodd" d="M4.5 5.653c0-1.427 1.529-2.33 2.779-1.643l11.54 6.347c1.295.712 1.295 2.573 0 3.286L7.28 19.99c-1.25.687-2.779-.217-2.779-1.643V5.653Z" clip-rule="evenodd" /></svg>
        <!-- Tailwind Pause Icon -->
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

  <!-- Search Overlay with Tailwind Close Icon -->
  <div class="search-overlay" id="search-overlay">
    <div class="search-header">
      <input type="text" class="search-input" id="search-input" placeholder="Search YouTube Music...">
      <button class="search-go-btn" id="search-go-btn">PLAY</button>
      <button class="action-btn" id="search-close-btn" title="Close Search">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill-rule="evenodd" d="M5.47 5.47a.75.75 0 0 1 1.06 0L12 10.94l5.47-5.47a.75.75 0 1 1 1.06 1.06L13.06 12l5.47 5.47a.75.75 0 1 1-1.06 1.06L12 13.06l-5.47 5.47a.75.75 0 0 1-1.06-1.06L10.94 12 5.47 6.53a.75.75 0 0 1 0-1.06Z" clip-rule="evenodd" /></svg>
      </button>
    </div>
    <div class="tag-pills">
      <span class="tag-pill" data-q="M83 Midnight City">Midnight City</span>
      <span class="tag-pill" data-q="BABYMONSTER SHEESH">BABYMONSTER - SHEESH</span>
      <span class="tag-pill" data-q="BABYMONSTER BATTER UP">BABYMONSTER - BATTER UP</span>
      <span class="tag-pill" data-q="Solo Leveling Dark Aria">Solo Leveling</span>
      <span class="tag-pill" data-q="King Gnu SPECIALZ">Jujutsu Kaisen</span>
      <span class="tag-pill" data-q="Naruto Blue Bird">Naruto</span>
      <span class="tag-pill" data-q="Bleach Number One">Bleach</span>
      <span class="tag-pill" data-q="Eminence in Shadow Highest">Eminence</span>
      <span class="tag-pill" data-q="Hunter x Hunter Departure">HxH</span>
    </div>
  </div>
</div>

<!-- Invisible HTML5 Audio Player -->
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
  const btnSearchToggle = document.getElementById('btn-search-toggle');
  const searchOverlay = document.getElementById('search-overlay');
  const searchInput = document.getElementById('search-input');
  const searchGoBtn = document.getElementById('search-go-btn');
  const searchCloseBtn = document.getElementById('search-close-btn');

  let isPlaying = false;
  let currentIndex = 0;

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
      loadTrackByIndex(currentIndex);
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
    if (q) {
      triggerSearch(q);
      searchOverlay.classList.remove('open');
    }
  });

  searchInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      const q = searchInput.value.trim();
      if (q) {
        triggerSearch(q);
        searchOverlay.classList.remove('open');
      }
    }
  });

  document.querySelectorAll('.tag-pill').forEach(pill => {
    pill.addEventListener('click', (e) => {
      e.stopPropagation();
      const q = pill.dataset.q;
      triggerSearch(q);
      searchOverlay.classList.remove('open');
    });
  });

  function triggerSearch(q) {
    btnPlayPause.classList.add('loading');
    trackTitle.textContent = "Loading...";
    trackArtist.textContent = q;
    window.pywebview && window.pywebview.api.search_and_play(q);
  }

  function loadTrackByIndex(idx) {
    btnPlayPause.classList.add('loading');
    window.pywebview && window.pywebview.api.load_index(idx);
  }

  // Called from Python when track stream is ready
  window.setTrack = function(title, artist, thumb, streamUrl) {
    btnPlayPause.classList.remove('loading');
    trackTitle.textContent = title;
    trackArtist.textContent = artist;
    if (thumb) albumArt.src = thumb;
    if (streamUrl) {
      audio.src = streamUrl;
      audio.play().then(() => updatePlayState(true)).catch(err => console.log(err));
    }
  };

  // Dragging window support
  let isDragging = false;
  let startX = 0, startY = 0;

  card.addEventListener('mousedown', (e) => {
    if (e.target.closest('button') || e.target.closest('input') || e.target.closest('.search-overlay')) return;
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
        self.current_index = 0
        self.ydl_opts = {
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

    def load_index(self, idx):
        self.current_index = idx % len(PRESET_TRACKS)
        track = PRESET_TRACKS[self.current_index]
        threading.Thread(target=self._resolve_and_send, args=(track['query'], track['title'], track['artist'], track['thumb']), daemon=True).start()

    def next_track(self):
        self.current_index = (self.current_index + 1) % len(PRESET_TRACKS)
        self.load_index(self.current_index)

    def prev_track(self):
        self.current_index = (self.current_index - 1) % len(PRESET_TRACKS)
        self.load_index(self.current_index)

    def search_and_play(self, query):
        threading.Thread(target=self._resolve_and_send, args=(query, None, None, None), daemon=True).start()

    def _resolve_and_send(self, query, fallback_title, fallback_artist, fallback_thumb):
        w = self.win_holder[0]
        if not w:
            return
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch1:{query}", download=False)
                if 'entries' in info and len(info['entries']) > 0:
                    entry = info['entries'][0]
                    title = fallback_title or entry.get('title', 'Unknown Title')
                    artist = fallback_artist or entry.get('uploader', 'Unknown Artist')
                    thumb = entry.get('thumbnail') or fallback_thumb or ''
                    stream_url = entry.get('url', '')
                    
                    if ' - ' in title:
                        parts = title.split(' - ', 1)
                        if not fallback_artist:
                            artist = parts[0]
                        title = parts[1]
                    title = title.replace(' (Official Video)', '').replace(' [Official Audio]', '').replace(' (Official Music Video)', '')
                    
                    title_json = json.dumps(title)
                    artist_json = json.dumps(artist)
                    thumb_json = json.dumps(thumb)
                    url_json = json.dumps(stream_url)
                    
                    js = f"window.setTrack({title_json}, {artist_json}, {thumb_json}, {url_json});"
                    w.evaluate_js(js)
        except Exception as e:
            err_title = json.dumps("Error playing track")
            err_msg = json.dumps(str(e)[:40])
            w.evaluate_js(f"window.setTrack({err_title}, {err_msg}, '', '');")


def main():
    win_holder = [None]
    api = MusicAPI(win_holder)

    # Position at exact center of screen with solid frameless window (visible guaranteed)
    w = webview.create_window(
        title='YouTube Desktop Widget',
        html=HTML_CONTENT,
        width=WIDGET_W,
        height=WIDGET_H,
        x=POS_X,
        y=POS_Y,
        frameless=True,
        resizable=False,
        on_top=True,
        js_api=api,
        background_color='#0f131a'
    )
    win_holder[0] = w

    def auto_start():
        import time
        time.sleep(1.0)
        api.load_index(0)

    threading.Thread(target=auto_start, daemon=True).start()
    webview.start()

if __name__ == '__main__':
    main()
