"""
Background Audio Streaming Service
Plays YouTube audio using hardware-accelerated HTML5 audio
"""
import webview
import yt_dlp
import json
import os
import sys
import threading
import time

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio_state.json")
CMD_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio_cmd.json")

class AudioAPI:
    def __init__(self, win_holder):
        self.win_holder = win_holder
        self.ydl_opts_stream = {'format': 'bestaudio/best', 'noplaylist': True, 'quiet': True, 'no_warnings': True}
        self.ydl_opts_search = {'format': 'bestaudio/best', 'noplaylist': True, 'quiet': True, 'extract_flat': True}

    def sync_time(self, cur, dur, playing):
        try:
            with open(STATE_FILE, "w") as f:
                json.dump({"time": cur, "duration": dur, "playing": playing}, f)
        except Exception:
            pass

    def check_commands(self):
        w = self.win_holder[0]
        if not w: return
        if os.path.exists(CMD_FILE):
            try:
                with open(CMD_FILE, "r") as f:
                    cmd = json.load(f)
                os.remove(CMD_FILE)
                action = cmd.get("action")
                if action == "play":
                    vid_id = cmd.get("id")
                    threading.Thread(target=self._stream_track, args=(vid_id, cmd.get("volume", 0.85)), daemon=True).start()
                elif action == "toggle":
                    w.evaluate_js("window.togglePlay();")
                elif action == "volume":
                    w.evaluate_js(f"window.setVol({cmd.get('val', 0.85)});")
            except Exception:
                pass

    def _stream_track(self, vid_id, vol):
        w = self.win_holder[0]
        if not w: return
        try:
            url = f"https://www.youtube.com/watch?v={vid_id}"
            with yt_dlp.YoutubeDL(self.ydl_opts_stream) as ydl:
                info = ydl.extract_info(url, download=False)
                stream_url = info.get('url', '')
                w.evaluate_js(f"window.playStream({json.dumps(stream_url)}, {vol});")
        except Exception:
            pass

HTML = """
<!DOCTYPE html><html><body>
<audio id="player" preload="auto"></audio>
<script>
  const a = document.getElementById('player');
  window.playStream = function(url, vol) {
    a.src = url;
    a.volume = vol;
    a.play().catch(e => console.log(e));
  };
  window.togglePlay = function() {
    if (a.paused) a.play(); else a.pause();
  };
  window.setVol = function(v) { a.volume = v; };
  setInterval(() => {
    if (window.pywebview) {
      window.pywebview.api.sync_time(a.currentTime || 0, a.duration || 0, !a.paused);
      window.pywebview.api.check_commands();
    }
  }, 250);
</script>
</body></html>
"""

def main():
    win_holder = [None]
    api = AudioAPI(win_holder)
    w = webview.create_window('AudioWorker', html=HTML, width=10, height=10, x=-500, y=-500, js_api=api)
    win_holder[0] = w

    def auto_play():
        time.sleep(1.2)
        api._stream_track("oC6brLXQe4I", 0.85)

    threading.Thread(target=auto_play, daemon=True).start()
    webview.start()

if __name__ == "__main__":
    main()
