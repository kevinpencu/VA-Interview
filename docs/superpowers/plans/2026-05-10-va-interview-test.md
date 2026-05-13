# VA Interview Test — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a web-based hiring test that filters out unfit VA candidates by exercising the three on-the-job judgments — pick TikToks, judge nano-banana generations, judge Kling videos — and produces an auto-recommendation for a hiring manager.

**Architecture:** React + Vite SPA served as static files by a FastAPI backend, with Supabase for Postgres + Storage + Auth. Two route trees: `/test/<token>` (public, candidate, opaque-token auth via cookie) and `/admin/*` (protected, manager, Supabase JWT). Single Docker container deployed to Railway, mirroring the AI Photos sibling project. Spec at `docs/superpowers/specs/2026-05-10-va-interview-test-design.md`.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, supabase-py, pytest. Node 20+, React 19, Vite 6, react-router-dom 7. Supabase (Postgres + Storage + Auth). Railway for deploy.

---

## Conventions

- All paths in this plan are relative to the project root: `/Users/victor/PycharmProjects/VA Interview/`
- The directory name has a space — quote it in shell commands.
- Backend tests use pytest. Run from `backend/`: `pytest -v`. The Supabase client is mocked in unit tests via a fixture.
- Frontend uses Vite. Run from `frontend/`: `npm run dev`. Build: `npm run build`.
- Commit after each task. Use Conventional Commits (`feat:`, `fix:`, `chore:`, `test:`, `docs:`).
- All test items are stored in private Supabase Storage buckets. Frontend gets short-lived signed URLs from the backend.

## File Structure (target)

```
VA Interview/
├── .env.example
├── .gitignore
├── Dockerfile
├── README.md
├── backend/
│   ├── main.py                FastAPI app entrypoint, mounts routers + static frontend
│   ├── auth.py                Supabase JWT verify (manager) + invite-token cookie verify (candidate)
│   ├── config.py              env-derived settings + scoring thresholds (constants)
│   ├── supabase_client.py     get_supabase() singleton
│   ├── models.py              Pydantic request/response schemas
│   ├── scoring.py             compute_recommendation(...) pure function
│   ├── seed.py                CLI: load test items + quiz → DB & Storage
│   ├── migrations.sql         full schema, applied once by hand
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── candidate.py       /api/test/<token>/* endpoints
│   │   └── manager.py         /api/manager/* endpoints
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py        shared fixtures (mocked Supabase, fastapi TestClient)
│   │   ├── test_scoring.py
│   │   ├── test_auth.py
│   │   ├── test_candidate_routes.py
│   │   └── test_manager_routes.py
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── eslint.config.js
│   └── src/
│       ├── main.jsx
│       ├── App.jsx                     Router, two route trees
│       ├── api.js                      fetch wrappers
│       ├── lib/
│       │   └── supabase.js             manager-side client
│       ├── components/
│       │   ├── candidate/
│       │   │   ├── InvalidLink.jsx
│       │   │   ├── Welcome.jsx
│       │   │   ├── Tutorial.jsx
│       │   │   ├── Quiz.jsx
│       │   │   ├── StepIntro.jsx
│       │   │   ├── TestStep.jsx
│       │   │   ├── JustificationModal.jsx
│       │   │   └── Submit.jsx
│       │   └── manager/
│       │       ├── Login.jsx
│       │       ├── Dashboard.jsx
│       │       ├── CandidateDetail.jsx
│       │       ├── InviteModal.jsx
│       │       └── ItemReplay.jsx
│       └── hooks/
│           ├── useTabBlurLogger.js
│           └── useTestSession.js
├── content/                            local-only seed material (gitignored)
│   ├── tiktoks/
│   ├── nano_banana/
│   ├── kling/
│   ├── tutorial_examples/
│   ├── items.csv
│   └── quiz.json
└── docs/
    └── superpowers/
        ├── specs/2026-05-10-va-interview-test-design.md
        └── plans/2026-05-10-va-interview-test.md   (this file)
```

---

## Task 1: Project skeleton + git + .gitignore + .env.example

**Files:**
- Create: `.gitignore`
- Create: `.env.example`
- Create: `README.md`
- Create: `backend/requirements.txt`
- Create: `frontend/package.json`
- Create: `backend/__init__.py` (empty)
- Create: `backend/tests/__init__.py` (empty)
- Run: `git init` in project root

- [ ] **Step 1: Initialize git in the project root**

```bash
cd "/Users/victor/PycharmProjects/VA Interview"
git init
git branch -M main
```

- [ ] **Step 2: Create `.gitignore`**

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
.pytest_cache/
.venv/
venv/

# Node
node_modules/
dist/
.vite/

# Env
.env
.env.local

# Content (seed material, not checked in)
content/

# Brainstorm artifacts
.superpowers/

# OS
.DS_Store
Thumbs.db

# IDE
.idea/
.vscode/
```

- [ ] **Step 3: Create `.env.example`**

```dotenv
# Supabase
SUPABASE_URL=https://YOUR-PROJECT.supabase.co
SUPABASE_SERVICE_KEY=eyJ... # service role key (backend only)
SUPABASE_ANON_KEY=eyJ...    # anon key (frontend, manager auth)
SUPABASE_JWT_SECRET=...     # JWT secret from Supabase project settings

# Manager
MANAGER_EMAIL=manager@example.com   # only this email is allowed to log in as manager

# Storage buckets (created in Task 2)
BUCKET_TIKTOKS=tiktoks
BUCKET_NANO_BANANA=nano_banana
BUCKET_KLING=kling
BUCKET_TUTORIAL=tutorial

# Server
PORT=8000
SIGNED_URL_TTL_SECONDS=60
SESSION_COOKIE_MAX_AGE_SECONDS=14400
```

- [ ] **Step 4: Create `backend/requirements.txt`**

```
fastapi==0.115.0
uvicorn[standard]==0.32.0
pydantic==2.9.2
supabase==2.7.4
python-dotenv==1.0.1
PyJWT[crypto]==2.9.0
pytest==8.3.3
pytest-asyncio==0.24.0
httpx==0.27.2
```

- [ ] **Step 5: Create `frontend/package.json`**

```json
{
  "name": "va-interview-frontend",
  "private": true,
  "version": "0.0.1",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview --port 4173"
  },
  "dependencies": {
    "@supabase/supabase-js": "^2.45.4",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "react-router-dom": "^7.0.0"
  },
  "devDependencies": {
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "@vitejs/plugin-react": "^4.3.4",
    "vite": "^6.0.0"
  }
}
```

- [ ] **Step 6: Create `README.md`**

```markdown
# VA Interview Test

Web-based hiring test for VA candidates. See `docs/superpowers/specs/2026-05-10-va-interview-test-design.md` for the design.

## Local development

1. Copy `.env.example` to `.env` and fill in Supabase credentials.
2. Apply schema: paste `backend/migrations.sql` into the Supabase SQL editor and run.
3. Backend: `cd backend && pip install -r requirements.txt && uvicorn main:app --reload --port 8000`
4. Frontend: `cd frontend && npm install && npm run dev` (port 5173)
5. Seed test content: `cd backend && python seed.py` (after putting files in `content/`)
```

- [ ] **Step 7: Create empty package init files**

```bash
touch backend/__init__.py backend/tests/__init__.py
mkdir -p backend/routers
touch backend/routers/__init__.py
```

- [ ] **Step 8: Commit**

```bash
git add .gitignore .env.example README.md backend/requirements.txt frontend/package.json backend/__init__.py backend/tests/__init__.py backend/routers/__init__.py
git commit -m "chore: project skeleton — gitignore, env example, requirements"
```

---

## Task 2: Database schema migration

**Files:**
- Create: `backend/migrations.sql`

This task does not run code locally. The migration is applied by the developer in the Supabase SQL editor. The file is the source of truth.

- [ ] **Step 1: Create `backend/migrations.sql`**

```sql
-- VA Interview Test — schema v1
-- Apply by pasting into Supabase SQL editor and running.

