"""Run one fixed showcase scenario (or all five) and export its replay dashboard."""

import argparse
import json
import shutil
from pathlib import Path

import yaml

from generate_scenario import run_oasis, summarise
from mirrorworld.catalog import CATALOG
from mirrorworld.dashboard import export, serve


ROOT = Path(__file__).resolve().parent
SCENARIOS = ROOT / "scenarios" / "showcase"
EXPECTED = {
    "01-shahed-power": (3, 1, 2),
    "02-decoy-water": (4, 2, 2),
    "03-recon-power": (4, 1, 1),
    "04-low-fpv-water": (4, 2, 2),
    "05-lost-contact-hospital": (2, 0, 0),
}
TITLES = {
    "01-shahed-power": "Shahed salvo · power station",
    "02-decoy-water": "Decoy screen · water works",
    "03-recon-power": "Recon cover · power station",
    "04-low-fpv-water": "Low FPV tracks · water works",
    "05-lost-contact-hospital": "Lost contact · hospital",
}


def run(name):
    source = SCENARIOS / f"{name}.yaml"
    cfg = yaml.safe_load(source.read_text())
    out = ROOT / "out" / "showcase" / name
    if out.exists():
        shutil.rmtree(out)
    run_oasis(source, out)
    site = next(o for o in cfg["objects"] if CATALOG[o["type"]]["kind"] == "site")
    hostile_types = sorted({o["type"] for o in cfg["objects"]
                            if o["side"] == "hostile" and CATALOG[o["type"]]["kind"] == "drone"})
    summary = summarise(out, {"showcase": name, "site_type": site["type"],
                              "drone_types": hostile_types}, cfg["seed"])
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    export(out)
    record = json.loads((out / "run.json").read_text())
    record["artifacts"] = sorted(str(p.relative_to(out)) for p in out.rglob("*")
                                 if p.is_file() and p.name != "run.json")
    (out / "run.json").write_text(json.dumps(record, indent=2) + "\n")

    hostiles = summary["outcome"]["hostiles"]
    actual = (len(hostiles), sum("intercepted_by" in h for h in hostiles.values()),
              sum(h.get("site") == "reached" for h in hostiles.values()))
    expected = EXPECTED[name]
    print(f"{name}: hostiles/intercepted/site reached = {actual}; expected {expected}; "
          f"{'OK' if actual == expected else 'MISMATCH'}")
    print(f"Audit: {summary['audit']}")
    print(f"Replay: {out / 'dashboard' / 'index.html'}")
    if actual != expected:
        raise RuntimeError(f"{name}: scenario did not produce its planned outcomes")
    return out


def write_index():
    root = ROOT / "out" / "showcase"
    links = "\n".join(
        f'<a href="{name}/dashboard/"><strong>{TITLES[name]}</strong><small>{name}</small></a>'
        for name in EXPECTED if (root / name / "dashboard" / "index.html").exists()
    )
    (root / "index.html").write_text(
        '<!doctype html><html lang="en"><meta charset="utf-8"><title>OASIS showcase</title>'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<style>body{font:16px system-ui;background:#0b111b;color:#edf3fb;max-width:760px;'
        'margin:6vh auto;padding:0 20px}h1{letter-spacing:.08em}p{color:#9eb0c5}'
        'a{display:block;padding:18px 22px;margin:12px 0;background:#172232;color:inherit;'
        'text-decoration:none;border:1px solid #344862;border-radius:12px}a:hover{border-color:#ffb000}'
        'small{display:block;color:#9eb0c5;margin-top:5px}</style>'
        '<h1>OASIS · five fixed replays</h1><p>Select a synthetic scenario.</p>'
        + links + '</html>\n'
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("scenario", choices=[*EXPECTED, "all"])
    ap.add_argument("--serve", action="store_true", help="serve one completed replay at localhost")
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    for name in EXPECTED if args.scenario == "all" else [args.scenario]:
        out = run(name)
    write_index()
    if args.serve:
        serve(ROOT / "out" / "showcase" if args.scenario == "all" else out, args.port)


if __name__ == "__main__":
    main()
