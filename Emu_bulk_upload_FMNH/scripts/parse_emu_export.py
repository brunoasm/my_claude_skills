#!/usr/bin/env python3
"""
Parse an Emu sites CSV export and build searchable indices.

Usage:
    python3 parse_emu_export.py <emu_export.csv> <output.json>

Builds:
    - coord_index: dict keyed by rounded (lat, lon) for fast coordinate lookup
    - name_indices: dict per hierarchy level, keyed by normalized name
    - stats: record counts, coordinate coverage, etc.
"""

import csv
import json
import sys
import os
from collections import defaultdict

# Emu CSV field name → canonical field name mapping
EMU_CSV_FIELDS = {
    "irn": "irn",
    "LocContinent": "LocContinent",
    "LocCountry": "LocCountry",
    "LocProvinceStateTerritory": "LocProvinceStateTerritory",
    "LocDistrictCountyShire": "LocDistrictCountyShire",
    "LocTownship": "LocTownship",
    "LocPreciseLocation": "LocPreciseLocation",
    "LocElevationASLFromMt": "LocElevationASLFromMt",
    "LocElevationASLToMt": "LocElevationASLToMt",
    "LocElevationFromFt": "LocElevationASLFromFt",
    "LocElevationToFt": "LocElevationASLToFt",
    "LatPreferredCentroidLatDec": "LatLatitude",
    "LatPreferredCentroidLongDec": "LatLongitude",
    "LatPreferredCentroidLatitude": "LatLatitudeText",
    "LatPreferredCentroidLongitude": "LatLongitudeText",
    "SitSiteNumber": "SitSiteNumber",
}

HIERARCHY_FIELDS = [
    "LocContinent",
    "LocCountry",
    "LocProvinceStateTerritory",
    "LocDistrictCountyShire",
    "LocTownship",
    "LocPreciseLocation",
]


def normalize_text(s):
    """Normalize text for comparison: lowercase, strip whitespace."""
    if not s:
        return ""
    return str(s).strip().lower()


def parse_float(s):
    """Parse a string as float, return None on failure."""
    if not s or not str(s).strip():
        return None
    try:
        return float(str(s).strip())
    except ValueError:
        return None


def round_coord(val, precision=2):
    """Round a coordinate for bucketing."""
    if val is None:
        return None
    return round(val, precision)


def read_emu_export(filepath):
    """Read Emu CSV and return normalized records."""
    records = []
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            record = {}
            for csv_field, canonical in EMU_CSV_FIELDS.items():
                val = row.get(csv_field, "").strip()
                record[canonical] = val if val else None

            # Parse coordinates as floats
            record["LatLatitude"] = parse_float(record.get("LatLatitude"))
            record["LatLongitude"] = parse_float(record.get("LatLongitude"))

            # Parse elevation as floats
            for elev_field in ["LocElevationASLFromMt", "LocElevationASLToMt",
                               "LocElevationASLFromFt", "LocElevationASLToFt"]:
                record[elev_field] = parse_float(record.get(elev_field))

            records.append(record)

    return records


def build_coord_index(records):
    """Build spatial index: {(rounded_lat, rounded_lon): [record_indices]}."""
    index = defaultdict(list)
    for i, rec in enumerate(records):
        lat = rec.get("LatLatitude")
        lon = rec.get("LatLongitude")
        if lat is not None and lon is not None:
            key = (round_coord(lat), round_coord(lon))
            index[key].append(i)
    return dict(index)


def build_name_indices(records):
    """Build name lookup: {hierarchy_level: {normalized_name: [record_indices]}}."""
    indices = {}
    for field in HIERARCHY_FIELDS:
        field_index = defaultdict(list)
        for i, rec in enumerate(records):
            val = rec.get(field)
            if val:
                key = normalize_text(val)
                field_index[key].append(i)
        indices[field] = dict(field_index)
    return indices


def compute_stats(records):
    """Compute summary statistics."""
    total = len(records)
    with_coords = sum(
        1
        for r in records
        if r.get("LatLatitude") is not None and r.get("LatLongitude") is not None
    )
    with_site_num = sum(1 for r in records if r.get("SitSiteNumber"))

    # Count non-empty values per hierarchy field
    field_counts = {}
    for field in HIERARCHY_FIELDS:
        field_counts[field] = sum(1 for r in records if r.get(field))

    return {
        "total_records": total,
        "with_coordinates": with_coords,
        "without_coordinates": total - with_coords,
        "with_site_number": with_site_num,
        "field_coverage": field_counts,
    }


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <emu_export.csv> <output.json>")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    print(f"Reading Emu export from {input_path}...")
    records = read_emu_export(input_path)
    print(f"Loaded {len(records)} records")

    print("Building coordinate index...")
    coord_index = build_coord_index(records)
    print(f"  {len(coord_index)} unique coordinate buckets")

    print("Building name indices...")
    name_indices = build_name_indices(records)
    for field in HIERARCHY_FIELDS:
        print(f"  {field}: {len(name_indices[field])} unique values")

    stats = compute_stats(records)
    print(f"\nStats: {stats['with_coordinates']} with coords, "
          f"{stats['with_site_number']} with site numbers")

    # Save everything as JSON
    # Records are stored as a list; indices reference by list index
    result = {
        "source_file": os.path.basename(input_path),
        "stats": stats,
        "records": records,
        "coord_index": {f"{k[0]},{k[1]}": v for k, v in coord_index.items()},
        "name_indices": name_indices,
    }

    print(f"\nWriting to {output_path}...")
    with open(output_path, "w") as f:
        json.dump(result, f)

    file_size = os.path.getsize(output_path) / (1024 * 1024)
    print(f"Done. Output size: {file_size:.1f} MB")


if __name__ == "__main__":
    main()
