# AERIS Troubleshooting

## 1. Backend import error

Use the repository root and set `PYTHONPATH=backend`:

```powershell
$env:PYTHONPATH="backend"
uvicorn app.api.app:app --reload
```

For the flagship runner:

```powershell
$env:PYTHONPATH="backend"
python scripts/run_flagship.py
```

---

## 2. Python package missing

Activate the virtual environment and reinstall:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## 3. Gemini configuration error

If you see:

```text
GEMINI_API_KEY is not configured
```

set the key in `.env` or the process environment.

The deterministic flagship runner does not require Gemini.

---

## 4. Gemini execution fails

This is expected to be recoverable in the hybrid path.

AERIS records the failure and falls back to deterministic investigation when possible.

The UI should not claim that the Gemini path succeeded if it did not.

---

## 5. Frontend cannot reach backend

Confirm the backend is running:

```text
http://127.0.0.1:8000/health
```

Expected:

```json
{
  "status": "ok",
  "service": "aeris"
}
```

Then check:

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Restart Vite after changing environment variables.

---

## 6. Frontend build fails

From `frontend/`:

```bash
npm install
npm run build
```

If dependencies appear corrupted:

```powershell
Remove-Item -Recurse -Force node_modules
Remove-Item package-lock.json
npm install
npm run build
```

Use this cleanup only when a normal `npm install` does not repair the dependency tree.

---

## 7. Dashboard shows stale decision state

Click:

```text
RERUN AERIS
```

The frontend calls `/copilot/reset`, clears the in-memory run store, and starts a new deterministic scenario from baseline.

A hard browser refresh can also clear local React state, but the backend run state is reset by the explicit AERIS reset flow.

---

## 8. Approval button remains locked

The approval button should only become usable when:

```text
agent state exists
AND
stage = HUMAN_APPROVAL
AND
recommendation exists
AND
approval = PENDING
```

This is intentional.

---

## 9. Verification is pending

Before approval, this is correct:

```text
EXECUTION  LOCKED
MODE       AWAITING_APPROVAL
VERIFY     PENDING
```

Verification should only become an active post-action concern after an approved execution.

---

## 10. Rejection creates a new recommendation

This is expected behavior.

The old candidate should become historically rejected, while the new recommendation should return to:

```text
HUMAN APPROVAL
EXECUTION LOCKED
VERIFICATION PENDING
```

If a new recommendation is shown as already `EXECUTED` or `VERIFIED`, that is a state-isolation bug and should be treated as a regression.

---

## 11. Full regression

From the repository root:

```bash
python -m pytest backend/tests -q
python -m pytest copilot/tests -q
```

Then:

```bash
cd frontend
npm run build
```

Finally:

```bash
cd ..
PYTHONPATH=backend python scripts/run_flagship.py
```
