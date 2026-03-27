#!/usr/bin/env python3
"""
Match deduplicated user sites against Emu site records.

Usage:
    python3 match_sites.py <dedup_sites.json> <emu_index.json> [output.json]

For each unique user site:
    - If coordinates exist: search by coordinate proximity + elevation
    - If no coordinates: fuzzy search by most precise available field
    - Score candidates and classify as exact_match, near_match, or no_match
"""

import json
import sys
import math
from difflib import SequenceMatcher

# Coordinate tolerance in degrees (~111m per 0.001 degree)
COORD_TOLERANCE = 0.005  # ~555m

# Fuzzy match threshold
FUZZY_THRESHOLD = 0.75

HIERARCHY_FIELDS = [
    "LocContinent",
    "LocCountry",
    "LocProvinceStateTerritory",
    "LocDistrictCountyShire",
    "LocTownship",
    "LocPreciseLocation",
]

FIELD_WEIGHTS = {
    "LocContinent": 5,
    "LocCountry": 10,
    "LocProvinceStateTerritory": 15,
    "LocDistrictCountyShire": 20,
    "LocTownship": 25,
    "LocPreciseLocation": 25,
}


def normalize_text(s):
    """Normalize for comparison."""
    if not s:
        return ""
    return str(s).strip().lower()


def fuzzy_ratio(a, b):
    """Fuzzy similarity ratio between two strings."""
    a_norm = normalize_text(a)
    b_norm = normalize_text(b)
    if not a_norm or not b_norm:
        return 0.0
    if a_norm == b_norm:
        return 1.0
    return SequenceMatcher(None, a_norm, b_norm).ratio()


