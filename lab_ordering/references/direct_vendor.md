# Direct from vendor — cart + review guide

Use when the header is neither Amazon nor Pritzker. Open the product link from
the request.

## Pre-checks
- If the vendor site has a lab account, verify logged in; if login is needed or
  no account exists, flag it and ask the user how to proceed.
- Confirm funding source.

## Steps
1. Navigate to the product via the request link; confirm it matches (size,
   pack count, catalog #).
2. Add the requested quantity to the cart.
3. Verify quantity and price against the quote.
4. If the site has a PO / order-notes field, enter the confirmed funding
   source; otherwise record it in the review summary. Default to cheapest
   shipping unless the request asks otherwise.
5. STOP before purchasing. Present the review summary and all flags. The user
   completes the purchase.

## Flags to raise
- No account / login required.
- Price differs from the quote, or sign-in required to see price.
- Item out of stock or ambiguous match.

## Clean Lab
If the header/flags say Clean Lab, after staging emit the capital-letters
CLEAN LAB alert from SKILL.md.
