# Tracking templates

Short, plain files the project keeps up to date. Store them in `00_admin/notes/` (create it if needed) unless the PI already keeps project notes elsewhere, and point to them from the state of play so future sessions find them.

## State of play (one file, rewritten when things change)

```markdown
# <Grant>: state of play (<date>)
**Clock:** internal deadline …; funder deadline …
**Canonical working copies:** the one location where each document is edited (sync outward from here)
**Version of record:** anything already uploaded or entered by someone else (e.g., budget entered by sponsored programs on <date>)
**Documents:** table of each required document → current file → status → owner (PI / Claude / sponsored programs / collaborator)
**Lives only in the submission system:** biosketch, current & pending, collaborators list, data-plan web form, cover-sheet certifications → status
**Bibliography:** reference manager (<which>, latest export <date>) or local library in `98_bibliography/`; inbox last processed <date>
**Sub-workflow notes:** letters → <path>; budget → <path>
**Blocking, not writing:** registrations, letters, approvals, recordings
**Open decisions:** …
**Next steps (owner):** …
```

## Session notes (one per working session)

File name: `<topic>-<YYYY-MM-DD>.md`

```markdown
# <What was done> (<date>)
**Files produced:** new file → based on → moved to drafts/
**Changes:** grouped by document; one line each
**Decisions (PI):** done / not done by the author's choice
**Checks:** page fit, numbers registry, validation
**Still open:** …
```

## Decisions log (append-only)

| Date | Decision | Decided by | Reason | Affects |
|---|---|---|---|---|

Include style decisions (serial comma, terminology), voice overrides ("rewrite freely in section 2"), and suggestions declined, so they are not raised again.

## Numbers registry

Every number, name, or date that appears in more than one document.

| Item | Value | Source of truth | Appears in (document, location) | Last checked |
|---|---|---|---|---|
| Total request | | budget workbook | form, justification, institutional letter | |
| Sample size / sites | | methods | summary, budget, timeline figure | |
| Personnel and effort | | budget | justification, management plan | |
| Partner names and titles | | letters | proposal, collaborations section | |

After any change, search every document for the old value.

## People roster

Every person named anywhere in the application. Fill one row per person and close every gap.

| Person (one name form) | Current title, institution (verified on) | Role in narrative (sections) | Letter (status) | Facilities / personnel text | Budget line | Collaborators list | Notes |
|---|---|---|---|---|---|---|---|

Gaps to look for: named without a letter; a letter for someone no longer named; missing from facilities or personnel; misspelled or inconsistent name forms ("Sam" vs "Samuel J."); outdated titles.

## Promise traceability matrix

One row per activity, deliverable, or claim that a reviewer could hold the proposal to (including numbers in the vision and summary).

| Promise (as worded) | Where stated | Activity / method | Timeline row (years) | Budget line (years, amount) | Who does it (on payroll those years?) | Assessment measure | Partner letter |
|---|---|---|---|---|---|---|---|

A row with an empty cell is either a gap to fill or a claim to cut. A research question whose method cannot answer it (e.g., a question about change over time answered with data from a single time point) is a gap too.

## Scope-change log

| Date | Change (cut / added / moved / renamed) | Old term(s) to search for | Documents checked | Leftovers found and fixed | Figures needing source-file edits |
|---|---|---|---|---|---|

## Sponsored-programs handoff memo

For items the PI's office owns (budget entry, rates, classifications, certifications).

```markdown
# <Grant>: items for sponsored programs (<date>)
Files reviewed: <budget file>, <justification file>
## Needs your action
1. <issue> — current value(s) and where; correct value if known, with source; what to change
## Needs your confirmation
- <classification or rate question>
## Already resolved — no action needed (listed so they are not re-raised)
- <item and decision>
```

## Letters tracker

| Slot | Writer | Role / organization (title verified on) | Template (own letterhead / placeholder) | Status (not started / drafted / sent / received / will not request) | Asked on | Due | Received | File | Dated and signed? | Says what it must? | Mismatches with proposal |
|---|---|---|---|---|---|---|---|---|---|---|---|

`will not request` needs a reason, recorded in the row. Either the funder does not require a letter for this person's role (e.g., personnel already on the budget, if the rules say so), in which case nothing else changes; or the person is no longer part of the project, in which case remove them from the narrative, facilities, and collaborators list, and log it in the scope-change log.

## Review findings tracker

| ID | Source (round, agent) | Issue | Location | Severity (stop-ship / important / minor) | Owner (narrative / PI decision / other document / sponsored programs / Word-only check) | Decision | Done in version |
|---|---|---|---|---|---|---|---|
