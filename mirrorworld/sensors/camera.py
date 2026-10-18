"""EO1: a pan-tilt electro-optical camera on a mast (sensor type `camera`).

Blind sensor: it records only what physically lands in its frame. Pointing comes from the
newest fused RF fix (or, in debug mode, from a truth object), so the target sits off-centre
by the real estimate error or misses the frame entirely. The scene is built from the real
sun position and the real DSM horizon silhouette; targets are drawn at their true angular
size and faded by Koschmieder haze. Everything true about the scene (object ids, occlusion,
true boxes) lives in answer_key/EO1*.csv, never under sensors/.

answer_key/EO1_frames.csv rows cover every object whose true box lies within 1.5x the frame
box (the cue can miss): `in_frame` says whether the box touches the recorded image,
`occluded` whether terrain hid it. Drawn == in_frame and not occluded.
"""
import csv
import math
from datetime import timedelta

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

from ..catalog import CATALOG
from ..world import K_REFRACT, R_EARTH

DEFAULTS = dict(fov_deg=3.0, width=1280, height=720, fps=1.0, cue="rf", max_frames=600,
                jpeg_quality=82, assumed_agl_m=100.0)
GROUND_CLASSES = {"OcuSync RC", "ELRS LoRa FHSS", "Wi-Fi", "Wideband noise"}  # cueing skips these
LABEL = {"hostile": "target", "unknown": "target", "friendly": "friendly", "neutral": "clutter"}
SHAPE_CLASS = {"quad": "multirotor", "delta": "fixed-wing", "flock": "bird"}
CLASSES = ("multirotor", "fixed-wing", "bird")
DARK = np.array([35.0, 35.0, 42.0])  # silhouette colour before haze mixing
EXPOSURE_S = 0.02  # 1/50 s shutter: motion blur only when apparent motion is fast
# sky colours keyed on sun elevation (deg): zenith and horizon gradient end points
SUN_KEYS = np.array([-18.0, -6.0, 0.0, 6.0, 18.0, 40.0])
ZENITH = np.array([[8, 10, 24], [14, 18, 42], [42, 56, 112], [62, 92, 168], [70, 118, 200], [66, 122, 208]], float)
HORIZON = np.array([[16, 20, 38], [36, 42, 72], [212, 132, 92], [232, 178, 128], [172, 202, 232], [168, 202, 232]], float)
GLOW = np.array([120.0, 70.0, 40.0])  # warm light toward the sun near the horizon


# --- params / geometry -------------------------------------------------
def _params(sensor):
    p = {**DEFAULTS, **sensor.params}
    if not 0.5 <= float(p["fov_deg"]) <= 90:
        raise ValueError(f"camera {sensor.id}: fov_deg must be in [0.5, 90], got {p['fov_deg']!r}")
    for k in ("width", "height"):
        if not isinstance(p[k], int) or p[k] < 16:
            raise ValueError(f"camera {sensor.id}: {k} must be an int >= 16, got {p[k]!r}")
    if float(p["fps"]) <= 0:
        raise ValueError(f"camera {sensor.id}: fps must be > 0, got {p['fps']!r}")
    if not isinstance(p["max_frames"], int) or p["max_frames"] < 1:
        raise ValueError(f"camera {sensor.id}: max_frames must be an int >= 1, got {p['max_frames']!r}")
    if not 10 <= int(p["jpeg_quality"]) <= 100:
        raise ValueError(f"camera {sensor.id}: jpeg_quality must be in [10, 100], got {p['jpeg_quality']!r}")
    if float(p["assumed_agl_m"]) < 0:
        raise ValueError(f"camera {sensor.id}: assumed_agl_m must be >= 0, got {p['assumed_agl_m']!r}")
    if p["cue"] != "rf" and not str(p["cue"]).startswith("truth:"):
        raise ValueError(f"camera {sensor.id}: cue must be 'rf' or 'truth:<object_id>', got {p['cue']!r}")
    return p


def focal_px(width, fov_deg):
    """Pinhole focal length in pixels: fov_deg is the horizontal field of view."""
    return (width / 2.0) / math.tan(math.radians(fov_deg) / 2.0)


