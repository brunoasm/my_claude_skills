#!/bin/bash
# Back up raw data folders to S3 cold storage as streamed tarballs.
#
# Usage:   backup_to_cloud.sh [--dry-run|-n] [<folder> ...]
# Example: backup_to_cloud.sh 2026/run-1353976626
#
# Config is read from ~/.config/secure_raw_data_backup/config.sh (override the
# path with SECURE_BACKUP_CONFIG). Required: STORAGE_ROOT, BUCKET, PROFILE.
# Optional: STORAGE_CLASS (default DEEP_ARCHIVE).
#
# --dry-run reports what a real run would do without uploading, prompting, or
# recording decisions.
#
# With no arguments, scans STORAGE_ROOT two levels deep (e.g. <year>/<run>/) for
# candidate folders. Each folder that is not yet backed up and has no recorded
# decision is asked about once:
#   y = back up (now and on every future run)
#   n = never back up
#   s = skip for now, ask again next run
# y/n answers are stored in .backup_decisions.tsv under STORAGE_ROOT.
# All prompts happen up front, so the uploads then run unattended.
#
# For each folder to back up:
#   1. Skips it if already backed up (checks for the completion marker on S3).
#   2. Verifies every *.md5 checksum file inside the folder before archiving,
#      and refuses to upload on any mismatch.
#   3. Streams a tarball straight to s3://$BUCKET/<rel>.tar (no local temp
#      copy; the AWS CLI verifies the upload end-to-end with a CRC64NVME
#      full-object checksum).
#   4. Uploads <key>.meta.txt (ingest checksum, size, file count) and then
#      <key>.manifest.txt (every path and size) to Standard, so contents are
#      readable without paying for a restore. The manifest is written LAST and
#      marks a completed backup, so an interrupted upload is retried next run.
#
# Run it detached so a Ctrl-C or dropped SSH session cannot kill a long upload:
#   nohup backup_to_cloud.sh > backup_$(date -Idate).log 2>&1 < /dev/null &
set -uo pipefail

CONFIG=${SECURE_BACKUP_CONFIG:-$HOME/.config/secure_raw_data_backup/config.sh}
if [[ ! -r "$CONFIG" ]]; then
    echo "ERROR: no config at $CONFIG (copy references/config.example.sh)" >&2
    exit 1
fi
source "$CONFIG"

: "${STORAGE_CLASS:=DEEP_ARCHIVE}"
for v in STORAGE_ROOT BUCKET PROFILE; do
    [[ -n "${!v:-}" ]] || { echo "ERROR: $v not set in $CONFIG" >&2; exit 1; }
done
DECISIONS="$STORAGE_ROOT/.backup_decisions.tsv"

DRYRUN=0
while [[ "${1:-}" == -* ]]; do
    case $1 in
        -h|--help) grep '^#' "$0" | head -35; exit 0 ;;
        -n|--dry-run) DRYRUN=1; shift ;;
        *) echo "ERROR: unknown option: $1" >&2; exit 1 ;;
    esac
done

# Activate the conda env holding the AWS CLI, if configured.
if [[ -n "${CONDA_SH:-}" && -n "${AWS_ENV:-}" ]]; then
    source "$CONDA_SH"
    conda activate "$AWS_ENV"
fi

s3() { aws --profile "$PROFILE" "$@"; }
decision_for() { awk -F'\t' -v r="$1" '$2 == r { print $1 }' "$DECISIONS" 2>/dev/null | tail -1; }

