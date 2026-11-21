"""
YouTube Desktop Player - Python + pywebview
Floating always-on-top anime-aesthetic music player widget
"""
import webview
import threading
import sys
import os

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<title>YT Player</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
:root {
  --bg: #0a0814;
  --accent: #c084fc;
  --accent2: #f472b6;
  --accent3: #38bdf8;
  --text: #e2e8f0;
  --muted: #64748b;
  --border: rgba(255,255,255,0.10);
  --glass: rgba(255,255,255,0.05);
}
html, body {
  width:100%; height:100%;
  background: var(--bg);
  color: var(--text);
  font-family: 'Segoe UI', system-ui, sans-serif;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  user-select: none;
}

/* ── TITLE BAR ── */
#titlebar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 10px;
  height: 36px;
  background: rgba(192,132,252,0.08);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  -webkit-app-region: drag;
  cursor: move;
}
#app-title {
  font-size:12px; font-weight:700; letter-spacing:.08em;
  background: linear-gradient(90deg,var(--accent),var(--accent2));
  -webkit-background-clip:text; -webkit-text-fill-color:transparent;
}
#win-controls { display:flex; gap:4px; -webkit-app-region:no-drag; }
#win-controls button {
  background:none; border:none; cursor:pointer;
  color:var(--muted); font-size:12px;
  width:28px; height:28px; border-radius:6px;
  display:flex; align-items:center; justify-content:center;
  transition: background .2s, color .2s;
}
#win-controls button:hover { background:var(--glass); color:var(--text); }
#btn-close:hover { background:rgba(239,68,68,.3)!important; color:#ef4444!important; }
#btn-pin.pinned { color:var(--accent); }

/* ── SEARCH ── */
#search-section {
  padding: 10px 12px 8px;
  flex-shrink:0;
  background:rgba(0,0,0,.2);
  border-bottom:1px solid var(--border);
}
#search-box { display:flex; gap:8px; }
#search-input {
  flex:1; background:rgba(255,255,255,.07);
  border:1px solid var(--border); border-radius:8px;
  color:var(--text); padding:7px 12px; font-size:12px; outline:none;
  transition: border-color .2s, box-shadow .2s;
}
#search-input:focus { border-color:var(--accent); box-shadow:0 0 0 2px rgba(192,132,252,.2); }
#search-input::placeholder { color:var(--muted); }
#btn-search {
  background: linear-gradient(135deg,var(--accent),var(--accent2));
  border:none; border-radius:8px; color:#fff;
  padding:7px 14px; font-size:11px; font-weight:700;
  cursor:pointer; letter-spacing:.05em; transition: opacity .2s;
}
#btn-search:hover { opacity:.85; }

/* Quick tags */
#quick-tags { display:flex; flex-wrap:wrap; gap:5px; margin-top:7px; }
.tag {
  background:var(--glass); border:1px solid var(--border);
  border-radius:20px; color:var(--muted); font-size:10px;
  padding:3px 10px; cursor:pointer; transition:all .2s;
}
.tag:hover { border-color:var(--accent); color:var(--accent); background:rgba(192,132,252,.1); }

/* ── PLAYER ── */
#player-container { flex:1; position:relative; overflow:hidden; background:#000; }
#yt-frame { width:100%; height:100%; border:none; display:block; }

/* ── STATUS ── */
#status-bar {
  display:flex; justify-content:space-between; align-items:center;
  padding:4px 12px; height:24px; font-size:9px;
  color:var(--muted); background:rgba(0,0,0,.3);
  border-top:1px solid var(--border); flex-shrink:0;
}
#pin-indicator { font-size:9px; color:var(--accent); opacity:.8; }

/* ── GLOW ── */
body { box-shadow: 0 0 20px rgba(192,132,252,.25); }
</style>
</head>
<body>

<div id="titlebar">
  <span id="app-title">▶ YT Player</span>
  <div id="win-controls">
    <button id="btn-pin"   title="Always on Top">📌</button>
    <button id="btn-close" title="Quit">✕</button>
  </div>
