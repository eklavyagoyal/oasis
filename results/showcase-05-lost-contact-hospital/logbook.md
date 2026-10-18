# Log book: 05-lost-contact-hospital

49.3754° N · 31.1882° E · 10 km square · 04 Nov 2026 14:01:00 UTC · 20 min · seed 505

Weather: wind from 219° at 3.8 m/s, 5 °C, visibility 14.1 km.

## Cast

| id | type | side | where |
|---|---|---|---|
| SITE-01 | hospital | friendly | 49.3982° N · 31.2531° E |
| ADT-01 | ad_team | friendly | 49.4019° N · 31.2301° E |
| ADB-01 | ad_battery | friendly | 49.4057° N · 31.2341° E |
| mavic_1 | dji_mavic3 | hostile | moves: 9 waypoints |
| op_mavic_1 | operator | hostile | 49.3666° N · 31.1279° E |
| fiber_1 | fpv_fiber | hostile | moves: 4 waypoints |
| jammer_1 | jammer | friendly | 49.3655° N · 31.1274° E |
| INT-MISS | jedi | friendly | moves: 2 waypoints |

**Sensors:** RF-01 (rf_df), RF-02 (rf_df), RF-03 (rf_df), RADAR-01 (radar), CAM-01 (camera), RID-01 (remote_id), C2-01 (c2)

## Timeline

TRUTH is what happened. SENSOR is the first record each sensor made of each object. C2 is what the command post concluded from sensor data alone (48 routine new-track notices are left out).

