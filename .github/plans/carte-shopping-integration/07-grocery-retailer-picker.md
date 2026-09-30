# 07: Groceries Shop -> Retailer Picker

Status: TODO
Owner repo: `amminox` (branch `feature/grocery-retailer-picker`)
Depends on: 06
Skills: `frontend-implementation`

## Goal

On the Groceries page, **Shop** opens a picker listing only the retailers the user connected. MFP's sheet (challenge screenshot 1) lists every partner ("Shop with Instacart / Walmart / Kroger stores / Whole Foods / Amazon Fresh"); Carte uses the same row style but filters to connected retailers, per the challenge. Picking one starts a shop for that retailer and store.

## Context

`client/app/(tabs)/grocery.tsx`: `handleShop(retailer)`, per-retailer cards defaulting to `walmart`, "Export to Walmart" and "Shop this online" buttons, `api.shopGroceryList(listId, retailer)`.
## Constraints

- The picker is a bottom sheet on native and a modal on web, sharing one component. TypeScript strict, jest-expo tests.
- Old endpoints (`shopGroceryList` legacy path, Walmart export) stay working until this PR removes their last caller; the server route removal ships in the same PR as the client change (hard rules: never deploy a server that breaks the deployed client).
- Connection data comes from `GET /api/retailers/connections`; no retailer list is hardcoded in the client.

## Steps

1. Replace per-retailer "Shop this online" buttons and "Export to Walmart" with one **Shop** action on the list.
2. Bottom sheet: rows for each connection (logo, retailer name, store name + city, chevron). Kroger rows with `link_status != linked` show "Sign in again" and route to the Kroger link step. Footer row "Add a retailer" -> task 06 flow, returning to the sheet afterwards.
3. Empty state (no connections): the sheet shows the connect CTA directly.
4. Remember the last used retailer and preselect it (still requires a tap to confirm).
5. Server: `POST /api/grocery-lists/:id/shop { retailer, storeId }` creates a shop with `retailer_key` + `store_id` (task 02 schema) and starts resolution; recipe "Shop this Recipe" uses the same picker.
6. Tests: jest (0, 1, many connections; expired Kroger link), Playwright (connected Walmart + Kroger in virt -> Shop -> both listed).

## Acceptance criteria

- Only connected retailers are listed; picking one opens the review page (task 08) for that store.
- Old Walmart-only buttons are gone.

## Evidence to report

jest and Playwright output; screenshots of the picker with 0, 1 and 2 connections and with an expired Kroger link.

## Do not

- Do not list retailers the user has not connected (MFP lists all partners; the challenge asks for connected only).
- Do not start a shop without an explicit tap on a retailer row.

## Log