def solar_position(dt, lat, lon):
    """(elevation, azimuth) of the sun in degrees, NOAA solar-calculator algorithm (~0.02 deg)."""
    y, m = dt.year, dt.month
    d = dt.day + (dt.hour + dt.minute / 60 + (dt.second + dt.microsecond / 1e6) / 3600) / 24
    if m <= 2:
        y, m = y - 1, m + 12
    b = 2 - y // 100 + y // 400
    jd = int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + b - 1524.5
    t = (jd - 2451545.0) / 36525.0
    l0 = (280.46646 + t * (36000.76983 + t * 0.0003032)) % 360
    mr = np.radians(357.52911 + t * (35999.05029 - 0.0001537 * t))
    e = 0.016708634 - t * (0.000042037 + 0.0000001267 * t)
    c = (np.sin(mr) * (1.914602 - t * (0.004817 + 0.000014 * t))
         + np.sin(2 * mr) * (0.019993 - 0.000101 * t) + np.sin(3 * mr) * 0.000289)
    omega = np.radians(125.04 - 1934.136 * t)
    app_long = l0 + c - 0.00569 - 0.00478 * np.sin(omega)
    mean_obliq = 23 + (26 + (21.448 - t * (46.815 + t * (0.00059 - t * 0.001813))) / 60) / 60
    obliq = mean_obliq + 0.00256 * np.cos(omega)
    decl = np.arcsin(np.sin(np.radians(obliq)) * np.sin(np.radians(app_long)))
    y2 = np.tan(np.radians(obliq / 2)) ** 2
    l0r = np.radians(l0)
    eq_time = 4 * np.degrees(y2 * np.sin(2 * l0r) - 2 * e * np.sin(mr)
                             + 4 * e * y2 * np.sin(mr) * np.cos(2 * l0r)
                             - 0.5 * y2 ** 2 * np.sin(4 * l0r) - 1.25 * e ** 2 * np.sin(2 * mr))
    minutes = (dt.hour * 3600 + dt.minute * 60 + dt.second + dt.microsecond / 1e6) / 60
    ha = np.radians((minutes + eq_time + 4 * lon) % 1440 / 4 - 180)  # hour angle
    latr = np.radians(lat)
    zen = np.arccos(np.clip(np.sin(latr) * np.sin(decl) + np.cos(latr) * np.cos(decl) * np.cos(ha), -1, 1))
    az = (np.degrees(np.arctan2(np.sin(ha),
                                np.cos(ha) * np.sin(latr) - np.tan(decl) * np.cos(latr))) + 180) % 360
    return 90.0 - np.degrees(zen), az


def horizon_profile(world, cam_xyz, az_step_deg=0.02, d_max=20000.0):
    """(azs, elev_deg, dist_m): max terrain elevation angle per azimuth and the distance at
    which it is reached. Ray-march the DSM out to d_max, counting the earth bulge
    d^2/(2 k R) as raised terrain (the same convention as World.los). Terrain beyond the
    DEM grid is clamped to its edge heights."""
    azs = np.arange(0.0, 360.0, az_step_deg)
    d = np.concatenate([np.arange(30.0, 2000.1, 10.0), np.geomspace(2010.0, d_max, 200)])
    bulge = d ** 2 / (2 * K_REFRACT * R_EARTH)
    x_lo, x_hi = world.x0 + 1e-3, world.x0 + world.spacing * (world.n - 1) - 1e-3
    out = np.empty(azs.size)
    dstar = np.empty(azs.size)
    for a0 in range(0, azs.size, 1500):
        az = np.radians(azs[a0:a0 + 1500])
        xs = np.clip(cam_xyz[0] + np.sin(az)[:, None] * d, x_lo, x_hi)
        ys = np.clip(cam_xyz[1] + np.cos(az)[:, None] * d, x_lo, x_hi)
        h = world.height(xs, ys)
        ang = np.degrees(np.arctan2(h + bulge - cam_xyz[2], d))
        i = np.argmax(ang, axis=1)
        out[a0:a0 + 1500] = ang[np.arange(ang.shape[0]), i]
        dstar[a0:a0 + 1500] = d[i]
    return azs, out, dstar


def project(cam_xyz, obj_xyz, az_deg, el_deg, f_px, width, height):
    """Pinhole projection of a point: image col/row and 3-D range from the camera."""
    dx, dy, dz = (np.asarray(obj_xyz, float) - np.asarray(cam_xyz, float)).tolist()
    horiz = math.hypot(dx, dy)
    rng = math.sqrt(horiz * horiz + dz * dz)
    daz = (math.degrees(math.atan2(dx, dy)) - az_deg + 180.0) % 360.0 - 180.0
    del_ = math.degrees(math.atan2(dz, horiz)) - el_deg
    return {"col": width / 2 + f_px * math.tan(math.radians(daz)),
            "row": height / 2 - f_px * math.tan(math.radians(del_)),
            "range_m": rng}


