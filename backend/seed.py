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
