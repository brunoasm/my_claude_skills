# Phase 1: Sites — Reference

Detailed reference for matching user locality data to existing Emu site records, creating new site records, and obtaining IRNs.

## Overview

The Sites phase takes the user's specimen data (already mapped to Emu template format) and:
1. Exports existing site records from Emu
2. Deduplicates the user's sites
3. Matches user sites against Emu records
4. Finds parent records for unmatched sites
5. Creates bulk upload tables for new sites
6. Finalizes the user table with site IRNs

## Source hierarchy (user input)

User input is flat — one column per hierarchy level. From most general to most precise:

| Level | Canonical field | Emu CSV field | User xlsx field |
|-------|----------------|---------------|-----------------|
| 0 | `LocContinent` | `LocContinent` | `LocContinent_tab` |
| 1 | `LocCountry` | `LocCountry` | `LocCountry_tab` |
| 2 | `LocProvinceStateTerritory` | `LocProvinceStateTerritory` | `LocProvinceStateTerritory_tab` |
| 3 | `LocDistrictCountyShire` | `LocDistrictCountyShire` | `LocDistrictCountyShire_tab` |
| 4 | `LocTownship` | `LocTownship` | `LocTownship_tab` |
| 5 | `LocPreciseLocation` | `LocPreciseLocation` | `LocPreciseLocation` |

## Target schema (Emu bulk upload CSV)

The bulk upload CSV is **record-oriented**: one row per Emu node. Each user site explodes into a chain of rows (one per missing intermediate), parented via `PolParentRef.irn`.

Columns (blank columns dropped at write time):

- `SitRecordClassification` — `Terrestrial` for insects (`Marine` / `Freshwater` are valid too).
- `PolPoliticalRank` — rank of this node only (`Country`, `State`, `County`, `City`, `Village`, `Town`, `Precise Locality`, `LMA`, `Plot/Transect`, `Sample Area`, `pd2`, `pd3`, `pd4`, …). See `references/political_ranks.md` for the complete list.
- `PolLocality` — name of this node only. Blank for the unnamed Precise Locality row carrying primary coordinates.
- `LocElevationASLFromMt` / `LocElevationASLToMt` / `LocElevationASLFromFt` / `LocElevationASLToFt`
- `LatLatitudeDecimal_nesttab` / `LatLongitudeDecimal_nesttab` (the upload form uses the `_nesttab` suffix)
- `PolParentRef.irn` — parent IRN, or a `__PENDING_Bx_Ry__` placeholder when the parent will be created by an earlier batch.

## Primary coordinates → unnamed Precise Locality rule

When the user's coordinates are *primary* (came from their own sampling metadata), the deepest row of the chain is an **unnamed Precise Locality** carrying coords + elevation; its parent is the most specific named, non-georeferenced node (often a Village, Town, or Sample Area). If that named parent does not yet exist in Emu, it is created without coordinates in an earlier batch.

Ask the user at session start whether their coordinates are primary. If they say no (coordinates are inherited/centroid), skip the unnamed-precise-locality split and keep the named node itself as the deepest row.

## PolPoliticalRank vocabulary

See `references/political_ranks.md` for the full allowed list and OSM → rank mapping. Ranks are assigned per named level using OpenStreetMap via `scripts/osm_rank_lookup.py`:

- **high confidence** → auto-apply suggested rank
- **medium / low confidence** → present candidates and confirm with the user

Intermediate nodes where the user has no value at that level are simply skipped (no node created).

## Site fields used for matching

All 13 fields that define a unique site:
- 6 hierarchy fields (above)
- 4 elevation fields: `LocElevationASLFromMt`, `LocElevationASLToMt`, `LocElevationASLFromFt`, `LocElevationASLToFt`
- 2 coordinate fields: `LatLatitude`, `LatLongitude`
- 1 identifier: `SitSiteNumber`

## Exporting sites from Emu

### Choosing search criteria

