# Amazon Business — cart + review guide

Open the URL from config (`amazon_business_url`).

## Pre-checks
- Verify you are logged in to Amazon Business. If not, pause and ask the user
  to log in, then continue.
- Confirm funding source (goes in the PO field at checkout review).

## Steps
1. For each requested item: search by part #, then by item name, then via the
   product link. Match carefully on size, sterility, pack count, and seller.
2. Add the requested quantity to the cart.
3. Open the cart. Verify each line's quantity and unit/total price against the
   quoted price from the request.
4. Begin checkout only far enough to reach the PO field; enter the confirmed
   funding source there. Default to the cheapest shipping unless the request
   asks for faster.
5. STOP before placing the order. Present the review summary and all flags. The
   user places the final order.

## Flags to raise
- Price differs from the quote.
- Item out of stock or no exact match (list the closest candidates).
- Multiple plausible matches — ask the user to choose.
- Login or org approval required.

## Clean Lab
If the header/flags say Clean Lab, after staging the cart emit the
capital-letters CLEAN LAB alert from SKILL.md.
