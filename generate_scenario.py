"""Generate a reproducible, fictional aerial sensor scenario as JSON."""

import argparse
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import random


ROOT = Path(__file__).resolve().parent
STEP_SECONDS = 10
DEFAULT_START = "2026-11-03T14:00:00Z"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def timestamp(start, step):
    return (start + timedelta(seconds=step * STEP_SECONDS)).isoformat().replace("+00:00", "Z")


def bearing(dx, dy):
    return math.degrees(math.atan2(dx, dy)) % 360


def position(step, total_steps, preset, site_position):
    fraction = step / total_steps
    if preset == "lost_contact":
        end = (9.0, 1.0)
    else:
        end = site_position
    return [round(1.0 + (end[0] - 1.0) * fraction, 3),
            round(8.0 + (end[1] - 8.0) * fraction, 3)]


def observe(sensor, drone_position, when, rng):
    dx = drone_position[0] - sensor["position_km"][0]
    dy = drone_position[1] - sensor["position_km"][1]
    distance = math.hypot(dx, dy)
    sensor_type = sensor["type"]
    miss_rate = {"rf_receiver": 0.08, "radar": 0.15,
                 "eo_ir_camera": 0.28, "acoustic": 0.35}[sensor_type]
    record = {"time": when, "sensor_id": sensor["id"],
              "object_id": "DRONE-01", "detected": False}
    if rng.random() < miss_rate:
        record["reason"] = "no_detection"
        return record

    record["detected"] = True
    angle = bearing(dx, dy)
    if sensor_type == "rf_receiver":
        record.update(bearing_deg=round((angle + rng.gauss(0, 3)) % 360, 1),
                      relative_strength_db=round(-20 * math.log10(max(distance, 0.1))
                                                 + rng.gauss(0, 1), 1),
                      uncertainty_deg=5.0)
    elif sensor_type == "radar":
        record.update(bearing_deg=round((angle + rng.gauss(0, 2)) % 360, 1),
                      range_km=round(max(0, distance + rng.gauss(0, 0.1)), 2),
                      uncertainty_km=0.25)
    elif sensor_type == "eo_ir_camera":
        record.update(bearing_deg=round((angle + rng.gauss(0, 4)) % 360, 1),
                      confidence=round(max(0.1, min(0.95, 1 - distance / 15
                                                     + rng.gauss(0, 0.05))), 2))
    else:
        record.update(bearing_deg=round((angle + rng.gauss(0, 10)) % 360, 1),
                      uncertainty_deg=15.0)
    return record


