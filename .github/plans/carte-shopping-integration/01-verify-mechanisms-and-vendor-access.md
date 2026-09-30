# 01: Verify Mechanisms and Obtain Vendor Access

Status: TODO
Owner repo: `amminox` (findings recorded in `amminox/research/retail-integrations/README.md`)
Depends on: none
Skills: `platform-operations` (approval gate for any account or billing action)

## Goal

Turn every **Inferred** item in the overview into Verified or Refuted, and get the credentials later tasks need. No product code in this task.

## Context

See overview "Research Findings". The user supplied screenshots only; nobody has observed ReciMe or MFP network traffic.
## Constraints

- `platform-operations` approval gate: the agent drafts every application, key and account form, and the user submits. No terms accepted on the user's behalf.
- Accounts belong to Millernest Labs (shared lab mailbox), not personal shopping accounts. The Kroger QA shopper is used only for testing.
- Generate the Walmart RSA key pair on the user's own machine. The private key goes only into K8s Secrets (`kubectl create secret generic ... --dry-run=client -o yaml | kubectl apply -f -`); only the public key is uploaded to walmart.io.
- The corporate laptop can reach public vendor APIs but not LAN hosts (`.github/learnings/2026-09-28-corporate-workstation-network-limits.md`). Emulator spikes run through the android-testing CI lease or from a lab machine.
- Record secret names only, never values, in plans, logs and research notes.

## Steps

### A. Vendor access (user action; the agent prepares the forms and stops at submit)

Summary:

