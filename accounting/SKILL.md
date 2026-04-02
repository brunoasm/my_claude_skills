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

## Session Start

1. **Detect year**: Determine the current year from today's date. Confirm with the user: "Working on **{year}** expenses — correct?"

2. **Load spreadsheet config**: Check for `spreadsheet_links.yaml` in the working folder (`/Users/bruno/Documents/docs_macbookair2015/lab/Field Museum/accounts_and_receipts`). If the file is missing or has no entry for this year, ask the user for the Google Sheet link and save it:
   ```yaml
   {year}:
     spreadsheet_id: "{extracted_id}"
     url: "{full_url}"
   ```

3. **Read current expenses**: Fetch the expenses tab via WebFetch CSV export:
   ```
   https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet=expenses
   ```
   Parse to understand existing records and the receipt numbers already used.

4. **Scan receipts folder**: List files in `{working_folder}/{year}/receipts/`. Identify:
   - Highest existing receipt number (pattern: `YYXXX_...`)
   - Any unnumbered files (those not matching the `YYXXX_` prefix pattern)

5. **Report status**:
   ```
   Year: {year}
   Spreadsheet: {url}
   Existing expense records: {count}
   Numbered receipts: {count} (highest: {number})
   Unnumbered files to process: {count}
   {list unnumbered filenames}
   ```

6. Ask the user what they'd like to do: process new receipts, reconcile, check budgets, or generate a supplement.

## Phase 1: Receipt Processing

For each unnumbered file in the receipts folder:

### Step 1.1 — Read the receipt
Use the Read tool to examine the PDF or image. Extract:
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

### Step 1.3 — Propose expense record
Fill in all 10 columns of the expenses tab:

| Field | How to determine |
|-------|-----------------|
| Expense | Brief description of what was purchased |
| Vendor | Vendor/merchant name from receipt |
| Cost | Total amount as `$X.XX` (negative for returns/credits) |
| date | Purchase date in `D-Mon-YYYY` format (e.g., `15-Mar-2026`) |
| method | Default `p-card` unless user says otherwise |
| Fund | Ask user — common values: `startup`, `SeedFunds` |
| GL code | Propose based on `references/gl_codes.md`, confirm with user |
| receipt_number | The `YYXXX` number assigned in Step 1.2 |
| notes | Leave empty unless something notable |
| request reimbursement | Leave empty unless user specifies |

### Step 1.4 — Entertainment check
If the GL code is an entertainment code (6455, 6460, 6470, 6475), collect additional information for the supplement form:
- **Location**: venue name and city (often derivable from receipt)
- **Persons Involved**: ask user for each attendee's name, title, and company/institution
- **Business Purpose**: ask user for a brief description of the meeting purpose
- **Alcohol**: ask if alcohol was purchased (affects VP approval requirement)

Store this supplement data for Phase 4.

### Step 1.5 — Confirm with user
Present all proposed data clearly and ask for confirmation before proceeding. Show:
- Proposed filename
- All expense record fields
- Entertainment supplement fields (if applicable)

Only after user confirms:
- Rename the file using `mv`
- Add the expense record to the accumulator for Phase 2

### Step 1.6 — Repeat
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
4. **Report** findings clearly, listing any discrepancies.

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
