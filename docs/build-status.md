# AERIS Build Status

## Release candidate

This release is structured as a deterministic-first, human-supervised decision system.

### Verified in the release workspace

- Python test suite: 393 passed, 5 skipped at release preparation time.
- Backend suite: 272 passed.
- Agent/coplanar tests are included in the repository suite.
- Agentic flagship proof: local leader ALT-A -> network-aware recommendation ALT-D.
- Critic challenge: ALT-A challenged.
- Approval guard: execution requires explicit approval.
- Verification path: VERIFIED after approval.
- Rejection path: recommendation is reassessed and returns to HUMAN_APPROVAL.
- Frontend source syntax: all JSX/JS files parse successfully with the TypeScript parser.
- Frontend dependencies are pinned to the release-tested versions.
- `node_modules` is intentionally excluded from the release archive.

### Important release note

The package should be installed fresh on the demo machine with `npm ci`. Do not copy a platform-specific `node_modules` directory into the submission.

The live Gemini path should be smoke-tested once with the actual `GEMINI_API_KEY` before the judging session. When Gemini is unavailable, AERIS falls back to its deterministic investigation path and the frontend has an explicit offline presentation fallback.
