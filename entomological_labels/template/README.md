# Specimen Label Preparation Tool

Prepares specimen data from the palm weevils database for mailmerge label printing.

## Installation

Create the conda environment:

```bash
conda env create -f environment.yml
conda activate specimen_labels
```

## Usage

Basic usage:
```bash
python prepare_for_labels.py -o labels.xlsx
```

### Filter by preservation type:
```bash
python prepare_for_labels.py -o labels.xlsx -p pinned
python prepare_for_labels.py -o labels.xlsx -p ethanol extracted
```

### Filter using SQL:
```bash
python prepare_for_labels.py -o labels.xlsx --sql-filter "SELECT * FROM specimens WHERE state = 'AM' AND higher_taxon = 'Anchylorhynchus'"
```

The SQL query operates on the merged specimens table. Use `--list-columns` to see available column names.

### List available columns:
```bash
python prepare_for_labels.py --list-columns
```

## Output Format

The script outputs a table with the following columns formatted for mailmerge:

- `sample_id`: Specimen ID
- `country`, `state`: Uppercased
- `locality`: From locality field, falls back to municipality
- `lat`, `lon`: Formatted with N/S/E/W prefixes, 5 decimal places
- `alt`: Altitude with 'm' suffix
- `date`: Formatted as day.roman_month.year (e.g., "20.v.2012"), supports date ranges
- `col`: Collector (primary + others if present)
- `col_method`: Collecting method + plant interaction
- `col_plant`: Plant genus + species
- `plant_auth`: Plant authority
- `certainty`, `species_certainty`: Identification certainty flags
- `higher_taxon`, `taxon_level`: Taxonomic information
- `species`: Species name (sp.* variants normalized to "sp.")
- `species_italicize`: Boolean flag for italicization
- `sex`: Specimen sex
- `genomics_id`: Extraction/genomics ID
- `det`, `det_year`: Determiner and determination year

## Data Sources

The script reads from three Excel files in `../../`:
- `insects.xlsx`: Specimen-level data
- `events.xlsx`: Collection event data
- `plants.xlsx`: Host plant data

Tables are merged as: insects LEFT JOIN events (on event_id) LEFT JOIN plants (on plant_id).

## Mailmerge Template

A Word mailmerge template is provided in `label_mailmerge_template.docx`. This template:

- Uses "coll.ID" instead of "Field book ID" for the collection identifier
- Includes a conditional "genomic.ID" field that only displays when a specimen has genomics data
- Is formatted for 3-column label sheets
- Contains all necessary mailmerge fields from the output columns above

To use with Microsoft Word mailmerge:
1. Generate label data: `python prepare_for_labels.py -o my_labels.xlsx`
2. Open `label_mailmerge_template.docx` in Word
3. Connect to the data source (my_labels.xlsx)
4. Preview and complete the merge
