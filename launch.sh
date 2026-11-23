#!/usr/bin/env bash
# ==============================================================================
# Desktop Music Visualizer - 1-Click Linux Launcher
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 1. Prefer local standalone AppImage in dist/
if [ -f "${SCRIPT_DIR}/dist/Desktop-Music-Visualizer-v1.0.0-Linux.AppImage" ]; then
    chmod +x "${SCRIPT_DIR}/dist/Desktop-Music-Visualizer-v1.0.0-Linux.AppImage"
    exec "${SCRIPT_DIR}/dist/Desktop-Music-Visualizer-v1.0.0-Linux.AppImage" "$@"
fi

# 2. Check installed standalone AppImage in ~/.local/share
INSTALLED_APPIMAGE="${HOME}/.local/share/youtube-desktop-player/Desktop-Music-Visualizer.AppImage"
if [ -f "${INSTALLED_APPIMAGE}" ]; then
    chmod +x "${INSTALLED_APPIMAGE}"
    exec "${INSTALLED_APPIMAGE}" "$@"
fi

# 3. Check standalone binary in dist/
if [ -f "${SCRIPT_DIR}/dist/Desktop-Music-Visualizer" ]; then
    chmod +x "${SCRIPT_DIR}/dist/Desktop-Music-Visualizer"
    exec "${SCRIPT_DIR}/dist/Desktop-Music-Visualizer" "$@"
fi

# 4. Check local Python virtual environment (.venv)
if [ -f "${SCRIPT_DIR}/.venv/bin/python" ]; then
    exec "${SCRIPT_DIR}/.venv/bin/python" "${SCRIPT_DIR}/widget.py" "$@"
fi

# 5. Check system python3
if command -v python3 >/dev/null 2>&1; then
    exec python3 "${SCRIPT_DIR}/widget.py" "$@"
fi

# 6. Fallback: run installer
echo "[!] Standalone executable not found. Running installer..."
exec "${SCRIPT_DIR}/install_linux.sh" "$@"
