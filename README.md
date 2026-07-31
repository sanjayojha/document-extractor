# Document Extractor Pro

Extract structured information from documents and store it in a database. Currently focused on invoices.

## Setup

Prerequisites: a local PostgreSQL instance with a `docextractor` database and `docextractor_test` database (used by the test suite), owned by a `docextractor_user` matching `backend/.env`.

### Backend

```
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in DATABASE_URL / OPENAI_API_KEY
alembic upgrade head
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

Run tests: `pytest` (from `backend/`, with `.venv` activated).

### Frontend

```
cd frontend
npm install
npm run dev
```

App: http://localhost:5173

See [CLAUDE.md](CLAUDE.md) for architecture, conventions, and project structure.
