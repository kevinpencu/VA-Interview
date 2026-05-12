"""Seed test_items + quiz_questions from local content/ folder.

NOTE: This file is a stub kept compatible with the v2 schema. Task C
replaces it with the production seeding script (NB pair handling,
tracked dupes via duplicate_of_item, etc.).

Idempotent: re-running upserts items by (pool, storage_path).
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from config import POOLS, QUIZ_QUESTION_COUNT
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
                "notes": (row.get("notes") or "").strip() or None,
            })
    return rows


def _validate(rows: list[dict]) -> None:
    # No-op: anchor-aware validation has been removed; Task C will replace this
    # file with a new seeding strategy that fits the v2 schema (NB pairs,
    # tracked dupes via duplicate_of_item).
    return


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
