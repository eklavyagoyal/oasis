"""Platform catalog: physical, RF, acoustic and radar signature per object type.

Public-source approximations, used as scenario archetypes, not performance models.
Tune numbers here, never inside sensor modules.

Link fields:
  tx        "self" = the object transmits (downlink); "operator" = the operator object whose
            `controls` points at this drone transmits it (uplink) — so DF on it finds the pilot.
  band_mhz  (lo, hi) the link lives in. `channels` (centre MHz) when it sits on fixed channels.
  hop       re-tunes every packet across the band (FHSS): each detection shows a different freq.
  duty      fraction of time on air (airtime). DJI remote_id = DroneID: unencrypted OFDM burst every
            ~640 ms inside OcuSync carrying drone AND pilot GPS (decoded by the remote_id sensor).
  sig_class what a spectrum classifier would call it.
rcs_m2: mean radar cross-section (X-band, Swerling 1 fluctuation applied by the radar sensor).
kind:   drone | bird | operator | emitter | site (a protected location) | response (a response-asset marker).
"""

_VIDEO_58 = [5658, 5695, 5732, 5769, 5806, 5843, 5880, 5917]  # raceband R1-R8
_WIFI_24 = [2412, 2437, 2462]  # non-overlapping channels 1/6/11

CATALOG = {
    # ---- small UAS ----
    "dji_mavic3": {
        "kind": "drone", "shape": "quad", "span_m": 0.38, "speed_mps": 12, "remote_id": True, "rcs_m2": 0.01,
        "sound": {"f0_hz": 200, "level_db_1m": 78},  # 2-blade props ~6000 rpm hover
        "links": [
            {"name": "video", "tx": "self", "band_mhz": (2400.0, 2483.5), "bw_mhz": 20, "eirp_dbm": 26,
             "duty": 0.9, "hop": False, "sig_class": "OcuSync video"},
            {"name": "rc", "tx": "operator", "band_mhz": (2400.0, 2483.5), "bw_mhz": 5, "eirp_dbm": 23,
             "duty": 0.25, "hop": True, "sig_class": "OcuSync RC"},
        ],
    },
    "fpv_analog": {
        "kind": "drone", "shape": "quad", "span_m": 0.30, "speed_mps": 25, "remote_id": False, "rcs_m2": 0.005,
        "sound": {"f0_hz": 500, "level_db_1m": 86},  # 7" tri-blade
        "links": [
            {"name": "video", "tx": "self", "band_mhz": (5645.0, 5930.0), "channels": _VIDEO_58, "bw_mhz": 20,
             "eirp_dbm": 29, "duty": 1.0, "hop": False, "sig_class": "Analog FM video"},
            {"name": "elrs", "tx": "operator", "band_mhz": (863.0, 870.0), "bw_mhz": 0.5, "eirp_dbm": 27,
             "duty": 0.8, "hop": True, "sig_class": "ELRS LoRa FHSS"},
        ],
    },
    "fpv_fiber": {  # fiber-optic spool: no radio at all — only ears, eyes and radar catch it
        "kind": "drone", "shape": "quad", "span_m": 0.35, "speed_mps": 18, "remote_id": False, "rcs_m2": 0.006,
        "sound": {"f0_hz": 450, "level_db_1m": 86},
        "links": [],
    },
    # ---- archetypes of Russian long-range and reconnaissance UAS ----
    "shahed136": {  # Geran-2; reported cellular modems for tracking, so the odd LTE burst
        "kind": "drone", "shape": "delta", "span_m": 2.5, "speed_mps": 50, "remote_id": False, "rcs_m2": 0.2,
        "sound": {"f0_hz": 117, "level_db_1m": 110},  # MD550 two-stroke ~7000 rpm, "moped"
        "links": [
            {"name": "lte", "tx": "self", "band_mhz": (1710.0, 1785.0), "bw_mhz": 5, "eirp_dbm": 23,
             "duty": 0.005, "hop": False, "sig_class": "LTE uplink"},
        ],
    },
    "gerbera": {  # cheap decoy with a Shahed-like silhouette: smaller, quieter, usually radio-silent
        "kind": "drone", "shape": "delta", "span_m": 2.0, "speed_mps": 45, "remote_id": False, "rcs_m2": 0.08,
        "sound": {"f0_hz": 150, "level_db_1m": 98},
        "links": [],
    },
    "orlan10": {  # reconnaissance; hopping datalink reported in 850-930 MHz
        "kind": "drone", "shape": "fixed_wing", "span_m": 3.1, "speed_mps": 30, "remote_id": False, "rcs_m2": 0.2,
        "sound": {"f0_hz": 95, "level_db_1m": 95},  # small gasoline pusher
        "links": [
            {"name": "datalink", "tx": "self", "band_mhz": (850.0, 930.0), "bw_mhz": 1.0, "eirp_dbm": 30,
             "duty": 0.5, "hop": True, "sig_class": "Orlan datalink FHSS"},
        ],
    },
    "zala": {  # electric reconnaissance UAS (ZALA 421 class): quiet; control reported in 867-872 MHz
        "kind": "drone", "shape": "fixed_wing", "span_m": 1.8, "speed_mps": 22, "remote_id": False, "rcs_m2": 0.05,
        "sound": {"f0_hz": 180, "level_db_1m": 80},
        "links": [
            {"name": "datalink", "tx": "self", "band_mhz": (867.0, 872.0), "bw_mhz": 0.5, "eirp_dbm": 27,
             "duty": 0.4, "hop": True, "sig_class": "ZALA datalink"},
        ],
    },
    "supercam": {  # electric reconnaissance UAS (S350 class): control reported in 976.5-1222 MHz
        "kind": "drone", "shape": "fixed_wing", "span_m": 3.2, "speed_mps": 25, "remote_id": False, "rcs_m2": 0.1,
        "sound": {"f0_hz": 170, "level_db_1m": 82},
        "links": [
            {"name": "datalink", "tx": "self", "band_mhz": (976.5, 1222.0), "bw_mhz": 2.0, "eirp_dbm": 30,
             "duty": 0.4, "hop": True, "sig_class": "Supercam datalink"},
        ],
    },
    # ---- Ukrainian response assets (generic) ----
    "interceptor": {  # generic interceptor drone (public examples: Octopus, JEDI); fast quad, digital video
        "kind": "drone", "shape": "quad", "span_m": 0.45, "speed_mps": 60, "remote_id": False, "rcs_m2": 0.01,
        "sound": {"f0_hz": 650, "level_db_1m": 90},
        "links": [
            {"name": "video", "tx": "self", "band_mhz": (5645.0, 5930.0), "channels": _VIDEO_58, "bw_mhz": 20,
             "eirp_dbm": 27, "duty": 1.0, "hop": False, "sig_class": "Digital FPV video"},
            {"name": "control", "tx": "operator", "band_mhz": (2400.0, 2480.0), "bw_mhz": 0.8, "eirp_dbm": 27,
             "duty": 0.6, "hop": True, "sig_class": "ELRS 2.4 FHSS"},
        ],
    },
    "ad_team": {"kind": "response", "label": "Mobile air-defence team", "height_m": 2.0, "links": []},
    "ad_battery": {"kind": "response", "label": "Air-defence battery", "height_m": 4.0, "links": []},
    "site": {"kind": "site", "label": "Protected site", "height_m": 0.0, "links": []},
    # ---- everything else in the sky and on the ground ----
    "geese": {  # migrating flock: clutter for cameras, mics and radar
        "kind": "bird", "shape": "flock", "span_m": 1.6, "speed_mps": 15, "remote_id": False, "rcs_m2": 0.05,
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

# Variants from data/assets.json: same physics as their base archetype, their own label.
CATALOG["lancet"] = {  # loitering munition archetype; control reported in 867-872 / 902-928 MHz
    "kind": "drone", "shape": "fixed_wing", "span_m": 1.0, "speed_mps": 30, "remote_id": False, "rcs_m2": 0.03,
    "sound": {"f0_hz": 210, "level_db_1m": 80},
    "links": [{"name": "datalink", "tx": "self", "band_mhz": (867.0, 872.0), "bw_mhz": 0.5, "eirp_dbm": 27,
               "duty": 0.5, "hop": True, "sig_class": "ZALA datalink"}],
}
for _type, _base, _label in [
    ("octopus", "interceptor", "Octopus interceptor drone"), ("jedi", "interceptor", "JEDI interceptor drone"),
    ("handheld_team", "ad_team", "Ground air-defence team"),
    ("patriot", "ad_battery", "Patriot"), ("iris_t", "ad_battery", "IRIS-T"), ("nasams", "ad_battery", "NASAMS"),
    ("power_station", "site", "Fictional power station"), ("water_works", "site", "Fictional water works"),
    ("hospital", "site", "Fictional hospital"),
]:
    CATALOG[_type] = {**CATALOG[_base], "label": _label, **({"display_only": True} if _type in ("patriot", "iris_t", "nasams") else {})}

# Names used by data/assets.json and data/scenario_presets.json -> OASIS names.
ALIASES = {
    "geran_shahed": "shahed136", "orlan_10": "orlan10", "interceptor_drone": "interceptor",
    "rf_receiver": "rf_df", "eo_ir_camera": "camera", "acoustic": "microphone",
    "central_valley": "ros-valley", "kharkiv_ne": "kupiansk-oskil", "border_sector": "vovchansk-border",
    "lost_contact": "lost-contact",
}
