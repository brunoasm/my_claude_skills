#!/usr/bin/env python3
"""Keep dated copies of working files that collaborators edit in place.

In a shared (synced) proposal folder, people often edit `Document_v2.docx`
directly instead of saving `Document_v3.docx`. This script copies every working
file whose content changed since its last snapshot into
<dest>/<YYYY-MM-DD_HHMM>/<same relative path>, and appends one line per copied
file to <dest>/LOG.md. Unchanged files are skipped (compared by SHA-256), so
running it often is cheap.

Usage:
  python3 snapshot.py SHARED_DIR DEST_DIR [--note "text"] [--tz America/Chicago]
                      [--skip 01_guidelines --skip 98_bibliography ...]
                      [--ext .docx --ext .xlsx ...]

Defaults: skips 01_guidelines, 98_bibliography, 99_archive, 04_final_submission;
copies .docx .xlsx .pptx .md .txt .csv .pdf; ignores Word lock files (~$...)
and hidden files. DEST_DIR should not be visible to collaborators (keep it
outside the shared folder) so nobody edits a snapshot by mistake.

Exit code 0 always unless the folders are missing; prints what was copied.
Standard library only (Python 3.9+).
"""
import argparse
import datetime
import hashlib
import json
import os
import shutil
import sys

DEFAULT_SKIP = ['01_guidelines', '98_bibliography', '99_archive', '04_final_submission']
DEFAULT_EXT = ['.docx', '.xlsx', '.pptx', '.md', '.txt', '.csv', '.pdf']


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('shared', help='folder to snapshot (the shared proposal folder)')
    ap.add_argument('dest', help='where snapshots go (keep it outside the shared folder)')
    ap.add_argument('--note', default='', help='note written to the log for this run')
    ap.add_argument('--tz', default=None, help='IANA time zone for folder names and times (default: local)')
    ap.add_argument('--skip', action='append', help='top-level subfolder to skip (repeatable)')
    ap.add_argument('--ext', action='append', help='file extension to include (repeatable)')
    a = ap.parse_args()

    shared = os.path.abspath(a.shared)
    dest = os.path.abspath(a.dest)
    if not os.path.isdir(shared):
        sys.exit(f'Shared folder not found: {shared}')
    if dest == shared or dest.startswith(shared + os.sep):
        sys.exit('DEST_DIR must be outside the shared folder.')
    os.makedirs(dest, exist_ok=True)

    tz = None
    if a.tz:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(a.tz)
    now = datetime.datetime.now(tz) if tz else datetime.datetime.now()
    stamp = now.strftime('%Y-%m-%d_%H%M')
    if os.path.exists(os.path.join(dest, stamp)):  # second run in the same minute
        n = 2
        while os.path.exists(os.path.join(dest, f'{stamp}-{n}')):
            n += 1
        stamp = f'{stamp}-{n}'
    skip = set(a.skip or DEFAULT_SKIP)
    exts = {e.lower() if e.startswith('.') else '.' + e.lower() for e in (a.ext or DEFAULT_EXT)}

    state_path = os.path.join(dest, 'state.json')
    log_path = os.path.join(dest, 'LOG.md')
    state = json.load(open(state_path)) if os.path.exists(state_path) else {}

    copied = []
    for d, dirs, files in os.walk(shared):
        rel_d = os.path.relpath(d, shared)
        if rel_d.split(os.sep)[0] in skip:
            dirs[:] = []
            continue
        dirs[:] = [x for x in dirs if not x.startswith('.')]
        for f in sorted(files):
            if f.startswith(('~$', '.')) or os.path.splitext(f)[1].lower() not in exts:
                continue
            p = os.path.join(d, f)
            rel = os.path.relpath(p, shared)
            try:
                h = sha256(p)
            except OSError as e:  # e.g. cloud placeholder not downloaded
                print(f'  could not read {rel}: {e}')
                continue
            if state.get(rel, {}).get('sha') == h:
                continue
            out = os.path.join(dest, stamp, rel)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            shutil.copy2(p, out)
            mt = os.path.getmtime(p)
            mtime = (datetime.datetime.fromtimestamp(mt, tz) if tz else datetime.datetime.fromtimestamp(mt)).strftime('%Y-%m-%d %H:%M')
            state[rel] = {'sha': h, 'snapshot': stamp, 'mtime': mtime}
            copied.append((rel, mtime, os.path.getsize(p), h[:10]))

    if copied:
        new = not os.path.exists(log_path)
        with open(log_path, 'a') as L:
            if new:
                L.write('# Snapshot log\n\nOne line per file copied. A file appears again only when its content changed.\n\n'
                        '| Snapshot | File | Last modified | Bytes | SHA-256 (first 10) | Note |\n|---|---|---|---|---|---|\n')
            for rel, mt, sz, h in copied:
                L.write(f'| {stamp} | {rel} | {mt} | {sz} | {h} | {a.note} |\n')
        with open(state_path, 'w') as S:
            json.dump(state, S, indent=1)
        print(f'{len(copied)} file(s) copied to {os.path.join(dest, stamp)}')
        for c in copied:
            print('  ', c[0])
    else:
        print('No changes since last snapshot.')


if __name__ == '__main__':
    main()
