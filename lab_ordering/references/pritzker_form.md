# Pritzker Lab Google Form — fill guide

Form title: "Pritzker Lab Ordering" — "Use this form to order up to five items."
Open the URL from config (`pritzker_form_url`).

## Pre-checks
- Confirm logged in to the correct Google account if the form requires it.
- Confirm funding source (goes in "Account to be charged").
- Default to cheapest shipping unless the request asks otherwise (note in Notes).

## Field mapping (item block repeats up to 5; only item 1 is required)

| Form field                       | Value                                         |
|----------------------------------|-----------------------------------------------|
| Name (required)                  | config identity.name                          |
| Email (required)                 | config identity.email                         |
| Account to be charged (required) | confirmed funding source                      |
| Company (required, item 1)       | vendor name (e.g. Fisher Scientific)          |
| Catalog Number (required, item 1)| catalog / part #                              |
| Item (required, item 1)          | item description                              |
| Quantity (required, item 1)      | requested quantity                            |
| URL (required, item 1)           | product link                                  |
| Notes (optional)                 | requester name; urgency; shipping; any flags  |
| Company/Catalog/Item/Quantity/URL/Notes 2–5 | additional items                   |

## Steps
1. Fill Name, Email, Account to be charged.
2. Fill the item 1 block, then items 2–5 as needed.
3. If the request has MORE than 5 items, fill the first 5, STOP for review,
   and after submission repeat with the remainder (confirm with the user
   between submissions).
4. Put requester name + urgency + shipping preference in each relevant Notes
   field.
5. Do NOT click Submit. Present the filled summary and wait for the user to
   submit.

## Clean Lab
If the header/flags say Clean Lab, after filling emit the capital-letters
CLEAN LAB alert from SKILL.md.
