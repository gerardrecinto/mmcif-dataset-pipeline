import shlex

AA = {
    "ALA": "A", "ARG": "R", "ASN": "N", "ASP": "D", "CYS": "C", "GLN": "Q",
    "GLU": "E", "GLY": "G", "HIS": "H", "ILE": "I", "LEU": "L", "LYS": "K",
    "MET": "M", "PHE": "F", "PRO": "P", "SER": "S", "THR": "T", "TRP": "W",
    "TYR": "Y", "VAL": "V",
}


class ParseError(ValueError):
    pass


def atom_rows(text):
    """Yield one dict per row of the _atom_site loop."""
    lines = iter(text.splitlines())
    for line in lines:
        if line.strip() != "loop_":
            continue
        cols = []
        for line in lines:
            if line.startswith("_atom_site."):
                cols.append(line.split(".", 1)[1].strip())
            else:
                break
        if not cols:
            continue
        while True:
            if not line.strip() or line.startswith(("#", "_", "loop_", "data_")):
                return
            vals = shlex.split(line)
            if len(vals) != len(cols):
                raise ParseError(f"atom_site row has {len(vals)} values, expected {len(cols)}: {line[:60]!r}")
            yield dict(zip(cols, vals))
            line = next(lines, "")
    raise ParseError("no _atom_site loop found")


def chains(text):
    """Return {chain_id: {"sequence": str, "ca": [[x, y, z], ...]}} for model 1, ATOM records only.

    Residues that are not one of the 20 standard amino acids are written as X
    so the sequence and the C-alpha list stay the same length.
    """
    out = {}
    seen = set()
    found = False
    for r in atom_rows(text):
        found = True
        if r.get("group_PDB") != "ATOM" or r.get("pdbx_PDB_model_num", "1") != "1":
            continue
        if r.get("label_alt_id", ".") not in (".", "?", "A"):
            continue
        if r["label_atom_id"] != "CA":
            continue
        chain = r["label_asym_id"]
        key = (chain, r["label_seq_id"])
        if key in seen:
            continue
        seen.add(key)
        c = out.setdefault(chain, {"sequence": [], "ca": []})
        c["sequence"].append(AA.get(r["label_comp_id"], "X"))
        c["ca"].append([float(r["Cartn_x"]), float(r["Cartn_y"]), float(r["Cartn_z"])])
    if not found:
        raise ParseError("no _atom_site rows")
    return {k: {"sequence": "".join(v["sequence"]), "ca": v["ca"]} for k, v in out.items()}
