# YouTube Desktop Player 🎵

<div align="center">

![YouTube Desktop Player](https://img.shields.io/badge/YouTube-Desktop%20Player-red?style=for-the-badge&logo=youtube)
![Electron](https://img.shields.io/badge/Electron-28-47848F?style=for-the-badge&logo=electron&logoColor=white)
![Node.js](https://img.shields.io/badge/Node.js-22-339933?style=for-the-badge&logo=node.js&logoColor=white)
![Windows](https://img.shields.io/badge/Windows-10%2F11-0078D6?style=for-the-badge&logo=windows&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-purple?style=for-the-badge)

**A floating, always-on-top YouTube music player widget with an anime dark glassmorphism UI.**

</div>

---

## ✨ Features

| Feature | Details |
|---|---|
| 🎨 Anime Dark UI | Glassmorphism with purple/pink gradient accents |
| 📌 Always on Top | Pin/unpin the player over all other windows |
| 🔍 YouTube Search | Search directly — results open in the embedded player |
| ⚡ Quick Tags | One-click buttons: Lo-Fi, Anime OST, BABYMONSTER, Naruto, JJK, Solo Leveling |
| 🪟 Mini Mode | Toggle between full (420×640) and mini bar (420×110) |
| 🖱️ Draggable | Drag the title bar to reposition anywhere on screen |
| 🗄️ System Tray | Minimize to tray; click tray icon to show/hide |
| 🖥️ Frameless | No OS window border — clean floating widget |

---

## 🚀 Quick Start

### Prerequisites

- [Node.js 18+](https://nodejs.org/) (tested on v22.13.1)
- npm (comes with Node.js)

### Installation

```bash
# Clone the repo
git clone https://github.com/villariasa/youtube-desktop-player.git
cd youtube-desktop-player

# Install dependencies
npm install

# Launch the player
npm start
```

The player will appear in the **bottom-right corner** of your screen.

---

## 🎮 Controls

| Control | Action |
|---|---|
| **Search bar** | Type + Enter or click GO |
| **Quick Tag buttons** | Instant search for preset categories |
| 📌 Pin button | Toggle always-on-top |
| ⬛ Toggle button | Switch between full mode and mini bar |
| － Hide button | Minimize to system tray |
| ✕ Close button | Quit the app |
| **`M` key** | Toggle mini/full mode |
| **`Esc` key** | Hide to tray |

---

## 🗂️ Project Structure

```
youtube-desktop-player/
├── main.js         # Electron main process (window, tray, IPC)
├── preload.js      # Secure bridge between main & renderer
├── index.html      # UI markup with webview embed
├── style.css       # Anime glassmorphism dark theme
├── renderer.js     # UI logic, search, controls
├── package.json    # Dependencies & scripts
└── README.md       # This file
```

---

## 🛠️ Tech Stack

- **[Electron](https://www.electronjs.org/)** — Cross-platform desktop shell
- **YouTube Embedded Player** — Via `<webview>` tag in Electron
- **Vanilla JS + CSS** — No heavy frontend frameworks
- **Glassmorphism CSS** — `backdrop-filter`, gradients, translucent layers

---

## 💻 Desktop Shortcut (Windows)

A `.bat` launcher is included. Double-click `launch.bat` from the project folder to start the player without opening a terminal.

You can also create a shortcut:
1. Right-click `launch.bat` → Send to → Desktop (create shortcut)
2. Right-click the shortcut → Properties → Change Icon → pick any YouTube/music icon

---

## 🗺️ Roadmap

- [ ] YouTube Data API v3 integration (search results list)
- [ ] Playlist queue management
- [ ] Global media key support (Play/Pause/Next)
- [ ] `electron-packager` .exe build
- [ ] Custom themes (Naruto, Solo Leveling, JJK skins)

---

## 👤 Author

**Medy B. Villarias** — [@villariasa](https://github.com/villariasa)

---

## 📝 License

[MIT](LICENSE) — free to use, modify, and distribute.
