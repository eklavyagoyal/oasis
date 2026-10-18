/* OASIS 3D replay console — plain JS, no framework, no build step.
 * Sections: helpers / terrain / imagery / viewer+clock / truth / sensors / LOBs /
 * fixes+error lines / shadows / feeds / RF chart / panels / view modes / tick loop.
 */
"use strict";

const MW = window.MW;

// ---------------------------------------------------------------- helpers
const SIDE_COLORS = {
  hostile: "#ff4d4d",
  friendly: "#4da3ff",
  neutral: "#b0b0b0",
  unknown: "#ffd24d",
};
const CLASS_COLORS = [
  "#ff8c1a", "#4ade80", "#5db2ff", "#ff5ddb", "#ffe14d", "#17e0d0", "#c08cff", "#ff6f6f",
];
const AMBER = "#ffb000";
const GREY = "#5a626c";
const M_PER_DEG = 111195;
const LOB_M = 8000;
const LOB_WINDOW_S = 3;
const FIX_WINDOW_S = 10;
const CHART_WINDOW_S = 600;

function esc(v) {  // data.js can come from LLM-written scenarios: never trust it as HTML
  return String(v).replace(/[&<>"']/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
  });
}

function classColor(i) {
  return CLASS_COLORS[((i | 0) + CLASS_COLORS.length) % CLASS_COLORS.length];
}
function cssColor(hex, alpha) {
  return Cesium.Color.fromCssColorString(hex).withAlpha(alpha === undefined ? 1 : alpha);
}
function clamp(v, lo, hi) {
  return v < lo ? lo : v > hi ? hi : v;
}
function fmtClock(t) {
  return Cesium.JulianDate.toIso8601(TIME0(t)).replace(/\.\d+Z$/, "Z").replace("T", " ");
}
function el(id) {
  return document.getElementById(id);
}

// ---------------------------------------------------------------- clock base
const START = Cesium.JulianDate.fromIso8601(MW.scenario.start);
const STOP = Cesium.JulianDate.addSeconds(START, MW.scenario.duration_s, new Cesium.JulianDate());
function TIME0(t) {
  return Cesium.JulianDate.addSeconds(START, t, new Cesium.JulianDate());
}

// ---------------------------------------------------------------- terrain
// MW.terrain: h[row * nx + col], row 0 = south, col 0 = west (matches the exporter).
function terrainHeight(lat, lon) {
  const T = MW.terrain;
  const fx = clamp(((lon - T.west) / (T.east - T.west)) * (T.nx - 1), 0, T.nx - 1);
  const fy = clamp(((lat - T.south) / (T.north - T.south)) * (T.ny - 1), 0, T.ny - 1);
  const x0 = Math.min(Math.floor(fx), T.nx - 2);
  const y0 = Math.min(Math.floor(fy), T.ny - 2);
  const dx = fx - x0, dy = fy - y0;
  const h = T.h;
  return (
    h[y0 * T.nx + x0] * (1 - dx) * (1 - dy) +
    h[y0 * T.nx + x0 + 1] * dx * (1 - dy) +
    h[(y0 + 1) * T.nx + x0] * (1 - dx) * dy +
    h[(y0 + 1) * T.nx + x0 + 1] * dx * dy
  );
}

// CustomHeightmapTerrainProvider callback: row-major, row 0 = NORTH edge, col 0 = west.
const TILING = new Cesium.GeographicTilingScheme();
const terrainProvider = new Cesium.CustomHeightmapTerrainProvider({
  width: 32,
  height: 32,
  tilingScheme: TILING,
  callback: function (x, y, level) {
    const rect = TILING.tileXYToRectangle(x, y, level);
    const w = 32, hgt = 32;
    const out = new Float32Array(w * hgt);
    for (let row = 0; row < hgt; row++) {
      const lat = Cesium.Math.toDegrees(rect.north - ((rect.north - rect.south) * row) / (hgt - 1));
      for (let col = 0; col < w; col++) {
        const lon = Cesium.Math.toDegrees(rect.west + ((rect.east - rect.west) * col) / (w - 1));
        out[row * w + col] = terrainHeight(lat, lon);
      }
    }
    return out;
  },
});

