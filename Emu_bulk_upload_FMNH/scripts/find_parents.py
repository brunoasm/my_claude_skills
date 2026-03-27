#!/usr/bin/env python3
"""
Find parent site records in Emu for unmatched user sites.

Usage:
    python3 find_parents.py <match_results.json> <emu_index.json> [output.json]

For each unmatched or near_match site (without a confirmed IRN), walks up the
site hierarchy to find the closest existing parent in Emu.

Parents are records at a higher hierarchy level that encompass the user site.
A valid parent should NOT have a SitSiteNumber (if that field is available).
"""

import json
import sys
from difflib import SequenceMatcher

HIERARCHY_FIELDS = [
    "LocContinent",
    "LocCountry",
    "LocProvinceStateTerritory",
    "LocDistrictCountyShire",
    "LocTownship",
    "LocPreciseLocation",
]

# Fields that define a parent's identity (parent should match on all
# hierarchy fields at its level and above)
FIELD_WEIGHTS = {
    "LocContinent": 5,
    "LocCountry": 15,
    "LocProvinceStateTerritory": 20,
    "LocDistrictCountyShire": 25,
    "LocTownship": 20,
    "LocPreciseLocation": 15,
}


def normalize_text(s):
    if not s:
        return ""
    return str(s).strip().lower()


def fuzzy_ratio(a, b):
    a_norm = normalize_text(a)
    b_norm = normalize_text(b)
    if not a_norm or not b_norm:
        return 0.0
    if a_norm == b_norm:
        return 1.0
    return SequenceMatcher(None, a_norm, b_norm).ratio()


def get_most_precise_level(user_site):
    """Find the index of the most precise hierarchy field with data."""
    for i in range(len(HIERARCHY_FIELDS) - 1, -1, -1):
        val = user_site.get(HIERARCHY_FIELDS[i])
        if val and str(val).strip():
            return i
    return -1


def is_valid_parent(emu_record, child_level_index):
    """Check if an Emu record is a valid parent.
    A parent should be at a higher (less precise) level than the child.
    It should not have data at the child's level or below (ideally).
    It should not have a SitSiteNumber."""
    # If SitSiteNumber is available and non-empty, not a valid parent
    site_num = emu_record.get("SitSiteNumber")
    if site_num and str(site_num).strip():
        return False
    return True


def score_parent_candidate(user_site, emu_record, search_level_index):
    """Score how well an Emu record matches as a parent.
    Only considers fields at the search level and above."""
    score = 0
    max_score = 0
    comparisons = {}

    for i in range(search_level_index + 1):
        field = HIERARCHY_FIELDS[i]
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
                "match": sim > 0.85,
            }
        elif not user_val and not emu_val:
            comparisons[field] = {"user": None, "emu": None, "match": True}
        elif user_val and not emu_val:
            # Emu record missing a field the user has — penalty
            max_score += weight
            comparisons[field] = {
                "user": user_site.get(field),
                "emu": None,
                "similarity": 0.0,
                "match": False,
            }

    # Check that Emu record does NOT have data below the search level
    # (a proper parent should be at the search level, not below)
    has_lower_data = False
    for i in range(search_level_index + 1, len(HIERARCHY_FIELDS)):
        field = HIERARCHY_FIELDS[i]
        emu_val = emu_record.get(field)
        if emu_val and str(emu_val).strip():
            has_lower_data = True
            break

    final_score = (score / max_score * 100) if max_score > 0 else 0

    # Penalize records that have data below the search level
    # (they are more specific than needed for a parent)
    if has_lower_data:
        final_score *= 0.7

    return round(final_score, 1), comparisons, has_lower_data


def find_parent_at_level(user_site, emu_data, level_index):
    """Search for parent candidates at a specific hierarchy level."""
    field = HIERARCHY_FIELDS[level_index]
    user_val = user_site.get(field)

    if not user_val or not str(user_val).strip():
        return []

    # Search the name index for this field
    name_index = emu_data["name_indices"].get(field, {})
    user_norm = normalize_text(user_val)

    candidates = []
    checked_irns = set()

    for emu_name, record_indices in name_index.items():
        sim = fuzzy_ratio(user_norm, emu_name)
        if sim < 0.75:
            continue

        for idx in record_indices:
            rec = emu_data["records"][idx]
            irn = rec["irn"]

            if irn in checked_irns:
                continue
            checked_irns.add(irn)

            if not is_valid_parent(rec, level_index):
                continue

            score, comparisons, has_lower = score_parent_candidate(
                user_site, rec, level_index
            )

            candidates.append({
                "irn": irn,
                "record_index": idx,
                "search_level": field,
                "name_similarity": round(sim, 3),
                "score": score,
                "has_lower_level_data": has_lower,
                "comparisons": comparisons,
                "emu_record": {k: v for k, v in rec.items()
                               if k in HIERARCHY_FIELDS or k.startswith("Loc") or k in ("irn",)},
            })

    # Sort: prefer records WITHOUT lower-level data, then by score
    candidates.sort(key=lambda c: (c["has_lower_level_data"], -c["score"]))
    return candidates[:10]


