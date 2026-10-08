---
name: grant-proposal-workflow
description: "Plan, write, edit, and review a multi-document grant application (NSF, NIH, foundations, internal awards): requirements, drafting, budgets, letters, citation checks, mock panel reviews, and the final submission package."
---

# Grant proposal workflow

Use this skill whenever someone is preparing a grant application that has more than one moving part: a project description, budget and budget justification, biosketch or CV, letters, data-management or mentoring plans, statements, an online form, and so on. It works for federal agencies (NSF, NIH, DOE, USDA), private foundations, and internal or institutional awards.

It covers the whole life of an application, not only the writing:

1. Setup: requirements, deadlines, folder structure
2. Gathering material and getting decisions from the PI
3. Drafting
4. Editing (with the author's voice preserved)
5. Budget
6. Citation verification
7. Letters and other people's documents
8. Mock panel and red-team reviews
9. Final submission package

**Guiding principles**

- **The funder's current solicitation is the source of truth.** Rules change between cycles. Never rely on memory of an agency's rules; read the current call, solicitation, or policy guide, and cite it.
- **The PI makes the calls.** Claude proposes, explains, and implements. Design decisions, claims about partners, budget choices, and anything submitted belong to the PI.
- **Everything is consistent, verified, and traceable.** Every number agrees across documents, every citation says what the text claims, and every edit is visible and reversible.
- **The author's voice is kept.** See section 4.

Reference files (read when the step comes up):

| File | Use it for |
|---|---|
| `references/requirements-template.md` | Building the requirements file in setup |
| `references/funder-patterns.md` | Typical structures and review criteria for NSF, NIH, and foundations, and what to verify in each current call |
| `references/tracking-templates.md` | Session notes, decisions log, numbers registry, letters tracker |
| `references/review-panel.md` | Prompts and procedure for mock panel, red-team, and audit agents |
| `references/final-checklist.md` | Per-file checks before upload |

Scripts (Python 3 standard library plus LibreOffice and poppler's `pdftotext`):

| Script | What it does |
|---|---|
| `scripts/docx_audit.py` | Flags fonts below a minimum size, disallowed fonts, condensed or expanded character spacing, narrow margins, Track Changes left on, unaccepted revisions, comments, placeholder markers, and leftover document metadata |
| `scripts/page_fit.py` | Renders a .docx to PDF and reports page count, where the body text ends, and how much space is left on the last page before a given heading (e.g., "References") |
| `scripts/cite_check.py` | Cross-checks author–year in-text citations against the reference list (and, optionally, a BibTeX file): cited but not listed, listed but not cited, year mismatches, "et al." in the reference list |

---

## 0. Every session

1. Read the project's state-of-play note, requirements file, decisions log, and latest session notes before changing anything. If they do not exist yet, go to section 1.
2. Check the clock: the funder deadline (with time zone), any internal institutional deadline (sponsored-programs offices often require files days earlier), and letter-writer lead times.
3. End the session with a short notes file: what was produced, what was decided, what is still open. Anything the PI decided is not re-proposed later.

## 1. Setup

**Requirements file.** Build it from the current call before writing anything (template in `references/requirements-template.md`): deadlines; award size, duration, per-year caps, indirect-cost rules, salary caps, eligible and ineligible costs; eligibility; review criteria quoted verbatim; formatting rules (fonts, minimum point size, margins, line spacing, character spacing, page limits and what counts toward them); every required document with its limit; every online-form field with its character limit; submission system and registration steps; contacts. State at the top that the source documents win on any conflict, and record the URL and access date of each source.

**Folder layout** (adapt names to the user's habits):

```
<grant>/
├── 00_admin/              registration, institutional info, working notes
├── 01_guidelines/         saved call, form preview, budget template, policy guide
├── 02_current/            ONLY the latest version of each document
│   └── drafts/            every earlier version
├── 03_supporting/         literature, preliminary data, figures + their source scripts,
│                          example funded proposals, correspondence, quotes
├── 04_final_submission/   exactly what is uploaded, in upload order
├── 98_bibliography/       reference-manager export + PDFs
└── 99_archive/
```

Name files `NN_<document>_vX[_tracked].ext`, where NN is the upload order.

**Find non-writing blockers on day one.** These cause most last-minute crises:

- Submission-system registration and roles (e.g., Research.gov, eRA Commons, Grants.gov/SAM.gov, or a foundation portal). Some take days or weeks.
- The institution's internal routing and approval deadline.
- Letters (institutional, reference, collaboration, support): who, by when, what they must say.
- Required forms only someone else can produce (institutional budget approvals, current-and-pending support, facilities statements).
- Anything recorded, signed, or notarized.

**Understand the funder.** Read the review criteria and any reviewer guidance. Look at what the program has funded before (public award abstracts, awardee pages) and at any example proposals the user has. Note anything a program officer said. Record prior awards from the same funder that must be disclosed.

## 2. Gather, then decide

- Collect literature into one reference-manager library and keep a short literature tracker (claim → source → page).
- List the **design decisions that drive the numbers** (sample sizes, sites, schedule, staffing, optional components). Get the PI's decision on each before drafting methods or the budget; log them.
- Make a **criteria map**: each review criterion and program goal → where the proposal answers it.
- Keep a "parked text" file for good material that does not fit, instead of deleting it.

## 3. Drafting

- Mirror the funder's required section headings and order so reviewers find each answer where they expect it.
- Answer every prompt in the call explicitly, including small ones that are easy to miss (e.g., how stakeholders shaped the design, status of each collaboration, data-sharing, mentoring, broader impacts).
- Make the payoff concrete. Name who uses the results, what they will do differently, and what they receive. For agencies with a separate impact criterion (NSF Broader Impacts, foundation "impact" or "action" criteria), give specific activities, audiences, and measures, not intentions.
- **Claims about partners must be backed by their letters.** Keep a list of letter-versus-proposal mismatches and close each one.
- Keep a **numbers registry** (template in `references/tracking-templates.md`): totals, counts, sample sizes, dates, titles, names, amounts. After every change, check every document against it. A stale number in one cell is the most common late error.
- State risks and limitations plainly, each with a mitigation or fallback.
- Keep figure source code and data beside each figure so it can be rebuilt; check captions against the methods text.
- Never invent the science. If a hypothesis, method, or result is not in the material, insert `[CLARIFY: …]` and ask the PI.

## 4. Editing rules

### Preserve the author's voice

Unless the author asks for a rewrite or a different tone, every edit keeps the original author's tone and voice:

- Make the smallest change that fixes the problem. Prefer cutting to rephrasing, and rephrasing a phrase to rewriting a sentence.
- Keep the author's word choices, terminology, sentence rhythm and length, person (I / we), level of formality, hedging style, and spelling variant (US or UK).
- Do not add stock phrases the author does not use ("crucially", "leverage", "delve", "this underscores", "a robust framework", em-dash asides, rule-of-three lists). Do not smooth distinctive phrasing into generic prose.
- When new text is needed, model it on the author's own sentences nearby and keep it short.
- When an edit would change meaning, emphasis, or a claim, do not apply it silently. Leave a comment with the suggestion and the reason.
- For documents written by other people (letters, co-authors' sections), keep their voice, not the PI's, and limit changes to what the PI asked for.
- The author can override this (e.g., "make this more formal", "rewrite freely"). Record overrides in the decisions log.

### Make every change visible and reversible

- **Never overwrite.** Write the next version as a new file in `02_current/`, then move the previous version to `drafts/` without overwriting anything there (`mv -n`). Do not move or edit a file that is open in Word (check for `~$` lock files); say so and leave it.
- **Start from the author's latest file**, not Claude's last output, whenever the author has edited in between.
- **Word documents:** make edits as tracked changes attributed to "Claude", with a comment on any edit that is not self-explanatory. When porting another person's edits from a separate copy, attribute them as "<Name> (via Claude)". If a docx skill with a redlining workflow is available, use it.
- **Spreadsheets:** there are no tracked changes, so fill edited cells with a highlight color and give a clean copy without highlights for upload. Formulas written by a script have no cached values until the workbook is opened and saved in Excel or LibreOffice; check that values are stored before submission.
- **House style:** record the author's style choices (serial comma, preferred terms, capitalization, citation style) in the decisions log and apply them consistently.
- **Page fit:** after each edit, run `scripts/page_fit.py` and report where the body ends and how much room is left. Fix overflow with content cuts or paragraph spacing, never by going below the funder's font, margin, or spacing rules. Word and LibreOffice paginate slightly differently, so ask the author to confirm the final fit in Word.
- When the author declines a suggestion, log it as "not done, author's choice" and do not raise it again.

## 5. Budget

- Write down the hard rules from the call (total cap, per-year cap, indirect rate and base, excluded costs, salary or effort caps, equipment threshold, participant-support rules, cost-share rules) and check them after every change.
- Recompute every total independently. Make sure rounded year, category, and indirect totals add up exactly. Report remaining headroom per year and overall.
- The budget justification follows the budget line by line, in the same order and with the same numbers, and explains anything uneven or unusual. Use the agency's required headings (e.g., NSF budget categories A–I; NIH modular vs. detailed).
- Keep an internal detailed workbook with per-line rationale and quotes; it is useful for progress reports later.
- Log items considered and dropped, with the reason.
- Check that the workbook prints legibly (all columns on one page if required) and that no hidden rows or columns carry amounts.
- Confirm institutional rates (fringe, indirect, salary escalation) with the sponsored-programs office rather than guessing.

## 6. Citation verification

- For any claim a reviewer could challenge (numbers, "first", "only", trends, effect sizes), check it against the **primary source**, not an abstract or memory. Record a verdict for each part of the claim (supported / partly / not in source) with page numbers, and propose a fix with its length cost.
- Run `scripts/cite_check.py` to reconcile in-text citations, the reference list, and the reference-manager export. Report what is missing or unused. Give the author corrected entries for their reference manager rather than editing their library.
- Check the funder's citation rules (e.g., some require all author names; NSF and NIH have their own reference-list expectations).
- Do not accept a review agent's correction of a citation without checking the source yourself; agents are wrong often enough to matter.
- Flag anything you could not verify (paywalled, in press, advance online without pages).

## 7. Letters and other people's documents

- Keep a letters tracker (template in `references/tracking-templates.md`).
- Offer writers a short brief or draft consistent with the proposal's claims, names, and dates, and in the writer's voice. Check the funder's rules first: some agencies restrict letter content (e.g., NSF letters of collaboration are limited to a statement of intent to collaborate).
- On receipt: file the final, keep the as-received copy, list typos and any statement that contradicts the proposal, and let the PI decide whether a re-signed version is worth asking for.
- If a required letter will not arrive, use the funder's sanctioned fallback (often a short explanation) and adjust how the collaboration is described.
- If the submission system takes one file per slot, merge letters into one PDF in a stated order.

## 8. Reviews

Plan at least two full review rounds before the deadline, plus a last pass on the exact files to be uploaded. Procedures and agent prompts are in `references/review-panel.md`. In short:

- **Mock panel.** Build a sealed packet (final files only, rendered to PDF and text, plus the call). Leave out notes, earlier reviews, and correspondence so reviewers read the application cold. Stage it from wherever the current files actually live and confirm with checksums; synced or cached older copies produce false findings. Run independent reviewer agents in parallel, each with a distinct perspective matched to the funder's criteria and review culture, plus a compliance-and-budget auditor and a cross-document fact-checker. Each scores using the funder's own criteria and scale.
- **Synthesis.** A score table and trend across rounds (treat differences of about half a point as noise), what is resolved, issues raised again that the PI already decided (listed, not re-argued), new issues with exact locations, and items checked and found not to be problems. Verify every new finding against the current files before reporting it.
- **Red team.** Same packet; agents hunt for stop-ship problems: missing documents, rule violations, inconsistent numbers, placeholders, unsupported claims.
- **Walk-through.** Present findings as a checklist and go through them with the PI one at a time: show the problem in context, propose the fix, apply it on their decision, log it.
- **Colleague or institutional edits.** Merge them into the current version as attributed tracked changes. Skip edits to text that has since been rewritten, and note anything not taken as written.

## 9. Final submission package

- `04_final_submission/` holds exactly what will be uploaded, in upload order, named clearly (e.g., `01_<PI>_ProjectDescription.pdf`), with a README table of slot, file, and what was verified. Keep clean source files and confirmations in subfolders.
- Run `scripts/docx_audit.py` on every Word source and work through `references/final-checklist.md` for every file.
- Prepare online-form answers in a paste-ready document with character counts beside every limited field. Recount after every edit.
- **Claude may prepare and stage uploads and form entries, but the PI presses submit.** If asked to submit, first restate exactly what will be submitted and what that commits them to, and get explicit confirmation.
- Save the submission confirmation and record the submission in the notes.

## Common failures

- Submission-system registration, roles, or institutional approval discovered too late.
- An institutional letter missing required content (committed resources, mission alignment) or with title or name mismatches.
- One stale number left in a budget cell or form field after the other documents were updated.
- Track Changes left on, or comments left in, an uploaded file; author metadata from a template.
- Captions, tables, or figure text below the minimum point size.
- Character-limited fields filled to within a few characters, then edited.
- Reviewing an outdated synced copy instead of the current file.
- A collaboration described as established with no letter to support it.
- Edits that quietly flatten the author's voice into generic prose.
