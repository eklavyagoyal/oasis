#!/usr/bin/env python3
"""
scenario_sim.py - one drone, two RF receivers, real physics (FSPL + Deygout
knife-edge diffraction over a DEM + fading + Doppler), synced waterfalls.

Usage:
    python scenario_sim.py --seed 7 --out scenario_001
    python scenario_sim.py --seed 8 --out scenario_002 --dem N49E037.tif   # real terrain

Everything is derived from ONE ground truth (the drone track), so every
sensor output is a view of the same reality.
"""
import argparse, json, os
from datetime import datetime, timedelta
import numpy as np

C = 299_792_458.0
R_EARTH = 6_371_000.0
K_FACTOR = 4 / 3  # effective earth radius factor

# ----------------------------------------------------------------------------
# CONFIG: this is what an LLM / user prompt would fill in
# ----------------------------------------------------------------------------
CONFIG = {
    "seed": 7,
    "t0_utc": "2026-10-18T02:00:00+00:00",
    # Local origin (placeholder in the Oskil valley area - change to your site)
    "origin": {"lat": 49.60, "lon": 37.55},
    "dem_half_size_m": 10_000,      # 20 x 20 km area
    "dem_res_m": 30,
    "dt_s": 0.5,                      # waterfall row period
    "drone": {
        # waypoints in local metres (east, north) from the origin
        "waypoints": [(-5000, 1800), (1500, 1500), (2500, 4600), (-1500, 6500),
                      (-4500, 3800), (-3000, 1200), (2000, 900),
                      (6500, 3500), (9000, 7500)],       # egress north-east towards R2
        "speed_mps": 22.0,
        "agl_m": 60.0,
        "tx_power_dbm": 30.0,         # 1 W ELRS-class control link
        "tx_gain_dbi": 2.0,
        "freq_hz": 868e6,
        "hop_channels": 8,
        "channel_bw_hz": 500e3,
        "hops_per_row": 20,
    },
    "receivers": [
        {"id": "A", "x": 0,    "y": 0,     "mast_m": 4.0, "clock_offset_s": 0.00},
        {"id": "B", "x": 7000, "y": -1500, "mast_m": 4.0, "clock_offset_s": 0.35},
    ],
    "rx": {
        "gain_dbi": 3.0,
        "noise_figure_db": 6.0,
        "ambient_noise_rise_db": 10.0,   # man-made noise near the front line
        "detect_snr_db": 6.0,
        "nbins": 512,
        "span_hz": 20e6,
        "doa_sigma0_deg": 3.0,           # bearing error floor
        "doa_outlier_prob": 0.03,        # multipath outliers
    },
    # --- radars in opposite corners of the 20x20 km square (SW and NE) ---
    "radars": [
        {"id": "R1", "x": -10000, "y": -10000, "mast_m": 50.0, "clock_offset_s": 0.00, "scan_phase_s": 0.0},
        {"id": "R2", "x":  10000, "y":  10000, "mast_m": 50.0, "clock_offset_s": -0.20, "scan_phase_s": 1.0},
    ],
    "radar": {                           # X-band surveillance radar, small-UAV class
        "freq_hz": 9.4e9,
        "peak_power_w": 2000.0,
        "gain_dbi": 33.0,
        "bandwidth_hz": 1e6,
        "noise_figure_db": 5.0,
        "losses_db": 4.0,
        "processing_gain_db": 24.0,      # pulse integration / compression
        "target_rcs_m2": 0.3,            # fixed-wing UAV (Orlan/Shahed class, nose-on to side-on)
        "scan_period_s": 2.0,            # 30 rpm
        "detect_snr_db": 13.0,
        "beamwidth_deg": 2.0,
        "range_res_m": 30.0,
        "max_range_m": 20_000.0,
        "min_radial_speed_mps": 1.5,     # MTI notch: tangential flyers hide in clutter
        "notch_penalty_db": 15.0,
        "false_alarm_per_scan": 0.25,
    },
    "background": [                      # unrelated emitters, same on both rx
        {"f_off_hz": -6.0e6, "power_dbm": -98, "bw_hz": 100e3, "duty": 1.0},
        {"f_off_hz": 5.2e6,  "power_dbm": -92, "bw_hz": 125e3, "duty": 0.15},
    ],
}


# ----------------------------------------------------------------------------
# Geometry helpers (local flat ENU is fine for a ~25 km box)
# ----------------------------------------------------------------------------
def xy_to_lonlat(x, y, o):
    return (o["lat"] + np.asarray(y) / 110_574.0,
            o["lon"] + np.asarray(x) / (111_320.0 * np.cos(np.radians(o["lat"]))))


# ----------------------------------------------------------------------------
# Terrain
# ----------------------------------------------------------------------------
class DEM:
    def __init__(self, z, x0, y0, res):
        self.z, self.x0, self.y0, self.res = z, x0, y0, res
        self.ny, self.nx = z.shape

    def sample(self, x, y):
        fx = np.clip((np.asarray(x, float) - self.x0) / self.res, 0, self.nx - 1.001)
        fy = np.clip((np.asarray(y, float) - self.y0) / self.res, 0, self.ny - 1.001)
        ix, iy = fx.astype(int), fy.astype(int)
        ax, ay = fx - ix, fy - iy
        z = self.z
        return (z[iy, ix] * (1 - ax) * (1 - ay) + z[iy, ix + 1] * ax * (1 - ay) +
                z[iy + 1, ix] * (1 - ax) * ay + z[iy + 1, ix + 1] * ax * ay)


