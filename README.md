# GPU Monitor for AI Workloads

A unified desktop dashboard for multi-source GPU telemetry — AMD ROCm, NVIDIA, and Intel XPU.

## Features

- **Unified Dashboard** — View GPUs from multiple sources in a single grid layout
- **Multi-Source Support** — AMD ROCm (HTTP agent), NVIDIA (local `nvidia-smi`), Intel XPU (HTTP agent)
- **Draggable Cards** — Reorder GPU cards to keep your most important ones visible
- **Source Filtering** — Filter by source with one click
- **Dynamic Source Management** — Add, rename, and enable/disable sources from the settings panel
- **Dark Theme** — Navy/blue theme with colour-coded accent borders per vendor

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Electron App                         │
│  ┌──────────┐    ┌──────────────────────────────────┐   │
│  │ Renderer  │    │          Dashboard UI            │   │
│  │ (HTML/JS) │    │  GPU cards + settings + filters  │   │
│  └─────┬─────┘    └──────────────────────────────────┘   │
│        │                                                │
│  ┌─────▼─────┐    ┌──────────────────────────────────┐   │
│  │  Main     │    │   Local NVIDIA telemetry         │   │
│  │ (Node.js) │───▶│   via nvidia-smi                 │   │
│  └─────┬─────┘    └──────────────────────────────────┘   │
│        │                                                │
│  ┌─────▼─────┐    ┌──────────────────────────────────┐   │
│  │  IPC      │    │   Remote ROCm/XPU telemetry      │   │
│  │ Bridge    │───▶│   via HTTP agent (Flask)         │   │
│  └───────────┘    └──────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### GPU Sources

| Source Type | Protocol | Agent | Platform |
|-------------|----------|-------|----------|
| **ROCm** | HTTP (Flask) | `rocm_agent.py` | Linux (AMD GPUs) |
| **NVIDIA** | Local CLI | Built-in (`nvidia-smi`) | Windows/Linux |
| **Intel XPU** | HTTP (Flask) | `xpu_agent.py` | Linux (Intel Arc/DC) |

## Quick Start

### Prerequisites

- Node.js 18+
- npm
- Electron (bundled via `package.json`)
- For NVIDIA: `nvidia-smi` on PATH (Windows/Linux)
- For AMD ROCm: Python 3 + Flask, plus `amd-smi` tool (Linux)
- For Intel XPU: Python 3 + Flask, plus `xpu-smi` (Intel XPU Manager) (Linux)

### Install & Run

```bash
cd rocm-monitor
npm install
npx electron .
```

### Remote Agent Setup (AMD ROCm)

Deploy the agent to the remote system:

```bash
scp rocm_agent.py user@remote-host:/path/to/agent/
ssh user@remote-host 'cd /path/to/agent && pip3 install flask && python3 rocm_agent.py'
```

The agent listens on port `5900` by default. Configure it in the app's Settings panel.

### Remote Agent Setup (Intel XPU)

Deploy the agent to the Intel GPU system:

```bash
scp xpu_agent.py user@intel-host:/path/to/agent/
ssh user@intel-host 'cd /path/to/agent && pip3 install flask && python3 xpu_agent.py'
```

The agent listens on port `5901` by default. Configure it in the app's Settings panel.

## Configuration

Click ⚙️ **Settings** to:

- Add/remove GPU sources (ROCm, NVIDIA, Intel XPU)
- Rename sources (labels update dynamically on cards)
- Toggle sources on/off
- Adjust polling interval (default: 2s)
- Test connections before saving

## Intel XPU Manager

For Intel GPU support, install [Intel XPU Manager](https://github.com/intel/xpumanager):

```bash
# Linux — follow the official installation guide:
# https://intel.github.io/xpumanager/2.0/index.html
```

The `xpu_agent.py` uses `xpu-smi --query-gpu` and `xpu-smi stats` for telemetry.

## AMD ROCm Agent

The `rocm_agent.py` uses `amd-smi metric --json` for accurate telemetry including:
- VRAM usage (total, used, free, percentage)
- GPU/memory/hotspot temperatures
- Fan speed (RPM and percentage)
- Power draw and limits
- Clock frequencies
- PCIe throughput

## License

MIT
