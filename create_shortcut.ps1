$WshShell = New-Object -comObject WScript.Shell
$Desktop = [System.Environment]::GetFolderPath('Desktop')
$Shortcut = $WshShell.CreateShortcut("$Desktop\YouTube Desktop Player.lnk")
$Shortcut.TargetPath = "pythonw.exe"
$Shortcut.Arguments = "C:\Github\youtube-desktop-player\widget.py"
$Shortcut.WorkingDirectory = "C:\Github\youtube-desktop-player"
$Shortcut.Description = "YouTube Desktop Music Player Widget"
$Shortcut.Save()
Write-Host "Desktop shortcut updated!"
