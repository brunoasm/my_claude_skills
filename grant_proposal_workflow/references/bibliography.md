# Bibliography and loose files

## 1. Choose the mode at setup

Ask the PI once and record the answer in the decisions log:

- **Reference manager** (Zotero, EndNote, Mendeley, Paperpile, ...): the PI's library is the source of truth. Claude works from its exports.
- **Local library**: Claude assembles and maintains an indexed folder of PDFs for this proposal.

Look before asking: a `.bib`, `.ris`, or CSL JSON export in the project, or reference-manager fields in the drafts (`scripts/docx_audit.py` counts them), means a manager is in use. A PI can also mix the two, keeping a manager while Claude finds and fetches new papers; then use the local-library steps for fetching, and hand the results to the manager (section 2).

## 2. Reference-manager mode

- Ask the PI for an export of the proposal's collection (BibTeX, RIS, or CSL JSON; BibTeX works with `cite_check.py --bib`) and save it as `98_bibliography/exports/<YYYY-MM-DD>_<collection>.<ext>`. Ask for a fresh export after the library changes; check against the newest one.
- Read attached PDFs from the manager's storage folder if the PI points to it, read-only. Never write to the manager's database or storage.
- Problems in the library (wrong year, missing pages, an abstract full of unrelated text) are fixed by the PI in the manager and then refreshed in the document. Give the PI the corrected fields, not an edited file.
- New papers Claude finds go to the PI as an import file (`98_bibliography/to_import/<date>.ris` or `.bib`) plus the PDFs, so the PI adds them to the library themselves. Citations go into documents as placeholders (`(CITE: Author Year, topic)`) for the PI to insert as live fields.

## 3. Local-library mode

### Layout

```
98_bibliography/
├── library.csv       the index (one row per work)
├── library.bib       BibTeX built from verified metadata (for cite_check.py --bib and later import)
├── pdfs/             <Surname>_<Year>_<ShortTitle>.pdf, plus _SI1, _SI2 for supplements
├── text/             <key>.txt from pdftotext, for searching quotes and page numbers
└── notes.md          conventions for this library (naming, style, anything unusual)
```

`library.csv` columns: `key, doi, authors, year, title, container, volume, pages, file, sha256, status, source, supports, notes`.

