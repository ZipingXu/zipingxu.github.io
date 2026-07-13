#!/usr/bin/env python3
"""Regenerate the website's section HTML from the CV LaTeX source.

Single source of truth: the Overleaf CV clone at
  ~/my_folder/knowledge/cv/Overleaf/  (main.tex + conference.bib)

Generated files (do NOT edit these by hand — edit the CV instead):
  assets/papers_with_years.html   <- conference.bib
  assets/awards.html              <- main.tex  "Fellowships & Awards"
  assets/teaching.html            <- main.tex  "Teaching Experiences" + "Mentoring Experience"
  assets/reviewing.html           <- main.tex  "Professional Activities"
  assets/invited_talks.html       <- main.tex  "Invited Talks"
  assets/CV.pdf                   <- Overleaf main.pdf

Hand-maintained (never touched by this script):
  assets/news.html                website-only news feed
  data/paper_links.json           paper links shown on the site (the CV has none);
                                  keyed by BibTeX key: {"key": [{"label": "...", "url": "..."}]}

Usage:
  python3 build_from_cv.py           # regenerate from the local CV clone
  python3 build_from_cv.py --pull    # git-pull the Overleaf clone first
"""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent
CV_REPO = Path.home() / 'my_folder/knowledge/cv/Overleaf'
BIB = CV_REPO / 'conference.bib'
MAINTEX = CV_REPO / 'main.tex'
LINKS_FILE = SITE / 'data/paper_links.json'


# --------------------------------------------------------------------------
# LaTeX helpers
# --------------------------------------------------------------------------

def read_balanced(text, i):
    """text[i] == '{'; return (content, index after closing brace)."""
    assert text[i] == '{'
    depth, j = 0, i
    while j < len(text):
        if text[j] == '{':
            depth += 1
        elif text[j] == '}':
            depth -= 1
            if depth == 0:
                return text[i + 1:j], j + 1
        j += 1
    raise ValueError(f'unbalanced braces at {i}')


def strip_comments(tex):
    return re.sub(r'(?<!\\)%.*', '', tex)


