// Local storage for OASIS: IndexedDB 'oasis' v1 with 'worlds' and 'runs'. No deps. Schema: docs/DATA-PIPELINE.md.
let dbp;
function db() {
  return (dbp ||= new Promise((ok, fail) => {
    const req = indexedDB.open('oasis', 1);
    req.onupgradeneeded = () => {
      const d = req.result;
      if (!d.objectStoreNames.contains('worlds')) d.createObjectStore('worlds', { keyPath: 'id' });
      if (!d.objectStoreNames.contains('runs')) d.createObjectStore('runs', { keyPath: 'id' }).createIndex('worldId', 'worldId');
    };
    req.onsuccess = () => ok(req.result);
    req.onerror = () => fail(req.error);
  }));
}
async function tx(store, mode, fn) {
  const t = (await db()).transaction(store, mode), req = fn(t.objectStore(store));
  return new Promise((ok, fail) => {
    t.oncomplete = () => ok(req?.result);
    t.onerror = t.onabort = () => fail(t.error);
  });
}

export const worldId = (worldSeed, tileKm) => `w${worldSeed}-${tileKm}km`;
export const runId = (wId, scenarioSeed, ts = Date.now()) => `${wId}/s${scenarioSeed}-${ts}`;

export const saveWorld = (w) => tx('worlds', 'readwrite', (s) => s.put(w));
export const saveRun = (r) => tx('runs', 'readwrite', (s) => s.put(r));
export const listWorlds = () => tx('worlds', 'readonly', (s) => s.getAll());
export const listRuns = (wId) => tx('runs', 'readonly', (s) => (wId ? s.index('worldId').getAll(wId) : s.getAll()));
export async function counts() {
  const [worlds, runs] = await Promise.all([tx('worlds', 'readonly', (s) => s.count()), tx('runs', 'readonly', (s) => s.count())]);
  return { worlds, runs };
}
export async function exportAll() {
  const [worlds, runs] = await Promise.all([listWorlds(), listRuns()]);
  const data = { schema: 'oasis.export/1', exported_at: new Date().toISOString(), worlds, runs };
  return new Blob([JSON.stringify(data)], { type: 'application/json' });
}
