# Script to create Desktop shortcut for YouTube Desktop Player
$WshShell = New-Object -comObject WScript.Shell
$Desktop = [System.Environment]::GetFolderPath('Desktop')
$Shortcut = $WshShell.CreateShortcut("$Desktop\YouTube Desktop Player.lnk")
$Shortcut.TargetPath = "C:\Github\youtube-desktop-player\launch.bat"
$Shortcut.WorkingDirectory = "C:\Github\youtube-desktop-player"
$Shortcut.Description = "Launch YouTube Desktop Player"
$Shortcut.Save()
Write-Host "Shortcut created on Desktop!"
