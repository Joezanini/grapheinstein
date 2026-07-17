# Feature Specification: Media Parsers

**Feature Branch**: `005-media-parsers`

**Created**: 2026-07-17

**Status**: Draft

**Input**: User description: "Add media parsers to grapheinstein: Images: OCR → text nodes; Audio/Video: local transcription → chunked nodes; Edges from media to related code/docs via filename similarity or content; Add flags --transcribe-media (warn on long files)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Index Images via OCR Text (Priority: P1)

A developer indexes a local project that includes image assets (screenshots, diagrams, UI captures). With media transcription enabled, the tool extracts readable text from images entirely offline and adds text/content nodes tied to each image file. Existing file/directory inventory and prior code/docs/PDF enrichment remain intact. OCR-derived content is recorded as directly extracted from the image.

**Why this priority**: Image OCR closes a constitution modality gap and turns screenshots/diagrams into searchable graph content for install and ops questions.

**Independent Test**: Index a fixture with an image containing clear text; with `--transcribe-media`, confirm text/content nodes linked to the image file with provenance `extracted`. Without the flag, no OCR enrichment.

**Acceptance Scenarios**:

1. **Given** a project with an image that contains readable text, **When** the user runs index with `--transcribe-media`, **Then** the graph includes one or more text/content nodes derived from OCR, related to the image file node.
2. **Given** the same project, **When** the user runs index without `--transcribe-media`, **Then** the graph does not gain OCR text/content nodes from images (file inventory behavior unchanged).
3. **Given** an image with no detectable text, **When** indexing with `--transcribe-media` completes, **Then** the index succeeds without inventing fake text nodes; the image file node remains.
4. **Given** ignore rules that exclude an image, **When** indexing with `--transcribe-media`, **Then** that image does not contribute OCR nodes.

---

### User Story 2 - Transcribe Audio and Video into Chunked Nodes (Priority: P1)

A developer indexes a project that includes audio and/or video files (e.g., recorded demos, walkthroughs). With `--transcribe-media`, the tool runs local transcription offline, splits the transcript into time- or length-based chunks, and adds chunk nodes related to the media file. Failed or unsupported media files are recorded without aborting the entire index when other files succeed.

**Why this priority**: Local A/V transcription is the other half of the media modality and makes spoken walkthroughs queryable alongside code and docs.

**Independent Test**: Index a fixture with a short audio or video file containing spoken words; confirm chunked transcript nodes and relationships to the media file with `extracted` provenance; confirm a corrupt file does not fail the whole index.

**Acceptance Scenarios**:

1. **Given** a project with an audio or video file that yields a usable local transcript, **When** the user runs index with `--transcribe-media`, **Then** the graph includes chunk nodes for the transcript (not a single undifferentiated blob when the transcript is long enough to chunk) related to the media file.
2. **Given** a media file whose transcription completes offline without network access, **When** indexing with `--transcribe-media` finishes, **Then** chunk content is derived from that local transcription (not from a remote service).
3. **Given** a media file that cannot be opened or yields no usable transcript, **When** indexing with `--transcribe-media` runs, **Then** the tool records the failure for that file, continues indexing other files, and still writes a valid graph for successful inputs.
4. **Given** ignore rules that exclude a media file, **When** indexing with `--transcribe-media`, **Then** that file does not contribute transcript chunks.

---

### User Story 3 - Link Media to Related Code and Docs (Priority: P2)

After media text (OCR or transcript chunks) is in the graph, the tool creates relationships from media assets (and/or their text/chunk nodes) to related code or documentation entities when filename similarity or content overlap supports a link. These heuristic links are labeled as inferred so agents can filter them separately from parser-extracted structure.

**Why this priority**: Connecting media to code/docs is the agent-facing value of media ingestion; it depends on Stories 1–2 producing text first.

**Independent Test**: Index a fixture where an image or audio file shares a clear basename with a code or doc file (and/or overlapping distinctive content); confirm inferred edges to those targets; confirm ambiguous matches are skipped.

**Acceptance Scenarios**:

1. **Given** a media file whose basename clearly matches an indexed code or documentation file (unambiguous), **When** indexing with `--transcribe-media` completes, **Then** the graph includes a typed relationship from the media (or its content/chunk node) to that target with provenance `inferred`.
2. **Given** media-derived text that substantially overlaps distinctive content in an indexed doc or code entity, **When** linking runs, **Then** the graph may include an inferred content-based relationship to that target.
3. **Given** ambiguous filename or content matches (multiple equally plausible targets), **When** linking runs, **Then** the tool does not invent a single guessed target; it skips or only links when resolution is unambiguous.
4. **Given** index without `--transcribe-media`, **When** indexing completes, **Then** no new media-to-code/docs inferred edges from this feature appear.