def _extent_px(shape, span_m, rng_m, f_px):
    """Rendered box size in pixels: quad/delta span_m wide, a flock spreads over ~30 m."""
    w_m, h_m = {"quad": (span_m, span_m), "delta": (span_m, 0.75 * span_m),
                "flock": (30.0, 16.0)}[shape]
    return w_m / rng_m * f_px, h_m / rng_m * f_px


def frame_objects(world, cam_xyz, objs, az_deg, el_deg, f_px, width, height):
    """Truth geometry for one frame: every object whose box is near the frame. pixels_on_object
    is the span projected to pixels, span_m / range * f_px; occluded uses terrain line of sight."""
    rows = []
    for o in objs:
        pt = project(cam_xyz, o["xyz"], az_deg, el_deg, f_px, width, height)
        w, h = _extent_px(o["shape"], o["span_m"], pt["range_m"], f_px)
        x0, y0 = pt["col"] - w / 2, pt["row"] - h / 2
        near = (abs(pt["col"] - width / 2) <= 1.5 * width / 2 + w / 2
                and abs(pt["row"] - height / 2) <= 1.5 * height / 2 + h / 2)
        if not near:
            continue
        pm = project(cam_xyz, o["xyz_prev"], az_deg, el_deg, f_px, width, height)
        rows.append({
            "object_id": o["id"], "shape": o["shape"],
            "col": pt["col"], "row": pt["row"], "range_m": pt["range_m"],
            "pixels_on_object": o["span_m"] / pt["range_m"] * f_px,
            "true_bbox": (x0, y0, w, h),
            "in_frame": bool(x0 < width and x0 + w > 0 and y0 < height and y0 + h > 0),
            "occluded": not bool(world.los(cam_xyz, o["xyz"])),
            "motion": (pt["col"] - pm["col"], pt["row"] - pm["row"]),
        })
    return rows


# --- rendering ---------------------------------------------------------
def _silhouette(shape, pixel_span, extent_px, dots, supers=4):
    """4x supersampled alpha mask (h, w) for one object silhouette."""
    w = max(int(round(extent_px[0])), 1)
    h = max(int(round(extent_px[1])), 1)
    xs = (np.arange(w * supers) + 0.5) / (w * supers) - 0.5
    ys = (np.arange(h * supers) + 0.5) / (h * supers) - 0.5
    x, y = np.meshgrid(xs, ys)
    if shape == "quad":  # X frame with four rotor discs
        m = ((np.abs(x - y) < 0.09) | (np.abs(x + y) < 0.09))
        for sx, sy in ((0.36, 0.36), (-0.36, 0.36), (0.36, -0.36), (-0.36, -0.36)):
            m |= (x - sx) ** 2 + (y - sy) ** 2 < 0.16 ** 2
    elif shape == "delta":  # flying wing, nose up
        m = (y >= -0.5) & (y <= 0.5) & (np.abs(x) <= 0.5 * (y + 0.5))
    else:  # flock: dots in a V (positions in metres, laid out once per object)
        m = np.zeros(x.shape, bool)
        rx = 0.5 * pixel_span / max(extent_px[0], 1e-6)  # dot radius in unit coords
        ry = 0.5 * pixel_span / max(extent_px[1], 1e-6)
        for dxm, dym in dots:
            m |= (((x - dxm / 30.0) / rx) ** 2 + ((y - dym / 16.0) / ry) ** 2) < 1.0
    return m.reshape(h, supers, w, supers).mean(axis=(1, 3))


def _stamp(img, alpha, colour, col, row):
    """Alpha-blend a small mask into img centred at (col, row)."""
    H, W, _ = img.shape
    h, w = alpha.shape
    x0, y0 = int(round(col - w / 2)), int(round(row - h / 2))
    xs0, ys0 = max(x0, 0), max(y0, 0)
    xs1, ys1 = min(x0 + w, W), min(y0 + h, H)
    if xs0 >= xs1 or ys0 >= ys1:
        return
    a = alpha[ys0 - y0:ys1 - y0, xs0 - x0:xs1 - x0, None]
    img[ys0:ys1, xs0:xs1] = img[ys0:ys1, xs0:xs1] * (1 - a) + colour * a


