# Path query fixtures

Schema `6.0.0` graphs for `grapheinstein path` tests and quickstart.

| File | Purpose | Phrases |
|------|---------|---------|
| `simple_chain.json` | Happy-path directed chain | start: `start-concept`, end: `end-concept` |
| `weighted_routes.json` | Competing routes; preferred mid is `preferred-mid` | start: `A` / `start-a`, end: `B` / `end-b` |
| `disconnected.json` | No directed path | `island-a`, `island-b` |

## Weighted routes policy

- **Discarded short route**: `concept::start-a` → `concept::end-b` via `related_to` / `inferred` / low confidence.
- **Preferred route**: `concept::start-a` → `func:preferred-mid` (`mentions` / `extracted` / high confidence) → `concept::end-b` (`calls` / `extracted` / high confidence).

Expected path node midpoints include `func:preferred-mid`.
