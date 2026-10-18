# Log book: 02-decoy-water

49.3754° N · 31.1882° E · 10 km square · 04 Nov 2026 14:01:00 UTC · 20 min · seed 207

Weather: wind from 157° at 1.4 m/s, 3 °C, visibility 18.4 km.

## Cast

| id | type | side | where |
|---|---|---|---|
| SITE-01 | water_works | friendly | 49.3957° N · 31.2531° E |
| ADT-01 | ad_team | friendly | 49.4000° N · 31.2269° E |
| ADB-01 | ad_battery | friendly | 49.4010° N · 31.2322° E |
| shahed_1 | shahed136 | hostile | moves: 5 waypoints |
| shahed_2 | shahed136 | hostile | moves: 4 waypoints |
| gerbera_1 | gerbera | hostile | moves: 4 waypoints |
| gerbera_2 | gerbera | hostile | moves: 4 waypoints |
| INT-01 | octopus | friendly | moves: 2 waypoints |
| op_INT-01 | operator | friendly | 49.4002° N · 31.2305° E |
| INT-02 | octopus | friendly | moves: 2 waypoints |
| op_INT-02 | operator | friendly | 49.4024° N · 31.2248° E |

**Sensors:** RF-01 (rf_df), RF-02 (rf_df), RADAR-01 (radar), CAM-01 (camera), C2-01 (c2)

## Timeline

TRUTH is what happened. SENSOR is the first record each sensor made of each object. C2 is what the command post concluded from sensor data alone (7 routine new-track notices are left out).

