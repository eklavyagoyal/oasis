"""Publish finished runs for browsing: each gets its own console, its log book and its raw files.

    uv run python scripts/publish_runs.py <built_console_dir> [out/<name> ...]   # default: every audited out/*

<built_console_dir> is the console's build output (vite build). Runs land in <dir>/runs/<name>/ next to
an index page. The console bundle is shared through symlinks, so a run adds only its data and media.
The hero (out/ros-valley) is the console at the site root, so it is listed but not copied.
"""
import html
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mirrorworld import logbook  # noqa: E402
from mirrorworld.config import coord_label, load  # noqa: E402

HERO = "ros-valley"
STYLE = """<style>
:root{color-scheme:dark;--bg:#07090c;--fg:#d8dee6;--dim:#7d8794;--line:#1c232c;--acc:#e8b04a}
body{background:var(--bg);color:var(--fg);font:14px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;margin:0;padding:24px 16px}
main{max-width:1100px;margin:auto}h1{font-size:20px;letter-spacing:.04em}h2{font-size:15px;color:var(--acc);margin-top:28px}
table{border-collapse:collapse;width:100%;overflow-x:auto;display:block}td,th{border-bottom:1px solid var(--line);padding:5px 8px;text-align:left;vertical-align:top}
th{color:var(--dim);font-weight:500}a{color:var(--acc)}p{color:var(--dim)}b{color:var(--fg)}
</style>"""


def md_html(text: str) -> str:
    """The log book's own markdown subset (headings, tables, bold, paragraphs), escaped."""
    out, rows = [], []

    def flush():
        cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows
                 if not re.fullmatch(r"\|[-| ]+\|", r.strip())]
        if cells:
            out.append("<table>" + "".join(
                "<tr>" + "".join(f"<{'th' if i == 0 else 'td'}>{c}</{'th' if i == 0 else 'td'}>" for c in row) + "</tr>"
                for i, row in enumerate(cells)) + "</table>")
        rows.clear()

    for line in text.splitlines():
        h = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html.escape(line, quote=False))
        if line.startswith("|"):
            rows.append(h)
            continue
        flush()
        if line.startswith("## "):
            out.append(f"<h2>{h[3:]}</h2>")
        elif line.startswith("# "):
            out.append(f"<h1>{h[2:]}</h1>")
        elif line.strip():
            out.append(f"<p>{h}</p>")
    flush()
    return "\n".join(out)


def page(title: str, body: str) -> str:
    return (f"<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport "
            f"content='width=device-width,initial-scale=1'><title>{html.escape(title)}</title>{STYLE}</head>"
            f"<body><main>{body}</main></body></html>")


def link(path: Path, target: Path):
    if not path.is_symlink() and not path.exists():
        path.symlink_to(target)


def publish(out: Path, site: Path) -> dict:
    cfg = load(out / "scenario.yaml")
    dest = site / "runs" / out.name
    dest.mkdir(parents=True, exist_ok=True)
    book = logbook.write(out)
    (dest / "logbook.html").write_text(page(f"Log book {out.name}", md_html(book.read_text())))
    link(dest / "raw", out.resolve())
    if out.name != HERO:
        if not (out / "dashboard" / "data.js").exists():  # bakes the terrain texture + asset layer
            r = subprocess.run([sys.executable, "-m", "mirrorworld", "dash", str(out)], cwd=ROOT,
                               capture_output=True, text=True)
            if r.returncode:
                print(f"warning: {out.name}: dash bake failed, console without texture/assets:\n{r.stderr[-800:]}",
                      file=sys.stderr)
        subprocess.run([sys.executable, str(ROOT / "dashboard/scripts/export_data.py"), str(out),
                        "--output", str(dest)], cwd=ROOT, check=True, capture_output=True, text=True)
        for name in ("index.html", "assets", "cesium", "icons"):
            link(dest / name, Path("../..") / name)
    audit = json.loads((out / "audit.json").read_text())["summary"] if (out / "audit.json").exists() else None
    site_key = out / "answer_key" / "C2-01_site.csv"
    fates = {}
    if site_key.exists():
        import pandas as pd
        for r in pd.read_csv(site_key, keep_default_na=False).to_dict("records"):
            fate = "intercepted" if r.get("ended_at_rendezvous") == "yes" else r.get("truth_status", "")
            fates[fate] = fates.get(fate, 0) + 1
    return {"name": out.name, "label": coord_label(cfg.area.lat, cfg.area.lon), "seed": cfg.seed,
            "start": f"{cfg.start:%d %b %Y %H:%M} UTC", "minutes": round(cfg.duration_s / 60),
            "hostiles": sum(o.side == "hostile" and bool(o.path) for o in cfg.objects),
            "types": sorted({o.type for o in cfg.objects if o.side == "hostile" and o.path}),
            "fates": fates, "audit": audit,
            "console": "../../" if out.name == HERO else f"{out.name}/"}


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    site = Path(sys.argv[1]).resolve()
    outs = [Path(p) for p in sys.argv[2:]] or sorted(p.parent for p in (ROOT / "out").glob("*/audit.json"))
    runs = []
    for out in outs:
        try:
            runs.append(publish(out, site))
            print(f"published {out.name}")
        except Exception as exc:  # one broken run must not hide the others; say which and why
            print(f"error: {out.name}: {exc}", file=sys.stderr)
    rows = "".join(
        f"<tr><td><b>{html.escape(r['name'])}</b><br>{html.escape(r['label'])} · seed {r['seed']}<br>"
        f"{html.escape(r['start'])} · {r['minutes']} min</td>"
        f"<td>{r['hostiles']} hostile<br>{html.escape(', '.join(r['types']))}</td>"
        f"<td>{html.escape(', '.join(f'{v} {k}' for k, v in r['fates'].items()) or '—')}</td>"
        f"<td>{(str(r['audit']['pass']) + ' pass · ' + str(r['audit']['fail']) + ' fail') if r['audit'] else '—'}</td>"
        f"<td><a href='{r['console']}'>console</a><br><a href='{r['name']}/logbook.html'>log book</a><br>"
        f"<a href='{r['name']}/raw/'>raw files</a></td></tr>" for r in runs)
    body = ("<h1>OASIS runs</h1><p>Each row is one generated scenario. Within a sector the built world is fixed "
            "(protected site, air-defence positions, receiver masts and their calibration, microphones); the template "
            "and seed change only what moves. Every run carries its truth, every sensor's files, answer keys, a log "
            "book and the independent audit.</p><table><tr><th>run</th><th>air picture</th><th>truth outcome at the "
            f"site</th><th>audit</th><th>open</th></tr>{rows}</table>")
    (site / "runs" / "index.html").write_text(page("OASIS runs", body))
    print(f"index: {site / 'runs' / 'index.html'} ({len(runs)} runs)")


if __name__ == "__main__":
    main()
