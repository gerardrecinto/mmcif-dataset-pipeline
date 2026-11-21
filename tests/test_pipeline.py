import json
import shutil
from pathlib import Path

from mmcifds.__main__ import main
from mmcifds.parse import chains
from mmcifds.pipeline import build, in_shard, summarize

DATA = Path(__file__).parent / "data"


def test_crambin_chain():
    c = chains((DATA / "1CRN.cif").read_text())
    assert list(c) == ["A"]
    assert c["A"]["sequence"] == "TTCCPSIVARSNFNVCRLPGTPEAICATYTGCIIIPGATCPGDYAN"
    assert len(c["A"]["sequence"]) == len(c["A"]["ca"]) == 46


def test_resume_skips_finished_and_retries_failed(tmp_path):
    src = tmp_path / "in"
    src.mkdir()
    shutil.copy(DATA / "1CRN.cif", src / "1CRN.cif")
    (src / "BAD.cif").write_text("data_BAD\n")
    out = tmp_path / "out"
    assert build(src, out)["done"] == 1
    assert (out / "failed" / "BAD.txt").exists()
    again = build(src, out)
    assert again["skipped"] == 1 and again["failed"] == 1 and again["done"] == 0
    (src / "BAD.cif").unlink()
    build(src, out)
    s = summarize(out)
    assert s["files"] == 1 and s["chains"] == 1 and s["residues"] == 46 and s["failed"] == ["BAD"]


def test_shards_cover_every_file_once(tmp_path):
    names = [f"{i:04d}.cif" for i in range(200)]
    for n in (3, 8):
        owners = [[i for i in range(n) if in_shard(x, i, n)] for x in names]
        assert all(len(o) == 1 for o in owners)


def test_cli_exit_codes(tmp_path, capsys):
    (tmp_path / "in").mkdir()
    shutil.copy(DATA / "1CRN.cif", tmp_path / "in" / "1CRN.cif")
    assert main(["build", str(tmp_path / "in"), str(tmp_path / "out")]) == 0
    assert main(["build", str(tmp_path / "nope"), str(tmp_path / "out")]) == 2
    assert main(["build", str(tmp_path / "in"), str(tmp_path / "out"), "--shard", "3", "--num-shards", "2"]) == 2
    line = json.loads(capsys.readouterr().out.splitlines()[0])
    assert line["done"] == 1


def test_unwritable_output_is_a_message_not_a_traceback(tmp_path, capsys):
    src = tmp_path / "in"
    src.mkdir()
    shutil.copy(DATA / "1CRN.cif", src / "1CRN.cif")
    blocker = tmp_path / "file"
    blocker.write_text("x")
    assert main(["build", str(src), str(blocker / "out")]) == 2
    err = capsys.readouterr().err
    assert "writable volume" in err and "Traceback" not in err
    assert main(["build", str(tmp_path / "nope"), str(tmp_path / "out")]) == 2
    assert not (tmp_path / "out").exists()
