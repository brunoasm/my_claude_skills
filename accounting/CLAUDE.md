# Accounting Skill — Technical Context

## Purpose
Manages procurement card expense tracking for a Field Museum researcher. Processes receipts, tracks expenses in Google Sheets, reconciles records, and generates entertainment supplement tables.

## Tools & Constraints
- **Read Google Sheets**: Use `WebFetch` with CSV export URL: `https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet={TAB_NAME}`
- **Write Google Sheets**: Not available (no API/MCP). Format expense rows as tab-separated text for user to paste.
- **Read receipts**: Use the `Read` tool on PDF/image files.
- **Rename files**: Use `Bash` with `mv` command.

## Working Folder
The accounts and receipts base folder is at:
`/Users/bruno/Documents/docs_macbookair2015/lab/Field Museum/accounts_and_receipts`

Structure per year:
- `{year}/receipts/` — numbered receipt files
- `{year}/supplements/` — monthly entertainment supplement PDFs

## Spreadsheet Configuration
On first run each year, the skill creates/updates `spreadsheet_links.yaml` in the working folder with the Google Sheet URL for that year. This file is NOT in the skill folder (it contains sensitive links).

## Naming Conventions
- Receipts: `YYXXX_short_description.ext` (e.g., `26025_amazon_labsupplies.pdf`)
- Supplements: `supplement_BASM_YYYY_MM.pdf`

## Sensitive Data Policy
The skill folder (this directory) is git-tracked. Never store spreadsheet links, actual expense data, receipt contents, or any personally identifiable information here. All session-specific data stays in the working folder.
