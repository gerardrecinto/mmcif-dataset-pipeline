import json
import os
import zlib
from pathlib import Path

from .parse import ParseError, chains


def shard_env():
    """Shard index and count from SLURM array or Kubernetes indexed Job variables."""
    if "SLURM_ARRAY_TASK_ID" in os.environ:
        return int(os.environ["SLURM_ARRAY_TASK_ID"]), int(os.environ.get("NUM_SHARDS", os.environ.get("SLURM_ARRAY_TASK_COUNT", "1")))
    if "JOB_COMPLETION_INDEX" in os.environ:
        return int(os.environ["JOB_COMPLETION_INDEX"]), int(os.environ.get("NUM_SHARDS", "1"))
    return 0, 1


def in_shard(name, index, count):
    return zlib.crc32(name.encode()) % count == index


def write_atomic(path, data):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(data)
    os.replace(tmp, path)


def build(src, out, index=0, count=1, min_len=1):
    """Convert every .cif in src that belongs to this shard. Safe to rerun after a kill.

    A finished file leaves out/records/<id>.jsonl. A rerun skips it. A file that
    cannot be parsed leaves out/failed/<id>.txt with the reason and is retried
    on the next run.
    """
    src, out = Path(src), Path(out)
    rec_dir, fail_dir = out / "records", out / "failed"
    rec_dir.mkdir(parents=True, exist_ok=True)
    fail_dir.mkdir(parents=True, exist_ok=True)
    stats = {"done": 0, "skipped": 0, "failed": 0, "chains": 0}
    files = sorted(p for p in src.iterdir() if p.suffix.lower() == ".cif" and in_shard(p.name, index, count))
    for p in files:
        rec, fail = rec_dir / f"{p.stem}.jsonl", fail_dir / f"{p.stem}.txt"
        if rec.exists():
            stats["skipped"] += 1
            continue
        try:
            cs = chains(p.read_text())
            rows = [
                json.dumps({"entry": p.stem, "chain": k, "length": len(v["sequence"]), **v})
                for k, v in sorted(cs.items())
                if len(v["sequence"]) >= min_len
            ]
            if not rows:
                raise ParseError(f"no chains with at least {min_len} residues")
        except (ParseError, OSError, KeyError, ValueError) as e:
            write_atomic(fail, f"{type(e).__name__}: {e}\n")
            stats["failed"] += 1
            continue
        write_atomic(rec, "\n".join(rows) + "\n")
        fail.unlink(missing_ok=True)
        stats["done"] += 1
        stats["chains"] += len(rows)
    return stats


def summarize(out):
    out = Path(out)
    recs = list((out / "records").glob("*.jsonl"))
    chains_n = residues = 0
    for r in recs:
        for line in r.read_text().splitlines():
            chains_n += 1
            residues += json.loads(line)["length"]
    failed = sorted(p.stem for p in (out / "failed").glob("*.txt"))
    return {"files": len(recs), "chains": chains_n, "residues": residues, "failed": failed}
