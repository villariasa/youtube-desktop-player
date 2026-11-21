# Creates Desktop shortcut for YouTube Desktop Player
$WshShell = New-Object -comObject WScript.Shell
$Desktop = [System.Environment]::GetFolderPath('Desktop')

# Main shortcut → Python player
$Shortcut = $WshShell.CreateShortcut("$Desktop\YouTube Desktop Player.lnk")
$Shortcut.TargetPath = "pythonw.exe"
$Shortcut.Arguments  = "C:\Github\youtube-desktop-player\player.py"
$Shortcut.WorkingDirectory = "C:\Github\youtube-desktop-player"
$Shortcut.Description = "Launch YouTube Desktop Player"
$Shortcut.Save()
Write-Host "Shortcut created on Desktop!"
