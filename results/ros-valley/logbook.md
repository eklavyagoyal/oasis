# Log book: ros-valley

49.3700° N · 31.2000° E · 16 km square · 04 Nov 2026 08:55:00 UTC · 340 min · seed 7

Weather: wind from 270° at 3.5 m/s, 4 °C, visibility 12 km.

## Cast

| id | type | side | where |
|---|---|---|---|
| farmer_mavic | dji_mavic3 | neutral | moves: 4 waypoints |
| farmer | operator | neutral | 49.3745° N · 31.1280° E |
| shahed_am | shahed136 | hostile | moves: 2 waypoints |
| wifi_1 | wifi_ap | neutral | 49.4168° N · 31.2526° E |
| wifi_2 | wifi_ap | neutral | 49.4076° N · 31.1119° E |
| mavic_1 | dji_mavic3 | hostile | moves: 7 waypoints |
| pilot_1 | operator | hostile | 49.3538° N · 31.2021° E |
| recon_1 | dji_mavic3 | friendly | moves: 4 waypoints |
| op_ua | operator | friendly | 49.3380° N · 31.1750° E |
| geese_1 | geese | neutral | moves: 2 waypoints |
| fpv_fiber_1 | fpv_fiber | hostile | moves: 3 waypoints |
| shahed_1 | shahed136 | hostile | moves: 2 waypoints |
| fpv_1 | fpv_analog | hostile | moves: 4 waypoints |
| pilot_2 | operator | hostile | 49.3040° N · 31.3000° E |
| jammer_1 | jammer | friendly | 49.3550° N · 31.2150° E |
| SITE-01 | power_station | friendly | 49.3820° N · 31.2050° E |
| ADT-01 | ad_team | friendly | 49.3700° N · 31.2150° E |

**Sensors:** RF1 (rf_df), RF2 (rf_df), RADAR-01 (radar), EO1 (camera), CAM-02 (camera), MIC1 (microphone), MIC2 (microphone), RID1 (remote_id), TEL1 (telemetry), SAT1 (satellite), HUM1 (reports), IQ1 (rf_iq), C2-01 (c2)

## Timeline

TRUTH is what happened. SENSOR is the first record each sensor made of each object. C2 is what the command post concluded from sensor data alone (263 routine new-track notices are left out).

