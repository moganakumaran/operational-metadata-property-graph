"""Phase-25 consistency checks: the manuscript against itself and its artefacts.

Each check below corresponds to a defect found in the audit of the previous
draft. They exist so the same class of error cannot reappear silently.

  feeds / lag_minutes    an edge and a property used by a query listing but
                         defined nowhere in the model
  evaluates              an edge drawn in the figure and absent from the table
  bitemporal fields      claimed as a requirement while only valid time was
                         specified
  figure == table        the figure and the edge table disagreeing on the
                         model
  listing == script      the query printed in the paper drifting from the one
                         that was executed
  verdict marks          Y/P/N/S used without definition

Usage:  python3 consistency.py
Exit 1 on any failure.
"""
from __future__ import annotations
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
tex = open(os.path.join(HERE, "paper.tex"), encoding="utf-8").read()
schema = open(os.path.join(HERE, "evaluation", "schema.cypher"),
              encoding="utf-8").read()
res = json.load(open(os.path.join(HERE, "evaluation", "results.json")))
cm = json.load(open(os.path.join(HERE, "evaluation",
                                 "capability_matrix.json")))

fails = []


def ck(name, ok, detail=""):
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" +
          (f" -- {detail}" if detail else ""))
    if not ok:
        fails.append(name)


# --- the span of the edge table, which is the model's authority in the paper
i = tex.index(r"\label{tab:edges}")
edge_tbl = tex[tex.index(r"\toprule", i):tex.index(r"\bottomrule", i)]
tbl_edges = set(re.findall(r"\\eg\{([a-z_\\]+)\}", edge_tbl))
tbl_edges = {e.replace("\\", "") for e in tbl_edges}

# --- the figure body
fi = tex.index(r"\begin{tikzpicture}")
fig = tex[fi:tex.index(r"\end{tikzpicture}", fi)]
# Edge labels may carry a trailing bitemporal dagger; strip it before
# comparing, or adding the marker silently breaks the figure-vs-table check.
raw = re.findall(r"node\[[^\]]*\]\{([^{}]*(?:\{[^{}]*\})?[^{}]*)\}", fig)
fig_edges = set()
for e in raw:
    e = re.sub(r"\$\\dagger\$", "", e)
    e = re.sub(r"\\[a-zA-Z]+", "", e).replace("\\", "").strip()
    if e and re.fullmatch(r"[a-z_ /]+", e):
        fig_edges.add(e)
# "reads / writes" is drawn as one label for two edges
expanded = set()
for e in fig_edges:
    expanded |= {x.strip() for x in e.split("/")}
fig_edges = {e for e in expanded if e}

ck("every figure edge is in the edge table",
   fig_edges <= tbl_edges, f"figure-only: {sorted(fig_edges - tbl_edges)}")
ck("every table edge is in the figure",
   tbl_edges <= fig_edges, f"table-only: {sorted(tbl_edges - fig_edges)}")

# --- schema declares exactly the model's edges
schema_rels = {m.group(1) for m in
               re.finditer(r"CREATE REL TABLE (\w+)\(", schema)}
ck("edge table matches the executed schema",
   tbl_edges == schema_rels,
   f"paper-only: {sorted(tbl_edges - schema_rels)}; "
   f"schema-only: {sorted(schema_rels - tbl_edges)}")

# --- the two defects that motivated this file
ck("`feeds` is defined in the model", "feeds" in tbl_edges)
ck("`lag_minutes` no longer appears", "lag_minutes" not in tex)
ck("`evaluates` is in both figure and table",
   "evaluates" in tbl_edges and "evaluates" in fig_edges)

# --- bitemporality actually specified, not merely demanded
for f in ("valid_from", "valid_to", "recorded_from", "recorded_to"):
    ck(f"`{f}` specified in the paper", f.replace("_", r"\_") in tex)
    ck(f"`{f}` present in the schema", f in schema)

