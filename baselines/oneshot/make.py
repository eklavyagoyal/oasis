"""Generate the one-shot LLM baseline: one OpenAI call, our file layout, raw response kept.

    uv run python baselines/oneshot/make.py

Needs OPENAI_API_KEY (env or repo .env); model from OPENAI_MODEL (default: a strong current
OpenAI model). Writes baselines/oneshot/out/ros-valley-oneshot/ and exits 2 without a key.
The auditor handles a missing baseline dir gracefully, so this is optional for the pitch.
"""
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))  # run as a plain script from anywhere
PROMPT = Path(__file__).resolve().parent / "PROMPT.md"
OUT = Path(__file__).resolve().parent / "out" / "ros-valley-oneshot"
DEFAULT_MODEL = "gpt-5.5"
TIMEOUT_S = 300.0
ATTEMPTS = 3

FILES = [  # the exact layout the prompt asks for; nothing else is written
    "truth/tracks.csv",
    "sensors/RF1/detections.csv",
    "sensors/RF2/detections.csv",
    "answer_key/RF1.csv",
    "answer_key/RF2.csv",
    "fused/fixes.csv",
    "answer_key/fused.csv",
]


def _fail(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(2)


def _api_key():
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        return key
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("OPENAI_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def _require_hero():
    """site.json + scenario.yaml come from our real run so the geometry is comparable."""
    run = ROOT / "out" / "ros-valley"
    sites = [run / "sensors" / s / "site.json" for s in ("RF1", "RF2")]
    if not all(p.exists() for p in sites):
        _fail("out/ros-valley/ is missing sensor site.json files — run the hero first:\n"
              "  uv run python -m mirrorworld run scenarios/ros-valley.yaml --skip-missing")
    return (run / "scenario.yaml") if (run / "scenario.yaml").exists() else ROOT / "scenarios" / "ros-valley.yaml", run


def _prompt_text(yaml_path):
    from mirrorworld.catalog import CATALOG
    text = PROMPT.read_text()
    text = text.replace("{SCENARIO_YAML}", yaml_path.read_text().strip())
    text = text.replace("{CATALOG_JSON}", json.dumps(CATALOG, indent=1))
    return text


def _call(model, prompt):
    from openai import OpenAI
    client = OpenAI(timeout=TIMEOUT_S, max_retries=0)  # retries are ours, bounded and visible
    last = None
    for attempt in range(ATTEMPTS):
        try:
            r = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            return r
        except Exception as e:  # noqa: BLE001 — every failure is reported, none swallowed
            last = e
            if "model" in str(e).lower() and ("not found" in str(e).lower() or "does not exist" in str(e).lower()):
                sys.exit(f"error: model {model!r} not available ({e}) — set OPENAI_MODEL to a valid chat model id")
            if attempt < ATTEMPTS - 1:
                wait = 2.0 * 2 ** attempt
                print(f"warning: attempt {attempt + 1} failed ({e}); retrying in {wait:.0f} s", file=sys.stderr)
                time.sleep(wait)
    sys.exit(f"error: OpenAI call failed after {ATTEMPTS} attempts: {last}")


def main():
    key = _api_key()
    if not key:
        _fail("no OPENAI_API_KEY in the environment or repo .env — cannot generate the "
              "one-shot baseline. The audit still runs: `python -m mirrorworld audit out/ros-valley`.")
    os.environ["OPENAI_API_KEY"] = key
    model = os.environ.get("OPENAI_MODEL", DEFAULT_MODEL)
    yaml_path, run = _require_hero()

    resp = _call(model, _prompt_text(yaml_path))
    text = resp.choices[0].message.content
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "raw.json").write_text(json.dumps({
        "model": model, "usage": resp.usage.model_dump() if resp.usage else None, "text": text}, indent=2))

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        sys.exit(f"error: response is not valid JSON ({e}); see {OUT / 'raw.json'}")
    missing = [f for f in FILES if f not in data]
    if missing:
        sys.exit(f"error: response is missing files {missing}; see {OUT / 'raw.json'}")

    for rel in FILES:
        p = OUT / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(data[rel])
    import shutil
    shutil.copyfile(yaml_path, OUT / "scenario.yaml")
    for s in ("RF1", "RF2"):
        (OUT / "sensors" / s).mkdir(parents=True, exist_ok=True)
        shutil.copyfile(run / "sensors" / s / "site.json", OUT / "sensors" / s / "site.json")

    print(f"wrote {OUT}/ ({len(FILES)} files, model {model}); raw response in raw.json")
    print(f"compare: uv run python -m mirrorworld audit out/ros-valley --baseline {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
