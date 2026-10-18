# Mirror World: RF propagation + SIGINT physics core (research spike)

Date: 2026-10-18. Author: RF research spike. Scope: terrain path loss, other propagation terms, receiver/DF realism, interference/EW, bearing fixing + error ellipse for CoT.

Status legend: **[measured]** = run in this spike (code + numbers below); **[verified]** = checked against a source fetched in this session; **[unverified]** = from memory or vendor marketing, not checked here. Treat unverified numbers as defaults to tune, not facts.

All spike code is in `scratch/rf-spike/scripts/`, run with `.venv/bin/python -I <script> <args>` (uv venv, Python 3.12, numpy 2.5.4, scipy 1.18.1, rasterio 1.5.2, itmlogic 1.2, itur 0.4.0).

---

## 0. Recommendation

**Write our own vectorised numpy delta-Bullington model (ITU-R P.526-16 §4.5, the same equations as P.1812 §4.3 and P.452 §4.2.3). Add free-space loss and a small set of stochastic terms on top. Use the eeveetza `Py1812` package only as a test oracle in CI, never at runtime.**

Evidence (all **[measured]**):

| What | Result |
|---|---|
| Agreement with the reference implementation (`Py1812.dl_delta_bull`, from the lineage of the ITU-R WP3M reference code) | max abs diff **1.4e-14 dB** over 8,897 random real-DEM links at 0.433, 2.44 and 5.8 GHz (about 50% NLOS, ranges 0.3 to 30 km, drone 2 to 2000 m AGL) |
| Agreement with the full `Py1812.bt_loss` (p = 50%, no clutter) on the ridge sweep | identical to 0.1 dB (for short paths at p = 50%, P.1812 reduces to FSPL + delta-Bullington) |
| Reciprocity (swap the two ends) | max diff 1.2e-11 dB over 2,000 links |
| Throughput with M = 256 profile points (about 27 m spacing at 7 km), including bilinear DEM profile extraction | **16 µs per link**. 1e5 links take 1.6 s and 1e6 about 16 s on one core (Apple Silicon, numpy). |
| `Py1812.bt_loss` in a Python loop | 243 µs per link, about 15x slower, and it still needs our profile extraction |
| `itmlogic` (Longley-Rice ITM 1.2.2 port) | about 200 µs per link; gives **+10 to +31 dB more loss** than P.1812 in NLOS on short paths (see §2.4) |
| `pycraf` 2.1.0 (P.452) | no macOS arm64 wheel. It builds from source, but import fails with `symbol not found '_omp_set_num_threads'` (OpenMP). It is also GPLv3. |
| Profile sampling | at spacing ≤ 30 m (the DEM posting) the 95th-percentile error vs a 7 m reference is ≤ 0.6 dB. At 54 m it is 1.7 dB, with a max of 16 dB (a ridge crest gets skipped). **Rule: spacing ≤ DEM posting.** |

Why our own implementation and not a library:
1. **Speed.** We need 1e4 to 1e6 evaluations per scenario. Vectorised numpy is 15x faster than the best library loop and trivially chunked.
2. **Same physics.** The code is bit-exact against the ITU reference implementation, so we lose nothing in faithfulness, and the presentation can say "ITU-R P.526/P.1812 delta-Bullington, verified against the ITU-R WP3M reference implementation".
3. **No dependency or licence baggage.** Py1812 imports ITU digital maps (`P1812.npz`, built from DN50.TXT and N050.TXT) that "must not be reproduced or distributed without explicit written permission from the ITU". We bypass them by passing `DN=45, N0=325` and a stub npz in tests. pycraf is GPLv3 and does not import on arm64 macs. itmlogic disagrees strongly with ITU on short NLOS paths.
4. **Scope.** The physics we care about (terrain masking, a smooth transition from diffraction to LoS, frequency dependence) is exactly what delta-Bullington models. Tropospheric scatter and ducting (the other half of P.1812/P.452) are irrelevant below 30 km at p = 50%.

How the faithfulness requirement shows up (from the real-DEM ridge sweep, §2.3): a drone 4.4 km west of RX1 in the valley behind a 212 m crest has **Ld = 44 dB at 5 m AGL, 35 dB at 40 m, 13 dB at 75 m, 7 dB at 80 m, and 0 dB from 90 m up (2.44 GHz)**. Its bearing still points at the ridge, which lies on the same azimuth as the drone. Its SNR drops by Ld, so bearing sigma grows and wild-bearing probability rises (§5).

---

## 1. Survey of Python-usable path-loss options

| Option | Install | Licence | Maintenance | API shape | Fit for air-to-ground with high Tx over DEM | Verdict |
|---|---|---|---|---|---|---|
| **Own numpy delta-Bullington** (this doc, `rfcore.py`) | none | ours | ours | batch: `delta_bullington(d[N,M], h[N,M], htg[N], hrg[N], f, ae)` | Good. Terrain-aware, any heights, 0.03 to 6 GHz validity inherited from P.526/P.1812 | **Use** |
| **Py1812** (eeveetza), ITU-R P.1812-8 | `pip install "git+https://github.com/eeveetza/Py1812"`, then supply ITU maps or a stub npz and pass DN/N0 | permissive custom ("AS IS", derivatives allowed with a change notice and acknowledgement) **[verified LICENSE]**. ITU maps are not redistributable. | active, pushed 2026-08-28, 14 stars **[verified GitHub API]** | scalar per call: `P1812.bt_loss(f, p, d, h, R, zone, htg, hrg, pol, phi_t, phi_r, lam_t, lam_r, DN=, N0=, ...)` returns `(Lb, Ep)`. Limits: 0.03 to 6 GHz, htg and hrg from 1 to 3000 m, d ≳ 0.25 km. | Good (heights up to 3000 m). Includes clutter heights R, location variability, and ducting/tropo. | **Test oracle** |
| **Py452** (eeveetza), P.452 | git install, needs ITU maps | same as Py1812 | pushed 2026-08-29 | scalar | Interference-oriented. Diffraction is the same delta-Bullington, plus ducting and hydrometeors. | skip |
| **Py528** (eeveetza), P.528 aeronautical | git install | same | pushed 2026-02-13, 0 stars | scalar | **No terrain profile** (smooth earth, IF-77 heritage). Two-ray lobing in LoS. 0.1 to 30 GHz, terminals up to 20 km. Only for long-range high aircraft. | optional cross-check |
| **Py2001** (eeveetza), P.2001 | git install, many ITU maps | same | pushed 2025-11-21 | scalar | Wide-range, Monte-Carlo oriented (0.00001 to 99.999% of time). Heavier, same diffraction core. | skip |
| **Py2108** (eeveetza), P.2108 clutter | git install (needs pandas) | same | pushed 2026-08-15 | scalar `cl_p2108_2(f,d,p)`, `cl_p2108_3(f,theta,p,h,hm)` | Clutter loss at the terminal (used in §4.4) | **use formulas** |
| **proplib-p2108** (NTIA, US reference implementation of P.2108) | `pip install proplib-p2108` (1.1.0, Jan 2025) **[verified PyPI]** | NTIA software disclaimer | NTIA | C++ with a Python wrapper | Same as Py2108 | alternative |
| **itmlogic** (Oughton), Longley-Rice ITM 1.2.2 | `pip install itmlogic` (1.2) | MIT **[verified dist-info]** | last pushed 2025-05-14, 73 stars | dict-based: `prop` dict, then `qlrpfl(prop)`, then `avar(zr, 0, zc, prop)` | 20 MHz to 20 GHz, heights 0.5 to 3000 m. **Short NLOS paths give +10 to +31 dB vs P.1812** at 0.9 to 5.8 GHz. Pure Python, 0.2 ms per call. | not recommended |
| **pyitm** (tmd224), ITM | `pip install pyitm` (0.3, 2022) | MIT | stale | untested | same model as itmlogic | skip |
| **pycraf** (B. Winkel), P.452 `pathprof`, P.676, antennas | `pip install pycraf` (2.1.0). Wheels only for x86_64 (mac/linux/win). On arm64 the source build "succeeds" in about 15 s but **import fails (OpenMP symbol)**. conda-forge may work **[unverified]**. | **GPLv3** | active | astropy-units heavy: `pathprof.PathProp(...)`, then `pathprof.loss_complete(pp, G_t, G_r)` | P.452 with a terrain profile (can take a custom profile). | skip (licence plus install friction) |
| **itur** (ITU-Rpy), P.676/P.838/P.618/... | `pip install itur` (0.4.0) | MIT **[unverified]** | maintained | `itu676.gaseous_attenuation_terrestrial_path(...)`, `itu838.rain_specific_attenuation(...)` | Atmospheric terms only. Used in §4.2 to show they are negligible. | dev-only |

