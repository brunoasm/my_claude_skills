---
name: secure-raw-data-backup
description: "Archive irreplaceable raw data (sequencing runs, imaging, field data) to write-once cloud cold storage — generate checksums, verify before upload, stream a tarball to S3 Deep Archive under Object Lock, and prove the pipeline with a restore test before trusting it at scale. Use when the user asks to back up or archive raw data, set up an immutable/WORM backup, generate md5 checksums for a data folder, or verify/restore an existing archive."
---

# Secure Raw Data Backup

Use this skill when the user wants irreplaceable raw data pushed to durable,
tamper-resistant cloud storage — or wants to verify or restore an archive that
is already there.

Keywords: backup, archive, cold storage, Deep Archive, Glacier, Object Lock,
WORM, immutable, checksums, md5, tarball, restore, retrieval, raw data,
sequencing run, off-site copy, 3-2-1.

## Golden rules (never violate)

1. **Checksums before upload, always.** An archive whose contents were never
   verified is a copy of unknown quality. If the folder has no checksums,
   generate them (Step 2) before archiving.
2. **Never delete or move the local copy** as part of a backup. Backing up and
   freeing space are separate decisions; a fresh archive is not yet a verified
   archive.
3. **Object Lock is irreversible.** Under a governance/compliance retention of
   N years, an uploaded object cannot be deleted or replaced with ordinary
   credentials. Say this out loud before the first upload to a locked bucket,
   every time.
4. **Prove the pipeline on the smallest folder first**, with a real restore
   (Step 6), before committing large data. Cost of being wrong scales with the
   first upload you trust blindly.
5. **Run uploads detached** (`nohup … < /dev/null &`) with a log. A terminal
   Ctrl-C or dropped SSH session kills a multi-hour upload otherwise.
6. **Do not compress already-compressed data.** See Step 3.
7. **Confirm the destination before the first upload** — bucket, prefix,
   storage class, credential profile. Read them from config, never guess.

## Step 0 — Load config (bootstrap if missing)

Read `~/.config/secure_raw_data_backup/config.sh`.

- If it exists, source it: `STORAGE_ROOT`, `BUCKET`, `PROFILE`,
  `STORAGE_CLASS`, `HASH_JOBS`.
- If it is missing, tell the user and walk them through creating it from
  `references/config.example.sh`, asking for each value. Never store bucket
  names, account IDs, or paths in the skill repo.
- If no bucket exists yet, follow `references/bucket_setup.md` — it covers
  Object Lock, versioning, the incomplete-multipart lifecycle rule, and a
  least-privilege IAM policy that can write but not delete.

## Step 1 — Inventory what needs backing up

Survey candidate folders and report a table before touching anything: folder,
size, file count, checksum coverage.

```bash
for d in "$STORAGE_ROOT"/*/*/; do
    n=$(find "$d" -type f ! -name '*.md5' | wc -l)
    e=$(find "$d" -name '*.md5' -exec cat {} + 2>/dev/null | wc -l)
    printf '%-40s %6s files=%-8s md5_entries=%s\n' "${d%/}" "$(du -sh "$d" | cut -f1)" "$n" "$e"
done
```

Interpreting coverage: `md5_entries` counts lines across all `.md5` files, so
it should equal the data-file count. Shortfalls are usually harmless report
files (`.html` data reports, `README.md`, logs, metadata `.csv`) — check which
files are uncovered before assuming a gap matters:

```bash
find "$d" -type f ! -name '*.md5' | while read -r f; do [[ -e "$f.md5" ]] || echo "$f"; done
```

Ask the user which folders are in scope. Data that is derived, reproducible, or
already public (reference genomes, downloaded databases, assembled results) is
usually **not** worth cold-storage money — only raw, irreplaceable data is.

## Step 2 — Freeze, then generate missing checksums

**Freeze the folder read-only BEFORE hashing it.** This ordering is the whole
ballgame, and getting it backwards is the most common way an archive goes
wrong:

```bash
chmod -R a-w "$dir"     # then hash; unfreeze only to write the checksum file
```

Checksums taken while a folder is still being worked in go stale silently.
Worse, `md5sum --check` only validates the files it lists — files *added* after
hashing pass unnoticed, so a stale checksum file is quietly incomplete as well
as wrong. A real instance: a folder was hashed mid-analysis, and by upload time
a tooling settings file had changed and a derived FASTQ had been regenerated at
double its size, while three new files had appeared and one had been deleted.
The upload guard caught the changed file; nothing would have caught the added
ones.

If the folder is still active, say so and offer the choice explicitly: wait
until the work concludes, archive only the immutable raw inputs, or take a
deliberate mid-work snapshot. Do not quietly archive a moving target.


`scripts/generate_checksums.sh <folder> [<folder> ...]`

Writes one aggregate `checksums.md5` at each folder root, with paths relative
to that root (`./sub/dir/file`), then `chmod 444`. Skips folders that already
have one.

Why it is built the way it is — these are correctness requirements, not style:

- **Parallel workers each write their own output file**, concatenated at the
  end. Appending from several processes to one file is not atomic on NFS and
  silently produces interleaved, corrupt lines.
- **The output is written only if the entry count matches the file count**, so
  a failed worker leaves no checksum file rather than a partial one that would
  later "verify" a subset and look fine.
