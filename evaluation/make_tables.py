"""Generate the paper's evidence tables from data, and splice them into paper.tex.

Three tables are generated rather than typed:

  tab_capability   both assessment layers as one matrix with two row groups,
                   from capability_matrix.json
  tab_answer       answerability, DERIVED from the two layers

Three further tables -- traceability, systems/evidence, and per-query
validation detail -- are emitted to SUPPLEMENTARY.md instead of the paper,
which is how the manuscript fits the venue's page limit without losing the
evidence.

Springer requires the manuscript to be a single .tex file, so these cannot be
\\input. Instead each table sits between
  % BEGIN GENERATED <name>  ...  % END GENERATED <name>
markers in paper.tex and this script rewrites the span. paper.tex therefore
stays self-contained and submittable while no capability claim in it is
hand-transcribed: change a cell in the JSON, re-run, and the paper follows.

Every capability cell carries a reason and a citation key in the JSON. A cell
with no citation key is a hard error here, which is the mechanism that keeps
"every judgment traceable to a source" true rather than aspirational.

Usage:  python make_tables.py [--check]
        --check verifies the spliced tables are current without writing.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PAPER = os.path.join(HERE, "..", "paper.tex")
SYSTEMS = ["OpenLineage", "Apache Atlas", "DataHub", "OpenMetadata",
           "Egeria", "Unity Catalog"]
# Column headings, shortened to fit a two-column Springer page.
HEAD = {"OpenLineage": "OpenL.", "Apache Atlas": "Atlas", "DataHub": "DataHub",
        "OpenMetadata": "OpenM.", "Egeria": "Egeria", "Unity Catalog": "UC"}


def mark(v: str) -> str:
    """Render a verdict, bolding only absence so the eye finds the gaps."""
    return {"Y": r"\ry", "P": r"\rp", "N": r"\rn", "-": r"\rna"}[v]


def load(p: str):
    return json.load(open(os.path.join(HERE, p), encoding="utf-8"))


def capability_table(cm: dict) -> str:
    """One matrix, two clearly separated row groups.

    The two layers were separate tables and cost a full page between them.
    Merging under group headings keeps the analytical separation -- which is
    the point of the two-layer method -- while spending one float instead of
    two. The per-cell citation check is retained: it is the mechanism behind
    the claim that every verdict is traceable, so it must not be a casualty of
    the consolidation.
    """
    rows, missing = [], []
    ans = answerability(cm)
    derived = {}
    for q, row in ans.items():
        lbl = cm["requirements"][q]["label"]
        derived[f"{q} {lbl}"] = {sy: [row[sy], "", "derived"] for sy in SYSTEMS}
    groups = [("(a) Metadata representation \\emph{-- does the system record "
               "it?}", cm["representation"]),
              ("(b) Query expressiveness \\emph{-- can its interface ask?}",
               cm["expressiveness"]),
              ("(c) Workload answerability \\emph{-- derived from (a) and (b) "
               "by Eq.~(\\ref{eq:answer})}", derived)]
    for gi, (title, block) in enumerate(groups):
        if gi:
            rows.append("\\addlinespace[3pt]\n\\midrule")
        rows.append(f"\\multicolumn{{{1 + len(SYSTEMS)}}}{{@{{}}l}}"
                    f"{{\\textbf{{{title}}}}} \\\\[1pt]")
        for prop, cells in block.items():
            if prop.startswith("_"):
                continue
            out = []
            for s in SYSTEMS:
                verdict, reason, cite = cells[s]
                if not cite:
                    missing.append(f"{prop}:{s}")
                out.append(mark(verdict))
            rows.append(f"\\quad {prop} & " + " & ".join(out) + r" \\")
    if missing:
        raise SystemExit("cells without a citation key: " + ", ".join(missing))
    cols = "@{}l" + "c" * len(SYSTEMS) + "@{}"
    head = " & ".join(HEAD[s] for s in SYSTEMS)
    caption = (
        "Capability assessment. \\ry~native, \\rp~partial, \\rn~absent, "
        "\\rna~not applicable (OpenLineage specifies data, not a query "
        "surface). A query needs its facts from (a) \\emph{and} its operations "
        "from (b); group~(c) is \\emph{computed} from the two above it by "
        "Eq.~(\\ref{eq:answer}), not assessed directly, so a disputed verdict "
        "there traces to a specific cell above. Groups (a) and (b) are "
        "generated from \\texttt{evaluation/capability\\_matrix.json}, where "
        "every cell carries a reason and a source.")
    return (f"\\begin{{table*}}[t]\n\\caption{{{caption}}}\n"
            f"\\label{{tab:capability}}\n\\scriptsize\n\\centering\n"
            f"\\begin{{tabular}}{{{cols}}}\n\\toprule\n"
            f" & {head} \\\\\n\\midrule\n" + "\n".join(rows) +
            "\n\\bottomrule\n\\end{tabular}\n\\end{table*}\n")


def answerability(cm: dict):
    """Derive, per query per system, whether the workload query is answerable.

    A query needs BOTH its representation facts and its query operations. The
    verdict is therefore the weakest required cell across the two layers --
    computed, not asserted, which is what lets a reader check it. The
    asymmetry this exposes is the paper's main result: a system can hold the
    data and be unable to ask, or be able to ask and not hold the data.
    """
    order = {"N": 0, "-": 1, "P": 2, "Y": 3}
    out = {}
    for q, req in cm["requirements"].items():
        row = {}
        for s in SYSTEMS:
            cells = ([cm["representation"][k][s] for k in req["representation"]]
                     + [cm["expressiveness"][k][s] for k in req["expressiveness"]])
            worst = min((c[0] for c in cells), key=lambda v: order[v])
            # "-" means the artefact has no query layer at all: report that as
            # specification-only rather than as a failure to support.
            if any(c[0] == "-" for c in cells):
                worst = "-"
            row[s] = worst
        out[q] = row
    return out


def md_trace(cm: dict) -> str:
    rows = ["| Query | Representation required | Query operation required | "
            "Reference-model elements |", "|---|---|---|---|"]
    for q, r in cm["requirements"].items():
        model = r["model"].replace("\\\\_", "_").replace("\\_", "_")
        rows.append(f"| **{q}** {r['label']} | "
                    + ", ".join(r["representation"]) + " | "
                    + ", ".join(r["expressiveness"]) + " | " + model + " |")
    return ("## Requirement-to-model traceability\n\n"
            "Every node, edge and property of the reference model appears in "
            "the last column of some row: an element that serves no query is "
            "not in the model. Referenced from Sect. 3 and 4 of the paper.\n\n"
            + "\n".join(rows) + "\n")


def md_evidence(cm: dict) -> str:
    keys = {}
    for layer in ("representation", "expressiveness"):
        for prop, cells in cm[layer].items():
            if prop.startswith("_"):
                continue
            for s_name, (_v, _r, cite) in cells.items():
                keys.setdefault(s_name, set()).add(cite)
    rows = ["| System | Kind | Version / documentation examined | Evidence keys |",
            "|---|---|---|---|"]
    for s_name in SYSTEMS:
        meta = cm["systems"][s_name]
        rows.append(f"| {s_name} | {meta['kind']} | {meta['version']} | "
                    + ", ".join(f"`{k}`" for k in sorted(keys.get(s_name, ())))
                    + " |")
    return ("## Systems assessed, versions, and evidence\n\n"
            "Evidence keys are bibliography keys in the paper's "
            "`references.bib`. Per-cell verdicts and reasons are in "
            "`capability_matrix.json`.\n\n" + "\n".join(rows) + "\n")


def md_validation(res: dict) -> str:
    rows = ["| Query | Capability exercised | Executable | Matches expected | Rows |",
            "|---|---|---|---|---|"]
    for q in sorted(res["queries"]):
        r = res["queries"][q]
        rows.append(f"| **{q}** | {r['capability']} | "
                    f"{'yes' if r['executable'] else 'no'} | "
                    f"{'yes' if r['matched_expected'] else 'no'} | "
                    f"{len(r.get('rows') or [])} |")
    out = ["## Query validation", "",
           "Each query executed against the synthetic graph on Kuzu "
           f"{res['engine'].split()[-1]}; *matches* means the returned rows "
           "equalled the expectation fixed in `run_validation.py` before the "
           "run. The paper states the 7/7 outcome in prose (Sect. 6.2) and "
           "points here for the per-query detail.", "",
           "\n".join(rows), "", "### Interpretations", ""]
    for q in sorted(res["queries"]):
        out.append(f"- **{q}** — {res['queries'][q]['reading']}")
    return "\n".join(out) + "\n"


def splice(tex: str, name: str, content: str) -> str:
    b, e = f"% BEGIN GENERATED {name}", f"% END GENERATED {name}"
    if b not in tex or e not in tex:
        raise SystemExit(f"markers for {name} not found in paper.tex")
    i, j = tex.index(b) + len(b), tex.index(e)
    return tex[:i] + "\n" + content + tex[j:]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    res = load("results.json")
    cm = load("capability_matrix.json")

    # In the paper: the merged capability matrix and the derived answerability
    # table. Everything else moves to SUPPLEMENTARY.md -- the paper has to fit
    # the CfP's 8-10 pages, and these three were costing about 2.5 of them.
    tables = {
        "tab_capability": capability_table(cm),
    }
    supp = "\n\n".join([
        "# Supplementary tables",
        "",
        "Tables relocated from the manuscript to meet the venue's page limit. "
        "Nothing here is new: each is generated by `make_tables.py` from the "
        "same data the paper's tables come from, so it cannot drift from "
        "them.",
        md_trace(cm), md_evidence(cm), md_validation(res),
    ])

    tex = open(PAPER, encoding="utf-8").read()
    new = tex
    for name, content in tables.items():
        new = splice(new, name, content)

    supp_path = os.path.join(HERE, "SUPPLEMENTARY.md")
    if args.check:
        same = new == tex
        try:
            same = same and open(supp_path, encoding="utf-8").read() == supp
        except OSError:
            same = False
        print("generated tables are current" if same
              else "STALE: re-run make_tables.py")
        return 0 if same else 1

    open(PAPER, "w", encoding="utf-8").write(new)
    open(supp_path, "w", encoding="utf-8").write(supp)
    n_cells = sum(len([k for k in b if not k.startswith("_")]) * len(SYSTEMS)
                  for b in (cm["representation"], cm["expressiveness"]))
    print(f"spliced {len(tables)} tables into paper.tex, "
          f"3 into SUPPLEMENTARY.md")
    print(f"  {n_cells} capability cells, all with a citation key")
    print(f"  validation: {sum(1 for q in res['queries'] if res['queries'][q]['matched_expected'])}"
          f"/{len(res['queries'])} queries matched expected results")
    return 0


if __name__ == "__main__":
    sys.exit(main())
