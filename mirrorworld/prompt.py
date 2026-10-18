"""`python -m mirrorworld prompt "<text>"`: text -> Scenario YAML.

The LLM contributes intent and structure only (PromptScenario JSON, pydantic-validated).
Every number is computed deterministically: place via Nominatim, sensor sites from DEM
high ground and `World.min_visible_agl`, paths from the requested behaviours. On a
Scenario validation error the LLM is retried once with the error text. With `--run` the
generated YAML is executed through the same pipeline as `python -m mirrorworld run`.

The OpenAI plumbing in this module (key loading, model check, chat with retries) is
shared with `mirrorworld/sensors/reports.py`.
"""
import argparse
import json
import math
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import numpy as np
import yaml
from pydantic import BaseModel, ValidationError

from .catalog import CATALOG
from .config import UKRAINE, Area, Obj, Scenario, Sensor
from .world import World

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = "gpt-4o-mini"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_UA = "mirror-world-hackathon"
CALL_TIMEOUT_S = 45.0
RETRIES = 2  # per LLM call / geocode request, with backoff

# Sensor types a scenario may name: what is implemented now plus the contract's types.
CONTRACT_TYPES = {"camera", "satellite", "microphone", "remote_id", "telemetry"}
AUTO_MIC_RADIUS_M = 1500.0
PATH_MARGIN = 0.85  # generated paths stay inside this fraction of the area half-size
RF_MIN_SEP_M = 4000.0  # auto-sited receivers must be >= 4 km apart
COVERAGE_AGL_M = 40.0  # auto-siting maximises coverage of targets at 40 m AGL


# ---------------------------------------------------------------- LLM plumbing
def load_api_key() -> str | None:
    """OPENAI_API_KEY from the environment, else from a KEY=VALUE .env in the repo root."""
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if key:
        return key
    env = REPO_ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line.startswith("OPENAI_API_KEY="):
                return line.split("=", 1)[1].strip().strip("'\"") or None
    return None


def make_client(key: str):
    from openai import OpenAI  # imported lazily so keyless runs never touch the SDK

    return OpenAI(api_key=key, timeout=CALL_TIMEOUT_S, max_retries=0)  # we do our own retries


def resolve_model(client) -> str:
    """Tiny call to verify the model works; on failure pick a working small one from the list."""
    errors = []

    def works(model: str) -> bool:
        try:
            client.chat.completions.create(
                model=model, messages=[{"role": "user", "content": "Reply with the single word ok"}])
            return True
        except Exception as e:  # noqa: BLE001 - report whatever the endpoint said
            errors.append(f"{model}: {e}")
            return False

    preferred = os.environ.get("OPENAI_MODEL", "").strip() or DEFAULT_MODEL
    if works(preferred):
        return preferred
    try:
        ids = sorted(m.id for m in client.models.list())
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"cannot list models after {preferred!r} failed: {e}\n" + "\n".join(errors)) from e
    for mid in ids:  # prefer small/cheap models
        if re.search(r"mini|small|flash|haiku|nano", mid) and works(mid):
            return mid
    raise RuntimeError(f"no working model among {len(ids)}; tried:\n" + "\n".join(errors))