def synthetic_dem(half, res, rng):
    xs = np.arange(-half, half + res, res)
    X, Y = np.meshgrid(xs, xs)
    z = 120 + 15 * np.sin(X / 2300 + 1) * np.cos(Y / 1900) + 8 * np.sin(X / 700 + Y / 900)
    z += 75 * np.exp(-((Y - (2600 + 0.15 * X)) / 450) ** 2)          # E-W ridge
    ramp = np.clip((Y - 1200) / 1500, 0, 1)                           # N-S ridge fades out smoothly
    z += 60 * np.exp(-((X - 4500) / 500) ** 2) * ramp ** 2
    z += rng.normal(0, 0.8, z.shape)
    return DEM(z, -half, -half, res)


def load_geotiff(path, o, half, res):
    """Resample a north-up GeoTIFF (e.g. Copernicus GLO-30) onto the local grid."""
    import rasterio  # pip install rasterio
    with rasterio.open(path) as src:
        arr = src.read(1).astype(float)
        T = src.transform
    xs = np.arange(-half, half + res, res)
    X, Y = np.meshgrid(xs, xs)
    lat, lon = xy_to_lonlat(X, Y, o)
    col = np.round((lon - T.c) / T.a).astype(int)
    row = np.round((lat - T.f) / T.e).astype(int)
    if row.min() < 0 or col.min() < 0 or row.max() >= arr.shape[0] or col.max() >= arr.shape[1]:
        raise ValueError("DEM tile does not cover the whole box; merge tiles or shrink dem_half_size_m")
    return DEM(arr[row, col], -half, -half, res)


# ----------------------------------------------------------------------------
# RF physics
# ----------------------------------------------------------------------------
def fspl_db(d_m, f_hz):
    return 20 * np.log10(max(d_m, 1.0)) + 20 * np.log10(f_hz) - 147.55


def knife_edge_db(v):
    """ITU-R P.526 single knife-edge loss."""
    return 6.9 + 20 * np.log10(np.sqrt((v - 0.1) ** 2 + 1) + v - 0.1) if v > -0.78 else 0.0


def _deygout(d, e, i0, i1, h0, h1, lam, depth):
    if i1 - i0 < 2:
        return 0.0
    k = np.arange(i0 + 1, i1)
    d1, d2 = d[k] - d[i0], d[i1] - d[k]
    los = h0 + (h1 - h0) * d1 / (d[i1] - d[i0])
    v = (e[k] - los) * np.sqrt(2 * (d1 + d2) / (lam * d1 * d2))
    j = int(np.argmax(v))
    if v[j] <= -0.78:
        return 0.0
    loss = knife_edge_db(v[j])
    if depth < 2:   # Deygout: recurse on both sides of the principal edge
        km = k[j]
        loss += _deygout(d, e, i0, km, h0, e[km], lam, depth + 1)
        loss += _deygout(d, e, km, i1, e[km], h1, lam, depth + 1)
    return loss


def terrain_loss_db(dem, p_tx, p_rx, f_hz):
    """p = (x, y, absolute_height_m). Deygout diffraction loss along the DEM profile."""
    (x1, y1, h1), (x2, y2, h2) = p_tx, p_rx
    D = float(np.hypot(x2 - x1, y2 - y1))
    n = max(int(D / 30) + 1, 16)
    d = np.linspace(0, D, n)
    xs, ys = np.linspace(x1, x2, n), np.linspace(y1, y2, n)
    e = dem.sample(xs, ys) + d * (D - d) / (2 * R_EARTH * K_FACTOR)   # terrain + earth bulge
    return min(_deygout(d, e, 0, n - 1, h1, h2, C / f_hz, 0), 70.0)


# ----------------------------------------------------------------------------
# Truth track
# ----------------------------------------------------------------------------
def build_track(wps, speed, agl, dem, dt):
    wps = np.array(wps, float)
    s = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(wps, axis=0).T))])
    t = np.arange(0, s[-1] / speed, dt)
    x, y = np.interp(t * speed, s, wps[:, 0]), np.interp(t * speed, s, wps[:, 1])
    alt = dem.sample(x, y) + agl
    return dict(t=t, x=x, y=y, alt=alt,
                vx=np.gradient(x, dt), vy=np.gradient(y, dt), vz=np.gradient(alt, dt))


