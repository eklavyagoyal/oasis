import { upperBound, heightAt, sample } from "../data.js";
import { color, ll, palette } from "../globe.js";
const C = window.Cesium;
export const classColor = () => palette.rf;
function poolLine(collection, width = 1.5) {
  return collection.add({
    positions: [C.Cartesian3.ZERO, C.Cartesian3.UNIT_X],
    width,
    show: false,
    material: C.Material.fromType("PolylineGlow", { color: color(palette.rf), glowPower: 0.14, taperPower: 1 }),
  });
}
export function createRF(globe, state) {
  const { scene } = globe,
    data = state.data;
  const rays = scene.primitives.add(new C.PolylineCollection());
  const pulses = scene.primitives.add(new C.PolylineCollection());
  const ellipses = scene.primitives.add(new C.PolylineCollection());
  const deltas = scene.primitives.add(new C.PolylineCollection());
  const points = scene.primitives.add(new C.PointPrimitiveCollection());
  const labels = scene.primitives.add(new C.LabelCollection());
  const rayPool = Array.from({ length: 256 }, () => poolLine(rays));
  const pulsePool = Array.from({ length: 256 }, () => poolLine(pulses, 2.4));
  const ellipsePool = Array.from({ length: 40 }, () => poolLine(ellipses, 1));
  const deltaPool = Array.from({ length: 40 }, () => poolLine(deltas, 1.2));
  const pointPool = Array.from({ length: 40 }, () =>
    points.add({
      position: C.Cartesian3.ZERO,
      pixelSize: 4,
      color: color(palette.rf),
      show: false,
      disableDepthTestDistance: Number.POSITIVE_INFINITY,
    }),
  );
  const labelPool = Array.from({ length: 40 }, () =>
    labels.add({
      position: C.Cartesian3.ZERO,
      text: "",
      font: '11px "Geist Mono"',
      showBackground: true,
      backgroundColor: color(palette.void, 0.8),
      backgroundPadding: new C.Cartesian2(8, 5),
      fillColor: C.Color.WHITE,
      outlineColor: color(palette.void),
      outlineWidth: 3,
      style: C.LabelStyle.FILL_AND_OUTLINE,
      pixelOffset: new C.Cartesian2(5, -10),
      show: false,
      disableDepthTestDistance: Number.POSITIVE_INFINITY,
    }),
  );
  const ripples = scene.primitives.add(new C.PolylineCollection());
  const ripplePool = Array.from({length: 40}, () => poolLine(ripples, 2.5));
  let relief = state.exaggeration;
  const positionCache = new Map();
  const sensors = new Map(data.sensors.map((s) => [s.id, s]));
  function rayPositions(s, bearing) {
    const r = (bearing * Math.PI) / 180,
      length = data.scenario.area.size_km * 650,
      positions = [globe.position(s.lon, s.lat, s.alt)];
    for (let step = 1; step <= 16; step++) {
      const dist = (length * step) / 16,
        lat = s.lat + (Math.cos(r) * dist) / 111320,
        lon =
          s.lon +
          (Math.sin(r) * dist) / (111320 * Math.cos((s.lat * Math.PI) / 180));
      if (
        lon < data.terrain.west ||
        lon > data.terrain.east ||
        lat < data.terrain.south ||
        lat > data.terrain.north
      )
        break;
      positions.push(globe.position(lon, lat, heightAt(data.terrain, lon, lat) + 18));
    }
    return positions.length > 1
      ? positions
      : [globe.position(s.lon, s.lat, s.alt), globe.position(s.lon, s.lat, s.alt + 0.01)];
  }
  function update() {
    if (relief !== state.exaggeration) { relief = state.exaggeration; positionCache.clear(); }
    const sensorVisible = state.mode !== "god";
    rays.show = sensorVisible && state.rays;
    pulses.show = rays.show;
    ellipses.show = sensorVisible && state.fixes;
    points.show = ellipses.show;
    ripples.show = ellipses.show;
    deltas.show = state.mode === "delta" && state.fixes && state.truth;
    labels.show = deltas.show;
    let count = 0;
    if (rays.show)
      for (const [id, r] of Object.entries(data.rf)) {
        const sensor = sensors.get(id);
        if (
          !state.receivers.has(id) ||
          (sensor.dead_t != null && state.t > sensor.dead_t)
        )
          continue;
        const start = upperBound(r.t, state.t - 3),
          end = upperBound(r.t, state.t);
        for (let i = end - 1; i >= start && count < rayPool.length; i--) {
          const key = `${id}:${i}`,
            line = rayPool[count++];
          if (!positionCache.has(key))
            positionCache.set(key, rayPositions(sensor, r.brg[i]));
          line.positions = positionCache.get(key);
          const age = state.t - r.t[i],
            fade = Math.max(0.08, 1 - age / 3),
            snr = Math.max(0.25, Math.min(1, (r.snr[i] + 5) / 30));
          const nlos = state.mode === "delta" && !r.los[i];
          line.material.uniforms.color = color(
            classColor(r.cls[i]),
            fade * snr * (nlos ? 0.22 : 0.78),
          );
          line.width = nlos ? 1 : 1.5;
          line.show = true;
          const pulse = pulsePool[count - 1],
            positions = line.positions;
          pulse.show =
            age < 0.3 &&
            !matchMedia("(prefers-reduced-motion: reduce)").matches;
          if (pulse.show) {
            const head = Math.min(
                positions.length - 1,
                Math.max(0.01, (age / 0.3) * (positions.length - 1)),
              ),
              tail = Math.max(0, head - 1.5);
            const at = (v) => {
              const a = Math.floor(v),
                b = Math.min(a + 1, positions.length - 1);
              return C.Cartesian3.lerp(
                positions[a],
                positions[b],
                v - a,
                new C.Cartesian3(),
              );
            };
            pulse.positions = [at(tail), at(head)];
            pulse.material.uniforms.color = color(classColor(r.cls[i]), 0.9);
          }
        }
      }
    for (let i = count; i < rayPool.length; i++) {
      rayPool[i].show = false;
      pulsePool[i].show = false;
    }
    if (positionCache.size > 1500) positionCache.clear();
    const f = data.fixes,
      first = upperBound(f.t, state.t - 6),
      end = upperBound(f.t, state.t);
    let n = 0,
      latestSelected = -1;
    if (state.mode === "delta")
      for (let i = end - 1; i >= 0 && f.t[i] >= state.t - 60; i--) {
        if (data.objects[f.obj[i]]?.id === state.selected) {
          latestSelected = i;
          break;
        }
      }
    const indices = Array.from({ length: end - first }, (_, j) => end - 1 - j);
    if (latestSelected >= 0 && !indices.includes(latestSelected))
      indices.unshift(latestSelected);
    if (ellipses.show)
      for (const i of indices.slice(0, ellipsePool.length)) {
        const lon = f.lon[i],
          lat = f.lat[i];
        if (
          lon < data.terrain.west ||
          lon > data.terrain.east ||
          lat < data.terrain.south ||
          lat > data.terrain.north
        )
          continue;
        const alt = heightAt(data.terrain, lon, lat) + 10,
          rotation = (f.orient[i] * Math.PI) / 180,
          verts = [];
        for (let j = 0; j <= 48; j++) {
          const angle = (j / 48) * Math.PI * 2,
            a = Math.cos(angle) * f.smaj[i],
            b = Math.sin(angle) * f.smin[i];
          const x = a * Math.sin(rotation) + b * Math.cos(rotation),
            y = a * Math.cos(rotation) - b * Math.sin(rotation);
          const lo = lon + x / (111320 * Math.cos((lat * Math.PI) / 180)),
            la = lat + y / 111320;
          verts.push(globe.position(lo, la, heightAt(data.terrain, lo, la) + 12));
        }
        const line = ellipsePool[n],
          point = pointPool[n],
          delta = deltaPool[n],
          label = labelPool[n];
        const fade = Math.max(
          i === latestSelected ? 0.45 : 0.1,
          1 - (state.t - f.t[i]) / 6,
        );
        line.positions = verts;
        line.show = true;
        line.material.uniforms.color = color(palette.rf, fade * 0.7);
        point.position = globe.position(lon, lat, alt);
        point.show = true;
        point.id = { type: "fix", index: i };
        const truth =
          f.obj[i] >= 0 ? sample(data.objects[f.obj[i]], f.t[i]) : null;
        delta.show = !!truth && deltas.show;
        label.show =
          !!truth &&
          deltas.show &&
          data.objects[f.obj[i]]?.id === state.selected &&
          n < 2;
        if (truth) {
          const a = globe.position(lon, lat, alt),
            b = globe.position(truth.lon, truth.lat, truth.alt);
          delta.positions = [a, b];
          delta.material.uniforms.color = color(palette.truth, fade * 0.72);
          label.position = C.Cartesian3.midpoint(a, b, new C.Cartesian3());
          label.text =
            f.err[i] == null
              ? "UNSCORED"
              : `${Math.round(f.err[i])} m Δ${state.t - f.t[i] > 6 ? ` / ${Math.round(state.t - f.t[i])} s OLD` : ""}`;
        }
        const ripple = ripplePool[n], age = state.t - f.t[i];
        ripple.show = age >= 0 && age < 1.2 && !matchMedia('(prefers-reduced-motion: reduce)').matches;
        if (ripple.show) {
          const centre = globe.position(lon, lat, alt);
          ripple.positions = verts.map(v => C.Cartesian3.lerp(centre, v, 1 + age * 0.35, new C.Cartesian3()));
          ripple.material.uniforms.color = color(palette.rf, (1 - age / 1.2) * 0.6);
        }
        n++;
      }
    for (let i = n; i < ellipsePool.length; i++) {
      ellipsePool[i].show = false;
      ripplePool[i].show = false;
      pointPool[i].show = false;
      deltaPool[i].show = false;
      labelPool[i].show = false;
    }
  }
  return { update };
}
