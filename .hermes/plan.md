# ROCM Monitor Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build a native Windows desktop app (Electron) that displays real-time AMD GPU telemetry from the Radeon AI PC via a lightweight HTTP agent running on the remote machine.

**Architecture:** Two components — (1) a tiny Python HTTP server (`rocm_agent.py`) that runs on the AI PC and returns `rocm-smi` data as JSON, (2) an Electron desktop app that polls this endpoint every 2 seconds and renders a clean dashboard with gauges, charts, and alerts.

**Tech Stack:** Electron + vanilla JS SPA (renderer), Python Flask (agent), no build step for the web layer.

---

## Component Overview

```
AI PC (192.168.90.171)                  Windows Desktop (Pedro's machine)
┌──────────────────────┐                ┌─────────────────────────────┐
│ rocm_agent.py        │  HTTP/JSON     │  Electron App               │
│ (Flask, port 5900)   │ ◄────────────► │  main.js + preload.js       │
│                      │  2s polling    │  index.html + renderer.js   │
│ Parses rocm-smi      │                │  styles.css                 │
│ Exposes /api/rocm    │                │  system tray icon           │
└──────────────────────┘                └─────────────────────────────┘
```

---

## Task 1: Create the AI PC HTTP Agent

**Objective:** Build a tiny Flask server that runs on the AI PC, executes `rocm-smi`, parses the output, and serves JSON.

**Files:**
- Create: `rocm-monitor-agent/rocm_agent.py`
- Create: `rocm-monitor-agent/requirements.txt`
- Create: `rocm-monitor-agent/start_agent.bat`

**Step 1: Create requirements.txt**

```
flask>=3.0
```

**Step 2: Create the Flask agent (`rocm_agent.py`)**

```python
#!/usr/bin/env python3
"""ROCM telemetry agent — runs on the AI PC, exposes GPU data as JSON."""

import json
import re
import subprocess
import platform
from datetime import datetime, timezone
from flask import Flask, jsonify

app = Flask(__name__)

def parse_rocm_smi():
    """Execute rocm-smi and parse output into structured JSON."""
    try:
        result = subprocess.run(
            ['rocm-smi', '--showuse', '--showtemp', '--showmemuse',
             '--showpower', '--showclock', '--showfanspeed'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return {'error': f'rocm-smi failed: {result.stderr.strip()}'}

        # Parse the output line by line
        lines = result.stdout.strip().split('\n')
        gpus = []
        current_gpu = {}

        for line in lines:
            line = line.strip()
            if not line or line.startswith('='):
                if current_gpu and 'gpu' in current_gpu:
                    gpus.append(current_gpu)
                    current_gpu = {}
                continue

            # Detect GPU header line
            gpu_match = re.match(r'(GPU#\s*)(\d+)', line)
            if gpu_match:
                if current_gpu and 'gpu' in current_gpu:
                    gpus.append(current_gpu)
                current_gpu = {'gpu': int(gpu_match.group(2))}
                continue

            # Parse key-value pairs
            parts = line.split()
            if len(parts) >= 2:
                key = parts[0].rstrip(':')
                value = ' '.join(parts[1:])

                # Clean up values
                if 'VGT' in key or 'THM' in key or 'CLK' in key or 'PWR' in key or 'FAN' in key:
                    current_gpu[key] = value
                elif '%' in value:
                    current_gpu[key] = value.replace('%', '')
                elif 'W' in value and not value.endswith('W'):
                    # Power value like "120.5 W"
                    pass

        # If only one GPU, still return as array
        if current_gpu and 'gpu' in current_gpu:
            gpus.append(current_gpu)

        if not gpus:
            # Fallback: try to parse single-GPU output
            return parse_single_gpu(result.stdout)

        return {'gpus': gpus, 'timestamp': datetime.now(timezone.utc).isoformat()}

    except FileNotFoundError:
        return {'error': 'rocm-smi not found. Is ROCm installed?'}
    except subprocess.TimeoutExpired:
        return {'error': 'rocm-smi timed out'}
    except Exception as e:
        return {'error': str(e)}


def parse_single_gpu(output):
    """Fallback parser for single-GPU rocm-smi output format."""
    gpu = {}
    lines = output.strip().split('\n')

    for line in lines:
        line = line.strip()
        if not line or line.startswith('=') or 'GPU#' in line:
            continue

        parts = line.split()
        if len(parts) >= 2:
            key = parts[0].rstrip(':').strip()
            value = ' '.join(parts[1:]).strip()

            # Map common rocm-smi keys to clean names
            mapping = {
                'GPU#': 'gpu',
                'THM': 'temperature',
                'HOT': 'hotspot_temperature',
                'HBM': 'hbm_temperature',
                'CLK': 'clock_speed',
                'PWR': 'power_draw',
                'SCLK': 'sclk',
                'MCLK': 'mclk',
                'VGT': 'vgt_clock',
                'MEM': 'memory_usage',
                'VRAM': 'vram_usage',
                'GDS': 'gds_usage',
                'HBM': 'hbm_usage',
                'FAN': 'fan_speed',
            }

            clean_key = mapping.get(key, key.lower().replace(' ', '_'))
            gpu[clean_key] = value

    if not gpu:
        # Last resort: try to extract any numbers from the output
        return {'raw_output': output, 'gpu': 0}

    gpu['gpu'] = 0
    return {'gpus': [gpu], 'timestamp': datetime.now(timezone.utc).isoformat()}


@app.route('/api/rocm')
def get_rocm_data():
    """Return parsed ROCm telemetry data."""
    data = parse_rocm_smi()
    if 'error' in data:
        return jsonify(data), 500
    return jsonify(data)


@app.route('/api/rocm/raw')
def get_raw_rocm():
    """Return raw rocm-smi output (for debugging)."""
    try:
        result = subprocess.run(
            ['rocm-smi'], capture_output=True, text=True, timeout=10
        )
        return {'output': result.stdout, 'error': result.stderr if result.returncode != 0 else None}
    except Exception as e:
        return {'error': str(e)}


@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok', 'service': 'rocm-agent'})


if __name__ == '__main__':
    host = '0.0.0.0'  # Accept connections from LAN
    port = 5900
    print(f'ROCM Agent running on http://{host}:{port}')
    app.run(host=host, port=port, debug=False)
```

