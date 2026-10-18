"""Generate scenarios from the asset catalog (data/assets.json + data/scenario_presets.json), powered by OASIS.

The catalog picks WHAT is in the scenario (preset, sector, drone, response, site, sensors); OASIS decides
everything physical: real terrain, sensor physics, blind sensor files and an answer key, then audits it.

    uv run python generate_scenario.py --seed 1 --preset intercepted --sector kharkiv_ne
    uv run python generate_scenario.py --matrix --seed 1          # every preset x sector, audited
"""

import argparse
import copy
import hashlib
import json
import random
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from mirrorworld.builder import Knobs, build
from mirrorworld.catalog import ALIASES, CATALOG

ROOT = Path(__file__).resolve().parent
STEP_SECONDS = 10  # ground-truth sampling in the JSON summary (full-rate truth is in the run directory)
AIR_KINDS = ("drone", "bird")


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def resolve(config, catalog, presets, rng):
    """The catalog's choices, seeded exactly like the original generator."""
    preset = config.get("preset") or rng.choice(list(presets["presets"]))
    sector = config.get("sector") or rng.choice(presets["sectors"])
    if preset not in presets["presets"] or sector not in presets["sectors"]:
        raise ValueError("unknown preset or sector")

    def choose(kind, key, choices=None):
        allowed = {e["type"]: e for e in catalog[kind]}
        pick = config.get(key) or rng.choice(choices or [e["type"] for e in catalog[kind]
                                                         if not e.get("optional") and not e.get("display_only")])
        if not isinstance(pick, str) or pick not in allowed:
            raise ValueError(f"unknown {key}: {pick}")
        return pick

    return {"preset": preset, "sector": sector,
            "drone_type": choose("drones", "drone_type"),
            "response_type": choose("responses", "response_type",
                                    ["interceptor_drone", "octopus", "jedi", "handheld_team"]),
            "site_type": choose("sites", "site_type"),
            "drones": int(config.get("drones", 3)),
            "include_acoustic": bool(config.get("include_acoustic", False)),
            "time_of_day": config.get("time_of_day", "dusk"),
            "duration_min": int(config.get("duration_min", 15))}


def scenario_yaml(r, seed):
    """Catalog choices -> knobs -> a full OASIS scenario on real terrain, then the catalog's labels."""
    knobs = Knobs(seed=seed, sector=ALIASES.get(r["sector"], r["sector"]),
                  template=ALIASES.get(r["preset"], r["preset"]),
                  mix={ALIASES.get(r["drone_type"], r["drone_type"]): 1.0}, drones=r["drones"],
                  defence=r["preset"] == "intercepted", time_of_day=r["time_of_day"],
                  duration_min=r["duration_min"], sensor_preset="standard" if r["include_acoustic"] else "minimal")
    text, _ = build(knobs)
    d = yaml.safe_load(text)
    resp = ALIASES.get(r["response_type"], r["response_type"])
    for o in d["objects"]:
        if o["type"] == "site":
            o["type"] = r["site_type"]
        elif o["type"] == "interceptor" and CATALOG[resp]["kind"] == "drone":
            o["type"] = resp
        elif o["type"] == "ad_team" and CATALOG[resp]["kind"] == "response":
            o["type"] = resp
    head = "".join(line + "\n" for line in text.splitlines() if line.startswith("#"))
    return head + f"# asset catalog: {json.dumps(r, sort_keys=True)}\n" + yaml.safe_dump(d, sort_keys=False)


def run_oasis(yaml_path, out_dir):
    py = sys.executable
    subprocess.run([py, "-m", "mirrorworld", "run", str(yaml_path), "-o", str(out_dir), "--skip-missing"],
                   check=True, cwd=ROOT)
    subprocess.run([py, "-m", "mirrorworld", "audit", str(out_dir)], cwd=ROOT,
                   stdout=subprocess.DEVNULL)  # exits 1 when a check fails; the verdict is in audit.json


