# VA Interview Test — Design Spec

**Date:** 2026-05-10
**Status:** Approved (brainstorm phase complete; implementation plan to follow)

## 1. Goal

Build a web-based hiring test that filters out unfit VA candidates *before* the existing AI Photos / AI Videos Replication pipelines see their work. Current VAs picked through informal channels have shipped: bad TikTok choices (non-English audio, ugly backgrounds, non-replicable scenes), bad nano-banana generations (model identity drift, missed bust size), and bad Kling output (clear AI artifacts, boring videos). They are also slow.

The test exercises the same three judgments a real VA does on the job — pick TikToks, judge nano-banana generations, judge Kling videos — and produces an auto-recommendation (Pass / Borderline / Fail) plus a full evidence trail for a hiring manager to make the final call.

## 2. Non-goals (v1)

- No admin UI for uploading test content (CSV + seed script only)
- No automatic email delivery of invite links (manager copies & sends manually)
- No video tutorial recording (text + still-image examples only)
- No mobile support (desktop-only)
- No multi-manager / per-manager candidate scoping
- No retake mechanism
- No randomized item pool (every candidate sees the same 30 per step, in shuffled order)
- No localization (English UI only)
- No item-level cross-candidate analytics

## 3. Users

| User | Auth | What they do |
|---|---|---|
| **Hiring manager** | Supabase email+password (single account in v1) | Generates one-time invite links, reviews candidate results, makes hire/reject decision |
| **Candidate** | One-time opaque invite token (no Supabase user) | Takes the test once. Token expires on submit or quiz failure. |

## 4. Architecture

```
┌────────────────────────────┐      ┌────────────────────────┐
│ Candidate (no auth)         │      │ Hiring manager (auth)   │
│   /test/<invite-token>      │      │   /admin/*              │
└──────────────┬──────────────┘      └────────────┬────────────┘
               │                                   │
               ▼                                   ▼
        ┌──────────────────────────────────────────────┐
        │         FastAPI backend (Python)              │
        │  • /api/test/<token>/...  invite-token auth   │
        │  • /api/manager/...       Supabase JWT auth   │
        │  • Static-serves built React frontend         │
        └─────────────────┬────────────────────────────┘
                          │
              ┌───────────┴────────────┐
              ▼                        ▼
        ┌──────────┐           ┌────────────────┐
        │ Supabase │           │ Supabase       │
        │ Postgres │           │ Storage        │
        │ (DB)     │           │ (mp4s, images) │
        └──────────┘           └────────────────┘
```

Single Docker image deployed to Railway, mirroring AI Photos.

## 5. Tech stack

- **Frontend:** React 19 + Vite (SPA, single bundle, 2 route trees: `/test/*` public, `/admin/*` protected)
- **Backend:** FastAPI (Python). Two auth schemes: Supabase JWT for manager endpoints, opaque invite-token for candidate endpoints.
- **Database:** Supabase Postgres
- **Storage:** Supabase Storage with three buckets: `tiktoks`, `nano_banana`, `kling`
- **Auth:** Supabase Auth (manager only). Candidates are not Supabase users — just rows keyed by an invite token.
- **Deployment:** Single Docker container on Railway. Frontend built into static files served by FastAPI. Same pattern as the AI Photos sibling project.

## 6. User flows

### 6.1 Hiring manager flow

1. Visit `/admin/login` → Supabase email+password auth.
2. **Dashboard** (`/admin`): paginated table of all candidates with columns:
   - Name (manager-entered label and candidate-entered name)
   - Invited (timestamp)
   - Status: `Invited` / `In Progress` / `Submitted` / `Failed Quiz`
   - Recommendation: `Pass` / `Borderline` / `Fail` / `—`
   - Total time (mm:ss)
   - Manager decision: `Hired` / `Rejected` / `—`
