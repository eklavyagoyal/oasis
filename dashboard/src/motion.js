import { reducedMotion } from "./theme.js";
const numbers = new WeakMap();
export function countTo(element, value, decimals = 0, unit = "") {
  if (!element || !Number.isFinite(value)) return;
  let entry = numbers.get(element);
  if (
    entry?.target === value &&
    entry.unit === unit &&
    element.firstElementChild === entry.number
  )
    return;
  if (entry) cancelAnimationFrame(entry.frame);
  const start = entry?.value ?? value;
  entry = { target: value, value: start, unit };
  numbers.set(element, entry);
  const number = document.createElement("span"),
    suffix = document.createElement("small");
  entry.number = number;
  suffix.textContent = unit;
  element.replaceChildren(number, suffix);
  const began = performance.now();
  const tick = (now) => {
    const p = reducedMotion() ? 1 : Math.min(1, (now - began) / 320);
    entry.value = start + (value - start) * (1 - Math.pow(1 - p, 4));
    number.textContent = entry.value.toFixed(decimals);
    if (p < 1 && element.isConnected) entry.frame = requestAnimationFrame(tick);
  };
  tick(began);
}
export function createOpening(globe, data) {
  const root = document.querySelector("#opening");
  let active = false,
    timers = [];
  function skip(restoreFocus = false) {
    if (!active) return;
    active = false;
    timers.forEach(clearTimeout);
    timers = [];
    root.hidden = true;
    root.classList.remove("title-visible");
    document.body.classList.remove("opening");
    globe.setIsland(true);
    globe.home(0);
    if (restoreFocus || document.activeElement?.id === "opening-skip")
      document.querySelector("#layers-toggle").focus({ preventScroll: true });
  }
  function start() {
    if (active || reducedMotion()) return;
    active = true;
    root.hidden = false;
    document.body.classList.add("opening");
    const date = new Date(data.scenario.start)
      .toLocaleDateString("en-GB", {
        day: "numeric",
        month: "short",
        year: "numeric",
        timeZone: "UTC",
      })
      .toUpperCase();
    document.querySelector("#opening-subtitle").textContent =
      `${data.scenario.name.replaceAll("-", " ").toUpperCase()} · ${date} · ONE WORLD, EVERY SIGNAL`;
    document.querySelector(".opening-coordinate").textContent =
      `${data.scenario.area.lat.toFixed(4)}° N / ${data.scenario.area.lon.toFixed(4)}° E`;
    globe.opening();
    timers.push(
      setTimeout(() => {
        globe.setIsland(true);
        globe.home(2.2, -18, -48);
      }, 3200),
    );
    timers.push(setTimeout(() => root.classList.add("title-visible"), 3600));
    timers.push(setTimeout(() => skip(), 6400));
  }
  document.querySelector("#opening-skip").onclick = () => skip(true);
  return {
    start,
    skip,
    get active() {
      return active;
    },
    destroy() {
      timers.forEach(clearTimeout);
      active = false;
      root.hidden = true;
      document.body.classList.remove("opening");
    },
  };
}