// ---------------------------------------------------------------- imagery
const IMAGERY = {
  esri: new Cesium.UrlTemplateImageryProvider({
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    credit: "Esri, Maxar, Earthstar Geographics",
    maximumLevel: 19,
  }),
  osm: new Cesium.UrlTemplateImageryProvider({
    url: "https://tile.openstreetmap.org/{z}/{x}/{y}",
    credit: "© OpenStreetMap contributors",
    maximumLevel: 19,
  }),
};
function setImagery(name) {
  const layers = viewer.imageryLayers;
  layers.removeAll();
  layers.addImageryProvider(IMAGERY[name]);
  for (const layer of shadowLayers) layers.add(layer); // shadows stay on top
}

// ---------------------------------------------------------------- viewer + clock
const viewer = new Cesium.Viewer("cesiumContainer", {
  baseLayerPicker: false,
  geocoder: false,
  homeButton: false,
  sceneModePicker: false,
  navigationHelpButton: false,
  fullscreenButton: false,
  infoBox: true,
  selectionIndicator: true,
  animation: false,
  timeline: false,
  baseLayer: new Cesium.ImageryLayer(IMAGERY.esri),
  terrainProvider: terrainProvider,
});
viewer.scene.globe.depthTestAgainstTerrain = true;

const clock = viewer.clock;
clock.startTime = START.clone();
clock.stopTime = STOP.clone();
clock.currentTime = START.clone();
clock.clockRange = Cesium.ClockRange.CLAMPED;
clock.multiplier = 20;
clock.shouldAnimate = false;

const timeline = new Cesium.Timeline("timelineContainer", clock);
timeline.zoomTo(START, STOP);
timeline.addEventListener("setTime", function (e) {
  clock.currentTime = e.timeJulian;
}, false);
new Cesium.Animation(
  "animationContainer",
  new Cesium.AnimationViewModel(new Cesium.ClockViewModel(clock))
);

const center = MW.scenario.area;
// Oblique look north over the area: same 9 km altitude, heading 0, pitch -35, but the
// camera sits south of the centre so the -35 degree frustum frames the area itself.
const CAM_AHEAD_M = 9000 / Math.tan(Cesium.Math.toRadians(35));
viewer.camera.setView({
  destination: Cesium.Cartesian3.fromDegrees(center.lon, center.lat - CAM_AHEAD_M / M_PER_DEG, 9000),
  orientation: { heading: 0, pitch: Cesium.Math.toRadians(-35), roll: 0 },
});

function nowT() {
  return Cesium.JulianDate.secondsDifference(clock.currentTime, START);
}

