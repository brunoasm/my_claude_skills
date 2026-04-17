---
name: emu-bulk-upload
description: "Help museum insect curators bulk upload specimen data to the Emu database. Maps any input format to Emu's template, matches localities to existing records, finds parent sites, creates bulk upload tables, and walks users through the upload process."
---

# Emu Bulk Upload Skill

Help users prepare and upload entomological specimen data to the Emu collection database at the Field Museum of Natural History (FMNH). The process starts by mapping whatever data the user provides into Emu's standard format, then works through each Emu module (Sites, Events, Catalog) to match existing records, create new ones, and produce properly formatted tables for bulk upload.

## When to use

- User wants to upload specimen data to Emu
- User needs to match localities to existing Emu site records
- User has specimen data in any format that needs database preparation
- Keywords: "bulk upload", "Emu", "upload specimens", "match sites", "prepare data"

## Key reference files

- `references/Emu_upload_default.xlsx` — The Emu upload template (49 columns, 3 modules)
- `references/emu_field_reference.md` — Complete field reference with descriptions, export name mappings, and normalization rules
- `references/phase1_sites.md` — Sites phase detailed reference (scripts, matching, export guide)

## Session start

### File discovery

At the start of a session, search the working directory for files the user may have already placed there:
- Look for data files: `.xlsx`, `.csv`, `.tsv`, `.txt`, or other tabular formats
- Look for Emu exports: `.csv` files that may contain site/event data

If any are found, list them and confirm with the user:

> I found these files in the working directory:
> - `specimen_data.csv` (csv, 145 KB)
> - `US_sites_export.csv` (csv, 12 MB)
>
> Which of these should I work with? Is `specimen_data.csv` your specimen data and `US_sites_export.csv` an Emu sites export?

### Privilege gating

Before any work, ask the user:

> Do you have Emu bulk upload privileges?
> 1. Yes
> 2. No (not sure = no)

Record the answer. It determines how upload steps are handled later:
- **With privileges**: walk through Emu upload steps directly
- **Without privileges**: prepare tables and ask user to send them to their collection manager

---

## Step 1: Data intake and mapping

This step takes the user's data in **any format** and maps it into the Emu template format (`references/Emu_upload_default.xlsx`).

### Accept any input

The user's data may be:
- An xlsx already in Emu template format (3-row header with Emu field names in Row 2)
- An xlsx or csv with their own column names (e.g., "lat", "long", "state", "species")
- A tsv, txt, or other delimited file
- Data with completely different column naming conventions

### Analyze the input

1. Read the file and present the columns and a sample of the data to the user
2. Read `references/emu_field_reference.md` to understand all Emu fields
3. Propose a column mapping: for each user column, suggest which Emu field it corresponds to

Present the mapping as a table for user review:

> Here's how I'd map your columns to Emu fields:
>
> | Your column | Emu field | User-friendly name |
> |---|---|---|
> | lat | LatLatitude_nesttab | Latitude |
> | long | LatLongitude_nesttab | Longitude |
> | state | LocProvinceStateTerritory_tab | Province/State |
> | county | LocDistrictCountyShire_tab | County |
> | locality | LocPreciseLocation | Precise Location |
> | species | IdeTaxonRef_tab.irn | Taxon |
> | collector | ColParticipantRef_tab(2).irn | Collectors |
> | *unmapped* | — | (columns with no Emu equivalent) |
>
> Does this look right? Any corrections?

Wait for user confirmation before proceeding. Unmapped columns are preserved but not used in Emu uploads.

### Check for Emu template format

If the file already has the 3-row header structure (Row 1 = friendly names, Row 2 = Emu field names, Row 3 = example) with correct Emu field names, skip the mapping and confirm:

> Your file is already in Emu template format. I found N data rows with columns for [Sites, Events, Catalog] fields.

### Build transformation script

Once the mapping is confirmed, **write a Python script on the fly** to transform the user's data into the Emu template format:

1. Read the user's input file (whatever format it is)
2. Map columns according to the confirmed mapping
3. Output an xlsx in Emu template format:
   - Row 1: user-friendly names (from template)
   - Row 2: Emu field names (from template)
   - Row 3: first data row as example
   - Row 4+: data
   - Column colors: green (`FFCCFFCC`) for Sites, gray (`FFC0C0C0`) for Events, tan (`FFFFCC99`) for Catalog
4. Only include columns that have data (skip entirely empty Emu fields)

Save the script to `/tmp/emu_transform.py` and run it. Save the output to `/tmp/emu_user_data.xlsx`.

Reference `scripts/parse_user_data.py` for patterns on reading xlsx files with openpyxl and applying cell colors.

### Present summary

After transformation, report:
- Number of data rows
- Which Emu modules have data (Sites, Events, Catalog)
- Sample of the transformed data
- Any data quality notes (missing values, format issues)

