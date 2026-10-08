---
name: grant-proposal-workflow
description: "Plan, write, edit, and review a multi-document grant application or resubmission (NSF, NIH, foundations, internal awards, and any program with its own solicitation): requirements, drafting, budgets and justifications, letters, citation and figure checks, cross-document consistency, mock panel reviews, and the final submission package."
---

# Grant proposal workflow

Use this skill whenever someone is preparing a grant application that has more than one moving part: a project description, budget and budget justification, biosketch or CV, letters, data-management or mentoring plans, statements, an online form, and so on. It works for federal agencies (NSF, NIH, DOE, USDA), private foundations, and internal or institutional awards, and for new applications and resubmissions alike.

It covers the whole life of an application, not only the writing:

1. Setup: requirements, deadlines, folder structure, who owns what
2. Gathering material and getting decisions from the PI (resubmissions: start from the reviews)
3. Drafting, with every promise traced to a timeline row, a budget line, and an assessment
4. Editing (with the author's voice preserved)
5. Budget
6. Citation and figure verification
7. Letters and other people's documents
8. Mock panel and red-team reviews
9. Final submission package, then closing the project out

**Guiding principles**

- **The funder's current solicitation is the source of truth.** Rules change between cycles. Never rely on memory of an agency's rules; read the current call, solicitation, or policy guide, and cite it.
- **The PI makes the calls.** Claude proposes, explains, and implements. Design decisions, claims about partners, budget choices, and anything submitted belong to the PI. Items owned by the sponsored-programs office (budget upload, institutional certifications, rates) belong to them; Claude prepares a clear handoff.
- **Everything is consistent, verified, and traceable.** Every number agrees across documents, every citation says what the text claims, every named person has the paperwork the funder requires, and every edit is visible and reversible.
- **The author's voice is kept.** See section 4.
- **The PI's hand edits are never overwritten.** Reload the live file before every edit and patch it in place; never regenerate a document, tracker, or spreadsheet the PI may have touched from a script or from Claude's last output.

Reference files (read when the step comes up):

| File | Use it for |
|---|---|
| `references/requirements-template.md` | Building the requirements file in setup |
| `references/funder-patterns.md` | Orientation on typical structures and review criteria for NSF, NIH, and foundations; what to look for in the program's own documents |
| `references/resubmission.md` | Turning prior reviews into a revision plan; scope cuts and their leftovers; year shifts |
| `references/tracking-templates.md` | State of play, session notes, decisions log, numbers registry, people roster, promise traceability matrix, scope-change log, letters tracker, sponsored-programs handoff memo |
| `references/review-panel.md` | Prompts and procedure for mock panel, red-team, audit, and prior-review compliance agents |
| `references/final-checklist.md` | Per-file checks before upload |

Scripts (Python 3 standard library plus LibreOffice and poppler's `pdftotext`/`pdffonts`):

| Script | What it does |
|---|---|
| `scripts/docx_audit.py` | Flags body, caption, and table text below separate minimum sizes; disallowed fonts; condensed or expanded spacing; narrow margins; Track Changes left on; unaccepted revisions (by author); comments; placeholders (`XXX`, `XX%`, `X to Y`, lorem ipsum, `(CITE …)`, `(REF)`) and keyboard-mash filler; hidden content that ships inside the .docx (reference-manager field codes with embedded abstracts, hidden text, flag terms); document metadata |
| `scripts/page_fit.py` | Renders a .docx to PDF and reports page count, where the body ends (before a "References" heading, or before a numbered reference list that runs to the end of the document), space left on the last page, and fonts that had to be substituted (metric-compatible stand-ins are noted separately; other substitutes make the fit approximate) |
| `scripts/cite_check.py` | Cross-checks in-text citations against the reference list, which can be a separate file (`--refs`), a heading, or a reference-manager bibliography field. Numbered (`[12, 14–16]`) and author–year styles; optional BibTeX check |
| `scripts/budget_check.py` | Checks Total rows and columns in the justification's tables, lists table totals the prose never states, and lists dollar amounts that do not appear among the budget workbook's stored values (catches stale summary tables and formulas with no stored value) |
| `scripts/figure_audit.py` | Caption numbering gaps and duplicates, citations to missing figures or tables, first-mention order, printed size and format of every image, EMF/WMF figures whose text cannot be checked, floating images and captions in text boxes, images anchored in headings, detached table captions |

---

## 0. Every session

1. Read the project's state-of-play note, requirements file, decisions log, and latest session notes before changing anything. If they do not exist yet, go to section 1. The state of play names the **canonical working copy** of each document (one location only); work there and nowhere else.
2. Check the clock: the funder deadline (with time zone), any internal institutional deadline (sponsored-programs offices often require files days earlier), and letter-writer lead times.
3. Before editing any file, reload it from disk and check for a newer-dated or newer-versioned copy and for an open-in-Word lock file (`~$…`). The PI may have edited it since the last session.
4. When a sub-area builds up its own conventions (letters, budget, facilities), keep them in a short notes file in that folder and point to it from the state of play, instead of growing one long memory file.
5. End the session with a short notes file: what was produced, what was decided, what is still open, who owns each open item. Anything the PI decided is not re-proposed later.

Files in cloud-synced folders can be offline placeholders that fail to open from a shell ("Resource deadlock avoided" on macOS iCloud, zero-byte reads). Fetch them through the sync client or ask the PI to download them; do not conclude the file is empty.

## 1. Setup

**Start from the guidelines.** Before planning or writing anything, collect the program's own documents: the current call, solicitation, or funding opportunity, and every document it links to or mentions. That usually includes the general proposal guide it defers to (e.g., NSF's PAPPG, NIH's application guide), policy notices and supplements in effect, the program's FAQ, templates and form previews, budget instructions, and reviewer guidance. Read each one, and follow its references in turn wherever they set rules (a guide that points elsewhere for formatting, eligibility, or a required form). Save each to `01_guidelines/` with its URL, version, and access date, extract the text, and confirm every page came through; a truncated local copy silently drops rules. If a document cannot be downloaded (behind a login, only inside a portal), list it and ask the PI for it. Where a solicitation differs from the general guide, the solicitation governs unless it says otherwise.

Every program is handled this way, including those with their own rules (career awards, collaborative or multi-institution proposals, centers, training grants, fellowships): the extra requirements come from that program's documents, not from memory or from this skill. `references/funder-patterns.md` is only orientation on what to look for.

**Requirements file.** Build it from those documents before writing anything (template in `references/requirements-template.md`): deadlines; award size, duration, per-year caps, indirect-cost rules, salary caps, eligible and ineligible costs; eligibility; review criteria quoted verbatim; formatting rules (fonts, minimum point size and any exceptions for captions or tables, margins, line spacing, character spacing, page limits and what counts toward them); every required document with its limit and owner; every online-form field with its character limit; submission system and registration steps; contacts. State at the top that the source documents win on any conflict, and cite the document and section for each rule. Include every program-specific requirement: extra documents, letters, criteria, eligibility conditions, and budget minimums or maximums.

**Folder layout** (adapt names to the user's habits; detect whether they version by date in the file name or by `vN`, and follow it):

```
<grant>/
├── 00_admin/              registration, institutional info, working notes
├── 01_guidelines/         saved call, form preview, budget template, policy guide
├── 02_current/            ONLY the latest version of each document
│   └── drafts/            every earlier version
├── 03_supporting/         literature, preliminary data and the code that produced it,
│                          figures + their source scripts, prior cycle's submission and
│                          reviews, example funded proposals, correspondence, quotes
├── 04_final_submission/   exactly what is uploaded, in upload order
├── 98_bibliography/       reference-manager export + PDFs
└── 99_archive/
```

Name files `NN_<document>_vX[_tracked].ext` (or `<document>_YYYYMMDD.ext` if that is the PI's habit), where NN is the upload order.

**Find non-writing blockers on day one.** These cause most last-minute crises:

- Submission-system registration and roles (e.g., Research.gov, eRA Commons, Grants.gov/SAM.gov, or a foundation portal). Some take days or weeks.
- The institution's internal routing and approval deadline, and what the sponsored-programs office will do itself (enter the budget, certify, check boxes on the cover sheet).
- Eligibility that depends on someone else's statement, especially for non-standard appointments (museum, government, or research-institute positions applying to programs written for faculty). Get it confirmed in writing early.
- Letters (departmental or institutional, reference, collaboration, support): who, by when, what they must say. A missing required institutional letter can mean return without review.
- Documents that live only inside the submission system or a profile tool (biosketch, current and pending support, collaborators list, data-management web forms, cover-sheet certifications). They will never appear in the project folder, so track them by name in the requirements file and confirm each one explicitly.
- Anything recorded, signed, or notarized.

**Understand the funder.** Read the review criteria and any reviewer guidance. Look at what the program has funded before (public award abstracts, awardee pages) and at any example proposals the user has. Note anything a program officer said, verbatim where possible. Record prior awards from the same funder that must be disclosed, and decide early whether a "results from prior support" section is required.

**Resubmission?** Read `references/resubmission.md` now. The prior reviews, the previous submission as actually submitted, and the program officer's comments are the most valuable inputs you have.

## 2. Gather, then decide

- Collect literature into one reference-manager library and keep a short literature tracker (claim → source → page).
- List the **design decisions that drive the numbers** (sample sizes, sites, countries, schedule, staffing and which years each person is paid, optional components). Get the PI's decision on each before drafting methods or the budget; log them.
- Make a **criteria map**: each review criterion and program goal → where the proposal answers it.
- Start the **people roster** and the **promise traceability matrix** (templates in `references/tracking-templates.md`). Both are cheap to keep and catch the most common cross-document errors.
- Keep a "parked text" file for good material that does not fit, instead of deleting it.
- Treat output from deep-research tools, literature agents, and summaries as leads, not facts. Verify every date, name, age, count, and citation year against a primary source before it goes into the proposal; these tools get nomenclature and years wrong often enough to matter.
- When preliminary results are generated for the proposal (models, analyses, pilot data), keep the code and results files in the project, and record for each number in the text the file it came from.

## 3. Drafting

- Mirror the funder's required section headings and order so reviewers find each answer where they expect it.
- Answer every prompt in the call explicitly, including small ones that are easy to miss (e.g., how stakeholders shaped the design, status of each collaboration, data-sharing, mentoring, broader impacts, and any prompt specific to the program).
- Make the payoff concrete. Name who uses the results, what they will do differently, and what they receive. For agencies with a separate impact criterion (NSF Broader Impacts, foundation "impact" or "action" criteria), give specific activities, audiences, committed numbers, and measures of learning or change, not only reach or intentions.
- **Trace every promise.** Each activity, audience size, deliverable, or claim made in the vision, summary, or aims must appear as an activity with a timeline row, a budget line in the right year (or a stated reason it costs nothing), the people who will be on the project that year, and an assessment measure. Each research question must be answerable by the method proposed for it. Update the promise traceability matrix as you write.
- **Claims about partners must be backed by their letters.** Every person named as contributing should appear consistently in the people roster: role in the narrative, letter, facilities or personnel description, budget line if any, collaborators list. Close both kinds of orphan: named without a letter, and a letter for someone the proposal no longer mentions.
- Keep a **numbers registry** (template in `references/tracking-templates.md`): totals, counts, sample sizes, dates, titles, names, amounts. After every change, check every document against it. A stale number in one cell is the most common late error.
- **Propagate every scope change.** When an activity, site, country, person, or year changes, log it in the scope-change log and search every document for the old term: narrative, summary, figures and their captions, timeline table, budget and justification, spreadsheet labels, facilities, mentoring plan, data plan, letters. Text inside image figures cannot be searched; list those figures for the PI to fix in the source file.
- State risks and limitations plainly, each with a mitigation or fallback, for the education and outreach components as well as the research.
- Keep figure source code and data beside each figure so it can be rebuilt; check captions against the methods text.
- Never invent the science. If a hypothesis, method, or result is not in the material, insert `[CLARIFY: …]` and ask the PI. Mark every placeholder with one of the conventions `scripts/docx_audit.py` detects, never with filler text.

## 4. Editing rules

### Preserve the author's voice

Unless the author asks for a rewrite or a different tone, every edit keeps the original author's tone and voice:

- Make the smallest change that fixes the problem. Prefer cutting to rephrasing, and rephrasing a phrase to rewriting a sentence.
- Keep the author's word choices, terminology, sentence rhythm and length, person (I / we), level of formality, hedging style, and spelling variant (US or UK).
- Do not add stock phrases the author does not use ("crucially", "leverage", "delve", "this underscores", "a robust framework", em-dash asides, rule-of-three lists). Do not smooth distinctive phrasing into generic prose.
- When new text is needed, model it on the author's own sentences nearby and keep it short. For a large rewrite (a whole section), draft it in a separate file for the PI to review before it goes into the document.
- When an edit would change meaning, emphasis, or a claim, do not apply it silently. Leave a comment with the suggestion and the reason.
- For documents written by other people (letters, co-authors' sections), keep their voice, not the PI's, and limit changes to what the PI asked for.
- The author can override this (e.g., "make this more formal", "rewrite freely"). Record overrides in the decisions log.

### Make every change visible and reversible

- **Never overwrite.** Write the next version as a new file, then move the previous version to `drafts/` without overwriting anything there (`mv -n`). Do not move or edit a file that is open in Word (check for `~$` lock files); say so and leave it.
- **Start from the author's latest file**, not Claude's last output, whenever the author has edited in between. For spreadsheets and trackers the PI edits by hand, change only the specific cells (load the existing workbook and write those cells); never rebuild the sheet.
- **Word documents:** make edits as tracked changes, with a comment on any edit that is not self-explanatory. Ask the PI once which author name to use ("Claude" by default; some PIs want their own name or a label such as "Budget reconciliation") and record it in the decisions log. When porting another person's edits from a separate copy, attribute them as "<Name> (via Claude)". If a docx skill with a redlining workflow is available, use it.
- **Citations in managed documents:** when the document uses a reference manager (Zotero, EndNote, Mendeley), never type citations as plain text. Insert a tracked placeholder such as `(CITE: Author Year, topic)` and give the PI the list to insert as live fields. Problems in the reference manager's data (a wrong year, an abstract full of unrelated text) are fixed in the library and then refreshed, not in the document XML, or the next refresh brings them back.
- **Spreadsheets:** there are no tracked changes, so fill edited cells with a highlight color and give a clean copy without highlights for upload. Formulas written by a script have no cached values until the workbook is opened and saved in Excel or LibreOffice; check that values are stored before submission. Text labels that quote numbers ("tuition $12,000 + fees $2,000") go stale when the numbers change; check them too.
- **House style:** record the author's style choices (serial comma, preferred terms, capitalization, citation style, name forms for people) in the decisions log and apply them consistently.
- **Page fit:** after each edit, run `scripts/page_fit.py` and report where the body ends and how much room is left. Fix overflow with content cuts or paragraph spacing, never by going below the funder's font, margin, or spacing rules. If the script reports substituted fonts, or the document has EMF figures or floating images, the count is approximate: ask the author to confirm the final fit in Word.
- When the author declines a suggestion, log it as "not done, author's choice" and do not raise it again.

## 5. Budget

- **Work in the grant's own budget template.** Each funder, program, or institution supplies its own: a workbook from the call, the sponsored-programs office's spreadsheet, or a form entered directly in the submission system. Find out which one is the version that will be submitted, and who enters it. Never build a budget in a format of your own and port it later.
- **Learn the template before entering anything.** Map its sheets, year columns, categories, and rows; which cells are inputs and which are formulas; how it computes fringe, escalation, indirect costs and their base, and totals; any built-in caps or checks; and its instructions tab. Write that map into a short budget notes file and confirm anything unclear with the PI or the sponsored-programs office. Enter numbers only in input cells; do not overwrite, move, or restructure formulas, rows, or sheets. If the template cannot hold something the budget needs, ask rather than adding rows.
- If the budget lives only in the submission system, keep a mirror of its exact fields and categories in a working sheet, and reconcile it field by field against what was entered.
- Write down the hard rules from the call (total cap or minimum, per-year cap, indirect rate and base, excluded costs, salary or effort caps, equipment threshold, participant-support rules, cost-share rules) and check them after every change. A template's built-in checks may lag the current call; the call wins.
- Recompute every total independently of the template's formulas. Make sure rounded year, category, and indirect totals add up exactly. Report remaining headroom per year and overall.
- The budget justification follows the budget line by line, in the template's categories and order and with the same numbers, and explains anything uneven or unusual. Use the headings the funder requires.
- **Summary tables drift.** Section headers, by-year tables, and "annual totals" sentences inside the justification are where stale numbers hide, especially after someone else edits a line item. Run `scripts/budget_check.py JUSTIFICATION.docx --xlsx BUDGET.xlsx` after every change by anyone, and resolve each FAIL and each unexplained CHECK.
- Keep a **personnel-by-year matrix** (who is paid in which years) and check every activity against it: no fieldwork, conference travel, or deliverable in a year when the person doing it is off the budget, unless the text says who does it instead.
- Keep an internal itemized worksheet beside the template (never in place of it) with per-line rationale and quotes (airfare, per diem, lodging, registration, rates). When figures are carried from an earlier proposal, say so and note what changed. It is useful for the sponsored-programs office and for progress reports later.
- Record the source and fiscal year of every external rate (tuition, fees, insurance, stipends, per diem, service fees), since partner institutions quote next year's figures differently.
- How to classify payments to outside organizations (subaward, contract for services, consultant) changes the indirect-cost treatment and the paperwork, and foreign organizations draw extra scrutiny. Let the sponsored-programs office decide; then make the narrative, the budget category, and the justification use the same term.
- Log items considered and dropped, with the reason, and list them as "already resolved, do not re-raise" in any memo to the sponsored-programs office.
- Once the sponsored-programs office has entered or uploaded the budget, that version is the version of record. Freeze it, and bring the justification and narrative into line with it rather than the reverse.
- Check that the workbook prints legibly (all columns on one page if required) and that no hidden rows or columns carry amounts.
- Confirm institutional rates (fringe, indirect, salary escalation) with the sponsored-programs office rather than guessing.

## 6. Citation and figure verification

- For any claim a reviewer could challenge (numbers, "first", "only", trends, effect sizes), check it against the **primary source**, not an abstract or memory. Record a verdict for each part of the claim (supported / partly / not in source) with page numbers, and propose a fix with its length cost. Watch "first" claims against the proposal's own tables and prior work.
- Run `scripts/cite_check.py` to reconcile in-text citations, the reference list, and the reference-manager export. If the funder wants the reference list as a separate document, check against that file with `--refs`. Report what is missing or unused. Give the author corrected entries for their reference manager rather than editing their library.
- Check that methods are cited where they are first used (the method's original paper, not only a software implementation) and that the prior art for any novelty claim is cited.
- Check the funder's citation rules (e.g., some require all author names; NSF and NIH have their own reference-list expectations).
- Do not accept a review agent's correction of a citation without checking the source yourself; agents are wrong often enough to matter.
- Flag anything you could not verify (paywalled, in press, advance online without pages).
- Run `scripts/figure_audit.py` on the narrative. Fix numbering gaps and dangling cross-references; list for the PI any figure under about 1.5 inches tall, any EMF/WMF figure, and any figure a past reviewer called hard to read, and ask the PI to check them at 100% in the PDF. Remind the PI to update fields in Word (select all, F9) before exporting so caption numbers match.

## 7. Letters and other people's documents

- Keep a letters tracker (template in `references/tracking-templates.md`) with a fixed status list (not started, drafted, sent, received, will not request).
- Check the funder's rules first: some agencies restrict letter content and format (e.g., NSF letters of collaboration are limited to a standard statement of intent to collaborate, with no endorsement).
- Use two templates: the PI's institution letterhead for colleagues at the same institution, and a version with a "[your institution's letterhead]" placeholder for everyone else. Check each template's fonts and margins against the funder's rules; institutional letterheads often fail them.
- Before drafting, confirm each writer's current title and affiliation from their institution's web page; do not reuse last cycle's title. For a resubmission, compare each draft side by side with the writer's previously signed letter (name, title, organization, project title, standard wording).
- Offer writers a short brief or draft consistent with the proposal's claims, names, and dates, and in the writer's voice.
- On receipt: file the final, keep the as-received copy, check the date (a future or last-year date happens), the signature, and that a scanned PDF actually shows the letter (an empty text layer means a scan; render it and look). List typos and any statement that contradicts the proposal, and let the PI decide whether a re-signed version is worth asking for.
- When scope changes affect what a collaborator does or is paid, draft an email that explains the change plainly, states what is unchanged, and asks them to confirm or adjust the affected figure rather than assuming a new number.
- If a required letter will not arrive, use the funder's sanctioned fallback (often a short explanation) and adjust how the collaboration is described.
- If the submission system takes one file per slot, merge letters into one PDF in a stated order.

## 8. Reviews

Plan at least two full review rounds before the deadline, plus a last pass on the exact files to be uploaded. Procedures and agent prompts are in `references/review-panel.md`. In short:

- **Mock panel.** Build a sealed packet (final files only, rendered to PDF and text, plus the call). Leave out notes, earlier reviews, and correspondence so reviewers read the application cold. Stage it from the canonical working copies and confirm with checksums; synced or cached older copies produce false findings. Run independent reviewer agents in parallel, each with a distinct perspective matched to the funder's criteria and review culture, plus a compliance-and-budget auditor and a cross-document fact-checker. Each scores using the funder's own criteria and scale.
- **Dimension audit.** In parallel, run narrow auditors that each check one thing across all documents: compliance with the current rules, figures and tables, citations, the people roster, the promise traceability matrix, the budget, and structural coherence (sections, numbering, leftovers from cut scope).
- **Prior-review compliance (resubmissions).** One separate agent gets the prior reviews and the current packet and reports, critique by critique, whether the revision answers it and where. Keep this agent apart from the blind panel.
- **Synthesis.** A score table and trend across rounds (treat differences of about half a point as noise), what is resolved, issues raised again that the PI already decided (listed, not re-argued), new issues with exact locations, and items checked and found not to be problems. Verify every new finding against the current files before reporting it. When a blind panelist independently raises a concern that sank the previous submission, say so prominently: it is the strongest signal in the round.
- **Red team.** Same packet; agents hunt for stop-ship problems: missing documents, rule violations, inconsistent numbers, placeholders, unsupported claims.
- **Triage by owner.** Split findings into: fix in the narrative (Claude drafts as tracked changes), PI decision needed, other documents (checklist), sponsored-programs office (handoff memo), and checks only possible in Word or the submission system (list for the PI). Blockers that depend on other people go first.
- **Walk-through.** Present findings as a checklist and go through them with the PI one at a time: show the problem in context, propose the fix, apply it on their decision, log it.
- **Colleague or institutional edits.** Merge them into the current version as attributed tracked changes. Skip edits to text that has since been rewritten, and note anything not taken as written.

## 9. Final submission package

- `04_final_submission/` holds exactly what will be uploaded, in upload order, named clearly (e.g., `01_<PI>_ProjectDescription.pdf`), with a README table of slot, file, and what was verified. Keep clean source files and confirmations in subfolders.
- Run `scripts/docx_audit.py` on every Word source and work through `references/final-checklist.md` for every file. Clear the hidden content it reports when the .docx itself is uploaded or shared; the PDF does not carry field codes.
- Export upload PDFs on a machine that has the document's fonts (usually the PI's, from Word). A PDF rendered with substituted fonts can change pagination and break the font rules.
- Prepare online-form and web-form answers (summaries, data-management web forms) in a paste-ready document organized by the form's own fields and options, with character counts beside every limited field. Recount after every edit.
- **Claude may prepare and stage uploads and form entries, but the PI presses submit.** If asked to submit, first restate exactly what will be submitted and what that commits them to, and get explicit confirmation.
- Save the submission confirmation and the submitted PDF as assembled by the funder's system, and record the submission in the notes.

**After submission:** move superseded files to the archive, keep the state of play pointing at the version of record, and write a short lessons-learned note (what went late, what the scripts caught, what to start earlier). When reviews arrive, transcribe them into a text file beside the submission so the next cycle starts from `references/resubmission.md`.

## Common failures

- Submission-system registration, roles, eligibility confirmation, or a required institutional letter discovered too late.
- A required document that lives only in the submission system, assumed done because nobody looked.
- An institutional letter missing required content (committed resources, mission alignment) or with title or name mismatches.
- One stale number left in a budget cell, a summary table inside the justification, a spreadsheet label, or a form field after the other documents were updated.
- An activity promised in the narrative with no budget line in that year, or done by someone who is no longer on the payroll that year.
- Leftovers of cut scope: a timeline row, a figure label, a caption, a "potential challenges" sentence, a collaborator, or a letter for work that was dropped.
- A collaborator named in the narrative with no letter, or a letter from someone the narrative no longer mentions.
- Track Changes left on, or comments left in, an uploaded file; author metadata from a template.
- Text below the minimum size where the funder allows no exception (check whether captions and tables have one); figures too small to read, which reviewers do mention.
- Figure numbers that skip, or cross-references to the wrong table, after figures are added or removed.
- Page count checked with substituted fonts or with the reference list still inside the project description.
- Character-limited fields filled to within a few characters, then edited.
- Reviewing an outdated synced copy instead of the canonical file.
- Facts from a research-agent report used without checking the primary source.
- Edits that quietly flatten the author's voice into generic prose.