**Step 3: Create launcher script (`start_agent.bat`)**

```bat
@echo off
echo Starting ROCm Telemetry Agent...
cd /d "%~dp0"
python rocm_agent.py
pause
```

**Step 4: Test the agent (run on AI PC)**

```bash
cd rocm-monitor-agent
python rocm_agent.py &
curl http://127.0.0.1:5900/api/rocm
curl http://127.0.0.1:5900/health
```

Expected output: JSON with GPU temperature, memory, power, clock speeds.

---

## Task 2: Set Up the Electron App Skeleton

**Objective:** Create the Electron project structure with proper dependencies.

**Files:**
- Create: `rocm-monitor/package.json`
- Create: `rocm-monitor/main.js`
- Create: `rocm-monitor/preload.js`
- Create: `rocm-monitor/build/icon.png` (placeholder)

**Step 1: Create `package.json`**

```json
{
  "name": "rocm-monitor",
  "version": "1.0.0",
  "description": "AMD ROCm GPU telemetry monitor for Windows",
  "main": "main.js",
  "scripts": {
    "start": "electron .",
    "build:win": "electron-builder --win --x64"
  },
  "build": {
    "appId": "com.pedro.rocm-monitor",
    "productName": "ROCM Monitor",
    "win": {
      "target": ["nsis"],
      "icon": "build/icon.ico"
    },
    "nsis": {
      "oneClick": false,
      "allowToChangeInstallationDirectory": true
    }
  },
  "dependencies": {
    "electron": "^33.0.0"
  },
  "devDependencies": {
    "electron-builder": "^25.0.0"
  }
}
```

**Step 2: Create `main.js`**