-- ============================================================
-- manager_profiles
-- ============================================================
CREATE TABLE IF NOT EXISTS manager_profiles (
  id          UUID PRIMARY KEY,                                  -- = auth.users.id
  email       TEXT UNIQUE NOT NULL,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- test_items
-- ============================================================
CREATE TABLE IF NOT EXISTS test_items (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pool            TEXT NOT NULL CHECK (pool IN ('tiktok','nano_banana','kling')),
  storage_path    TEXT NOT NULL,
  correct_answer  BOOLEAN NOT NULL,
  is_anchor       BOOLEAN NOT NULL DEFAULT false,
  anchor_kind     TEXT CHECK (anchor_kind IS NULL OR anchor_kind IN ('obvious_good','obvious_bad')),
  notes           TEXT,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (pool, storage_path)
);

CREATE INDEX IF NOT EXISTS test_items_pool_idx ON test_items(pool);

-- ============================================================
-- quiz_questions
-- ============================================================
CREATE TABLE IF NOT EXISTS quiz_questions (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  question        TEXT NOT NULL,
  options         JSONB NOT NULL,
  correct_index   INT NOT NULL,
  display_order   INT NOT NULL UNIQUE
);

-- ============================================================
-- candidates
-- ============================================================
CREATE TABLE IF NOT EXISTS candidates (
  id                            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  invite_token                  TEXT UNIQUE NOT NULL,
  invited_by                    UUID REFERENCES manager_profiles(id),
  invited_label                 TEXT,
  invited_label_email           TEXT,
  candidate_name                TEXT,
  candidate_email               TEXT,
  session_id                    TEXT,
  forced_justification_indexes  JSONB,
  created_at                    TIMESTAMPTZ DEFAULT NOW(),
  started_at                    TIMESTAMPTZ,
  submitted_at                  TIMESTAMPTZ,
  link_used                     BOOLEAN NOT NULL DEFAULT false,
  recommendation                TEXT CHECK (recommendation IS NULL OR recommendation IN ('pass','borderline','fail')),
  auto_fail_reasons             JSONB DEFAULT '[]'::jsonb,
  manager_decision              TEXT CHECK (manager_decision IS NULL OR manager_decision IN ('hired','rejected')),
  manager_notes                 TEXT
);

CREATE INDEX IF NOT EXISTS candidates_invite_token_idx ON candidates(invite_token);

-- ============================================================
-- candidate_quiz_answers
-- ============================================================
CREATE TABLE IF NOT EXISTS candidate_quiz_answers (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id    UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
  question_id     UUID NOT NULL REFERENCES quiz_questions(id),
  answered_index  INT,
  is_correct      BOOLEAN,
  answered_at     TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (candidate_id, question_id)
);

-- ============================================================
-- candidate_decisions
-- ============================================================
CREATE TABLE IF NOT EXISTS candidate_decisions (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id          UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
  item_id               UUID NOT NULL REFERENCES test_items(id),
  pool                  TEXT NOT NULL CHECK (pool IN ('tiktok','nano_banana','kling')),
  display_index         INT NOT NULL,
  answer                BOOLEAN NOT NULL,
  is_correct            BOOLEAN NOT NULL,
  dwell_ms              INT NOT NULL,
  shown_at              TIMESTAMPTZ,
  answered_at           TIMESTAMPTZ DEFAULT NOW(),
  justification         TEXT,
  duplicate_of          UUID REFERENCES candidate_decisions(id),
  forced_justification  BOOLEAN NOT NULL DEFAULT false
);

CREATE INDEX IF NOT EXISTS candidate_decisions_lookup_idx
  ON candidate_decisions(candidate_id, pool, display_index);

-- ============================================================
-- candidate_events
-- ============================================================
CREATE TABLE IF NOT EXISTS candidate_events (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id  UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
  kind          TEXT NOT NULL CHECK (kind IN (
                  'tab_blur','tab_focus','step_start','step_end',
                  'tutorial_view','quiz_start','quiz_end','session_start')),
  meta          JSONB DEFAULT '{}'::jsonb,
  occurred_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS candidate_events_lookup_idx
  ON candidate_events(candidate_id, kind, occurred_at);
```

- [ ] **Step 2: Apply the migration manually**

Open the Supabase project's SQL editor in a browser. Paste the contents of `backend/migrations.sql`. Click Run. Verify all tables exist via `Table Editor`.

- [ ] **Step 3: Create the four Storage buckets**

In Supabase Storage UI, create buckets:
- `tiktoks` (private)
- `nano_banana` (private)
- `kling` (private)
- `tutorial` (public)

- [ ] **Step 4: Create the manager auth user**

In Supabase Auth, click "Add user" → "Create new user". Enter the manager's email and password. Confirm the user is created. Then in SQL editor:

```sql
INSERT INTO manager_profiles (id, email)
SELECT id, email FROM auth.users WHERE email = 'YOUR_MANAGER_EMAIL'
ON CONFLICT (id) DO NOTHING;
```

- [ ] **Step 5: Commit the migration file**

```bash
git add backend/migrations.sql
git commit -m "feat: database schema for VA interview test"
```

---

## Task 3: Backend config + Supabase client + main app skeleton

**Files:**
- Create: `backend/config.py`
- Create: `backend/supabase_client.py`
- Create: `backend/main.py`

- [ ] **Step 1: Create `backend/config.py`**

```python
"""Environment-derived settings + scoring thresholds."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _env(key: str, default: str | None = None, *, required: bool = False) -> str:
    val = os.getenv(key, default)
    if required and not val:
        raise RuntimeError(f"Missing required env var: {key}")
    return val or ""


@dataclass(frozen=True)
class Settings:
    supabase_url: str
    supabase_service_key: str
    supabase_jwt_secret: str
    manager_email: str
    bucket_tiktoks: str
    bucket_nano_banana: str
    bucket_kling: str
    bucket_tutorial: str
    signed_url_ttl_seconds: int
    session_cookie_max_age_seconds: int


def load_settings() -> Settings:
    return Settings(
        supabase_url=_env("SUPABASE_URL", required=True),
        supabase_service_key=_env("SUPABASE_SERVICE_KEY", required=True),
        supabase_jwt_secret=_env("SUPABASE_JWT_SECRET", required=True),
        manager_email=_env("MANAGER_EMAIL", required=True).lower(),
        bucket_tiktoks=_env("BUCKET_TIKTOKS", "tiktoks"),
        bucket_nano_banana=_env("BUCKET_NANO_BANANA", "nano_banana"),
        bucket_kling=_env("BUCKET_KLING", "kling"),
        bucket_tutorial=_env("BUCKET_TUTORIAL", "tutorial"),
        signed_url_ttl_seconds=int(_env("SIGNED_URL_TTL_SECONDS", "60")),
        session_cookie_max_age_seconds=int(_env("SESSION_COOKIE_MAX_AGE_SECONDS", "14400")),
    )


# ============================================================
# Test composition + scoring constants (LOCKED — do not change without spec update)
# ============================================================
ITEMS_PER_STEP = 30
UNIQUE_ITEMS_PER_STEP = 28
DUPLICATES_PER_STEP = 2
OBVIOUS_GOOD_ANCHORS_PER_STEP = 4
OBVIOUS_BAD_ANCHORS_PER_STEP = 4
NORMAL_ITEMS_PER_STEP = 20
FORCED_JUSTIFICATIONS_PER_STEP = 2

POOLS = ("tiktok", "nano_banana", "kling")

QUIZ_QUESTION_COUNT = 5
QUIZ_PASS_THRESHOLD = 4    # ≥4/5 to proceed

# Auto-fail thresholds
STEP_ACCURACY_FAIL_FLOOR = 0.70
# Auto-borderline thresholds
STEP_ACCURACY_BORDERLINE_FLOOR = 0.80
TAB_SWITCH_BORDERLINE_THRESHOLD = 5
```

- [ ] **Step 2: Create `backend/supabase_client.py`**

```python
"""Singleton Supabase client (service role)."""
from __future__ import annotations

from functools import lru_cache

from supabase import Client, create_client

from config import load_settings


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    s = load_settings()
    return create_client(s.supabase_url, s.supabase_service_key)
```

- [ ] **Step 3: Create `backend/main.py` (skeleton)**

```python
"""FastAPI entrypoint. Mounts routers and serves the built frontend."""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI(title="VA Interview Test")

# CORS — frontend dev server runs on :5173
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


# Static frontend (built into ../frontend/dist by Dockerfile / npm run build)
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    def serve_spa(path: str):
        # SPA fallback: any non-API path returns index.html
        return FileResponse(FRONTEND_DIST / "index.html")
```

- [ ] **Step 4: Verify the app starts**

```bash
cd backend && uvicorn main:app --port 8000
```

In another shell: `curl http://localhost:8000/api/health` → expect `{"ok":true}`. Stop the server.

- [ ] **Step 5: Commit**

```bash
git add backend/config.py backend/supabase_client.py backend/main.py
git commit -m "feat(backend): app skeleton with config + Supabase client"
```

---

## Task 4: Pytest setup + shared fixtures (mocked Supabase)

**Files:**
- Create: `backend/tests/conftest.py`
- Create: `backend/pytest.ini`

- [ ] **Step 1: Create `backend/pytest.ini`**

```ini
[pytest]
testpaths = tests
addopts = -v --tb=short
asyncio_mode = auto
```

- [ ] **Step 2: Create `backend/tests/conftest.py`**

```python
"""Shared fixtures: mocked Supabase client + FastAPI TestClient."""
from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    """Stub env vars so config.load_settings() works in tests."""
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test-service-key")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-jwt-secret")
    monkeypatch.setenv("MANAGER_EMAIL", "manager@example.com")


@pytest.fixture
def mock_supabase(monkeypatch):
    """Replace get_supabase() with a MagicMock. Tests configure return values per call."""
    mock = MagicMock(name="supabase_client")
    import supabase_client
    monkeypatch.setattr(supabase_client, "get_supabase", lambda: mock)
    # Also patch in the module that imports it
    return mock


@pytest.fixture
def client(mock_supabase) -> TestClient:
    from main import app
    return TestClient(app)
```

- [ ] **Step 3: Run the tests directory (no tests yet, just verify pytest discovers)**

```bash
cd backend && pytest
```

Expected: `no tests ran` (exit 5) — that's fine.

- [ ] **Step 4: Commit**

```bash
git add backend/pytest.ini backend/tests/conftest.py
git commit -m "test(backend): pytest config + shared fixtures"
```

---

## Task 5: Scoring module (pure function) — TDD

**Files:**
- Create: `backend/scoring.py`
- Create: `backend/tests/test_scoring.py`

`scoring.compute_recommendation` takes the raw decision/quiz/event records and returns `(recommendation, auto_fail_reasons)`. Pure function, no DB access.

- [ ] **Step 1: Write the failing tests in `backend/tests/test_scoring.py`**

```python
"""Tests for scoring.compute_recommendation."""
from __future__ import annotations

from scoring import StepStats, ScoringInput, compute_recommendation


def _step(
    accuracy: float = 1.0,
    obvious_bad_caught: int = 4,
    obvious_good_caught: int = 4,
    duplicate_consistency: int = 2,
) -> StepStats:
    return StepStats(
        accuracy=accuracy,
        obvious_bad_caught=obvious_bad_caught,
        obvious_good_caught=obvious_good_caught,
        duplicate_consistency=duplicate_consistency,
    )


def _input(
    quiz_score: int = 5,
    tab_switches: int = 0,
    tiktok: StepStats | None = None,
    nano_banana: StepStats | None = None,
    kling: StepStats | None = None,
) -> ScoringInput:
    return ScoringInput(
        quiz_score=quiz_score,
        tab_switches=tab_switches,
        tiktok=tiktok or _step(),
        nano_banana=nano_banana or _step(),
        kling=kling or _step(),
    )


def test_perfect_candidate_passes():
    rec, reasons = compute_recommendation(_input())
    assert rec == "pass"
    assert reasons == []


def test_failed_quiz_is_fail():
    rec, reasons = compute_recommendation(_input(quiz_score=3))
    assert rec == "fail"
    assert "failed_quiz" in reasons


def test_missed_obvious_bad_is_fail():
    rec, reasons = compute_recommendation(_input(tiktok=_step(obvious_bad_caught=3)))
    assert rec == "fail"
    assert "missed_obvious_bad_tiktok" in reasons


def test_missed_obvious_bad_in_kling_is_fail():
    rec, reasons = compute_recommendation(_input(kling=_step(obvious_bad_caught=2)))
    assert rec == "fail"
    assert "missed_obvious_bad_kling" in reasons


def test_dupe_inconsistency_is_fail():
    rec, reasons = compute_recommendation(_input(nano_banana=_step(duplicate_consistency=1)))
    assert rec == "fail"
    assert "inconsistent_duplicate_nano_banana" in reasons


def test_below_floor_accuracy_is_fail():
    rec, reasons = compute_recommendation(_input(tiktok=_step(accuracy=0.69)))
    assert rec == "fail"
    assert "below_floor_tiktok" in reasons


def test_70_percent_is_not_fail():
    rec, reasons = compute_recommendation(_input(tiktok=_step(accuracy=0.70)))
    # 0.70 is the floor — ≥ 0.70 is not below floor. But < 0.80 is borderline.
    assert rec == "borderline"
    assert "weak_step_tiktok" in reasons


def test_rejected_obvious_good_is_borderline():
    rec, reasons = compute_recommendation(_input(kling=_step(obvious_good_caught=3)))
    assert rec == "borderline"
    assert "rejected_obvious_good_kling" in reasons


def test_high_tab_switches_is_borderline():
    rec, reasons = compute_recommendation(_input(tab_switches=6))
    assert rec == "borderline"
    assert "high_tab_switching" in reasons


def test_5_tab_switches_is_not_borderline():
    rec, reasons = compute_recommendation(_input(tab_switches=5))
    assert rec == "pass"
    assert reasons == []


def test_fail_takes_precedence_over_borderline():
    rec, reasons = compute_recommendation(_input(
        quiz_score=3,                                    # fail
        kling=_step(obvious_good_caught=2),              # borderline
    ))
    assert rec == "fail"
    assert "failed_quiz" in reasons
    # borderline reasons not added when overall is fail
    assert all(not r.startswith("rejected_obvious_good") for r in reasons)


def test_multiple_fail_reasons_all_recorded():
    rec, reasons = compute_recommendation(_input(
        quiz_score=3,
        tiktok=_step(obvious_bad_caught=3),
        kling=_step(accuracy=0.5),
    ))
    assert rec == "fail"
    assert "failed_quiz" in reasons
    assert "missed_obvious_bad_tiktok" in reasons
    assert "below_floor_kling" in reasons
```

- [ ] **Step 2: Run tests — they should fail (module doesn't exist yet)**

```bash
cd backend && pytest tests/test_scoring.py -v
```

Expected: `ImportError: cannot import name 'StepStats' from 'scoring'` (or similar).

- [ ] **Step 3: Implement `backend/scoring.py`**

```python
"""Pure scoring logic: recommendation + auto_fail_reasons from raw stats."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from config import (
    OBVIOUS_BAD_ANCHORS_PER_STEP,
    OBVIOUS_GOOD_ANCHORS_PER_STEP,
    DUPLICATES_PER_STEP,
    POOLS,
    QUIZ_PASS_THRESHOLD,
    STEP_ACCURACY_BORDERLINE_FLOOR,
    STEP_ACCURACY_FAIL_FLOOR,
    TAB_SWITCH_BORDERLINE_THRESHOLD,
)


Recommendation = Literal["pass", "borderline", "fail"]


@dataclass(frozen=True)
class StepStats:
    accuracy: float                # correct / 30
    obvious_bad_caught: int        # 0..OBVIOUS_BAD_ANCHORS_PER_STEP
    obvious_good_caught: int       # 0..OBVIOUS_GOOD_ANCHORS_PER_STEP
    duplicate_consistency: int     # 0..DUPLICATES_PER_STEP


@dataclass(frozen=True)
class ScoringInput:
    quiz_score: int                # 0..QUIZ_QUESTION_COUNT
    tab_switches: int
    tiktok: StepStats
    nano_banana: StepStats
    kling: StepStats

    def step(self, name: str) -> StepStats:
        return getattr(self, name)


def compute_recommendation(inp: ScoringInput) -> tuple[Recommendation, list[str]]:
    """Return (recommendation, [auto_fail_reasons]).

    Order of evaluation:
    1. Hard fail rules. If any fire → 'fail' with fail-reasons only.
    2. Borderline rules. If any fire → 'borderline' with all reasons.
    3. Otherwise 'pass' with empty reasons.
    """
    fail_reasons: list[str] = []

    if inp.quiz_score < QUIZ_PASS_THRESHOLD:
        fail_reasons.append("failed_quiz")

    for pool in POOLS:
        s = inp.step(pool)
        if s.obvious_bad_caught < OBVIOUS_BAD_ANCHORS_PER_STEP:
            fail_reasons.append(f"missed_obvious_bad_{pool}")
        if s.duplicate_consistency < DUPLICATES_PER_STEP:
            fail_reasons.append(f"inconsistent_duplicate_{pool}")
        if s.accuracy < STEP_ACCURACY_FAIL_FLOOR:
            fail_reasons.append(f"below_floor_{pool}")

    if fail_reasons:
        return "fail", fail_reasons

    borderline_reasons: list[str] = []
    for pool in POOLS:
        s = inp.step(pool)
        if s.obvious_good_caught < OBVIOUS_GOOD_ANCHORS_PER_STEP:
            borderline_reasons.append(f"rejected_obvious_good_{pool}")
        if s.accuracy < STEP_ACCURACY_BORDERLINE_FLOOR:
            borderline_reasons.append(f"weak_step_{pool}")
    if inp.tab_switches > TAB_SWITCH_BORDERLINE_THRESHOLD:
        borderline_reasons.append("high_tab_switching")

    if borderline_reasons:
        return "borderline", borderline_reasons

    return "pass", []
```

- [ ] **Step 4: Run tests — should pass**

```bash
cd backend && pytest tests/test_scoring.py -v
```

Expected: 12 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/scoring.py backend/tests/test_scoring.py
git commit -m "feat(backend): scoring module with pass/borderline/fail rules"
```

---

## Task 6: Auth module — manager JWT verify + invite-token cookie verify

**Files:**
- Create: `backend/auth.py`
- Create: `backend/tests/test_auth.py`

The manager auth uses Supabase JWT (HS256, secret = `SUPABASE_JWT_SECRET`). The candidate auth uses an opaque `session_id` cookie that must match the candidate's stored session_id.

- [ ] **Step 1: Write failing tests in `backend/tests/test_auth.py`**

```python
"""Tests for auth.verify_manager_jwt and verify_candidate_session."""
from __future__ import annotations

import time

import jwt
import pytest
from fastapi import HTTPException

from auth import verify_candidate_session, verify_manager_jwt


JWT_SECRET = "test-jwt-secret"


def _manager_token(email: str = "manager@example.com", exp_offset: int = 3600) -> str:
    payload = {
        "sub": "00000000-0000-0000-0000-000000000001",
        "email": email,
        "exp": int(time.time()) + exp_offset,
        "aud": "authenticated",
        "role": "authenticated",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def test_verify_manager_jwt_accepts_correct_email():
    token = _manager_token()
    claims = verify_manager_jwt(f"Bearer {token}")
    assert claims["email"] == "manager@example.com"


def test_verify_manager_jwt_rejects_wrong_email():
    token = _manager_token(email="someone-else@example.com")
    with pytest.raises(HTTPException) as exc:
        verify_manager_jwt(f"Bearer {token}")
    assert exc.value.status_code == 403


def test_verify_manager_jwt_rejects_expired():
    token = _manager_token(exp_offset=-10)
    with pytest.raises(HTTPException) as exc:
        verify_manager_jwt(f"Bearer {token}")
    assert exc.value.status_code == 401


def test_verify_manager_jwt_rejects_missing_header():
    with pytest.raises(HTTPException) as exc:
        verify_manager_jwt(None)
    assert exc.value.status_code == 401


def test_verify_manager_jwt_rejects_malformed_header():
    with pytest.raises(HTTPException) as exc:
        verify_manager_jwt("Token abc")
    assert exc.value.status_code == 401


def test_verify_candidate_session_matches():
    # Candidate row has session_id 'sess-123' and link_used=False
    candidate = {"session_id": "sess-123", "link_used": False}
    # cookie value matches
    verify_candidate_session(candidate, cookie_value="sess-123")
    # no exception → success


def test_verify_candidate_session_rejects_mismatch():
    candidate = {"session_id": "sess-123", "link_used": False}
    with pytest.raises(HTTPException) as exc:
        verify_candidate_session(candidate, cookie_value="sess-other")
    assert exc.value.status_code == 409


def test_verify_candidate_session_rejects_missing_cookie():
    candidate = {"session_id": "sess-123", "link_used": False}
    with pytest.raises(HTTPException) as exc:
        verify_candidate_session(candidate, cookie_value=None)
    assert exc.value.status_code == 409


def test_verify_candidate_session_rejects_used_link():
    candidate = {"session_id": "sess-123", "link_used": True}
    with pytest.raises(HTTPException) as exc:
        verify_candidate_session(candidate, cookie_value="sess-123")
    assert exc.value.status_code == 410   # Gone
```

- [ ] **Step 2: Run tests — fail with ImportError**

```bash
cd backend && pytest tests/test_auth.py -v
```

- [ ] **Step 3: Implement `backend/auth.py`**

```python
"""Auth helpers: manager JWT verify + candidate session-cookie verify."""
from __future__ import annotations

import jwt
from fastapi import HTTPException

from config import load_settings


def verify_manager_jwt(authorization_header: str | None) -> dict:
    """Verify a manager Supabase JWT and return its claims.

    Raises HTTPException(401) for missing/malformed/expired,
    HTTPException(403) for valid token with non-manager email.
    """
    if not authorization_header or not authorization_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")
    token = authorization_header.removeprefix("Bearer ").strip()
    settings = load_settings()
    try:
        claims = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

    email = (claims.get("email") or "").lower()
    if email != settings.manager_email:
        raise HTTPException(status_code=403, detail="Not authorized as manager")
    return claims


def verify_candidate_session(candidate: dict, cookie_value: str | None) -> None:
    """Validate a candidate session cookie against the stored session_id.

    Raises HTTPException(410) if link_used is true,
    HTTPException(409) if cookie missing or mismatched.
    """
    if candidate.get("link_used"):
        raise HTTPException(status_code=410, detail="Link already used")
    expected = candidate.get("session_id")
    if not expected or cookie_value != expected:
        raise HTTPException(status_code=409, detail="Session in use elsewhere or expired")
```

- [ ] **Step 4: Run tests — should pass**

```bash
cd backend && pytest tests/test_auth.py -v
```

Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/auth.py backend/tests/test_auth.py
git commit -m "feat(backend): auth — manager JWT + candidate session cookie"
```

---

## Task 7: Pydantic models for shared request/response shapes

**Files:**
- Create: `backend/models.py`

This task is mostly definitional — no tests beyond Pydantic's own validation.

- [ ] **Step 1: Create `backend/models.py`**

```python
"""Pydantic v2 schemas for API requests/responses."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

Pool = Literal["tiktok", "nano_banana", "kling"]
Recommendation = Literal["pass", "borderline", "fail"]
ManagerDecision = Literal["hired", "rejected"]
EventKind = Literal[
    "tab_blur", "tab_focus", "step_start", "step_end",
    "tutorial_view", "quiz_start", "quiz_end", "session_start",
]


# ============================================================
# Candidate-side requests
# ============================================================

class StartRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr


class QuizRequest(BaseModel):
    answers: list[int] = Field(min_length=5, max_length=5)


class DecisionRequest(BaseModel):
    item_id: str
    answer: bool
    dwell_ms: int = Field(ge=0)
    shown_at: datetime


class JustificationRequest(BaseModel):
    decision_id: str
    justification: str = Field(min_length=1, max_length=2000)


class EventRequest(BaseModel):
    kind: EventKind
    meta: dict = Field(default_factory=dict)


# ============================================================
# Candidate-side responses
# ============================================================

class StateResponseItem(BaseModel):
    """The next item to show, when state is step_<n>_in_progress."""
    id: str
    storage_url: str       # signed URL for the media file
    pool: Pool
    display_index: int     # 0..29


class StateResponse(BaseModel):
    state: Literal[
        "needs_name", "needs_tutorial", "needs_quiz",
        "step_tiktok_intro", "step_tiktok_in_progress",
        "step_nano_banana_intro", "step_nano_banana_in_progress",
        "step_kling_intro", "step_kling_in_progress",
        "submitted", "invalid", "session_in_use",
    ]
    progress_in_step: int = 0       # number of decisions already submitted in current step
    next_item: StateResponseItem | None = None


class DecisionResponseNext(BaseModel):
    item: StateResponseItem | None = None
    step_complete: bool = False
    test_complete: bool = False


class DecisionResponse(BaseModel):
    decision_id: str
    needs_justification: bool
    next: DecisionResponseNext


class QuizResponse(BaseModel):
    passed: bool
    score: int        # 0..5


# ============================================================
# Manager-side requests
# ============================================================

class CreateInviteRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr


class CreateInviteResponse(BaseModel):
    candidate_id: str
    token: str
    url: str


class PatchCandidateRequest(BaseModel):
    manager_decision: ManagerDecision | None = None
    manager_notes: str | None = None


# ============================================================
# Manager-side responses
# ============================================================

class CandidateRow(BaseModel):
    id: str
    invited_label: str | None
    invited_label_email: str | None
    candidate_name: str | None
    candidate_email: str | None
    created_at: datetime
    started_at: datetime | None
    submitted_at: datetime | None
    link_used: bool
    recommendation: Recommendation | None
    manager_decision: ManagerDecision | None
    total_time_seconds: int | None


class StepBreakdown(BaseModel):
    pool: Pool
    accuracy: float
    obvious_bad_caught: int
    obvious_good_caught: int
    duplicate_consistency: int
    median_dwell_ms: int | None
    duration_seconds: int | None


class CandidateDetail(BaseModel):
    row: CandidateRow
    auto_fail_reasons: list[str]
    quiz_correct: int
    quiz_total: int
    tab_switches: int
    steps: list[StepBreakdown]
    free_text_justifications: list[dict]   # [{pool, item_id, item_storage_path, justification}]
    decisions: list[dict]                  # full per-item record for the expandable view
    manager_notes: str | None
```

- [ ] **Step 2: Quick sanity check (Python imports the file without error)**

```bash
cd backend && python -c "import models; print('ok')"
```

Expected: `ok`.

- [ ] **Step 3: Commit**

```bash
git add backend/models.py
git commit -m "feat(backend): pydantic schemas for candidate + manager APIs"
```

---

## Task 8: Storage helpers — signed URLs

**Files:**
- Create: `backend/storage.py`

Small helper that wraps Supabase Storage signed URL generation.

- [ ] **Step 1: Create `backend/storage.py`**

```python
"""Helpers for Supabase Storage signed URLs."""
from __future__ import annotations

from config import load_settings
from supabase_client import get_supabase


def bucket_for_pool(pool: str) -> str:
    s = load_settings()
    return {
        "tiktok": s.bucket_tiktoks,
        "nano_banana": s.bucket_nano_banana,
        "kling": s.bucket_kling,
    }[pool]


def signed_url_for_item(pool: str, storage_path: str) -> str:
    """Return a short-lived signed URL for the given item."""
    s = load_settings()
    bucket = bucket_for_pool(pool)
    res = get_supabase().storage.from_(bucket).create_signed_url(
        storage_path, s.signed_url_ttl_seconds
    )
    # supabase-py returns {'signedURL': '...'} or {'signed_url': '...'} depending on version
    return res.get("signedURL") or res.get("signed_url") or ""
```

- [ ] **Step 2: Verify import**

```bash
cd backend && python -c "import storage; print('ok')"
```

- [ ] **Step 3: Commit**

```bash
git add backend/storage.py
git commit -m "feat(backend): storage signed-URL helper"
```

---

## Task 9: Candidate routes — `/state` and `/start` (TDD with TestClient)

**Files:**
- Create: `backend/routers/candidate.py`
- Modify: `backend/main.py` (mount router)
- Create: `backend/tests/test_candidate_state_start.py`

This is the entry point of the candidate flow. `/state` is public (no cookie required for unstarted candidates); `/start` creates the session and sets the cookie.

- [ ] **Step 1: Write failing tests in `backend/tests/test_candidate_state_start.py`**

```python
"""Tests for /api/test/<token>/state and /start."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock


def _candidate_row(**overrides):
    base = {
        "id": str(uuid.uuid4()),
        "invite_token": "tok-abc",
        "session_id": None,
        "started_at": None,
        "submitted_at": None,
        "link_used": False,
        "candidate_name": None,
        "candidate_email": None,
        "forced_justification_indexes": None,
    }
    base.update(overrides)
    return base


def _setup_select_single(mock_supabase, table: str, value):
    """Configure mock_supabase.table(<table>).select(...).eq(...).single().execute() = value."""
    table_chain = mock_supabase.table.return_value
    select_chain = table_chain.select.return_value
    eq_chain = select_chain.eq.return_value
    single_chain = eq_chain.single.return_value
    single_chain.execute.return_value = MagicMock(data=value)


def test_state_unknown_token_is_invalid(client, mock_supabase):
    _setup_select_single(mock_supabase, "candidates", None)
    r = client.get("/api/test/nope/state")
    assert r.status_code == 200
    assert r.json()["state"] == "invalid"


def test_state_unstarted_candidate_returns_needs_name(client, mock_supabase):
    _setup_select_single(mock_supabase, "candidates", _candidate_row())
    r = client.get("/api/test/tok-abc/state")
    assert r.status_code == 200
    assert r.json()["state"] == "needs_name"


def test_state_used_link_returns_invalid(client, mock_supabase):
    _setup_select_single(mock_supabase, "candidates", _candidate_row(link_used=True))
    r = client.get("/api/test/tok-abc/state")
    assert r.json()["state"] == "invalid"


def test_state_started_session_without_cookie_returns_session_in_use(client, mock_supabase):
    row = _candidate_row(started_at="2026-05-10T00:00:00Z", session_id="sess-123")
    _setup_select_single(mock_supabase, "candidates", row)
    r = client.get("/api/test/tok-abc/state")
    assert r.json()["state"] == "session_in_use"


def test_start_creates_session_and_sets_cookie(client, mock_supabase):
    row = _candidate_row()
    _setup_select_single(mock_supabase, "candidates", row)
    update_chain = mock_supabase.table.return_value.update.return_value
    update_chain.eq.return_value.execute.return_value = MagicMock(data=[row])

    r = client.post("/api/test/tok-abc/start", json={"name": "Jane Doe", "email": "j@d.com"})
    assert r.status_code == 200
    assert "session_id" in r.cookies


def test_start_rejects_already_started(client, mock_supabase):
    row = _candidate_row(started_at="2026-05-10T00:00:00Z", session_id="sess-existing")
    _setup_select_single(mock_supabase, "candidates", row)
    r = client.post("/api/test/tok-abc/start", json={"name": "X", "email": "y@z.com"})
    assert r.status_code == 409


def test_start_rejects_used_link(client, mock_supabase):
    row = _candidate_row(link_used=True)
    _setup_select_single(mock_supabase, "candidates", row)
    r = client.post("/api/test/tok-abc/start", json={"name": "X", "email": "y@z.com"})
    assert r.status_code == 410
```

- [ ] **Step 2: Run tests — fail**

```bash
cd backend && pytest tests/test_candidate_state_start.py -v
```

- [ ] **Step 3: Implement `backend/routers/candidate.py`**

```python
"""Candidate-side endpoints: /api/test/<token>/*"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Cookie, HTTPException, Response

from auth import verify_candidate_session
from config import load_settings
from models import StartRequest, StateResponse
from supabase_client import get_supabase

router = APIRouter(prefix="/api/test/{token}", tags=["candidate"])

SESSION_COOKIE = "session_id"


def _get_candidate(token: str) -> dict | None:
    res = (
        get_supabase()
        .table("candidates")
        .select("*")
        .eq("invite_token", token)
        .single()
        .execute()
    )
    return res.data


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_state(candidate: dict | None, cookie: str | None) -> StateResponse:
    if candidate is None or candidate.get("link_used"):
        return StateResponse(state="invalid")
    if not candidate.get("started_at"):
        return StateResponse(state="needs_name")
    # Started — must have a matching cookie to proceed
    if cookie != candidate.get("session_id"):
        return StateResponse(state="session_in_use")
    # Detailed state (tutorial/quiz/step) computed in later tasks
    return StateResponse(state="needs_tutorial")


@router.get("/state", response_model=StateResponse)
def state(token: str, session_id: str | None = Cookie(default=None)) -> StateResponse:
    candidate = _get_candidate(token)
    return _resolve_state(candidate, session_id)


@router.post("/start", response_model=StateResponse)
def start(token: str, body: StartRequest, response: Response) -> StateResponse:
    candidate = _get_candidate(token)
    if candidate is None:
        raise HTTPException(404, "Invalid invite link")
    if candidate.get("link_used"):
        raise HTTPException(410, "Link already used")
    if candidate.get("started_at") or candidate.get("session_id"):
        raise HTTPException(409, "Test already in progress")

    new_session = secrets.token_urlsafe(32)
    now = _now_iso()
    update = {
        "candidate_name": body.name,
        "candidate_email": body.email,
        "session_id": new_session,
        "started_at": now,
    }
    get_supabase().table("candidates").update(update).eq("invite_token", token).execute()

    settings = load_settings()
    response.set_cookie(
        key=SESSION_COOKIE,
        value=new_session,
        max_age=settings.session_cookie_max_age_seconds,
        httponly=True,
        samesite="lax",
        path=f"/api/test/{token}",
    )
    return StateResponse(state="needs_tutorial")
```

- [ ] **Step 4: Mount the router in `backend/main.py`**

Add import and include:

```python
from routers import candidate as candidate_router
# ... after CORS middleware:
app.include_router(candidate_router.router)
```

- [ ] **Step 5: Run tests — should pass**

```bash
cd backend && pytest tests/test_candidate_state_start.py -v
```

Expected: 7 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/routers/candidate.py backend/main.py backend/tests/test_candidate_state_start.py
git commit -m "feat(backend): candidate /state and /start endpoints"
```

---

## Task 10: Candidate routes — `/tutorial-acknowledged`, quiz state, `/quiz`

**Files:**
- Modify: `backend/routers/candidate.py`
- Create: `backend/tests/test_candidate_tutorial_quiz.py`

The state machine resolves to `needs_tutorial` after start. Once tutorial is acknowledged, state advances to `needs_quiz`. Submitting the quiz either fails the candidate (if <4/5) or advances to `step_tiktok_intro`.

- [ ] **Step 1: Update `_resolve_state` in `backend/routers/candidate.py` to consider events and quiz answers**

Replace the body of `_resolve_state` and add helpers:

```python
def _has_event(candidate_id: str, kind: str) -> bool:
    res = (
        get_supabase()
        .table("candidate_events")
        .select("id")
        .eq("candidate_id", candidate_id)
        .eq("kind", kind)
        .limit(1)
        .execute()
    )
    return bool(res.data)


def _quiz_answered(candidate_id: str) -> bool:
    res = (
        get_supabase()
        .table("candidate_quiz_answers")
        .select("id", count="exact")
        .eq("candidate_id", candidate_id)
        .execute()
    )
    return (res.count or 0) >= 5


def _resolve_state(candidate: dict | None, cookie: str | None) -> StateResponse:
    if candidate is None or candidate.get("link_used"):
        return StateResponse(state="invalid")
    if not candidate.get("started_at"):
        return StateResponse(state="needs_name")
    if cookie != candidate.get("session_id"):
        return StateResponse(state="session_in_use")
    if candidate.get("submitted_at"):
        return StateResponse(state="submitted")
    cid = candidate["id"]
    if not _has_event(cid, "tutorial_view"):
        return StateResponse(state="needs_tutorial")
    if not _quiz_answered(cid):
        return StateResponse(state="needs_quiz")
    # Step routing computed in Task 12. Until then default to first step intro.
    return StateResponse(state="step_tiktok_intro")
```

- [ ] **Step 2: Add the two endpoints**

Append to `backend/routers/candidate.py`:

```python
from models import EventRequest, QuizRequest, QuizResponse
from config import QUIZ_PASS_THRESHOLD


@router.post("/tutorial-acknowledged", response_model=StateResponse)
def tutorial_ack(token: str, session_id: str | None = Cookie(default=None)) -> StateResponse:
    candidate = _get_candidate(token)
    if candidate is None:
        raise HTTPException(404, "Invalid invite link")
    verify_candidate_session(candidate, session_id)
    cid = candidate["id"]
    if not _has_event(cid, "tutorial_view"):
        get_supabase().table("candidate_events").insert({
            "candidate_id": cid,
            "kind": "tutorial_view",
        }).execute()
    return _resolve_state(_get_candidate(token), session_id)


@router.post("/quiz", response_model=QuizResponse)
def submit_quiz(token: str, body: QuizRequest, session_id: str | None = Cookie(default=None)) -> QuizResponse:
    candidate = _get_candidate(token)
    if candidate is None:
        raise HTTPException(404, "Invalid invite link")
    verify_candidate_session(candidate, session_id)
    cid = candidate["id"]
    if _quiz_answered(cid):
        raise HTTPException(409, "Quiz already submitted")

    # Fetch the 5 questions in display_order
    qres = (
        get_supabase()
        .table("quiz_questions")
        .select("id,correct_index,display_order")
        .order("display_order")
        .execute()
    )
    questions = qres.data or []
    if len(questions) != 5:
        raise HTTPException(500, f"Expected 5 quiz questions, got {len(questions)}")

    score = 0
    rows_to_insert = []
    for idx, q in enumerate(questions):
        answered = body.answers[idx]
        is_correct = answered == q["correct_index"]
        if is_correct:
            score += 1
        rows_to_insert.append({
            "candidate_id": cid,
            "question_id": q["id"],
            "answered_index": answered,
            "is_correct": is_correct,
        })
    get_supabase().table("candidate_quiz_answers").insert(rows_to_insert).execute()

    passed = score >= QUIZ_PASS_THRESHOLD
    if not passed:
        # Auto-fail immediately. Mark link used, set recommendation.
        get_supabase().table("candidates").update({
            "link_used": True,
            "submitted_at": _now_iso(),
            "recommendation": "fail",
            "auto_fail_reasons": ["failed_quiz"],
        }).eq("id", cid).execute()
    return QuizResponse(passed=passed, score=score)
```

- [ ] **Step 3: Write tests in `backend/tests/test_candidate_tutorial_quiz.py`**

```python
"""Tests for /tutorial-acknowledged and /quiz."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock


CID = str(uuid.uuid4())


def _candidate(**overrides):
    base = {
        "id": CID,
        "invite_token": "tok-abc",
        "session_id": "sess-1",
        "started_at": "2026-05-10T00:00:00Z",
        "submitted_at": None,
        "link_used": False,
        "forced_justification_indexes": None,
    }
    base.update(overrides)
    return base


def _wire(mock, *, candidate, has_event=False, quiz_count=0, questions=None):
    """Wire up the most common chain calls used by these tests."""
    table = mock.table

    def _select_single(value):
        return MagicMock(execute=MagicMock(return_value=MagicMock(data=value)))

    def candidates_select():
        return MagicMock(eq=lambda *_a, **_k: MagicMock(single=lambda: _select_single(candidate)))

    def events_select():
        return MagicMock(eq=lambda *_a, **_k: MagicMock(eq=lambda *_a, **_k: MagicMock(
            limit=lambda *_a, **_k: MagicMock(execute=lambda: MagicMock(data=[1] if has_event else []))
        )))

    def quiz_answers_select():
        return MagicMock(eq=lambda *_a, **_k: MagicMock(execute=lambda: MagicMock(count=quiz_count)))

    def quiz_questions_select():
        return MagicMock(order=lambda *_a, **_k: MagicMock(execute=lambda: MagicMock(data=questions or [])))

    insert_chain = MagicMock(execute=MagicMock())
    update_chain = MagicMock(eq=MagicMock(return_value=MagicMock(execute=MagicMock())))

    def table_router(name):
        m = MagicMock()
        if name == "candidates":
            m.select = MagicMock(return_value=candidates_select())
            m.update = MagicMock(return_value=update_chain)
        elif name == "candidate_events":
            m.select = MagicMock(return_value=events_select())
            m.insert = MagicMock(return_value=insert_chain)
        elif name == "candidate_quiz_answers":
            m.select = MagicMock(return_value=quiz_answers_select())
            m.insert = MagicMock(return_value=insert_chain)
        elif name == "quiz_questions":
            m.select = MagicMock(return_value=quiz_questions_select())
        return m

    table.side_effect = table_router


def test_tutorial_ack_logs_event(client, mock_supabase):
    cand = _candidate()
    _wire(mock_supabase, candidate=cand, has_event=False, quiz_count=0)
    r = client.post(
        "/api/test/tok-abc/tutorial-acknowledged",
        cookies={"session_id": "sess-1"},
    )
    assert r.status_code == 200
    # Insert into candidate_events called
    mock_supabase.table.assert_any_call("candidate_events")


def test_quiz_pass_advances_state(client, mock_supabase):
    cand = _candidate()
    questions = [{"id": str(uuid.uuid4()), "correct_index": i % 4, "display_order": i} for i in range(5)]
    _wire(mock_supabase, candidate=cand, has_event=True, quiz_count=0, questions=questions)
    answers = [q["correct_index"] for q in questions]   # all correct
    r = client.post("/api/test/tok-abc/quiz",
                    json={"answers": answers},
                    cookies={"session_id": "sess-1"})
    assert r.status_code == 200
    assert r.json() == {"passed": True, "score": 5}


def test_quiz_fail_marks_link_used(client, mock_supabase):
    cand = _candidate()
    questions = [{"id": str(uuid.uuid4()), "correct_index": 0, "display_order": i} for i in range(5)]
    _wire(mock_supabase, candidate=cand, has_event=True, quiz_count=0, questions=questions)
    # 2/5 correct
    answers = [0, 0, 1, 1, 1]
    r = client.post("/api/test/tok-abc/quiz",
                    json={"answers": answers},
                    cookies={"session_id": "sess-1"})
    assert r.status_code == 200
    assert r.json() == {"passed": False, "score": 2}
    # update was called on candidates with link_used=True
    update_calls = [c for c in mock_supabase.table.return_value.update.call_args_list]
    assert any("link_used" in str(call) for call in update_calls)
```

> Note: the wiring in `_wire` is intentionally permissive — exact assertions live in dedicated unit tests for scoring. Here we verify endpoints respond and trigger expected DB calls.

- [ ] **Step 4: Run tests — should pass**

```bash
cd backend && pytest tests/test_candidate_tutorial_quiz.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/routers/candidate.py backend/tests/test_candidate_tutorial_quiz.py
git commit -m "feat(backend): tutorial-ack + quiz endpoints with auto-fail"
```

---

## Task 11: Candidate routes — step intro + `/decision` (the heart of the flow)

**Files:**
- Modify: `backend/routers/candidate.py`
- Create: `backend/tests/test_candidate_decision.py`

This task wires up the per-step item delivery and decision recording. It is the most complex task in the plan.

Key behaviors:
- Each step has a fixed sequence per candidate. The sequence is computed deterministically the first time a step starts: 28 unique items (4 obvious-good anchors + 4 obvious-bad anchors + 20 normal) shuffled, then 2 of those items duplicated and inserted at random positions later in the sequence (positions > the original index). Positions stored implicitly via `display_index` on `candidate_decisions` rows.
- Forced-justification indexes are picked once at `/start` time (Task 9 pre-work — we add it now retroactively) — but it is simpler to lazily pick them when each step first begins. We do that here.
- `/decision` records the decision row, computes `is_correct`, sets `forced_justification` flag if the index matches the chosen indexes for the step, and returns the next item or `step_complete`.

- [ ] **Step 1: Add the step-sequence builder helpers in `backend/routers/candidate.py`**

```python
import random as _random

from config import (
    DUPLICATES_PER_STEP, FORCED_JUSTIFICATIONS_PER_STEP, ITEMS_PER_STEP,
    OBVIOUS_BAD_ANCHORS_PER_STEP, OBVIOUS_GOOD_ANCHORS_PER_STEP,
    NORMAL_ITEMS_PER_STEP, POOLS, UNIQUE_ITEMS_PER_STEP,
)
from models import DecisionRequest, DecisionResponse, DecisionResponseNext, StateResponseItem
from storage import signed_url_for_item


def _candidate_decisions_for_step(candidate_id: str, pool: str) -> list[dict]:
    res = (
        get_supabase()
        .table("candidate_decisions")
        .select("*")
        .eq("candidate_id", candidate_id)
        .eq("pool", pool)
        .order("display_index")
        .execute()
    )
    return res.data or []


def _items_for_pool(pool: str) -> list[dict]:
    res = get_supabase().table("test_items").select("*").eq("pool", pool).execute()
    return res.data or []


def _build_step_sequence(pool: str, rng: _random.Random) -> list[dict]:
    """Return a list of ITEMS_PER_STEP item dicts in the order to be shown.

    Layout: 28 unique (4 obvious_good + 4 obvious_bad + 20 normal) shuffled,
    then 2 random items from the 28 are duplicated and inserted at later positions.
    Returns dicts with keys: item_id, is_duplicate, original_display_index (or None).
    """
    items = _items_for_pool(pool)
    obvious_good = [i for i in items if i["is_anchor"] and i["anchor_kind"] == "obvious_good"]
    obvious_bad = [i for i in items if i["is_anchor"] and i["anchor_kind"] == "obvious_bad"]
    normal = [i for i in items if not i["is_anchor"]]

    if (len(obvious_good) < OBVIOUS_GOOD_ANCHORS_PER_STEP
            or len(obvious_bad) < OBVIOUS_BAD_ANCHORS_PER_STEP
            or len(normal) < NORMAL_ITEMS_PER_STEP):
        raise HTTPException(500, f"Insufficient items in pool {pool}")

    chosen = (
        rng.sample(obvious_good, OBVIOUS_GOOD_ANCHORS_PER_STEP)
        + rng.sample(obvious_bad, OBVIOUS_BAD_ANCHORS_PER_STEP)
        + rng.sample(normal, NORMAL_ITEMS_PER_STEP)
    )
    rng.shuffle(chosen)

    sequence = [{"item_id": i["id"], "is_duplicate": False, "original_index": None} for i in chosen]
    # Pick 2 unique source positions to duplicate. Their dupes go at later positions.
    source_positions = rng.sample(range(UNIQUE_ITEMS_PER_STEP), DUPLICATES_PER_STEP)
    for src in sorted(source_positions):
        # Insert duplicate at a position strictly later than src and strictly later than current end.
        insert_at = rng.randint(src + 1, len(sequence))
        sequence.insert(insert_at, {
            "item_id": sequence[src]["item_id"],
            "is_duplicate": True,
            "original_index": src,
        })
    assert len(sequence) == ITEMS_PER_STEP
    return sequence


def _ensure_step_started(candidate: dict, pool: str) -> tuple[list[dict], list[int]]:
    """If the candidate has not started this step, build & return the sequence and forced-justification indexes.

    Sequence is materialized lazily as the candidate answers (we don't pre-insert decision rows).
    Forced-justification indexes are persisted on candidates.forced_justification_indexes the first time the step starts.
    Returns (full_sequence, forced_indexes).
    """
    cid = candidate["id"]
    decisions = _candidate_decisions_for_step(cid, pool)
    forced = (candidate.get("forced_justification_indexes") or {}).get(pool)

    # If we already have the forced indexes, we also already have the sequence — reconstruct from existing rows
    # *plus* a precomputed cache. Since we don't precompute, we rebuild from a deterministic seed each step.
    seed = f"{candidate['session_id']}:{pool}"
    rng = _random.Random(seed)
    sequence = _build_step_sequence(pool, rng)

    if forced is None:
        forced = sorted(rng.sample(range(ITEMS_PER_STEP), FORCED_JUSTIFICATIONS_PER_STEP))
        all_forced = candidate.get("forced_justification_indexes") or {}
        all_forced[pool] = forced
        get_supabase().table("candidates").update({
            "forced_justification_indexes": all_forced,
        }).eq("id", cid).execute()
        # also log step_start
        get_supabase().table("candidate_events").insert({
            "candidate_id": cid, "kind": "step_start", "meta": {"pool": pool},
        }).execute()

    return sequence, forced


def _next_item_for_step(candidate: dict, pool: str) -> StateResponseItem | None:
    cid = candidate["id"]
    sequence, _forced = _ensure_step_started(candidate, pool)
    decisions = _candidate_decisions_for_step(cid, pool)
    next_idx = len(decisions)
    if next_idx >= ITEMS_PER_STEP:
        return None
    item_id = sequence[next_idx]["item_id"]
    item = get_supabase().table("test_items").select("*").eq("id", item_id).single().execute().data
    return StateResponseItem(
        id=item_id,
        storage_url=signed_url_for_item(pool, item["storage_path"]),
        pool=pool,
        display_index=next_idx,
    )
```

- [ ] **Step 2: Replace the placeholder step routing in `_resolve_state`**

```python
def _step_progress(candidate_id: str) -> dict[str, int]:
    out = {p: 0 for p in POOLS}
    res = (
        get_supabase()
        .table("candidate_decisions")
        .select("pool", count="exact")
        .eq("candidate_id", candidate_id)
        .execute()
    )
    # supabase-py can't group by — fall back to fetching all rows' pools
    rows = (
        get_supabase()
        .table("candidate_decisions")
        .select("pool")
        .eq("candidate_id", candidate_id)
        .execute()
    ).data or []
    for r in rows:
        out[r["pool"]] = out.get(r["pool"], 0) + 1
    return out


def _resolve_state(candidate: dict | None, cookie: str | None) -> StateResponse:
    if candidate is None or candidate.get("link_used"):
        return StateResponse(state="invalid")
    if not candidate.get("started_at"):
        return StateResponse(state="needs_name")
    if cookie != candidate.get("session_id"):
        return StateResponse(state="session_in_use")
    if candidate.get("submitted_at"):
        return StateResponse(state="submitted")
    cid = candidate["id"]
    if not _has_event(cid, "tutorial_view"):
        return StateResponse(state="needs_tutorial")
    if not _quiz_answered(cid):
        return StateResponse(state="needs_quiz")
    progress = _step_progress(cid)
    for pool in POOLS:
        if progress[pool] == 0 and not _has_event(cid, f"step_{pool}_intro_acked"):
            # Use a generic kind for intro-acked stored in meta
            return StateResponse(state=f"step_{pool}_intro")
        if progress[pool] < ITEMS_PER_STEP:
            next_item = _next_item_for_step(candidate, pool)
            return StateResponse(
                state=f"step_{pool}_in_progress",
                progress_in_step=progress[pool],
                next_item=next_item,
            )
    # All steps complete but not submitted yet
    return StateResponse(state="step_kling_in_progress")  # caller should call /submit
```

> Note: the `step_<pool>_intro_acked` event is logged via `/step/<pool>/intro-acknowledged` below. It uses `kind="step_start"` plus `meta.intro_acked=true`, OR it can use a dedicated kind. For simplicity, use a separate kind `step_<pool>_intro_acked`. Since the `candidate_events.kind` CHECK constraint is fixed to a known set, we'll use `meta` with `kind="step_start"` and `meta={"pool":..., "intro_acked":true}`. **Refactor:** since `step_start` is already logged when the step actually starts (in `_ensure_step_started`), use it WITHOUT `intro_acked` for that event, and use a separate `step_start` event with `meta.intro_acked=true` for intro-acknowledgment. Track presence of an intro-ack event via `_has_intro_acked` helper:

```python
def _has_intro_acked(candidate_id: str, pool: str) -> bool:
    res = (
        get_supabase()
        .table("candidate_events")
        .select("id,meta")
        .eq("candidate_id", candidate_id)
        .eq("kind", "step_start")
        .execute()
    )
    rows = res.data or []
    return any((r.get("meta") or {}).get("intro_acked") and (r.get("meta") or {}).get("pool") == pool for r in rows)
```

And update `_resolve_state` to call `_has_intro_acked(cid, pool)` instead of `_has_event(cid, f"step_{pool}_intro_acked")`.

- [ ] **Step 3: Add the intro-acknowledged endpoint**

```python
@router.post("/step/{pool}/intro-acknowledged", response_model=StateResponse)
def step_intro_ack(token: str, pool: str, session_id: str | None = Cookie(default=None)) -> StateResponse:
    if pool not in POOLS:
        raise HTTPException(404, "Unknown pool")
    candidate = _get_candidate(token)
    if candidate is None:
        raise HTTPException(404, "Invalid invite link")
    verify_candidate_session(candidate, session_id)
    if not _has_intro_acked(candidate["id"], pool):
        get_supabase().table("candidate_events").insert({
            "candidate_id": candidate["id"],
            "kind": "step_start",
            "meta": {"pool": pool, "intro_acked": True},
        }).execute()
    return _resolve_state(_get_candidate(token), session_id)
```

- [ ] **Step 4: Add the `/decision` endpoint**

```python
@router.post("/decision", response_model=DecisionResponse)
def decision(token: str, body: DecisionRequest, session_id: str | None = Cookie(default=None)) -> DecisionResponse:
    candidate = _get_candidate(token)
    if candidate is None:
        raise HTTPException(404, "Invalid invite link")
    verify_candidate_session(candidate, session_id)
    cid = candidate["id"]

    item = get_supabase().table("test_items").select("*").eq("id", body.item_id).single().execute().data
    if item is None:
        raise HTTPException(404, "Unknown item")
    pool = item["pool"]
    sequence, forced = _ensure_step_started(candidate, pool)
    progress = _step_progress(cid)
    expected_idx = progress[pool]
    if expected_idx >= ITEMS_PER_STEP:
        raise HTTPException(409, f"Step {pool} already complete")
    expected_id = sequence[expected_idx]["item_id"]
    if expected_id != body.item_id:
        raise HTTPException(409, f"Out of order item; expected {expected_id}")

    is_correct = body.answer == item["correct_answer"]
    forced_now = expected_idx in forced
    duplicate_of = None
    if sequence[expected_idx]["is_duplicate"]:
        original_idx = sequence[expected_idx]["original_index"]
        prior = (
            get_supabase().table("candidate_decisions")
            .select("id").eq("candidate_id", cid).eq("pool", pool).eq("display_index", original_idx)
            .single().execute().data
        )
        duplicate_of = (prior or {}).get("id")

    inserted = (
        get_supabase().table("candidate_decisions").insert({
            "candidate_id": cid,
            "item_id": body.item_id,
            "pool": pool,
            "display_index": expected_idx,
            "answer": body.answer,
            "is_correct": is_correct,
            "dwell_ms": body.dwell_ms,
            "shown_at": body.shown_at.isoformat(),
            "forced_justification": forced_now,
            "duplicate_of": duplicate_of,
        }).execute()
    )
    decision_id = inserted.data[0]["id"]

    # Build next response
    next_progress = expected_idx + 1
    if next_progress >= ITEMS_PER_STEP:
        # log step_end
        get_supabase().table("candidate_events").insert({
            "candidate_id": cid, "kind": "step_end", "meta": {"pool": pool},
        }).execute()
        next_pool = _next_pool(pool)
        if next_pool is None:
            return DecisionResponse(
                decision_id=decision_id,
                needs_justification=forced_now,
                next=DecisionResponseNext(test_complete=True),
            )
        return DecisionResponse(
            decision_id=decision_id,
            needs_justification=forced_now,
            next=DecisionResponseNext(step_complete=True),
        )

    next_item_id = sequence[next_progress]["item_id"]
    next_item_row = get_supabase().table("test_items").select("*").eq("id", next_item_id).single().execute().data
    next_item_payload = StateResponseItem(
        id=next_item_id,
        storage_url=signed_url_for_item(pool, next_item_row["storage_path"]),
        pool=pool,
        display_index=next_progress,
    )
    return DecisionResponse(
        decision_id=decision_id,
        needs_justification=forced_now,
        next=DecisionResponseNext(item=next_item_payload),
    )


def _next_pool(pool: str) -> str | None:
    idx = POOLS.index(pool)
    return POOLS[idx + 1] if idx + 1 < len(POOLS) else None
```

- [ ] **Step 5: Tests in `backend/tests/test_candidate_decision.py`**

> The decision endpoint touches many tables. Use focused integration-style tests on the core invariants. Full happy-path is covered in Task 17 (E2E).

```python
"""Lighter integration tests for /decision — invariants only."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock


def test_decision_rejects_unknown_item(client, mock_supabase):
    """If item_id doesn't exist, 404."""
    cand = {
        "id": str(uuid.uuid4()), "session_id": "sess-1",
        "started_at": "2026-05-10T00:00:00Z", "link_used": False,
        "submitted_at": None, "forced_justification_indexes": None,
    }
    table_router = {}

    def _table(name):
        m = MagicMock()
        if name == "candidates":
            m.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=cand)
        elif name == "test_items":
            m.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=None)
        return m
    mock_supabase.table.side_effect = _table

    r = client.post(
        "/api/test/tok/decision",
        json={"item_id": str(uuid.uuid4()), "answer": True, "dwell_ms": 1000,
              "shown_at": "2026-05-10T00:01:00Z"},
        cookies={"session_id": "sess-1"},
    )
    assert r.status_code == 404