def _km(cfg, lat, lon):
    """Catalog coordinates: kilometres from the south-west corner of the sector tile."""
    half = cfg["area"]["size_km"] / 2.0
    y = (np.asarray(lat) - cfg["area"]["lat"]) * 111.195
    x = (np.asarray(lon) - cfg["area"]["lon"]) * 111.195 * np.cos(np.radians(cfg["area"]["lat"]))
    return np.round(x + half, 3), np.round(y + half, 3)


def observations(out):
    """Every sensor record, blind (what the sensor logged), plus the answer key that attributes it."""
    obs, key = [], {}
    for folder in sorted((out / "sensors").iterdir()):
        ak = out / "answer_key" / f"{folder.name}.csv"
        if ak.exists():
            k = pd.read_csv(ak)
            if {"record_id", "object_id"} <= set(k.columns):
                key.update(dict(zip(k["record_id"], k["object_id"].fillna(""))))
        for f in ("detections.csv", "plots.csv", "messages.csv", "reports.csv"):
            if (folder / f).exists():
                df = pd.read_csv(folder / f)
                df = df.drop(columns=[c for c in df.columns if c in ("object_id", "label")], errors="ignore")
                if "sensor_id" not in df.columns:
                    df.insert(0, "sensor_id", folder.name)
                obs += json.loads(df.to_json(orient="records"))
    return obs, key


def outcome_of(cfg, tracks, key):
    """Scenario outcome from the truth: site reached / intercepted / contact lost."""
    kind = {o["id"]: CATALOG[o["type"]]["kind"] for o in cfg["objects"]}
    side = {o["id"]: o.get("side") for o in cfg["objects"]}
    site = next((o for o in cfg["objects"] if kind[o["id"]] == "site"), None)
    hostiles = [o for o in tracks["object_id"].unique() if kind.get(o) == "drone" and side.get(o) == "hostile"]
    friendly = [o for o in tracks["object_id"].unique() if kind.get(o) == "drone" and side.get(o) == "friendly"]
    seen = pd.Series(list(key.values()))
    per, events = {}, []
    for h in hostiles:
        tr = tracks[tracks["object_id"] == h]
        res = {"airborne_s": float(tr["t"].max() - tr["t"].min()), "records": int((seen == h).sum())}
        if site is not None:
            sx, sy = _km(cfg, site["pos"][0], site["pos"][1])
            hx, hy = _km(cfg, tr["lat"].to_numpy(), tr["lon"].to_numpy())
            dmin = float(np.min(np.hypot(hx - sx, hy - sy)) * 1000)
            res["min_distance_to_site_m"] = round(dmin, 1)
            res["site"] = "reached" if dmin < 100 else "approached" if dmin < 1000 else "not reached"
        end = float(tr["t"].max())
        for f in friendly:
            fr = tracks[tracks["object_id"] == f]
            if abs(float(fr["t"].max()) - end) <= 1.0:
                res["intercepted_by"], res["intercepted_t"] = f, end
                events.append({"t": end, "type": "interception", "object_id": h, "response_id": f})
        if res.get("site") == "reached":
            events.append({"t": end, "type": "site_reached", "object_id": h, "site_id": site["id"]})
        per[h] = res
    kinds = [("intercepted", any("intercepted_by" in v for v in per.values())),
             ("incoming", any(v.get("site") in ("reached", "approached") for v in per.values()))]
    overall = next((k for k, hit in kinds if hit), "passed")
    return {"type": overall, "hostiles": per}, sorted(events, key=lambda e: e["t"])


