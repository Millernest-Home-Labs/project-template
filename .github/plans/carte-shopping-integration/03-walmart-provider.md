# 03: Walmart Official API Provider

Status: IN-PROGRESS (2026-09-30, amminox PR #3; real calls BLOCKED on walmart.io credentials)
Owner repo: `amminox` (branch `feature/walmart-affiliate-api`)
Depends on: 01 (Walmart secrets, storeId approval status, quantity syntax), 02
Skills: `backend-implementation`

## Goal

Replace unofficial Walmart calls with the Walmart Affiliate API: store locator by ZIP, store-scoped product search and lookup, and server-built affiliate add-to-cart URLs.

## Context (Verified, walmart.io docs)

- Every call needs headers `WM_CONSUMER.ID`, `WM_CONSUMER.INTIMESTAMP` (ms), `WM_SEC.KEY_VERSION`, `WM_SEC.AUTH_SIGNATURE` = base64(SHA256withRSA(private key, `consumerId\ntimestamp\nkeyVersion\n`)), keys sorted by name. Signature TTL is 180 s: sign per request.
- Stores: `GET https://developer.api.walmart.com/api-proxy/service/affil/product/v2/stores?zip=` (or `lat`/`lon`) -> `no, name, streetAddress, city, stateProvCode, zip, coordinates`.
- Search: `.../affil/product/v2/search?query=&numItems<=25&start=&categoryId=&facet=on` -> items with `itemId, upc, name, salePrice, thumbnailImage, mediumImage, stock, offerType, availableOnline, affiliateAddToCartUrl`. Search is online-catalog scoped.
- Product Lookup: `.../affil/product/v2/items?ids=<up to 20>&zipCode=|storeId=` -> price and availability for that store or ZIP. `storeId` needs business approval.
- Affiliate cart URL shape: `goto.walmart.com/c/<publisherId>/568844/9383?...&u=<encoded affil.walmart.com/cart/addToCart?items=<ids>>`.
## Constraints

- Sign every request separately (180 s signature TTL). Never cache or log `WM_SEC.AUTH_SIGNATURE`.
- `storeId` lookups need Walmart business-team approval ([Product Lookup](https://walmart.io/docs/affiliates/v1/product-lookup)). Gate them behind config `WALMART_PRICE_SCOPE=zip|store` (default `zip`) so the feature ships before approval arrives. Switching to `store` is a config change only.
- Product Lookup takes at most 20 ids per call and Search at most 25 items per page: batch accordingly.
- "Several categories are excluded from the API calls" ([Introduction](https://walmart.io/docs/affiliates/v1/introduction)): log ingredient searches that return nothing so gaps are visible.
- Cache stores 24h per ZIP, search results 6h per `(storeOrZip, query)`, and lookups 6h per `(storeOrZip, itemId)`.

## Steps

1. `server/src/retailers/walmart/sign.js`: Node `crypto.createSign("RSA-SHA256")` implementation; unit test against a fixture key and known canonical string.
2. `locateStores`: Stores API; compute `distanceMiles` (haversine from ZIP centroid or device coords); sort closest first; cache 24h (existing locator cache). Build the display name from the returned fields per task 01 C.3 (target: MFP-style "Wylie Supercenter #5210"). Delete the `walmart.com/store/finder/api/search` call.
3. `searchProducts({storeId, query})`: grocery-biased search (`categoryId` for Food, from the Taxonomy API, stored as config), then `lookupProducts` for the top N with `storeId` (or `zipCode` from the connection when storeId approval is missing) to get store price and stock. Drop results with `stock: "Not available"` at that store; mark `fulfillment.inStore` from `offerType` (`ONLINE_AND_STORE`, `STORE_ONLY`).
4. Scoring: reuse `shopSearch.js` normalization + scoring; the resolver order stays user mapping -> curated default -> scored search, now store-aware (cache key from task 02).
5. `prepareCart({lines})`: build `affil.walmart.com/cart/addToCart?items=` using the quantity syntax verified in task 01; wrap in the Impact tracking URL with `IMPACT_PUBLISHER_ID`; `fallbackUrl` = `https://www.walmart.com/cart`. Allowlist hosts: `goto.walmart.com`, `affil.walmart.com`, `www.walmart.com`.
6. Remove the public site-search scrape path from production code (keep a virt fixture only if a test needs it). Retire `EXPO_PUBLIC_WALMART_AFFILIATE_KEY` and `WALMART_CONSUMER_KEY/WALMART_SECRET` names in favor of task 01 names; update `.env.example`.
7. Virtualizer fixtures: real-shaped JSON for stores (ZIP 75001 style), search ("chicken breast", "olive oil", unknown term), lookup with in-stock/out-of-stock mix.

## Acceptance criteria

- With virt: ZIP -> 10 closest stores; search at a store returns only items available at that store with price; cart result URL decodes to the expected `items=` list with quantities.
- With real keys in `dev`: one manual smoke run records a stores response and a lookup response (redacted) in the task log.
- No request to `www.walmart.com` from server code remains (grep evidence).

## Evidence to report

Unit + sociable test output, grep for removed endpoints, redacted `dev` smoke responses.

## Do not

- Do not ship the private key to the client or log signatures.
- Do not call Walmart from tests.

## Log

- 2026-09-30: Provider built to the public walmart.io docs and verified against the virtualizer (`server/src/retailers/walmart/`: `sign.js`, `affiliate.js`). Steps 1, 2 (display name composed as `<City> <Type> #<no>`), 3, 5 and 7 done; `WALMART_PRICE_SCOPE=zip` default. `/api/retailers/nearby` uses the provider only once `WALMART_CONSUMER_ID/WALMART_PRIVATE_KEY/WALMART_KEY_VERSION` exist; the legacy walmart.com locator stays until then. Remaining: step 6 (remove site-search scrape + old `WALMART_CONSUMER_KEY` path) after keys arrive, `dev` smoke run.
