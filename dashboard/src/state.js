export const MODES = ["operator", "god", "delta"];
export const SPEEDS = [1, 5, 20, 60, 300];
export function createState(data) {
  const initial =
    data.game ? 0 : data.scenario.duration_s >= 18427 ? 18427 : (data.fixes.t[0] ?? 0);
  return {
    data,
    t: initial,
    playing: false,
    speed: 20,
    mode: "delta",
    selected:
      data.objects.find((o) => o.id === "mavic_1")?.id ?? data.objects[0]?.id,
    selectedFix: null,
    densityFiltered: true,
    follow: false,
    truth: true,
    rays: true,
    fixes: true,
    shadow: false,
    shadowSensor:
      Object.keys(data.shadow).find((id) => id === "RF2") ??
      Object.keys(data.shadow)[0],
    shadowHeight: 40,
    contours: false,
    natural: true,
    osm: false,
    island: true,
    exaggeration: 2.5,
    receivers: new Set(Object.keys(data.rf)),
    feed: "camera",
    tab: "feeds",
    presenting: false,
    beat: 0,
    revision: 0,
  };
}
