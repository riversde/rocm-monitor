/**
 * NVIDIA GPU data fetcher — runs nvidia-smi locally via Electron IPC.
 */

async function fetchNVIDIA(source) {
  try {
    const data = await window.electronAPI.runNvidiaSmi();
    if (data.error) throw new Error(data.error);

    // Parse memory strings like "4189 MiB" → MB
    const memUsed = parseMemoryStr(data.memory_used);
    const memTotal = parseMemoryStr(data.memory_total);

    return {
      sourceId: source.id,
      sourceName: source.name,
      sourceType: 'nvidia',
      gpus: [{
        gpu: 0,
        name: data.name || 'NVIDIA GPU',
        model: data.name || 'NVIDIA GPU',
        temperature: data.temperature || 0,
        memory_used: memUsed,
        memory_total: memTotal,
        memory_percent: memTotal > 0 ? (memUsed / memTotal * 100) : 0,
        power_draw: data.power_draw || 0,
        power_limit: data.power_limit || 0,
        clock_gr: data.clock_gr || 'N/A',
        clock_mem: data.clock_mem || 'N/A',
        utilization: data.utilization || 0,
        fan_speed: data.fan_speed || 0,
        driver_version: data.driver_version || '',
      }],
      timestamp: new Date().toISOString(),
    };
  } catch (err) {
    return { sourceId: source.id, sourceName: source.name, error: err.message };
  }
}

function parseMemoryStr(str) {
  if (!str) return 0;
  const num = parseFloat(String(str).replace(/[^0-9.]/g, ''));
  return isNaN(num) ? 0 : num;
}

module.exports = { fetchNVIDIA };
