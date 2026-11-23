#!/usr/bin/env bash
# ==============================================================================
# Desktop Music Visualizer - 1-Click Standalone Linux Installer
# Installs standalone application, desktop shortcuts, and terminal command
# No root (sudo) or compilation required!
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="youtube-desktop-player"
DISPLAY_NAME="Desktop Music Visualizer"
APP_DIR="${HOME}/.local/share/${APP_NAME}"
BIN_DIR="${HOME}/.local/bin"
ICON_DIR="${HOME}/.local/share/icons/hicolor/256x256/apps"
DESKTOP_DIR="${HOME}/.local/share/applications"
TARGET_APPIMAGE="${APP_DIR}/Desktop-Music-Visualizer.AppImage"
RELEASE_URL="https://github.com/villariasa/youtube-desktop-player/releases/download/v1.0.0/Desktop-Music-Visualizer-v1.0.0-Linux.AppImage"

echo "========================================================="
echo "   ${DISPLAY_NAME} - 1-Click Linux Installer"
echo "========================================================="
echo ""

mkdir -p "${APP_DIR}"
mkdir -p "${BIN_DIR}"
mkdir -p "${ICON_DIR}"
mkdir -p "${DESKTOP_DIR}"

# Step 1: Locate or Download Standalone AppImage
echo "[1/4] Setting up standalone application binary..."

LOCAL_APPIMAGE=""
if [ -f "${SCRIPT_DIR}/dist/Desktop-Music-Visualizer-v1.0.0-Linux.AppImage" ]; then
    LOCAL_APPIMAGE="${SCRIPT_DIR}/dist/Desktop-Music-Visualizer-v1.0.0-Linux.AppImage"
elif [ -f "${SCRIPT_DIR}/dist/Desktop-Music-Visualizer" ]; then
    LOCAL_APPIMAGE="${SCRIPT_DIR}/dist/Desktop-Music-Visualizer"
fi

if [ -n "${LOCAL_APPIMAGE}" ]; then
    echo "      Found local standalone package: $(basename "${LOCAL_APPIMAGE}")"
    cp "${LOCAL_APPIMAGE}" "${TARGET_APPIMAGE}"
    chmod +x "${TARGET_APPIMAGE}"
elif [ -f "${TARGET_APPIMAGE}" ]; then
    echo "      Using existing installed standalone binary."
    chmod +x "${TARGET_APPIMAGE}"
else
    echo "      Local binary not found. Downloading standalone package from GitHub release..."
    DOWNLOAD_SUCCESS=false
    if command -v curl >/dev/null 2>&1; then
        curl -fL -# -o "${TARGET_APPIMAGE}" "${RELEASE_URL}" && DOWNLOAD_SUCCESS=true || true
    elif command -v wget >/dev/null 2>&1; then
        wget -q --show-progress -O "${TARGET_APPIMAGE}" "${RELEASE_URL}" && DOWNLOAD_SUCCESS=true || true
    fi

    if [ "$DOWNLOAD_SUCCESS" = "true" ] && [ -f "${TARGET_APPIMAGE}" ] && [ -s "${TARGET_APPIMAGE}" ]; then
        chmod +x "${TARGET_APPIMAGE}"
        echo "      Download complete!"
    else
        echo "      [INFO] Standalone binary unavailable. Falling back to portable Python runner..."
        # Fallback to python venv if download fails or running offline
        if command -v python3 >/dev/null 2>&1; then
            VENV_DIR="${APP_DIR}/venv"
            python3 -m venv "${VENV_DIR}" 2>/dev/null || true
            if [ -x "${VENV_DIR}/bin/pip" ]; then
                "${VENV_DIR}/bin/pip" install --upgrade pip -q 2>/dev/null || true
                "${VENV_DIR}/bin/pip" install -r "${SCRIPT_DIR}/requirements.txt" -q 2>/dev/null || true
            fi
            cat << 'RUNNER' > "${TARGET_APPIMAGE}"
#!/usr/bin/env bash
HERE="$(dirname "$(readlink -f "${0}")")"
if [ -x "${HERE}/venv/bin/python" ]; then
    exec "${HERE}/venv/bin/python" "${HERE}/widget.py" "$@"
else
    exec python3 "${HERE}/widget.py" "$@"
fi
RUNNER
            chmod +x "${TARGET_APPIMAGE}"
            cp "${SCRIPT_DIR}/widget.py" "${APP_DIR}/" 2>/dev/null || true
            cp "${SCRIPT_DIR}/renderer.js" "${APP_DIR}/" 2>/dev/null || true
            cp "${SCRIPT_DIR}/style.css" "${APP_DIR}/" 2>/dev/null || true
        fi
    fi
fi

# Step 2: Install Application Icons
echo "[2/4] Installing high-resolution application icon..."
if [ -f "${SCRIPT_DIR}/assets/icon.png" ]; then
    cp "${SCRIPT_DIR}/assets/icon.png" "${ICON_DIR}/${APP_NAME}.png"
    cp "${SCRIPT_DIR}/assets/icon.png" "${APP_DIR}/icon.png"
fi

# Step 3: Configure Desktop Shortcuts and Terminal Command
echo "[3/4] Creating Desktop Shortcut and Command Launcher..."

# Desktop Entry
cat << EOF > "${DESKTOP_DIR}/${APP_NAME}.desktop"
[Desktop Entry]
Name=${DISPLAY_NAME}
Comment=Immersive Glassmorphism Desktop Music Visualizer
Exec=${TARGET_APPIMAGE}
Icon=${ICON_DIR}/${APP_NAME}.png
Terminal=false
Type=Application
Categories=AudioVideo;Audio;Player;
StartupNotify=true
EOF
chmod +x "${DESKTOP_DIR}/${APP_NAME}.desktop"

# Copy to ~/Desktop if it exists
if [ -d "${HOME}/Desktop" ]; then
    cp "${DESKTOP_DIR}/${APP_NAME}.desktop" "${HOME}/Desktop/${APP_NAME}.desktop"
    chmod +x "${HOME}/Desktop/${APP_NAME}.desktop"
    gio set "${HOME}/Desktop/${APP_NAME}.desktop" metadata::trusted true 2>/dev/null || true
fi

# Terminal CLI command in ~/.local/bin
cat << EOF > "${BIN_DIR}/${APP_NAME}"
#!/usr/bin/env bash
exec "${TARGET_APPIMAGE}" "\$@"
EOF
chmod +x "${BIN_DIR}/${APP_NAME}"

# Update desktop database
update-desktop-database "${DESKTOP_DIR}" 2>/dev/null || true
gtk-update-icon-cache -f -t "${HOME}/.local/share/icons/hicolor" 2>/dev/null || true

echo "[4/4] Installation complete!"
echo ""
echo "========================================================="
echo "   ${DISPLAY_NAME} is Ready to Use!"
echo "========================================================="
echo "Launch options:"
echo "  1. Double-click '${DISPLAY_NAME}' on your Desktop"
echo "  2. Search for '${DISPLAY_NAME}' in your Application Menu"
echo "  3. Type '${APP_NAME}' in any terminal"
echo "  4. Run './launch.sh' directly from this folder"
echo "========================================================="
echo ""

# Launch immediately if interactive display is present
if [ -n "$DISPLAY" ]; then
    echo "Starting ${DISPLAY_NAME} now..."
    "${TARGET_APPIMAGE}" >/dev/null 2>&1 &
fi
