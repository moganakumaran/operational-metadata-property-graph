"""Assert the model is consistent across schema, figure, table and queries.

`consistency.py` compared edge *label* sets between Figure 1 and Table 1. That
is too weak: the figure drew `owns: Principal -> Consumer`, which does not
exist in the model, and omitted `owns: Principal -> Dataset`. Both are
labelled `owns`, so a name-set comparison passed while the figure was wrong.

This file compares **endpoints**, and additionally asserts that every stored
relationship signature is exercised by something. An element no query touches
contradicts the paper's claim that no element is present that serves no query,
and that claim is load-bearing for the minimality argument.

Usage:  python3 evaluation/test_model_consistency.py
Exit 1 on any failure.
"""
from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

schema = open(os.path.join(HERE, "schema.cypher"), encoding="utf-8").read()
tex = open(os.path.join(ROOT, "paper.tex"), encoding="utf-8").read()

fails: list[str] = []


def ck(name: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))
    if not ok:
        fails.append(name)


# ---------------------------------------------------------------- the model
def schema_signatures() -> set[tuple[str, str, str]]:
    out = set()
    for m in re.finditer(r"CREATE REL TABLE (\w+)\((.*?)\);", schema, re.S):
        for f, t in re.findall(r"FROM (\w+) TO (\w+)", m.group(2)):
            out.add((m.group(1), f, t))
    return out


SIG = schema_signatures()
DERIVED = {"feeds"}
STORED = {s for s in SIG if s[0] not in DERIVED}
LABELS = {s[0] for s in STORED}

ck("schema declares 11 node labels",
   len(re.findall(r"CREATE NODE TABLE (\w+)\(", schema)) == 11)
ck("13 stored relationship labels", len(LABELS) == 13, f"{len(LABELS)}")
ck("15 stored endpoint signatures", len(STORED) == 15, f"{len(STORED)}")
ck("exactly one derived relation",
   len({s for s in SIG if s[0] in DERIVED}) == 1)

# ------------------------------------------------- Figure 1, by ENDPOINT
fig = tex[tex.index(r"\begin{tikzpicture}"):tex.index(r"\end{tikzpicture}")]
# TikZ node id -> node label, read from the figure's own declarations
ids = dict(re.findall(r"\\node\[[^\]]*\]\s*\((\w+)\)\s*\{([A-Za-z]+)\}", fig))
fig_sigs = set()
# Anchors may contain spaces ("sla.north east"), so the endpoint pattern has
# to admit them; requiring [\w.]+ silently skipped five real edges and made
# the figure look incomplete when it was not.
for m in re.finditer(r"\\draw\[[a-z]+\]\s*\(([\w.\s]+?)\)[^;]*?node\[[^\]]*\]\{([^{}]*(?:\$[^$]*\$)?[^{}]*)\}[^;]*?\(([\w.\s]+?)\)",
                     fig, re.S):
    a, lbl, b = m.group(1).split(".")[0].strip(), m.group(2), m.group(3).split(".")[0].strip()
    lbl = re.sub(r"\$\\dagger\$|\\", "", lbl).strip()
    for one in [x.strip() for x in lbl.split("/")]:
        if one and a in ids and b in ids:
            fig_sigs.add((one, ids[a], ids[b]))

stored_no_deriv = {(l, f, t) for (l, f, t) in STORED}
ck("every figure edge exists in the model (by endpoint)",
   fig_sigs <= stored_no_deriv | {(d, "Dataset", "Dataset") for d in DERIVED},
   f"figure-only: {sorted(fig_sigs - stored_no_deriv - {(d,'Dataset','Dataset') for d in DERIVED})}")
ck("every stored signature appears in the figure (by endpoint)",
   stored_no_deriv <= fig_sigs,
   f"missing from figure: {sorted(stored_no_deriv - fig_sigs)}")

# ------------------------------------------------- queries vs the schema
qsrc = {}
for q in range(1, 8):
    s = open(os.path.join(HERE, f"q{q}.cypher"), encoding="utf-8").read()
    qsrc[f"Q{q}"] = "\n".join(l for l in s.splitlines()
                              if not l.strip().startswith("//"))
derive = open(os.path.join(HERE, "derive_feeds.cypher"), encoding="utf-8").read()

used_by = {l: [q for q, s in qsrc.items() if re.search(r"[:\[]" + l + r"\b", s)]
           for l in LABELS | DERIVED}

# every relationship a query names must be declared
named = set()
for s in qsrc.values():
    named |= set(re.findall(r"-\[:(\w+)", s)) | set(re.findall(r"\[:(\w+)\*", s))
ck("every relationship used by q1-q7 is declared in the schema",
   named <= LABELS | DERIVED, f"undeclared: {sorted(named - LABELS - DERIVED)}")

# no resurrection of removed names
for ghost in ("of", "lag_minutes"):
    ck(f"removed element `{ghost}` has not reappeared",
       not any(re.search(r"[:\[.]" + ghost + r"\b", s) for s in qsrc.values())
       and not re.search(r"[:\[.]" + ghost + r"\b", schema))

# every stored label is exercised by a query, or by the documented derivation
for l in sorted(LABELS):
    in_derive = bool(re.search(r"\[:" + l + r"\]", derive))
    ck(f"`{l}` is exercised",
       bool(used_by[l]) or in_derive,
       ", ".join(used_by[l]) or ("derive_feeds.cypher" if in_derive else "NOTHING"))

ck("`feeds` is declared derived, not stored",
   "feeds" in DERIVED and "derived" in schema.lower())

# Q5 must reach pipelines, or Principal->Pipeline is dead weight
ck("Q5 resolves ownership over pipelines as well as datasets",
   "Pipeline" in qsrc["Q5"] and "via_pipeline" in qsrc["Q5"])

# the multi-endpoint signatures must both be reachable
ck("both `owns` signatures can bind in Q5",
   re.search(r"\(pr:Principal\)-\[:owns\]->\(\w+\)", qsrc["Q5"]) is not None,
   "untyped endpoint binds Dataset and Pipeline")

# Q7 must be evaluated at an explicit time against the full validity interval
ck("Q7 tests valid_from and valid_to",
   "valid_from" in qsrc["Q7"] and "valid_to" in qsrc["Q7"])

# temporal properties present on exactly the bitemporal edges
for rel in ("has_schema", "derives_from"):
    blk = re.search(r"CREATE REL TABLE " + rel + r"\((.*?)\);", schema, re.S).group(1)
    ck(f"`{rel}` carries all four temporal properties",
       all(p in blk for p in ("valid_from", "valid_to",
                              "recorded_from", "recorded_to")))

print(f"\n{len(fails)} failure(s)")
sys.exit(1 if fails else 0)