| Vendor | Required for | Approval gate | Secret names (K8s `dev`/`prod`, never values in git) |
|---|---|---|---|
| Walmart walmart.io | Stores, Search, Product Lookup (task 03) | Self-serve key; **`storeId` lookups need Walmart business-team approval** | `WALMART_CONSUMER_ID`, `WALMART_PRIVATE_KEY` (PKCS#8 base64), `WALMART_KEY_VERSION` |
| Walmart via Impact | Commission on add-to-cart links only | Impact publisher application review | `IMPACT_PUBLISHER_ID` |
| Kroger | Locations, Products, Identity, Cart (task 04) | Self-serve; Cart/Identity usable only in Production | `KROGER_CLIENT_ID`, `KROGER_CLIENT_SECRET` |
| Instacart IDP | Shopping list handoff (task 05) | Application + demo approval before production key (~30-40 days) | `INSTACART_IDP_API_KEY` |
| USDA FoodData Central | Nutrition (task 11) | Self-serve data.gov key | `USDA_API_KEY` (already used by `nutritionEnrichment.js`) |
| Open Food Facts | Nutrition fallback (task 11) | No key; usage form requested | none (custom `User-Agent` only) |
| Kroger QA account | E2E, emulator profile `kroger-authenticated` | none | `kroger-test-account` |
| Amazon Associates | Phase 2 attribution for Amazon Fresh / Whole Foods (task 12) | Associates application review | `AMAZON_ASSOCIATES_TAG` |
| Amazon Creators API | Phase 2 product search (task 12) | **10 qualifying sales in the past 30 days** before API access | `AMAZON_CREATORS_CREDENTIAL_ID`, `AMAZON_CREATORS_CREDENTIAL_SECRET`, `AMAZON_CREATORS_VERSION` |

#### A1. Walmart Affiliate API (walmart.io)

Docs: [Introduction](https://walmart.io/docs/affiliates/v1/introduction), [Quick Start](https://walmart.io/docs/affiliates/v1/quickstart), [Additional Headers](https://walmart.io/docs/affiliates/v1/additional-headers), [Key tutorial](https://walmart.io/key-tutorial).

1. Sign in at walmart.io with a Walmart.com account (create one for Millernest Labs, not a personal shopping account).
2. Create an application (name, description, use case: "recipe app sending grocery lists to Walmart").
3. Generate an RSA key pair locally (per the key tutorial: 2048-bit, private key PKCS#8). Upload the **public** key in the dashboard. walmart.io then issues the **Consumer ID** and a key version.
4. Smoke call: `GET https://developer.api.walmart.com/api-proxy/service/affil/product/v2/taxonomy` with the four signed headers. Store the taxonomy response (redacted) in the task log.
5. **Request `storeId` approval.** [Product Lookup](https://walmart.io/docs/affiliates/v1/product-lookup) says: "Price and availability is also dependent on zipCode and storeId ... Usage of storeId as option to lookup need additional approval from business team." Contact through the walmart.io portal ("Open Chat" / support). Say you show in-store prices for a user-selected store and send carts via affiliate add-to-cart links. Until it's approved, use `zipCode` (no approval needed per the same page); prices then come from the ZIP's default store rather than the exact store.
6. Also note from [Introduction](https://walmart.io/docs/affiliates/v1/introduction): "Several categories are excluded from the API calls." Task 03 checks that grocery/food is returned for common ingredients.

Does Impact matter? The Quick Start needs only the walmart.io app and key; `publisherId` is an **optional** query parameter on [Search](https://walmart.io/docs/affiliates/v1/search) and [Product Lookup](https://walmart.io/docs/affiliates/v1/product-lookup). Impact ([affiliates.walmart.com](https://affiliates.walmart.com/)) only fills the `|PUBID|` in `productTrackingUrl` / `affiliateAddToCartUrl` so purchases earn commission. Apply to Impact in parallel; it does not block development. Without it, the add-to-cart link still works with no attribution.

#### A2. Kroger Public API

Docs: [Quick Start](https://developer.kroger.com/documentation/public/getting-started/quick-start), [API Basics (environments, rate limits)](https://developer.kroger.com/documentation/public/getting-started/apis), [Customer OAuth2 + PKCE](https://developer.kroger.com/documentation/public/security/customer), [Products API](https://developer.kroger.com/api-products/api/product-api-public), [Locations API](https://developer.kroger.com/api-products/api/location-api-public), [Cart API](https://developer.kroger.com/api-products/api/cart-api-public).

1. [Create a developer account](https://developer.kroger.com/create-account/) and verify the email.
2. [Register the application](https://developer.kroger.com/manage/apps/register) in **Production**. Credentials are locked to one environment, and "user accounts are not available in the certification environment", so Cart/Identity only work in Production. Register a second app in Certification only if a sandbox for Locations/Products is wanted.
3. Redirect URI: `<server public URL>/api/retailers/kroger/callback` (plus a `dev` host URI). Scopes: `product.compact cart.basic:write profile.compact`.
4. Smoke call: `POST https://api.kroger.com/v1/connect/oauth2/token` with `grant_type=client_credentials` (Basic auth) -> access token.
5. Rate limits to plan around: Products 10,000/day, Locations 1,600/day per endpoint, Cart 5,000/day. Higher limits are only for Partner APIs (separate relationship; not needed now).
6. Create the dedicated QA shopper at [kroger.com/account/create](https://www.kroger.com/account/create?redirectUrl=/).

#### A3. Instacart Developer Platform

Docs: [Get started](https://docs.instacart.com/developer_platform_api/get_started/overview), [Get an API key](https://docs.instacart.com/developer_platform_api/get_started/api-keys), [Developer terms](https://docs.instacart.com/developer_platform_api/guide/terms_and_policies/developer_terms), [Developer guidelines](https://docs.instacart.com/developer_platform_api/guide/terms_and_policies/developer_guidelines).

1. [Apply](https://www.instacart.com/company/business/developers). A development key works against `https://connect.dev.instacart.tools`.
2. Instacart states "The average integration time from access request to demo approval and production key access is approximately 30-40 days." Plan task 05 after Walmart and Kroger; build against the virtualizer meanwhile.
3. Read the developer messaging guidelines before writing button copy ("Get Recipe Ingredients" style rules).

#### A5. Amazon Fresh and Whole Foods (task 12)

Phase 1 needs **no account**. It uses the ingredients landing form. Phase 2 needs Associates + Creators API.

Docs: [Creators API introduction](https://affiliate-program.amazon.com/creatorsapi/docs/en-us/introduction), [Onboarding](https://affiliate-program.amazon.com/creatorsapi/docs/en-us/onboarding), [Sign up as an Associate](https://affiliate-program.amazon.com/creatorsapi/docs/en-us/onboarding/sign-up-as-an-amazon-associate), [Register for Creators API](https://affiliate-program.amazon.com/creatorsapi/docs/en-us/onboarding/register-for-creators-api), [Migration from PA-API](https://affiliate-program.amazon.com/creatorsapi/docs/en-us/migrating-to-creatorsapi-from-paapi), [API rates](https://affiliate-program.amazon.com/creatorsapi/docs/en-us/concepts/api-rates), [PA-API 5 deprecation](https://affiliate-program.amazon.com/creatorsapi/docs/en-us/paapiv5-deprecation), [Operating agreement](https://affiliate-program.amazon.com/help/operating/agreement/), [Program policies](https://affiliate-program.amazon.com/help/operating/policies).

1. Capture MFP's exact Amazon link (user action, no tooling): in MFP, Shop -> Amazon Fresh opens `myfitnesspal.com/v2/mealapp/grocery/delivery/amazonFresh?i=...`. **Long-press "Continue on Amazon Fresh" -> Copy Link** (or open the page on desktop and inspect the button). Record the host, path (expected `/afx/ingredients/landingencoded` or `/afx/ingredients/landing`), parameter names, how the ingredients are encoded (base64 / URL-encoded JSON), and any `almBrandId`, `tag` or `ref` parameters. Redact nothing structural, but do not keep personal data. Repeat for Whole Foods.
2. Phase 1 verification (no account; manual, from a lab or personal machine with a signed-in Amazon account in a US Fresh delivery area):
   - Build a local HTML form that POSTs `ingredients={"ingredients":[{"name":"roma tomato","quantityList":[{"unit":"count","amount":3}]},{"name":"olive oil","quantityList":[{"unit":"tbsp","amount":2}]}]}` to `https://www.amazon.com/afx/ingredients/landing`. Record the resulting page (screenshot), which storefront it uses, and whether each line matched.
   - Repeat with `almBrandId=VUZHIFdob2xlIEZvb2Rz` (Whole Foods) and `almBrandId=QW1hem9uIEZyZXNo` (Fresh) as query parameters on the action URL. Record whether the storefront changes.
   - Test units: `count`, `each`, `lb`, `oz`, `cup`, `tbsp`, `tsp`, `g`, `ml`. Record which are understood. Test a 40-line list for any cap.
   - Test from a phone: tap the captured GET link from a web page on another domain; confirm the Amazon app opens (expected, as with MFP). Tap a POST form to `/landing`; record whether the app or the browser opens.
3. Phase 2 prerequisites (only when the user decides to pursue it):
   - [Sign up as an Amazon Associate](https://affiliate-program.amazon.com/creatorsapi/docs/en-us/onboarding/sign-up-as-an-amazon-associate) with the Millernest Labs account (the same account must be used for Creators API so sales are attributed).
   - Reach **10 qualifying sales in 30 days** through Associates links (Phase 1 handoff pages are not Associates links, so this requires separate tagged links, for example Phase 2 add-to-cart links once enabled, or other content).
   - In Associates Central -> Tools -> Creators API: Create Application, then Create Credential. Store the **Credential ID, Credential Secret (shown once) and Version** in K8s Secrets.
   - Initial limit is 1 TPS / 8,640 TPD for 30 days, then it scales with shipped revenue. Access is revoked after 30 days without qualified sales.
   - Verify whether `https://www.amazon.com/gp/aws/cart/add.html?ASIN.1=&Quantity.1=&AssociateTag=` still adds grocery ASINs to the Fresh / Whole Foods cart. Its old doc page now redirects to the PA-API deprecation notice.

#### A4. Nutrition sources (task 11)

- USDA FDC: [API guide](https://fdc.nal.usda.gov/api-guide), [key signup](https://fdc.nal.usda.gov/api-key-signup), [bulk downloads](https://fdc.nal.usda.gov/download-datasets). 1,000 requests/hour/IP; CC0 public domain (citation requested).
- Open Food Facts: [API intro](https://openfoodfacts.github.io/openfoodfacts-server/api/), [data exports](https://world.openfoodfacts.org/data). No key; custom `User-Agent: Carte/<ver> (<contact email>)`; 15 product reads/min/IP; ODbL license (attribution + share-alike on the derived database); fill the API usage form.

### B. Handoff behavior spike (device, no product code)

1. On the shared Android emulator (`walmart-authenticated` profile) run `adb shell am start -a android.intent.action.VIEW -d "<affil add-to-cart URL with 2 real itemIds>"`. Record: does the Walmart app (`com.walmart.android`) open directly, does a chooser appear, does Chrome open. Repeat with `-p com.walmart.android` to force the package.
2. Test quantity syntax: `items=<id>|2,<id>|1` vs repeated ids. Record which one sets quantity.
3. Record whether the affiliate URL through `goto.walmart.com` (tracking) still ends in the app.
4. `adb shell pm get-app-links com.walmart.android` and the same for Kroger (`com.kroger.mobile`) and Instacart (`com.instacart.client`) to list verified App Link hosts. Verify the package names from the Play Store listing before relying on them.
5. iOS (user, physical iPhone): open the same URLs from Notes and from a test Expo build via `Linking.openURL`; record whether the Walmart app opens. Universal links do not fire on some redirect chains; if the app does not open, test `https://www.walmart.com/...` targets directly.

### C. Mechanism confirmation for ReciMe and MFP (non-invasive)

Already settled by the challenge screenshots (see overview): MFP hands off to the native Walmart and Kroger apps, MFP's Kroger sign-in is an embedded view, and the Walmart handoff does not carry the store. Still open:

1. Install ReciMe and MFP on the emulator or a personal phone on a network with DNS logging (for example Pi-hole query log). Run each app's shop flow once for Walmart and Kroger.
2. Record only **hostnames** contacted (for example `developer.api.walmart.com`, `api.kroger.com`, `connect.instacart.com`, or an aggregator host). Do not intercept TLS, decompile, or bypass certificate pinning.
3. With real Walmart affiliate keys, call the Stores API for ZIP 75098 and compare its fields to MFP's store list ("Wylie N S State Hwy 78 Supercenter #5210"). If the affiliate API cannot produce names that descriptive, record which fields it does return; Carte composes a name from them (for example `<city> <type> #<no>`).
4. Confirm the affiliate add-to-cart link lands in the Walmart app's current store cart (expected per screenshot 7) and record whether a `storeId` parameter on the link changes anything.

## Acceptance criteria

- Findings table in `amminox/research/retail-integrations/README.md` with each overview Inferred item marked Verified/Refuted plus evidence (screenshot or command output).
- Secrets exist in the `dev` namespace (names only reported) or the task is `BLOCKED (<vendor> approval pending)`.
- Quantity syntax and Android/iOS handoff behavior for the Walmart link are recorded.

## Evidence to report

Command outputs from step B, hostname lists from step C, vendor approval status per row.

## Do not

- Do not submit vendor applications, accept terms, or create accounts without the user's explicit go-ahead (platform-operations approval gate).
- Do not MITM, decompile, or scrape ReciMe/MFP.
- Do not commit any key material, including test keys.

## Log
