---
name: gui-screenshot-annotation
description: Use when the user pastes a screenshot and wants it marked up, annotated, or diagrammed with red drawings labeling GUI elements (red boxes, leader lines, numbered callouts, term tags). Produces a professionally annotated copy of the screenshot using standard UI/UX vocabulary from the gui-interface-diagramming skill.
---

# GUI Screenshot Annotation (Red Markup)

Purpose: turn a pasted screenshot into an annotated diagram where GUI elements are boxed in red and labeled with their proper UI/UX terms.

## HARD RULE: never write new Python scripts

`annotate.py` beside this skill is the **stable rendering engine**. It already implements
every drawing rule (red rounded boxes, pill tags, auto-placement, overlap validation,
baked-markup gate). You must NOT write, generate, or inline any new Python code to do
measurements, rendering, cropping, or annotation — no `py -c "..."` one-liners that draw,
no `final_annotate.py`, no per-image copies of the engine.

The ONLY Python artifact you may create per image is a **manifest file** — a tiny
declarative Python module (see step 6) containing `SRC`, `SCALE`, and a `CALLOUTS` list.
Everything else is done by running the existing scripts:

- `python grid.py <input> <tmp-grid.png> 100` — calibration grid
- `python annotate.py <manifest.py>` — render the annotation

If a render looks wrong, fix the manifest's coordinates and re-run `annotate.py`.
Never patch the engine or write a replacement script.

## Workflow

