---
name: accounting
description: "Process receipts, track expenses in Google Sheets, reconcile records, and generate entertainment supplement tables for Field Museum procurement card accounting"
---

# Accounting Skill

Use this skill when the user wants to:
- Process new receipts and add expense records
- Reconcile receipts against spreadsheet records
- Generate entertainment supplement tables
- Check budget or fund balances
- Organize procurement card accounting

Keywords: receipt, expense, accounting, budget, fund, supplement, p-card, procurement, GL code, reconcile

## Available Resources

- `references/gl_codes.md` — GL code reference table with entertainment flags
- `references/supplement_guide.md` — Supplement form layout and filing rules
- `references/smartdata_reports.md` — SmartData report formats, parsing, the 1% international fee, and pairing rules
- `scripts/parse_smartdata.py` — parses a SmartData Account Statement XLSX and pairs international fees

## Session Start

**Run this skill from the accounts and receipts working folder.** Every path below is relative to it, and `{working_folder}` means that directory — the current one. The folder's location is deliberately not recorded in this repo.

If the current directory holds neither `spreadsheet_links.yaml` nor a `{year}/` directory, this is the wrong folder: say so and ask the user to restart the session from the right one. Do not go searching the filesystem for it.

1. **Detect year**: Determine the current year from today's date. Confirm with the user: "Working on **{year}** expenses — correct?"

2. **Get spreadsheet link**: Check for `spreadsheet_links.yaml` in the working folder.
   - If a link for this year **already exists** in the YAML, show it and ask: "Using this spreadsheet — correct? {url}"
   - If the file is missing or has no entry for this year, ask the user for the Google Sheet link.
   Save/update the link:
   ```yaml
   {year}:
     spreadsheet_id: "{extracted_id}"
     url: "{full_url}"
   ```

3. **Read current expenses**: Detect the environment by testing whether this is a local Mac session — `command -v open` succeeds and the `{year}/receipts/` directory is present. Then:

   - **On cowork (local Mac)**:
     Open the spreadsheet in Chrome so the user can interact with it:
     ```bash
     open -a "Google Chrome" "{full_url}"
     ```
     Also fetch the expenses tab via WebFetch CSV export:
     ```
     https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet=expenses
     ```
     If the WebFetch CSV export fails or returns an auth/login page, note this and ask the user to manually export the sheet as CSV and provide the file path.

   - **Not on cowork (cloud/remote — no local receipts tree)**:
     Fetch directly via WebFetch CSV export:
     ```
     https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet=expenses
     ```
     If this fails, ask the user to paste the spreadsheet data or provide a downloaded CSV file.

   Parse the expenses data to understand existing records and the receipt numbers already used. **Analyze patterns** in existing records to learn Fund and GL code assignment conventions — e.g., which vendors consistently map to which funds and GL codes. Use these precedents when proposing values for new receipts rather than defaulting to a single fund.

4. **Read past supplements**: List and read existing supplement PDFs in `{working_folder}/{year}/supplements/` to learn default patterns for entertainment supplement fields (Persons Involved, Business Purpose). For example, grocery store purchases may consistently use a standard lab group description while restaurant meals may list named attendees. Use these patterns as defaults when proposing supplement data for new entertainment expenses.

5. **Scan receipts folder**: List files in `{working_folder}/{year}/receipts/`. Identify:
   - Highest existing receipt number (pattern: `YYXXX_...`)
   - Any unnumbered files (those not matching the `YYXXX_` prefix pattern)

6. **Read all unnumbered files**: Proactively read the contents of every unnumbered file before presenting anything to the user. Files may have misleading names (e.g., `receipts_2026.pdf`, `Pcard Missing Receipt Form.pdf`). Classify each file by inspection:
   - **Normal receipt**: proceed with processing
   - **Duplicate**: matches an already-numbered receipt — flag for user but don't process
   - **Non-receipt**: forms, summaries, statements — flag for user, skip processing
   - **Unreadable**: image too low-resolution or corrupted — flag and ask user for details

7. **Load SmartData reports**: List `{working_folder}/{year}/reports/`. For each `YYYY_MM.xlsx`, run:
   ```bash
   python3 scripts/parse_smartdata.py "{working_folder}/{year}/reports/{file}" --json
   ```
   Keep the parsed purchases, fee lines, and pairings for use in Phase 1, and note which posting-date windows are covered. If `validation.ok` is false, report the failing checks to the user before processing anything. See `references/smartdata_reports.md` for the formats, the PDF fallbacks, and what each `problems` reason means.

   The folder is optional — if it is missing or empty, continue without it and ask per Step 1.3 when a receipt actually needs the information.

