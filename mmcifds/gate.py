import json
from pathlib import Path


class GateInputError(ValueError):
    pass


def load_results(path):
    try:
        rows = [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
        return {r["case"]: bool(r["passed"]) for r in rows}
    except FileNotFoundError:
        raise GateInputError(f"{path} not found. Run `python -m mmcifds eval SRC {path}` first.") from None
    except (json.JSONDecodeError, KeyError, TypeError):
        raise GateInputError(f"{path} is not eval results. Each line needs a case and a passed field.") from None


def write_baseline(results, path):
    Path(path).write_text(json.dumps({"passing": sorted(c for c, ok in results.items() if ok)}, indent=2) + "\n")


def check(results, baseline_path, min_pass_rate=0.0):
    """Return a list of reasons to block a release. Empty means the gate is open."""
    try:
        passing = json.loads(Path(baseline_path).read_text())["passing"]
    except FileNotFoundError:
        raise GateInputError(f"{baseline_path} not found. Create it from a release you trust: python -m mmcifds gate RESULTS --write-baseline {baseline_path}") from None
    except (json.JSONDecodeError, KeyError, TypeError):
        raise GateInputError(f"{baseline_path} is not a baseline file. Recreate it with --write-baseline.") from None
    reasons = []
    for case in passing:
        if case not in results:
            reasons.append(f"{case}: passed in the baseline and is missing from this run")
        elif not results[case]:
            reasons.append(f"{case}: passed in the baseline and fails now")
    if not results:
        reasons.append("no cases in this run")
    elif sum(results.values()) / len(results) < min_pass_rate:
        reasons.append(f"pass rate {sum(results.values()) / len(results):.3f} is below the minimum {min_pass_rate:.3f}")
    return reasons
