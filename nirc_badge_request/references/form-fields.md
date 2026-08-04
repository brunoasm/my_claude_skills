# NIRC Badge Request Form — field reference

**Form URL:** `nirc_badge_form_url` from `~/.config/nirc_badge_request/config.yaml` (see `config.example.yaml`). The live link is deliberately not stored in this repo.

**Verified against the live form:** 2026-08-04. Google Forms does not expose prefill entry IDs for this form, so a prefilled URL cannot be constructed — drive the live form in the browser instead (see "Browser quirks" at the end of this file).

## Header text on the form

> Please use this form to request Field Museum ID Badges for the NIRC.
>
> - Only Museum staff are allowed to submit badge requests.
> - Staff, Intern, and Volunteer badges are handled by HR.
> - Access Control requests at least 7 days to complete badges on-time.
> - Same day, or next day requests, will probably not be accommodated.
> - Please do not submit a badge request more than two weeks from pickup.
>
> Unpaid staff are required to submit a $10 cash deposit for their badge.

## Questions, in form order

| # | Question | Required | Type | Options / notes |
|---|----------|----------|------|-----------------|
| 1 | Email | Yes | Short answer | Auto-recorded from the signed-in submitter. This is the submitting Museum staff member, **not** the badgeholder. |
| 2 | First name of the badgeholder | Yes | Short answer | |
| 3 | Last name of the badgeholder | Yes | Short answer | |
| 4 | What is their personal phone number? This should be their cell or home number and not a Museum extension. | Yes | Short answer | |
| 5 | NIRC Department | Yes | Dropdown | NIRC / Earth Sciences · NIRC / Life Sciences · NIRC / Social Sciences · NIRC / Pritzker Lab · NIRC / SEM Lab · NIRC / Administration |
| 6 | (Identity) Badge Type | Yes | Multiple choice | Scientific Affiliate · Visitor · Contractor. Staff and Intern badges are handled by HR. |
| 7 | Is this a badge renewal? | No | Multiple choice | Yes · No |
| 8 | For **Contractor** badge ONLY — Company name | No | Short answer | Leave blank unless badge type is Contractor. |
| 9 | Hours needed — check all that apply | No | Checkbox | After Hours · Weekends. **After hours and/or weekend access cannot be added to a Visitor badge.** |
| 10 | If you want the badgeholder to receive After Hours/Weekend Access, did you receive approval from your supervisor or {`after_hours_approver`}? | Yes | Multiple choice | "Do NOT add either After Hours or Weekends to their badge" · "Yes" |
| 11 | If after-hours/weekends are needed, provide the reason; otherwise put N/A | Yes | Short answer | Required regardless. Enter `N/A` when no after-hours access is requested. Added after the Sept 2024 version of the form. |
| 12 | Is the badgeholder younger than 18? | No | Multiple choice | Yes · No |
| 13 | Badge Start Date | Yes | Date (MM/DD/YYYY) | Access Control requests at least 7 days. |
| 14 | Badge End Date | Yes | Date (MM/DD/YYYY) | Scientific Affiliate terms are commonly two years. |
| 15 | Supervisor's name | Yes | Short answer | **Must be a Museum staff person.** |
| 16 | Supervisor's extension of contact number | Yes | Short answer | **Must be a Museum staff person.** Museum extension is fine here. |
| 17 | Emergency contact name | Yes | Short answer | Note the relationship if known, e.g. "Jane Doe (spouse)". |
| 18 | Emergency phone number | Yes | Short answer | |
| 19 | Please indicate rooms/specific room number(s) needed to access. | No | Short answer | Also where West Lot parking is requested. **West Lot parking cannot be added to a Visitor badge without prior approval.** Keys are requested separately via the NIRC Key Request Form (`nirc_key_form_url`). Useful to state elevators and rooms on separate lines, e.g. `Elevators: Botany Light Well Elevator for floor 2M` / `Rooms: 3rd floor, Insects Pinned Collection Mezzanine (2749/2740/2743)`. |

## Confirmation email

On submission, Google Forms sends the submitter a receipt from `forms-receipts-noreply@google.com` with the subject "NIRC Badge Request Form", listing every answer. This is the best source for renewals — ask for it rather than re-collecting fields from scratch.

## Browser quirks

Observed while filling the live form on 2026-08-04:

| Element | Behaviour |
|---|---|
| First/last name, phone, reason, supervisor, emergency contact, rooms | Real `<input>`/`<textarea>` — `form_input` works |
| Badge Start/End Date | Real `type="date"` inputs — pass `YYYY-MM-DD`, they display as MM/DD/YYYY |
| "Record my email" checkbox | A DIV — must be clicked. Confirm via "A copy of your responses will be emailed to…" near Submit |
| Badge Type radios, renewal checkbox, hours checkboxes, approval radios | DIVs — click by element ref |
| NIRC Department dropdown | Opens an animated overlay that leaves a stale ghost painted on the page. A click during the animation selects nothing and can raise "This is a required question". Click to open → screenshot to confirm full render → click the option → scroll back and confirm the field reads the chosen value, not "Choose" |
| Element refs | Only elements near the viewport get refs; re-read the page after each scroll |

The form is a single page — there is no pagination. Submit and "Clear form" sit at the bottom; never click either.

## Known people and roles

- **`after_hours_approver`** (from config) — named on the form as an approver for after-hours/weekend access, alongside the requester's own supervisor.
- **Access Control** — the office that produces the badges and sets the 7-day lead time.
- **HR** — owns Staff, Intern, and Volunteer badges. Those never go through this form.