8. **Report status**:
   ```
   Year: {year}
   Spreadsheet: {url}
   Existing expense records: {count}
   Reports loaded: {count} covering {posting-date windows}
   Numbered receipts: {count} (highest: {number})
   Unnumbered files to process: {count}
   {list unnumbered filenames}
   ```

9. Ask the user what they'd like to do: process new receipts, reconcile, check budgets, or generate a supplement.

## Phase 1: Receipt Processing

For each unnumbered file in the receipts folder:

### Step 1.1 — Read the receipt
The file was already read during session start (step 6). Use the extracted contents. If the file was an image too low-resolution to read, acknowledge this immediately and ask the user for: vendor name, amount, date, and description. Do not guess from unreadable images.

From the receipt contents, extract:
- Vendor name
- Date of purchase
- Total amount (including tax)
- Description of items purchased
- Payment method if visible

### Step 1.2 — Propose filename
Generate the next receipt number continuing from the highest existing number:
- Format: `YYXXX_short_description.ext` (keep original file extension)
- Short description: lowercase, underscores, 2-4 words describing the purchase
- Example: `26025_amazon_labsupplies.pdf`

### Step 1.3 — Cross-check against the SmartData report

Use the reports loaded during session start (step 7). See
`references/smartdata_reports.md` for details.

1. **Payment method**: match the receipt to a parsed purchase by description and
   amount. Descriptions are card descriptors (`AMAZON MKTPL*<id>`,
   `SQ *<merchant>`), so match fuzzily. A match confirms `p-card`. If there is no
   match, ask whether this is a p-card charge that has not posted yet, `finance`,
   or `reimbursement` — never silently default to `p-card`.

2. **Amount**: compare the receipt total to the posted USD amount. If they
   differ, show both and ask which to record. Differences are usually legitimate
   — tips, currency conversion, partial capture, hotel incidentals — so the
   posted amount normally wins, but do not assume it.

3. **International fee**: the charge is international when the report's Country
   is present and not `UNITED STATES`. If no report covers the receipt's period,
   fall back to the heuristic (non-USD receipt, or a vendor outside the US even
   if billed in USD).
   - If a paired fee line exists, use its **actual** amount.
   - If the charge is international but has not posted, compute **1% of the
     posted USD amount, rounded half-up** and mark it an estimate.
   - If the parser reported the fee under `problems`, show the candidates and
     ask. When `equivalent` is true, say that either assignment gives the same
     numbers.

For an international charge, `Cost` on the main row is the **posted USD amount**,
not the receipt's foreign total, and `notes` carries the original amount,
currency, and conversion rate.

**When a report is needed but missing**: if the receipt's period has no report at
all, ask the user to export that statement month from SmartData into
`{year}/reports/` as `YYYY_MM.xlsx`. Offer to continue meanwhile with a computed
1% estimate and a flagged payment method — a missing report must never block the
work. If a report covers the period but the charge is absent, it simply has not
posted; do not ask for another report.

### Step 1.4 — Propose expense record
Fill in all 10 columns of the expenses tab:

| Field | How to determine |
|-------|-----------------|
| Expense | Brief description of what was purchased. For refunds/credits, match the original expense name from the spreadsheet followed by "(refund)" — e.g., "Claude subscription for students (refund)", not a generic description |
| Vendor | Vendor/merchant name from receipt |
| Cost | Total amount as `$X.XX` (negative for returns/credits) |
| date | Purchase date in `D-Mon-YYYY` format (e.g., `15-Mar-2026`) |
| method | Default `p-card` unless user says otherwise |
| Fund | Propose based on patterns learned from existing spreadsheet records for the same vendor or expense type. Only ask the user if no clear precedent exists |
| GL code | Propose based on `references/gl_codes.md` (consult ALL codes, not just commonly used ones) AND patterns from existing spreadsheet records. Only ask the user if no clear precedent exists |
| receipt_number | The `YYXXX` number assigned in Step 1.2 |
| notes | Leave empty unless something notable |
| request reimbursement | Leave empty unless user specifies |

**International transaction fee row.** When Step 1.3 found or computed a fee, emit a
**second row** alongside the main one:

| Field | Value |
|-------|-------|
| Expense | `{vendor} — international transaction fee` |
| Vendor | same as the parent row |
| Cost | the actual fee from the report, else 1% of the parent's USD amount rounded half-up |
| date | the **parent row's** date, so the two rows stay adjacent |
| method | `p-card` |
| Fund | same as the parent row |
| GL code | same as the parent row |
| receipt_number | same as the parent row |
| notes | `Foreign transaction fee on {what} (see {receipt_number})` — append `; 1% estimate, verify against statement` when computed rather than read |

