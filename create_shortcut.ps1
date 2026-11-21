$WshShell = New-Object -comObject WScript.Shell
$Desktop = [System.Environment]::GetFolderPath('Desktop')
$Shortcut = $WshShell.CreateShortcut("$Desktop\YouTube Desktop Player.lnk")
$Shortcut.TargetPath = "C:\Github\youtube-desktop-player\launch.bat"
$Shortcut.WorkingDirectory = "C:\Github\youtube-desktop-player"
$Shortcut.WindowStyle = 7  # Minimized
$Shortcut.Description = "YouTube Desktop Music Player Widget"
$Shortcut.Save()
Write-Host "Desktop shortcut updated!"