```javascript
const { app, BrowserWindow, Tray, Menu, ipcMain, dialog, nativeImage } = require('electron');
const path = require('path');
const isDev = !app.isPackaged;

let mainWindow = null;
let tray = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 900,
    height: 700,
    minWidth: 700,
    minHeight: 500,
    fullscreenable: false,
    alwaysOnTop: false,
    transparent: false,
    backgroundColor: '#1a1a2e',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  // CSP for local dev
  mainWindow.webContents.on('will-navigate', (event) => {
    event.preventDefault();
  });

  if (isDev) {
    mainWindow.loadFile('index.html');
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile('index.html');
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

function createTray() {
  const iconPath = path.join(__dirname, 'build', 'tray.png');
  try {
    const trayIcon = nativeImage.createFromPath(iconPath);
    if (!trayIcon.isEmpty()) {
      tray = new Tray(trayIcon);
    } else {
      tray = new Tray(path.join(__dirname, 'build', 'icon.ico'));
    }
  } catch (e) {
    tray = new Tray(path.join(__dirname, 'build', 'icon.ico'));
  }

  const contextMenu = Menu.buildFromTemplate([
    { label: 'Show ROCM Monitor', click: () => {
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.show();
        if (mainWindow.isMinimized()) mainWindow.restore();
        mainWindow.focus();
      }
    }},
    { type: 'separator' },
    { label: 'Settings', click: () => openSettings() },
    { type: 'separator' },
    { label: 'Quit', click: () => app.quit() },
  ]);

  tray.setToolTip('ROCM Monitor');
  tray.setContextMenu(contextMenu);

  tray.on('click', () => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      if (mainWindow.isVisible()) {
        mainWindow.hide();
      } else {
        mainWindow.show();
        mainWindow.focus();
      }
    }
  });
}

function openSettings() {
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send('open-settings');
  }
}

// IPC: Save settings
ipcMain.handle('save-settings', async (_event, settings) => {
  const fs = require('fs');
  const configPath = path.join(app.getPath('userData'), 'config.json');
  fs.writeFileSync(configPath, JSON.stringify(settings, null, 2));
  return { ok: true };
});

// IPC: Load settings
ipcMain.handle('load-settings', async () => {
  const fs = require('fs');
  const configPath = path.join(app.getPath('userData'), 'config.json');
  if (fs.existsSync(configPath)) {
    return JSON.parse(fs.readFileSync(configPath, 'utf-8'));
  }
  return { host: '192.168.90.171', port: 5900, refreshInterval: 2000 };
});

app.whenReady().then(() => {
  createWindow();
  createTray();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  if (tray) {
    try { tray.destroy(); } catch (e) {}
    tray = null;
  }
  if (mainWindow) {
    try { mainWindow.destroy(); } catch (e) {}
    mainWindow = null;
  }
});
```

**Step 3: Create `preload.js`**

```javascript
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  saveSettings: (settings) => ipcRenderer.invoke('save-settings', settings),
  loadSettings: () => ipcRenderer.invoke('load-settings'),
  onOpenSettings: (callback) => ipcRenderer.on('open-settings', callback),
});
```

**Step 4: Install dependencies**

```bash
cd rocm-monitor
npm install
```

---

## Task 3: Build the Dashboard UI

**Objective:** Create the main dashboard HTML/CSS/JS with real-time GPU telemetry display.

**Files:**
- Create: `rocm-monitor/index.html`
- Create: `rocm-monitor/renderer.js`
- Create: `rocm-monitor/styles.css`