1. **Locate the canonical image file.** A pasted chat image must exist on disk to be edited. Pasted images land in `%USERPROFILE%\AppData\Roaming\Code - Insiders\User\workspaceStorage\vscode-chat-images\` — find the newest `image-*.png` there, or ask the user to save it into the workspace (e.g., `GUI Interface Diagrams/`) and provide the path. Use the original full-resolution file, never a preview, crop, or browser-scaled render.
2. **Measure the real canvas first.** Run `python grid.py <input> <tmp-grid.png> 100` (it prints the true width/height) and record the real dimensions. Treat the image as pixel-accurate source of truth. If the canvas differs from the visible preview, trust the real pixels.
3. **Calibrate with a coordinate grid.** Draw a labeled grid on the source at 100px steps and read the exact pixel coordinates for each element off the lines. Never author coordinates by eyeballing from a chat preview or a resized screenshot. Error compounds away from `(0,0)`.
4. **Create a calibration ledger before drawing.** Record a per-element list like `term | box=(x0,y0,x1,y1) | side | justification`. If a box was estimated instead of measured, reject it and remeasure. This ledger is mandatory, not optional.
5. **Build a callout manifest.** For each element, record: `term`, `box=(x0,y0,x1,y1)`, `tag_side`, and `notes` like “full-width row” or “inside inset grouped list.” Use the standard vocabulary in the **gui-interface-diagramming** skill. If the user leaves a fill-in-the-blank term, resolve it before drawing and state the decision explicitly.
6. **Draw the markup by running the engine** — write a manifest file (the only per-image
   artifact allowed) and run `python annotate.py <manifest.py>`. The manifest is a tiny
   Python module, nothing more:

   ```python
   # manifest_<image>.py
   SRC = r"<path to clean source screenshot>"
   DST = None          # default: <SRC stem>-annotated.png next to the original
   SCALE = 3.0         # @3x screenshot: CALLOUTS coords are logical points
   BRIGHT_THRESHOLD = 40  # optional: raise (e.g. 45) for dark themes
   CALLOUTS = [
       # (term, (x0, y0, x1, y1) logical, tag_xy logical or None)
       ("Status Bar", (0, 13, 440, 49), (70, 53)),
       ("Button",     (24, 58, 135, 109), None),   # None = auto-place
   ]
   ```

   The engine draws the red rounded rectangles and pill-shaped name tags (number circle +
   term text, self-describing — no separate legend needed), validates tag placement, and
   saves as `<original-name>-annotated.png` next to the original. Do not write any other
   Python code; if the output is misaligned, correct the manifest coordinates and re-run.
7. **Validate alignment before finishing.** Open the output image and confirm: boxes hug the element bounds, tags are on the side with empty space, no callout overlaps another box, and nothing important is visually obscured. If any tag is off by more than a few pixels, reject the render and remeasure in source coordinates.
8. **Report.** Give the output path and a one-line summary of what was annotated.

## Calibration checklist (hard validation)

Before accepting any annotation, the agent must complete all of the following:

- **Source-of-truth check:** coordinates were measured from the real image file, not from a scaled preview or prior annotation output.
- **Grid check:** the agent used a 100px grid overlay and confirmed the element sits on the correct pixel bounds.
- **Boundary check:** every box begins and ends at the actual visual boundary of the element, not on an estimate.
- **Tag placement check:** the label side (`left`, `right`, `top`, `right-bottom`) was chosen only after checking for empty space.
- **Reject-on-drift rule:** if a label or box is visibly misaligned, the render is rejected and remeasured before continuing.
- **No stale coordinates:** never reuse a previous image's box list for a different screenshot.

## Annotation conventions (professional mark-up style)

- **Color:** one markup color — red `(232, 58, 68)`. Never multi-color unless the user asks for semantic coloring.
- **Boxes:** 6px rounded rectangles (radius 20) drawn just outside the element's bounds so the element stays fully visible.
- **Name tags (pill style), not a legend:** each box gets an adjacent **pill-shaped tag** — a red rounded rectangle containing a white number circle + the element's term in white bold text. The tag IS the label; no cross-referencing key.
  - Tag placement: `left`, `right`, `top`, or `right-bottom` of its box, vertically centered on the box edge (or above for `top`, below for `right-bottom`).
  - Choose the side with empty space; clamp tags so they never run off the image edge.
  - On narrow mobile screenshots prefer `left`/`right` beside the row; use `top` for full-width bars (tab bar) and `right-bottom` for large containers.
- **Nested elements:** when one element sits inside another (chevron inside a list cell inside a grouped list), shrink the inner boxes so outlines don't overlap — e.g., box the List Cell up to just before the chevron's box.
- **Density:** annotate all relevant elements in ONE output file per source image. Never split a screen into multiple annotated outputs; if tags compete for space, resolve placement (sides, stacking, leader lines) rather than splitting.
- **Coordinates:** author in ACTUAL pixel space (`grid.py` prints the real canvas size first — HiDPI screenshots are larger than they appear). This is a hard requirement, not a suggestion.
- **No new scripts:** any response that creates a Python file other than the manifest, or runs a `py -c` snippet that draws/annotates, is a violation of this skill. Re-do it with `annotate.py` + a manifest.
- **Alignment guardrails:** never “fix” a bad box by eye after the fact. If a tag or box is visibly off, revisit the measured rectangle and recompute it in source coordinates. Repositioning after the fact without a new measurement is a defect.
- **No guessing:** a callout must be traceable to a measured box and a chosen side. If the actual empty space is unclear, reduce scope and annotate only the clearest elements first.
- **Validation pass:** before reporting completion, spot-check at least one element per section of the frame and ensure every box begins/ends on the actual element boundary rather than on a rough visual estimate.

## Python/Pillow requirements

- Pillow (`pip install pillow`); bold font from `C:/Windows/Fonts/arialbd.ttf` (fallback `arial.ttf`).
- Draw on an RGBA overlay, then `Image.alpha_composite` onto the original so markup is crisp and the original pixels untouched.
- Output PNG (RGB) next to the input file with an `-annotated` suffix.

## Term resolution

- Element names come from the gui-interface-diagramming vocabulary (list cell, chevron/disclosure indicator, section header, badge, tab bar, etc.).
- Fill-in-the-blank pattern: choose the most standard term, mark it up, and call out the resolution explicitly in the reply (e.g., "`___ Card` → **Action Card**").
- When a new term is coined during annotation, add it to the gui-interface-diagramming table so both skills stay in sync.
## Element selection rules (MANDATORY)

- **Never annotate the OS status bar.** The status bar (clock, battery, signal, dynamic island) belongs to the phone, not the app. Skip it entirely.
- **Never use generic terms alone.** "Button", "Card", "Bar" are forbidden as complete names. If an element is a special button, name WHY it is special (e.g. "Log Button", "Go Premium Button", "Add FAB"). For containers, use the fill-in-the-blank pattern: "Calories Card", "Macros Card", "Meal List Card" — the qualifier says what the app uses it for.
- **Never annotate two instances of the same element.** If two elements are visually and functionally identical (e.g. identical meal cards, repeated Log buttons), annotate ONE representative instance. Only unique elements get callouts.
## Companion tools (beside this SKILL.md) — PLUG-AND-PLAY CONTRACT

**`annotate.py` is a stable engine. NEVER edit it per image. NEVER write a new
one-off annotation/measurement script.** All per-image work lives in a small
**manifest** file (e.g. `manifest_<screen>.py`); all reusable measurement
primitives live in `gui_annotation_helpers.py` and are exposed to manifests
automatically.

### Engine usage (the ONLY supported invocation)

```
python <skill-dir>/annotate.py <manifest.py> [source_image_override]
```

### Manifest format (the only per-image artifact)

```python
# manifest_<screen>.py
SRC = r"E:\...\IMG_8013.PNG"   # clean source screenshot
DST = None                     # default: <SRC stem>-annotated.png
SCALE = 3.0                    # @3x image: CALLOUTS coords are LOGICAL pts
                               # (use 1.0 if you measured in raw pixels)