// ---------------------------------------------------------------- truth objects
const truthEntities = [];
const entitiesByObj = [];
for (let oi = 0; oi < MW.objects.length; oi++) {
  const o = MW.objects[oi];
  const pos = new Cesium.SampledPositionProperty();
  pos.setInterpolationOptions({
    interpolationDegree: 1,
    interpolationAlgorithm: Cesium.LinearApproximation,
  });
  for (let i = 0; i < o.t.length; i++) {
    pos.addSample(TIME0(o.t[i]), Cesium.Cartesian3.fromDegrees(o.lon[i], o.lat[i], o.alt[i]));
  }
  const color = cssColor(SIDE_COLORS[o.side] || SIDE_COLORS.unknown);
  const isOp = o.kind === "operator";
  const isEm = o.kind === "emitter";
  const opts = {
    name: o.id,
    position: pos,
    availability: new Cesium.TimeIntervalCollection([
      new Cesium.TimeInterval({ start: TIME0(o.t[0]), stop: TIME0(o.t[o.t.length - 1]) }),
    ]),
    label: {
      text: o.id,
      font: "11px monospace",
      style: Cesium.LabelStyle.FILL_AND_OUTLINE,
      outlineWidth: 3,
      outlineColor: Cesium.Color.BLACK,
      fillColor: color,
      pixelOffset: new Cesium.Cartesian2(0, -14),
      verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
      distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, 40000),
    },
    description:
      "<b>" + o.id + "</b><br>type: " + o.type + " · " + o.kind + "<br>side: " + o.side,
  };
  if (isEm) {
    const hex = SIDE_COLORS[o.side] || SIDE_COLORS.unknown;
    opts.billboard = {
      image:
        "data:image/svg+xml;base64," +
        btoa(
          '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14">' +
            '<path d="M7 0 L14 7 L7 14 L0 7 Z" fill="' + hex + '" stroke="#0b0e12" stroke-width="1.5"/></svg>'
        ),
      width: 14,
      height: 14,
    };
  } else {
    opts.point = {
      pixelSize: isOp ? 6 : 9,
      color: color,
      outlineColor: Cesium.Color.BLACK.withAlpha(0.6),
      outlineWidth: 1,
    };
  }
  if (!isOp && !isEm) {
    opts.path = {
      leadTime: 0,
      trailTime: 120,
      width: 1,
      resolution: 1,
      material: color.withAlpha(0.45),
    };
  }
  const ent = viewer.entities.add(opts);
  ent._objIdx = oi;
  truthEntities.push(ent);
  entitiesByObj.push(ent);
}

// nearest truth sample of object oi at time t -> Cartesian3 (MSL alt)
function truthPositionAt(oi, t) {
  const o = MW.objects[oi];
  const ts = o.t;
  let lo = 0, hi = ts.length - 1;
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1;
    if (ts[mid] < t) lo = mid; else hi = mid;
  }
  const i = Math.abs(ts[lo] - t) <= Math.abs(ts[hi] - t) ? lo : hi;
  return Cesium.Cartesian3.fromDegrees(o.lon[i], o.lat[i], o.alt[i]);
}

// ---------------------------------------------------------------- sensor markers
const sensorEntities = [];
for (const s of MW.sensors) {
  const top = Cesium.Cartesian3.fromDegrees(s.lon, s.lat, s.alt);
  const base = Cesium.Cartesian3.fromDegrees(s.lon, s.lat, s.ground);
  const mast = viewer.entities.add({
    polyline: {
      positions: [base, top],
      width: 2,
      material: cssColor(AMBER, 0.55),
    },
  });
  const mark = viewer.entities.add({
    name: s.id,
    position: top,
    point: {
      pixelSize: 8,
      color: cssColor(AMBER),
      outlineColor: Cesium.Color.BLACK,
      outlineWidth: 2,
    },
    label: {
      text: s.id,
      font: "11px monospace",
      style: Cesium.LabelStyle.FILL_AND_OUTLINE,
      outlineWidth: 3,
      outlineColor: Cesium.Color.BLACK,
      fillColor: cssColor(AMBER),
      pixelOffset: new Cesium.Cartesian2(0, -14),
      verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
      distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, 60000),
    },
    description: "<b>" + s.id + "</b> (" + s.type + ")<br>antenna " + s.alt + " m MSL",
  });
  sensorEntities.push({ sensor: s, mark: mark, mast: mast, dead: false });
}