**Step 1: Create `index.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ROCM Monitor</title>
  <link rel="stylesheet" href="styles.css">
  <meta http-equiv="Content-Security-Policy"
    content="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self' http://localhost:* http://127.0.0.1:* http://*:*;">
</head>
<body>
  <div id="app">
    <!-- Header -->
    <header class="header">
      <div class="header-left">
        <h1>ROCM Monitor</h1>
        <span id="connection-status" class="status-badge disconnected">Disconnected</span>
      </div>
      <div class="header-right">
        <button id="btn-settings" class="btn-icon" title="Settings">⚙️</button>
        <button id="btn-minimize" class="btn-icon" title="Minimize">─</button>
        <button id="btn-close" class="btn-icon" title="Close">×</button>
      </div>
    </header>

    <!-- Settings Modal -->
    <div id="settings-modal" class="modal hidden">
      <div class="modal-content">
        <h2>Settings</h2>
        <div class="form-group">
          <label for="agent-host">AI PC Host</label>
          <input type="text" id="agent-host" placeholder="192.168.90.171">
        </div>
        <div class="form-group">
          <label for="agent-port">Port</label>
          <input type="number" id="agent-port" placeholder="5900">
        </div>
        <div class="form-group">
          <label for="refresh-interval">Refresh Interval (seconds)</label>
          <input type="number" id="refresh-interval" placeholder="2" min="1" max="60">
        </div>
        <div class="form-actions">
          <button id="btn-test-connection" class="btn btn-secondary">Test Connection</button>
          <button id="btn-save-settings" class="btn btn-primary">Save</button>
          <button id="btn-cancel-settings" class="btn btn-secondary">Cancel</button>
        </div>
        <div id="settings-message"></div>
      </div>
    </div>

    <!-- Main Dashboard -->
    <main id="dashboard">
      <div id="gpu-container" class="gpu-grid">
        <!-- GPU cards injected here by renderer.js -->
      </div>

      <!-- Bottom bar: stats summary -->
      <footer class="footer">
        <span id="last-update">Waiting for data...</span>
        <span id="poll-count">Polls: 0</span>
      </footer>
    </main>
  </div>

  <script src="renderer.js"></script>
</body>
</html>
```

**Step 2: Create `styles.css`**

```css
:root {
  --bg-primary: #1a1a2e;
  --bg-secondary: #16213e;
  --bg-card: #0f3460;
  --text-primary: #e4e4e4;
  --text-secondary: #a0a0b0;
  --accent: #e94560;
  --accent-green: #00d2ff;
  --accent-yellow: #f0c040;
  --accent-red: #ff4444;
  --border: rgba(255,255,255,0.1);
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  background: var(--bg-primary);
  color: var(--text-primary);
  overflow: hidden;
  height: 100vh;
}

#app {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

/* Header */
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border);
}

.header-left h1 {
  font-size: 1.2rem;
  font-weight: 600;
  letter-spacing: 1px;
}

.status-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 0.75rem;
  margin-left: 12px;
  vertical-align: middle;
}

.status-badge.connected { background: #0a3d0a; color: #4ade80; }
.status-badge.disconnected { background: #3d0a0a; color: #f87171; }
.status-badge.connecting { background: #3d3d0a; color: #fbbf24; }

.header-right { display: flex; gap: 8px; }

.btn-icon {
  background: transparent;
  border: 1px solid var(--border);
  color: var(--text-secondary);
  width: 32px;
  height: 32px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-icon:hover { background: rgba(255,255,255,0.1); color: var(--text-primary); }

/* Dashboard */
#dashboard {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.gpu-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(380px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

/* GPU Card */
.gpu-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px;
  transition: border-color 0.3s;
}

.gpu-card:hover { border-color: var(--accent); }

.gpu-card h2 {
  font-size: 1rem;
  margin-bottom: 16px;
  color: var(--accent-green);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.gpu-card .gpu-model { font-size: 0.8rem; color: var(--text-secondary); }

.metric-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid var(--border);
}

.metric-row:last-child { border-bottom: none; }

.metric-label {
  color: var(--text-secondary);
  font-size: 0.85rem;
}

.metric-value {
  font-size: 1.1rem;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.metric-value.warning { color: var(--accent-yellow); }
.metric-value.danger { color: var(--accent-red); }

/* Progress bar */
.progress-bar {
  width: 100%;
  height: 6px;
  background: rgba(255,255,255,0.1);
  border-radius: 3px;
  overflow: hidden;
  margin-top: 4px;
}

.progress-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.5s ease, background-color 0.3s;
}

.progress-bar-fill.green { background: var(--accent-green); }
.progress-bar-fill.yellow { background: var(--accent-yellow); }
.progress-bar-fill.red { background: var(--accent-red); }

/* Footer */
.footer {
  display: flex;
  justify-content: space-between;
  padding: 12px 20px;
  background: var(--bg-secondary);
  border-top: 1px solid var(--border);
  font-size: 0.8rem;
  color: var(--text-secondary);
}

/* Modal */
.modal {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal.hidden { display: none; }

.modal-content {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 24px;
  width: 400px;
  max-width: 90vw;
}

.modal-content h2 { margin-bottom: 20px; }

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.form-group input {
  width: 100%;
  padding: 8px 12px;
  background: var(--bg-primary);
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 0.9rem;
}

.form-group input:focus {
  outline: none;
  border-color: var(--accent-green);
}

.form-actions {
  display: flex;
  gap: 8px;
  margin-top: 20px;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85rem;
  transition: background 0.2s;
}

.btn-primary { background: var(--accent-green); color: #000; }
.btn-primary:hover { background: #00b8e6; }
.btn-secondary { background: rgba(255,255,255,0.1); color: var(--text-primary); }
.btn-secondary:hover { background: rgba(255,255,255,0.2); }

#settings-message {
  margin-top: 12px;
  font-size: 0.85rem;
  min-height: 20px;
}

/* No data state */
.no-data {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-secondary);
}

.no-data p { font-size: 1.1rem; margin-bottom: 8px; }
.no-data .hint { font-size: 0.85rem; opacity: 0.7; }

/* Animations */
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.status-badge.connecting { animation: pulse 1s infinite; }
```