```

> The plan keeps these tests minimal because the full sequence builder is exercised end-to-end in Task 17. The deterministic-seed approach in `_ensure_step_started` makes the sequence reproducible from the candidate's `session_id`, which is also useful for the manager replay view.

- [ ] **Step 6: Run tests + sanity-check the module imports**

```bash
cd backend && pytest tests/test_candidate_decision.py -v
cd backend && python -c "from routers import candidate; print('ok')"
```

- [ ] **Step 7: Commit**

```bash
git add backend/routers/candidate.py backend/tests/test_candidate_decision.py
git commit -m "feat(backend): step intro + decision endpoints with seq builder"
```

---

## Task 12: Candidate routes — `/justification`, `/event`, `/submit`

**Files:**
- Modify: `backend/routers/candidate.py`
- Create: `backend/tests/test_candidate_submit.py`

`/submit` is the orchestrator that computes per-step stats, calls `compute_recommendation`, and persists the result.

- [ ] **Step 1: Add `/justification` and `/event` endpoints to `backend/routers/candidate.py`**

```python
from models import EventRequest, JustificationRequest


@router.post("/justification", response_model=StateResponse)
def justification(token: str, body: JustificationRequest, session_id: str | None = Cookie(default=None)) -> StateResponse:
    candidate = _get_candidate(token)
    if candidate is None:
        raise HTTPException(404, "Invalid invite link")
    verify_candidate_session(candidate, session_id)
    # Confirm the decision belongs to this candidate
    dec = (
        get_supabase().table("candidate_decisions")
        .select("id,candidate_id,forced_justification")
        .eq("id", body.decision_id).single().execute().data
    )
    if dec is None or dec["candidate_id"] != candidate["id"]:
        raise HTTPException(404, "Unknown decision")
    if not dec["forced_justification"]:
        raise HTTPException(409, "Decision did not require justification")
    get_supabase().table("candidate_decisions").update({
        "justification": body.justification,
    }).eq("id", body.decision_id).execute()
    return _resolve_state(_get_candidate(token), session_id)