</div>

<div id="search-section">
  <div id="search-box">
    <input type="text" id="search-input" placeholder="🔍  Search YouTube…" autocomplete="off"/>
    <button id="btn-search">GO</button>
  </div>
  <div id="quick-tags">
    <button class="tag" data-q="lo-fi hip hop radio beats">Lo-Fi</button>
    <button class="tag" data-q="anime ost playlist 2024">Anime OST</button>
    <button class="tag" data-q="BABYMONSTER kpop playlist">BABYMONSTER</button>
    <button class="tag" data-q="naruto shippuden ost">Naruto</button>
    <button class="tag" data-q="jujutsu kaisen ost">JJK</button>
    <button class="tag" data-q="solo leveling ost soundtrack">Solo Leveling</button>
    <button class="tag" data-q="hunter x hunter ost">HxH</button>
    <button class="tag" data-q="bleach ost soundtrack">Bleach</button>
  </div>
</div>

<div id="player-container">
  <iframe id="yt-frame"
    src="https://www.youtube.com/embed?listType=search&list=lo-fi+hip+hop+radio&autoplay=0&controls=1&rel=0&modestbranding=1"
    allow="autoplay; encrypted-media; fullscreen"
    allowfullscreen>
  </iframe>
</div>

<div id="status-bar">
  <span id="status-text">Search or tap a quick tag ↑</span>
  <span id="pin-indicator">📌 ON</span>
</div>

<script>
const frame     = document.getElementById('yt-frame');
const searchIn  = document.getElementById('search-input');
const btnSearch = document.getElementById('btn-search');
const statusTxt = document.getElementById('status-text');

function search(q) {
  if (!q.trim()) return;
  statusTxt.textContent = 'Searching: ' + q + '…';
  const enc = encodeURIComponent(q);
  frame.src = 'https://www.youtube.com/results?search_query=' + enc;
}

btnSearch.addEventListener('click', () => search(searchIn.value));
searchIn.addEventListener('keydown', e => { if (e.key === 'Enter') search(searchIn.value); });

document.querySelectorAll('.tag').forEach(t => {
  t.addEventListener('click', () => { searchIn.value = t.dataset.q; search(t.dataset.q); });
});

document.getElementById('btn-close').addEventListener('click', () => {
  window.pywebview && window.pywebview.api.close_app();
});

document.getElementById('btn-pin').addEventListener('click', function() {
  this.classList.toggle('pinned');
});

// Title dragging  
let dragging=false, ox=0, oy=0;
const tb = document.getElementById('titlebar');
tb.addEventListener('mousedown', e => { if(e.target.closest('#win-controls')) return; dragging=true; ox=e.screenX; oy=e.screenY; });
document.addEventListener('mousemove', e => {
  if (!dragging) return;
  window.pywebview && window.pywebview.api.move_window(e.screenX - ox, e.screenY - oy);
  ox=e.screenX; oy=e.screenY;
});
document.addEventListener('mouseup', () => { dragging=false; });
</script>
</body>
</html>
"""

class Api:
    def __init__(self, win_ref):
        self._win = win_ref

    def close_app(self):
        self._win[0].destroy()

    def move_window(self, dx, dy):
        try:
            w = self._win[0]
            x, y = w.x, w.y
            w.move(x + int(dx), y + int(dy))
        except Exception:
            pass


def main():
    win_ref = [None]
    api = Api(win_ref)

    win = webview.create_window(
        title='YouTube Desktop Player',
        html=HTML,
        width=440,
        height=640,
        x=-1,          # will reposition after create
        y=-1,
        resizable=True,
        frameless=False,   # use native frame for stability
        on_top=True,
        js_api=api,
        min_size=(380, 200),
        background_color='#0a0814',
    )
    win_ref[0] = win

    webview.start(debug=False)


if __name__ == '__main__':
    main()
