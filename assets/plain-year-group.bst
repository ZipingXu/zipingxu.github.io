% Based on plain.bst with modifications for year grouping
ENTRY
  { address
    author
    booktitle
    chapter
    edition
    editor
    howpublished
    institution
    journal
    key
    month
    note
    number
    organization
    pages
    publisher
    school
    series
    title
    type
    volume
    year
  }
  {}
  { label extra.label sort.label sort.year }

INTEGERS { output.state before.all mid.sentence after.sentence after.block current.year }

% ... [previous plain.bst functions remain the same] ...

FUNCTION {init.state.consts}
{ #0 'before.all :=
  #1 'mid.sentence :=
  #2 'after.sentence :=
  #3 'after.block :=
  #9999 'current.year := % Initialize current year to a high value
}

FUNCTION {new.year.block}
{ year empty$
    { skip$ }
    { year text.to_number current.year =
        { skip$ }
        { year text.to_number 'current.year :=
          "\end{thebibliography}" write$ newline$
          "\section*{" current.year int.to.str$ * "}" * write$ newline$
          "\begin{thebibliography}{}" write$ newline$
        }
      if$
    }
  if$
}

FUNCTION {presort}
{ calc.label
  label sortify
  "    "
  *
  type$ "book" =
  type$ "inbook" =
  or
    'author.editor.sort
    { type$ "proceedings" =
        'editor.sort
        'author.sort
      if$
    }
  if$
  #1 entry.max$ substring$
  'sort.label :=
  sort.label
  year field.or.null sortify
  "    "
  *
  title field.or.null
  sort.format.title
  *
  #1 entry.max$ substring$
  'sort.key$ :=
  year empty$
    { "" }
    { year }
  if$
  'sort.year :=
}

ITERATE {presort}

SORT

FUNCTION {begin.bib}
{ preamble$ empty$
    'skip$
    { preamble$ write$ newline$ }
  if$
  "\begin{thebibliography}{}" write$ newline$
}

% ... [rest of plain.bst functions remain the same] ...

READ

EXECUTE {init.state.consts}

ITERATE {call.type$}

FUNCTION {end.bib}
{ newline$
  "\end{thebibliography}" write$ newline$
} 