# ----------------------------------------------------------------------------
# Main simulation
# ----------------------------------------------------------------------------
def simulate(cfg, out, dem_path=None):
    rng = np.random.default_rng(cfg["seed"])
    o, dr, rxc = cfg["origin"], cfg["drone"], cfg["rx"]
    t0 = datetime.fromisoformat(cfg["t0_utc"])
    iso = lambda s: (t0 + timedelta(seconds=float(s))).isoformat(timespec="milliseconds")

    dem = (load_geotiff(dem_path, o, cfg["dem_half_size_m"], cfg["dem_res_m"]) if dem_path
           else synthetic_dem(cfg["dem_half_size_m"], cfg["dem_res_m"], rng))
    trk = build_track(dr["waypoints"], dr["speed_mps"], dr["agl_m"], dem, cfg["dt_s"])
    n_rows, dt, f0 = len(trk["t"]), cfg["dt_s"], dr["freq_hz"]

    nb, span = rxc["nbins"], rxc["span_hz"]
    bin_bw = span / nb
    nf = rxc["noise_figure_db"] + rxc["ambient_noise_rise_db"]
    n_bin_dbm = -174 + 10 * np.log10(bin_bw) + nf
    n_ch_dbm = -174 + 10 * np.log10(dr["channel_bw_hz"]) + nf
    freqs = f0 + (np.arange(nb) - nb / 2 + 0.5) * bin_bw
    hop_f = f0 + (np.arange(dr["hop_channels"]) - (dr["hop_channels"] - 1) / 2) * (span * 0.8 / dr["hop_channels"])

    os.makedirs(f"{out}/rf", exist_ok=True)
    os.makedirs(f"{out}/truth", exist_ok=True)

    # ---- truth files
    lat, lon = xy_to_lonlat(trk["x"], trk["y"], o)
    with open(f"{out}/truth/drone_track.csv", "w") as f:
        f.write("t_utc,x_m,y_m,lat,lon,alt_asl_m,speed_mps\n")
        for i in range(n_rows):
            sp = np.sqrt(trk["vx"][i] ** 2 + trk["vy"][i] ** 2 + trk["vz"][i] ** 2)
            f.write(f"{iso(trk['t'][i])},{trk['x'][i]:.1f},{trk['y'][i]:.1f},{lat[i]:.6f},"
                    f"{lon[i]:.6f},{trk['alt'][i]:.1f},{sp:.2f}\n")

    events = [{"t_utc": iso(0), "event": "drone_first_emission"}]
    results = {}

    for rx in cfg["receivers"]:
        rid = rx["id"]
        rz = dem.sample(rx["x"], rx["y"]) + rx["mast_m"]
        wf = np.zeros((n_rows, nb), np.float32)
        link_rows, doa_rows = [], []
        shadow, prev_state = 0.0, None

        for i in range(n_rows):
            t = trk["t"][i]
            dx, dy, dz = trk["x"][i] - rx["x"], trk["y"][i] - rx["y"], trk["alt"][i] - rz
            d2d, d3d = np.hypot(dx, dy), np.sqrt(dx * dx + dy * dy + dz * dz)
            bearing = np.degrees(np.arctan2(dx, dy)) % 360
            rate = (dx * trk["vx"][i] + dy * trk["vy"][i] + dz * trk["vz"][i]) / d3d
            f_dopp = -rate / C * f0

            tl = terrain_loss_db(dem, (trk["x"][i], trk["y"][i], trk["alt"][i]),
                                 (rx["x"], rx["y"], rz), f0)
            los = tl < 3.0
            state = "LOS" if los else "BLOCKED"
            if prev_state and state != prev_state:
                events.append({"t_utc": iso(t), "receiver": rid,
                               "event": f"link_{'restored' if los else 'masked_by_terrain'}",
                               "terrain_loss_db": round(tl, 1)})
            prev_state = state

            # slow shadowing (AR(1)); bigger when diffracted
            shadow = 0.95 * shadow + np.sqrt(1 - 0.95 ** 2) * rng.normal()
            shadow_db = shadow * (2.0 if los else 5.0)
            pr_mean = (dr["tx_power_dbm"] + dr["tx_gain_dbi"] + rxc["gain_dbi"]
                       - fspl_db(d3d, f0) - tl + shadow_db)
            snr = pr_mean - n_ch_dbm

            # ---- waterfall row
            row = 10 ** (n_bin_dbm / 10) * rng.gamma(4, 1 / 4, nb)   # averaged noise
            for bg in cfg["background"]:
                if (t % 20) < 20 * bg["duty"]:
                    m = np.abs(freqs - (f0 + bg["f_off_hz"])) < bg["bw_hz"] / 2
                    row[m] += 10 ** (bg["power_dbm"] / 10) / max(m.sum(), 1) * rng.gamma(4, 1 / 4, m.sum())
            counts = rng.multinomial(dr["hops_per_row"], np.ones(dr["hop_channels"]) / dr["hop_channels"])
            K = 10.0 if los else 0.0   # Rician K (linear) vs Rayleigh
            for ch, c in enumerate(counts):
                if c == 0:
                    continue
                h = (np.sqrt(K / (K + 1)) + np.sqrt(1 / (K + 1)) * (rng.normal() + 1j * rng.normal()) / np.sqrt(2))
                fade_db = 20 * np.log10(max(abs(h), 0.03))
                p_mw = 10 ** ((pr_mean + fade_db) / 10) * c / dr["hops_per_row"]
                m = np.abs(freqs - (hop_f[ch] + f_dopp)) < dr["channel_bw_hz"] / 2
                row[m] += p_mw / max(m.sum(), 1)
            wf[i] = 10 * np.log10(row)

            # ---- direction finding
            det = snr > rxc["detect_snr_db"]
            if det:
                sigma = rxc["doa_sigma0_deg"] + 25 * 10 ** (-snr / 20)
                meas = bearing + rng.normal(0, sigma)
                outlier = rng.random() < rxc["doa_outlier_prob"]
                if outlier:
                    meas += rng.choice([-1, 1]) * rng.uniform(30, 90)
                doa_rows.append((t, meas % 360, snr, sigma, outlier))
            link_rows.append((t, d3d, bearing, tl, state, pr_mean, snr, f_dopp, det))

        # ---- save per-receiver data (timestamps in the RECEIVER's own clock)
        off = rx["clock_offset_s"]
        np.save(f"{out}/rf/receiver_{rid}.waterfall.npy", wf)
        rlat, rlon = xy_to_lonlat(rx["x"], rx["y"], o)
        meta = {"receiver": rid, "lat": float(rlat), "lon": float(rlon),
                "x_m": rx["x"], "y_m": rx["y"], "mast_m": rx["mast_m"],
                "center_freq_hz": f0, "span_hz": span, "nbins": nb, "bin_bw_hz": bin_bw,
                "units": "dBm per bin (power spectral row, 4 averages)",
                "rx_clock_t0_utc": iso(off), "dt_s": dt, "n_rows": n_rows,
                "clock_offset_s": off,
                "note": "row i timestamp (receiver clock) = rx_clock_t0_utc + i*dt_s; "
                        "true UTC = receiver clock - clock_offset_s",
                "noise_floor_dbm_per_bin": float(n_bin_dbm)}
        json.dump(meta, open(f"{out}/rf/receiver_{rid}.meta.json", "w"), indent=2)
        with open(f"{out}/rf/receiver_{rid}.doa.csv", "w") as f:
            f.write("t_rx_utc,bearing_deg,snr_db\n")
            for t, b, s, _, _ in doa_rows:
                f.write(f"{iso(t + off)},{b:.1f},{s:.1f}\n")
        with open(f"{out}/truth/link_{rid}.csv", "w") as f:
            f.write("t_true_utc,range_m,true_bearing_deg,terrain_loss_db,state,rx_power_dbm,snr_db,doppler_hz,detected\n")
            for r in link_rows:
                f.write(f"{iso(r[0])},{r[1]:.0f},{r[2]:.2f},{r[3]:.1f},{r[4]},{r[5]:.1f},{r[6]:.1f},{r[7]:.1f},{int(r[8])}\n")
        results[rid] = dict(wf=wf, links=link_rows, doa=doa_rows, off=off, meta=meta)

    radar_res = simulate_radars(cfg, dem, trk, out, iso, events)
    events.append({"t_utc": iso(trk["t"][-1]), "event": "drone_last_emission"})
    events.sort(key=lambda e: e["t_utc"])
    json.dump({"config": cfg, "dem": "geotiff:" + dem_path if dem_path else "synthetic",
               "events": events}, open(f"{out}/truth/truth.json", "w"), indent=2, default=str)

    self_check(results, cfg)
    plot(out, dem, trk, cfg, results, n_bin_dbm, n_ch_dbm, freqs)
    plot_snr(out, cfg, results)
    plot_trajectory(out, dem, trk, cfg)
    if radar_res:
        self_check_radar(radar_res, trk, cfg)
        plot_radar(out, dem, trk, cfg, radar_res)
    return results


