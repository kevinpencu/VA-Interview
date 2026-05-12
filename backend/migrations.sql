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

-- ============================================================
-- additional FK indexes (perf for manager detail joins)
-- ============================================================
CREATE INDEX IF NOT EXISTS candidate_decisions_item_idx
  ON candidate_decisions(item_id);

CREATE INDEX IF NOT EXISTS candidate_decisions_duplicate_of_idx
  ON candidate_decisions(duplicate_of) WHERE duplicate_of IS NOT NULL;

-- ============================================================
-- v2 — drop anchors, NB pair support, tracked dupe
-- ============================================================
ALTER TABLE test_items ADD COLUMN IF NOT EXISTS reference_path TEXT;
ALTER TABLE test_items ADD COLUMN IF NOT EXISTS duplicate_of_item UUID REFERENCES test_items(id);
CREATE INDEX IF NOT EXISTS test_items_duplicate_of_idx ON test_items(duplicate_of_item) WHERE duplicate_of_item IS NOT NULL;