3. Top-right **+ New Invite** button → modal asks for candidate name + email (label only) → backend generates a unique URL `/test/<token>` → manager copies, sends via WhatsApp/email manually.
4. Click any candidate row → **detail page** (`/admin/candidates/<id>`):
   - Header: name, email, recommendation badge, manager-decision dropdown
   - Auto-fail reasons (if any), surfaced as a red banner with concrete triggers
   - Per-step section (×3): accuracy %, anchor performance ("missed 1/4 obvious-bad — accepted item #14, a clearly-AI Kling video"), duplicate consistency, median dwell time
   - Quiz answers
   - Free-text justifications (verbatim)
   - Tab-switch count + total time + per-step time
   - Expandable "View answers" — every item with the candidate's answer side-by-side with the labeled correct answer; click to replay the video/image and see the admin notes for why that item is good/bad

### 6.2 Candidate flow

1. Click `/test/<token>`.
   - If unknown / used / quiz-failed → **InvalidLink** screen ("This link is invalid or already used").
   - Otherwise → **Welcome form**: full name + email → POST → token now bound to candidate; `started_at` set.
2. **Tutorial page** (`/test/<token>/tutorial`) — text rules with embedded image examples per step (good/bad pairs). "I've read the rules → continue" button.
3. **Comprehension quiz** — 5 multiple-choice questions presented one at a time or all on one page (5 questions, single page is fine). Submit.
   - If `quiz_score < 4/5`: token marked used; recommendation set to `Fail` with reason `failed_quiz`. Candidate sees a brief "Thanks for your time" page. Test ends here.
   - Else: continue.
4. **Step 1 intro page** — "You'll now review 30 TikToks. Mark which you would save for recreation. Reminder of TikTok-specific rules." → Continue.
5. **Step 1: TikTok review** — 30 decisions, one item at a time. Layout B: video on left, decision context + buttons on right. Buttons: `Yes, save this` / `No, skip`. Progress `12 / 30`. Keyboard shortcuts ← / →. On 2 random items per step, after they click, a modal appears: "One sentence — why?" with a textarea, must enter ≥1 character to continue.
6. **Step 2 intro page** → **Step 2: Nano-banana review** — 30 images. Buttons: `Use this generation` / `Reject`. Same forced-justification mechanic.
7. **Step 3 intro page** → **Step 3: Kling video review** — 30 videos. Buttons: `Good` / `Bad`. Same forced-justification mechanic.
8. **Submit page** — "You're done. Thanks, the team will be in touch." Token marked used; `submitted_at` set; recommendation computed and stored.

#### Test-screen UX requirements (Layout B)

- Video on the left at fixed width (~200px wide for 9:16 vertical TikToks, scales for landscape Kling videos)
- Right column: question text ("Would you save this TikTok?") + two stacked buttons. The bottom of each button has a one-line subtitle reminding the rule (e.g. "Wrong language / boring / can't be recreated").
- Progress indicator (`12 / 30`) at top, step indicator (`Step 1 of 3`) at top.
- Keyboard shortcuts: ← rejects, → accepts. Spacebar plays/pauses video.
- No back button mid-step.
- `beforeunload` warning when navigating away mid-test.
- For TikTok and Kling videos: `<video>` element with `controls` and audio enabled (not muted).
- Forced-justification modal: appears after the candidate clicks an answer button on a flagged item. Modal blocks navigation until they submit a non-empty justification.

## 7. Test composition

Per step (×3 steps):

| Item type | Count | Notes |
|---|---|---|
| Obvious-bad anchors | 4 | Hand-labeled. So clearly broken any competent VA must reject. |
| Obvious-good anchors | 4 | Hand-labeled. So clearly correct any competent VA must accept. |
| Normal items | 20 | Mix of subtle good / subtle bad. |
| Hidden duplicates | 2 | Each is a re-show of one of the 28 unique items above, presented later in the step. The candidate is not told. |
| **Total decisions** | **30** | |

