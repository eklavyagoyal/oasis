# Log book: 03-recon-power

49.3754° N · 31.1882° E · 10 km square · 04 Nov 2026 14:01:00 UTC · 20 min · seed 301

Weather: wind from 7° at 1.6 m/s, 4 °C, visibility 19.5 km.

## Cast

| id | type | side | where |
|---|---|---|---|
| SITE-01 | power_station | friendly | 49.4003° N · 31.2499° E |
| ADT-01 | ad_team | friendly | 49.3962° N · 31.2373° E |
| ADB-01 | ad_battery | friendly | 49.3857° N · 31.2531° E |
| shahed_1 | shahed136 | hostile | moves: 5 waypoints |
| shahed_2 | shahed136 | hostile | moves: 4 waypoints |
| orlan_1 | orlan10 | hostile | moves: 7 waypoints |
| orlan_2 | orlan10 | hostile | moves: 7 waypoints |
| INT-01 | interceptor | friendly | moves: 2 waypoints |
| op_INT-01 | operator | friendly | 49.3936° N · 31.2414° E |

**Sensors:** RF-01 (rf_df), RF-02 (rf_df), RADAR-01 (radar), CAM-01 (camera), C2-01 (c2)

## Timeline

TRUTH is what happened. SENSOR is the first record each sensor made of each object. C2 is what the command post concluded from sensor data alone (15 routine new-track notices are left out).

