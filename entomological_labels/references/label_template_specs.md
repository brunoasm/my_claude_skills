# Label Template Specifications

Exact measurements and formatting specs extracted from the Word template (`template/first_template.docx`). Use these values when generating label sheets with docx-js.

## Unit Reference

| Unit | Conversion |
|------|-----------|
| 1 inch | 1440 DXA (twentieths of a point) |
| 1 pt | 20 DXA |
| Font size | specified in half-points (sz=8 means 4pt) |
| 1 cm | ~567 DXA |
| 1 mm | ~56.7 DXA |

## Page Setup

| Property | Value | DXA | Notes |
|----------|-------|-----|-------|
| Page size | US Letter | 12240 x 15840 | width x height |
| Top margin | ~0.43" | 619 | |
| Right margin | ~0.42" | 605 | |
| Bottom margin | ~0.58" | 835 | |
| Left margin | ~0.42" | 605 | |
| Usable width | ~7.66" | 11030 | page width - left - right margins |

```javascript
// docx-js page setup
properties: {
  page: {
    size: { width: 12240, height: 15840 },
    margin: { top: 619, right: 605, bottom: 835, left: 605 }
  }
}
```

## Table Layout — Thin Separator Design

The label sheet uses a table with **11 columns**: 9 label columns + 2 thin separator columns. Each row holds 3 specimens, each with 3 label types (locality, collection, determination).

### Column Structure (per row)

```
| Loc1 | Coll1 | Det1 | SEP | Loc2 | Coll2 | Det2 | SEP | Loc3 | Coll3 | Det3 |
|  A   |   B   |  C   |thin |  A   |   B   |  C   |thin |  A   |   B   |  C   |
```

### Column Widths

| Column Type | Width (DXA) | Width (inches) | Count |
|-------------|-------------|----------------|-------|
| Label cell | 1194 | ~0.83" | 9 |
| Separator | 144 | ~0.10" | 2 |
| **Total** | **11034** | **~7.66"** | **11** |

Calculation: 9 x 1194 + 2 x 144 = 10746 + 288 = 11034 DXA

```javascript
// docx-js column widths array
columnWidths: [1194, 1194, 1194, 144, 1194, 1194, 1194, 144, 1194, 1194, 1194]
```

### Row Layout

| Property | Value | Notes |
|----------|-------|-------|
| Rows per page | 27 | |
| Row height | 490 DXA | exact height (not minimum) |
| Total row height | 27 x 490 = 13230 DXA | fits within usable height |

```javascript
// docx-js row height
new TableRow({
  height: { value: 490, rule: "exact" },  // HeightRule.EXACT
  children: [/* cells */]
})
```

## Typography

### Font Specifications

| Element | Font | Size (pt) | Size (half-pt) | Notes |
|---------|------|-----------|-----------------|-------|
| Label text (default) | Helvetica | 4 | 8 | all label content |
| Specimen/genomic IDs | Helvetica | 3.5 | 7 | slightly smaller for IDs |
| Genus + species epithet | Helvetica | 4 | 8 | **italic** |
| "sp.", "cf.", "aff." | Helvetica | 4 | 8 | roman (not italic) |
| Authority names | Helvetica | 4 | 8 | roman |
| Family name | Helvetica | 4 | 8 | roman |
| "det." prefix | Helvetica | 4 | 8 | roman |
| Host plant epithet | Helvetica | 4 | 8 | **italic** |
| "On" prefix | Helvetica | 4 | 8 | roman |

### Line Spacing

| Property | Value | Notes |
|----------|-------|-------|
| Line spacing | 90 twips | exact line spacing |
| Spacing before | 0 | no space before paragraphs |
| Spacing after | 0 | no space after paragraphs |

```javascript
// docx-js paragraph spacing for label text
new Paragraph({
  spacing: { line: 90, before: 0, after: 0 },
  children: [new TextRun({ text: "...", font: "Helvetica", size: 8 })]
})
```

**Note:** In docx-js, `spacing.line` uses twips (1/20 of a point). A value of 90 twips = 4.5pt line spacing, which is tight for 4pt text.

## Borders

| Property | Value |
|----------|-------|
| Border style | single |
| Border width | 0.5pt (4 eighth-points) |
| Border color | #E7E6E6 (light gray) |
| Applied to | all four sides of every label cell |

