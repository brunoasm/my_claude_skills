#!/usr/bin/env python3
"""
Deduplicate user site records.

Usage:
    python3 deduplicate_sites.py <user_sites.json> [output.json]

Input: JSON from parse_user_data.py
Output: JSON with unique sites and their original row indices.
"""

import json
import sys


def make_site_key(record, fields=None):
    """Create a hashable key from site fields for deduplication."""
    if fields is None:
        fields = [
            "LocContinent", "LocCountry", "LocProvinceStateTerritory",
            "LocDistrictCountyShire", "LocTownship", "LocPreciseLocation",
            "LocElevationASLFromMt", "LocElevationASLToMt",
            "LocElevationASLFromFt", "LocElevationASLToFt",
            "LatLatitude", "LatLongitude", "SitSiteNumber",
        ]

    parts = []
    for field in fields:
        val = record.get(field)
        if val is None or str(val).strip() == "":
            parts.append("")
        else:
            parts.append(str(val).strip())
    return tuple(parts)


def deduplicate(site_records, row_mapping):
    """Group site records by unique site, return unique sites with row lists."""
    seen = {}  # key → index in unique_sites
    unique_sites = []
    site_rows = []  # parallel list: original xlsx row numbers per unique site

    for i, record in enumerate(site_records):
        key = make_site_key(record)

        # Skip all-empty records
        if all(v == "" for v in key):
            continue

        if key in seen:
            idx = seen[key]
            site_rows[idx].append(row_mapping[i])
        else:
            seen[key] = len(unique_sites)
            unique_sites.append(record)
            site_rows.append([row_mapping[i]])

    return unique_sites, site_rows


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <user_sites.json> [output.json]")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    with open(input_path) as f:
        data = json.load(f)

    site_records = data["site_records"]
    row_mapping = data["row_mapping"]

    unique_sites, site_rows = deduplicate(site_records, row_mapping)

    result = {
        "source_file": data["source_file"],
        "total_input_rows": len(site_records),
        "unique_sites": len(unique_sites),
        "sites": [
            {
                "site_index": i,
                "fields": site,
                "original_rows": rows,
                "specimen_count": len(rows),
            }
            for i, (site, rows) in enumerate(zip(unique_sites, site_rows))
        ],
    }

    output = json.dumps(result, indent=2, default=str)

    if output_path:
        with open(output_path, "w") as f:
            f.write(output)
        print(f"Deduplicated: {len(site_records)} rows → {len(unique_sites)} unique sites")
    else:
        print(output)

    # Print summary table
    print(f"\n{'#':<4} {'Location':<40} {'Specimens':<10}")
    print("-" * 54)
    for i, (site, rows) in enumerate(zip(unique_sites, site_rows)):
        loc = site.get("LocPreciseLocation") or site.get("LocTownship") or site.get("LocDistrictCountyShire") or "?"
        state = site.get("LocProvinceStateTerritory", "")
        label = f"{loc}, {state}" if state else loc
        print(f"{i:<4} {label:<40} {len(rows):<10}")


if __name__ == "__main__":
    main()