def paint_objects(img, rows, f_px, dots_by_id, visibility_km):
    """Draw every object that is in frame and not terrain-occluded, dark against the sky with
    contrast reduced by Koschmieder haze exp(-3.912 r / V), smeared along apparent motion."""
    for r in rows:
        if r["occluded"] or not r["in_frame"]:
            continue
        contrast = math.exp(-3.912 * (r["range_m"] / 1000.0) / visibility_km)
        h, w = img.shape[:2]
        bg = img[int(np.clip(r["row"], 0, h - 1)), int(np.clip(r["col"], 0, w - 1))]
        colour = bg * (1.0 - contrast) + DARK * contrast
        alpha = _silhouette(r["shape"], r["pixels_on_object"],
                            (r["true_bbox"][2], r["true_bbox"][3]), dots_by_id.get(r["object_id"], ()))
        md = math.hypot(*r["motion"])
        offs = [(0.0, 0.0)] if md <= 1.0 else [(-0.5 * r["motion"][0], -0.5 * r["motion"][1]),
                                               (0.0, 0.0),
                                               (0.5 * r["motion"][0], 0.5 * r["motion"][1])]
        for dx, dy in offs:
            _stamp(img, alpha / len(offs), colour, r["col"] + dx, r["row"] + dy)


def _scene(p, sun_el, sun_az, az0, el0, f_px, hel_col, dstar_col, cam_agl_m, visibility_km, rng):
    """Sky gradient from the real sun, real DSM horizon silhouette, hazed dark ground."""
    H, W = p["height"], p["width"]
    cols, rows = np.arange(W), np.arange(H)
    daz_col = (az0 + np.degrees(np.arctan((cols - W / 2) / f_px)) - sun_az + 180.0) % 360.0 - 180.0
    el_row = el0 - np.degrees(np.arctan((rows - H / 2) / f_px))

    zen = np.array([float(np.interp(sun_el, SUN_KEYS, ZENITH[:, i])) for i in range(3)])
    hor = np.array([float(np.interp(sun_el, SUN_KEYS, HORIZON[:, i])) for i in range(3)])
    g = np.clip(el_row / 45.0, 0.0, 1.0)[:, None]
    base = hor * (1 - g) + zen * g  # (H, 3) vertical gradient
    bright = 0.75 + 0.25 * np.exp(-(daz_col / 70.0) ** 2)  # dimmer away from the sun azimuth
    glow_row = np.exp(-(np.clip(el_row, 0, None) / 12.0) ** 2)
    glow_str = math.exp(-((sun_el - 2.0) / 9.0) ** 2) if sun_el > -6 else 0.15
    sky = base[:, None, :] * bright[None, :, None] + GLOW * (glow_str * np.exp(-(daz_col / 35.0) ** 2)[None, :]
                                                             * glow_row[:, None])[:, :, None]

    row_h = H / 2 + f_px * np.tan(np.radians(el0 - hel_col))  # horizon silhouette per column
    ground = rows[:, None] > row_h[None, :]
    glit = 0.12 + 0.55 * np.clip((sun_el + 6.0) / 30.0, 0.0, 1.0)
    ground_col = np.array([30.0, 32.0, 26.0]) * glit
    # Koschmieder haze: below horizontal the ray hits flat ground at cam_agl/sin(-el); above
    # horizontal the pixel shows the silhouette-forming ridge at its ray-marched distance
    below = np.radians(np.clip(-el_row[:, None], 0.03, None))
    rng_m = np.where(el_row[:, None] < 0.0, cam_agl_m / np.sin(below), dstar_col[None, :])
    contrast = np.exp(-3.912 * (np.clip(rng_m, 200.0, 30000.0) / 1000.0) / visibility_km)
    ground_img = ground_col * contrast[:, :, None] + sky * (1 - contrast[:, :, None])
    img = np.where(ground[:, :, None], ground_img, sky)
    img = np.where(ground[:, :, None], img + rng.normal(0.0, 2.0, (H, W, 1)), img)
    return np.clip(img, 0.0, 255.0)


# --- simulated detector ------------------------------------------------
def _class_guess(rng, true_class, px):
    """Classification confusion grows as the object shrinks; geese get called multirotors."""
    p_correct = 0.5 + 0.5 / (1.0 + math.exp(-(px - 8.0) / 3.0))
    if rng.random() < p_correct:
        return true_class
    if true_class == "bird":
        return "multirotor" if rng.random() < 0.7 else "fixed-wing"
    return [c for c in CLASSES if c != true_class][int(rng.integers(2))]


