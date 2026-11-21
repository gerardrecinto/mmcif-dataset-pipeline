import argparse
import json
import sys

from .evalset import run_eval
from .gate import GateInputError, check, load_results, write_baseline
from .pipeline import build, shard_env, summarize


def main(argv=None):
    ap = argparse.ArgumentParser(prog="mmcifds", description="mmCIF files to resumable chain records.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="convert .cif files in SRC into OUT/records")
    b.add_argument("src")
    b.add_argument("out")
    b.add_argument("--shard", type=int, help="shard index (default: SLURM_ARRAY_TASK_ID or JOB_COMPLETION_INDEX, else 0)")
    b.add_argument("--num-shards", type=int, help="shard count (default: NUM_SHARDS, else 1)")
    b.add_argument("--min-len", type=int, default=1, help="drop chains shorter than this")
    e = sub.add_parser("eval", help="check parsed sequences against each file's own entity sequence")
    e.add_argument("src")
    e.add_argument("results", help="JSONL file to write, one line per chain")
    g = sub.add_parser("gate", help="exit 1 if a case that passed in the baseline fails now")
    g.add_argument("results")
    g.add_argument("--baseline", help="baseline file made with --write-baseline")
    g.add_argument("--write-baseline", metavar="FILE", help="save the passing cases of this run to FILE and exit 0")
    g.add_argument("--min-pass-rate", type=float, default=0.0)
    s = sub.add_parser("stats", help="count what is in OUT")
    s.add_argument("out")
    a = ap.parse_args(argv)

    if a.cmd == "eval":
        if not __import__("os").path.isdir(a.src):
            print(f"mmcifds: {a.src} not found. Pass the folder that holds your .cif files.", file=sys.stderr)
            return 2
        print(json.dumps(run_eval(a.src, a.results)))
        return 0
    if a.cmd == "gate":
        try:
            results = load_results(a.results)
            if a.write_baseline:
                write_baseline(results, a.write_baseline)
                print(f"mmcifds: saved {sum(results.values())} passing cases to {a.write_baseline}.")
                return 0
            if not a.baseline:
                print("mmcifds: pass --baseline FILE, or --write-baseline FILE to create one.", file=sys.stderr)
                return 2
            reasons = check(results, a.baseline, a.min_pass_rate)
        except GateInputError as e:
            print(f"mmcifds: {e}", file=sys.stderr)
            return 2
        for r in reasons:
            print(f"BLOCK {r}")
        print(f"gate {'closed' if reasons else 'open'}: {sum(results.values())}/{len(results)} cases pass")
        return 1 if reasons else 0
    if a.cmd == "stats":
        print(json.dumps(summarize(a.out), indent=2))
        return 0
    idx, cnt = shard_env()
    idx = idx if a.shard is None else a.shard
    cnt = cnt if a.num_shards is None else a.num_shards
    if not 0 <= idx < cnt:
        print(f"mmcifds: shard {idx} is outside 0..{cnt - 1}. Set --num-shards to the number of array tasks.", file=sys.stderr)
        return 2
    try:
        st = build(a.src, a.out, idx, cnt, a.min_len)
    except FileNotFoundError:
        print(f"mmcifds: {a.src} not found. Pass the folder that holds your .cif files.", file=sys.stderr)
        return 2
    print(json.dumps({"shard": idx, "of": cnt, **st}))
    if st["failed"]:
        print(f"mmcifds: {st['failed']} files failed, see {a.out}/failed/. Fix or remove them and rerun; finished files are skipped.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
