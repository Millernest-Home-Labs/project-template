# 02: Retailer Provider Abstraction + Virtualizer

Status: IN-PROGRESS (2026-09-30, amminox PR #3 `feature/retail-providers`)
Owner repo: `amminox` (branch `feature/retail-providers`)
Depends on: none
Skills: `backend-implementation`, `create-sociable-tests`

## Goal

A provider-neutral retailer layer on the server so Walmart, Kroger and Instacart plug in behind one contract, plus a virtualizer that stands in for all three in tests and `APP_ENV=virt`.

## Context

Today Walmart logic is spread across `server/src/retailers.js` (locator proxy, connections), `shopSearch.js` (official API or public site-search scrape), `shop.js` (resolution engine, handoff tokens), `cart-assist.js`, `retailerRegistry.js` (registry seed, `SUPPORTED_RETAILERS`). All outbound calls go through `guardedFetch.js`.

## Contract

```ts
// server/src/retailers/provider.js (JSDoc types; server is JS)
interface RetailerProvider {
  key: "walmart" | "kroger" | "instacart";
  capabilities: {
    requiresAccountLink: boolean;          // kroger: true
    storeScopedSearch: boolean;            // walmart (after storeId approval), kroger: true; instacart: false
    cartMode: "server-api" | "handoff-url" | "handoff-form"; // kroger: server-api; walmart, instacart: handoff-url; amazon (task 12): handoff-form
    locator: "stores" | "retailers";       // instacart returns retailers, not stores
  };
  locateStores({ zip, lat, lng }): Promise<Store[]>;              // closest first
  searchProducts({ storeId, query, limit, ctx }): Promise<Product[]>;
  lookupProducts({ storeId, ids, ctx }): Promise<Product[]>;       // refresh price/stock for cached picks
  prepareCart({ storeId, lines, ctx }): Promise<CartResult>;
}
type Store = { storeId, name, address, distanceMiles, lat, lng, chain?, appIds?: { ios?, android? } };
type Product = { productId, upc?, name, brand?, size?, imageUrl?, price?: { regular, promo? }, stock?: "high"|"low"|"out"|"unknown", aisle?, fulfillment?: { inStore, pickup, delivery } };
type CartResult =
  | { mode: "server-api", added: { productId, quantity }[], failed: { productId, reason }[], openUrl: string }
  | { mode: "handoff-url", openUrl: string, fallbackUrl: string }
  | { mode: "handoff-form", openUrl: string }; // openUrl is a Carte-hosted auto-submit page (task 12)
```

`ctx` carries the user id so Kroger can load that user's token. `openUrl` hosts must be on the provider's allowlist.
## Constraints

- Ship as three PRs (< ~400 changed lines each where practical): (a) move Walmart behind the provider interface with no behavior change, (b) migrations + provider-neutral routes + OpenAPI, (c) virtualizer component + CI job.
- Server stack is Node + Express + MySQL with `node --test` (`server/package.json`). ESLint zero errors; no new `any`-style untyped client calls: regenerate the typed client from OpenAPI.
- Migrations are forward-only and must run on the CI scratch database.
- Every outbound call goes through `guardedFetch.js`. Base URLs come from env/config, never from request input.
- The virtualizer follows hard rules section 5: its own `Dockerfile`, `kube-deploy/` (probes, requests/limits), tests and CI build job; `/_virt/*` control API.

## Steps

1. Create `server/src/retailers/` with `provider.js` (contract + validation), `registry.js` (key -> provider, replaces `SUPPORTED_RETAILERS`), and move the Walmart code behind `walmart.js` without behavior change (task 03 swaps its internals).
2. Migration (forward-only): `retailer_registry` adds `requires_account_link`, `cart_mode`; `retailer_connections` adds `zip`, `store_chain`, `link_status ENUM('none','linked','expired','revoked')`; new `retailer_tokens (user_id, retailer_key, access_token_enc, refresh_token_enc, expires_at, scopes, created_at, updated_at, PRIMARY KEY(user_id, retailer_key))`; new `retailer_product_cache (retailer_key, store_id, query_norm, payload JSON, fetched_at)` with a TTL index strategy (prices: 6h, mappings: 30d).
3. Make shop resolution provider-aware: `shops` store `retailer_key` + `store_id`; resolution cache key becomes `(userId, ingredientName, retailer, storeId)`; fall back to the retailer-wide key when the store key misses.
4. Routes (provider-neutral; update the OpenAPI spec and the client typed API):
   - `GET /api/retailers` adds `capabilities`.
   - `POST /api/retailers/nearby {retailer, zip | lat+lng}` delegates to `locateStores`.
   - `GET /api/retailers/:key/products?storeId=&q=` -> `searchProducts` (auth, throttled).
   - `POST /api/shops/:id/cart` -> `prepareCart`; returns `CartResult`.
5. Virtualizer: `amminox/virtualizer/` (Node, own `Dockerfile`, `kube-deploy/`, tests, CI job). Routes mimic each vendor's paths (`/walmart/api-proxy/service/affil/product/v2/{stores,search,items}`, `/kroger/v1/{locations,products,cart/add,connect/oauth2/*}`, `/instacart/idp/v1/{retailers,products/products_link}`) with deterministic fixtures, plus `/_virt/scenario` (`timeout`, `http_401_token_expired`, `http_429`, `http_500`, `malformed`, `out_of_stock`, `retry_then_success`), `/_virt/reset`, `/_virt/state`.
6. Fail-closed guards: `APP_ENV=virt` requires virtualizer base URLs and refuses real-looking keys; production refuses virtualizer hosts.
7. Tests (`node --test`, sociable): registry dispatch, resolution cache keys, each route against the virtualizer including every scenario.

## Acceptance criteria

- Existing Walmart shop flow and all current server/client tests pass unchanged after the move.
- New routes documented in OpenAPI; client API types regenerated.
- Virtualizer image builds in CI; `APP_ENV=virt` E2E stack starts with it.

## Evidence to report

Test run summary, migration applied on a scratch DB in CI, virtualizer `/_virt/state` output.

## Do not

- Do not change user-visible behavior here.
- Do not store tokens unencrypted, even in `dev`.
- Do not edit applied migrations.

## Log

- 2026-09-30: PR #3 (CI green). Done: `server/src/retailers/` (util, providers registry with capabilities + handoff host allowlist, walmart/, kroger/, instacart/, tokenCrypto), guardedFetch method/body + internal `upstreamStatus`, migration 0061 (connection `zip` + `link_status`, `retailer_tokens`, `retailer_oauth_states`), routes `GET /api/retailers/:key/products`, provider-backed `/api/retailers/nearby`, `virtualizer/` (Walmart, Kroger, Instacart, Amazon + `/_virt`), CI jobs `retail-tests` (gates image build) and `retail-db-tests` (MySQL service). Remaining: step 3 (shop resolver + cache keyed by store, `shops.store_id`), `POST /api/shops/:id/cart`, fail-closed guard that refuses real-looking keys in virt, OpenAPI + client types. Deviation: provider capabilities live in code (`providers.js`), not in `retailer_registry` columns; registry `active` is additionally gated on provider configuration.