So 28 unique items per step × 3 steps = **84 unique items total** to seed.

**Order:** the 30 items are shuffled randomly per candidate. The shuffle is recorded in `candidate_decisions.display_index`, so the manager can always replay the exact sequence the candidate saw.

**Forced free-text justification:** when the candidate calls `/start`, the backend picks **2 distinct display-indexes per step** (uniform random from 0..29) and stores them on `candidates.forced_justification_indexes`. When a `/decision` arrives whose `(pool, display_index)` matches one of those indexes, the response includes `needs_justification: true` so the frontend opens the modal. Total = 6 free-text answers per candidate.

**Quiz:** 5 multiple-choice questions, fixed for v1. ≥4/5 correct to proceed.

## 8. Scoring & recommendation

### 8.1 Per-candidate metrics (computed on submit)

```
For each step s in {tiktok, nano_banana, kling}:
  step_accuracy[s]          = correct_decisions / 30
  obvious_bad_caught[s]     = #obvious-bad anchors correctly rejected   (max 4)
  obvious_good_caught[s]    = #obvious-good anchors correctly accepted  (max 4)
  duplicate_consistency[s]  = #pairs answered identically               (max 2)
  median_dwell_ms[s]        = median(decision.dwell_ms)
  step_duration_s[s]        = step_end - step_start

quiz_score                  = correct_answers / 5
tab_switches                = count of tab_blur events
total_time_s                = submitted_at - started_at
```

### 8.2 Recommendation rules

```
recommendation = 'fail' if ANY of:
  - quiz_score < 4/5                                    → 'failed_quiz'
  - obvious_bad_caught[any step] < 4                    → 'missed_obvious_bad_<step>'
  - duplicate_consistency[any step] < 2                 → 'inconsistent_duplicate_<step>'
  - step_accuracy[any step] < 0.70                      → 'below_floor_<step>'

recommendation = 'borderline' if not fail AND ANY of:
  - obvious_good_caught[any step] < 4                   → 'rejected_obvious_good_<step>'
  - step_accuracy[any step] < 0.80                      → 'weak_step_<step>'
  - tab_switches > 5                                    → 'high_tab_switching'

recommendation = 'pass' otherwise
```

`auto_fail_reasons` is a JSONB array storing every triggered rule — manager sees the exact triggers. Manager always has the final call via `manager_decision`.

## 9. Data model