// ---------------------------------------------------------------- lines of bearing
const lobCollection = viewer.scene.primitives.add(new Cesium.PolylineCollection());
function lobPositions(s, brgDeg) {
  const brg = Cesium.Math.toRadians(brgDeg);
  const cosLat = Math.cos(Cesium.Math.toRadians(s.lat));
  const pts = [];
  for (let k = 0; k < 5; k++) {
    const d = (LOB_M * k) / 4;
    const lat = s.lat + (d * Math.cos(brg)) / M_PER_DEG;
    const lon = s.lon + (d * Math.sin(brg)) / (M_PER_DEG * cosLat);
    const z = k === 0 ? s.alt : terrainHeight(lat, lon) + 50;
    pts.push(Cesium.Cartesian3.fromDegrees(lon, lat, z));
  }
  return pts;
}
function rebuildLobs(now) {
  lobCollection.removeAll();
  for (const s of MW.sensors) {
    const rec = MW.rf[s.id];
    if (!rec || !lobOn[s.id]) continue;
    for (let i = 0; i < rec.t.length; i++) {
      const age = now - rec.t[i];
      if (age < 0 || age > LOB_WINDOW_S) continue;
      if (hideFA && MW.labels[rec.label[i]] === "false_alarm") continue;
      const hex = classColor(rec.cls[i]);
      lobCollection.add({
        positions: lobPositions(s, rec.brg[i]),
        width: 2,
        material: Cesium.Material.fromType("Color", {
          color: cssColor(hex, 0.12 + 0.8 * (1 - age / LOB_WINDOW_S)),
        }),
      });
    }
  }
}

// ---------------------------------------------------------------- fixes + error lines
const FIX_POOL = 48;
const fixPool = [];
const poolCenter = Cesium.Cartesian3.fromDegrees(center.lon, center.lat, 200);
for (let i = 0; i < FIX_POOL; i++) {
  const e = viewer.entities.add({
    show: false,
    position: poolCenter,
    ellipse: {
      height: 200,
      semiMajorAxis: 30,
      semiMinorAxis: 30,
      rotation: 0,
      material: cssColor("#ffffff", 0.15),
      outline: true,
      outlineColor: cssColor("#ffffff", 0.8),
    },
    point: { pixelSize: 5, color: Cesium.Color.WHITE },
  });
  e._fixInfo = "";
  fixPool.push(e);
}
const errCollection = viewer.scene.primitives.add(new Cesium.PolylineCollection());

function rebuildFixes(now) {
  const f = MW.fixes;
  let slot = 0;
  errCollection.removeAll();
  for (let i = 0; i < f.t.length; i++) {
    const age = now - f.t[i];
    if (age < 0 || age > FIX_WINDOW_S || slot >= FIX_POOL) continue;
    const e = fixPool[slot++];
    const hex = classColor(f.cls[i]);
    const z = terrainHeight(f.lat[i], f.lon[i]) + 30;
    e.position = Cesium.Cartesian3.fromDegrees(f.lon[i], f.lat[i], z);
    e.ellipse.height = z;
    e.ellipse.semiMajorAxis = Math.max(f.smaj[i] || 0, 20);
    e.ellipse.semiMinorAxis = Math.max(f.smin[i] || 0, 20);
    e.ellipse.rotation = Cesium.Math.toRadians(-(f.orient[i] || 0));
    e.ellipse.material = cssColor(hex, 0.16);
    e.ellipse.outlineColor = cssColor(hex, 0.9);
    e.point.color = cssColor(hex);
    e._fixInfo =
      "FIX @ " + fmtClock(f.t[i]) +
      "\nclass: " + (MW.classes[f.cls[i]] || "?") +
      "\nce: " + f.ce[i] + " m · cep50: " + f.cep50[i] + " m" +
      (f.err[i] === null ? "" : "\nerror vs truth: " + f.err[i] + " m");
    e.show = true;
    if (viewMode === "both" && f.obj[i] >= 0) {
      errCollection.add({
        positions: [
          Cesium.Cartesian3.fromDegrees(f.lon[i], f.lat[i], z),
          truthPositionAt(f.obj[i], f.t[i]),
        ],
        width: 1,
        material: Cesium.Material.fromType("Color", { color: cssColor("#ffffff", 0.5) }),
      });
    }
  }
  for (let i = slot; i < FIX_POOL; i++) fixPool[i].show = false;
}

// hover tooltip for fixes
const tooltip = el("tooltip");
const handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);
handler.setInputAction(function (movement) {
  const picked = viewer.scene.pick(movement.endPosition);
  const ent = picked && picked.id;
  if (ent && ent._fixInfo) {
    tooltip.style.display = "block";
    tooltip.style.left = movement.endPosition.x + 14 + "px";
    tooltip.style.top = movement.endPosition.y + 14 + "px";
    tooltip.textContent = ent._fixInfo;
  } else {
    tooltip.style.display = "none";
  }
}, Cesium.ScreenSpaceEventType.MOUSE_MOVE);

