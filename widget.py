"""
YouTube Desktop Music Player Widget
Windows 11 Floating Acrylic / Glassmorphism Music Flyout
Styled exactly like Windows 11 native music widget
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
WIDGET_H = 136

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

  body {
    background: transparent;
    width: 100vw;
    height: 100vh;
    display: flex;
    justify-content: center;
    align-items: center;
    overflow: hidden;
  }

  /* Main Card matching Windows 11 Acrylic Music Flyout */
  .music-card {
    width: 440px;
    height: 136px;
    background: rgba(32, 36, 44, 0.95);
    backdrop-filter: blur(32px) saturate(180%);
    -webkit-backdrop-filter: blur(32px) saturate(180%);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 14px;
    box-shadow: 0 16px 36px rgba(0, 0, 0, 0.55), 0 0 0 1px rgba(255, 255, 255, 0.05);
    display: flex;
    align-items: center;
    padding: 14px 16px;
    gap: 16px;
    position: relative;
    cursor: grab;
    transition: box-shadow 0.2s ease, border-color 0.2s ease;
  }

  .music-card:active {
    cursor: grabbing;
  }

  .music-card:hover {
    border-color: rgba(255, 255, 255, 0.22);
    box-shadow: 0 20px 42px rgba(0, 0, 0, 0.65), 0 0 18px rgba(103, 232, 249, 0.18);
  }

  /* Album Art */
  .album-wrap {
    width: 96px;
    height: 96px;
    border-radius: 10px;
    overflow: hidden;
    position: relative;
    flex-shrink: 0;
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.5);
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
    transform: scale(1.04);
  }

  /* Info & Controls */
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
    background: #67e8f9;
    border-radius: 2px;
    transition: width 0.1s linear;
  }

  /* Controls Row */
  .controls-row {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-top: 2px;
  }

  .btn-icon {
    background: transparent;
    border: none;
    color: #cbd5e1;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 4px;
    border-radius: 6px;
    transition: color 0.15s ease, transform 0.1s ease;
  }

  .btn-icon:hover {
    color: #ffffff;
    transform: scale(1.12);
  }

  .btn-icon:active {
    transform: scale(0.92);
  }

  .btn-icon svg {
    width: 18px;
    height: 18px;
    fill: currentColor;
  }

  /* Play/Pause Button - Cyan Rounded Square (exact match to screenshot) */
  .btn-play-pause {
    width: 38px;
    height: 38px;
    background: #67e8f9;
    border-radius: 10px;
    border: none;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    box-shadow: 0 4px 14px rgba(103, 232, 249, 0.4);
    transition: transform 0.15s ease, background 0.15s ease, box-shadow 0.15s ease;
  }

  .btn-play-pause:hover {
    background: #a5f3fc;
    transform: scale(1.08);
    box-shadow: 0 6px 18px rgba(103, 232, 249, 0.6);
  }

  .btn-play-pause:active {
    transform: scale(0.94);
  }

  .btn-play-pause svg {
    width: 16px;
    height: 16px;
    fill: #0f172a;
  }

  /* YouTube Music Badge */
  .yt-badge {
    margin-left: auto;
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    color: #64748b;
    font-weight: 500;
  }

  .yt-dot {
    width: 7px;
    height: 7px;
    background: #ef4444;
    border-radius: 50%;
    box-shadow: 0 0 6px rgba(239, 68, 68, 0.8);
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
    color: #64748b;
    width: 22px;
    height: 22px;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    font-size: 12px;
    transition: background 0.15s, color 0.15s;
  }

  .action-btn:hover {
    background: rgba(255, 255, 255, 0.1);
    color: #e2e8f0;
  }

  .action-btn.btn-close:hover {
    background: rgba(239, 68, 68, 0.35);
    color: #ef4444;
  }

  /* Search Overlay inside card */
  .search-overlay {
    position: absolute;
    inset: 8px;
    background: rgba(24, 28, 36, 0.98);
    backdrop-filter: blur(32px);
    border-radius: 10px;
    padding: 10px;
    display: none;
    flex-direction: column;
    gap: 8px;
    z-index: 20;
    box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.1);
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
    border-color: #67e8f9;
  }

  .search-go-btn {
    background: #67e8f9;
    border: none;
    border-radius: 8px;
    color: #0f172a;
    font-size: 11px;
    font-weight: 700;
    padding: 6px 12px;
    cursor: pointer;
  }

  .search-close-btn {
    background: transparent;
    border: none;
    color: #94a3b8;
    font-size: 14px;
    cursor: pointer;
    padding: 4px;
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
    border-color: #67e8f9;
    color: #67e8f9;
    background: rgba(103, 232, 249, 0.1);
  }

  /* Loading Spinner */
  .loading-ring {
    display: none;
    width: 16px;
    height: 16px;
    border: 2px solid rgba(15, 23, 42, 0.25);
    border-top: 2px solid #0f172a;
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
  <!-- Top Right Actions -->
  <div class="top-actions">
    <button class="action-btn" id="btn-search-toggle" title="Search Music">🔍</button>
    <button class="action-btn btn-close" id="btn-close" title="Close">✕</button>
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

    <!-- Controls Row -->
    <div class="controls-row">
      <!-- Previous -->
      <button class="btn-icon" id="btn-prev" title="Previous Track">
        <svg viewBox="0 0 24 24"><path d="M6 6h2v12H6zm3.5 6l8.5 6V6z"/></svg>
      </button>

      <!-- Play / Pause (Cyan Button) -->
      <button class="btn-play-pause" id="btn-play-pause" title="Play / Pause">
        <div class="loading-ring"></div>
        <svg class="play-icon" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
        <svg class="pause-icon" style="display:none;" viewBox="0 0 24 24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>
      </button>

      <!-- Next -->
      <button class="btn-icon" id="btn-next" title="Next Track">
        <svg viewBox="0 0 24 24"><path d="M6 18l8.5-6L6 6v12zM16 6v12h2V6h-2z"/></svg>
      </button>

      <!-- YouTube Music Badge -->
      <div class="yt-badge">
        <div class="yt-dot"></div>
        <span>YouTube Music</span>
      </div>
    </div>
  </div>

  <!-- Search Overlay inside card -->
  <div class="search-overlay" id="search-overlay">
    <div class="search-header">
      <input type="text" class="search-input" id="search-input" placeholder="Search YouTube Music...">
      <button class="search-go-btn" id="search-go-btn">PLAY</button>
      <button class="search-close-btn" id="search-close-btn">✕</button>
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

    # Position at exact center of screen
    w = webview.create_window(
        title='YouTube Desktop Widget',
        html=HTML_CONTENT,
        width=WIDGET_W,
        height=WIDGET_H,
        x=POS_X,
        y=POS_Y,
        frameless=True,
        transparent=True,
        on_top=True,
        js_api=api,
        background_color='#1e222a'
    )
    win_holder[0] = w

    # Autoplay first track (Midnight City) after window loads
    def auto_start():
        import time
        time.sleep(1.0)
        api.load_index(0)

    threading.Thread(target=auto_start, daemon=True).start()
    webview.start()

if __name__ == '__main__':
    main()
