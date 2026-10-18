"""Write the live build-status README on the `status` branch (main's README stays untouched).

    uv run python scripts/status.py                      # preview: prints what changed since the last update
    uv run python scripts/status.py --publish "note" ... # regenerate, commit and push to origin/status

Facts come from the repo itself: self-checks run now, sensor modules present, the hero audit, and the
commits on main since the previous update. Notes are one-line human summaries of what changed.
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WT = ROOT.parent / "mw-status"  # git worktree checked out on branch `status`


def sh(*cmd, cwd=ROOT):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=300).stdout.strip()


def ensure_worktree():
    if not WT.exists():
        if sh("git", "branch", "--list", "status"):
            sh("git", "worktree", "add", str(WT), "status")
        else:
            sh("git", "worktree", "add", "-b", "status", str(WT), "main")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish", nargs="*", metavar="NOTE", help="publish with these one-line notes")
    args = ap.parse_args()
    ensure_worktree()
    stamp = WT / ".last_update"
    since = stamp.read_text().strip() if stamp.exists() else "6 hours ago"
    new = sh("git", "log", "main", f"--since={since}", "--no-merges", "--format=- %s (%h)")
    if args.publish is None:
        print(f"commits on main since {since}:\n{new or '(none)'}")
        return

    tests = {}
    for t in sorted((ROOT / "tests").glob("test_*.py")):
        r = subprocess.run([sys.executable, str(t)], cwd=ROOT, capture_output=True, text=True, timeout=600)
        tests[t.stem[5:]] = "✅" if r.returncode == 0 else "❌"
    sensors = sorted(p.stem for p in (ROOT / "mirrorworld" / "sensors").glob("*.py") if p.stem != "__init__")
    audit_p = ROOT / "out" / "ros-valley" / "audit.json"
    audit = json.loads(audit_p.read_text()) if audit_p.exists() else None
    now = datetime.now().astimezone()

    lines = [f"# OASIS: live build status", "",
             f"_Updated {now:%H:%M %Z, %d %b %Y}. Auto-generated on the `status` branch; `main` holds the product._", "",
             "**OASIS** generates synthetic aerial defence scenarios over real Ukrainian terrain: one true world, "
             "every sensor's physically faithful recordings, and an answer key tracing each record to its cause.", ""]
    if args.publish:
        lines += ["## What changed since the last update", ""] + [f"- {n}" for n in args.publish] + [""]
    lines += ["## Commits on main since the last update", "", new or "_(none)_", "",
              "## Sensor modules on main", "", ", ".join(f"`{s}`" for s in sensors), "",
              "## Self-checks (run now)", "", "| check | result |", "|---|---|"]
    lines += [f"| `{k}` | {v} |" for k, v in tests.items()] + [""]
    if audit:
        s = audit["summary"]
        lines += ["## Hero audit (independent physics checks)", "",
                  f"**{s['pass']} pass · {s['fail']} fail · {s['skip']} skip**", "", "| check | status | value |", "|---|---|---|"]
        lines += [f"| {c['name']} | {c['status']} | {c['value'] if c['value'] is not None else '—'} |" for c in audit["checks"]]
        if audit.get("baseline"):
            b = audit["baseline"]["summary"]
            lines += ["", f"One-shot LLM baseline on the same window: **{b['pass']} pass · {b['fail']} fail · {b['skip']} skip**"]
        lines.append("")
    lines += ["## Run it", "", "```", "uv sync",
              "uv run python -m mirrorworld run scenarios/ros-valley.yaml --skip-missing",
              "uv run python -m mirrorworld audit out/ros-valley",
              "uv run python -m mirrorworld dash out/ros-valley --serve",
              "uv run python generate_scenario.py --matrix --seed 1", "```", ""]
    (WT / "README.md").write_text("\n".join(lines))
    stamp.write_text(now.isoformat(timespec="seconds"))
    sh("git", "add", "README.md", ".last_update", cwd=WT)
    sh("git", "commit", "-q", "-m", f"status: {now:%H:%M}", cwd=WT)
    print(sh("git", "push", "-q", "-u", "origin", "status", cwd=WT) or f"published status {now:%H:%M}")


if __name__ == "__main__":
    main()