| UTC | T+ | voice | event |
|---|---|---|---|
| 14:01:45 |    45.0 s | SENSOR | RF-01 first records **mavic_1** (1,086 records in all) |
| 14:01:45 |    45.0 s | SENSOR | RF-01 first records **op_mavic_1** (945 records in all) |
| 14:01:45 |    45.0 s | SENSOR | RF-02 first records **mavic_1** (864 records in all) |
| 14:01:45 |    45.0 s | SENSOR | RF-02 first records **op_mavic_1** (946 records in all) |
| 14:01:45 |    45.0 s | SENSOR | RF-03 first records **mavic_1** (1,123 records in all) |
| 14:01:45 |    45.0 s | TRUTH | **mavic_1** (dji_mavic3, hostile) airborne |
| 14:01:45 |    45.0 s | SENSOR | RID-01 first records **mavic_1** (997 records in all) |
| 14:03:07 |   127.0 s | C2 | WARN: LOST CONTACT TRK-000001: no update for 60 s |
| 14:03:07 |   127.0 s | C2 | ADT-01 → alerted (first warn alert ALT-000006) |
| 14:03:07 |   127.0 s | C2 | ADT-01 → responding (dispatched on ALT-000006) |
| 14:03:07 |   127.0 s | C2 | ADB-01 → alerted (first warn alert ALT-000006) |
| 14:03:07 |   127.0 s | C2 | ADB-01 → responding (dispatched on ALT-000006) |
| 14:03:20 |   140.0 s | C2 | WARN: LOST CONTACT TRK-000000: no update for 60 s |
| 14:03:55 |   175.0 s | C2 | WARN: LOST CONTACT TRK-000004: no update for 60 s |
| 14:04:42 |   222.0 s | C2 | WARN: LOST CONTACT TRK-000002: no update for 60 s |
| 14:05:09 |   249.0 s | SENSOR | RADAR-01 first records **mavic_1** (62 records in all) |
| 14:05:18 |   258.0 s | C2 | WARN: LOST CONTACT TRK-000005: no update for 60 s |
| 14:05:42 |   282.0 s | C2 | WARN: LOST CONTACT TRK-000008: no update for 60 s |
| 14:05:45 |   285.0 s | C2 | WARN: LOST CONTACT TRK-000007: no update for 60 s |
| 14:07:34 |   394.0 s | C2 | WARN: LOST CONTACT TRK-000011: no update for 60 s |
| 14:07:42 |   402.0 s | TRUTH | **fiber_1** (fpv_fiber, hostile) airborne |
| 14:07:56 |   416.0 s | C2 | WARN: LOST CONTACT TRK-000010: no update for 60 s |
| 14:08:31 |   451.0 s | C2 | WARN: LOST CONTACT TRK-000017: no update for 60 s |
| 14:09:20 |   500.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000020 at 1694 m |
| 14:09:20 |   500.0 s | SENSOR | RF-01 first records **INT-MISS** (16 records in all) |
| 14:09:20 |   500.0 s | SENSOR | RF-03 first records **INT-MISS** (16 records in all) |
| 14:09:20 |   500.0 s | TRUTH | **INT-MISS** (jedi, friendly) airborne |
| 14:09:26 |   506.0 s | SENSOR | RF-02 first records **INT-MISS** (4 records in all) |
| 14:09:35 |   515.5 s | TRUTH | **INT-MISS** track ends |
| 14:09:53 |   533.0 s | C2 | WARN: LOST CONTACT TRK-000012: no update for 60 s |
| 14:10:35 |   575.0 s | C2 | WARN: LOST CONTACT TRK-000020: no update for 60 s |
| 14:11:18 |   618.0 s | SENSOR | RADAR-01 first records **fiber_1** (189 records in all) |
| 14:11:57 |   657.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000024 at 2794 m |
| 14:12:40 |   700.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000018 at 2998 m |
| 14:13:01 |   721.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000028 at 2552 m |
| 14:13:52 |   772.0 s | C2 | WARN: LOST CONTACT TRK-000026: no update for 60 s |
| 14:13:55 |   775.9 s | TRUTH | **jammer_1** on |
| 14:13:56 |   776.0 s | SENSOR | RF-01 first records **jammer_1** (139 records in all) |
| 14:13:56 |   776.0 s | SENSOR | RF-02 first records **jammer_1** (139 records in all) |
| 14:14:52 |   832.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000031 at 1708 m |
| 14:15:07 |   847.0 s | C2 | WARN: LOST CONTACT TRK-000029: no update for 60 s |
| 14:15:22 |   862.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000033 at 1719 m |
| 14:15:24 |   864.0 s | C2 | WARN: LOST CONTACT TRK-000018: no update for 60 s |
| 14:16:00 |   900.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000022 at 2945 m |
| 14:16:14 |   914.6 s | TRUTH | **jammer_1** off |
| 14:16:29 |   929.0 s | C2 | WARN: LOST CONTACT TRK-000033: no update for 60 s |
| 14:16:36 |   936.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000034 at 849 m |
| 14:16:36 |   936.0 s | C2 | CRITICAL: CLOSE TO SITE-01: TRK-000034 at 849 m |
| 14:16:37 |   937.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000035 at 1650 m |
| 14:16:42 |   942.0 s | C2 | SITE-01 → approached (confirmed track TRK-000034 within 987 m) |
| 14:17:00 |   960.0 s | C2 | WARN: LOST CONTACT TRK-000030: no update for 60 s |
| 14:17:29 |   989.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000036 at 730 m |
| 14:17:29 |   989.0 s | C2 | CRITICAL: CLOSE TO SITE-01: TRK-000036 at 730 m |
| 14:17:30 |   990.0 s | C2 | WARN: LOST CONTACT TRK-000022: no update for 60 s |
| 14:17:35 |   995.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000037 at 1579 m |
| 14:17:46 |  1006.0 s | C2 | WARN: LOST CONTACT TRK-000034: no update for 60 s |
| 14:17:53 |  1013.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000038 at 974 m |
| 14:17:53 |  1013.0 s | C2 | CRITICAL: CLOSE TO SITE-01: TRK-000038 at 974 m |
| 14:18:08 |  1028.5 s | TRUTH | **fiber_1** track ends |
| 14:18:30 |  1050.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000041 at 2800 m |
| 14:18:58 |  1078.0 s | C2 | WARN: LOST CONTACT TRK-000035: no update for 60 s |
| 14:19:17 |  1097.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000043 at 1253 m |
| 14:19:34 |  1114.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000044 at 849 m |
| 14:19:34 |  1114.0 s | C2 | CRITICAL: CLOSE TO SITE-01: TRK-000044 at 849 m |
| 14:19:48 |  1128.0 s | C2 | WARN: LOST CONTACT TRK-000038: no update for 60 s |
| 14:19:54 |  1134.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000045 at 2733 m |
| 14:20:20 |  1160.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000046 at 1188 m |
| 14:20:37 |  1177.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000047 at 2316 m |
| 14:20:41 |  1181.0 s | TRUTH | **mavic_1** track ends |
| 14:20:52 |  1192.0 s | C2 | WARN: LOST CONTACT TRK-000043: no update for 60 s |
| 14:20:59 |  1199.5 s | C2 | ADT-01 → no contact (no C2 track within 500 m at its end) |
| 14:20:59 |  1199.5 s | C2 | ADB-01 → no contact (no C2 track within 500 m at its end) |

## Outcome per hostile

| hostile | airborne | first sensor record | first C2 alert | truth outcome |
|---|---|---|---|---|
| mavic_1 | 14:01:45 | 14:01:45 (+0 s) | 14:01:47 (+2 s) | not reached |
| fiber_1 | 14:07:42 | 14:11:18 (+216 s) | none | approached |

## Audit (independent physics checks)

**7 pass · 0 fail · 3 skip**

| check | status | value |
|---|---|---|
| Provenance | PASS | 0 |
| Clock sync | PASS | 0 |
| Bearing geometry | PASS | 0.9369 |
| Terrain shadow | SKIP | — |
| Occlusion gaps | PASS | 0.0 |
| Fix calibration | PASS | 0.5076 |
| Range law | PASS | 2.646 |
| Acoustic delay | SKIP | — |
| Spoof visibility | SKIP | — |
| Cross-sensor time | PASS | 1.0 |
