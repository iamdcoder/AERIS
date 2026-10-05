# AERIS — Submission Release Notes

This archive is the cleaned submission release for the AERIS hackathon build.

## What was hardened

- Fixed and regression-tested the deterministic backend/engine path.
- Preserved the agentic investigation, critic, human approval, verification, and reassessment lifecycle.
- Added a real `/ws/airspace` realtime snapshot endpoint with `ping`, `snapshot`, and bounded `advance` messages.
- Corrected backend product metadata and CORS configuration.
- Removed unused Deck.gl dependencies from the frontend.
- Pinned frontend dependencies to the lockfile-tested versions instead of `latest`.
- Added an explicit offline presentation fallback so the command center does not become unusable when the backend is unavailable during judging.
- Added a single release-check command for Python compilation, automated tests, and flagship agent proof.
- Aligned the offline flagship metrics with the deterministic engine's current ALT-A / ALT-D comparison, including the 4/5 stress-survival result for ALT-D.

## Verified release checks

- Python compile check: PASS
- Full automated suite: 394 passed, 5 skipped
- Agentic flagship proof: PASS
- Local leader: ALT-A
- Network-aware recommendation: ALT-D
- Critic challenge: ALT-A challenged
- Human approval gate: enforced
- Post-approval verification: VERIFIED
- Rejection/reassessment: ALT-D → ALT-A → HUMAN_APPROVAL
- Frontend JSX/JS parser check: PASS
- `npm ci --dry-run`: PASS

## Final frontend check on the demo machine

Because the final archive intentionally excludes platform-specific `node_modules`, perform a clean frontend install before judging:

```powershell
cd frontend
npm ci
npm run build
npm run dev
```

The source is syntax-checked and the dependency lockfile is consistent. A full Vite build could not be executed in the Linux review environment because the required platform-native npm package was not cached there; a clean Windows install is the correct final verification.