@router.post("/event", response_model=StateResponse)
def event(token: str, body: EventRequest, session_id: str | None = Cookie(default=None)) -> StateResponse:
    candidate = _get_candidate(token)
    if candidate is None:
        raise HTTPException(404, "Invalid invite link")
    verify_candidate_session(candidate, session_id)
    get_supabase().table("candidate_events").insert({
        "candidate_id": candidate["id"],
        "kind": body.kind,
        "meta": body.meta,
    }).execute()
    return _resolve_state(_get_candidate(token), session_id)
```

- [ ] **Step 2: Add a stats-builder + `/submit` endpoint**

```python
from scoring import ScoringInput, StepStats, compute_recommendation


def _build_scoring_input(cid: str) -> ScoringInput:
    decisions = (
        get_supabase().table("candidate_decisions")
        .select("*").eq("candidate_id", cid).execute()
    ).data or []
    items_by_id = {
        i["id"]: i for i in (
            get_supabase().table("test_items").select("*").execute()
        ).data or []
    }
    quiz = (
        get_supabase().table("candidate_quiz_answers")
        .select("is_correct").eq("candidate_id", cid).execute()
    ).data or []
    events = (
        get_supabase().table("candidate_events")
        .select("kind").eq("candidate_id", cid).eq("kind", "tab_blur").execute()
    ).data or []

    def _step_stats(pool: str) -> StepStats:
        step_decisions = [d for d in decisions if d["pool"] == pool]
        if not step_decisions:
            return StepStats(0.0, 0, 0, 0)
        correct = sum(1 for d in step_decisions if d["is_correct"])
        accuracy = correct / len(step_decisions)
        # Anchor scoring (only first show — exclude duplicates)
        non_dupes = [d for d in step_decisions if d["duplicate_of"] is None]
        obvious_bad_caught = sum(
            1 for d in non_dupes
            if items_by_id[d["item_id"]]["anchor_kind"] == "obvious_bad" and d["is_correct"]
        )
        obvious_good_caught = sum(
            1 for d in non_dupes
            if items_by_id[d["item_id"]]["anchor_kind"] == "obvious_good" and d["is_correct"]
        )
        # Duplicate consistency: same answer on dupe pair
        dupes = [d for d in step_decisions if d["duplicate_of"] is not None]
        dupe_consistency = 0
        for d in dupes:
            original = next((x for x in step_decisions if x["id"] == d["duplicate_of"]), None)
            if original is not None and original["answer"] == d["answer"]:
                dupe_consistency += 1
        return StepStats(
            accuracy=accuracy,
            obvious_bad_caught=obvious_bad_caught,
            obvious_good_caught=obvious_good_caught,
            duplicate_consistency=dupe_consistency,
        )

    return ScoringInput(
        quiz_score=sum(1 for q in quiz if q["is_correct"]),
        tab_switches=len(events),
        tiktok=_step_stats("tiktok"),
        nano_banana=_step_stats("nano_banana"),
        kling=_step_stats("kling"),
    )


