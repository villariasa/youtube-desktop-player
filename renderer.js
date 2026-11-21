/* ============================================================
   renderer.js — YouTube Desktop Player Logic
   ============================================================ */

'use strict';

// ── DOM refs ──────────────────────────────────────────────
const webview      = document.getElementById('yt-webview');
const searchInput  = document.getElementById('search-input');
const btnSearch    = document.getElementById('btn-search');
const btnToggle    = document.getElementById('btn-toggle');
const btnClose     = document.getElementById('btn-close');
const btnHide      = document.getElementById('btn-hide');
const btnPin       = document.getElementById('btn-pin');
const statusText   = document.getElementById('status-text');
const pinIndicator = document.getElementById('pin-indicator');
const miniTitle    = document.getElementById('mini-title');
const miniArtist   = document.getElementById('mini-artist');
const miniThumb    = document.getElementById('mini-thumb');
const miniPlayBtn  = document.getElementById('mini-play');
const tags         = document.querySelectorAll('.tag');

// ── State ─────────────────────────────────────────────────
let isMini      = false;
let isPinned    = true;
let isPlaying   = false;

// ── Helpers ───────────────────────────────────────────────
function ytSearchUrl(query) {
  // Use YouTube embed search
  const q = encodeURIComponent(query);
  return `https://www.youtube.com/results?search_query=${q}`;
}

function ytEmbedSearchUrl(query) {
  const q = encodeURIComponent(query);
  return `https://www.youtube.com/embed?listType=search&list=${q}&autoplay=1&controls=1&rel=0&modestbranding=1`;
}

function setStatus(msg) {
  statusText.textContent = msg;
}

// ── Search ────────────────────────────────────────────────
function doSearch(query) {
  if (!query.trim()) return;
  setStatus(`Searching: ${query}…`);
  miniTitle.textContent  = query;
  miniArtist.textContent = 'Loading…';

  // Navigate the webview to YouTube search results (full page — user can click)
  webview.src = ytSearchUrl(query);
}

btnSearch.addEventListener('click', () => doSearch(searchInput.value));
searchInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') doSearch(searchInput.value);
});

tags.forEach(tag => {
  tag.addEventListener('click', () => {
    const q = tag.dataset.q;
    searchInput.value = q;
    doSearch(q);
  });
});

// ── Webview events ────────────────────────────────────────
webview.addEventListener('did-start-loading', () => {
  setStatus('Loading…');
});

webview.addEventListener('did-stop-loading', () => {
  const url = webview.getURL();
  setStatus('Ready');
  // Extract video title from page title
  webview.getTitle().then ? null : null;
  try {
    const title = webview.getTitle();
    if (title && title !== 'YouTube') {
      miniTitle.textContent  = title.replace(' - YouTube', '');
      miniArtist.textContent = 'YouTube';
      setStatus(miniTitle.textContent);
    }
  } catch {}
});

webview.addEventListener('page-title-updated', (e) => {
  const title = (e.title || '').replace(' - YouTube', '').trim();
  if (title && title !== 'YouTube') {
    miniTitle.textContent  = title;
    miniArtist.textContent = 'YouTube';
    setStatus(title);
  }
});

webview.addEventListener('did-fail-load', (e) => {
  if (e.errorCode !== -3) {   // -3 = aborted (normal for navigations)
    setStatus(`Load error ${e.errorCode}: ${e.errorDescription}`);
  }
});

// ── Mini play button (sends key to webview) ───────────────
miniPlayBtn.addEventListener('click', () => {
  // Toggle play/pause by sending Space key to the webview
  webview.sendInputEvent({ type: 'keyDown', keyCode: ' ' });
  webview.sendInputEvent({ type: 'keyUp',   keyCode: ' ' });
  isPlaying = !isPlaying;
  miniPlayBtn.textContent = isPlaying ? '⏸' : '▶';
});

// ── Window controls ───────────────────────────────────────
btnToggle.addEventListener('click', () => {
  isMini = !isMini;
  document.body.classList.toggle('mini', isMini);
  btnToggle.title = isMini ? 'Expand' : 'Mini mode';
  btnToggle.textContent = isMini ? '⬜' : '⬛';
  window.electronAPI.toggleSize();
});

btnClose.addEventListener('click', () => window.electronAPI.closeApp());
btnHide.addEventListener('click',  () => window.electronAPI.hideApp());

btnPin.addEventListener('click', () => {
  isPinned = !isPinned;
  window.electronAPI.setAlwaysOnTop(isPinned);
  btnPin.classList.toggle('pinned', isPinned);
  pinIndicator.textContent = isPinned ? '📌 ON' : '📌 OFF';
  pinIndicator.style.color = isPinned ? 'var(--accent)' : 'var(--muted)';
  setStatus(isPinned ? 'Always on top: ON' : 'Always on top: OFF');
});

// ── Keyboard shortcuts ────────────────────────────────────
document.addEventListener('keydown', (e) => {
  if (document.activeElement === searchInput) return;  // let search input handle keys

  switch (e.key) {
    case 'Escape': window.electronAPI.hideApp(); break;
    case 'm':
    case 'M':
      btnToggle.click();
      break;
  }
});
