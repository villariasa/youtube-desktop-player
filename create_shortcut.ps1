$WshShell = New-Object -comObject WScript.Shell
$Desktop = [System.Environment]::GetFolderPath('Desktop')
$Shortcut = $WshShell.CreateShortcut("$Desktop\YouTube Desktop Player.lnk")
$Shortcut.TargetPath = "C:\Github\youtube-desktop-player\launch.bat"
$Shortcut.WorkingDirectory = "C:\Github\youtube-desktop-player"
$Shortcut.Description = "Wallpaper-Integrated Desktop Music Visualizer"
$Shortcut.Save()
Write-Host "Desktop shortcut updated!"