Not pursued: Sionna RT and other ray tracers (GPU, needs meshes, overkill), SPLAT! (C++ CLI, ITM), Signal-Server (C, ITM/Hata).

---

## 2. Hands-on test

### 2.1 DEM: Copernicus GLO-30 COG windowed read **[measured, verified URL]**

- `curl -I` on `https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N49_00_E031_00_DEM/Copernicus_DSM_COG_10_N49_00_E031_00_DEM.tif` returns **HTTP 200**, 43,027,743 bytes, `Accept-Ranges: bytes`, Last-Modified 2022-05-09.
- Tile metadata: EPSG:4326, 3600x3600 px, float32, res 1 arcsec (0.000277°, about 31 m N-S and 20 m E-W at 49.4°N), bounds 30.99986 to 31.99986 E and 49.00014 to 50.00014 N (the half-pixel offset means pixel *centres* sit on integer degrees), 1024x1024 internal tiles, overviews 2/4/8, nodata None.
- Window 31.00 to 31.40 E, 49.25 to 49.50 N (1440x900 px) read through `/vsicurl/` in **2.07 s**. Elevation ranges 56 to 259 m (mean 168 m). The brief's truth point 49.3754 N, 31.1882 E is at **190.9 m**.
- Caveats: GLO-30 is a **DSM** (X-band InSAR, so it partially includes canopy and buildings). Forest blocks and shelterbelts therefore already appear as raised terrain, so do not add clutter loss for those on top. Heights are orthometric (EGM2008 geoid) **[unverified, from memory]**, while CoT `hae` is height above the WGS84 ellipsoid. Add the geoid undulation (roughly +20 to +25 m in central Ukraine **[unverified]**, compute it with PROJ's EGM2008 grid). A scenario that straddles a 1° tile needs a mosaic of tiles.

```python
# scripts/dem_fetch.py (core)
URL = ("/vsicurl/https://copernicus-dem-30m.s3.amazonaws.com/"
       "Copernicus_DSM_COG_10_N49_00_E031_00_DEM/Copernicus_DSM_COG_10_N49_00_E031_00_DEM.tif")
GDAL_ENV = dict(GDAL_HTTP_TIMEOUT=30, GDAL_HTTP_CONNECTTIMEOUT=10, GDAL_HTTP_MAX_RETRY=3,
                GDAL_HTTP_RETRY_DELAY=1, GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
                CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif", VSI_CACHE="TRUE")
with rasterio.Env(**GDAL_ENV):
    with rasterio.open(URL) as ds:
        win = from_bounds(west, south, east, north, ds.transform).round_offsets().round_lengths()
        z = ds.read(1, window=win); tr = ds.window_transform(win)
if not np.isfinite(z).all(): raise ValueError("non-finite DEM samples")   # no silent failures
```

### 2.2 Terrain reality check near the truth point **[measured]**

`scripts/find_ridge.py` puts two receivers on the highest ground within 1.5 km of points 3 km west and 3 km east of the truth point. That gives **RX1 at 49.36623 N, 31.12605 E (203.3 m)** and **RX2 at 49.36866 N, 31.20892 E (197.7 m)**, 6.0 km apart, matching the brief. Masts are 20 m. A radial horizon scan (360 azimuths, 30 m steps, 6 km, k = 1.40) computes the **minimum drone AGL that is visible** in each ground cell. It is vectorised with a prefix maximum (`np.maximum.accumulate`) of the terrain elevation angle:

- 56% (RX1) and 64% (RX2) of ground cells within 6 km are hidden at 0 m AGL. But the **median minimum visible height in hidden cells is only 7 to 11 m AGL (p90 33 to 38 m)**.
- **Consequence for scenario design:** central-Ukraine farmland is gentle. "Hidden behind a ridge" only happens for drones below about 40 to 80 m AGL or in the river valleys (the Ros valley is in this window). A 2-minute masking event has to be designed: route the drone through the shadow map at low altitude. This map is cheap (milliseconds per receiver) and is a strong demo visual.

```python
# horizon / min-visible-AGL map per receiver (scripts/find_ridge.py)
ang  = (H - hr - r**2/(2*ae)) / r                        # terrain elevation angle incl. earth bulge
hor  = np.maximum.accumulate(ang, axis=1)                 # horizon angle up to range r
hprev= np.concatenate([np.full((naz,1), -np.inf), hor[:, :-1]], axis=1)
need = np.maximum(0.0, hr + hprev*r + r**2/(2*ae) - H)    # min AGL at (az, r) for geometric LoS
```

The chosen ridge-shadowed spot is 49.36485 N, 31.06560 E: 4.38 km from RX1 at azimuth 268°, ground at 130.2 m, minimum visible AGL 75 m. The crest is 212.2 m at 2.70 km from RX1.

### 2.3 Ridge sweep: drone rises from behind the ridge into LoS **[measured]**

`scripts/compare.py`. RX1 has a 20 m mast and the drone is at the spot above. The profile uses M = 256 points (17 m spacing), k = 1.40 (ΔN = 45), vertical polarisation, inland, p = 50%. Ld_Py1812 is the reference `dl_delta_bull` on identical inputs. Lb_P1812full is the complete `bt_loss`. Lb_ITM is itmlogic at 50% reliability and 50% confidence.

**2.44 GHz** (FSPL 113.0 dB):

| AGL m | LoS? | Ld ours | Ld Py1812 | Lb ours | Lb P.1812 full | Lb ITM |
|---|---|---|---|---|---|---|
| 5 | no | 44.12 | 44.12 | 157.1 | 157.1 | 183.8 |
| 10 | no | 42.90 | 42.90 | 155.9 | 155.9 | 181.1 |
| 20 | no | 40.47 | 40.47 | 153.5 | 153.5 | 178.1 |
| 30 | no | 38.21 | 38.21 | 151.2 | 151.2 | 173.0 |
| 40 | no | 35.09 | 35.09 | 148.1 | 148.1 | 166.2 |
| 50 | no | 29.78 | 29.78 | 142.8 | 142.8 | 155.3 |
| 60 | no | 24.46 | 24.46 | 137.4 | 137.4 | 148.9 |
| 70 | no | 17.83 | 17.83 | 130.8 | 130.8 | 140.7 |
| 75 | no | 13.06 | 13.06 | 126.0 | 126.0 | 135.5 |
| 80 | yes (sub-path, inside the Fresnel zone) | 7.36 | 7.36 | 120.3 | 120.3 | 113.0 |
| ≥ 90 | yes | 0.00 | 0.00 | 113.0 | 113.0 | 113.0 |

The same sweep at other frequencies (Ld ours = Ld Py1812 in every row; ITM in brackets):
- **433 MHz:** Ld = 38.1 / 27.5 / 12.7 / 10.4 / 5.3 / 0 dB at 5 / 40 / 75 / 80 / 90 / 100 m AGL. ITM is close at this frequency (136.6 vs 136.1 dB total at 5 m).
- **915 MHz:** Ld = 39.8 / 30.8 / 12.8 / 9.4 / 1.7 / 0 dB. ITM is +13 dB at 5 m.
- **5.8 GHz:** Ld = 47.9 / 38.9 / 13.4 / 4.4 / 0 dB. ITM is +31 dB at 5 m.

So diffraction loss rises with frequency as expected (about +10 dB from 433 MHz to 5.8 GHz deep in the shadow), and lower frequencies diffract into the shadow more gently (433 MHz still loses 5 dB at 90 m). These are exactly the frequency-dependent cues the jury wants to see.

### 2.4 Timing per call **[measured, M = 256]**

| Implementation | ms per link |
|---|---|
| `Py1812.bt_loss` (full P.1812) | 0.243 to 0.25 |
| `Py1812.dl_delta_bull` (diffraction only, after `smooth_earth_heights`) | 0.039 (plus about 0.05 for the heights) |
| itmlogic `qlrpfl` + `avar` | 0.20 |
| ours, a single link (numpy overhead dominates) | 0.110 |
| ours, batched, **profile extraction + delta-Bullington** | **0.0075 (M = 128), 0.016 (M = 256), 0.035 (M = 512)** |

Batch breakdown at N = 1e5, chunks of 8192 links:

| M | Profile extraction, µs/link | delta-Bullington, µs/link |
|---|---|---|
| 128 | 4.1 | 4.2 |
| 256 | 7.4 | 8.6 |
| 512 | 17.0 | 18.0 |

The end-to-end SIGINT demo (§5.6) computes 2x596 links in 13 to 15 ms.

### 2.5 Profile-resolution sensitivity **[measured]**

About 1,500 random links from 1 to 10 km, Rx mast 20 m, drone 2 to 500 m. Reference is M = 1024 (7 m spacing).

| M | Median spacing | Mean error | p95 abs error | Max abs error |
|---|---|---|---|---|
| 512 | 13 m | -0.04 dB | 0.22 dB | 2.3 dB |
| 256 | 27 m | -0.12 dB | 0.60 dB | 5.7 dB |
| 128 | 54 m | -0.33 dB | 1.74 dB | 16.0 dB |
| 64 | 108 m | -0.63 dB | 3.60 dB | 21.5 dB |

→ Use `M = clip(ceil(d / 30 m) + 1, 32, 1024)` and bucket links by M (for example powers of two). A 30 km link costs about 70 µs.

### 2.6 Implementation (`scripts/rfcore.py`, verified bit-exact against Py1812)

```python
"""Vectorised terrain path loss: ITU-R P.526-16 §4.5 / P.1812-7/8 §4.3.4 delta-Bullington.

All link-level arrays are shape (N,), profile arrays are shape (N, M) with
d[:, 0] = 0 (station 'T') and d[:, -1] = dtot (station 'R').  Units follow ITU:
distances km, heights m amsl, f GHz.  Pure numpy, no Python loops over links.
"""
import numpy as np

C_ITU = 0.2998          # ITU-R P.452/P.1812/P.2001 use lambda = 0.2998 / f[GHz]
R_EARTH_KM = 6371.0


def k_factor_from_dn(dn=45.0):
    """P.1812/P.452 eq.(6): median k50 = 157/(157-DN); DN=45 N-units/km -> k=1.40 (~4/3)."""
    return 157.0 / (157.0 - dn)


def fspl_db(d3d_km, f_ghz):
    """Free-space basic transmission loss, P.525 / P.1812 eq.(8): 92.4 + 20log f(GHz) + 20log d(km)."""
    return 92.4 + 20.0 * np.log10(f_ghz) + 20.0 * np.log10(d3d_km)


def _knife_edge_j(nu):
    """J(nu) per P.526 eq.(31) approximation, 0 for nu <= -0.78."""
    nu = np.asarray(nu)
    out = np.zeros_like(nu, dtype=float)
    m = nu > -0.78
    v = nu[m] - 0.1
    out[m] = 6.9 + 20.0 * np.log10(np.sqrt(v * v + 1.0) + v)
    return out


def bullington(d, g, hts, hrs, ae, f):
    """Bullington loss (P.526-16 §4.5.1 / P.1812 §4.3.1, eqs 12-21), vectorised over N links."""
    lam = C_ITU / f
    dtot = d[:, -1]
    dt = dtot[:, None]
    di = d[:, 1:-1]
    gi = g[:, 1:-1]
    curv = gi + 500.0 / ae * di * (dt - di)            # terrain incl. earth bulge
    stim = np.max((curv - hts[:, None]) / di, axis=1)   # eq (13)
    s_tr = (hrs - hts) / dtot                           # eq (14)
    los = stim < s_tr
    nu = np.empty_like(dtot)
    if los.any():                                       # eq (15): max nu over profile
        L = np.flatnonzero(los)
        dtl, dil = dt[L], di[L]
        nu[L] = np.max((curv[L] - (hts[L, None] * (dtl - dil) + hrs[L, None] * dil) / dtl)
                       * np.sqrt(0.002 * dtl / (lam * dil * (dtl - dil))), axis=1)
    if (~los).any():                                    # eqs (17)-(20): Bullington point
        T = np.flatnonzero(~los)
        dtt, dit = dt[T], di[T]
        srim = np.max((curv[T] - hrs[T, None]) / (dtt - dit), axis=1)
        dtt = dtt[:, 0]
        dbp = (hrs[T] - hts[T] + srim * dtt) / (stim[T] + srim)
        nu[T] = ((hts[T] + stim[T] * dbp - (hts[T] * (dtt - dbp) + hrs[T] * dbp) / dtt)
                 * np.sqrt(0.002 * dtt / (lam * dbp * (dtt - dbp))))
    luc = _knife_edge_j(nu)
    return luc + (1.0 - np.exp(-luc / 6.0)) * (10.0 + 0.02 * dtot), los   # eq (21)


def _ldft(d, hte, hre, a, f, pol, epsr=22.0, sigma=0.003):
    """First-term spherical-earth diffraction (P.526 §3.2 / P.1812 eqs 29-36); land default."""
    K = 0.036 * (a * f) ** (-1 / 3) * ((epsr - 1) ** 2 + (18 * sigma / f) ** 2) ** -0.25
    if pol == 1:  # vertical
        K = K * np.sqrt(epsr ** 2 + (18 * sigma / f) ** 2)
    beta = (1 + 1.6 * K**2 + 0.67 * K**4) / (1 + 4.5 * K**2 + 1.53 * K**4)
    X = 21.88 * beta * (f / a**2) ** (1 / 3) * d
    Fx = np.where(X >= 1.6, 11 + 10 * np.log10(X) - 17.6 * X,
                  -20 * np.log10(X) - 5.6488 * X**1.425)
    def G(h):
        B = beta * 0.9575 * beta * (f**2 / a) ** (1 / 3) * h
        with np.errstate(invalid="ignore", divide="ignore"):
            Gv = np.where(B > 2, 17.6 * np.sqrt(np.maximum(B - 1.1, 1e-9)) - 5 * np.log10(np.maximum(B - 1.1, 1e-9)) - 8,
                          20 * np.log10(B + 0.1 * B**3))
        return np.maximum(Gv, 2 + 20 * np.log10(K))
    return -Fx - G(hte) - G(hre)


def spherical_earth(d, hte, hre, ap, f, pol=1):
    """Spherical-earth diffraction loss Ldsph (P.1812 §4.3.2 eqs 22-27), vectorised."""
    lam = C_ITU / f
    out = np.zeros_like(d)
    dlos = np.sqrt(2 * ap) * (np.sqrt(0.001 * hte) + np.sqrt(0.001 * hre))
    far = d >= dlos
    if far.any():
        out[far] = _ldft(d[far], hte[far], hre[far], ap, f, pol)
    n = ~far
    if n.any():
        dn, ht, hr = d[n], hte[n], hre[n]
        c = (ht - hr) / (ht + hr)
        m = 250 * dn**2 / (ap * (ht + hr))
        b = 2 * np.sqrt((m + 1) / (3 * m)) * np.cos(np.pi / 3 + np.arccos(
            np.clip(1.5 * c * np.sqrt(3 * m / (m + 1) ** 3), -1, 1)) / 3)
        d1 = dn / 2 * (1 + b)
        d2 = dn - d1
        hse = ((ht - 500 * d1**2 / ap) * d2 + (hr - 500 * d2**2 / ap) * d1) / dn
        hreq = 17.456 * np.sqrt(d1 * d2 * lam / dn)
        aem = 500 * (dn / (np.sqrt(ht) + np.sqrt(hr))) ** 2
        ldft = np.maximum(_ldft(dn, ht, hr, aem, f, pol), 0)
        out[n] = np.where(hse > hreq, 0.0, (1 - hse / hreq) * ldft)
    return out


def smooth_earth_diff_heights(d, h, hts, hrs):
    """hstd, hsrd: effective smooth-earth heights for diffraction (P.1812 Att.1 eqs 85-91)."""
    dtot = d[:, -1]
    dd = np.diff(d, axis=1)
    v1 = np.sum(dd * (h[:, 1:] + h[:, :-1]), axis=1)
    v2 = np.sum(dd * (h[:, 1:] * (2 * d[:, 1:] + d[:, :-1]) + h[:, :-1] * (d[:, 1:] + 2 * d[:, :-1])), axis=1)
    hst = (2 * v1 * dtot - v2) / dtot**2
    hsr = (v2 - v1 * dtot) / dtot**2
    dt, di = dtot[:, None], d[:, 1:-1]
    HH = h[:, 1:-1] - (hts[:, None] * (dt - di) + hrs[:, None] * di) / dt
    hobs = HH.max(axis=1)
    a_t = (HH / di).max(axis=1)
    a_r = (HH / (dt - di)).max(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        gt = a_t / (a_t + a_r)
        gr = a_r / (a_t + a_r)
    obs = hobs > 0
    hstp = np.where(obs, hst - hobs * gt, hst)
    hsrp = np.where(obs, hsr - hobs * gr, hsr)
    hstd = np.where(hstp >= h[:, 0], h[:, 0], hstp)
    hsrd = np.where(hsrp > h[:, -1], h[:, -1], hsrp)
    return hstd, hsrd


def delta_bullington(d, h, htg, hrg, f, ae, pol=1, clutter=None):
    """Delta-Bullington diffraction loss Ld (dB), P.526-16 §4.5 / P.1812 eq (39).

    d, h: (N, M) km / m amsl terrain; htg, hrg: (N,) antenna heights AGL (m).
    clutter: optional (N, M) representative clutter heights added to interior points.
    Returns Ld, Lbulla, los_flag.
    """
    hts = h[:, 0] + htg
    hrs = h[:, -1] + hrg
    g = h if clutter is None else h + clutter * np.r_[0, np.ones(h.shape[1] - 2), 0]
    lbulla, los = bullington(d, g, hts, hrs, ae, f)
    hstd, hsrd = smooth_earth_diff_heights(d, h, hts, hrs)
    hts1, hrs1 = hts - hstd, hrs - hsrd
    lbulls, _ = bullington(d, np.zeros_like(d), hts1, hrs1, ae, f)
    ldsph = spherical_earth(d[:, -1], hts1, hrs1, ae, f, pol)
    return lbulla + np.maximum(ldsph - lbulls, 0.0), lbulla, los


class DEM:
    """Regular lat/lon grid (EPSG:4326, north-up) with bilinear sampling."""
    def __init__(self, z, transform):
        self.z = np.ascontiguousarray(z, dtype=np.float32)
        a, _, c, _, e, f_ = transform[:6]
        # GDAL transform gives pixel *corner*; +0.5 to address pixel centres
        self.x0, self.dx, self.y0, self.dy = c + 0.5 * a, a, f_ + 0.5 * e, e

    def sample(self, lat, lon):
        cf = (lon - self.x0) / self.dx
        rf = (lat - self.y0) / self.dy
        H, W = self.z.shape
        c0 = np.clip(np.floor(cf).astype(np.int64), 0, W - 2)
        r0 = np.clip(np.floor(rf).astype(np.int64), 0, H - 2)
        tc = np.clip(cf - c0, 0, 1); tr = np.clip(rf - r0, 0, 1)
        z = self.z
        z00 = z[r0, c0]; z01 = z[r0, c0 + 1]; z10 = z[r0 + 1, c0]; z11 = z[r0 + 1, c0 + 1]
        return (z00 * (1 - tc) + z01 * tc) * (1 - tr) + (z10 * (1 - tc) + z11 * tc) * tr

    def profiles(self, lat_a, lon_a, lat_b, lon_b, m):
        """m equally spaced samples A->B (straight in lat/lon; fine for <~50 km). Returns d_km (N,M), h (N,M)."""
        t = np.linspace(0.0, 1.0, m)
        lat = lat_a[:, None] + (lat_b - lat_a)[:, None] * t
        lon = lon_a[:, None] + (lon_b - lon_a)[:, None] * t
        dtot = ground_dist_km(lat_a, lon_a, lat_b, lon_b)
        return dtot[:, None] * t, self.sample(lat, lon)


def ground_dist_km(lat1, lon1, lat2, lon2):
    """Equirectangular distance; <0.1% error for <50 km links."""
    latm = np.radians(0.5 * (lat1 + lat2))
    dx = np.radians(lon2 - lon1) * np.cos(latm)
    dy = np.radians(lat2 - lat1)
    return R_EARTH_KM * np.hypot(dx, dy)


def link_loss(dem, rx_lat, rx_lon, rx_agl, tx_lat, tx_lon, tx_agl, f_ghz, m=256, k=None, pol=1):
    """Median basic transmission loss Rx<->Tx over DEM terrain: Lbfs + Ld (delta-Bullington)."""
    ae = R_EARTH_KM * (k if k is not None else k_factor_from_dn(45.0))
    d, h = dem.profiles(rx_lat, rx_lon, tx_lat, tx_lon, m)
    ld, lbulla, los = delta_bullington(d, h, rx_agl, tx_agl, f_ghz, ae, pol)
    dh_km = ((h[:, -1] + tx_agl) - (h[:, 0] + rx_agl)) / 1000.0
    d3 = np.hypot(d[:, -1], dh_km)
    return fspl_db(d3, f_ghz) + ld, ld, los, d[:, -1]
```

Validation harness: `scripts/bench.py` loops `Py1812.smooth_earth_heights` and `Py1812.dl_delta_bull` over the same profiles and reports the max abs difference. Keep a 1,000-link version of it as a CI test, using the stub `P1812.npz` (DN50/N050 constant arrays) and passing `DN=45, N0=325` explicitly.

### 2.7 Performance knobs, in order of payoff
1. **Evaluate at 1 to 2 Hz per (emitter, receiver) and interpolate in dB.** Loss changes slowly except at ridge transitions. If |ΔLd| > 3 dB between samples, refine adaptively. A 2 h scenario with 5 emitters, 4 receivers at 1 Hz is 144k links, about 2.5 s.
2. **Bucket by distance** so M matches the DEM posting (§2.5), and chunk 4k to 16k links (an 8192x256 float64 array is 16.8 MB).
3. **LoS early-out:** if the drone is above the receiver's horizon mask (§2.2 prefix-max trick) plus 0.6 of the first Fresnel radius, then Ld = 0 and the delta-Bullington call can be skipped.
4. **Per-receiver radial cache:** profiles from a fixed receiver are prefixes of radials. The receiver-side slope Stim(dtot) = 500·Ce·dtot + cummax_i[(g_i − hts)/d_i − 500·Ce·d_i] is a prefix max, so it costs O(1) per link. The drone-side terms still need the per-link max. This is only worth doing if we go beyond about 1e6 links.
5. float32 and numba would each give 2 to 4x more. They are not needed at our scale.

---

## 3. What the total loss is made of

```
Lb(t) = FSPL(d3D, f)                     # P.525: 92.4 + 20 log f[GHz] + 20 log d[km]
      + Ld(delta-Bullington, DEM)        # deterministic terrain diffraction (this doc)
      + A_veg / L_clutter (terminal)     # only for terminals inside trees or villages (§4.3/4.4)
      + A_gas (≈0.008 dB/km)             # optional, negligible (§4.2)
Prx(t) = EIRP_tx(az,el,roll) − Lb(t) + G_rx(az,el) − L_cable − L_pol(t)
       + S_shadow(t)  [AR(1), Gudmundson]  + F_fast(t) [Rician, K by state]
```

Keep the deterministic part (FSPL + Ld) in the ground-truth log, so "why is this RSSI low?" can be answered for every record. That fits the brief's "which object every record came from" and our "no hidden failures" ethos.

---

## 4. Other propagation terms

### 4.1 Effective earth radius
- P.1812/P.452 eq. (6): `k50 = 157/(157 − ΔN)`, `ae = 6371·k50` km. ΔN = 45 N-units/km (the Py1812 default) gives **k = 1.40, ae = 8,918 km**. The classic k = 4/3 (ΔN ≈ 39) differs by < 0.3 dB of Ld on our < 30 km paths. **[measured value of k; verified formula in Py1812 source]**
- For a November dusk inversion, optionally use ΔN = 60 to 80 (k = 1.6 to 2) for a "super-refractive evening" flavour. That is a small effect below 30 km.
- Radio horizon with k = 4/3: `d ≈ 4.12(√h1 + √h2)` km. A 20 m mast and a 2000 m aircraft give 203 km, so high flyers are always in LoS inside the scenario box.

### 4.2 Gaseous and rain attenuation: negligible **[measured with itur 0.4.0, P.676 + P.838]**
November, T = 278 K, P = 1000 hPa, ρ = 5 g/m³:

| f | Gas, dB/km (dB per 30 km) | Rain 5 mm/h, dB/km (dB per 30 km) | Rain 25 mm/h, dB/km (dB per 30 km) |
|---|---|---|---|
| ≤ 1 GHz | 0.0058 (0.17) | 0.0001 (0.004) | 0.0005 (0.01) |
| 2.44 GHz | 0.0076 (0.23) | 0.0007 (0.02) | 0.0035 (0.11) |
| 5.8 GHz | 0.0093 (0.28) | 0.0051 (0.15) | 0.066 (**1.98**) |

→ Ignore both, or add a constant 0.008 dB/km. Only 5.8 GHz in a downpour reaches 2 dB over 30 km.

### 4.3 Vegetation: ITU-R P.833 **[verified from P.833-2 PDF]**
- One terminal inside woodland: `A_ev = A_m·[1 − exp(−d·γ/A_m)]`, where d is the path length inside the vegetation in metres.
- `A_m = 0.18·f^0.752` dB, with f in MHz (Rio de Janeiro measurements, 900 to 1800 MHz, trees 15 m, Rx 2.4 m). That gives 30 dB at 900 MHz, 50 dB at 1800 MHz, and an extrapolated about 63 dB at 2.4 GHz.
- γ read off P.833 Fig. 2 (approximate): **0.2 dB/m at 1 GHz** (V and H converge there), about **0.45 dB/m at 2.4 GHz**, about **1.1 dB/m at 5.8 GHz**, about 0.1 dB/m (V) or 0.08 dB/m (H) at 433 MHz. The H curve rises about one decade per decade of frequency.
  - Cross-check: a 2.4 GHz ZigBee forest study measured 0.52 dB/m **[verified via search summary]**.
  - At about 1 GHz, trees in leaf are about 20% worse than leafless trees. A November scenario is leafless, so use 0.8·γ.
- Single vegetative obstruction (≤ 3 GHz, both terminals outside the vegetation): `A_et = d·γ`, capped by diffraction around the obstruction (P.526).
- Where it matters: Ukrainian farmland shelterbelts (10 to 20 m tall, 10 to 30 m deep **[unverified typical]**) when a drone flies below canopy height, and ground emitters such as an operator in a tree line. Example: 20 m of foliage at 2.4 GHz gives 63.5·(1 − e^(−20·0.45/63.5)) ≈ **8.4 dB**.
- **Do not apply this when the DSM already raises the profile over the forest.** Use it only for terminals inside or below the canopy.

### 4.4 Clutter: ITU-R P.2108 **[measured with eeveetza Py2108; equations verified in source]**
- §3.2, terrestrial terminal in urban or suburban clutter. Use it for ground emitters (village Wi-Fi APs, an operator's RC in a village) and receivers placed in villages.

  ```
  Ll = −2·log10(10^(−5·log10 f − 12.5) + 10^(−16.5));   σl = 4
  Ls = 32.98 + 23.9·log10 d + 3·log10 f;               σs = 6
  Lctt = −5·log10(10^(−0.2Ll) + 10^(−0.2Ls)) − σcb·Q⁻¹(p/100)
  ```

  Here f is in GHz and d in km. The older revision used `Ll = 23.5 + 9.6 log f`.
  - Medians at d = 2 km: **0.5 GHz 22.0 dB, 0.915 GHz 24.6 dB, 2.44 GHz 28.9 dB, 5.8 GHz 32.2 dB**.
  - At 2.44 GHz, p = 10% / 90% gives 23.7 / 34.0 dB.
- §3.3 (P.2108-2, per the Py2108 docstring dated 12 Jun 2025 **[revision date unverified]**), Earth-space and aeronautical paths with the ground terminal at height h among clutter of median height hm. This is the right model for "drone seen from a 2 m antenna in a low-rise village".
  - f = 2.44 GHz, h = 2 m, hm = 8 m gives L(10/50/90%) of **[14.6, 22.2, 29.5] dB at 1° elevation, [11.7, 21.4, 28.7] at 5°, [0, 18.3, 25.8] at 20°, [0, 10.0, 20.7] at 45°**.
- Receivers on masts on high ground get no clutter loss. Drones at ≥ 30 m AGL are above clutter.

### 4.5 Shadowing (residual log-normal), spatially correlated **[verified TR 38.901 values]**
- Because the DEM gives terrain shadowing deterministically, the residual σ should be at the low end. It stands for DEM errors, unresolved buildings, trees and the airframe.
- 3GPP TR 38.901 Table 7.5-6, RMa:
  - SF σ is 8 dB in NLOS. In LOS it is 4 dB before the breakpoint and 6 dB after (Table 7.4.1-1) **[LOS values unverified, from memory]**.
  - **SF decorrelation distance 37 m (LOS) and 120 m (NLOS)**. K-factor 7 dB mean with 4 dB std, K decorrelation 40 m.
- TR 36.777 (aerial UEs), RMa-AV LOS: `σ_SF = 4.2·exp(−0.0046·h_UT)` dB for 1.5 to 10 m. Shadowing shrinks with UAV height **[verified via iTecSpec render, formula reconstructed; check against the TR]**.
- Gudmundson (Electronics Letters 27(23):2145-2146, 1991): `R(Δx) = exp(−|Δx|/d_corr)`. Implement it as an AR(1) process along the distance the drone travels: `s[n] = ρ·s[n−1] + √(1−ρ²)·σ·w[n]`, with `ρ = exp(−v·Δt/d_corr)`.
- Suggested values: **σ = 3 dB LOS / 6 dB NLOS, d_corr = 50 m LOS / 120 m NLOS.** Draw them independently per (receiver, emitter) pair, seeded from (scenario_seed, rx_id, tx_id) so runs are reproducible.

### 4.6 Fast fading (Rician) **[verified K values]**
- Matolak & Sun, NASA Glenn air-ground campaign (2013), with L-band about 968 MHz and C-band about 5 GHz:
  - hilly: **K = 12.8 dB (L) and 29.4 dB (C)**
  - suburban: 14 dB (L) and 28.5 dB (C)
  - near-urban: 12 dB (L) and 27.4 dB (C)
  - C-band delay spread is typically about 10 ns, up to 1 µs in hilly terrain.
- TR 36.777 Annex B.1.2 (Alt. 2), LOS K as a function of UAV height h (m): UMa-AV `K = 4.217·log10 h + 5.787` dB, which is about 10 dB at 10 m and 14 dB at 100 m. RMa-AV `K = 22.55·log10 h − 4.72` dB, which is very high above 50 m. Alt. 3 uses K = 15 dB.
- Suggested rule:
  - **LOS, drone ≥ 50 m: K ≈ 12 dB at ≤ 1 GHz, 20 dB at 2.4 GHz, 27 dB at 5.8 GHz (±3 dB std)**
  - LOS, low drone (< 30 m): 7 ± 4 dB (TR 38.901 RMa)
  - NLOS (Ld > 6 dB): K = 0 to 3 dB
- Doppler `f_D = v/λ`: 20 m/s at 2.44 GHz gives 163 Hz, so coherence time ≈ 0.423/f_D ≈ 2.6 ms. An RSSI report averaged over ≥ 10 ms averages several fades (use n_looks ≈ T_avg·2f_D, capped). Wideband signals (10 to 20 MHz) add frequency diversity. In practice the RSSI jitter is about **1 to 2 dB in LOS and 4 to 5 dB in NLOS**. The demo uses Rician with 8 looks.
- Ground-reflection lobing (two-ray, as included in P.528) is optional. Over a rough DSM at 2.4 GHz the Rayleigh roughness criterion `h_rms > λ/(8 sinψ)` is usually met, so coherent lobing is weak.

### 4.7 Antenna patterns and polarisation **[formulas standard; gains unverified]**
- **Receiver DF array elements:** vertical monopoles or dipoles (omni in azimuth, about 0 to 3 dBi), or sector log-periodics (about 5 to 8 dBi) **[unverified]**.
  - Vertical half-wave dipole power pattern: `G(θ) = 1.64·[cos(π/2·cosθ)/sinθ]²` (θ from zenith, 2.15 dBi at the horizon). This gives a **cone of silence** when the drone is nearly overhead: −3 dB at about 50° elevation and a null at zenith.
  - Our geometries are mostly below 5° elevation, so the effect only shows during near passes.
- **Drone antennas:** DJI uses vertical dipoles or patches in the landing legs **[unverified]**. FPV craft use linear dipoles (ELRS/Crossfire 868/915 MHz and 2.4 GHz) and RHCP for 5.8 GHz video. 2 to 3 dBi omni.
- **Polarisation mismatch between linear antennas:** `L_pol = −20·log10|cos Δψ|`, where Δψ is the angle between the two E-field directions projected on the plane normal to the LOS.
  - Compute it from the dipole axis `a` rotated by the drone's roll, pitch and yaw: `a⊥ = a − (a·u)u` and `z⊥ = z − (z·u)u`, so `cosΔψ = a⊥·z⊥ / (|a⊥||z⊥|)`. The transmit dipole gain toward u scales with `|a⊥|²`.
  - Bank 15° costs 0.3 dB, 30° 1.25 dB, 45° 3.0 dB, 60° 6.0 dB and 75° 11.7 dB. **Cap at the cross-polar discrimination (XPD) of 15 to 20 dB** because multipath depolarises **[unverified cap]**.
  - Circular to linear is a constant 3 dB, independent of roll. That is a nice FPV-video detail.
- **Airframe blockage:** add an azimuth-dependent ripple of ±3 to 6 dB (a random-phase sinusoid in the aspect angle) **[heuristic]**.

---

## 5. Receiver and direction-finding realism

### 5.1 Noise floor
`N[dBm] = −174 + 10·log10(B[Hz]) + NF`. With NF = 6 dB that gives −108 dBm (1 MHz), −98 (10 MHz), −95 (20 MHz) and −92 (40 MHz). Add external noise as `F_sys = F_a + (F_rx − 1)`, linear.
- **SDR NF:**
  - Ettus USRP B200/B210 (AD9361): typical NF **< 8 dB**, max input 0 dBm **[verified spec sheet]**.
  - A masthead LNA gives a system NF of about 2 to 4 dB **[unverified]**.
  - HackRF One without preamp is about 10 to 15 dB **[unverified]**.
  - RTL-SDR (R820T2) is about 4 to 6 dB below 1.5 GHz **[unverified]**.
- **Dynamic range:** 12-bit ADC gives about 60 to 70 dB instantaneous **[unverified]**. Strong nearby jammers or Wi-Fi can block or compress the front end.
- **Published sensitivity example:** a Ukrainian EW direction finder (DETECT GROUP SeekLevel) quotes −94 dBm **[verified via search summary]**.

### 5.2 Man-made noise: ITU-R P.372 **[verified via secondary source quoting P.372]**
`F_am = c − d·log10 f[MHz]`, valid 0.3 to 250 MHz. Upper and lower deciles for rural are +9.2 / −4.6 dB.

| Environment | c | d |
|---|---|---|
| City | 76.8 | 27.7 |
| Residential | 72.5 | 27.7 |
| Rural | 67.2 | 27.7 |
| Quiet rural | 53.6 | 28.6 |
| Galactic | 52.0 | 23.0 |

Extrapolating rural to 433 MHz gives F_am ≈ −5.8 dB, which is negligible against NF = 6 dB. So **man-made Gaussian noise only matters at VHF and low UHF. At 0.9, 2.4 and 5.8 GHz the "noise" that matters is interference** (§6). The FFI Norway measurements found real noise lower than P.372 predicts, while residential areas in the Netherlands are trending up.

### 5.3 Detection threshold and CFAR
- Energy detector, complex samples, N = B·T: `SNR_req ≈ (Q⁻¹(Pfa) − Q⁻¹(Pd))/√N`. With Pfa = 1e-6 and Pd = 0.9, N = 1e4 (1 ms at 10 MHz) gives −12.2 dB.
- Noise-power uncertainty x dB imposes an **SNR wall** `ρ − 1/ρ`, with ρ = 10^(x/10) (Tandra & Sahai 2008 **[from memory]**). x = 1 dB gives −3.3 dB and x = 0.5 dB gives −6.4 dB. Below the wall, more integration does not help.
- Sensible defaults:
  - **wideband feature or energy detector: detect when the input SNR ≥ −3 dB** (in the noise bandwidth of the emitter)
  - simple spectrum-peak CFAR on averaged periodograms: threshold ≈ `10·log10(1 + Q⁻¹(Pfa)/√N_avg)` dB above the noise estimate per bin. N_avg = 100 and Pfa = 1e-4 gives +1.4 dB, so in practice a 3 to 6 dB per-bin SNR.
  - classification confidence `= logistic((SNR − 5 dB)/2)`
- Per-detection record: t, f_c, B, RSSI dBm, SNR dB, protocol guess and confidence, bearing, σ_bearing, receiver id, and the truth link back to the emitter id (brief requirement (c)).

### 5.4 DF methods and accuracy
- **Watson-Watt** (Adcock with 4 elements plus sense): amplitude comparison, small aperture, cheap. Sensitive to multipath and polarisation. Typically 2 to 5° RMS **[unverified]**.
- **Pseudo-Doppler** (commutated circular array): 2 to 5° RMS **[unverified]**.
- **Correlative interferometer** (5 to 9 element circular array, D/λ about 0.5 to 5; measured phase vector correlated against a calibrated table). This is what R&S and CRFS sell. It is the most robust, at 1 to 3° RMS in benign sites. MUSIC and other super-resolution methods are similar with coherent multichannel SDRs.
- **Published C-UAS and DF accuracies:**
  - CRFS DFH18 (0.5 to 18 GHz) **< 2.5° RMS typical**, DFH40 < 3°, DFH500 (30 to 500 MHz) < 2.5° **[verified datasheets via search]**
  - CRFS blog: "typical 3 to 5° RMS error across the frequency range". Competitors' "1° RMS" figures are from chambers, and "a 1° RMS result from a test chamber becomes irrelevant in a multipath environment where the system could be pointing in completely the wrong direction" **[verified]**
  - Aaronia IsoLOG 3D DF "up to 1°" with SPECTRAN (vendor PR); AARTOS X9 tracking 1 to 3° **[verified as vendor claims]**
  - Dedrone RF-300 **±5° mean error**, needs ≥ 2 sensors for geolocation. RF-360 detects at 2 km normally and up to 5 km ideally **[verified product pages]**
  - DroneShield RfOne MkII: range 8 km, **no published bearing accuracy**
  - Kvertus "MS Azimuth" (Ukraine): about 15 km detection claim, **no published accuracy**
  - Hidden Level: nothing found (search budget exhausted)
- **Bearing error model (recommended):**

  ```
  σ_stat = (1/(κ·√(SNR_lin·N_snap))) rad,  κ = 2π·(D/λ)·cosθ_off  (≈π for a D/λ=0.5 pair; UCA ~ similar)
  σ_θ    = √(σ_site² + σ_stat²) (+3° if NLOS)    with σ_site = 2–3° (vendor-realistic field floor)
  bias   = per-site constant ~ N(0, 1°)  (array north-alignment / calibration), drawn once per scenario
  wild   : p_wild = 0.01 (LOS) ;  0.05 + 0.25·(1 − e^(−Ld/20)) (NLOS);  wild bearing = true + U(−90°, +90°)
           (better: bearing to a random terrain facet visible to both drone and receiver = a reflection)
  ```

  With N_snap = 100 the statistical term is 1.8° at −3 dB, 1.3° at 0 dB and 0.4° at 10 dB, so the site floor dominates above about 5 dB SNR. That is realistic. Diffraction over a single ridge roughly preserves azimuth, because the edge lies in the vertical plane of the link. NLOS harm therefore shows up as low SNR, wider σ and occasional wild bearings, not as a systematic bias.
- **Elevation and conical error** for horizontal planar arrays at high elevation is minor here.

### 5.5 TDOA as an alternative
- CRLB: `σ_τ ≥ 1/(2π·β_rms·√(2·SNR·B·T))`. For flat spectra β_rms ≈ B/√12. At B = 10 MHz and an effective SNR of 30 dB this is about 1.7 ns (0.5 m), so in practice **sync and multipath dominate**. A GPSDO gives roughly 10 to 50 ns (3 to 15 m) **[unverified]**, and White Rabbit over fibre is sub-ns.
- Needs ≥ 3 synchronised sites for 2D (≥ 4 for 3D), a raw IQ snippet exchange, wideband signals, and good GDOP. CRFS RFeye Site auto-selects the best 3 (2D) or 4 (3D) nodes; vendor statements put COTS-drone TDOA accuracy at about 5 km (one release) or about 7 km (another) from the network centre **[verified as vendor claims]**.
- **Recommendation: DF (AoA) is primary for the hackathon.** TDOA is a stretch feature and needs a third receiver.

### 5.6 End-to-end demo **[measured, `scripts/sigint_demo.py`]**
- **Track:** the drone flies from the ridge-shadowed spot to the brief's truth point at 15 m/s and 40 m AGL, 596 s.
- **Emitter:** 2.44 GHz, EIRP 20 dBm (DJI CE mode **[unverified]**), B = 10 MHz.
- **Receivers:** RX1 and RX2 with 20 m masts, G = 3 dBi, cable 2 dB, NF 6 dB, so noise is −98 dBm. Detection at SNR > −3 dB.
- **Channel:** AR(1) shadowing (3 / 6 dB, d_corr 100 m), Rician fading (K 12 / 3 dB, 8 looks). The DF model is §5.4 with σ_site = 2°.
- **RX1:** NLOS 7% of the track (about 42 s), max Ld 35.1 dB, Prx −134.6 to −68.2 dBm, **detected 95%**.
- **RX2:** NLOS 20%, max Ld 36.6 dB, **detected 75%**.
- **Fixes:** 446 two-site fixes. Median miss 433 m against a median CEP50 of 295 m. **43% of truths fall inside the reported CEP50**, because site bias, wild bearings and a poor crossing angle (the track runs along the RX1-RX2 baseline) all hurt.
- This is a realistic "the reported uncertainty is optimistic" behaviour. Either keep it (it is a feature for the analytics team) or inflate the covariance by about 1.3x.
- A geometry note for the scenario: put the two receivers so the area of interest sees crossing angles of 40 to 140°. With both receivers on an E-W line, targets near that line triangulate badly.

---

## 6. Interference and electronic warfare

### 6.1 Village Wi-Fi at 2.4 GHz
- **Emitters:** about one AP per household **[unverified]**. Central-Ukraine villages have roughly 200 to 1,000 households **[unverified]**. EIRP ≤ 20 dBm (ETSI EN 300 328, 100 mW **[unverified, from memory]**). Mostly channels 1, 6 and 11, each 20 MHz.
- **Duty cycle:**
  - beacons alone are 0.2% (12 Mbps basic rate) to about 2.3% (1 Mbps) of airtime per SSID **[verified, vendor calculator]**
  - idle networks about 1 to 5% total; evening streaming 20 to 50% **[unverified]**
- **Losses:** indoor APs at 1 to 3 m height see building entry loss plus clutter. Use P.2108 §3.2 (≈ 29 dB median at 2.44 GHz) or BEL 10 to 15 dB (P.2109 traditional buildings **[unverified]**) plus the terrain profile.
- **Equivalent emitter per village (cheap model):** `EIRP_eq = 20 + 10·log10(N_AP·duty)` dBm at the village centroid, spread over 3 channels. Bursts follow a Poisson on/off process in time.
- **Worked example:** 300 APs at 5% duty, 3 km from a mast receiver. Per AP: 20 − 109.7 (FSPL) − 25 (clutter) ≈ −115 dBm. Aggregate ≈ −103 dBm, about −108 dBm per channel. That is **below the −98 dBm floor on average, but bursts from a village 500 m away reach about −90 dBm**. This causes intermittent false alarms and raises the CFAR threshold, a subtle realism cue.

### 6.2 Barrage jammers
- **Model:** a band-limited noise source of power P_j over bandwidth B_j at a location. At each receiver channel of bandwidth B_rx, `I = P_j + G_j − 10·log10(B_j/B_rx) − L_path(j→rx) + G_rx`, using the same terrain loss engine. Add it linearly to the noise floor. If `I_total` exceeds about −20 to −10 dBm at the front end, flag blocking or compression **[unverified threshold]**.
- **Typical powers [unverified, order of magnitude]:**
  - handheld drone guns: 5 to 20 W per band (37 to 43 dBm)
  - trench, vehicle or "dome" C-UAS jammers: 10 to 100 W per band
  - GNSS jammers: tens of W at 1.2/1.5 GHz
- **Bands:** 433, 868/915 MHz (ELRS/Crossfire control), 1.2/1.5 GHz (GNSS), 2.4 GHz, 5.2 and 5.8 GHz.
- **Worked example:** 20 W (43 dBm) spread over 80 MHz at 2.4 GHz, 10 km away in LoS. In a 10 MHz channel: 43 − 9 − 120.2 (FSPL) ≈ −86 dBm. **The noise floor rises from −98 to about −86 dBm (+12 dB), so LoS detection range shrinks about 4x.** That is a good "EW on/off" demo moment.
- An own-side jammer near a receiver also desensitises it, and sweeping jammers produce time-varying floors.

### 6.3 Frequency hopping vs a scanning receiver (keep it simple)
- Receiver: instantaneous bandwidth B_ib (AD9361 class 56 MHz; newer SDRs 100 to 250 MHz **[unverified]**), a scan list of bands, and a dwell T_d per band.
- Per dwell, `P_hit = duty_emitter · min(1, B_ib/B_band)`. Over a window W, `P_int = 1 − (1 − P_hit)^(W/T_revisit)`.
- 2.4 GHz ISM (83.5 MHz) is covered by about 2 tunings and 5.8 GHz (150 MHz) by 3. ELRS and OcuSync hop or burst at hundreds of Hz **[unverified]**, so continuous emitters are intercepted with near-certainty within about 100 ms.
- **Intercept probability matters mainly for (a) receivers time-sharing many bands (433/868/915/1.2/2.4/5.8 at 10 to 50 ms dwell each) and (b) sparse bursts** (telemetry, Remote ID beacons). Emit detections only at the end of dwells. This creates realistic time gaps and timestamp jitter, which also exercises the "timestamps in sync" requirement.

---

## 7. Geolocation from ≥ 2 bearings, error ellipse, and CoT `ce`

**Geometry** (local ENU, x east and y north, bearings θ clockwise from north): sensor i sits at s_i. The bearing line has normal `n_i = (cos θ_i, −sin θ_i)`, and the constraint is `n_i·(p − s_i) = 0`.

**Weighted pseudo-linear least squares (Stansfield-type), iterated 2 to 3 times with range re-weighting:**
```
w_i = 1/(σ_i² · r_i²)                      (r_i from previous iterate; Fisher information of a bearing)
A   = Σ w_i n_i n_iᵀ ,   b = Σ w_i n_i n_iᵀ s_i ,   p̂ = A⁻¹ b
P   = A⁻¹                                   (2×2 covariance ≈ CRLB for bearings-only)
```
- With 2 sensors this is the exact intersection, and P is its covariance.
- Reject fixes, or set `ce = 9999999`, when the crossing angle is under about 10 to 15° or the condition number of A is huge.
- The ML fit (Gauss-Newton on wrapped atan2 residuals, Torrieri 1984 **[unverified ref]**) removes the **Stansfield bias** that comes from the small-angle sin(e) ≈ e approximation. Per the literature, Stansfield is close to ML and usually better than plain unweighted LS (Ji et al.; NLOS-AoA paper).
- "Brown estimator": I could not verify a standard bearing-fix estimator by that name in this session **[flag]**.

**Ellipse:** take `eig(P)`, giving λ1 ≥ λ2. Semi-axes are `a = √(λ1·k)` and `b = √(λ2·k)`, with k = 1 (1σ), 1.386 (50%), 5.991 (95%). Orientation = atan2 of the major eigenvector's (x, y) components, converted to degrees from north.

**Circular measures (exact, numeric, cheap)** **[measured]**: `P(R) = (1/(2π σ1 σ2))·∫₀^{2π} (1 − exp(−R² q(φ)/2))/q(φ) dφ`, where `q(φ) = cos²φ/σ1² + sin²φ/σ2²`. Solve by bisection (`radius_for(P, prob)` in `sigint_demo.py`).

| σ2/σ1 | CEP50 exact | 0.5887(σ1+σ2) | 39.35% radius ("circular 1σ") | √((σ1²+σ2²)/2) |
|---|---|---|---|---|
| 1.0 | 1.177 σ1 | 1.177 | 1.000 | 1.000 |
| 0.5 | 0.870 | 0.883 | 0.730 | 0.791 |
| 0.25 | 0.725 | 0.736 | 0.583 | 0.729 |
| 0.1 | 0.682 | 0.648 | 0.525 | 0.711 |

→ `0.5887(σ1+σ2)` is within 1.5% for ratios ≥ 0.25 and 5% at 0.1. RMS-style formulas overstate the 1σ radius for thin ellipses.

**CoT:** `<point lat lon hae ce le/>`. The common reading is `ce` = circular error at 1σ in metres, `le` = linear (vertical) error at 1σ, and 9999999 = unknown **[unverified: the MITRE schema PDF was 403 and the search budget ran out]**.
- **Recommendation:** set `ce` = the exact 39.35%-containment radius (equal to σ for a circular Gaussian).
- Put CEP50 and the full ellipse in `<detail>` (a custom element, e.g. `<_mw_fix semi_major_m=".." semi_minor_m=".." orient_deg=".." cep50_m=".." n_lob="2" sensors="RX1,RX2"/>`).
- For single-sensor LOB reports, either emit a line-of-bearing shape or keep the LOB in detail with `ce = 9999999`.
- `hae` needs the geoid correction (§2.1).

```python
def fix(sensors, brg_deg, sig_deg):            # sensors: (n,2) km ENU
    th, sg = np.radians(brg_deg), np.radians(sig_deg)
    N = np.stack([np.cos(th), -np.sin(th)], -1); w = 1 / sg**2
    for _ in range(3):
        A = np.einsum("i,ij,ik->jk", w, N, N); b = np.einsum("i,ij,ik,ik->j", w, N, N, sensors)
        p = np.linalg.solve(A, b); r = np.linalg.norm(p - sensors, axis=1)
        w = 1 / (sg**2 * np.maximum(r, 0.05) ** 2)
    return p, np.linalg.inv(np.einsum("i,ij,ik->jk", w, N, N))
```

---

## 8. Suggested module boundary and tests (for the build)

- `terrain.py`: COG window read (bounded GDAL HTTP timeouts and retries, fail loudly on non-finite samples), tile mosaic, `DEM.profiles()`, horizon and min-visible-AGL map, geoid offset.
- `propagation.py`: `rfcore` delta-Bullington plus FSPL, P.833 and P.2108 terminal terms, AR(1) shadowing, Rician fading, antenna and polarisation.
- `sigint.py`: receivers (noise floor, scan schedule, CFAR detection), DF (σ(SNR), site bias, wild bearings), fixes with an ellipse, and CoT emission with truth back-links.
- **Tests worth having:**
  1. bit-exact vs Py1812 on 1,000 random links (dev dependency, stub npz)
  2. reciprocity
  3. Ld monotone non-increasing with drone height on a fixed profile
  4. Ld = 0 when clearance exceeds 0.6·F1
  5. profile resolution: M ≥ d/30 m holds the p95 error under 0.6 dB
  6. a determinism test with a fixed seed
  7. the DEM fetch failure path (timeout, or a tile missing for a sea or edge area) raises a typed error with the URL and window in the message

---

## 9. Unverified or assumed items to double-check if time allows
- The CoT `ce` and `le` semantics.
- GLO-30 vertical datum (EGM2008) and the geoid value near Korsun.
- The P.2108 revision number and date (§3.3 model).
- TR 38.901 RMa LOS σ_SF values.
- The ETSI EN 300 328 20 dBm EIRP limit.
- DJI EIRP by region.
- Hop rates of ELRS and OcuSync.
- Jammer powers.
- Village AP density.
- SDR NFs other than the B210.
- Watson-Watt and pseudo-Doppler accuracies.
- GPSDO sync figures.
- The SNR-wall reference.
- A "Brown" estimator.
- Hidden Level and DroneShield DF specs (not published or not found).
- pycraf behaviour on conda-forge arm64.

## 10. References (fetched or confirmed this session unless marked)
- Copernicus DEM tile (HTTP 200 checked): https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N49_00_E031_00_DEM/Copernicus_DSM_COG_10_N49_00_E031_00_DEM.tif
- ITU-R P.526 / P.1812 / P.452 / P.528 / P.2001 / P.2108 / P.833 / P.372 / P.676 / P.838: https://www.itu.int/rec/R-REC-P.526/en (swap the number), https://www.itu.int/rec/R-REC-P.1812/en
- ITU-R SG3 digital products and validation: https://www.itu.int/en/ITU-R/study-groups/rsg3/rwp3m/Pages/digprod.aspx
- P.833-2 PDF (equations 1 to 3 and Fig. 2 read): https://itu.int/dms_pubrec/itu-r/rec/p/R-REC-P.833-2-199910-S!!PDF-E.pdf
- eeveetza ports: https://github.com/eeveetza/Py1812, https://github.com/eeveetza/Py452, https://github.com/eeveetza/Py528, https://github.com/eeveetza/Py2001, https://github.com/eeveetza/Py2108
- itmlogic: https://github.com/edwardoughton/itmlogic (PyPI `itmlogic` 1.2, MIT)
- pyitm: https://github.com/tmd224/pyitm
- pycraf: PyPI `pycraf` 2.1.0, GPLv3 (repo https://github.com/bwinkel/pycraf **[URL from memory]**)
- NTIA P.2108 wrapper: https://github.com/NTIA/p2108-python (PyPI `proplib-p2108` 1.1.0)
- itur (ITU-Rpy): PyPI `itur` 0.4.0 (repo https://github.com/inigodelportillo/ITU-Rpy **[URL from memory]**)
- Matolak & Sun AG channel, Part II (hilly): https://scholarcommons.sc.edu/elct_facpub/320. Part III (suburban): https://scholarcommons.sc.edu/elct_facpub/317
- 3GPP TR 36.777 Annex B: https://itecspec.com/3gpp/36.777/s/annex-b and https://itecspec.com/3gpp/36.777/s/b.1.2
- 3GPP TR 38.901 §7.5: https://itecspec.com/3gpp/38.901/s/7.5
- Gudmundson 1991 correlation model (form confirmed via secondary sources): Electronics Letters 27(23):2145-2146
- P.372 man-made noise constants (secondary): https://arxiv.org/pdf/2609.05811. FFI measurements: https://www.ffi.no/en/publications-archive/external-man-made-radio-noise-measurements
- CRFS DF RMS blog: https://www.crfs.com/blog/direction-finding-rms-error. DFH18: https://www.crfs.com/hubfs/CR-006335-DS%20DFH18.pdf. DFH40: https://www.crfs.com/hubfs/CR-006336-DS%20DFH40.pdf. RFeye Site TDOA release: https://crfs.com/blog/new-rfeye-site-release-improvements-for-enhanced-drone-detection
- Aaronia (vendor PR, "up to 1°"): https://www.everythingrf.com/news/details/21208-aaronia-showcases-advanced-spectrum-monitoring-and-drone-detection-technology-at-aoc-2025. X9 1 to 3°: https://www.cbinsights.com/company/aaronia-ag
- Dedrone RF-300 ±5°: https://www.dedrone.com/products/drone-detection/rf-sensors/rf-300. RF-360: https://www.dedrone.com/products/hardware/rf-sensors/rf-360
- DroneShield RfOne MkII: https://www.securityinfowatch.com/perimeter-security/robotics/anti-drone-technologies/product/21148504/droneshield-droneshields-rfone-mkii-drone-detection-solution
- Kvertus MS Azimuth: https://en.defence-ua.com/weapon_and_tech/ukrainians_created_ms_azimuth_system_to_notice_drones_beyond_the_field_of_view_capabilities_breakdown-8561.html
- Ettus B200/B210 spec sheet: https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/7161/b200_b210_spec_sheet-3236990.pdf
- Wi-Fi beacon airtime: https://www.purple.ai/en-us/wifitools/beacon-overhead-calculator and https://en.wikipedia.org/wiki/Beacon_frame
- Bearing-only bias (Stansfield / Gavish-Weiss context): https://openresearch-repository.anu.edu.au/bitstream/1885/53760/2/01_Ji_Bias-Correction_In_2009.pdf. NLOS AoA: https://isif.org/media/294

## Appendix: spike scripts
All live in `scratch/rf-spike/scripts/`:

| Script | What it does |
|---|---|
| `dem_fetch.py` | COG window read |
| `rfcore.py` | the model |
| `find_ridge.py` | receiver siting plus the min-visible-AGL map |
| `compare.py` | ridge sweep vs Py1812 and ITM, plus timings |
| `bench.py` | random-link validation plus throughput |
| `m_sensitivity.py` | profile resolution |
| `extras_check.py` | reciprocity plus P.2108 values |
| `atten_check.py` | itur gas and rain |
| `sigint_demo.py` | end-to-end detections, bearings, fixes and CEP |
| `pycraf_test.py` | the failed import |

Third-party clones are under `rf-spike/ext/` (untrusted data, imported only via explicit `sys.path` in `-I` mode).
