#!/usr/bin/env python3
"""
Generate Emu bulk upload CSV tables for new Sites records.

Input: a chains JSON that Claude assembles during orchestration. Each chain
describes the sequence of nodes needed to place a user's site in Emu's tree,
bottom-up-resolved: every chain starts from a known parent IRN (or None for
top-level) and lists the nodes below it that still need to be created.

Input format (example):
    {
      "classification": "Terrestrial",
      "primary_coords": true,
      "chains": [
        {
          "user_site_index": 4,
          "label": "San Simon pt. 1",
          "parent_irn": "503258",              # known Emu IRN anchoring the chain
          "nodes": [
            {
              "rank": "Village",
              "name": "San Simon",
              "status": "needs_creation",      # or "exists"
              "irn": null,                     # filled if status==exists
              "coords": null,
              "elevation": null
            },
            {
              "rank": "Precise Locality",
              "name": "",                      # unnamed precise locality
              "status": "needs_creation",
              "coords": {"lat": 31.989444, "lon": -109.17333},
              "elevation": {"from_m": 1380}
            }
          ]
        },
        ...
      ]
    }

Output:
    <output_dir>/sites_upload_batch_1.csv   # nodes at depth 1 below known parents
    <output_dir>/sites_upload_batch_2.csv   # nodes that parent to a batch-1 row
    ...
    <output_dir>/upload_metadata.json       # dependency map + placeholders

Columns in each CSV (blank columns auto-removed):
    SitRecordClassification
    PolPoliticalRank
    PolLocality
    LocElevationASLFromMt, LocElevationASLToMt, LocElevationASLFromFt, LocElevationASLToFt
    LatLatitudeDecimal_nesttab, LatLongitudeDecimal_nesttab
    PolParentRef.irn

Cross-batch parent refs use placeholders like `__PENDING_B1_R3__` (batch 1, row 3,
1-indexed including header offset). After each batch is uploaded to Emu, the
user returns the new IRNs and Claude substitutes the placeholders in later
batches before running them.
"""

import csv
import json
import os
import sys

UPLOAD_COLUMNS = [
    "SitRecordClassification",
    "PolPoliticalRank",
    "PolLocality",
    "LocElevationASLFromMt",
    "LocElevationASLToMt",
    "LocElevationASLFromFt",
    "LocElevationASLToFt",
    "LatLatitudeDecimal_nesttab",
    "LatLongitudeDecimal_nesttab",
    "PolParentRef.irn",
]


def elevation_fields(elevation):
    if not elevation:
        return {}
    out = {}
    if "from_m" in elevation and elevation["from_m"] not in (None, ""):
        out["LocElevationASLFromMt"] = elevation["from_m"]
    if "to_m" in elevation and elevation["to_m"] not in (None, ""):
        out["LocElevationASLToMt"] = elevation["to_m"]
    if "from_ft" in elevation and elevation["from_ft"] not in (None, ""):
        out["LocElevationASLFromFt"] = elevation["from_ft"]
    if "to_ft" in elevation and elevation["to_ft"] not in (None, ""):
        out["LocElevationASLToFt"] = elevation["to_ft"]
    return out


def coord_fields(coords):
    if not coords:
        return {}
    out = {}
    if coords.get("lat") not in (None, ""):
        out["LatLatitudeDecimal_nesttab"] = coords["lat"]
    if coords.get("lon") not in (None, ""):
        out["LatLongitudeDecimal_nesttab"] = coords["lon"]
    return out


def node_key(classification, rank, name, parent_ref, coords, elevation):
    """Stable dedup key for a new node."""
    c = (coords or {}).get("lat"), (coords or {}).get("lon")
    e = tuple(sorted((elevation or {}).items()))
    return (classification, rank, (name or "").strip(), str(parent_ref), c, e)


