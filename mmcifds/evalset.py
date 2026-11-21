import json
from pathlib import Path

from .parse import ParseError, chain_entities, chains, entity_sequences


def run_eval(src, results_path):
    """Check each chain's parsed sequence against the file's own _entity_poly_seq.

    One case per chain, named ENTRY:CHAIN. A file that cannot be read gives one
    failed case named ENTRY. Writes one JSON line per case and returns the counts.
    """
    cases = []
    for p in sorted(Path(src).glob("*.cif")):
        try:
            text = p.read_text()
            got, ents, want = chains(text), chain_entities(text), entity_sequences(text)
        except (ParseError, OSError, ValueError) as e:
            cases.append({"case": p.stem, "passed": False, "detail": f"{type(e).__name__}: {e}"})
            continue
        for chain, rec in sorted(got.items()):
            expected = want.get(ents.get(chain), "")
            ok = rec["sequence"] == expected
            detail = "" if ok else f"parsed {len(rec['sequence'])} residues, entity has {len(expected)}"
            cases.append({"case": f"{p.stem}:{chain}", "passed": ok, "detail": detail})
    Path(results_path).write_text("".join(json.dumps(c) + "\n" for c in cases))
    passed = sum(c["passed"] for c in cases)
    return {"cases": len(cases), "passed": passed, "pass_rate": round(passed / len(cases), 4) if cases else 0.0}
