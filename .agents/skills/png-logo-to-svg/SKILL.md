---
name: png-logo-to-svg
description: 'Convert a PNG logo (e.g. found on Google Images) into a clean, compressed, tightly-cropped SVG. Use when: convert PNG to SVG, vectorize logo, SVG conversion, compress SVG, crop SVG viewport, remove white background from SVG, logo vectorization.'
---

# PNG Logo → SVG

Purpose: turn a PNG logo into a production-ready SVG using the three-stage pipeline the
user follows manually. The agent drives the same web tools the user uses, verifies each
stage, and hands back a single final SVG file.

## When to Use

- The user provides a PNG logo (path, pasted image, or URL) and wants an SVG
- The user asks to "vectorize", "convert", "compress", or "crop" a logo/SVG
- The user asks to remove a white background from an SVG

## Step 0 — Ask the use case FIRST (mandatory)

Before converting anything, determine **where the SVG will be displayed**. The same
brand can need completely different assets:

| Use case | Ideal shape | Example |
|----------|-------------|---------|
| Square slot (list item, avatar, app icon, badge) | ~1:1 tile or roundel | retailer icon in a 90×90 gift-list card |
| Header / footer / banner | wide wordmark OK | brand bar on a website |
| Inline with text | wordmark sized to text height | "powered by" line |

**Fitness test for a square slot:** compute the viewBox aspect ratio. If it is wider
than ~1.4:1 (or taller than ~1:1.4), the logo will be cropped to a sliver by
`resizeMode="cover"` in a square box, or render illegibly small. A 3.6:1 wordmark in a
90×90 cover box shows only ~28% of the logo.

**If the wordmark fails the fitness test, do not convert it — find the brand's square
treatment instead:**

1. **App icon (best):** the official iOS app icon is a purpose-built square tile.
   Look it up with Apple's iTunes API (no key needed):
   `https://itunes.apple.com/search?term=<brand>&entity=software&country=us&limit=10`
   → take `results[0].artworkUrl512` for the official app (verify `trackName`).
   Example: Costco → `com.costco.costco` → red "C" roundel, 512×512.
2. **Wikimedia Commons:** search `https://commons.wikimedia.org` for a square variant
   (rare — most brand marks there are wide wordmarks).
3. **Last resort:** pad the wordmark onto a brand-colored square tile yourself — but
   only with the user's sign-off, since that is a derived asset, not the official mark.

Report the aspect ratio and the chosen treatment to the user before running the
pipeline.

## Pipeline Overview

