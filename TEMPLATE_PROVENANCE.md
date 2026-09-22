# Template provenance

`sn-jnl.cls` and `bst/` are vendored here because the class is **not on CTAN**
and **not in tectonic's package bundle**, so the build cannot fetch it.

| | |
|---|---|
| Source | Springer Nature official LaTeX template |
| Landing page | https://www.springernature.com/gp/authors/campaigns/latex-author-support |
| Direct zip | https://cms-resources.apps.public.k8s.springernature.io/springer-cms/rest/v1/content/18782940/data/v12 |
| Version | 3.1, December 2024 (per header of `sn-article.tex`) |
| Retrieved | 21 September 2026 |
| sha256 (zip) | see below |

Not vendored: `sn-article.tex` (the demo), `fig.eps`, `empty.eps`,
`sn-bibliography.bib`, `user-manual.pdf`. Only the class and the bibliography
styles are needed to build.

Class options used: `[pdflatex,sn-basic,Numbered]`. `sn-basic` alone defaults to
author-year and then rejects a numbered bibliography.

`812e76dcaa9c28dc1bff1fb6065d51729b67d4ea140552a05088317414a3ecae`
