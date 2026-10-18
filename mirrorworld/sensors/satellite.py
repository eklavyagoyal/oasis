"""Satellite: the real Sentinel-2 pass over this spot, and what the mission would have imaged.

The pass comes from TLEs (CelesTrak + skyfield), the ground background from a real
Sentinel-2 L2A scene (Earth Search STAC COGs), and every world object near the pass is
stamped in sub-pixel: each MSI band sees it at its own acquisition time (colour fringes
on movers), at its parallax-displaced position, with its sun-cast shadow on the ground.
Numbers and sources: docs/research/geo-data.md sections 3, 3b and 4.
"""
import json
import math
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import rasterio
from PIL import Image, ImageDraw, ImageFont
from rasterio.crs import CRS
from rasterio.transform import Affine, from_bounds
from rasterio.warp import transform as warp_transform
from rasterio.windows import Window
from skyfield.api import EarthSatellite, Loader, load_file, wgs84
from skyfield.framelib import itrs

from ..catalog import CATALOG
from ..world import CACHE_DIR, R_EARTH

NORAD = {"SENTINEL-2A": 40697, "SENTINEL-2B": 42063, "SENTINEL-2C": 60989}
DEFAULTS = dict(platform="SENTINEL-2A", chip_km=6.0, gsd_m=10.0, max_cloud_pct=5.0)
SWATH_HALF_KM = 145.0  # the MSI images a 290 km swath
MIN_SUN_EL_DEG = 5.0  # optical imaging needs the sun up
# MSI inter-band acquisition delays after B02 (ESA table, via Binet et al. 2022); a ground
# point is imaged at these offsets as the satellite moves, so movers smear between bands.
BAND_DELAY_S = {"B02": 0.0, "B08": 0.264, "B03": 0.527, "B04": 1.005}
BANDS = ["B02", "B03", "B04", "B08"]
OBJ_REFL = {"B02": 0.07, "B03": 0.08, "B04": 0.09, "B08": 0.06}  # dark grey airframe, 0.06-0.10
SHADOW_FACTOR = 0.5  # shadowed ground keeps ~50% of its reflectance
SUPER = 10  # supersampling per pixel edge for sub-pixel coverage
LABEL = {"hostile": "target", "unknown": "target", "friendly": "friendly", "neutral": "clutter"}
GDAL_ENV = dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
                GDAL_HTTP_TIMEOUT="30", GDAL_HTTP_CONNECTTIMEOUT="10", GDAL_HTTP_MAX_RETRY="3",
                GDAL_HTTP_RETRY_DELAY="1", GDAL_HTTP_MERGE_CONSECUTIVE_RANGES="YES", VSI_CACHE="TRUE")
TLE_URL = "https://celestrak.org/NORAD/elements/gp.php?CATNR={}&FORMAT=TLE"
DE421_URL = "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/a_old_versions/de421.bsp"
STAC_URL = "https://earth-search.aws.element84.com/v1/search"


# --- network: timeouts + bounded retries, never silent -------------------------------------------
def _get(url, timeout=20, retries=3, stop_on_http=False):
    """GET bytes. `stop_on_http` enforces CelesTrak's policy: stop on any non-200."""
    last = ""
    for k in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if stop_on_http or e.code not in (429, 500, 502, 503, 504):
                raise RuntimeError(f"GET {url} -> HTTP {e.code} {e.reason}") from e
            last = f"HTTP {e.code}"
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last = str(e)
        time.sleep(0.5 * 2 ** k)
    raise RuntimeError(f"GET {url} failed after {retries} attempts ({last})")


def _post_json(url, payload, timeout=30, retries=3):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json", "User-Agent": "mirrorworld/0.1"})
    last = ""
    for k in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504):
                raise RuntimeError(f"POST {url} -> HTTP {e.code} {e.reason}") from e
            last = f"HTTP {e.code}"
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last = str(e)
        time.sleep(0.5 * 2 ** k)
    raise RuntimeError(f"POST {url} failed after {retries} attempts ({last})")