def _detect(rng, rows, visibility_km):
    """conf = sigmoid((pixels_on_object - 6) / 2) * contrast + N(0, 0.05); emit above 0.3."""
    dets = []
    for r in rows:
        if r["occluded"] or not r["in_frame"]:
            continue
        contrast = math.exp(-3.912 * (r["range_m"] / 1000.0) / visibility_km)
        conf = float(np.clip(1.0 / (1.0 + math.exp(-(r["pixels_on_object"] - 6.0) / 2.0))
                             * contrast + rng.normal(0.0, 0.05), 0.0, 1.0))
        if conf <= 0.3:
            continue
        x, y, w, h = r["true_bbox"]
        j = 1.0 + rng.normal(0.0, 0.10, 4)  # ~10% box jitter
        dets.append({"bbox": (x + j[0] * 0.1 * w, y + j[1] * 0.1 * h,
                              max(w * j[2], 1.0), max(h * j[3], 1.0)),
                     "class": _class_guess(rng, SHAPE_CLASS[r["shape"]], r["pixels_on_object"]),
                     "conf": conf, "row": r})
    return dets


def _font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # older Pillow
        return ImageFont.load_default()


def _burn_in(im, stamp, fov_deg, dets):
    """Recording burn-in: camera + time + FOV, green boxes with class/conf, x9 zoom inset."""
    draw = ImageDraw.Draw(im)
    font = _font(15)
    inset = None
    if dets:  # crop the zoom from the clean frame, before any overlay is drawn
        real = [d for d in dets if d["row"]]
        best = max(real or dets, key=lambda d: d["conf"])
        n_px = (round(best["row"]["pixels_on_object"]) if best["row"]
                else round(best["bbox"][2]))
        bx, by, bw, bh = best["bbox"]
        cs = int(np.clip(max(bw, bh) * 3, 6, 26))
        cx0 = int(np.clip(bx + bw / 2 - cs / 2, 0, im.width - cs))
        cy0 = int(np.clip(by + bh / 2 - cs / 2, 0, im.height - cs))
        crop = im.crop((cx0, cy0, cx0 + cs, cy0 + cs))
        inset = (crop.resize((cs * 9, cs * 9), Image.Resampling.NEAREST), n_px)
    draw.text((10, 8), f"{stamp} FOV {fov_deg:.1f}\N{DEGREE SIGN}", fill=(255, 255, 255), font=font)
    for d in dets:
        x, y, w, h = d["bbox"]
        draw.rectangle([x, y, x + w, y + h], outline=(0, 220, 0), width=2)
        draw.text((x, max(y - 14, 2)), f"{d['class']} {d['conf']:.2f}", fill=(0, 220, 0), font=font)
    if inset is not None:
        crop, n_px = inset
        im.paste(crop, (im.width - crop.width - 12, 12))
        draw.text((im.width - crop.width - 12, 16 + crop.height),
                  f"zoom x9: about {n_px} px wide", fill=(255, 255, 255), font=font)


# --- plan / run --------------------------------------------------------
def _load_fixes(ctx):
    path = ctx.out / "fused" / "fixes.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"camera needs {path} to cue on (run rf_df first, or use params.cue: truth:<object_id>)")
    return pd.read_csv(path)


def _plan(p, sensor, ctx, fixes):
    """Frame times at fps where a cue exists, capped at max_frames. rf cue: newest fix within
    5 s (airborne classes preferred); truth cue: the debug object active."""
    grid = np.arange(0.0, ctx.cfg.duration_s, 1.0 / p["fps"])
    alive = ctx.alive(sensor, grid)
    out = []
    if p["cue"] == "rf":
        all_t = fixes["t"].to_numpy()
        air = fixes[~fixes["sig_class"].isin(GROUND_CLASSES)]
        air_t = air["t"].to_numpy()
        for k, t in enumerate(grid):
            if not alive[k]:
                continue
            fix = None
            for ts, src in ((air_t, air), (all_t, fixes)):
                i = np.searchsorted(ts, t, side="right") - 1
                if i >= 0 and ts[i] >= t - 5.0:
                    fix = src.iloc[i]
                    break
            if fix is not None:
                out.append((float(t), fix))
    else:
        oid = p["cue"][len("truth:"):]
        for k, t in enumerate(grid):
            if not alive[k]:
                continue
            st = ctx.state(oid, t)
            if np.isfinite(st["x"]):
                out.append((float(t), None))
    if len(out) > p["max_frames"]:
        idx = np.unique(np.round(np.linspace(0, len(out) - 1, p["max_frames"])).astype(int))
        out = [out[i] for i in idx]
    return out


