---
name: emu-bulk-upload
description: "Help museum insect curators bulk upload specimen data to the Emu database. Matches locality data to existing Emu site records, finds parent sites, creates bulk upload tables, and walks users through the upload process."
---

# Emu Bulk Upload Skill

Help users prepare and upload entomological specimen data to the Emu collection database at the Field Museum of Natural History (FMNH). The process involves matching user locality data to existing Emu records, creating new records where needed, and producing properly formatted tables for bulk upload.

## When to use

- User wants to upload specimen data to Emu
- User needs to match localities to existing Emu site records
- User has a spreadsheet of specimen data that needs database preparation
- Keywords: "bulk upload", "Emu", "upload specimens", "match sites", "prepare data"

## Session start: privilege gating

Before any work, ask the user:

> Do you have Emu bulk upload privileges? (If you're not sure what this means, the answer is probably no.)

Record the answer. It determines how upload steps are handled later:
- **With privileges**: walk through Emu upload steps directly
- **Without privileges**: prepare tables and ask user to send them to their collection manager

## Phase 1: Sites

### Step 1: Ingest user data

Ask the user for their specimen data file (xlsx format). Run:

```bash
python3 scripts/parse_user_data.py <user_file.xlsx> /tmp/emu_user_sites.json
```

Present a summary:
- Number of specimen records found
- Site columns detected (should be green-filled columns from LocContinent to SitSiteNumber)
- Sample of the data

**Expected format**: Row 1 = user-friendly names, Row 2 = Emu field names, Row 3 = example, data starts Row 4. Site columns have green fill (`FFCCFFCC`).

### Step 2: Ingest Emu sites export

Ask the user for their Emu sites export (CSV). If they don't have one, teach them how to download it:

> In Emu, go to the Sites module. Run a search for the relevant records (e.g., all sites for a country). Then use File > Export to save as CSV. Make sure to include these columns: irn, LocContinent, LocCountry, LocProvinceStateTerritory, LocDistrictCountyShire, LocTownship, LocPreciseLocation, LocElevationASLFromMt, LocElevationASLToMt, LocElevationFromFt, LocElevationToFt, LatPreferredCentroidLatDec, LatPreferredCentroidLongDec, SitSiteNumber (if available).

Parse the export:

```bash
python3 scripts/parse_emu_export.py <emu_export.csv> /tmp/emu_index.json
```

This creates a searchable index. Report: number of records loaded, coordinate coverage.

**Note**: The Emu index file can be large (~100MB for 200K+ records). It loads once and is reused for all matching steps.

### Step 3: Deduplicate user sites

```bash
python3 scripts/deduplicate_sites.py /tmp/emu_user_sites.json /tmp/emu_dedup.json
```

Report: "Your N specimens contain M unique sites." Show the unique sites table.

### Step 4: Match sites to Emu

```bash
python3 scripts/match_sites.py /tmp/emu_dedup.json /tmp/emu_index.json /tmp/emu_match.json
```

This produces candidates for each unique site. **Your role as Claude is critical here** — review the match results and exercise judgment:

#### For exact matches (score >= 90, close coordinates):
Report silently: "N sites matched existing Emu records."

#### For near matches (score 60-90):
Present each to the user with a comparison table showing:
- User's values vs Emu record values for each field
- Coordinate distance (if applicable)
- Score and similarity details
- Your assessment (e.g., "This appears to be a typo: 'Chochise' vs 'Cochise'")

Ask the user to confirm or reject each near match.

#### For no matches:
Note these need new records + parent finding.

#### Field comparison notes:
- "United States" vs "United States of America" is a known mismatch — treat as equivalent
- Watch for typos in county/locality names (fuzzy matching catches these)
- Coordinate matches within ~500m with matching elevation are likely the same site
- If precise location differs but coordinates are very close (<100m), flag for user review

### Step 5: Find parents for unmatched sites

```bash
python3 scripts/find_parents.py /tmp/emu_match.json /tmp/emu_index.json /tmp/emu_parents.json
```

Review parent results:

- **Perfect parents** (score >= 90, proper hierarchy level): proceed silently
- **Partial parents**: present to user with comparison details, ask for confirmation
- **No parent found**: flag for manual resolution (this is rare — at minimum continent/country should exist)

**Parent rules**:
- Parents cannot have a SitSiteNumber
- Parents should be at a higher hierarchy level than the child site
- A proper parent should NOT have data below its hierarchy level (e.g., a county parent should not have a LocPreciseLocation)

### Step 6: Summary report

Present a clear summary:
- N sites matched directly (have IRNs)
- M new sites need creation
- P new parent records need creation (if any)
- Q multi-level parent chains (if any)

If all sites matched, skip to Step 8.

### Step 7: Create and upload new sites

```bash
python3 scripts/generate_bulk_upload.py /tmp/emu_parents.json /tmp/emu_upload/
```

This creates `sites_upload_batch_N.xlsx` files.

**For users WITH bulk upload privileges**:
> Upload instructions (placeholder — to be detailed later):
> 1. Open Emu and go to the Sites module
> 2. Use File > Import to load the batch file
> 3. After upload, export the newly created records to get their IRNs
> 4. Provide the exported file back to Claude

**For users WITHOUT privileges**:
> Please send `sites_upload_batch_1.xlsx` to your collection manager and ask them to:
> 1. Upload these records to Emu
> 2. Return the same table with a new column "ColSiteRef.irn" containing the assigned IRNs

After receiving IRNs back from the user, update the internal mapping. If there are multiple batches (due to parent dependencies), repeat for each batch.

### Step 8: Final output

Once all sites have IRNs, create the IRN mapping and finalize:

```bash
python3 scripts/finalize_user_table.py <original.xlsx> <irn_mapping.json> <output.xlsx>
```

The `irn_mapping.json` should be created by Claude with this format:
```json
{"row_irn_map": {"4": "123456", "5": "123457", ...}}
```

The output xlsx will have a `ColSiteRef.irn` column inserted after `SitSiteNumber` with the same green fill color.

Deliver this file to the user.

## Communication guidelines

- Be concise; batch similar items together
- Use tables for presenting match comparisons
- Flag typos and discrepancies clearly with your assessment
- For large numbers of matches, group by status and only detail the ambiguous ones
- Always tell the user how many sites remain to process after each decision

## Site hierarchy reference

From most general to most precise:
1. `LocContinent`
2. `LocCountry`
3. `LocProvinceStateTerritory`
4. `LocDistrictCountyShire`
5. `LocTownship`
6. `LocPreciseLocation`

## Field name conventions

User xlsx fields use `_tab` suffixes (e.g., `LocCountry_tab`). Emu CSV exports use bare names (`LocCountry`). Coordinate fields differ: user has `LatLatitude_nesttab`, Emu has `LatPreferredCentroidLatDec`. The scripts handle normalization automatically. See `references/emu_field_mapping.md` for the complete mapping table.

## Future phases (not yet implemented)

- **Phase 2: Events** — match collecting events to site IRNs
- **Phase 3: Catalog** — upload specimen catalog records
- **Phase 4: Other entities** — taxonomy, collector parties
- **Future features** — guess intermediate parents, geocoding from coordinates