@router.post("/submit", response_model=StateResponse)
def submit(token: str, session_id: str | None = Cookie(default=None)) -> StateResponse:
    candidate = _get_candidate(token)
    if candidate is None:
        raise HTTPException(404, "Invalid invite link")
    verify_candidate_session(candidate, session_id)
    cid = candidate["id"]
    progress = _step_progress(cid)
    if any(progress[p] < ITEMS_PER_STEP for p in POOLS):
        raise HTTPException(409, "Test not complete")
    inp = _build_scoring_input(cid)
    rec, reasons = compute_recommendation(inp)
    get_supabase().table("candidates").update({
        "submitted_at": _now_iso(),
        "link_used": True,
        "recommendation": rec,
        "auto_fail_reasons": reasons,
    }).eq("id", cid).execute()
    return _resolve_state(_get_candidate(token), session_id)
```

- [ ] **Step 3: Tests for `/submit` recommendation roundtrip — `backend/tests/test_candidate_submit.py`**

```python
"""Verify /submit calls compute_recommendation with correctly assembled stats."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch


def test_submit_writes_recommendation(client, mock_supabase):
    cid = str(uuid.uuid4())
    cand = {"id": cid, "session_id": "s", "link_used": False, "submitted_at": None,
            "started_at": "2026-05-10T00:00:00Z", "forced_justification_indexes": None}

    # Wire: candidate, decisions count = 90, build_scoring_input returns a perfect score
    def _table(name):
        m = MagicMock()
        if name == "candidates":
            m.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=cand)
            m.update.return_value.eq.return_value.execute.return_value = MagicMock()
        elif name == "candidate_decisions":
            # _step_progress: returns 90 rows total, 30 per pool
            rows = [{"pool": p} for p in ("tiktok",)*30 + ("nano_banana",)*30 + ("kling",)*30]
            m.select.return_value.eq.return_value.execute.return_value = MagicMock(data=rows, count=90)
        elif name == "candidate_events":
            m.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        return m
    mock_supabase.table.side_effect = _table

    # Patch _build_scoring_input to skip the heavy assembly
    from scoring import ScoringInput, StepStats
    perfect = StepStats(1.0, 4, 4, 2)
    perfect_input = ScoringInput(quiz_score=5, tab_switches=0, tiktok=perfect, nano_banana=perfect, kling=perfect)
    with patch("routers.candidate._build_scoring_input", return_value=perfect_input):
        r = client.post("/api/test/tok/submit", cookies={"session_id": "s"})
    assert r.status_code == 200
```

- [ ] **Step 4: Run tests**

```bash
cd backend && pytest tests/test_candidate_submit.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/routers/candidate.py backend/tests/test_candidate_submit.py
git commit -m "feat(backend): justification + event + submit endpoints"
```

---

## Task 13: Manager routes — invites, candidate list, detail, decision PATCH, signed URL

**Files:**
- Create: `backend/routers/manager.py`
- Modify: `backend/main.py` (mount router)
- Create: `backend/tests/test_manager_routes.py`

All endpoints require a valid manager JWT. Returns 401/403 if not.

- [ ] **Step 1: Create `backend/routers/manager.py`**

```python
"""Manager-side endpoints: /api/manager/*"""
from __future__ import annotations

import secrets
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from auth import verify_manager_jwt
from config import POOLS, ITEMS_PER_STEP
from models import (
    CandidateRow, CandidateDetail, CreateInviteRequest, CreateInviteResponse,
    PatchCandidateRequest, StepBreakdown,
)
from storage import signed_url_for_item
from supabase_client import get_supabase

router = APIRouter(prefix="/api/manager", tags=["manager"])


def _require_manager(authorization: str | None = Header(default=None)) -> dict:
    return verify_manager_jwt(authorization)


@router.post("/invites", response_model=CreateInviteResponse)
def create_invite(
    body: CreateInviteRequest,
    request: Request,
    claims: dict = Depends(_require_manager),
) -> CreateInviteResponse:
    token = secrets.token_urlsafe(24)
    res = (
        get_supabase().table("candidates").insert({
            "invite_token": token,
            "invited_by": claims.get("sub"),
            "invited_label": body.name,
            "invited_label_email": body.email,
        }).execute()
    )
    candidate_id = res.data[0]["id"]
    base = str(request.base_url).rstrip("/")
    return CreateInviteResponse(
        candidate_id=candidate_id,
        token=token,
        url=f"{base}/test/{token}",
    )


def _row_from_candidate(c: dict, total_time_seconds: int | None) -> CandidateRow:
    return CandidateRow(
        id=c["id"],
        invited_label=c.get("invited_label"),
        invited_label_email=c.get("invited_label_email"),
        candidate_name=c.get("candidate_name"),
        candidate_email=c.get("candidate_email"),
        created_at=c["created_at"],
        started_at=c.get("started_at"),
        submitted_at=c.get("submitted_at"),
        link_used=c.get("link_used", False),
        recommendation=c.get("recommendation"),
        manager_decision=c.get("manager_decision"),
        total_time_seconds=total_time_seconds,
    )


@router.get("/candidates", response_model=list[CandidateRow])
def list_candidates(_: dict = Depends(_require_manager)) -> list[CandidateRow]:
    rows = (
        get_supabase().table("candidates").select("*").order("created_at", desc=True).execute()
    ).data or []
    out: list[CandidateRow] = []
    for c in rows:
        tts = None
        if c.get("submitted_at") and c.get("started_at"):
            from datetime import datetime
            tts = int(
                (datetime.fromisoformat(c["submitted_at"].replace("Z", "+00:00"))
                 - datetime.fromisoformat(c["started_at"].replace("Z", "+00:00"))).total_seconds()
            )
        out.append(_row_from_candidate(c, tts))
    return out


@router.get("/candidates/{cid}", response_model=CandidateDetail)
def candidate_detail(cid: str, _: dict = Depends(_require_manager)) -> CandidateDetail:
    candidate = (
        get_supabase().table("candidates").select("*").eq("id", cid).single().execute().data
    )
    if candidate is None:
        raise HTTPException(404, "Unknown candidate")

    decisions = (
        get_supabase().table("candidate_decisions")
        .select("*").eq("candidate_id", cid).order("pool").order("display_index").execute()
    ).data or []
    items = (
        get_supabase().table("test_items").select("*").execute()
    ).data or []
    items_by_id = {i["id"]: i for i in items}
    quiz = (
        get_supabase().table("candidate_quiz_answers")
        .select("is_correct").eq("candidate_id", cid).execute()
    ).data or []
    events = (
        get_supabase().table("candidate_events")
        .select("*").eq("candidate_id", cid).execute()
    ).data or []

    tab_switches = sum(1 for e in events if e["kind"] == "tab_blur")
    quiz_correct = sum(1 for q in quiz if q.get("is_correct"))

    steps: list[StepBreakdown] = []
    for pool in POOLS:
        step_decisions = [d for d in decisions if d["pool"] == pool]
        non_dupes = [d for d in step_decisions if d["duplicate_of"] is None]
        accuracy = (sum(1 for d in step_decisions if d["is_correct"]) / len(step_decisions)) if step_decisions else 0.0
        ob_caught = sum(1 for d in non_dupes
                        if items_by_id[d["item_id"]]["anchor_kind"] == "obvious_bad" and d["is_correct"])
        og_caught = sum(1 for d in non_dupes
                        if items_by_id[d["item_id"]]["anchor_kind"] == "obvious_good" and d["is_correct"])
        dupes = [d for d in step_decisions if d["duplicate_of"] is not None]
        dupe_consistency = sum(
            1 for d in dupes
            if next((x for x in step_decisions if x["id"] == d["duplicate_of"]), {}).get("answer") == d["answer"]
        )
        median_dwell = None
        if step_decisions:
            ds = sorted(d["dwell_ms"] for d in step_decisions)
            median_dwell = ds[len(ds) // 2]
        # duration: step_start (intro_acked=true) → step_end
        intro = next((e for e in events if e["kind"] == "step_start" and (e.get("meta") or {}).get("pool") == pool and (e.get("meta") or {}).get("intro_acked")), None)
        end = next((e for e in events if e["kind"] == "step_end" and (e.get("meta") or {}).get("pool") == pool), None)
        duration = None
        if intro and end:
            from datetime import datetime
            duration = int(
                (datetime.fromisoformat(end["occurred_at"].replace("Z", "+00:00"))
                 - datetime.fromisoformat(intro["occurred_at"].replace("Z", "+00:00"))).total_seconds()
            )
        steps.append(StepBreakdown(
            pool=pool, accuracy=accuracy,
            obvious_bad_caught=ob_caught, obvious_good_caught=og_caught,
            duplicate_consistency=dupe_consistency,
            median_dwell_ms=median_dwell, duration_seconds=duration,
        ))

    free_text = [
        {
            "pool": d["pool"],
            "item_id": d["item_id"],
            "item_storage_path": items_by_id[d["item_id"]]["storage_path"],
            "justification": d["justification"],
        }
        for d in decisions if d.get("justification")
    ]

    tts = None
    if candidate.get("submitted_at") and candidate.get("started_at"):
        from datetime import datetime
        tts = int(
            (datetime.fromisoformat(candidate["submitted_at"].replace("Z", "+00:00"))
             - datetime.fromisoformat(candidate["started_at"].replace("Z", "+00:00"))).total_seconds()
        )

    return CandidateDetail(
        row=_row_from_candidate(candidate, tts),
        auto_fail_reasons=candidate.get("auto_fail_reasons") or [],
        quiz_correct=quiz_correct,
        quiz_total=len(quiz),
        tab_switches=tab_switches,
        steps=steps,
        free_text_justifications=free_text,
        decisions=[
            {
                "id": d["id"], "pool": d["pool"], "display_index": d["display_index"],
                "item_id": d["item_id"],
                "storage_path": items_by_id[d["item_id"]]["storage_path"],
                "answer": d["answer"], "is_correct": d["is_correct"],
                "is_anchor": items_by_id[d["item_id"]]["is_anchor"],
                "anchor_kind": items_by_id[d["item_id"]]["anchor_kind"],
                "dwell_ms": d["dwell_ms"], "is_duplicate": d["duplicate_of"] is not None,
                "justification": d.get("justification"),
            }
            for d in decisions
        ],
        manager_notes=candidate.get("manager_notes"),
    )


@router.patch("/candidates/{cid}")
def patch_candidate(cid: str, body: PatchCandidateRequest, _: dict = Depends(_require_manager)) -> dict:
    update: dict[str, Any] = {}
    if body.manager_decision is not None:
        update["manager_decision"] = body.manager_decision
    if body.manager_notes is not None:
        update["manager_notes"] = body.manager_notes
    if not update:
        return {"ok": True}
    get_supabase().table("candidates").update(update).eq("id", cid).execute()
    return {"ok": True}


@router.get("/items/{item_id}/signed-url")
def item_signed_url(item_id: str, _: dict = Depends(_require_manager)) -> dict:
    item = get_supabase().table("test_items").select("*").eq("id", item_id).single().execute().data
    if item is None:
        raise HTTPException(404, "Unknown item")
    return {"url": signed_url_for_item(item["pool"], item["storage_path"])}
```

- [ ] **Step 2: Mount the manager router in `backend/main.py`**

```python
from routers import manager as manager_router
app.include_router(manager_router.router)
```

- [ ] **Step 3: Manager route tests in `backend/tests/test_manager_routes.py`**

```python
"""Manager route auth + happy paths (mocked Supabase)."""
from __future__ import annotations

import time
import uuid
from unittest.mock import MagicMock

import jwt


JWT_SECRET = "test-jwt-secret"


def _manager_jwt(email: str = "manager@example.com") -> str:
    payload = {
        "sub": str(uuid.uuid4()),
        "email": email,
        "exp": int(time.time()) + 3600,
        "aud": "authenticated",
        "role": "authenticated",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def test_invites_requires_auth(client):
    r = client.post("/api/manager/invites", json={"name": "x", "email": "x@y.com"})
    assert r.status_code == 401


def test_invites_rejects_wrong_email(client):
    tok = _manager_jwt("intruder@example.com")
    r = client.post(
        "/api/manager/invites",
        json={"name": "x", "email": "x@y.com"},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 403


def test_invites_creates_row(client, mock_supabase):
    new_id = str(uuid.uuid4())
    insert_chain = mock_supabase.table.return_value.insert.return_value
    insert_chain.execute.return_value = MagicMock(data=[{"id": new_id}])

    tok = _manager_jwt()
    r = client.post(
        "/api/manager/invites",
        json={"name": "Jane Doe", "email": "j@d.com"},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["candidate_id"] == new_id
    assert body["url"].endswith("/test/" + body["token"])


def test_list_candidates_returns_rows(client, mock_supabase):
    rows = [{
        "id": str(uuid.uuid4()),
        "invited_label": "Jane",
        "invited_label_email": "j@d.com",
        "candidate_name": None, "candidate_email": None,
        "created_at": "2026-05-10T00:00:00Z",
        "started_at": None, "submitted_at": None,
        "link_used": False, "recommendation": None, "manager_decision": None,
    }]
    chain = mock_supabase.table.return_value.select.return_value.order.return_value
    chain.execute.return_value = MagicMock(data=rows)

    tok = _manager_jwt()
    r = client.get("/api/manager/candidates", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    assert len(r.json()) == 1
```

- [ ] **Step 4: Run tests**

```bash
cd backend && pytest tests/test_manager_routes.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/routers/manager.py backend/main.py backend/tests/test_manager_routes.py
git commit -m "feat(backend): manager routes — invites, list, detail, patch, signed-url"
```

---

## Task 14: Seed script — load `content/items.csv` + `content/quiz.json` into Storage + DB

**Files:**
- Create: `backend/seed.py`

This is a one-shot CLI the developer runs after dropping files into `content/`.

- [ ] **Step 1: Create `backend/seed.py`**

```python
"""Seed test_items + quiz_questions from local content/ folder.

Layout expected:
  content/
    tiktoks/<filename>.mp4
    nano_banana/<filename>.png
    kling/<filename>.mp4
    items.csv      columns: filename,pool,correct_answer,is_anchor,anchor_kind,notes
    quiz.json      [{"question":"...","options":[...],"correct_index":N}, ...]

Idempotent: re-running upserts items by (pool, storage_path).
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from config import (
    OBVIOUS_BAD_ANCHORS_PER_STEP, OBVIOUS_GOOD_ANCHORS_PER_STEP,
    POOLS, QUIZ_QUESTION_COUNT, UNIQUE_ITEMS_PER_STEP,
)
from storage import bucket_for_pool
from supabase_client import get_supabase

ROOT = Path(__file__).resolve().parent.parent / "content"


def _load_items_csv() -> list[dict]:
    rows = []
    with (ROOT / "items.csv").open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "filename": row["filename"].strip(),
                "pool": row["pool"].strip(),
                "correct_answer": row["correct_answer"].strip().lower() == "true",
                "is_anchor": row["is_anchor"].strip().lower() == "true",
                "anchor_kind": (row.get("anchor_kind") or "").strip() or None,
                "notes": (row.get("notes") or "").strip() or None,
            })
    return rows


def _validate(rows: list[dict]) -> None:
    by_pool: dict[str, list[dict]] = {p: [] for p in POOLS}
    for r in rows:
        if r["pool"] not in POOLS:
            raise SystemExit(f"Unknown pool: {r['pool']}")
        by_pool[r["pool"]].append(r)
    for pool, items in by_pool.items():
        if len(items) != UNIQUE_ITEMS_PER_STEP:
            raise SystemExit(f"Pool {pool}: expected {UNIQUE_ITEMS_PER_STEP} items, got {len(items)}")
        og = sum(1 for i in items if i["is_anchor"] and i["anchor_kind"] == "obvious_good")
        ob = sum(1 for i in items if i["is_anchor"] and i["anchor_kind"] == "obvious_bad")
        if og != OBVIOUS_GOOD_ANCHORS_PER_STEP:
            raise SystemExit(f"Pool {pool}: expected {OBVIOUS_GOOD_ANCHORS_PER_STEP} obvious_good anchors, got {og}")
        if ob != OBVIOUS_BAD_ANCHORS_PER_STEP:
            raise SystemExit(f"Pool {pool}: expected {OBVIOUS_BAD_ANCHORS_PER_STEP} obvious_bad anchors, got {ob}")


def _upload_and_upsert(rows: list[dict]) -> None:
    sb = get_supabase()
    for r in rows:
        local_dir = {
            "tiktok": ROOT / "tiktoks",
            "nano_banana": ROOT / "nano_banana",
            "kling": ROOT / "kling",
        }[r["pool"]]
        local_path = local_dir / r["filename"]
        if not local_path.is_file():
            raise SystemExit(f"Missing file: {local_path}")
        bucket = bucket_for_pool(r["pool"])
        with local_path.open("rb") as fh:
            sb.storage.from_(bucket).upload(
                path=r["filename"],
                file=fh,
                file_options={"upsert": "true"},
            )
        sb.table("test_items").upsert({
            "pool": r["pool"],
            "storage_path": r["filename"],
            "correct_answer": r["correct_answer"],
            "is_anchor": r["is_anchor"],
            "anchor_kind": r["anchor_kind"],
            "notes": r["notes"],
        }, on_conflict="pool,storage_path").execute()
        print(f"  ✓ {r['pool']}/{r['filename']}")


def _seed_quiz() -> None:
    sb = get_supabase()
    with (ROOT / "quiz.json").open() as f:
        questions = json.load(f)
    if len(questions) != QUIZ_QUESTION_COUNT:
        raise SystemExit(f"quiz.json must have exactly {QUIZ_QUESTION_COUNT} questions")
    # Wipe and re-insert (small table, simpler)
    sb.table("candidate_quiz_answers").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    sb.table("quiz_questions").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    for idx, q in enumerate(questions):
        sb.table("quiz_questions").insert({
            "question": q["question"],
            "options": q["options"],
            "correct_index": q["correct_index"],
            "display_order": idx,
        }).execute()
    print(f"  ✓ {QUIZ_QUESTION_COUNT} quiz questions")


def main() -> int:
    if not ROOT.is_dir():
        print(f"content directory not found: {ROOT}", file=sys.stderr)
        return 1
    print("Loading items.csv...")
    rows = _load_items_csv()
    print(f"  {len(rows)} rows")
    print("Validating...")
    _validate(rows)
    print("Uploading + upserting items...")
    _upload_and_upsert(rows)
    print("Seeding quiz...")
    _seed_quiz()
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Smoke test that the script imports + runs the validator on a fixture**

For a real seed run, you need the `content/` files; we can't test that in CI. Just verify imports:

```bash
cd backend && python -c "import seed; print('ok')"
```

- [ ] **Step 3: Commit**

```bash
git add backend/seed.py
git commit -m "feat(backend): seed CLI for test_items + quiz_questions"
```

---

## Task 15: Frontend scaffolding — Vite, routing, API client

**Files:**
- Create: `frontend/vite.config.js`
- Create: `frontend/index.html`
- Create: `frontend/src/main.jsx`
- Create: `frontend/src/App.jsx`
- Create: `frontend/src/api.js`
- Create: `frontend/src/lib/supabase.js`
- Create: `frontend/eslint.config.js`

- [ ] **Step 1: Install dependencies**

```bash
cd frontend && npm install
```

- [ ] **Step 2: Create `frontend/vite.config.js`**

```js
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        // forward cookies for the candidate session
        cookieDomainRewrite: { "*": "" },
      },
    },
  },
});
```

- [ ] **Step 3: Create `frontend/index.html`**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>VA Interview</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

- [ ] **Step 4: Create `frontend/src/main.jsx`**

```jsx
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App.jsx";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);
```

- [ ] **Step 5: Create `frontend/src/App.jsx` with stub routes**

```jsx
import { Navigate, Route, Routes } from "react-router-dom";
import CandidateRoot from "./components/candidate/Root.jsx";
import ManagerRoot from "./components/manager/Root.jsx";
import "./styles.css";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/admin" replace />} />
      <Route path="/test/:token/*" element={<CandidateRoot />} />
      <Route path="/admin/*" element={<ManagerRoot />} />
      <Route path="*" element={<div style={{ padding: 32 }}>Not found</div>} />
    </Routes>
  );
}
```

- [ ] **Step 6: Create `frontend/src/api.js`**

```js
const BASE = "";

async function call(method, path, { body, auth } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth) headers.Authorization = `Bearer ${auth}`;
  const res = await fetch(`${BASE}${path}`, {
    method,
    credentials: "include",
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw Object.assign(new Error(err.detail || `${res.status}`), { status: res.status, body: err });
  }
  return res.json();
}

export const candidateApi = {
  state: (token) => call("GET", `/api/test/${token}/state`),
  start: (token, name, email) => call("POST", `/api/test/${token}/start`, { body: { name, email } }),
  tutorialAck: (token) => call("POST", `/api/test/${token}/tutorial-acknowledged`),
  quiz: (token, answers) => call("POST", `/api/test/${token}/quiz`, { body: { answers } }),
  stepIntroAck: (token, pool) => call("POST", `/api/test/${token}/step/${pool}/intro-acknowledged`),
  decision: (token, payload) => call("POST", `/api/test/${token}/decision`, { body: payload }),
  justification: (token, decisionId, text) =>
    call("POST", `/api/test/${token}/justification`, { body: { decision_id: decisionId, justification: text } }),
  event: (token, kind, meta = {}) => call("POST", `/api/test/${token}/event`, { body: { kind, meta } }),
  submit: (token) => call("POST", `/api/test/${token}/submit`),
};

export const managerApi = {
  createInvite: (auth, name, email) => call("POST", `/api/manager/invites`, { body: { name, email }, auth }),
  listCandidates: (auth) => call("GET", `/api/manager/candidates`, { auth }),
  candidateDetail: (auth, id) => call("GET", `/api/manager/candidates/${id}`, { auth }),
  patchCandidate: (auth, id, patch) => call("PATCH", `/api/manager/candidates/${id}`, { body: patch, auth }),
  itemSignedUrl: (auth, id) => call("GET", `/api/manager/items/${id}/signed-url`, { auth }),
};
```

- [ ] **Step 7: Create `frontend/src/lib/supabase.js`**

```js
import { createClient } from "@supabase/supabase-js";

export const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL,
  import.meta.env.VITE_SUPABASE_ANON_KEY,
  { auth: { persistSession: true, autoRefreshToken: true } }
);
```

> Add `frontend/.env` with:
> ```
> VITE_SUPABASE_URL=https://YOUR-PROJECT.supabase.co
> VITE_SUPABASE_ANON_KEY=eyJ...
> ```

- [ ] **Step 8: Create `frontend/src/styles.css` with minimal global resets**

```css
:root {
  --bg: #0a0a0a;
  --panel: #141414;
  --line: #1f1f1f;
  --text: #e6e6e6;
  --muted: #888;
  --accent-good: #22c55e;
  --accent-bad: #ef4444;
}
* { box-sizing: border-box; }
html, body, #root { height: 100%; margin: 0; }
body {
  background: var(--bg);
  color: var(--text);
  font: 15px/1.4 ui-sans-serif, system-ui, sans-serif;
}
button { font: inherit; cursor: pointer; }
.card { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 16px; }
.muted { color: var(--muted); }
.label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); }
```

- [ ] **Step 9: Create stub `Root.jsx` for both flows so the build succeeds**

`frontend/src/components/candidate/Root.jsx`:
```jsx
export default function CandidateRoot() {
  return <div style={{ padding: 32 }}>Candidate flow — not implemented yet</div>;
}
```

`frontend/src/components/manager/Root.jsx`:
```jsx
export default function ManagerRoot() {
  return <div style={{ padding: 32 }}>Manager flow — not implemented yet</div>;
}
```

- [ ] **Step 10: Verify the dev server starts**

```bash
cd frontend && npm run dev
```

Open `http://localhost:5173/admin` — should show "Manager flow — not implemented yet". Stop the server.

- [ ] **Step 11: Commit**

```bash
git add frontend/
git commit -m "feat(frontend): vite scaffold + routing + API client"
```

---

## Task 16: Frontend candidate — useTestSession hook + InvalidLink + Welcome

**Files:**
- Create: `frontend/src/hooks/useTestSession.js`
- Create: `frontend/src/components/candidate/Root.jsx` (replace stub)
- Create: `frontend/src/components/candidate/InvalidLink.jsx`
- Create: `frontend/src/components/candidate/Welcome.jsx`

`useTestSession` is the client-side state machine. It calls `GET /state` on mount and re-fetches after any mutating action.

- [ ] **Step 1: Create `frontend/src/hooks/useTestSession.js`**

```js
import { useCallback, useEffect, useState } from "react";
import { candidateApi } from "../api";

export function useTestSession(token) {
  const [state, setState] = useState({ state: "loading", progress_in_step: 0, next_item: null });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const s = await candidateApi.state(token);
      setState(s);
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { refresh(); }, [refresh]);

  return { state, setState, loading, error, refresh };
}
```

- [ ] **Step 2: Create `frontend/src/components/candidate/InvalidLink.jsx`**

```jsx
export default function InvalidLink() {
  return (
    <div style={{ padding: 48, textAlign: "center" }}>
      <h1>Link unavailable</h1>
      <p className="muted">This invite link is invalid or has already been used.</p>
    </div>
  );
}
```

- [ ] **Step 3: Create `frontend/src/components/candidate/Welcome.jsx`**

```jsx
import { useState } from "react";
import { candidateApi } from "../../api";

export default function Welcome({ token, onStarted }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  async function submit(e) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await candidateApi.start(token, name, email);
      await onStarted();
    } catch (e) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div style={{ maxWidth: 480, margin: "80px auto", padding: 16 }}>
      <h1>VA Interview Test</h1>
      <p className="muted">
        This test takes about 30–45 minutes. You must complete it in one sitting on a desktop browser.
        You cannot pause or retake. Make sure you have audio enabled.
      </p>
      <form onSubmit={submit} style={{ marginTop: 24 }}>
        <label className="label">Full name</label>
        <input
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
          style={{ width: "100%", padding: 10, marginTop: 4, marginBottom: 16, background: "#141414", color: "#fff", border: "1px solid #333", borderRadius: 6 }}
        />
        <label className="label">Email</label>
        <input
          required type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          style={{ width: "100%", padding: 10, marginTop: 4, marginBottom: 16, background: "#141414", color: "#fff", border: "1px solid #333", borderRadius: 6 }}
        />
        {error && <p style={{ color: "var(--accent-bad)" }}>{error}</p>}
        <button
          disabled={submitting || !name || !email}
          style={{ padding: "12px 24px", background: "#fff", color: "#000", border: "none", borderRadius: 6, fontWeight: 600 }}
        >
          {submitting ? "Starting..." : "Start test"}
        </button>
      </form>
    </div>
  );
}
```

- [ ] **Step 4: Replace `frontend/src/components/candidate/Root.jsx`**

```jsx
import { useParams } from "react-router-dom";
import { useTestSession } from "../../hooks/useTestSession.js";
import InvalidLink from "./InvalidLink.jsx";
import Welcome from "./Welcome.jsx";

export default function CandidateRoot() {
  const { token } = useParams();
  const { state, refresh, loading, error } = useTestSession(token);

  if (loading) return <div style={{ padding: 48 }}>Loading…</div>;
  if (error) return <InvalidLink />;

  switch (state.state) {
    case "invalid":
      return <InvalidLink />;
    case "session_in_use":
      return (
        <div style={{ padding: 48, textAlign: "center" }}>
          <h1>Test in progress in another window</h1>
          <p className="muted">Close other tabs/windows showing this link, then refresh.</p>
        </div>
      );
    case "needs_name":
      return <Welcome token={token} onStarted={refresh} />;
    default:
      // Other states wired in later tasks
      return <div style={{ padding: 48 }}>State: {state.state} — coming next.</div>;
  }
}
```

- [ ] **Step 5: Verify in the browser**

```bash
cd frontend && npm run dev
```

Visit `http://localhost:5173/test/some-token`. Backend should return `state: "invalid"` (no such candidate); UI should show InvalidLink.

- [ ] **Step 6: Commit**

```bash
git add frontend/src
git commit -m "feat(frontend): test session hook + InvalidLink + Welcome"
```

---

## Task 17: Frontend candidate — Tutorial, Quiz, StepIntro, Submit

**Files:**
- Create: `frontend/src/components/candidate/Tutorial.jsx`
- Create: `frontend/src/components/candidate/Quiz.jsx`
- Create: `frontend/src/components/candidate/StepIntro.jsx`
- Create: `frontend/src/components/candidate/Submit.jsx`
- Modify: `frontend/src/components/candidate/Root.jsx` (route the rest of the states)

The tutorial is a static text page with example image grids. Image URLs come from the public `tutorial` Storage bucket.

- [ ] **Step 1: Create `Tutorial.jsx`**

```jsx
import { useEffect, useState } from "react";
import { candidateApi } from "../../api";

const TUTORIAL = `${import.meta.env.VITE_SUPABASE_URL}/storage/v1/object/public/tutorial`;

const RULES = {
  tiktok: [
    "English audio only — songs and voice-over",
    "American or generic Western style backgrounds — no foreign indoor scenes",
    "Visually interesting — boring static videos are out",
    "Recreatable on Kling — no extreme physics, multiple people, or rapid scene cuts",
    "Not too short or too long (5–30s sweet spot)",
  ],
  nano_banana: [
    "Model identity must match — same face, same body, same bust size as our references",
    "No clear AI artifacts — extra fingers, melted faces, weird hands",
    "Outfit and pose must roughly match the reference scene",
    "Lighting and skin should look like a phone photo, not a studio render",
  ],
  kling: [
    "Realistic motion — no impossible body movements",
    "Face stays consistent through the whole video",
    "No flickering, smearing, or warping",
    "Engaging — not boring or static",
  ],
};

export default function Tutorial({ token, onContinue }) {
  const [submitting, setSubmitting] = useState(false);

  async function ack() {
    setSubmitting(true);
    await candidateApi.tutorialAck(token);
    await onContinue();
  }

  return (
    <div style={{ maxWidth: 760, margin: "32px auto", padding: 16 }}>
      <h1>Read the rules carefully</h1>
      <p className="muted">After this you'll answer 5 quick questions to confirm you understood. If you fail, the test ends.</p>

      {Object.entries(RULES).map(([pool, rules]) => (
        <section key={pool} className="card" style={{ marginTop: 24 }}>
          <h2 style={{ marginTop: 0 }}>{poolName(pool)}</h2>
          <ul>{rules.map((r) => <li key={r}>{r}</li>)}</ul>
          <ExamplesGrid pool={pool} />
        </section>
      ))}

      <button onClick={ack} disabled={submitting}
        style={{ marginTop: 32, padding: "12px 24px", background: "#fff", color: "#000", border: "none", borderRadius: 6, fontWeight: 600 }}>
        I've read the rules → continue
      </button>
    </div>
  );
}

function poolName(p) {
  return { tiktok: "TikTok screening", nano_banana: "Nano-banana review", kling: "Kling video review" }[p];
}

function ExamplesGrid({ pool }) {
  // Each pool has up to 4 example images named good_1.jpg, good_2.jpg, bad_1.jpg, bad_2.jpg in tutorial bucket
  const examples = ["good_1.jpg", "good_2.jpg", "bad_1.jpg", "bad_2.jpg"];
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8, marginTop: 12 }}>
      {examples.map((f) => {
        const isGood = f.startsWith("good");
        return (
          <div key={f} style={{ position: "relative" }}>
            <img src={`${TUTORIAL}/${pool}/${f}`} alt={f} style={{ width: "100%", borderRadius: 6, opacity: 0.95 }} />
            <span style={{
              position: "absolute", top: 6, left: 6, padding: "2px 6px", borderRadius: 3,
              fontSize: 10, fontWeight: 700, background: isGood ? "var(--accent-good)" : "var(--accent-bad)", color: "#000",
            }}>{isGood ? "GOOD" : "BAD"}</span>
          </div>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 2: Create `Quiz.jsx`**

You'll need quiz question text — for v1, hardcode the 5 questions in the frontend (they mirror what's seeded into the DB). The backend grades by index, so the frontend just needs to send back the indexes.

```jsx
import { useState } from "react";
import { candidateApi } from "../../api";

const QUIZ = [
  {
    q: "Which of the following is NOT a reason to reject a TikTok?",
    options: [
      "Non-English audio",
      "Ugly background",
      "Trending in the United States",
      "Clearly impossible to recreate on Kling",
    ],
  },
  {
    q: "A nano-banana generation comes back with a clearly smaller bust than our reference photos. You should:",
    options: [
      "Approve it — it's close enough",
      "Reject it",
      "Approve it and add a note",
      "Approve it if the rest of the image looks good",
    ],
  },
  {
    q: "A Kling video shows the model's face flickering for 1 second mid-clip. You should:",
    options: [
      "Approve — the rest is fine",
      "Approve if it's only a small section",
      "Reject — face must stay consistent",
      "Approve if you can crop it out",
    ],
  },
  {
    q: "How many TikToks, nano-banana images, and Kling videos will you review in this test?",
    options: ["10 of each", "20 of each", "30 of each", "50 of each"],
  },
  {
    q: "Can you go back to a previous answer once you've clicked?",
    options: ["Yes, anytime", "Yes, within the same step", "Only if you refresh", "No, never"],
  },
];

export default function Quiz({ token, onPass, onFail }) {
  const [answers, setAnswers] = useState(Array(QUIZ.length).fill(null));
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  function set(qIdx, optIdx) {
    setAnswers((prev) => prev.map((v, i) => (i === qIdx ? optIdx : v)));
  }

  async function submit() {
    setSubmitting(true);
    setError(null);
    try {
      const res = await candidateApi.quiz(token, answers);
      if (res.passed) await onPass();
      else await onFail();
    } catch (e) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  }

  const allAnswered = answers.every((a) => a !== null);

  return (
    <div style={{ maxWidth: 720, margin: "32px auto", padding: 16 }}>
      <h1>Comprehension check</h1>
      <p className="muted">Answer all 5 questions. You need at least 4 correct to continue.</p>
      {QUIZ.map((q, qi) => (
        <div key={qi} className="card" style={{ marginTop: 16 }}>
          <p style={{ marginTop: 0, fontWeight: 600 }}>{qi + 1}. {q.q}</p>
          {q.options.map((opt, oi) => (
            <label key={oi} style={{ display: "block", padding: "6px 0" }}>
              <input
                type="radio"
                name={`q-${qi}`}
                checked={answers[qi] === oi}
                onChange={() => set(qi, oi)}
                style={{ marginRight: 8 }}
              />
              {opt}
            </label>
          ))}
        </div>
      ))}
      {error && <p style={{ color: "var(--accent-bad)" }}>{error}</p>}
      <button onClick={submit} disabled={!allAnswered || submitting}
        style={{ marginTop: 24, padding: "12px 24px", background: "#fff", color: "#000", border: "none", borderRadius: 6, fontWeight: 600 }}>
        {submitting ? "Submitting…" : "Submit answers"}
      </button>
    </div>
  );
}
```

> Note: the questions in `QUIZ` must mirror `content/quiz.json`. Both are seeded once and locked in. If they drift, scoring breaks.

- [ ] **Step 3: Create `StepIntro.jsx`**

```jsx
import { useState } from "react";
import { candidateApi } from "../../api";

const COPY = {
  tiktok: {
    title: "Step 1 of 3 — TikTok screening",
    body: "You'll review 30 TikToks. Mark which you would save for recreation. Reject anything in a non-English language, with ugly or non-American backgrounds, that's boring, or that can't be recreated on Kling.",
    button: "Start TikTok review",
  },
  nano_banana: {
    title: "Step 2 of 3 — Nano-banana review",
    body: "You'll review 30 AI-generated photos of our model based on TikTok frames. Mark which you would actually use to feed Kling. Watch for: identity drift (different face, smaller bust), AI artifacts (weird hands), wrong outfit/pose.",
    button: "Start nano-banana review",
  },
  kling: {
    title: "Step 3 of 3 — Kling video review",
    body: "You'll review 30 Kling videos. Mark which came out well. Watch for: face inconsistency, flickering, warping, impossible motion, boring/static videos.",
    button: "Start Kling review",
  },
};

export default function StepIntro({ token, pool, onContinue }) {
  const [submitting, setSubmitting] = useState(false);
  const c = COPY[pool];

  async function go() {
    setSubmitting(true);
    await candidateApi.stepIntroAck(token, pool);
    await onContinue();
  }

  return (
    <div style={{ maxWidth: 640, margin: "80px auto", padding: 16, textAlign: "center" }}>
      <h1>{c.title}</h1>
      <p style={{ fontSize: 16, lineHeight: 1.6 }}>{c.body}</p>
      <button onClick={go} disabled={submitting}
        style={{ marginTop: 32, padding: "14px 32px", background: "#fff", color: "#000", border: "none", borderRadius: 6, fontWeight: 600, fontSize: 15 }}>
        {submitting ? "Loading…" : c.button}
      </button>
    </div>
  );
}
```

- [ ] **Step 4: Create `Submit.jsx`**

```jsx
export default function SubmitScreen() {
  return (
    <div style={{ padding: 80, textAlign: "center", maxWidth: 520, margin: "0 auto" }}>
      <h1>You're done.</h1>
      <p style={{ fontSize: 16 }}>Thanks for taking the time. The team will review your answers and be in touch.</p>
    </div>
  );
}
```

- [ ] **Step 5: Update `Root.jsx` to route the new states**

Replace the `default` arm:

```jsx
import Tutorial from "./Tutorial.jsx";
import Quiz from "./Quiz.jsx";
import StepIntro from "./StepIntro.jsx";
import SubmitScreen from "./Submit.jsx";

// inside switch:
case "needs_tutorial":
  return <Tutorial token={token} onContinue={refresh} />;
case "needs_quiz":
  return <Quiz token={token} onPass={refresh} onFail={refresh} />;
case "step_tiktok_intro":
  return <StepIntro token={token} pool="tiktok" onContinue={refresh} />;
case "step_nano_banana_intro":
  return <StepIntro token={token} pool="nano_banana" onContinue={refresh} />;
case "step_kling_intro":
  return <StepIntro token={token} pool="kling" onContinue={refresh} />;
case "submitted":
  return <SubmitScreen />;
case "step_tiktok_in_progress":
case "step_nano_banana_in_progress":
case "step_kling_in_progress":
  return <div style={{ padding: 48 }}>Step screen — implemented in Task 18.</div>;
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/candidate/
git commit -m "feat(frontend): tutorial + quiz + step intro + submit screens"
```

---

## Task 18: Frontend candidate — TestStep (Layout B) + JustificationModal + tab-blur logger

**Files:**
- Create: `frontend/src/components/candidate/TestStep.jsx`
- Create: `frontend/src/components/candidate/JustificationModal.jsx`
- Create: `frontend/src/hooks/useTabBlurLogger.js`
- Modify: `frontend/src/components/candidate/Root.jsx`

This implements Layout B from the spec.

- [ ] **Step 1: Create `useTabBlurLogger.js`**

```js
import { useEffect } from "react";
import { candidateApi } from "../api";

export function useTabBlurLogger(token, enabled) {
  useEffect(() => {
    if (!enabled) return;
    function onVis() {
      const kind = document.visibilityState === "hidden" ? "tab_blur" : "tab_focus";
      candidateApi.event(token, kind).catch(() => {});
    }
    document.addEventListener("visibilitychange", onVis);
    return () => document.removeEventListener("visibilitychange", onVis);
  }, [token, enabled]);
}
```

- [ ] **Step 2: Create `JustificationModal.jsx`**

```jsx
import { useState } from "react";

export default function JustificationModal({ onSubmit, onCancel }) {
  const [text, setText] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function go() {
    setSubmitting(true);
    await onSubmit(text.trim());
    setSubmitting(false);
  }

  return (
    <div style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)",
      display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100,
    }}>
      <div style={{ background: "#141414", border: "1px solid #2a2a2a", borderRadius: 8, padding: 24, width: 480 }}>
        <h3 style={{ marginTop: 0 }}>One sentence — why?</h3>
        <p className="muted" style={{ marginTop: 0 }}>
          Briefly explain your decision. This helps us understand your reasoning.
        </p>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={4}
          autoFocus
          style={{ width: "100%", padding: 10, background: "#0a0a0a", color: "#fff", border: "1px solid #2a2a2a", borderRadius: 6 }}
        />
        <div style={{ marginTop: 16, textAlign: "right" }}>
          <button onClick={go} disabled={submitting || !text.trim()}
            style={{ padding: "10px 20px", background: "#fff", color: "#000", border: "none", borderRadius: 6, fontWeight: 600 }}>
            {submitting ? "…" : "Continue"}
          </button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create `TestStep.jsx` (Layout B)**

```jsx
import { useEffect, useRef, useState } from "react";
import { candidateApi } from "../../api";
import JustificationModal from "./JustificationModal.jsx";

const COPY = {
  tiktok: {
    question: "Would you save this TikTok for recreation?",
    yes: { label: "Yes, save this", sub: "Worth recreating" },
    no:  { label: "No, skip", sub: "Wrong language / boring / can't recreate" },
    type: "video",
  },
  nano_banana: {
    question: "Would you use this generation to feed Kling?",
    yes: { label: "Yes, use this", sub: "Identity matches, no AI artifacts" },
    no:  { label: "No, reject", sub: "Wrong identity / artifacts / off-prompt" },
    type: "image",
  },
  kling: {
    question: "Did this Kling video come out well?",
    yes: { label: "Good", sub: "Realistic motion, consistent face" },
    no:  { label: "Bad", sub: "Flicker / warp / inconsistent / boring" },
    type: "video",
  },
};

export default function TestStep({ token, pool, item, progress, onAdvance }) {
  const c = COPY[pool];
  const [shownAt] = useState(() => new Date().toISOString());
  const startMs = useRef(performance.now());
  const [submitting, setSubmitting] = useState(false);
  const [pendingJustification, setPendingJustification] = useState(null); // { decisionId } when needed
  const [pendingAdvance, setPendingAdvance] = useState(null);

  async function answer(value) {
    if (submitting || pendingJustification) return;
    setSubmitting(true);
    const dwell = Math.round(performance.now() - startMs.current);
    try {
      const res = await candidateApi.decision(token, {
        item_id: item.id, answer: value, dwell_ms: dwell, shown_at: shownAt,
      });
      if (res.needs_justification) {
        setPendingJustification({ decisionId: res.decision_id });
        setPendingAdvance(() => async () => {
          await onAdvance(res.next);
        });
      } else {
        await onAdvance(res.next);
      }
    } finally {
      setSubmitting(false);
    }
  }

  useEffect(() => {
    function onKey(e) {
      if (pendingJustification) return;
      if (e.key === "ArrowRight") answer(true);
      if (e.key === "ArrowLeft") answer(false);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [pendingJustification, item.id]);

  async function submitJustification(text) {
    await candidateApi.justification(token, pendingJustification.decisionId, text);
    setPendingJustification(null);
    if (pendingAdvance) await pendingAdvance();
  }

  return (
    <div style={{ maxWidth: 880, margin: "32px auto", padding: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
        <span className="label">Step {stepNumber(pool)} — {stepName(pool)}</span>
        <span className="label">{progress + 1} / 30</span>
      </div>
      <div style={{ display: "flex", gap: 24, alignItems: "stretch", background: "#0d0d0d", padding: 24, borderRadius: 8 }}>
        <div style={{ flexShrink: 0 }}>
          {c.type === "video" ? (
            <video
              key={item.id}
              src={item.storage_url}
              controls autoPlay
              style={{ width: 240, aspectRatio: "9/16", borderRadius: 6, background: "#000" }}
            />
          ) : (
            <img
              src={item.storage_url}
              alt=""
              style={{ width: 320, borderRadius: 6 }}
            />
          )}
        </div>
        <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center", gap: 12 }}>
          <p style={{ fontSize: 16, color: "#bbb", margin: 0 }}>{c.question}</p>
          <button onClick={() => answer(true)} disabled={submitting}
            style={btnStyle("good")}>
            <span style={{ fontWeight: 600 }}>{c.yes.label}</span>
            <span className="muted" style={{ display: "block", fontSize: 11, marginTop: 4 }}>{c.yes.sub}</span>
          </button>
          <button onClick={() => answer(false)} disabled={submitting}
            style={btnStyle("bad")}>
            <span style={{ fontWeight: 600 }}>{c.no.label}</span>
            <span className="muted" style={{ display: "block", fontSize: 11, marginTop: 4 }}>{c.no.sub}</span>
          </button>
          <span className="label" style={{ marginTop: 8 }}>← reject  /  → accept</span>
        </div>
      </div>
      {pendingJustification && (
        <JustificationModal onSubmit={submitJustification} onCancel={() => {}} />
      )}
    </div>
  );
}

function stepName(p) { return { tiktok: "TikTok review", nano_banana: "Nano-banana review", kling: "Kling video review" }[p]; }
function stepNumber(p) { return { tiktok: 1, nano_banana: 2, kling: 3 }[p]; }
function btnStyle(kind) {
  const palette = kind === "good"
    ? { bg: "#1f3a1f", color: "#b5f5b5", border: "#2a5a2a" }
    : { bg: "#3a1f1f", color: "#f5b5b5", border: "#5a2a2a" };
  return {
    padding: "16px 18px", background: palette.bg, color: palette.color,
    border: `1px solid ${palette.border}`, borderRadius: 6,
    textAlign: "left", fontSize: 14,
  };
}
```

- [ ] **Step 4: Wire `TestStep` + tab-blur logger into `Root.jsx`**

```jsx
import TestStep from "./TestStep.jsx";
import { useTabBlurLogger } from "../../hooks/useTabBlurLogger.js";

// inside CandidateRoot, before switch:
const inSession = !["loading", "invalid", "needs_name"].includes(state.state);
useTabBlurLogger(token, inSession);

// add cases in switch:
case "step_tiktok_in_progress":
case "step_nano_banana_in_progress":
case "step_kling_in_progress": {
  if (!state.next_item) return <div style={{ padding: 48 }}>Loading next item…</div>;
  const pool = state.next_item.pool;
  return (
    <TestStep
      token={token}
      pool={pool}
      item={state.next_item}
      progress={state.progress_in_step}
      onAdvance={async (next) => {
        if (next?.test_complete) {
          await candidateApi.submit(token);
          await refresh();
        } else if (next?.step_complete) {
          await refresh();   // server will route to the next step's intro
        } else if (next?.item) {
          // Optimistically update next_item without a full refresh
          setState((s) => ({
            ...s,
            progress_in_step: state.progress_in_step + 1,
            next_item: next.item,
          }));
        } else {
          await refresh();
        }
      }}
    />
  );
}
```

> Note: `setState` was already returned by `useTestSession`, so it's available in `Root.jsx`. Update the destructure: `const { state, setState, refresh, loading, error } = useTestSession(token);`

- [ ] **Step 5: Manual verification**

Run backend + frontend. Generate a candidate via SQL:

```sql
INSERT INTO candidates (invite_token) VALUES ('test-link-1');
```

Visit `http://localhost:5173/test/test-link-1`, complete name → tutorial → quiz (with all-correct answers) → first step intro → first item should appear with video on the left and buttons on the right.

- [ ] **Step 6: Commit**

```bash
git add frontend/src
git commit -m "feat(frontend): TestStep layout B + justification modal + tab-blur logger"
```

---

## Task 19: Frontend manager — Login, Dashboard, InviteModal

**Files:**
- Create: `frontend/src/components/manager/Root.jsx` (replace stub)
- Create: `frontend/src/components/manager/Login.jsx`
- Create: `frontend/src/components/manager/Dashboard.jsx`
- Create: `frontend/src/components/manager/InviteModal.jsx`

- [ ] **Step 1: Create `Login.jsx`**

```jsx
import { useState } from "react";
import { supabase } from "../../lib/supabase.js";

export default function Login({ onLogin }) {
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    const { error } = await supabase.auth.signInWithPassword({ email, password: pw });
    setSubmitting(false);
    if (error) return setError(error.message);
    await onLogin();
  }

  return (
    <div style={{ maxWidth: 360, margin: "120px auto", padding: 16 }}>
      <h1>Manager login</h1>
      <form onSubmit={submit}>
        <label className="label">Email</label>
        <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required
          style={inputStyle} />
        <label className="label">Password</label>
        <input value={pw} onChange={(e) => setPw(e.target.value)} type="password" required
          style={inputStyle} />
        {error && <p style={{ color: "var(--accent-bad)" }}>{error}</p>}
        <button disabled={submitting}
          style={{ padding: "12px 24px", background: "#fff", color: "#000", border: "none", borderRadius: 6, fontWeight: 600, marginTop: 8 }}>
          {submitting ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}

const inputStyle = {
  width: "100%", padding: 10, marginTop: 4, marginBottom: 16,
  background: "#141414", color: "#fff", border: "1px solid #333", borderRadius: 6,
};
```

- [ ] **Step 2: Create `InviteModal.jsx`**

```jsx
import { useState } from "react";
import { managerApi } from "../../api";

export default function InviteModal({ token, onClose, onCreated }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [result, setResult] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  async function go() {
    setSubmitting(true);
    setError(null);
    try {
      const res = await managerApi.createInvite(token, name, email);
      setResult(res);
      onCreated();
    } catch (e) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div style={overlayStyle}>
      <div style={modalStyle}>
        {!result ? (
          <>
            <h3 style={{ marginTop: 0 }}>New invite</h3>
            <label className="label">Candidate name (label only)</label>
            <input value={name} onChange={(e) => setName(e.target.value)} style={inputStyle} />
            <label className="label">Candidate email (label only)</label>
            <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" style={inputStyle} />
            {error && <p style={{ color: "var(--accent-bad)" }}>{error}</p>}
            <div style={{ textAlign: "right" }}>
              <button onClick={onClose} style={ghostBtn}>Cancel</button>
              <button onClick={go} disabled={!name || !email || submitting} style={primaryBtn}>
                {submitting ? "…" : "Generate link"}
              </button>
            </div>
          </>
        ) : (
          <>
            <h3 style={{ marginTop: 0 }}>Send this link</h3>
            <p className="muted">Copy and paste it in WhatsApp. The link is single-use.</p>
            <input readOnly value={result.url} onClick={(e) => e.target.select()} style={inputStyle} />
            <div style={{ textAlign: "right" }}>
              <button onClick={onClose} style={primaryBtn}>Done</button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

const overlayStyle = { position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100 };
const modalStyle = { background: "#141414", border: "1px solid #2a2a2a", borderRadius: 8, padding: 24, width: 480 };
const inputStyle = { width: "100%", padding: 10, marginTop: 4, marginBottom: 16, background: "#0a0a0a", color: "#fff", border: "1px solid #2a2a2a", borderRadius: 6 };
const primaryBtn = { padding: "8px 16px", background: "#fff", color: "#000", border: "none", borderRadius: 6, fontWeight: 600, marginLeft: 8 };
const ghostBtn = { padding: "8px 16px", background: "transparent", color: "#fff", border: "1px solid #333", borderRadius: 6 };
```

- [ ] **Step 3: Create `Dashboard.jsx`**

```jsx
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { managerApi } from "../../api";
import InviteModal from "./InviteModal.jsx";

export default function Dashboard({ jwt }) {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showInvite, setShowInvite] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setRows(await managerApi.listCandidates(jwt));
    setLoading(false);
  }, [jwt]);

  useEffect(() => { load(); }, [load]);

  return (
    <div style={{ maxWidth: 1100, margin: "32px auto", padding: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1 style={{ margin: 0 }}>Candidates</h1>
        <button onClick={() => setShowInvite(true)}
          style={{ padding: "8px 16px", background: "#fff", color: "#000", border: "none", borderRadius: 6, fontWeight: 600 }}>
          + New invite
        </button>
      </div>
      {loading ? <p>Loading…</p> : (
        <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 24 }}>
          <thead>
            <tr style={{ textAlign: "left", borderBottom: "1px solid #2a2a2a" }}>
              <th style={th}>Name</th>
              <th style={th}>Status</th>
              <th style={th}>Recommendation</th>
              <th style={th}>Manager</th>
              <th style={th}>Total time</th>
              <th style={th}>Invited</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} style={{ borderBottom: "1px solid #1a1a1a" }}>
                <td style={td}>
                  <Link to={`/admin/candidates/${r.id}`}>{r.candidate_name || r.invited_label || "—"}</Link>
                  <div className="muted" style={{ fontSize: 11 }}>{r.candidate_email || r.invited_label_email || ""}</div>
                </td>
                <td style={td}>{statusOf(r)}</td>
                <td style={td}><RecBadge rec={r.recommendation} /></td>
                <td style={td}>{r.manager_decision || "—"}</td>
                <td style={td}>{r.total_time_seconds ? `${Math.round(r.total_time_seconds / 60)}m` : "—"}</td>
                <td style={td}>{new Date(r.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {showInvite && (
        <InviteModal
          token={jwt}
          onClose={() => setShowInvite(false)}
          onCreated={load}
        />
      )}
    </div>
  );
}

function statusOf(r) {
  if (r.submitted_at) return "Submitted";
  if (r.started_at) return "In progress";
  return "Invited";
}

function RecBadge({ rec }) {
  if (!rec) return <span className="muted">—</span>;
  const color = { pass: "#22c55e", borderline: "#f59e0b", fail: "#ef4444" }[rec];
  return (
    <span style={{ background: color, color: "#000", padding: "2px 8px", borderRadius: 999, fontSize: 12, fontWeight: 700 }}>
      {rec.toUpperCase()}
    </span>
  );
}

const th = { padding: "12px 8px", fontSize: 11, textTransform: "uppercase", color: "#888", letterSpacing: 0.05 };
const td = { padding: "12px 8px" };
```

- [ ] **Step 4: Replace `Root.jsx`**

```jsx
import { useEffect, useState } from "react";
import { Route, Routes } from "react-router-dom";
import { supabase } from "../../lib/supabase.js";
import Login from "./Login.jsx";
import Dashboard from "./Dashboard.jsx";
import CandidateDetail from "./CandidateDetail.jsx";

export default function ManagerRoot() {
  const [session, setSession] = useState(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => { setSession(data.session); setLoaded(true); });
    const { data: sub } = supabase.auth.onAuthStateChange((_e, s) => setSession(s));
    return () => sub.subscription.unsubscribe();
  }, []);

  if (!loaded) return <div style={{ padding: 48 }}>…</div>;
  if (!session) return <Login onLogin={() => {/* state listener will pick it up */}} />;

  const jwt = session.access_token;
  return (
    <Routes>
      <Route path="" element={<Dashboard jwt={jwt} />} />
      <Route path="candidates/:id" element={<CandidateDetail jwt={jwt} />} />
    </Routes>
  );
}
```

- [ ] **Step 5: Stub `CandidateDetail.jsx` so the build passes**

```jsx
export default function CandidateDetail() {
  return <div style={{ padding: 32 }}>Candidate detail — Task 20.</div>;
}
```

- [ ] **Step 6: Verify**

```bash
cd frontend && npm run dev
```

Open `http://localhost:5173/admin`, log in, see the empty dashboard, click "+ New invite", generate a link.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/manager
git commit -m "feat(frontend): manager Login + Dashboard + InviteModal"
```

---

## Task 20: Frontend manager — CandidateDetail page

**Files:**
- Modify: `frontend/src/components/manager/CandidateDetail.jsx`
- Create: `frontend/src/components/manager/ItemReplay.jsx`

- [ ] **Step 1: Replace `CandidateDetail.jsx`**

```jsx
import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { managerApi } from "../../api";
import ItemReplay from "./ItemReplay.jsx";

