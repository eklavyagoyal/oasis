/** The only input boundary. Dropped JavaScript is parsed as JSON, never executed. */
const MAX_SAMPLES = 2_000_000;
const finite = (v) => typeof v === "number" && Number.isFinite(v);
const fail = (message) => {
  throw new Error(`Invalid scenario: ${message}`);
};
const numeric = (values, name, nullable = false) => {
  if (
    !Array.isArray(values) ||
    values.length > MAX_SAMPLES ||
    values.some((v) => !(nullable && v === null) && !finite(v))
  )
    fail(`${name} must be a finite number array`);
};
function columns(record, names, name, nullable = []) {
  if (!record || typeof record !== "object") fail(`${name} is missing`);
  for (const col of names) {
    numeric(record[col], `${name}.${col}`, nullable.includes(col));
    if (record[col].length !== record[names[0]].length)
      fail(`${name}.${col} has mismatched length`);
  }
  if (record.t?.some((t, i) => t < 0 || (i && t < record.t[i - 1])))
    fail(`${name}.t must be sorted, nonnegative`);
}
function grid(g, name, field) {
  if (
    !g ||
    ![g.west, g.south, g.east, g.north].every(finite) ||
    g.west >= g.east ||
    g.south >= g.north ||
    g.west < -180 ||
    g.east > 180 ||
    g.south < -90 ||
    g.north > 90
  )
    fail(`${name} bounds`);
  if (![g.nx, g.ny].every((n) => Number.isInteger(n) && n >= 2 && n <= 2048))
    fail(`${name} grid dimensions`);
  numeric(g[field], `${name}.${field}`);
  if (g[field].length !== g.nx * g.ny) fail(`${name} grid size`);
}
function position(lat, lon, name) {
  if (!finite(lat) || !finite(lon) || Math.abs(lat) > 90 || Math.abs(lon) > 180)
    fail(`${name} coordinates`);
}
export function safeMediaPath(path) {
  if (
    typeof path !== "string" ||
    path.length > 2048 ||
    /[\\\x00-\x20?#]/.test(path)
  )
    return false;
  let decoded;
  try {
    decoded = decodeURIComponent(path);
  } catch {
    return false;
  }
  return /^\.?\.?\//.test(path) || /^[\w-]+[\w.%-]*(?:\/|$)/.test(path)
    ? !decoded.startsWith("/") &&
        !decoded.includes("..") &&
        !decoded.includes(":") &&
        !decoded.includes("\\")
    : false;
}
export function validateData(value) {
  if (!value || typeof value !== "object") fail("no data.js loaded");
  const d = structuredClone(value);
  const s = d.scenario;
  if (
    !s ||
    typeof s.name !== "string" ||
    typeof s.start !== "string" ||
    !Number.isFinite(Date.parse(s.start)) ||
    !finite(s.duration_s) ||
    s.duration_s <= 0 ||
    s.duration_s > 31_536_000
  )
    fail("scenario metadata");
  position(s.area?.lat, s.area?.lon, "area");
  if (!finite(s.area.size_km) || s.area.size_km <= 0 || s.area.size_km > 1000)
    fail("area size");
  if (
    !s.weather ||
    ![
      "wind_from_deg",
      "wind_mps",
      "temp_c",
      "rh_pct",
      "visibility_km",
      "cloud_pct",
    ].every((k) => finite(s.weather[k]))
  )
    fail("weather");
  grid(d.terrain, "terrain", "h");
  const texture = d.terrain.texture;
  if (texture != null) {
    if (!safeMediaPath(texture.src) || typeof texture.credit !== 'string' ||
        ![texture.west, texture.south, texture.east, texture.north].every(finite) ||
        texture.west >= texture.east || texture.south >= texture.north ||
        texture.west < -180 || texture.east > 180 || texture.south < -90 || texture.north > 90)
      fail('terrain.texture path, credit or bounds');
  }
  for (const key of ["objects", "sensors", "classes", "links", "labels"])
    if (!Array.isArray(d[key])) fail(`${key} must be an array`);
  if (d.objects.length > 1000 || d.sensors.length > 256)
    fail("too many objects or sensors");
  for (const key of ["classes", "links", "labels"])
    if (d[key].some((x) => typeof x !== "string"))
      fail(`${key} must contain strings`);
  const ids = new Set();
  for (const o of d.objects) {
    if (
      !o ||
      typeof o.id !== "string" ||
      ids.has(o.id) ||
      typeof o.type !== "string" ||
      !["drone", "bird", "operator", "emitter", "site", "response"].includes(o.kind) ||
      !["hostile", "friendly", "neutral", "unknown"].includes(o.side)
    )
      fail("object identity/type");
    ids.add(o.id);
    columns(o, ["t", "lat", "lon", "alt"], o.id);
    o.lat.forEach((lat, i) => position(lat, o.lon[i], o.id));
  }
  const sensorIds = new Set();
  for (const sensor of d.sensors) {
    if (
      !sensor ||
      typeof sensor.id !== "string" ||
      typeof sensor.type !== "string" ||
      sensorIds.has(sensor.id)
    )
      fail("sensor identity/type");
    sensorIds.add(sensor.id);
    position(sensor.lat, sensor.lon, sensor.id);
    if (
      ![sensor.ground, sensor.alt, sensor.mast_m].every(finite) ||
      !(sensor.dead_t == null || finite(sensor.dead_t))
    )
      fail(`${sensor.id} height or lifetime`);
  }
  d.rf ??= {};
  for (const [id, rf] of Object.entries(d.rf)) {
    if (!sensorIds.has(id)) fail(`unknown receiver ${id}`);
    columns(
      rf,
      ["t", "brg", "std", "snr", "pwr", "cls", "obj", "link", "los", "label"],
      id,
    );
    for (const [key, count, min] of [
      ["cls", d.classes.length, 0],
      ["obj", d.objects.length, -1],
      ["link", d.links.length, 0],
      ["label", d.labels.length, 0],
    ]) {
      if (rf[key].some((i) => !Number.isInteger(i) || i < min || i >= count))
        fail(`${id}.${key} index`);
    }
    if (rf.los.some((v) => v !== 0 && v !== 1) || rf.std.some((v) => v < 0))
      fail(`${id} bearing uncertainty / LOS`);
  }
  d.fixes ??= Object.fromEntries(
    [
      "t",
      "lat",
      "lon",
      "smaj",
      "smin",
      "orient",
      "ce",
      "cep50",
      "cls",
      "obj",
      "err",
    ].map((k) => [k, []]),
  );
  columns(
    d.fixes,
    [
      "t",
      "lat",
      "lon",
      "smaj",
      "smin",
      "orient",
      "ce",
      "cep50",
      "cls",
      "obj",
      "err",
    ],
    "fixes",
    ["err"],
  );
  d.fixes.lat.forEach((lat, i) => position(lat, d.fixes.lon[i], "fix"));
  if (
    ["smaj", "smin", "ce", "cep50"].some((k) =>
      d.fixes[k].some((n) => n < 0),
    ) ||
    d.fixes.obj.some(
      (i) => !Number.isInteger(i) || i < -1 || i >= d.objects.length,
    ) ||
    d.fixes.cls.some(
      (i) => !Number.isInteger(i) || i < 0 || i >= d.classes.length,
    )
  )
    fail("fix ellipse or index");
  d.shadow ??= {};
  for (const [id, g] of Object.entries(d.shadow)) {
    if (!sensorIds.has(id)) fail(`unknown shadow receiver ${id}`);
    grid(g, `shadow.${id}`, "agl");
  }
  d.events ??= [];
  d.media ??= [];
  if (!Array.isArray(d.events) || !Array.isArray(d.media))
    fail("events/media must be arrays");
  for (const e of d.events)
    if (
      !e ||
      !finite(e.t) ||
      e.t < 0 ||
      e.t > s.duration_s ||
      typeof e.label !== "string" ||
      typeof e.kind !== "string"
    )
      fail("event");
  for (const m of d.media)
    if (
      !m ||
      !sensorIds.has(m.sensor) ||
      !finite(m.t) ||
      m.t < 0 ||
      m.t > s.duration_s ||
      !["image", "audio", "iq", "event"].includes(m.kind) ||
      !safeMediaPath(m.src)
    )
      fail("media record/path");
  d.events.sort((a, b) => a.t - b.t);
  d.media.sort((a, b) => a.t - b.t);
  function audit(a) {
    if (a == null) return;
    if (
      !a.summary ||
      !["pass", "fail", "skip"].every(
        (k) => Number.isInteger(a.summary[k]) && a.summary[k] >= 0,
      ) ||
      !Array.isArray(a.checks) ||
      a.checks.some(
        (c) =>
          !c ||
          typeof c.name !== "string" ||
          !["PASS", "FAIL", "SKIP"].includes(c.status),
      )
    )
      fail("audit schema");
    if (a.baseline) audit({ ...a.baseline, baseline: null });
  }
  audit(d.audit);
  for (const [name, record] of [
    ...d.objects.map((o) => [o.id, o]),
    ...Object.entries(d.rf),
    ["fixes", d.fixes],
  ]) {
    if (record.t.some((t) => t > s.duration_s))
      fail(`${name} timestamps exceed scenario duration`);
  }
  return d;
}
export function parseDataFile(text) {
  if (text.length > 100_000_000)
    throw new Error("Scenario file exceeds 100 MB.");
  const source = text.trim().replace(/^\uFEFF/, "");
  const json = source.startsWith("{")
    ? source
    : source.replace(/^(?:window\.)?MW\s*=\s*/, "").replace(/;\s*$/, "");
  let value;
  try {
    value = JSON.parse(json);
  } catch {
    throw new Error(
      "Use a JSON object or window.MW = {…}; with strict JSON. Executable JavaScript is not accepted.",
    );
  }
  return validateData(value);
}
export function upperBound(values, t) {
  let lo = 0,
    hi = values.length;
  while (lo < hi) {
    const mid = (lo + hi) >>> 1;
    if (values[mid] <= t) lo = mid + 1;
    else hi = mid;
  }
  return lo;
}
export function sample(object, t) {
  if (!object?.t.length || t < object.t[0] || t > object.t.at(-1)) return null;
  const i = Math.min(upperBound(object.t, t) - 1, object.t.length - 1),
    j = Math.min(i + 1, object.t.length - 1);
  const f = j === i ? 0 : (t - object.t[i]) / (object.t[j] - object.t[i] || 1);
  return {
    lat: object.lat[i] + (object.lat[j] - object.lat[i]) * f,
    lon: object.lon[i] + (object.lon[j] - object.lon[i]) * f,
    alt: object.alt[i] + (object.alt[j] - object.alt[i]) * f,
  };
}
export function heightAt(grid, lon, lat, field = "h") {
  const x = Math.max(
    0,
    Math.min(
      grid.nx - 1,
      ((lon - grid.west) / (grid.east - grid.west)) * (grid.nx - 1),
    ),
  );
  const y = Math.max(
    0,
    Math.min(
      grid.ny - 1,
      ((lat - grid.south) / (grid.north - grid.south)) * (grid.ny - 1),
    ),
  );
  const ix = Math.min(Math.floor(x), grid.nx - 2),
    iy = Math.min(Math.floor(y), grid.ny - 2),
    dx = x - ix,
    dy = y - iy;
  const h = grid[field],
    n = grid.nx;
  return (
    h[iy * n + ix] * (1 - dx) * (1 - dy) +
    h[iy * n + ix + 1] * dx * (1 - dy) +
    h[(iy + 1) * n + ix] * (1 - dx) * dy +
    h[(iy + 1) * n + ix + 1] * dx * dy
  );
}
export function timeLabel(d, t, milliseconds = false) {
  return new Date(Date.parse(d.scenario.start) + t * 1000)
    .toISOString()
    .slice(11, milliseconds ? 23 : 19);
}
export const escapeHTML = (s) =>
  String(s ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
export function summarize(d) {
  return {
    scenario: d.scenario.name,
    objects: d.objects.length,
    sensors: d.sensors.length,
    detections: Object.values(d.rf).reduce((n, r) => n + r.t.length, 0),
    fixes: d.fixes.t.length,
    terrain: `${d.terrain.nx} × ${d.terrain.ny}`,
    media: d.media.length,
    audit: d.audit ? "loaded" : "not supplied",
  };
}
