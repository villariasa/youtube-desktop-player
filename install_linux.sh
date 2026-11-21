#!/usr/bin/env bash
# ==============================================================================
# Desktop Music Visualizer - Linux Automated Installer
# Supports Debian/Ubuntu/Mint, Arch/Manjaro, Fedora/RHEL, and openSUSE
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="youtube-desktop-player"
DISPLAY_NAME="Desktop Music Visualizer"

echo "========================================================="
echo "   ${DISPLAY_NAME} - Linux Automated Installer"
echo "========================================================="
echo ""

# 1. Detect Package Manager and Install System Dependencies
echo "[1/5] Detecting Linux distribution and installing system dependencies..."

if command -v apt-get >/dev/null 2>&1; then
    echo "      Detected Debian / Ubuntu / Mint based system (apt)"
    sudo apt-get update -qq
    # Try WebKit2GTK (4.1 or 4.0 depending on distribution version)
    sudo apt-get install -y python3 python3-pip python3-venv python3-gi \
        libpulse-dev alsa-utils libgirepository1.0-dev gir1.2-webkit2-4.1 2>/dev/null || \
    sudo apt-get install -y python3 python3-pip python3-venv python3-gi \
        libpulse-dev alsa-utils libgirepository1.0-dev gir1.2-webkit2-4.0 2>/dev/null || true

elif command -v pacman >/dev/null 2>&1; then
    echo "      Detected Arch Linux / Manjaro based system (pacman)"
    sudo pacman -Sy --noconfirm --needed python python-pip python-virtualenv \
        webkit2gtk alsa-utils libpulse

elif command -v dnf >/dev/null 2>&1; then
    echo "      Detected Fedora / RHEL based system (dnf)"
    sudo dnf install -y python3 python3-pip python3-virtualenv \
        webkit2gtk4.1 alsa-utils pulseaudio-libs-devel 2>/dev/null || \
    sudo dnf install -y python3 python3-pip python3-virtualenv \
        webkit2gtk4.0 alsa-utils pulseaudio-libs-devel 2>/dev/null || true

elif command -v zypper >/dev/null 2>&1; then
    echo "      Detected openSUSE based system (zypper)"
    sudo zypper install -y python3 python3-pip python3-virtualenv \
        webkit2gtk3-devel alsa-utils libpulse-devel || true

else
    echo "      [WARN] Unknown package manager. Please ensure Python 3, WebKit2GTK, and ALSA/Pulse are installed."
fi

# 2. Set up Python Virtual Environment
echo "[2/5] Setting up isolated Python virtual environment..."
VENV_DIR="${SCRIPT_DIR}/.venv"
if [ ! -d "${VENV_DIR}" ]; then
    python3 -m venv "${VENV_DIR}"
fi

# 3. Install Python Dependencies
echo "[3/5] Installing Python packages from requirements.txt..."
"${VENV_DIR}/bin/pip" install --upgrade pip -q
"${VENV_DIR}/bin/pip" install -r "${SCRIPT_DIR}/requirements.txt" -q

# 4. Generate Icon if missing
if [ ! -f "${SCRIPT_DIR}/assets/icon.png" ]; then
    echo "[4/5] Generating application icon..."
    mkdir -p "${SCRIPT_DIR}/assets"
    "${VENV_DIR}/bin/python" -c "
from PIL import Image, ImageDraw
size = 256
img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)
draw.ellipse([8, 8, size-8, size-8], fill=(13, 23, 33, 240), outline=(34, 211, 238, 255), width=4)
for i, h in enumerate([30, 55, 90, 130, 160, 120, 85, 50, 25]):
    bx = 38 + i * 20
    draw.rounded_rectangle([bx, (size-h)//2, bx + 14, (size-h)//2 + h], radius=7, fill=(34, 211, 238, 255))
img.save('${SCRIPT_DIR}/assets/icon.png')
"
fi

# Install icon to system icon theme directory
ICON_DEST="${HOME}/.local/share/icons/hicolor/256x256/apps"
mkdir -p "${ICON_DEST}"
cp "${SCRIPT_DIR}/assets/icon.png" "${ICON_DEST}/${APP_NAME}.png"

# 5. Create Desktop Entry & CLI Symlink
echo "[5/5] Creating Desktop Launcher and Terminal CLI command..."

# Desktop file
DESKTOP_DIR="${HOME}/.local/share/applications"
mkdir -p "${DESKTOP_DIR}"
cat <<EOF > "${DESKTOP_DIR}/${APP_NAME}.desktop"
[Desktop Entry]
Name=${DISPLAY_NAME}
Comment=Immersive Glassmorphism Desktop Music Visualizer
Exec="${VENV_DIR}/bin/python" "${SCRIPT_DIR}/widget.py"
Icon=${ICON_DEST}/${APP_NAME}.png
Terminal=false
Type=Application
Categories=AudioVideo;Audio;Player;
StartupNotify=true
EOF

chmod +x "${DESKTOP_DIR}/${APP_NAME}.desktop"

# Copy to Desktop if ~/Desktop exists
if [ -d "${HOME}/Desktop" ]; then
    cp "${DESKTOP_DIR}/${APP_NAME}.desktop" "${HOME}/Desktop/${APP_NAME}.desktop"
    chmod +x "${HOME}/Desktop/${APP_NAME}.desktop"
    gio set "${HOME}/Desktop/${APP_NAME}.desktop" metadata::trusted true 2>/dev/null || true
fi

# CLI wrapper in ~/.local/bin
BIN_DIR="${HOME}/.local/bin"
mkdir -p "${BIN_DIR}"
cat <<EOF > "${BIN_DIR}/${APP_NAME}"
#!/usr/bin/env bash
exec "${VENV_DIR}/bin/python" "${SCRIPT_DIR}/widget.py" "\$@"
EOF
chmod +x "${BIN_DIR}/${APP_NAME}"

echo ""
echo "========================================================="
echo "   Installation Successful!"
echo "========================================================="
echo "You can launch the visualizer by:"
echo "  1. Clicking '${DISPLAY_NAME}' in your Application Menu"
echo "  2. Double-clicking the shortcut on your Desktop"
echo "  3. Running '${APP_NAME}' in any terminal"
echo "========================================================="
