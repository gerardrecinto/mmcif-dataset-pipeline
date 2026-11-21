#!/bin/bash
# Usage: sbatch --array=0-15 -e logs/%A_%a.err deploy/slurm/build.sbatch /data/cif /data/out
# Each array task takes the files that hash to its index. Resubmit the same command
# after a failure or preemption; finished files are skipped.
#SBATCH --job-name=mmcifds
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=02:00:00
#SBATCH --requeue
set -euo pipefail
: "${SLURM_ARRAY_TASK_COUNT:?submit with --array=0-N so the shard count is known}"
python3 -m mmcifds build "$1" "$2"
