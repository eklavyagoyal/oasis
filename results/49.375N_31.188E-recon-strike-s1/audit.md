# Audit — 49.375N_31.188E-recon-strike-s1

Independent checks: geometry from `truth/tracks.csv` + `sensors/*/site.json` and the real DEM
(`World.los`), causality and statistics. The answer key's derived columns are never trusted.

| id | check | status | value | threshold | detail |
|---|---|---|---|---|---|
| provenance | Provenance | PASS | 0 | 0 issues | clean |
| clock | Clock sync | PASS | 0 | 0 problems; abs(time_utc − (start+t)) ≤ 1 ms | 21870 rows, max \|time_utc − (start+t)\| = 0.431 ms |
| bearing_geometry | Bearing geometry | PASS | 0.9498 | ≥ 0.85 of LOS within 2σ | RF-01: bias -0.03°, within 2σ 0.951 (n=1146, n_los=1146); RF-02: bias +0.72°, within 2σ 0.950 (n=662, n_los=658); RF-03: bias -0.72°, within 2σ 0.956 (n=1132, n_los=1132) |
| terrain_shadow | Terrain shadow | SKIP | — | ≥ 10 dB | no sensor with ≥ 20 LOS and ≥ 20 NLOS detections with power + geometry |
| occlusion_gaps | Occlusion gaps | SKIP | — | < 0.5 | no sensor/drone pair with NLOS intervals ≥ 30 s |
| fix_calibration | Fix calibration | PASS | 0.4866 | share(error < cep50_m) in [0.35, 0.65] | n=707, median error 213 m, median cep50 212 m |
| range_law | Range law | PASS | 2.696 | path-loss exponent in [1.5, 4.5] (free space 2) | RF-01: exponent 2.70 (n=1146); RF-02: exponent 2.13 (n=658); RF-03: exponent 1.61 (n=1132) |
| acoustic_delay | Acoustic delay | PASS | 0.0059 | max \|Δdelay\|/delay ≤ 2%, no arrival before emission | max relative delay error 0.59%, 0 causality violations |
| spoof_visible | Spoof visibility | SKIP | — | large error only inside spoof windows | no GNSS spoofing in scenario |
| cross_sensor_time | Cross-sensor time | PASS | 1 | every frame within 5 s of a fix | 609 frames, 0 without a fix within 5 s |

**7 pass, 0 fail, 3 skip.**
