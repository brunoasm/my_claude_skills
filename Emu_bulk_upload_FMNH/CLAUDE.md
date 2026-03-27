# Emu Bulk Upload Skill — FMNH Entomology

Interactive Claude skill to help insect curators bulk upload specimen data to the Emu database at the Field Museum of Natural History (FMNH). Emu has no API, so the workflow involves downloading existing records, matching/comparing, creating upload tables, and guiding users through Emu's bulk upload interface.

## Roadmap

### Phase 1: Sites (current)
Match user locality data to existing Emu site records. Create new site records where needed (with recursive parent finding). Output user table with site IRN column.

### Phase 2: Events (planned)
Match collecting events (date, collector, method) linked to site IRNs from Phase 1.

### Phase 3: Catalog (planned)
Upload specimen catalog records linking to event records from Phase 2.

### Phase 4: Other entities (planned)
Taxonomy, collector parties, and other dependent records.

## Data conventions

- User data is an xlsx file. Row 1 = user-friendly field names, Row 2 = Emu field names, Row 3 = example, data starts Row 4.
- Column colors indicate Emu modules: green fill (`FFCCFFCC`) = Sites module.
- User xlsx field names use `_tab` suffixes (e.g., `LocCountry_tab`); Emu CSV exports use bare names (`LocCountry`).
- Coordinate fields differ: user has `LatLatitude_nesttab`/`LatLongitude_nesttab`, Emu export has `LatPreferredCentroidLatDec`/`LatPreferredCentroidLongDec`.

## Site hierarchy (most general to most precise)
1. `LocContinent`
2. `LocCountry`
3. `LocProvinceStateTerritory`
4. `LocDistrictCountyShire`
5. `LocTownship`
6. `LocPreciseLocation`

## User privilege gating
Some users have Emu bulk upload privileges, others do not. Ask at session start. Users without privileges get data prep assistance and are asked to send tables to their collection manager. Users with privileges are walked through the Emu upload interface.

## Project structure
```
CLAUDE.md                          # This file
SKILL.md                           # Interactive skill specification
references/
  emu_field_mapping.md             # Field name mappings and conventions
scripts/
  parse_user_data.py               # Extract site columns from user xlsx
  parse_emu_export.py              # Index Emu CSV export for matching
  deduplicate_sites.py             # Deduplicate user sites
  match_sites.py                   # Match sites by coordinates or name
  find_parents.py                  # Recursive parent finding
  generate_bulk_upload.py          # Create bulk upload xlsx tables
  finalize_user_table.py           # Add IRN column to user table
skill_building_docs/
  instructions.txt                 # Original workflow specification
  Weevil_workshop_cryo.xlsx        # Example user data
  Group1.csv                       # Example Emu sites export (USA)
```

## Dependencies
- Python 3 with `openpyxl` (for xlsx I/O)
- Python stdlib: `csv`, `json`, `difflib`, `os`, `sys`
