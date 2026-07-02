# GPU Monitor for AI Workloads

A native Windows desktop application (Electron) that provides a unified, interactive dashboard for GPU telemetry from multiple sources. Built for AI/ML developers who need real-time visibility into their GPU workloads across AMD, NVIDIA, and Intel hardware.

[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-FFDD00?style=for-the-badge&logo=buymeacoffee&labelColor=5B5B5B)](https://buymeacoffee.com/riversde)

## Screenshots

![GPU Monitor Dashboard](screenshots/dashboard.png)

## Why This Exists

When running AI models, fine-tuning LLMs, or training deep learning networks, GPU utilization is everything. But existing monitoring tools are either web-based (laggy), platform-specific (AMD only, NVIDIA only), or require complex setup. GPU Monitor gives you a **single native desktop window** that shows all your GPUs — local and remote — in one place.

## Features

- **Unified Dashboard** — AMD ROCm, NVIDIA, and Intel XPU GPUs displayed side by side
- **Draggable Tiles** — reorder GPU cards by dragging the handle (⠿) to prioritise what matters most
- **Source Filtering** — filter by vendor with one click
- **Dark Navy Theme** — easy on the eyes during long training sessions; cyan for ROCm, green for NVIDIA, blue for Intel
- **Custom Window Chrome** — frameless window with native minimise/maximise/close controls
- **Configurable Sources** — add/remove HTTP sources via Settings (gear icon)
- **Auto-Polling** — configurable refresh interval (default: 2 seconds)
- **Always-on-Top Mode** — keep the dashboard visible above your IDE

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

### What Gets Monitored

| Metric | AMD ROCm | NVIDIA | Intel XPU |
|--------|----------|--------|-----------|
| GPU Utilization | ✅ `gfx_activity` | ✅ `utilization.gpu` | ✅ `gpu_utilization` |
| Memory Usage | ✅ Total/Used | ✅ Total/Used | ✅ Total/Used |
| Temperature | ✅ | ✅ | ✅ |
| Power Draw | ✅ | ✅ | ✅ |
| Fan Speed | ✅ (PWM→%) | ✅ | ✅ |
| PCIe Throughput | ✅ TX/RX | — | ✅ TX/RX |
| Memory Bandwidth | ✅ | — | ✅ |
| EU Array Utilization | — | — | ✅ Per-tile breakdown |
| RAS Error Counters | — | — | ✅ |

## Quick Start

```bash
# Install dependencies
npm install

# Run the dashboard
npm start
```

### Prerequisites

- **Node.js 18+** and npm
- **NVIDIA GPUs**: `nvidia-smi` must be on PATH (NVIDIA driver installed)
- **AMD/Intel GPUs**: Deploy the included agents to a remote Linux machine (see below)

## Agents (`agent/`)

Two Flask HTTP agents expose GPU telemetry as JSON. Deploy these on remote Linux systems, then add them as HTTP sources in the Electron dashboard.

### AMD ROCm Agent (`agent/rocm_agent.py`)

Exposes comprehensive telemetry from AMD GPUs via `amd-smi`.

```bash
pip install flask
python agent/rocm_agent.py    # listens on 0.0.0.0:5900
```

**Dependencies:** Python 3, Flask, `amd-smi` (AMD ROCm system management interface)

### Intel XPU Agent (`agent/xpu_agent.py`)

Exposes telemetry from Intel GPUs via `xpu-smi`, including EU array utilization, PCIe throughput, memory bandwidth, and RAS error counters.

```bash
pip install flask
python agent/xpu_agent.py     # listens on 0.0.0.0:5901
```

**Dependencies:** Python 3, Flask, [Intel XPU Manager](https://github.com/intel/xpumanager) (`xpu-smi`)

> **Note:** Intel XPU Manager (`xpu-smi`) is **Linux-only**. For Windows hosts with Intel GPUs, deploy this agent on a remote Linux machine.

### Agent Endpoints (both agents)

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check — returns `{"status": "ok"}` |
| `GET /api/rocm` or `/api/xpu` | Parsed GPU telemetry JSON |
| `GET /api/rocm/raw` or `/api/xpu/raw` | Raw CLI output for debugging |

### systemd Deployment (recommended)

Copy the service file and start the agent:

```bash
sudo cp agent/rocm-monitor.service /etc/systemd/system/
sudo systemctl enable --now rocm-monitor
```

## Configuration

1. Open **Settings** (gear icon in header)
2. **Sources tab** — add HTTP sources for AMD/Intel GPUs with host, port, and display name
3. **General tab** — adjust refresh interval (1–60 seconds), toggle always-on-top
4. **Test Connection** — verify each source returns valid GPU data

## Buy Me a Coffee

If this tool has saved you time or helped debug a GPU issue, consider buying me a coffee:

[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-FFDD00?style=for-the-badge&logo=buymeacoffee&labelColor=5B5B5B)](https://buymeacoffee.com/riversde)

A GitHub Sponsors button also appears on the repository page — click it for a one-time or recurring contribution.

## License

MIT