**Step 3: Create `renderer.js`**

```javascript
// ROCM Monitor — Dashboard Renderer

const API_BASE = ''; // Will be set from settings
let refreshInterval = 2000;
let pollTimer = null;
let pollCount = 0;
let settings = { host: '192.168.90.171', port: 5900, refreshInterval: 2000 };

// DOM Elements
const elDashboard = document.getElementById('dashboard');
const elGpuContainer = document.getElementById('gpu-container');
const elStatus = document.getElementById('connection-status');
const elLastUpdate = document.getElementById('last-update');
const elPollCount = document.getElementById('poll-count');
const elSettingsModal = document.getElementById('settings-modal');

// Buttons
document.getElementById('btn-settings').addEventListener('click', openSettings);
document.getElementById('btn-cancel-settings').addEventListener('click', closeSettings);
document.getElementById('btn-save-settings').addEventListener('click', saveSettings);
document.getElementById('btn-test-connection').addEventListener('click', testConnection);
document.getElementById('btn-minimize').addEventListener('click', () => {
  if (window.electronAPI) window.electronAPI.minimize?.();
});
document.getElementById('btn-close').addEventListener('click', () => {
  if (window.electronAPI) window.electronAPI.hide?.();
});

// Electron IPC handlers
if (window.electronAPI) {
  window.electronAPI.onOpenSettings?.(() => openSettings());
}

async function loadSettings() {
  if (window.electronAPI) {
    settings = await window.electronAPI.loadSettings();
  }
  refreshInterval = settings.refreshInterval || 2000;
  startPolling();
}

function getApiUrl() {
  return `http://${settings.host}:${settings.port}/api/rocm`;
}

async function fetchTelemetry() {
  try {
    elStatus.className = 'status-badge connecting';
    elStatus.textContent = 'Connecting...';

    const resp = await fetch(getApiUrl(), { signal: AbortSignal.timeout(5000) });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

    const data = await resp.json();
    pollCount++;

    if (data.error) {
      throw new Error(data.error);
    }

    elStatus.className = 'status-badge connected';
    elStatus.textContent = 'Connected';
    renderDashboard(data);
    elLastUpdate.textContent = `Last update: ${new Date().toLocaleTimeString()}`;
    elPollCount.textContent = `Polls: ${pollCount}`;

  } catch (err) {
    elStatus.className = 'status-badge disconnected';
    elStatus.textContent = `Error: ${err.message}`;
    console.error('Telemetry fetch failed:', err);
  }
}

