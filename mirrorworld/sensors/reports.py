"""Human sensors: an observer post plus ePPO-style civilians reporting what they can
actually hear or see. Perception is computed from the terrain (world.los at 1.7 m), the
catalog sound level / angular size and the real sun elevation; every number in a report
comes from that geometry. The text only verbalises the structured facts — via the LLM
when OPENAI_API_KEY is set, else a template — and never changes them.
"""
import json
import math
import re

import numpy as np
import pandas as pd

from ..catalog import CATALOG
from ..prompt import chat_json, load_api_key, make_client, resolve_model

LABEL = {"hostile": "target", "unknown": "target", "friendly": "friendly", "neutral": "clutter"}

PERSON_M = 1.7          # eye/ear height above ground
HEAR_DBA = 40.0         # hearing threshold for a quiet rural night/day
LOS_PENALTY_DB = 15.0   # terrain screening between source and listener
ABSORB_DB_PER_M = 0.005 # excess absorption beyond 1/r spreading
SEE_RAD = 0.0003        # ~1 arcmin: smallest angular size a person resolves
CIVIL_DUSK_DEG = -6.0   # eyes stop working around civil dusk
EPISODE_S = 15.0        # continuous perception needed to make one episode
GAP_S = 2.0             # episodes merge across dropouts this short
DT_S = 1.0              # perception sampling step

# civilians live around the area's settlements and the observer post (lat, lon)
SETTLEMENTS = [("Korsun-Shevchenkivskyi", 49.4180, 31.2557), ("Stebliv", 49.4019, 31.0956)]
CIVILIAN_RADIUS_M = 3000.0

# what people call things, per catalog type and cue (seen or heard): [(guess uk, guess en, p)]
CONFUSION = {
    "shahed136": {"hear": [("шахед (звук мопеда)", "shahed (moped sound)", 0.60),
                           ("мопед", "moped", 0.30), ("дрон", "drone", 0.10)],
                  "see": [("шахед (звук мопеда)", "shahed (moped sound)", 0.75),
                          ("дрон", "drone", 0.25)]},
    "dji_mavic3": {"hear": [("дрон", "drone", 0.55), ("квадрокоптер", "quadcopter", 0.45)],
                   "see": [("дрон", "drone", 0.50), ("квадрокоптер", "quadcopter", 0.50)]},
    "fpv_analog": {"hear": [("FPV", "FPV", 0.45), ("дрон", "drone", 0.35),
                            ("квадрокоптер", "quadcopter", 0.20)],
                   "see": [("дрон", "drone", 0.45), ("квадрокоптер", "quadcopter", 0.35),
                           ("FPV", "FPV", 0.20)]},
    "fpv_fiber": {"hear": [("FPV (тільки за звуком)", "FPV (by sound only)", 0.70),
                           ("дрон", "drone", 0.20), ("мопед", "moped", 0.10)],
                  "see": [("дрон", "drone", 0.45), ("квадрокоптер", "quadcopter", 0.35),
                          ("FPV", "FPV", 0.20)]},
    "geese": {"hear": [("зграя птахів", "flock of birds", 0.50), ("дрон", "drone", 0.50)],
              "see": [("зграя птахів", "flock of birds", 0.60), ("дрон", "drone", 0.40)]},
}

_COMPASS_UK = ["з півночі", "з північного сходу", "зі сходу", "з південного сходу",
               "з півдня", "з південного заходу", "із заходу", "з північного заходу"]
_COMPASS_EN = ["the north", "the northeast", "the east", "the southeast",
               "the south", "the southwest", "the west", "the northwest"]


