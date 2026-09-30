# 12: Amazon Fresh and Whole Foods Provider

Status: TODO
Owner repo: `amminox` (branch `feature/amazon-grocery-provider`)
Depends on: 01 (section A5 findings), 02, 09 (handoff plumbing)
Skills: `backend-implementation`, `frontend-implementation`

## Goal

Let users send a grocery list to **Amazon Fresh** or **Whole Foods Market** (both sold through amazon.com). The user finishes item selection and checkout in Amazon with their own Amazon session. This matches MFP's iOS options (challenge screenshot 1).

## Context

### What exists at Amazon for third parties

| Mechanism | What it does | Access requirements | Status | Source |
|---|---|---|---|---|
| **Amazon Fresh ingredients landing** `POST https://www.amazon.com/afx/ingredients/landing` | Takes a recipe's ingredient list as JSON in a form field; Amazon matches products and shows a page where the user adds them to the Fresh cart | None known (no key) | **Community-documented, not officially documented.** `GET` returns 405 (endpoint exists and expects POST, checked 2026-09-29). Payload shape per [Lime Daley guide (2020)](http://limedaley.com/post/amazon-fresh-api): `{"ingredients":[{"name":"Chicken breast","quantityList":[{"unit":"lb","amount":1}]}]}` in a hidden input named `ingredients` | Inferred; verify in task 01 A5 |
| Storefront selection via `almBrandId` | Amazon Fresh = `QW1hem9uIEZyZXNo`, Whole Foods Market = `VUZHIFdob2xlIEZvb2Rz` (base64 of the brand names) | None | **Verified** in amazon.com storefront links ([Amazon grocery hub](https://www.amazon.com/fmc/m/30003175)). Whether the landing endpoint accepts `almBrandId` for Whole Foods is **Inferred** (a `landingencoded?almBrandId=...` URL is indexed for amazon.de) | Verify in task 01 A5 |
| **Creators API** (successor to PA-API 5) | `SearchItems`, `GetItems` (ASIN only, up to 10 per call), `GetVariations`, `GetBrowseNodes`; resources include `itemInfo.externalIds` (UPC/EAN), `offersV2.listings.price/availability` | Amazon Associates account **and at least 10 qualifying sales in the past 30 days**; OAuth 2.0 client credentials; bearer token valid 1 h | **Verified**: [Introduction](https://affiliate-program.amazon.com/creatorsapi/docs/en-us/introduction), [Onboarding](https://affiliate-program.amazon.com/creatorsapi/docs/en-us/onboarding), [GetItems](https://affiliate-program.amazon.com/creatorsapi/docs/en-us/api-reference/operations/get-items) | Phase 2 only |
| PA-API 5 | Old product API | none | **Deprecated**: calls return 403 `AccessDeniedException` ([deprecation notice](https://affiliate-program.amazon.com/creatorsapi/docs/en-us/paapiv5-deprecation)) | Do not use |
| Associates "Add to Cart form" `https://www.amazon.com/gp/aws/cart/add.html?ASIN.1=<asin>&Quantity.1=<n>&AssociateTag=<tag>` | Adds specific ASINs to the user's amazon.com cart | Associates tag for attribution | Its doc page (`webservices.amazon.com/paapi5/documentation/add-to-cart-form.html`) now redirects to the PA-API deprecation notice, so **current support is unverified**. Also unclear whether Fresh/Whole Foods ASINs land in the Fresh cart | Phase 2 only; verify |

### Creators API rate model (Verified, [API Rates](https://affiliate-program.amazon.com/creatorsapi/docs/en-us/concepts/api-rates))

- First 30 days after credentials: 1 TPS and 8,640 TPD.
- After that the limit scales with shipped revenue from API links: 1 TPD per $0.05 and 1 TPS per $4,320 (max 10 TPS), over the previous 30 days.
- **Access is revoked after 30 consecutive days without qualified referring sales**, and restored within two days after a referred sale ships.
- Always use the primary account's credentials and keep all URL parameters unchanged so sales are attributed.

### How MFP does it (observed by the user, 2026-09-29)

1. Tapping Shop -> Amazon Fresh in the MFP app opens an **MFP-hosted web page**: `https://www.myfitnesspal.com/v2/mealapp/grocery/delivery/amazonFresh?i=<id>`. `i` identifies the grocery list stored on MFP's server, so the ingredients are not in the app-to-web URL.
2. That page shows one button, **"Continue on Amazon Fresh"**.
3. Tapping it opens the **native Amazon app**, which asks which delivery address to use and then shows the cart with the matched items.

Interpretation:

- The bridge page exists because Amazon's ingredient handoff is a web entry point (`/afx/ingredients/...`), not an app API. The page builds the Amazon request server-side from the stored list (and can add attribution).
- The **user tap** on the bridge page matters: iOS universal links open the target app only on user-initiated navigation to a different domain. A link tap from `myfitnesspal.com` to `www.amazon.com` qualifies, so the Amazon app opens instead of Safari.
- The Amazon app opening points to a **GET link** rather than a form POST (universal links are not triggered by form submissions). Amazon has a GET variant: `https://www.amazon.com/afx/ingredients/landingencoded` (Verified 2026-09-29: with no payload it redirects to the Fresh storefront `alm/storefront?almBrandId=QW1hem9uIEZyZXNo`, so the route exists and accepts GET). The name and encoding of its ingredient parameter are **not verified**. Task 01 A5 captures it from MFP's button.
- The address prompt comes from Amazon: Fresh availability depends on the delivery address, so Amazon asks inside its app. Carte cannot and should not pre-select it.

### What there is NOT

- No public Amazon cart API for third parties and no customer OAuth for grocery carts.
- No public store locator or store-level price API for Whole Foods or Amazon Fresh. Availability and prices depend on the user's Amazon delivery address, set inside Amazon.
- No in-app, store-scoped product search without the Creators API (which also has no store or delivery-address scoping).

## Design

Two phases. Phase 1 needs no Amazon credentials and ships first.

### Phase 1: ingredient-list handoff (no keys)

- Provider key `amazon` with two storefronts, `amazonfresh` and `wholefoods` (two registry rows, one provider module).
- Capabilities: `requiresAccountLink=false`, `storeScopedSearch=false`, `cartMode="handoff-form"` (new mode), `locator="none"`.
- Connect flow (task 06): no store list. Ask for the ZIP only to show "Amazon Fresh / Whole Foods delivery is set by your Amazon delivery address." There is no availability API, so never claim the ZIP is covered.
- Review page (task 08): ingredient lines + quantities, no product rows and no Swap (same shape as Instacart). Footer "Send list to Amazon Fresh" / "Send list to Whole Foods Market".
- Handoff (task 09), mirroring MFP's bridge page:
  1. `POST /api/shops/:id/cart` returns `{ mode: "handoff-form", openUrl: "<server>/amazon/<storefront>?t=<single-use token>" }`.
  2. `GET /amazon/<storefront>?t=` validates the one-time token (5 min TTL, bound to the shop and not to user credentials) and renders a Carte-branded bridge page with one button, "Continue on Amazon Fresh" / "Continue on Whole Foods Market".
  3. **Primary:** the button is a plain `<a href>` to `https://www.amazon.com/afx/ingredients/landingencoded?...` with the list encoded as task 01 A5 finds (GET). A user tap on a cross-domain link lets iOS/Android open the Amazon app via universal/app links, matching MFP. **Fallback** (if the GET encoding cannot be confirmed): the button submits a POST form to `/afx/ingredients/landing`. That opens Amazon in the browser rather than the app.
  4. The client opens the bridge URL with `WebBrowser.openBrowserAsync` (SFSafariViewController / Chrome Custom Tab) or the system browser; a tap inside it can hand off to the Amazon app. Never auto-redirect: universal links need the user's tap.
- Response headers on the handoff page: `Content-Security-Policy: default-src 'none'; form-action https://www.amazon.com; script-src 'nonce-<n>'`, `Referrer-Policy: no-referrer`, `Cache-Control: no-store`.
- Payload mapping: name = ingredient name (not a product title); `quantityList` in Amazon-recognised units from a conversion table verified in task 01, falling back to `{unit:"count", amount:n}`; skip pantry-excluded lines; cap line count per task 01 findings.

### Phase 2 (optional): product-level matching via Creators API

Enable only when Associates has qualifying sales (see prerequisites). Gated by `AMAZON_CREATORS_ENABLED`.

- `searchProducts` via `SearchItems` (keywords = ingredient; browse node for Grocery; resources `itemInfo.title`, `images.primary.small`, `offersV2.listings.price`, `offersV2.listings.availability`, `itemInfo.externalIds`). This is not scoped to Fresh/Whole Foods inventory or the user's address, so results show "Amazon price, availability depends on your address".
- `prepareCart` via the Add to Cart form URL if task 01 confirms it still works and puts grocery ASINs in the right cart; otherwise stay on Phase 1.
- `itemInfo.externalIds` UPCs feed task 11 nutrition.
- The whole feature falls back to Phase 1 automatically when the API returns 429 or access is revoked (30 days without sales).

## Constraints

- The ingredients-landing endpoint is not officially documented. Treat it as a best-effort handoff: detect failure (a Carte-side "Did Amazon show your list?" prompt on return, logging no/yes counts) and disable the storefront with a registry flag if it breaks.
- Amazon Associates Operating Agreement and Program Policies apply to any Associates link ([Operating agreement](https://affiliate-program.amazon.com/help/operating/agreement/), [Program policies](https://affiliate-program.amazon.com/help/operating/policies)). Show the required Associates disclosure wherever tagged links appear (Phase 2).
- Creators API credentials: Credential ID, Credential Secret (shown once at creation), Version (selects the regional token endpoint). Server-side only.
- No WebView. The handoff opens the system browser.
- The handoff token is single-use, short-lived and scoped to one shop's ingredient names/quantities (no user id, no email).

## Steps

1. Registry migration: `amazonfresh` (exists, inactive) and new `wholefoods`, both `provider='amazon'`, `cart_mode='handoff-form'`, inactive until this task passes.
2. `server/src/retailers/amazon.js` Phase 1 provider + unit conversion table + payload builder (tests for escaping: ingredient names with quotes, `<`, `&`, emoji).
3. Handoff route + one-time token table (`handoff_tokens(token_hash, shop_id, purpose, expires_at, used_at)`); HTML rendered from a fixed template with the JSON HTML-attribute-escaped. Never interpolate raw strings.
4. Client: `handoff-form` branch in `retailerHandoff.ts` (opens the system browser), connect-flow and review-page variants, return-to-app "Did Amazon show your list?" prompt.
5. Virtualizer: `/amazon/afx/ingredients/landing` that records the POSTed JSON in `/_virt/state` and returns a stub page; scenarios `http_500`, `malformed_page`.
6. Phase 2 (separate PR, behind flag): Creators API client (OAuth token cache 55 min, `x-marketplace: www.amazon.com`), `SearchItems`/`GetItems` mapping, externalIds -> task 11.
7. Tests: sociable server tests against virt; jest for client branches; Playwright (web) asserting the auto-submit form posts the expected JSON to the virtualizer.

## Acceptance criteria

- Virt: sending a list to Amazon Fresh and to Whole Foods posts the exact expected ingredients JSON (and storefront id if applicable) to the virtualizer.
- Real (manual, `dev`): on Android and iOS, the handoff opens the system browser on Amazon's ingredient page with the list for each storefront; screenshots recorded.
- Handoff tokens cannot be reused or used after 5 minutes (tests).
- With `AMAZON_CREATORS_ENABLED=false` no Creators API call is made.

## Evidence to report

Virt test output showing the POSTed payload, real-device screenshots of the Amazon ingredient page for both storefronts, token misuse test output, and (Phase 2) a redacted `SearchItems` response.

## Do not

- Do not scrape amazon.com or use the deprecated PA-API 5.
- Do not ask for or store Amazon credentials; the user signs in on amazon.com only.
- Do not claim items were added to an Amazon cart; copy says "Sent your list to Amazon Fresh/Whole Foods".
- Do not generate the handoff HTML with string concatenation of user-controlled text.

## Log
