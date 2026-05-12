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

Tutorial lessons (--lessons-dir): walks the same six folder names and uploads
their files to the `tutorial` bucket under `<pool_key>/<good|bad>/<filename>`.
Writes a `manifest.json` at the bucket root that the frontend Tutorial reads.

Usage:
    python seed.py
    python seed.py --content-dir "/Users/victor/Desktop/VA Interview photos:videos"
    python seed.py --content-dir ./content --dry-run --quiet
    python seed.py --lessons-dir "/Users/victor/Desktop/lessons before test for VA"
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from config import POOLS, QUIZ_QUESTION_COUNT, load_settings
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
# Tutorial lessons
# ----------------------------------------------------------------------------
# Maps the on-disk folder name to (pool_key, side) for the tutorial manifest.
LESSON_FOLDER_MAP: dict[str, tuple[str, str]] = {
    "Good TikToks": ("tiktok", "good"),
    "Bad TikToks": ("tiktok", "bad"),
    "Good Kling": ("kling", "good"),
    "Bad Kling": ("kling", "bad"),
    "Good NanoBanana": ("nano_banana", "good"),
    "Bad NanoBanana": ("nano_banana", "bad"),
}

# Extensions accepted per pool for tutorial lessons. Mirrors the test-content
# rules but tolerates more image formats for nano_banana so we don't drop
# example files needlessly.
LESSON_EXTS: dict[str, set[str]] = {
    "tiktok": {".mp4"},
    "kling": {".mp4"},
    "nano_banana": {".png", ".jpg", ".jpeg", ".webp"},
}

_NB_ORIGINAL_RE = re.compile(r"^(.+) ORIGINAL\.\w+$", re.IGNORECASE)
_NB_AI_RE = re.compile(r"^(.+) AI\.\w+$", re.IGNORECASE)
_NB_IMG_RE = re.compile(r"^IMG_(\d+)\.\w+$", re.IGNORECASE)


def _list_lesson_files(folder: Path, pool: str) -> list[Path]:
    """Return non-dotfile files in `folder` whose extension is valid for `pool`."""
    if not folder.is_dir():
        raise SystemExit(f"missing lessons folder: {folder}")
    allowed = LESSON_EXTS[pool]
    out: list[Path] = []
    for p in sorted(folder.iterdir()):
        if not p.is_file() or _is_dotfile(p.name):
            continue
        if p.suffix.lower() not in allowed:
            continue
        out.append(p)
    return out


def _public_url(sb, bucket: str, path: str) -> str:
    """Resolve the public URL for `bucket/path`. supabase-py returns either a
    plain string or a dict depending on version — handle both."""
    res = sb.storage.from_(bucket).get_public_url(path)
    if isinstance(res, str):
        return res
    if isinstance(res, dict):
        # Common keys across versions.
        return (
            res.get("publicURL")
            or res.get("publicUrl")
            or res.get("public_url")
            or ""
        )
    return str(res or "")


def _fallback_public_url(supabase_url: str, bucket: str, path: str) -> str:
    """Construct the canonical public URL when supabase-py doesn't return one.
    Preserves the raw path (no percent-encoding) — the frontend handles that
    via encodeURI when fetching."""
    return f"{supabase_url.rstrip('/')}/storage/v1/object/public/{bucket}/{path}"


def _pair_nb_good(files: list[Path], warn: list[str]) -> list[dict]:
    """Pair Good NanoBanana files. Order:
       1) <prefix> ORIGINAL.<ext> + <prefix> AI.<ext> (case-insensitive prefix).
       2) IMG_<N>.<ext> + IMG_<N+1>.<ext> consecutive pairs.
       Anything left over emits a warning."""
    pairs: list[tuple[Path, Path]] = []  # (original, ai)
    used: set[Path] = set()

    # Pass 1: ORIGINAL / AI by shared prefix.
    originals_by_prefix: dict[str, Path] = {}
    ais_by_prefix: dict[str, Path] = {}
    for p in files:
        mo = _NB_ORIGINAL_RE.match(p.name)
        ma = _NB_AI_RE.match(p.name)
        if mo:
            originals_by_prefix[mo.group(1).strip().lower()] = p
        elif ma:
            ais_by_prefix[ma.group(1).strip().lower()] = p
    for prefix, original in originals_by_prefix.items():
        ai = ais_by_prefix.get(prefix)
        if ai is not None:
            pairs.append((original, ai))
            used.add(original)
            used.add(ai)

    # Pass 2: IMG_<N> consecutive pairs.
    img_by_n: dict[int, Path] = {}
    for p in files:
        if p in used:
            continue
        m = _NB_IMG_RE.match(p.name)
        if not m:
            continue
        img_by_n[int(m.group(1))] = p
    ns = sorted(img_by_n.keys())
    i = 0
    while i < len(ns) - 1:
        if ns[i + 1] == ns[i] + 1:
            a, b = img_by_n[ns[i]], img_by_n[ns[i + 1]]
            pairs.append((a, b))
            used.add(a)
            used.add(b)
            i += 2
        else:
            i += 1

    # Warn about leftovers.
    for p in files:
        if p not in used:
            warn.append(f"NB-good unpaired file (skipped): {p.name}")

    return [(orig, ai) for orig, ai in pairs]  # type: ignore[return-value]