def latex_to_html(s):
    s = re.sub(r'\\href\{([^}]*)\}\{([^}]*)\}', r'<a href="\1">\2</a>', s)
    s = re.sub(r'\\textbf\{([^{}]*)\}', r'<strong>\1</strong>', s)
    s = re.sub(r'\\textit\{([^{}]*)\}', r'\1', s)
    # nested \textit{\textbf{...}} handled by running textbf first, textit second;
    # one more pass for any leftovers
    s = re.sub(r'\\textit\{(.*?)\}', r'\1', s)
    s = s.replace('\\&', '&amp;').replace('\\$', '$').replace('\\%', '%')
    s = s.replace('``', '"').replace("''", '"')
    s = s.replace('~', ' ')
    s = s.replace('---', '&mdash;').replace('--', '&ndash;')
    s = re.sub(r'\\hspace\{[^}]*\}|\\vspace\{[^}]*\}|\\small|\\large', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def strip_braces(s):
    """Remove protective braces: {JITAIs} -> JITAIs, {R}einforcement -> Reinforcement."""
    prev = None
    while prev != s:
        prev = s
        s = re.sub(r'\{([^{}]*)\}', r'\1', s)
    return s


# --------------------------------------------------------------------------
# Publications from conference.bib
# --------------------------------------------------------------------------

def parse_bib(path):
    text = path.read_text()
    entries = []
    for m in re.finditer(r'@(\w+)\s*\{', text):
        body, _ = read_balanced(text, m.end() - 1)
        key, _, rest = body.partition(',')
        fields = {}
        i = 0
        for fm in re.finditer(r'(\w[\w+-]*)\s*=\s*', rest):
            if fm.start() < i:
                continue
            j = fm.end()
            if j < len(rest) and rest[j] == '{':
                val, i = read_balanced(rest, j)
            elif j < len(rest) and rest[j] == '"':
                k = rest.index('"', j + 1)
                val, i = rest[j + 1:k], k + 1
            else:
                k = re.search(r'[,\n]', rest[j:])
                k = j + (k.start() if k else 0)
                val, i = rest[j:k], k
            fields[fm.group(1).lower()] = val.strip()
        entries.append({'type': m.group(1).lower(), 'key': key.strip(), **fields})
    return entries


def format_author(tok):
    star = bool(re.search(r'\$\^?[\\]?[*∗]|\$\^\*\$', tok)) or '$^*$' in tok
    tok = re.sub(r'\$\^\{?\\?\*?a?s?t?\}?\$', '', tok.replace('$^*$', ''))
    bold = '\\textbf' in tok
    tok = re.sub(r'\\textbf\{([^{}]*)\}', r'\1', tok)
    tok = strip_braces(tok).strip().strip(',').strip()
    if tok.lower() == 'others':
        return 'et al.', False
    if ',' in tok:
        last, first = [p.strip() for p in tok.split(',', 1)]
        name = f'{first} {last}'
    else:
        name = tok
    name = re.sub(r'\s+', ' ', name).replace(' ', '&nbsp;') if False else re.sub(r'\s+', ' ', name)
    if bold:
        name = f'<strong>{name}</strong>'
    if star:
        name += '*'
    return name, tok.lower() == 'others'


def format_authors(field):
    toks = re.split(r'\s+and\s+', field.replace('\n', ' '))
    names = [format_author(t)[0] for t in toks if t.strip()]
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f'{names[0]} and {names[1]}'
    if names[-1] == 'et al.':
        return ', '.join(names[:-1]) + ', et al.'
    return ', '.join(names[:-1]) + f', and {names[-1]}'


def format_venue_extras(e):
    venue = e.get('journal') or e.get('booktitle') or ''
    venue = strip_braces(venue.replace('\n', ' '))
    venue = re.sub(r'^In\s+', '', venue).strip()
    venue = venue.replace('\\&', '&amp;')
    extras = []
    if e.get('volume'):
        extras.append(f"vol. {e['volume']}")
    pages = e.get('pages', '').replace('--', '--').strip()
    if pages:
        if '-' in pages:
            extras.append(f"pp. {pages.replace('---', '--').replace('-', '--').replace('----', '--')}")
        elif pages.isdigit() and len(pages) <= 5:
            extras.append(f'p. {pages}')
        else:
            extras.append(pages)
    for f in ('publisher', 'organization'):
        if e.get(f):
            extras.append(strip_braces(e[f]))
    return venue, ', '.join(extras)


def entry_links(e, overrides):
    if e['key'] in overrides:
        return overrides[e['key']]
    for field, label in (('pdf', 'pdf'), ('url', 'http'), ('doi', 'DOI')):
        if e.get(field):
            url = e[field]
            if field == 'doi' and not url.startswith('http'):
                url = f'https://doi.org/{url}'
            return [{'label': label, 'url': url}]
    return []


def build_publications():
    overrides = json.loads(LINKS_FILE.read_text()) if LINKS_FILE.exists() else {}
    entries = parse_bib(BIB)
    unknown = set(overrides) - {e['key'] for e in entries}
    if unknown:
        print(f'  warning: paper_links.json keys not in conference.bib: {sorted(unknown)}')

    by_year = {}
    for e in entries:
        by_year.setdefault(e.get('year', 'n.d.'), []).append(e)

    out = ['<bold>You can view my full list of publications at '
           '<a href="https://scholar.google.com/citations?user=V-VcaYIAAAAJ&hl=en&oi=ao">'
           'Google Scholar</a></bold>',
           '<br>', '(* denotes equal contribution)', '<table>', '']
    for year in sorted(by_year, reverse=True):
        out.append(f'<tr><td><h3>{year}</h3></td></tr>\n')
        for e in by_year[year]:
            title = strip_braces(e.get('title', '').replace('\n', ' '))
            title = re.sub(r'\s+', ' ', title).strip()
            authors = format_authors(e.get('author', '')).removesuffix('.')
            venue, extras = format_venue_extras(e)
            venue_line = f'<em><br>{venue}</em>'
            if extras:
                venue_line += f', {extras}'
            links = entry_links(e, overrides)
            link_html = ''
            if links:
                parts = ' | '.join(f'<a href="{l["url"]}">{l["label"]}</a>' for l in links)
                link_html = f'\n [&nbsp;{parts}&nbsp;]'
            out.append('<tr valign="top">\n<td class="bibtexitem">\n'
                       f'<b>{title}</b><br>\n{authors}.\n {venue_line}.\n {year}.'
                       f'{link_html}\n</td>\n</tr>\n')
    out.append('</table>')
    return '\n'.join(out) + '\n'


# --------------------------------------------------------------------------
# main.tex sections
# --------------------------------------------------------------------------

def parse_maintex(path):
    """Return list of (section, subsection, date, content) in document order."""
    tex = strip_comments(path.read_text())
    tex = tex[tex.index('\\begin{document}'):]
    items = []
    section = subsection = None
    i = 0
    while i < len(tex):
        m = re.compile(r'\\(section|subsection|cvitem|cventry)\s*(\[[^\]]*\])?\{').search(tex, i)
        if not m:
            break
        cmd = m.group(1)
        arg1, j = read_balanced(tex, m.end() - 1)
        if cmd == 'section':
            section, subsection = latex_to_html(arg1), None
        elif cmd == 'subsection':
            subsection = latex_to_html(arg1)
        elif cmd == 'cvitem':
            k = j
            while k < len(tex) and tex[k] in ' \t\n':
                k += 1
            content, j = read_balanced(tex, k)
            items.append((section, subsection, arg1.strip(), content.strip()))
        else:  # cventry — skip its remaining 5 args
            for _ in range(5):
                k = j
                while k < len(tex) and tex[k] in ' \t\n':
                    k += 1
                _, j = read_balanced(tex, k)
        i = j
    return items


GRID2 = '<div class="teaching-grid" style="grid-template-columns: {w} auto; gap: 0.3rem;">'


def rows_html(rows, width='130px'):
    parts = [GRID2.format(w=width)]
    for date, content in rows:
        parts.append(f'        <div style="padding-right: 1rem;">{date}</div>')
        parts.append(f'        <div>{content}</div>\n')
    parts.append('    </div>')
    return '\n'.join(parts)


def build_awards(items):
    rows = [(latex_to_html(d), latex_to_html(c))
            for s, _, d, c in items if s and s.startswith('Fellowships') and d]
    return f'<div class="news-item">\n    {rows_html(rows, "85px")}\n</div>\n'


def build_reviewing(items):
    groups = {}
    order = []
    for s, sub, d, c in items:
        if s == 'Professional Activities' and sub:
            if sub not in groups:
                groups[sub] = []
                order.append(sub)
            groups[sub].append((latex_to_html(d), latex_to_html(c)))
    parts = ['<div class="news-item">']
    for gi, sub in enumerate(order):
        if gi:
            parts.append('\n    <br>')
        parts.append(f'    <h3>{sub}</h3>')
        parts.append('    ' + rows_html(groups[sub]))
    parts.append('</div>')
    return '\n'.join(parts) + '\n'


def build_teaching(items):
    parts = ['<div class="news-item">']
    # Teaching subsections (Teaching Fellow / Graduate Student Instructor)
    subs = {}
    order = []
    for s, sub, d, c in items:
        if s == 'Teaching Experiences' and sub:
            course, _, inst = c.partition('\\hfill')
            if sub not in subs:
                subs[sub] = []
                order.append(sub)
            subs[sub].append((latex_to_html(d), latex_to_html(course), latex_to_html(inst)))
    for gi, sub in enumerate(order):
        if gi:
            parts.append('\n    <br>')
        parts.append(f'    <h3>{sub}</h3>')
        parts.append('    <div class="teaching-grid" style="grid-template-columns: 130px '
                     'minmax(150px, 500px) minmax(100px, auto); gap: 0.3rem;">')
        for date, course, inst in subs[sub]:
            parts.append(f'        <div style="padding-right: 1rem;">{date}</div>')
            parts.append(f'        <div style="padding-right: 1rem;">{course}</div>')
            parts.append(f'        <div>{inst}</div>\n')
        parts.append('    </div>')
    # Mentoring: cvitem with a date starts a student; empty-date cvitems are detail lines
    parts.append('\n    <br>\n    <h3>Mentoring Experience</h3>')
    parts.append('    <div class="teaching-grid" style="grid-template-columns: 130px auto;">')
    students = []
    for s, _, d, c in items:
        if s != 'Mentoring Experience':
            continue
        if d:
            students.append([latex_to_html(d), [latex_to_html(c)]])
        elif students:
            students[-1][1].append(latex_to_html(c))
    for date, lines in students:
        parts.append(f'        <div style="padding-right: 1rem;">{date}</div>')
        parts.append(f'        <div>{"<br>".join(lines)}</div>\n')
    parts.append('    </div>\n</div>')
    return '\n'.join(parts) + '\n'


def build_talks(items):
    parts = ['<div class="news-item">']
    talks = [(latex_to_html(d), c) for s, _, d, c in items if s == 'Invited Talks' and d]
    for ti, (date, raw) in enumerate(talks):
        m = re.match(r"\s*``(.*)''\s*,\s*(.*)$", raw, re.S)
        title, venue = (m.group(1), m.group(2)) if m else (raw, '')
        if ti:
            parts.append('    <br>')
        parts.append(f'    <span class="talk-title">{latex_to_html(title)}</span>')
        parts.append(f'    <span class="date">{date}</span>')
        parts.append('    <div class="review-item">')
        parts.append(f'        {latex_to_html(venue)}')
        parts.append('    </div>')
    parts.append('</div>')
    return '\n'.join(parts) + '\n'


# --------------------------------------------------------------------------

def main():
    if '--pull' in sys.argv:
        print(f'pulling {CV_REPO} ...')
        subprocess.run(['git', '-C', str(CV_REPO), 'pull', '--no-rebase'], check=True)

    for f in (BIB, MAINTEX):
        if not f.exists():
            sys.exit(f'missing CV source: {f}')

    items = parse_maintex(MAINTEX)
    outputs = {
        'assets/papers_with_years.html': build_publications(),
        'assets/awards.html': build_awards(items),
        'assets/reviewing.html': build_reviewing(items),
        'assets/teaching.html': build_teaching(items),
        'assets/invited_talks.html': build_talks(items),
    }
    for rel, content in outputs.items():
        path = SITE / rel
        old = path.read_text() if path.exists() else None
        path.write_text(content)
        status = 'unchanged' if content == old else 'updated  '
        print(f'  {status} {rel}')

    cv_pdf = CV_REPO / 'main.pdf'
    if cv_pdf.exists():
        dest = SITE / 'assets/CV.pdf'
        changed = (not dest.exists()) or dest.read_bytes() != cv_pdf.read_bytes()
        if changed:
            shutil.copyfile(cv_pdf, dest)
        print(f'  {"updated  " if changed else "unchanged"} assets/CV.pdf (from Overleaf main.pdf)')

    print('done. news.html is hand-maintained; paper links live in data/paper_links.json.')


if __name__ == '__main__':
    main()
