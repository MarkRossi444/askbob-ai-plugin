const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('askbob', {
  // Settings
  getSettings: () => ipcRenderer.invoke('get-settings'),
  saveSettings: (settings) => ipcRenderer.invoke('save-settings', settings),

  // Player context (hiscores)
  getPlayerContext: (rsn) => ipcRenderer.invoke('get-player-context', rsn),

  // Window controls
  minimize: () => ipcRenderer.invoke('window-minimize'),
  close: () => ipcRenderer.invoke('window-close'),

  // External links
  openExternal: (url) => ipcRenderer.invoke('open-external', url),

  // Listen for settings panel open from tray
  onOpenSettings: (callback) => {
    ipcRenderer.on('open-settings', () => callback());
  },

  // Auto-update
  onUpdateDownloaded: (callback) => {
    ipcRenderer.on('update-downloaded', (_event, version) => callback(version));
  },
  installUpdate: () => ipcRenderer.invoke('install-update'),
});
