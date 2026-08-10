# Verifying an archive

Four checks, in increasing cost and increasing strength. Know what each one
proves — it is easy to run the cheap ones and feel finished.

| Check | Cost | Proves | Does **not** prove |
|---|---|---|---|
| 1. `head-object` | free | The object exists, its size and storage class are right, S3 holds a checksum | Nothing about contents |
| 2. Manifest diff | free | Every intended file and byte size went in | That the bytes are correct or the stream is readable |
| 3. Restore + `tar -t` | retrieval + egress | The tar stream is intact and every member is listable | Per-file byte correctness |
| 4. Restore + extract + `md5sum --check` | retrieval + egress + scratch | Every byte of every file survived the round trip | — |

## 1. Object metadata

```bash
aws --profile "$PROFILE" s3api head-object \
  --bucket "$BUCKET" --key "$KEY" --checksum-mode ENABLED
```

Expect `ContentLength` slightly **above** the on-disk folder size — tar adds a
512-byte header per member plus padding. Overhead of ~0.0002% is normal;
overhead that looks like compression (a *smaller* object) means something is
wrong. Record `ChecksumCRC64NVME`: S3 computed it on ingest, so it is
independent evidence of what arrived.

## 2. Manifest diff

The manifest lives in Standard, so this costs nothing and needs no restore.

```bash
aws --profile "$PROFILE" s3 cp "s3://$BUCKET/$KEY.manifest.txt" /tmp/m.txt --quiet
( cd "$STORAGE_ROOT" && find "$REL" -type f -printf '%s\t%p\n' | sort -k2 ) > /tmp/d.txt
diff /tmp/m.txt /tmp/d.txt && echo "MANIFEST MATCHES ON-DISK EXACTLY"
```

Any diff means the local folder changed after archiving, or the archive is
incomplete. Investigate before concluding which.

## 3. Restore test — the one that actually matters

Do this **once on your smallest folder** before large data depends on the
pipeline. It is the only test that exercises tar, the network, multipart
reassembly, and cold storage together.

```bash
# Request retrieval (Bulk = cheapest, up to 48 h; Standard ≈ 12 h)
aws --profile "$PROFILE" s3api restore-object \
  --bucket "$BUCKET" --key "$KEY" \
  --restore-request '{"Days":7,"GlacierJobParameters":{"Tier":"Bulk"}}'

# Poll. ongoing-request="true" means still thawing.
aws --profile "$PROFILE" s3api head-object \
  --bucket "$BUCKET" --key "$KEY" --query Restore --output text
# ready looks like: ongoing-request="false", expiry-date="..."
```

`Days` is how long the readable copy persists — give yourself a window wider
than the wait so it cannot expire mid-verification.

Once warm, list the archive contents **without writing 48 GB to disk**:

```bash
aws --profile "$PROFILE" s3 cp "s3://$BUCKET/$KEY" - | tar -t > /tmp/members.txt
wc -l /tmp/members.txt
```

Compare against the manifest (the manifest holds files only; tar lists
directories too, so filter):

```bash
grep -v '/$' /tmp/members.txt | sort > /tmp/a
cut -f2 /tmp/m.txt | sort > /tmp/b
diff /tmp/a /tmp/b && echo "ALL MEMBERS PRESENT"
```

A clean `tar -t` over the whole stream is strong evidence: tar detects
truncation and header corruption, so listing every member to the end means the
object reassembled correctly.

## 4. Full byte-level round trip

For a small folder, go all the way — this is the only check that verifies
content rather than structure:

```bash
mkdir -p /scratch/verify && cd /scratch/verify
aws --profile "$PROFILE" s3 cp "s3://$BUCKET/$KEY" - | tar -x
cd "$REL" && md5sum --check --strict checksums.md5
```

Every line `OK` means the bytes that come back out are the bytes that went in.
Delete the scratch copy afterwards.

## What checksums do and do not establish

Checksums generated at archive time prove integrity **from that moment
forward** — through upload, storage, and restore. They cannot prove the files
match what the instrument or sequencing provider produced. If the provider
supplied original `.md5` files, those are the provenance record: keep them,
verify against them, and never regenerate over them. When a dataset arrived
without checksums, say so plainly in the report rather than implying the
archive is provenance-verified.

## Re-verification over time

Bit rot in S3 is not the realistic threat — S3 is designed for 11 nines of
durability and repairs internally. The realistic threats are a broken *process*
(archives that were never extractable), an expired or misconfigured credential,
and a bucket policy that silently changed. So re-verify by re-running checks 1
and 2 across all archives periodically (free), and rotate check 3 through one
archive at a time rather than re-reading everything.

```bash
# Cheap audit of every archive: object present + manifest marker present
aws --profile "$PROFILE" s3 ls "s3://$BUCKET/" --recursive | grep -c '\.tar$'
aws --profile "$PROFILE" s3 ls "s3://$BUCKET/" --recursive | grep -c '\.manifest\.txt$'
```

Those two counts should be equal. A `.tar` without a matching
`.manifest.txt` is an interrupted upload, not a backup.
