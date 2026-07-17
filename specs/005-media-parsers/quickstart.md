# Quickstart Validation: Media Parsers

**Feature**: `005-media-parsers`  
**Date**: 2026-07-17

Use this guide after implementation to prove the feature end-to-end. Contracts: [cli.md](./contracts/cli.md), [graph-json.md](./contracts/graph-json.md). Data model: [data-model.md](./data-model.md).

## Prerequisites

- Python 3.11+
- Repo checkout with this feature implemented
- System **Tesseract OCR** installed and on `PATH`
- **ffmpeg** available for A/V decode (recommended)
- No network required after dependencies and the local Whisper model cache are present

## Setup

```bash
cd /path/to/grapheinstein
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,media]"
```

## Fixture project

Create/use `tests/fixtures/media_project/` (illustrative layout):

```text
media_project/
├── .gitignore                 # e.g. ignored_media/
├── src/
│   └── login.py               # basename/stem target for related_to
├── docs/
│   └── install.md             # content overlap target (optional)
├── assets/
│   ├── login.png              # image with clear OCR text ("Sign in…")
│   └── blank.png              # no text
├── demos/
│   ├── setup.wav              # short spoken clip (< 30s)
│   ├── long_stub.bin          # or oversized file renamed .mp4 for size warn tests
│   └── corrupt.mp3            # invalid bytes
└── ignored_media/
    └── secret.png
```

Document expected OCR text and transcript phrases in fixture README or test constants. Prefer tiny committed fixtures; CI may stub OCR/ASR engines when Tesseract/Whisper are unavailable, but this quickstart assumes real local tooling.

## Scenario A — Flag off (no media enrichment)

```bash
grapheinstein index tests/fixtures/media_project --output /tmp/grapheinstein-v5-default.json
echo $?
```

**Expected**:
- Exit code `0`
- `schema_version` is `"5.0.0"`
- File nodes for images/A/V may exist from inventory
- **No** `media_text` / `transcript_chunk` nodes
- **No** `related_to` edges from this feature
- `graph.transcribe_media` is false/absent

## Scenario B — `--transcribe-media` OCR + transcript

```bash
grapheinstein index tests/fixtures/media_project \
  --transcribe-media \
  --output /tmp/grapheinstein-v5-media.json
```

**Expected**:
- `media_text` node for `assets/login.png` with non-empty OCR text and `section_of` → file (`extracted`)
- `blank.png` produces no `media_text`
- At least one `transcript_chunk` for `demos/setup.wav` with `start_sec`/`end_sec` and `section_of` → file (`extracted`)
- Ignored `secret.png` contributes no OCR nodes
- Corrupt media increments skips / warnings but exit `0` if other work succeeds
- `graph.transcribe_media` is `true`

## Scenario C — Inferred `related_to`

Using the Scenario B output (or a fixture where `login.png` uniquely pairs with `login.py`):

```bash
python - <<'PY'
import json
g=json.load(open("/tmp/grapheinstein-v5-media.json"))
rels=[l for l in g["links"] if l.get("type")=="related_to"]
print(len(rels), rels[:3])
assert all(l.get("provenance")=="inferred" for l in rels)
PY
```

**Expected**:
- At least one `related_to` edge from the media file (or its text) to `src/login.py` (or other unique target)
- Ambiguous multi-match fixtures (if added) produce no incorrect single-target guess
- All `related_to` edges have `provenance: "inferred"`

## Scenario D — Long-file warning

```bash
# Ensure fixture includes a >100MB media-named file or a long-duration clip
grapheinstein index tests/fixtures/media_project \
  --transcribe-media \
  --output /tmp/grapheinstein-v5-long.json \
  2> /tmp/grapheinstein-v5-long.err
grep -i long /tmp/grapheinstein-v5-long.err || grep -i "100" /tmp/grapheinstein-v5-long.err
echo $?
```

**Expected**:
- Warning on stderr naming the oversized/long path
- Exit code `0` when other files succeed (warning alone does not fail the run)

## Scenario E — Missing `[media]` extras

```bash
# In an environment with only base install (no media extras):
pip install -e ".[dev]"   # without media
grapheinstein index tests/fixtures/media_project --transcribe-media -o /tmp/should-not-matter.json
echo $?
```

**Expected**:
- Non-zero exit
- Clear message mentioning `grapheinstein[media]` (or equivalent install hint)
- No success graph claiming media transcription completed

## Scenario F — visualize / status on schema 5

```bash
grapheinstein visualize --input /tmp/grapheinstein-v5-media.json
grapheinstein status --output /tmp/grapheinstein-v5-media.json
```

**Expected**:
- Summaries include `media_text` / `transcript_chunk` / `related_to` counts
- Loading a schema `4.0.0` artifact fails with unsupported-schema / re-index guidance

## Notes for CI

- Unit tests SHOULD inject fake OCR/ASR backends so CI does not require GPU or large model downloads.
- Integration/quickstart scenarios above are the human/agent validation path on a workstation with Tesseract + ffmpeg + Whisper model cache.