| UTC | T+ | voice | event |
|---|---|---|---|
| 08:55:00 |     0.0 s | SENSOR | RF2 first records **farmer_mavic** (1,201 records in all) |
| 08:55:00 |     0.0 s | SENSOR | RF1 first records **farmer_mavic** (1,201 records in all) |
| 08:55:00 |     0.0 s | TRUTH | **farmer_mavic** (dji_mavic3, neutral) airborne |
| 08:55:00 |     0.0 s | SENSOR | RID1 first records **farmer_mavic** (1,091 records in all) |
| 08:55:01 |     1.0 s | SENSOR | RF1 first records **wifi_2** (8,074 records in all) |
| 08:55:01 |     1.0 s | SENSOR | RF1 first records **farmer** (853 records in all) |
| 08:55:06 |     6.0 s | SENSOR | RF2 first records **farmer** (176 records in all) |
| 08:56:10 |    70.0 s | C2 | WARN: LOST CONTACT TRK-000000: no update for 60 s |
| 08:56:10 |    70.0 s | C2 | ADT-01 → alerted (first warn alert ALT-000006) |
| 08:56:10 |    70.0 s | C2 | ADT-01 → responding (dispatched on ALT-000006) |
| 08:57:33 |   153.0 s | C2 | WARN: LOST CONTACT TRK-000004: no update for 60 s |
| 08:57:37 |   157.0 s | C2 | WARN: LOST CONTACT TRK-000003: no update for 60 s |
| 08:58:11 |   191.0 s | C2 | WARN: LOST CONTACT TRK-000009: no update for 60 s |
| 08:58:31 |   211.0 s | SENSOR | MIC1 first records **farmer_mavic** (8 records in all) |
| 08:59:18 |   258.0 s | C2 | WARN: LOST CONTACT TRK-000012: no update for 60 s |
| 08:59:20 |   260.0 s | C2 | WARN: LOST CONTACT TRK-000015: no update for 60 s |
| 09:01:04 |   364.0 s | C2 | WARN: LOST CONTACT TRK-000017: no update for 60 s |
| 09:01:06 |   366.0 s | C2 | WARN: LOST CONTACT TRK-000020: no update for 60 s |
| 09:01:30 |   390.0 s | C2 | WARN: LOST CONTACT TRK-000026: no update for 60 s |
| 09:02:32 |   452.0 s | C2 | WARN: LOST CONTACT TRK-000027: no update for 60 s |
| 09:03:01 |   481.0 s | C2 | WARN: LOST CONTACT TRK-000028: no update for 60 s |
| 09:03:01 |   481.0 s | TRUTH | **shahed_am** (shahed136, hostile) airborne |
| 09:03:16 |   496.0 s | SENSOR | RF1 first records **shahed_am** (24 records in all) |
| 09:03:24 |   504.0 s | SENSOR | RF2 first records **shahed_am** (20 records in all) |
| 09:03:31 |   511.0 s | C2 | WARN: LOST CONTACT TRK-000030: no update for 60 s |
| 09:04:08 |   548.0 s | SENSOR | MIC2 first records **shahed_am** (349 records in all) |
| 09:04:20 |   560.0 s | C2 | WARN: LOST CONTACT TRK-000032: no update for 60 s |
| 09:04:22 |   562.0 s | SENSOR | RADAR-01 first records **shahed_am** (145 records in all) |
| 09:04:38 |   578.0 s | C2 | WARN: LOST CONTACT TRK-000031: no update for 60 s |
| 09:04:43 |   583.0 s | SENSOR | MIC1 first records **shahed_am** (310 records in all) |
| 09:05:40 |   640.0 s | SENSOR | CAM-02 first records **shahed_am** (48 records in all) |
| 09:05:44 |   644.0 s | C2 | WARN: LOST CONTACT TRK-000036: no update for 60 s |
| 09:06:02 |   662.0 s | C2 | WARN: LOST CONTACT TRK-000033: no update for 60 s |
| 09:06:05 |   665.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000039 at 2965 m |
| 09:06:15 |   675.0 s | C2 | WARN: LOST CONTACT TRK-000035: no update for 60 s |
| 09:06:21 |   681.0 s | C2 | WARN: LOST CONTACT TRK-000034: no update for 60 s |
| 09:06:28 |   688.0 s | C2 | WARN: LOST CONTACT TRK-000038: no update for 60 s |
| 09:06:49 |   709.0 s | C2 | CRITICAL: CLOSE TO SITE-01: TRK-000039 at 969 m |
| 09:06:49 |   709.0 s | C2 | SITE-01 → approached (confirmed track TRK-000039 within 969 m) |
| 09:07:33 |   753.1 s | SENSOR | HUM1 first records **shahed_am** (9 records in all) |
| 09:07:39 |   759.0 s | C2 | WARN: LOST CONTACT TRK-000042: no update for 60 s |
| 09:08:20 |   800.0 s | C2 | WARN: LOST CONTACT TRK-000044: no update for 60 s |
| 09:08:53 |   833.0 s | C2 | WARN: LOST CONTACT TRK-000046: no update for 60 s |
| 09:08:54 |   834.0 s | C2 | WARN: LOST CONTACT TRK-000039: no update for 60 s |
| 09:09:37 |   877.0 s | C2 | WARN: LOST CONTACT TRK-000047: no update for 60 s |
| 09:10:16 |   916.0 s | TRUTH | **shahed_am** track ends |
| 09:10:26 |   926.0 s | C2 | WARN: LOST CONTACT TRK-000049: no update for 60 s |
| 09:10:57 |   957.0 s | C2 | WARN: LOST CONTACT TRK-000051: no update for 60 s |
| 09:11:43 |  1003.0 s | C2 | WARN: LOST CONTACT TRK-000055: no update for 60 s |
| 09:11:50 |  1010.0 s | C2 | WARN: LOST CONTACT TRK-000050: no update for 60 s |
| 09:14:16 |  1156.0 s | C2 | WARN: LOST CONTACT TRK-000058: no update for 60 s |
| 09:15:00 |  1200.0 s | TRUTH | **farmer_mavic** track ends |
| 09:15:05 |  1205.0 s | SENSOR | RF1 first records **wifi_1** (3,479 records in all) |
| 09:15:06 |  1206.6 s | SENSOR | HUM1 first records **farmer_mavic** (1 records in all) |
| 09:15:21 |  1221.0 s | C2 | WARN: LOST CONTACT TRK-000065: no update for 60 s |
| 09:15:59 |  1259.0 s | C2 | WARN: LOST CONTACT TRK-000067: no update for 60 s |
| 13:58:32 | 18212.5 s | TRUTH | **mavic_1** (dji_mavic3, hostile) airborne |
| 13:58:33 | 18213.0 s | SENSOR | RF2 first records **pilot_1** (1,272 records in all) |
| 13:58:33 | 18213.0 s | SENSOR | RADAR-01 first records **mavic_1** (494 records in all) |
| 13:58:33 | 18213.0 s | SENSOR | RF1 first records **pilot_1** (1,528 records in all) |
| 13:58:33 | 18213.0 s | SENSOR | RF1 first records **mavic_1** (1,227 records in all) |
| 13:58:33 | 18213.0 s | SENSOR | RF2 first records **mavic_1** (318 records in all) |
| 13:58:35 | 18215.0 s | SENSOR | RID1 first records **mavic_1** (422 records in all) |
| 13:58:36 | 18216.0 s | SENSOR | CAM-02 first records **mavic_1** (157 records in all) |
| 13:58:43 | 18223.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000069 at 2672 m |
| 13:58:43 | 18223.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000068 at 2992 m |
| 13:59:02 | 18242.0 s | SENSOR | MIC2 first records **mavic_1** (16 records in all) |
| 13:59:28 | 18268.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000070 at 2964 m |
| 13:59:32 | 18272.0 s | SENSOR | MIC1 first records **mavic_1** (236 records in all) |
| 13:59:48 | 18288.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000074 at 2532 m |
| 14:00:00 | 18300.0 s | C2 | WARN: LOST CONTACT TRK-000069: no update for 60 s |
| 14:00:00 | 18300.0 s | SENSOR | RF2 first records **recon_1** (2,011 records in all) |
| 14:00:00 | 18300.0 s | SENSOR | RF1 first records **recon_1** (1,825 records in all) |
| 14:00:00 | 18300.0 s | SENSOR | TEL1 first records **recon_1** (10,498 records in all) |
| 14:00:00 | 18300.0 s | TRUTH | **recon_1** (dji_mavic3, friendly) airborne |
| 14:00:00 | 18300.0 s | SENSOR | RID1 first records **recon_1** (970 records in all) |
| 14:00:30 | 18330.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000078 at 2662 m |
| 14:00:52 | 18352.0 s | C2 | WARN: LOST CONTACT TRK-000070: no update for 60 s |
| 14:01:01 | 18361.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000080 at 2525 m |
| 14:01:16 | 18376.0 s | SENSOR | RADAR-01 first records **recon_1** (206 records in all) |
| 14:01:47 | 18407.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000081 at 2198 m |
| 14:01:49 | 18409.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000082 at 2535 m |
| 14:01:54 | 18414.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000073 at 2938 m |
| 14:02:23 | 18443.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000083 at 2022 m |
| 14:02:29 | 18449.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000079 at 2945 m |
| 14:02:48 | 18468.0 s | C2 | CRITICAL: CLOSE TO SITE-01: TRK-000068 at 994 m |
| 14:03:05 | 18485.0 s | C2 | WARN: LOST CONTACT TRK-000075: no update for 60 s |
| 14:03:16 | 18496.0 s | C2 | WARN: LOST CONTACT TRK-000073: no update for 60 s |
| 14:03:28 | 18508.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000084 at 2958 m |
| 14:03:30 | 18510.0 s | C2 | WARN: LOST CONTACT TRK-000079: no update for 60 s |
| 14:03:34 | 18514.0 s | SENSOR | RF1 first records **op_ua** (8 records in all) |
| 14:03:48 | 18528.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000089 at 2124 m |
| 14:03:51 | 18531.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000090 at 964 m |
| 14:03:51 | 18531.0 s | C2 | CRITICAL: CLOSE TO SITE-01: TRK-000090 at 964 m |
| 14:04:16 | 18556.0 s | C2 | WARN: LOST CONTACT TRK-000086: no update for 60 s |
| 14:04:23 | 18563.0 s | C2 | WARN: LOST CONTACT TRK-000085: no update for 60 s |
| 14:04:31 | 18571.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000096 at 1065 m |
| 14:04:45 | 18585.0 s | C2 | WARN: LOST CONTACT TRK-000088: no update for 60 s |
| 14:05:00 | 18600.0 s | TRUTH | **geese_1** (geese, neutral) airborne |
| 14:05:41 | 18641.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000099 at 2357 m |
| 14:05:45 | 18645.0 s | C2 | WARN: LOST CONTACT TRK-000094: no update for 60 s |
| 14:06:03 | 18663.0 s | C2 | WARN: LOST CONTACT TRK-000068: no update for 60 s |
| 14:06:21 | 18681.0 s | C2 | WARN: LOST CONTACT TRK-000093: no update for 60 s |
| 14:06:30 | 18690.0 s | C2 | WARN: LOST CONTACT TRK-000092: no update for 60 s |
| 14:06:45 | 18705.0 s | C2 | WARN: LOST CONTACT TRK-000098: no update for 60 s |
| 14:07:43 | 18763.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000108 at 2377 m |
| 14:07:46 | 18766.0 s | C2 | WARN: LOST CONTACT TRK-000084: no update for 60 s |
| 14:07:54 | 18774.0 s | C2 | WARN: LOST CONTACT TRK-000105: no update for 60 s |
| 14:08:16 | 18796.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000109 at 2428 m |
| 14:08:30 | 18810.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000111 at 1061 m |
| 14:08:54 | 18834.0 s | C2 | WARN: LOST CONTACT TRK-000107: no update for 60 s |
| 14:10:00 | 18900.0 s | TRUTH | **fpv_fiber_1** (fpv_fiber, hostile) airborne |
| 14:10:07 | 18907.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000113 at 2992 m |
| 14:10:12 | 18912.0 s | C2 | WARN: LOST CONTACT TRK-000112: no update for 60 s |
| 14:10:13 | 18913.0 s | C2 | WARN: LOST CONTACT TRK-000110: no update for 60 s |
| 14:10:17 | 18917.0 s | C2 | WARN: LOST CONTACT TRK-000104: no update for 60 s |
| 14:11:00 | 18960.0 s | SENSOR | RADAR-01 first records **geese_1** (343 records in all) |
| 14:11:02 | 18962.0 s | SENSOR | MIC2 first records **geese_1** (8 records in all) |
| 14:11:12 | 18972.3 s | SENSOR | HUM1 first records **geese_1** (7 records in all) |
| 14:11:23 | 18983.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000119 at 2819 m |
| 14:11:25 | 18985.0 s | SENSOR | MIC2 first records **recon_1** (8 records in all) |
| 14:12:49 | 19069.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000125 at 2114 m |
| 14:12:49 | 19069.0 s | SENSOR | CAM-02 first records **geese_1** (163 records in all) |
| 14:12:52 | 19072.0 s | SENSOR | MIC1 first records **geese_1** (165 records in all) |
| 14:12:56 | 19076.0 s | C2 | WARN: LOST CONTACT TRK-000113: no update for 60 s |
| 14:12:58 | 19078.9 s | SENSOR | HUM1 first records **fpv_fiber_1** (3 records in all) |
| 14:12:59 | 19079.0 s | C2 | WARN: LOST CONTACT TRK-000115: no update for 60 s |
| 14:13:19 | 19099.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000123 at 2948 m |
| 14:13:29 | 19109.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000127 at 1563 m |
| 14:13:29 | 19109.0 s | C2 | WARN: LOST CONTACT TRK-000121: no update for 60 s |
| 14:13:48 | 19128.0 s | C2 | WARN: LOST CONTACT TRK-000122: no update for 60 s |
| 14:13:51 | 19131.0 s | C2 | WARN: LOST CONTACT TRK-000119: no update for 60 s |
| 14:14:05 | 19145.0 s | C2 | WARN: LOST CONTACT TRK-000125: no update for 60 s |
| 14:14:15 | 19155.0 s | C2 | CRITICAL: CLOSE TO SITE-01: TRK-000127 at 996 m |
| 14:15:17 | 19217.7 s | SENSOR | HUM1 first records **mavic_1** (7 records in all) |
| 14:15:21 | 19221.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000126 at 2977 m |
| 14:15:54 | 19254.0 s | C2 | WARN: LOST CONTACT TRK-000123: no update for 60 s |
| 14:16:25 | 19285.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000134 at 2156 m |
| 14:16:30 | 19290.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000130 at 2950 m |
| 14:16:37 | 19297.0 s | C2 | WARN: LOST CONTACT TRK-000126: no update for 60 s |
| 14:16:43 | 19303.0 s | C2 | WARN: LOST CONTACT TRK-000132: no update for 60 s |
| 14:17:15 | 19335.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000135 at 2854 m |
| 14:17:29 | 19349.0 s | C2 | WARN: LOST CONTACT TRK-000133: no update for 60 s |
| 14:17:50 | 19370.0 s | C2 | WARN: LOST CONTACT TRK-000130: no update for 60 s |
| 14:18:09 | 19389.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000137 at 2744 m |
| 14:18:55 | 19435.0 s | C2 | WARN: LOST CONTACT TRK-000135: no update for 60 s |
| 14:19:05 | 19445.0 s | TRUTH | **fpv_fiber_1** track ends |
| 14:19:17 | 19457.0 s | C2 | WARN: LOST CONTACT TRK-000136: no update for 60 s |
| 14:19:54 | 19494.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000145 at 2948 m |
| 14:20:18 | 19518.0 s | C2 | WARN: LOST CONTACT TRK-000137: no update for 60 s |
| 14:20:27 | 19527.0 s | C2 | WARN: LOST CONTACT TRK-000127: no update for 60 s |
| 14:20:27 | 19527.0 s | C2 | WARN: LOST CONTACT TRK-000138: no update for 60 s |
| 14:20:34 | 19534.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000140 at 2970 m |
| 14:21:00 | 19560.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000153 at 2787 m |
| 14:21:04 | 19564.0 s | C2 | WARN: LOST CONTACT TRK-000143: no update for 60 s |
| 14:21:09 | 19569.0 s | C2 | WARN: LOST CONTACT TRK-000147: no update for 60 s |
| 14:21:42 | 19602.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000156 at 2925 m |
| 14:21:51 | 19611.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000157 at 2512 m |
| 14:21:53 | 19613.0 s | C2 | WARN: LOST CONTACT TRK-000151: no update for 60 s |
| 14:21:58 | 19618.0 s | C2 | WARN: LOST CONTACT TRK-000146: no update for 60 s |
| 14:22:43 | 19663.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000161 at 2917 m |
| 14:22:51 | 19671.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000162 at 2966 m |
| 14:22:53 | 19673.0 s | C2 | WARN: LOST CONTACT TRK-000155: no update for 60 s |
| 14:23:17 | 19697.0 s | C2 | WARN: LOST CONTACT TRK-000154: no update for 60 s |
| 14:23:20 | 19700.0 s | TRUTH | **shahed_1** (shahed136, hostile) airborne |
| 14:23:23 | 19703.0 s | C2 | WARN: LOST CONTACT TRK-000140: no update for 60 s |
| 14:23:26 | 19706.0 s | SENSOR | RF1 first records **shahed_1** (22 records in all) |
| 14:23:27 | 19707.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000160 at 2846 m |
| 14:23:50 | 19730.0 s | SENSOR | MIC2 first records **shahed_1** (364 records in all) |
| 14:23:57 | 19737.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000168 at 2895 m |
| 14:24:13 | 19753.0 s | SENSOR | RF2 first records **shahed_1** (22 records in all) |
| 14:24:20 | 19760.0 s | SENSOR | MIC1 first records **shahed_1** (317 records in all) |
| 14:24:23 | 19763.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000170 at 2487 m |
| 14:24:29 | 19769.0 s | SENSOR | RADAR-01 first records **shahed_1** (153 records in all) |
| 14:24:36 | 19776.0 s | C2 | WARN: LOST CONTACT TRK-000160: no update for 60 s |
| 14:24:37 | 19777.0 s | C2 | WARN: LOST CONTACT TRK-000163: no update for 60 s |
| 14:24:55 | 19795.0 s | SENSOR | RF2 first records **pilot_2** (480 records in all) |
| 14:24:55 | 19795.0 s | SENSOR | RF1 first records **pilot_2** (516 records in all) |
| 14:24:55 | 19795.0 s | SENSOR | RF1 first records **fpv_1** (154 records in all) |
| 14:24:55 | 19795.0 s | TRUTH | **fpv_1** (fpv_analog, hostile) airborne |
| 14:24:57 | 19797.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000173 at 2994 m |
| 14:24:58 | 19798.0 s | C2 | WARN: LOST CONTACT TRK-000164: no update for 60 s |
| 14:25:17 | 19817.0 s | C2 | WARN: LOST CONTACT TRK-000168: no update for 60 s |
| 14:25:23 | 19823.0 s | SENSOR | CAM-02 first records **shahed_1** (25 records in all) |
| 14:25:33 | 19833.0 s | C2 | WARN: LOST CONTACT TRK-000171: no update for 60 s |
| 14:25:42 | 19842.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000186 at 1988 m |
| 14:25:50 | 19850.0 s | SENSOR | RF1 first records **jammer_1** (121 records in all) |
| 14:25:50 | 19850.0 s | TRUTH | **jammer_1** on |
| 14:26:06 | 19866.0 s | C2 | WARN: LOST CONTACT TRK-000175: no update for 60 s |
| 14:26:09 | 19869.0 s | SENSOR | RF2 first records **fpv_1** (214 records in all) |
| 14:26:13 | 19873.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000178 at 2955 m |
| 14:26:45 | 19905.0 s | C2 | WARN: LOST CONTACT TRK-000166: no update for 60 s |
| 14:26:46 | 19906.0 s | C2 | WARN: LOST CONTACT TRK-000173: no update for 60 s |
| 14:26:57 | 19917.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000196 at 2311 m |
| 14:26:59 | 19919.0 s | C2 | WARN: LOST CONTACT TRK-000182: no update for 60 s |
| 14:27:44 | 19964.0 s | TRUTH | **geese_1** track ends |
| 14:27:49 | 19969.5 s | SENSOR | HUM1 first records **shahed_1** (8 records in all) |
| 14:27:50 | 19970.0 s | TRUTH | **jammer_1** off |
| 14:28:38 | 20018.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000207 at 2888 m |
| 14:29:12 | 20052.0 s | C2 | WARN: LOST CONTACT TRK-000178: no update for 60 s |
| 14:29:43 | 20083.0 s | C2 | WARN: LOST CONTACT TRK-000207: no update for 60 s |
| 14:29:43 | 20083.0 s | C2 | WARN: LOST CONTACT TRK-000213: no update for 60 s |
| 14:29:53 | 20093.5 s | TRUTH | **mavic_1** reaches SITE-01 (23.4 m) |
| 14:30:06 | 20106.0 s | C2 | WARN: LOST CONTACT TRK-000215: no update for 60 s |
| 14:30:25 | 20125.0 s | TRUTH | **shahed_1** track ends |
| 14:30:26 | 20126.0 s | SENSOR | MIC1 first records **recon_1** (4 records in all) |
| 14:30:41 | 20141.0 s | C2 | WARN: LOST CONTACT TRK-000203: no update for 60 s |
| 14:30:53 | 20153.0 s | C2 | WARN: LOST CONTACT TRK-000186: no update for 60 s |
| 14:31:10 | 20170.0 s | C2 | WARN: LOST CONTACT TRK-000222: no update for 60 s |
| 14:31:11 | 20171.0 s | C2 | WARN: SENSOR SILENT MIC2: no detections since 2026-11-04T14:30:11.000Z (EO1, HUM1, MIC1, RADAR-01, RF1, RF2, RID1, TEL1 still reporting) |
| 14:31:13 | 20173.0 s | C2 | WARN: LOST CONTACT TRK-000227: no update for 60 s |
| 14:31:42 | 20202.0 s | C2 | WARN: LOST CONTACT TRK-000228: no update for 60 s |
| 14:32:12 | 20232.0 s | C2 | WARN: LOST CONTACT TRK-000234: no update for 60 s |
| 14:32:17 | 20237.0 s | C2 | WARN: LOST CONTACT TRK-000238: no update for 60 s |
| 14:32:34 | 20254.0 s | C2 | WARN: LOST CONTACT TRK-000239: no update for 60 s |
| 14:32:38 | 20258.0 s | C2 | WARN: LOST CONTACT TRK-000237: no update for 60 s |
| 14:32:41 | 20261.0 s | C2 | WARN: LOST CONTACT TRK-000243: no update for 60 s |
| 14:33:01 | 20281.0 s | C2 | WARN: LOST CONTACT TRK-000245: no update for 60 s |
| 14:33:08 | 20288.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000259 at 2601 m |
| 14:33:08 | 20288.0 s | C2 | WARN: LOST CONTACT TRK-000241: no update for 60 s |
| 14:33:12 | 20292.0 s | C2 | WARN: LOST CONTACT TRK-000246: no update for 60 s |
| 14:33:30 | 20310.5 s | TRUTH | **fpv_1** track ends |
| 14:33:30 | 20310.5 s | TRUTH | **RF2** destroyed by fpv_1 |
| 14:33:47 | 20327.0 s | C2 | WARN: LOST CONTACT TRK-000247: no update for 60 s |
| 14:33:56 | 20336.0 s | C2 | WARN: LOST CONTACT TRK-000252: no update for 60 s |
| 14:34:00 | 20340.0 s | C2 | WARN: LOST CONTACT TRK-000253: no update for 60 s |
| 14:34:01 | 20341.0 s | C2 | WARN: LOST CONTACT TRK-000257: no update for 60 s |
| 14:34:06 | 20346.0 s | C2 | WARN: LOST CONTACT TRK-000258: no update for 60 s |
| 14:34:30 | 20370.0 s | C2 | WARN: LOST CONTACT TRK-000260: no update for 60 s |
| 14:34:30 | 20370.0 s | C2 | WARN: SENSOR SILENT RF2: no detections since 2026-11-04T14:33:30.000Z (CAM-02, EO1, MIC1, RADAR-01, RF1, RID1, TEL1 still reporting) |
| 14:34:35 | 20375.0 s | C2 | WARN: SENSOR SILENT EO1: no detections since 2026-11-04T14:33:35.000Z (CAM-02, MIC1, RADAR-01, RF1, RID1, TEL1 still reporting) |
| 14:34:59 | 20399.5 s | C2 | ADT-01 → no contact (no C2 track within 500 m at its end) |

## Outcome per hostile

| hostile | airborne | first sensor record | first C2 alert | truth outcome |
|---|---|---|---|---|
| shahed_am | 09:03:01 | 09:03:16 (+15 s) | none | approached |
| mavic_1 | 13:58:32 | 13:58:33 (+0 s) | 14:01:01 (+148 s) | reached |
| fpv_fiber_1 | 14:10:00 | 14:12:58 (+179 s) | none | not reached |
| shahed_1 | 14:23:20 | 14:23:26 (+6 s) | none | not reached |
| fpv_1 | 14:24:55 | 14:24:55 (+0 s) | 14:26:12 (+77 s) | not reached |

## Audit (independent physics checks)

**9 pass · 0 fail · 1 skip**

| check | status | value |
|---|---|---|
| Provenance | PASS | 0 |
| Clock sync | PASS | 0 |
| Bearing geometry | PASS | 0.948 |
| Terrain shadow | SKIP | — |
| Occlusion gaps | PASS | 0.0 |
| Fix calibration | PASS | 0.5254 |
| Range law | PASS | 4.154 |
| Acoustic delay | PASS | 0.0017 |
| Spoof visibility | PASS | — |
| Cross-sensor time | PASS | 1.0 |
