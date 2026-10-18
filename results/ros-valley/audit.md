# Audit — ros-valley

Independent checks: geometry from `truth/tracks.csv` + `sensors/*/site.json` and the real DEM
(`World.los`), causality and statistics. The answer key's derived columns are never trusted.

| id | check | status | value | threshold | detail |
|---|---|---|---|---|---|
| provenance | Provenance | PASS | 0 | 0 issues | clean |
| clock | Clock sync | PASS | 0 | 0 problems; abs(time_utc − (start+t)) ≤ 1 ms | 249206 rows, max \|time_utc − (start+t)\| = 0.499 ms |
| bearing_geometry | Bearing geometry | PASS | 0.948 | ≥ 0.85 of LOS within 2σ | RF1: bias +0.84°, within 2σ 0.959 (n=1716, n_los=1712); RF2: bias -0.59°, within 2σ 0.948 (n=1000, n_los=1000) |
| terrain_shadow | Terrain shadow | SKIP | — | ≥ 10 dB | no sensor with ≥ 20 LOS and ≥ 20 NLOS detections with power + geometry |
| occlusion_gaps | Occlusion gaps | PASS | 0 | rate_in / rate_out < 0.5 | RF1/fpv_fiber_1: 1 interval(s) 36s, 0 det in vs 0 out, ratio n/a; RF2/mavic_1: 1 interval(s) 336s, 0 det in vs 8 out, ratio 0.000 |
| fix_calibration | Fix calibration | PASS | 0.5254 | share(error < cep50_m) in [0.35, 0.65] | n=236, median error 319 m, median cep50 334 m |
| range_law | Range law | PASS | 4.154 | path-loss exponent in [1.5, 4.5] (free space 2) | RF1: exponent 1.89 (n=1712); RF2: exponent 4.15 (n=1000) |
| acoustic_delay | Acoustic delay | PASS | 0.0017 | max \|Δdelay\|/delay ≤ 2%, no arrival before emission | max relative delay error 0.17%, 0 causality violations |
| spoof_visible | Spoof visibility | PASS | — | error grows ≥3× and ≥50 m inside spoof windows (informational) | recon_1: median error 2 m outside vs 245 m inside spoof window |
| cross_sensor_time | Cross-sensor time | PASS | 1 | every frame within 5 s of a fix | 1603 frames, 0 without a fix within 5 s |

**9 pass, 0 fail, 1 skip.**

## OASIS vs one-shot LLM

One-shot baseline: `baselines/oneshot/out/ros-valley-oneshot` (same window, same layout, one LLM call).

| check | OASIS | one-shot LLM |
|---|---|---|
| Provenance | PASS (0) | PASS (0) |
| Clock sync | PASS (0) | FAIL (2) |
| Bearing geometry | PASS (0.948) | FAIL (0) |
| Terrain shadow | SKIP (—) | SKIP (—) |
| Occlusion gaps | PASS (0) | SKIP (—) |
| Fix calibration | PASS (0.5254) | FAIL (1) |
| Range law | PASS (4.154) | SKIP (—) |
| Acoustic delay | PASS (0.0017) | SKIP (—) |
| Spoof visibility | PASS (—) | SKIP (—) |
| Cross-sensor time | PASS (1) | SKIP (—) |

OASIS: 9 pass / 0 fail / 1 skip. One-shot LLM: 1 pass / 3 fail / 6 skip.
