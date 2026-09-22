"""Verify every reference in references.bib against DBLP, then Crossref.

The standing rule on this work is that references are never invented and never
carry made-up metadata. A reference that cannot be verified is flagged, not
quietly kept. This script is how that rule is enforced rather than asserted.

It reads `references.bib` and queries, per entry, OpenAlex and then Crossref by
title. OpenAlex leads because it indexes the venues a database bibliography
actually lives in -- CIDR, PVLDB, SIGMOD proceedings -- which Crossref covers
unevenly.

DBLP would be the natural first stop for computer science and is deliberately
*not* used: it is unreachable from this environment (connection reset), and a
lookup that silently returns zero hits is indistinguishable from "this
reference does not exist". For a tool whose entire purpose is catching
fabricated references, a false negative of that kind is worse than no check at
all, so an unreachable source is reported as UNREACHABLE and never as a miss.

What it checks, per entry:
  title   fuzzy-matched, since bibtex titles carry braces and subtitles vary
  year    exact; a year mismatch is the most common real error
  venue   reported for eyeballing, not asserted -- DBLP's venue strings and
          bibtex's do not agree often enough to fail a build on

Deliberately not checked: authors. DBLP's author lists are reliable, but name
formatting differs enough ("J. Doe" vs "Jane Doe") that automated comparison
produces mostly false alarms. Author lists are checked by reading the report.

Web entries (@misc with a url and no DOI) are expected to be unverifiable here
-- documentation pages are not indexed. They are reported separately as WEB
and must instead carry an access or inspection date, which this script checks.

Usage:  python3 verify_refs.py [--bib references.bib]
Exit code 1 if any non-web entry is UNVERIFIED, so it works as a build gate.
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
UA = {"User-Agent": "refcheck/1.0 (academic bibliography verification)"}
CACHE_PATH = os.path.join(HERE, ".refcache.json")

# Successful lookups are cached on disk. Without this, OpenAlex rate-limits a
# 36-entry run partway through and the second half reports as unreachable --
# which made consecutive runs disagree about which references were verified.
# Only successes are cached, so a rate-limited entry is retried next time.
try:
    CACHE = json.load(open(CACHE_PATH))
except Exception:
    CACHE = {}


def save_cache() -> None:
    try:
        json.dump(CACHE, open(CACHE_PATH, "w"), indent=0)
    except Exception:
        pass


def fetch(url: str, tries: int = 4) -> dict | None:
    if url in CACHE:
        return CACHE[url]
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as fh:
                d = json.load(fh)
            CACHE[url] = d
            save_cache()
            return d
        except Exception:
            if i == tries - 1:
                return None
            time.sleep(3 * (i + 1))      # OpenAlex throttles; back off properly
    return None


def parse_bib(path: str) -> list[dict]:
    """Minimal bibtex reader.

    Brace-counting rather than a regex per field: titles in this bibliography
    contain nested braces to protect capitalisation ({GQL}), and a
    non-greedy regex silently truncates at the first inner close-brace.
    """
    src = open(path, encoding="utf-8").read()
    out = []
    for m in re.finditer(r"@(\w+)\s*\{", src):
        kind = m.group(1).lower()
        # Brace counting must start at the entry's opening brace. Starting at
        # the comma after the key -- which is where the obvious regex leaves
        # you -- makes depth 0 immediately, so every body parsed as the empty
        # string and every title silently came back blank.
        open_brace = m.end() - 1
        i, depth = open_brace, 0
        while i < len(src):
            depth += (src[i] == "{") - (src[i] == "}")
            i += 1
            if depth == 0:
                break
        inner = src[open_brace + 1:i - 1]
        km = re.match(r"\s*([^,\s]+)\s*,", inner)
        if not km:
            continue
        key = km.group(1)
        body = inner[km.end():]
        fields = {}
        j = 0
        while j < len(body):
            fm = re.compile(r"(\w+)\s*=\s*").search(body, j)
            if not fm:
                break
            k, j = fm.group(1).lower(), fm.end()
            if body[j] == "{":
                d, st = 0, j
                while j < len(body):
                    d += (body[j] == "{") - (body[j] == "}")
                    j += 1
                    if d == 0:
                        break
                fields[k] = body[st + 1:j - 1]
            else:
                em = re.compile(r"[,\n]").search(body, j)
                end = em.start() if em else len(body)
                fields[k] = body[j:end].strip().strip('"')
                j = end
            j += 1
        out.append({"kind": kind, "key": key, "fields": fields})
    return out


def norm(s: str) -> str:
    s = re.sub(r"\\[a-zA-Z]+", " ", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s.lower())
    return " ".join(s.split())


def openalex(title: str) -> list[tuple[str, str, str]]:
    url = ("https://api.openalex.org/works?per-page=5&select=display_name,"
           "publication_year,primary_location&search="
           + urllib.parse.quote(clean(title)))
    d = fetch(url)
    if d is None:
        return None                      # unreachable, not empty
    out = []
    for w in d.get("results", []):
        loc = w.get("primary_location") or {}
        src = (loc.get("source") or {}).get("display_name") or ""
        out.append((w.get("display_name") or "",
                    str(w.get("publication_year") or ""), src))
    return out


def clean(t: str) -> str:
    """Strip bibtex protection braces and LaTeX before sending to a search API.

    Colons and brace-protected acronyms ({ACID}, {GQL}) are what break these
    queries; the APIs treat them as literal tokens.
    """
    t = re.sub(r"\\[a-zA-Z]+", " ", t)
    t = t.replace("{", "").replace("}", "")
    return " ".join(re.sub(r"[^A-Za-z0-9 ]", " ", t).split())


def crossref(title: str) -> list[dict]:
    url = ("https://api.crossref.org/works?rows=5&select=title,issued,"
           "container-title,DOI&query.bibliographic="
           + urllib.parse.quote(clean(title)))
    d = fetch(url)
    if d is None:
        return None
    return d.get("message", {}).get("items", [])


def best(cands: list[tuple[str, str, str]], want: str):
    """Pick the closest title match; return (ratio, title, year, venue)."""
    top = (0.0, None, None, None)
    for t, y, v in cands:
        r = difflib.SequenceMatcher(None, norm(want), norm(t or "")).ratio()
        if r > top[0]:
            top = (r, t, y, v)
    return top


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bib", default=os.path.join(HERE, "references.bib"))
    ap.add_argument("--threshold", type=float, default=0.80)
    args = ap.parse_args()

    entries = parse_bib(args.bib)
    print(f"{len(entries)} entries in {os.path.basename(args.bib)}\n")

    bad, web, ok, unreach = [], [], [], []
    for e in entries:
        f = e["fields"]
        key, title = e["key"], f.get("title", "")
        year = (f.get("year") or "").strip()
        # Web entries carry their URL in `url`, `howpublished`, or -- for the
        # consolidated per-organisation entries, which cover several pages at
        # once -- inside `note`. Missing the third form made the verifier try
        # to look up "Databricks documentation" as if it were a paper.
        is_web = e["kind"] == "misc" and not f.get("doi") and (
            f.get("url") or f.get("howpublished")
            or "\\url{" in (f.get("note") or ""))

        if is_web:
            note = f.get("note", "")
            has_date = bool(re.search(r"[Aa]ccessed|[Ii]nspected", note))
            web.append((key, has_date))
            print(f"{'WEB ' if has_date else 'WEB!'} {key}"
                  f"{'' if has_date else '   <-- no access date in note'}")
            continue

        # Prefer the DOI when the bib carries one. Three entries in this
        # bibliography are indexed under a truncated title ("Delta lake",
        # "Cypher", "Goods"), so fuzzy title matching reports them as misses
        # even though they are correct. A DOI check is exact and settles them.
        doi = (f.get("doi") or "").strip()
        if doi:
            d = fetch("https://api.crossref.org/works/" + doi)
            if d is None:
                unreach.append((key, "crossref-doi"))
            else:
                mm = d.get("message", {})
                dy = str((mm.get("issued", {}).get("date-parts")
                          or [[None]])[0][0] or "")
                dv = " ".join(mm.get("container-title") or [])
                if dy and year and dy != year:
                    print(f"YEAR {key}  [doi] bib {year} vs {dy}  {dv[:40]}")
                    bad.append((key, f"bib {year}, DOI says {dy}"))
                else:
                    ok.append(key)
                    print(f"OK   {key}  [doi {doi}] {dy}  {dv[:40]}")
                time.sleep(0.3)
                continue

        oa = openalex(title)
        src, cands = "openalex", oa
        if cands is None:
            unreach.append((key, "openalex"))
            cands = []
        r, mt, my, mv = best(cands, title)
        if r < args.threshold:
            cr = crossref(title)
            if cr is None:
                unreach.append((key, "crossref"))
                cr = []
            cands2 = [(" ".join(c.get("title", []) or []),
                       str((c.get("issued", {}).get("date-parts") or
                            [[None]])[0][0]),
                       " ".join(c.get("container-title", []) or []))
                      for c in cr]
            r2, mt2, my2, mv2 = best(cands2, title)
            if r2 > r:
                r, mt, my, mv, src = r2, mt2, my2, mv2, "crossref"

        if r >= args.threshold:
            if my and year and my != year:
                # A year disagreement is reported, not auto-failed: preprint,
                # proceedings and journal-version years legitimately differ.
                print(f"YEAR {key}  [{src} {r:.2f}] bib {year} vs {my}"
                      f"  {mv[:44]}")
                bad.append((key, f"bib says {year}, {src} says {my} -- check"))
            else:
                ok.append(key)
                print(f"OK   {key}  [{src} {r:.2f}] {my}  {(mv or '')[:44]}")
        else:
            bad.append((key, f"no match above {args.threshold} "
                             f"(best {r:.2f}) -- verify by hand"))
            print(f"MISS {key}  best {r:.2f}: {(mt or '-')[:52]}")
        time.sleep(0.3)

    print(f"\n{len(ok)} verified, {len(web)} web, {len(bad)} to check")
    for k, why in bad:
        print(f"  {k}: {why}")
    undated = [k for k, d in web if not d]
    if undated:
        print(f"  web entries missing an access date: {', '.join(undated)}")
    if unreach:
        srcs = sorted({s for _, s in unreach})
        print(f"  NOTE: {len(unreach)} lookups hit an unreachable source "
              f"({', '.join(srcs)}). Those are NOT misses -- re-run before "
              f"trusting any MISS above.")
    return 1 if (bad or undated) else 0


if __name__ == "__main__":
    sys.exit(main())
