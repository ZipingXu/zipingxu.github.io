bibtex2html -nodoc -nofooter -noheader -nokeywords -noabstract -s mybold.bst -nobibsource -d -r papers.bib && sed -i '' 's/Ziping Xu/<strong>Ziping Xu<\/strong>/g' papers.html
