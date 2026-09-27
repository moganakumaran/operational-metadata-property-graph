"""Generate the paper's evidence tables from data, and splice them into paper.tex.

Four tables are generated rather than typed:

  tab_capability   both assessment layers as one matrix, plus answerability
                   DERIVED from them, from capability_matrix.json
  tab_trace        requirement-to-model traceability, the evidence behind the
                   minimality claim
  tab_systems      the systems assessed, their versions, and the evidence
  tab_validation   per-query validation detail behind the 7/7 claim

The per-query prose readings stay in SUPPLEMENTARY.md: commentary rather than
evidence, and too long for the manuscript.

The manuscript is a single .tex file, so these cannot be
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
# Column headings, shortened to fit a two-column page.
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
    note = (
        "\\ry~native, \\rp~partial, \\rn~absent, "
        "\\rna~not applicable (OpenLineage specifies data, not a query "
        "surface). A query needs its facts from (a) \\emph{and} its operations "
        "from (b); group~(c) is \\emph{computed} from the two above it by "
        "Eq.~(\\ref{eq:answer}), not assessed directly, so a disputed verdict "
        "there traces to a specific cell above. Groups (a) and (b) are "
        "generated from \\texttt{evaluation/capability\\_matrix.json}, where "
        "every cell carries a reason and a source.")
    return (f"\\begin{{table*}}[t]\n"
            f"\\caption{{Capability assessment of six metadata systems}}\n"
            f"\\label{{tab:capability}}\n\\scriptsize\n\\centering\n"
            f"\\begin{{tabular}}{{{cols}}}\n\\toprule\n"
            f" & {head} \\\\\n\\midrule\n" + "\n".join(rows) +
            "\n\\bottomrule\n\\end{tabular}\n" + note_block(note) +
            "\\end{table*}\n")


def esc(t: str) -> str:
    """Escape a plain-text JSON value for LaTeX.

    Values in capability_matrix.json's `model` field are already escaped, so
    only the fields known to be plain text go through here.
    """
    return t.replace("\\", r"\textbackslash{}").replace("_", r"\_") \
            .replace("&", r"\&").replace("%", r"\%").replace("#", r"\#")


def note_block(text: str, width: str = "\\textwidth") -> str:
    """A caption-sized note below the rules.

    IEEEtran sets table captions in small caps above the table, where anything
    longer than a line is unreadable. The detail belongs under the bottom rule.
    """
    return ("\n\\smallskip\n\\begin{minipage}{" + width + "}\n\\scriptsize\n"
            + text + "\n\\end{minipage}\n")


def trace_table(cm: dict) -> str:
    """Requirement-to-model traceability: the evidence behind minimality.

    Every model element appears in the last column of some row; an element
    serving no query is not in the model. This was in SUPPLEMENTARY.md under
    the Springer page limit and comes back into the paper under IEEE's.
    """
    rows = []
    for q, r in cm["requirements"].items():
        rows.append(
            f"{q} \\emph{{{esc(r['label'])}}} & "
            + esc(", ".join(r["representation"])) + " & "
            + esc(", ".join(r["expressiveness"])) + " & "
            + r["model"] + r" \\")
    note = ("Every node, edge and property of the reference model appears in "
            "the last column of some row: an element that serves no query is "
            "not in the model. Generated from "
            "\\texttt{evaluation/capability\\_matrix.json}.")
    cols = ("@{}l"
            ">{\\raggedright\\arraybackslash}p{0.20\\textwidth}"
            ">{\\raggedright\\arraybackslash}p{0.22\\textwidth}"
            ">{\\raggedright\\arraybackslash}p{0.34\\textwidth}@{}")
    return ("\\begin{table*}[t]\n"
            "\\caption{Requirement-to-model traceability}\n"
            "\\label{tab:trace}\n\\scriptsize\n\\centering\n"
            f"\\begin{{tabular}}{{{cols}}}\n\\toprule\n"
            "Query & Representation required & Query operation required & "
            "Reference-model elements \\\\\n\\midrule\n"
            + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}\n"
            + note_block(note) + "\\end{table*}\n")


def systems_table(cm: dict) -> str:
    """Systems, versions and the evidence behind each column."""
    keys = {}
    for layer in ("representation", "expressiveness"):
        for prop, cells in cm[layer].items():
            if prop.startswith("_"):
                continue
            for s_name, (_v, _r, cite) in cells.items():
                keys.setdefault(s_name, set()).add(cite)
    rows = []
    for s_name in SYSTEMS:
        meta = cm["systems"][s_name]
        cites = ",".join(sorted(keys.get(s_name, ())))
        rows.append(f"{esc(s_name)} & {esc(meta['kind'])} & "
                    f"{esc(meta['version'])} & "
                    + (f"\\cite{{{cites}}}" if cites else "--") + r" \\")
    note = ("All assessments were made on 21 September 2026 against the most "
            "current documentation we could locate, and against source where "
            "documentation was silent on a point the workload depends on. "
            "Per-cell verdicts and reasons are in "
            "\\texttt{evaluation/capability\\_matrix.json}.")
    cols = ("@{}ll"
            ">{\\raggedright\\arraybackslash}p{0.42\\textwidth}"
            "l@{}")
    return ("\\begin{table*}[t]\n"
            "\\caption{Systems assessed, versions, and evidence}\n"
            "\\label{tab:systems}\n\\scriptsize\n\\centering\n"
            f"\\begin{{tabular}}{{{cols}}}\n\\toprule\n"
            "System & Kind & Version / documentation examined & Evidence \\\\\n"
            "\\midrule\n" + "\n".join(rows) + "\n\\bottomrule\n"
            "\\end{tabular}\n" + note_block(note) + "\\end{table*}\n")


def validation_table(res: dict) -> str:
    """Per-query validation detail behind the 7/7 claim."""
    rows = []
    for q in sorted(res["queries"]):
        r = res["queries"][q]
        rows.append(f"{q} & {esc(r['capability'])} & "
                    f"{'yes' if r['executable'] else 'no'} & "
                    f"{'yes' if r['matched_expected'] else 'no'} & "
                    f"{len(r.get('rows') or [])} " + r"\\")
    # results.json records the engine lowercased; the paper names it Kuzu.
    engine = esc(res["engine"])
    engine = engine[:1].upper() + engine[1:]
    note = (f"Each query executed against the synthetic graph on {engine}. "
            "\\emph{Matches} means the returned rows equalled an expectation "
            "fixed in \\texttt{evaluation/run\\_validation.py} \\emph{before} "
            "the run. Per-query readings are in "
            "\\texttt{evaluation/results.json}.")
    cols = ("@{}l>{\\raggedright\\arraybackslash}p{0.46\\textwidth}"
            "ccc@{}")
    return ("\\begin{table*}[t]\n"
            "\\caption{Query validation on the reference implementation}\n"
            "\\label{tab:validation}\n\\scriptsize\n\\centering\n"
            f"\\begin{{tabular}}{{{cols}}}\n\\toprule\n"
            "Query & Capability exercised & Executes & Matches & Rows \\\\\n"
            "\\midrule\n" + "\n".join(rows) + "\n\\bottomrule\n"
            "\\end{tabular}\n" + note_block(note) + "\\end{table*}\n")


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
           "run. The per-query outcome is in the paper's query-validation "
           "table; what follows is the reading of each result.", "",
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

    # All four evidence tables are in the paper. Under the Springer 8-10 page
    # limit three of them lived in SUPPLEMENTARY.md; the IEEE build has the
    # room, and an assessment paper is stronger when its evidence is in it.
    tables = {
        "tab_capability": capability_table(cm),
        "tab_trace": trace_table(cm),
        "tab_systems": systems_table(cm),
        "tab_validation": validation_table(res),
    }
    # What stays out is the per-query prose reading, which is long and is
    # commentary rather than evidence.
    supp = "\n\n".join([
        "# Supplementary material",
        "",
        "The four generated evidence tables are in the paper itself "
        "(Tables II--V). What remains here is the per-query reading of the "
        "validation results: commentary on what each returned row means, too "
        "long for the manuscript and generated by `make_tables.py` from the "
        "same `results.json` the paper's table comes from, so it cannot drift "
        "from it.",
        md_validation(res),
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
          f"readings into SUPPLEMENTARY.md")
    print(f"  {n_cells} capability cells, all with a citation key")
    print(f"  validation: {sum(1 for q in res['queries'] if res['queries'][q]['matched_expected'])}"
          f"/{len(res['queries'])} queries matched expected results")
    return 0


if __name__ == "__main__":
    sys.exit(main())