---

## Phase 1: Sites

Match user localities to existing Emu site records, create new records where needed, and obtain site IRNs.

**Detailed reference**: `references/phase1_sites.md`

### Step 1.1: Extract site data

From the transformed user xlsx (`/tmp/emu_user_data.xlsx`), extract the site columns (green-filled: hierarchy, elevation, coordinates, site number).

```bash
python3 scripts/parse_user_data.py /tmp/emu_user_data.xlsx /tmp/emu_user_sites.json
```

Report: number of specimens, site columns detected, sample data.

### Step 1.2: Get Emu sites export

Ask for the Emu sites export (CSV). If identified during file discovery, use it directly. If the user doesn't have one:

1. Analyze the user's data and suggest search criteria (see `references/phase1_sites.md` § "Choosing search criteria")
2. Ask: "Do you know how to export sites from Emu, or would you like step-by-step guidance with screenshots?"
   - **Option 1 — Quick summary**: See `references/phase1_sites.md` § "Quick summary"
   - **Option 2 — Step-by-step guide**: Walk through each screenshot one at a time (see `references/phase1_sites.md` § "Step-by-step screenshot guide"). Show one step, wait for confirmation, then proceed.

Parse the export:
```bash
python3 scripts/parse_emu_export.py <emu_export.csv> /tmp/emu_index.json
```

Report: records loaded, coordinate coverage.

### Step 1.3: Deduplicate and match

```bash
python3 scripts/deduplicate_sites.py /tmp/emu_user_sites.json /tmp/emu_dedup.json
python3 scripts/match_sites.py /tmp/emu_dedup.json /tmp/emu_index.json /tmp/emu_match.json
```

Report: "Your N specimens contain M unique sites."

Review matches using your judgment (see `references/phase1_sites.md` § "Match review guidelines"):
- **Exact matches** (score >= 90): report silently
- **Near matches** (60–89): present comparison table, ask user to confirm/reject each
- **No matches**: note for parent finding

### Step 1.4: Find parents for unmatched sites

```bash
python3 scripts/find_parents.py /tmp/emu_match.json /tmp/emu_index.json /tmp/emu_parents.json
```

Review parent results (see `references/phase1_sites.md` § "Parent rules"):
- **Perfect parents** (score >= 90): proceed silently
- **Partial parents**: present to user for confirmation
- **No parent found**: flag for manual resolution

### Step 1.5: Summary and upload

Present summary: N matched, M new sites, P new parents.

If new sites need creation:
```bash
python3 scripts/generate_bulk_upload.py /tmp/emu_parents.json /tmp/emu_upload/
```

Handle upload based on user privileges (see `references/phase1_sites.md` § "Upload instructions").

### Step 1.6: Finalize with IRNs

Once all sites have IRNs:
```bash
python3 scripts/finalize_user_table.py /tmp/emu_user_data.xlsx <irn_mapping.json> /tmp/emu_user_data_with_irns.xlsx
```

Create `irn_mapping.json` with format: `{"row_irn_map": {"4": "123456", ...}}`

Report the output file path.

---

## Phase 2: Events (planned)

Match collecting events (date, collector, method, habitat) to site IRNs from Phase 1.

**Reference**: `references/phase2_events.md` (to be created)

Event fields are gray-colored columns in the template. See `references/emu_field_reference.md` § "Collection Events module".

---

## Phase 3: Catalog (planned)

Upload specimen catalog records linking to event records from Phase 2.

**Reference**: `references/phase3_catalog.md` (to be created)

Catalog fields are tan/orange-colored columns in the template. See `references/emu_field_reference.md` § "Catalog module".

---

## Phase 4: Other entities (planned)

Taxonomy, collector parties, and other dependent records.

---

## Communication guidelines

- Be concise; batch similar items together
- Use tables for presenting match comparisons and column mappings
- Flag typos and discrepancies clearly with your assessment
- For large numbers of matches, group by status and only detail the ambiguous ones
- Always tell the user how many items remain to process after each decision

## User interaction guidelines

### Structured choices
Present numbered choices on separate lines:
```
1. Yes
2. No
```

For near-match review:
```
**Site 3**: "Cochise County" vs "Chochise County" (score 87, likely typo)
1. Accept match (use Emu record IRN 45678)
2. Reject match (create new record)
```

### File inputs
- Tell users they can **upload/attach files directly** or provide a file path
- If uploaded, save to `/tmp/` with a descriptive name
- Confirm receipt: "Got your file — saved to `/tmp/emu_user_specimens.xlsx`"

### File outputs
- Always state the **full file path**
- Example: "Bulk upload table ready: `/tmp/emu_upload/sites_upload_batch_1.csv`"
