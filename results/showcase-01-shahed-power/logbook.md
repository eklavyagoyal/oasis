# Log book: 01-shahed-power

49.3754° N · 31.1882° E · 10 km square · 04 Nov 2026 14:01:00 UTC · 20 min · seed 101

Weather: wind from 300° at 5.7 m/s, 2 °C, visibility 9.6 km.

## Cast

| id | type | side | where |
|---|---|---|---|
| SITE-01 | power_station | friendly | 49.4177° N · 31.2239° E |
| ADT-01 | ad_team | friendly | 49.4042° N · 31.2108° E |
| ADB-01 | ad_battery | friendly | 49.4050° N · 31.2160° E |
| shahed_1 | shahed136 | hostile | moves: 4 waypoints |
| shahed_2 | shahed136 | hostile | moves: 5 waypoints |
| shahed_3 | shahed136 | hostile | moves: 4 waypoints |
| INT-01 | jedi | friendly | moves: 2 waypoints |
| op_INT-01 | operator | friendly | 49.4020° N · 31.2095° E |

**Sensors:** RF-01 (rf_df), RF-02 (rf_df), RADAR-01 (radar), CAM-01 (camera), C2-01 (c2)

## Timeline

TRUTH is what happened. SENSOR is the first record each sensor made of each object. C2 is what the command post concluded from sensor data alone (6 routine new-track notices are left out).

| UTC | T+ | voice | event |
|---|---|---|---|
| 14:03:18 |   138.5 s | TRUTH | **shahed_3** (shahed136, hostile) airborne |
| 14:03:19 |   139.0 s | SENSOR | RADAR-01 first records **shahed_3** (33 records in all) |
| 14:03:25 |   145.0 s | SENSOR | RF-01 first records **shahed_3** (9 records in all) |
| 14:03:26 |   146.0 s | SENSOR | RF-02 first records **shahed_3** (3 records in all) |
| 14:03:40 |   160.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000000 at 2986 m |
| 14:03:40 |   160.0 s | C2 | ADT-01 → alerted (first warn alert ALT-000001) |
| 14:03:40 |   160.0 s | C2 | ADT-01 → responding (dispatched on ALT-000001) |
| 14:03:40 |   160.0 s | C2 | ADB-01 → alerted (first warn alert ALT-000001) |
| 14:03:40 |   160.0 s | C2 | ADB-01 → responding (dispatched on ALT-000001) |
| 14:04:56 |   236.0 s | TRUTH | **shahed_3** reaches SITE-01 (26.2 m) |
| 14:05:16 |   256.0 s | C2 | WARN: LOST CONTACT TRK-000000: no update for 60 s |
| 14:10:28 |   568.0 s | TRUTH | **shahed_1** (shahed136, hostile) airborne |
| 14:10:36 |   576.0 s | SENSOR | RADAR-01 first records **shahed_1** (112 records in all) |
| 14:10:43 |   583.0 s | SENSOR | RF-01 first records **shahed_1** (4 records in all) |
| 14:10:46 |   586.0 s | SENSOR | RF-02 first records **shahed_1** (9 records in all) |
| 14:12:22 |   682.0 s | SENSOR | RF-01 first records **INT-01** (46 records in all) |
| 14:12:22 |   682.0 s | SENSOR | RF-01 first records **op_INT-01** (46 records in all) |
| 14:12:22 |   682.0 s | TRUTH | **INT-01** (jedi, friendly) airborne |
| 14:12:23 |   683.0 s | SENSOR | RF-02 first records **INT-01** (30 records in all) |
| 14:12:24 |   684.0 s | SENSOR | RADAR-01 first records **INT-01** (3 records in all) |
| 14:12:24 |   684.5 s | TRUTH | **shahed_2** (shahed136, hostile) airborne |
| 14:12:27 |   687.0 s | SENSOR | RADAR-01 first records **shahed_2** (58 records in all) |
| 14:12:27 |   687.0 s | SENSOR | RF-01 first records **shahed_2** (5 records in all) |
| 14:12:39 |   699.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000003 at 2326 m |
| 14:12:41 |   701.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000004 at 2096 m |
| 14:12:43 |   703.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000005 at 2830 m |
| 14:12:53 |   713.0 s | SENSOR | RF-02 first records **shahed_2** (5 records in all) |
| 14:12:56 |   716.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000002 at 2805 m |
| 14:13:07 |   727.0 s | TRUTH | **shahed_1** track ends |
| 14:13:07 |   727.0 s | TRUTH | **INT-01** track ends |
| 14:13:42 |   762.0 s | C2 | CRITICAL: CLOSE TO SITE-01: TRK-000002 at 970 m |
| 14:13:42 |   762.0 s | C2 | SITE-01 → approached (confirmed track TRK-000002 within 970 m) |
| 14:13:56 |   776.0 s | C2 | WARN: LOST CONTACT TRK-000004: no update for 60 s |
| 14:14:01 |   781.5 s | TRUTH | **shahed_2** reaches SITE-01 (18.3 m) |
| 14:14:05 |   785.0 s | C2 | WARN: SENSOR SILENT CAM-01: no detections since 2026-11-04T14:13:05.000Z (RADAR-01, RF-01, RF-02 still reporting) |
| 14:14:09 |   789.0 s | C2 | WARN: LOST CONTACT TRK-000001: no update for 60 s |
| 14:15:00 |   840.0 s | C2 | WARN: LOST CONTACT TRK-000002: no update for 60 s |
| 14:20:59 |  1199.5 s | C2 | ADT-01 → no contact (no C2 track within 500 m at its end) |
| 14:20:59 |  1199.5 s | C2 | ADB-01 → no contact (no C2 track within 500 m at its end) |

## Outcome per hostile

| hostile | airborne | first sensor record | first C2 alert | truth outcome |
|---|---|---|---|---|
| shahed_1 | 14:10:28 | 14:10:36 (+8 s) | none | not reached |
| shahed_2 | 14:12:24 | 14:12:27 (+2 s) | none | reached |
| shahed_3 | 14:03:18 | 14:03:19 (+0 s) | none | reached |

## Audit (independent physics checks)

**4 pass · 3 fail · 3 skip**

| check | status | value |
|---|---|---|
| Provenance | PASS | 0 |
| Clock sync | PASS | 0 |
| Bearing geometry | PASS | 0.9362 |
| Terrain shadow | FAIL | 9.58 |
| Occlusion gaps | SKIP | — |
| Fix calibration | FAIL | 0.9 |
| Range law | FAIL | 0.317 |
| Acoustic delay | SKIP | — |
| Spoof visibility | SKIP | — |
| Cross-sensor time | PASS | 1.0 |
