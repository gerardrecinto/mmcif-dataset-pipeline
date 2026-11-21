# mmcifds

Turns a folder of mmCIF files into one JSONL record per protein chain (sequence and C-alpha coordinates). It splits work across SLURM array tasks or Kubernetes indexed Job pods, and a killed run picks up where it stopped. Python 3.9+, standard library only.

## Run it

```sh
git clone https://github.com/gerardrecinto/mmcif-dataset-pipeline && cd mmcif-dataset-pipeline
python3 -m mmcifds build tests/data out
python3 -m mmcifds stats out
```

Each finished file leaves `out/records/<id>.jsonl`. A file that cannot be parsed leaves `out/failed/<id>.txt` with the reason, the command exits 1, and the next run retries only the failures.

## Scale out

- SLURM: `sbatch --array=0-15 deploy/slurm/build.sbatch /data/cif /data/out`
- Kubernetes: edit `completions` and `NUM_SHARDS` in `deploy/k8s/job.yaml`, then `kubectl apply -f`
- Anywhere else: `--shard I --num-shards N`

A file belongs to shard `crc32(name) % N`, so every file is handled by exactly one task. To roll back, delete `out/`; inputs are never modified.

## Gate a release on an eval

`eval` checks each chain's parsed sequence against the sequence the file itself declares (`_entity_poly_seq`) and writes one JSON line per chain. `gate` fails if a case that passed in the baseline fails now, or is missing.

```sh
python3 -m mmcifds eval tests/data results.jsonl
python3 -m mmcifds gate results.jsonl --baseline evals/baseline.json
```

On the four bundled entries 7 of 7 chains pass. With one residue's C-alpha row removed from 1UBQ, the gate printed `BLOCK 1UBQ:A: passed in the baseline and fails now`, `gate closed: 6/7 cases pass` and exited 1. Exit 2 means a missing or malformed file, with the command to fix it. `.github/workflows/release.yml` runs build, eval, gate and publish in that order, and publish waits for the `production` environment. The publish step only lists the files; replace it with your push. After a change you accept, rebuild the baseline with `gate results.jsonl --write-baseline evals/baseline.json` and review the diff. The eval measures parsing against the file's own declaration, not model quality.

## What it does not do yet

Model 1 only, ATOM records only, first alternate location only. No ligands, no side chains, no tensor output, no sequence-database joins. Residues outside the 20 standard amino acids become `X`. The tests use four real entries (1CRN, 1UBQ, 2LZM and 4HHB from the RCSB Protein Data Bank); throughput on a large archive has not been measured.
