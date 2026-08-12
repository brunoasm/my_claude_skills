# Bucket setup for write-once raw data archives

One-time setup. Everything here needs **admin** credentials, not the backup
user's — that separation is the point.

Choose a region close to where the data lives, and remember the region is
permanent for the bucket.

## 1. Create the bucket with Object Lock enabled

Object Lock **can only be enabled at creation time**, and it requires
versioning. There is no way to add it to an existing bucket, so get this right
the first time.

```bash
aws s3api create-bucket \
  --bucket my-raw-data-archive \
  --region us-east-2 \
  --create-bucket-configuration LocationConstraint=us-east-2 \
  --object-lock-enabled-for-bucket

aws s3api put-bucket-versioning \
  --bucket my-raw-data-archive \
  --versioning-configuration Status=Enabled
```

## 2. Set a default retention rule

```bash
aws s3api put-object-lock-configuration \
  --bucket my-raw-data-archive \
  --object-lock-configuration '{
    "ObjectLockEnabled": "Enabled",
    "Rule": { "DefaultRetention": { "Mode": "GOVERNANCE", "Years": 5 } }
  }'
```

**Understand the two modes before choosing.** This is the decision people
regret:

| Mode | Who can remove the lock early | Use when |
|---|---|---|
| `GOVERNANCE` | An admin holding `s3:BypassGovernanceRetention` | You want protection against accident, malware, and stolen server credentials — but a deliberate admin action can still fix a mistake. **Default choice.** |
| `COMPLIANCE` | **Nobody, including the account root, until retention expires** | A regulator or grant requires provable immutability, and you accept that a wrongly-uploaded 10 TB object is billed for the full term with no recourse. |

Retention is per-object-version, applied at upload from the bucket default.
Lengthening it later is allowed; shortening it is not (except by governance
bypass). A 5-year `GOVERNANCE` default is a sane starting point.

### Governance mode and the root user

**Default: use `GOVERNANCE` and leave the root user able to delete.** Under
governance, destroying a locked version requires all of:

- the `x-amz-bypass-governance-retention: true` header,
- the `s3:BypassGovernanceRetention` permission,
- `s3:DeleteObjectVersion` with an explicit `--version-id`.

Root holds every permission implicitly and cannot be restrained by IAM
identity policies, so root can do this. That is the point of the mode, not a
gap: it protects against accident, malware, and stolen server credentials,
while keeping a deliberate human able to correct a mistaken multi-terabyte
upload. Do not "harden" this away by reflex — an archive nobody can fix is a
liability of its own.

Two behaviours that are easy to misread:

- **A DELETE without a version ID is not destruction.** In a versioned bucket
  it creates a *delete marker*: the object vanishes from `s3 ls`, but the
  version and its bytes remain, still under retention and still billed. Remove
  the marker and it is back. Check `list-object-versions` before concluding
  anything was lost.
- **Lowering the bucket default retention does not unlock existing archives.**
  Retention is stamped per object version at upload; changing the default
  affects only future uploads.

Only tighten beyond this when there is a stated requirement (a regulator, a
grant, a documented threat model). The options, strongest last:

| Control | Effect on root | Limitation |
|---|---|---|
| Bucket policy `Deny` on `s3:BypassGovernanceRetention` | Applies to root — resource policies bind root | Root can rewrite the policy; stops accidents, not intent |
| Legal Hold per object | Independent of retention; blocks deletion until removed | Removable with `s3:PutObjectLegalHold` |
| SCP in an AWS Organization | The real control over a member account's root | Needs Organizations; bucket must be in a member, not management, account |
| `COMPLIANCE` mode | Nobody, including root, until expiry | A wrongly-uploaded 10 TB object is billed for the full term with no recourse |

And the limit no in-account control fixes: **closing the account, or losing it
for non-payment, destroys the data regardless of mode.** Object Lock protects
against deletion, not against loss of the account. If that matters, the answer
is a copy in a separate account or provider, not a stronger lock.

### Confirm the lock is real

A retention rule you never verified is an assumption. After the first upload,
check with admin credentials that retention actually landed on the object — if
the bucket default was never configured, nothing is locked at all:

```bash
aws s3api get-object-lock-configuration --bucket my-raw-data-archive
aws s3api get-object-retention --bucket my-raw-data-archive --key <key>
```

Expect `Mode: GOVERNANCE` and a `RetainUntilDate` the full retention period
out. Note that the write-only backup user cannot read these — they need admin
credentials.

## 3. Abort orphaned multipart uploads automatically

A failed streaming upload leaves parts that are **billed as storage but do not
appear in `s3 ls`**. Without this rule they accumulate invisibly.

```bash
aws s3api put-bucket-lifecycle-configuration \
  --bucket my-raw-data-archive \
  --lifecycle-configuration '{
    "Rules": [{
      "ID": "abort-incomplete-multipart",
      "Status": "Enabled",
      "Filter": { "Prefix": "" },
      "AbortIncompleteMultipartUpload": { "DaysAfterInitiation": 7 }
    }]
  }'
```

Check for existing orphans any time an upload dies:

```bash
aws s3api list-multipart-uploads --bucket my-raw-data-archive
```

