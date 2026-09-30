# 08: Review Page with Auto-Selection + Store Search Swap

Status: TODO
Owner repo: `amminox` (branch `feature/shop-review-swap`)
Depends on: 03 or 04 (at least one store-scoped provider), 07
Skills: `frontend-implementation`, `backend-implementation`

## Goal

After picking a retailer, the user sees every grocery line with a product **already selected** from their store (ReciMe style, not MFP's per-item "Add"), can swap any item through an in-app search of that store, and sees a summary of what will be sent (challenge screenshots 4, 5, 6, 9, 10).

## Context

`client/src/components/shop/GroceryShoppingScreen.tsx` (header with store + Change Store, rows with qty stepper, View Alternatives, per-item search), `ShopSendingModal.tsx`, `client/app/shop/[shopId].tsx`, server `shop.js` resolver and `GET /api/shops/:id`.
## Constraints

- Swap search is debounced and server-cached (task 02 product cache) to protect vendor rate limits (Kroger Products 10,000/day).
- The review payload is provider-neutral; the client branches only on `capabilities`, never on retailer key strings.
- Price display follows vendor fields exactly (`salePrice` for Walmart; `price.regular`/`price.promo` for Kroger) and is always labelled an estimate.
- Row layout must fit 320 px wide (smallest supported phone) without truncating the price.

## Steps

1. Server payload (`GET /api/shops/:id`): per line `{ ingredientName, quantityLine, status, selected: Product | null, alternates: Product[] (top 3), reason? }` plus `store`, `retailer`, `capabilities`. Selection rule: user mapping for this retailer -> curated default -> best scored in-stock product at the store. Items with `stock: "out"` are never auto-selected.
2. Quantity suggestion: convert recipe quantity to package count (existing `packageSize` logic), minimum 1; user can change it.
3. Review page: every resolved row is **included by default** with a checkbox to exclude (pantry items). Header shows retailer logo + store + Change Store, then an info banner "Double-check the quantity of each item" (MFP screenshot 4). Footer "Add N items to <Retailer> cart" with an estimated total labelled "excludes tax and delivery charges". For Walmart, add "Prices at <store>. Walmart uses the store set in your Walmart app." (MFP screenshot 7 showed a different store and price after handoff).
4. Swap screen (new route `client/app/shop/[shopId]/swap/[line].tsx`, matches MFP screenshots 5 and 9): search box prefilled with the ingredient name, results from `GET /api/retailers/:key/products?storeId=&q=` showing name + size, price (promo in green with regular struck through), image, swap icon; plus stock badge and aisle when known; debounce 300 ms; tap selects and returns. Choosing a product writes a user mapping (MVP7 alias system) so it becomes the default next time.
5. Unresolved lines: "Not found at <store>" with Search action (same swap screen) or Skip.
6. Provider without store search (Instacart): show ingredient lines and quantities only, no Swap, footer "Send list to Instacart".
7. Summary/confirm screen (screenshots 6 and 10): selected products grouped, total count, estimated total, modality selector for Kroger (Pickup / Delivery), primary action triggers task 09.
8. Tests: jest (default selection, exclude, swap returns and persists mapping, out-of-stock never selected, Instacart variant), server sociable tests for the selection rule, Playwright web E2E against virt.

## Acceptance criteria

- Opening a shop shows all resolvable lines preselected with store-specific products; no per-item "Add" tap is required.
- Swap searches the selected store only and persists the choice as the next default.
- Out-of-stock products are never preselected.

## Evidence to report

Server and client test output; screenshots of the review page (Walmart and Kroger), swap search results, unresolved row, Instacart variant, and confirm screen, side by side with MFP screenshots 4, 5, 6, 9 and 10.

## Do not

- Do not show prices as exact totals; label them estimates.
- Do not require a per-item "Add" tap for resolved lines.
- Do not search other stores in the swap screen.

## Log