def generate(config):
    catalog = load_json(ROOT / "data" / "assets.json")
    presets = load_json(ROOT / "data" / "scenario_presets.json")
    seed = config.get("seed")
    if seed is None:
        seed = random.SystemRandom().randrange(2**32)
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("seed must be an integer")
    rng = random.Random(seed)

    preset = config.get("preset") or rng.choice(list(presets["presets"]))
    sector = config.get("sector") or rng.choice(presets["sectors"])
    if preset not in presets["presets"] or sector not in presets["sectors"]:
        raise ValueError("unknown preset or sector")

    def choose(kind, key, choices=None):
        entries = catalog[kind]
        allowed = {entry["type"]: entry for entry in entries}
        selected = config.get(key) or rng.choice(choices or
                        [item["type"] for item in entries if not item.get("optional")
                         and not item.get("display_only")])
        if not isinstance(selected, str) or selected not in allowed:
            raise ValueError(f"unknown {key}: {selected}")
        return allowed[selected]

    drone_type = choose("drones", "drone_type")
    response_type = choose("responses", "response_type",
                           ["interceptor_drone", "octopus", "jedi", "handheld_team"])
    site_type = choose("sites", "site_type")
    sensor_types = {item["type"] for item in catalog["sensors"]}
    assets = copy.deepcopy(presets["default_assets"])
    if config.get("include_acoustic", False):
        assets["sensors"].append({"id": "ACOUSTIC-01", "type": "acoustic",
                                   "position_km": [5.0, 5.0]})
    sensor_ids = config.get("sensor_ids")
    if sensor_ids is not None:
        available = {item["id"] for item in assets["sensors"]}
        if (not isinstance(sensor_ids, list)
                or not all(isinstance(item, str) for item in sensor_ids)
                or not set(sensor_ids) <= available):
            raise ValueError("sensor_ids must list available sensor IDs")
        assets["sensors"] = [item for item in assets["sensors"]
                              if item["id"] in sensor_ids]
    if not any(item["type"] == "rf_receiver" for item in assets["sensors"]):
        raise ValueError("at least one RF receiver is required")
    if any(item["type"] not in sensor_types for item in assets["sensors"]):
        raise ValueError("unknown sensor type")

    assets["drone"] = {"id": "DRONE-01", "type": drone_type["type"],
                       "label": drone_type["label"], "affiliation": "russian"}
    assets["response"].update(type=response_type["type"], label=response_type["label"])
    assets["site"].update(type=site_type["type"], label=site_type["label"])
    start_raw = config.get("start_time", DEFAULT_START)
    try:
        start = datetime.fromisoformat(start_raw.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as error:
        raise ValueError("start_time must be an ISO 8601 timestamp") from error
    if start.tzinfo is None:
        raise ValueError("start_time must include a timezone")
    start = start.astimezone(timezone.utc)

    duration = presets["presets"][preset]["duration_seconds"]
    steps = duration // STEP_SECONDS
    last_truth_step = 8 if preset == "intercepted" else steps
    last_sensor_step = 6 if preset == "lost_contact" else last_truth_step
    truth = []
    observations = []
    for step in range(last_truth_step + 1):
        when = timestamp(start, step)
        drone_position = position(step, steps, preset, assets["site"]["position_km"])
        truth.append({"time": when, "object_id": "DRONE-01",
                      "position_km": drone_position, "altitude_agl_m": 120,
                      "status": "intercepted" if preset == "intercepted" and step == 8
                      else "airborne"})
        if step <= last_sensor_step:
            observations.extend(observe(sensor, drone_position, when, rng)
                                for sensor in assets["sensors"])

    events = []
    if preset == "incoming":
        events.append({"time": timestamp(start, steps), "type": "site_boundary_reached",
                       "object_id": "DRONE-01", "site_id": "SITE-01"})
    elif preset == "intercepted":
        events.extend([
            {"time": timestamp(start, 7), "type": "response_alerted",
             "object_id": "DRONE-01", "response_id": "RESP-01"},
            {"time": timestamp(start, 8), "type": "interception_recorded",
             "object_id": "DRONE-01", "response_id": "RESP-01"}
        ])
    else:
        events.append({"time": timestamp(start, 7), "type": "track_lost",
                       "object_id": "DRONE-01"})

    resolved = {"seed": seed, "preset": preset, "sector": sector,
                "drone_type": drone_type["type"], "response_type": response_type["type"],
                "site_type": site_type["type"], "sensor_ids": [x["id"] for x in assets["sensors"]],
                "start_time": timestamp(start, 0)}
    scenario_id = hashlib.sha256(json.dumps(resolved, sort_keys=True).encode()).hexdigest()[:12]
    return {"schema_version": 1, "scenario_id": scenario_id, "configuration": resolved,
            "duration_seconds": duration, "assets": assets, "ground_truth": truth,
            "sensor_observations": observations, "event_log": events,
            "outcome": {"type": preset, "object_id": "DRONE-01",
                        "site_reached": preset == "incoming",
                        "response_id": "RESP-01" if preset == "intercepted" else None}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, help="JSON configuration file")
    parser.add_argument("--seed", type=int, help="override the random seed")
    parser.add_argument("--preset", choices=["incoming", "intercepted", "lost_contact"])
    parser.add_argument("--sector", choices=["central_valley", "kharkiv_ne", "border_sector"])
    parser.add_argument("--output", type=Path, help="write JSON here instead of stdout")
    args = parser.parse_args()
    config = load_json(args.config) if args.config else {}
    for name in ("seed", "preset", "sector"):
        value = getattr(args, name)
        if value is not None:
            config[name] = value
    result = json.dumps(generate(config), indent=2) + "\n"
    if args.output:
        args.output.write_text(result, encoding="utf-8")
    else:
        print(result, end="")


if __name__ == "__main__":
    main()