function renderDashboard(data) {
  if (!data.gpus || data.gpus.length === 0) {
    elGpuContainer.innerHTML = `
      <div class="no-data" style="grid-column: 1 / -1;">
        <p>No GPU data received</p>
        <span class="hint">Ensure the ROCm agent is running on the AI PC</span>
      </div>`;
    return;
  }

  elGpuContainer.innerHTML = data.gpus.map((gpu, idx) => {
    const temp = parseFloat(gpu.temperature || gpu.THM || gpu.hot || 0);
    const memUsed = parseMemory(gpu.memory_usage || gpu.MEM || gpu.vram_usage || '0 MB');
    const memTotal = parseMemory(gpu.memory_total || gpu.MEM_TOTAL || '0 MB');
    const memPercent = memTotal > 0 ? (memUsed / memTotal * 100) : 0;
    const power = parseFloat(gpu.power_draw || gpu.PWR || 0);
    const fan = parseFloat(gpu.fan_speed || gpu.FAN || 0);

    return `
      <div class="gpu-card">
        <h2>
          <span>GPU ${gpu.gpu ?? idx}</span>
          <span class="gpu-model">${gpu.model || 'AMD GPU'}</span>
        </h2>

        <!-- Temperature -->
        <div class="metric-row">
          <span class="metric-label">Temperature</span>
          <span class="metric-value ${temp > 85 ? 'danger' : temp > 70 ? 'warning' : ''}">
            ${temp.toFixed(1)}°C
          </span>
        </div>

        <!-- Memory Usage -->
        <div class="metric-row" style="flex-direction: column; align-items: stretch;">
          <div style="display: flex; justify-content: space-between;">
            <span class="metric-label">VRAM</span>
            <span class="metric-value">${memUsed.toFixed(0)} / ${memTotal.toFixed(0)} MB (${memPercent.toFixed(1)}%)</span>
          </div>
          <div class="progress-bar">
            <div class="progress-bar-fill ${memPercent > 90 ? 'red' : memPercent > 70 ? 'yellow' : 'green'}"
                 style="width: ${Math.min(memPercent, 100)}%"></div>
          </div>
        </div>

        <!-- Power Draw -->
        <div class="metric-row">
          <span class="metric-label">Power Draw</span>
          <span class="metric-value ${power > 300 ? 'warning' : ''}">
            ${power.toFixed(1)} W
          </span>
        </div>

        <!-- Fan Speed -->
        <div class="metric-row">
          <span class="metric-label">Fan Speed</span>
          <span class="metric-value">
            ${fan > 0 ? fan.toFixed(0) + '%' : 'N/A'}
          </span>
        </div>

        <!-- Clock Speed -->
        <div class="metric-row">
          <span class="metric-label">Clock</span>
          <span class="metric-value">${gpu.sclk || gpu.CLK || 'N/A'}</span>
        </div>

        <!-- GPU Utilization -->
        <div class="metric-row">
          <span class="metric-label">GPU Use</span>
          <span class="metric-value ${parseFloat(gpu.gpu_use || 0) > 90 ? 'warning' : ''}">
            ${gpu.gpu_use || 'N/A'}%
          </span>
        </div>
      </div>`;
  }).join('');
}

function parseMemory(str) {
  if (!str) return 0;
  str = String(str).trim().toUpperCase();
  const num = parseFloat(str.replace(/[^0-9.]/g, ''));
  if (isNaN(num)) return 0;
  // If value is in GB, convert to MB
  if (str.includes('GB')) return num * 1024;
  return num;
}

function startPolling() {
  if (pollTimer) clearInterval(pollTimer);
  fetchTelemetry(); // Immediate first fetch
  pollTimer = setInterval(fetchTelemetry, refreshInterval);
}

// Settings Modal
function openSettings() {
  document.getElementById('agent-host').value = settings.host;
  document.getElementById('agent-port').value = settings.port;
  document.getElementById('refresh-interval').value = settings.refreshInterval / 1000;
  document.getElementById('settings-message').textContent = '';
  elSettingsModal.classList.remove('hidden');
}

