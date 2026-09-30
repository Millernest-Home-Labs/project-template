# Plans

Persistent handoff memory for multi-session work. Each plan folder holds an overview plus one self-contained task file per handoff. An agent picking up a task must be able to execute it from the task file alone, plus the files it links to.

## Conventions

- One folder per initiative: `plans/<initiative>/00-overview.md` and `NN-<task>.md`.
- Every task file has: Status, Owner repo, Depends on, Goal, Context, Constraints, Steps, Acceptance criteria, Evidence to report, Do not.
- Status values: `TODO` | `IN-PROGRESS (<agent/date>)` | `BLOCKED (<reason>)` | `DONE (<date>, <PR/commit>)`.
- Update the task's Status line and the overview's task table when you start, block, or finish a task. Append discoveries to the task's `## Log` section, newest first.
- Never put secret values in plans. Reference secret names and locations only.
- Read `.github/learnings/` before starting. Those record dead ends that must not be retried.

## Initiatives

| Folder | Summary |
|---|---|
| `android-testing/` | Shared, leasable Android emulator in labs-infra that agents can drive via CI; amminox migrated as the first consumer |
| `carte-shopping-integration/` | Carte (amminox) grocery shopping via official Walmart, Kroger and Instacart APIs: ZIP store selection, auto-selected store products with swap search, cart handoff to the retailer's native app |