# Audit — 49.375N_31.188E-saturation-s1

Independent checks: geometry from `truth/tracks.csv` + `sensors/*/site.json` and the real DEM
(`World.los`), causality and statistics. The answer key's derived columns are never trusted.

| id | check | status | value | threshold | detail |
|---|---|---|---|---|---|
| provenance | Provenance | PASS | 0 | 0 issues | clean |
| clock | Clock sync | PASS | 0 | 0 problems; abs(time_utc − (start+t)) ≤ 1 ms | 20941 rows, max \|time_utc − (start+t)\| = 0.457 ms |
| bearing_geometry | Bearing geometry | PASS | 0.9207 | ≥ 0.85 of LOS within 2σ | RF-01: bias +0.29°, within 2σ 0.944 (n=886, n_los=712); RF-02: bias +1.15°, within 2σ 0.921 (n=164, n_los=164); RF-03: bias -0.93°, within 2σ 0.956 (n=914, n_los=914) |
| terrain_shadow | Terrain shadow | PASS | 19.32 | NLOS − LOS median excess ≥ 10 dB | RF-01: excess LOS -5.7 dB (n=712) vs NLOS 13.6 dB (n=174), Δ=19.3 dB |
| occlusion_gaps | Occlusion gaps | SKIP | — | < 0.5 | no sensor/drone pair with NLOS intervals ≥ 30 s |
| fix_calibration | Fix calibration | PASS | 0.5637 | share(error < cep50_m) in [0.35, 0.65] | n=204, median error 229 m, median cep50 257 m |
| range_law | Range law | FAIL | 0.261 | path-loss exponent in [1.5, 4.5] (free space 2) | RF-01: exponent 0.26 (n=712); RF-02: exponent 3.03 (n=164); RF-03: exponent 1.30 (n=914) |
| acoustic_delay | Acoustic delay | FAIL | 0.0235 | max \|Δdelay\|/delay ≤ 2%, no arrival before emission | max relative delay error 2.35%, 0 causality violations |
| spoof_visible | Spoof visibility | SKIP | — | large error only inside spoof windows | no GNSS spoofing in scenario |
| cross_sensor_time | Cross-sensor time | PASS | 1 | every frame within 5 s of a fix | 527 frames, 0 without a fix within 5 s |

**6 pass, 2 fail, 2 skip.**