```javascript
// docx-js border definition
const labelBorder = {
  style: BorderStyle.SINGLE,
  size: 4,        // in eighth-points: 4 = 0.5pt
  color: "E7E6E6"
};
const labelCellBorders = {
  top: labelBorder,
  bottom: labelBorder,
  left: labelBorder,
  right: labelBorder
};
```

### Separator Column Borders

Separator columns have **no borders** (or transparent borders). They exist only to create visual spacing between specimen groups.

```javascript
const noBorder = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const separatorBorders = {
  top: noBorder, bottom: noBorder,
  left: noBorder, right: noBorder
};
```

## Cell Margins

| Property | Value (DXA) | Notes |
|----------|-------------|-------|
| Top | 29 | ~0.02" |
| Bottom | 29 | ~0.02" |
| Left | 29 | ~0.02" |
| Right | 29 | ~0.02" |

```javascript
// docx-js table-level margins (applies to all cells)
margins: { top: 29, bottom: 29, left: 29, right: 29 }
```

## Character Limits

Based on Helvetica at the specified sizes within the label cell width (~0.83" minus margins):

| Font Size | Usable width | Approx. chars/line | Notes |
|-----------|-------------|---------------------|-------|
| 4pt (sz=8) | ~0.79" | 28-30 | main label text |
| 3.5pt (sz=7) | ~0.79" | 32-35 | ID text |

These are approximate. Actual character count depends on the specific characters used (W is wider than i). Use these as guidelines when checking for text overflow.

### Tight Fields (most likely to overflow)

1. **Locality** — geographic names can be very long
2. **Collector** — multiple collectors with full names
3. **Host plant** — genus + species + authority
4. **Coordinates** — lat + lon on one line can be tight with high precision

## Label Content Layout

### Label A — Locality

```
COUNTRY, STATE          ← line 1 (uppercased)
locality text           ← line 2 (may wrap)
S0.12345, W35.67890     ← line 3 (formatted coords)
1200m                   ← line 4 (elevation + "m")
20.v.2012               ← line 5 (day.romanMonth.year)
B.A.S. de Medeiros      ← line 6 (collector)
```

### Label B — Collection Data

```
beating, on flowers     ← line 1 (method + interaction)
On Genus species Auth.  ← line 2 (host plant, italic genus+sp)
coll.ID FMNH-INS-12345 ← line 3 (catalog number, smaller font)
genomic.ID BdM-1234    ← line 4 (if present, smaller font)
```

### Label C — Determination

```
Family Name             ← line 1 (roman)
Genus species           ← line 2 (italic genus+epithet)
  (Author, Year)        ← line 3 (roman, if present)
F. Last det. 2024       ← line 4 (determiner + year)
```

## Pagination

- 27 rows per page x 3 specimens per row = **81 specimens per page**
- For N specimens: `Math.ceil(N / 81)` pages
- Each page after the first starts with a new section or page break
- All pages use identical layout and table structure

## Complete docx-js Table Construction Pattern

```javascript
// Helper: create a label cell
function labelCell(paragraphs, width = 1194) {
  return new TableCell({
    width: { size: width, type: WidthType.DXA },
    borders: labelCellBorders,
    children: paragraphs
  });
}

// Helper: create a separator cell
function separatorCell() {
  return new TableCell({
    width: { size: 144, type: WidthType.DXA },
    borders: separatorBorders,
    children: [new Paragraph({ spacing: { line: 90, before: 0, after: 0 }, children: [] })]
  });
}

// Helper: create a label paragraph
function labelParagraph(runs, fontSize = 8) {
  // Apply default font to runs that don't specify one
  const styledRuns = runs.map(r => {
    if (r instanceof TextRun) return r; // already constructed
    return new TextRun({ font: "Helvetica", size: fontSize, ...r });
  });
  return new Paragraph({
    spacing: { line: 90, before: 0, after: 0 },
    children: styledRuns
  });
}
```

## Notes

- Helvetica may not be available on all systems. Consider fallback: `font: "Helvetica"` in docx-js will use the closest available substitute. On Windows this typically maps to Arial.
- The template uses "exact" row heights, meaning content that exceeds the cell height will be clipped, not wrapped to the next row. Keep text within character limits.
- When generating multi-page documents, use separate sections or page breaks — do not rely on table auto-pagination for precise control.
