// World picker: where in Ukraine the tile is, its real terrain (AWS Terrarium) and real infrastructure (OSM Overpass). Keyless.
import UKR from './ukraine.json';
import { rng, M_PER_DEG } from './seed.js';

// mirrorworld/config.py UKRAINE = (lat_min, lat_max, lon_min, lon_max). ponytail: bbox, the border is ukraine.json.
export const UKRAINE_BBOX = { south: 44.0, north: 52.5, west: 22.0, east: 40.5 };
export const ukraineOutline = () => UKR.geometry.coordinates;  // rings of [lon, lat]

function inside(lon, lat, ring) {  // even-odd ray casting
  let c = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i], [xj, yj] = ring[j];
    if (yi > lat !== yj > lat && lon < ((xj - xi) * (lat - yi)) / (yj - yi) + xi) c = !c;
  }
  return c;
}
const inUkraine = (lon, lat) => inside(lon, lat, ukraineOutline()[0]);

// Uniform in lon/lat inside the border (rejection sampling), deterministic per world seed.
export function randomSite(worldSeed) {
  const r = rng(worldSeed, 'site'), b = UKRAINE_BBOX;
  for (let k = 0; k < 10000; k++) {
    const lon = r.range(b.west, b.east), lat = r.range(b.south, b.north);
    if (inUkraine(lon, lat)) return { lat: +lat.toFixed(5), lon: +lon.toFixed(5) };
  }
  return { lat: 49.37, lon: 31.2 };
}

const bboxAround = (lat, lon, km) => {
  const dLat = (km * 500) / M_PER_DEG, dLon = (km * 500) / (M_PER_DEG * Math.cos((lat * Math.PI) / 180));
  return { west: lon - dLon, east: lon + dLon, south: lat - dLat, north: lat + dLat };
};

// ---- terrain: AWS Terrain Tiles (terrarium PNG, zoom 12 ~30 m), height = R*256 + G + B/256 - 32768 ----
const ELEV = (z, x, y) => `https://s3.amazonaws.com/elevation-tiles-prod/terrarium/${z}/${x}/${y}.png`;
const mercPx = (lat, lon, z) => {
  const n = 256 * 2 ** z, s = Math.sin((lat * Math.PI) / 180);
  return [((lon + 180) / 360) * n, (0.5 - Math.log((1 + s) / (1 - s)) / (4 * Math.PI)) * n];
};
const loadImg = (src) => new Promise((ok, fail) => {
  const i = new Image(), t = setTimeout(() => { i.src = ''; fail(new Error(`terrain tile timeout: ${src}`)); }, 10000);
  i.crossOrigin = 'anonymous';
  i.onload = () => { clearTimeout(t); ok(i); };
  i.onerror = () => { clearTimeout(t); fail(new Error(`terrain tile failed: ${src}`)); };
  i.src = src;
});

// Grid in MW.terrain format covering sizeKm * 1.2 around the centre (margin = globe context). Rows south -> north.
// ponytail: samples the Mercator crop on a lon/lat lattice (Mercator y is monotonic in lat, error < 0.5% at 24 km).
export async function loadTerrain(lat, lon, sizeKm, n = 181, z = 12) {
  const b = bboxAround(lat, lon, sizeKm * 1.2);
  const [x0, y0] = mercPx(b.north, b.west, z), [x1, y1] = mercPx(b.south, b.east, z);
  const tx0 = Math.floor(x0 / 256), ty0 = Math.floor(y0 / 256), tx1 = Math.floor(x1 / 256), ty1 = Math.floor(y1 / 256);
  const c = document.createElement('canvas');
  c.width = (tx1 - tx0 + 1) * 256;
  c.height = (ty1 - ty0 + 1) * 256;
  const g = c.getContext('2d', { willReadFrequently: true });
  g.imageSmoothingEnabled = false;  // RGB encodes height: never blend pixels
  const jobs = [];
  for (let tx = tx0; tx <= tx1; tx++)
    for (let ty = ty0; ty <= ty1; ty++)
      jobs.push(loadImg(ELEV(z, tx, ty)).then((img) => g.drawImage(img, (tx - tx0) * 256, (ty - ty0) * 256)));
  await Promise.all(jobs);
  const d = g.getImageData(0, 0, c.width, c.height).data, h = new Array(n * n);
  for (let j = 0; j < n; j++) {  // j = 0 is the south row
    const la = b.south + ((b.north - b.south) * j) / (n - 1);
    for (let i = 0; i < n; i++) {
      const [px, py] = mercPx(la, b.west + ((b.east - b.west) * i) / (n - 1), z);
      const x = Math.min(c.width - 1, Math.floor(px - tx0 * 256)), y = Math.min(c.height - 1, Math.floor(py - ty0 * 256));
      const k = (y * c.width + x) * 4;
      h[j * n + i] = Math.round((d[k] * 256 + d[k + 1] + d[k + 2] / 256 - 32768) * 10) / 10;
    }
  }
  return { ...b, nx: n, ny: n, h };
}

// ---- features: real infrastructure from OpenStreetMap (Overpass). Never throws. ----
// Main instance first, then a mirror (overpass-api.de answers 406/429 when busy or rate-limiting).
const OVERPASS = ['https://overpass-api.de/api/interpreter', 'https://overpass.private.coffee/api/interpreter'];
export async function loadFeatures(T) {
  const bb = `${T.south},${T.west},${T.north},${T.east}`;
  const q = `[out:json][timeout:8];(
nwr["power"="substation"](${bb});
way["bridge"="yes"]["highway"](${bb});way["bridge"="yes"]["railway"](${bb});
node["place"~"^(village|town|hamlet)$"]["name"](${bb});
nwr["man_made"~"^(mast|tower)$"]["tower:type"="communication"](${bb});
nwr["amenity"="fuel"](${bb});
);out center 200;`;
  const ac = new AbortController(), t = setTimeout(() => ac.abort(), 8000);
  try {
    let res;
    for (const url of OVERPASS) {  // one shared 8 s budget
      res = await fetch(url, { method: 'POST', body: new URLSearchParams({ data: q }), signal: ac.signal });
      if (res.ok) break;
    }
    if (!res.ok) throw new Error(`Overpass HTTP ${res.status}`);
    const typeOf = (g) => g.power === 'substation' ? 'substation' : g.bridge === 'yes' ? 'bridge' : g.place ? 'village'
      : g.amenity === 'fuel' ? 'fuel_depot' : g['tower:type'] === 'communication' ? 'comms_mast' : null;
    const out = [], per = {};
    for (const e of (await res.json()).elements || []) {
      const type = typeOf(e.tags || {}), lat = e.lat ?? e.center?.lat, lon = e.lon ?? e.center?.lon;
      if (!type || lat == null || (per[type] = (per[type] || 0) + 1) > 10) continue;  // max 10 per type keeps the mix
      out.push({ type, lat, lon, name: e.tags.name || e.tags['name:en'] || '' });
      if (out.length >= 40) break;
    }
    return out;
  } catch (err) {
    console.warn('loadFeatures: Overpass failed, falling back to procedural assets', err);
    return [];
  } finally {
    clearTimeout(t);
  }
}
