const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  toggleSize:      ()      => ipcRenderer.send('toggle-size'),
  closeApp:        ()      => ipcRenderer.send('close-app'),
  hideApp:         ()      => ipcRenderer.send('hide-app'),
  setAlwaysOnTop:  (val)   => ipcRenderer.send('set-always-on-top', val),
});