def _point(p, ctx, cam, t, fix):
    """Camera az/el: at the fix's ground height + assumed_agl_m (rf cue) or the true object."""
    if p["cue"] == "rf":
        fx, fy = ctx.world.to_xy(fix["lat"], fix["lon"])
        gh = ctx.world.height(float(fx), float(fy))
        dx, dy = float(fx) - cam[0], float(fy) - cam[1]
        el = math.degrees(math.atan2(gh + p["assumed_agl_m"] - cam[2], math.hypot(dx, dy)))
        return math.degrees(math.atan2(dx, dy)) % 360.0, el, str(fix["fix_id"])
    oid = p["cue"][len("truth:"):]
    st = ctx.state(oid, t)
    dx, dy, dz = float(st["x"]) - cam[0], float(st["y"]) - cam[1], float(st["z"]) - cam[2]
    el = math.degrees(math.atan2(dz, math.hypot(dx, dy)))
    return math.degrees(math.atan2(dx, dy)) % 360.0, el, p["cue"]


def _active(ctx, t):
    """Every truth object with a catalog span (drones, geese) active at t, with its shape."""
    out = []
    for oid, o in ctx.objects.items():
        cat = CATALOG[o.type]
        span = cat.get("span_m")
        if span is None:
            continue
        st = ctx.state(oid, t)
        if not np.isfinite(st["x"]):
            continue
        prev = ctx.state(oid, t - EXPOSURE_S)
        xyz = np.array([st["x"], st["y"], st["z"]], float)
        xyz_prev = xyz if not np.isfinite(prev["x"]) else np.array([prev["x"], prev["y"], prev["z"]], float)
        out.append({"id": oid, "shape": cat["shape"], "span_m": span,
                    "xyz": xyz, "xyz_prev": xyz_prev, "side": o.side})
    return out