---

### User Story 4 - Opt In with --transcribe-media and Warn on Long Files (Priority: P1)

A developer (or agent) enables all media parsing (image OCR and A/V transcription) via `grapheinstein index --transcribe-media`. Without the flag, prior index behavior is unchanged regarding media enrichment. When a media file exceeds a documented “long file” threshold (duration and/or size), the tool emits a clear warning on the human-readable progress/error stream before or while processing, so users know indexing may take a long time.

**Why this priority**: Explicit opt-in keeps default index fast; long-file warnings prevent surprise multi-hour runs on large videos.

**Independent Test**: Index the same fixture with and without the flag; separately index a fixture with an oversized/long media file and confirm a warning is emitted while the run still completes (or fails only that file if transcription fails).

**Acceptance Scenarios**:

1. **Given** a project with images and A/V files, **When** the user runs index without `--transcribe-media`, **Then** no OCR text nodes, transcript chunks, or media-linking edges from this feature are added.
2. **Given** the same project, **When** the user runs `grapheinstein index --transcribe-media`, **Then** both image OCR and A/V transcription enrichments run (subject to file presence and success).
3. **Given** a media file that exceeds the documented long-file threshold, **When** indexing with `--transcribe-media`, **Then** the tool warns about the long file (including enough identity to identify the path) on the human-readable progress/error stream.
4. **Given** a long media file warning, **When** the user does not cancel the run, **Then** indexing continues (warn-and-continue); the warning alone MUST NOT abort the whole index.

---

### Edge Cases

- Image with no OCR text: file node remains; no text nodes required; index succeeds.
- Empty, silent, or music-only audio/video with no speech: succeed without inventing transcript chunks; optionally record empty transcription.
- Corrupt, unsupported codec, or unreadable media: record per-file failure; continue the index.
- Very large video or long recording: warn when over threshold; process offline; progress remains usable; failure of that file does not abort the run.
- Filename similarity with many near-matches: skip ambiguous links rather than guessing.
- Media files that are also ignored by `.gitignore` / config: excluded from OCR, transcription, and linking.
- Repeated index with flag toggled: later run’s graph reflects flags for that run (default replace output graph for that invocation, consistent with prior increments).
- Optional OCR/transcription tooling not installed or not configured: report a clear error or skip-with-warning for media enrichment without corrupting non-media graph output when possible.

## Requirements *(mandatory)*

<!--
  Grapheinstein constitution constraints in scope for this feature:
  - Local-first / offline-capable defaults; no required cloud APIs
  - CLI subcommands; portable graph.json for agent reuse
  - Typed edges with provenance: extracted | inferred
  - Modalities covered: image (OCR) and audio/video (local transcription); prior code/docs/PDF retained
-->

### Functional Requirements

- **FR-001**: System MUST support offline image OCR when `--transcribe-media` is set, producing text/content nodes related to each successfully processed image file.
- **FR-002**: System MUST support offline audio and video transcription when `--transcribe-media` is set, producing chunked transcript nodes related to each successfully processed media file.
- **FR-003**: Users MUST be able to enable media OCR and transcription via `grapheinstein index --transcribe-media`; without the flag, media OCR, transcription, and media-linking enrichment from this feature MUST NOT run.
- **FR-004**: When a media file exceeds a documented long-file threshold (duration and/or size), the system MUST emit a warning identifying the file on the human-readable progress/error stream; the warning alone MUST NOT abort the entire index (warn-and-continue).
- **FR-005**: System MUST create relationships from media assets and/or their text/chunk nodes to related code or documentation entities based on unambiguous filename similarity and/or content overlap, with provenance `inferred`.
- **FR-006**: OCR- and transcription-derived structure (text/chunk nodes and their containment/attachment to the media file) MUST use provenance `extracted`.
- **FR-007**: System MUST continue to respect `.gitignore` (and configured ignore rules) so ignored media files do not contribute OCR, transcript, or linking edges.
- **FR-008**: System MUST NOT abort the entire index solely because one media file fails OCR or transcription; failures MUST be reported and successful files MUST still contribute to the output graph.
- **FR-009**: Media parsing MUST work offline with local tooling; this increment MUST NOT require cloud APIs or remote speech/OCR services for the default path.
- **FR-010**: Output MUST remain a portable project graph suitable for agent reuse (same documented graph persistence path/format as existing index), including prior file/dir/code/docs/PDF nodes alongside new media enrichment.
- **FR-011**: Transcript chunking MUST split long transcripts into multiple chunk nodes (by time window and/or length); short transcripts MAY result in a single chunk.
- **FR-012**: Ambiguous filename or content matches MUST NOT produce a single guessed link; the system MUST skip or only create inferred edges when the target is unambiguous.

