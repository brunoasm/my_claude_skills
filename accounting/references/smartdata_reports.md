# SmartData reports

Reports exported from SmartData (J.P. Morgan) live in
`{working_folder}/{year}/reports/`. They are the authority on what was actually
charged to the p-card: which charges exist, their posted USD amount, and the
international transaction fees.

## Formats, in precedence order

| Source | Filename | Gives | Use |
|---|---|---|---|
| Account Statement, XLSX | `YYYY_MM.xlsx` | posting + transaction date, description, location, **country**, original amount + currency, conversion rate, USD amount, and a summary block of counts and totals | **Primary.** Parse with `scripts/parse_smartdata.py`. |
| Account Statement, PDF | e.g. `Account Statement (Version 2).pdf` | the same fields | Fallback. Read with `pdftotext -layout`; column alignment shifts between pages and long country names wrap, so treat results with suspicion. |
| Expense Inbox print, PDF | e.g. `Expense Management.pdf` | description, posting date, USD amount, **status** (Open/Rejected) | Supplement. No country, currency, or rate, but it reaches past the statement close date and is the only source of status. |

A statement covers a fixed posting-date window, printed in its header and
reported by the parser as `period`. Charges made after the close date are not in
it. The `YYYY_MM.xlsx` filename names the statement month.

## Parsing

Run the parser rather than reading the sheet by hand:

    python3 {skill_dir}/scripts/parse_smartdata.py "{year}/reports/YYYY_MM.xlsx" --json

`{skill_dir}` is the skill's own directory; the report path is relative to the
working folder. See SKILL.md's Session Start for that split.

It returns `period`, `purchases`, `fees`, `pairs`, `problems`,
`international_without_fee`, and `validation`. Amounts are strings in JSON;
compare them as decimals, not floats.

The script absorbs the traps in this export — a header row that moves and
contains embedded newlines, Level-3 addendum rows interleaved with
transactions, whitespace-padded numeric cells, and half-up cent rounding. Do
not re-derive that logic inline.

## Exit codes

Neither script signals "the command failed" through its exit status, so do not
read a non-zero exit that way:

| Script | Code | Meaning |
|---|---|---|
| `parse_smartdata.py` | `0` | parsed, and validation passed |
| `parse_smartdata.py` | `1` | parsed, but **validation failed** — in `--json` mode too. The JSON on stdout is complete and usable; see "Self-validation" below |
| `check_missing_receipts.py` | `0` | always. Findings live in the buckets, never in the exit status |

An actual failure — a missing file, an unreadable workbook — surfaces as a
traceback with no JSON on stdout. That is the only "the command failed" signal.

## The 1% fee

The international transaction fee is **1% of the posted USD amount, rounded
half-up to the cent**. It posts as its own transaction, described
`INTERNATIONAL TRANSACTION`, with blank location and country.

Read the actual fee from the report whenever one covers the charge. Compute 1%
instead when the charge has not posted yet, or when the report covers it but
shows no fee line for it — that is, when the purchase is listed under
`international_without_fee` **and** no unpaired `no_match` fee in the same
report plausibly belongs to it (same transaction date, amount within a cent of
1%). Either way, mark that row as an estimate. The qualifier matters: a fee
whose amount is not exactly 1% half-up lands in `problems` as `no_match` while
its parent lands in `international_without_fee`, so the actual figure is sitting
in the same report and must be used rather than re-derived.

## International detection

A charge is international when its report **Country is present and not
`UNITED STATES`**. When no report covers the charge, fall back to the
heuristic: a non-USD receipt, **or** a vendor outside the US even if billed in
USD — card networks levy the fee on foreign vendors billing dollars too.

## Fee pairing

Fee rows carry no merchant name. A fee pairs with the purchase whose
transaction date matches, whose country is non-US, and whose USD amount times
1% equals the fee. The parser reports anything other than a unique match under
`problems` instead of guessing:

