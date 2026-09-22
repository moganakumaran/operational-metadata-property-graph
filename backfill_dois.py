"""Find a DOI for every scholarly reference that lacks one, and refuse to guess.

Springer's Datenbank-Spektrum guidelines say to "always include DOIs as full
DOI links". `sn-basic.bst` already renders a `doi` field as
https://doi.org/... , so the format is right and only the coverage is short.

Filling that gap by taking Crossref's top hit is exactly how this project
previously acquired two *wrong* bibliography entries: a search for Klettke's
schema paper returned a different paper, and the wrong title, venue and year
went in unnoticed. A first pass of this script reproduced the same class of
error -- the top hit for the CIDR lakehouse paper was a book chapter called
"MODERN DATA WAREHOUSING", and for Hellerstein's Ground it was the "European
Ground Motion Service".

So a candidate is accepted only when THREE independent signals agree:

    title    >= 0.87 similarity after normalisation
    year     exact match with the bib entry
    author   the bib entry's first-author surname appears in Crossref's
             author list

Author agreement is the signal that does the real work. Venue strings cannot
carry it: bibtex says "PODS" where Crossref says "Proceedings of the
twenty-sixth ACM SIGMOD-SIGACT-SIGART symposium...", and any matcher loose
enough to bridge that is loose enough to accept the wrong paper. The venue is
therefore printed for eyeballing but never used to accept.

Every one of the five candidates Crossref returns is tested, not just the
closest title, because the right paper is not always ranked first.

Crossref's *search* also misses records its index plainly holds: no query
tried here surfaced Hogan et al.'s "Knowledge Graphs" in ACM Computing
Surveys, because the title is two common words. For that case a candidate DOI
may be supplied by hand in CANDIDATE_DOIS -- but it is then resolved against
Crossref and must pass the identical three-signal check before it is written.
Supplying a candidate is proposing a lookup, never asserting a fact; a wrong
guess resolves to a different paper, or to nothing, and is rejected.

Some venues register no DOIs at all -- CIDR, BTW/GI-LNI, DBPL, MLSys. An entry
with no DOI is a legitimate outcome there, recorded as an explicit exception
in check.py rather than silently tolerated.

Usage:  python3 backfill_dois.py            # report only, writes nothing
        python3 backfill_dois.py --apply    # write accepted DOIs into the bib
"""
from __future__ import annotations

import argparse
import difflib
import os
import re
import sys
import time
import urllib.parse

from verify_refs import clean, fetch, norm, parse_bib

HERE = os.path.dirname(os.path.abspath(__file__))
BIB = os.path.join(HERE, "references.bib")

TITLE_MIN = 0.87

# Hand-proposed candidates for entries Crossref search cannot surface. Each is
# VERIFIED against the authoritative Crossref record for that exact DOI, under
# the same title/year/author agreement required of a searched candidate.
CANDIDATE_DOIS = {
    "hogan2021knowledge": "10.1145/3447772",
}


def first_surname(authors: str) -> str:
    """Surname of the first author, from either bibtex name convention."""
    a = re.split(r"\s+and\s+", authors.strip())[0]
    a = re.sub(r"\\[a-zA-Z]+|[{}]", "", a).strip()
    if "," in a:                               # "Surname, Given"
        return norm(a.split(",")[0])
    return norm(a.split()[-1]) if a.split() else ""


def crossref_candidates(title: str, surname: str) -> list[dict] | None:
    """Ask Crossref by title, and again by title+author.

    The author-qualified query is what surfaces the right record when the
    title alone is generic ("Knowledge Graphs", "Provenance semirings").
    """
    base = ("https://api.crossref.org/works?rows=5&select=title,issued,"
            "container-title,DOI,author&query.bibliographic=")
    urls = [base + urllib.parse.quote(clean(title))]
    if surname:
        urls.append(base + urllib.parse.quote(clean(title))
                    + "&query.author=" + urllib.parse.quote(surname))
    out, reachable = [], False
    for u in urls:
        d = fetch(u)
        if d is None:
            continue
        reachable = True
        out.extend(d.get("message", {}).get("items", []))
        time.sleep(0.3)
    return out if reachable else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    entries = parse_bib(BIB)
    accepted, review, web = {}, [], []

    for e in entries:
        f, key = e["fields"], e["key"]
        if f.get("doi"):
            continue
        if e["kind"] == "misc":
            web.append(key)
            continue

        title = f.get("title", "")
        year = (f.get("year") or "").strip()
        surname = first_surname(f.get("author", ""))
        bv = f.get("booktitle") or f.get("journal") or ""

        cands = crossref_candidates(title, surname)
        if cands is not None and key in CANDIDATE_DOIS:
            d = fetch("https://api.crossref.org/works/" + CANDIDATE_DOIS[key])
            if d:
                cands.insert(0, d.get("message", {}))
        if cands is None:
            review.append((key, "crossref UNREACHABLE -- re-run, not a miss", ""))
            print(f"UNREACH {key}")
            continue

        hit, best_seen = None, (0.0, "", "")
        for c in cands:
            ct = " ".join(c.get("title") or [])
            cy = str((c.get("issued", {}).get("date-parts") or [[None]])[0][0] or "")
            cv = " ".join(c.get("container-title") or [])
            names = norm(" ".join((a.get("family") or "")
                                  for a in (c.get("author") or [])))
            r = difflib.SequenceMatcher(None, norm(title), norm(ct)).ratio()
            if r > best_seen[0]:
                best_seen = (r, ct, cy)
            if r >= TITLE_MIN and cy == year and surname and surname in names.split():
                hit = (r, ct, cy, cv, c.get("DOI", ""))
                break

        if hit and hit[4]:
            accepted[key] = hit[4]
            print(f"ACCEPT {key}  [title {hit[0]:.2f}, year {hit[2]}, "
                  f"author {surname}]  {hit[4]}\n         {hit[3][:60]}")
        else:
            why = (f"no candidate matched all three signals "
                   f"(best title {best_seen[0]:.2f} '{best_seen[1][:40]}' "
                   f"{best_seen[2]}); bib venue '{bv}'")
            review.append((key, why, ""))
            print(f"REJECT {key}  {why}")

    print(f"\n{len(accepted)} accepted, {len(review)} rejected/unresolved, "
          f"{len(web)} web entries skipped")
    if review:
        print("\nNO DOI WRITTEN (verify by hand, or the venue registers none):")
        for k, why, _ in review:
            print(f"  {k}: {why}")

    if args.apply and accepted:
        src = open(BIB, encoding="utf-8").read()
        for key, doi in accepted.items():
            pat = re.compile(r"(@\w+\{" + re.escape(key)
                             + r",.*?\n)(\s*)(year\s*=\s*\{[^}]*\})(,?)", re.S)
            m = pat.search(src)
            if not m:
                sys.exit(f"could not locate year field of {key} -- nothing written")
            ins = f",\n{m.group(2)}doi     = {{{doi}}}" + (m.group(4) or ",")
            src = src[:m.end(3)] + ins + src[m.end(4):]
        open(BIB, "w", encoding="utf-8").write(src)
        print(f"\nwrote {len(accepted)} DOIs into references.bib")
    return 0


if __name__ == "__main__":
    sys.exit(main())
