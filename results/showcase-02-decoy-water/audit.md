# Audit — 02-decoy-water

Independent checks: geometry from `truth/tracks.csv` + `sensors/*/site.json` and the real DEM
(`World.los`), causality and statistics. The answer key's derived columns are never trusted.

| id | check | status | value | threshold | detail |
|---|---|---|---|---|---|
| provenance | Provenance | PASS | 0 | 0 issues | clean |
| clock | Clock sync | PASS | 0 | 0 problems; abs(time_utc − (start+t)) ≤ 1 ms | 9277 rows, max \|time_utc − (start+t)\| = 0.441 ms |
| bearing_geometry | Bearing geometry | PASS | 0.9655 | ≥ 0.85 of LOS within 2σ | RF-01: bias -0.22°, within 2σ 1.000 (n=48, n_los=39); RF-02: bias -1.86°, within 2σ 0.966 (n=29, n_los=29) |
| terrain_shadow | Terrain shadow | SKIP | — | ≥ 10 dB | no sensor with ≥ 20 LOS and ≥ 20 NLOS detections with power + geometry |
| occlusion_gaps | Occlusion gaps | SKIP | — | < 0.5 | no sensor/drone pair with NLOS intervals ≥ 30 s |
| fix_calibration | Fix calibration | FAIL | 0 | share(error < cep50_m) in [0.35, 0.65] | n=3, median error 1284 m, median cep50 912 m |
| range_law | Range law | PASS | 2.228 | path-loss exponent in [1.5, 4.5] (free space 2) | RF-01: exponent 2.23 (n=39) |
| acoustic_delay | Acoustic delay | SKIP | — | ≤ 2% | no microphone in scenario |
| spoof_visible | Spoof visibility | SKIP | — | large error only inside spoof windows | no remote_id/telemetry in scenario |
| cross_sensor_time | Cross-sensor time | PASS | 1 | every frame within 5 s of a fix | 15 frames, 0 without a fix within 5 s |

**5 pass, 1 fail, 4 skip.**
