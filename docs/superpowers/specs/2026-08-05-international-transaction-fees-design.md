# International transaction fees in the accounting skill

**Date:** 2026-08-05
**Skill:** `accounting`

## Goal

International charges post to the p-card in two parts: the purchase, converted to
USD, and a separate 1% cross-border fee. The skill currently records neither
correctly — it takes the receipt total as the cost, which for a foreign receipt is
denominated in the wrong currency and omits the fee entirely.

Two changes:

1. Record the **posted USD amount** as the cost, not the receipt's foreign total.
2. Add a **second expense row** for the international transaction fee.

Both are driven from a SmartData report rather than guesswork, so the skill reads
what was actually charged instead of asking the user to recall it.

## Data source: `{year}/reports/`

The user exports reports from SmartData (J.P. Morgan) into
`{working_folder}/{year}/reports/`. Three formats appear there, in precedence
order:

| Source | Filename | Gives | Use |
|---|---|---|---|
| Account Statement, XLSX | `YYYY_MM.xlsx` | posting + transaction date, description, location, **country**, original amount + currency, conversion rate, USD amount, and a summary block with counts and totals | **Primary.** Typed cells, no layout parsing. |
| Account Statement, PDF | e.g. `Account Statement (Version 2).pdf` | same fields | Fallback only. Column alignment shifts between pages and long country names wrap, so parsing is fragile. |
| Expense Inbox print, PDF | e.g. `Expense Management.pdf` | description, posting date, USD amount, **status** (Open/Rejected) | Supplement. No country, currency, or rate — but reaches past the statement close date and is the only source of status. |

A statement covers a fixed posting-date window (stated in the header, e.g.
`Posting Date: 06/26/2026 - 07/25/2026`), so charges made after the close date will
not appear in it. The `YYYY_MM.xlsx` filename names that statement month.

The folder is optional. If it is absent or empty the skill still works — it falls
back to asking, per "Asking rules" below.

## The 1% rate

The international transaction fee is **1% of the posted USD amount, rounded half-up
to the cent**.

Verified against a full statement month: every one of its seven cross-border
purchases had a matching fee line equal to 1% of the USD amount rounded half-up,
with no exceptions, and its sole domestic-airport charge had no fee line. The
statement's own summary block counted those seven fee lines separately from the
purchases and their sum matched. One earlier hand-entered row in the expense sheet
also used exactly 1%.

The rate is treated as a constant, not a lookup. It is only ever *computed* when a
charge has not yet posted; whenever a report covers the charge, the actual fee
amount is read from it.

## XLSX parsing contract

Sheet `Detail Report`:

- Metadata occupies roughly rows 1–12: report title, run date, report id, posting
  date window, then cardholder name, tax id, **card number**, and street address.
- The table header is the row whose first cell strips to `Posting Date` (row 14 in
  the observed export). Locate it by that test rather than hard-coding 14. Header
  cells contain embedded newlines (`Transaction\nDate`, `Original\nCurrency Code`),
  so match on stripped, whitespace-collapsed text.
- Columns, in order: Posting Date, Transaction Date, Description, Location,
  Country, Original Amount, Original Currency Code, Conversion Rate, Amount.
- **A row is a transaction if and only if its first cell matches
  `^\d{2}/\d{2}/\d{4}$`.** Every other row is Level-3 addendum detail belonging to
  the transaction above it, keyed by labels such as `Description:`, `Quantity:`,
  `Guest Name:`, `Total Room Nights:`. These must be skipped.
- Numeric cells are **whitespace-padded strings**, and summary figures also carry
  thousands separators. Strip whitespace and remove commas before converting. Use
  `Decimal` with `ROUND_HALF_UP` for the 1% computation; float rounding does not
  reliably reproduce the observed cents.
- Fee rows have `Description == "INTERNATIONAL TRANSACTION"` with **blank Location
  and Country**.

Sheet `Summary Report`: the row whose first cell is `Report Totals` carries
Transaction Count / Transaction Amount (purchases), Payment Count / Payment Amount
(**the fee lines**), and Total Count / Total Amount.

**Self-validation.** After parsing, check that the purchase count and sum match
Transaction Count/Amount, and the fee count and sum match Payment Count/Amount. On
mismatch, report the failing checks to the user and then **continue using the
parse**, treating fee amounts derived from it as unconfirmed until the user says
otherwise. Stopping would be wrong: a refund or payment in the month lands in the
statement's Payment bucket alongside the fees, so a perfectly correct parse
mismatches on the fee side whenever a credit occurs.

