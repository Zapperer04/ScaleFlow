# ReplaySystem Documentation

## Responsibilities
Provides deterministic replayability of failure scenarios by storing random seeds, event sequences, and environment details.

## Operations
```bash
python -m simulation.replay runs/run_<timestamp>
```

## Failure Modes
- Drift in system packages or schemas could invalidate logs. Tracked via simulation environment versions.
