# Emu Field Reference

Complete reference for all columns in the Emu upload template (`Emu_upload_default.xlsx`).

## Template format

| Row | Content |
|-----|---------|
| Row 1 | User-friendly column names |
| Row 2 | Emu database field names (with `_tab`/`_nesttab` suffixes where applicable) |
| Row 3 | Example data |
| Row 4+ | Actual specimen data |

## Column colors by module

| Color | Hex code | Module |
|-------|----------|--------|
| Green | `FFCCFFCC` | Sites |
| Gray | `FFC0C0C0` | Collection Events |
| Tan/Orange | `FFFFCC99` | Catalog |

---

## Catalog module (tan/orange — `FFFFCC99`)

### Specimen identification

| Col | User-friendly name | Emu field (Row 2) | Description |
|-----|--------------------|-------------------|-------------|
| 1 | FMNH-INS# | `CatCatalogNo2` | FMNH catalog number |
| 2 | Region | `LotRegion_tab` | Biogeographic region (e.g., "Neotropical") |
| 3 | Project | `CatProjectInsects_tab` | Project code (e.g., "2025") |

---

## Sites module (green — `FFCCFFCC`)

### Site hierarchy

These fields form a hierarchy from most general to most precise. In Emu, each site record sits at a specific level and links to a parent record at the level above.

| Col | User-friendly name | Emu field (Row 2) | Canonical name | Emu CSV export name | Description |
|-----|--------------------|-------------------|----------------|----------------------|-------------|
| 4 | Continent | `LocContinent_tab` | `LocContinent` | `LocContinent` | Continent name (e.g., "North America") |
| 5 | Country | `LocCountry_tab` | `LocCountry` | `LocCountry` | Country name. Emu uses "United States of America" (user data may say "United States") |
| 6 | Province/State | `LocProvinceStateTerritory_tab` | `LocProvinceStateTerritory` | `LocProvinceStateTerritory` | State, province, or territory |
| 7 | County | `LocDistrictCountyShire_tab` | `LocDistrictCountyShire` | `LocDistrictCountyShire` | County, district, or shire |
| 8 | City | `LocTownship_tab` | `LocTownship` | `LocTownship` | City, town, or township |
| 9 | Precise Location | `LocPreciseLocation` | `LocPreciseLocation` | `LocPreciseLocation` | Specific locality description (e.g., "Barfoot Park") |

### Elevation

| Col | User-friendly name | Emu field (Row 2) | Canonical name | Emu CSV export name | Description |
|-----|--------------------|-------------------|----------------|----------------------|-------------|
| 10 | Elevation From Mt. | `LocElevationASLFromMt` | `LocElevationASLFromMt` | `LocElevationASLFromMt` | Lower elevation bound in meters |
| 11 | Elevation To Mt. | `LocElevationASLToMt` | `LocElevationASLToMt` | `LocElevationASLToMt` | Upper elevation bound in meters |
| 12 | Elevation From Ft. | `LocElevationASLFromFt` | `LocElevationASLFromFt` | `LocElevationFromFt` | Lower elevation bound in feet |
| 13 | Elevation To Ft. | `LocElevationASLToFt` | `LocElevationASLToFt` | `LocElevationToFt` | Upper elevation bound in feet |

**Note**: Emu CSV exports use shorter names without "ASL" for feet fields.

### Decimal coordinates

| Col | User-friendly name | Emu field (Row 2) | Canonical name | Emu CSV export name | Description |
|-----|--------------------|-------------------|----------------|----------------------|-------------|
| 14 | Latitude | `LatLatitude_nesttab` | `LatLatitude` | `LatPreferredCentroidLatDec` | Decimal latitude (e.g., 31.917222) |
| 15 | Longitude | `LatLongitude_nesttab` | `LatLongitude` | `LatPreferredCentroidLongDec` | Decimal longitude (e.g., -109.279722) |

**Note**: Emu CSV exports also provide text versions: `LatPreferredCentroidLatitude` and `LatPreferredCentroidLongitude`.

### Other site fields

| Col | User-friendly name | Emu field (Row 2) | Canonical name | Emu CSV export name | Description |
|-----|--------------------|-------------------|----------------|----------------------|-------------|
| 16 | Site Number | `SitSiteNumber` | `SitSiteNumber` | not in standard export | Emu site number identifier. Parent records should NOT have this field. |

### Output-only fields (added by the skill)

| Field | Emu CSV export | Bulk upload | Description |
|-------|----------------|-------------|-------------|
| `ColSiteRef.irn` | — | `ColSiteRef.irn` | Site IRN — inserted into user table after sites are matched/created in Emu |
| — | `irn` | — | Site IRN as it appears in Emu CSV export |
| — | — | `PolParentRef.irn` | Parent site IRN used in bulk upload of new sites |

---

## Collection Events module (gray — `FFC0C0C0`)

