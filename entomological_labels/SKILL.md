---
name: entomological-labels
description: "Generate entomological specimen labels as .docx files from any tabular data. Interactively maps data to Darwin Core, assists with text abbreviation, and produces print-ready label sheets. Use when users need specimen labels for entomological collections."
---

# Entomological Specimen Label Generator

## Overview

Generate print-ready entomological specimen labels (.docx) from any tabular data source. This skill replaces the traditional mail merge workflow (Python script + Word template) with an interactive process that:

1. Reads any tabular data (xlsx, csv, tsv, multi-table databases)
2. Maps columns to Darwin Core terms
3. Walks the user through label design and text abbreviation
4. Generates .docx label sheets using the docx-js library

The default output matches the existing template: Helvetica 4pt, light gray borders (#E7E6E6), 3 specimens per row, 27 rows per page, US Letter, with thin separator columns between specimen groups.

## When to Use This Skill

Use when users request:
- "Generate specimen labels"
- "Make labels for my insect collection"
- "Create label sheets from my spreadsheet"
- "Print labels for specimens"
- "Prepare labels from EMu/Specify/database export"

The skill triggers when users mention specimen labels, entomological labels, collection labels, or want to produce label sheets from tabular data.

## Available Resources

### References
- **`references/darwin_core_mapping.md`** — DwC term mapping table with aliases from EMu, Specify, Symbiota, and custom spreadsheets. Load this when mapping user columns.
- **`references/label_template_specs.md`** — Exact DXA measurements, typography, borders, cell dimensions, and docx-js code patterns for the label table. **MANDATORY: Read this entire file before generating any docx-js code.**
- **`references/abbreviation_conventions.md`** — Standard entomological abbreviations for geographic features, collectors, methods, dates, and taxonomy. Load this during the abbreviation phase.

### Template Files (for reference only)
- `template/prepare_for_labels.py` — Existing Python script for data prep (reference for formatting logic)
- `template/first_template.docx` — Original Word template (reference for visual layout)
- `template/labels_with_genomics_filtered.xlsx` — Test data (420 specimens)
- `template/Oxycorynus EMu workbook.xlsx` — Test data (EMu export format)

### External Skill Dependency
- **docx skill** — Read the docx-js reference (`docx-js.md`) for the complete docx-js API before generating document code. Path: `../anthropic-skills/document-skills/docx/docx-js.md`

---

## Workflow

The skill runs in 4 interactive phases. Each phase requires user confirmation before proceeding.

### Phase 1: Data Ingestion

#### Step 1.1 — Read the User's Data

Accept any tabular format. Use Python with pandas to read the file:

```python
import pandas as pd
import json
import sys

file_path = sys.argv[1]

if file_path.endswith('.csv'):
    df = pd.read_csv(file_path)
elif file_path.endswith('.tsv'):
    df = pd.read_csv(file_path, sep='\t')
elif file_path.endswith(('.xlsx', '.xls')):
    # Check for multiple sheets
    xls = pd.ExcelFile(file_path)
    if len(xls.sheet_names) > 1:
        print(f"Multiple sheets found: {xls.sheet_names}")
        # Read all sheets, let user decide
        for name in xls.sheet_names:
            sheet = pd.read_excel(file_path, sheet_name=name)
            print(f"\n--- Sheet '{name}' ---")
            print(f"  Columns: {list(sheet.columns)}")
            print(f"  Rows: {len(sheet)}")
    df = pd.read_excel(file_path)  # default: first sheet
else:
    df = pd.read_csv(file_path)  # try csv as fallback

# Normalize column names
df.columns = [c.strip().lower().replace(' ', '_').replace('-', '_') for c in df.columns]

print(f"Shape: {df.shape}")
print(f"Columns: {list(df.columns)}")
print(df.head(3).to_string())
```

#### Step 1.2 — Display Data Summary

Show the user:
- Number of rows (specimens)
- Column names
- First 3-5 sample rows
- Data types (to catch numeric vs string issues)

#### Step 1.3 — Map Columns to Darwin Core

Load `references/darwin_core_mapping.md` and auto-map columns:

1. Normalize user column names (lowercase, underscores)
2. Match against alias lists in the mapping table
3. Present the mapping as a table to the user:

```
Your Column          → DwC Term              Status
─────────────────────────────────────────────────────
country              → country               exact match
state                → stateProvince          exact match
lat                  → decimalLatitude        prefix match
lon                  → decimalLongitude       prefix match
det                  → identifiedBy           ⚠ ambiguous (could also be dateIdentified)
id                   → ???                    ⚠ unmapped — please clarify
```

4. Ask the user to confirm the mapping and resolve ambiguous/unmapped columns
5. Ask which columns are not needed for labels (will be ignored)

#### Step 1.4 — Handle Multi-Table Input

If the user has data in multiple files or sheets:

1. Ask which column links the tables (e.g., `event_id`, `sample_id`)
2. Perform LEFT JOINs in the order: specimens → events → taxonomy → plants
3. Handle column name conflicts with suffixes
4. Show the merged result to the user for confirmation

---

### Phase 2: Label Design

#### Step 2.1 — Choose Label Types

Ask how many label types per specimen (use `AskUserQuestion`):

- **3 labels (default):** Locality (A) + Collection Data (B) + Determination (C)
- **2 labels:** Locality+Collection combined (A) + Determination (C)
- **1 label:** All data on a single label
- **Custom:** User specifies their own layout

#### Step 2.2 — Configure Label Content

For each label type, show the default field layout and let the user customize. Default layouts:

**Label A — Locality:**
```
Line 1: COUNTRY, STATE              (uppercased)
Line 2: locality                    (may need abbreviation)
Line 3: S0.12345, W35.67890         (formatted coordinates)
Line 4: 1200m                       (elevation with "m" suffix)
Line 5: 20.v.2012                   (day.romanMonth.year)
Line 6: B.A.S. de Medeiros          (collector)
```

**Label B — Collection Data:**
```
Line 1: beating, on flowers         (method + interaction)
Line 2: On Genus species Auth.      ("On" roman, genus+sp italic)
Line 3: coll.ID FMNH-INS-12345     (catalog number, 3.5pt)
Line 4: genomic.ID BdM-1234        (if present, 3.5pt)
```

**Label C — Determination:**
```
Line 1: Family Name                 (roman)
Line 2: Genus species               (italic genus + epithet)
Line 3:   (Author, Year)            (roman, if present)
Line 4: F. Last det. 2024           (determiner + year)
```

Ask the user:
- "Does this layout work for your specimens?"
- "Any fields to add, remove, or reorder?"
- "Do you have genomic IDs to include?"

#### Step 2.3 — Page Layout Options

Present defaults (from `references/label_template_specs.md`) with option to customize:

| Parameter | Default | Customizable? |
|-----------|---------|---------------|
| Font | Helvetica 4pt | yes |
| ID font size | 3.5pt | yes |
| Line spacing | 90 twips | yes |
| Specimens per row | 3 | yes |
| Rows per page | 27 | yes |
| Page size | US Letter | yes |
| Margins | tight (see specs) | yes |
| Borders | #E7E6E6 light gray | yes |
| Separator width | 0.1" (144 DXA) | yes |

Most users will accept defaults. Only present customization if asked.

#### Step 2.4 — Character Limits

Calculate and display:
- Label cell width in inches
- Character limit per line at chosen font size
- Flag any known long fields from the data (e.g., locality names > 30 chars)

---

### Phase 3: Data Cleaning & Abbreviation

This is the **key interactive phase**. Process each field to ensure it fits within character limits.

#### Step 3.1 — Auto-Format (no user input needed)

Apply these formatting rules automatically:

**Scientific names:**
- Genus + specificEpithet → italic (will be applied in docx-js as `italics: true`)
- "sp.", "sp.1", "sp. nov.", etc. → normalize to "sp." (roman)
- "cf.", "aff." → roman, placed between italic genus and italic species
- Authority → roman
- Family → roman

**Dates:**
- Convert to day.romanMonth.year format (e.g., 20.v.2012)
- Handle date ranges: 5-12.viii.2024
- Handle ISO dates, "Jan 5 2024", etc.
- Use the ROMAN_MONTHS lookup from `references/abbreviation_conventions.md`

**Coordinates:**
- Negative latitude → "S" + |value|, positive → "N" + |value|
- Negative longitude → "W" + |value|, positive → "E" + |value|
- Round to 5 decimal places
- Format: `S0.12345, W35.67890`

**Country/State:**
- UPPERCASE both fields

**Elevation:**
- Append "m" suffix (no space): `1200m`
- Ranges: `800-1200m`
- Drop decimals

**Missing data:**
- Omit the entire line for empty/NaN fields
- Never print "NaN", "None", "nan", or blank lines

#### Step 3.2 — Abbreviation Assistance (interactive)

Load `references/abbreviation_conventions.md` for suggestions.

For each field, check unique values against the character limit. For values that exceed it:

1. **Batch identical values** — group by unique value and count occurrences:
   ```
   LOCALITY field — values exceeding 30-char limit:

   45 specimens: "Parque Nacional da Gorongosa" (28 chars) → OK (fits)
   23 specimens: "Reserva Biológica do Jarú, margem do Rio Jarú" (46 chars)
      Suggestion: "REBIO Jarú, R. Jarú" (19 chars)
   12 specimens: "Estação Ecológica de Maracá-Jipioca" (35 chars)
      Suggestion: "ESEC Maracá-Jipioca" (19 chars)

   Accept all suggestions? Or customize individually?
   ```

2. **Collector names:**
   ```
   COLLECTOR field — values exceeding limit:

   120 specimens: "B.A.S. de Medeiros, J.R. Smith, L.K. Jones" (43 chars)
      Suggestion: "B. de Medeiros et al." (21 chars)

   Accept?
   ```

3. **Host plants:**
   - Drop authority first if too long
   - Then abbreviate genus to initial
   - Ask user before any abbreviation

4. **Locality names:**
   - Suggest standard geographic abbreviations (NP, NF, Res., Mt., etc.)
   - Suggest country-specific abbreviations (PN, REBIO, etc.)
   - Ask user for custom abbreviations if no standard exists

Present all suggestions grouped by field, then by frequency. Let the user approve, modify, or reject each one.

#### Step 3.3 — Final Data Check

After abbreviation, show a summary:
- Total specimens
- Count of unique values per label field
- Any remaining fields exceeding character limits
- Sample formatted labels (text preview of 2-3 specimens)

---

### Phase 4: Document Generation

#### Step 4.1 — Read docx-js Reference

**MANDATORY:** Read the docx skill's reference file for the complete docx-js API:

```
Read file: ../anthropic-skills/document-skills/docx/docx-js.md
```

Also read `references/label_template_specs.md` for exact measurements and code patterns.

#### Step 4.2 — Generate Python Preprocessing Script

Create a Python script that:
1. Reads the user's original data file
2. Applies column mapping, formatting, and abbreviations from Phase 1-3
3. Exports cleaned data as JSON for the docx-js script

```python
#!/usr/bin/env python3
"""Preprocess specimen data for label generation."""
import pandas as pd
import numpy as np
import json
import sys

ROMAN_MONTHS = {1:'i',2:'ii',3:'iii',4:'iv',5:'v',6:'vi',
                7:'vii',8:'viii',9:'ix',10:'x',11:'xi',12:'xii'}

def format_coordinate(val, neg_prefix, pos_prefix):
    if pd.isna(val): return ''
    v = round(float(val), 5)
    return f"{neg_prefix}{abs(v)}" if v < 0 else f"{pos_prefix}{abs(v)}"

def format_date(row):
    # Implement date formatting based on available columns
    # day.romanMonth.year format
    pass  # Customize per user's date columns

# Read data
df = pd.read_excel(sys.argv[1])  # or csv
# ... apply column mapping from Phase 1
# ... apply formatting from Phase 3.1
# ... apply abbreviations from Phase 3.2

# Export as JSON
records = df.to_dict('records')
with open('label_data.json', 'w') as f:
    json.dump(records, f, default=str)
print(f"Exported {len(records)} specimens to label_data.json")
```

**Important:** This is a template pattern. Generate the actual script with the user's specific column mappings, abbreviation rules, and data transformations baked in — not a generic script.

#### Step 4.3 — Generate docx-js Label Script

Create a JavaScript file that builds the complete .docx document. Use the patterns from `references/label_template_specs.md`.

**Complete script structure:**

```javascript
const fs = require('fs');
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        BorderStyle, WidthType, AlignmentType, ShadingType } = require('docx');

// ── Load data ──
const specimens = JSON.parse(fs.readFileSync('label_data.json', 'utf-8'));

// ── Constants from template specs ──
const LABEL_W = 1194;    // label cell width in DXA
const SEP_W = 144;       // separator column width in DXA
const ROW_H = 490;       // row height in DXA (exact)
const ROWS_PER_PAGE = 27;
const SPECIMENS_PER_ROW = 3;
const SPECIMENS_PER_PAGE = ROWS_PER_PAGE * SPECIMENS_PER_ROW; // 81
const FONT = "Helvetica";
const FONT_SZ = 8;       // 4pt in half-points
const ID_SZ = 7;         // 3.5pt in half-points
const LINE_SP = 90;      // line spacing in twips

// ── Borders ──
const labelBorder = { style: BorderStyle.SINGLE, size: 4, color: "E7E6E6" };
const cellBorders = { top: labelBorder, bottom: labelBorder, left: labelBorder, right: labelBorder };
const noBorder = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const sepBorders = { top: noBorder, bottom: noBorder, left: noBorder, right: noBorder };

// ── Helpers ──
function p(runs, fontSize = FONT_SZ) {
  return new Paragraph({
    spacing: { line: LINE_SP, before: 0, after: 0 },
    children: runs.filter(Boolean).map(r =>
      r instanceof TextRun ? r : new TextRun({ font: FONT, size: fontSize, ...r })
    )
  });
}

function labelCell(paragraphs) {
  return new TableCell({
    width: { size: LABEL_W, type: WidthType.DXA },
    borders: cellBorders,
    children: paragraphs.filter(Boolean)
  });
}

function separatorCell() {
  return new TableCell({
    width: { size: SEP_W, type: WidthType.DXA },
    borders: sepBorders,
    children: [p([])]
  });
}

// Empty label cell (for padding incomplete rows)
function emptyCell() {
  return new TableCell({
    width: { size: LABEL_W, type: WidthType.DXA },
    borders: cellBorders,
    children: [p([])]
  });
}

// ── Label Builders ──

function buildLocalityLabel(s) {
  const lines = [];
  // Line 1: COUNTRY, STATE
  const countryState = [s.country, s.stateProvince].filter(Boolean).join(', ');
  if (countryState) lines.push(p([{ text: countryState }]));
  // Line 2: locality
  if (s.locality) lines.push(p([{ text: s.locality }]));
  // Line 3: coordinates
  if (s.lat && s.lon) lines.push(p([{ text: `${s.lat}, ${s.lon}` }]));
  // Line 4: elevation
  if (s.elevation) lines.push(p([{ text: s.elevation }]));
  // Line 5: date
  if (s.date) lines.push(p([{ text: s.date }]));
  // Line 6: collector
  if (s.collector) lines.push(p([{ text: s.collector }]));
  return labelCell(lines.length ? lines : [p([])]);
}

function buildCollectionLabel(s) {
  const lines = [];
  // Line 1: method
  if (s.method) lines.push(p([{ text: s.method }]));
  // Line 2: host plant (italic genus + species)
  if (s.hostPlant) {
    // "On" roman + genus species italic + authority roman
    const runs = [{ text: "On " }];
    if (s.hostGenus) runs.push({ text: s.hostGenus, italics: true });
    if (s.hostSpecies) runs.push({ text: " " + s.hostSpecies, italics: true });
    if (s.hostAuthority) runs.push({ text: " " + s.hostAuthority });
    lines.push(p(runs));
  }
  // Line 3: coll.ID (smaller font)
  if (s.catalogNumber) lines.push(p([{ text: `coll.ID ${s.catalogNumber}` }], ID_SZ));
  // Line 4: genomic.ID (smaller font, only if present)
  if (s.genomicID) lines.push(p([{ text: `genomic.ID ${s.genomicID}` }], ID_SZ));
  return labelCell(lines.length ? lines : [p([])]);
}

function buildDeterminationLabel(s) {
  const lines = [];
  // Line 1: Family
  if (s.family) lines.push(p([{ text: s.family }]));
  // Line 2: scientific name with proper formatting
  if (s.genus) {
    const runs = [];
    runs.push({ text: s.genus, italics: true });
    if (s.qualifier) runs.push({ text: ` ${s.qualifier}` }); // cf., aff. = roman
    if (s.species && s.species !== 'sp.') {
      runs.push({ text: ` ${s.species}`, italics: true });
    } else if (s.species === 'sp.') {
      runs.push({ text: ' sp.' }); // roman
    }
    if (s.sex) runs.push({ text: ` ${s.sex}` });
    lines.push(p(runs));
  }
  // Line 3: authority
  if (s.authority) lines.push(p([{ text: `  ${s.authority}` }]));
  // Line 4: determiner
  if (s.determiner) {
    const detText = s.detYear ? `${s.determiner} det. ${s.detYear}` : `${s.determiner} det.`;
    lines.push(p([{ text: detText }]));
  }
  return labelCell(lines.length ? lines : [p([])]);
}

// ── Build Rows ──
function buildRow(specimenGroup) {
  const cells = [];
  for (let i = 0; i < SPECIMENS_PER_ROW; i++) {
    if (i > 0) cells.push(separatorCell()); // separator between specimen groups
    if (i < specimenGroup.length) {
      const s = specimenGroup[i];
      cells.push(buildLocalityLabel(s));
      cells.push(buildCollectionLabel(s));
      cells.push(buildDeterminationLabel(s));
    } else {
      // Padding for incomplete rows
      cells.push(emptyCell());
      cells.push(emptyCell());
      cells.push(emptyCell());
    }
  }
  return new TableRow({
    height: { value: ROW_H, rule: "exact" },
    children: cells
  });
}

// ── Build Pages ──
function buildPage(pageSpecimens) {
  const rows = [];
  for (let r = 0; r < ROWS_PER_PAGE; r++) {
    const start = r * SPECIMENS_PER_ROW;
    const group = pageSpecimens.slice(start, start + SPECIMENS_PER_ROW);
    rows.push(buildRow(group));
  }
  return new Table({
    columnWidths: [LABEL_W, LABEL_W, LABEL_W, SEP_W,
                   LABEL_W, LABEL_W, LABEL_W, SEP_W,
                   LABEL_W, LABEL_W, LABEL_W],
    margins: { top: 29, bottom: 29, left: 29, right: 29 },
    rows: rows
  });
}

// ── Assemble Document ──
const pageCount = Math.ceil(specimens.length / SPECIMENS_PER_PAGE);
const sections = [];

for (let pg = 0; pg < pageCount; pg++) {
  const start = pg * SPECIMENS_PER_PAGE;
  const pageData = specimens.slice(start, start + SPECIMENS_PER_PAGE);
  sections.push({
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 619, right: 605, bottom: 835, left: 605 }
      }
    },
    children: [buildPage(pageData)]
  });
}

const doc = new Document({ sections });

Packer.toBuffer(doc).then(buffer => {
  const outPath = process.argv[2] || 'specimen_labels.docx';
  fs.writeFileSync(outPath, buffer);
  console.log(`Wrote ${specimens.length} specimens across ${pageCount} pages to ${outPath}`);
});
```

**Important:** This is the structural pattern. When generating the actual script for a user, customize:
- The field names in specimen objects to match their mapped DwC terms
- The label builder functions to match their chosen layout
- Any custom label types they requested
- Font sizes and spacing if they customized the layout

#### Step 4.4 — Show Preview Summary

Before generating, display:

```
Label Generation Summary
════════════════════════
Specimens: 420
Pages: 6 (81 per page, last page: 15 specimens)
Label types: 3 (Locality, Collection, Determination)
Font: Helvetica 4pt (IDs at 3.5pt)
Page size: US Letter

Sample Label Preview (Specimen 1):
┌─────────────────────┬─────────────────────┬─────────────────────┐
│ BRAZIL, AMAZONAS    │ FIT                 │ Curculionidae       │
│ Res. Ducke, 26km    │ On Syagrus sp.      │ Anchylorhynchus     │
│ NE Manaus           │ coll.ID FMNH-12345  │   trapezicollis     │
│ S2.94985, W59.93417 │ genomic.ID BdM-0001 │   Vaurie, 1954      │
│ 80m                 │                     │ B. de Medeiros      │
│ 20.v.2012           │                     │   det. 2024         │
│ B. de Medeiros      │                     │                     │
└─────────────────────┴─────────────────────┴─────────────────────┘

Proceed with generation?
```

#### Step 4.5 — Generate and Run

Execute the scripts:

```bash
# Step 1: Preprocess data
python3 preprocess_labels.py input_data.xlsx

# Step 2: Generate .docx
node generate_labels.js specimen_labels.docx
```

#### Step 4.6 — Iterate

After generation, offer:
- "Open the file to check the layout?"
- "Adjust any abbreviations?"
- "Change font size or spacing?"
- "Regenerate with different settings?"

If the user wants to visually verify:
```bash
soffice --headless --convert-to pdf specimen_labels.docx
```

---

## Key Formatting Rules

These rules are **non-negotiable** and must be applied consistently:

### 1. Italic Rules
- **Italic:** genus name, specific epithet, infraspecific epithet, host plant genus + species
- **Roman (not italic):** "sp.", "spp.", "cf.", "aff.", "n. sp.", authority names, family names, "det.", "On", all other text

### 2. Date Format
- day.romanMonth.year: `20.v.2012`
- Ranges same month: `5-12.viii.2024`
- Ranges different months: `20.v-3.vi.2012`
- No leading zeros, lowercase Roman numerals

### 3. Coordinates
- Hemisphere prefix + |decimal value|, 5 decimal places
- `S2.94985, W59.93417`

### 4. Country/State
- Always UPPERCASED: `BRAZIL, AMAZONAS`

### 5. Host Plants
- "On " (roman) + *Genus species* (italic) + Authority (roman)
- Example: On *Syagrus inajai* (Spruce) Becc.

### 6. Missing Data
- Omit the entire line — no blanks, no "NaN", no empty lines

### 7. "sp." Handling
- Normalize all variants (sp.1, sp.A, sp. nov., sp.n., sp. indet.) to "sp."
- Display: *Genus* sp. — genus italic, "sp." roman

### 8. Determiner Line
- Format: `F. Last det. YEAR`
- "det." always lowercase, roman

---

## Communication Guidelines

### During Phase 1 (Data Ingestion)
- Show column mapping as a clear table
- Flag ambiguous mappings with specific options
- Ask about multi-table joins only if multiple files/sheets are present

### During Phase 2 (Label Design)
- Show default layout first — most users will accept defaults
- Only offer customization when explicitly requested
- Display character limits prominently

### During Phase 3 (Abbreviation)
- **Batch identical values** — never ask about each specimen individually
- Sort by frequency (most common values first)
- Show before/after character counts
- Suggest specific abbreviations from the conventions reference
- Let the user approve or modify in groups

### During Phase 4 (Generation)
- Show a text preview before generating
- Report specimen count and page count
- Offer iteration without restarting the entire workflow

### General
- Be concise — specimen label work is repetitive, don't over-explain
- Preserve the user's data exactly except for the formatting rules above
- When in doubt about an abbreviation, ask — never silently truncate

---

## Attribution

Skill created by Bruno de Medeiros (Field Museum of Natural History), building on the existing `prepare_for_labels.py` workflow and Word template.
