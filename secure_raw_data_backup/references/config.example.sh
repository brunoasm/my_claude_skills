# Example config for the secure-raw-data-backup skill.
#
# Copy to ~/.config/secure_raw_data_backup/config.sh and edit. This file is
# sourced by the scripts, so it must be valid bash. Keep it out of any git
# repo — it names your bucket and paths.
#
#   mkdir -p ~/.config/secure_raw_data_backup
#   cp references/config.example.sh ~/.config/secure_raw_data_backup/config.sh
#   chmod 600 ~/.config/secure_raw_data_backup/config.sh

# Root of the data tree. Candidate folders are found at STORAGE_ROOT/*/*/
# (e.g. 2026/run-name/). Archive keys are paths relative to this root, so the
# bucket layout mirrors the local layout.
STORAGE_ROOT=/path/to/raw_data

# Destination bucket (see references/bucket_setup.md to create one).
BUCKET=my-raw-data-archive

# AWS CLI named profile holding the write-only backup credentials.
PROFILE=my-backup-profile

# DEEP_ARCHIVE  — cheapest, retrieval in hours. Right for "never expect to
#                 read this, but must not lose it".
# GLACIER_IR    — ~4x the storage cost, millisecond retrieval. Use when the
#                 data is occasionally read.
# STANDARD_IA   — for data you actually reach for a few times a year.
STORAGE_CLASS=DEEP_ARCHIVE

# Parallel workers for checksum generation. Past ~6 the shared filesystem,
# not the CPU, is usually the limit.
HASH_JOBS=6

# Optional: if the AWS CLI lives in a conda env rather than on PATH, set both
# and the scripts will activate it.
#CONDA_SH=$HOME/miniconda3/etc/profile.d/conda.sh
#AWS_ENV=awscli
