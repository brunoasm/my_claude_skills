# Accounting Skill — Technical Context

## Purpose
Manages procurement card expense tracking for a Field Museum researcher. Processes receipts, tracks expenses in Google Sheets, reconciles records, and generates entertainment supplement tables.

## Tools & Constraints
- **Read Google Sheets**: Use `WebFetch` with CSV export URL: `https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet={TAB_NAME}`
- **Write Google Sheets**: Not available (no API/MCP). Format expense rows as tab-separated text for user to paste.
- **Read receipts**: Use the `Read` tool on PDF/image files.
- **Rename files**: Use `Bash` with `mv` command.

## Working Folder
The skill runs **from** the accounts and receipts folder — that is all it needs
to know. `{working_folder}` means the current directory, and every path below is
relative to it. The folder's absolute location is deliberately not recorded in
this repo; do not add it back, and do not search the filesystem for it. If the
current directory does not look like the working folder, SKILL.md's Session
Start asks the user to restart from the right one.

Structure per year:
- `{year}/receipts/` — numbered receipt files
- `{year}/supplements/` — monthly entertainment supplement PDFs
- `{year}/reports/` — SmartData exports (`YYYY_MM.xlsx` preferred; statement and
  expense-inbox PDFs also appear). Parse with `scripts/parse_smartdata.py`; see
  `references/smartdata_reports.md`.

## Spreadsheet Configuration
On first run each year, the skill creates/updates `spreadsheet_links.yaml` in the working folder with the Google Sheet URL for that year. This file is NOT in the skill folder (it contains sensitive links).

## Naming Conventions
- Receipts: `YYXXX_short_description.ext` (e.g., `26025_amazon_labsupplies.pdf`)
- Supplements: `supplement_BASM_YYYY_MM.pdf`

## Sensitive Data Policy
The skill folder (this directory) is git-tracked. Never store spreadsheet links, actual expense data, receipt contents, or any personally identifiable information here. All session-specific data stays in the working folder.

SmartData reports in `{year}/reports/` carry the cardholder's name, tax id, card
number, street address, and account balances. They stay in the working folder.
Never copy any of it into the spreadsheet, into row notes, or into this
directory. `scripts/parse_smartdata.py` deliberately excludes those fields from
its output.
