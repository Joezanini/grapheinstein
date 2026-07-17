# llm_project fixture

- `src/auth.py`: defines `validate_token`; mentions jwt/PyJWT
- `docs/auth.md`: literal "Auth Middleware" and validation description
- `ignored/secret.md`: gitignored; must not be enriched

Tests inject a fake Ollama chat responder; live Ollama is optional for quickstart.
