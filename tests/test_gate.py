import json
import shutil
from pathlib import Path

from mmcifds.__main__ import main
from mmcifds.evalset import run_eval

DATA = Path(__file__).parent / "data"


def test_every_real_entry_chain_matches_its_entity_sequence(tmp_path):
    out = run_eval(DATA, tmp_path / "r.jsonl")
    rows = [json.loads(x) for x in (tmp_path / "r.jsonl").read_text().splitlines()]
    assert {r["case"] for r in rows} >= {"1CRN:A", "1UBQ:A", "2LZM:A", "4HHB:A", "4HHB:B", "4HHB:C", "4HHB:D"}
    assert out["passed"] == out["cases"], [r for r in rows if not r["passed"]]


def test_broken_file_is_one_failed_case(tmp_path):
    src = tmp_path / "in"
    src.mkdir()
    (src / "BAD.cif").write_text("data_BAD\n")
    out = run_eval(src, tmp_path / "r.jsonl")
    assert out == {"cases": 1, "passed": 0, "pass_rate": 0.0}


def test_gate_blocks_a_regression_and_a_missing_case(tmp_path, capsys):
    good = tmp_path / "good.jsonl"
    good.write_text('{"case":"a","passed":true}\n{"case":"b","passed":true}\n')
    base = tmp_path / "base.json"
    assert main(["gate", str(good), "--write-baseline", str(base)]) == 0
    assert main(["gate", str(good), "--baseline", str(base)]) == 0

    worse = tmp_path / "worse.jsonl"
    worse.write_text('{"case":"a","passed":false}\n')
    assert main(["gate", str(worse), "--baseline", str(base)]) == 1
    out = capsys.readouterr().out
    assert "a: passed in the baseline and fails now" in out and "b: passed in the baseline and is missing" in out and "gate closed" in out


def test_gate_min_pass_rate_and_input_errors(tmp_path, capsys):
    res = tmp_path / "r.jsonl"
    res.write_text('{"case":"a","passed":true}\n{"case":"b","passed":false}\n')
    base = tmp_path / "base.json"
    base.write_text('{"passing": []}')
    assert main(["gate", str(res), "--baseline", str(base), "--min-pass-rate", "0.9"]) == 1
    assert main(["gate", str(res), "--baseline", str(tmp_path / "nope.json")]) == 2
    assert main(["gate", str(tmp_path / "nope.jsonl"), "--baseline", str(base)]) == 2
    assert main(["gate", str(res)]) == 2
    err = capsys.readouterr().err
    assert "--write-baseline" in err and "mmcifds eval" in err