# --- pure physics / geometry (shared with tests) -------------------------------------------------
def band_positions(state, object_id, t_pass):
    """Per-band true ground state of the object: each band images a ground point at its own
    acquisition time, so a mover is at a different position in every band (the colour fringe)."""
    return {b: state(object_id, t_pass + BAND_DELAY_S[b]) for b in BANDS}


def parallax_offset_m(h_agl_m, sat_zenith_deg):
    """An elevated target appears where its line of sight meets the ground: h*tan(zenith)
    away from the satellite's azimuth."""
    return float(h_agl_m) * math.tan(math.radians(sat_zenith_deg))


def shadow_offset_m(h_agl_m, sun_el_deg):
    """Ground distance from the point below the target to its shadow: h/tan(sun elevation)."""
    return float(h_agl_m) / math.tan(math.radians(sun_el_deg))


def anti_sun_offset_m(h_agl_m, sun_el_deg, sun_az_deg):
    """(east, north) m of the shadow from the point below the target: away from the sun."""
    d = shadow_offset_m(h_agl_m, sun_el_deg)
    a = math.radians(sun_az_deg + 180.0)
    return d * math.sin(a), d * math.cos(a)


def parallax_ground_offset_m(h_agl_m, sat_zenith_deg, sat_az_deg):
    """(east, north) m of the apparent target position from its true ground position."""
    d = parallax_offset_m(h_agl_m, sat_zenith_deg)
    a = math.radians(sat_az_deg + 180.0)  # displaced away from the satellite
    return d * math.sin(a), d * math.cos(a)


def footprint_mask(shape, span_m, u, v):
    """Point-in-footprint in the object frame: u forward along the heading, v starboard (m)."""
    if shape == "delta":  # flying wing: full span at the tail, tapering to the nose
        length = 1.4 * span_m
        half_w = (span_m / 2.0) * np.clip((length / 2.0 - u) / length, 0.0, 1.0)
        return (np.abs(v) <= half_w) & (u >= -length / 2.0) & (u <= length / 2.0)
    if shape == "quad":
        return (np.abs(u) <= span_m / 2.0) & (np.abs(v) <= span_m / 2.0)
    if shape == "flock":  # loose scatter of birds inside a few spans
        m = np.zeros(np.broadcast(u, v).shape, dtype=bool)
        for du, dv in ((0, 0), (1.8, 0.9), (-1.6, 1.2), (2.2, -1.5), (-2.0, -1.1), (0.5, 2.4), (-0.4, -2.3)):
            b = 0.35 * span_m
            m |= (np.abs(u - du * span_m) <= b) & (np.abs(v - dv * span_m) <= b)
        return m
    raise ValueError(f"unknown footprint shape {shape!r}")


def sprite_coverage(shape, span_m, heading_deg, x_px, y_px, size_px, gsd_m):
    """Sub-pixel covered fraction per pixel for the footprint centred at fractional pixel
    coordinates (x_px, y_px) rotated to `heading_deg` true. Returns cov, (r0, r1, c0, c1)."""
    half = 2.0 * span_m / gsd_m + 1.0  # generous: covers delta length and flock spread
    r0, r1 = max(0, int(math.floor(y_px - half))), min(size_px, int(math.ceil(y_px + half)))
    c0, c1 = max(0, int(math.floor(x_px - half))), min(size_px, int(math.ceil(x_px + half)))
    if r0 >= r1 or c0 >= c1:
        return np.zeros((0, 0)), (r0, r1, c0, c1)
    j = c0 + (np.arange((c1 - c0) * SUPER) + 0.5) / SUPER  # subpixel centres, corner coords
    i = r0 + (np.arange((r1 - r0) * SUPER) + 0.5) / SUPER
    dx, dy = (j - x_px) * gsd_m, (i - y_px) * gsd_m  # metres east / south of the sprite
    th = math.radians(heading_deg)
    u = dx[None, :] * math.sin(th) - dy[:, None] * math.cos(th)  # forward
    v = dx[None, :] * math.cos(th) + dy[:, None] * math.sin(th)  # starboard
    m = footprint_mask(shape, span_m, u, v)
    cov = m.reshape(r1 - r0, SUPER, c1 - c0, SUPER).mean(axis=(1, 3))
    return cov, (r0, r1, c0, c1)


