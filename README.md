# ELO Javadoc Scraper

A Python script that scrapes ELO Javadoc documentation and converts it into Markdown format. This tool is designed to make ELO's Java API documentation more accessible and easier to read for AI.

## Features

- Scrapes complete Javadoc documentation from ELO's forum
- Supports multiple Javadoc versions and modules (ix, jc, as)
- Handles both modern (Java 11+) and legacy Javadoc formats
- Extracts detailed information including:
  - Package structure
  - Class descriptions
  - Method signatures and documentation
  - Constructor details
  - Parameter descriptions
  - Return values
  - Method overrides
- Generates a well-structured Markdown file with:
  - Table of Contents
  - Package organization
  - Class hierarchies
  - Detailed method documentation

## Prerequisites

- Python 3.x
- Required Python packages:
  - `requests`
  - `beautifulsoup4`
  - `certifi`
  - `markdown`

## Installation

1. Clone or download this repository
2. Install the required packages:
```bash
pip install requests beautifulsoup4 certifi markdown
```

## Usage

Run the script from the command line with a Javadoc URL as the argument:

```bash
python scraper.py <javadoc_url>
```

### Example URLs:
```bash
python scraper.py https://forum.elo.com/javadoc/ix/23/
python scraper.py https://forum.elo.com/javadoc/jc/23/
python scraper.py https://forum.elo.com/javadoc/as/23/
```

You can also use shortened versions of the URLs:
```bash
python scraper.py ix/23
python scraper.py jc/23
python scraper.py as/23
```

## Output

The script generates a Markdown file named based on the input URL (e.g., `javadoc.ix.23.md`). The output file includes:
- A comprehensive table of contents
- Package-level organization
- Detailed class documentation
- Method signatures and descriptions
- Parameter details
- Return value information
- Inheritance hierarchies

## Error Handling

The script includes robust error handling for:
- SSL certificate verification
- Network connection issues
- Different Javadoc format versions
- UTF-8 encoding
- Missing or malformed documentation

## Debugging

The script provides detailed debug information during execution:
- Python environment details
- SSL configuration
- Package detection
- HTML structure analysis
- Processing progress

## Note

This script is specifically designed for ELO's Javadoc documentation structure. It may require modifications to work with other Javadoc sources.
