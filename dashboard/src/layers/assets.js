import { heightAt, upperBound } from "../data.js";
import { color, palette } from "../globe.js";
const C = window.Cesium;

// High-value assets (protected sites with approach 1 km / impact 100 m rings, response teams) and sensor
// sites, drawn with the asset-catalog icon set (public/icons, Tabler, MIT; white strokes tinted here).
export const ICONS = {
  power_station: "building-factory-2", water_works: "droplet-cog", hospital: "building-hospital",
  site: "building-factory-2", ad_team: "users-group", handheld_team: "users-group",
  ad_battery: "shield-bolt", patriot: "shield-bolt", iris_t: "shield-bolt", nasams: "shield-bolt",
  gerbera: "plane-inflight", interceptor: "drone", octopus: "drone", jedi: "drone",
  dji_mavic3: "drone", fpv_analog: "drone", fpv_fiber: "drone",
  rf_df: "antenna", rf_iq: "antenna", remote_id: "antenna", radar: "radar", camera: "device-cctv",
  microphone: "microphone-2",
};
export const iconUrl = (type) => (ICONS[type] ? `./icons/${ICONS[type]}.svg` : null);
const TONE = { reached: "hostile", approached: "rf", alerted: "rf", responding: "rf" };

function statusAt(a, t) {
  const i = upperBound(a.status.t, t) - 1;
  return i >= 0 ? a.status.s[i] : a.kind === "site" ? "not reached" : "available";
}

export function createAssets(globe, state) {
  const source = new C.CustomDataSource("assets");
  globe.viewer.dataSources.add(source);
  const items = (state.data.assets || []).map((a) => {
    const ground = heightAt(state.data.terrain, a.lon, a.lat);
    const base = palette[a.side] ?? palette.system;
    const entity = source.entities.add({
      id: `asset:${a.id}`,
      position: globe.position(a.lon, a.lat, ground + 4),
      billboard: {
        image: iconUrl(a.type) ?? iconUrl(a.kind === "site" ? "site" : "ad_team"),
        color: color(base),
        width: 26,
        height: 26,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
      label: {
        text: a.id,
        font: '12px "Geist Mono"',
        fillColor: color(base),
        pixelOffset: new C.Cartesian2(16, -2),
        horizontalOrigin: C.HorizontalOrigin.LEFT,
        outlineColor: color(palette.void),
        outlineWidth: 3,
        style: C.LabelStyle.FILL_AND_OUTLINE,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
    });
    const rings = a.kind !== "site" ? [] : [1000, 100].map((r) =>
      source.entities.add({
        position: globe.position(a.lon, a.lat, ground),
        ellipse: {
          semiMajorAxis: r,
          semiMinorAxis: r,
          height: globe.displayHeight(a.lon, a.lat, ground + 1),
          material: color(r === 100 ? palette.hostile : palette.rf, r === 100 ? 0.08 : 0.035),
          outline: true,
          outlineColor: color(r === 100 ? palette.hostile : palette.rf, 0.6),
        },
      }),
    );
    return { a, entity, rings, ground, base };
  });
  // Sensor sites: one icon per mast (mounted sensors share it), struck dark once destroyed.
  const masts = new Map();
  for (const s of state.data.sensors || []) {
    if (!iconUrl(s.type)) continue;
    const key = `${s.lat.toFixed(5)},${s.lon.toFixed(5)}`;
    if (masts.has(key)) masts.get(key).ids.push(s.id);
    else masts.set(key, { s, ids: [s.id] });
  }
  const sites = [...masts.values()].map(({ s, ids }) => ({
    s,
    entity: source.entities.add({
      id: `sensor-site:${s.id}`,
      position: globe.position(s.lon, s.lat, s.alt),
      billboard: {
        image: iconUrl(s.type),
        color: color(palette.rf),
        width: 22,
        height: 22,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
      label: {
        text: ids.join(" · "),
        font: '11px "Geist Mono"',
        fillColor: color(palette.rf),
        pixelOffset: new C.Cartesian2(14, -2),
        horizontalOrigin: C.HorizontalOrigin.LEFT,
        outlineColor: color(palette.void),
        outlineWidth: 3,
        style: C.LabelStyle.FILL_AND_OUTLINE,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
    }),
  }));
  return {
    update() {
      for (const { s, entity } of sites) {
        const dead = s.dead_t != null && state.t > s.dead_t;
        entity.position = globe.position(s.lon, s.lat, s.alt);
        entity.billboard.color = color(dead ? palette.hostile : palette.rf, dead ? 0.5 : 1);
      }
      for (const { a, entity, rings, ground, base } of items) {
        const s = statusAt(a, state.t);
        const tone = palette[TONE[s]] ?? base;
        entity.position = globe.position(a.lon, a.lat, ground + 4);
        entity.label.text = `${a.id} · ${a.label.toUpperCase()} · ${s.toUpperCase()}`;
        entity.label.fillColor = color(tone);
        for (const ring of rings) ring.ellipse.height = globe.displayHeight(a.lon, a.lat, ground + 1);
      }
    },
  };
}