@dataclass
class LessonDiscovery:
    """Pre-upload view of the lessons folder. Mirrors the manifest shape but
    holds local paths so the upload step can map name->URL after upload."""
    # pool -> side -> list of entries
    # tiktok/kling entries: {"type": "video", "path": Path}
    # nb good entries:      {"type": "pair", "original": Path, "ai": Path}
    # nb bad entries:       {"type": "image", "path": Path}
    pools: dict[str, dict[str, list[dict]]] = field(
        default_factory=lambda: {p: {"good": [], "bad": []} for p in POOLS}
    )
    # Flat list of (storage_path, local_path) tuples for the uploader.
    uploads: list[tuple[str, Path]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def discover_lessons(lessons_dir: Path) -> LessonDiscovery:
    """Walk the six lesson folders and build a LessonDiscovery."""
    d = LessonDiscovery()
    for folder_name, (pool, side) in LESSON_FOLDER_MAP.items():
        folder = lessons_dir / folder_name
        files = _list_lesson_files(folder, pool)

        if pool in ("tiktok", "kling"):
            for p in files:
                storage_path = f"{pool}/{side}/{p.name}"
                d.pools[pool][side].append({"type": "video", "path": p, "storage_path": storage_path})
                d.uploads.append((storage_path, p))
            continue

        # nano_banana
        if side == "good":
            pairs = _pair_nb_good(files, d.warnings)
            for original, ai in pairs:
                op = f"nano_banana/good/{original.name}"
                ap = f"nano_banana/good/{ai.name}"
                d.pools["nano_banana"]["good"].append({
                    "type": "pair",
                    "original": original,
                    "ai": ai,
                    "original_storage_path": op,
                    "ai_storage_path": ap,
                })
                d.uploads.append((op, original))
                d.uploads.append((ap, ai))
        else:
            # Bad NB: every file is a standalone failure-mode image.
            for p in files:
                storage_path = f"nano_banana/bad/{p.name}"
                d.pools["nano_banana"]["bad"].append({
                    "type": "image",
                    "path": p,
                    "storage_path": storage_path,
                })
                d.uploads.append((storage_path, p))
    return d


def build_manifest(d: LessonDiscovery, url_for: callable) -> dict:
    """Build the manifest JSON from a LessonDiscovery. `url_for(storage_path)`
    returns the public URL for an already-uploaded path."""
    manifest: dict = {p: {"good": [], "bad": []} for p in POOLS}
    for pool, sides in d.pools.items():
        for side, entries in sides.items():
            for e in entries:
                if e["type"] == "video":
                    manifest[pool][side].append({
                        "type": "video",
                        "url": url_for(e["storage_path"]),
                    })
                elif e["type"] == "image":
                    manifest[pool][side].append({
                        "type": "image",
                        "url": url_for(e["storage_path"]),
                    })
                elif e["type"] == "pair":
                    manifest[pool][side].append({
                        "type": "pair",
                        "original_url": url_for(e["original_storage_path"]),
                        "generation_url": url_for(e["ai_storage_path"]),
                    })
    return manifest


def _lesson_summary(d: LessonDiscovery) -> dict[str, dict[str, int]]:
    """Per-pool, per-side counts (counts entries, i.e. pairs count as 1)."""
    out: dict[str, dict[str, int]] = {p: {"good": 0, "bad": 0} for p in POOLS}
    for pool, sides in d.pools.items():
        for side, entries in sides.items():
            out[pool][side] = len(entries)
    return out


def _print_lesson_summary(d: LessonDiscovery) -> None:
    s = _lesson_summary(d)
    print("Lesson discovery summary:")
    for pool in POOLS:
        print(f"  {pool}: good={s[pool]['good']} bad={s[pool]['bad']}")
    if d.warnings:
        print("Lesson warnings:")
        for w in d.warnings:
            print(f"  ! {w}")


def _truncate(url: str, n: int = 60) -> str:
    if len(url) <= n:
        return url
    return url[: n - 3] + "..."


def _print_manifest_preview(manifest: dict) -> None:
    """Pretty-print the manifest with truncated URLs (for --dry-run)."""
    preview: dict = {}
    for pool, sides in manifest.items():
        preview[pool] = {}
        for side, entries in sides.items():
            preview[pool][side] = []
            for e in entries:
                if e["type"] == "pair":
                    preview[pool][side].append({
                        "type": "pair",
                        "original_url": _truncate(e["original_url"]),
                        "generation_url": _truncate(e["generation_url"]),
                    })
                else:
                    preview[pool][side].append({
                        "type": e["type"],
                        "url": _truncate(e["url"]),
                    })
    print("Manifest preview:")
    print(json.dumps(preview, indent=2))


def seed_lessons(
    lessons_dir: Path,
    *,
    dry_run: bool,
    verbose: bool,
) -> int:
    """Upload lesson files to the tutorial bucket and write manifest.json.
    Returns a non-zero exit code on failure."""
    if verbose:
        print(f"\nLessons dir: {lessons_dir}")
        print("Discovering lessons...")
    try:
        d = discover_lessons(lessons_dir)
    except SystemExit as e:
        print(f"lesson discovery error: {e}", file=sys.stderr)
        return 1

    _print_lesson_summary(d)

    if dry_run:
        # Build manifest with fake but realistic URLs so the preview is meaningful.
        # Avoid load_settings() here — it would require a populated .env even
        # though dry-run is supposed to work offline.
        import os as _os
        base = (_os.getenv("SUPABASE_URL") or "https://<supabase-url>").rstrip("/")
        bucket = _os.getenv("BUCKET_TUTORIAL", "tutorial")

        def fake_url(path: str) -> str:
            return f"{base}/storage/v1/object/public/{bucket}/{path}"

        manifest = build_manifest(d, fake_url)
        if verbose:
            print("\nDry run — would upload to tutorial bucket:")
            for storage_path, local in d.uploads:
                print(f"  ^ {bucket}/{storage_path}")
            _print_manifest_preview(manifest)
        return 0

    # Real run.
    from supabase_client import get_supabase  # imported here so --dry-run works offline

    sb = get_supabase()
    s = load_settings()
    bucket = s.bucket_tutorial

    if verbose:
        print(f"\nUploading {len(d.uploads)} lesson files to bucket '{bucket}'...")
    for storage_path, local in d.uploads:
        with local.open("rb") as fh:
            sb.storage.from_(bucket).upload(
                path=storage_path,
                file=fh,
                file_options={
                    "upsert": "true",
                    "content-type": _content_type(local.name),
                },
            )
        if verbose:
            print(f"  ^ {bucket}/{storage_path}")

    def url_for(path: str) -> str:
        url = _public_url(sb, bucket, path)
        if not url:
            url = _fallback_public_url(s.supabase_url, bucket, path)
        return url

    manifest = build_manifest(d, url_for)
    manifest_bytes = json.dumps(manifest, indent=2).encode("utf-8")
    sb.storage.from_(bucket).upload(
        path="manifest.json",
        file=manifest_bytes,
        file_options={"upsert": "true", "content-type": "application/json"},
    )
    manifest_url = url_for("manifest.json")
    if verbose:
        print(f"\nManifest uploaded: {manifest_url}")
        counts = _lesson_summary(d)
        print("Per-pool/side upload counts (manifest entries):")
        for pool in POOLS:
            print(f"  {pool}: good={counts[pool]['good']} bad={counts[pool]['bad']}")
    print("\nLessons seeded.")
    return 0


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


def _seed_content(content_dir: Path, *, dry_run: bool, verbose: bool) -> int:
    """Seed test_items + quiz from content_dir. Returns non-zero on failure."""
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

    if dry_run:
        if verbose:
            print("\nDry run — would upload + upsert:")
            for it in originals:
                ref = f" (ref={it.reference_storage_path})" if it.reference_storage_path else ""
                print(f"  + {it.pool}/{it.storage_path}{ref}")
            for it in dupes:
                print(f"  + {it.pool}/{it.storage_path} (dupe of {it.dupe_of_storage_path})")
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
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--content-dir",
        default=None,
        help="test-content root (skip test-item seed if omitted)",
    )
    parser.add_argument(
        "--lessons-dir",
        default=None,
        help="tutorial lessons root (skip lesson seed if omitted)",
    )
    parser.add_argument("--dry-run", action="store_true", help="discover only; no uploads/inserts")
    parser.add_argument("--quiet", action="store_true", help="suppress per-file progress")
    args = parser.parse_args(argv)

    verbose = not args.quiet

    # If neither flag is given, default --content-dir to the legacy ./content
    # directory so the previous CLI invocation `python seed.py` still works.
    if args.content_dir is None and args.lessons_dir is None:
        args.content_dir = (Path(__file__).resolve().parent.parent / "content").as_posix()

    ran_anything = False

    if args.content_dir is not None:
        content_dir = Path(args.content_dir).expanduser().resolve()
        if not content_dir.is_dir():
            print(f"content directory not found: {content_dir}", file=sys.stderr)
            return 1
        rc = _seed_content(content_dir, dry_run=args.dry_run, verbose=verbose)
        if rc != 0:
            return rc
        ran_anything = True

    if args.lessons_dir is not None:
        lessons_dir = Path(args.lessons_dir).expanduser().resolve()
        if not lessons_dir.is_dir():
            print(f"lessons directory not found: {lessons_dir}", file=sys.stderr)
            return 1
        rc = seed_lessons(lessons_dir, dry_run=args.dry_run, verbose=verbose)
        if rc != 0:
            return rc
        ran_anything = True

    if not ran_anything:
        # Shouldn't reach here given the default above, but be defensive.
        print("Nothing to do — pass --content-dir and/or --lessons-dir.", file=sys.stderr)
        return 1

    if args.dry_run:
        print("\nDry run complete.")
    else:
        print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
