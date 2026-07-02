# GPU Monitor for AI Workloads

A native Windows desktop application (Electron) that provides a unified, interactive dashboard for GPU telemetry from multiple sources:

- **AMD ROCm** GPUs via `amd-smi` (remote HTTP agent)
- **NVIDIA** GPUs via `nvidia-smi` (local)
- **Intel XPU** GPUs via `xpu-smi` (remote HTTP agent)

[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-FFDD00?style=for-the-badge&logo=buymeacoffee&labelColor=5B5B5B)](https://buymeacoffee.com/riversde)

## Quick Start

```bash
# Install dependencies
npm install

# Run the dashboard
npm start
```

## Architecture

```
┌──────────────────────────────────────────────────────┐
│              GPU Monitor (Electron App)               │
│  ┌───────────┬───────────┬──────────────────────────┐ │
│  │ AMD ROCm  │ NVIDIA    │ Intel XPU                │ │
│  │ HTTP Agent│ nvidia-smi│ HTTP Agent               │ │
│  │ (remote)  │ (local)   │ (remote)                 │ │
│  └───────────┴───────────┴──────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

## Features

- **Unified Dashboard** — all GPU types displayed side by side
- **Draggable Tiles** — reorder GPU cards by dragging the handle
- **Source Filtering** — filter by AMD, NVIDIA, or Intel
- **Dark Navy Theme** — cyan for ROCm, green for NVIDIA, blue for Intel
- **Custom Window Chrome** — frameless window with native controls
- **Configurable Sources** — add/remove HTTP sources via Settings
- **Auto-Polling** — configurable refresh interval (default: 2s)

## Agents (included in `agent/`)

Two Flask HTTP agents that expose GPU telemetry as JSON for the dashboard. Deploy these on remote Linux systems.

### AMD ROCm Agent (`agent/rocm_agent.py`)

```bash
pip install flask
python agent/rocm_agent.py    # listens on 0.0.0.0:5900
```

**Dependencies:** Python 3, Flask, `amd-smi` (AMD System Management Interface)

### Intel XPU Agent (`agent/xpu_agent.py`)

```bash
pip install flask
python agent/xpu_agent.py     # listens on 0.0.0.0:5901
```

**Dependencies:** Python 3, Flask, [Intel XPU Manager](https://github.com/intel/xpumanager) (`xpu-smi`)

> **Note:** Intel XPU Manager (`xpu-smi`) is **Linux-only**. The agent cannot run on Windows. For Windows hosts with Intel GPUs, use a remote Linux machine running this agent and add it as an HTTP source in the Electron dashboard.

### Agent Endpoints (both)

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check — returns `{"status": "ok"}` |
| `GET /api/rocm` or `/api/xpu` | Parsed GPU telemetry JSON |
| `GET /api/rocm/raw` or `/api/xpu/raw` | Raw CLI output for debugging |

### systemd Deployment

Copy `agent/rocm-monitor.service` to `/etc/systemd/system/`, edit the path, then:

```bash
sudo systemctl enable --now rocm-monitor
```

## Configuration

1. Open **Settings** (gear icon in header)
2. **Sources tab** — add HTTP sources for AMD/Intel GPUs
3. **General tab** — adjust refresh interval, always-on-top setting

## Buy Me a Coffee

If you find this tool useful, consider buying me a coffee:

[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-FFDD00?style=for-the-badge&logo=buymeacoffee&labelColor=5B5B5B)](https://buymeacoffee.com/riversde)

## License

MIT
