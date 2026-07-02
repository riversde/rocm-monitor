/**
 * ROCm GPU data fetcher — HTTP GET to remote agent.
 */

async function fetchROCM(source) {
  try {
    const url = `http://${source.host}:${source.port}/api/rocm`;
    const resp = await fetch(url, { signal: AbortSignal.timeout(5000) });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

    const data = await resp.json();
    if (data.error) throw new Error(data.error);

    return {
      sourceId: source.id,
      sourceName: source.name,
      sourceType: 'rocm',
      gpus: data.gpus || [],
      timestamp: data.timestamp || new Date().toISOString(),
    };
  } catch (err) {
    return { sourceId: source.id, sourceName: source.name, error: err.message };
  }
}

module.exports = { fetchROCM };
