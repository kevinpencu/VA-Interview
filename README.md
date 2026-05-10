# VA Interview Test

Web-based hiring test for VA candidates. See `docs/superpowers/specs/2026-05-10-va-interview-test-design.md` for the design.

## Local development

1. Copy `.env.example` to `.env` and fill in Supabase credentials.
2. Apply schema: paste `backend/migrations.sql` into the Supabase SQL editor and run.
3. Backend: `cd backend && pip install -r requirements.txt && uvicorn main:app --reload --port 8000`
4. Frontend: `cd frontend && npm install && npm run dev` (port 5173)
5. Seed test content: `cd backend && python seed.py` (after putting files in `content/`)