```sql
manager_profiles
  id              UUID PK  (= Supabase auth user id)
  email           TEXT
  created_at      TIMESTAMPTZ DEFAULT NOW()

test_items
  id                   UUID PK
  pool                 TEXT NOT NULL CHECK (pool IN ('tiktok','nano_banana','kling'))
  storage_path         TEXT NOT NULL                                    -- e.g. 'tiktoks/tt_017.mp4'
  correct_answer       BOOLEAN NOT NULL                                 -- true = save/use/good
  is_anchor            BOOLEAN NOT NULL DEFAULT false
  anchor_kind          TEXT CHECK (anchor_kind IN ('obvious_good','obvious_bad') OR anchor_kind IS NULL)
  notes                TEXT                                             -- admin-only label notes
  created_at           TIMESTAMPTZ DEFAULT NOW()
  UNIQUE (pool, storage_path)

quiz_questions
  id              UUID PK
  question        TEXT NOT NULL
  options         JSONB NOT NULL                                        -- ['a','b','c','d']
  correct_index   INT NOT NULL
  display_order   INT NOT NULL

candidates
  id                    UUID PK
  invite_token          TEXT UNIQUE NOT NULL
  invited_by            UUID REFERENCES manager_profiles(id)
  invited_label         TEXT                                            -- name manager typed
  invited_label_email   TEXT                                            -- email manager typed
  candidate_name        TEXT                                            -- name candidate entered
  candidate_email       TEXT                                            -- email candidate entered
  session_id            TEXT                                            -- issued on first /start, mirrored into a cookie
  forced_justification_indexes JSONB                                    -- {"tiktok":[4,17], "nano_banana":[2,8], "kling":[6,21]}
  created_at            TIMESTAMPTZ DEFAULT NOW()
  started_at            TIMESTAMPTZ
  submitted_at          TIMESTAMPTZ
  link_used             BOOLEAN NOT NULL DEFAULT false
  recommendation        TEXT CHECK (recommendation IN ('pass','borderline','fail') OR recommendation IS NULL)
  auto_fail_reasons     JSONB DEFAULT '[]'::jsonb
  manager_decision      TEXT CHECK (manager_decision IN ('hired','rejected') OR manager_decision IS NULL)
  manager_notes         TEXT

candidate_quiz_answers
  id                UUID PK
  candidate_id      UUID REFERENCES candidates(id) ON DELETE CASCADE
  question_id       UUID REFERENCES quiz_questions(id)
  answered_index    INT
  is_correct        BOOLEAN
  answered_at       TIMESTAMPTZ DEFAULT NOW()

candidate_decisions
  id                UUID PK
  candidate_id      UUID REFERENCES candidates(id) ON DELETE CASCADE
  item_id           UUID REFERENCES test_items(id)
  pool              TEXT NOT NULL                                       -- denormalized
  display_index     INT NOT NULL                                        -- 0..29 within the step
  answer            BOOLEAN NOT NULL
  is_correct        BOOLEAN NOT NULL
  dwell_ms          INT NOT NULL
  shown_at          TIMESTAMPTZ
  answered_at       TIMESTAMPTZ
  justification     TEXT                                                -- nullable; set when forced
  duplicate_of      UUID REFERENCES candidate_decisions(id)             -- 2nd showing → first showing
  forced_justification BOOLEAN NOT NULL DEFAULT false

candidate_events
  id            UUID PK
  candidate_id  UUID REFERENCES candidates(id) ON DELETE CASCADE
  kind          TEXT NOT NULL CHECK (kind IN (
                  'tab_blur','tab_focus','step_start','step_end',
                  'tutorial_view','quiz_start','quiz_end','session_start'
                ))
  meta          JSONB DEFAULT '{}'::jsonb
  occurred_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
```

**Indexes:**
- `candidate_decisions(candidate_id, pool, display_index)` — fast per-step views
- `candidates(invite_token)` — token lookup
- `candidate_events(candidate_id, kind, occurred_at)` — aggregations on the detail page

**No row-level security in v1** since there's only one manager. All `/api/manager/*` endpoints just check the JWT belongs to the registered manager email.

## 10. API surface

### Candidate (auth: invite token in URL path)

- `GET  /api/test/<token>/state` — public (no cookie required for the unstarted case). Returns the candidate's current state (`needs_name` | `needs_tutorial` | `needs_quiz` | `step_<n>_intro` | `step_<n>_in_progress` | `submitted` | `invalid` | `session_in_use`) and whatever data the next screen needs (next item, progress, forced-justification flag). If the candidate has started but the request lacks the matching session cookie → returns `session_in_use`.
- `POST /api/test/<token>/start` — body: `{ name, email }`. Creates `started_at`, generates `session_id` (UUID), persists it on `candidates`, and Set-Cookie's it (httpOnly, scoped to `/api/test/<token>/`, Max-Age=14400). Idempotent only if no session is already established; otherwise returns 409.
- `POST /api/test/<token>/tutorial-acknowledged` — logs event.
- `POST /api/test/<token>/quiz` — body: `{ answers: [int, int, int, int, int] }`. Computes score; if <4/5, marks link_used + recommendation=fail and returns done state.
- `POST /api/test/<token>/step/<step_name>/intro-acknowledged` — logs event.
- `POST /api/test/<token>/decision` — body: `{ item_id, answer, dwell_ms, shown_at }`. Returns `{ decision_id, needs_justification: bool, next: { item } | { step_complete: true } | { test_complete: true } }`. If `needs_justification` is true, the frontend opens the justification modal before rendering the next item.
- `POST /api/test/<token>/justification` — body: `{ decision_id, justification }`. Required when `needs_justification` was true on the prior decision response. Validates non-empty server-side.
- `POST /api/test/<token>/event` — body: `{ kind, meta }`. For tab_blur etc.
- `POST /api/test/<token>/submit` — finalizes; computes recommendation; sets link_used.

