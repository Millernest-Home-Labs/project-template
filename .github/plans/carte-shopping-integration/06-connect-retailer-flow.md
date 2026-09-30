# 06: Connect-Retailer Flow (ZIP, Stores, Sign-in)

Status: TODO
Owner repo: `amminox` (branch `feature/connect-retailer-zip`)
Depends on: 02; 04 for the Kroger sign-in step
Skills: `frontend-implementation`

## Goal

Settings -> Retailers -> Add Retailer: choose a retailer, **enter a ZIP code**, pick one of the closest stores, sign in when the retailer requires it, done. Matches challenge screenshots 2, 3 and 8.

## Context

`client/src/components/retailers/RetailersScreen.tsx`, `client/app/settings/retailers.tsx`, `RetailerSignIn.native.tsx` / `.web.tsx` (Walmart WebView sign-in from MVP8 Amendment 2a), `walmartSignIn.ts`, `clearWalmartSession.*`.
## Constraints

- Expo single codebase (web + iOS + Android). TypeScript strict, no `any`; ESLint zero errors; jest-expo tests for every new component and state.
- Kroger sign-in uses `expo-web-browser` `openAuthSessionAsync` with the app scheme `amminox` (`client/app.json`). It is a system auth sheet, never `react-native-webview`.
- ZIP validation is client-side for UX and server-side for trust (`^\d{5}$`); the server rejects anything else with 400.
- Location permission is requested only when the user taps "Use my location".
- Mobile-first layouts; loading, empty and error states for every async step.

## Steps

1. Retailer list: active providers from `GET /api/retailers` (Walmart, Kroger, Instacart); others stay "coming soon".
2. ZIP step (new, first; matches MFP screenshot 2 "Select store"): 5-digit US ZIP input with validation, prefilled from the last used ZIP; secondary "Use my location" shortcut (existing geolocation path). Copy: "We'll use your location to find local <Retailer> stores offering pickup or delivery."
3. Store list (MFP screenshot 3): `POST /api/retailers/nearby` results closest first (store name with number, street, city/state/ZIP, distance in miles, chevron); loading, empty ("No stores within 50 miles of 12345") and error states. For Instacart, list retailers available at that ZIP.
4. Store confirm screen (existing pattern): name, address, distance, Continue.
5. Sign-in step only when `capabilities.requiresAccountLink`:
   - Kroger: `POST /api/retailers/kroger/link/start` -> `WebBrowser.openAuthSessionAsync(authorizeUrl, "amminox://retailers/linked")`; parse `status` from the return URL; on success refetch connections. Web build: same flow with a normal redirect back to the web app route.
   - Walmart and Instacart: no sign-in step. Remove the Walmart WebView sign-in (`RetailerSignIn.*`, `walmartSignIn.ts`, `clearWalmartSession.*`) and their tests; the Walmart app keeps its own session.
6. Connected retailers list shows store + ZIP, "Change store", and for Kroger the link state (Linked / Sign in again / Disconnect).
7. Tests: jest for each step and state; Playwright web E2E against virt (ZIP -> stores -> connect; Kroger virt consent -> linked).

## Acceptance criteria

- Adding Walmart asks for ZIP first and lists stores closest first from the provider API.
- Adding Kroger opens Kroger's sign-in in the system auth sheet (virt consent page in E2E) and returns Linked.
- No WebView is used anywhere in the connect flow.

## Evidence to report

jest and Playwright output; screenshots of each step (retailer list, ZIP, store list, store confirm, Kroger linked state) from web and the Android emulator; grep showing `RetailerSignIn`, `walmartSignIn` and `clearWalmartSession` are removed.

## Do not

- Do not store the ZIP or location anywhere except the user's connection row.
- Do not keep the Walmart WebView sign-in as a fallback.
- Do not request location permission on screen load.

## Log
