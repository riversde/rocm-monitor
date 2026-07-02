#!/usr/bin/env python3
"""Intel XPU Manager telemetry agent — runs on Intel GPU systems, exposes GPU data as JSON.

Uses xpu-smi (Intel XPU Manager) for hardware telemetry.
Compatible with Intel Arc Pro Series and Data Center GPUs.
Linux only (xpu-smi is Linux-only per Intel docs).

Usage:
    python3 xpu_agent.py [--port PORT]

Environment:
    PORT  — HTTP port (default: 5901)
"""

import json
import subprocess
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = int(__import__("os").environ.get("PORT", "5901"))


def run_cmd(cmd, timeout=10):
    """Run a shell command and return (stdout, stderr, returncode)."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "", "Command timed out", 124


def discover_gpus():
    """Discover all Intel GPUs and return list of device info dicts."""
    raw, _, rc = run_cmd("xpu-smi --list-gpus")
    if rc != 0 or not raw:
        return []

    gpus = []
    for line in raw.strip().split("\n"):
        parts = line.split()
        if len(parts) >= 3:
            try:
                idx = int(parts[0])
                gpu_id = parts[1]
                name = " ".join(parts[2:])
                gpus.append({"index": idx, "device_id": gpu_id, "name": name})
            except ValueError:
                continue
    return gpus


def query_gpu_fields(device_id, fields):
    """Query specific fields from a GPU via xpu-smi --query-gpu."""
    cmd = f"xpu-smi --query-gpu={fields} --id {device_id} -j 2>&1"
    raw, _, rc = run_cmd(cmd)
    if rc != 0 or not raw:
        return {}
    try:
        data = json.loads(raw)
        if isinstance(data, list) and len(data) > 0:
            return data[0]
        return data
    except json.JSONDecodeError:
        return {}


def get_gpu_stats(device_id, include_eu=False, include_ras=False):
    """Get comprehensive stats for a GPU via xpu-smi stats -j.

    Args:
        device_id: GPU device ID.
        include_eu: Include EU array metrics (requires -e flag).
        include_ras: Include RAS error counters (requires -r flag).
    """
    cmd = f"xpu-smi stats --device {device_id} -j"
    if include_eu:
        cmd += " -e"
    if include_ras:
        cmd += " -r"
    raw, _, rc = run_cmd(f"{cmd} 2>&1")
    if rc != 0 or not raw:
        return {}
    try:
        data = json.loads(raw)
        # xpu-smi stats returns a list of device stats
        if isinstance(data, list) and len(data) > 0:
            return data[0]
        return data
    except json.JSONDecodeError:
        return {}


def parse_xpu_gpu(device_info):
    """Parse xpu-smi data into our unified GPU format."""
    idx = device_info["index"]

    # Get identity info
    identity = query_gpu_fields(
        device_info["device_id"],
        "name,serial,driver_version,vbios_version,pci.bus_id,pci.device_id"
    )

    # Get stats (comprehensive metrics, including EU arrays and RAS errors)
    stats = get_gpu_stats(device_info["device_id"], include_eu=True, include_ras=True)

    # Parse temperature
    temp = 0
    mem_temp = 0
    hotspot_temp = None
    if "temperature" in stats:
        t = stats["temperature"]
        temp = t.get("gpu", 0) or t.get("gpu_celsius", 0) or 0
        mem_temp = t.get("memory", 0) or t.get("memory_celsius", 0) or 0

    # Parse power
    power_draw = 0
    power_limit = 0
    if "power" in stats:
        p = stats["power"]
        power_draw = p.get("draw", 0) or p.get("average", 0) or 0
        power_limit = p.get("limit", 0) or p.get("max", 0) or 0

    # Parse memory
    mem_used = 0
    mem_total = 0
    mem_free = 0
    if "memory" in stats:
        m = stats["memory"]
        mem_total = m.get("total", 0) or m.get("total_mib", 0) or 0
        mem_used = m.get("used", 0) or m.get("used_mib", 0) or 0
        mem_free = m.get("free", 0) or m.get("free_mib", 0) or 0

    # Parse utilization
    gpu_util = 0
    if "utilization" in stats:
        u = stats["utilization"]
        gpu_util = u.get("gpu", 0) or u.get("total", 0) or 0

    # Parse fan
    fan_speed = 0
    fan_rpm = None
    if "fan" in stats:
        fans = stats["fan"]
        if isinstance(fans, list):
            fan_speed = fans[0].get("speed_percent", 0) if fans else 0
        elif isinstance(fans, dict):
            fan_speed = fans.get("speed_percent", 0) or fans.get("speed", 0) or 0

    # Parse clocks
    sclk = None
    mclk = None
    if "clock" in stats:
        c = stats["clock"]
        sclk = c.get("graphics", 0) or c.get("current_graphics_mhz", 0) or None
        mclk = c.get("media", 0) or c.get("current_media_mhz", 0) or None

    # Parse EU array (Intel-specific)
    eu_active = None
    eu_stall = None
    eu_idle = None
    if "eu_array" in stats:
        eu = stats["eu_array"]
        eu_active = eu.get("active", 0) or eu.get("gpu_eu_utilization", 0) or None
        eu_stall = eu.get("stall", 0) or None
        eu_idle = eu.get("idle", 0) or None

    # Parse PCIe
    pcie_tx = 0
    pcie_rx = 0
    if "pcie" in stats:
        p = stats["pcie"]
        pcie_tx = p.get("tx_kbs", 0) or p.get("write_kbs", 0) or 0
        pcie_rx = p.get("rx_kbs", 0) or p.get("read_kbs", 0) or 0

    # Parse memory bandwidth
    mem_read_bw = 0
    mem_write_bw = 0
    if "memory_bandwidth" in stats:
        bw = stats["memory_bandwidth"]
        mem_read_bw = bw.get("read_kbs", 0) or 0
        mem_write_bw = bw.get("write_kbs", 0) or 0

    # Calculate VRAM percentage
    vram_percent = 0
    if mem_total > 0:
        vram_percent = (mem_used / mem_total) * 100

    return {
        "device_id": device_info["device_id"],
        "index": idx,
        "name": identity.get("name", device_info.get("name", f"Intel GPU {idx}")),
        "serial": identity.get("serial", ""),
        "driver_version": identity.get("driver_version", ""),
        "vbios_version": identity.get("vbios_version", ""),
        "pci_bus_id": identity.get("pci.bus_id", ""),
        "pci_device_id": identity.get("pci.device_id", ""),
        "temperature": temp,
        "mem_temp": mem_temp,
        "hotspot_temp": hotspot_temp,
        "power_draw": power_draw,
        "power_limit": power_limit,
        "memory_used": round(mem_used, 1),
        "memory_total": round(mem_total, 1),
        "memory_free": round(mem_free, 1),
        "vram_percent": round(vram_percent, 2),
        "gpu_use": gpu_util,
        "fan_speed": fan_speed,
        "fan_rpm": fan_rpm,
        "sclk": sclk,
        "mclk": mclk,
        "eu_active": eu_active,
        "eu_stall": eu_stall,
        "eu_idle": eu_idle,
        "pcie_tx": pcie_tx,
        "pcie_rx": pcie_rx,
        "mem_read_bw": mem_read_bw,
        "mem_write_bw": mem_write_bw,
    }


def get_all_gpus():
    """Get all GPUs in unified format."""
    devices = discover_gpus()
    if not devices:
        # Fallback: try xpu-smi discovery for each potential device
        for i in range(4):  # Check up to 4 devices
            raw, _, rc = run_cmd(f"xpu-smi --query-gpu=name --id {i} -j 2>&1")
            if rc == 0 and raw:
                try:
                    data = json.loads(raw)
                    if isinstance(data, list) and len(data) > 0 and data[0].get("name"):
                        devices.append({"index": i, "device_id": str(i), "name": data[0]["name"]})
                except json.JSONDecodeError:
                    pass

    return [parse_xpu_gpu(d) for d in devices]


class XPUHandler(BaseHTTPRequestHandler):
    """HTTP handler for XPU telemetry API."""

    def log_message(self, format, *args):
        """Suppress default logging to reduce noise."""
        pass

    def do_GET(self):
        if self.path == "/api/xpu" or self.path == "/api/xpu/":
            gpus = get_all_gpus()
            response = {
                "source": "intel-xpu",
                "tool": "xpu-smi",
                "gpus": gpus,
                "gpu_count": len(gpus),
            }
            self._send_json(200, response)

        elif self.path == "/api/xpu/raw":
            devices = discover_gpus()
            raw_data = {}
            for d in devices:
                raw_data[d["device_id"]] = {
                    "identity": query_gpu_fields(d["device_id"], "name,serial,driver_version,vbios_version"),
                    "stats": get_gpu_stats(d["device_id"], include_eu=True, include_ras=True),
                }
            self._send_json(200, {"discovered_gpus": devices, "raw_data": raw_data})

        elif self.path == "/health" or self.path == "/health/":
            self._send_json(200, {
                "service": "xpu-monitor-agent",
                "status": "ok",
                "tool": "xpu-smi",
            })

        else:
            self._send_json(404, {"error": "Not found"})

    def _send_json(self, status_code, data):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())


def main():
    print(f"Starting Intel XPU Monitor Agent on port {PORT}...")

    # Quick health check
    _, _, rc = run_cmd("xpu-smi --version 2>&1")
    if rc != 0:
        print("ERROR: xpu-smi not found. Is Intel XPU Manager installed?")
        print("Install: https://github.com/intel/xpumanager")
        sys.exit(1)

    gpus = get_all_gpus()
    print(f"Discovered {len(gpus)} Intel GPU(s):")
    for g in gpus:
        print(f"  GPU {g['index']}: {g['name']} ({g['memory_total']}MB VRAM)")

    server = HTTPServer(("0.0.0.0", PORT), XPUHandler)
    print(f"Serving on http://0.0.0.0:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