def chat_json(client, model: str, system: str, user: str, validate):
    """One chat call expecting JSON. Timeout + 2 retries with backoff; parse/validation
    errors are fed back to the model. `validate(obj)` raises on bad structure."""
    last = None
    for attempt in range(RETRIES + 1):
        try:
            resp = client.chat.completions.create(
                model=model, messages=[{"role": "system", "content": system},
                                       {"role": "user", "content": user}])
            text = resp.choices[0].message.content or ""
            return validate(json.loads(_strip_fences(text)))
        except Exception as e:  # noqa: BLE001
            last = e
            if attempt < RETRIES:
                user = f"{user}\n\nYour previous reply was rejected: {e}\nReply with corrected JSON only."
                time.sleep(2.0 * (attempt + 1))
    raise RuntimeError(f"LLM call failed after {RETRIES + 1} attempts (model {model}): {last}")


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n|```$", "", text).strip()
    i, j = text.find("{"), text.rfind("}")
    return text[i:j + 1] if i >= 0 and j > i else text


# ---------------------------------------------------------------- geocoding
_geo_cache: dict[str, tuple[float, float]] = {}


def geocode(place: str, viewbox: tuple | None = None) -> tuple[float, float]:
    """Nominatim search -> (lat, lon). `viewbox` = (lon_min, lat_min, lon_max, lat_max)
    bounds results to the area for scenario landmarks. <= 1 request/s, timeout + retries."""
    if place in _geo_cache:
        return _geo_cache[place]
    params = {"format": "json", "q": place, "limit": 1}
    if viewbox is not None:
        lon_min, lat_min, lon_max, lat_max = viewbox
        params["viewbox"] = f"{lon_min},{lat_max},{lon_max},{lat_min}"  # left,top,right,bottom
        params["bounded"] = 1
    url = NOMINATIM_URL + "?" + urllib.parse.urlencode(params)
    for attempt in range(RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": NOMINATIM_UA})
            with urllib.request.urlopen(req, timeout=15.0) as r:
                data = json.load(r)
            time.sleep(1.0)  # nominatim usage policy: <= 1 req/s
            if not data:
                raise ValueError(f"Nominatim found nothing for {place!r}")
            _geo_cache[place] = (float(data[0]["lat"]), float(data[0]["lon"]))
            return _geo_cache[place]
        except ValueError:
            raise
        except Exception as e:  # noqa: BLE001
            if attempt == RETRIES:
                raise RuntimeError(f"Nominatim request for {place!r} failed: {e}") from e
            time.sleep(2.0 * (attempt + 1))
    raise AssertionError("unreachable")


# ---------------------------------------------------------------- LLM schema
def _norm(ident: str) -> str:
    """Object ids the LLM writes may differ in case or -/_ only: 'scout-1' vs 'scout_1'."""
    return ident.strip().lower().replace("_", "-")


class PObject(BaseModel):
    id: str
    type: str  # CATALOG key
    side: Literal["hostile", "friendly", "neutral", "unknown"] = "unknown"
    behaviour: Literal["patrol", "transit", "loiter", "attack_sensor", "static"] = "static"
    offset_km: tuple[float, float] | None = None  # (east, north) km from the area centre
    landmark: str | None = None  # named place instead of offsets
    target_sensor: str | None = None  # for attack_sensor
    alt_agl_m: float = 80.0
    start_min: float = 0.0
    end_min: float | None = None
    controls: str | None = None
    gnss_spoof: tuple[float, float] | None = None  # spoof window in minutes after start


class PSensor(BaseModel):
    id: str
    type: str
    placement: str | tuple[float, float] = "auto"  # "auto" or (east, north) km from the centre
    mast_m: float = 10.0
    monitors: list[str] | None = None  # telemetry: object ids to log


class PWeather(BaseModel):
    wind_from_deg: float = 270.0
    wind_mps: float = 3.0
    temp_c: float = 5.0
    rh_pct: float = 80.0
    visibility_km: float = 10.0
    cloud_pct: float = 60.0


class PromptScenario(BaseModel):
    title: str
    place: str
    date: str  # YYYY-MM-DD (UTC)
    start_utc: str  # HH:MM (UTC)
    duration_min: float
    seed: int = 7
    size_km: float = 16.0
    objects: list[PObject]
    sensors: list[PSensor]
    weather: PWeather = PWeather()


def available_sensor_types() -> list[str]:
    pkg = Path(__file__).resolve().parent / "sensors"
    found = {p.stem for p in pkg.glob("*.py") if p.stem != "__init__"}
    return sorted(found | CONTRACT_TYPES)


SYSTEM_PROMPT = """You plan synthetic aerial-defence scenarios over real Ukrainian terrain for a simulation.
Reply with JSON only matching this JSON schema:
{schema}

Rules:
- types: objects must use these catalog keys: {obj_types}. Sensors must use these types: {sensor_types}.
- offsets are approximate intent (km east/north of the area centre); never invent precise coordinates,
  altitudes above sea level, ranges or speeds - the simulation computes those from real terrain.
- behaviour: patrol = a loop around the point, transit = a straight pass across the area through
  the point, loiter = a circle, attack_sensor = fly straight into target_sensor (set it), static = fixed.
- placement "auto" means the simulation chooses the site (RF on DEM high ground, cameras/remote_id
  mounted on the first RF sensor). Cameras and remote_id sensors always mount on the first rf_df.
- gnss_spoof is only for friendly drones that get spoofed; give the window in minutes after start.
- date/start_utc are UTC. Keep the cast small and coherent with the requested story."""


def ask_llm(client, model: str, text: str, feedback: str | None = None) -> PromptScenario:
    user = f"Scenario request:\n{text}"
    if feedback:
        user += f"\n\nYour previous plan was rejected by the validator:\n{feedback}\nFix it."

    def validate(obj):
        ps = PromptScenario.model_validate(obj)
        ids = {_norm(o.id) for o in ps.objects}
        for o in ps.objects:
            if o.type not in CATALOG:
                raise ValueError(f"object {o.id}: unknown type {o.type!r}; known: {sorted(CATALOG)}")
            if o.controls and _norm(o.controls) not in ids:
                raise ValueError(f"object {o.id}: controls -> unknown object {o.controls!r}; "
                                 f"objects are {sorted(x.id for x in ps.objects)}")
        bad = {s.type for s in ps.sensors if s.type not in available_sensor_types()}
        if bad:
            raise ValueError(f"unknown sensor types {sorted(bad)}; available: {available_sensor_types()}")
        return ps

    return chat_json(client, model, SYSTEM_PROMPT.format(
        schema=json.dumps(PromptScenario.model_json_schema(), indent=1),
        obj_types=sorted(CATALOG), sensor_types=available_sensor_types()), user, validate)


# ---------------------------------------------------------------- deterministic build
def _terrain_world(area: Area) -> World:
    """World reads only cfg.area; build the smallest Scenario that satisfies the validator."""
    dummy = Scenario(name="prompt-terrain", seed=0, start=datetime(2026, 1, 1, tzinfo=timezone.utc),
                     duration_s=60, area=area,
                     objects=[Obj(id="o", type="operator", pos=(area.lat, area.lon))],
                     sensors=[Sensor(id="s", type="rf_df", pos=(area.lat, area.lon))])
    return World(dummy)


def auto_sites(world, area: Area, n_sites: int = 2, min_sep_m: float = RF_MIN_SEP_M,
               mast_m: float = 10.0, target_agl_m: float = COVERAGE_AGL_M,
               grid_n: int = 20, eval_n: int = 24):
    """Site n rf_df receivers on DEM high ground: greedily maximise the share of the area
    visible at `target_agl_m` (World.min_visible_agl), keeping >= `min_sep_m` between sites.
    Candidates are the highest point of each tile of the coarse grid. Returns (n, 2) x, y."""
    half = area.size_km * 500.0
    gx = np.linspace(-half * 0.95, half * 0.95, grid_n)
    xs, ys = np.meshgrid(gx, gx)
    h = world.height(xs, ys)
    ex = np.linspace(-half * 0.95, half * 0.95, eval_n)
    exs, eys = np.meshgrid(ex, ex)
    exs, eys = exs.ravel(), eys.ravel()
    tile = max(grid_n // 4, 1)  # 16 spread-out candidates: each tile's highest point
    cand = []
    for a in range(0, grid_n, tile):
        for b in range(0, grid_n, tile):
            sub = h[a:a + tile, b:b + tile]
            i, j = np.unravel_index(int(np.argmax(sub)), sub.shape)
            cand.append((xs[a + i, b + j], ys[a + i, b + j]))
    cand_xy = np.unique(np.round(np.array(cand), 3), axis=0)
    k = len(cand_xy)
    cov = np.empty((k, exs.size), dtype=bool)
    for i, (cx, cy) in enumerate(cand_xy):
        site = np.array([cx, cy, float(world.height(cx, cy)) + mast_m])
        cov[i] = world.min_visible_agl(site, exs, eys) <= target_agl_m
    chosen: list[int] = []
    covered = np.zeros(exs.size, dtype=bool)
    for _ in range(n_sites):
        best, best_gain = None, -1
        for i in range(k):
            if any(np.hypot(*(cand_xy[i] - cand_xy[j])) < min_sep_m - 1e-6 for j in chosen):
                continue
            gain = int((cov[i] & ~covered).sum())
            if gain > best_gain:
                best, best_gain = i, gain
        if best is None:
            break
        chosen.append(best)
        covered |= cov[best]
    if len(chosen) < 2:
        raise RuntimeError(f"auto-siting found only {len(chosen)} rf_df site(s) with >= "
                           f"{min_sep_m / 1000:.0f} km separation")
    return cand_xy[chosen]


def behaviour_path(behaviour: str, x: float, y: float, half_km: float, alt: float,
                   heading_deg: float = 45.0, target: tuple[float, float] | None = None):
    """Waypoints (x, y, alt_agl) in the local frame for a behaviour; always inside the area.
    Returns (waypoints, loop, attack: bool)."""
    lim = half_km * 1000.0 * PATH_MARGIN

    def clamp(px, py):
        return float(np.clip(px, -lim, lim)), float(np.clip(py, -lim, lim))

    if behaviour == "static":
        return [(x, y, alt)], False, False
    if behaviour == "patrol":
        d = min(1200.0, lim * 0.4)
        box = [(x + d, y + d), (x + d, y - d), (x - d, y - d), (x - d, y + d)]
        return [(*clamp(px, py), alt) for px, py in box], True, False
    if behaviour == "loiter":
        r = min(800.0, lim * 0.4)
        angs = np.linspace(0.0, 2 * np.pi, 8, endpoint=False)
        return [(*clamp(x + r * math.cos(a), y + r * math.sin(a)), alt) for a in angs], True, False
    # transit / attack_sensor: a straight line to the box exit (or to the target)
    if behaviour == "attack_sensor":
        if target is None:
            raise ValueError("attack_sensor needs target_sensor")
        tx, ty = target
        vx, vy = tx - x, ty - y
        dist = math.hypot(vx, vy) or 1.0
        vx, vy = vx / dist, vy / dist
        start = clamp(tx + vx * lim, ty + vy * lim)  # come in from the area edge
        return [(start[0], start[1], alt), (tx, ty, alt)], False, True
    h = math.radians(heading_deg)
    vx, vy = math.sin(h), math.cos(h)  # bearing -> local unit vector
    x, y = clamp(x, y)  # the intent point may sit on the margin box
    ts = []
    for a, u in ((x, vx), (y, vy)):
        if abs(u) > 1e-9:
            ts += [(lim - a) / u, (-lim - a) / u]
        else:
            ts += [0.0]
    lo, hi = max(t for t in ts if t <= 0), min(t for t in ts if t >= 0)
    return [(x + lo * vx, y + lo * vy, alt), (x + hi * vx, y + hi * vy, alt)], False, False


def _placement_xy(placement, area: Area, idx: int, n_auto: int, world) -> tuple[float, float]:
    half = area.size_km * 500.0
    if isinstance(placement, str) and placement == "auto":
        r = min(AUTO_MIC_RADIUS_M, half * 0.5)
        a = 2 * math.pi * idx / max(n_auto, 1)
        x, y = r * math.cos(a), r * math.sin(a)
    else:
        east, north = placement
        x, y = east * 1000.0, north * 1000.0
    if abs(x) > half or abs(y) > half:
        raise ValueError(f"sensor placement {placement} is outside the {area.size_km} km area")
    return x, y


def build_scenario(ps: PromptScenario, area: Area, world: World) -> dict:
    """PromptScenario + resolved terrain -> a plain dict that Scenario accepts."""
    half_km = area.size_km / 2.0
    half = area.size_km * 500.0

    # sensors first: an attack_sensor behaviour targets one of them
    n_rf_auto = sum(1 for s in ps.sensors if s.type == "rf_df" and s.placement == "auto")
    rf_sites = auto_sites(world, area, n_sites=max(n_rf_auto, 2)) if n_rf_auto else []
    n_auto = sum(1 for s in ps.sensors if s.placement == "auto")
    first_rf_id = next((s.id for s in ps.sensors if s.type == "rf_df"), None)
    sensors, used_sites = [], 0
    for i, s in enumerate(ps.sensors):
        d = {"id": s.id, "type": s.type, "mast_m": s.mast_m, "params": {}}
        if s.type in ("camera", "remote_id"):
            if first_rf_id is None:
                raise ValueError(f"{s.id}: {s.type} needs an rf_df sensor to mount on")
            d["mount"] = first_rf_id  # cameras and RID ride the first receiver's tower
        elif s.type == "rf_df" and s.placement == "auto":
            x, y = rf_sites[used_sites]
            used_sites += 1
            lat, lon = world.to_ll(x, y)
            d["pos"] = [round(float(lat), 6), round(float(lon), 6)]
        else:
            x, y = _placement_xy(s.placement, area, i, n_auto, world)
            lat, lon = world.to_ll(x, y)
            d["pos"] = [round(float(lat), 6), round(float(lon), 6)]
        if s.type == "telemetry":
            d["params"]["objects"] = s.monitors or [o.id for o in ps.objects
                                                    if o.side == "friendly" and o.type != "operator"]
        elif s.type == "reports":
            d["params"]["eppo_civilians"] = 20
        sensors.append(d)
    sensor_ids = {s["id"] for s in sensors}

    objects = []
    for o in ps.objects:
        if o.offset_km is not None:
            x, y = o.offset_km[0] * 1000.0, o.offset_km[1] * 1000.0
            if abs(x) > half or abs(y) > half:
                raise ValueError(f"{o.id}: offset_km {o.offset_km} is outside the area")
        elif o.landmark:
            dlat, dlon = half / 111_195.0, half / (111_195.0 * math.cos(math.radians(area.lat)))
            lat, lon = geocode(o.landmark, viewbox=(area.lon - dlon, area.lat - dlat,
                                                   area.lon + dlon, area.lat + dlat))
            x, y = world.to_xy(lat, lon)
            x, y = float(x), float(y)
            if abs(x) > half or abs(y) > half:
                raise ValueError(f"{o.id}: landmark {o.landmark!r} resolves to ({lat:.5f}, {lon:.5f}), "
                                 f"outside the {area.size_km} km area; give offset_km instead")
        else:
            raise ValueError(f"{o.id}: give offset_km or landmark")
        d: dict = {"id": o.id, "type": o.type, "side": o.side}
        target = None
        if o.behaviour == "attack_sensor":
            tid = o.target_sensor or first_rf_id
            if tid not in sensor_ids:
                raise ValueError(f"{o.id}: target_sensor {tid!r} is not a scenario sensor")
            tsensor = next(s for s in sensors if s["id"] == tid)
            tl, tn = tsensor["pos"]
            target = tuple(world.to_xy(tl, tn))
            target = (float(target[0]), float(target[1]))
        wps, loop, attack = behaviour_path(o.behaviour, x, y, half_km, o.alt_agl_m, target=target)
        if o.behaviour == "static":
            lat, lon = world.to_ll(x, y)
            d["pos"] = [round(float(lat), 6), round(float(lon), 6)]
            d["alt_agl_m"] = o.alt_agl_m
        else:
            path = []
            for wx, wy, walt in wps:
                lat, lon = world.to_ll(wx, wy)
                path.append([round(float(lat), 6), round(float(lon), 6), o.alt_agl_m])
            d["path"] = path
            if loop:
                d["loop"] = True
        d["start_s"] = round(o.start_min * 60.0, 1)
        if o.end_min is not None:
            d["end_s"] = round(o.end_min * 60.0, 1)
        elif attack:  # impact ends the track; the hit sensor goes dark on it
            dist = math.hypot(wps[1][0] - wps[0][0], wps[1][1] - wps[0][1])
            speed = CATALOG[o.type].get("speed_mps", 20.0)
            d["end_s"] = round(d["start_s"] + dist / speed, 1)
            tsensor["destroyed_by"] = o.id
        if o.controls:
            ctrl = _norm(o.controls)
            d["controls"] = next((p.id for p in ps.objects if _norm(p.id) == ctrl), None)
            if d["controls"] is None:
                raise ValueError(f"{o.id}: controls -> unknown object {o.controls!r}")
        if o.gnss_spoof:
            d["gnss_spoof"] = {"start_s": round(o.gnss_spoof[0] * 60.0, 1),
                               "end_s": round(o.gnss_spoof[1] * 60.0, 1)}
        objects.append(d)

    w = ps.weather
    return {
        "name": _slug(ps.title),
        "seed": ps.seed,
        "start": f"{ps.date}T{ps.start_utc}:00Z",
        "duration_s": round(ps.duration_min * 60.0, 1),
        "area": {"lat": area.lat, "lon": area.lon, "size_km": area.size_km},
        "weather": {"wind_from_deg": w.wind_from_deg, "wind_mps": w.wind_mps, "temp_c": w.temp_c,
                    "rh_pct": w.rh_pct, "visibility_km": w.visibility_km, "cloud_pct": w.cloud_pct},
        "objects": objects,
        "sensors": sensors,
    }


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "prompted"


class _Dumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True


def _list_repr(dumper, data):
    flow = all(isinstance(i, (int, float, str, bool)) for i in data)
    return dumper.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=flow)


_Dumper.add_representer(list, _list_repr)


def write_yaml(path: Path, scen: dict, title: str, prompt_text: str) -> None:
    header = [f"# {title}",
              "# Generated by `python -m mirrorworld prompt`; sensor sites and paths computed from real terrain.",
              "# Original prompt:"]
    header += [f"#   {line}" for line in prompt_text.splitlines()]
    body = yaml.dump(scen, Dumper=_Dumper, sort_keys=False, allow_unicode=True, default_flow_style=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(header) + "\n" + body)


# ---------------------------------------------------------------- CLI
def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="mirrorworld prompt",
                                 description="Turn a text brief into a validated scenario YAML via an LLM.")
    ap.add_argument("text")
    ap.add_argument("-o", "--out", default=None, help="output YAML (default scenarios/<title>.yaml)")
    ap.add_argument("--run", action="store_true", help="run the generated scenario afterwards")
    args = ap.parse_args(argv)

    key = load_api_key()
    if not key:
        print("error: no LLM API key found. Set OPENAI_API_KEY in the environment, or add\n"
              "       OPENAI_API_KEY=<key> to a .env file in the repo root.", file=sys.stderr)
        sys.exit(2)

    client = make_client(key)
    model = resolve_model(client)
    feedback = None
    for attempt in range(2):  # one retry with the validator's error text
        ps = ask_llm(client, model, args.text, feedback)
        try:
            lat, lon = geocode(ps.place)
            lat0, lat1, lon0, lon1 = UKRAINE
            if not (lat0 <= lat <= lat1 and lon0 <= lon <= lon1):
                raise ValueError(f"{ps.place!r} geocoded to ({lat:.4f}, {lon:.4f}), outside Ukraine")
            area = Area(lat=round(lat, 5), lon=round(lon, 5), size_km=ps.size_km)
            scen = build_scenario(ps, area, _terrain_world(area))
            Scenario.model_validate(scen)  # the same validator `run` uses
            break
        except (ValidationError, ValueError) as e:
            feedback = str(e)
    else:
        sys.exit(f"error: the LLM plan stayed invalid after one retry:\n{feedback}")

    out = Path(args.out) if args.out else REPO_ROOT / "scenarios" / f"{_slug(ps.title)}.yaml"
    write_yaml(out, scen, ps.title, args.text)
    print(f"wrote {out} ({len(scen['objects'])} objects, {len(scen['sensors'])} sensors, model {model})")
    if args.run:
        from .__main__ import main as run_main

        run_main(["run", str(out), "--skip-missing"])