Before the export, analyze the user's data and suggest the most efficient search:
- All specimens from one country → search by country
- Specimens from 2–3 states → search by state (PD2), possibly multiple exports
- Specimens spanning many countries → country-level per country, or continent search

### Quick summary

> In Emu, log in and go to the **Sites** module. In the Search window, click the **Class: Political** tab at the bottom. Type your search criteria in the appropriate field, then click **Search**. From the results, go to **Tools > Reports**, select the **"Localities Insects"** report, and click **Report...**. The exported CSV will appear in your shared folder.

### Step-by-step screenshot guide

Screenshots are at: `https://github.com/brunoasm/my_claude_skills/blob/main/Emu_bulk_upload_FMNH/references/screenshots_sites_export/`

| Step | Screenshot | Action |
|------|-----------|--------|
| 2a | [01_emu_login.png](https://github.com/brunoasm/my_claude_skills/blob/main/Emu_bulk_upload_FMNH/references/screenshots_sites_export/01_emu_login.png) | Open KE EMu (FMNH). Host: `10.10.10.25`, Service: `emufmnh`. Click OK. |
| 2b | [02_select_sites_module.png](https://github.com/brunoasm/my_claude_skills/blob/main/Emu_bulk_upload_FMNH/references/screenshots_sites_export/02_select_sites_module.png) | From the module list, click **Sites**. |
| 2c | [03_sites_search_site_tab.png](https://github.com/brunoasm/my_claude_skills/blob/main/Emu_bulk_upload_FMNH/references/screenshots_sites_export/03_sites_search_site_tab.png) | Default view when Sites opens. Click **Class: Political** tab at the bottom. |
| 2d | [04_enter_search_criteria.png](https://github.com/brunoasm/my_claude_skills/blob/main/Emu_bulk_upload_FMNH/references/screenshots_sites_export/04_enter_search_criteria.png) | In the **Class: Political** tab, type search criteria in the appropriate field (Country, PD2, PD3). |
| 2e | [05_class_political_tab.png](https://github.com/brunoasm/my_claude_skills/blob/main/Emu_bulk_upload_FMNH/references/screenshots_sites_export/05_class_political_tab.png) | Click **Search** at the bottom left to run the query. |
| 2f | [06_search_results.png](https://github.com/brunoasm/my_claude_skills/blob/main/Emu_bulk_upload_FMNH/references/screenshots_sites_export/06_search_results.png) | Results in Display mode. Check total count in status bar. |
| 2g | [07_tools_menu.png](https://github.com/brunoasm/my_claude_skills/blob/main/Emu_bulk_upload_FMNH/references/screenshots_sites_export/07_tools_menu.png) | Click **Tools** menu. |
| 2h | [08_select_reports.png](https://github.com/brunoasm/my_claude_skills/blob/main/Emu_bulk_upload_FMNH/references/screenshots_sites_export/08_select_reports.png) | Click **Reports...**. |
| 2i | [09_choose_localities_insects_report.png](https://github.com/brunoasm/my_claude_skills/blob/main/Emu_bulk_upload_FMNH/references/screenshots_sites_export/09_choose_localities_insects_report.png) | Select **Localities Insects**, click **Report...**. |
| 2j | [10_exported_file_in_shared_folder.png](https://github.com/brunoasm/my_claude_skills/blob/main/Emu_bulk_upload_FMNH/references/screenshots_sites_export/10_exported_file_in_shared_folder.png) | CSV appears in shared folder. |

If search requires multiple exports, repeat steps 2e–2j for each.

## Scripts

### parse_emu_export.py

Parses Emu CSV export into a searchable JSON index.

```bash
python3 scripts/parse_emu_export.py <emu_export.csv> /tmp/emu_index.json
```

Creates three indices:
- `coord_index`: spatial bucketing by rounded lat/lon for proximity search
- `name_indices`: per-field name lookup for fuzzy matching
- `records`: full record list

The index can be large (~100MB for 200K+ records). It loads once and is reused.

### deduplicate_sites.py

Groups specimens by identical site (all 13 site fields must match).

```bash
python3 scripts/deduplicate_sites.py /tmp/emu_user_sites.json /tmp/emu_dedup.json
```

### match_sites.py

Matches user sites against Emu index.

```bash
python3 scripts/match_sites.py /tmp/emu_dedup.json /tmp/emu_index.json /tmp/emu_match.json
```

**Matching strategy**:
1. If coordinates exist → search by coordinate proximity (555m tolerance)
2. If no coordinates → fuzzy search by most precise hierarchy field
3. Candidates scored with weighted hierarchy fields (more precise = higher weight)
4. Classification: exact_match (score >= 90), near_match (60–89), no_match (< 60)

### find_parents.py

Finds the nearest existing parent for each unmatched site AND emits the chain of intermediate nodes the user specified below that parent (each defaulting to `needs_creation`). Claude then checks each intermediate with `match_named_node` (see `match_sites.py`) to flip `needs_creation` → `exists` when a suitable existing node is found.

```bash
python3 scripts/find_parents.py /tmp/emu_match.json /tmp/emu_index.json /tmp/emu_parents.json
```

**Parent rules**:
- Parents cannot have a `SitSiteNumber`.
- Parents must be at a higher hierarchy level than the child.
- Parents must NOT have data below their own hierarchy level (enforced by `match_named_node`).
- Every intermediate level the user provided must exist as a separate node. Missing intermediates are confirmed with the user one-by-one before being added to the upload plan.

### osm_rank_lookup.py

Suggests a `PolPoliticalRank` for a named locality by querying OpenStreetMap Nominatim.

```bash
python3 scripts/osm_rank_lookup.py "San Simon" "United States" --parent "Arizona" --lat 31.99 --lon -109.17
```

Returns `{suggested_rank, confidence, candidates, osm_evidence}`. Confidence `high` → auto-apply; `medium`/`low` → confirm with user.

### generate_bulk_upload.py

Creates CSV tables for new Sites records from a resolved chains file.

```bash
python3 scripts/generate_bulk_upload.py /tmp/emu_site_chains.json /tmp/emu_upload/
```

Input `chains.json` is assembled by Claude from `find_parents` output + OSM rank suggestions + user confirmations. Each chain is a list of `{rank, name, status, coords, elevation}` nodes anchored to a known `parent_irn`. See the docstring in the script for the full format.

Output:
- `sites_upload_batch_1.csv` — nodes that parent directly to an existing Emu record.
- `sites_upload_batch_N.csv` — nodes that parent to a row in batch N-1 (placeholders `__PENDING_Bx_Ry__` are substituted after each batch is uploaded and the new IRNs come back).
- `upload_metadata.json` — dependency map.

Entirely blank columns are auto-removed.

### finalize_user_table.py

Adds `ColSiteRef.irn` column to user table.

```bash
python3 scripts/finalize_user_table.py <original.xlsx> <irn_mapping.json> <output.xlsx>
```

IRN mapping format (created by Claude):
```json
{"row_irn_map": {"4": "123456", "5": "123457"}}
```

## Match review guidelines

### Exact matches (score >= 90)
Report silently: "N sites matched existing Emu records."

### Near matches (score 60–89)
Present each with a comparison table:
- User's values vs Emu record values
- Coordinate distance (if applicable)
- Score and similarity details
- Assessment (e.g., "Likely typo: 'Chochise' vs 'Cochise'")
- Ask user to confirm or reject

### No matches
Need new records + parent finding.

### Known equivalences
- "United States" ↔ "United States of America"
- Coordinate matches within ~500m + matching elevation = likely same site
- Close coordinates (<100m) but different precise location → flag for review

## Upload instructions

**Users WITH bulk upload privileges**:
1. Open Emu → Sites module
2. File > Import to load the batch file
3. After upload, export newly created records to get IRNs
4. Provide exported file back to Claude

**Users WITHOUT privileges**:
Send the upload table to your collection manager and ask them to:
1. Upload records to Emu
2. Return the table with a new `ColSiteRef.irn` column containing assigned IRNs
