"""CLI entry point and the shared Context every sensor module receives."""
import argparse
import importlib
import json
import platform
import shutil
import sys
import time
import zlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from . import config
from .catalog import CATALOG
from .config import Scenario, Sensor
from .truth import iso as _iso
from .truth import simulate
from .world import World


@dataclass
class Context:
    cfg: Scenario
    world: World
    truth: pd.DataFrame  # tracks.csv rows
    objects: dict  # id -> Obj
    out: Path

    def __post_init__(self):
        self._sensors = {s.id: s for s in self.cfg.sensors}
        self._tracks = {}  # object id -> (t, {x, y, z, vx, vy, vz}) cache for state()

    def rng(self, name: str) -> np.random.Generator:
        return np.random.default_rng([self.cfg.seed, zlib.crc32(name.encode())])

    def iso(self, t):
        return _iso(self.cfg.start, t)

    def state(self, object_id: str, t) -> dict:
        """x, y, z, vx, vy, vz at arbitrary t, linearly interpolated; NaN outside the span."""
        tt = np.asarray(t, dtype=np.float64)
        cols = {"x": "x_m", "y": "y_m", "z": "z_m", "vx": "vx", "vy": "vy", "vz": "vz"}
        if object_id not in self._tracks:  # filter the truth table once per object, not once per call
            rows = self.truth[self.truth["object_id"] == object_id].sort_values("t")
            self._tracks[object_id] = (rows["t"].to_numpy(), {k: rows[c].to_numpy() for k, c in cols.items()})
        ts, vals = self._tracks[object_id]
        if not ts.size:
            return {k: np.full(tt.shape, np.nan) for k in cols}
        return {k: np.interp(tt, ts, vals[k], left=np.nan, right=np.nan) for k in cols}

    def sensor_xyz(self, sensor: Sensor) -> np.ndarray:
        site = sensor
        while site.mount:  # a mounted sensor uses the mount's site with its own mast_m
            site = self._sensors[site.mount]
        x, y = self.world.to_xy(site.pos[0], site.pos[1])
        return np.array([x, y, self.world.height(x, y) + sensor.mast_m], dtype=np.float64)

    def alive(self, sensor: Sensor, t):
        tt = np.asarray(t, dtype=np.float64)
        if sensor.destroyed_by:
            last = self.truth.loc[self.truth["object_id"] == sensor.destroyed_by, "t"].max()
            mask = tt <= last  # False after the last truth tick of the destroying object
        else:
            mask = np.ones(tt.shape, dtype=bool)
        return bool(mask) if tt.ndim == 0 else mask


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        _usage()
    cmd, rest = argv[0], argv[1:]
    if cmd == "run":
        _run(rest)
    elif cmd == "dash":
        _call_main("mirrorworld.dashboard", rest)
    elif cmd in ("audit", "view", "prompt"):
        _call_main(f"mirrorworld.{cmd}", rest)
    else:
        sys.exit(f"unknown command {cmd!r}; expected run, dash, audit, view or prompt\n" + USAGE)


USAGE = "usage: python -m mirrorworld {run|dash|audit|view|prompt} ..."


def _usage() -> None:
    print(USAGE)
    print("  run <yaml> [-o OUT_DIR] [--skip-missing]   simulate a scenario into out/<name>/")
    print("  dash out/<name> [--serve] [--port 8765]    export / serve the 3D replay dashboard")
    print("  audit|view|prompt ...                     other lanes' tools, forwarded as-is")
    sys.exit(2)


def _call_main(module_name: str, argv: list[str]) -> None:
    try:
        mod = importlib.import_module(module_name)
    except ModuleNotFoundError as e:
        if e.name != module_name:
            raise
        sys.exit(f"error: {module_name} is not implemented yet")
    mod.main(argv)


def _run(argv: list[str]) -> None:
    ap = argparse.ArgumentParser(prog="mirrorworld run", description="Simulate a scenario.")
    ap.add_argument("yaml")
    ap.add_argument("-o", "--out", default=None, help="output directory (default out/<name>)")
    ap.add_argument("--skip-missing", action="store_true",
                    help="warn and continue when a sensor module is not implemented yet")
    args = ap.parse_args(argv)

    timings: dict[str, float] = {}
    t0 = time.perf_counter()
    cfg = config.load(args.yaml)
    timings["load"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    world = World(cfg)
    timings["world"] = time.perf_counter() - t0

    out = Path(args.out) if args.out else Path("out") / cfg.name
    ctx = Context(cfg, world, None, {o.id: o for o in cfg.objects}, out)

    t0 = time.perf_counter()
    ctx.truth = simulate(cfg, world, ctx.rng("truth"))
    timings["truth"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    (out / "truth").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(args.yaml, out / "scenario.yaml")  # input copied verbatim
    pd.DataFrame(
        [{"id": o.id, "type": o.type, "kind": CATALOG[o.type]["kind"], "side": o.side,
          "controls": o.controls or ""} for o in cfg.objects],
        columns=["id", "type", "kind", "side", "controls"],
    ).to_csv(out / "truth" / "objects.csv", index=False)
    ctx.truth.to_csv(out / "truth" / "tracks.csv", index=False)
    timings["write"] = time.perf_counter() - t0

    # rf_df first (camera reads fused/fixes.csv), then first-appearance order in the YAML
    types: list[str] = []
    for s in cfg.sensors:
        if s.type not in types:
            types.append(s.type)
    if "rf_df" in types:
        types.remove("rf_df")
        types.insert(0, "rf_df")

    skipped: list[str] = []
    for typ in types:
        group = [s for s in cfg.sensors if s.type == typ]
        try:
            mod = importlib.import_module(f"mirrorworld.sensors.{typ}")
        except ModuleNotFoundError as e:
            if e.name != f"mirrorworld.sensors.{typ}":
                raise
            if not args.skip_missing:
                sys.exit(f"error: mirrorworld/sensors/{typ}.py is not implemented yet "
                         f"({len(group)} sensor(s); use --skip-missing to continue)")
            print(f"warning: mirrorworld.sensors.{typ} missing, skipping {len(group)} sensor(s)",
                  file=sys.stderr)
            skipped.append(typ)
            continue
        t0 = time.perf_counter()
        mod.run(group, ctx)
        timings[f"sensors:{typ}"] = time.perf_counter() - t0

    (out / "run.json").write_text(json.dumps({
        "seed": cfg.seed,
        "start": ctx.iso(0),
        "duration_s": cfg.duration_s,
        "dem_sources": world.sources,
        "skipped_sensor_types": skipped,
        "timings_s": timings,
        "python": platform.python_version(),
        "numpy": np.__version__,
    }, indent=2))
    print(f"wrote {out}/ ({len(ctx.truth)} truth rows, DEM tiles: {len(world.sources)})")


if __name__ == "__main__":
    main()