### Manager (auth: Supabase JWT)

- `POST /api/manager/invites` — body: `{ name, email }`. Returns `{ token, url }`.
- `GET  /api/manager/candidates` — list, with filters.
- `GET  /api/manager/candidates/<id>` — full detail including all decisions, events, justifications.
- `PATCH /api/manager/candidates/<id>` — body: `{ manager_decision, manager_notes }`.
- `GET  /api/manager/items/<id>/signed-url` — returns time-limited signed URL to play back any item from Storage on the detail page.

All candidate-side media URLs are also signed (short-lived) so the storage bucket can stay private.

## 11. Storage layout

```
Supabase Storage:
├── tiktoks/         (private bucket; objects keyed by storage_path in test_items)
├── nano_banana/
├── kling/
└── tutorial/        (public bucket; example images embedded in tutorial page)
```

All test-item buckets are private. The frontend gets signed URLs (60s TTL) per item from the backend.

## 12. Anti-cheating measures

- **Single-use invite link**: `link_used` flips on submit OR quiz fail. Re-opening shows InvalidLink.
- **Single session lock**: `/start` issues a `session_id` and sets it as an httpOnly cookie scoped to `/api/test/<token>/`, with `Max-Age=14400` (4h). Subsequent `/decision`/`/event`/`/submit` calls validate the cookie matches `candidates.session_id`. A different tab/device opening the same link has no cookie → 409 with "test in progress in another window."
- **Tab/window blur logging**: `visibilitychange` listener → POST `/api/test/<token>/event`. Counted, surfaced to manager.
- **Refresh behavior**: refresh in the same browser keeps the cookie → `GET /state` returns the current step + last completed `display_index` so the frontend resumes seamlessly. After 4h the cookie expires; the candidate is locked out and the manager must intervene. `beforeunload` warning still fires to discourage refresh.
- **Hidden duplicates**: 2 per step, link via `duplicate_of` in DB.
- **Anchors**: 8 per step, asymmetric scoring (missed obvious-bad = auto-fail, rejected obvious-good = borderline only).
- **Dwell time**: per-item; surfaced for manager review.

Out of scope for v1: webcam/screen-share verification, fingerprinting, IP allowlists, mouse-movement biometrics.

## 13. Edge cases

| Case | Handling |
|---|---|
| Candidate fails quiz | Token marked used, recommendation=fail, polite "thanks" page. |
| Candidate refreshes mid-test | `beforeunload` warning fires. If they refresh anyway, the session_id cookie persists in the same browser, so `GET /state` returns the next item and the test resumes. Cookie expires after 4h — past that, link is dead. |
| Candidate opens link in two tabs | First `/start` wins via session_id cookie; second tab's `/state` returns 409 "test in progress in another window." |
| Candidate closes the tab and reopens within 4h | Same browser → cookie present → `/state` resumes. New browser/device → no cookie → 409. |
| Manager opens InvalidLink page | Same screen as candidate; benign. |
| Backend dies mid-decision | Decisions are POSTed individually with `shown_at` and `dwell_ms` from the client. If a request fails, the client retries up to 3 times. If still failing, the test halts with an error screen and the manager has to manually reset (manual SQL in v1). |
| Item file 404 in Storage | Frontend shows error placeholder; logs `item_load_error` event; candidate skips by clicking either button — but the manager will see the load error in the events. |
| Two candidates submit at once | Independent rows; no conflict. |
| Forced-justification text is empty | Frontend prevents submit; backend re-validates and 422s an empty submission. |

