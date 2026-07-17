# CLI Contract: grapheinstein (media parsers)

**Feature**: `005-media-parsers`  
**CLI contract version**: 5.0.0 (paired with graph schema_version `5.0.0`)

## Entrypoint

- Console script: `grapheinstein`
- Module: `python -m grapheinstein`

## Global / shared options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--config` | path | unset | YAML config path; overrides user config for this run |
| `--help` | flag | — | Show help |

Config precedence: CLI flags > `--config` file > `~/.grapheinstein/config.yaml` > built-ins.

User config path: `~/.grapheinstein/config.yaml`

Supported keys (retained; media flag is CLI-primary for v1):

| Key | Type | Description |
|-----|------|-------------|
| `output` | string | Default graph output path |
| `log_level` | string | Logging level |
| `languages` | list of strings | Enabled code structure-extraction languages |

Canonical language ids unchanged: `python`, `javascript`, `typescript`, `java`, `go`, `rust`, `cpp`, `sql`.

## Commands

### Default (no subcommand)

```text
grapheinstein PROJECT_PATH [--output PATH] [--languages LIST] [--include-docs] [--include-pdfs] [--transcribe-media] [--config PATH]
```

**Behavior**: Same as `grapheinstein index PROJECT_PATH ...`  
**Success exit**: `0`

### `index`

```text
grapheinstein index PROJECT_PATH [--output PATH] [--languages LIST] [--include-docs] [--include-pdfs] [--transcribe-media] [--config PATH]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `PROJECT_PATH` | path | required | Project folder to index |
| `--output` / `-o` | path | config or `graph.json` | Destination graph artifact |
| `--languages` | string | unset | Comma-separated language ids; when set, replaces config/default for this run |
| `--include-docs` | flag | off | Enable Markdown / TXT / RST heading + link structure enrichment |
| `--include-pdfs` | flag | off | Enable PDF text extraction and section chunk enrichment |
| `--transcribe-media` | flag | off | Enable image OCR + A/V transcription + media linking |

**Behavior**:
1. Validate `PROJECT_PATH` and resolve config (including languages)
2. If any language id is unknown → exit non-zero; do not write a success graph
3. If `--transcribe-media` and required Python media extras are not importable → exit non-zero with install hint (`pip install 'grapheinstein[media]'`); do not write a success graph that claims media ran
4. Discover files/dirs respecting `.gitignore`; do not follow symlinks
5. Build inventory: `contains` + basename `references` (`extracted`)
6. Code structure extract for enabled languages; per-file failures warn and continue
7. If `--include-docs` / `--include-pdfs`: prior docs/PDF enrichment (schema 4 behavior retained)
8. If `--transcribe-media`:
   - For non-ignored image extensions: OCR → `media_text` + `section_of` (`extracted`)
   - For non-ignored audio/video extensions: local transcription → `transcript_chunk` + `section_of` (`extracted`)
   - Warn on long files (size > 100 MB or duration > 600 s when known); continue
   - Build unambiguous `related_to` edges (`inferred`) from filename similarity and/or content overlap
   - Per-file OCR/ASR failures warn and continue (`parse_skips`)
9. Without `--transcribe-media`, skip OCR, transcription, and media linking (file nodes may still exist from inventory)
10. Write graph artifact per [graph-json.md](./graph-json.md) schema `5.0.0` (overwrite if exists)
11. Print success summary including prior counts plus `media_text`, `transcript_chunk`, and `related_to` counts

**Exit codes**:

| Code | Meaning |
|------|---------|
| 0 | Success (including when some files skipped for structure/media) |
| 1 | Usage / validation / I/O / config / unknown language / missing `[media]` extras when flag set |

### `visualize` (retained, extended summary)

```text
grapheinstein visualize --input PATH [--dot PATH] [--config PATH]
```

**Behavior**: Load schema `5.0.0` only. Console summary MUST include counts for prior node/edge types plus `media_text`, `transcript_chunk`, and `related_to` (zero when absent), plus a brief sample. Optional `--dot` still writes DOT and keeps the summary.

**Exit codes**: `0` success; `1` missing/unreadable input, unsupported/malformed graph (including schema `4.0.0`), unwritable DOT, config error.

### `status` (retained)

```text
grapheinstein status [--output PATH] [--config PATH]
```

**Behavior**: Stats from schema `5.0.0` graphs only (include media totals when present). Old schemas → unsupported-format error. Missing graph → clear “no index” failure (existing exit convention).

## Output streams

| Stream | Content |
|--------|---------|
| Human console (stderr via Rich/console) | Progress, summaries, long-file warnings, skipped parses, errors |
| `--output` file | Graph JSON only |

## Long-file warning contract

When `--transcribe-media` processes a media file that exceeds the threshold:

- Emit a warning that includes the project-relative path
- MUST NOT treat the warning alone as a fatal error
- Thresholds: **100 MB** file size **or** **600 seconds** duration when duration is obtainable

## Non-goals (this contract version)

- Separate `--ocr-images` / `--transcribe-av` flags
- Cloud OCR/ASR
- Query command (`explain` / `path` / `ask`) behavior changes beyond loading schema 5
- Guaranteeing Whisper/Tesseract accuracy metrics beyond fixture smoke tests
