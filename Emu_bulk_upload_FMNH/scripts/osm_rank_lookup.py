#!/usr/bin/env python3
"""
OSM-based PolPoliticalRank suggestion.

Queries the Nominatim public API for a locality name and returns a candidate
Emu PolPoliticalRank plus a confidence score. Intended to be called once per
distinct named level in the user's data; results are cached on disk.

Usage:
    python3 osm_rank_lookup.py "San Simon" "United States" [--parent "Arizona"] [--lat 31.99 --lon -109.17]

Output (stdout, JSON):
    {
      "query": {...},
      "suggested_rank": "Village",
      "confidence": "high|medium|low",
      "candidates": [ {"rank": "...", "osm_tags": {...}, "display_name": "..."}, ... ],
      "osm_evidence": {...}
    }

Respect Nominatim usage policy:
    - User-Agent identifies this skill.
    - At most 1 request/second.
    - Results cached in /tmp/osm_cache.json.
"""

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request

NOMINATIM = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "FMNH-Emu-Bulk-Upload-Skill/1.0 (bdemedeiros@fieldmuseum.org)"
CACHE_PATH = "/tmp/osm_cache.json"
MIN_INTERVAL = 1.05  # seconds between requests

_last_request_time = 0.0


def load_cache():
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH) as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_cache(cache):
    try:
        with open(CACHE_PATH, "w") as f:
            json.dump(cache, f)
    except Exception:
        pass


def throttle():
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < MIN_INTERVAL:
        time.sleep(MIN_INTERVAL - elapsed)
    _last_request_time = time.time()


def nominatim_search(query_parts, lat=None, lon=None):
    cache = load_cache()
    cache_key = json.dumps({"q": query_parts, "lat": lat, "lon": lon}, sort_keys=True)
    if cache_key in cache:
        return cache[cache_key]

    params = {
        "q": ", ".join(p for p in query_parts if p),
        "format": "jsonv2",
        "addressdetails": 1,
        "extratags": 1,
        "limit": 5,
    }
    url = f"{NOMINATIM}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    throttle()
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e), "results": []}

    # Optionally filter/sort by distance to requested coords
    if lat is not None and lon is not None:
        for r in data:
            try:
                r["_dist_deg"] = (
                    (float(r["lat"]) - lat) ** 2 + (float(r["lon"]) - lon) ** 2
                ) ** 0.5
            except Exception:
                r["_dist_deg"] = 999
        data.sort(key=lambda r: r.get("_dist_deg", 999))

    cache[cache_key] = {"results": data}
    save_cache(cache)
    return {"results": data}


# Mapping from (place tag, admin_level, country_code) → Emu rank
def rank_from_osm(tags, address, country_code):
    place = tags.get("place") or ""
    extratags = tags.get("extratags") or {}
    osm_type = tags.get("type") or ""
    category = tags.get("category") or ""
    admin_level = None
    try:
        admin_level = int(extratags.get("admin_level") or tags.get("admin_level") or 0)
    except Exception:
        admin_level = 0

    # place=*
    place_map = {
        "city": "City",
        "town": "Town",
        "village": "Village",
        "hamlet": "Village",
        "municipality": "Municipality",
        "county": "County",
        "state": "State",
        "province": "Province",
        "country": "Country",
        "continent": "Continent",
    }
    if place in place_map:
        return place_map[place]

    # Parks / protected areas → LMA
    if category == "boundary" and osm_type in ("national_park", "protected_area"):
        return "LMA"
    if category == "leisure" and osm_type == "park":
        return "LMA"

    # admin_level by country
    if category == "boundary" and osm_type == "administrative" and admin_level:
        cc = (country_code or "").lower()
        if admin_level == 2:
            return "Country"
        if cc == "us":
            return {4: "State", 6: "County", 7: "City", 8: "City"}.get(admin_level)
        if cc == "ca":
            return {4: "Province", 6: "County", 8: "City"}.get(admin_level)
        if cc == "br":
            return {4: "State", 6: "Municipality", 8: "City"}.get(admin_level)
        if cc in ("gb", "uk"):
            return {4: "Country", 6: "County", 8: "City"}.get(admin_level)
        if cc == "fr":
            return {4: "Region", 6: "Department", 7: "Arrondissement", 8: "City"}.get(admin_level)
        # generic fallback by depth
        return {3: "Region", 4: "State", 5: "Region", 6: "County", 7: "Municipality", 8: "City"}.get(admin_level)

    return None


def classify(results, country_hint):
    candidates = []
    cc = None
    if results:
        addr = results[0].get("address") or {}
        cc = addr.get("country_code")
    for r in results:
        rank = rank_from_osm(r, r.get("address") or {}, cc or country_hint)
        if rank:
            candidates.append({
                "rank": rank,
                "osm_category": r.get("category"),
                "osm_type": r.get("type"),
                "place": (r.get("extratags") or {}).get("place") or r.get("class"),
                "admin_level": (r.get("extratags") or {}).get("admin_level"),
                "display_name": r.get("display_name"),
                "dist_deg": r.get("_dist_deg"),
            })

    if not candidates:
        return {
            "suggested_rank": None,
            "confidence": "low",
            "candidates": [],
            "osm_evidence": {"n_results": len(results)},
        }

    # Count ranks among top candidates
    rank_counts = {}
    for c in candidates[:3]:
        rank_counts[c["rank"]] = rank_counts.get(c["rank"], 0) + 1

    best_rank, best_count = max(rank_counts.items(), key=lambda kv: kv[1])

    if len(candidates) == 1:
        confidence = "high"
    elif best_count >= 2 and best_count > sum(rank_counts.values()) / 2:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "suggested_rank": best_rank,
        "confidence": confidence,
        "candidates": candidates,
        "osm_evidence": {"n_results": len(results)},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("country", nargs="?", default="")
    ap.add_argument("--parent", default="")
    ap.add_argument("--lat", type=float)
    ap.add_argument("--lon", type=float)
    args = ap.parse_args()

    query_parts = [p for p in [args.name, args.parent, args.country] if p]
    res = nominatim_search(query_parts, lat=args.lat, lon=args.lon)
    results = res.get("results", [])

    out = classify(results, args.country)
    out["query"] = {
        "name": args.name,
        "parent": args.parent,
        "country": args.country,
        "lat": args.lat,
        "lon": args.lon,
    }
    json.dump(out, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