| Stage | Tool | Purpose |
|-------|------|---------|
| 0. Fit | use-case check (this file) | Pick the right source asset for the target slot |
| 1. Convert | [pngtosvg.com](https://www.pngtosvg.com/) | Raster → vector paths |
| 2. Compress | [vecta.io/nano](https://vecta.io/nano) | Minify SVG markup |
| 3. Crop | [svgcrop.com](https://svgcrop.com/) | Trim unused viewport margins |

Stages 1–3 are automated by [convert-pipeline.js](./scripts/convert-pipeline.js) —
prefer running it over hand-driving the sites.

Stage order matters: compress before crop, so the cropper sees the final markup and the
output is not re-inflated by whitespace after trimming.

## Tool Mechanics (verified 2026-10-04)

All three tools run **entirely client-side** — there are no upload APIs to call. Drive
them with Playwright (`chromium`, headless works for all three).

### Stage 1 — pngtosvg.com

- Single hidden `input[type=file]` (accept `image/*`); use `setInputFiles` directly.
- After upload, pick the **"Logo / Clip art"** mode button for flat-color logos, then
  wait ~8s for the re-trace.
- **Download** opens a modal with `SVG` / `PNG` / `PDF` options — click **SVG** and
  capture the `download` event.
- Output contains a full-canvas `<path fill="#ffffff">` background (letter-shaped holes
  punched out) plus one path per color. Delete the white path with
  `[regex]::Replace($svg, '<path[^>]*fill="#ffffff"[^>]*/>', '')`.

### Stage 2 — vecta.io/nano

- No file input — a dropzone `<section id="drop.id">` (the id literally contains a dot;
  selector is `[id="drop.id"]`). There is no `setInputFiles` target; dispatch a
  synthetic drop **inside one `page.evaluate`** (a `DataTransfer` cannot cross the
  Node/browser boundary):
  build a `File` from the SVG bytes, add to `DataTransfer`, dispatch
  `new DragEvent('drop', { dataTransfer: dt, bubbles: true })` on the zone.
- Wait ~15s; the result card shows the savings (e.g. "46.9% saved").
- Nano's compression works by rewriting absolute path commands to relative and adding
  root attributes (`fill-rule="evenodd"`, `stroke-width=".25"`,
  `stroke-linejoin="round"`) — output markup will differ from input; that is expected.
- Nano sets `width="600" height="400"` (its preview canvas size) regardless of the
  viewBox aspect ratio. Harmless in the full pipeline because Stage 3 strips them, but
  if cropping is skipped, fix width/height to match the viewBox before delivering.
- The **Download** anchor (`href="#"`) may not emit a Playwright download event.
  Reliable capture: patch `URL.createObjectURL` before clicking to record every blob's
  `text()`, click via `page.evaluate`, then take the **last** captured blob — the first
  is the preview render, the last is the compressed output.

### Stage 3 — svgcrop.com

- Real `input#myfile` (accept `.svg`) — use `setInputFiles`.
- Wait for `.ButtonWrap a[download*="-cropped"]`, then decode its `data:image/svg+xml;base64`
  `href` to get the cropped SVG.
- svgcrop **strips `width`/`height`** from the root, leaving only `viewBox`. That is
  usually desirable (the SVG scales to any container), but if a fixed size is needed,
  re-add `width`/`height` matching the viewBox after cropping.
- Cropping is a no-op when the artwork already fills the viewBox — the output may be
  byte-identical (or near-identical) to the input. That is a pass, not a failure.

## Workflow

0. **Determine the use case and pick the right source asset** (see Step 0 above). If
   the user's source asset fails the fitness test for the target slot, source the
   square treatment (e.g. app icon via iTunes lookup) and use that as the pipeline
   input instead.
1. **Resolve the source PNG.** Accept an explicit path, a pasted image (newest
   `image-*.png` under
   `%USERPROFILE%\AppData\Roaming\Code - Insiders\User\workspaceStorage\vscode-chat-images\`),
   or a Google Images URL. For brand logos, Wikimedia Commons is a reliable source:
   query `https://en.wikipedia.org/w/api.php?action=query&titles=File:<Name>&prop=imageinfo&iiprop=url|size&format=json`
   and download the `imageinfo.url`. Work in a temp directory; never overwrite the
   user's original.
2. **Stage 1 — Convert.** Run the pipeline script:
   `node <skill>/scripts/convert-pipeline.js <input.png> <output.svg>` (set
   `NODE_PATH` to a Playwright install first — see Notes). It drives all three tools
   in sequence, strips the white background after Stage 1, and prints the size table.
   For flat-color logos the script selects **Logo / Clip art** mode. If running the
   stages manually instead, follow the Tool Mechanics below and **edit the SVG to
   remove any white background**: delete the full-canvas white `<path>`/`<rect>` and
   verify no element paints the full viewBox area in white.
3. **Stage 2 — Compress.** (handled by the script) Verify the result is valid XML and
   smaller than the input.
4. **Stage 3 — Crop.** (handled by the script) Verify the `viewBox` tightly bounds the
   drawn content (no large empty margins) and the artwork still renders.
5. **Verify the final artifact.** Confirm the file parses as XML, renders non-blank
   (screenshot the SVG loaded via `file://` and check dominant pixel colors), and
   report the byte size at each stage (original PNG → converted → compressed →
   cropped). Sanity-check the root: no `fill="#ffffff"` anywhere, and `viewBox` present
   (`width`/`height` are stripped by Stage 3 — that is expected). **Re-run the Step 0
   fitness test on the final viewBox** and confirm the asset suits the stated use case.
6. **Deliver.** Save the final SVG next to the source PNG (e.g. `logo.svg`) and report
   the path plus the stage-by-stage size table.

## Gotchas (hit in practice)

- **Playwright download events are unreliable on these sites.** pngtosvg's modal SVG
  button does fire `download`, but Vecta's anchor does not — the blob-interception
  technique in Stage 2 mechanics is the dependable pattern for both. When a download
  event times out, don't retry blindly; switch to interception.
- **`page.dispatchEvent` cannot carry a `DataTransfer`** — Playwright serializes
  event-init across the Node/browser boundary and `DataTransfer` isn't serializable
  (`Failed to construct 'DragEvent'`). All drop simulation must happen inside a single
  `page.evaluate`.
- **Element ids on these sites contain dots** (`drop.id`, `uploads.id`,
  `download_all.id`). A bare `#drop.id` selector means "class `id`" in CSS — always use
  the attribute form `[id="drop.id"]`.
- **App state is nondeterministic between runs** (ad/consent scripts, timing). A
  selector that is visible in one run may be hidden in the next. Poll for the expected
  UI state (e.g. anchors matching `/download/i` with non-zero rects) instead of
  assuming, and re-check before every click.
- **Consent/ad popups** (Ezoic, gatekeeper CMP) can overlay the page. If a click is
  blocked, look for a `Consent` button and dismiss it first.
- **The white background is not always a `<rect>`.** pngtosvg emits it as a full-canvas
  `<path fill="#ffffff">` with the letter shapes punched out as subpaths — deleting it
  is safe because the logo paths render on transparency.

## Notes

- If a web tool is unreachable, report the failure and stop — do not substitute a
  different converter or write custom conversion code; the user's pipeline is
  tool-specific by intent.
- Keep intermediate files (`stage1.svg`, `stage2.svg`) until delivery, then clean up
  temp files, preserving only the source PNG and final SVG.
- Playwright module resolution: scripts run outside a `node_modules` tree need
  `$env:NODE_PATH = '<repo>\<product>-client\node_modules'` (e.g. the client's
  Playwright install).
- **Wikimedia is a better source than Google Images for brand logos** — Google's image
  results are often photos of storefronts or re-compressed thumbnails; Wikimedia
  Commons hosts the canonical asset (and often an official SVG already). If Wikimedia
  has the logo as SVG, tell the user — running the raster pipeline on it is
  unnecessary.
- **App icons from the iTunes lookup are JPEGs** (`512x512bb.jpg`) with opaque white
  corners outside the rounded tile. pngtosvg traces the white corners as background —
  the Stage-1 white-background strip removes them, leaving the tile shape on
  transparency. Verify the corners are gone in the final render.