def stamp_object(band, cov, box, refl):
    """Mix the object's reflectance into the band over its covered fraction."""
    r0, r1, c0, c1 = box
    band[r0:r1, c0:c1] = band[r0:r1, c0:c1] * (1.0 - cov) + refl * cov


def stamp_shadow(band, cov, box):
    """Darken ground reflectance under the shadow over its covered fraction."""
    r0, r1, c0, c1 = box
    band[r0:r1, c0:c1] *= 1.0 - SHADOW_FACTOR * cov


# --- pass geometry (skyfield + CelesTrak) ---------------------------------------------------------
def _get_tle(norad):
    """(name, l1, l2, epoch_utc). Cached forever: CelesTrak asks for one download per update,
    and a weeks-old TLE still times passes to seconds (geo-data.md section 4)."""
    path = CACHE_DIR / f"tle_{norad}.txt"
    if not path.exists():
        path.write_bytes(_get(TLE_URL.format(norad), stop_on_http=True))
    lines = [l for l in path.read_text().splitlines() if l.strip()]
    for i in range(len(lines) - 1, 0, -1):
        if lines[i].startswith("2 ") and lines[i - 1].startswith("1 "):
            l1 = lines[i - 1]
            name = lines[i - 2].strip() if i >= 2 else f"NORAD {norad}"
            yr = int(l1[18:20])
            year = (1900 if yr >= 57 else 2000) + yr
            epoch = datetime(year, 1, 1, tzinfo=timezone.utc) + timedelta(days=float(l1[20:32]) - 1)
            return name, l1, lines[i], epoch
    raise RuntimeError(f"{path} is not a 3-line TLE")


def _ephemeris():
    """JPL DE421 for sun geometry; fetched with our timeout (skyfield's downloader has none)."""
    path = CACHE_DIR / "de421.bsp"
    if not path.exists():
        path.write_bytes(_get(DE421_URL, timeout=60))
    return load_file(str(path))


def _approaches(sat, site, ts, dt0, dt1, step_s):
    """Closest-approach (sub-point) times of the ground track to the site within [dt0, dt1]."""
    n = max(int(round((dt1 - dt0).total_seconds() / step_s)) + 1, 3)
    t = ts.linspace(ts.from_datetime(dt0), ts.from_datetime(dt1), n)
    p = sat.at(t).frame_xyz(itrs).m  # geocentric ITRS, shape (3, n)
    s = site.itrs_xyz.m
    cosg = np.clip((p * s[:, None]).sum(0) / (np.linalg.norm(p, axis=0) * np.linalg.norm(s)), -1, 1)
    d = np.arccos(cosg) * R_EARTH  # ground distance site <-> sub-point (m)
    mins = np.where((d[1:-1] < d[:-2]) & (d[1:-1] <= d[2:]))[0] + 1
    out = []
    for k in mins:
        # parabolic refinement on the coarse samples
        d0, d1, d2 = d[k - 1], d[k], d[k + 1]
        shift = 0.5 * (d0 - d2) / (d0 - 2 * d1 + d2) if d0 - 2 * d1 + d2 != 0 else 0.0
        out.append((t[k].utc_datetime() + timedelta(seconds=float(shift) * step_s), float(min(d0, d1, d2))))
    return out


def _pass_geometry(sat, eph, site, ts, dt):
    """View and sun geometry from the point at time dt (UTC)."""
    t = ts.from_datetime(dt)
    el, az, rng = (sat - site).at(t).altaz()
    sun_el, sun_az, _ = (eph["sun"] - eph["earth"] - site).at(t).altaz()  # sun as seen from the point
    return dict(time_utc=dt, elev_deg=float(el.degrees), az_deg=float(az.degrees),
                zenith_deg=90.0 - float(el.degrees), range_km=float(rng.km),
                sun_el_deg=float(sun_el.degrees), sun_az_deg=float(sun_az.degrees))