# ---------------------------------------------------------------- physics
def sun_elevation_deg(unix_ts, lat, lon):
    """Solar elevation (degrees) from the NOAA/Meeus approximate position; unix seconds."""
    d = np.asarray(unix_ts, dtype=np.float64) / 86400.0 - 10957.5  # days since J2000
    g = np.radians((357.529 + 0.98560028 * d) % 360.0)             # mean anomaly
    q = (280.459 + 0.98564736 * d) % 360.0                         # mean longitude
    ll = np.radians((q + 1.915 * np.sin(g) + 0.020 * np.sin(2 * g)) % 360.0)
    omega = np.radians(125.04 - 1934.136 * d)
    lam = ll - np.radians(0.00569 + 0.00478 * np.sin(omega))       # apparent longitude
    eps = np.radians(23.439 - 0.00000036 * d + 0.00256 * np.cos(omega))
    dec = np.arcsin(np.sin(eps) * np.sin(lam))
    ra = np.arctan2(np.cos(eps) * np.sin(lam), np.cos(lam))
    gmst = (18.697374558 + 24.06570982441908 * d) % 24.0           # hours
    ha = np.radians((gmst + lon / 15.0) * 15.0) - ra               # hour angle
    lat_r = np.radians(lat)
    el = np.arcsin(np.sin(lat_r) * np.sin(dec) + np.cos(lat_r) * np.cos(dec) * np.cos(ha))
    return np.degrees(el)


def hear_level_db(level_db_1m, r_m, los):
    """Level at the listener: 1/r spreading + excess absorption, -15 dB behind terrain."""
    r = np.maximum(np.asarray(r_m, dtype=np.float64), 1.0)
    return (level_db_1m - 20.0 * np.log10(r) - ABSORB_DB_PER_M * r
            - np.where(np.asarray(los, dtype=bool), 0.0, LOS_PENALTY_DB))


def can_hear(level_db_1m, r_m, los):
    return hear_level_db(level_db_1m, r_m, los) > HEAR_DBA


def can_see(los, span_m, r_m, sun_deg):
    """Seen when the ray clears terrain, the object spans > ~1 arcmin and the sun is up."""
    return (np.asarray(los, dtype=bool)
            & (span_m / np.maximum(np.asarray(r_m, dtype=np.float64), 1.0) > SEE_RAD)
            & (np.asarray(sun_deg, dtype=np.float64) > CIVIL_DUSK_DEG))


def episodes(perceived):
    """Boolean samples at DT_S -> spans (i0, i1) of continuous perception >= EPISODE_S,
    merging dropouts <= GAP_S."""
    idx = np.flatnonzero(perceived)
    if idx.size == 0:
        return []
    runs = np.split(idx, np.flatnonzero(np.diff(idx) > GAP_S / DT_S + 1) + 1)
    out = []
    for run in runs:
        i0, i1 = int(run[0]), int(run[-1])
        if (i1 - i0 + 1) * DT_S >= EPISODE_S:
            out.append((i0, i1))
    return out


# ---------------------------------------------------------------- people & text
def _people(sensor, ctx):
    """The observer post plus N civilians at deterministic random points within 3 km of
    the area's settlements and the post."""
    rng = ctx.rng(f"reports:{sensor.id}:people")
    anchors = SETTLEMENTS + [("observer post", sensor.pos[0], sensor.pos[1])]
    people = [{"id": "observer", "type": "observer", "lat": sensor.pos[0], "lon": sensor.pos[1]}]
    for i in range(int(sensor.params.get("eppo_civilians", 0))):
        _, alat, alon = anchors[i % len(anchors)]
        r = CIVILIAN_RADIUS_M * math.sqrt(rng.random())
        a = 2 * math.pi * rng.random()
        dx, dy = r * math.sin(a), r * math.cos(a)
        lat = alat + dy / 111_195.0
        lon = alon + dx / (111_195.0 * math.cos(math.radians(alat)))
        # the 3 km disk can stick out of the area: clamp onto the area square
        x, y = ctx.world.to_xy(lat, lon)
        lim = ctx.cfg.area.size_km * 500.0 - 200.0
        x, y = float(np.clip(x, -lim, lim)), float(np.clip(y, -lim, lim))
        lat, lon = ctx.world.to_ll(x, y)
        people.append({
            "id": f"civilian_{i:02d}", "type": "eppo",
            "lat": float(lat), "lon": float(lon),
        })
    return people