def run(sensors, ctx):
    (ctx.out / "answer_key").mkdir(parents=True, exist_ok=True)
    for s in sensors:
        p = _params(s)
        cue_obj = p["cue"][len("truth:"):] if p["cue"].startswith("truth:") else None
        if cue_obj and cue_obj not in ctx.objects:
            raise ValueError(f"camera {s.id}: cue {p['cue']!r} names no object")
        rng = ctx.rng(f"camera:{s.id}")
        cam = ctx.sensor_xyz(s)
        f_px = focal_px(p["width"], p["fov_deg"])
        vis_km = ctx.cfg.weather.visibility_km
        cam_agl = cam[2] - ctx.world.height(cam[0], cam[1])
        fixes = _load_fixes(ctx) if p["cue"] == "rf" else None
        plan = _plan(p, s, ctx, fixes)
        _, hel, dstar = horizon_profile(ctx.world, cam)
        step = 360.0 / hel.size
        dots = {}
        for oid, o in ctx.objects.items():
            if CATALOG[o.type].get("shape") == "flock":
                r = ctx.rng(f"camera:{s.id}:flock:{oid}")
                n = int(r.integers(8, 21))
                step_m = 15.0 / max((n + 1) // 2, 1)
                dots[oid] = [(((-1) ** i) * ((i + 1) // 2) * step_m * r.uniform(0.85, 1.15),
                              ((i + 1) // 2) * step_m * 0.55 * r.uniform(0.85, 1.15))
                             for i in range(n)]
        folder = ctx.out / "sensors" / s.id
        (folder / "frames").mkdir(parents=True, exist_ok=True)
        frames_rows, det_rows, key_rows, frame_key_rows, media_rows = [], [], [], [], []
        n = 0
        for t, fix in plan:
            az0, el0, fix_id = _point(p, ctx, cam, t, fix)
            dt = ctx.cfg.start + timedelta(seconds=t)
            sun_el, sun_az = solar_position(dt, ctx.cfg.area.lat, ctx.cfg.area.lon)
            idx = np.clip(np.round(((az0 + np.degrees(np.arctan(
                (np.arange(p["width"]) - p["width"] / 2) / f_px))) % 360) / step).astype(int),
                0, hel.size - 1)
            img = _scene(p, sun_el, sun_az, az0, el0, f_px, hel[idx], dstar[idx], cam_agl, vis_km, rng)
            rows = frame_objects(ctx.world, cam, _active(ctx, t), az0, el0, f_px,
                                 p["width"], p["height"])
            paint_objects(img, rows, f_px, dots, vis_km)
            img = np.clip(img + rng.normal(0.0, 1.0, img.shape)
                          * (1.5 + 6.0 * (1.0 - img / 255.0)), 0.0, 255.0)  # read noise, stronger dark
            frame_id = f"{s.id}-{n:06d}"
            n += 1
            iso = ctx.iso(t)
            dets = _detect(rng, rows, vis_km)
            if rng.random() < 0.01:  # false alarm ~1% of frames
                dets.append({"bbox": (rng.uniform(0, p["width"] - 20), rng.uniform(0, p["height"] - 20),
                                      rng.uniform(4, 20), rng.uniform(4, 20)),
                             "class": CLASSES[int(rng.integers(3))],
                             "conf": float(rng.uniform(0.31, 0.9)), "row": None})
            for d in dets:
                d["record_id"] = f"{s.id}-{n:06d}"
                n += 1
            im = Image.fromarray(img.round().astype(np.uint8))
            _burn_in(im, f"{s.id} {iso[:10]} {iso[11:19]}.{iso[20:22]}Z", p["fov_deg"], dets)
            im.save(folder / "frames" / f"{frame_id}.jpg", quality=p["jpeg_quality"])
            frames_rows.append([frame_id, iso, f"{t:.3f}", f"frames/{frame_id}.jpg",
                                round(az0, 3), round(el0, 3), fix_id])
            media_rows.append([f"{t:.3f}", iso, "image", f"frames/{frame_id}.jpg"])
            for d in dets:
                x, y, w, h = d["bbox"]
                det_rows.append([d["record_id"], iso, f"{t:.3f}", frame_id,
                                 round(x, 1), round(y, 1), round(w, 1), round(h, 1),
                                 d["class"], round(d["conf"], 3)])
                r = d["row"]
                if r is None:
                    key_rows.append([d["record_id"], "", "false_alarm", "", "", ""])
                else:
                    bx, by, bw, bh = r["true_bbox"]
                    key_rows.append([d["record_id"], r["object_id"], LABEL[r["side"]],
                                     round(r["range_m"], 1), round(r["pixels_on_object"], 2),
                                     f"{bx:.1f},{by:.1f},{bw:.1f},{bh:.1f}"])
            for r in rows:
                bx, by, bw, bh = r["true_bbox"]
                frame_key_rows.append([frame_id, r["object_id"], r["in_frame"], r["occluded"],
                                       round(r["range_m"], 1), round(r["pixels_on_object"], 2),
                                       f"{bx:.1f},{by:.1f},{bw:.1f},{bh:.1f}"])
        with open(folder / "frames.csv", "w", newline="") as f:
            w = csv_writer(f, ["frame_id", "time_utc", "t", "file", "az_deg", "el_deg", "pointing_fix_id"])
            w.writerows(frames_rows)
        with open(folder / "detections.csv", "w", newline="") as f:
            w = csv_writer(f, ["record_id", "time_utc", "t", "frame_id", "x", "y", "w", "h", "class", "conf"])
            w.writerows(det_rows)
        with open(folder / "media.csv", "w", newline="") as f:
            w = csv_writer(f, ["t", "time_utc", "kind", "path"])
            w.writerows(media_rows)
        with open(ctx.out / "answer_key" / f"{s.id}.csv", "w", newline="") as f:
            w = csv_writer(f, ["record_id", "object_id", "label", "true_range_m",
                               "pixels_on_object", "true_bbox"])
            w.writerows(key_rows)
        with open(ctx.out / "answer_key" / f"{s.id}_frames.csv", "w", newline="") as f:
            w = csv_writer(f, ["frame_id", "object_id", "in_frame", "occluded", "range_m",
                               "pixels_on_object", "true_bbox"])
            w.writerows(frame_key_rows)
        print(f"{s.id}: {len(frames_rows)} frame(s), {len(det_rows)} detection(s)")


def csv_writer(f, header):
    w = csv.writer(f)
    w.writerow(header)
    return w