| Col | User-friendly name | Emu field (Row 2) | Description |
|-----|--------------------|-------------------|-------------|
| 17 | Habitat | `HabHabitat` | Habitat description |
| 18 | Microhabitat | `HabMicroHabitat` | Microhabitat description |
| 19 | Collection Method | `ColCollectionMethod` | How specimens were collected (e.g., "hand collected") |
| 20 | EventNotes | `ColSpecifics_tab` | Notes about the collecting event |
| 21 | Collection Code | `ColCollectionEventCode` | Unique event code |
| 22 | Date Visited From | `ColDateVisitedFrom` | Start date of collecting event |
| 23 | Date Visited To | `ColDateVisitedTo` | End date of collecting event |
| 24 | Other Collection Numbers | `ColOtherNumbers_tab` | Other collection number references |
| 25 | Verbatim D/T/S | `SigVerbatimDateTime` | Verbatim date/time/season as recorded by collector |
| 26 | Collectors | `ColParticipantRef_tab(2).irn` | Collector names/IRNs. Index notation `(2)` for multiple collectors. |

---

## Catalog module (continued)

### Preparation (specimen 1)

| Col | User-friendly name | Emu field (Row 2) | Description |
|-----|--------------------|-------------------|-------------|
| 27 | Prepartion 1 | `PrvPreservation_tab(1)` | Preservation method (e.g., "RNAlater", "pinned") |
| 28 | Life stage 1 | `PheStage_tab(1)` | Life stage (e.g., "adult", "larva") |
| 29 | Sex 1 | `PheSex_tab(1)` | Sex of specimen |
| 30 | Count 1 | `PreCount_tab(1)` | Number of specimens in this lot |
| 31 | Estimate 1 | `LotLotsEstimate_tab(1)` | Estimated count if exact count unavailable |

### Preparation (specimen 2)

| Col | User-friendly name | Emu field (Row 2) | Description |
|-----|--------------------|-------------------|-------------|
| 32 | Life stage 2 | `PheStage_tab(2)` | Life stage for second preparation |
| 33 | Sex 2 | `PheSex_tab(2)` | Sex for second preparation |
| 34 | Count 2 | `PreCount_tab(2)` | Count for second preparation |
| 35 | Estimate 2 | `LotLotsEstimate_tab(2)` | Estimate for second preparation |

### Taxonomy

| Col | User-friendly name | Emu field (Row 2) | Description |
|-----|--------------------|-------------------|-------------|
| 36 | Taxon | `IdeTaxonRef_tab.irn` | Taxonomic name or IRN reference |
| 37 | Certainty/Qualifier | `IdeQualifier_tab` | Identification certainty (e.g., "cf.", "aff.") |
| 38 | Qualifier rank | `IdeQualifierRank_tab` | Taxonomic rank the qualifier applies to |
| 39 | Identified by IRN | `IdeIdentifiedByRef_nesttab.irn` | Person who identified the specimen |
| 40 | Date Identified | `IdeDateIdentified0` | Date of identification |
| 41 | Identification Notes | `IdeIdentificationNotes_tab` | Notes about the identification |
| 42 | Label Notes | `IdeLotLabelNotes` | Notes for specimen labels |

### Natural history / host associations

| Col | User-friendly name | Emu field (Row 2) | Description |
|-----|--------------------|-------------------|-------------|
| 43 | Relationship | `RelNhRelationship_tab` | Nature of association (e.g., "on flowers of") |
| 44 | Host Name | `RelNhTaxonRef_tab.irn` | Host organism name or IRN |
| 45 | Host Count | `RelNhCount_tab` | Number of host organisms |
| 46 | According To | `RelNhAccordingToRef_tab.irn` | Source of association observation |
| 47 | Host URI | `RelNhURI_tab` | Link to supporting observation (e.g., iNaturalist URL) |
| 48 | Repository | `RelNhRepositoryRef_tab.irn` | Repository holding host record |
| 49 | Host remarks | `RelNhRemarks0` | Additional notes about host association |

---

## Field name conventions

### Suffixes in user xlsx (Row 2)
- `_tab` — indicates a table/repeatable field (e.g., `LocCountry_tab`)
- `_nesttab` — indicates a nested table field (e.g., `LatLatitude_nesttab`)
- `.irn` — indicates an IRN reference to another module (e.g., `IdeTaxonRef_tab.irn`)
- `(N)` — index for multi-valued fields (e.g., `PheStage_tab(1)`, `PheStage_tab(2)`)

### Normalization rules
When comparing user xlsx fields to Emu export fields:
1. Strip `_tab` and `_nesttab` suffixes
2. Emu elevation exports lack "ASL": `LocElevationFromFt` maps to `LocElevationASLFromFt`
3. Emu coordinate exports use different names: `LatPreferredCentroidLatDec` maps to `LatLatitude`
4. Known value mismatches to handle via fuzzy matching:
   - "United States" (user) vs "United States of America" (Emu)
   - Typos in county/locality names (e.g., "Chochise" vs "Cochise")

### Column fill conventions
- The `ColSiteRef.irn` output column should use the same green fill (`FFCCFFCC`) as other site columns.