## 14. Content seeding

`backend/seed.py` — CLI script the developer runs once locally.

1. Reads `content/items.csv`:
   ```csv
   filename,pool,correct_answer,is_anchor,anchor_kind,notes
   tt_001.mp4,tiktok,true,true,obvious_good,
   tt_002.mp4,tiktok,false,true,obvious_bad,non-English audio
   tt_003.mp4,tiktok,true,false,,
   ```
2. For each row:
   - Uploads `content/<pool>/<filename>` to `<pool>/<filename>` in Supabase Storage (UPSERT)
   - Inserts/updates the `test_items` row by `(pool, storage_path)`
3. Reads `content/quiz.json`:
   ```json
   [
     {"question":"...","options":["a","b","c","d"],"correct_index":2}
   ]
   ```
4. Inserts/updates `quiz_questions`.

Re-runnable. Validates: each pool has exactly 28 unique items, exactly 4 obvious-good anchors, exactly 4 obvious-bad anchors. Aborts with a clear error if not.

`tutorial_examples/` is uploaded to the `tutorial` (public) bucket. The tutorial React component references those public URLs directly.

## 15. File structure

```
VA Interview/
├── Dockerfile
├── docker-compose.yml         (optional, for local dev)
├── backend/
│   ├── main.py                 FastAPI app, mounts routers, serves frontend
│   ├── auth.py                 Supabase JWT verify (manager) + invite-token verify (candidate)
│   ├── config.py               env, scoring thresholds
│   ├── supabase_client.py      singleton
│   ├── models.py               Pydantic request/response schemas
│   ├── routers/
│   │   ├── candidate.py        /api/test/<token>/* endpoints
│   │   └── manager.py          /api/manager/* endpoints
│   ├── scoring.py              compute_recommendation(...)
│   ├── seed.py                 CLI: load test items + quiz from local content/ → DB & Storage
│   ├── migrations.sql          full schema, applied once by hand
│   └── requirements.txt
│
├── frontend/
│   ├── index.html
│   ├── vite.config.js
│   ├── package.json
│   └── src/
│       ├── App.jsx                       Router: /test/* (public) + /admin/* (protected)
│       ├── api.js                        fetch wrappers
│       ├── lib/supabase.js               manager-side client
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
│
├── content/                              local-only seed material; gitignored
│   ├── tiktoks/
│   ├── nano_banana/
│   ├── kling/
│   ├── tutorial_examples/
│   ├── items.csv
│   └── quiz.json
│
└── docs/
    └── superpowers/specs/
        └── 2026-05-10-va-interview-test-design.md   (this file)
```

## 16. Open questions / v2 candidates

- **Admin upload UI** for content (replace seed.py)
- **Email delivery** of invite links (SendGrid / Postmark)
- **Multi-manager** with per-manager candidate scoping
- **Randomized item pool** (would also need RLS or careful query design)
- **Failure-mode multi-choice** test (item 5 from brainstorm — "what's wrong with this?" multi-choice)
- **Ranking sub-task** (item 6 from brainstorm — drag-rank 4 NB gens of the same frame)
- **Mobile support** if real candidates need it
- **Item-level analytics** ("which items are hardest? are any items mis-labeled?")
- **Manager corrections feed back into test_items.correct_answer** (calibration over time)
- **Resume on refresh** if too many candidates lose progress

## 17. Success criteria

- A candidate can complete the test on a desktop browser in 30-45 minutes start to finish.
- The manager can generate an invite, receive a result, and view a full evidence trail without ever touching the database directly.
- Auto-fail rules correctly trigger on candidates who: don't read the tutorial, click randomly, accept clearly-broken items.
- Re-running `seed.py` against a re-labeled `content/items.csv` updates labels without losing candidate data.
- All test media is served from private Supabase Storage via short-lived signed URLs.
