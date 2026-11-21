"""The SLURM and Kubernetes templates, exercised the way the schedulers run them."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(__file__).parent / "data"
NAMES = [f"e{i:02d}" for i in range(40)]


def corpus(tmp_path):
    """40 inputs, so the shards have something to divide. They are copies of one real entry."""
    src = tmp_path / "in"
    src.mkdir()
    for n in NAMES:
        (src / f"{n}.cif").write_bytes((DATA / "1CRN.cif").read_bytes())
    return src


def run_cli(src, out, env_extra, script=None):
    env = {**os.environ, **env_extra}
    # the sbatch script calls python3; make sure that is the interpreter running the tests
    env["PATH"] = os.path.dirname(sys.executable) + os.pathsep + env.get("PATH", "")
    env["PYTHONPATH"] = str(ROOT)
    cmd = ["bash", str(ROOT / "deploy/slurm/build.sbatch"), str(src), str(out)] if script else [
        sys.executable, "-m", "mmcifds", "build", str(src), str(out)]
    return subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=ROOT)


def records(out):
    return sorted(p.stem for p in (Path(out) / "records").glob("*.jsonl"))


def test_k8s_indexed_job_numbers_agree():
    yaml = pytest.importorskip("yaml")
    job = yaml.safe_load((ROOT / "deploy/k8s/job.yaml").read_text())
    spec = job["spec"]
    env = {e["name"]: e["value"] for e in spec["template"]["spec"]["containers"][0]["env"]}
    assert spec["completionMode"] == "Indexed"
    assert spec["completions"] == spec["parallelism"] == int(env["NUM_SHARDS"])


def test_k8s_indexed_job_every_file_is_built_exactly_once(tmp_path):
    yaml = pytest.importorskip("yaml")
    job = yaml.safe_load((ROOT / "deploy/k8s/job.yaml").read_text())
    n = job["spec"]["completions"]
    src = corpus(tmp_path)
    for index in range(n):
        r = run_cli(src, tmp_path / "out", {"JOB_COMPLETION_INDEX": str(index), "NUM_SHARDS": str(n)})
        assert r.returncode == 0, r.stderr
    assert records(tmp_path / "out") == NAMES
    rerun = run_cli(src, tmp_path / "out", {"JOB_COMPLETION_INDEX": "0", "NUM_SHARDS": str(n)})
    assert json.loads(rerun.stdout)["done"] == 0


def test_slurm_array_script_every_file_is_built_exactly_once(tmp_path):
    src = corpus(tmp_path)
    for task in range(3):
        r = run_cli(src, tmp_path / "out", {"SLURM_ARRAY_TASK_ID": str(task), "SLURM_ARRAY_TASK_COUNT": "3"}, script=True)
        assert r.returncode == 0, r.stderr
    assert records(tmp_path / "out") == NAMES


def test_slurm_script_without_an_array_says_how_to_submit(tmp_path):
    env = {k: v for k, v in os.environ.items() if not k.startswith("SLURM_")}
    r = subprocess.run(["bash", str(ROOT / "deploy/slurm/build.sbatch"), str(DATA), str(tmp_path / "o")],
                       capture_output=True, text=True, env=env, cwd=ROOT)
    assert r.returncode != 0 and "--array=0-N" in r.stderr
