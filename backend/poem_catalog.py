import hashlib
import json
import re
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from database import get_connection, initialize_database
from poems import row_to_poem


router = APIRouter()

PUNCTUATION_RE = re.compile(r"[\s，。！？；：、‘’“”（）《》〈〉,.!?;:'\"()\[\]{}<>·—-]+")
AGE_LEVELS = {"age_3_4", "age_5_7"}


class VerifiedPoemCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    author: str
    dynasty: str = ""
    content: List[str]
    translation: str = ""
    tags: List[str] = Field(default_factory=list)
    age_level: str = "age_5_7"
    age_range: str = "5-7岁"
    difficulty: int = Field(default=2, ge=1, le=5)
    theme_tags: List[str] = Field(default_factory=list)
    knowledge_tags: List[str] = Field(default_factory=list)
    source_url: str = ""
    source_version: str = ""


class ResolvePoemsRequest(BaseModel):
    recognized_text: str = ""
    candidates: List[VerifiedPoemCandidate] = Field(default_factory=list)
    auto_insert: bool = True


def normalize_poem_text(value: str) -> str:
    return PUNCTUATION_RE.sub("", value or "").lower()


def poem_content_hash(content: List[str]) -> str:
    normalized = normalize_poem_text("".join(content))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest() if normalized else ""


def _clean_list(values: List[str]) -> List[str]:
    return list(dict.fromkeys(item.strip() for item in values if item and item.strip()))


def validate_verified_candidate(candidate: VerifiedPoemCandidate) -> List[str]:
    errors = []
    if not candidate.title.strip():
        errors.append("标题不能为空")
    if not candidate.author.strip():
        errors.append("作者不能为空")
    lines = _clean_list(candidate.content)
    if len(lines) < 2 or any(len(normalize_poem_text(line)) < 2 for line in lines):
        errors.append("正文至少包含两句有效诗句")
    if len(normalize_poem_text("".join(lines))) < 8:
        errors.append("正文过短，无法可靠入库")
    if candidate.age_level not in AGE_LEVELS:
        errors.append("age_level 仅支持 age_3_4 或 age_5_7")
    from tag_rules import validate_tag_metadata
    errors.extend(validate_tag_metadata(candidate.model_dump()))
    return errors


def _find_existing(connection, candidate: VerifiedPoemCandidate):
    content_hash = poem_content_hash(candidate.content)
    if content_hash:
        row = connection.execute(
            "SELECT * FROM poems WHERE content_hash = ? LIMIT 1", (content_hash,)
        ).fetchone()
        if row:
            return row, "content_hash"

    rows = connection.execute(
        "SELECT * FROM poems WHERE title = ? AND author = ?",
        (candidate.title.strip(), candidate.author.strip()),
    ).fetchall()
    if not rows:
        return None, ""

    candidate_text = normalize_poem_text("".join(candidate.content))
    for row in rows:
        stored = json.loads(row["content_json"] or "[]")
        if normalize_poem_text("".join(stored)) == candidate_text:
            return row, "title_author_content"
    return "conflict", "title_author_conflict"


def _backfill_hashes(connection) -> None:
    rows = connection.execute(
        "SELECT id, content_json FROM poems WHERE content_hash = '' OR content_hash IS NULL"
    ).fetchall()
    for row in rows:
        try:
            content = json.loads(row["content_json"] or "[]")
        except json.JSONDecodeError:
            content = []
        connection.execute(
            "UPDATE poems SET content_hash = ? WHERE id = ?",
            (poem_content_hash(content), row["id"]),
        )


def _next_poem_id(connection) -> str:
    """Allocate the next regular poem ID, starting at poem_301.

    The caller holds a BEGIN IMMEDIATE transaction, so concurrent writers cannot
    receive the same ID.
    """
    rows = connection.execute("SELECT id FROM poems WHERE id LIKE 'poem_%'").fetchall()
    numbers = []
    for row in rows:
        match = re.fullmatch(r"poem_(\d+)", row["id"] or "")
        if match:
            numbers.append(int(match.group(1)))
    return f"poem_{max([300, *numbers]) + 1:03d}"


def _insert_verified_poem(connection, candidate: VerifiedPoemCandidate):
    poem_id = _next_poem_id(connection)
    now = datetime.now(timezone.utc).isoformat()
    content = _clean_list(candidate.content)
    connection.execute(
        """
        INSERT INTO poems (
            id, title, author, dynasty, content_json, translation, tags_json,
            age_level, age_range, difficulty, theme_tags_json,
            knowledge_tags_json, recommend_reason, content_hash, library_scope,
            source_name, source_url, source_version, verification_status,
            content_complete, recommend_eligible, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '', ?, 'core',
                  ?, ?, ?, 'verified', 1, 1, ?, ?)
        """,
        (
            poem_id, candidate.title.strip(), candidate.author.strip(),
            candidate.dynasty.strip(), json.dumps(content, ensure_ascii=False),
            candidate.translation.strip(),
            json.dumps(_clean_list(candidate.tags), ensure_ascii=False),
            candidate.age_level, candidate.age_range.strip(), candidate.difficulty,
            json.dumps(_clean_list(candidate.theme_tags), ensure_ascii=False),
            json.dumps(_clean_list(candidate.knowledge_tags), ensure_ascii=False),
            poem_content_hash(content), "cloud_verified_poem",
            candidate.source_url.strip(), candidate.source_version.strip(), now, now,
        ),
    )
    return connection.execute("SELECT * FROM poems WHERE id = ?", (poem_id,)).fetchone()


def _as_frontend_poem(row):
    poem = row_to_poem(row)
    poem.pop("source_name", None)
    poem.pop("verification_status", None)
    poem["poem_id"] = poem["id"]
    return poem


def resolve_verified_poems(request: ResolvePoemsRequest, db_path: Optional[str] = None):
    initialize_database(db_path)
    resolved = []
    rejected = []
    connection = get_connection(db_path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        _backfill_hashes(connection)
        for candidate in request.candidates:
            errors = validate_verified_candidate(candidate)
            if errors:
                rejected.append({"title": candidate.title, "errors": errors})
                continue

            existing, match_type = _find_existing(connection, candidate)
            if existing == "conflict":
                rejected.append({
                    "title": candidate.title,
                    "errors": ["同标题、作者已存在，但正文不一致，禁止自动覆盖"],
                })
                continue
            if existing is not None:
                poem = _as_frontend_poem(existing)
                poem["resolution"] = "reused"
                poem["match_type"] = match_type
                resolved.append(poem)
                continue
            if not request.auto_insert:
                rejected.append({"title": candidate.title, "errors": ["正式库未命中且未开启自动入库"]})
                continue

            poem = _as_frontend_poem(_insert_verified_poem(connection, candidate))
            poem["resolution"] = "inserted"
            poem["match_type"] = "verified_new_poem"
            resolved.append(poem)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    return {
        "success": bool(resolved),
        "poems": resolved,
        "rejected": rejected,
        "recognized_text": request.recognized_text,
    }


@router.post("/poems/resolve")
def resolve_poems(request: ResolvePoemsRequest):
    """Reuse existing poems or insert cloud-verified poems into the poems table."""
    return resolve_verified_poems(request)
