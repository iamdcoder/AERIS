# Submission Preflight

Run the final repository gate from the project root:

```bash
python scripts/preflight_submission.py
```

The preflight verifies:

- Python environment and `compileall`;
- backend + copilot regression tests;
- deterministic flagship proof;
- agentic flagship proof, including approval, verification, rejection and fail-closed reassessment;
- T+35 operational replay;
- FastAPI health, `/operations/live`, and `/ws/operations`;
- dependency-free frontend timeline/recommendation regression tests;
- Vite production build when frontend dependencies are available;
- documentation consistency;
- submission hygiene and obvious credential leakage.

The preflight does not treat a missing npm registry/dependency installation as a source-code pass. It reports that condition as `BLOCKED BY ENVIRONMENT`.

The final target state is:

```text
AERIS SUBMISSION STATUS: JUDGE READY
```

Before handing the project to judges, also run the frontend build on a network-enabled machine:

```bash
cd frontend
npm ci
npm test
npm run build
```
