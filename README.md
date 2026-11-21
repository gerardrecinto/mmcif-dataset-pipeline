# mmcifds

Turns a folder of mmCIF files into one JSONL record per protein chain (sequence and C-alpha coordinates). It splits work across SLURM array tasks or Kubernetes indexed Job pods, and a killed run picks up where it stopped. Python 3.9+, standard library only.

## Run it

```sh
git clone https://github.com/gerardrecinto/mmcif-dataset-pipeline && cd mmcif-dataset-pipeline
python3 -m mmcifds build tests/data out
python3 -m mmcifds stats out
```

To install it as a command instead of running from a clone: `pip install git+https://github.com/gerardrecinto/mmcif-dataset-pipeline`, then use `mmcifds` in place of `python3 -m mmcifds`. For Kubernetes, `docker build -t mmcifds:0.1.0 .` makes the image the Job needs; push it to your registry and set it in `deploy/k8s/job.yaml`. The image runs as a non-root user and works with a read-only root filesystem, so only the output volume has to be writable.

Each finished file leaves `out/records/<id>.jsonl`. A file that cannot be parsed leaves `out/failed/<id>.txt` with the reason, the command exits 1, and the next run retries only the failures.

## Scale out

- SLURM: `sbatch --array=0-15 deploy/slurm/build.sbatch /data/cif /data/out`
- Kubernetes: build and push the image, then in `deploy/k8s/job.yaml` set `image`, and set `completions` and `NUM_SHARDS` to the same number. Then `kubectl apply -f deploy/k8s/job.yaml`. Without a pushed image the pods stay in `ImagePullBackOff`.
- Anywhere else: `--shard I --num-shards N`

A file belongs to shard `crc32(name) % N`, so every file is handled by exactly one task. To roll back, delete `out/`; inputs are never modified.

## What it does not do yet

Model 1 only, ATOM records only, first alternate location only. No ligands, no side chains, no tensor output, no sequence-database joins. Residues outside the 20 standard amino acids become `X`. The tests use one real entry (1CRN from the RCSB Protein Data Bank); throughput on a large archive has not been measured.
