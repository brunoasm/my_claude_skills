# Cost model

Order-of-magnitude figures for `us-east-*` as of 2026. **Always confirm current
rates** at https://aws.amazon.com/s3/pricing/ before quoting numbers to
someone making a spending decision — these move, and regions differ.

## Storage

| Class | ~$/TB/month | Retrieval latency | Min. duration |
|---|---|---|---|
| Standard | ~$23 | instant | none |
| Standard-IA | ~$12.50 | instant | 30 days |
| Glacier Instant Retrieval | ~$4 | milliseconds | 90 days |
| Glacier Flexible Retrieval | ~$3.60 | minutes–hours | 90 days |
| **Deep Archive** | **~$1** | hours | **180 days** |

Minimum duration is the trap: deleting a Deep Archive object after a month is
billed as if it lived 180 days. Irrelevant under a multi-year Object Lock, but
it matters if you are tempted to "try it and clean up".

Deep Archive also adds ~32 KB of billed metadata overhead per object, which is
a strong argument for archiving one tarball per run rather than thousands of
individual files. A 1000-file run stored loose wastes far more on per-object
overhead and request costs than the tar saves in convenience.

## Retrieval

| Tier | Wait | ~$/TB retrieved |
|---|---|---|
| Bulk | up to 48 h | ~$2.50 |
| Standard | up to 12 h | ~$20 |
| Expedited | *not available for Deep Archive* | — |

Retrieval only makes a temporary readable copy; you keep paying archive storage
throughout, plus a small charge for the restored copy while it exists.

## Egress — usually the real cost

Data *out* to the internet is ~$90/TB after the first 100 GB/month free. For
verification and most restores, **egress dominates everything else**.

## Worked examples

**Archiving 3 TB of sequencing runs, kept 5 years:**

- Storage: 3 TB × ~$1/TB/month = **~$3/month**, ~$180 over five years
- Upload: PUT requests are trivial; ingress is free
- Total to keep 3 TB safe for 5 years: **under $200**

Compare with the cost of regenerating the data — a sequencing run is typically
thousands of dollars and, for field-collected specimens, sometimes
irreplaceable at any price. That asymmetry is the entire argument for archiving.

**Verifying one 48 GB archive (the restore test):**

- Bulk retrieval: 0.048 TB × ~$2.50 = **~$0.12**
- Egress to read it here: 0.048 TB × ~$90 = **~$4.30**
- Total: **~$4.50** and up to 48 h of waiting

**Restoring all 3 TB in a real disaster:**

- Bulk retrieval: **~$7.50**
- Egress: 3 TB × ~$90 = **~$270**

That number is worth stating up front when someone asks "what if we lose
everything" — the archive is cheap to keep and meaningfully expensive to pull
back in full. Ways to reduce it: restore only the runs you need (one tarball
per run makes this possible), or process in EC2/Athena in the same region where
egress to the internet never happens.

## Reducing verification cost

- Verify with `tar -t` streamed to stdout instead of extracting — same egress,
  no scratch space.
- Run the read on an EC2 instance in the bucket's region: same-region S3→EC2
  transfer is free, so you pay only retrieval plus instance time. Worth it for
  multi-TB verification, not for a one-off 48 GB check.
- Use ranged GETs to read only part of a tar when spot-checking rather than
  proving the whole stream.
- Lean on the free checks (`head-object`, manifest diff) for routine audits and
  spend egress only on periodic rotating deep verification.

## When cold storage is the wrong answer

Do not archive what you can regenerate cheaply or download again: reference
genomes, public databases, assembled or filtered results, intermediate
pipeline output. Deep Archive is for data that is **raw, irreplaceable, and
unlikely to be read** — that combination is what makes ~$1/TB/month with
hours-long retrieval the right trade.
