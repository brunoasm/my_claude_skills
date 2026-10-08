# Mock panel, red-team, and audit reviews

## 1. Build the sealed packet

1. Copy the **current** files only, from the canonical working copies named in the state of play. Record checksums (`md5sum` / `shasum`) of the originals and the copies, and compare. Cached or synced older copies on another machine have produced false findings before.
2. Rename files without status words (`v12_tracked`, `FINAL`, `DRAFT`) so reviewers are not primed.
3. In the packet copies only, accept tracked changes and delete comments. Never change the originals.
4. Add:
   - PDF renders of every document (`soffice --headless --convert-to pdf`).
   - Text extracts of every PDF (`pdftotext -layout`); OCR any scanned letters.
   - The funder's call and form preview, as text.
   - A README listing the files, what each is, and any known gaps (e.g., "letter X pending; fallback statement included").
5. Leave out: earlier reviews, project notes, correspondence, internal budget detail, the PI's comments, and anything else a real reviewer would not see.

## 2. Choose the reviewers

Match perspectives to the funder's criteria and the panel the funder actually uses. Run them in parallel with no access to each other or to anything outside the packet. Typical set:

| Agent | Perspective | Main questions |
|---|---|---|
| Panelist A | Domain specialist in the core method | Is the design sound and feasible? Are the hypotheses testable? Are risks handled? |
| Panelist B | Adjacent-field scientist | Is the significance clear to a non-specialist scientist? Is it novel? |
| Panelist C | End user or practitioner (manager, clinician, educator, industry) | Will the results change anything for people like me? Is the pathway believable? |
| Panelist D | Generalist or program-goal reviewer (training, broader impacts, equity, community) | Are the impact and training activities specific, integrated, and measurable? |
| Auditor E | Compliance and budget | Every formatting and content rule; limits; arithmetic; budget versus justification versus form; metadata; required sections present |
| Checker F | Cross-document fact-checker and copy editor | Every number, name, title, and date agrees across documents; citations match references; typos; undefined acronyms |

For NIH-style panels, include assigned primary, secondary, and discussant roles. For NSF, include at least one reviewer from outside the immediate subfield. When the program adds its own review criteria, give one reviewer those criteria as their main focus. For foundations, include someone who represents the foundation's mission.

**Dimension auditors** (run alongside the panel; each reads the whole packet for one thing):

| Agent | Checks |
|---|---|
| Rules | Every rule in the current call and policy guide, including supplements and notices issued during the cycle |
| Figures and tables | `scripts/figure_audit.py` output plus the rendered PDF: numbering, cross-references, legibility at print size, captions matching the text and the figures |
| Citations | `scripts/cite_check.py` output; methods cited at first use; prior art for novelty claims; claims stronger than the source |
| People | Every named person against letters, facilities or personnel text, budget, collaborators list; name forms; titles |
| Promises | Every activity, number, and claim against timeline, budget year, personnel-by-year, and assessment; each research question against its method |
| Budget | `scripts/budget_check.py` output (table arithmetic, totals the prose never states, amounts missing from the workbook); justification against workbook; caps and rates checked by hand against the requirements file, since the script does not check them |
| Structure | Required sections and headings; leftovers from cut scope; placeholders; section numbering |

## 3. Panelist prompt (adapt)

```
You are serving on a review panel for <funder, program>. You are <persona: field, career stage, what you care about>.

Read ONLY the files in <packet path>. Do not open any other file, note, or prior review, even if it appears in your context.

Read the call (<file>) first, then the application as a reviewer would.

Produce:
1. A score for each review criterion on the funder's scale (<criteria and scale>), each with 2–4 sentences of justification.
2. An overall score and a recommendation in the funder's terms.
3. Strengths (specific, with locations).
4. Weaknesses (specific, with page/section; most important first).
5. Questions you would raise in panel discussion.
6. The three changes that would most raise your score.

Be candid and specific. Quote the text you are reacting to.
```

## 4. Auditor prompt (adapt)

```
You are a compliance and budget auditor for <funder, program>. Read ONLY <packet path>.

Check every rule in the call (<file>) against every document: fonts and minimum sizes (including captions, tables, figure text), margins, spacing, page and character limits, required sections and headings, required content in each document and letter, file types.

Recompute every budget total from line items. Check year caps, total cap, indirect rate and base, salary caps, and agreement between budget, justification, online form, and any letter that states an amount.

Check document properties (title, author, company), tracked changes, comments, placeholders, hidden rows/columns.

Report a table: rule or item | document | finding | evidence | severity (stop-ship / important / minor).
```

## 5. Fact-checker prompt (adapt)

```
You are a cross-document fact-checker and copy editor. Read ONLY <packet path>.

Build a list of every number, name, title, date, site, and claim that appears in more than one document, and report every disagreement with exact locations.

Check that each in-text citation appears in the reference list and vice versa, and flag claims that look stronger than a typical source would support.

List typos, grammar errors, undefined acronyms, and inconsistent terms, with locations. Do not suggest stylistic rewrites; the author's voice is intentional.
```

## 6. Prior-review compliance prompt (resubmissions; adapt)

```
You are checking whether a revised application answers its previous reviews. Read the previous reviews and panel summary (<file>) and the current application (<packet path>).

For every critique (quote it), report: addressed / partly / not addressed / no longer applies (scope removed), the location of the change, and what a skeptical reviewer would still say. Start with the reasons given for the decision.

Then list strengths the reviews praised and say whether the revision kept them.
```

This agent must not share context with the blind panel.

## 7. Red-team prompt (adapt)

```
Your job is to find every reason this application could be rejected or returned without review. Read ONLY <packet path>.

Look for: missing or late documents, rule violations, unsupported or overstated claims, inconsistent numbers, placeholders, eligibility problems, letters that do not say what the call requires, and weaknesses a skeptical panelist would seize on.

Classify each as stop-ship (fix before submission), score lever (would change the score), or minor. Give location and a concrete fix.
```

## 8. Synthesis

Write one report for the PI:

1. **How it was run:** packet contents, what was excluded, agents and perspectives, any independence caveats.
2. **Scores:** table of criterion × reviewer, mean, recommendation. Add a trend table across rounds. Treat differences of about ±0.5 as noise.
3. **Resolved since last round.**
4. **Raised again, already decided by the PI:** list with the earlier decision. Do not re-argue.
5. **New issues:** table with ID, issue, which agents raised it, location, severity, owner. **Verify each one against the current files before including it.** Mark any that turn out to be artifacts of the packet. For a resubmission, flag any concern that a blind panelist raised and that also appeared in the previous reviews.
6. **Checked and not actionable:** findings that turned out to be wrong, with the evidence.
7. **Proposed action plan:** ordered by severity and effort, split by owner: narrative fixes (as tracked changes), PI decisions, other documents (checklist), sponsored-programs items (handoff memo), and checks only possible in Word or the submission system. Put blockers that depend on other people first.

## 9. Walk-through with the PI

Present the findings as a checklist (an interactive page with saved progress works well). For each item: show the problem in context, propose a minimal fix in the author's voice, and apply it only on the PI's decision. Log every decision, including "not done".