## International detection

A charge is international when its report **Country is present and not
`UNITED STATES`**. This is a fact from the report, not an inference.

When no report covers the charge, fall back to the heuristic: the receipt is
denominated in a non-USD currency, **or** the vendor is outside the US even if
billed in USD. Card networks levy the cross-border fee on foreign vendors billing
dollars too, so currency alone is insufficient.

## Fee pairing

Fee rows carry no merchant name, so each must be attributed to its parent:

> A fee line pairs with a purchase when the purchase's **Transaction Date** equals
> the fee's, the purchase's Country is non-US, and 1% of the purchase's USD amount
> rounded half-up equals the fee amount.

In the verified statement this produced a unique match for all seven fees. Where it
yields **more than one candidate or none**, present the candidates and ask — do not
guess. As a completeness check, the count of non-US purchases should equal the count
of fee lines.

## Workflow changes

### Session start — new step 7, "Load SmartData reports"

Inserted after the existing step 6 ("Read all unnumbered files") so that step 6
cross-references elsewhere in the skill stay valid. Subsequent steps renumber:
status report becomes 8, the closing question becomes 9.

Read every report in `{year}/reports/`, preferring XLSX. Build a posted-charge list
of description, posting date, transaction date, country, original amount and
currency, conversion rate, USD amount, and status where available. Hold the
`INTERNATIONAL TRANSACTION` lines separately for pairing. Record which posting-date
windows are covered, and run the self-validation above.

The status report in step 8 gains a line naming the reports loaded and the
posting-date range they cover, so gaps are visible before processing starts.

### Phase 1 — new Step 1.3, "Cross-check against the SmartData report"

Inserted before the expense record is filled in, because the posted USD amount *is*
the cost. Existing steps renumber: expense record 1.3 → 1.4, entertainment check
1.4 → 1.5, confirmation 1.5 → 1.6, repeat 1.6 → 1.7. The reference to "the `YYXXX`
number assigned in Step 1.2" stays correct.

The step does three things:

1. **Payment method.** Match the receipt to a posted charge by description and
   amount. Descriptions are card descriptors (`AMAZON MKTPL*<id>`,
   `SQ *<merchant>`), so match fuzzily. A match confirms `p-card`. No match → ask;
   never silently default to `p-card`.
2. **Amount.** Compare the receipt total to the posted USD amount. If they differ,
   show both and ask which to record. Differences are usually legitimate — tips,
   currency conversion, partial capture, hotel incidentals — so the posted amount
   normally wins but is not assumed.
3. **International fee.** If a paired fee line exists, use its actual amount. If
   the charge is international but unposted, compute 1% and mark it an estimate. If
   pairing is ambiguous, show candidates and ask. If the report covers the charge
   but shows no fee line for it and no ambiguity — the parser's
   `international_without_fee` — treat the fee as not yet posted: compute the 1%
   estimate, mark it, and say the report showed no fee line. The usual cause is the
   fee posting just after the statement close, which Phase 3 then reconciles.

   These branches must be exhaustive **over purchases** — a paired fee, an
   unposted charge, an `ambiguous` `problems` entry naming this purchase, and
   `international_without_fee`. They are not exhaustive over *fee lines*: a
   `problems` entry with `reason: "no_match"` is an orphan fee that names no
   purchase at all, so nothing links it to a receipt being processed. Orphan fees
   need their own branch — report the orphan's date and amount, and check it
   against estimated rows from the previous statement, since a fee posting just
   after the close appears on the next statement without its parent. Before
   falling back to a computed estimate, check whether an orphan fee in the same
   report plausibly belongs to the charge in hand (same transaction date, amount
   within a cent of 1% of the posted amount) — the actual figure always beats an
   estimate.

For an international charge, the main row records the posted USD amount as `Cost`,
and `notes` carries the original amount, currency, and conversion rate.

### The fee row

Follows the convention already established by hand in the expense sheet:

| Field | Value |
|---|---|
| Expense | `{vendor} — international transaction fee` |
| Vendor | same as the parent row |
| Cost | actual fee from the report, else 1% of the parent USD amount rounded half-up |
| date | **the parent row's date**, so the two rows stay adjacent |
| method | `p-card` |
| Fund | same as the parent row |
| GL code | same as the parent row |
| receipt_number | same as the parent row |
| notes | `Foreign transaction fee on {what} (see {receipt_number})`, plus `1% estimate, verify against statement` when computed rather than read |