# ----------------------------------------------------------------------------
# Radar model
# ----------------------------------------------------------------------------
K_BOLTZ = 1.380649e-23


def radar_snr_db(rc, R, tl_oneway_db):
    """Monostatic radar equation. Terrain loss is applied twice (out and back)."""
    lam = C / rc["freq_hz"]
    G = 10 ** (rc["gain_dbi"] / 10)
    num = rc["peak_power_w"] * G * G * lam ** 2 * rc["target_rcs_m2"]
    den = ((4 * np.pi) ** 3 * R ** 4 * K_BOLTZ * 290 * rc["bandwidth_hz"]
           * 10 ** ((rc["noise_figure_db"] + rc["losses_db"]) / 10))
    return 10 * np.log10(num / den) + rc["processing_gain_db"] - 2 * tl_oneway_db


def simulate_radars(cfg, dem, trk, out, iso, events):
    rc, radars = cfg.get("radar"), cfg.get("radars")
    if not rc or not radars:
        return None
    rng = np.random.default_rng(cfg["seed"] + 1)       # separate stream: RF data stays unchanged
    os.makedirs(f"{out}/radar", exist_ok=True)
    t_end = trk["t"][-1]
    res = {"radars": {}, "all_plots": []}

    for rd in radars:
        rid, off = rd["id"], rd["clock_offset_s"]
        rz = dem.sample(rd["x"], rd["y"]) + rd["mast_m"]
        scans, plots, state = [], [], "LOS"
        for tk in np.arange(rd["scan_phase_s"], t_end, rc["scan_period_s"]):
            x, y, alt, vx, vy, vz = [float(np.interp(tk, trk["t"], trk[k]))
                                     for k in ("x", "y", "alt", "vx", "vy", "vz")]
            dx, dy, dz = x - rd["x"], y - rd["y"], alt - rz
            R = float(np.sqrt(dx * dx + dy * dy + dz * dz))
            az = float(np.degrees(np.arctan2(dx, dy)) % 360)
            vr = (dx * vx + dy * vy + dz * vz) / R                     # + = flying away
            tl = terrain_loss_db(dem, (x, y, alt), (rd["x"], rd["y"], rz), rc["freq_hz"])
            new_state = "BLOCKED" if tl > 6 else ("LOS" if tl < 3 else state)   # hysteresis
            if new_state != state:
                events.append({"t_utc": iso(tk), "receiver": rid,
                               "event": "radar_masked_by_terrain" if new_state == "BLOCKED" else "radar_line_of_sight_restored",
                               "terrain_loss_db": round(tl, 1)})
            state = new_state
            snr_mean = radar_snr_db(rc, R, tl)
            notch = abs(vr) < rc["min_radial_speed_mps"]
            if notch:
                snr_mean -= rc["notch_penalty_db"]
            snr_obs = snr_mean + 10 * np.log10(rng.exponential(1.0))    # Swerling I RCS fluctuation
            det = bool(snr_obs > rc["detect_snr_db"] and R < rc["max_range_m"])
            scans.append(dict(t=tk, R=R, az=az, tl=tl, snr_mean=snr_mean, snr_obs=snr_obs,
                              notch=notch, det=det, vr=vr, state=state))
            if det:
                sl = 10 ** (snr_obs / 10)
                sr = max(3.0, rc["range_res_m"] / np.sqrt(2 * sl))
                sa = max(0.05, rc["beamwidth_deg"] / np.sqrt(2 * sl))
                plots.append(dict(t=tk, r=R + rng.normal(0, sr), az=(az + rng.normal(0, sa)) % 360,
                                  snr=snr_obs, vr=vr + rng.normal(0, 0.4), sr=sr, sa=sa,
                                  target=True, tr=R, taz=az))
            for _ in range(rng.poisson(rc["false_alarm_per_scan"])):   # clutter / false alarms
                plots.append(dict(t=tk, r=rng.uniform(500, rc["max_range_m"]), az=rng.uniform(0, 360),
                                  snr=rc["detect_snr_db"] + rng.exponential(1.5), vr=rng.uniform(-25, 25),
                                  sr=rc["range_res_m"] / 2, sa=rc["beamwidth_deg"] / 2, target=False,
                                  tr=np.nan, taz=np.nan))
        plots.sort(key=lambda p: p["t"])

        # ---- files (plots stamped in the radar's own clock; truth in true UTC)
        with open(f"{out}/radar/radar_{rid}.plots.csv", "w") as f:
            f.write("t_radar_utc,range_m,azimuth_deg,snr_db,radial_velocity_mps\n")
            for p in plots:
                f.write(f"{iso(p['t'] + off)},{p['r']:.1f},{p['az']:.3f},{p['snr']:.1f},{p['vr']:.2f}\n")
        with open(f"{out}/truth/radar_{rid}_plot_labels.csv", "w") as f:
            f.write("t_true_utc,is_target,true_range_m,true_azimuth_deg\n")
            for p in plots:
                f.write(f"{iso(p['t'])},{int(p['target'])},{p['tr']:.1f},{p['taz']:.3f}\n")
        with open(f"{out}/truth/radar_{rid}_scans.csv", "w") as f:
            f.write("t_true_utc,range_m,true_azimuth_deg,terrain_loss_oneway_db,state,mean_snr_db,in_doppler_notch,detected\n")
            for sc in scans:
                f.write(f"{iso(sc['t'])},{sc['R']:.0f},{sc['az']:.2f},{sc['tl']:.1f},{sc['state']},"
                        f"{sc['snr_mean']:.1f},{int(sc['notch'])},{int(sc['det'])}\n")
        rlat, rlon = xy_to_lonlat(rd["x"], rd["y"], cfg["origin"])
        json.dump({"radar": rid, "lat": float(rlat), "lon": float(rlon), "x_m": rd["x"], "y_m": rd["y"],
                   "mast_m": rd["mast_m"], "clock_offset_s": off, "rx_clock_t0_utc": iso(rd["scan_phase_s"] + off),
                   "note": "true UTC = radar clock - clock_offset_s", **rc},
                  open(f"{out}/radar/radar_{rid}.meta.json", "w"), indent=2)
        res["radars"][rid] = dict(scans=scans, plots=plots, off=off, x=rd["x"], y=rd["y"])
        for p in plots:
            res["all_plots"].append(dict(rid=rid, ts=p["t"] + off, r=p["r"], az=p["az"], sr=p["sr"],
                                         sa=p["sa"], rx=rd["x"], ry=rd["y"], target=p["target"]))

    res["tracks"] = build_tracks(res["all_plots"])
    lat0 = cfg["origin"]
    with open(f"{out}/radar/fused_track.csv", "w") as f:
        f.write("t_utc,track_id,x_m,y_m,lat,lon\n")
        for k, tr in enumerate(res["tracks"]):
            for ts, x, y, _ in tr["pts"]:
                la, lo = xy_to_lonlat(x, y, lat0)
                f.write(f"{iso(ts)},{k},{x:.1f},{y:.1f},{float(la):.6f},{float(lo):.6f}\n")
    return res