// ---------------------------------------------------------------- terrain-shadow overlays
const shadowLayers = [];
let aglThreshold = 40;
const shadowOn = {};
function rebuildShadows() {
  for (const layer of shadowLayers) viewer.imageryLayers.remove(layer, true);
  shadowLayers.length = 0;
  if (viewMode === "truth") return;
  for (const s of MW.sensors) {
    const sh = MW.shadow[s.id];
    if (!sh || !shadowOn[s.id]) continue;
    const canvas = document.createElement("canvas");
    canvas.width = sh.nx;
    canvas.height = sh.ny;
    const ctx2d = canvas.getContext("2d");
    const img = ctx2d.createImageData(sh.nx, sh.ny);
    for (let row = 0; row < sh.ny; row++) {
      for (let col = 0; col < sh.nx; col++) {
        const px = ((sh.ny - 1 - row) * sh.nx + col) * 4; // canvas row 0 = north
        if (sh.agl[row * sh.nx + col] > aglThreshold) {
          img.data[px] = 255;
          img.data[px + 1] = 40;
          img.data[px + 2] = 40;
          img.data[px + 3] = 110;
        }
      }
    }
    ctx2d.putImageData(img, 0, 0);
    const layer = viewer.imageryLayers.addImageryProvider(
      new Cesium.SingleTileImageryProvider({
        url: canvas.toDataURL(),
        rectangle: Cesium.Rectangle.fromDegrees(sh.west, sh.south, sh.east, sh.north),
        tileWidth: sh.nx,
        tileHeight: sh.ny,
      })
    );
    shadowLayers.push(layer);
  }
}

// ---------------------------------------------------------------- media feeds
const feedCards = [];
function buildFeeds() {
  const host = el("feeds");
  for (const s of MW.sensors) {
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML =
      '<div class="cap">' + esc(s.id) + " · " + esc(s.type) + "</div>" +
      '<div class="body"><span class="placeholder">no media yet</span></div>' +
      '<audio controls preload="none"></audio>';
    host.appendChild(card);
    feedCards.push({
      sensor: s.id,
      card: card,
      body: card.querySelector(".body"),
      audio: card.querySelector("audio"),
      imgT: null,
      audioT: null,
    });
  }
}
function updateFeeds(now) {
  for (const fc of feedCards) {
    // latest image at or before now
    let img = null, aud = null;
    for (const m of MW.media) {
      if (m.sensor !== fc.sensor || m.t > now) continue;
      if (m.kind === "image" && (!img || m.t >= img.t)) img = m;
      if (m.kind === "audio" && (!aud || m.t >= aud.t)) aud = m;
    }
    if (img && fc.imgT !== img.t) {
      fc.imgT = img.t;
      const im = document.createElement("img");
      im.src = img.src;
      im.alt = fc.sensor;
      const cap = document.createElement("div");
      cap.className = "cap";
      cap.textContent = fmtClock(img.t);
      fc.body.replaceChildren(im, cap);
    } else if (!img && fc.imgT !== null) {
      fc.imgT = null;
      fc.body.innerHTML = '<span class="placeholder">no media yet</span>';
    }
    if (aud && fc.audioT !== aud.t) {
      fc.audioT = aud.t;
      fc.audio.src = aud.src;
    }
    if (aud) {
      const want = now - aud.t;
      if (clock.shouldAnimate && want >= 0 && want <= (fc.audio.duration || 1e9)) {
        if (fc.audio.paused) fc.audio.play().catch(function () {});
        if (Math.abs(fc.audio.currentTime - want) > 0.3) fc.audio.currentTime = want;
      } else if (!fc.audio.paused) {
        fc.audio.pause();
      }
    }
  }
}