- `key` matches the BibTeX key and the file name stem (`Surname_Year_ShortTitle`; add `a`, `b` for collisions).
- `status`: `pdf` / `abstract only` / `needed` / `not obtainable` (with the reason).
- `source`: where the PDF came from (open-access URL, publisher via the PI's browser, PI-provided, inbox).
- `supports`: the claims or sections that cite it, so a cut section shows which references may become uncited.

Update the CSV and the BibTeX together, and edit them in place: the PI may annotate the CSV. If an existing `library.csv` lacks some of these columns, add them at the end and leave existing columns and values as they are. Read and write it by column name with a CSV library (e.g., Python's `csv.DictReader`/`DictWriter`), never by position: the column order differs between libraries. Create `library.bib` when the first work is confirmed (not as an empty file), `text/` when the first PDF is filed, and `notes.md` when the first convention needs recording.

### Finding papers

1. **Metadata first, from an authoritative record.** Resolve every work to a DOI (or PMID, arXiv ID, ISBN) and take authors, year, title, journal, volume, and pages from that record (Crossref, PubMed, OpenAlex, the publisher's page), not from a file name, a PDF's first page, or an AI summary. Works without a DOI (books, chapters, reports, theses, agency documents) are confirmed from a library catalog, the publisher's or issuing agency's page, or the institutional repository. Verify that the year and authors in the proposal's text match. If no record can be found, the work is **unconfirmed**: do not add it to `library.bib`, and ask the PI for the full citation (it may be in press, grey literature, or misremembered).
2. **Open-access copies, independently.** Look for a legal open copy: the publisher (open-access article), PubMed Central, preprint servers, institutional or author repositories, or an open-access discovery service (e.g., Unpaywall's API by DOI). Use whatever search and fetch tools the session has. Never use shadow libraries.
3. **Paywalled papers, with the PI's help in their browser.** List what is still needed (key, DOI link, why it is needed) and get the PI's go-ahead before downloading.
   - If a browser tool can drive the PI's own Chrome, use it: the PI's institutional access, cookies, and proxy only exist there. Open each DOI link and use the publisher's download button. When a login, single sign-on, two-factor prompt, or CAPTCHA appears, stop and ask the PI to complete it; never type or store credentials.
   - Download one paper at a time, only what the proposal needs; publishers block and licenses forbid systematic downloading.
   - Without browser control, give the PI the list as clickable DOI links and ask them to save the PDFs into the inbox.
   - Downloads land in the browser's download folder. Move them into the inbox and process them like any other loose file.
4. **Can't get it.** Mark `not obtainable` with the reason, and say so wherever a claim depends on that paper: a claim checked only against an abstract is not verified (SKILL.md section 6). Interlibrary loan or asking the authors are options for the PI.

### Building the reference list

Format the reference list from `library.bib` in the style the funder or PI requires, record the style in the decisions log, and run `scripts/cite_check.py --bib 98_bibliography/library.bib` after every change. Check the funder's rules on author lists (some require all authors) and on URLs and DOIs.

The library is a working copy for the PI's research use. Keep it local: do not put the PDFs in shared repositories or send them to others.

## 4. Loose files: the inbox

The PI drops anything into `00_inbox/` (or another folder they name) at any time: papers, supplements, saved web pages, letters, quotes, data, screenshots. At the start of each session, and whenever the PI says files were added, process it:

1. **Inventory.** Check the library first: a PDF in `pdfs/` with no row gets a row (status from whether its metadata is confirmed), and a row whose file is missing gets status `needed` and a note. Then run `scripts/pdf_identify.py 00_inbox --library 98_bibliography` for the PDFs. It reports identifiers, a title and year guess, page count, whether there is a text layer, whether it looks like supplementary material, and duplicates of files already in the library (by checksum and DOI). List the non-PDF files by type.
2. **Identify by content, not by name.** Open every file and decide what it is from what it contains; a file name is a hint at most. When the name and the contents disagree (a "quote" that is a full budget table), treat it as ambiguous. For papers, confirm the work from an authoritative record (section 3); the script's title and year guesses are leads only. A file without a text layer is a scan: render the first page and look at it. It may be a paper, a signed letter, a figure, or something else, and is sorted like any other file of that kind.
3. **Sort.**
   - Papers, confirmed: in local-library mode, rename to the key and move to `pdfs/`, extract text to `text/`, and add or update the rows in `library.csv` and `library.bib`. In reference-manager mode, move them to `to_import/` and add them to the import file.
   - Papers that cannot be confirmed: leave them in `00_inbox/_unsorted/` with the specific question for the PI (which work is it, which citation is correct).
   - Supplements: once the parent is filed, name them after it (`_SI1`) and link them in the parent's row; until then, keep them with the parent in `_unsorted/`.
   - Duplicates:
     - Identical to a file already in the library (same checksum): move to `00_inbox/_duplicates/`.
     - Same DOI as a library row whose PDF is missing: this copy fills the gap; file it under the row's key after confirming the metadata, and correct the row if it disagrees with the record.
     - Same work as a library PDF but a different file: keep the better copy (publisher version over preprint, text layer over scan, unless the PI cited the preprint). If the better one is the new file, ask before swapping, then move the old library copy to `_duplicates/` and record the change in the row.
     - Two copies in the inbox: move the lesser copy to `_duplicates/` and treat the better one like any other paper (filed if confirmed, otherwise kept in `_unsorted/`).
   - Unreadable files (damaged or incomplete downloads): if Claude downloaded it, download it again; otherwise leave it in `_unsorted/` and ask the PI for a new copy.
   - Everything else: move it to its project folder, following the PI's folder habits: call text and templates to `01_guidelines/`; signed and draft letters to `03_supporting/letters/`; quotes and correspondence to `03_supporting/`; data and code with the analysis that uses them.
   - Anything ambiguous (two candidate works, unclear purpose, name and contents disagree, a possible new version of a document): leave it in `00_inbox/_unsorted/` and ask.
4. **Never lose anything.** Move, do not copy-and-delete; use `mv -n` so nothing is overwritten; never delete a file. Do not move a file that is open (a `~$` lock file sits beside it).
5. **Log every move** in `00_inbox/LOG.md` (date, from, to, why). Summarize what was filed and the questions for the PI in that session's notes file (template and location in `references/tracking-templates.md`; create it if this is the first session), and keep asking about anything left in `_unsorted/` until it is resolved.
