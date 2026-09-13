# Changelog

All notable changes to grapheinstein will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.1] - 2026-09-13

### Added
- Warning when indexing produces an empty graph (only root directory, no files)
- Warning when graph has files but no extracted entities (all parse failures)
- Warning when parse skip ratio exceeds 50% of files
- Timeout warning when 80% of timeout budget is consumed
- Categorized error messages in CLI (Configuration, I/O, Graph validation, etc.)
- Troubleshooting section in README with common failure scenarios
- Integration and unit tests for empty/sparse graph detection
- Better error context in exception messages (includes exception type for unexpected errors)
- `GRAPHEINSTEIN_DEBUG_LOG` environment variable for debugging silent failures
- Explicit stderr flushing to ensure errors are captured even if process is killed
- At-exit handler to flush stderr before process termination

### Changed
- CLI error handling now distinguishes transient errors (I/O) from permanent errors (config, validation)
- Error messages now indicate error category to help with debugging and retry logic
- Timeout check now stores budget for warning calculation
- Error handler has fallback to raw stderr if Rich formatting fails

### Fixed
- Improved visibility of parse failures and empty graph scenarios
- Better error messages for operators running grapheinstein in automated environments (CI, Librarian)
- Stderr flushing race condition that could cause empty stderr in subprocess calls
- Error handling robustness - now has fallback if Rich fails

## [0.2.0] - (Previous release)
- Schema version 6.0.0
- Initial public release with core indexing, explain, path, and query features