// ---------------------------------------------------------------- RF chart
let selectedObj = -1;
let rfWindowMode = "600";
const chartCanvas = el("rf-chart");
const chartCtx = chartCanvas.getContext("2d");

function drawChart(now) {
  const W = chartCanvas.width, H = chartCanvas.height;
  chartCtx.clearRect(0, 0, W, H);
  chartCtx.font = "10px monospace";
  if (selectedObj < 0) {
    chartCtx.fillStyle = "#6b7480";
    chartCtx.fillText("click a truth entity to inspect its RF", 10, H / 2);
    el("rf-target").textContent = "";
    return;
  }
  const o = MW.objects[selectedObj];
  el("rf-target").textContent = "· " + o.id;
  let t0, t1;
  if (rfWindowMode === "full") {
    t0 = o.t[0];
    t1 = o.t[o.t.length - 1];
  } else {
    t1 = now;
    t0 = now - CHART_WINDOW_S;
  }
  if (t1 - t0 < 1) t1 = t0 + 1;

  // gather series
  const series = [];
  let pmin = Infinity, pmax = -Infinity;
  for (const s of MW.sensors) {
    const rec = MW.rf[s.id];
    if (!rec) continue;
    const pts = [];
    for (let i = 0; i < rec.t.length; i++) {
      if (rec.obj[i] !== selectedObj) continue;
      const t = rec.t[i];
      if (t < t0 || t > t1) continue;
      pts.push([t, rec.pwr[i], rec.los[i]]);
      if (rec.pwr[i] < pmin) pmin = rec.pwr[i];
      if (rec.pwr[i] > pmax) pmax = rec.pwr[i];
    }
    if (pts.length) series.push({ id: s.id, pts: pts });
  }
  if (!series.length) {
    chartCtx.fillStyle = "#6b7480";
    chartCtx.fillText("no RF records for " + o.id + " in window", 10, H / 2);
    return;
  }
  if (pmax - pmin < 10) { pmax += 5; pmin -= 5; }
  const pad = { l: 34, r: 6, t: 8, b: 14 };
  const X = t => pad.l + ((t - t0) / (t1 - t0)) * (W - pad.l - pad.r);
  const Y = p => pad.t + ((pmax - p) / (pmax - pmin)) * (H - pad.t - pad.b);

  // grid + axes
  chartCtx.strokeStyle = "#2a2f36";
  chartCtx.fillStyle = "#6b7480";
  for (let k = 0; k <= 4; k++) {
    const p = pmin + ((pmax - pmin) * k) / 4;
    chartCtx.beginPath();
    chartCtx.moveTo(pad.l, Y(p));
    chartCtx.lineTo(W - pad.r, Y(p));
    chartCtx.stroke();
    chartCtx.fillText(p.toFixed(0), 2, Y(p) + 3);
  }
  chartCtx.fillText(fmtClock(t0), pad.l, H - 3);
  chartCtx.fillText(fmtClock(t1), W - pad.r - 92, H - 3);

  // one line per rf sensor
  for (const se of series) {
    const hex = classColor(rfSensors.findIndex(function (s) { return s.id === se.id; }));
    const col = cssColor(hex);
    chartCtx.strokeStyle = col;
    chartCtx.fillStyle = col;
    chartCtx.beginPath();
    se.pts.forEach(function (p, i) {
      if (i === 0) chartCtx.moveTo(X(p[0]), Y(p[1]));
      else chartCtx.lineTo(X(p[0]), Y(p[1]));
    });
    chartCtx.stroke();
    for (const p of se.pts) {
      chartCtx.beginPath();
      chartCtx.arc(X(p[0]), Y(p[1]), 2.2, 0, Math.PI * 2);
      if (p[2]) {
        chartCtx.fill();
      } else {
        chartCtx.strokeStyle = col;
        chartCtx.stroke(); // NLOS: hollow
      }
    }
    chartCtx.fillText(se.id, X(se.pts[se.pts.length - 1][0]) + 4, Y(se.pts[se.pts.length - 1][1]) + 3);
  }

  // cursor at now
  if (now >= t0 && now <= t1) {
    chartCtx.strokeStyle = "#ffb000";
    chartCtx.beginPath();
    chartCtx.moveTo(X(now), pad.t);
    chartCtx.lineTo(X(now), H - pad.b);
    chartCtx.stroke();
  }
}