# --- background: real Sentinel-2 L2A from Earth Search -------------------------------------------
def _find_scene(lat, lon, max_cloud_pct):
    """Best real L2A scene over the point: MGRS 36UUV preferred (35UQQ clips the east edge),
    then the capture's season (Oct-Nov), then lowest cloud. Background is from another day."""
    payload = {
        "collections": ["sentinel-2-l2a"],
        "intersects": {"type": "Point", "coordinates": [lon, lat]},
        "datetime": "2015-06-01T00:00:00Z/" + datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "query": {"eo:cloud_cover": {"lt": max_cloud_pct}},
        "sortby": [{"field": "properties.eo:cloud_cover", "direction": "asc"}],
        "limit": 200,
    }
    feats = _post_json(STAC_URL, payload).get("features", [])
    if not feats:
        raise RuntimeError(f"no Sentinel-2 L2A scene with cloud < {max_cloud_pct}% over ({lat}, {lon}); "
                           f"raise params.max_cloud_pct or check the STAC service")

    def rank(f):
        p = f["properties"]
        return (p.get("grid:code") != "MGRS-36UUV", int(p["datetime"][5:7]) not in (10, 11),
                p["eo:cloud_cover"], p["datetime"])

    return min(feats, key=rank)


def _chip_calibration(dns, scales, offsets):
    """Reflectance offsets for a whole chip. The pre-C1 COG line (collection sentinel-2-l2a)
    ships the baseline >= 04.00 BOA offset as boilerplate but stores absolute DNs (its C1
    twin is exactly +1000 DN), so an offset that would drive any band's median below zero is
    not this scene's calibration and is dropped for all bands alike."""
    if any(float(np.median(dns[b] * scales[b] + offsets[b])) < 0 for b in dns):
        return {b: 0.0 for b in dns}
    return dict(offsets)


def _band_asset(item, band):
    """COG href + reflectance scale/offset (baseline >= 04.00 BOA offset; don't hard-code)."""
    for a in item["assets"].values():
        href = a.get("href", "")
        if href.endswith(f"/{band}.tif"):
            rb = (a.get("raster:bands") or [{}])[0]
            return href, float(rb.get("scale", 1e-4)), float(rb.get("offset", 0.0))
    raise RuntimeError(f"scene {item['id']} has no {band} COG asset")


def _read_chip(item, lat, lon, chip_km, gsd_m):
    """B02/B03/B04/B08 reflectance of a chip_km square at gsd_m in the scene CRS. Cached."""
    cache = CACHE_DIR / f"s2_{item['id']}_chip.npz"
    if cache.exists():
        z = np.load(cache)
        dns = {b: z[f"dn_{b}"].astype(np.float64) for b in BANDS}
        scales = {b: float(z[f"scale_{b}"]) for b in BANDS}
        offsets = {b: float(z[f"offset_{b}"]) for b in BANDS}
        used = _chip_calibration(dns, scales, offsets)
        bands = {b: dns[b] * scales[b] + used[b] for b in BANDS}
        return bands, Affine(*z["transform"]), str(z["crs"]), {b: {"scale": scales[b], "offset_used": used[b]} for b in BANDS}
    url0, _, _ = _band_asset(item, "B02")
    with rasterio.Env(**GDAL_ENV), rasterio.open(f"/vsicurl/{url0}") as ds0:
        crs, tr = ds0.crs, ds0.transform
        x0, y0 = warp_transform("EPSG:4326", crs, [lon], [lat])
        col_f, row_f = (~tr) * (x0[0], y0[0])  # fractional pixel coords of the point
        n_nat = max(int(round(chip_km * 1000 / abs(tr.a))), 2)  # window at the native 10 m grid
        win = Window(int(round(col_f - n_nat / 2)), int(round(row_f - n_nat / 2)), n_nat, n_nat)
        if win.col_off < 0 or win.row_off < 0 or win.col_off + n_nat > ds0.width or win.row_off + n_nat > ds0.height:
            raise RuntimeError(f"chip window clipped at MGRS tile edge of {item['id']} - pick another grid:code")
        w, s, e, n = rasterio.windows.bounds(win, tr)
        dns, scales, offsets = {}, {}, {}
        for b in BANDS:
            href, scale, offset = _band_asset(item, b)
            with rasterio.Env(**GDAL_ENV), rasterio.open(f"/vsicurl/{href}") as ds:
                if ds.crs != crs or ds.transform != tr:
                    raise RuntimeError(f"{item['id']} {b} is not on the same grid as B02")
                dn = ds.read(1, window=win).astype(np.float64)
            out_n = max(int(round(chip_km * 1000 / gsd_m)), 2)
            if dn.shape != (out_n, out_n):  # only when gsd_m != the native 10 m: nearest resample
                rr = np.arange(out_n) * dn.shape[0] // out_n
                cc = np.arange(out_n) * dn.shape[1] // out_n
                dn = dn[rr[:, None], cc[None, :]]
            dns[b], scales[b], offsets[b] = dn, scale, offset
        used = _chip_calibration(dns, scales, offsets)
        bands = {b: dns[b] * scales[b] + used[b] for b in BANDS}
        transform = from_bounds(w, s, e, n, bands["B02"].shape[1], bands["B02"].shape[0])
        np.savez_compressed(cache, transform=np.array(tuple(transform)), crs=str(crs),
                            **{f"dn_{b}": dns[b].round().astype(np.uint16) for b in BANDS},
                            **{f"scale_{b}": scales[b] for b in BANDS}, **{f"offset_{b}": offsets[b] for b in BANDS})
    return bands, Affine(*transform), str(crs), {b: {"scale": scales[b], "offset_used": used[b]} for b in BANDS}


