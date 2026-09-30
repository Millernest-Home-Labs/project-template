# 09: Cart Handoff to the Retailer App

Status: TODO
Owner repo: `amminox` (branch `feature/cart-app-handoff`)
Depends on: 08; task 01 handoff findings
Skills: `frontend-implementation`, `backend-implementation`

## Goal

"Send to cart" puts the items in the retailer's cart and opens the retailer's **native app** (challenge screenshots 7 and 11), not a WebView. MFP does exactly this for Walmart and Kroger; iOS shows "< MyFitnessPal" in the retailer app, which confirms an app-to-app open.

## Context

Current flow: `GroceryShoppingScreen.tsx` builds the affiliate deep link on the client (`client/src/lib/walmartDeepLink.ts`, public `EXPO_PUBLIC_WALMART_AFFILIATE_KEY`). Native opens it in `ShopCartWebView.native.tsx`; web opens a new tab. The superseded MVP8 cart assist (bookmarklet, injected script, handoff tokens, walmart.com CORS exception) is still in the codebase. MFP screenshots 7 and 11 show the target: the retailer's own app opens with the cart.

## Constraints

- Handoff URLs are built only on the server (task 03/04/05 providers) and checked against the per-provider host allowlist on both server and client.
- Android package names and iOS behaviors come from task 01 findings, never guessed. `expo-intent-launcher` is added only if task 01 shows `Linking.openURL` does not reach the app.
- Removing the superseded cart-assist code must also remove its server route, CORS exception and tests in the same PR.
- Honesty rule: "Added" only for Kroger API-confirmed lines; Walmart and Instacart say "Sent".

## Flow per provider

| Provider | Server (`POST /api/shops/:id/cart`) | Client |
|---|---|---|
| Kroger (`server-api`) | Adds items via Cart API; returns per-item result + `openUrl` (banner cart URL) | Shows "Added N items to your Kroger cart" (only confirmed items), lists failures, button "Open Kroger" |
| Walmart (`handoff-url`) | Returns affiliate add-to-cart URL with quantities | "Sending your list to Walmart" beat, then opens the URL; copy says items were sent and Walmart confirms |
| Instacart (`handoff-url`) | Returns cached `products_link_url` | Opens the URL; copy says the list was sent |

## Steps

1. `client/src/lib/retailerHandoff.ts`:
   - Validate `openUrl` host against the per-provider allowlist from `GET /api/retailers` (defense in depth; reject otherwise).
   - Android: `Linking.openURL(openUrl)`; the OS routes verified App Links to the installed app. If task 01 shows a chooser or browser, use `IntentLauncher.startActivityAsync("android.intent.action.VIEW", { data: openUrl, packageName })` with the verified package, catching `ActivityNotFoundException` -> fallback to `Linking.openURL`.
   - iOS: `Linking.openURL(openUrl)` (universal links open the app when installed). Add `LSApplicationQueriesSchemes` only if task 01 finds a documented custom scheme is needed; do not guess schemes.
   - App not installed: browser opens the same URL (works signed-in or prompts Walmart login there); show a secondary "Get the <Retailer> app" link using store ids from provider/chain data.
   - Web build: `window.open(openUrl, "_blank", "noopener")`.
2. Return-to-app: on `AppState` active after a handoff, show the completion screen (what was sent, when, to which store) and mark the shop `sent` (handoff) or `added` (Kroger confirmed).
3. Delete superseded code and tests: `ShopCartWebView.*`, `CartAssistBookmarklet.tsx`, `cartAssistScript.ts`, `server/src/cart-assist.js`, handoff-token route and CORS exception for walmart.com, `walmartDeepLink.ts` (logic moved server-side), related `__tests__` files. Update REQUIREMENTS.md and MVP docs to record the ruling change (handoff to native app replaces WebView).
4. Tests: jest for allowlist rejection, Android intent fallback, completion states; server tests for Kroger partial failure; Maestro flow on the shared emulator (task 10).

## Acceptance criteria

- On Android with the Walmart app installed and signed in, Send opens the Walmart app and the items are in its cart (screenshot).
- On Android with the Kroger app signed in to the QA account, Send adds items via API and "Open Kroger" shows them in the app cart (screenshot).
- No `react-native-webview` usage remains in the shop flow; grep evidence.
- "Added" is only shown for Kroger items the API confirmed.

## Evidence to report

Walmart and Kroger app cart screenshots after a handoff from Carte (emulator profiles `walmart-authenticated`, `kroger-authenticated`); iOS screenshots from the user's phone if available; grep evidence for removed files; jest output for allowlist and fallback cases.

## Do not

- Do not open arbitrary server-provided URLs without the host allowlist check.
- Do not keep the bookmarklet or injected-JS paths as fallbacks.

## Log
