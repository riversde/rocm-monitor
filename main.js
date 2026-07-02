const { app, BrowserWindow, Tray, Menu, ipcMain, nativeImage } = require('electron');
const path = require('path');
const isDev = !app.isPackaged;

let mainWindow = null;
let tray = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 960,
    height: 720,
    minWidth: 700,
    minHeight: 500,
    show: true,
    fullscreenable: false,
    backgroundColor: '#1a1a2e',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  mainWindow.webContents.on('will-navigate', (event) => event.preventDefault());

  if (isDev) {
    mainWindow.loadFile('index.html');
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile('index.html');
  }

  mainWindow.on('closed', () => { mainWindow = null; });
}

function createTray() {
  let trayIcon = null;
  const iconPath = path.join(__dirname, 'build', 'tray.png');
  try {
    const img = nativeImage.createFromPath(iconPath);
    if (!img.isEmpty()) trayIcon = img;
  } catch (e) {}

  if (!trayIcon) {
    try {
      const img = nativeImage.createFromPath(path.join(__dirname, 'build', 'icon.ico'));
      if (!img.isEmpty()) trayIcon = img;
    } catch (e) {}
  }

  if (!trayIcon) {
    // Fallback: create a simple 16x16 blue square as PNG in memory
    trayIcon = nativeImage.createFromBuffer(Buffer.from(
      'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAIklEQVQ4jWNgGAWjYBSMglEwCkYB',
      'base64'
    ));
  }

  tray = new Tray(trayIcon);
  tray.setToolTip('GPU Monitor for AI Workloads');

  const contextMenu = Menu.buildFromTemplate([
    { label: 'Show GPU Monitor for AI Workloads', click: () => {
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.show();
        if (mainWindow.isMinimized()) mainWindow.restore();
        mainWindow.focus();
      }
    }},
    { type: 'separator' },
    { label: 'Settings', click: () => {
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('open-settings');
      }
    }},
    { type: 'separator' },
    { label: 'Quit', click: () => app.quit() },
  ]);

  tray.setContextMenu(contextMenu);

  tray.on('click', () => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      if (mainWindow.isVisible()) mainWindow.hide();
      else { mainWindow.show(); mainWindow.focus(); }
    }
  });
}

// IPC: Save sources config
ipcMain.handle('save-sources', async (_event, sources) => {
  const fs = require('fs');
  const configPath = path.join(app.getPath('userData'), 'config.json');
  fs.writeFileSync(configPath, JSON.stringify(sources, null, 2));
  return { ok: true };
});

// IPC: Load sources config
ipcMain.handle('load-sources', async () => {
  const fs = require('fs');
  const configPath = path.join(app.getPath('userData'), 'config.json');
  if (fs.existsSync(configPath)) {
    return JSON.parse(fs.readFileSync(configPath, 'utf-8'));
  }
  // Default sources — replace with your own config via Settings panel
  return {
    sources: [
      { id: 'remote-gpu', name: 'Remote GPU', type: 'rocm', host: '', port: 5900, enabled: false },
      { id: 'local-nvidia', name: 'Local NVIDIA', type: 'nvidia', local: true, enabled: true },
    ],
    refreshInterval: 2000,
  };
});

// IPC: Run nvidia-smi locally
ipcMain.handle('run-nvidia-smi', async () => {
  const { exec } = require('child_process');
  return new Promise((resolve) => {
    exec('nvidia-smi --query-gpu=name,temperature.gpu,memory.used,memory.total,power.draw,power.limit,clocks.gr,clocks.mem,utilization.gpu,fan.speed,driver_version --format=csv,noheader,nounits',
      { timeout: 5000 }, (error, stdout, stderr) => {
        if (error) {
          resolve({ error: error.message || 'nvidia-smi not available' });
          return;
        }
        const line = stdout.trim();
        if (!line) {
          resolve({ error: 'No NVIDIA GPU detected' });
          return;
        }
        const parts = line.split(',').map(s => s.trim());
        if (parts.length < 11) {
          resolve({ error: 'Unexpected nvidia-smi output format' });
          return;
        }
        resolve({
          gpu: 0,
          name: parts[0] || 'NVIDIA GPU',
          temperature: parseFloat(parts[1]) || 0,
          memory_used: parts[2],
          memory_total: parts[3],
          power_draw: parseFloat(parts[4]) || 0,
          power_limit: parseFloat(parts[5]) || 0,
          clock_gr: parts[6],
          clock_mem: parts[7],
          utilization: parseFloat(parts[8]) || 0,
          fan_speed: parseFloat(parts[9]) || 0,
          driver_version: parts[10] || '',
        });
      });
  });
});

// IPC: Window controls from renderer
ipcMain.on('window-minimize', () => {
  if (mainWindow) mainWindow.minimize();
});

ipcMain.on('window-close', () => {
  if (mainWindow) mainWindow.close();
});

app.whenReady().then(() => {
  createWindow();
  createTray();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

app.on('before-quit', () => {
  if (tray) { try { tray.destroy(); } catch (e) {} tray = null; }
  if (mainWindow) { try { mainWindow.destroy(); } catch (e) {} mainWindow = null; }
});