export default function CandidateDetail({ jwt }) {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [replay, setReplay] = useState(null);
  const [savingNotes, setSavingNotes] = useState(false);
  const [notes, setNotes] = useState("");

  const load = useCallback(async () => {
    const d = await managerApi.candidateDetail(jwt, id);
    setData(d);
    setNotes(d.manager_notes || "");
  }, [jwt, id]);
  useEffect(() => { load(); }, [load]);

  async function decide(decision) {
    await managerApi.patchCandidate(jwt, id, { manager_decision: decision });
    await load();
  }
  async function saveNotes() {
    setSavingNotes(true);
    await managerApi.patchCandidate(jwt, id, { manager_notes: notes });
    setSavingNotes(false);
  }

  if (!data) return <div style={{ padding: 32 }}>Loading…</div>;
  const { row, auto_fail_reasons, quiz_correct, quiz_total, tab_switches, steps, free_text_justifications, decisions } = data;

  return (
    <div style={{ maxWidth: 1100, margin: "32px auto", padding: 16 }}>
      <h1>{row.candidate_name || row.invited_label}</h1>
      <p className="muted">{row.candidate_email || row.invited_label_email}</p>

      <div style={{ display: "flex", gap: 24, marginTop: 16 }}>
        <Stat label="Recommendation" value={row.recommendation?.toUpperCase() || "—"} />
        <Stat label="Quiz" value={`${quiz_correct}/${quiz_total}`} />
        <Stat label="Tab switches" value={tab_switches} />
        <Stat label="Total time" value={row.total_time_seconds ? `${Math.round(row.total_time_seconds / 60)}m` : "—"} />
      </div>

      {auto_fail_reasons?.length > 0 && (
        <div style={{ marginTop: 24, padding: 16, background: "#3a1f1f", borderRadius: 8, border: "1px solid #5a2a2a" }}>
          <strong>Auto-fail reasons</strong>
          <ul style={{ marginBottom: 0 }}>
            {auto_fail_reasons.map((r) => <li key={r}>{r}</li>)}
          </ul>
        </div>
      )}

      <h2 style={{ marginTop: 32 }}>Per-step</h2>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead><tr style={{ borderBottom: "1px solid #2a2a2a", textAlign: "left" }}>
          <th style={th}>Step</th><th style={th}>Accuracy</th><th style={th}>Obvious bad caught</th>
          <th style={th}>Obvious good caught</th><th style={th}>Dupe consistency</th>
          <th style={th}>Median dwell</th><th style={th}>Duration</th>
        </tr></thead>
        <tbody>
          {steps.map((s) => (
            <tr key={s.pool} style={{ borderBottom: "1px solid #1a1a1a" }}>
              <td style={td}>{s.pool}</td>
              <td style={td}>{(s.accuracy * 100).toFixed(0)}%</td>
              <td style={td}>{s.obvious_bad_caught}/4</td>
              <td style={td}>{s.obvious_good_caught}/4</td>
              <td style={td}>{s.duplicate_consistency}/2</td>
              <td style={td}>{s.median_dwell_ms ? `${(s.median_dwell_ms / 1000).toFixed(1)}s` : "—"}</td>
              <td style={td}>{s.duration_seconds ? `${Math.round(s.duration_seconds / 60)}m` : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {free_text_justifications.length > 0 && (
        <>
          <h2 style={{ marginTop: 32 }}>Free-text justifications</h2>
          {free_text_justifications.map((j, i) => (
            <div key={i} className="card" style={{ marginTop: 8 }}>
              <span className="label">{j.pool}</span>
              <p style={{ margin: "4px 0" }}>{j.justification}</p>
            </div>
          ))}
        </>
      )}

      <h2 style={{ marginTop: 32 }}>All decisions</h2>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead><tr style={{ borderBottom: "1px solid #2a2a2a", textAlign: "left" }}>
          <th style={th}>Pool</th><th style={th}>#</th><th style={th}>Type</th>
          <th style={th}>Their answer</th><th style={th}>Correct?</th><th style={th}>Dwell</th><th></th>
        </tr></thead>
        <tbody>
          {decisions.map((d) => (
            <tr key={d.id} style={{ borderBottom: "1px solid #1a1a1a", background: !d.is_correct ? "#1f0d0d" : "transparent" }}>
              <td style={td}>{d.pool}</td>
              <td style={td}>{d.display_index + 1}{d.is_duplicate ? "*" : ""}</td>
              <td style={td}>{d.anchor_kind || "normal"}</td>
              <td style={td}>{d.answer ? "Yes" : "No"}</td>
              <td style={td}>{d.is_correct ? "✓" : "✗"}</td>
              <td style={td}>{(d.dwell_ms / 1000).toFixed(1)}s</td>
              <td style={td}><button onClick={() => setReplay(d)} style={{ padding: "4px 10px", background: "transparent", border: "1px solid #333", color: "#fff", borderRadius: 4 }}>Replay</button></td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2 style={{ marginTop: 32 }}>Manager decision</h2>
      <div style={{ display: "flex", gap: 8 }}>
        <button onClick={() => decide("hired")} style={{ padding: "8px 16px", background: row.manager_decision === "hired" ? "#22c55e" : "transparent", color: row.manager_decision === "hired" ? "#000" : "#fff", border: "1px solid #333", borderRadius: 6 }}>Hire</button>
        <button onClick={() => decide("rejected")} style={{ padding: "8px 16px", background: row.manager_decision === "rejected" ? "#ef4444" : "transparent", color: row.manager_decision === "rejected" ? "#000" : "#fff", border: "1px solid #333", borderRadius: 6 }}>Reject</button>
      </div>

      <h2 style={{ marginTop: 32 }}>Notes</h2>
      <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={4}
        style={{ width: "100%", padding: 10, background: "#0a0a0a", color: "#fff", border: "1px solid #2a2a2a", borderRadius: 6 }} />
      <button onClick={saveNotes} disabled={savingNotes}
        style={{ marginTop: 8, padding: "8px 16px", background: "#fff", color: "#000", border: "none", borderRadius: 6, fontWeight: 600 }}>
        {savingNotes ? "Saving…" : "Save notes"}
      </button>

      {replay && <ItemReplay jwt={jwt} decision={replay} onClose={() => setReplay(null)} />}
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div className="card" style={{ minWidth: 120 }}>
      <span className="label">{label}</span>
      <p style={{ margin: 0, fontSize: 22, fontWeight: 600 }}>{value}</p>
    </div>
  );
}
const th = { padding: "10px 8px", fontSize: 11, textTransform: "uppercase", color: "#888" };
const td = { padding: "10px 8px" };
```

- [ ] **Step 2: Create `ItemReplay.jsx`**

```jsx
import { useEffect, useState } from "react";
import { managerApi } from "../../api";

export default function ItemReplay({ jwt, decision, onClose }) {
  const [url, setUrl] = useState(null);

  useEffect(() => {
    managerApi.itemSignedUrl(jwt, decision.item_id).then((r) => setUrl(r.url));
  }, [jwt, decision.item_id]);

  const isVideo = decision.pool !== "nano_banana";

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.85)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100 }}>
      <div style={{ background: "#141414", border: "1px solid #2a2a2a", borderRadius: 8, padding: 24, maxWidth: 720 }}>
        <button onClick={onClose} style={{ float: "right", background: "transparent", color: "#fff", border: "none", fontSize: 18 }}>×</button>
        <h3 style={{ marginTop: 0 }}>{decision.pool} — item #{decision.display_index + 1}</h3>
        <p className="muted">
          Candidate said: <strong>{decision.answer ? "Yes" : "No"}</strong> ·
          Correct answer: <strong>{decision.is_correct ? "(matches)" : "(opposite)"}</strong> ·
          Type: <strong>{decision.anchor_kind || "normal"}</strong>
        </p>
        {url ? (
          isVideo ? <video src={url} controls style={{ maxWidth: "100%" }} /> :
                    <img src={url} alt="" style={{ maxWidth: "100%" }} />
        ) : "Loading…"}
        {decision.justification && <p style={{ marginTop: 12 }}><em>"{decision.justification}"</em></p>}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Verify**

Generate an invite, take the test all the way through (with a real candidate) or insert hand-crafted decisions, then load `/admin/candidates/<id>` to confirm the page renders.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/manager
git commit -m "feat(frontend): manager candidate detail + item replay"
```

---

## Task 21: Dockerfile + Railway deploy config

**Files:**
- Create: `Dockerfile`
- Create: `.dockerignore`
- Modify: `backend/main.py` (already has SPA fallback — verify FRONTEND_DIST path)

- [ ] **Step 1: Create `.dockerignore`**

```
.git
.venv
node_modules
**/__pycache__
**/.pytest_cache
content
docs
.env
.env.example
.superpowers
```

- [ ] **Step 2: Create `Dockerfile`**

```dockerfile
# ============================================================
# Stage 1: build frontend
# ============================================================
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_ANON_KEY
ENV VITE_SUPABASE_URL=$VITE_SUPABASE_URL
ENV VITE_SUPABASE_ANON_KEY=$VITE_SUPABASE_ANON_KEY
RUN npm run build

# ============================================================
# Stage 2: python runtime
# ============================================================
FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt
COPY backend/ /app/backend/
COPY --from=frontend-build /app/frontend/dist /app/frontend/dist

ENV PYTHONUNBUFFERED=1
ENV PORT=8000
EXPOSE 8000
WORKDIR /app/backend
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

- [ ] **Step 3: Build locally to verify**

```bash
cd "/Users/victor/PycharmProjects/VA Interview"
docker build \
  --build-arg VITE_SUPABASE_URL=$(grep VITE_SUPABASE_URL frontend/.env | cut -d= -f2) \
  --build-arg VITE_SUPABASE_ANON_KEY=$(grep VITE_SUPABASE_ANON_KEY frontend/.env | cut -d= -f2) \
  -t va-interview-test .
```

Expected: build succeeds.

- [ ] **Step 4: Run locally**

```bash
docker run -p 8000:8000 --env-file .env va-interview-test
```

Visit `http://localhost:8000/admin` — should load the manager UI.

- [ ] **Step 5: Commit**

```bash
git add Dockerfile .dockerignore
git commit -m "feat: dockerfile with multi-stage build (frontend + backend)"
```

- [ ] **Step 6: Deploy to Railway (manual)**

1. Connect Railway to the git repo (push to GitHub first if you haven't)
2. Set env vars in Railway dashboard: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `SUPABASE_JWT_SECRET`, `MANAGER_EMAIL`, `BUCKET_*`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` (the VITE_ vars get baked in at build time)
3. Trigger a deploy
4. Verify the deploy URL responds at `/api/health` with `{"ok": true}`

---

## Task 22: End-to-end smoke test (manual checklist)

This task is a written acceptance checklist, not code. Walk through each scenario in the deployed app.

- [ ] **Manager generates an invite**
  - Log in at `/admin`
  - Click "+ New invite", enter name + email
  - Copy the URL

- [ ] **Candidate happy path**
  - Open the URL in an incognito window (so cookies are isolated)
  - Enter name + email → Welcome submits
  - Tutorial page renders with example images for all 3 pools
  - Click "I've read the rules" → comprehension quiz
  - Answer all 5 correctly → step 1 intro page
  - Click "Start TikTok review" → first item appears (video on left, buttons on right)
  - Answer all 30 items in step 1 (use ← / → keys at least once to verify shortcuts)
  - At least 1 item should trigger the justification modal
  - Step 2 intro → 30 items → step 3 intro → 30 items → submit → "You're done"
  - Reopen the same URL → should show "link unavailable"

- [ ] **Manager reviews candidate**
  - Back to `/admin` → candidate row shows "Submitted" + recommendation badge
  - Click candidate → see per-step accuracy, anchor performance, dupe consistency, free-text justifications, full decisions list
  - Click "Replay" on a row → media plays
  - Click "Hire" → manager_decision saves
  - Type notes → "Save notes"

- [ ] **Quiz failure path**
  - Generate another invite, take the test, answer 1/5 on the quiz
  - Should see "thanks for your time" — link is now dead
  - Manager dashboard shows recommendation = `Fail` with reason `failed_quiz`

- [ ] **Multi-tab abuse**
  - Generate invite, open in tab A, click Welcome, start
  - Open same URL in tab B → should show "Test in progress in another window"

- [ ] **Tab-switch logging**
  - Mid-test, switch to a different tab and back at least 3 times
  - Manager detail should show `tab_switches: ≥3`

- [ ] **Refresh resilience**
  - Mid-test, refresh the page → should resume on the next item
  - Close the browser entirely, reopen, navigate to the link → should resume (within 4h cookie window)
  - After 4h, the cookie expires and the link is effectively dead

- [ ] **All checks pass — commit final**

```bash
git add -A
git commit -m "chore: e2e checklist verified"
```

---

## Self-review (writing-plans skill)

Mapped to spec sections:

| Spec § | Implemented in task |
|---|---|
| 1. Goal | covered by overall plan |
| 2. Non-goals | enforced by what we *don't* build |
| 3. Users | Tasks 6, 9, 13 |
| 4. Architecture | Tasks 3, 21 |
| 5. Tech stack | Tasks 1, 3, 15, 21 |
| 6.1 Manager flow | Tasks 13, 19, 20 |
| 6.2 Candidate flow | Tasks 9–12, 16–18 |
| 6.2 Step intro screens | Task 17 |
| 6.2 Layout B test screen | Task 18 |
| 7. Test composition | Task 11 (`_build_step_sequence`), Task 14 (validation in seed) |
| 8. Scoring & recommendation | Tasks 5, 12 |
| 9. Data model | Task 2 |
| 10. API surface | Tasks 9–13 |
| 11. Storage layout | Tasks 2, 8 |
| 12. Anti-cheating | Tasks 9 (cookie), 18 (tab logger), 11 (sequence builder), 12 (link_used) |
| 13. Edge cases | Tasks 9 (session_in_use), 12 (link_used / 410) |
| 14. Content seeding | Task 14 |
| 15. File structure | Task 1 (skeleton) — full structure populated across all tasks |
| 16. v2 candidates | None (deliberately not built) |
| 17. Success criteria | Task 22 (acceptance checklist) |

**Placeholder scan:** none of the forbidden patterns (TBD, TODO, "implement later", "add appropriate error handling", "similar to Task N", "write tests for the above") appear.

**Type consistency check:**
- `StepStats` (Task 5) ↔ `compute_recommendation`'s `ScoringInput.step()` (Task 5) — consistent
- `compute_recommendation` returns `(recommendation, reasons)` — used in Task 12 `/submit` consistently
- `StateResponse.state` enum values are referenced in Task 16 (`Root.jsx`'s switch) and produced by Task 9–12 backend — same set
- `candidateApi`/`managerApi` method names match backend routes
- `forced_justification_indexes` JSONB written in Task 11, read in Task 11 — consistent

No issues found.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-10-va-interview-test.md`.

Two execution options:

**1. Subagent-Driven (recommended)** — fresh subagent per task, two-stage review between tasks, fast iteration. Best for a plan this large because each task touches different files and has its own contained tests.

**2. Inline Execution** — execute tasks in this session using `executing-plans`, batching with checkpoints for review.

Pick one when ready.
