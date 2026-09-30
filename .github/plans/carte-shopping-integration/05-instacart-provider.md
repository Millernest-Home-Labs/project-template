# 05: Instacart Provider

Status: IN-PROGRESS (2026-09-30, amminox PR #3; real calls BLOCKED on an IDP key)
Owner repo: `amminox` (branch `feature/instacart-provider`)
Depends on: 01 (IDP development key), 02
Skills: `backend-implementation`

## Goal

Let users send a grocery list to Instacart (which also covers many of the registry's "coming soon" grocers such as Aldi, Sprouts, Central Market) by handing off a hosted Instacart shopping list page to the Instacart app.

## Context (Verified, docs.instacart.com Developer Platform)

- Base `https://connect.instacart.com/idp/v1/` (dev: `https://connect.dev.instacart.tools`). `Authorization: Bearer <API key>`.
- `GET /retailers?postal_code=&country_code=US` -> `{ retailers: [{ retailer_key, name, retailer_logo_url }] }` (retailers, not store locations).
- `POST /products/products_link` body `{ title, image_url?, link_type: "shopping_list" | "recipe", expires_in?, line_items: [{ name, display_text?, upcs? | product_ids?, line_item_measurements: [{ quantity, unit }], filters? }], landing_page_configuration: { partner_linkback_url?, enable_pantry_items? } }` -> `{ products_link_url }`. UPC wins when given. Cache the URL and regenerate only when the list changes.
- The user chooses the store and swaps items inside Instacart. There is no account link and no server-side cart.
## Constraints

- Production key access follows Instacart's demo approval (about 30-40 days per [Get started](https://docs.instacart.com/developer_platform_api/get_started/overview)). Build and test against `connect.dev.instacart.tools` and the virtualizer; production is a config flip.
- Follow the [developer messaging guidelines](https://docs.instacart.com/developer_platform_api/guide/terms_and_policies/developer_messaging) for button copy and logo use.
- Use only [supported units of measurement](https://docs.instacart.com/developer_platform_api/api/units_of_measurement); unsupported units break quantity matching.
- `upcs` and `product_ids` are mutually exclusive per line, and duplicates across lines are rejected (400): de-duplicate before sending.
- Link URLs are cached by content hash. `expires_in` is left unset for `shopping_list` links (no default expiry); regenerate only when the list changes.

## Steps

1. Provider capabilities: `requiresAccountLink=false`, `storeScopedSearch=false`, `cartMode="handoff-url"`, `locator="retailers"`.
2. `locateStores({zip})` -> Instacart retailers near the ZIP, shown as "Available through Instacart" rows. A connection stores `retailer_key` of the chosen Instacart retailer (for display) and the ZIP.
3. `searchProducts`: not supported. The review page (task 08) shows ingredient lines, not products, and hides Swap for this provider.
4. `prepareCart`: map shop lines to `line_items` (name, `line_item_measurements` using only Instacart-supported units; convert amminox units with a table and fall back to `each`), pass UPCs when a line was resolved from Walmart/Kroger mapping history, `partner_linkback_url` = `amminox://grocery`. Cache by content hash. Allowlist host `*.instacart.com`.
5. Virtualizer fixtures and tests: unit conversion table, invalid unit scenario (400), URL caching by hash.

## Acceptance criteria

- Virt: shop -> `CartResult { mode: "handoff-url", openUrl: https://...instacart... }`.
- `dev` with the development key: one real link opens in the Instacart app on the emulator with the list populated (screenshot).

## Evidence to report

Test output (unit table, 400 scenario, cache hit), one redacted `products_link` request/response from `dev`, emulator screenshot of the Instacart app with the list.

## Do not

- Do not claim items were added to an Instacart cart; copy says the list was sent.
- Do not expose the API key to the client.
- Do not send more than one link request per list change (cache first).

## Log

- 2026-09-30: Steps 1, 2, 4 (minus content-hash cache) and 5 done in PR #3 (`server/src/retailers/instacart/idp.js`); verified against the virtualizer. Remaining: link caching by content hash, wiring into `POST /api/shops/:id/cart` (task 09), `dev` check with a development key.
