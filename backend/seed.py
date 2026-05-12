"""Seed test_items + quiz_questions by walking the content folder directly.

Discovers items from six standard folders inside --content-dir:

    Good TikToks/        -> pool=tiktok,      correct=True
    Bad TikToks/         -> pool=tiktok,      correct=False
    Good Kling/          -> pool=kling,       correct=True
    Bad Kling/           -> pool=kling,       correct=False
    Good NanoBanana/     -> pool=nano_banana, correct=True
    Bad NanoBanana/      -> pool=nano_banana, correct=False

TikTok / Kling: each file is one row. A file `X copy.<ext>` whose sibling
`X.<ext>` also exists in the same folder becomes a tracked duplicate row
(`duplicate_of_item` -> original's UUID).

NanoBanana: files come in pairs by stem. `N.<ext>` is the original reference
TikTok frame, `N-N.<ext>` is the AI generation. One row per pair:
    storage_path   = generation's storage key
    reference_path = original's storage key
Both files are uploaded to the nano_banana bucket. Orphan files (one side
missing) emit a warning and are skipped.

Idempotent: upserts by (pool, storage_path). Two-pass insert so dupes can
resolve to the original's UUID.

Quiz: read content_dir/quiz.json if present, else fall back to a hardcoded
default that mirrors frontend/src/components/candidate/Quiz.jsx.

Usage:
    python seed.py
    python seed.py --content-dir "/Users/victor/Desktop/VA Interview photos:videos"
    python seed.py --content-dir ./content --dry-run --quiet
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from config import POOLS, QUIZ_QUESTION_COUNT
from storage import bucket_for_pool


# ----------------------------------------------------------------------------
# Folder -> (pool, correct_answer) mapping
# ----------------------------------------------------------------------------
FOLDER_MAP: dict[str, tuple[str, bool]] = {
    "Good TikToks": ("tiktok", True),
    "Bad TikToks": ("tiktok", False),
    "Good Kling": ("kling", True),
    "Bad Kling": ("kling", False),
    "Good NanoBanana": ("nano_banana", True),
    "Bad NanoBanana": ("nano_banana", False),
}

# Case-insensitive allowed extensions per pool.
TIKTOK_EXTS = {".mp4"}
KLING_EXTS = {".mp4"}
NB_EXTS = {".png", ".jpg", ".jpeg"}

# Default quiz, mirrors frontend/src/components/candidate/Quiz.jsx.
DEFAULT_QUIZ: list[dict] = [
    {
        "question": "Which of the following is NOT a reason to reject a TikTok?",
        "options": [
            "Non-English audio",
            "Ugly background",
            "Trending in the United States",
            "Clearly impossible to recreate on Kling",
        ],
        "correct_index": 2,
    },
    {
        "question": "A nano-banana generation comes back with a clearly smaller bust than our reference photos. You should:",
        "options": [
            "Approve it — it's close enough",
            "Reject it",
            "Approve it and add a note",
            "Approve it if the rest of the image looks good",
        ],
        "correct_index": 1,
    },
    {
        "question": "A Kling video shows the model's face flickering for 1 second mid-clip. You should:",
        "options": [
            "Approve — the rest is fine",
            "Approve if it's only a small section",
            "Reject — face must stay consistent",
            "Approve if you can crop it out",
        ],
        "correct_index": 2,
    },
    {
        "question": "How many TikToks, nano-banana images, and Kling videos will you review in this test?",
        "options": ["10 of each", "20 of each", "30 of each", "50 of each"],
        "correct_index": 2,
    },
    {
        "question": "Can you go back to a previous answer once you've clicked?",
        "options": ["Yes, anytime", "Yes, within the same step", "Only if you refresh", "No, never"],
        "correct_index": 3,
    },
]


# ----------------------------------------------------------------------------
# Item dataclass
# ----------------------------------------------------------------------------
@dataclass
class Item:
    pool: str
    correct_answer: bool
    storage_path: str  # basename within the pool's bucket
    local_path: Path
    # NB pair only: original frame uploaded alongside the generation.
    reference_storage_path: str | None = None
    reference_local_path: Path | None = None
    # Tracked dupe (TikTok / Kling): pass-2 needs to look up the original UUID.
    dupe_of_storage_path: str | None = None

    @property
    def is_dupe(self) -> bool:
        return self.dupe_of_storage_path is not None


# ----------------------------------------------------------------------------
# Discovery
# ----------------------------------------------------------------------------
def _allowed_exts(pool: str) -> set[str]:
    if pool == "tiktok":
        return TIKTOK_EXTS
    if pool == "kling":
        return KLING_EXTS
    if pool == "nano_banana":
        return NB_EXTS
    raise ValueError(f"unknown pool: {pool}")


def _ext_ok(name: str, pool: str) -> bool:
    return Path(name).suffix.lower() in _allowed_exts(pool)


def _is_dotfile(name: str) -> bool:
    return name.startswith(".")


def _list_files(folder: Path, pool: str) -> list[Path]:
    """Return files in `folder` whose extension is valid for `pool`."""
    if not folder.is_dir():
        raise SystemExit(f"missing folder: {folder}")
    out: list[Path] = []
    for p in sorted(folder.iterdir()):
        if not p.is_file() or _is_dotfile(p.name):
            continue
        if not _ext_ok(p.name, pool):
            continue
        out.append(p)
    return out


def _discover_flat(folder: Path, pool: str, correct: bool) -> tuple[list[Item], list[Item]]:
    """TikTok / Kling: one Item per file. Detect ' copy.<ext>' dupes."""
    files = _list_files(folder, pool)
    by_name = {p.name: p for p in files}

    originals: list[Item] = []
    dupes: list[Item] = []
    for p in files:
        stem, ext = p.stem, p.suffix
        if stem.endswith(" copy"):
            original_stem = stem[: -len(" copy")]
            original_name = f"{original_stem}{ext}"
            if original_name in by_name:
                dupes.append(Item(
                    pool=pool,
                    correct_answer=correct,
                    storage_path=p.name,
                    local_path=p,
                    dupe_of_storage_path=original_name,
                ))
                continue
            # ' copy' suffix but no sibling original — treat as a normal item.
        originals.append(Item(
            pool=pool,
            correct_answer=correct,
            storage_path=p.name,
            local_path=p,
        ))
    return originals, dupes


def _discover_nb(folder: Path, correct: bool, warn: list[str]) -> list[Item]:
    """NanoBanana: pair `N.<ext>` (original) with `N-N.<ext>` (generation).

    One Item per pair, with both local paths recorded. Orphan files warn + skip.

    Storage paths are namespaced `good/<name>` or `bad/<name>` because Good and
    Bad NanoBanana folders use overlapping integer stems (e.g. both contain
    `2-2.png`) — a flat basename would collide on the (pool, storage_path)
    unique key and silently lose rows.
    """
    files = _list_files(folder, "nano_banana")
    # Group by stem so we can find {N: N.ext, N-N: N-N.ext}.
    by_stem: dict[str, Path] = {p.stem: p for p in files}
    prefix = "good" if correct else "bad"

    items: list[Item] = []
    seen: set[str] = set()
    # Find generations (stems shaped like 'N-N') and pair to originals (stem 'N').
    for p in files:
        stem = p.stem
        if "-" not in stem:
            continue
        left, _, right = stem.partition("-")
        if left != right or not left:
            continue
        original_stem = left
        original = by_stem.get(original_stem)
        if original is None:
            warn.append(f"NB generation without original: {folder.name}/{p.name}")
            continue
        items.append(Item(
            pool="nano_banana",
            correct_answer=correct,
            storage_path=f"{prefix}/{p.name}",                 # generation
            local_path=p,
            reference_storage_path=f"{prefix}/{original.name}",
            reference_local_path=original,
        ))
        seen.add(p.stem)
        seen.add(original.stem)

    # Anything left unseen is an orphan.
    for p in files:
        if p.stem in seen:
            continue
        # Skip generations that already warned above.
        stem = p.stem
        if "-" in stem:
            left, _, right = stem.partition("-")
            if left == right and left:
                continue  # already warned
        warn.append(f"NB original without generation: {folder.name}/{p.name}")

    return items


def discover_items(content_dir: Path) -> tuple[list[Item], list[Item], list[str]]:
    """Walk the six standard folders.

    Returns (originals, dupes, warnings). `originals` includes NB pair rows
    (which are not duplicates — they're independent items with a reference).
    `dupes` is only TikTok/Kling tracked duplicates.
    """
    originals: list[Item] = []
    dupes: list[Item] = []
    warnings: list[str] = []

    for folder_name, (pool, correct) in FOLDER_MAP.items():
        folder = content_dir / folder_name
        if pool == "nano_banana":
            originals.extend(_discover_nb(folder, correct, warnings))
        else:
            o, d = _discover_flat(folder, pool, correct)
            originals.extend(o)
            dupes.extend(d)
    return originals, dupes, warnings


# ----------------------------------------------------------------------------
# Upload + insert
# ----------------------------------------------------------------------------
def _content_type(filename: str) -> str:
    guess, _ = mimetypes.guess_type(filename)
    return guess or "application/octet-stream"


def upload_file(sb, bucket: str, storage_path: str, local_path: Path) -> None:
    """Upload `local_path` to Supabase Storage at `bucket/storage_path` with upsert."""
    with local_path.open("rb") as fh:
        sb.storage.from_(bucket).upload(
            path=storage_path,
            file=fh,
            file_options={
                "upsert": "true",
                "content-type": _content_type(storage_path),
            },
        )


def insert_items_pass1(sb, items: Iterable[Item]) -> dict[tuple[str, str], str]:
    """Insert / upsert non-dupe rows. Return {(pool, storage_path): uuid}."""
    out: dict[tuple[str, str], str] = {}
    for it in items:
        row = {
            "pool": it.pool,
            "storage_path": it.storage_path,
            "correct_answer": it.correct_answer,
            "reference_path": it.reference_storage_path,
            "duplicate_of_item": None,
        }
        res = sb.table("test_items").upsert(
            row, on_conflict="pool,storage_path"
        ).execute()
        data = res.data or []
        if not data:
            # Some supabase-py versions don't return rows on upsert; fetch.
            sel = sb.table("test_items").select("id").eq(
                "pool", it.pool
            ).eq("storage_path", it.storage_path).limit(1).execute()
            data = sel.data or []
        if not data:
            raise SystemExit(
                f"failed to resolve inserted row id for {it.pool}/{it.storage_path}"
            )
        out[(it.pool, it.storage_path)] = data[0]["id"]
    return out


def insert_items_pass2(
    sb,
    dupes: Iterable[Item],
    originals_map: dict[tuple[str, str], str],
) -> None:
    """Insert dupe rows pointing at their original's UUID."""
    for it in dupes:
        assert it.dupe_of_storage_path is not None
        key = (it.pool, it.dupe_of_storage_path)
        original_id = originals_map.get(key)
        if original_id is None:
            raise SystemExit(
                f"dupe {it.pool}/{it.storage_path} references missing original "
                f"{it.dupe_of_storage_path}"
            )
        row = {
            "pool": it.pool,
            "storage_path": it.storage_path,
            "correct_answer": it.correct_answer,
            "reference_path": None,
            "duplicate_of_item": original_id,
        }
        sb.table("test_items").upsert(
            row, on_conflict="pool,storage_path"
        ).execute()


def seed_quiz(sb, quiz: list[dict]) -> None:
    if len(quiz) != QUIZ_QUESTION_COUNT:
        raise SystemExit(
            f"quiz must have exactly {QUIZ_QUESTION_COUNT} questions, got {len(quiz)}"
        )
    # Wipe + reinsert (small table; keeps display_order clean).
    sb.table("candidate_quiz_answers").delete().neq(
        "id", "00000000-0000-0000-0000-000000000000"
    ).execute()
    sb.table("quiz_questions").delete().neq(
        "id", "00000000-0000-0000-0000-000000000000"
    ).execute()
    for idx, q in enumerate(quiz):
        sb.table("quiz_questions").insert({
            "question": q["question"],
            "options": q["options"],
            "correct_index": q["correct_index"],
            "display_order": idx,
        }).execute()


def _load_quiz(content_dir: Path) -> list[dict]:
    qpath = content_dir / "quiz.json"
    if qpath.is_file():
        with qpath.open() as f:
            return json.load(f)
    return DEFAULT_QUIZ


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------
def _summarize(originals: list[Item], dupes: list[Item]) -> dict[str, dict]:
    summary: dict[str, dict] = {p: {"unique": 0, "dupes": 0, "nb_pairs": 0} for p in POOLS}
    for it in originals:
        if it.pool == "nano_banana":
            summary[it.pool]["nb_pairs"] += 1
            summary[it.pool]["unique"] += 1
        else:
            summary[it.pool]["unique"] += 1
    for it in dupes:
        summary[it.pool]["dupes"] += 1
    return summary


def _print_summary(summary: dict[str, dict], warnings: list[str]) -> None:
    print("Discovery summary:")
    for pool in POOLS:
        s = summary[pool]
        total = s["unique"] + s["dupes"]
        if pool == "nano_banana":
            print(
                f"  {pool}: {total} items "
                f"({s['nb_pairs']} pairs, {s['dupes']} dupes)"
            )
        else:
            print(
                f"  {pool}: {total} items "
                f"({s['unique']} unique + {s['dupes']} dupe)"
            )
    if warnings:
        print("Warnings:")
        for w in warnings:
            print(f"  ! {w}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    default_content = (Path(__file__).resolve().parent.parent / "content").as_posix()
    parser.add_argument("--content-dir", default=default_content, help="content root")
    parser.add_argument("--dry-run", action="store_true", help="discover only; no uploads/inserts")
    parser.add_argument("--quiet", action="store_true", help="suppress per-file progress")
    args = parser.parse_args(argv)

    content_dir = Path(args.content_dir).expanduser().resolve()
    if not content_dir.is_dir():
        print(f"content directory not found: {content_dir}", file=sys.stderr)
        return 1

    verbose = not args.quiet

    if verbose:
        print(f"Content dir: {content_dir}")
        print("Discovering items...")
    try:
        originals, dupes, warnings = discover_items(content_dir)
    except SystemExit as e:
        print(f"discovery error: {e}", file=sys.stderr)
        return 1

    summary = _summarize(originals, dupes)
    _print_summary(summary, warnings)

    quiz = _load_quiz(content_dir)
    if len(quiz) != QUIZ_QUESTION_COUNT:
        print(
            f"quiz has {len(quiz)} questions, expected {QUIZ_QUESTION_COUNT}",
            file=sys.stderr,
        )
        return 1
    print(f"Quiz: {len(quiz)} questions ({'from quiz.json' if (content_dir / 'quiz.json').is_file() else 'default'})")

    if args.dry_run:
        if verbose:
            print("\nDry run — would upload + upsert:")
            for it in originals:
                ref = f" (ref={it.reference_storage_path})" if it.reference_storage_path else ""
                print(f"  + {it.pool}/{it.storage_path}{ref}")
            for it in dupes:
                print(f"  + {it.pool}/{it.storage_path} (dupe of {it.dupe_of_storage_path})")
        print("\nDry run complete.")
        return 0

    # Real run — talk to Supabase.
    from supabase_client import get_supabase  # imported here so --dry-run works offline
    sb = get_supabase()

    if verbose:
        print("\nUploading files...")
    for it in (*originals, *dupes):
        bucket = bucket_for_pool(it.pool)
        upload_file(sb, bucket, it.storage_path, it.local_path)
        if verbose:
            print(f"  ^ {bucket}/{it.storage_path}")
        if it.reference_local_path is not None and it.reference_storage_path is not None:
            upload_file(sb, bucket, it.reference_storage_path, it.reference_local_path)
            if verbose:
                print(f"  ^ {bucket}/{it.reference_storage_path} (reference)")

    if verbose:
        print("\nInserting items (pass 1: originals + NB pairs)...")
    originals_map = insert_items_pass1(sb, originals)
    if verbose:
        print(f"  inserted {len(originals_map)} rows")

    if verbose:
        print("Inserting items (pass 2: dupes)...")
    insert_items_pass2(sb, dupes, originals_map)
    if verbose:
        print(f"  inserted {len(dupes)} dupe rows")

    if verbose:
        print("Seeding quiz...")
    seed_quiz(sb, quiz)
    if verbose:
        print(f"  inserted {len(quiz)} quiz questions")

    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