def coord_distance(lat1, lon1, lat2, lon2):
    """Simple Euclidean distance in degrees (sufficient for small distances)."""
    if any(v is None for v in (lat1, lon1, lat2, lon2)):
        return float("inf")
    return math.sqrt((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2)


def score_match(user_site, emu_record):
    """Score how well two records match across hierarchy fields.
    Returns (score 0-100, field_comparisons dict)."""
    score = 0
    max_score = 0
    comparisons = {}

    for field in HIERARCHY_FIELDS:
        weight = FIELD_WEIGHTS[field]
        user_val = normalize_text(user_site.get(field))
        emu_val = normalize_text(emu_record.get(field))

        if user_val and emu_val:
            max_score += weight
            sim = fuzzy_ratio(user_val, emu_val)
            score += weight * sim
            comparisons[field] = {
                "user": user_site.get(field),
                "emu": emu_record.get(field),
                "similarity": round(sim, 3),
                "match": sim > 0.9,
            }
        elif not user_val and not emu_val:
            comparisons[field] = {"user": None, "emu": None, "match": True}
        else:
            max_score += weight
            score += weight * 0.1  # Penalty for missing on one side
            comparisons[field] = {
                "user": user_site.get(field),
                "emu": emu_record.get(field),
                "similarity": 0.0,
                "match": False,
            }

    # Elevation comparison (bonus)
    user_elev = user_site.get("LocElevationASLFromMt")
    emu_elev = emu_record.get("LocElevationASLFromMt")
    if user_elev is not None and emu_elev is not None:
        try:
            elev_diff = abs(float(user_elev) - float(emu_elev))
            comparisons["elevation"] = {
                "user": user_elev,
                "emu": emu_elev,
                "diff_meters": elev_diff,
                "match": elev_diff < 50,
            }
        except (ValueError, TypeError):
            pass

    final_score = (score / max_score * 100) if max_score > 0 else 0
    return round(final_score, 1), comparisons


def get_coord_neighbors(coord_index, lat, lon, tolerance):
    """Get all record indices near a coordinate from the bucketed index."""
    if lat is None or lon is None:
        return []

    # Check surrounding buckets (precision=2 means buckets of 0.01)
    indices = []
    bucket_range = int(tolerance / 0.01) + 1
    lat_r = round(lat, 2)
    lon_r = round(lon, 2)

    for dlat in range(-bucket_range, bucket_range + 1):
        for dlon in range(-bucket_range, bucket_range + 1):
            key = f"{round(lat_r + dlat * 0.01, 2)},{round(lon_r + dlon * 0.01, 2)}"
            if key in coord_index:
                indices.extend(coord_index[key])

    return indices


def match_by_coordinates(user_site, emu_data, tolerance=COORD_TOLERANCE):
    """Find Emu records near the user site's coordinates."""
    user_lat = user_site.get("LatLatitude")
    user_lon = user_site.get("LatLongitude")

    if user_lat is None or user_lon is None:
        return []

    user_lat = float(user_lat)
    user_lon = float(user_lon)

    # Get candidate indices from coordinate index
    candidate_indices = get_coord_neighbors(
        emu_data["coord_index"], user_lat, user_lon, tolerance
    )

    candidates = []
    for idx in candidate_indices:
        rec = emu_data["records"][idx]
        emu_lat = rec.get("LatLatitude")
        emu_lon = rec.get("LatLongitude")
        if emu_lat is None or emu_lon is None:
            continue

        dist = coord_distance(user_lat, user_lon, float(emu_lat), float(emu_lon))
        if dist <= tolerance:
            score, comparisons = score_match(user_site, rec)
            candidates.append({
                "irn": rec["irn"],
                "record_index": idx,
                "coord_distance_deg": round(dist, 6),
                "coord_distance_m": round(dist * 111000, 1),
                "score": score,
                "comparisons": comparisons,
                "emu_record": {k: v for k, v in rec.items()
                               if k in HIERARCHY_FIELDS or k.startswith("Loc") or k in ("irn", "LatLatitude", "LatLongitude")},
            })

    # Sort by coordinate distance, then score
    candidates.sort(key=lambda c: (c["coord_distance_deg"], -c["score"]))
    return candidates


def match_by_name(user_site, emu_data):
    """Fuzzy search by most precise available field."""
    # Find the most precise field with data
    for field in reversed(HIERARCHY_FIELDS):
        user_val = user_site.get(field)
        if user_val and str(user_val).strip():
            return _fuzzy_search_field(user_site, emu_data, field, user_val)
    return []


def _fuzzy_search_field(user_site, emu_data, field, user_val):
    """Search Emu name index for fuzzy matches at a specific field level."""
    name_index = emu_data["name_indices"].get(field, {})
    user_norm = normalize_text(user_val)

    candidates = []
    for emu_name, record_indices in name_index.items():
        sim = fuzzy_ratio(user_norm, emu_name)
        if sim >= FUZZY_THRESHOLD:
            # Score a sample of records (limit to avoid huge candidate lists)
            for idx in record_indices[:20]:
                rec = emu_data["records"][idx]
                score, comparisons = score_match(user_site, rec)
                candidates.append({
                    "irn": rec["irn"],
                    "record_index": idx,
                    "matched_field": field,
                    "field_similarity": round(sim, 3),
                    "score": score,
                    "comparisons": comparisons,
                    "emu_record": {k: v for k, v in rec.items()
                                   if k in HIERARCHY_FIELDS or k.startswith("Loc") or k in ("irn", "LatLatitude", "LatLongitude")},
                })

    candidates.sort(key=lambda c: -c["score"])
    return candidates[:10]  # Top 10


def classify_result(candidates, user_site):
    """Classify match result."""
    if not candidates:
        return "no_match"

    best = candidates[0]

    # Exact match: high score + (close coordinates OR same name)
    if best["score"] >= 90:
        if "coord_distance_m" in best and best["coord_distance_m"] < 100:
            return "exact_match"
        if "field_similarity" in best and best["field_similarity"] > 0.95:
            return "exact_match"

    if best["score"] >= 60:
        return "near_match"

    return "no_match"


def match_all_sites(dedup_data, emu_data):
    """Match all deduplicated user sites against Emu."""
    results = []

    for site_entry in dedup_data["sites"]:
        user_site = site_entry["fields"]
        site_idx = site_entry["site_index"]

        has_coords = (
            user_site.get("LatLatitude") is not None
            and user_site.get("LatLongitude") is not None
        )

        if has_coords:
            candidates = match_by_coordinates(user_site, emu_data)
            method = "coordinates"
        else:
            candidates = match_by_name(user_site, emu_data)
            method = "name"

        status = classify_result(candidates, user_site)

        # Build location label
        loc_parts = []
        for f in reversed(HIERARCHY_FIELDS):
            v = user_site.get(f)
            if v:
                loc_parts.append(str(v))
            if len(loc_parts) >= 2:
                break
        location_label = ", ".join(loc_parts) if loc_parts else "Unknown"

        results.append({
            "site_index": site_idx,
            "location_label": location_label,
            "method": method,
            "status": status,
            "specimen_count": site_entry["specimen_count"],
            "original_rows": site_entry["original_rows"],
            "candidates": candidates[:5],  # Top 5 candidates
            "matched_irn": candidates[0]["irn"] if status == "exact_match" else None,
            "user_site": user_site,
        })

    return results


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <dedup_sites.json> <emu_index.json> [output.json]")
        sys.exit(1)

    dedup_path = sys.argv[1]
    emu_path = sys.argv[2]
    output_path = sys.argv[3] if len(sys.argv) > 3 else None

    with open(dedup_path) as f:
        dedup_data = json.load(f)

    print(f"Loading Emu index from {emu_path}...")
    with open(emu_path) as f:
        emu_data = json.load(f)
    print(f"Loaded {len(emu_data['records'])} Emu records")

    print(f"\nMatching {len(dedup_data['sites'])} unique sites...")
    results = match_all_sites(dedup_data, emu_data)

    # Summary
    exact = sum(1 for r in results if r["status"] == "exact_match")
    near = sum(1 for r in results if r["status"] == "near_match")
    no_match = sum(1 for r in results if r["status"] == "no_match")

    print(f"\nResults:")
    print(f"  Exact matches:  {exact}")
    print(f"  Near matches:   {near} (need review)")
    print(f"  No matches:     {no_match} (need parent + creation)")

    print(f"\n{'#':<4} {'Status':<12} {'Method':<8} {'Location':<40} {'Specimens':<5} {'Best IRN':<10} {'Score':<6}")
    print("-" * 90)
    for r in results:
        best_irn = r["candidates"][0]["irn"] if r["candidates"] else "-"
        best_score = r["candidates"][0]["score"] if r["candidates"] else "-"
        print(f"{r['site_index']:<4} {r['status']:<12} {r['method']:<8} "
              f"{r['location_label'][:40]:<40} {r['specimen_count']:<5} {best_irn:<10} {best_score:<6}")

    output_data = {
        "source_file": dedup_data["source_file"],
        "summary": {
            "total_sites": len(results),
            "exact_matches": exact,
            "near_matches": near,
            "no_matches": no_match,
        },
        "results": results,
    }

    if output_path:
        with open(output_path, "w") as f:
            json.dump(output_data, f, indent=2, default=str)
        print(f"\nDetailed results written to {output_path}")
    else:
        print(json.dumps(output_data, indent=2, default=str))


if __name__ == "__main__":
    main()
