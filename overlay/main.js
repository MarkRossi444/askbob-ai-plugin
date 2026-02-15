const { app, BrowserWindow, Tray, Menu, globalShortcut, ipcMain, nativeImage, shell } = require('electron');
const path = require('path');
const https = require('https');
const Store = require('electron-store');
const { autoUpdater } = require('electron-updater');

const store = new Store({
  defaults: {
    windowBounds: { x: undefined, y: undefined, width: 380, height: 520 },
    opacity: 0.95,
    backendUrl: 'https://askbob-backend-production.up.railway.app',
    rsn: '',
    gameMode: 'main',
    theme: 'dark',
    launchOnBoot: false,
  },
});

let mainWindow = null;
let tray = null;

// ─── Hiscores Cache ───
const hiscoresCache = { data: null, rsn: '', timestamp: 0 };
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

// ─── OSRS Hiscores Skill Order (from the lite JSON endpoint) ───
const SKILL_NAMES = [
  'overall', 'attack', 'defence', 'strength', 'hitpoints', 'ranged',
  'prayer', 'magic', 'cooking', 'woodcutting', 'fletching', 'fishing',
  'firemaking', 'crafting', 'smithing', 'mining', 'herblore', 'agility',
  'thieving', 'slayer', 'farming', 'runecraft', 'hunter', 'construction',
];

// ─── Window Creation ───
function createWindow() {
  const { x, y, width, height } = store.get('windowBounds');

  mainWindow = new BrowserWindow({
    x,
    y,
    width,
    height,
    minWidth: 320,
    minHeight: 400,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    resizable: true,
    skipTaskbar: false,
    hasShadow: true,
    backgroundColor: '#00000000',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.setOpacity(store.get('opacity'));
  mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'));

  // Save window position/size on move or resize
  const saveBounds = () => {
    if (mainWindow && !mainWindow.isMinimized() && !mainWindow.isMaximized()) {
      store.set('windowBounds', mainWindow.getBounds());
    }
  };
  mainWindow.on('moved', saveBounds);
  mainWindow.on('resized', saveBounds);

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// ─── System Tray ───
function createTray() {
  const iconPath = path.join(__dirname, 'assets', 'icon.png');
  let trayIcon;
  try {
    trayIcon = nativeImage.createFromPath(iconPath).resize({ width: 16, height: 16 });
  } catch {
    trayIcon = nativeImage.createEmpty();
  }

  tray = new Tray(trayIcon);
  tray.setToolTip('AskBob.Ai');

  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'Show / Hide',
      click: () => toggleWindow(),
    },
    { type: 'separator' },
    {
      label: 'Settings',
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.webContents.send('open-settings');
        }
      },
    },
    { type: 'separator' },
    {
      label: 'Quit AskBob.Ai',
      click: () => {
        app.isQuitting = true;
        app.quit();
      },
    },
  ]);

  tray.setContextMenu(contextMenu);

  tray.on('click', () => toggleWindow());
}

function toggleWindow() {
  if (!mainWindow) {
    createWindow();
    return;
  }
  if (mainWindow.isVisible()) {
    mainWindow.hide();
  } else {
    mainWindow.show();
    mainWindow.focus();
  }
}

// ─── Hiscores Fetching ───
function fetchHiscoresJSON(rsn, endpoint) {
  return new Promise((resolve, reject) => {
    const url = `https://secure.runescape.com/m=${endpoint}/index_lite.json?player=${encodeURIComponent(rsn)}`;
    https.get(url, (res) => {
      if (res.statusCode === 404) {
        resolve(null); // Player not found on this hiscores
        return;
      }
      if (res.statusCode !== 200) {
        reject(new Error(`HTTP ${res.statusCode}`));
        return;
      }
      let body = '';
      res.on('data', (chunk) => (body += chunk));
      res.on('end', () => {
        try {
          resolve(JSON.parse(body));
        } catch (e) {
          reject(e);
        }
      });
    }).on('error', reject);
  });
}

async function detectAccountType(rsn) {
  // Check specific hiscores endpoints in order of specificity
  const checks = [
    { endpoint: 'hiscore_oldschool_hardcore_ironman', type: 'HARDCORE_IRONMAN' },
    { endpoint: 'hiscore_oldschool_ultimate', type: 'ULTIMATE_IRONMAN' },
    { endpoint: 'hiscore_oldschool_ironman', type: 'IRONMAN' },
  ];

  for (const check of checks) {
    try {
      const data = await fetchHiscoresJSON(rsn, check.endpoint);
      if (data) return check.type;
    } catch {
      // Continue checking
    }
  }
  return 'NORMAL';
}

