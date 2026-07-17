# Explain fixtures

- `auth_neighborhood.json` — schema `6.0.0` graph with `concept::auth` linked through `auth.py::check_auth` → `auth.py` → `middleware/helpers.py` (distinct 1-hop and 2-hop neighborhoods). Also includes `concept::authentication` for multi-match / approximate phrases and an `unrelated.py` noise node.
