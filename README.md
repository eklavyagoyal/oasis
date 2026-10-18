# OASIS

Synthetic aerial defence scenarios over real Ukrainian terrain: the ground truth, plus the data every sensor would have recorded, with each record traced back to the object that produced it.

Built for the "Mirror World" synthetic defence scenario generator challenge. Work in progress.

## Automatic scenario records

Run `uv run python generate_scenario.py --seed 42 --preset intercepted`, or omit
the seed and preset for a random run. The command uses the shared OASIS builder,
sensors, and audit. Each run automatically saves `scenario.yaml`, truth tracks,
sensor files, answer keys, `run.json`, and `summary.json` under `out/<run-name>/`.
The summary contains the outcome, event log, sensor observations, and links to
the truth through the answer key. `run.json` lists the files produced by the
sensor modules present in that run, so new team modules join the record without
changing this command.

## Five fixed demos

Run `uv run python run_showcase.py all --serve` to generate five preplanned
scenarios and browse their replay dashboards at `http://localhost:8765/`.
See [scenarios/showcase/README.md](scenarios/showcase/README.md) for the
aircraft, protected sites, and expected outcomes in each one.
