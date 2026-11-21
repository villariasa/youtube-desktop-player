'use strict';

const { app, BrowserWindow, ipcMain, Tray, Menu, nativeImage, screen } = require('electron');
const path = require('path');

let mainWindow;
let tray;
let isExpanded = true;

const MINI_SIZE = { width: 420, height: 110 };
const FULL_SIZE = { width: 420, height: 640 };

app.commandLine.appendSwitch('disable-features', 'OutOfBlinkCors');
app.commandLine.appendSwitch('autoplay-policy', 'no-user-gesture-required');

function createWindow() {
  const { width: sw, height: sh } = screen.getPrimaryDisplay().workAreaSize;

  mainWindow = new BrowserWindow({
    width:     FULL_SIZE.width,
    height:    FULL_SIZE.height,
    x:         sw - FULL_SIZE.width  - 20,
    y:         sh - FULL_SIZE.height - 20,
    frame:     false,
    transparent: true,
    alwaysOnTop: true,
    resizable:   false,
    skipTaskbar: false,
    hasShadow:   false,
    show:        false,
    webPreferences: {
      preload:          path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration:  false,
      webviewTag:       true,
      webSecurity:      false,
    },
  });

  mainWindow.loadFile('index.html');

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
    mainWindow.focus();
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

function createTray() {
  const icon = nativeImage.createEmpty();
  tray = new Tray(icon);
  tray.setToolTip('YouTube Desktop Player');

  const ctxMenu = Menu.buildFromTemplate([
    { label: 'Show Player', click: () => { mainWindow?.show(); mainWindow?.focus(); } },
    { label: 'Hide Player', click: () => mainWindow?.hide() },
    { type: 'separator' },
    { label: 'Always on Top', type: 'checkbox', checked: true,
      click: (mi) => mainWindow?.setAlwaysOnTop(mi.checked) },
    { type: 'separator' },
    { label: 'Quit', click: () => app.quit() },
  ]);

  tray.setContextMenu(ctxMenu);
  tray.on('click', () => {
    if (mainWindow?.isVisible()) mainWindow.hide();
    else { mainWindow?.show(); mainWindow?.focus(); }
  });
}

// ── IPC handlers ────────────────────────────────────────────
ipcMain.on('toggle-size', () => {
  if (!mainWindow) return;
  isExpanded = !isExpanded;
  const { width: sw, height: sh } = screen.getPrimaryDisplay().workAreaSize;
  const size = isExpanded ? FULL_SIZE : MINI_SIZE;
  mainWindow.setSize(size.width, size.height, true);
  mainWindow.setPosition(sw - size.width - 20, sh - size.height - 20, true);
});

ipcMain.on('close-app',        ()      => app.quit());
ipcMain.on('hide-app',         ()      => mainWindow?.hide());
ipcMain.on('set-always-on-top', (_e, val) => mainWindow?.setAlwaysOnTop(val));

// ── App lifecycle ────────────────────────────────────────────
app.whenReady().then(() => {
  createWindow();
  createTray();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
