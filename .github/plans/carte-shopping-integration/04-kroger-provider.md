# 04: Kroger Provider (OAuth, Products, Cart)

Status: IN-PROGRESS (2026-09-30, amminox PR #3; production verification BLOCKED on a Kroger Production app + QA account)
Owner repo: `amminox` (branch `feature/kroger-provider`)
Depends on: 01 (Kroger production client, QA account), 02
Skills: `backend-implementation`

## Goal

Full Kroger integration: user links their Kroger account through Kroger's sign-in, picks a store by ZIP, searches that store, and the server adds items to the user's real Kroger cart.

## Context (Verified, developer.kroger.com)

- Base `https://api.kroger.com/v1/`. Certification (`api-ce`) has no customer accounts, so Cart/Identity are tested in production with the QA account.
- App token (client credentials, scope `product.compact`) for Locations and Products.
- Customer token: Authorization Code + PKCE S256. Authorize `GET /connect/oauth2/authorize?scope=&response_type=code&client_id=&redirect_uri=&state=&code_challenge=&code_challenge_method=S256`. Token `POST /connect/oauth2/token` with `Authorization: Basic base64(id:secret)`, `grant_type=authorization_code&code=&redirect_uri=&code_verifier=`. Access token ~30 min (`expires_in: 1800`); refresh with `grant_type=refresh_token` (a new refresh token is returned each time: persist it).
- Locations: `GET /locations?filter.zipCode.near=&filter.radiusInMiles=&filter.limit=&filter.chain=`; 1,600 calls/day per endpoint. Chain details give banner `appleAppId`/`googleAppId`/`domain` (Ralphs, King Soopers, Fred Meyer, etc.).
- Products: `GET /products?filter.term=&filter.locationId=<8 chars>&filter.limit=` returns price, stock level, aisle, fulfillment when `locationId` is set. Batch refresh with `filter.productId=` (comma list).
- Cart: `PUT /cart/add` body `{ items: [{ upc, quantity, modality: "PICKUP" | "DELIVERY" }] }` -> 204; 5,000 calls/day. The API is add-only (no read, no remove).
## Constraints

- Cart and Identity work only in Production with a real customer account. CI never calls Kroger; production checks are manual and use the QA shopper only.
- Daily limits: Products 10,000, Locations 1,600 per endpoint, Cart 5,000. Add per-user throttles (for example 60 product searches/hour) and alert at 80% of any daily budget.
- Token encryption key `RETAILER_TOKEN_ENC_KEY` (32 bytes, K8s Secret). The encryption helper supports key rotation by storing a key id with each ciphertext.
- OAuth `state` rows expire after 10 minutes and are single-use.
- The Cart API is add-only: Carte cannot read or clear the Kroger cart, so copy never promises a clean cart.

## Steps

1. Server-side OAuth (confidential client, secret stays on server):
   - `POST /api/retailers/kroger/link/start` (auth) -> creates `state` (random 32 bytes, bound to user, 10 min TTL) + PKCE verifier stored server-side; returns the authorize URL.
   - `GET /api/retailers/kroger/callback?code&state` (public, registered redirect URI) -> validates state, exchanges code, encrypts tokens into `retailer_tokens`, sets `link_status=linked`, then 302 to `amminox://retailers/linked?retailer=kroger&status=ok` (or `status=error&reason=<code>`, no token data in the URL).
   - `DELETE /api/retailers/kroger/link` -> delete tokens, `link_status=revoked`.
   - Token helper: refresh when < 60 s left; on `invalid_grant` set `link_status=expired` and return 409 `{ code: "RETAILER_RELINK_REQUIRED" }`.
2. `locateStores`: Locations API with ZIP; include `chain` and banner app ids from a cached `/chains` call (24h). Cache per ZIP 24h to protect the 1,600/day limit.
3. `searchProducts` / `lookupProducts`: Products API with `filter.locationId`; map `items[0].price.{regular,promo}`, `inventory.stockLevel` (`HIGH`, `LOW`, `TEMPORARILY_OUT_OF_STOCK`), `aisleLocations[0]`, `fulfillment`. Product cache 6h per `(storeId, query)`.
4. `prepareCart`: requires linked token; send one `PUT /cart/add` with all lines (UPC, quantity, modality from the confirm screen, default `PICKUP`); on 204 all lines are `added`; on 4xx split into single-item calls to report per-item failures honestly. `openUrl` = the banner domain cart page (for example `https://www.kroger.com/cart`), which the banner app claims as an app link (confirm in task 01).
5. Virtualizer: OAuth authorize page (auto-consent form), token endpoint (including refresh rotation and `invalid_grant` scenario), locations, products, cart/add with 204/401/400.
6. Tests: state mismatch rejected; PKCE verifier required; tokens never in logs or responses; refresh rotation persisted; relink path; per-item failure reporting.

## Acceptance criteria

- Virt: full link -> locate -> search -> cart flow passes sociable tests.
- `dev` with the QA account: a manual run adds 2 items; screenshot of the Kroger app cart showing them (android-testing profile `kroger-authenticated`).
- Refresh tokens encrypted at rest (DB row shows ciphertext), revoke deletes them.

## Evidence to report

Test output, redacted callback log line (no code/token), Kroger app cart screenshot.

## Do not

- Do not open the Kroger sign-in in a WebView.
- Do not put tokens, codes or client secret in the client, URLs back to the app, or logs.
- Do not run cart tests against production Kroger in CI.

## Log

- 2026-09-30: Steps 1-3, 5 and most of 6 done in PR #3: `server/src/retailers/kroger/` (`oauth.js` PKCE + app token cache, `api.js` Locations/Products/Cart with per-line fallback, `link.js` state/tokens/refresh/revoke), routes `POST/DELETE /api/retailers/kroger/link`, `GET /api/retailers/kroger/callback`. Verified in CI against MySQL + virtualizer (authorize -> callback -> encrypted tokens -> single-use state -> revoke). Route name differs from plan: `POST /api/retailers/kroger/link` (not `/link/start`). Remaining: step 4 cart route (lands with task 09 `POST /api/shops/:id/cart`), chain banner app ids, 80% rate-limit alerting, production check with the QA shopper.
