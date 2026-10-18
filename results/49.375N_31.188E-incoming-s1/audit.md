# Audit — 49.375N_31.188E-incoming-s1

Independent checks: geometry from `truth/tracks.csv` + `sensors/*/site.json` and the real DEM
(`World.los`), causality and statistics. The answer key's derived columns are never trusted.

| id | check | status | value | threshold | detail |
|---|---|---|---|---|---|
| provenance | Provenance | PASS | 0 | 0 issues | clean |
| clock | Clock sync | PASS | 0 | 0 problems; abs(time_utc − (start+t)) ≤ 1 ms | 21698 rows, max \|time_utc − (start+t)\| = 0.438 ms |
| bearing_geometry | Bearing geometry | PASS | 0.9472 | ≥ 0.85 of LOS within 2σ | RF-01: bias +0.13°, within 2σ 0.951 (n=853, n_los=853); RF-02: bias +0.83°, within 2σ 0.954 (n=411, n_los=411); RF-03: bias -0.81°, within 2σ 0.947 (n=852, n_los=852) |
| terrain_shadow | Terrain shadow | SKIP | — | ≥ 10 dB | no sensor with ≥ 20 LOS and ≥ 20 NLOS detections with power + geometry |
| occlusion_gaps | Occlusion gaps | SKIP | — | < 0.5 | no sensor/drone pair with NLOS intervals ≥ 30 s |
| fix_calibration | Fix calibration | PASS | 0.4943 | share(error < cep50_m) in [0.35, 0.65] | n=435, median error 192 m, median cep50 184 m |
| range_law | Range law | PASS | 3.046 | path-loss exponent in [1.5, 4.5] (free space 2) | RF-01: exponent 3.05 (n=853); RF-02: exponent 1.91 (n=411); RF-03: exponent 2.49 (n=852) |
| acoustic_delay | Acoustic delay | PASS | 0.0176 | max \|Δdelay\|/delay ≤ 2%, no arrival before emission | max relative delay error 1.76%, 0 causality violations |
| spoof_visible | Spoof visibility | SKIP | — | large error only inside spoof windows | no GNSS spoofing in scenario |
| cross_sensor_time | Cross-sensor time | PASS | 1 | every frame within 5 s of a fix | 605 frames, 0 without a fix within 5 s |

**7 pass, 0 fail, 3 skip.**