def build_tracks(plots, sigma_a=3.0, gate=13.8, v_max=50.0, drop_s=30.0, min_updates=5):
    """Constant-velocity Kalman tracker over plots from all radars (gated, with coast + drop)."""
    plots = sorted(plots, key=lambda p: p["ts"])
    H = np.hstack([np.eye(2), np.zeros((2, 2))])

    def cart(p):
        s_, c_ = np.sin(np.radians(p["az"])), np.cos(np.radians(p["az"]))
        z = np.array([p["rx"] + p["r"] * s_, p["ry"] + p["r"] * c_])
        u, v = np.array([s_, c_]), np.array([c_, -s_])
        sr, st = 1.5 * p["sr"], 1.5 * p["r"] * np.radians(p["sa"])
        return z, sr ** 2 * np.outer(u, u) + st ** 2 * np.outer(v, v) + 1e-6 * np.eye(2)

    tracks, cur, pend = [], None, None
    for p in plots:
        z, Rm = cart(p)
        if cur is None:                                   # initiation: two consistent plots
            if pend is not None:
                dt = p["ts"] - pend["ts"]
                if dt >= 10:
                    pend = None
                elif dt < 1.5:
                    continue
                else:
                    dist = float(np.hypot(*(z - pend["z"])))
                    if dist / dt < v_max:
                        v = (z - pend["z"]) / dt
                        cur = dict(x=np.array([z[0], z[1], v[0], v[1]]),
                                   P=np.diag([150.0 ** 2, 150.0 ** 2, 20.0 ** 2, 20.0 ** 2]),
                                   t=p["ts"], n=1, pts=[(p["ts"], z[0], z[1], "init")])
                        pend = None
                        continue
            pend = dict(ts=p["ts"], z=z)
            continue
        dt = p["ts"] - cur["t"]
        if dt > drop_s:                                   # lost: close track, start over
            tracks.append(cur)
            cur, pend = None, dict(ts=p["ts"], z=z)
            continue
        F = np.eye(4); F[0, 2] = F[1, 3] = dt
        q = sigma_a ** 2
        Q = q * np.array([[dt ** 4 / 4, 0, dt ** 3 / 2, 0], [0, dt ** 4 / 4, 0, dt ** 3 / 2],
                          [dt ** 3 / 2, 0, dt ** 2, 0], [0, dt ** 3 / 2, 0, dt ** 2]])
        x, P = F @ cur["x"], F @ cur["P"] @ F.T + Q
        S = H @ P @ H.T + Rm
        innov = z - H @ x
        if innov @ np.linalg.solve(S, innov) > gate:      # outside gate: false plot, ignore
            continue
        K = P @ H.T @ np.linalg.inv(S)
        cur["x"], cur["P"], cur["t"] = x + K @ innov, (np.eye(4) - K @ H) @ P, p["ts"]
        cur["n"] += 1
        cur["pts"].append((p["ts"], cur["x"][0], cur["x"][1], "update"))
    if cur is not None:
        tracks.append(cur)
    return [t for t in tracks if t["n"] >= min_updates]


