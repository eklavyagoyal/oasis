import { GLYPHS } from "./glyphs.js";

// Map markers: a dark glass disc with a coloured ring and soft glow around a white catalog glyph.
// Drawn as a 128 px SVG so it stays sharp at any zoom; one image per (glyph, colour, state), cached.
const cache = new Map();

export function badge(glyph, hex, dim = false) {
  const key = `${glyph}|${hex}|${dim}`;
  if (!cache.has(key)) {
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 64 64"><defs><radialGradient id="g" cx="50%" cy="34%" r="66%"><stop offset="0" stop-color="${hex}" stop-opacity="${dim ? 0.1 : 0.42}"/><stop offset="0.72" stop-color="#0b0e13" stop-opacity="0.93"/><stop offset="1" stop-color="#06080b" stop-opacity="0.97"/></radialGradient><filter id="b" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="2.4"/></filter></defs><circle cx="32" cy="32" r="26" fill="none" stroke="${hex}" stroke-opacity="${dim ? 0.12 : 0.6}" stroke-width="4" filter="url(#b)"/><circle cx="32" cy="32" r="23" fill="url(#g)" stroke="${hex}" stroke-opacity="${dim ? 0.45 : 1}" stroke-width="2.2"/><circle cx="32" cy="32" r="19.6" fill="none" stroke="#ffffff" stroke-opacity="0.14" stroke-width="0.8"/><g transform="translate(20 20)" fill="none" stroke="${dim ? "#8e96a3" : "#f4f1ea"}" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">${GLYPHS[glyph] ?? ""}</g></svg>`;
    cache.set(key, "data:image/svg+xml," + encodeURIComponent(svg));
  }
  return cache.get(key);
}