Note the interaction with Object Lock: `AbortIncompleteMultipartUpload` works
on parts (not yet objects, so not yet locked), but **expiration rules cannot
delete locked object versions** — do not expect a lifecycle rule to clean up
archives before their retention ends.

## 4. Block public access

```bash
aws s3api put-public-access-block \
  --bucket my-raw-data-archive \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

## 5. Create a write-only backup user

The credentials that sit on the data server should be able to add archives and
read metadata, and nothing else. If that server is compromised, the attacker
cannot destroy the backups — which is the whole reason the backup exists.

```bash
aws iam create-user --user-name backup-server

cat > /tmp/backup-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "WriteArchivesAndReadMetadata",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:GetObjectAttributes",
        "s3:ListBucket",
        "s3:ListBucketMultipartUploads",
        "s3:ListMultipartUploadParts",
        "s3:AbortMultipartUpload"
      ],
      "Resource": [
        "arn:aws:s3:::my-raw-data-archive",
        "arn:aws:s3:::my-raw-data-archive/*"
      ]
    }
  ]
}
EOF

aws iam put-user-policy --user-name backup-server \
  --policy-name backup-write-only --policy-document file:///tmp/backup-policy.json

aws iam create-access-key --user-name backup-server
```

Deliberately absent: `s3:DeleteObject*`, `s3:BypassGovernanceRetention`,
`s3:PutObjectRetention`, `s3:PutBucketPolicy`, and any `iam:*`.

**Also absent: `s3:RestoreObject`.** This is a real tradeoff, not an
oversight. Leaving it out means the server cannot even begin a retrieval; it
also means verification and restores need admin credentials, which is
inconvenient exactly when you are stressed. Recommended: grant it as a
*separate* inline policy so it can be reasoned about and revoked on its own.
Retrieval only creates a temporary readable copy — it cannot alter or delete
anything, so it does not weaken the write-once guarantee.

```bash
cat > /tmp/restore-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "AllowGlacierRestoreOnly",
    "Effect": "Allow",
    "Action": "s3:RestoreObject",
    "Resource": "arn:aws:s3:::my-raw-data-archive/*"
  }]
}
EOF

aws iam put-user-policy --user-name backup-server \
  --policy-name backup-restore --policy-document file:///tmp/restore-policy.json
```

## 6. Install the profile on the data server

```bash
aws configure --profile my-backup-profile   # paste the access key + region
aws --profile my-backup-profile sts get-caller-identity
```

Then confirm the guardrail actually holds — a delete attempt **should** fail:

```bash
aws --profile my-backup-profile s3api delete-object \
  --bucket my-raw-data-archive --key does-not-exist
# expect: AccessDenied
```

Test the write-once property for real before trusting it. A lock you never
tested is a lock you are assuming.

Upload a small throwaway object first (a few KB under a `_test/` prefix), then
run this from an admin/root shell. Substitute the real version ID — pasting a
`<PLACEHOLDER>` into bash fails with `syntax error near unexpected token
'newline'`, because `<` is read as input redirection.

```bash
aws s3api list-object-versions --bucket my-raw-data-archive --prefix _test/

# Is retention actually applied?
aws s3api get-object-retention --bucket my-raw-data-archive \
  --key _test/probe.bin --version-id 'REAL_VERSION_ID'
#   => {"Retention": {"Mode": "GOVERNANCE", "RetainUntilDate": "2031-..."}}

# An ordinary version delete MUST be refused, even for root
aws s3api delete-object --bucket my-raw-data-archive \
  --key _test/probe.bin --version-id 'REAL_VERSION_ID'
#   => AccessDenied ... object protected by object lock

# Only a deliberate bypass succeeds
aws s3api delete-object --bucket my-raw-data-archive \
  --key _test/probe.bin --version-id 'REAL_VERSION_ID' \
  --bypass-governance-retention
#   => {"VersionId": "REAL_VERSION_ID"}   (permanent — no undo)
```

Those outputs are what a correctly configured bucket produces. Interpretation:

- **Retention empty or `NoSuchObjectLockConfiguration`** → the bucket default
  was not in place when that object was written. Nothing is locked. Fix before
  archiving anything real.
- **The no-bypass delete succeeds** → same conclusion, and more urgent.
- **The bypass delete fails** → the identity lacks
  `s3:BypassGovernanceRetention`. Fine for a scoped user; worth knowing before
  an incident if it is the identity you would rely on to fix a mistake.

Note that bypass is triggered by the `x-amz-bypass-governance-retention: true`
header, not by permission alone — which is why the no-bypass delete is refused
even for root, and why the test is meaningful from any privileged identity.

Deleting a specific version removes it outright and leaves **no delete
marker**. Only a version-less `delete-object` creates a marker.

Deletion does not require a restore, even for `DEEP_ARCHIVE` objects — only
reading does.

## 7. Where this fits in 3-2-1

This bucket is one off-site copy. It is not a complete backup strategy: the
local copy is copy one, this is copy two, and a locked cloud archive with a
5-year retention is specifically protection against deletion — accidental,
malicious, or ransomware — rather than against your own bad data. Verify with a
restore (see `verification.md`), because an untested archive is an assumption.
