# Darwin Core Term Mapping Reference

Map user-supplied column names to standardized Darwin Core (DwC) terms for entomological specimen labels.

## How to Use

1. Normalize user columns: lowercase, strip whitespace, replace spaces/hyphens with underscores
2. Look up each normalized name in the **Aliases** column below
3. Present the auto-mapping to the user for confirmation
4. Flag ambiguous matches (e.g., "id" could be catalogNumber or materialSampleID)

## Mapping Table

### Occurrence / Specimen

| DwC Term | Label Use | Aliases |
|----------|-----------|---------|
| `catalogNumber` | coll.ID line | catalog_number, catalogue_number, cat_no, catno, specimen_id, sample_id, fmnh_ins, voucher_id, accession, barcode, irn |
| `materialSampleID` | genomic.ID line | material_sample_id, genomics_id, genomic_id, dna_id, tissue_id, extraction_id, extract_id, dna_number, tissue_number, genetics_id |
| `otherCatalogNumbers` | additional IDs | other_catalog_numbers, alt_id, field_number, field_id, fieldbook_id, field_book_id, notebook_id |
| `recordedBy` | collector line | recorded_by, collector, collectors, primary_collector, leg, legit, coll, collected_by |
| `recordNumber` | — | record_number, collector_number, coll_number, coll_no |
| `sex` | det label sex | sex, gender |
| `lifeStage` | det label stage | life_stage, lifestage, stage, instar |
| `preparations` | — | preparation, prep, preservation, prep_type |
| `individualCount` | — | individual_count, count, n_specimens, num_specimens |
| `associatedSequences` | — | associated_sequences, genbank, genbank_accession, sequence_id |

### Event / Collecting

| DwC Term | Label Use | Aliases |
|----------|-----------|---------|
| `eventDate` | date line | event_date, date, collection_date, date_collected, collecting_date, coll_date, date_coll |
| `year` | date component | year, year_start, start_year, coll_year |
| `month` | date component | month, month_start, start_month, coll_month |
| `day` | date component | day, day_start, start_day, coll_day |
| `endDayOfYear` | date range end | end_day_of_year |
| `eventDate` (end) | date range | end_date, date_end |
| `year` (end) | date range | year_end, end_year |
| `month` (end) | date range | month_end, end_month |
| `day` (end) | date range | day_end, end_day |
| `samplingProtocol` | method line | sampling_protocol, collecting_method, method, trap_type, trap, collection_method, coll_method |
| `habitat` | locality context | habitat, microhabitat, vegetation, environment |
| `fieldNotes` | — | field_notes, notes, remarks, event_remarks |

### Location

| DwC Term | Label Use | Aliases |
|----------|-----------|---------|
| `country` | COUNTRY line | country, country_name, nation, pais, countrycode, country_code |
| `stateProvince` | STATE line | state_province, state, province, estado, dept, department, admin1, region, uf |
| `county` | — | county, municipality, municipio, mun, concelho, admin2 |
| `locality` | locality line | locality, site, location, collecting_locality, loc, localidade, place, site_name, specific_locality |
| `decimalLatitude` | lat line | decimal_latitude, latitude, lat, lat_dec, lat_decimal, y, verbatim_latitude |
| `decimalLongitude` | lon line | decimal_longitude, longitude, lon, long, lng, lon_dec, lon_decimal, x, verbatim_longitude |
| `minimumElevationInMeters` | elevation line | minimum_elevation_in_meters, elevation, alt, altitude, elev, min_elev, elevation_m |
| `maximumElevationInMeters` | elevation range | maximum_elevation_in_meters, max_elev, max_elevation, max_alt |
| `verbatimElevation` | elevation line | verbatim_elevation, elev_verbatim |
| `geodeticDatum` | — | geodetic_datum, datum, epsg |
| `coordinateUncertaintyInMeters` | — | coordinate_uncertainty, coord_uncertainty, gps_error |

### Taxonomy / Identification