candidates=()
if (( $# > 0 )); then
    candidates=("$@")
else
    for d in "$STORAGE_ROOT"/*/*/; do
        [[ -d "$d" ]] && candidates+=("$d")
    done
    if (( ${#candidates[@]} == 0 )); then
        echo "No candidate folders found under $STORAGE_ROOT/*/*/" >&2
        exit 1
    fi
fi

# Pass 1: validate paths and gather decisions before any long upload starts.
queue=()
nfail=0
for arg in "${candidates[@]}"; do
    dir=$(readlink -f "$arg")
    if [[ ! -d "$dir" ]]; then
        echo "ERROR: not a directory: $arg" >&2; nfail=$((nfail+1)); continue
    fi
    rel=${dir#"$STORAGE_ROOT"/}
    if [[ "$rel" == "$dir" || -z "$rel" ]]; then
        echo "ERROR: $dir is not inside $STORAGE_ROOT" >&2; nfail=$((nfail+1)); continue
    fi
    case $(decision_for "$rel") in
        yes) queue+=("$rel"); continue ;;
        no)  echo "SKIP: $rel (marked 'no' in $(basename "$DECISIONS"))"; continue ;;
    esac
    if s3 s3api head-object --bucket "$BUCKET" --key "$rel.tar.manifest.txt" >/dev/null 2>&1; then
        echo "SKIP: already backed up (s3://$BUCKET/$rel.tar)"
        continue
    fi
    if (( DRYRUN )); then
        echo "NEW: $rel ($(du -sh "$dir" | cut -f1)) — a real run would ask whether to back it up"
        continue
    fi
    if [[ ! -t 0 ]]; then
        echo "SKIP: $rel is new; run interactively to decide whether to back it up" >&2
        continue
    fi
    while true; do
        read -r -p "Back up $rel ($(du -sh "$dir" | cut -f1))? [y]es / [n]ever / [s]kip for now: " ans
        case $ans in
            y|Y) printf 'yes\t%s\t%s\n' "$rel" "$(date -Idate)" >> "$DECISIONS"; queue+=("$rel"); break ;;
            n|N) printf 'no\t%s\t%s\n'  "$rel" "$(date -Idate)" >> "$DECISIONS"; break ;;
            s|S) break ;;
        esac
    done
done

# Pass 2: upload everything queued.
for rel in "${queue[@]}"; do
    dir="$STORAGE_ROOT/$rel"
    key="$rel.tar"
    echo "=== $rel ==="

    if s3 s3api head-object --bucket "$BUCKET" --key "$key.manifest.txt" >/dev/null 2>&1; then
        echo "SKIP: already backed up (s3://$BUCKET/$key)"
        continue
    fi
    if s3 s3api head-object --bucket "$BUCKET" --key "$key" >/dev/null 2>&1; then
        echo "NOTE: tarball exists but no completion marker (previous run interrupted?); re-uploading as a new version"
    fi

    if (( DRYRUN )); then
        echo "WOULD UPLOAD: $rel ($(du -sh "$dir" | cut -f1)) to s3://$BUCKET/$key ($STORAGE_CLASS)"
        continue
    fi

    echo "Verifying md5 checksums..."
    nmd5=0 badmd5=0
    while IFS= read -r -d '' m; do
        nmd5=$((nmd5+1))
        if ! (cd "$(dirname "$m")" && md5sum --check --quiet --strict "$(basename "$m")"); then
            echo "MD5 FAIL: $m" >&2; badmd5=1
        fi
    done < <(find "$dir" -type f -name '*.md5' -print0)
    if (( badmd5 )); then
        echo "ERROR: checksum failure in $rel; NOT uploading" >&2; nfail=$((nfail+1)); continue
    fi
    if (( nmd5 == 0 )); then
        echo "WARNING: no .md5 files found in $rel; contents not verified" >&2
        echo "         run generate_checksums.sh first for a verifiable archive" >&2
    else
        echo "OK: $nmd5 md5 file(s) verified"
    fi

    bytes=$(du -sb "$dir" | cut -f1)
    # tar adds headers/padding; overestimate so multipart part-sizing never runs short
    expected=$(( bytes + bytes/20 + 10485760 ))
    echo "Uploading $(numfmt --to=iec "$bytes") to s3://$BUCKET/$key ($STORAGE_CLASS)..."
    if ! tar -C "$STORAGE_ROOT" -cf - "$rel" | \
         s3 s3 cp - "s3://$BUCKET/$key" --expected-size "$expected" --storage-class "$STORAGE_CLASS"; then
        echo "ERROR: upload of $rel failed; rerun to retry" >&2; nfail=$((nfail+1)); continue
    fi

    # Record what S3 actually ingested, so a later restore can be checked
    # against it without trusting anything computed at restore time.
    size=$(s3 s3api head-object --bucket "$BUCKET" --key "$key" --query ContentLength --output text)
    crc=$(s3 s3api head-object --bucket "$BUCKET" --key "$key" --checksum-mode ENABLED \
              --query ChecksumCRC64NVME --output text 2>/dev/null)
    nfiles=$(find "$dir" -type f | wc -l)

    meta=$(mktemp)
    {
        printf 'source_path\t%s\n' "$dir"
        printf 'archived_utc\t%s\n' "$(date -u -Is)"
        printf 'host\t%s\n' "$(hostname)"
        printf 'storage_class\t%s\n' "$STORAGE_CLASS"
        printf 'local_bytes\t%s\n' "$bytes"
        printf 'object_bytes\t%s\n' "$size"
        printf 'checksum_crc64nvme\t%s\n' "$crc"
        printf 'file_count\t%s\n' "$nfiles"
    } > "$meta"
    if ! s3 s3 cp "$meta" "s3://$BUCKET/$key.meta.txt" --only-show-errors; then
        echo "ERROR: meta upload for $rel failed; rerun to retry" >&2
        rm -f "$meta"; nfail=$((nfail+1)); continue
    fi
    rm -f "$meta"

    # Manifest goes last: its presence is the completion marker.
    manifest=$(mktemp)
    ( cd "$STORAGE_ROOT" && find "$rel" -type f -printf '%s\t%p\n' | sort -k2 ) > "$manifest"
    if ! s3 s3 cp "$manifest" "s3://$BUCKET/$key.manifest.txt" --only-show-errors; then
        echo "ERROR: manifest upload for $rel failed; rerun to retry" >&2
        rm -f "$manifest"; nfail=$((nfail+1)); continue
    fi
    rm -f "$manifest"

    echo "DONE: s3://$BUCKET/$key ($(numfmt --to=iec "$size"), crc64nvme=$crc)"
done

(( nfail == 0 )) || { echo "Finished with $nfail failure(s)" >&2; exit 1; }
echo "All done."
