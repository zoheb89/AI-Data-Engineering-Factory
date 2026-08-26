# EliteInteliA Intelligence Factory 0.2.1 — Next.js + Python

This build separates the enterprise product UI from the existing Python AI/data-engineering engine.

## Architecture

Next.js / React UI -> HTTP API adapter -> existing `c_invent` Python services -> ProjectStore/SQLite -> Databricks/LLM adapters.

The Python business logic was copied from the supplied 0.1.29 source package. It is not replaced by a new backend.

## Run

### Python backend

```bash
cd python_backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn api_server:app --host 0.0.0.0 --port 8000
```

Windows:
```powershell
cd python_backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn api_server:app --host 0.0.0.0 --port 8000
```

### Next.js frontend

```bash
npm install
cp .env.example .env.local
npm run dev
```

Open http://localhost:3000.

## Real lifecycle

1. Intake Center uploads an RFI/RFP/notes file or pasted content.
2. `/api/intake` creates/reuses an engagement and stores extracted evidence.
3. The returned engagement ID is saved in browser local storage.
4. Workspace pages call the existing Python `Orchestrator`.
5. Outputs/runs/artifacts remain in the existing ProjectStore.
6. Configure Databricks/LLM environment variables only when those capabilities are needed.

## API endpoints

- `GET /api/health`
- `GET /api/projects`
- `POST /api/projects`
- `GET /api/projects/{id}`
- `POST /api/intake`
- `POST /api/projects/{id}/stage/{stage}`
- `POST /api/projects/{id}/platform`
- `GET /api/projects/{id}/runs/{agent}`

## Important

The UI does not fabricate customer evidence. Intake analysis labels domain, source, use-case and platform detections as signals. Discovery and downstream gates remain responsible for validation.

This build is an integration foundation, not a production security boundary. Before enterprise deployment add authentication/SSO, authorization, secret management, audit hardening, file malware scanning, rate limits and customer-isolated storage.
