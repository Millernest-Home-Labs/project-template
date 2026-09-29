---
name: penpot-wireframing
description: Create wireframes and UI designs in self-hosted Penpot via the MCP execute_code pipeline. Use when the user asks to wireframe, mock up, or design mobile/web screens, or to modify existing Penpot boards. ALWAYS end by listing the Penpot URL for every screen created or modified.
---

# Penpot Wireframing

Design screens in the self-hosted Penpot instance (https://penpot.millernest.com)
by driving the MCP `execute_code` tool. No manual drawing required.

## Prerequisites (already set up)

- Penpot AIO on k3s, MCP exposed at `https://penpot.millernest.com/mcp/stream?userToken=<token>`
  (see `w:\labs-infra\penpot\MCP-SETUP.md` for the full stack: pod nginx routes,
  NGINX Proxy Manager WebSocket fix, token generation).
- Helper script `w:\tmp-mcp-call.ps1` performs the MCP handshake
  (initialize -> initialized -> tools/call) and executes JS in the Penpot
  plugin sandbox. If missing, recreate it (see MCP-SETUP.md Layer 5).
- A browser tab must be open on the Penpot file - the plugin runs inside the
  user's browser session. If execute_code fails with "No plugin instance
  connected", open the file URL in the browser first and wait ~10s.

## Workflow

### 1. Write the design code to a temp file

Never pass multi-line JS on the PowerShell command line. Write it to
`w:\tmp-code.txt` (UTF-8), then run:

    powershell -NoProfile -ExecutionPolicy Bypass -Command "`$code = Get-Content w:\tmp-code.txt -Raw; & w:\tmp-mcp-call.ps1 -Code `$code"

### 2. Plugin sandbox API rules (SES - these WILL bite you)

- `import("penpot")` is REJECTED (SES_IMPORT_REJECTED). `penpot` is a global.
- `penpot.createText(str)` takes the string as its argument. Creating empty
  text then setting `.characters` fails validation.
- There is NO `findOneById` / `findShapeById`. Traverse instead:
  - `penpot.root.children` - top-level boards
  - `board.children` - shapes inside a board
  - Find a board: `penpot.root.children.find(c => c.name === "...")`
- `penpot.currentPage` exposes only id/name/background/flows/rulerGuides.
- Shape creation: `penpot.createBoard()`, `createRectangle()`, `createText()`,
  `createEllipse()`, `createPath()`, `createShapeFromSvg()`.
- After `appendChild(child)`, set `child.x`/`child.y` (coordinates are
  relative to the parent board).
- `shape.fills = [{ fillColor: "#RRGGBB", fillOpacity: 1 }]`
- `shape.borderRadius = N` for rounded corners.
- `shape.remove()` deletes a shape.
- Return values must be JSON-serializable; return objects/arrays, not DOM refs.

### 3. Design conventions

- Mobile: 390x844 board. Place new boards at x = 500 * (boardIndex), y = 0
  so multiple screens sit side by side.
- Name boards clearly: "Wireframe - <Screen Name>" or "<App> - <Screen>".
- Name every shape semantically ("Header", "Search Bar", "Card 1 Thumb") -
  names show up in the layers panel and in geometry exports.
- Wireframe style: grays only (#F5F5F5 surfaces, #E0E0E0 placeholders,
  #9E9E9E secondary text, #424242 primary text). High-fidelity style: real
  colors, but keep it simple.
- Standard mobile anatomy: status bar (44px), header (56px), content,
  tab bar (64px) pinned at bottom (y = 780).

### 4. Verify

After creating shapes, query back and confirm:

    const board = penpot.root.children.find(c => c.name === "<Board Name>");
    return { children: board.children.length,
             names: board.children.map(c => c.name) };

Check for duplicates from failed partial runs and `remove()` them.

### 5. ALWAYS finish with screen links

Every wireframe response MUST end with a list of Penpot URLs, one per screen
created or modified. Build each URL as:

    https://penpot.millernest.com/#/workspace?team-id=e9fef758-0743-805d-8008-b24e65a213f6&file-id=a968a163-07a7-8153-8008-b2c59afd6a20&page-id=a968a163-07a7-8153-8008-b2c59afd6a21

(The file-id/page-id above is the current "New File 1"; if a new file is
created, get its ids from the browser URL after opening it.)

Format:

    ## Screens
    1. [Wireframe - Home Screen](<URL>) - 390x844, N shapes
    2. [Wireframe - Detail Screen](<URL>) - 390x844, N shapes

Tell the user to press Shift+1 in the Penpot canvas to zoom-to-fit.

## Multi-screen example

    // Board 1
    const home = penpot.createBoard();
    home.name = "Wireframe - Home";
    home.x = 0; home.y = 0; home.resize(390, 844);
    // ... shapes ...
    // Board 2
    const detail = penpot.createBoard();
    detail.name = "Wireframe - Detail";
    detail.x = 500; detail.y = 0; detail.resize(390, 844);
    // ... shapes ...
    return [{ name: home.name, id: home.id }, { name: detail.name, id: detail.id }];

## Troubleshooting

| Error | Fix |
|---|---|
| "No plugin instance connected for user token" | Open the Penpot file in a browser tab, wait ~10s, retry. |
| "No userToken found in session context" | Use the public URL with `?userToken=`, not the port-forwarded 4401 endpoint. |

## Browser login

- Penpot login: `ethan.romans5.8@gmail.com`.
- **Password: the VALUE of the Windows environment variable `LITELLM_API_KEY` — NOT the literal
  string "LITELLM_API_KEY".** Read it with
  `[Environment]::GetEnvironmentVariable('LITELLM_API_KEY','User')` (falls back to Machine, then
  `$env:LITELLM_API_KEY`). Stage it via `Set-Clipboard` and paste into the browser (Ctrl+V) — never
  type the variable name as the password.
- Login may take ~15s to redirect after submit; the file workspace loads automatically.
| SES_IMPORT_REJECTED | Remove `await import("penpot")` - `penpot` is already global. |
| "Value not valid ... createText" | Pass the string to `createText(str)`; do not set `.characters` on empty text. |
| "findOneById is not a function" | Use `penpot.root.children.find(...)` traversal. |
| Duplicate shapes | A previous run partially succeeded; query children and `remove()` strays. |