BRIGHT_THRESHOLD = 40          # optional: open-space brightness threshold.
                               # Dark themes (card bg > 40) need ~45, or
                               # auto-placement finds no legal adjacent slot.

CALLOUTS = [
    # (term, (x0,y0,x1,y1) logical, tag_xy logical or None)
    ("Status Bar", (0, 13, 440, 49), (70, 53)),
    ("Button",     (24, 58, 135, 109), None),   # None = engine auto-places
]

def run_assertions(rgb_img, H):     # optional measured-fact checks
    H.assert_band(rgb_img, x=220, y_lo=673, y_hi=681, min_bright=12)
```

### Engine-provided guarantees (every run, zero per-image code)

1. **Baked-markup gate** — scans for exact annotation red; aborts if pre-annotated.
2. **Validator** — tags on-canvas, no tag/tag overlap, no tag/box crossing, no
   tag over bright source pixels; prints named failures and exits non-zero.
3. **Auto-placement** (`tag_xy=None`) — centered flush below/above/right/left,
   then vertical free-slot scan; first pixel-verified-open slot wins.
4. **Inclusive collision bounds** — touching is not overlapping.
5. **Clipboard + console placement report** on success.

### Helper primitives available in `run_assertions(rgb_img, H)`

`H.assert_band`, `H.assert_dark`, `H.find_row_bands`, `H.find_col_clusters`,
`H.bbox_of_bright`, `H.card_bands` — see `gui_annotation_helpers.py`. Use them
inside the manifest to pin measured facts (card edges, glyph bounds, slot
emptiness) instead of writing scripts.

### Iteration protocol

If the validator fails or the visual check finds drift: **edit only the
manifest** (boxes/tag slots/assertions) and re-run the engine. One render +
one verification view per iteration. Creating `measure_*.py`/`annotate_*.py`
scripts per image is a process defect — those primitives already exist in the
engine and helpers.

### Legacy

- `grid.py` — coordinate grid overlay for calibration:
  `python grid.py <input> <output> [step]` (still useful for a first look).
- `GUI Interface Diagrams/annotate_current.py` and `annotate_loseit.py` /
  `annotate_addfood.py` are historical reference implementations, superseded
  by the engine. Do not copy them for new work.

## Render-and-verify loop (MANDATORY - this is the step that was always skipped)

After rendering, the agent MUST:

1. **Detect baked-in markup.** Scan the source for annotation red `(232,58,68)` before drawing. If red pixels are already present, the file is a previously-annotated copy - STOP and find the clean original. Annotating an already-annotated image is always wrong.
2. **View the rendered output.** Open the output PNG in the browser (`file:///` URL), set the viewport to the image's natural size, and screenshot it. Compare against the source. Do NOT accept a render you have not looked at.
3. **Check each callout:** box edges coincide with element edges, tags do not overlap text or other tags, nothing runs off-canvas.
4. **Reject and remeasure on any misalignment.** Do not nudge coordinates by eye - re-derive the box programmatically (brightness band scans for cards, bright-pixel bounding boxes for text/icons) and re-render.
5. **Never hand-estimate coordinates from a scaled view.** Measure with `Image.open(...).size` and pixel scans. The image is usually @3x; a label that looks like it starts at x=352 in a scaled browser view may be at a different true x.