No new GL code: the fee inherits the parent's, so `references/gl_codes.md` is
unchanged. Sharing the parent's `receipt_number` is already safe — Phase 3
documents that one receipt number may cover multiple rows. If the fee's own posting
date differs from the parent's, note it rather than splitting the rows apart.

### Non-p-card methods

For `finance` and `reimbursement`, add **no fee row** — the 1% is a card
assessment. Record the USD amount if it is known — from the payer's own statement
or the reimbursement figure — and otherwise ask, since no report the skill can
read covers a non-p-card payment. Put the foreign amount in `notes` either way.

### Phase 3 — reconciliation

Add: re-check rows whose notes carry a 1% estimate against a report that now covers
them, correct the cost if it differs, and drop the estimate caveat once confirmed.

## Asking rules

The skill asks rather than assumes in these cases, and distinguishes two kinds of
gap:

- **No report covers the receipt's period** → ask the user to export that statement
  month from SmartData into `{year}/reports/`, naming the file it wants
  (`YYYY_MM.xlsx`). Offer to continue meanwhile with a computed 1% estimate and a
  flagged payment method, so a missing report never blocks the work.
- **A report covers the period but the charge is absent** → the charge has probably
  not posted yet. Do not ask for a new report; compute the 1% estimate and flag it.
- Receipt total disagrees with the posted amount.
- Fee pairing is ambiguous or finds no candidate.
- Self-validation against the summary block fails — report the failing checks and
  continue, rather than stopping; see Self-validation above.

## Missing-charge check

A report lists every charge that posted, so it also reveals charges that were
never recorded — the mirror image of the orphaned-receipt check Phase 3 already
does. This catches a missed receipt within a statement cycle instead of at
year-end reconciliation.

**Inputs:** a parsed report, the expenses sheet already fetched at session start
(as CSV), and a date window (default 5 days, since posting lags the transaction
and the sheet records the purchase date).

**Matching runs in two phases**, and the ordering is load-bearing.

*Phase 1* — for each report charge, purchases *and* fee lines, look for a sheet
row whose `Cost` equals the charge amount and whose `date` falls within the
window of the charge's transaction date. Exactly one match claims that row; more
than one is ambiguous; none defers the charge to phase 2.

*Phase 2* — for deferred charges only, and only over rows still unclaimed, retry
within the window on **vendor token overlap alone**. This surfaces a row recorded
with the wrong amount instead of misreporting it as absent.

Every exact match must resolve before any fuzzy matching begins. Interleaving the
two lets a row be offered as a mismatch candidate for one charge and then consumed
as the confirmed match for another, so a human would be sent to edit the row that
is in fact correct. One row is claimed by at most one charge.

**Outputs**, each an explicit bucket rather than a single "missing" list:

- `missing_from_sheet` — posted, not recorded. The actionable list.
- `possible_amount_mismatch` — recorded, but the amount disagrees.
- `ambiguous` — several sheet rows could be the same charge.
- `rows_without_receipt_number` — matched, but the row has no receipt number, so
  no receipt file can exist for it.

**Surfaced in** Phase 3 reconciliation, with a count in the session-start status
report so a gap is visible before processing begins.

**Known limits**, which must be stated when reporting results rather than left
for the user to discover:

- A charge not yet processed is a true positive, not an error — early in a cycle
  the list is *expected* to be long.
- Only the cardholder's own charges appear in their report, so another
  cardholder's spending is out of scope and its absence means nothing.
- Aggregated sheet rows (a month of another person's spending recorded as one
  total) cannot match individual charges and will surface as unmatched.

## Files to change

- `accounting/SKILL.md` — new session-start step 7 and renumbering; new Phase 1
  Step 1.3 and renumbering of 1.3–1.6; fee row convention; Phase 3 bullets for
  estimated fees and the missing-charge check.
- `accounting/CLAUDE.md` — document `{year}/reports/` in the working-folder
  structure, note the XLSX-first precedence, and record that reports carry PII and
  never leave the working folder.
- `accounting/references/gl_codes.md` — unchanged.

## Privacy

Reports contain the cardholder's name, tax id, **card number**, street address, and
account balances. They stay in the working folder. None of it may be copied into
the spreadsheet, into row notes, or anywhere in this git repo — including this
document, whose examples are deliberately structural rather than actual records.

## Non-goals

- No new GL code for fees.
- No currency conversion by looked-up rate; the posted amount is authoritative.
- No claiming of personal-card foreign fees on `reimbursement` rows.
- The missing-charge check reports gaps; it never writes rows or invents receipt
  numbers for them.
