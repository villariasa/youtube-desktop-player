# Desktop Music Visualizer - Windows PowerShell Installer
[CmdletBinding()]
param()

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host "   Desktop Music Visualizer - PowerShell Installer" -ForegroundColor White
Write-Host "=========================================================" -ForegroundColor Cyan

# 1. Check Python
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Error "Python 3 is not found in PATH. Please install Python 3.10+ from python.org."
    exit 1
}

$pyVersion = (& python --version 2>&1)
Write-Host "[1/4] Found $pyVersion" -ForegroundColor Green

# 2. Install dependencies
Write-Host "[2/4] Installing Python requirements..." -ForegroundColor Yellow
& python -m pip install --upgrade pip | Out-Null
& python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to install dependencies."
    exit 1
}
Write-Host "      Dependencies installed successfully." -ForegroundColor Green

# 3. Create Desktop and Start Menu Shortcuts
Write-Host "[3/4] Creating Desktop and Start Menu shortcuts..." -ForegroundColor Yellow
$WshShell = New-Object -ComObject WScript.Shell
$DesktopPath = [Environment]::GetFolderPath('Desktop')
$StartMenuPath = [Environment]::GetFolderPath('Programs')
$IconPath = Join-Path $ScriptDir "assets\icon.ico"
$WidgetPath = Join-Path $ScriptDir "widget.py"

foreach ($dir in @($DesktopPath, $StartMenuPath)) {
    $ShortcutPath = Join-Path $dir "Desktop Music Visualizer.lnk"
    $Shortcut = $WshShell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = "pythonw.exe"
    $Shortcut.Arguments = "`"$WidgetPath`""
    $Shortcut.WorkingDirectory = $ScriptDir
    if (Test-Path $IconPath) {
        $Shortcut.IconLocation = $IconPath
    }
    $Shortcut.Description = "Immersive Glassmorphism Desktop Music Visualizer"
    $Shortcut.Save()
}
Write-Host "      Shortcuts created successfully." -ForegroundColor Green

# 4. Generate launcher script
Write-Host "[4/4] Writing launch.bat..." -ForegroundColor Yellow
@"
@echo off
cd /d "%~dp0"
start "" pythonw.exe widget.py
"@ | Set-Content -Path (Join-Path $ScriptDir "launch.bat") -Encoding ASCII

Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host "   Installation Complete!" -ForegroundColor Green
Write-Host "You can now launch the app from your Desktop shortcut." -ForegroundColor White
Write-Host "=========================================================" -ForegroundColor Cyan
