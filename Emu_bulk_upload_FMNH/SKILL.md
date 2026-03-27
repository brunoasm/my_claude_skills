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

Ask the user for their specimen data file (xlsx format). The user can upload/attach the file directly or provide a path. If uploaded, save it to `/tmp/` first (e.g., `/tmp/emu_user_specimens.xlsx`). Run:

```bash
python3 scripts/parse_user_data.py <user_file.xlsx> /tmp/emu_user_sites.json
```

Present a summary:
- Number of specimen records found
- Site columns detected (should be green-filled columns from LocContinent to SitSiteNumber)
- Sample of the data

**Expected format**: Row 1 = user-friendly names, Row 2 = Emu field names, Row 3 = example, data starts Row 4. Site columns have green fill (`FFCCFFCC`).

### Step 2: Ingest Emu sites export

Ask the user for their Emu sites export (CSV). The user can upload/attach the file directly or provide a path. If uploaded, save it to `/tmp/` (e.g., `/tmp/emu_sites_export.csv`).

If they don't have one, first analyze the user's data from Step 1 and suggest the most efficient search criteria for Emu. For example:
- All specimens from one country → search by country
- Specimens from 2–3 states in one country → search by state (PD2), possibly multiple exports
- Specimens spanning many countries → suggest country-level search per country, or broader continent search

Then ask:

> Do you know how to export sites from Emu, or would you like step-by-step guidance with screenshots?
> 1. I know how — just give me the quick summary
> 2. I need step-by-step guidance

#### Quick summary (option 1)

Tell the user your specific search suggestion based on their data, then:

> In Emu, log in and go to the **Sites** module. In the Search window, click the **Class: Political** tab at the bottom. Type your search criteria (e.g., [Claude fills in based on user data]) in the appropriate field, then click **Search**. From the results, go to **Tools > Reports**, select the **"Localities Insects"** report, and click **Report...**. The exported CSV will appear in your shared folder.

#### Step-by-step guidance (option 2)

Walk the user through each step one at a time. For each step, use the Read tool to show the screenshot, explain what it shows and what action to take, then wait for the user to confirm before proceeding to the next step.

**Step 2a — Log in to Emu**
Screenshot: `references/screenshots_sites_export/01_emu_login.png`
> Open KE EMu (FMNH). Enter your credentials — Host: `10.10.10.25`, Service: `emufmnh`. Click OK.

**Step 2b — Select the Sites module**
Screenshot: `references/screenshots_sites_export/02_select_sites_module.png`
> From the module list, click **Sites**.

**Step 2c — You'll see the Site tab (default view)**
Screenshot: `references/screenshots_sites_export/03_sites_search_site_tab.png`
> This is what you see when Sites opens — the Site tab with Record Classification and other fields. You need to switch to a different tab. Click the **Class: Political** tab at the bottom of the window.

**Step 2d — Class: Political tab**
Screenshot: `references/screenshots_sites_export/04_class_political_tab.png`
> Now you see the Political Details fields: Country, PD2 (state/province), PD3 (county), etc. This is where you'll enter your search.

**Step 2e — Enter search criteria**
Screenshot: `references/screenshots_sites_export/05_enter_search_criteria.png`
> [Claude tells the user exactly what to type and in which field, based on Step 1 data analysis. E.g., "Type 'United States' in the **Country** field" or "Type 'Arizona' in the **PD2** field"]. Then click **Search** at the bottom left.

**Step 2f — Review search results**
Screenshot: `references/screenshots_sites_export/06_search_results.png`
> Your search results appear in Display mode. The status bar at the bottom shows the total number of matching sites (e.g., 218,294). Verify this looks reasonable for your search.

**Step 2g — Open the Tools menu**
Screenshot: `references/screenshots_sites_export/07_tools_menu.png`
> Click the **Tools** menu in the menu bar.

**Step 2h — Select Reports**
Screenshot: `references/screenshots_sites_export/08_select_reports.png`
> Click **Reports...** from the Tools menu.

**Step 2i — Choose the Localities Insects report**
Screenshot: `references/screenshots_sites_export/09_choose_localities_insects_report.png`
> In the Reports dialog, select **Localities Insects**, then click the **Report...** button at the bottom.

**Step 2j — Find the exported file**
Screenshot: `references/screenshots_sites_export/10_exported_file_in_shared_folder.png`
> The export may take several minutes for large datasets. When done, the CSV file appears in your shared folder. Provide its path back to me.

If the search requires multiple exports (e.g., one per state), repeat steps 2e–2j for each.

#### Parse the export

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

This creates `sites_upload_batch_N.xlsx` files. Columns that are entirely blank across all rows are automatically removed from the output to keep the table clean.

Present the output file path to the user clearly (see "File outputs" in interaction guidelines).

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

Present the output file path to the user clearly (see "File outputs" in interaction guidelines).

## Communication guidelines

- Be concise; batch similar items together
- Use tables for presenting match comparisons
- Flag typos and discrepancies clearly with your assessment
- For large numbers of matches, group by status and only detail the ambiguous ones
- Always tell the user how many sites remain to process after each decision

## User interaction guidelines

### Structured choices
When asking the user to choose between options, present numbered choices on separate lines so they are easy to tap or select:

```
1. Yes
2. No
```

For near-match review, present each match with clear options:
```
**Site 3**: "Cochise County" vs "Chochise County" (score 87, likely typo)
1. Accept match (use Emu record IRN 45678)
2. Reject match (create new record)
```

For the privilege gating question at session start, present as:
```
Do you have Emu bulk upload privileges?
1. Yes
2. No (not sure = no)
```

### File inputs
When asking the user for a file (specimen xlsx, Emu CSV export):
- Tell them they can **upload/attach the file directly** in the chat, or provide a file path
- If the user uploads a file in chat, save it to `/tmp/` with a descriptive name (e.g., `/tmp/emu_user_specimens.xlsx`) before running scripts
- Confirm the file was received: "Got your file — saved to `/tmp/emu_user_specimens.xlsx`"

### File outputs
When a file is produced (bulk upload table, final output table):
- Always state the **full file path**
- Tell the user the file is ready and where to find it
- Example: "Bulk upload table ready: `/tmp/emu_upload/sites_upload_batch_1.xlsx`"

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