viewer.selectedEntityChanged.addEventListener(function (ent) {
  if (ent && ent._objIdx !== undefined) {
    selectedObj = ent._objIdx;
    drawChart(nowT());
  }
});

// ---------------------------------------------------------------- panels
function buildLegend() {
  const host = el("legend");
  for (const side of Object.keys(SIDE_COLORS)) {
    host.insertAdjacentHTML(
      "beforeend",
      '<div class="item"><span class="swatch" style="background:' + SIDE_COLORS[side] +
        '"></span>side · ' + esc(side) + "</div>"
    );
  }
  MW.classes.forEach(function (c, i) {
    host.insertAdjacentHTML(
      "beforeend",
      '<div class="item"><span class="swatch" style="background:' + classColor(i) +
        '"></span>class · ' + esc(c) + "</div>"
    );
  });
}

function buildKeyMoments() {
  const host = el("keymoments");
  for (const ev of MW.events) {
    const li = document.createElement("li");
    li.innerHTML = '<span class="kt">' + fmtClock(ev.t) + "</span>" + esc(ev.label);
    li.addEventListener("click", function () {
      clock.currentTime = TIME0(ev.t);
      const words = ev.label.split(/[\s:,]+/);
      const o = MW.objects.find(function (ob) { return words.indexOf(ob.id) >= 0; });
      if (o) {
        viewer.flyTo(entitiesByObj[MW.objects.indexOf(o)], { duration: 1.2 }).catch(function () {});
      }
    });
    host.appendChild(li);
  }
}

function updateStats() {
  const parts = [];
  for (const s of MW.sensors) {
    const rec = MW.rf[s.id];
    if (rec) parts.push(s.id + ": " + rec.t.length + " rec");
  }
  const errs = MW.fixes.err.filter(function (e) { return e !== null; }).sort(function (a, b) { return a - b; });
  const med = errs.length ? errs[Math.floor(errs.length / 2)] : null;
  parts.push("fixes: " + MW.fixes.t.length);
  parts.push("median fix err: " + (med === null ? "n/a" : med + " m"));
  el("stats").innerHTML = parts.map(esc).join("<br>");
}

function renderAudit() {
  const host = el("audit");
  if (!MW.audit) {
    host.textContent = "audit not run yet";
    return;
  }
  const rows = [];
  const checks = MW.audit.checks;
  if (Array.isArray(checks)) {
    for (const c of checks) {
      const name = c.name || c.check || c.title || "check";
      const ok = c.pass !== undefined ? c.pass : c.ok !== undefined ? c.ok : c.status;
      rows.push([name, ok]);
    }
  } else if (checks && typeof checks === "object") {
    for (const k of Object.keys(checks)) rows.push([k, checks[k]]);
  } else {
    for (const k of Object.keys(MW.audit)) rows.push([k, MW.audit[k]]);
  }
  host.innerHTML = rows
    .map(function (r) {
      const ok = r[1] === true || r[1] === "PASS" || r[1] === "pass";
      const cls = ok ? "pass" : "fail";
      return '<div class="' + cls + '">' + (ok ? "PASS" : "FAIL") + " · " + esc(r[0]) + "</div>";
    })
    .join("");
}

