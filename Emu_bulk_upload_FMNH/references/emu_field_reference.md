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

## Sites module (green — `FFCCFFCC`)

### Site hierarchy

These fields form a hierarchy from most general to most precise. In Emu, each site record sits at a specific level and links to a parent record at the level above.

| Col | User-friendly name | Emu field (Row 2) | Canonical name | Description |
|-----|--------------------|-------------------|----------------|-------------|
| 3 | Continent | `LocContinent_tab` | `LocContinent` | Continent name (e.g., "North America") |
| 4 | Country | `LocCountry_tab` | `LocCountry` | Country name. Emu uses "United States of America" (user data may say "United States") |
| 5 | Province/State | `LocProvinceStateTerritory_tab` | `LocProvinceStateTerritory` | State, province, or territory |
| 6 | County | `LocDistrictCountyShire_tab` | `LocDistrictCountyShire` | County, district, or shire |
| 7 | City | `LocTownship_tab` | `LocTownship` | City, town, or township |
| 8 | Precise Location | `LocPreciseLocation` | `LocPreciseLocation` | Specific locality description (e.g., "Barfoot Park") |

### Elevation

| Col | User-friendly name | Emu field (Row 2) | Canonical name | Description |
|-----|--------------------|-------------------|----------------|-------------|
| 9 | Elevation From Mt. | `LocElevationASLFromMt` | `LocElevationASLFromMt` | Lower elevation bound in meters |
| 10 | Elevation To Mt. | `LocElevationASLToMt` | `LocElevationASLToMt` | Upper elevation bound in meters |
| 11 | Elevation From Ft. | `LocElevationASLFromFt` | `LocElevationASLFromFt` | Lower elevation bound in feet |
| 12 | Elevation To Ft. | `LocElevationASLToFt` | `LocElevationASLToFt` | Upper elevation bound in feet |

**Note**: Emu CSV exports use shorter names without "ASL": `LocElevationFromFt`, `LocElevationToFt`.

### UTM coordinates

These fields have Emu mappings but the exact database field names are not yet confirmed. See TODO in CLAUDE.md.

| Col | User-friendly name | Emu field (Row 2) | Canonical name | Description |
|-----|--------------------|-------------------|----------------|-------------|
| 13 | UTM Northing | *TBD* | *TBD* | UTM northing coordinate |
| 14 | UTM Easting | *TBD* | *TBD* | UTM easting coordinate |
| 15 | UTM Zone | *TBD* | *TBD* | UTM zone designator |

### Decimal coordinates

| Col | User-friendly name | Emu field (Row 2) | Canonical name | Description |
|-----|--------------------|-------------------|----------------|-------------|
| 16 | Latitude | `LatLatitude_nesttab` | `LatLatitude` | Decimal latitude (e.g., 31.917222) |
| 17 | Longitude | `LatLongitude_nesttab` | `LatLongitude` | Decimal longitude (e.g., -109.279722) |

**Note**: Emu CSV exports use `LatPreferredCentroidLatDec` and `LatPreferredCentroidLongDec`.

### Other site fields

| Col | User-friendly name | Emu field (Row 2) | Canonical name | Description |
|-----|--------------------|-------------------|----------------|-------------|
| 18 | Site Number | `SitSiteNumber` | `SitSiteNumber` | Emu site number identifier. Parent records should NOT have this field. |

### Output-only fields (added by the skill)

| Field | Description |
|-------|-------------|
| `ColSiteRef.irn` | Site IRN — inserted into user table after sites are matched/created in Emu |

---

## Collection Events module (gray — `FFC0C0C0`)

