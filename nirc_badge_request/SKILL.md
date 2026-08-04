---
name: nirc-badge-request
description: "Prepare Field Museum NIRC ID badge requests (Scientific Affiliate, Visitor, Contractor) and prefill the NIRC Badge Request Google Form for human review. Use this skill whenever the user mentions a badge, badge renewal, expiring badge, building access, door access, room access, West Lot parking for a non-staff person, or getting a research associate, affiliate, visitor, or contractor into NIRC spaces or the collections — even if they never name the form. Also use it for the questions this process raises: whether after-hours or weekend access is possible, who has to approve it, how far in advance to submit, and whether someone should go through this form or through HR. Restricted to curators; other Museum staff may prepare a draft but must route it to a curator for submission."
---

# NIRC Badge Request

## Overview

Prepare a complete, validated NIRC badge request, prefill the live form, and stop for a curator to review and submit. **Never click Submit** — badge sponsorship is an accountable act by a named Museum staff person, and the final click is theirs.

Keywords: badge, badge renewal, NIRC, ID badge, building access, door access, room access, Access Control, Scientific Affiliate, Visitor badge, Contractor badge, West Lot parking, affiliate, research associate.

## Reference files

- `references/form-fields.md` — every question in form order, required/optional, all dropdown and radio options, and the browser quirks encountered when filling it. Read this before collecting answers or touching the browser; the form has been revised since 2024 and this file is where changes get recorded.
- `references/config.example.yaml` — placeholder config layout.

## Workflow

| Step | Action |
|---|---|
| 0 | Load config — the form URL lives outside this repo |
| 1 | Establish the requester's status — curator, other staff, or non-staff |
| 2 | Confirm this form is the right channel at all |
| 3 | Collect the field values (renewals carry forward) |
| 4 | Validate against the rules that bounce requests |
| 5 | Prefill the live form in the browser |
| 6 | Hand off an answer sheet and stop |

## Step 0 — Load config (bootstrap if missing)

Read `~/.config/nirc_badge_request/config.yaml`.

- If it exists, load `nirc_badge_form_url`, `nirc_key_form_url`, and `after_hours_approver`.
- If it is missing, tell the user and walk them through creating it: copy the layout from `references/config.example.yaml`, ask for each value, and write the completed file to `~/.config/nirc_badge_request/config.yaml`. Never store these values in the skill repo.

Where this file says "the approver" for after-hours access, use `after_hours_approver`.

## Step 1 — Establish who is asking

The supervisor field names an accountable Museum staff person vouching for a non-staff individual, so standing matters before the work starts, not after.

- **Curator** — proceed normally.
- **Other Museum staff** — prepare the full draft, then state plainly that a curator must review and submit it. The draft is useful groundwork; don't refuse it.
- **Not Museum staff** — stop. The form accepts submissions only from Museum staff. Point them to their curator sponsor and offer to assemble the information that sponsor will need.

## Step 2 — Confirm the channel

Catching a misrouted request here saves a bounce later:

- **Staff, Intern, and Volunteer badges are handled by HR**, not this form. Say so and stop.
- **Keys** go through the separate NIRC Key Request Form. A badge request may name rooms, but grants no keys.
- This form covers **Scientific Affiliate, Visitor, and Contractor** badges only.

## Step 3 — Collect the information

Work from `references/form-fields.md` rather than memory.

**For renewals, ask for the previous submission first.** Google Forms emails a receipt from `forms-receipts-noreply@google.com` with the subject "NIRC Badge Request Form" containing every prior answer. Read it, then ask only what plausibly changed — dates, phone, emergency contact, room access, after-hours status. Confirming five fields beats re-asking eighteen. Check "Yes" on the renewal question.

**Offer the paste option explicitly.** Many people would rather hand over everything at once than answer serial questions. Tell them they can paste a table, a list, or the old receipt email, and that gaps will be asked about afterward. When asking directly, batch related fields into one question rather than going one at a time.

## Step 4 — Validate

Raise each of these as a question rather than guessing:

| Check | Why it matters |
|---|---|
| Start date ≥ 7 days out | Access Control's stated lead time; same-day and next-day requests are usually refused |
| Start date ≤ 2 weeks out | The form asks that requests not be submitted earlier than this |
| After-hours/weekends on a Visitor badge | Not possible at all — this is a badge-type problem, not a checkbox |
| After-hours/weekend approval | Requires the requester's supervisor or `after_hours_approver` in advance |
| After-hours reason field | Required even when no after-hours access is wanted; takes `N/A` |
| Supervisor is Museum staff | With a real Museum extension or contact number |
| West Lot parking on a Visitor badge | Needs prior approval |
| Unpaid staff | Owe a $10 cash deposit at pickup — warn them before they go |
| End date | Affiliate terms are commonly two years; confirm rather than assume, and check it follows the start date |

A renewal requested well before expiry shortens the current term. Point this out and offer the continuous alternative (new term starting the day after the current badge ends) so the choice is deliberate.

## Step 5 — Prefill the form in the browser

Open `nirc_badge_form_url` in the user's Chrome and fill every field so the curator reviews a populated form rather than a list of values to retype. Google Forms is a custom-widget UI, so the mechanics matter:

- **Text, textarea, and date inputs are real inputs** — read the page for element refs and set them with `form_input`. Dates take `YYYY-MM-DD` and render as MM/DD/YYYY.
- **Checkboxes and radios are DIVs.** `form_input` fails on them with "Element type DIV is not a supported form input" — click them instead, preferring element refs over coordinates.
- **The "Record my email" checkbox at the top is required** and is one of those DIVs. Confirm it took by looking for "A copy of your responses will be emailed to…" above the Submit button.
- **The department dropdown needs two clicks and verification.** The overlay animates in and often leaves a stale ghost painted over the page; a click that lands during the animation selects nothing and can trigger "This is a required question". Click to open, screenshot to confirm the options are fully rendered, then click the option — and scroll back afterward to confirm the field shows the chosen value rather than "Choose".
- **Only elements near the viewport get refs**, so read the page again after each scroll rather than reusing stale refs.
- **Verify by scrolling through the whole form before handing off.** Silent failures here are the expensive kind — they surface as a rejected submission.

Do not click Submit, and do not click Clear form.

## Step 6 — Hand off

Deliver an answer sheet file alongside the prefilled form, in the form's own question order so it reads top to bottom:

```markdown
# NIRC Badge Request — [Badgeholder name][, Renewal]
**Form:** [url]
**Prepared for submission by:** [curator name]

| # | Form question | Answer |
|---|---------------|--------|

## Before you submit
- [each validation flag that applies, and what to do about it]

## Notes
- [what was carried forward, and anything still unconfirmed]
```

Close with one line naming what still needs a human decision, and state explicitly that Submit has not been clicked.