def build_batches(chains_data):
    """Walk each chain, assign depths relative to the known parent IRN, and
    return a list of per-depth batches. Each batch entry has a stable id so
    later batches can reference it via placeholder."""
    classification = chains_data.get("classification", "Terrestrial")
    chains = chains_data.get("chains", [])

    # rows keyed by depth. Within a depth, we dedup by node_key (so the same
    # Village is only created once even if referenced by many chains).
    depth_rows = {}          # depth -> list of row dicts
    dedup_by_key = {}        # (depth, key) -> row id
    row_id_counter = 0

    # For placeholder resolution: each chain keeps track of the effective
    # parent ref at each step (either a known IRN string or a `__PENDING_Bx_Ry__`).
    for chain in chains:
        parent_ref = chain.get("parent_irn") or ""
        depth = 0
        for node in chain.get("nodes", []):
            status = node.get("status", "needs_creation")
            rank = node["rank"]
            name = node.get("name") or ""

            if status == "exists":
                # Node already exists in Emu — becomes the parent_ref for the next node.
                parent_ref = str(node.get("irn") or "")
                continue

            depth += 1
            coords = node.get("coords")
            elevation = node.get("elevation")
            key = node_key(classification, rank, name, parent_ref, coords, elevation)
            existing_row_id = dedup_by_key.get((depth, key))
            if existing_row_id is not None:
                # Reuse existing row for next node's parent placeholder
                parent_ref = f"__PENDING_B{depth}_R{existing_row_id}__"
                continue

            row_id_counter += 1
            this_id = row_id_counter
            row = {
                "id": this_id,
                "depth": depth,
                "SitRecordClassification": classification,
                "PolPoliticalRank": rank,
                "PolLocality": name,
                "PolParentRef.irn": parent_ref,
            }
            row.update(elevation_fields(elevation))
            row.update(coord_fields(coords))

            depth_rows.setdefault(depth, []).append(row)
            dedup_by_key[(depth, key)] = this_id
            parent_ref = f"__PENDING_B{depth}_R{this_id}__"

    # Build batches in ascending depth order
    batches = []
    for depth in sorted(depth_rows.keys()):
        batches.append({"depth": depth, "rows": depth_rows[depth]})
    return batches


def write_csv(rows, output_path):
    # Drop columns with no data
    active = [c for c in UPLOAD_COLUMNS
              if any(r.get(c) not in (None, "") for r in rows)]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(active)
        for r in rows:
            w.writerow([r.get(c, "") if r.get(c) is not None else "" for c in active])
    return len(rows), active


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <chains.json> <output_dir>")
        sys.exit(1)

    chains_path = sys.argv[1]
    output_dir = sys.argv[2]

    with open(chains_path) as f:
        chains_data = json.load(f)

    os.makedirs(output_dir, exist_ok=True)

    batches = build_batches(chains_data)
    if not batches:
        print("No new sites to upload (all chains already resolved).")
        return

    meta = {
        "classification": chains_data.get("classification", "Terrestrial"),
        "primary_coords": chains_data.get("primary_coords", True),
        "batches": [],
    }

    for i, batch in enumerate(batches, 1):
        out_path = os.path.join(output_dir, f"sites_upload_batch_{i}.csv")
        n, active = write_csv(batch["rows"], out_path)
        print(f"Batch {i} (depth {batch['depth']}): {n} rows -> {out_path}")
        meta["batches"].append({
            "batch": i,
            "depth": batch["depth"],
            "csv": os.path.basename(out_path),
            "columns": active,
            "rows": [
                {
                    "id": r["id"],
                    "PolPoliticalRank": r["PolPoliticalRank"],
                    "PolLocality": r["PolLocality"],
                    "PolParentRef.irn": r["PolParentRef.irn"],
                }
                for r in batch["rows"]
            ],
        })

    meta_path = os.path.join(output_dir, "upload_metadata.json")
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2, default=str)
    print(f"Metadata -> {meta_path}")

    # Warn about placeholders so user knows they must be substituted
    pending = sum(
        1
        for b in batches
        for r in b["rows"]
        if str(r.get("PolParentRef.irn", "")).startswith("__PENDING_")
    )
    if pending:
        print(
            f"\nNote: {pending} row(s) reference a parent IRN that will only exist "
            f"after an earlier batch is uploaded. These appear as placeholders "
            f"(`__PENDING_Bx_Ry__`). After each batch is uploaded, collect the new "
            f"IRNs and substitute them before uploading the next batch."
        )


if __name__ == "__main__":
    main()