# --- rendering outputs ---------------------------------------------------------------------------
def _stretch(bands):
    """(3, h, w) uint8 from reflectance with a 2-98% per-channel stretch."""
    out = np.empty((3,) + bands["B02"].shape, dtype=np.uint8)
    for k, b in enumerate(("B04", "B03", "B02")):  # true colour
        lo, hi = np.percentile(bands[b], [2, 98])
        out[k] = np.clip((bands[b] - lo) / max(hi - lo, 1e-6), 0, 1) * 255
    return out


def _font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # older Pillow
        return ImageFont.load_default()


def _burn_in(img, text):
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([0, 0, img.width, 22], fill=(0, 0, 0, 160))
    d.text((8, 5), text, fill=(255, 255, 255, 255), font=_font(14))


def _write_png(rgb, path, label):
    img = Image.fromarray(np.transpose(rgb, (1, 2, 0)))
    _burn_in(img, label)
    img.save(path)


# --- the capture ---------------------------------------------------------------------------------
def _capture(sensor, ctx, p, folder):
    platform = str(p["platform"]).upper()
    if platform not in NORAD:
        raise ValueError(f"{sensor.id}: platform {p['platform']!r} not in {sorted(NORAD)}")
    site_xyz = ctx.sensor_xyz(sensor)
    lat0, lon0 = (float(v) for v in ctx.world.to_ll(site_xyz[0], site_xyz[1]))
    ground_m = float(ctx.world.height(site_xyz[0], site_xyz[1]))

    # 1. PASS: TLE + skyfield, closest approach inside the swath with the sun up
    name, l1, l2, tle_epoch = _get_tle(NORAD[platform])
    ts = Loader(str(CACHE_DIR)).timescale()
    sat = EarthSatellite(l1, l2, name, ts)
    site = wgs84.latlon(lat0, lon0, elevation_m=ground_m)  # DEM datum (geoid ~25 m: <0.005 deg at 790 km)
    t0 = ctx.cfg.start.replace(tzinfo=timezone.utc)
    t1 = t0 + timedelta(seconds=ctx.cfg.duration_s)
    approaches = _approaches(sat, site, ts, t0, t1, 1.0)
    eph = _ephemeris()
    cands = []
    for dt, d_m in approaches:
        g = _pass_geometry(sat, eph, site, ts, dt)
        g["cross_track_km"] = d_m / 1000.0
        g["in_swath"] = d_m / 1000.0 < SWATH_HALF_KM
        g["sun_ok"] = g["sun_el_deg"] > MIN_SUN_EL_DEG
        g["t_s"] = (dt - t0).total_seconds()
        cands.append(g)
    qualifying = [g for g in cands if g["in_swath"] and g["sun_ok"]]
    status = {
        "sensor_id": sensor.id, "platform": platform, "norad_id": NORAD[platform],
        "tle": {"file": f"cache/tle_{NORAD[platform]}.txt",
                "epoch_utc": f"{tle_epoch:%Y-%m-%dT%H:%M:%SZ}", "source": "CelesTrak"},
        "window_utc": [ctx.iso(0), ctx.iso(ctx.cfg.duration_s)],
        "passes_in_window": [{k: g[k] for k in ("time_utc", "cross_track_km", "elev_deg", "zenith_deg",
                                                "sun_el_deg", "in_swath", "sun_ok", "t_s")} for g in cands],
        "chip_km": p["chip_km"], "gsd_m": p["gsd_m"], "max_cloud_pct": p["max_cloud_pct"],
        "band_delay_s": BAND_DELAY_S, "object_reflectance": OBJ_REFL, "shadow_factor": SHADOW_FACTOR,
    }
    for g in status["passes_in_window"]:
        g["time_utc"] = f"{g['time_utc']:%Y-%m-%dT%H:%M:%S.%f}"[:-3] + "Z"
        for k in ("cross_track_km", "elev_deg", "zenith_deg", "sun_el_deg", "t_s"):
            g[k] = round(g[k], 3)
    if not qualifying:
        # honest no-capture: nearest passes (extend a little past the window), nothing else
        near = _approaches(sat, site, ts, t0 - timedelta(days=2), t1 + timedelta(days=2), 10.0)
        status["pass"] = None
        status["nearest_passes"] = [{"time_utc": f"{dt:%Y-%m-%dT%H:%M:%SZ}", "cross_track_km": round(d / 1000.0, 1)}
                                    for dt, d in near]
        (folder / "status.json").write_text(json.dumps(status, indent=1))
        print(f"{sensor.id}: no pass in window, status.json lists {len(near)} nearest pass(es)")
        return
    geo = min(qualifying, key=lambda g: g["cross_track_km"])  # best look at the point
    geo["time_utc"] = geo["time_utc"].replace(tzinfo=timezone.utc)
    t_pass = geo["t_s"]
    status["pass"] = {k: geo[k] for k in ("t_s", "cross_track_km", "elev_deg", "zenith_deg", "az_deg",
                                          "range_km", "sun_el_deg", "sun_az_deg")}
    status["pass"]["time_utc"] = ctx.iso(t_pass)
    for k in status["pass"]:
        if isinstance(status["pass"][k], float):
            status["pass"][k] = round(status["pass"][k], 3)

    if not ctx.alive(sensor, t_pass):
        status["note"] = f"{sensor.id} was destroyed before its pass; nothing recorded"
        (folder / "status.json").write_text(json.dumps(status, indent=1))
        print(f"{sensor.id}: {status['note']}")
        return

    # 2. BACKGROUND: a real L2A scene (a different day - recorded in status.json)
    item = _find_scene(lat0, lon0, p["max_cloud_pct"])
    props = item["properties"]
    bands, transform, crs_str, calibration = _read_chip(item, lat0, lon0, p["chip_km"], p["gsd_m"])
    size_px = bands["B02"].shape[0]
    crs = CRS.from_string(crs_str)
    status["background"] = {
        "scene_id": item["id"], "datetime_utc": props["datetime"], "cloud_pct": props["eo:cloud_cover"],
        "mgrs_tile": props.get("grid:code"), "sun_elev_deg": props.get("view:sun_elevation"),
        "cache": f"s2_{item['id']}_chip.npz", "reflectance_calibration": calibration,
        "note": "real Copernicus Sentinel-2 L2A scene from a different day than the pass; "
                "only the inserted objects come from the world truth",
    }

    # 3. INSERT MOVERS: sub-pixel footprints at each band's own acquisition time + shadows
    cx_utm, cy_utm = warp_transform("EPSG:4326", crs, [lon0], [lat0])
    half_chip_m = p["chip_km"] * 500.0
    inv = ~transform
    rows, skipped = [], {}
    for obj in ctx.cfg.objects:
        cat = CATALOG[obj.type]
        st0 = ctx.state(obj.id, t_pass)
        if not np.isfinite(st0["x"]):
            continue  # not active at the pass
        o_lat, o_lon = (float(v) for v in ctx.world.to_ll(st0["x"], st0["y"]))
        e, n = warp_transform("EPSG:4326", crs, [o_lon], [o_lat])
        inside = abs(e[0] - cx_utm[0]) < half_chip_m and abs(n[0] - cy_utm[0]) < half_chip_m
        shape, span = cat.get("shape"), cat.get("span_m")
        if not inside:
            skipped["outside the chip"] = skipped.get("outside the chip", 0) + 1
            continue
        if not shape or not span:
            skipped["no catalog footprint (span_m/shape)"] = skipped.get("no catalog footprint (span_m/shape)", 0) + 1
            continue
        rec = {"record_id": f"{sensor.id}-{len(rows) + 1:06d}", "object_id": obj.id, "link": "",
               "label": LABEL.get(obj.side, "target"),
               "true_lat": round(o_lat, 6), "true_lon": round(o_lon, 6),
               "true_alt_msl_m": round(float(st0["z"]), 1),
               "true_alt_agl_m": round(float(st0["z"] - ctx.world.height(st0["x"], st0["y"])), 1)}
        per_band = band_positions(ctx.state, obj.id, t_pass)
        for b in BANDS:
            st = per_band[b]
            h_agl = float(st["z"] - ctx.world.height(st["x"], st["y"]))
            heading = math.degrees(math.atan2(float(st["vx"]), float(st["vy"]))) % 360.0
            lat, lon = ctx.world.to_ll(st["x"], st["y"])
            ux, uy = warp_transform("EPSG:4326", crs, [float(lon)], [float(lat)])
            px, py = parallax_ground_offset_m(h_agl, geo["zenith_deg"], geo["az_deg"])
            x_px, y_px = inv * (ux[0] + px, uy[0] + py)
            cov, box = sprite_coverage(shape, span, heading, x_px, y_px, size_px, p["gsd_m"])
            if cov.size:
                stamp_object(bands[b], cov, box, OBJ_REFL[b])
            rec[f"{b.lower()}_row"], rec[f"{b.lower()}_col"] = int(math.floor(y_px)), int(math.floor(x_px))
            # shadow on the ground at the same band time, thrown along the anti-sun azimuth
            sx, sy = anti_sun_offset_m(h_agl, geo["sun_el_deg"], geo["sun_az_deg"])
            sh_x, sh_y = inv * (ux[0] + sx, uy[0] + sy)
            scov, sbox = sprite_coverage(shape, span, heading, sh_x, sh_y, size_px, p["gsd_m"])
            if scov.size:
                stamp_shadow(bands[b], scov, sbox)
            if b == "B02":
                rec["shadow_row"], rec["shadow_col"] = int(math.floor(sh_y)), int(math.floor(sh_x))
                rec["covered_px_frac"] = round(float(cov.sum()), 5)  # object area / pixel area
        rows.append(rec)
    # status stays blind to truth ids (answer_key/SAT1.csv carries the linkage)
    status["inserted_count"] = len(rows)
    status["skipped"] = [{"reason": r, "count": n} for r, n in sorted(skipped.items())]

    # 4. OUTPUTS
    stamp = f"{geo['time_utc']:%Y-%m-%dT%H-%M-%SZ}"
    tif, png = folder / f"s2_{stamp}.tif", folder / f"s2_{stamp}.png"
    with rasterio.Env(**GDAL_ENV), rasterio.open(
            tif, "w", driver="GTiff", height=size_px, width=size_px, count=4, dtype="uint16",
            crs=crs, transform=transform, compress="deflate") as ds:
        for k, b in enumerate(BANDS):
            ds.write(np.clip(bands[b] * 10000, 0, 65535).astype(np.uint16), k + 1)
            ds.set_band_description(k + 1, b)
    rgb = _stretch(bands)
    burn = f"{platform.title()} · {ctx.iso(t_pass)[:19].replace('T', ' ')}Z · {p['gsd_m']:.0f} m"
    _write_png(rgb, png, burn)

    zoom = folder / f"s2_{stamp}_zoom.png"
    if rows:
        zr = np.mean([r[f"{b.lower()}_row"] for r in rows for b in ("B02", "B03", "B04", "B08")])
        zc = np.mean([r[f"{b.lower()}_col"] for r in rows for b in ("B02", "B03", "B04", "B08")])
        r0 = min(max(int(round(zr)) - 32, 0), size_px - 64)
        c0 = min(max(int(round(zc)) - 32, 0), size_px - 64)
        # presentation zoom: stretch over the crop only, so the sub-pixel target's few-DN
        # signature and its per-band fringe positions become visible (real values, relabelled)
        crop = np.repeat(np.repeat(_stretch({b: bands[b][r0:r0 + 64, c0:c0 + 64] for b in BANDS}),
                                   8, axis=1), 8, axis=2)
        img = Image.fromarray(np.transpose(crop, (1, 2, 0)))
        d = ImageDraw.Draw(img)
        ccx, ccy = (int(round(zc)) - c0 + 0.5) * 8, (int(round(zr)) - r0 + 0.5) * 8
        d.ellipse([ccx - 80, ccy - 80, ccx + 80, ccy + 80], outline=(255, 220, 0, 255), width=4)
        # per-band sprite positions as ticks: the fringe the push-broom delays produce
        for rec in rows:
            for b, col in (("B02", (60, 120, 255)), ("B08", (80, 220, 220)),
                           ("B03", (80, 220, 80)), ("B04", (255, 80, 80))):
                tx = (rec[f"{b.lower()}_col"] - c0 + 0.5) * 8
                ty = (rec[f"{b.lower()}_row"] - r0 + 0.5) * 8
                d.line([tx - 12, ty, tx + 12, ty], fill=col + (255,), width=3)
                d.line([tx, ty - 12, tx, ty + 12], fill=col + (255,), width=3)
        _burn_in(img, f"{sensor.id} 8x zoom (presentation: crop stretch; ticks = band sprite pixels)")
        lx = 8
        for b, col in (("B02", (60, 120, 255)), ("B08", (80, 220, 220)),
                       ("B03", (80, 220, 80)), ("B04", (255, 80, 80))):
            d.rectangle([lx, img.height - 20, lx + 12, img.height - 8], fill=col + (255,))
            d.text((lx + 16, img.height - 20), b, fill=(255, 255, 255, 255), font=_font(12))
            lx += 64
        img.save(zoom)

    pd.DataFrame(rows, columns=["record_id", "object_id", "link", "label", "true_lat", "true_lon",
                                "true_alt_msl_m", "true_alt_agl_m",
                                *[f"{b}_{r}" for b in ("b02", "b03", "b04", "b08") for r in ("row", "col")],
                                "shadow_row", "shadow_col", "covered_px_frac"]).to_csv(
        ctx.out / "answer_key" / f"{sensor.id}.csv", index=False)
    media = [{"t": t_pass, "time_utc": ctx.iso(t_pass), "kind": "image", "path": png.name}]
    if zoom.exists():
        media.append({"t": t_pass, "time_utc": ctx.iso(t_pass), "kind": "image", "path": zoom.name})
    media.append({"t": t_pass, "time_utc": ctx.iso(t_pass), "kind": "event", "path": "Sentinel-2A pass"})
    pd.DataFrame(media, columns=["t", "time_utc", "kind", "path"]).to_csv(folder / "media.csv", index=False)
    (folder / "status.json").write_text(json.dumps(status, indent=1, default=str))
    print(f"{sensor.id}: pass {ctx.iso(t_pass)} (cross-track {geo['cross_track_km']:.1f} km, "
          f"sun {geo['sun_el_deg']:.1f} deg), {len(rows)} object(s) inserted from {item['id']}")


def run(sensors, ctx):
    (ctx.out / "answer_key").mkdir(parents=True, exist_ok=True)
    for s in sensors:
        p = {**DEFAULTS, **s.params}
        folder = ctx.out / "sensors" / s.id
        folder.mkdir(parents=True, exist_ok=True)
        try:
            _capture(s, ctx, p, folder)
        except Exception as e:  # never fail silently: the status file carries the error too
            status_path = folder / "status.json"
            status = json.loads(status_path.read_text()) if status_path.exists() else {"sensor_id": s.id}
            status["error"] = str(e)
            status_path.write_text(json.dumps(status, indent=1, default=str))
            raise