- `reason: "ambiguous"` — several candidates. When `equivalent` is `true` they
  all cost the same, so either assignment yields identical numbers; say so when
  asking.
- `reason: "no_match"` — no candidate, and `candidates` is empty, so **nothing
  in the parse links the fee to any receipt**. Usually the parent is on an
  adjacent statement: a fee posting just after a statement close appears on the
  next one alone. Report the orphan's date and amount so it is not silently
  lost, and check it against the previous statement's estimated fee rows before
  attributing it to anything in hand. Never guess a parent.

`international_without_fee` lists non-US purchases with no fee line, excluding
any purchase already named as a candidate in `problems` (because a purchase
counted there is not also double-reported as missing a fee).

## Self-validation

The parser cross-checks its own counts and sums against the statement's
`Report Totals` row and reports each check under `validation`. If the Summary
sheet is missing, or present but laid out differently, there is a single
`summary_present` check reporting that nothing could be cross-checked.

**What a failure means, and what to do.** Report the failing checks to the user,
then **continue using the parse**, treating any fee amount derived from it as
unconfirmed until the user says otherwise. Do not stop work over it. The
statement's "Payment" bucket held exactly the fee lines in the verified month,
but real payments and refunds land there too — so any month containing a refund
produces a `fee_count`/`fee_total` mismatch on a perfectly correct parse. That is
the common benign cause. A `purchase_count` or `purchase_total` mismatch is more
serious and deserves a closer look before the numbers are trusted, but it is
still a `REVIEW`, not a halt. SKILL.md's Session Start step 7 says the same
thing; keep the two in agreement.

## Privacy

Reports carry the cardholder's name, tax id, **card number**, street address,
and account balances. They stay in the working folder. Never copy any of it into
the spreadsheet, into row notes, or anywhere in the skill repo. The parser is
written to exclude those fields from its output; keep it that way.

## Missing-charge check

    python3 {skill_dir}/scripts/check_missing_receipts.py "{year}/reports/YYYY_MM.xlsx" \
        --expenses /tmp/expenses_check.csv --json

The `--expenses` argument is a **file**, which WebFetch cannot produce. SKILL.md
Session Start step 3 gives the recipe: `curl` the sheet's CSV export to a
temporary path outside this repo and outside the working folder, run the check,
then delete it.

A charge claims a sheet row when the amounts are equal and the sheet date is
within `--window-days` (default 5) of the charge's transaction date. Posting lags
the transaction, and the sheet records the purchase date, so some tolerance is
required. Where no exact match exists, a second pass matches on vendor word
overlap within the same window, which distinguishes *recorded with the wrong
amount* from *not recorded at all*.

`INTERNATIONAL` and `TRANSACTION` are excluded from that overlap test, because
every fee line carries both words and so does every fee row on the sheet —
matching on them would pair any fee with any fee. A fee line therefore has no
discriminating words at all and skips the second pass entirely: an unrecorded fee
always lands in `missing_from_sheet`, never in `possible_amount_mismatch`.

Buckets:

| Key | Meaning |
|---|---|
| `missing_from_sheet` | Posted, not recorded. The actionable list. |
| `possible_amount_mismatch` | Recorded, but the amount disagrees — often the receipt's foreign total instead of the posted USD. |
| `ambiguous` | Several sheet rows could be the same charge; ask which. |
| `rows_without_receipt_number` | Matched, but the row has no receipt number, so no receipt file can exist. |

Every charge falls into exactly one of the first three, or matches cleanly and
appears in none of them. `rows_without_receipt_number` is a subset of the matched
rows, not a fourth charge bucket, so its count is not additive with the others.

Always report these limits with the results:

- A charge not yet processed is a true positive. Early in a cycle the missing
  list is *expected* to be long.
- Only the cardholder's own charges appear in their report.
- Aggregated sheet rows (a month of spending as one total) cannot match
  individual charges and will surface as unmatched.

The check reports gaps only. It never writes rows and never invents receipt
numbers.
