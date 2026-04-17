# Emu Bulk Upload Skill — FMNH Entomology

Interactive Claude skill to help insect curators bulk upload specimen data to the Emu database at the Field Museum of Natural History (FMNH). Emu has no API, so the workflow involves mapping user data to Emu's format, downloading existing records, matching/comparing, creating upload tables, and guiding users through Emu's bulk upload interface.

## Roadmap

### Data intake (current)
Accept user data in any format (xlsx, csv, tsv, etc.) and map it to the Emu template format. Claude analyzes the input, proposes column mappings, and builds transformation scripts on the fly.

### Phase 1: Sites (current)
Match user locality data to existing Emu site records. Create new site records where needed (with recursive parent finding). Output user table with site IRN column.

### Phase 2: Events (planned)
Match collecting events (date, collector, method) linked to site IRNs from Phase 1.

### Phase 3: Catalog (planned)
Upload specimen catalog records linking to event records from Phase 2.

### Phase 4: Other entities (planned)
Taxonomy, collector parties, and other dependent records.

## Data conventions

- The Emu upload template is at `references/Emu_upload_default.xlsx` (49 columns, 3 modules).
- Template format: Row 1 = user-friendly field names, Row 2 = Emu field names, Row 3 = example, data starts Row 4.
- Column colors indicate Emu modules: green (`FFCCFFCC`) = Sites, gray (`FFC0C0C0`) = Events, tan (`FFFFCC99`) = Catalog.
- User xlsx field names use `_tab` suffixes (e.g., `LocCountry_tab`); Emu CSV exports use bare names (`LocCountry`).
- Coordinate fields differ: user has `LatLatitude_nesttab`/`LatLongitude_nesttab`, Emu export has `LatPreferredCentroidLatDec`/`LatPreferredCentroidLongDec`.

## User privilege gating
Some users have Emu bulk upload privileges, others do not. Ask at session start. Users without privileges get data prep assistance and are asked to send tables to their collection manager. Users with privileges are walked through the Emu upload interface.

## Project structure
```
CLAUDE.md                          # This file
SKILL.md                           # Interactive skill specification (main orchestrator)
README.md                          # Author credits
references/
  Emu_upload_default.xlsx          # Emu upload template (54 columns, the target format)
  emu_field_reference.md           # Complete field reference (all modules, export mappings, normalization rules)
  phase1_sites.md                  # Sites phase detailed reference
  screenshots_sites_export/        # Step-by-step Emu sites export screenshots (10 images)
scripts/
  parse_user_data.py               # Extract site columns from Emu-formatted xlsx (internal reference)
  parse_emu_export.py              # Index Emu CSV export for matching
  deduplicate_sites.py             # Deduplicate user sites
  match_sites.py                   # Match sites by coordinates or name
  find_parents.py                  # Recursive parent finding
  generate_bulk_upload.py          # Create bulk upload CSV tables
  finalize_user_table.py           # Add IRN column to user table
```

Note: `skill_building_docs/` is local-only (not tracked in git). It contains example data and original specifications.

## Dependencies
- Python 3 with `openpyxl` (for xlsx I/O)
- Python stdlib: `csv`, `json`, `difflib`, `os`, `sys`

## TODO

- [x] ~~Confirm Emu field names for unmapped template columns~~ — Resolved: UTM and Expedition columns removed from template; Other numbers 1 mapped to `ColOtherNumbers_tab`.
- [ ] Create `references/phase2_events.md` when Events phase is implemented
- [ ] Create `references/phase3_catalog.md` when Catalog phase is implemented