### Key Entities

- **Image / Media File Node**: Existing or retained file node for an image, audio, or video path; media enrichment attaches via edges rather than replacing inventory.
- **OCR Text / Content Node**: Text extracted from an image; attributes include stable id, type, source path, text content, and location metadata when available.
- **Transcript Chunk Node**: A segment of transcribed audio/video; attributes include stable id, type, source path, chunk text, and time range or ordinal position when available.
- **Media Containment Edge**: Relates text/chunk nodes to their containing media file (e.g., `section_of`, `contains`, or equivalent documented type); provenance `extracted`.
- **Media Relation Edge**: Relates media or media-derived text to a code/doc entity via filename similarity or content overlap; provenance `inferred`.
- **Parse Failure Record**: Non-fatal record that a specific media file could not be OCR’d or transcribed, without failing the whole index.
- **Long-File Warning**: Human-readable warning that a media file exceeds the long-file threshold, emitted without aborting the run by itself.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On a fixture with an image containing clear text, `--transcribe-media` produces OCR text/content nodes related to that image with `extracted` provenance in a single offline index run; omitting the flag produces no such nodes.
- **SC-002**: On a fixture with a short spoken audio or video file, `--transcribe-media` produces one or more transcript chunk nodes related to the media file with `extracted` provenance, without network dependency.
- **SC-003**: On a fixture where a media basename uniquely matches a code or doc file, indexing with `--transcribe-media` produces at least one `inferred` relationship from the media (or its content) to that target; ambiguous multi-match fixtures produce no incorrect single-target guess.
- **SC-004**: Indexing a fixture that includes one media file over the long-file threshold emits a warning naming that file and still completes a valid graph write when other inputs succeed.
- **SC-005**: At least 95% of well-formed, text-bearing images and short speech fixtures in the test set yield expected text/chunk nodes when `--transcribe-media` is set; at least one intentionally broken media file does not prevent a successful graph write when other files succeed.
- **SC-006**: A developer or agent can enable media parsing using only the documented `--transcribe-media` flag and obtain an updated portable graph without changing unrelated index behavior (ignore rules, output path, existing modalities).

## Assumptions

- `--transcribe-media` is a single opt-in that enables both image OCR and audio/video transcription (plus subsequent media linking); separate per-modality flags are out of scope for this increment unless later revised.
- Intended local tooling direction: OCR via EasyOCR or Tesseract-backed local OCR; transcription via faster-whisper or whisper.cpp (or equivalent local Whisper path). Exact library choice is a planning decision; the requirement is offline local operation.
- Supported image extensions for OCR follow common raster formats used in projects (e.g., PNG, JPEG, WebP, GIF); exotic formats may be skipped with a per-file warning.
- Supported A/V extensions follow common local formats the chosen transcoder/transcriber can read; unsupported codecs are per-file failures, not whole-index failures.
- Default long-file threshold: warn when media duration exceeds 10 minutes or file size exceeds 100 MB (whichever is detectable); exact values MAY be config-overridable in a later polish pass but MUST be documented for this feature.
- Filename-similarity linking follows the same unambiguous-target preference as existing basename/`references` behavior.
- Content-based linking uses overlap/similarity heuristics sufficient for fixtures; it does not require cloud embedding APIs (local embeddings allowed if already present in the product; otherwise lexical overlap is acceptable for this increment).
- Edge type names for media containment and media-to-code/docs links will be documented in the graph contract during planning; provenance rules above are fixed (`extracted` for OCR/transcript structure, `inferred` for similarity/content links).
- Query commands (`explain`, `path`, `ask`) are unchanged except that the enriched graph must remain consumable by existing visualize/status flows.
- Schema versioning: if new node/edge types require a documented schema bump, that bump is part of delivering this feature’s portable graph contract.
- Optional heavy dependencies for OCR/transcription MAY be optional extras so default installs stay light; when the flag is used without dependencies available, the CLI MUST fail clearly or skip media enrichment with an explicit message rather than silently succeeding as if media were processed.
