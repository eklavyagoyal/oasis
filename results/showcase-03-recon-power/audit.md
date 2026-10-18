# Audit — 03-recon-power

Independent checks: geometry from `truth/tracks.csv` + `sensors/*/site.json` and the real DEM
(`World.los`), causality and statistics. The answer key's derived columns are never trusted.

| id | check | status | value | threshold | detail |
|---|---|---|---|---|---|
| provenance | Provenance | PASS | 0 | 0 issues | clean |
| clock | Clock sync | PASS | 0 | 0 problems; abs(time_utc − (start+t)) ≤ 1 ms | 17796 rows, max \|time_utc − (start+t)\| = 0.480 ms |
| bearing_geometry | Bearing geometry | PASS | 0.9524 | ≥ 0.85 of LOS within 2σ | RF-01: bias +0.04°, within 2σ 0.952 (n=1274, n_los=1239); RF-02: bias -0.29°, within 2σ 0.956 (n=1239, n_los=1239) |
| terrain_shadow | Terrain shadow | PASS | 22.07 | NLOS − LOS median excess ≥ 10 dB | RF-01: excess LOS -3.2 dB (n=1239) vs NLOS 18.8 dB (n=35), Δ=22.1 dB |
| occlusion_gaps | Occlusion gaps | SKIP | — | < 0.5 | no sensor/drone pair with NLOS intervals ≥ 30 s |
| fix_calibration | Fix calibration | PASS | 0.5756 | share(error < cep50_m) in [0.35, 0.65] | n=238, median error 220 m, median cep50 223 m |
| range_law | Range law | PASS | 2.195 | path-loss exponent in [1.5, 4.5] (free space 2) | RF-01: exponent 2.20 (n=1239); RF-02: exponent 1.93 (n=1239) |
| acoustic_delay | Acoustic delay | SKIP | — | ≤ 2% | no microphone in scenario |
| spoof_visible | Spoof visibility | SKIP | — | large error only inside spoof windows | no remote_id/telemetry in scenario |
| cross_sensor_time | Cross-sensor time | PASS | 1 | every frame within 5 s of a fix | 306 frames, 0 without a fix within 5 s |

**7 pass, 0 fail, 3 skip.**