def self_check_radar(res, trk, cfg):
    print("\n=== radar self-check ===")
    for rid, r in res["radars"].items():
        S = r["scans"]
        det = np.array([s["det"] for s in S]); blk = np.array([s["state"] == "BLOCKED" for s in S])
        notch = np.array([s["notch"] for s in S])
        pr = [p for p in r["plots"] if p["target"]]
        er = np.array([p["r"] - p["tr"] for p in pr]); ea = np.array([((p["az"] - p["taz"] + 180) % 360) - 180 for p in pr])
        pd = lambda m: f"{det[m].mean() * 100:3.0f}%" if m.any() else "  - "
        print(f"[{rid}] Pd clear {pd(~blk)} | blocked {pd(blk)} | in Doppler notch {pd(notch)} | "
              f"false plots {sum(not p['target'] for p in r['plots'])} | range err RMS {np.sqrt(np.mean(er ** 2)):.1f} m, "
              f"az err RMS {np.sqrt(np.mean(ea ** 2)):.2f} deg")
    errs, covered = [], np.zeros(len(trk["t"]), bool)
    for tr in res["tracks"]:
        for ts, x, y, _ in tr["pts"]:
            errs.append(np.hypot(x - np.interp(ts, trk["t"], trk["x"]), y - np.interp(ts, trk["t"], trk["y"])))
        tt = np.array([p[0] for p in tr["pts"]])
        for i, t in enumerate(trk["t"]):
            if np.min(np.abs(tt - t)) < 6:
                covered[i] = True
    print(f"fused track: {len(res['tracks'])} track(s), covers {covered.mean() * 100:.0f}% of the flight, "
          f"position error RMS {np.sqrt(np.mean(np.square(errs))) if errs else float('nan'):.0f} m")


def plot_radar(out, dem, trk, cfg, res):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.gridspec import GridSpec
    h = cfg["dem_half_size_m"]
    cols = {"R1": "tab:blue", "R2": "tab:orange"}
    fig = plt.figure(figsize=(16, 8.5))
    gs = GridSpec(2, 2, width_ratios=[1.1, 1])

    ax = fig.add_subplot(gs[:, 0])
    ax.imshow(dem.z, origin="lower", extent=[-h, h, -h, h], cmap="Greys", alpha=0.35)
    ax.plot(trk["x"], trk["y"], color="k", lw=1.0, label="truth")
    for rid, r in res["radars"].items():
        tp = [p for p in r["plots"] if p["target"]]
        fp = [p for p in r["plots"] if not p["target"]]
        c = cols.get(rid, "tab:green")
        ax.scatter([r["x"] + p["r"] * np.sin(np.radians(p["az"])) for p in tp],
                   [r["y"] + p["r"] * np.cos(np.radians(p["az"])) for p in tp],
                   s=7, color=c, alpha=0.6, label=f"{rid} target plots")
        ax.scatter([r["x"] + p["r"] * np.sin(np.radians(p["az"])) for p in fp],
                   [r["y"] + p["r"] * np.cos(np.radians(p["az"])) for p in fp],
                   s=14, marker="x", color="grey", alpha=0.7, label="false plots" if rid == "R1" else None)
        ax.plot(r["x"], r["y"], "^", color=c, ms=13, mec="k")
        ax.annotate(rid, (r["x"], r["y"]), xytext=(8, 8), textcoords="offset points", color=c, weight="bold")
    for k, tr in enumerate(res["tracks"]):
        pts = np.array([(p[1], p[2]) for p in tr["pts"]])
        ax.plot(pts[:, 0], pts[:, 1], color="crimson", lw=2.2, alpha=0.9,
                label="fused radar track" if k == 0 else None)
    ax.set_xlim(-h - 300, h + 300); ax.set_ylim(-h - 300, h + 300); ax.set_aspect("equal")
    ax.set_xlabel("east [m]"); ax.set_ylabel("north [m]")
    ax.set_title("Radar trajectory reconstruction (20 x 20 km, radars in opposite corners)")
    ax.legend(loc="lower right", fontsize=8)

    ax2 = fig.add_subplot(gs[0, 1])
    thr = cfg["radar"]["detect_snr_db"]
    for rid, r in res["radars"].items():
        t = np.array([s["t"] for s in r["scans"]])
        ax2.plot(t, [s["snr_mean"] for s in r["scans"]], color=cols.get(rid), lw=0.9, label=f"{rid} mean SNR (truth)")
        d = np.array([s["det"] for s in r["scans"]])
        ax2.scatter(t[d], np.array([s["snr_obs"] for s in r["scans"]])[d], s=6, color=cols.get(rid), alpha=0.6)
    ax2.axhline(thr, color="k", ls="--", lw=0.8, label=f"detection threshold ({thr:g} dB)")
    ax2.set_ylim(-60, 50); ax2.set_ylabel("SNR [dB]"); ax2.set_title("Radar SNR (dots = scans with a detection)")
    ax2.grid(alpha=0.3); ax2.legend(fontsize=8, loc="lower right")

    ax3 = fig.add_subplot(gs[1, 1], sharex=ax2)
    for k, tr in enumerate(res["tracks"]):
        ts = np.array([p[0] for p in tr["pts"]])
        e = [np.hypot(p[1] - np.interp(p[0], trk["t"], trk["x"]), p[2] - np.interp(p[0], trk["t"], trk["y"]))
             for p in tr["pts"]]
        ax3.plot(ts, e, color="crimson", lw=1.0)
    ax3.set_xlabel("t since scenario start [s]"); ax3.set_ylabel("fused track error [m]")
    ax3.set_title("Track position error vs truth (gaps = no radar coverage)"); ax3.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"{out}/radar_tracks.png", dpi=110)