def compass(deg):
    i = int(((deg % 360.0) + 22.5) // 45.0) % 8
    return _COMPASS_UK[i], _COMPASS_EN[i]


def _render_template(f):
    """Template text from the structured facts alone (the no-key / no-LLM path)."""
    frm_uk, frm_en = compass(f["direction_deg"])
    dist_uk = (f"{round(f['est_distance_m'] / 50) * 50:.0f} м" if f["est_distance_m"] < 1000
               else f"{max(round(f['est_distance_m'] / 500) * 0.5, 0.5):.1f} км")
    dist_en = (f"{round(f['est_distance_m'] / 50) * 50:.0f} m" if f["est_distance_m"] < 1000
               else f"{max(round(f['est_distance_m'] / 500) * 0.5, 0.5):.1f} km")
    if f["est_alt_m"] is None:
        alt_uk, alt_en = "", ""
    else:
        lvl = "низько" if f["est_alt_m"] < 50 else ("на середній висоті" if f["est_alt_m"] <= 300 else "високо")
        lvl_en = {"низько": "low", "на середній висоті": "medium", "високо": "high"}[lvl]
        alt_uk = f", {lvl}, ~{f['est_alt_m']:.0f} м"
        alt_en = f", {lvl_en}, ~{f['est_alt_m']:.0f} m"
    cnt = "" if f["count"] == 1 else f" ×{f['count']}"
    if f["reporter_type"] == "observer":
        uk = (f"SALUTE: S — {f['count']} од., {f['est_type']}; A — у польоті{alt_uk}, "
              f"напрямок {f['direction_deg']:.0f}° ({frm_uk}); L — {dist_uk} {frm_uk} від поста; "
              f"U — не встановлено; T — {f['obs_time_utc']}; E — спостереження: {f['perceived']}.")
        en = (f"SALUTE: S — {f['count']} x {f['est_type_en']}; A — in flight{alt_en}, "
              f"bearing {f['direction_deg']:.0f} ({frm_en}); L — {dist_en} toward {frm_en} of the post; "
              f"U — not determined; T — {f['obs_time_utc']}; E — observed by {f['perceived']}.")
    else:
        verb_uk = {"hear": "Чую", "see": "Бачу", "both": "Чую і бачу"}[f["perceived"]]
        verb_en = {"hear": "Hearing", "see": "Seeing", "both": "Hearing and seeing"}[f["perceived"]]
        uk = f"{verb_uk} {f['est_type']}{cnt}, летить {frm_uk}{alt_uk}, десь {dist_uk}."
        en = (f"{verb_en} {f['est_type_en']}{cnt}, flying from {frm_en}{alt_en}, about {dist_en} out.")
    return uk, en


LLM_SYSTEM = """You verbalise structured observation facts into short realistic reports from Ukraine.
Rules:
- NEVER change, add or infer facts. Every report MUST contain the fact numbers: the direction
  (use direction_uk / direction_en or the degrees), the estimated distance and (when present) the
  estimated altitude, accurate to about 15%.
- The perception cue comes from "perceived" ONLY: hear -> "чую" / "I hear"; see -> "бачу" / "I see";
  both -> "чую і бачу" / "I hear and see". ePPO texts must START with that cue word. Never mention
  the other sense: no "чути" when perceived is "see", no "бачити" when it is "hear".
- Do not invent headings of flight, speeds, places, times or counts; the facts JSON is the only source.
- For reporter_type "eppo": short civilian ePPO/Telegram style in Ukrainian, plus an English translation.
- For reporter_type "observer": compact military SALUTE format in Ukrainian and English.
Examples (style and cue only):
  facts: perceived "see", est_type "дрон", direction_uk "зі сходу", direction_en "the east",
         est_distance_m 1200, est_alt_m 80 -> text_uk: "Бачу дрон, зі сходу, низько, ~80 м, десь 1,2 км."
         text_en: "I see a drone, from the east, low, ~80 m, about 1.2 km out."
  facts: perceived "hear", est_type "шахед (звук мопеда)", direction_uk "з півдня",
         direction_en "the south", est_distance_m 2400, est_alt_m null ->
         text_uk: "Чую шахед (звук мопеда), з півдня, десь 2,4 км."
         text_en: "I hear a shahed (moped sound), from the south, about 2.4 km out."
Output strict JSON: {"reports": [{"record_id": ..., "text_uk": ..., "text_en": ...}]} with one
entry per input fact, in the same order."""

_NUM = re.compile(r"\d+(?:[.,]\d+)?")
# cue roots with boundaries: "чу" must not match inside "бачу", etc.
_HEAR_UK = re.compile(r"(?<![а-яіїєґ])чу", re.I)
_SEE_UK = re.compile(r"(?<![а-яіїєґ])бач", re.I)
_HEAR_EN = re.compile(r"\b(?:hear|hears|hearing|heard)\b", re.I)
_SEE_EN = re.compile(r"\b(?:see|sees|seeing|saw|seen)\b", re.I)


def check_fact_text(f, uk, en):
    """True when the text still carries the facts: distance, altitude, direction and the
    right perception cue. Used to enforce that the LLM only verbalises."""
    for txt, lang in ((uk, "uk"), (en, "en")):
        low = txt.lower()
        nums = [float(m.replace(",", ".")) for m in _NUM.findall(txt)]
        d = f["est_distance_m"]
        if not any(abs(n - d) <= 0.15 * d or abs(n - d / 1000.0) <= max(0.15 * d / 1000.0, 0.3)
                   for n in nums):
            return False, f"{f['record_id']} text_{lang} dropped the distance {d:.0f} m"
        if f["est_alt_m"]:
            a = f["est_alt_m"]
            if not any(abs(n - a) <= max(0.15 * a, 50.0) for n in nums):
                return False, f"{f['record_id']} text_{lang} dropped the altitude {a:.0f} m"
        frm_uk, frm_en = compass(f["direction_deg"])
        diff = [(abs(n - f["direction_deg"]) + 180.0) % 360.0 - 180.0 for n in nums]
        if not ((frm_uk in low) if lang == "uk" else (frm_en in low)) and not any(abs(x) <= 6.0 for x in diff):
            return False, f"{f['record_id']} text_{lang} dropped the direction {f['direction_deg']:.0f} deg"
    if f["perceived"] == "hear" and (_SEE_UK.search(uk) or _SEE_EN.search(en)):
        return False, f"{f['record_id']} claims seeing but perceived is 'hear'"
    if f["perceived"] == "see" and (_HEAR_UK.search(uk) or _HEAR_EN.search(en)):
        return False, f"{f['record_id']} claims hearing but perceived is 'see'"
    if f["reporter_type"] == "observer" and "salute" not in (uk + " " + en).lower():
        return False, f"{f['record_id']} observer text is not SALUTE"
    return True, ""


def _verbalise(facts, notes):
    """facts -> ({record_id: (text_uk, text_en, source)}, llm model or None).
    Templates when the LLM is absent, or per record where its text changes the facts."""
    out = {f["record_id"]: (*_render_template(f), "template") for f in facts}
    key = load_api_key()
    if not facts:
        return out, None
    if not key:
        notes.append("OPENAI_API_KEY not set: report texts are templates verbalising the structured facts")
        return out, None
    try:
        client = make_client(key)
        model = resolve_model(client)
    except Exception as e:  # noqa: BLE001 - explicit degraded mode, facts unaffected
        notes.append(f"LLM unreachable ({e}): report texts are templates")
        return out, None
    drifted = 0
    for a in range(0, len(facts), 10):
        chunk = facts[a:a + 10]
        payload = []
        for f in chunk:
            frm_uk, frm_en = compass(f["direction_deg"])
            payload.append({k: f[k] for k in ("record_id", "reporter_type", "obs_time_utc", "perceived",
                                              "est_type", "est_type_en", "count", "direction_deg",
                                              "est_distance_m", "est_alt_m")}
                           | {"direction_uk": frm_uk, "direction_en": frm_en})
        user = json.dumps(payload, ensure_ascii=False)

        def validate(obj, wanted={f["record_id"] for f in chunk}):
            rows = obj.get("reports") if isinstance(obj, dict) else None
            if not isinstance(rows, list) or {r.get("record_id") for r in rows} != wanted:
                raise ValueError("expected a 'reports' list covering exactly the input record_ids")
            return rows

        try:
            rows = chat_json(client, model, LLM_SYSTEM, user, validate)
        except Exception as e:  # noqa: BLE001 - explicit degraded mode per batch
            notes.append(f"LLM text call failed for {len(chunk)} report(s), using templates: {e}")
            continue
        by_id = {f["record_id"]: f for f in chunk}
        for r in rows:
            ok, why = check_fact_text(by_id[r["record_id"]], r.get("text_uk") or "", r.get("text_en") or "")
            if ok:
                out[r["record_id"]] = (r["text_uk"], r["text_en"], "llm")
            else:
                drifted += 1  # this record keeps its template: the facts win over the prose
    if drifted:
        notes.append(f"{drifted} report(s) had LLM text that changed the facts; those use templates")
    return out, model


# ---------------------------------------------------------------- run
def run(sensors, ctx):
    (ctx.out / "answer_key").mkdir(parents=True, exist_ok=True)
    for sensor in sensors:
        _post(sensor, ctx)


def _post(sensor, ctx):
    out = ctx.out / "sensors" / sensor.id
    out.mkdir(parents=True, exist_ok=True)
    people = _people(sensor, ctx)
    sun_base = ctx.cfg.start.timestamp()
    reports, notes, episodes_seen = [], [], 0

    obj_ids = sorted(ctx.truth["object_id"].unique())
    for person in people:
        rng = ctx.rng(f"reports:{sensor.id}:{person['id']}")
        px, py = ctx.world.to_xy(person["lat"], person["lon"])
        px, py, pz = float(px), float(py), float(ctx.world.height(px, py)) + PERSON_M
        for obj_id in obj_ids:
            obj = ctx.objects[obj_id]
            cat = CATALOG[obj.type]
            snd, span = cat.get("sound"), cat.get("span_m")
            if snd is None and span is None:
                continue  # Wi-Fi, jammers, people: nothing to hear or see
            rows = ctx.truth.loc[ctx.truth["object_id"] == obj_id, "t"]
            ts = np.arange(math.ceil(rows.min()), math.floor(rows.max()) + DT_S, DT_S)
            st = ctx.state(obj_id, ts)
            ok = np.isfinite(st["x"])
            if not ok.any():
                continue
            dx, dy, dz = st["x"] - px, st["y"] - py, st["z"] - pz
            r = np.sqrt(dx * dx + dy * dy + dz * dz)
            r_max = max(10 ** ((snd["level_db_1m"] - HEAR_DBA) / 20.0) if snd else 0.0,
                        span / SEE_RAD if span else 0.0)
            near = ok & (r <= r_max)
            los = np.zeros(ts.size, dtype=bool)
            if near.any():  # terrain between listener and object, eye/ear at 1.7 m
                oxyz = np.stack([st["x"][near], st["y"][near], st["z"][near]], axis=1)
                los[near] = ctx.world.los(oxyz, np.array([px, py, pz]))
            hear = np.zeros(ts.size, dtype=bool)
            if snd:
                hear[near] = can_hear(snd["level_db_1m"], r[near], los[near])
            see = np.zeros(ts.size, dtype=bool)
            if span:
                sun = sun_elevation_deg(sun_base + ts, person["lat"], person["lon"])
                see[near] = can_see(los[near], span, r[near], sun[near])

            for i0, i1 in episodes(hear | see):
                episodes_seen += 1
                if rng.random() > (1.0 if person["type"] == "observer" else 0.5):
                    continue
                obs_t = float((ts[i0] + ts[i1]) / 2.0)
                st_m = ctx.state(obj_id, np.array([obs_t]))
                ox, oy, oz = float(st_m["x"][0]), float(st_m["y"][0]), float(st_m["z"][0])
                true_r = math.sqrt((ox - px) ** 2 + (oy - py) ** 2 + (oz - pz) ** 2)
                true_az = math.degrees(math.atan2(ox - px, oy - py)) % 360.0
                delay = float(rng.uniform(30.0, 90.0) if person["type"] == "observer"
                              else rng.uniform(60.0, 240.0))
                t_report = obs_t + delay
                if t_report > ctx.cfg.duration_s or not ctx.alive(sensor, t_report):
                    continue  # reported after the scenario window (or the post is gone)
                sigma = 8.0 if person["type"] == "observer" else 20.0
                seen = bool(see[i0:i1 + 1].any())
                heard = bool(hear[i0:i1 + 1].any())
                perceived = "both" if seen and heard else ("see" if seen else "hear")
                guesses = CONFUSION.get(obj.type, {}).get("see" if perceived == "see" else "hear",
                                                          [("дрон", "drone", 1.0)])
                gi = rng.choice(len(guesses), p=[g[2] for g in guesses])
                if obj.type == "geese" and guesses[gi][0].startswith("зграя"):
                    count = int(rng.integers(7, 31))  # a flock read as birds: the flock size
                else:
                    count = 2 if rng.random() < 0.1 else 1
                reports.append({
                    "t": t_report,
                    "reporter_type": person["type"],
                    "reporter_lat": round(person["lat"], 3),  # own position rounded to 100 m
                    "reporter_lon": round(person["lon"], 3),
                    "direction_deg": round((true_az + float(rng.normal(0.0, sigma))) % 360.0, 1),
                    "est_distance_m": round(float(true_r * rng.lognormal(0.0, 0.5)) / 10.0) * 10,
                    "est_type": guesses[gi][0],
                    "est_type_en": guesses[gi][1],
                    "count": count,
                    "est_alt_m": (round(float(st_m["z"][0] - ctx.world.height(ox, oy))
                                        * rng.lognormal(0.0, 0.35)) / 10.0) * 10 if seen else None,
                    "perceived": perceived,
                    "obs_time_utc": ctx.iso(obs_t),
                    "_obj": obj_id, "_true_r": true_r, "_true_az": true_az,
                    "_delay": delay,
                })

    reports.sort(key=lambda f: f["t"])
    for n, f in enumerate(reports):
        f["record_id"] = f"{sensor.id}-{n:06d}"
    texts, model = _verbalise(reports, notes)

    rows, answers = [], []
    for f in reports:
        uk, en, source = texts[f["record_id"]]
        rows.append({
            "record_id": f["record_id"], "time_utc": ctx.iso(f["t"]),
            "reporter_type": f["reporter_type"], "reporter_lat": f["reporter_lat"],
            "reporter_lon": f["reporter_lon"], "direction_deg": f["direction_deg"],
            "est_distance_m": f["est_distance_m"], "est_type": f["est_type"],
            "count": f["count"], "est_alt": f["est_alt_m"], "text_uk": uk, "text_en": en,
        })
        answers.append({
            "record_id": f["record_id"], "object_id": f["_obj"],
            "label": LABEL[ctx.objects[f["_obj"]].side], "perceived_by": f["perceived"],
            "obs_time_utc": f["obs_time_utc"], "true_range_m": round(f["_true_r"], 1),
            "true_az_deg": round(f["_true_az"], 1), "delay_s": round(f["_delay"], 1),
            "text_source": source,
        })
    cols = ["record_id", "time_utc", "reporter_type", "reporter_lat", "reporter_lon",
            "direction_deg", "est_distance_m", "est_type", "count", "est_alt",
            "text_uk", "text_en"]
    acols = ["record_id", "object_id", "label", "perceived_by", "obs_time_utc",
             "true_range_m", "true_az_deg", "delay_s", "text_source"]
    pd.DataFrame(rows, columns=cols).to_csv(out / "reports.csv", index=False)
    with open(out / "reports.jsonl", "w") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    pd.DataFrame(answers, columns=acols).to_csv(ctx.out / "answer_key" / f"{sensor.id}.csv", index=False)

    n_llm = sum(1 for v in texts.values() if v[2] == "llm")
    (out / "status.json").write_text(json.dumps({
        "sensor_id": sensor.id,
        "text_source": "llm" if reports and n_llm == len(reports) else "template",
        "llm_model": model, "llm_reports": n_llm,
        "people": {"observer": 1, "eppo_civilians": len(people) - 1},
        "episodes": episodes_seen, "reports": len(reports),
        "notes": notes,
    }, ensure_ascii=False, indent=1))