| UTC | T+ | voice | event |
|---|---|---|---|
| 14:04:34 |   214.0 s | TRUTH | **gerbera_1** (gerbera, hostile) airborne |
| 14:05:07 |   247.0 s | SENSOR | RADAR-01 first records **gerbera_1** (26 records in all) |
| 14:06:23 |   323.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000001 at 2975 m |
| 14:06:23 |   323.0 s | C2 | ADT-01 → alerted (first warn alert ALT-000002) |
| 14:06:23 |   323.0 s | C2 | ADT-01 → responding (dispatched on ALT-000002) |
| 14:06:23 |   323.0 s | C2 | ADB-01 → alerted (first warn alert ALT-000002) |
| 14:06:23 |   323.0 s | C2 | ADB-01 → responding (dispatched on ALT-000002) |
| 14:06:24 |   324.0 s | TRUTH | **INT-02** (octopus, friendly) airborne |
| 14:06:25 |   325.0 s | SENSOR | RF-01 first records **INT-02** (7 records in all) |
| 14:06:26 |   326.0 s | SENSOR | RF-02 first records **INT-02** (4 records in all) |
| 14:06:28 |   328.0 s | SENSOR | RF-01 first records **op_INT-02** (1 records in all) |
| 14:06:29 |   329.0 s | C2 | WARN: LOST CONTACT TRK-000000: no update for 60 s |
| 14:06:30 |   330.0 s | SENSOR | RADAR-01 first records **INT-02** (2 records in all) |
| 14:06:31 |   331.5 s | TRUTH | **gerbera_1** track ends |
| 14:06:31 |   331.5 s | TRUTH | **INT-02** track ends |
| 14:07:36 |   396.0 s | C2 | WARN: LOST CONTACT TRK-000001: no update for 60 s |
| 14:07:40 |   400.5 s | TRUTH | **shahed_1** (shahed136, hostile) airborne |
| 14:07:42 |   402.0 s | SENSOR | RADAR-01 first records **shahed_1** (45 records in all) |
| 14:07:47 |   407.0 s | SENSOR | RF-02 first records **shahed_1** (4 records in all) |
| 14:07:56 |   416.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000002 at 2915 m |
| 14:08:27 |   447.0 s | SENSOR | RF-01 first records **shahed_1** (5 records in all) |
| 14:08:30 |   450.0 s | TRUTH | **shahed_2** (shahed136, hostile) airborne |
| 14:08:31 |   451.0 s | SENSOR | RF-02 first records **shahed_2** (11 records in all) |
| 14:08:37 |   457.0 s | SENSOR | RADAR-01 first records **shahed_2** (70 records in all) |
| 14:08:41 |   461.0 s | SENSOR | RF-01 first records **shahed_2** (12 records in all) |
| 14:08:58 |   478.0 s | SENSOR | RF-01 first records **op_INT-01** (8 records in all) |
| 14:08:58 |   478.0 s | TRUTH | **INT-01** (octopus, friendly) airborne |
| 14:08:59 |   479.0 s | SENSOR | RF-01 first records **INT-01** (15 records in all) |
| 14:09:00 |   480.0 s | SENSOR | RF-02 first records **INT-01** (10 records in all) |
| 14:09:03 |   483.0 s | SENSOR | RADAR-01 first records **INT-01** (3 records in all) |
| 14:09:04 |   484.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000004 at 2640 m |
| 14:09:12 |   492.0 s | C2 | CRITICAL: CLOSE TO SITE-01: TRK-000002 at 993 m |
| 14:09:12 |   492.0 s | C2 | SITE-01 → approached (confirmed track TRK-000002 within 993 m) |
| 14:09:13 |   493.0 s | TRUTH | **shahed_1** track ends |
| 14:09:13 |   493.0 s | TRUTH | **INT-01** track ends |
| 14:09:43 |   523.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000003 at 2981 m |
| 14:10:12 |   552.0 s | C2 | WARN: SENSOR SILENT CAM-01: no detections since 2026-11-04T14:09:12.000Z (RADAR-01, RF-01, RF-02 still reporting) |
| 14:10:18 |   558.0 s | C2 | WARN: LOST CONTACT TRK-000002: no update for 60 s |
| 14:10:25 |   565.0 s | C2 | CRITICAL: CLOSE TO SITE-01: TRK-000003 at 928 m |
| 14:10:28 |   568.0 s | SENSOR | RADAR-01 first records **gerbera_2** (30 records in all) |
| 14:10:28 |   568.0 s | TRUTH | **gerbera_2** (gerbera, hostile) airborne |
| 14:10:43 |   583.0 s | TRUTH | **shahed_2** reaches SITE-01 (14.4 m) |
| 14:11:48 |   648.0 s | C2 | WARN: LOST CONTACT TRK-000003: no update for 60 s |
| 14:11:54 |   654.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000006 at 1619 m |
| 14:12:16 |   676.0 s | C2 | CRITICAL: CLOSE TO SITE-01: TRK-000006 at 892 m |
| 14:12:29 |   689.0 s | TRUTH | **gerbera_2** reaches SITE-01 (2.4 m) |
| 14:13:16 |   736.0 s | C2 | WARN: LOST CONTACT TRK-000006: no update for 60 s |
| 14:15:58 |   898.9 s | C2 | WARN: SENSOR SILENT RF-01: no detections since 2026-11-04T14:14:58.925Z (RADAR-01 still reporting) |
| 14:20:59 |  1199.5 s | C2 | ADT-01 → no contact (no C2 track within 500 m at its end) |
| 14:20:59 |  1199.5 s | C2 | ADB-01 → no contact (no C2 track within 500 m at its end) |

## Outcome per hostile

| hostile | airborne | first sensor record | first C2 alert | truth outcome |
|---|---|---|---|---|
| shahed_1 | 14:07:40 | 14:07:42 (+2 s) | none | approached |
| shahed_2 | 14:08:30 | 14:08:31 (+1 s) | 14:09:43 (+73 s) | reached |
| gerbera_1 | 14:04:34 | 14:05:07 (+33 s) | none | not reached |
| gerbera_2 | 14:10:28 | 14:10:28 (+0 s) | none | reached |

## Audit (independent physics checks)

**5 pass · 1 fail · 4 skip**

| check | status | value |
|---|---|---|
| Provenance | PASS | 0 |
| Clock sync | PASS | 0 |
| Bearing geometry | PASS | 0.9655 |
| Terrain shadow | SKIP | — |
| Occlusion gaps | SKIP | — |
| Fix calibration | FAIL | 0.0 |
| Range law | PASS | 2.228 |
| Acoustic delay | SKIP | — |
| Spoof visibility | SKIP | — |
| Cross-sensor time | PASS | 1.0 |