| DwC Term | Label Use | Aliases |
|----------|-----------|---------|
| `scientificName` | determination label | scientific_name, species_name, taxon, identification, full_name, name, sci_name |
| `genus` | italic on det label | genus, gen |
| `specificEpithet` | italic on det label | specific_epithet, species, epithet, sp |
| `infraspecificEpithet` | det label | infraspecific_epithet, subspecies, variety, form, subsp, var |
| `scientificNameAuthorship` | det label (roman) | scientific_name_authorship, authority, author, species_authority, author_year |
| `family` | det label (roman) | family, familia |
| `order` | — | order, ordem |
| `higherClassification` | — | higher_classification, higher_taxon, higher_taxonomy, suprageneric |
| `taxonRank` | formatting decisions | taxon_rank, rank, taxon_level, id_level |
| `identifiedBy` | det line | identified_by, determiner, determined_by, det, id_by, identifier |
| `dateIdentified` | det year | date_identified, det_date, det_year, id_date, determination_date, id_year |
| `identificationQualifier` | cf./aff. handling | identification_qualifier, qualifier, certainty, species_certainty, cf, aff |
| `identificationRemarks` | — | identification_remarks, det_remarks, id_notes |
| `typeStatus` | type label | type_status, type, holotype, paratype |

### Associated Taxa (Host Plants)

| DwC Term | Label Use | Aliases |
|----------|-----------|---------|
| `associatedTaxa` | host plant line | associated_taxa, host_plant, plant, host, plant_species, host_association, association |
| — (plant genus) | italic on label | plant_genus, host_genus, plant_gen |
| — (plant species) | italic on label | plant_species, host_species, plant_epithet, host_epithet, plant_sp |
| — (plant authority) | roman on label | plant_authority, plant_author, host_authority |
| — (plant interaction) | prefix text | plant_interaction, interaction, association_type, on_plant |

## EMu-Specific Field Mappings

EMu (the museum database system) uses non-standard field names. These require special handling:

| EMu Field | DwC Term | Notes |
|-----------|----------|-------|
| `irn` | `catalogNumber` | Internal EMu record number |
| `ColCollectionEventRef` | — | Foreign key to event table |
| `ColRegPrefix` + `ColRegNumber` | `catalogNumber` | Concatenate with separator |
| `DarCountry` | `country` | EMu Darwin Core wrapper |
| `DarStateProvince` | `stateProvince` | EMu Darwin Core wrapper |
| `DarLocality` | `locality` | EMu Darwin Core wrapper |
| `DarLatitude` / `DarLongitude` | `decimalLatitude/Longitude` | May be DMS strings |
| `DarCollector` | `recordedBy` | |
| `DarDateLastModified` | — | Not useful for labels |
| `IdeTaxonRef_tab` | `scientificName` | Linked taxon record |
| `IdeIdentifiedByRef_tab` | `identifiedBy` | Linked person record |
| `IdeDateIdentified0` | `dateIdentified` | Array field |
| `EntPreSpecies` | `specificEpithet` | Entomology-specific |
| `EntPreGenus` | `genus` | Entomology-specific |
| `EcoColl*` | `samplingProtocol` | Multiple ecology fields |

## Multi-Table Join Logic

When the user has data in multiple tables (common with relational databases):

1. **Identify key columns** — ask the user which column links the tables (e.g., `event_id`, `sample_id`, `irn`)
2. **Determine join order** — typically: specimens LEFT JOIN events LEFT JOIN taxonomy LEFT JOIN plants
3. **Handle suffix conflicts** — when column names collide after join (e.g., `det` in both insects and events), use suffixes and let the user pick which to keep
4. **Flatten the result** — all label fields should come from a single flat table before proceeding to label design

## Fuzzy Matching Strategy

When auto-mapping, apply these rules in order:

1. **Exact match** after normalization (lowercase, underscores)
2. **Prefix match**: `lat` matches `latitude`, `col` matches `collector`
3. **Contains match**: column containing `elev` maps to elevation terms
4. **Abbreviation match**: `det` → `identifiedBy`, `leg` → `recordedBy`, `alt` → elevation
5. **Flag ambiguous**: if multiple DwC terms could match, present options to user

Always present the full mapping to the user before proceeding. Never silently map ambiguous columns.
