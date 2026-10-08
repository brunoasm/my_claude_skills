# Claude skills from the de Medeiros lab

Skills for Claude that I use for research, writing, and running a lab at the Field Museum. Some apply to any research group, like extracting data from papers, OCR, phylogenomics, data archiving, and grant writing. Others are tied to Field Museum systems and procedures.

The skills work in Claude Code (installed as plugins from this repo's marketplace) and in Claude.ai (uploaded as zip files from [Releases](https://github.com/brunoasm/my_claude_skills/releases)).

## Skills

### `general-skills`

| Skill | What it does | Needs |
|---|---|---|
| [`grant-proposal-workflow`](./grant_proposal_workflow/SKILL.md) | Takes a multi-document grant application or resubmission (NSF, NIH, foundations, internal awards) from the call to the submission package. Starts from the program's own guidelines and every document they reference, works inside the grant's own budget template, and keeps people, promises, numbers, and scope changes consistent across documents. Covers drafting that keeps the author's voice, letters, citations, and mock panel and red-team reviews. Scripts audit .docx formatting and hidden content, report page fit, cross-check citations, check budget-justification arithmetic, and audit figures and captions. | Python 3; LibreOffice and poppler for the page-fit check |
| [`extract-from-pdfs`](./extract_from_pdfs/SKILL.md) | Turns a collection of scientific PDFs into a validated dataset for systematic reviews and meta-analyses: filters by abstract, extracts data, checks names and places against external databases (GBIF, WFO, GeoNames, PubChem, NCBI), and exports. [Details](./extract_from_pdfs/README.md) | Conda environment; Anthropic API key or a local Ollama model |
| [`document-ocr`](./document_ocr/SKILL.md) | Converts scanned PDFs and page images to Markdown, keeping multi-column reading order, diacritics, tables, and figures. Uses docling for layout and a vision-language model for the text. | Conda environment; an OCR backend you already run (vLLM, Ollama, or a cloud vision API) |
| [`secure-raw-data-backup`](./secure_raw_data_backup/SKILL.md) | Archives irreplaceable raw data to write-once S3 Deep Archive: freezes and checksums folders, streams an uncompressed tarball under Object Lock with no local temp copy, writes a manifest you can read without a restore, and proves the setup with a restore test. | AWS account and CLI; `~/.config/secure_raw_data_backup/config.sh` |
| [`accounting`](./accounting/SKILL.md) | Field Museum p-card accounting: processes receipts into a Google Sheets expense log, assigns GL codes, reconciles against SmartData statements (including the 1% international fee), and builds entertainment supplement tables. | Run from your receipts folder; Google Sheets access |
| [`lab-ordering`](./lab_ordering/SKILL.md) | Turns lab members' supply requests into staged orders on Amazon Business, the Pritzker Lab form, or a vendor site, and stops for a human to review before anything is bought. | Browser control (Claude in Chrome or similar); `~/.config/lab_ordering/config.yaml` |

### `bioinfo-skills`

| Skill | What it does | Needs |
|---|---|---|
| [`busco-phylogeny`](./phylo_from_buscos/SKILL.md) | Builds phylogenomic pipelines from genome assemblies or NCBI accessions using BUSCO/compleasm single-copy orthologs. Generates scripts for SLURM, PBS, or a local machine, for both concatenated and coalescent trees. [Details](./phylo_from_buscos/README.md) | Conda (environment setup included) |
| [`biogeobears`](./biogeobears/SKILL.md) | Sets up BioGeoBEARS ancestral-range analyses in R: validates and reformats the tree and range files, writes an RMarkdown workflow comparing DEC, DIVALIKE, and BAYAREALIKE, and plots the results. [Details](./biogeobears/README.md) | R with BioGeoBEARS |

### `museum-skills` (Field Museum only)

| Skill | What it does | Needs |
|---|---|---|
| [`emu-bulk-upload`](./Emu_bulk_upload_FMNH/SKILL.md) | Helps insect collection staff bulk-upload specimen data to EMu: maps any input format to the EMu template, matches localities to existing site records, finds parent sites, and builds the upload tables. [Details](./Emu_bulk_upload_FMNH/README.md) | EMu exports of existing sites |
| [`nirc-badge-request`](./nirc_badge_request/SKILL.md) | Prepares NIRC ID badge requests (Scientific Affiliate, Visitor, Contractor), checks lead time and after-hours rules, and prefills the Google Form for a curator to review. Curators submit the form; other staff can draft. | Browser control; `~/.config/nirc_badge_request/config.yaml` |

## How these skills behave

- **You press submit.** Skills that touch forms, carts, or portals stage everything and stop. Claude doesn't place orders, submit forms, or send requests on its own.
- **No private details in the repo.** Names, URLs, accounts, and folder locations live in a local config file or your working folder, and the skill asks for them the first time you use it.
- **Checks before claims.** Where a mistake is costly, a script does the checking (checksums, citation lists, document formatting, page fit, missing receipts) instead of relying on Claude's reading.

## Install

### Claude Code

Add the marketplace once, then install the plugins you want:

```
/plugin marketplace add brunoasm/my_claude_skills
/plugin install general-skills@basm-claude-skills
/plugin install bioinfo-skills@basm-claude-skills
/plugin install museum-skills@basm-claude-skills
```

Claude Code will ask whether to install for yourself (user), for everyone working in the current project (project), or only for you in this project (local).

To get updates later:

```
/plugin marketplace update basm-claude-skills
```

The same commands work from the shell as `claude plugin ...`, e.g. `claude plugin install general-skills@basm-claude-skills --scope user`. To work from a local clone, add the marketplace by path (`/plugin marketplace add ./my_claude_skills`) and install the same way.

### Claude.ai and the desktop app

1. Download a skill's zip from the [latest release](https://github.com/brunoasm/my_claude_skills/releases/latest).
2. In Claude, go to [Customize → Skills](https://claude.ai/customize/skills) and upload the zip.
3. Turn the skill on.

Skills that run scripts need code execution, and skills that drive a browser work best in Claude Code or with Claude in Chrome.

## License

[Apache 2.0](./LICENSE)

## See also

- [Claude Code plugins](https://code.claude.com/docs/en/plugins)
- [Claude Code skills](https://code.claude.com/docs/en/skills)
