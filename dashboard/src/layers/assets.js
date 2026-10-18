import { heightAt, upperBound } from "../data.js";
import { color, palette } from "../globe.js";
const C = window.Cesium;

// High-value assets: protected sites (approach 1 km / impact 100 m rings) and response teams,
// labelled with the status C2 had at the current replay time.
const ICONS = {
  site: '<path d="M16 3 28 10v12L16 29 4 22V10Z"/><circle cx="16" cy="16" r="4"/>',
  response: '<path d="M16 3 27 7v8c0 7-5 12-11 14C10 27 5 22 5 15V7Z"/><path d="m11 16 4 4 7-8"/>',
};
const TONE = { reached: "hostile", approached: "rf", alerted: "rf", responding: "rf" };

function icon(kind, stroke) {
  return (
    "data:image/svg+xml," +
    encodeURIComponent(
      `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 32 32"><g fill="none" stroke="${stroke}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">${ICONS[kind]}</g></svg>`,
    )
  );
}

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
        image: icon(a.kind, base),
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
  return {
    update() {
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
