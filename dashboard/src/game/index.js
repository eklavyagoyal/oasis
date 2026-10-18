// Game controller: seed engine -> world + scenario -> real-time sim -> layer + panel. Owns no DOM besides #game-panel.
import './game.css';
import { generate, makeScenario, saveJSON, DEFAULTS } from './seed.js';
import { createSim, step, summary, DT } from './sim.js';
import { createGameLayer } from './layer.js';
import { createGamePanel } from './panel.js';

export function createGame(globe, state, notify) {
  const grid = state.data.terrain, layer = createGameLayer(globe), opts = { coverage: true, links: true, labels: true };
  let G = null, S = null, acc = 0, running = false, report = null;
  const meta = () => ({ seed: { world: G.cfg.worldSeed, scenario: G.cfg.scenarioSeed }, dem: state.data.scenario.name, tile_km: G.tile.sizeKm });
  const reset = () => {
    S = createSim(G);
    acc = 0; running = false; report = null;
    layer.update(S, opts);
    panel.update(S);
  };
  const load = (next, fly) => {
    G = next;
    layer.setGame(G);
    panel.setGame(G);
    reset();
    if (fly) globe.flyTo(G.tile.lon, G.tile.lat, 300, G.tile.size * 1.7);
  };
  const h = {
    generateWorld(cfg) {
      load(generate(grid, { ...DEFAULTS, ...cfg }), true);
      notify(`World ${G.cfg.worldSeed}: ${G.world.length} fixed assets on a ${G.tile.sizeKm} km tile. Scenario ${G.cfg.scenarioSeed}: ${G.drones.length} drones.`);
    },
    newScenario(cfg) {  // same world (tile + fixed assets), new movable assets
      if (!G) return h.generateWorld(cfg);
      const c = { ...G.cfg, ...cfg, worldSeed: G.cfg.worldSeed, tileKm: G.cfg.tileKm };
      load({ ...G, cfg: c, drones: makeScenario(G.tile, G.world, c) }, false);
      notify(`Scenario ${c.scenarioSeed} on world ${c.worldSeed}: ${G.drones.length} drones.`);
    },
    start() {
      if (!G) h.generateWorld(DEFAULTS);
      if (S.done) reset();
      state.playing = false;  // the replay clock stops while the match runs
      running = true;
    },
    pause() { running = false; },
    reset() { if (G) reset(); },
    download() {
      if (!G) return;
      const body = JSON.stringify({ world: JSON.parse(saveJSON(G)), report: summary(S, meta()) }, null, 1);
      const a = document.createElement('a');
      a.href = URL.createObjectURL(new Blob([body], { type: 'application/json' }));
      a.download = `oasis-world${G.cfg.worldSeed}-scenario${G.cfg.scenarioSeed}.json`;
      a.click();
      URL.revokeObjectURL(a.href);
    },
    setOpt(name, value) {
      opts[name] = value;
      if (S) layer.update(S, opts);
    },
  };
  const panel = createGamePanel(document.querySelector('#game-panel'), h);
  return {
    get active() { return !!G; },
    get running() { return running; },
    tick(dt, speed) {  // wall-clock seconds x speed -> fixed DT sim steps
      if (!running || !S) return;
      acc += dt * speed;
      while (acc >= DT && !S.done) { step(S); acc -= DT; }
      if (S.done && !report) {
        running = false;
        report = summary(S, meta());
        panel.showSummary(report);
      }
    },
    render() {
      if (!S) return;
      layer.update(S, opts);
      panel.update(S);
    },
    destroy() { layer.destroy(); },
  };
}