def find_parent(user_site, emu_data):
    """Find the best parent for a user site by walking up the hierarchy.

    Returns:
        dict with parent_irn, search_level, candidates, and classification
        (perfect, partial, not_found, needs_creation)
    """
    most_precise = get_most_precise_level(user_site)
    if most_precise < 0:
        return {
            "status": "not_found",
            "message": "No hierarchy fields available",
            "candidates": [],
        }

    # Start searching one level above the most precise field
    for level_idx in range(most_precise - 1, -1, -1):
        field = HIERARCHY_FIELDS[level_idx]
        user_val = user_site.get(field)

        if not user_val or not str(user_val).strip():
            continue

        candidates = find_parent_at_level(user_site, emu_data, level_idx)

        if not candidates:
            continue

        best = candidates[0]

        # Classify
        if best["score"] >= 90 and not best["has_lower_level_data"]:
            return {
                "status": "perfect",
                "parent_irn": best["irn"],
                "search_level": field,
                "best_candidate": best,
                "candidates": candidates[:5],
                "message": f"Perfect parent match at {field} level",
            }
        elif best["score"] >= 60:
            return {
                "status": "partial",
                "parent_irn": best["irn"],
                "search_level": field,
                "best_candidate": best,
                "candidates": candidates[:5],
                "message": f"Partial parent match at {field} level — needs user confirmation",
            }

    # No parent found at any level
    return {
        "status": "not_found",
        "message": "No matching parent found at any hierarchy level",
        "candidates": [],
        "needs_creation": True,
    }


def find_parents_for_unmatched(match_results, emu_data):
    """Find parents for all unmatched sites."""
    parent_results = []

    for result in match_results["results"]:
        if result["status"] == "exact_match" and result.get("matched_irn"):
            parent_results.append({
                "site_index": result["site_index"],
                "location_label": result["location_label"],
                "match_status": "already_matched",
                "matched_irn": result["matched_irn"],
                "parent_search": None,
            })
            continue

        # Need to find a parent
        user_site = result["user_site"]
        parent_info = find_parent(user_site, emu_data)

        parent_results.append({
            "site_index": result["site_index"],
            "location_label": result["location_label"],
            "match_status": result["status"],
            "matched_irn": result.get("matched_irn"),
            "parent_search": parent_info,
            "user_site": user_site,
        })

    return parent_results


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <match_results.json> <emu_index.json> [output.json]")
        sys.exit(1)

    match_path = sys.argv[1]
    emu_path = sys.argv[2]
    output_path = sys.argv[3] if len(sys.argv) > 3 else None

    with open(match_path) as f:
        match_data = json.load(f)

    print(f"Loading Emu index from {emu_path}...")
    with open(emu_path) as f:
        emu_data = json.load(f)
    print(f"Loaded {len(emu_data['records'])} Emu records")

    print(f"\nFinding parents for unmatched sites...")
    results = find_parents_for_unmatched(match_data, emu_data)

    # Summary
    already_matched = sum(1 for r in results if r["match_status"] == "already_matched")
    perfect_parents = sum(1 for r in results if r.get("parent_search", {}).get("status") == "perfect")
    partial_parents = sum(1 for r in results if r.get("parent_search", {}).get("status") == "partial")
    no_parent = sum(1 for r in results if r.get("parent_search", {}).get("status") == "not_found")

    print(f"\nParent finding results:")
    print(f"  Already matched (have IRN):    {already_matched}")
    print(f"  Perfect parent found:          {perfect_parents}")
    print(f"  Partial parent (need review):  {partial_parents}")
    print(f"  No parent found:               {no_parent}")

    print(f"\n{'#':<4} {'Match':<16} {'Parent':<10} {'Level':<25} {'Parent IRN':<12} {'Location':<35}")
    print("-" * 105)
    for r in results:
        parent = r.get("parent_search") or {}
        parent_status = parent.get("status", "-")
        parent_irn = parent.get("parent_irn", "-") if parent else r.get("matched_irn", "-")
        level = parent.get("search_level", "-") if parent else "-"
        print(f"{r['site_index']:<4} {r['match_status']:<16} {parent_status:<10} "
              f"{level:<25} {str(parent_irn):<12} {r['location_label'][:35]:<35}")

    output_data = {
        "source_file": match_data["source_file"],
        "summary": {
            "already_matched": already_matched,
            "perfect_parents": perfect_parents,
            "partial_parents": partial_parents,
            "no_parent_found": no_parent,
            "total_new_sites": perfect_parents + partial_parents + no_parent,
        },
        "results": results,
    }

    if output_path:
        with open(output_path, "w") as f:
            json.dump(output_data, f, indent=2, default=str)
        print(f"\nDetailed results written to {output_path}")


if __name__ == "__main__":
    main()
