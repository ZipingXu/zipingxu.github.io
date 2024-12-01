import re

def add_year_sections(input_file, output_file):
    # Read the input file
    with open(input_file, 'r') as f:
        content = f.read()

    # Split into individual entries
    entries = content.split('<tr valign="top">')
    
    # The first element will be the header (before first entry)
    header = entries[0]
    entries = entries[1:]  # Remove the header from entries

    # Extract year from each entry and pair it with the entry
    year_entries = []
    for entry in entries:
        # Look for year in various formats
        year_match = re.search(r'\b(20\d{2})\b', entry)
        if year_match:
            year = int(year_match.group(1))
            year_entries.append((year, '<tr valign="top">' + entry))
        else:
            print(f"Warning: Could not find year in entry: {entry[:100]}...")

    # Group by year (maintaining original order)
    current_year = None
    output_content = [header]  # Start with the header

    for year, entry in year_entries:
        if year != current_year:
            # Add year header
            output_content.append(f'<tr><td colspan="2"><h3>{year}</h3></td></tr>\n\n')
            current_year = year
        output_content.append(entry)

    # Write to output file
    with open(output_file, 'w') as f:
        f.write(''.join(output_content))

add_year_sections('assets/papers.html', 'assets/papers_with_years.html')