The fee inherits the parent's GL code, so no new GL code is needed. Sharing the
parent's `receipt_number` is expected: Phase 3 already treats one receipt number
covering multiple rows as normal. If the fee's own posting date differs from the
parent's, note it rather than splitting the rows apart.

For `finance` and `reimbursement`, add **no** fee row — the 1% is a card
assessment. Still record the posted USD amount and put the foreign amount in
`notes`.

### Step 1.5 — Entertainment check
If the GL code is an entertainment code (6455, 6460, 6470, 6475), collect supplement form fields. Use patterns learned from past supplements (read during session start, step 4) to propose defaults:
- **Location**: venue name and city (often derivable from receipt)
- **Persons Involved**: propose based on patterns from past supplements for similar expense types — e.g., grocery/snack purchases may consistently use a standard lab group description, while restaurant meals list named attendees. Only ask the user to confirm or correct, not to provide from scratch
- **Business Purpose**: propose based on past supplement patterns for the same venue or expense type. Only ask to confirm
- **Alcohol**: ask if alcohol was purchased (affects VP approval requirement)

Store this supplement data for Phase 4.

### Step 1.6 — Confirm with user
Present all proposed data clearly and ask for confirmation before proceeding. Show:
- Proposed filename
- All expense record fields
- Entertainment supplement fields (if applicable)

Only after user confirms:
- Rename the file using `mv`
- Add the expense record to the accumulator for Phase 2

### Step 1.7 — Repeat
Move to the next unnumbered file. After all files are processed, proceed to Phase 2.

## Phase 2: Spreadsheet Update

After all receipts are processed:

1. Compile all new expense records using pipe `|` as separator, matching the column order:
   ```
   Expense|Vendor|Cost|date|method|Fund|GL code|receipt_number|notes|request reimbursement
   ```

2. Print the pipe-separated rows directly (do NOT write to a file). Instruct the user:
   - Click on the first empty cell in column A
   - Paste the text
   - Click the small paste icon that appears at the bottom-left
   - Select **Split text to columns**
   - Choose **Custom** separator and type `|`

3. Remind the user to sort the sheet by date after pasting if desired.

## Phase 3: Reconciliation

Compare receipts folder against spreadsheet records:

1. **Read current expenses** from the spreadsheet (re-fetch via CSV export).
2. **List receipt files** in `{year}/receipts/` matching the `YYXXX_` pattern.
3. **Compare**:
   - **Orphaned receipts**: files in folder with no matching `receipt_number` in the spreadsheet
   - **Missing files**: spreadsheet records whose `receipt_number` has no matching file
   - **Note**: some receipt numbers may cover multiple expense rows (same receipt, multiple items) — this is expected
4. **Confirm estimated fees**: for rows whose notes carry `1% estimate`, check them
   against a report that now covers the period. Correct the cost if it differs and
   drop the estimate caveat once confirmed.
5. **Report** findings clearly, listing any discrepancies.

## Phase 4: Entertainment Supplement

Generate the supplement table for a given month:

1. Ask which month to generate (default: current or most recent month with entertainment expenses).
2. Filter entertainment expenses (GL 6455/6460/6470/6475) for that month from the spreadsheet.
3. Combine with the supplement data collected during Phase 1 (if in the same session) or ask the user for missing fields.
4. Format as a table matching the supplement form layout:

   ```
   Date | Location | Persons Involved (Name, Title, Company) | Business Purpose | Total
   -----|----------|------------------------------------------|-----------------|------
   {rows}
                                                                          Total: ${sum}
   ```

5. Output the table as copyable text.
6. Note if any expenses involved alcohol (VP approval required).
7. Remind: save as `supplement_BASM_{YYYY}_{MM}.pdf` in `{year}/supplements/`.

## Phase 5: Budget & Fund Check

On user request:

1. Fetch the **funds** tab via CSV export — show available balances per fund.
2. Fetch the **budget** tab via CSV export — show spending by GL category, flag any over-budget items.
3. Present a concise summary with the most relevant information.

## Communication Guidelines

- Be concise. Lead with the data, not explanations.
- When proposing expense records, present them in a clear table format.
- When multiple receipts need processing, handle them one at a time — don't batch confirmations.
- For the paste block, use pipe `|` as separator. Tab-separated text does not survive copy-paste from Claude, and commas conflict with values. Pipe is safe and Google Sheets supports it via custom separator.
- Always confirm before renaming files or finalizing expense records.
