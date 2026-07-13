# zipingxu.github.io

Personal academic homepage. Static HTML/CSS; section content is loaded from
partials in `assets/`.

## Single source of truth: the CV

All CV-derived sections (publications, awards, teaching, mentoring, service,
invited talks, and the CV PDF itself) are **generated from the CV LaTeX source**,
the Overleaf clone at `~/my_folder/knowledge/cv/Overleaf/` (`main.tex` +
`conference.bib`). To update the website content:

1. Edit the CV (on Overleaf or in the clone) — bib entries, `\cvitem` lines, etc.
2. From this repo:

   ```bash
   python3 build_from_cv.py --pull   # --pull syncs the Overleaf clone first
   ```

3. Review `git diff`, then commit and push.

Generated files — **never edit these by hand**, they are overwritten:

- `assets/papers_with_years.html` ← `conference.bib`
- `assets/awards.html` ← `main.tex` "Fellowships & Awards"
- `assets/teaching.html` ← `main.tex` "Teaching Experiences" + "Mentoring Experience"
- `assets/reviewing.html` ← `main.tex` "Professional Activities"
- `assets/invited_talks.html` ← `main.tex` "Invited Talks"
- `assets/CV.pdf` ← Overleaf `main.pdf`

Hand-maintained files:

- `assets/news.html` — website-only news feed (short items, newest first).
- `data/paper_links.json` — paper links (arXiv/pdf/DOI) shown on the site but
  not on the CV, keyed by BibTeX key. Links also come automatically from a
  bib entry's `pdf`/`url`/`doi` field; this file overrides those.
- `index.html`, `styles.css` — page structure and design.

The old `bibtex2html` flow (`papers.bib` + `add_year_sections.py`) is
superseded by `build_from_cv.py`.

## Local preview

```bash
python3 dev_server.py   # then open http://localhost:8000
```
