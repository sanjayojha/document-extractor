# doc-extractor-pro

A document extractor. Currently scoped to **invoices**: upload a PDF/image, run it through an extraction pipeline, review/correct the extracted fields. General document-type support is a future direction, not built yet.

## Stack

- **Backend**: Python, FastAPI, SQLAlchemy 2.0 (typed `Mapped`/`mapped_column` style), Alembic migrations, PostgreSQL, `pydantic-settings` for config.
- **Frontend**: React + TypeScript + Vite (no Next.js) + Tailwind CSS, in `frontend/`.
- **Database**: PostgreSQL. Runs locally, managed outside this repo — not containerized as part of this project. Assumes a `docextractor` database (dev) and `docextractor_test` database (tests) already exist with the user/credentials in `backend/.env`.
- **LLM**: OpenAI (text model, structured outputs) for field extraction from PDF text extracted via `pdfplumber`. No OCR/vision model yet — scanned/image-only documents are gated out as low-confidence rather than processed.

## Dev workflow

Backend — always `cd backend` and activate the virtualenv before running anything:
```
cd backend
source .venv/bin/activate

uvicorn app.main:app --reload      # run the API (http://localhost:8000, docs at /docs)
alembic upgrade head               # apply migrations
alembic revision --autogenerate -m "..."   # create a new migration after model changes
pytest                             # run tests (hits a real Postgres test DB, see below)
ruff check .                       # lint
```

Frontend:
```
cd frontend
npm run dev       # http://localhost:5173
```

Both need to run at once for the full app to work locally; backend must have CORS configured for the frontend's dev origin.

## Repository structure

```
backend/
  app/
    main.py                # FastAPI app, middleware, router registration
    core/config.py         # pydantic-settings Settings (reads backend/.env)
    core/constants.py      # plain string status constants (DocumentStatus, ExtractionStatus)
    db/                    # SQLAlchemy engine/session/base
    api/routers/           # one router module per resource
    models/                # SQLAlchemy ORM models
    schemas/api/           # Pydantic request/response schemas
    services/              # business logic, one concern per module
  alembic/                 # migrations
  tests/                   # pytest, mirrors app/ structure (test_api/, test_services/)
frontend/
  src/
    api/                   # fetch-based API client, one module per backend resource
    types/                 # TS types mirroring backend Pydantic schemas
    hooks/                 # react-query hooks
    pages/                 # route-level components
    components/            # reusable UI pieces
```

## Data model (already stable, don't casually redesign)

- `Document`: an uploaded file. Deduplicated by SHA-256 hash. `status` tracks its lifecycle: `pending` → `processing` → `completed` / `needs_review` / `failed` / `low_confidence`.
- `Extraction`: one attempt at extracting a document (`attempt_number` per document, supports retries). Stores the model used, schema version, raw LLM response (JSONB), and its own status.
- `ExtractionField`: one row per extracted field per attempt. Stores the extracted `field_value` (JSONB), a heuristic `confidence_score`, `is_flagged`, and correction fields (`was_corrected`, `corrected_value`, `corrected_at`) for the human-review workflow.

## Conventions

- Services under `app/services/` are small, mostly-pure functions/dataclasses — one custom exception type per concern (e.g. `UploadValidationError`, `TextExtractionError`), not generic exceptions.
- Status values are plain strings (`String(20)` columns), defined once as string-constant classes in `app/core/constants.py` — not database enums.
- Routers stay thin: validation and orchestration live in `services/`, routers wire HTTP <-> services <-> DB.
- Tests run against a **real local Postgres test database** (`docextractor_test`), not mocks or SQLite — each test runs inside a transaction that's rolled back afterward (see `tests/conftest.py`). Follow this pattern for new tests rather than introducing a different DB testing strategy.
- Don't add authentication, a job queue, or containerize the backend/frontend unless explicitly asked — this is a single-user local MVP for now.

## System dependencies

- `python-magic` requires the system `libmagic` library to be installed (not pip-installable alone).
- `pdfplumber` has no extra system dependencies beyond its pip package.
