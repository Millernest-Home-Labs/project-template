---
name: gui-interface-diagramming
description: Use for creating, reviewing, or discussing UI/UX terminology, interface element naming, screen annotations, or spec language for GUI designs. Applies when describing screens, writing design specs, labeling screenshots, or translating visual UI into standard element and style vocabulary (list cells, tab bars, badges, disclosure indicators, design tokens, etc.).
---

# GUI Interface Diagramming & Terminology

Purpose: provide a shared, precise vocabulary for naming UI elements and describing how they are styled, so specs and reviews are unambiguous.

## Core Principles

- **Two-axis naming.** Every element gets (1) an **element name** (what it *is*) and (2) a **style term** (how it *looks*). Example: a "List Cell" styled as an "inset grouped cell."
- **Generic over app-specific.** Definitions must be all-purpose, not tied to one app. App specifics go in examples, never in the definition.
- **Discourse-community terms.** Use the vocabulary designers/developers actually use (iOS HIG + Material Design + web/HTML terms). Prefer the most widely recognized term.
- **Element vs. state.** Distinguish the element (Tab Item) from its state (Active/Selected State). Never conflate them.
- **Affordances are named.** Visual cues that signal behavior (chevron = navigates) must be called out by name.

## Standard Vocabulary

| Element Name | Style Term | Definition |
|---|---|---|
| Status Bar | System chrome | OS strip showing time/battery/signal — device, not app. |
| App Bar / Header | Large title style | Top area holding the screen title and optional actions. |
| List Item / Menu Item | Action row | A tappable row that performs an action or navigates. |
| List Cell | Inset grouped cell | One row within a grouped list (icon + label + optional chevron). |
| Leading Icon | Icon badge (rounded container) | Icon at the start (left) of a row identifying it. |
| Trailing Element | Trailing slot | Anything at the end of a row: chevron, badge, toggle, value. |
| Section Header | Eyebrow heading (small caps) | Small label naming a group of items. |
| Grouped List | Inset grouped list | Related rows bundled in one rounded container. |
| Disclosure Indicator | Trailing affordance | `>` chevron signaling navigation to another screen. |
| Divider / Separator | Inset divider | Thin line separating rows; "inset" = doesn't span full width. |
| Tab Bar / Bottom Navigation | Floating pill tab bar | Persistent bottom bar for top-level sections. |
| Tab Item | Icon + label pair | One destination in the tab bar. |
| Badge | Count / notification badge | Small overlay (often a number) indicating count or status. |
| Active / Selected State | Highlighted / filled state | Styling showing the currently chosen tab or item. |
| Surface / Card | Elevated surface (rounded fill) | Rounded container elevating content above the background. |
| Design Token | Named style value (`color.accent`) | Named color/radius/spacing value from the design system. |
| Affordance | Visual cue | A cue hinting how an element can be used. |

## Rules for Writing Specs

1. **Spec sentence pattern:** "Each `<element>` should be a simple `<style term>`…" — e.g., "Each Menu Item should be a simple **list cell** styled as part of an **inset grouped list**."
2. **Action vs. navigation rows.** Rows without a chevron perform immediate actions; rows with a disclosure indicator navigate. State which in specs.
3. **Leading vs. trailing.** Left-side elements are "leading"; right-side are "trailing" (LTR layouts).
4. **HTML mapping.** When a web equivalent helps, give it: list cell → `<li>`/`<tr>`, tab bar → `<nav>`, badge → positioned `<span>`, section header → `<h2>`.
5. **No invented jargon.** If a term isn't in the table above and isn't standard HIG/Material vocabulary, define it inline on first use.
6. **Diagram annotations.** When annotating screenshots, label with the element name, and add the style term in parentheses when the styling is notable: "List Cell (inset grouped, dark elevated surface)."

## Output Format

When asked to break down a screenshot or mockup, produce a flashcard-style table with columns: **Term (Element Name) | Style Term | Definition** — generic definitions first, app-specific observations as examples beneath the table.
