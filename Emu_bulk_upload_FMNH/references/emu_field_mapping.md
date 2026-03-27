# Emu Field Mapping Reference

## Site hierarchy fields

| Level | User xlsx (Row 2) | Emu CSV export | Bulk upload |
|-------|-------------------|----------------|-------------|
| Continent | `LocContinent_tab` | `LocContinent` | `LocContinent` |
| Country | `LocCountry_tab` | `LocCountry` | `LocCountry` |
| State/Province | `LocProvinceStateTerritory_tab` | `LocProvinceStateTerritory` | `LocProvinceStateTerritory` |
| County/District | `LocDistrictCountyShire_tab` | `LocDistrictCountyShire` | `LocDistrictCountyShire` |
| Township/City | `LocTownship_tab` | `LocTownship` | `LocTownship` |
| Precise Location | `LocPreciseLocation` | `LocPreciseLocation` | `LocPreciseLocation` |

## Elevation fields

| Description | User xlsx (Row 2) | Emu CSV export |
|-------------|-------------------|----------------|
| Elevation from (meters) | `LocElevationASLFromMt` | `LocElevationASLFromMt` |
| Elevation to (meters) | `LocElevationASLToMt` | `LocElevationASLToMt` |
| Elevation from (feet) | `LocElevationASLFromFt` | `LocElevationFromFt` |
| Elevation to (feet) | `LocElevationASLToFt` | `LocElevationToFt` |

## Coordinate fields

| Description | User xlsx (Row 2) | Emu CSV export |
|-------------|-------------------|----------------|
| Latitude | `LatLatitude_nesttab` | `LatPreferredCentroidLatDec` |
| Longitude | `LatLongitude_nesttab` | `LatPreferredCentroidLongDec` |
| Latitude (text) | — | `LatPreferredCentroidLatitude` |
| Longitude (text) | — | `LatPreferredCentroidLongitude` |

## Other site fields

| Description | User xlsx (Row 2) | Emu CSV export |
|-------------|-------------------|----------------|
| Site number | `SitSiteNumber` | not in standard export |
| Site IRN | — | `irn` |
| Parent IRN | — (output: `ColSiteRef.irn`) | — (bulk upload: `PolParent`) |

## Normalization rules

- Strip `_tab` and `_nesttab` suffixes from user xlsx field names to get canonical Emu names.
- Known value mismatches to handle via fuzzy matching:
  - "United States" (user) vs "United States of America" (Emu)
  - Typos in county/locality names (e.g., "Chochise" vs "Cochise")

## Column color conventions

- Green fill (`FFCCFFCC`): Sites module fields
- Tan/orange fill (`FFFFCC99`): Catalog/specimen fields
- The `ColSiteRef.irn` output column should use the same green fill as other site columns.

## Site columns in user xlsx (typical order)

Columns C through R in the example data:
- C: `LocContinent_tab`
- D: `LocCountry_tab`
- E: `LocProvinceStateTerritory_tab`
- F: `LocDistrictCountyShire_tab`
- G: `LocTownship_tab`
- H: `LocPreciseLocation`
- I: `LocElevationASLFromMt`
- J: `LocElevationASLToMt`
- K: `LocElevationASLFromFt`
- L: `LocElevationASLToFt`
- M–O: UTM fields (if present)
- P: `LatLatitude_nesttab`
- Q: `LatLongitude_nesttab`
- R: `SitSiteNumber`
