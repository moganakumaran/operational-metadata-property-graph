# Template provenance

The paper builds with `\documentclass[conference]{IEEEtran}`.

Nothing is vendored. `IEEEtran.cls` and `IEEEtran.bst` are on CTAN and ship
with every TeX Live / MacTeX distribution, and tectonic pulls them from its
TeX Live bundle on first build, so the repository carries no class or style
file and no third-party redistribution question arises.

| | |
|---|---|
| Class | `IEEEtran`, option `conference` |
| Bibliography | `IEEEtran.bst`, via `\bibliographystyle{IEEEtran}` |
| Source | CTAN, fetched by tectonic from its TeX Live bundle |
| Engine | tectonic (`tectonic -X compile paper.tex`) |

## Two things the class needed help with

Both were found by rendering the PDF, not by reading the log, and both are set
in the preamble with a comment saying why:

- **Fonts.** IEEEtran asks for Times (`ptm`) shapes that are not set up under
  the Unicode encoding tectonic's engine uses. The result is not an error:
  every bold and small-caps run silently falls back to the default family, so
  `\textbf` produces no bold at all. `newtxtext`/`newtxmath` supply the shapes.
  They must load **after** `amssymb` with `\let\Bbbk\relax`, because both
  packages define that symbol and the clash is an error rather than a warning.

- **Table captions.** IEEEtran sets them in small caps above the table, where
  anything longer than a line is unreadable. The two long captions inherited
  from the Springer build were cut to a title, and their detail moved to a
  `\scriptsize` note under the bottom rule. `make_tables.py` emits generated
  tables in the same shape (`note_block()`).

## Previous template

Before this build the manuscript targeted *Datenbank-Spektrum* and used
Springer Nature's `sn-jnl.cls` with the `[iicol]` option, vendored here with a
checksum because it is not on CTAN and not in tectonic's bundle. That build,
`sn-jnl.cls`, `sn-basic.bst` and the `bst/` style directory are on the `main`
branch of this repository and were removed when the paper moved to IEEE
format.