## Tag placement: prefer open space (MANDATORY)

When choosing a tag side, the agent MUST:

1. **Scan for open space first.** Check all four sides of the box for a region large enough for the tag (tag height + 10px margin). Prefer the side with genuinely empty canvas � the area above a bottom-anchored element, below a top-anchored one, or the wider gutter beside it.
2. **Never place a tag over open space when a covered alternative exists** � and conversely, never cover an element when open space exists nearby. Open space always wins.
3. **Covering is a fallback, not a default.** If no open space fits, covering an element is acceptable ONLY if that element is not the focal point of another annotation (don't obscure what another callout is highlighting).
4. **Tight boxes for small glyphs.** For small elements (chevrons, badges, icons), measure the glyph's actual bright-pixel bounds and box exactly that � padding of 2-4px max. A box larger than the glyph covers it and defeats the annotation.

## Hard no-overlap guard (MANDATORY - tags may NEVER cover their own element)

The most common and unacceptable failure mode: the tag for an element (e.g. a Disclosure Indicator) is rendered ON TOP of the very element it names. This is always a defect.

The annotator script MUST implement a collision guard, not rely on hand-picked coordinates:

1. **Collect every annotated element box** as tags are placed.
2. **Before drawing a tag, test its rect against** (a) its own element box, (b) every other element box, and (c) every already-placed tag.
3. **If the requested side collides, try the other sides** (top, right, left, bottom) in order. If all collide, push the tag OUTWARD from the box (e.g. centered directly above it) - never inward over the element.
4. **Never clamp a tag back over the element.** Clamping must only pull tags inside the CANVAS, never onto annotated boxes.

Reference implementation exists in `GUI Interface Diagrams/annotate_current.py` (the `overlaps` check + side-fallback loop). Reuse it.

> **Superseded:** the engine (`annotate.py`) implements this guard natively — see the plug-and-play contract below.

Rule of thumb: if you would have to cover the chevron to label the chevron, the label goes beside it - always.

## Nested elements: tags must escape the container (MANDATORY)

When annotating an element that sits INSIDE a larger annotated container (a chevron inside a list cell inside a grouped list), a side-placement that lands the tag anywhere inside the container's bounds is a defect - even if it misses the glyph itself. The tag text over the container interior reads as covering the element.

Rule: **the tag must be fully outside the parent container.**

1. Identify the innermost annotated ancestor container of the element.
2. Place the tag beyond that container's edge: above its top edge, below its bottom edge, or outside its left/right gutter.
3. A `below-container` / `above-container` placement (tag right-aligned with the container edge, just outside it) is the reliable default for trailing elements like chevrons on the right side of a full-width list.
4. Verify visually: the tag must not overlap ANY part of the container interior, not just the glyph.

## Minimum box padding (MANDATORY)

Boxes must never hug or touch the element. After measuring an element's bounds, expand the box outward by at least 8-12px on every side (at @3x scale) so the stroke floats clear of the element with visible breathing room. A box drawn exactly on the glyph bounds will cut into it because the stroke is centered on the path.

- Small glyphs (chevrons, badges, icons): +10-14px padding per side.
- Larger elements (rows, cards, bars): +6-8px per side is enough.
- The box should read as "surrounding" the element, never "tracing" it.

## Leading Icon callout

The icon at the start of a list cell is a **Leading Icon** (icon badge / rounded container). It sits left of the label text, usually inside its own rounded container. Box the container (or the glyph if no container is visible), not the text. When the user asks "what are these icons called", annotate one representative Leading Icon rather than every cell's icon.

## Tag-vs-tag collision (MANDATORY - labels never interfere with each other)

Tags must never overlap other tags. The collision guard must check each new tag against (a) its own element box, (b) all other element boxes, (c) all already-placed tags. If every side collides, do NOT fall back to a fixed position - instead keep the preferred x and scan vertically (up then down, in half-tag-height steps) for the nearest free y where the tag fits without touching anything. Tags stack; they never stack on top of each other.

Reference implementation: the vertical free-slot scan in `GUI Interface Diagrams/annotate_current.py`.

> **Superseded:** the engine (`annotate.py`) implements this scan natively in its auto-placement — see the plug-and-play contract below.

## Open space = pixel-verified emptiness (HARDENED)

"Open space" is not just "not overlapping an annotated box" - it must be genuinely empty canvas. Before accepting a tag position, sample the SOURCE image under the tag rect: if any sampled pixel is brighter than the dark background (real UI content), the spot is NOT open, even if no annotation box covers it. A tag sitting on top of an un-annotated element (e.g. a section header, a row label) violates the open-space rule just as much as covering an annotated one.

## Leader lines for distant tags

When the nearest open space forces a tag away from its element (no edge adjacency - the gap between tag rect and element rect exceeds ~one tag height), draw a red line (4px) connecting the tag's nearest edge to the element's nearest edge. The line makes the association unambiguous. Tags adjacent to their boxes need no line.

## Section headers are elements too

Section headers (small labels naming a group, e.g. "HELP CENTER") are annotatable elements. Measure their text bounds, pad the box, and give them a tag like any other element. Do not let other tags sit on them - they count as occupied space in the open-space test.

## Placement priority: nearest open space, no artificial distance (MANDATORY)

1. **Never add distance when adjacent space exists.** If there is open space directly adjacent to the element (above, below, or beside it), the tag goes THERE - not pushed away to a distant free region. Distance is only for when no adjacent space fits.
2. **`top`/`bottom` tags are centered** horizontally on their element box (clamped to canvas), not left-aligned to the box edge. A centered tag above a wide element reads as belonging to it.
3. **Leader lines must be tasteful elbows, never diagonal shots.** Route horizontally into the clear gutter first, then vertically to the tag. The anchor point on the element must be an edge midpoint that does NOT touch any other annotated box - if the facing edge is blocked, try the other three edges before falling back.
4. **Ambiguity rule:** a leader line must start from the annotated element's own box, positioned so it cannot be mistaken for pointing at a neighboring element.

## Tags touch their boxes (MANDATORY)

When there is space adjacent to an element, the tag sits FLUSH against the element's box edge - zero gap. A tag floating even 14-18px away forces the eye to guess which box it belongs to; a touching tag is unambiguous. The default margin between a tag and its element box is 0. Distance (plus a leader line) is ONLY for when no adjacent space exists.

Every "it should be a little lower / closer" complaint about tag placement is this rule being violated. Default to touching; only separate when forced.

## Touching is not overlapping (implementation rule)

The collision test must use inclusive bounds (`<=` / `>=`) so that a tag sharing an edge with a box counts as TOUCHING, not OVERLAPPING. With strict `<` comparisons, a flush tag at exactly the box edge fails the overlap test and gets pushed away - making the "tags touch their boxes" rule impossible to satisfy no matter what the prose says. If tags persistently render with a mysterious gap despite margin=0, check the comparison operators first.

## Draw order matters for contested space

Tags are placed greedily in list order; a tag drawn early can steal the open space another tag needs (e.g. a Badge tag centered above the Tab Bar steals the space the Tab Bar tag needs). When two elements compete for the same adjacent space, assign the side with more alternatives the farther/alternative side, or reorder placement so the bigger/anchored element claims its natural spot first.

## Unambiguous ownership (THE invariant all placement rules serve)

Every other placement rule exists to guarantee one thing: **you must never have to ask which element a label belongs to.** A tag violates this invariant if ANY of the following is true:

1. **It touches two boxes** (e.g. a tag squeezed between the Status Bar box above and the App Bar box below). Touching two elements makes ownership ambiguous even though the "touch your box" rule is technically satisfied. Fix: place the tag on the side of its element that faces EMPTY canvas (e.g. above the Status Bar box, not below it).
2. **It sits edge-to-edge with another tag** - two pills at the same height read as one connected label row. Leave visible separation OR different heights between neighboring tags.
3. **It floats with a gap** when adjacent open space exists - distance implies the tag belongs to something else farther away.

When choosing a side, prefer the side whose adjacent space is bounded by empty canvas on the tag's far side - not a side that puts the tag sandwiched between its element and another element/tag.
