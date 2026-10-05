# AERIS Release Checklist

## Before submission

### Backend / agent

```powershell
$env:PYTHONPATH = "backend;."
py scripts\run_release_check.py
```

The release check covers Python compilation, the complete automated test suite, and the flagship agent proof.

### Frontend

Run from `frontend`:

```powershell
npm ci
npm run build
npm run dev
```

Use a clean install. Do not include `node_modules` in the submission archive.

### Gemini

Set `GEMINI_API_KEY` in the root `.env` and run the flagship flow once. Gemini is used for investigation/orchestration; deterministic tools remain authoritative for operational calculations. When Gemini is unavailable, the backend falls back to deterministic investigation and the frontend can use its explicitly labeled offline presentation path.

### Judging proof

The flagship scenario should show:

1. Local leader `ALT-A`.
2. Network-aware winner `ALT-D`.
3. Critic challenge of `ALT-A`.
4. Explicit human approval gate.
5. Verified post-action state.
6. Rejection followed by reassessment.

The release should never be presented as autonomous aircraft control or an ATC replacement.