# ----------------------------------------------------------------------------
# Self-check: does the data agree with the truth?
# ----------------------------------------------------------------------------
def self_check(results, cfg):
    print("\n=== self-check ===")
    for rid, r in results.items():
        L = np.array([(x[3], x[6], x[8]) for x in r["links"]], float)
        blocked, clear = L[:, 0] >= 3.0, L[:, 0] < 3.0
        print(f"[{rid}] clear {clear.mean() * 100:4.0f}% of time | mean SNR clear "
              f"{L[clear, 1].mean() if clear.any() else float('nan'):6.1f} dB vs blocked "
              f"{L[blocked, 1].mean() if blocked.any() else float('nan'):6.1f} dB | "
              f"detected {L[:, 2].mean() * 100:3.0f}% (clear {L[clear, 2].mean() * 100 if clear.any() else 0:3.0f}%, "
              f"blocked {L[blocked, 2].mean() * 100 if blocked.any() else 0:3.0f}%)")
        truth_b = {round(x[0], 3): x[2] for x in r["links"]}
        err = [((m - truth_b[round(t, 3)] + 180) % 360) - 180 for t, m, _, _, o in r["doa"] if not o]
        if err:
            print(f"     bearing error (non-outliers): RMS {np.sqrt(np.mean(np.square(err))):.1f} deg over {len(err)} fixes")


# ----------------------------------------------------------------------------
def plot(out, dem, trk, cfg, results, n_bin, n_ch, freqs):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(2, 2, figsize=(15, 11))
    h = cfg["dem_half_size_m"]
    a = ax[0, 0]
    im = a.imshow(dem.z, origin="lower", extent=[-h, h, -h, h], cmap="terrain")
    a.plot(trk["x"], trk["y"], "k-", lw=1.2, label="drone (truth)")
    for rx in cfg["receivers"]:
        a.plot(rx["x"], rx["y"], "r^", ms=10)
        a.annotate(rx["id"], (rx["x"], rx["y"]), color="r", xytext=(6, 6), textcoords="offset points")
    a.set_title("Terrain + truth track"); a.legend(); plt.colorbar(im, ax=a, label="m ASL")

    a = ax[0, 1]
    for rid, r in results.items():
        t = [x[0] for x in r["links"]]
        a.plot(t, [x[6] for x in r["links"]], lw=0.8, label=f"RX {rid} SNR (truth)")
        bl = np.array([x[4] == "BLOCKED" for x in r["links"]])
        a.fill_between(t, -40, 60, where=bl, alpha=0.12)
    a.axhline(cfg["rx"]["detect_snr_db"], color="k", ls="--", lw=0.7)
    a.set_ylim(-40, 60); a.set_xlabel("t [s]"); a.set_ylabel("SNR [dB]")
    a.set_title("True SNR (shaded = terrain-blocked)"); a.legend()

    for k, (rid, r) in enumerate(results.items()):
        a = ax[1, k]
        wf = r["wf"]
        T = wf.shape[0] * cfg["dt_s"]
        a.imshow(wf, aspect="auto", origin="upper", cmap="viridis",
                 vmin=n_bin - 3, vmax=n_bin + 35,
                 extent=[(freqs[0]) / 1e6, freqs[-1] / 1e6, T + r["off"], r["off"]])
        a.set_title(f"Receiver {rid} waterfall (rx clock offset {r['off']:+.2f} s)")
        a.set_xlabel("MHz"); a.set_ylabel("t since start, rx clock [s]")
    plt.tight_layout()
    plt.savefig(f"{out}/overview.png", dpi=110)


