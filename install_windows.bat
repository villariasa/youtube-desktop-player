@echo off
setlocal enabledelayedexpansion
title Desktop Music Visualizer - Windows Installer

echo =========================================================
echo    Desktop Music Visualizer - Windows One-Click Installer
echo =========================================================
echo.

cd /d "%~dp0"

:: 1. Check Python installation
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python 3 is not found in your system PATH.
    echo Please install Python 3.10+ from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%v in ('python --version 2^>^&1') do set PY_VER=%%v
echo [1/4] Found %PY_VER%

:: 2. Upgrade pip and install requirements
echo [2/4] Installing dependencies from requirements.txt...
python -m pip install --upgrade pip >nul 2>nul
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)
echo      Dependencies installed successfully.

:: 3. Generate icons if missing
if not exist "assets\icon.ico" (
    echo [3/4] Generating application icon...
    python -c "from PIL import Image, ImageDraw; size=256; img=Image.new('RGBA', (size,size), (0,0,0,0)); draw=ImageDraw.Draw(img); draw.ellipse([8,8,size-8,size-8], fill=(13,23,33,240), outline=(34,211,238,255), width=4); [draw.rounded_rectangle([38+i*20, (size-h)//2, 38+i*20+14, (size-h)//2+h], radius=7, fill=(34,211,238,255)) for i, h in enumerate([30,55,90,130,160,120,85,50,25])]; img.save('assets\\icon.ico', format='ICO', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])" >nul 2>nul
)

:: 4. Create Desktop & Start Menu Shortcuts via PowerShell
echo [3/4] Creating Desktop shortcut...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ws = New-Object -ComObject WScript.Shell; " ^
  "$desktop = [Environment]::GetFolderPath('Desktop'); " ^
  "$s = $ws.CreateShortcut(\"$desktop\Desktop Music Visualizer.lnk\"); " ^
  "$s.TargetPath = 'pythonw.exe'; " ^
  "$s.Arguments = '\"%~dp0widget.py\"'; " ^
  "$s.WorkingDirectory = '%~dp0'; " ^
  "$s.IconLocation = '%~dp0assets\icon.ico'; " ^
  "$s.Description = 'Immersive Glassmorphism Desktop Music Visualizer'; " ^
  "$s.Save(); " ^
  "$startMenu = [Environment]::GetFolderPath('Programs'); " ^
  "$sm = $ws.CreateShortcut(\"$startMenu\Desktop Music Visualizer.lnk\"); " ^
  "$sm.TargetPath = 'pythonw.exe'; " ^
  "$sm.Arguments = '\"%~dp0widget.py\"'; " ^
  "$sm.WorkingDirectory = '%~dp0'; " ^
  "$sm.IconLocation = '%~dp0assets\icon.ico'; " ^
  "$sm.Description = 'Immersive Glassmorphism Desktop Music Visualizer'; " ^
  "$sm.Save(); "

echo      Shortcut created on Desktop and Start Menu.

:: 5. Create launcher batch file
echo [4/4] Creating clean background launcher...
(
    echo @echo off
    echo cd /d "%%~dp0"
    echo start "" pythonw.exe widget.py
) > launch.bat

echo.
echo =========================================================
echo    Installation Complete!
echo =========================================================
echo You can now launch the visualizer anytime by:
echo   - Double-clicking the "Desktop Music Visualizer" on your Desktop
echo   - Running "launch.bat" in this folder
echo.
pause