// layer toggles
const lobOn = {};
const rfSensors = MW.sensors.filter(function (s) { return MW.rf[s.id]; });
for (const s of rfSensors) {
  lobOn[s.id] = true;
  shadowOn[s.id] = false;
  el("lob-toggles").insertAdjacentHTML(
    "beforeend",
    '<label><input type="checkbox" data-sid="' + esc(s.id) + '" checked> LOB ' + esc(s.id) + "</label><br>"
  );
  el("shadow-toggles").insertAdjacentHTML(
    "beforeend",
    '<label><input type="checkbox" data-sid="' + esc(s.id) + '"> shadow ' + esc(s.id) + "</label><br>"
  );
}
el("lob-toggles").addEventListener("change", function (e) {
  if (e.target.dataset.sid) lobOn[e.target.dataset.sid] = e.target.checked;
});
el("shadow-toggles").addEventListener("change", function (e) {
  if (e.target.dataset.sid) {
    shadowOn[e.target.dataset.sid] = e.target.checked;
    rebuildShadows();
  }
});
let hideFA = false;
el("tgl-fa").addEventListener("change", function (e) { hideFA = e.target.checked; });
el("agl-slider").addEventListener("input", function (e) {
  aglThreshold = Number(e.target.value);
  el("agl-value").textContent = e.target.value;
  rebuildShadows();
});
el("imagery-toggle").addEventListener("click", function (e) {
  const b = e.target.closest("button");
  if (!b) return;
  for (const x of this.querySelectorAll("button")) x.classList.remove("active");
  b.classList.add("active");
  setImagery(b.dataset.img);
});
el("rf-window").addEventListener("click", function (e) {
  const b = e.target.closest("button");
  if (!b) return;
  for (const x of this.querySelectorAll("button")) x.classList.remove("active");
  b.classList.add("active");
  rfWindowMode = b.dataset.win;
  drawChart(nowT());
});
for (const b of document.querySelectorAll(".collapse-btn")) {
  b.addEventListener("click", function () {
    el(this.dataset.target).classList.toggle("collapsed");
  });
}

// ---------------------------------------------------------------- view modes
let viewMode = "both";
function applyViewMode() {
  const truthVisible = viewMode !== "sensor" && el("tgl-truth").checked;
  for (const e of truthEntities) e.show = truthVisible;
  for (const s of sensorEntities) {
    const vis = viewMode !== "truth";
    s.mark.show = vis;
    s.mast.show = vis;
  }
  lobCollection.show = viewMode !== "truth";
  errCollection.show = viewMode === "both" && el("tgl-err").checked;
  rebuildShadows();
}
el("view-mode").addEventListener("click", function (e) {
  const b = e.target.closest("button");
  if (!b) return;
  for (const x of this.querySelectorAll("button")) x.classList.remove("active");
  b.classList.add("active");
  viewMode = b.dataset.mode;
  applyViewMode();
});
el("tgl-truth").addEventListener("change", applyViewMode);
el("tgl-fixes").addEventListener("change", applyViewMode);
el("tgl-err").addEventListener("change", applyViewMode);

// ---------------------------------------------------------------- tick loop
let lastFeedWall = 0;
clock.onTick.addEventListener(function () {
  const now = nowT();
  el("utc-clock").textContent = "· " + fmtClock(now);
  rebuildLobs(now);
  if (viewMode !== "truth" && el("tgl-fixes").checked) rebuildFixes(now);
  else {
    for (const e of fixPool) e.show = false;
    errCollection.removeAll();
  }
  // dead sensors go grey after dead_t
  for (const s of sensorEntities) {
    const dead = s.sensor.dead_t !== null && now > s.sensor.dead_t;
    if (dead !== s.dead) {
      s.dead = dead;
      const col = cssColor(dead ? GREY : AMBER);
      s.mark.point.color = col;
      s.mark.label.fillColor = col;
      s.mast.polyline.material = dead ? cssColor(GREY, 0.4) : cssColor(AMBER, 0.55);
    }
  }
  const wall = Date.now();
  if (wall - lastFeedWall > 250) {
    lastFeedWall = wall;
    updateFeeds(now);
    drawChart(now);
  }
});

// ---------------------------------------------------------------- init
el("scen-name").textContent = "· " + (MW.scenario.label || MW.scenario.name) + " ·";
buildLegend();
buildKeyMoments();
buildFeeds();
updateStats();
renderAudit();
applyViewMode();
drawChart(0);
