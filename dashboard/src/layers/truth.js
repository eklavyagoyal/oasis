import { sample, heightAt, upperBound } from "../data.js";
import { ll, color, palette } from "../globe.js";
import { ICON_SCALE, ICONS, LABEL_SCALE } from "./assets.js";
import { airframeBadge, badge } from "./badge.js";
const C = window.Cesium;
function glyph(o) {
  const shape =
    o.kind === "operator"
      ? '<path d="M16 29S6 19 6 12a10 10 0 0 1 20 0c0 7-10 17-10 17Z"/><circle cx="16" cy="12" r="3"/>'
      : o.kind === "emitter"
        ? '<path d="M16 6v22M11 11a7 7 0 0 0 0 10M21 11a7 7 0 0 1 0 10M7 7a13 13 0 0 0 0 18M25 7a13 13 0 0 1 0 18"/>'
        : o.kind === "bird"
          ? '<path d="m3 17 6-4 7 6 7-6 6 4M9 7l4-2 4 3"/>'
          : /shahed/.test(o.type)
            ? '<path d="m16 3 13 25-13-7-13 7Z"/>'
            : /supercam|wing/.test(o.type)
              ? '<path d="M16 2v27M3 18l13-7 13 7M11 28l5-3 5 3"/>'
              : '<path d="m9 9 14 14m0-14L9 23"/><circle cx="8" cy="8" r="4"/><circle cx="24" cy="8" r="4"/><circle cx="8" cy="24" r="4"/><circle cx="24" cy="24" r="4"/><path d="m16 3-3 4h6Z"/>';
  return (
    "data:image/svg+xml," +
    encodeURIComponent(
      `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 32 32"><defs><filter id="halo" x="-40%" y="-40%" width="180%" height="180%"><feDropShadow dx="0" dy="0" stdDeviation="1.6" flood-color="${palette.void}" flood-opacity="1"/></filter></defs><g filter="url(#halo)" fill="none" stroke="${palette[o.side] ?? palette.truth}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">${shape}</g></svg>`,
    )
  );
}
export function createTruth(globe, state) {
  const { viewer, scene } = globe,
    // sites and response teams are drawn by the assets layer
    data = { ...state.data, objects: state.data.objects.filter((o) => !['site', 'response'].includes(o.kind)) };
  const source = new C.CustomDataSource("ground truth");
  viewer.dataSources.add(source);
  const entities = new Map(),
    halos = scene.primitives.add(new C.PointPrimitiveCollection());
  const velocity = scene.primitives.add(new C.PolylineCollection());
  for (const object of data.objects) {
    if (!object.t.length) continue;
    const position = new C.SampledPositionProperty();
    // Packed samples avoid a large array of temporary JulianDate objects.
    const packed = [];
    for (let i = 0; i < object.t.length; i++) {
      const p = globe.position(object.lon[i], object.lat[i], object.alt[i]);
      packed.push(object.t[i], p.x, p.y, p.z);
    }
    position.addSamplesPackedArray(packed, viewer.clock.startTime);
    const entity = source.entities.add({
      id: `truth:${object.id}`,
      name: object.id,
      position,
      availability: new C.TimeIntervalCollection([
        new C.TimeInterval({
          start: C.JulianDate.addSeconds(
            viewer.clock.startTime,
            object.t[0],
            new C.JulianDate(),
          ),
          stop: C.JulianDate.addSeconds(
            viewer.clock.startTime,
            object.t.at(-1),
            new C.JulianDate(),
          ),
        }),
      ]),
      billboard: {
        image: object.kind === "drone"
          ? airframeBadge(object.type,
              { hostile: palette.hostile, friendly: palette.friendly }[object.side] ?? palette.neutral)
          : glyph(object),
        width: object.kind === "drone" ? 46 : 30,
        height: object.kind === "drone" ? 46 : 30,
        scaleByDistance: ICON_SCALE,
        heightReference: C.HeightReference.NONE,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
      label: {
        text: object.id.toUpperCase(),
        font: '600 12px "Geist Mono"',
        showBackground: true,
        backgroundColor: new C.Color(0.024, 0.031, 0.043, 0.8),
        backgroundPadding: new C.Cartesian2(7, 4),
        scaleByDistance: LABEL_SCALE,
        pixelOffsetScaleByDistance: ICON_SCALE,
        fillColor: color(palette.unknown),
        outlineColor: color(palette.void),
        outlineWidth: 3,
        style: C.LabelStyle.FILL_AND_OUTLINE,
        pixelOffset: new C.Cartesian2(24, -18),
        horizontalOrigin: C.HorizontalOrigin.LEFT,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
    });
    entities.set(object.id, entity);
  }
  const trails = scene.primitives.add(new C.PolylineCollection());
  const trailPool = new Map(
    data.objects
      .filter((o) => ["drone", "bird"].includes(o.kind))
      .map((o) => [
        o.id,
        Array.from({ length: 8 }, (_, i) =>
          trails.add({
            positions: [C.Cartesian3.ZERO, C.Cartesian3.UNIT_X],
            show: false,
            width: 2.2,
            material: C.Material.fromType("PolylineGlow", {
              color: color(palette.truth, 0.06 + (i / 7) * 0.56),
              glowPower: 0.13,
              taperPower: 1,
            }),
          }),
        ),
      ]),
  );
  let relief = state.exaggeration;
  const ticks = new Map(),
    rings = new Map();
  for (const object of data.objects) {
    ticks.set(
      object.id,
      velocity.add({
        positions: [C.Cartesian3.ZERO, C.Cartesian3.UNIT_X],
        width: 1,
        show: false,
        material: C.Material.fromType("Color", {
          color: color(palette.truth, 0.55),
        }),
      }),
    );
    if (object.side === "hostile")
      rings.set(
        object.id,
        halos.add({
          position: C.Cartesian3.ZERO,
          pixelSize: 44,
          color: color(palette.hostile, 0.025),
          outlineColor: color(palette.hostile, 0.18),
          outlineWidth: 1,
          show: false,
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
        }),
      );
  }
  function update() {
    const visible = state.mode !== "operator" && state.truth;
    const opacity = state.layerOpacity ?? 1;
    source.show = visible;
    velocity.show = visible;
    halos.show = visible;
    trails.show = visible;
    if (relief !== state.exaggeration) {
      relief = state.exaggeration;
      for (const o of data.objects) {
        const entity = entities.get(o.id);
        if (!entity) continue;
        const position = new C.SampledPositionProperty(),
          packed = [];
        for (let i = 0; i < o.t.length; i++) {
          const p = globe.position(o.lon[i], o.lat[i], o.alt[i]);
          packed.push(o.t[i], p.x, p.y, p.z);
        }
        position.addSamplesPackedArray(packed, viewer.clock.startTime);
        entity.position = position;
      }
    }
    const priority = data.objects
      .filter((o) => sample(o, state.t))
      .sort(
        (a, b) =>
          (a.id === state.selected ? -10 : a.side === "hostile" ? -1 : 0) -
          (b.id === state.selected ? -10 : b.side === "hostile" ? -1 : 0),
      );
    const labels = new Set(priority.slice(0, 6).map((o) => o.id));
    for (const object of data.objects) {
      const p = sample(object, state.t),
        tick = ticks.get(object.id),
        ring = rings.get(object.id);
      const entity = entities.get(object.id);
      if (entity) {
        entity.label.show =
          labels.has(object.id) && object.id !== state.selected;
        entity.billboard.color = color(palette.truth, opacity);
        entity.label.fillColor = color(palette.unknown, opacity);
        const ahead = object.kind === "drone" && p ? sample(object, state.t + 2) : null;
        if (ahead && (ahead.lon !== p.lon || ahead.lat !== p.lat)) {  // airframe nose along the track
          const heading = Math.atan2((ahead.lon - p.lon) * Math.cos((p.lat * Math.PI) / 180), ahead.lat - p.lat);
          entity.billboard.rotation = viewer.camera.heading - heading;
        }
      }
      const segments = trailPool.get(object.id);
      segments?.forEach((line, i) => {
        const positions = [];
        for (
          let t = state.t - 120 + i * 15;
          t <= state.t - 105 + i * 15;
          t += 3
        ) {
          const at = sample(object, t);
          if (at) positions.push(globe.position(at.lon, at.lat, at.alt));
        }
        line.show = positions.length > 1;
        line.material.uniforms.color = color(
          palette.truth,
          opacity * (0.06 + (i / 7) * 0.56),
        );
        if (line.show) line.positions = positions;
      });
      if (tick) {
        const next = sample(object, state.t + 3);
        tick.show = !!p && !!next;
        if (p && next)
          tick.positions = [
            globe.position(p.lon, p.lat, p.alt),
            globe.position(next.lon, next.lat, next.alt),
          ];
      }
      if (ring) {
        ring.show = !!p;
        if (p) {
          ring.position = globe.position(p.lon, p.lat, p.alt);
          ring.pixelSize = matchMedia("(prefers-reduced-motion: reduce)")
            .matches
            ? 42
            : 42 + 4 * Math.sin(state.t * 2);
        }
      }
    }
    updateReticle();
  }
  function updateReticle() {
    const visible = state.mode !== "operator" && state.truth;
    const reticle = document.querySelector("#selection-reticle");
    const entity = visible ? entities.get(state.selected) : null;
    const pos = entity?.position.getValue(viewer.clock.currentTime);
    if (!pos) {
      reticle.hidden = true;
      return;
    }
    const screen = C.SceneTransforms.worldToWindowCoordinates(scene, pos);
    if (
      !screen ||
      screen.x < 0 ||
      screen.x > scene.canvas.clientWidth ||
      screen.y < 0 ||
      screen.y > scene.canvas.clientHeight
    ) {
      reticle.hidden = true;
      return;
    }
    const p = sample(
      data.objects.find((o) => o.id === state.selected),
      state.t,
    );
    reticle.hidden = false;
    const callout = reticle.querySelector(".reticle-callout");
    const deckLeft = document.querySelector(".right-rail").offsetLeft;
    reticle.classList.toggle(
      "callout-left",
      screen.x > 320 && screen.x + 76 + callout.offsetWidth > deckLeft - 16,
    );
    reticle.style.transform = `translate(${screen.x}px,${screen.y}px)`;
    document.querySelector("#reticle-label").textContent =
      state.selected.toUpperCase();
    const object = data.objects.find((o) => o.id === state.selected),
      prev = sample(object, state.t - 1);
    const speed = prev
      ? Math.hypot(
          (p.lat - prev.lat) * 111320,
          (p.lon - prev.lon) * 111320 * Math.cos((p.lat * Math.PI) / 180),
        )
      : 0;
    const values = document.querySelector("#reticle-values");
    if (values)
      values.textContent = `${Math.round(p.alt - heightAt(data.terrain, p.lon, p.lat))} m AGL  ·  ${speed.toFixed(1)} m/s`;
    const receivers = document.querySelector("#reticle-receivers");
    if (receivers) {
      const oi = data.objects.indexOf(object);
      const seen = Object.entries(data.rf)
        .filter(([id, r]) => {
          const sensor = data.sensors.find((s) => s.id === id);
          if (sensor.dead_t != null && state.t > sensor.dead_t) return false;
          for (
            let i = upperBound(r.t, state.t) - 1;
            i >= 0 && r.t[i] >= state.t - 3;
            i--
          )
            if (r.obj[i] === oi) return true;
          return false;
        })
        .map(([id]) => id);
      receivers.textContent =
        state.mode === "god"
          ? "GROUND TRUTH"
          : seen.length
            ? `DETECTED BY ${seen.join(" · ")}`
            : "NO RECENT RF";
    }
  }
  return { update, updateReticle, entities, source };
}

export function createSensors(globe, state) {
  const source = new C.CustomDataSource("sensors");
  globe.viewer.dataSources.add(source);
  const entries = [];
  for (const s of state.data.sensors.filter((s) =>
    ["rf_df", "microphone"].includes(s.type),
  )) {
    const c = color(palette.system);
    const entity = source.entities.add({
      id: `sensor:${s.id}`,
      position: globe.position(s.lon, s.lat, s.alt),
      polyline: {
        positions: [
          globe.position(s.lon, s.lat, s.ground),
          globe.position(s.lon, s.lat, s.alt),
        ],
        width: 2,
        material: new C.PolylineGlowMaterialProperty({
          color: c,
          glowPower: 0.2,
        }),
      },
      ellipse: {
        semiMajorAxis: 110,
        semiMinorAxis: 110,
        height: globe.displayHeight(s.lon, s.lat, s.ground + 2),
        material: color(palette.system, 0.025),
        outline: true,
        outlineColor: color(palette.system, 0.35),
      },
    });
    entries.push([s, entity]);
  }
  return {
    update() {
      for (const [s, e] of entries) {
        const dead = s.dead_t != null && state.t > s.dead_t,
          c = color(dead ? palette.neutral : palette.system);
        e.position = globe.position(s.lon, s.lat, s.alt);
        e.polyline.positions = [
          globe.position(s.lon, s.lat, s.ground),
          globe.position(s.lon, s.lat, s.alt),
        ];
        e.ellipse.height = globe.displayHeight(s.lon, s.lat, s.ground + 2);
        const dying =
          dead &&
          state.t - s.dead_t < 1.5 &&
          !matchMedia("(prefers-reduced-motion: reduce)").matches;
        if (dying)
          c.alpha = 0.2 + 0.8 * Math.abs(Math.sin((state.t - s.dead_t) * 30));
        e.polyline.material.color = c;
        e.ellipse.outlineColor = c.withAlpha(dead ? 0.1 : 0.3);
        e.ellipse.semiMajorAxis =
          dead || matchMedia("(prefers-reduced-motion: reduce)").matches
            ? 110
            : 105 + 10 * Math.sin(state.t * 1.5);
        e.ellipse.semiMinorAxis = e.ellipse.semiMajorAxis;
      }
    },
  };
}