- **Aggregate at the folder root, not sidecars**, when starting from zero: one
  file covers a whole tree and `md5sum --check` run from that root verifies
  everything in one pass. When a folder already uses per-file sidecars, match
  that convention for the few missing files instead of mixing styles.

Two things to tell the user explicitly:

- Hashing reads every byte. Budget from measured throughput — roughly **1 TB
  per hour** with 6 workers on decent shared storage. Run it detached.
- Checksums generated now prove integrity **from now on**. They cannot prove
  the files match what the instrument produced. If the provider supplied
  original checksums, those are the real provenance record — keep them and
  never regenerate over them.

If a folder is not writable (owned by another user), say so and stop for that
folder; do not `chmod` someone else's data.

## Step 3 — Choose the archive format

**Default: uncompressed `tar`.** Justify it if asked, and re-measure rather
than assuming:

```bash
f=<one representative file>; ls -l "$f"; gzip -c "$f" | wc -c
```

On typical raw data (`.fastq.gz`, `.pod5`, `.bam`, `.cram`, `.jpg`, `.zip`)
compression recovers a fraction of a percent — measured **0.004%** on a real
425 MB `fastq.gz`. Against that, `tar.gz` costs:

1. **Throughput** — single-threaded gzip runs ~40–60 MB/s and becomes the
   bottleneck instead of the network.
2. **Fragility** — a compressed stream is one dependency chain, so a single
   bit-flip destroys everything after it. In a plain tar, damage is contained
   to the member it lands in.
3. **Partial restore** — a plain tar supports ranged GETs to pull out one
   sample; `.tar.gz` must be fetched and decompressed whole.

Compression is worth it only for genuinely uncompressed input — raw `.bcl`
runs, `.sam`, `.vcf`, `.fasta`, XML/log trees. Check before deciding.

## Step 4 — Upload

`scripts/backup_to_cloud.sh [--dry-run] [<folder> ...]`

Always start with `--dry-run` and show the user the plan. Then run detached:

```bash
cd "$STORAGE_ROOT" && nohup scripts/backup_to_cloud.sh > backup_$(date -Idate).log 2>&1 < /dev/null &
```

What the script guarantees:

- Verifies every `*.md5` in the folder and **refuses to upload on any
  mismatch**; warns loudly if none exist.
- Streams `tar -cf -` straight to S3 — no local temp copy, so no scratch space
  is needed for a 1 TB folder. `--expected-size` is passed (overestimated) so
  multipart part-sizing never runs short on a large archive.
- Asks about each new folder **up front**, then uploads unattended. Answers
  persist in a decisions file (`yes` = always, `no` = never, `s` = ask again).
- Uploads `<key>.meta.txt` (ingest checksum, size, file count) and then
  `<key>.manifest.txt` (every path and byte size) to **Standard**, so the
  archive's contents are readable instantly without paying for a restore. The
  manifest is written last and acts as the completion marker, so an interrupted
  upload is retried on the next run rather than being mistaken for done.

If a previous run died, check for orphaned multipart uploads before retrying —
they are billed as storage while invisible in `ls`:

```bash
aws --profile "$PROFILE" s3api list-multipart-uploads --bucket "$BUCKET"
```

## Step 5 — Verify the upload (cheap, immediate)

For each uploaded folder:

1. `aws s3api head-object --bucket "$BUCKET" --key "<key>" --checksum-mode ENABLED`
   — confirm size is slightly over the folder size (tar headers and padding),
   storage class is as intended, and record the ingest checksum.
2. Diff `<key>.manifest.txt` against a freshly generated on-disk listing; every
   path and size must match.
3. Confirm the completion marker exists, so a rerun skips the folder instead of
   re-uploading it.

This validates ingest and contents. It does **not** prove the tar stream is
extractable — only Step 6 does.

## Step 6 — Restore test (do this once, on the smallest folder)

See `references/verification.md` for the full procedure. Summary: request a
Bulk retrieval, wait, then stream the restored object through `tar -t` and
compare the member list against the manifest and `checksums.md5`. For full
confidence on a small folder, extract to scratch and run
`md5sum --check checksums.md5` against the extracted copy.

Restore is the only test that exercises the whole path. Do it before large data
depends on the pipeline, and treat "the upload succeeded" as unproven until it
passes.

## Step 7 — Report and record

Tell the user what is now backed up, what it costs per month, what was
excluded and why, and what remains unverified. If the local data is meant to
become read-only after archiving, `chmod` it — but never delete it as part of
this skill.

## Cost awareness

Quote real numbers before spending money; see `references/cost_model.md`. The
shape to remember: Deep Archive storage is ~$1/TB/month, retrieval is cheap,
and **egress is usually the dominant cost of any verification** — a 48 GB
restore-and-read is ~$0.12 Bulk retrieval plus ~$4.30 egress. Retrieval also
has latency measured in hours (Bulk up to 48 h), so plan verification around
the wait rather than blocking on it.

## Available resources

- `references/bucket_setup.md` — bucket creation, Object Lock, versioning,
  lifecycle rules, least-privilege IAM policy, credential profile.
- `references/verification.md` — checksum conventions, restore-test procedure,
  what each check does and does not prove.
- `references/cost_model.md` — storage classes, retrieval tiers, egress, and
  worked examples.
- `references/config.example.sh` — placeholder config layout.
- `scripts/generate_checksums.sh` — parallel checksum generation, NFS-safe.
- `scripts/backup_to_cloud.sh` — verify, stream tarball to cold storage, write
  meta + manifest markers.
