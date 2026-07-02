# Multi-Source GPU Monitoring — Feasibility Analysis

## Current Hardware Inventory

| Machine | GPU | Interface | Network Reachable? |
|---------|-----|-----------|-------------------|
| AI PC (192.168.90.171) | AMD Radeon (ROCm) | `rocm-smi` | Yes, LAN |
| Desktop (localhost) | NVIDIA RTX 4090 | `nvidia-smi` | N/A — local |

## Approach: Unified Dashboard with Multiple Sources

Instead of a single-agent architecture, we use a **source registry** pattern. The Electron app maintains a list of GPU sources, each with its own connection config and data parser.

### Architecture

```
Electron App (Windows Desktop)
├── Source Registry (config.json)
│   ├── Source A: "AI PC" — HTTP → 192.168.90.171:5900 /api/rocm
│   └── Source B: "Desktop 4090" — Local nvidia-smi command
│
├── Unified Data Fetcher
│   ├── fetchROCM(source) → HTTP GET → parse ROCm JSON
│   └── fetchNVIDIA(source) → local nvidia-smi → parse CSV
│
└── Dashboard Renderer
    └── Renders all GPUs from all sources in a single grid
```

### Implementation Strategy

**Option A: Electron-only (recommended)**
- The Electron app has TWO data fetchers built in:
  1. **ROCM fetcher**: HTTP GET to remote agent → parse JSON
  2. **NVIDIA fetcher**: Run `nvidia-smi` via Node.js `child_process.exec()` locally
- Single config file stores all sources
- Dashboard renders all GPUs together, tagged by source
- No extra service needed on the local machine

**Option B: Local NVIDIA agent (parallel to ROCm agent)**
- Build a tiny Flask agent for NVIDIA too (same pattern as ROCm agent)
- Electron app polls both via HTTP
- More uniform but unnecessary complexity for local GPU

**Verdict: Option A.** The local NVIDIA fetcher is trivial — just one `child_process.exec('nvidia-smi --query-gpu=... --format=csv')` call. No extra service needed. For future remote NVIDIA GPUs, the same HTTP pattern used for ROCm works identically.

### Source Registry Format (`config.json`)

```json
{
  "sources": [
    {
      "id": "ai-pc",
      "name": "AI PC",
      "type": "rocm",
      "host": "192.168.90.171",
      "port": 5900,
      "enabled": true
    },
    {
      "id": "desktop-4090",
      "name": "Desktop RTX 4090",
      "type": "nvidia",
      "local": true,
      "enabled": true
    }
  ],
  "refreshInterval": 2000
}
```

### Dashboard Changes

- Each GPU card gets a **source tag** (e.g. "AI PC" or "Desktop") in small grey text
- Cards from different sources are visually distinguished by a subtle border accent colour:
  - ROCm cards: cyan accent (`#00d2ff`)
  - NVIDIA cards: green accent (`#76b900` — NVIDIA green)
- Source toggle buttons in the header to filter by source

### New Settings UI

The settings modal expands to a **Sources tab** where you can:
- Add new sources (HTTP/ROCm or local NVIDIA)
- Edit host/port for remote sources
- Toggle individual sources on/off
- Reorder sources

### Files Modified vs Created

**Modified from original plan:**
- `package.json` — add `electron` (already there), no new deps needed
- `main.js` — load source registry from config
- `preload.js` — expose `saveSources`, `loadSources`, `getLocalNvidiaData` IPC
- `index.html` — add source filter buttons, extend settings modal with Sources tab
- `renderer.js` — unified fetcher, multi-source rendering, source filtering
- `styles.css` — source accent colours, filter button styles

**New files:**
- `rocm-monitor/src/nvidia-fetcher.js` — local nvidia-smi parsing (Node.js)
- `rocm-monitor/src/rocm-fetcher.js` — HTTP ROCm fetcher
- `rocm-monitor/src/source-registry.js` — config management

**Unchanged from original plan:**
- `rocm-monitor-agent/` — identical, no changes needed

### Future-Proofing

This architecture supports adding more sources trivially:
- **Remote NVIDIA GPU**: Add a source with `type: "nvidia-http"`, same HTTP pattern as ROCm
- **More AMD GPUs on AI PC**: Already supported (agent returns array)
- **Another remote machine**: Just add another HTTP source in config
- **Intel Arc / other**: Add new fetcher type, same dashboard

### Complexity Impact

- **Original plan**: ~10 files, ~2 hours
- **With multi-source**: ~13 files, ~3 hours
- **Net cost increase**: +1 hour for significant UX value
