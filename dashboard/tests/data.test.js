import { test } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import {
  validateData,
  parseDataFile,
  heightAt,
  sample,
  upperBound,
  safeMediaPath,
} from "../src/data.js";

const fixture = () => ({
  scenario: {
    name: "test",
    start: "2026-11-04T08:55:00Z",
    duration_s: 100,
    area: { lat: 49, lon: 31, size_km: 1 },
    weather: {
      wind_from_deg: 270,
      wind_mps: 3,
      temp_c: 4,
      rh_pct: 80,
      visibility_km: 12,
      cloud_pct: 40,
    },
  },
  terrain: {
    west: 30,
    south: 48,
    east: 32,
    north: 50,
    nx: 2,
    ny: 2,
    h: [0, 10, 20, 30],
  },
  objects: [
    {
      id: "drone",
      type: "quad",
      kind: "drone",
      side: "hostile",
      t: [0, 10],
      lat: [49, 49.1],
      lon: [31, 31.1],
      alt: [40, 50],
    },
  ],
  sensors: [
    {
      id: "RF1",
      type: "rf_df",
      lat: 49,
      lon: 31,
      ground: 10,
      alt: 30,
      mast_m: 20,
      dead_t: null,
    },
  ],
  classes: ["video"],
  links: ["drone:video"],
  labels: ["target"],
  rf: {
    RF1: {
      t: [0, 1],
      brg: [90, 92],
      std: [2, 2],
      snr: [10, 9],
      pwr: [-80, -81],
      cls: [0, 0],
      obj: [0, 0],
      link: [0, 0],
      los: [1, 0],
      label: [0, 0],
    },
  },
  audit: null,
});

test("DEM bilinear interpolation preserves south-to-north orientation and clamps edges", () => {
  const g = fixture().terrain;
  assert.equal(heightAt(g, 30, 48), 0);
  assert.equal(heightAt(g, 32, 50), 30);
  assert.equal(heightAt(g, 31, 49), 15);
  assert.equal(heightAt(g, 100, 100), 30);
  assert.equal(heightAt(g, -100, -100), 0);
});
test("truth interpolation is bounded by actual object lifetime", () => {
  const o = fixture().objects[0];
  assert.equal(sample(o, -1), null);
  assert.equal(sample(o, 11), null);
  assert.deepEqual(sample(o, 5), { lat: 49.05, lon: 31.05, alt: 45 });
  assert.equal(sample(o, 10).alt, 50);
});
test("binary search includes detections at the current instant and handles duplicates", () => {
  const t = [0, 1, 1, 3];
  assert.equal(upperBound(t, -1), 0);
  assert.equal(upperBound(t, 1), 3);
  assert.equal(upperBound(t, 10), 4);
  assert.equal(upperBound([], 1), 0);
});
test("data.js loading accepts only JSON and cannot execute appended JavaScript", () => {
  const d = fixture();
  assert.equal(
    parseDataFile(`window.MW = ${JSON.stringify(d)};`).scenario.name,
    "test",
  );
  assert.throws(
    () =>
      parseDataFile(
        `window.MW = ${JSON.stringify(d)}; globalThis.COMPROMISED=true`,
      ),
    /Executable JavaScript/,
  );
  assert.throws(
    () => parseDataFile('window.MW = (() => {throw "execute"})()'),
    /Executable JavaScript/,
  );
  assert.equal(globalThis.COMPROMISED, undefined);
});
test("malformed columns, unsorted timestamps, unknown indices, and invalid coordinates are rejected", () => {
  const mutations = [
    (d) => (d.scenario.start = 2026),
    (d) => (d.rf.RF1.t[1] = 101),
    (d) => d.rf.RF1.t.push(2),
    (d) => d.rf.RF1.t.reverse(),
    (d) => (d.rf.RF1.obj[0] = 10),
    (d) => (d.objects[0].lat[0] = Infinity),
    (d) => d.sensors.push({ ...d.sensors[0] }),
    (d) => d.terrain.h.pop(),
    (d) => (d.scenario.weather = null),
  ];
  for (const mutate of mutations) {
    const d = fixture();
    mutate(d);
    assert.throws(() => validateData(d), /Invalid scenario/);
  }
});
test("missing optional observations are explicit empty arrays, never invented", () => {
  const d = fixture();
  delete d.rf;
  const valid = validateData(d);
  assert.deepEqual(valid.rf, {});
  assert.deepEqual(valid.media, []);
  assert.equal(valid.fixes.t.length, 0);
  assert.equal(valid.audit, null);
});
test("media paths reject external URLs, schemes, encoded traversal and backslashes", () => {
  for (const path of [
    "https://example.com/record.wav",
    "//example.com/a",
    "data:audio/wav,x",
    "../private",
    "./%2e%2e/private",
    "./sensors\\evil",
    "/sensors/a.png",
    "./sensors/a.png?token=x",
  ])
    assert.equal(safeMediaPath(path), false, path);
  assert.equal(safeMediaPath("./sensors/IQ1/snap_000.png"), true);
});
test("audit scores require nonnegative integer counts and valid statuses", () => {
  const d = fixture();
  d.audit = {
    summary: { pass: 1, fail: 0, skip: 0 },
    checks: [
      { id: "one", name: "Geometry", status: "PASS", value: 1, threshold: 2 },
    ],
  };
  assert.equal(validateData(d).audit.summary.pass, 1);
  d.audit.checks[0].status = "PROBABLY";
  assert.throws(() => validateData(d), /audit/);
});
test("real exported scenario meets the frontend contract when available", async (t) => {
  let source;
  try {
    source = await readFile("dashboard/public/data.js", "utf8");
  } catch (error) {
    if (error.code === "ENOENT") {
      t.skip("No generated scenario");
      return;
    }
    throw error;
  }
  if (source.includes("window.MW = null")) {
    t.skip("No generated scenario");
    return;
  }
  const data = parseDataFile(source);
  assert.ok(data.terrain.h.length > 4);
  assert.ok(Object.values(data.rf).every((r) => r.t.length === r.obj.length));
});

test("baked terrain texture accepts local files and rejects unsafe paths or bounds", () => {
  const d = fixture();
  d.terrain.texture = {
    src: "texture.jpg",
    west: 30,
    south: 48,
    east: 32,
    north: 50,
    credit: "Copernicus",
  };
  assert.equal(validateData(d).terrain.texture.src, "texture.jpg");
  for (const src of [
    "https://example.com/texture.jpg",
    "../texture.jpg",
    "./%2e%2e/texture.jpg",
    "javascript:alert(1)",
  ]) {
    assert.throws(
      () =>
        validateData({
          ...d,
          terrain: { ...d.terrain, texture: { ...d.terrain.texture, src } },
        }),
      /terrain.texture/,
    );
  }
  assert.throws(
    () =>
      validateData({
        ...d,
        terrain: { ...d.terrain, texture: { ...d.terrain.texture, west: 33 } },
      }),
    /terrain.texture/,
  );
});