# --- Q4: the paper no longer prints the query (page budget), so instead pin
# the artefact query to the formal definition it is supposed to implement.
# Deleting the check would let q4.cypher drift away from Eq. (7) unnoticed.
q4_file = open(os.path.join(HERE, "evaluation", "q4.cypher"),
               encoding="utf-8").read()
q4_file = "\n".join(l for l in q4_file.splitlines()
                    if not l.strip().startswith("//"))


def norm(s):
    return re.sub(r"\s+", " ", s).strip().lower().rstrip(";")


for clause in ("match p =", "list_sum(list_transform(", "max(path_latency)",
               "governed_by", "max_staleness_minutes"):
    ck(f"q4.cypher implements `{clause}`", clause in norm(q4_file))
# Eq. (7) is now the paper's only statement of Q4, so it must be present and
# must still define both the path-local sum and the cross-path maximum.
ck("paper states Q4 formally (eq:q4)", r"\label{eq:q4}" in tex)
for sym in (r"L(P)", r"\mathrm{ImpliedStaleness}", r"\max_{P"):
    ck(f"eq:q4 defines {sym}", sym in tex)
ck("paper points at the executed query",
   "q4.cypher" in tex)

# --- verdict marks are defined before use
for m in ("ry", "rp", "rn", "rna"):
    ck(f"verdict macro \\{m} defined",
       re.search(r"\\newcommand\{\\" + m + r"\}", tex) is not None)

# --- no unverified cell reaches the paper
ck("no `?` verdict in the capability matrix",
   not any(v[0] == "?" for layer in ("representation", "expressiveness")
           for k, cells in cm[layer].items() if not k.startswith("_")
           for v in cells.values()))

# --- the paper's prose about the Q4 path set must match the enumeration the
# run actually produced. An earlier draft said "three distinct paths" when
# there are four; prose describing the validation data is exactly the kind of
# claim that drifts without a check.
paths = res.get("q4_paths") or []
WORD = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}
ck("results.json records the Q4 path enumeration", bool(paths),
   f"{len(paths)} paths")
if paths:
    n = len(paths)
    ck(f"paper says {WORD[n]} paths into daily_revenue",
       f"{WORD[n]} distinct" in tex or f"{WORD[n]} paths" in tex,
       f"expected the word '{WORD[n]}'")
    # every path total quoted in the prose must be one the run produced
    totals = sorted((p["total_minutes"] for p in paths), reverse=True)
    ck("paper's headline staleness equals the max path total",
       f"{totals[0]} minutes" in tex, f"max={totals[0]}")
    others = ", ".join(str(t) for t in totals[1:])
    ck("paper lists the remaining path totals",
       others in tex or " and ".join([", ".join(str(t) for t in totals[1:-1]),
                                      str(totals[-1])]) in tex,
       f"others={others}")

# --- abstract and evaluation agree
ck("all seven queries matched, as the abstract states",
   all(q["matched_expected"] for q in res["queries"].values()),
   f"{sum(q['matched_expected'] for q in res['queries'].values())}/7")
n_nodes = sum(res["node_counts"].values())
n_edges = sum(res["edge_counts"].values())
ck("graph size in prose matches results.json",
   f"{n_nodes} nodes" in tex and f"{n_edges} edges" in tex,
   f"{n_nodes} nodes / {n_edges} edges")

# --- the "no more than three of seven" claim must follow from the derivation
order = {"N": 0, "-": 1, "P": 2, "Y": 3}
best = 0
for s_name in cm["systems"]:
    n_y = 0
    for q, req in cm["requirements"].items():
        cells = ([cm["representation"][k][s_name] for k in req["representation"]]
                 + [cm["expressiveness"][k][s_name] for k in req["expressiveness"]])
        if any(c[0] == "-" for c in cells):
            continue
        if min((c[0] for c in cells), key=lambda v: order[v]) == "Y":
            n_y += 1
    best = max(best, n_y)
ck("no system answers more than three queries, as claimed",
   best <= 3, f"max answered = {best}")

print(f"\n{len(fails)} failure(s)")
sys.exit(1 if fails else 0)