function closeSettings() {
  elSettingsModal.classList.add('hidden');
}

async function testConnection() {
  const host = document.getElementById('agent-host').value.trim();
  const port = document.getElementById('agent-port').value.trim();
  const msgEl = document.getElementById('settings-message');

  if (!host || !port) {
    msgEl.textContent = 'Please enter both host and port.';
    msgEl.style.color = '#f87171';
    return;
  }

  msgEl.textContent = 'Testing connection...';
  msgEl.style.color = '#fbbf24';

  try {
    const resp = await fetch(`http://${host}:${port}/health`, { signal: AbortSignal.timeout(3000) });
    if (resp.ok) {
      msgEl.textContent = '✓ Connection successful!';
      msgEl.style.color = '#4ade80';
    } else {
      msgEl.textContent = `✗ HTTP ${resp.status}`;
      msgEl.style.color = '#f87171';
    }
  } catch (err) {
    msgEl.textContent = `✗ Connection failed: ${err.message}`;
    msgEl.style.color = '#f87171';
  }
}

async function saveSettings() {
  const newSettings = {
    host: document.getElementById('agent-host').value.trim(),
    port: parseInt(document.getElementById('agent-port').value.trim()) || 5900,
    refreshInterval: (parseInt(document.getElementById('refresh-interval').value.trim()) || 2) * 1000,
  };

  if (window.electronAPI) {
    await window.electronAPI.saveSettings(newSettings);
  }

  settings = newSettings;
  closeSettings();
  startPolling();
}

// Initialize
loadSettings();
```

---

## Task 4: Add Tray Icon and Build Support Files

**Objective:** Create placeholder icons and the Windows launcher.

**Files:**
- Create: `rocm-monitor/build/icon.ico` (16x16 or 32x32 ICO)
- Create: `rocm-monitor/build/tray.png` (16x16 PNG)
- Create: `rocm-monitor/start.bat`

**Step 1: Create launcher (`start.bat`)**

```bat
@echo off
cd /d "%~dp0"
echo Starting ROCM Monitor...
node .
pause
```

**Step 2: Create a simple icon**

Sir, for the icon I'll generate a minimal 32x32 ICO file programmatically. Let me create that.

---

## Task 5: Package and Distribute

**Objective:** Build a standalone Windows installer.

**Steps:**
1. Install `electron-builder` dev dependency
2. Run `npm run build:win` to produce NSIS installer
3. Test the installer on Windows

---

## Task 6: Documentation

**Objective:** Create README with setup instructions for both components.

**Files:**
- Create: `rocm-monitor/README.md`
- Create: `rocm-monitor-agent/README.md`

---

## Verification Checklist

- [ ] Agent runs on AI PC and `/api/rocm` returns valid JSON
- [ ] Agent `/health` endpoint responds with `{"status": "ok"}`
- [ ] Electron app starts without errors
- [ ] Dashboard displays GPU data from remote agent
- [ ] Settings modal allows changing host/port/interval
- [ ] Connection test works (tests `/health` endpoint)
- [ ] System tray icon appears and responds to clicks
- [ ] Minimize hides window, tray click restores it
- [ ] Data refreshes at configured interval
- [ ] Temperature/memory/power values colour-coded correctly
- [ ] Packaged .exe runs standalone

---

## Notes & Considerations

1. **rocm-smi output parsing** is the trickiest part — ROCm versions vary in their output format. The agent includes a robust fallback parser. We'll need to test against the actual AI PC output and adjust field mappings.

2. **Network**: The AI PC must be reachable from Pedro's desktop on port 5900. Firewall rules may need adjustment.

3. **Auto-start**: Can add the agent to the AI PC's startup scripts (`/etc/systemd/system/rocm-agent.service` or Windows equivalent) for always-on availability.

4. **Alerts** (future): Could add temperature/power thresholds with desktop notifications via Electron's `new Notification()`.

5. **Multiple GPUs**: Grid layout handles any number of GPUs automatically.