def summarise(out, r, seed):
    cfg = yaml.safe_load((out / "scenario.yaml").read_text())
    tracks = pd.read_csv(out / "truth" / "tracks.csv")
    obs, key = observations(out)
    outcome, truth_events = outcome_of(cfg, tracks, key)
    sample = tracks[(tracks["t"] % STEP_SECONDS) == 0]
    x, y = _km(cfg, sample["lat"].to_numpy(), sample["lon"].to_numpy())
    truth = [{"time": t, "object_id": o, "position_km": [float(a), float(b)], "lat": la, "lon": lo,
              "altitude_agl_m": round(float(agl), 1)}
             for t, o, a, b, la, lo, agl in zip(sample["time_utc"], sample["object_id"], x, y,
                                               sample["lat"], sample["lon"], sample["alt_agl_m"])]
    c2 = out / "sensors" / "C2-01" / "alerts.jsonl"
    alerts = [json.loads(line) for line in c2.read_text().splitlines()] if c2.exists() else []
    audit = json.loads((out / "audit.json").read_text()) if (out / "audit.json").exists() else None
    assets = {"sensors": [{"id": s["id"], "type": s["type"], **({"pos": s["pos"]} if s.get("pos") else
                           {"mount": s.get("mount")})} for s in cfg["sensors"]],
              "objects": [{"id": o["id"], "type": o["type"], "side": o.get("side"),
                           "label": CATALOG[o["type"]].get("label", o["type"])} for o in cfg["objects"]]}
    resolved = {"seed": seed, **r}
    return {"schema_version": 2,
            "scenario_id": hashlib.sha256(json.dumps(resolved, sort_keys=True).encode()).hexdigest()[:12],
            "configuration": resolved, "duration_seconds": cfg["duration_s"], "start_time": cfg["start"],
            "assets": assets, "ground_truth": truth,
            "sensor_observations": obs,     # blind: exactly what the sensors logged
            "answer_key": key,              # record_id -> object that produced it ('' = false alarm)
            "event_log": {"truth": truth_events, "c2_alerts": alerts},
            "outcome": outcome,
            "audit": audit and audit["summary"], "oasis_run": str(out.relative_to(ROOT))}


def generate(config):
    catalog, presets = load_json(ROOT / "data" / "assets.json"), load_json(ROOT / "data" / "scenario_presets.json")
    seed = config.get("seed")
    if seed is None:
        seed = random.SystemRandom().randrange(2**31)
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("seed must be an integer")
    r = resolve(config, catalog, presets, random.Random(seed))
    name = f"{r['sector']}-{r['preset']}-s{seed}".replace("_", "-")
    yaml_path = ROOT / "scenarios" / "generated" / f"{name}.yaml"
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    yaml_path.write_text(scenario_yaml(r, seed))
    out = ROOT / "out" / name
    run_oasis(yaml_path, out)
    result = summarise(out, r, seed)
    (out / "summary.json").write_text(json.dumps(result, indent=1) + "\n")
    run_record = load_json(out / "run.json")
    run_record["artifacts"] = sorted(set(run_record.get("artifacts", [])) | {"summary.json"})
    (out / "run.json").write_text(json.dumps(run_record, indent=2) + "\n")
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", type=Path, help="JSON configuration file")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--preset", choices=["incoming", "intercepted", "lost_contact"])
    ap.add_argument("--sector", choices=["central_valley", "kharkiv_ne", "border_sector"])
    ap.add_argument("--matrix", action="store_true", help="every preset x sector; index in out/matrix.json")
    ap.add_argument("--output", type=Path, help="write the JSON summary here instead of stdout")
    args = ap.parse_args()
    config = load_json(args.config) if args.config else {}
    for k in ("seed", "preset", "sector"):
        if getattr(args, k) is not None:
            config[k] = getattr(args, k)
    if not args.matrix:
        text = json.dumps(generate(config), indent=1) + "\n"
        args.output.write_text(text) if args.output else print(text, end="")
        return
    presets = load_json(ROOT / "data" / "scenario_presets.json")
    rows = []
    for i, (pr, se) in enumerate((p, s) for p in presets["presets"] for s in presets["sectors"]):
        res = generate({**copy.deepcopy(config), "preset": pr, "sector": se, "seed": config.get("seed", 1) + i})
        rows.append({"scenario": res["oasis_run"], "preset": pr, "sector": se, "drone": res["configuration"]["drone_type"],
                     "outcome": res["outcome"]["type"], "records": len(res["sensor_observations"]), "audit": res["audit"]})
        print(f"{pr:<13} {se:<15} {rows[-1]['drone']:<13} outcome={rows[-1]['outcome']:<12} "
              f"records={rows[-1]['records']:<6} audit={res['audit']}", flush=True)
    (ROOT / "out" / "matrix.json").write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
