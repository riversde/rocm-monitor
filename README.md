# GPU Monitor for AI Workloads

A native Windows desktop application (Electron) that provides a unified, interactive dashboard for GPU telemetry from multiple sources:

- **AMD ROCm** GPUs via remote HTTP agent (`amd-smi`)
- **NVIDIA** GPUs via `nvidia-smi` (local)
- **Intel XPU** GPUs via remote HTTP agent (`xpu-smi`)

[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-FFDD00?style=flat&logo=buymeacoffee&labelColor=5B5B5B)](https://buymeacoffee.com/riversde)

## Features

- **Unified Dashboard** — all GPU types displayed side by side
- **Draggable Tiles** — reorder GPU cards by dragging the handle
- **Source Filtering** — filter by AMD, NVIDIA, or Intel
- **Dark Navy Theme** — cyan for ROCm, green for NVIDIA, blue for Intel
- **Custom Window Chrome** — frameless window with native controls
- **Configurable Sources** — add/remove HTTP sources via Settings
- **Auto-Polling** — configurable refresh interval (default: 2s)

## Screenshots

![GPU Monitor Dashboard](./screenshots/dashboard.png)

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/riversde/rocm-monitor.git
cd rocm-monitor

# Install dependencies
npm install

# Run the application
npm start
```

### Prerequisites

- Node.js 18+ and npm
- For NVIDIA: `nvidia-smi` available on PATH
- For AMD: Deploy the [rocm-monitor-agent](https://github.com/riversde/rocm-monitor-agent) to a remote Linux machine
- For Intel XPU: Deploy the [rocm-monitor-agent](https://github.com/riversde/rocm-monitor-agent) to a remote Linux machine

## Architecture

```
┌─────────────────────────────────────────────┐
│          GPU Monitor (Electron App)         │
│  ┌──────────┬──────────┬──────────────────┐ │
│  │ AMD ROCm │ NVIDIA   │ Intel XPU        │ │
│  │ HTTP     │ nvidia-  │ HTTP             │ │
│  │ Agent    │ smi      │ Agent            │ │
│  └──────────┴──────────┴──────────────────┘ │
└─────────────────────────────────────────────┘
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