| UTC | T+ | voice | event |
|---|---|---|---|
| 14:06:57 |   357.5 s | TRUTH | **orlan_1** (orlan10, hostile) airborne |
| 14:06:58 |   358.0 s | SENSOR | RF-01 first records **orlan_1** (740 records in all) |
| 14:06:58 |   358.0 s | SENSOR | RF-02 first records **orlan_1** (745 records in all) |
| 14:07:06 |   366.0 s | SENSOR | RADAR-01 first records **orlan_1** (499 records in all) |
| 14:08:23 |   443.0 s | TRUTH | **shahed_2** (shahed136, hostile) airborne |
| 14:08:24 |   444.0 s | SENSOR | RF-02 first records **shahed_2** (11 records in all) |
| 14:08:30 |   450.0 s | SENSOR | RADAR-01 first records **shahed_2** (150 records in all) |
| 14:08:42 |   462.0 s | SENSOR | RF-01 first records **shahed_2** (12 records in all) |
| 14:09:41 |   521.0 s | C2 | WARN: LOST CONTACT TRK-000000: no update for 60 s |
| 14:09:41 |   521.0 s | C2 | ADT-01 → alerted (first warn alert ALT-000003) |
| 14:09:41 |   521.0 s | C2 | ADT-01 → responding (dispatched on ALT-000003) |
| 14:09:41 |   521.0 s | C2 | ADB-01 → alerted (first warn alert ALT-000003) |
| 14:09:41 |   521.0 s | C2 | ADB-01 → responding (dispatched on ALT-000003) |
| 14:09:41 |   521.0 s | C2 | INT-01 → alerted (first warn alert ALT-000003) |
| 14:10:28 |   568.5 s | TRUTH | **orlan_2** (orlan10, hostile) airborne |
| 14:10:29 |   569.0 s | SENSOR | RF-02 first records **orlan_2** (453 records in all) |
| 14:10:29 |   569.0 s | SENSOR | RADAR-01 first records **orlan_2** (318 records in all) |
| 14:10:30 |   570.0 s | SENSOR | RF-01 first records **orlan_2** (445 records in all) |
| 14:10:59 |   599.0 s | SENSOR | RF-01 first records **shahed_1** (7 records in all) |
| 14:10:59 |   599.0 s | TRUTH | **shahed_1** (shahed136, hostile) airborne |
| 14:11:00 |   600.0 s | SENSOR | RADAR-01 first records **shahed_1** (38 records in all) |
| 14:11:03 |   603.0 s | SENSOR | RF-02 first records **shahed_1** (9 records in all) |
| 14:11:13 |   613.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000003 at 2995 m |
| 14:11:23 |   623.0 s | C2 | WARN: LOST CONTACT TRK-000002: no update for 60 s |
| 14:11:55 |   655.0 s | C2 | CRITICAL: CLOSE TO SITE-01: TRK-000003 at 961 m |
| 14:11:55 |   655.0 s | C2 | SITE-01 → approached (confirmed track TRK-000003 within 961 m) |
| 14:12:00 |   660.3 s | C2 | INT-01 → available (asset on hand) |
| 14:12:00 |   660.3 s | C2 | INT-01 → responding (launched by C2) |
| 14:12:00 |   660.5 s | TRUTH | **INT-01** (interceptor, friendly) airborne |
| 14:12:01 |   661.0 s | SENSOR | RF-01 first records **INT-01** (35 records in all) |
| 14:12:01 |   661.0 s | SENSOR | RF-01 first records **op_INT-01** (35 records in all) |
| 14:12:03 |   663.0 s | SENSOR | RADAR-01 first records **INT-01** (1 records in all) |
| 14:12:04 |   664.0 s | SENSOR | RF-02 first records **INT-01** (21 records in all) |
| 14:12:13 |   673.0 s | C2 | WARN: LOST CONTACT TRK-000004: no update for 60 s |
| 14:12:15 |   675.0 s | TRUTH | **shahed_2** reaches SITE-01 (1.3 m) |
| 14:12:23 |   683.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000007 at 2246 m |
| 14:12:23 |   683.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000001 at 2977 m |
| 14:12:25 |   685.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000008 at 2230 m |
| 14:12:31 |   691.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000006 at 2966 m |
| 14:12:35 |   695.0 s | TRUTH | **shahed_1** intercepted (closest approach to SITE-01: 2695.5 m) |
| 14:12:35 |   695.0 s | TRUTH | **INT-01** at the rendezvous point |
| 14:12:35 |   695.3 s | C2 | INT-01 → no contact (no C2 track within 500 m at its end) |
| 14:13:19 |   739.0 s | C2 | WARN: LOST CONTACT TRK-000003: no update for 60 s |
| 14:13:34 |   754.0 s | C2 | WARN: LOST CONTACT TRK-000008: no update for 60 s |
| 14:13:35 |   755.0 s | C2 | WARN: LOST CONTACT TRK-000006: no update for 60 s |
| 14:14:48 |   828.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000005 at 2975 m |
| 14:15:56 |   896.0 s | C2 | CRITICAL: CLOSE TO SITE-01: TRK-000005 at 1000 m |
| 14:18:02 |  1022.0 s | TRUTH | **orlan_2** track ends |
| 14:18:03 |  1023.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000009 at 251 m |
| 14:18:03 |  1023.0 s | C2 | CRITICAL: CLOSE TO SITE-01: TRK-000009 at 251 m |
| 14:18:04 |  1024.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000010 at 2703 m |
| 14:18:12 |  1032.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000011 at 2022 m |
| 14:18:21 |  1041.0 s | SENSOR | CAM-01 first records **orlan_1** (6 records in all) |
| 14:18:59 |  1079.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000012 at 2794 m |
| 14:19:07 |  1087.0 s | C2 | WARN: LOST CONTACT TRK-000005: no update for 60 s |
| 14:19:14 |  1094.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000013 at 2268 m |
| 14:19:20 |  1100.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000014 at 2944 m |
| 14:19:22 |  1102.0 s | C2 | WARN: LOST CONTACT TRK-000009: no update for 60 s |
| 14:19:22 |  1102.0 s | TRUTH | **orlan_1** track ends |
| 14:19:30 |  1110.0 s | C2 | WARN: LOST CONTACT TRK-000011: no update for 60 s |
| 14:19:37 |  1117.0 s | C2 | WARN: LOST CONTACT TRK-000010: no update for 60 s |
| 14:20:19 |  1159.0 s | C2 | WARN: LOST CONTACT TRK-000001: no update for 60 s |
| 14:20:22 |  1162.0 s | C2 | WARN: SENSOR SILENT RF-01: no detections since 2026-11-04T14:19:22.000Z (CAM-01, RADAR-01 still reporting) |
| 14:20:25 |  1165.0 s | C2 | WARN: SENSOR SILENT CAM-01: no detections since 2026-11-04T14:19:25.000Z (RADAR-01 still reporting) |
| 14:20:59 |  1199.5 s | C2 | ADT-01 → no contact (no C2 track within 500 m at its end) |
| 14:20:59 |  1199.5 s | C2 | ADB-01 → no contact (no C2 track within 500 m at its end) |

## Outcome per hostile

| hostile | airborne | first sensor record | first C2 alert | truth outcome |
|---|---|---|---|---|
| shahed_1 | 14:10:59 | 14:10:59 (+0 s) | 14:11:03 (+4 s) | intercepted |
| shahed_2 | 14:08:23 | 14:08:24 (+1 s) | none | reached |
| orlan_1 | 14:06:57 | 14:06:58 (+0 s) | 14:06:58 (+0 s) | not reached |
| orlan_2 | 14:10:28 | 14:10:29 (+0 s) | none | approached |

## Audit (independent physics checks)

**7 pass · 0 fail · 3 skip**

| check | status | value |
|---|---|---|
| Provenance | PASS | 0 |
| Clock sync | PASS | 0 |
| Bearing geometry | PASS | 0.9524 |
| Terrain shadow | PASS | 22.07 |
| Occlusion gaps | SKIP | — |
| Fix calibration | PASS | 0.5756 |
| Range law | PASS | 2.195 |
| Acoustic delay | SKIP | — |
| Spoof visibility | SKIP | — |
| Cross-sensor time | PASS | 1.0 |
