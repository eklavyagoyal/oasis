import { heightAt, upperBound } from "../data.js";
import { color, palette } from "../globe.js";
import { badge } from "./badge.js";
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
// Markers follow the map: ~1x at the overview distance, up to 1.7x close in, never below 0.8x.
export const ICON_SCALE = new C.NearFarScalar(2.0e3, 1.7, 5.0e4, 0.8);
export const LABEL_SCALE = new C.NearFarScalar(2.0e3, 1.3, 5.0e4, 0.9);
const NEAR_ONLY = new C.DistanceDisplayCondition(0, 1.2e4); // detail lines appear once you zoom in
const OUTLINE = { outlineWidth: 2, style: C.LabelStyle.FILL_AND_OUTLINE, horizontalOrigin: C.HorizontalOrigin.LEFT,
  showBackground: true, backgroundColor: new C.Color(0.024, 0.031, 0.043, 0.8), backgroundPadding: new C.Cartesian2(8, 5),
  pixelOffsetScaleByDistance: ICON_SCALE, scaleByDistance: LABEL_SCALE,
  disableDepthTestDistance: Number.POSITIVE_INFINITY };
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
        image: badge(ICONS[a.type] ?? (a.kind === "site" ? "building-factory-2" : "users-group"), base),
        width: 46,
        height: 46,
        scaleByDistance: ICON_SCALE,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
      label: {
        text: a.id,
        font: '600 13px "Geist Mono"',
        fillColor: color(base),
        pixelOffset: new C.Cartesian2(28, -6),
        outlineColor: color(palette.void),
        ...OUTLINE,
      },
    });
    const detail = source.entities.add({
      position: globe.position(a.lon, a.lat, ground + 4),
      label: {
        text: "",
        font: '11px "Geist Mono"',
        fillColor: color(base),
        pixelOffset: new C.Cartesian2(28, 9),
        outlineColor: color(palette.void),
        distanceDisplayCondition: NEAR_ONLY,
        ...OUTLINE,
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
    return { a, entity, detail, rings, ground, base };
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
        image: badge(ICONS[s.type], palette.system),
        width: 38,
        height: 38,
        scaleByDistance: ICON_SCALE,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
      label: {
        text: ids.join(" · "),
        font: '12px "Geist Mono"',
        fillColor: color(palette.system),
        pixelOffset: new C.Cartesian2(24, -2),
        outlineColor: color(palette.void),
        ...OUTLINE,
      },
    }),
    ids,
  }));
  return {
    update() {
      for (const { s, entity, ids } of sites) {
        const dead = s.dead_t != null && state.t > s.dead_t,
          tone = color(dead ? palette.neutral : palette.system, dead ? 0.55 : 1);
        entity.position = globe.position(s.lon, s.lat, s.alt);
        const img = badge(ICONS[s.type], dead ? palette.neutral : palette.system, dead);
        if (entity.billboard.image.getValue() !== img) entity.billboard.image = img;
        entity.label.fillColor = tone;
        entity.label.text = `${ids.join(" · ")}${dead ? " / DOWN" : ""}`;
      }
      for (const { a, entity, detail, rings, ground, base } of items) {
        const s = statusAt(a, state.t);
        const tone = palette[TONE[s]] ?? base;  // status shows as colour at any zoom, as text up close
        entity.position = detail.position = globe.position(a.lon, a.lat, ground + 4);
        const img = badge(ICONS[a.type] ?? (a.kind === "site" ? "building-factory-2" : "users-group"), tone);
        if (entity.billboard.image.getValue() !== img) entity.billboard.image = img;
        entity.label.fillColor = detail.label.fillColor = color(tone);
        detail.label.text = `${a.label.toUpperCase()} · ${s.toUpperCase()}`;
        for (const ring of rings) ring.ellipse.height = globe.displayHeight(a.lon, a.lat, ground + 1);
      }
    },
  };
}
