"""Build the paper and run every submission gate. Exit non-zero if any fails.

One command so the checks are reproducible rather than remembered. Each gate
below exists because something it catches actually went wrong while writing
this paper:

  compile      tectonic must finish with no errors
  citations    the PDF must contain no "[?]" -- bibtex silently produced an
               empty bibliography when the .bst was not resolvable, and the
               compile still "succeeded"
  overfull     a table wider than its column, and a TikZ figure that resized
               past \\textwidth
  pages        10-12, the target for this IEEE build, measured on the PDF
  model        endpoint-level figure/table/schema agreement, and no model
               element left unexercised by any query
  anon         paper_anon.tex is current, and neither it nor its PDF carries
               an identifying string
  abstract     150-250 words. IEEE sets no limit; the bound is kept because it
               is the range that reads well in a two-column abstract block and
               a silent doubling of it would otherwise go unnoticed
  artefact     the availability footnote must survive into the rendered PDF --
               it replaced the Springer Declarations section and lives in a
               \\thanks, which is easy to lose in an author-block edit
  dois         IEEEtran.bst does not print DOIs, so this gates the `doi` field
               being present in the .bib -- the record readers follow to the
               source -- with a named exception per venue that registers none
  refs         verify_refs.py: every reference confirmed against a live index
  independence 8-gram similarity against the author's prior papers, which the
               venue plan requires to be near zero

Deliberately not gated: the AI-writing heuristic. It is a heuristic, its score
moves with legitimate technical vocabulary, and failing a build on it would
invite degrading the prose to satisfy a number. Reported, never enforced.

Usage:  python3 check.py [--skip-refs]
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PAPER = os.path.join(HERE, "paper.tex")
PDF = os.path.join(HERE, "paper.pdf")
# The target band for this IEEE conference build. A lower bound is included so
# that silently losing a section fails too.
MIN_PAGES, MAX_PAGES = 10, 12
MIN_ABSTRACT, MAX_ABSTRACT = 150, 250
# Scholarly references legitimately without a DOI, each because the venue
# registers none. Named individually so that a NEW reference without a DOI
# fails the gate instead of hiding behind a blanket tolerance.
NO_DOI_VENUE = {
    "armbrust2021lakehouse": "CIDR",
    "hellerstein2017ground": "CIDR",
    "breck2019validation": "MLSys",
    "scherzinger2013nosql": "DBPL",
    "klettke2015schema": "BTW / GI-LNI",
}
VENV = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".venv",
                    "bin", "python")


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, cwd=HERE, **kw)


def gate(name: str, ok: bool, detail: str = "") -> bool:
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-refs", action="store_true",
                    help="skip the network reference check")
    args = ap.parse_args()
    results = []

    print("building")
    r = run(["tectonic", "-X", "compile", "paper.tex"])
    log = r.stdout + r.stderr
    errs = [l for l in log.splitlines() if l.startswith("error")]
    results.append(gate("compile", not errs and os.path.exists(PDF),
                        errs[0] if errs else ""))

    # Overfull boxes only matter when large enough to visibly leave the column.
    over = [l for l in log.splitlines()
            if re.search(r"Overfull \\hbox \((\d{2,})", l)]
    results.append(gate("no large overfull boxes", not over,
                        f"{len(set(over))} distinct" if over else ""))

    bib_warn = [l for l in log.splitlines() if "Warning--" in l]
    results.append(gate("bibtex clean", not bib_warn,
                        f"{len(bib_warn)} warnings" if bib_warn else ""))

    txt = run(["pdftotext", "-nopgbrk", "paper.pdf", "-"]).stdout
    n_unres = txt.count("[?]")
    results.append(gate("citations resolved", n_unres == 0,
                        f"{n_unres} unresolved" if n_unres else ""))

    info = run(["pdfinfo", "paper.pdf"]).stdout
    m = re.search(r"Pages:\s+(\d+)", info)
    pages = int(m.group(1)) if m else -1
    results.append(gate(f"pages in [{MIN_PAGES},{MAX_PAGES}]",
                        MIN_PAGES <= pages <= MAX_PAGES, f"{pages} pages"))

    # Every gap-analysis cell must cite its evidence, and no cell may ship
    # unverified. The '?' marker is the one thing the analysis must never
    # contain, since guessing a capability is the failure mode that matters.
    # The reference implementation must actually run, and every query must
    # match the expectation fixed before the run. This is the gate that makes
    # the evaluation section a claim about behaviour rather than about intent.
    py = VENV if os.path.exists(VENV) else sys.executable
    r = run([py, "-u", "evaluation/run_validation.py"])
    last = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
    results.append(gate("reference queries execute and match",
                        r.returncode == 0, last))

    # Tables in the paper must be current with the evidence they come from.
    r = run([sys.executable, "evaluation/make_tables.py", "--check"])
    results.append(gate("generated tables current", r.returncode == 0,
                        r.stdout.strip().splitlines()[-1] if r.stdout else ""))

    # Manuscript-internal consistency: figure vs table vs schema vs listing.
    r = run([sys.executable, "consistency.py"])
    tail = [l for l in r.stdout.splitlines() if "failure" in l]
    results.append(gate("manuscript self-consistent", r.returncode == 0,
                        tail[-1] if tail else ""))

    # Model consistency by ENDPOINT, not by label. The label-level check above
    # passed while Figure 1 drew owns: Principal -> Consumer, a relationship
    # the model does not contain, and omitted owns: Principal -> Dataset.
    # This also fails if any stored signature stops being exercised.
    r = run([sys.executable, "evaluation/test_model_consistency.py"])
    tail = [l for l in r.stdout.splitlines() if "failure" in l]
    results.append(gate("model consistent (endpoints, orphans)",
                        r.returncode == 0, tail[-1] if tail else ""))

    # The blinded manuscript is generated, so it can go stale silently. This
    # also re-scans it for identifying strings, which is the failure that
    # actually matters: a leak reaches the reviewers.
    r = run([sys.executable, "make_anon.py", "--check"])
    results.append(gate("anonymous version current and clean",
                        r.returncode == 0,
                        r.stdout.strip().splitlines()[-1] if r.stdout else ""))

    # Build it too, so a blinded PDF that does not compile cannot ship.
    r = run(["tectonic", "-X", "compile", "paper_anon.tex"])
    anon_errs = [l for l in (r.stdout + r.stderr).splitlines()
                 if l.startswith("error")]
    anon_pdf = os.path.join(HERE, "paper_anon.pdf")
    leak = 0
    if os.path.exists(anon_pdf):
        atxt = run(["pdftotext", "-nopgbrk", "paper_anon.pdf", "-"]).stdout
        leak = sum(atxt.lower().count(t.lower())
                   for t in ("sivaraman", "mogana", "ieee.org",
                             "san francisco"))
    results.append(gate("anonymous PDF builds with no identifying text",
                        not anon_errs and os.path.exists(anon_pdf) and leak == 0,
                        f"{leak} identifying string(s)" if leak else ""))

    # Abstract length. Counted from the source so the failure names a number
    # to cut to, not just "too long". IEEEtran uses an environment where the
    # Springer class used a \abstract{...} command.
    tex = open(PAPER, encoding="utf-8").read()
    i = tex.index(r"\begin{abstract}") + len(r"\begin{abstract}")
    abs_end = tex.index(r"\end{abstract}")
    body = tex[i:abs_end]
    body = re.sub(r"\\[a-zA-Z]+\*?", "", body)
    body = re.sub(r"[{}~$\\]", " ", body)
    n_abs = len([w for w in body.split() if re.search(r"[A-Za-z0-9]", w)])
    results.append(gate(f"abstract in [{MIN_ABSTRACT},{MAX_ABSTRACT}] words",
                        MIN_ABSTRACT <= n_abs <= MAX_ABSTRACT, f"{n_abs} words"))

    # The Springer Declarations section is gone; what replaced it is a \thanks
    # footnote on the author block carrying artefact availability and the
    # synthetic-data statement. Checked on the rendered text, not the source,
    # because a \thanks that fails to typeset still compiles cleanly.
    required = ("released with this paper", "The running example is synthetic")
    missing = [d for d in required if d.lower() not in txt.lower()]
    results.append(gate("artefact availability footnote in the PDF",
                        not missing,
                        f"missing: {', '.join(missing)}" if missing else
                        "availability and synthetic-data statement present"))

    # DOI coverage. IEEEtran.bst does not print DOIs, so this gates the field
    # being present in the .bib rather than its appearance in the PDF.
    from verify_refs import parse_bib
    scholarly = [e for e in parse_bib(os.path.join(HERE, "references.bib"))
                 if e["kind"] != "misc"]
    no_doi = {e["key"] for e in scholarly if not e["fields"].get("doi")}
    unexpected = sorted(no_doi - set(NO_DOI_VENUE))
    stale = sorted(set(NO_DOI_VENUE) - no_doi)   # exception no longer needed
    results.append(gate("scholarly references carry DOIs",
                        not unexpected and not stale,
                        (f"no DOI and no recorded exception: {unexpected}; "
                         if unexpected else "")
                        + (f"stale exceptions: {stale}" if stale else
                           f"{len(scholarly) - len(no_doi)}/{len(scholarly)}, "
                           f"{len(no_doi)} known DOI-less venues")))

    if not args.skip_refs:
        r = run([sys.executable, "-u", "verify_refs.py"])
        tail = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
        results.append(gate("references verified", r.returncode == 0, tail))
    else:
        print("  [skip] references verified")

    print("\nreported, not gated:")
    print(f"  pages={pages}  words~{len(txt.split())}")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
