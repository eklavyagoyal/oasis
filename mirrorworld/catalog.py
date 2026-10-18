"""Platform catalog: physical, RF and acoustic signature per object type.

Public-source approximations. Tune numbers here, never inside sensor modules.

Link fields:
  tx        "self" = the object transmits (downlink); "operator" = the operator object whose
            `controls` points at this drone transmits it (uplink) — so DF on it finds the pilot.
  band_mhz  (lo, hi) the link lives in. `channels` (centre MHz) when it sits on fixed channels.
  hop       re-tunes every packet across the band (FHSS): each detection shows a different freq.
  duty      fraction of time on air (airtime). DJI remote_id = DroneID: unencrypted OFDM burst every
            ~640 ms inside OcuSync carrying drone AND pilot GPS (lane D decodes it, not rf_df).
  sig_class what a spectrum classifier would call it.
"""

_VIDEO_58 = [5658, 5695, 5732, 5769, 5806, 5843, 5880, 5917]  # raceband R1-R8
_WIFI_24 = [2412, 2437, 2462]  # non-overlapping channels 1/6/11

CATALOG = {
    "dji_mavic3": {
        "kind": "drone", "shape": "quad", "span_m": 0.38, "speed_mps": 12, "remote_id": True,
        "sound": {"f0_hz": 200, "level_db_1m": 78},  # 2-blade props ~6000 rpm hover
        "links": [
            {"name": "video", "tx": "self", "band_mhz": (2400.0, 2483.5), "bw_mhz": 20, "eirp_dbm": 26,
             "duty": 0.9, "hop": False, "sig_class": "OcuSync video"},
            {"name": "rc", "tx": "operator", "band_mhz": (2400.0, 2483.5), "bw_mhz": 5, "eirp_dbm": 23,
             "duty": 0.25, "hop": True, "sig_class": "OcuSync RC"},
        ],
    },
    "fpv_analog": {
        "kind": "drone", "shape": "quad", "span_m": 0.30, "speed_mps": 25, "remote_id": False,
        "sound": {"f0_hz": 500, "level_db_1m": 86},  # 7" tri-blade
        "links": [
            {"name": "video", "tx": "self", "band_mhz": (5645.0, 5930.0), "channels": _VIDEO_58, "bw_mhz": 20,
             "eirp_dbm": 29, "duty": 1.0, "hop": False, "sig_class": "Analog FM video"},
            {"name": "elrs", "tx": "operator", "band_mhz": (863.0, 870.0), "bw_mhz": 0.5, "eirp_dbm": 27,
             "duty": 0.8, "hop": True, "sig_class": "ELRS LoRa FHSS"},
        ],
    },
    "fpv_fiber": {  # fiber-optic spool: no radio at all — only ears and eyes catch it
        "kind": "drone", "shape": "quad", "span_m": 0.35, "speed_mps": 18, "remote_id": False,
        "sound": {"f0_hz": 450, "level_db_1m": 86},
        "links": [],
    },
    "shahed136": {  # Geran-2; reported cellular modems for tracking, so the odd LTE burst
        "kind": "drone", "shape": "delta", "span_m": 2.5, "speed_mps": 50, "remote_id": False,
        "sound": {"f0_hz": 117, "level_db_1m": 110},  # MD550 two-stroke ~7000 rpm, "moped"
        "links": [
            {"name": "lte", "tx": "self", "band_mhz": (1710.0, 1785.0), "bw_mhz": 5, "eirp_dbm": 23,
             "duty": 0.005, "hop": False, "sig_class": "LTE uplink"},
        ],
    },
    "geese": {  # migrating flock: clutter for cameras, mics (and radar if anyone adds one)
        "kind": "bird", "shape": "flock", "span_m": 1.6, "speed_mps": 15, "remote_id": False,
        "sound": {"f0_hz": 600, "level_db_1m": 85},
        "links": [],
    },
    "operator": {"kind": "operator", "height_m": 1.5, "links": []},  # transmits its drone's uplinks
    "wifi_ap": {
        "kind": "emitter", "height_m": 4.0,
        "links": [
            {"name": "wifi", "tx": "self", "band_mhz": (2401.0, 2473.0), "channels": _WIFI_24, "bw_mhz": 20,
             "eirp_dbm": 20, "duty": 0.05, "hop": False, "sig_class": "Wi-Fi"},
        ],
    },
    "jammer": {  # barrage jammer over the 2.4 GHz ISM band
        "kind": "emitter", "height_m": 6.0,
        "links": [
            {"name": "barrage", "tx": "self", "band_mhz": (2400.0, 2500.0), "channels": [2450], "bw_mhz": 100,
             "eirp_dbm": 43, "duty": 1.0, "hop": False, "sig_class": "Wideband noise"},
        ],
    },
}
