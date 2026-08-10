#!/bin/bash
# Generate an aggregate md5 checksum file for each given data folder.
#
# Usage: generate_checksums.sh <folder> [<folder> ...]
#
# Writes <folder>/checksums.md5 with one line per file, paths relative to the
# folder root (./sub/dir/file), then makes it read-only. Folders that already
# have a checksums.md5 are skipped, so this is safe to rerun.
#
# Verify later with:  cd <folder> && md5sum --check --strict checksums.md5
#
# Correctness notes (do not "simplify" these away):
#  * Each parallel worker writes its OWN output file. Appending to a single
#    file from several processes is not atomic on NFS and silently produces
#    interleaved, corrupt lines.
#  * The checksum file is written only if the entry count matches the file
#    count, so a failed worker leaves nothing behind rather than a partial
#    file that would later "verify" a subset and appear healthy.
set -uo pipefail

JOBS=${HASH_JOBS:-6}
CONFIG=${SECURE_BACKUP_CONFIG:-$HOME/.config/secure_raw_data_backup/config.sh}
[[ -r "$CONFIG" ]] && source "$CONFIG"
JOBS=${HASH_JOBS:-$JOBS}

if (( $# == 0 )); then
    echo "Usage: $(basename "$0") <folder> [<folder> ...]" >&2
    exit 1
fi

nfail=0
for arg in "$@"; do
    dir=$(readlink -f "$arg")
    if [[ ! -d "$dir" ]]; then
        echo "ERROR: not a directory: $arg" >&2; nfail=$((nfail+1)); continue
    fi
    out="$dir/checksums.md5"
    if [[ -e "$out" ]]; then
        echo "SKIP: $out already exists"; continue
    fi
    if [[ ! -w "$dir" ]]; then
        echo "ERROR: $dir is not writable (owned by $(stat -c %U "$dir")); cannot write checksums there" >&2
        nfail=$((nfail+1)); continue
    fi

    echo "=== $dir ($(du -sh "$dir" | cut -f1)) — $(date '+%H:%M:%S')"
    tmp=$(mktemp -d)
    ( cd "$dir" && find . -type f ! -name '*.md5' -print0 | sort -z ) > "$tmp/list"
    n=$(tr -cd '\0' < "$tmp/list" | wc -c)
    if (( n == 0 )); then
        echo "  WARNING: no files to hash in $dir" >&2; rm -rf "$tmp"; continue
    fi

    # A newline-delimited split is only safe if no filename contains a newline.
    if (( $(tr '\0' '\n' < "$tmp/list" | wc -l) != n )); then
        echo "  ERROR: a filename in $dir contains a newline; refusing to hash" >&2
        rm -rf "$tmp"; nfail=$((nfail+1)); continue
    fi

    echo "  hashing $n files with $JOBS parallel workers..."
    split -n r/"$JOBS" -d --additional-suffix=.chunk <(tr '\0' '\n' < "$tmp/list") "$tmp/c"

    pids=()
    for c in "$tmp"/c*.chunk; do
        ( cd "$dir" && tr '\n' '\0' < "$c" | xargs -0 -r md5sum > "$c.md5sums" ) &
        pids+=($!)
    done
    rc=0
    for p in "${pids[@]}"; do wait "$p" || rc=1; done
    if (( rc != 0 )); then
        echo "  ERROR: hashing failed; not writing $out" >&2
        rm -rf "$tmp"; nfail=$((nfail+1)); continue
    fi

    cat "$tmp"/c*.chunk.md5sums | sort -k2 > "$tmp/all"
    got=$(wc -l < "$tmp/all")
    if (( got != n )); then
        echo "  ERROR: hashed $got of $n files; not writing $out" >&2
        rm -rf "$tmp"; nfail=$((nfail+1)); continue
    fi

    cp "$tmp/all" "$out"
    chmod 444 "$out"
    echo "  WROTE $out ($got entries) — $(date '+%H:%M:%S')"
    rm -rf "$tmp"
done

(( nfail == 0 )) || { echo "Finished with $nfail failure(s)" >&2; exit 1; }
echo "All done — $(date '+%H:%M:%S')"