| Col | User-friendly name | Emu field (Row 2) | Description |
|-----|--------------------|-------------------|-------------|
| 19 | Habitat | `HabHabitat` | Habitat description |
| 20 | Microhabitat | `HabMicroHabitat` | Microhabitat description |
| 21 | Collection Method | `ColCollectionMethod` | How specimens were collected (e.g., "hand collected") |
| 22 | EventNotes | `ColSpecifics_tab` | Notes about the collecting event |
| 23 | Collection Code | `ColCollectionEventCode` | Unique event code |
| 24 | Other numbers 1 | *TBD* | Additional reference numbers. Emu field name TBD. |
| 25 | Other numbers 2 | *TBD* | Additional reference numbers. Emu field name TBD. |
| 26 | Expedition | *TBD* | Expedition name (e.g., "2025 Weevil Workshop"). Emu field name TBD. |
| 27 | Date Visited From | `ColDateVisitedFrom` | Start date of collecting event |
| 28 | Date Visited To | `ColDateVisitedTo` | End date of collecting event |
| 29 | Other Collection Numbers | `ColOtherNumbers_tab` | Other collection number references |
| 30 | Verbatim D/T/S | `SigVerbatimDateTime` | Verbatim date/time/season as recorded by collector |
| 31 | Collectors | `ColParticipantRef_tab(2).irn` | Collector names/IRNs. Index notation `(2)` for multiple collectors. |

---

## Catalog module (tan/orange — `FFFFCC99`)

### Specimen identification

| Col | User-friendly name | Emu field (Row 2) | Description |
|-----|--------------------|-------------------|-------------|
| 1 | FMNH-INS# | `CatCatalogNo2` | FMNH catalog number |
| 2 | Region | `LotRegion_tab` | Biogeographic region (e.g., "Neotropical") |

### Preparation (specimen 1)

| Col | User-friendly name | Emu field (Row 2) | Description |
|-----|--------------------|-------------------|-------------|
| 32 | Preparation 1 | `PrvPreservation_tab(1)` | Preservation method (e.g., "RNAlater", "pinned") |
| 33 | Life stage 1 | `PheStage_tab(1)` | Life stage (e.g., "adult", "larva") |
| 34 | Sex 1 | `PheSex_tab(1)` | Sex of specimen |
| 35 | Count 1 | `PreCount_tab(1)` | Number of specimens in this lot |
| 36 | Estimate 1 | `LotLotsEstimate_tab(1)` | Estimated count if exact count unavailable |

### Preparation (specimen 2)

| Col | User-friendly name | Emu field (Row 2) | Description |
|-----|--------------------|-------------------|-------------|
| 37 | Life stage 2 | `PheStage_tab(2)` | Life stage for second preparation |
| 38 | Sex 2 | `PheSex_tab(2)` | Sex for second preparation |
| 39 | Count 2 | `PreCount_tab(2)` | Count for second preparation |
| 40 | Estimate 2 | `LotLotsEstimate_tab(2)` | Estimate for second preparation |

### Taxonomy

| Col | User-friendly name | Emu field (Row 2) | Description |
|-----|--------------------|-------------------|-------------|
| 41 | Taxon | `IdeTaxonRef_tab.irn` | Taxonomic name or IRN reference |
| 42 | Certainty/Qualifier | `IdeQualifier_tab` | Identification certainty (e.g., "cf.", "aff.") |
| 43 | Qualifier rank | `IdeQualifierRank_tab` | Taxonomic rank the qualifier applies to |
| 44 | Identified by IRN | `IdeIdentifiedByRef_nesttab.irn` | Person who identified the specimen |
| 45 | Date Identified | `IdeDateIdentified0` | Date of identification |
| 46 | Identification Notes | `IdeIdentificationNotes_tab` | Notes about the identification |
| 47 | Label Notes | `IdeLotLabelNotes` | Notes for specimen labels |

### Natural history / host associations

| Col | User-friendly name | Emu field (Row 2) | Description |
|-----|--------------------|-------------------|-------------|
| 48 | Relationship | `RelNhRelationship_tab` | Nature of association (e.g., "on flowers of") |
| 49 | Host Name | `RelNhTaxonRef_tab.irn` | Host organism name or IRN |
| 50 | Host Count | `RelNhCount_tab` | Number of host organisms |
| 51 | According To | `RelNhAccordingToRef_tab.irn` | Source of association observation |
| 52 | Host URI | `RelNhURI_tab` | Link to supporting observation (e.g., iNaturalist URL) |
| 53 | Repository | `RelNhRepositoryRef_tab.irn` | Repository holding host record |
| 54 | Host remarks | `RelNhRemarks0` | Additional notes about host association |

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
2. Emu elevation exports lack "ASL": `LocElevationFromFt` → `LocElevationASLFromFt`
3. Emu coordinate exports use different names: `LatPreferredCentroidLatDec` → `LatLatitude`
4. Known value mismatches: "United States" ↔ "United States of America"