function parseHiscoresData(data) {
  if (!data || !data.skills) return null;

  const skills = {};
  for (const skill of data.skills) {
    const name = skill.name ? skill.name.toLowerCase() : null;
    if (name) {
      skills[name] = {
        level: skill.level,
        xp: skill.xp,
        rank: skill.rank,
      };
    }
  }

  const overall = skills['overall'] || {};
  return {
    total_level: overall.level || 0,
    skills,
  };
}

function calculateCombatLevel(skills) {
  const get = (name) => (skills[name] ? skills[name].level : 1);
  const base = 0.25 * (get('defence') + get('hitpoints') + Math.floor(get('prayer') / 2));
  const melee = 0.325 * (get('attack') + get('strength'));
  const ranged = 0.325 * (Math.floor(get('ranged') * 3 / 2));
  const magic = 0.325 * (Math.floor(get('magic') * 3 / 2));
  return Math.floor(base + Math.max(melee, ranged, magic));
}

async function getPlayerContext(rsn) {
  if (!rsn) return null;

  // Check cache
  const now = Date.now();
  if (
    hiscoresCache.rsn === rsn &&
    hiscoresCache.data &&
    now - hiscoresCache.timestamp < CACHE_TTL
  ) {
    return hiscoresCache.data;
  }

  try {
    const [mainData, accountType] = await Promise.all([
      fetchHiscoresJSON(rsn, 'hiscore_oldschool'),
      detectAccountType(rsn),
    ]);

    if (!mainData) return null;

    const parsed = parseHiscoresData(mainData);
    if (!parsed) return null;

    const context = {
      player_name: rsn,
      account_type: accountType,
      combat_level: calculateCombatLevel(parsed.skills),
      total_level: parsed.total_level,
      skills: parsed.skills,
    };

    // Cache it
    hiscoresCache.data = context;
    hiscoresCache.rsn = rsn;
    hiscoresCache.timestamp = now;

    return context;
  } catch (err) {
    console.error('Hiscores fetch error:', err.message);
    return hiscoresCache.data || null; // Return stale cache if available
  }
}

// ─── IPC Handlers ───
ipcMain.handle('get-settings', () => {
  return {
    backendUrl: store.get('backendUrl'),
    rsn: store.get('rsn'),
    gameMode: store.get('gameMode'),
    opacity: store.get('opacity'),
    theme: store.get('theme'),
    launchOnBoot: store.get('launchOnBoot'),
  };
});

ipcMain.handle('save-settings', (event, settings) => {
  if (settings.backendUrl !== undefined) store.set('backendUrl', settings.backendUrl);
  if (settings.rsn !== undefined) store.set('rsn', settings.rsn);
  if (settings.gameMode !== undefined) store.set('gameMode', settings.gameMode);
  if (settings.theme !== undefined) store.set('theme', settings.theme);
  if (settings.launchOnBoot !== undefined) {
    store.set('launchOnBoot', settings.launchOnBoot);
    app.setLoginItemSettings({ openAtLogin: settings.launchOnBoot });
  }
  if (settings.opacity !== undefined) {
    store.set('opacity', settings.opacity);
    if (mainWindow) mainWindow.setOpacity(settings.opacity);
  }
  return true;
});

ipcMain.handle('get-player-context', async (event, rsn) => {
  return await getPlayerContext(rsn || store.get('rsn'));
});

ipcMain.handle('window-minimize', () => {
  if (mainWindow) mainWindow.hide();
});

ipcMain.handle('window-close', () => {
  if (mainWindow) mainWindow.hide();
});

ipcMain.handle('open-external', (event, url) => {
  shell.openExternal(url);
});

// ─── Auto-Update ───
autoUpdater.autoDownload = true;
autoUpdater.autoInstallOnAppQuit = true;

function setupAutoUpdater() {
  autoUpdater.on('update-downloaded', (info) => {
    if (mainWindow) {
      mainWindow.webContents.send('update-downloaded', info.version);
    }
  });

  autoUpdater.checkForUpdatesAndNotify().catch((err) => {
    console.log('Auto-update check failed:', err.message);
  });
}

ipcMain.handle('install-update', () => {
  autoUpdater.quitAndInstall();
});

// ─── App Lifecycle ───
app.whenReady().then(() => {
  createWindow();
  createTray();
  setupAutoUpdater();

  // Global hotkey: Ctrl+Shift+B (Cmd+Shift+B on Mac)
  const hotkey = process.platform === 'darwin' ? 'CommandOrControl+Shift+B' : 'Ctrl+Shift+B';
  globalShortcut.register(hotkey, () => toggleWindow());
});

app.on('window-all-closed', () => {
  // Don't quit — keep running in tray
});

app.on('activate', () => {
  if (!mainWindow) createWindow();
});

app.on('will-quit', () => {
  globalShortcut.unregisterAll();
});

// Prevent multiple instances
const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      mainWindow.show();
      mainWindow.focus();
    }
  });
}