def plot_snr(out, cfg, results):
    """One SNR figure with all receivers on the same axes."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    thr = cfg["rx"]["detect_snr_db"]
    colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    fig, ax = plt.subplots(figsize=(13, 5.5))

    all_snr = np.concatenate([[x[6] for x in r["links"]] for r in results.values()])
    lo, hi = all_snr.min() - 8, all_snr.max() + 5
    strip_h = (hi - lo) * 0.03

    for k, (rid, r) in enumerate(results.items()):
        L = r["links"]
        t = np.array([x[0] for x in L])
        snr = np.array([x[6] for x in L])
        blocked = np.array([x[4] == "BLOCKED" for x in L])
        c = colors[k % len(colors)]
        ax.plot(t, snr, color=c, lw=0.9, label=f"RX {rid} SNR (truth)")
        # blocked-by-terrain strip along the bottom, one row per receiver
        y0 = lo + k * strip_h
        ax.fill_between(t, y0, y0 + strip_h * 0.8, where=blocked, color=c, alpha=0.6, step="mid",
                        label=f"RX {rid} terrain-blocked")

    ax.axhline(thr, color="k", ls="--", lw=0.8, label=f"detection threshold ({thr:g} dB)")
    ax.set_ylim(lo, hi)
    ax.set_xlabel("t since scenario start [s] (true time)")
    ax.set_ylabel("SNR [dB]")
    ax.set_title("Signal-to-noise ratio at each receiver")
    ax.grid(alpha=0.3)
    ax.legend(loc="upper right", fontsize=8, ncol=2)
    plt.tight_layout()
    plt.savefig(f"{out}/snr.png", dpi=110)


def plot_trajectory(out, dem, trk, cfg):
    """True drone trajectory on the 20 x 20 km area square, coloured by time."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    h = cfg["dem_half_size_m"]
    km = 1000.0
    fig, ax = plt.subplots(figsize=(11, 8.6))
    im = ax.imshow(dem.z, origin="lower", extent=[-h / km, h / km, -h / km, h / km],
                   cmap="terrain", alpha=0.55)
    plt.colorbar(im, ax=ax, label="terrain elevation [m ASL]", shrink=0.75, pad=0.01, aspect=30)

    # path coloured by time
    pts = np.column_stack([trk["x"] / km, trk["y"] / km])
    segs = np.stack([pts[:-1], pts[1:]], axis=1)
    lc = LineCollection(segs, cmap="plasma", linewidths=3)
    lc.set_array(trk["t"][:-1] / 60.0)
    ax.add_collection(lc)
    cb = plt.colorbar(lc, ax=ax, label="time since start [min]", shrink=0.75, pad=0.03, aspect=30)

    # direction arrows every ~2 min
    step = max(int(120 / cfg["dt_s"]), 1)
    for i in range(step // 2, len(trk["t"]) - 1, step):
        ax.annotate("", xy=(pts[i + 1, 0], pts[i + 1, 1]), xytext=(pts[i, 0], pts[i, 1]),
                    arrowprops=dict(arrowstyle="-|>", color="k", lw=1.2, mutation_scale=16))

    ax.plot(*pts[0], "o", color="lime", mec="k", ms=11, zorder=5, label="start")
    ax.plot(*pts[-1], "s", color="red", mec="k", ms=11, zorder=5, label="end")

    for rd in cfg.get("radars", []):
        ax.plot(rd["x"] / km, rd["y"] / km, "^", color="navy", mec="w", ms=14, zorder=6,
                label="radar" if rd["id"] == cfg["radars"][0]["id"] else None)
        ax.annotate(rd["id"], (rd["x"] / km, rd["y"] / km), xytext=(-4 if rd["x"] > 0 else 8, -16 if rd["y"] > 0 else 8),
                    textcoords="offset points", ha="right" if rd["x"] > 0 else "left", weight="bold", color="navy")
    for rx in cfg["receivers"]:
        ax.plot(rx["x"] / km, rx["y"] / km, "D", color="crimson", mec="w", ms=9, zorder=6,
                label="RF receiver" if rx["id"] == cfg["receivers"][0]["id"] else None)
        ax.annotate(rx["id"], (rx["x"] / km, rx["y"] / km), xytext=(7, 5), textcoords="offset points",
                    color="crimson", weight="bold")

    ax.add_patch(plt.Rectangle((-h / km, -h / km), 2 * h / km, 2 * h / km, fill=False, ec="k", lw=2))
    ax.set_xlim(-h / km - 0.4, h / km + 0.4)
    ax.set_ylim(-h / km - 0.4, h / km + 0.4)
    ax.set_aspect("equal")
    ax.set_xticks(np.arange(-10, 11, 2)); ax.set_yticks(np.arange(-10, 11, 2))
    ax.grid(alpha=0.35)
    ax.set_xlabel("east [km]"); ax.set_ylabel("north [km]")
    dur = trk["t"][-1] / 60.0
    length = float(np.sum(np.hypot(np.diff(trk["x"]), np.diff(trk["y"])))) / km
    ax.set_title("Drone trajectory (truth) on the 20 x 20 km area\n"
                 f"{dur:.0f} min, {length:.1f} km flown, {cfg['drone']['speed_mps']:.0f} m/s, "
                 f"{cfg['drone']['agl_m']:.0f} m above ground", fontsize=12)
    ax.legend(loc="lower right", fontsize=9, framealpha=0.9)
    plt.tight_layout()
    plt.savefig(f"{out}/trajectory.png", dpi=120)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=CONFIG["seed"])
    ap.add_argument("--out", default="scenario_001")
    ap.add_argument("--dem", default=None, help="path to GeoTIFF (Copernicus GLO-30)")
    args = ap.parse_args()
    CONFIG["seed"] = args.seed
    simulate(CONFIG, args.out, args.dem)
    print(f"\nwritten to {args.out}/")