#!/usr/bin/env python3
"""Microdrama Memory Manager helper CLI."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CURRENT_SCHEMA_VERSION = 2
DEFAULT_WORKSPACE_NAME = "microdrama_workspace"
DEFAULT_STYLE_LOCK_NAME = "chinese_microdrama_v1.md"
DEFAULT_TROPES = [
    "hidden heiress",
    "fake poor billionaire",
    "public humiliation",
    "secret CEO",
    "contract marriage",
    "inheritance battle",
    "revenge acquisition",
]


class MemoryError(RuntimeError):
    pass


@dataclass
class WorkspacePaths:
    root: Path
    memory_dir: Path
    stories_dir: Path
    characters_dir: Path
    style_locks_dir: Path
    assets_dir: Path
    storyboards_dir: Path
    seedance_outputs_dir: Path
    final_videos_dir: Path
    configs_dir: Path
    logs_dir: Path
    db_path: Path
    config_path: Path
    default_style_lock_path: Path


SCHEMA_SQL = [
    "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)",
    """
    CREATE TABLE IF NOT EXISTS stories (
      story_id TEXT PRIMARY KEY,
      title TEXT NOT NULL,
      logline TEXT,
      trope_primary TEXT,
      trope_secondary TEXT,
      hook_type TEXT,
      reveal_type TEXT,
      ending_type TEXT,
      virality_score REAL,
      status TEXT,
      markdown_path TEXT,
      created_at TEXT,
      updated_at TEXT,
      published_url TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS episodes (
      episode_id TEXT PRIMARY KEY,
      story_id TEXT,
      episode_number INTEGER,
      title TEXT,
      beat_summary TEXT,
      script_status TEXT,
      storyboard_status TEXT,
      video_status TEXT,
      final_video_path TEXT,
      approval_status TEXT,
      review_notes TEXT,
      revision_count INTEGER,
      approved_at TEXT,
      asset_version TEXT,
      duration_seconds REAL,
      created_at TEXT,
      updated_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS characters (
      character_id TEXT PRIMARY KEY,
      story_id TEXT,
      name TEXT,
      role TEXT,
      archetype TEXT,
      personality_summary TEXT,
      appearance_summary TEXT,
      character_sheet_path TEXT,
      markdown_path TEXT,
      created_at TEXT,
      updated_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS storyboards (
      storyboard_id TEXT PRIMARY KEY,
      story_id TEXT,
      episode_id TEXT,
      block_number INTEGER,
      shot_count INTEGER,
      prompt_text TEXT,
      image_path TEXT,
      status TEXT,
      approval_status TEXT,
      review_notes TEXT,
      revision_count INTEGER,
      approved_at TEXT,
      asset_version TEXT,
      duration_seconds REAL,
      created_at TEXT,
      updated_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS videos (
      video_id TEXT PRIMARY KEY,
      story_id TEXT,
      episode_id TEXT,
      storyboard_id TEXT,
      block_number INTEGER,
      seedance_prompt TEXT,
      raw_video_path TEXT,
      status TEXT,
      approval_status TEXT,
      review_notes TEXT,
      revision_count INTEGER,
      approved_at TEXT,
      asset_version TEXT,
      duration_seconds REAL,
      created_at TEXT,
      updated_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS trope_usage (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      trope_name TEXT UNIQUE,
      usage_count INTEGER,
      last_used_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS production_events (
      event_id TEXT PRIMARY KEY,
      story_id TEXT,
      event_type TEXT,
      event_note TEXT,
      created_at TEXT
    )
    """,
]

DEFAULT_STYLE_LOCK = """# Chinese Microdrama Style Lock v1

- Favor emotionally legible hooks.
- Keep stakes, humiliation, secrets, and reversals clear.
- Preserve character consistency across episodes.
- Treat this file as a reusable style reference, not as a story generator.
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def slug_number(prefix: str, value: int) -> str:
    return f"{prefix}_{value:03d}"


def story_numeric_suffix(story_id: str) -> int:
    try:
        return int(story_id.split("_")[-1])
    except Exception as exc:
        raise MemoryError(f"Invalid story_id format: {story_id}") from exc


def resolve_paths(workspace_root: str | None) -> WorkspacePaths:
    root = Path(workspace_root or DEFAULT_WORKSPACE_NAME).expanduser().resolve()
    memory_dir = root / "memory"
    return WorkspacePaths(
        root=root,
        memory_dir=memory_dir,
        stories_dir=memory_dir / "stories",
        characters_dir=memory_dir / "characters",
        style_locks_dir=memory_dir / "style_locks",
        assets_dir=root / "assets",
        storyboards_dir=root / "assets" / "storyboards",
        seedance_outputs_dir=root / "assets" / "seedance_outputs",
        final_videos_dir=root / "assets" / "final_videos",
        configs_dir=root / "configs",
        logs_dir=root / "logs",
        db_path=memory_dir / "microdrama_memory.db",
        config_path=root / "configs" / "microdrama_config.json",
        default_style_lock_path=memory_dir / "style_locks" / DEFAULT_STYLE_LOCK_NAME,
    )


def ensure_dirs(paths: WorkspacePaths) -> None:
    for path in [
        paths.root,
        paths.memory_dir,
        paths.stories_dir,
        paths.characters_dir,
        paths.style_locks_dir,
        paths.assets_dir,
        paths.storyboards_dir,
        paths.seedance_outputs_dir,
        paths.final_videos_dir,
        paths.configs_dir,
        paths.logs_dir,
    ]:
        path.mkdir(parents=True, exist_ok=True)


def connect_db(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def initialize_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    for sql in SCHEMA_SQL:
        cur.execute(sql)
    version_row = cur.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
    if version_row is None:
        cur.execute("INSERT INTO schema_version(version) VALUES (?)", (CURRENT_SCHEMA_VERSION,))
    conn.commit()


def seed_default_tropes(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    for trope in DEFAULT_TROPES:
        cur.execute(
            "INSERT INTO trope_usage(trope_name, usage_count, last_used_at) VALUES (?, 0, NULL) "
            "ON CONFLICT(trope_name) DO NOTHING",
            (trope,),
        )
    conn.commit()


def write_default_files(paths: WorkspacePaths) -> None:
    if not paths.default_style_lock_path.exists():
        paths.default_style_lock_path.write_text(DEFAULT_STYLE_LOCK)
    if not paths.config_path.exists():
        paths.config_path.write_text(
            json.dumps(
                {
                    "database_path": "./memory/microdrama_memory.db",
                    "default_style_lock": "chinese_microdrama_v1",
                    "max_memory_results": 20,
                    "similarity_threshold": 0.75,
                },
                indent=2,
            )
            + "\n"
        )


def bootstrap(paths: WorkspacePaths) -> dict[str, Any]:
    ensure_dirs(paths)
    conn = connect_db(paths.db_path)
    try:
        initialize_schema(conn)
        run_migrations(conn)
        seed_default_tropes(conn)
    finally:
        conn.close()
    write_default_files(paths)
    return {
        "workspace_root": str(paths.root),
        "database_path": str(paths.db_path),
        "created": True,
        "schema_version": CURRENT_SCHEMA_VERSION,
    }


def get_schema_version(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
    return int(row[0]) if row else 0


def table_has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row[1] == column for row in rows)


def ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    if not table_has_column(conn, table, column):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def run_migrations(conn: sqlite3.Connection) -> list[str]:
    applied: list[str] = []
    current = get_schema_version(conn)
    if current < 1:
        conn.execute("DELETE FROM schema_version")
        conn.execute("INSERT INTO schema_version(version) VALUES (?)", (1,))
        conn.commit()
        applied.append("init_to_v1")
        current = 1
    if current > CURRENT_SCHEMA_VERSION:
        raise MemoryError(
            f"Database schema version {current} is newer than supported version {CURRENT_SCHEMA_VERSION}."
        )
    if current < 2:
        for table in ["episodes", "storyboards", "videos"]:
            ensure_column(conn, table, "approval_status", "TEXT")
            ensure_column(conn, table, "review_notes", "TEXT")
            ensure_column(conn, table, "revision_count", "INTEGER DEFAULT 0")
            ensure_column(conn, table, "approved_at", "TEXT")
            ensure_column(conn, table, "asset_version", "TEXT")
            ensure_column(conn, table, "duration_seconds", "REAL")
        conn.execute("UPDATE schema_version SET version = ?", (2,))
        conn.commit()
        applied.append("v2_detailed_production_tracking")
    return applied


def bootstrap_if_missing(paths: WorkspacePaths) -> None:
    if not paths.db_path.exists():
        bootstrap(paths)
        return
    ensure_dirs(paths)
    write_default_files(paths)
    conn = connect_db(paths.db_path)
    try:
        initialize_schema(conn)
        run_migrations(conn)
        seed_default_tropes(conn)
    finally:
        conn.close()


def fetch_json_arg(inline: str | None, file_path: str | None, default: Any = None) -> Any:
    if inline:
        return json.loads(inline)
    if file_path:
        return json.loads(Path(file_path).read_text())
    return default


def tokenize(text: str) -> set[str]:
    return {part.strip(" ,.-_\n\t").lower() for part in text.split() if part.strip(" ,.-_\n\t")}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def check_duplicate(conn: sqlite3.Connection, payload: dict[str, Any], limit: int, threshold: float) -> dict[str, Any]:
    candidate_title = payload.get("candidate_title", "")
    candidate_tropes = [str(t).strip().lower() for t in payload.get("candidate_tropes", []) if str(t).strip()]
    candidate_tokens = tokenize(candidate_title) | set(candidate_tropes)
    rows = conn.execute(
        "SELECT story_id, title, trope_primary, trope_secondary, reveal_type, hook_type FROM stories ORDER BY updated_at DESC, created_at DESC LIMIT 200"
    ).fetchall()
    similar: list[dict[str, Any]] = []
    is_duplicate = False
    for row in rows:
        story_tokens = tokenize(row["title"] or "") | tokenize((row["trope_primary"] or "") + " " + (row["trope_secondary"] or ""))
        similarity = jaccard(candidate_tokens, story_tokens)
        same_title = (row["title"] or "").strip().lower() == candidate_title.strip().lower()
        if similarity >= threshold or same_title:
            reason_parts = []
            if same_title:
                reason_parts.append("same title")
            if row["trope_primary"] and row["trope_primary"].lower() in candidate_tropes:
                reason_parts.append("same primary trope")
            if row["trope_secondary"] and row["trope_secondary"].lower() in candidate_tropes:
                reason_parts.append("same secondary trope")
            if not reason_parts:
                reason_parts.append(f"similarity {similarity:.2f}")
            similar.append(
                {
                    "story_id": row["story_id"],
                    "title": row["title"],
                    "similarity_reason": ", ".join(reason_parts),
                    "score": round(similarity, 3),
                }
            )
            if same_title or similarity >= max(threshold, 0.9):
                is_duplicate = True
    similar = sorted(similar, key=lambda item: item["score"], reverse=True)[:limit]
    overused = overused_tropes(conn, limit=5)
    recommendation = "safe_to_use"
    if is_duplicate:
        recommendation = "change_title_or_trope_mix"
    elif similar:
        recommendation = "safe_to_use_but_change_reveal"
    elif overused and any(t["trope_name"] in candidate_tropes for t in overused):
        recommendation = "safe_to_use_but_rotate_tropes"
    return {
        "is_duplicate": is_duplicate,
        "similar_stories": [
            {k: v for k, v in item.items() if k != "score"} for item in similar
        ],
        "recommendation": recommendation,
    }


def overused_tropes(conn: sqlite3.Connection, limit: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT trope_name, usage_count, last_used_at FROM trope_usage ORDER BY usage_count DESC, trope_name ASC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows if (row["usage_count"] or 0) > 0]


def underused_tropes(conn: sqlite3.Connection, limit: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT trope_name, usage_count, last_used_at FROM trope_usage ORDER BY usage_count ASC, trope_name ASC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]


def story_memory_summary(conn: sqlite3.Connection, limit: int) -> dict[str, Any]:
    story_rows = conn.execute(
        "SELECT trope_primary, trope_secondary, hook_type, reveal_type, ending_type FROM stories ORDER BY updated_at DESC, created_at DESC LIMIT ?",
        (max(limit, 10),),
    ).fetchall()
    recent_patterns: list[str] = []
    combos: dict[str, int] = {}
    for row in story_rows:
        for key in ["trope_primary", "trope_secondary"]:
            value = row[key]
            if value and value not in recent_patterns:
                recent_patterns.append(value)
        if row["trope_primary"] and row["reveal_type"]:
            combo = f"{row['trope_primary']} + {row['reveal_type']}"
            combos[combo] = combos.get(combo, 0) + 1
    overused = [item["trope_name"] for item in overused_tropes(conn, limit=5)]
    underused = [item["trope_name"] for item in underused_tropes(conn, limit=5)]
    avoid = [name for name, count in sorted(combos.items(), key=lambda kv: kv[1], reverse=True) if count >= 2][:5]
    return {
        "recent_story_patterns": recent_patterns[:10],
        "overused_tropes": overused,
        "underused_tropes": underused,
        "avoid_combinations": avoid,
    }


def next_story_id(conn: sqlite3.Connection) -> str:
    row = conn.execute("SELECT story_id FROM stories ORDER BY story_id DESC LIMIT 1").fetchone()
    next_num = 1 if not row else story_numeric_suffix(row[0]) + 1
    return slug_number("DRAMA", next_num)


def story_markdown_path(paths: WorkspacePaths, story_id: str) -> Path:
    return paths.stories_dir / f"{story_id}.md"


def character_markdown_path(paths: WorkspacePaths, character_id: str) -> Path:
    return paths.characters_dir / f"{character_id}.md"


def increment_trope(conn: sqlite3.Connection, trope_name: str | None) -> None:
    if not trope_name:
        return
    conn.execute(
        "INSERT INTO trope_usage(trope_name, usage_count, last_used_at) VALUES (?, 1, ?) "
        "ON CONFLICT(trope_name) DO UPDATE SET usage_count = usage_count + 1, last_used_at = excluded.last_used_at",
        (trope_name, utc_now()),
    )


def write_story_markdown(path: Path, story: dict[str, Any]) -> None:
    content = [
        f"# {story['title']}",
        "",
        f"- Story ID: {story['story_id']}",
        f"- Status: {story.get('status', 'approved')}",
        f"- Primary trope: {story.get('trope_primary', '')}",
        f"- Secondary trope: {story.get('trope_secondary', '')}",
        f"- Hook type: {story.get('hook_type', '')}",
        f"- Reveal type: {story.get('reveal_type', '')}",
        f"- Ending type: {story.get('ending_type', '')}",
        f"- Virality score: {story.get('virality_score', '')}",
        "",
        "## Full Concept",
        story.get('full_concept', '') or story.get('logline', '') or '',
        "",
        "## Logline",
        story.get('logline', '') or '',
        "",
        "## Beats",
        story.get('beats', '') or '',
        "",
        "## Scripts",
        story.get('scripts', '') or '',
        "",
        "## Revisions",
        story.get('revisions', '') or '',
        "",
        "## Notes",
        story.get('notes', '') or '',
        "",
    ]
    path.write_text("\n".join(content))


def store_story(conn: sqlite3.Connection, paths: WorkspacePaths, payload: dict[str, Any]) -> dict[str, Any]:
    story_id = payload.get("story_id") or next_story_id(conn)
    now = utc_now()
    path = story_markdown_path(paths, story_id)
    story = {
        "story_id": story_id,
        "title": payload["title"],
        "logline": payload.get("logline"),
        "trope_primary": payload.get("trope_primary"),
        "trope_secondary": payload.get("trope_secondary"),
        "hook_type": payload.get("hook_type"),
        "reveal_type": payload.get("reveal_type"),
        "ending_type": payload.get("ending_type"),
        "virality_score": payload.get("virality_score"),
        "status": payload.get("status", "approved"),
        "markdown_path": str(path),
        "created_at": now,
        "updated_at": now,
        "published_url": payload.get("published_url"),
        "notes": payload.get("notes"),
        "full_concept": payload.get("full_concept"),
        "beats": payload.get("beats"),
        "scripts": payload.get("scripts"),
        "revisions": payload.get("revisions"),
    }
    conn.execute(
        """
        INSERT INTO stories (
          story_id, title, logline, trope_primary, trope_secondary, hook_type,
          reveal_type, ending_type, virality_score, status, markdown_path,
          created_at, updated_at, published_url
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            story["story_id"],
            story["title"],
            story["logline"],
            story["trope_primary"],
            story["trope_secondary"],
            story["hook_type"],
            story["reveal_type"],
            story["ending_type"],
            story["virality_score"],
            story["status"],
            story["markdown_path"],
            story["created_at"],
            story["updated_at"],
            story["published_url"],
        ),
    )
    increment_trope(conn, story["trope_primary"])
    increment_trope(conn, story["trope_secondary"])
    conn.commit()
    write_story_markdown(path, story)
    return {
        "story_id": story_id,
        "title": story["title"],
        "status": story["status"],
        "markdown_path": str(path),
    }


def next_character_id(conn: sqlite3.Connection) -> str:
    row = conn.execute("SELECT character_id FROM characters ORDER BY character_id DESC LIMIT 1").fetchone()
    next_num = 1 if not row else story_numeric_suffix(row[0]) + 1
    return slug_number("CHAR", next_num)


def next_episode_id(story_id: str, episode_number: int) -> str:
    story_num = story_numeric_suffix(story_id)
    return f"EP_{story_num:03d}_{episode_number:02d}"


def next_storyboard_id(story_id: str, episode_number: int, block_number: int) -> str:
    story_num = story_numeric_suffix(story_id)
    block_label = chr(ord("A") + max(block_number - 1, 0))
    return f"SB_{story_num:03d}_{episode_number:02d}_{block_label}"


def next_video_id(story_id: str, episode_number: int, block_number: int) -> str:
    story_num = story_numeric_suffix(story_id)
    block_label = chr(ord("A") + max(block_number - 1, 0))
    return f"VID_{story_num:03d}_{episode_number:02d}_{block_label}"


def write_character_markdown(path: Path, character: dict[str, Any]) -> None:
    content = [
        f"# {character['name']}",
        "",
        f"- Character ID: {character['character_id']}",
        f"- Story ID: {character.get('story_id', '')}",
        f"- Role: {character.get('role', '')}",
        f"- Archetype: {character.get('archetype', '')}",
        f"- Character sheet path: {character.get('character_sheet_path', '')}",
        "",
        "## Character Lore",
        character.get('character_lore', '') or '',
        "",
        "## Personality",
        character.get('personality_summary', '') or '',
        "",
        "## Appearance",
        character.get('appearance_summary', '') or '',
        "",
        "## References",
        character.get('references', '') or '',
        "",
        "## Wardrobe",
        character.get('wardrobe', '') or '',
        "",
        "## Notes",
        character.get('notes', '') or '',
        "",
    ]
    path.write_text("\n".join(content))


def store_character(conn: sqlite3.Connection, paths: WorkspacePaths, payload: dict[str, Any]) -> dict[str, Any]:
    character_id = payload.get("character_id") or next_character_id(conn)
    now = utc_now()
    path = character_markdown_path(paths, character_id)
    record = {
        "character_id": character_id,
        "story_id": payload.get("story_id"),
        "name": payload["name"],
        "role": payload.get("role"),
        "archetype": payload.get("archetype"),
        "personality_summary": payload.get("personality_summary"),
        "appearance_summary": payload.get("appearance_summary"),
        "character_sheet_path": payload.get("character_sheet_path"),
        "markdown_path": str(path),
        "created_at": now,
        "updated_at": now,
        "notes": payload.get("notes"),
        "character_lore": payload.get("character_lore"),
        "references": payload.get("references"),
        "wardrobe": payload.get("wardrobe"),
    }
    conn.execute(
        """
        INSERT INTO characters (
          character_id, story_id, name, role, archetype, personality_summary,
          appearance_summary, character_sheet_path, markdown_path, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record["character_id"],
            record["story_id"],
            record["name"],
            record["role"],
            record["archetype"],
            record["personality_summary"],
            record["appearance_summary"],
            record["character_sheet_path"],
            record["markdown_path"],
            record["created_at"],
            record["updated_at"],
        ),
    )
    conn.commit()
    write_character_markdown(path, record)
    return {
        "character_id": character_id,
        "name": record["name"],
        "story_id": record["story_id"],
        "markdown_path": str(path),
    }


def get_character_references(conn: sqlite3.Connection, payload: dict[str, Any], limit: int) -> dict[str, Any]:
    story_id = payload.get("story_id")
    name_query = payload.get("name_query")
    clauses = []
    params: list[Any] = []
    if story_id:
        clauses.append("story_id = ?")
        params.append(story_id)
    if name_query:
        clauses.append("LOWER(name) LIKE ?")
        params.append(f"%{name_query.lower()}%")
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = conn.execute(
        f"SELECT character_id, story_id, name, role, archetype, personality_summary, appearance_summary, markdown_path FROM characters {where} ORDER BY updated_at DESC LIMIT ?",
        (*params, limit),
    ).fetchall()
    return {
        "results": [
            {
                "character_id": row["character_id"],
                "story_id": row["story_id"],
                "name": row["name"],
                "role": row["role"],
                "archetype": row["archetype"],
                "summary": "; ".join(
                    part for part in [row["personality_summary"], row["appearance_summary"]] if part
                ),
                "markdown_path": row["markdown_path"],
            }
            for row in rows
        ]
    }


def create_episode(conn: sqlite3.Connection, payload: dict[str, Any]) -> dict[str, Any]:
    story_id = payload["story_id"]
    episode_number = int(payload["episode_number"])
    episode_id = payload.get("episode_id") or next_episode_id(story_id, episode_number)
    now = utc_now()
    conn.execute(
        """
        INSERT INTO episodes (
          episode_id, story_id, episode_number, title, beat_summary, script_status,
          storyboard_status, video_status, final_video_path, approval_status,
          review_notes, revision_count, approved_at, asset_version, duration_seconds,
          created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            episode_id,
            story_id,
            episode_number,
            payload.get("title"),
            payload.get("beat_summary"),
            payload.get("script_status", "not_started"),
            payload.get("storyboard_status", "not_started"),
            payload.get("video_status", "not_started"),
            payload.get("final_video_path"),
            payload.get("approval_status", "pending"),
            payload.get("review_notes"),
            int(payload.get("revision_count", 0)),
            payload.get("approved_at"),
            payload.get("asset_version"),
            payload.get("duration_seconds"),
            now,
            now,
        ),
    )
    conn.commit()
    return {
        "episode_id": episode_id,
        "story_id": story_id,
        "episode_number": episode_number,
        "script_status": payload.get("script_status", "not_started"),
    }


def update_episode_script(conn: sqlite3.Connection, payload: dict[str, Any]) -> dict[str, Any]:
    episode_id = payload["episode_id"]
    revision_increment = int(payload.get("revision_increment", 1))
    conn.execute(
        """
        UPDATE episodes
        SET title = COALESCE(?, title),
            beat_summary = COALESCE(?, beat_summary),
            script_status = COALESCE(?, script_status),
            review_notes = COALESCE(?, review_notes),
            revision_count = COALESCE(revision_count, 0) + ?,
            updated_at = ?
        WHERE episode_id = ?
        """,
        (
            payload.get("title"),
            payload.get("beat_summary"),
            payload.get("script_status", "draft"),
            payload.get("review_notes"),
            revision_increment,
            utc_now(),
            episode_id,
        ),
    )
    conn.commit()
    return get_episode_status(conn, {"episode_id": episode_id})


def approve_episode_script(conn: sqlite3.Connection, payload: dict[str, Any]) -> dict[str, Any]:
    episode_id = payload["episode_id"]
    now = utc_now()
    conn.execute(
        """
        UPDATE episodes
        SET script_status = 'approved',
            approval_status = 'approved',
            approved_at = ?,
            review_notes = COALESCE(?, review_notes),
            updated_at = ?
        WHERE episode_id = ?
        """,
        (now, payload.get("review_notes"), now, episode_id),
    )
    conn.commit()
    return get_episode_status(conn, {"episode_id": episode_id})


def get_episode_status(conn: sqlite3.Connection, payload: dict[str, Any]) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT episode_id, story_id, episode_number, title, script_status, storyboard_status,
               video_status, approval_status, review_notes, revision_count, approved_at,
               asset_version, duration_seconds, final_video_path, updated_at
        FROM episodes WHERE episode_id = ?
        """,
        (payload["episode_id"],),
    ).fetchone()
    if not row:
        raise MemoryError(f"Episode not found: {payload['episode_id']}")
    return dict(row)


def create_storyboard_block(conn: sqlite3.Connection, payload: dict[str, Any]) -> dict[str, Any]:
    story_id = payload["story_id"]
    episode_id = payload["episode_id"]
    episode_number = int(payload["episode_number"])
    block_number = int(payload["block_number"])
    storyboard_id = payload.get("storyboard_id") or next_storyboard_id(story_id, episode_number, block_number)
    now = utc_now()
    conn.execute(
        """
        INSERT INTO storyboards (
          storyboard_id, story_id, episode_id, block_number, shot_count, prompt_text,
          image_path, status, approval_status, review_notes, revision_count,
          approved_at, asset_version, duration_seconds, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            storyboard_id,
            story_id,
            episode_id,
            block_number,
            payload.get("shot_count"),
            payload.get("prompt_text"),
            payload.get("image_path"),
            payload.get("status", "not_started"),
            payload.get("approval_status", "pending"),
            payload.get("review_notes"),
            int(payload.get("revision_count", 0)),
            payload.get("approved_at"),
            payload.get("asset_version"),
            payload.get("duration_seconds"),
            now,
            now,
        ),
    )
    conn.commit()
    return {"storyboard_id": storyboard_id, "episode_id": episode_id, "block_number": block_number}


def update_storyboard_prompt(conn: sqlite3.Connection, payload: dict[str, Any]) -> dict[str, Any]:
    storyboard_id = payload["storyboard_id"]
    conn.execute(
        """
        UPDATE storyboards
        SET prompt_text = COALESCE(?, prompt_text),
            status = COALESCE(?, status),
            review_notes = COALESCE(?, review_notes),
            revision_count = COALESCE(revision_count, 0) + ?,
            updated_at = ?
        WHERE storyboard_id = ?
        """,
        (
            payload.get("prompt_text"),
            payload.get("status", "draft"),
            payload.get("review_notes"),
            int(payload.get("revision_increment", 1)),
            utc_now(),
            storyboard_id,
        ),
    )
    conn.commit()
    return get_storyboard_status(conn, storyboard_id)


def store_storyboard_image(conn: sqlite3.Connection, payload: dict[str, Any]) -> dict[str, Any]:
    storyboard_id = payload["storyboard_id"]
    conn.execute(
        """
        UPDATE storyboards
        SET image_path = ?,
            asset_version = COALESCE(?, asset_version),
            status = COALESCE(?, status),
            updated_at = ?
        WHERE storyboard_id = ?
        """,
        (
            payload["image_path"],
            payload.get("asset_version"),
            payload.get("status", "generated"),
            utc_now(),
            storyboard_id,
        ),
    )
    conn.commit()
    return get_storyboard_status(conn, storyboard_id)


def get_storyboard_status(conn: sqlite3.Connection, storyboard_id: str) -> dict[str, Any]:
    row = conn.execute(
        "SELECT * FROM storyboards WHERE storyboard_id = ?",
        (storyboard_id,),
    ).fetchone()
    if not row:
        raise MemoryError(f"Storyboard not found: {storyboard_id}")
    return dict(row)


def approve_storyboard(conn: sqlite3.Connection, payload: dict[str, Any]) -> dict[str, Any]:
    storyboard_id = payload["storyboard_id"]
    now = utc_now()
    conn.execute(
        "UPDATE storyboards SET status = 'approved', approval_status = 'approved', approved_at = ?, review_notes = COALESCE(?, review_notes), updated_at = ? WHERE storyboard_id = ?",
        (now, payload.get("review_notes"), now, storyboard_id),
    )
    conn.commit()
    return get_storyboard_status(conn, storyboard_id)


def reject_storyboard(conn: sqlite3.Connection, payload: dict[str, Any]) -> dict[str, Any]:
    storyboard_id = payload["storyboard_id"]
    conn.execute(
        "UPDATE storyboards SET status = 'rejected', approval_status = 'rejected', review_notes = COALESCE(?, review_notes), revision_count = COALESCE(revision_count, 0) + 1, updated_at = ? WHERE storyboard_id = ?",
        (payload.get("review_notes"), utc_now(), storyboard_id),
    )
    conn.commit()
    return get_storyboard_status(conn, storyboard_id)


def create_video_block(conn: sqlite3.Connection, payload: dict[str, Any]) -> dict[str, Any]:
    story_id = payload["story_id"]
    episode_id = payload["episode_id"]
    episode_number = int(payload["episode_number"])
    block_number = int(payload["block_number"])
    video_id = payload.get("video_id") or next_video_id(story_id, episode_number, block_number)
    now = utc_now()
    conn.execute(
        """
        INSERT INTO videos (
          video_id, story_id, episode_id, storyboard_id, block_number, seedance_prompt,
          raw_video_path, status, approval_status, review_notes, revision_count,
          approved_at, asset_version, duration_seconds, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            video_id,
            story_id,
            episode_id,
            payload.get("storyboard_id"),
            block_number,
            payload.get("seedance_prompt"),
            payload.get("raw_video_path"),
            payload.get("status", "not_started"),
            payload.get("approval_status", "pending"),
            payload.get("review_notes"),
            int(payload.get("revision_count", 0)),
            payload.get("approved_at"),
            payload.get("asset_version"),
            payload.get("duration_seconds"),
            now,
            now,
        ),
    )
    conn.commit()
    return {"video_id": video_id, "episode_id": episode_id, "block_number": block_number}


def get_video_status(conn: sqlite3.Connection, video_id: str) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM videos WHERE video_id = ?", (video_id,)).fetchone()
    if not row:
        raise MemoryError(f"Video not found: {video_id}")
    return dict(row)


def store_seedance_prompt(conn: sqlite3.Connection, payload: dict[str, Any]) -> dict[str, Any]:
    video_id = payload["video_id"]
    conn.execute(
        "UPDATE videos SET seedance_prompt = ?, status = COALESCE(?, status), review_notes = COALESCE(?, review_notes), revision_count = COALESCE(revision_count, 0) + ?, updated_at = ? WHERE video_id = ?",
        (
            payload["seedance_prompt"],
            payload.get("status", "prompt_ready"),
            payload.get("review_notes"),
            int(payload.get("revision_increment", 1)),
            utc_now(),
            video_id,
        ),
    )
    conn.commit()
    return get_video_status(conn, video_id)


def store_raw_video(conn: sqlite3.Connection, payload: dict[str, Any]) -> dict[str, Any]:
    video_id = payload["video_id"]
    conn.execute(
        "UPDATE videos SET raw_video_path = ?, asset_version = COALESCE(?, asset_version), duration_seconds = COALESCE(?, duration_seconds), status = COALESCE(?, status), updated_at = ? WHERE video_id = ?",
        (
            payload["raw_video_path"],
            payload.get("asset_version"),
            payload.get("duration_seconds"),
            payload.get("status", "rendered"),
            utc_now(),
            video_id,
        ),
    )
    conn.commit()
    return get_video_status(conn, video_id)


def approve_video_block(conn: sqlite3.Connection, payload: dict[str, Any]) -> dict[str, Any]:
    video_id = payload["video_id"]
    now = utc_now()
    conn.execute(
        "UPDATE videos SET status = 'approved', approval_status = 'approved', approved_at = ?, review_notes = COALESCE(?, review_notes), updated_at = ? WHERE video_id = ?",
        (now, payload.get("review_notes"), now, video_id),
    )
    conn.commit()
    return get_video_status(conn, video_id)


def reject_video_block(conn: sqlite3.Connection, payload: dict[str, Any]) -> dict[str, Any]:
    video_id = payload["video_id"]
    conn.execute(
        "UPDATE videos SET status = 'rejected', approval_status = 'rejected', review_notes = COALESCE(?, review_notes), revision_count = COALESCE(revision_count, 0) + 1, updated_at = ? WHERE video_id = ?",
        (payload.get("review_notes"), utc_now(), video_id),
    )
    conn.commit()
    return get_video_status(conn, video_id)


def get_story_production_summary(conn: sqlite3.Connection, payload: dict[str, Any]) -> dict[str, Any]:
    story_id = payload["story_id"]
    episode_rows = conn.execute(
        "SELECT episode_id, episode_number, script_status FROM episodes WHERE story_id = ? ORDER BY episode_number ASC",
        (story_id,),
    ).fetchall()
    episodes: list[dict[str, Any]] = []
    for episode in episode_rows:
        storyboards = conn.execute(
            "SELECT block_number, status FROM storyboards WHERE episode_id = ? ORDER BY block_number ASC",
            (episode["episode_id"],),
        ).fetchall()
        videos = conn.execute(
            "SELECT block_number, status FROM videos WHERE episode_id = ? ORDER BY block_number ASC",
            (episode["episode_id"],),
        ).fetchall()
        storyboard_map = {row["block_number"]: row["status"] for row in storyboards}
        video_map = {row["block_number"]: row["status"] for row in videos}
        episodes.append(
            {
                "episode_id": episode["episode_id"],
                "episode_number": episode["episode_number"],
                "script_status": episode["script_status"] or "not_started",
                "storyboards": {
                    chr(ord("A") + i - 1): storyboard_map.get(i, "not_started") for i in range(1, 4)
                },
                "videos": {
                    chr(ord("A") + i - 1): video_map.get(i, "not_started") for i in range(1, 4)
                },
            }
        )
    return {"story_id": story_id, "episodes": episodes}


def update_production_status(conn: sqlite3.Connection, payload: dict[str, Any]) -> dict[str, Any]:
    story_id = payload["story_id"]
    event_type = payload["event_type"]
    event_note = payload.get("event_note", "")
    event_id = payload.get("event_id") or str(uuid.uuid4())
    conn.execute(
        "INSERT INTO production_events(event_id, story_id, event_type, event_note, created_at) VALUES (?, ?, ?, ?, ?)",
        (event_id, story_id, event_type, event_note, utc_now()),
    )
    if payload.get("story_status"):
        conn.execute(
            "UPDATE stories SET status = ?, updated_at = ? WHERE story_id = ?",
            (payload["story_status"], utc_now(), story_id),
        )
    conn.commit()
    return {
        "story_id": story_id,
        "event_id": event_id,
        "event_type": event_type,
        "story_status": payload.get("story_status"),
    }


def with_db(args: argparse.Namespace, callback):
    paths = resolve_paths(args.workspace_root)
    bootstrap_if_missing(paths)
    conn = connect_db(paths.db_path)
    try:
        return callback(conn, paths)
    finally:
        conn.close()


def cmd_create_episode(args: argparse.Namespace) -> None:
    payload = fetch_json_arg(args.json_input, args.json_file, {})
    if not payload.get("story_id") or payload.get("episode_number") is None:
        raise MemoryError("create-episode requires story_id and episode_number")
    print(json.dumps(with_db(args, lambda conn, _paths: create_episode(conn, payload)), indent=2, ensure_ascii=False))


def cmd_update_episode_script(args: argparse.Namespace) -> None:
    payload = fetch_json_arg(args.json_input, args.json_file, {})
    if not payload.get("episode_id"):
        raise MemoryError("update-episode-script requires episode_id")
    print(json.dumps(with_db(args, lambda conn, _paths: update_episode_script(conn, payload)), indent=2, ensure_ascii=False))


def cmd_approve_episode_script(args: argparse.Namespace) -> None:
    payload = fetch_json_arg(args.json_input, args.json_file, {})
    if not payload.get("episode_id"):
        raise MemoryError("approve-episode-script requires episode_id")
    print(json.dumps(with_db(args, lambda conn, _paths: approve_episode_script(conn, payload)), indent=2, ensure_ascii=False))


def cmd_get_episode_status(args: argparse.Namespace) -> None:
    payload = fetch_json_arg(args.json_input, args.json_file, {})
    if not payload.get("episode_id"):
        raise MemoryError("get-episode-status requires episode_id")
    print(json.dumps(with_db(args, lambda conn, _paths: get_episode_status(conn, payload)), indent=2, ensure_ascii=False))


def cmd_create_storyboard_block(args: argparse.Namespace) -> None:
    payload = fetch_json_arg(args.json_input, args.json_file, {})
    for key in ["story_id", "episode_id", "episode_number", "block_number"]:
        if payload.get(key) is None:
            raise MemoryError(f"create-storyboard-block requires {key}")
    print(json.dumps(with_db(args, lambda conn, _paths: create_storyboard_block(conn, payload)), indent=2, ensure_ascii=False))


def cmd_update_storyboard_prompt(args: argparse.Namespace) -> None:
    payload = fetch_json_arg(args.json_input, args.json_file, {})
    if not payload.get("storyboard_id"):
        raise MemoryError("update-storyboard-prompt requires storyboard_id")
    print(json.dumps(with_db(args, lambda conn, _paths: update_storyboard_prompt(conn, payload)), indent=2, ensure_ascii=False))


def cmd_store_storyboard_image(args: argparse.Namespace) -> None:
    payload = fetch_json_arg(args.json_input, args.json_file, {})
    if not payload.get("storyboard_id") or not payload.get("image_path"):
        raise MemoryError("store-storyboard-image requires storyboard_id and image_path")
    print(json.dumps(with_db(args, lambda conn, _paths: store_storyboard_image(conn, payload)), indent=2, ensure_ascii=False))


def cmd_approve_storyboard(args: argparse.Namespace) -> None:
    payload = fetch_json_arg(args.json_input, args.json_file, {})
    if not payload.get("storyboard_id"):
        raise MemoryError("approve-storyboard requires storyboard_id")
    print(json.dumps(with_db(args, lambda conn, _paths: approve_storyboard(conn, payload)), indent=2, ensure_ascii=False))


def cmd_reject_storyboard(args: argparse.Namespace) -> None:
    payload = fetch_json_arg(args.json_input, args.json_file, {})
    if not payload.get("storyboard_id"):
        raise MemoryError("reject-storyboard requires storyboard_id")
    print(json.dumps(with_db(args, lambda conn, _paths: reject_storyboard(conn, payload)), indent=2, ensure_ascii=False))


def cmd_create_video_block(args: argparse.Namespace) -> None:
    payload = fetch_json_arg(args.json_input, args.json_file, {})
    for key in ["story_id", "episode_id", "episode_number", "block_number"]:
        if payload.get(key) is None:
            raise MemoryError(f"create-video-block requires {key}")
    print(json.dumps(with_db(args, lambda conn, _paths: create_video_block(conn, payload)), indent=2, ensure_ascii=False))


def cmd_store_seedance_prompt(args: argparse.Namespace) -> None:
    payload = fetch_json_arg(args.json_input, args.json_file, {})
    if not payload.get("video_id") or not payload.get("seedance_prompt"):
        raise MemoryError("store-seedance-prompt requires video_id and seedance_prompt")
    print(json.dumps(with_db(args, lambda conn, _paths: store_seedance_prompt(conn, payload)), indent=2, ensure_ascii=False))


def cmd_store_raw_video(args: argparse.Namespace) -> None:
    payload = fetch_json_arg(args.json_input, args.json_file, {})
    if not payload.get("video_id") or not payload.get("raw_video_path"):
        raise MemoryError("store-raw-video requires video_id and raw_video_path")
    print(json.dumps(with_db(args, lambda conn, _paths: store_raw_video(conn, payload)), indent=2, ensure_ascii=False))


def cmd_approve_video_block(args: argparse.Namespace) -> None:
    payload = fetch_json_arg(args.json_input, args.json_file, {})
    if not payload.get("video_id"):
        raise MemoryError("approve-video-block requires video_id")
    print(json.dumps(with_db(args, lambda conn, _paths: approve_video_block(conn, payload)), indent=2, ensure_ascii=False))


def cmd_reject_video_block(args: argparse.Namespace) -> None:
    payload = fetch_json_arg(args.json_input, args.json_file, {})
    if not payload.get("video_id"):
        raise MemoryError("reject-video-block requires video_id")
    print(json.dumps(with_db(args, lambda conn, _paths: reject_video_block(conn, payload)), indent=2, ensure_ascii=False))


def cmd_get_story_production_summary(args: argparse.Namespace) -> None:
    payload = fetch_json_arg(args.json_input, args.json_file, {})
    if not payload.get("story_id"):
        raise MemoryError("get-story-production-summary requires story_id")
    print(json.dumps(with_db(args, lambda conn, _paths: get_story_production_summary(conn, payload)), indent=2, ensure_ascii=False))


def cmd_bootstrap(args: argparse.Namespace) -> None:
    paths = resolve_paths(args.workspace_root)
    print(json.dumps(bootstrap(paths), indent=2, ensure_ascii=False))


def cmd_migrate(args: argparse.Namespace) -> None:
    paths = resolve_paths(args.workspace_root)
    bootstrap_if_missing(paths)
    conn = connect_db(paths.db_path)
    try:
        applied = run_migrations(conn)
        print(json.dumps({"schema_version": get_schema_version(conn), "applied": applied}, indent=2))
    finally:
        conn.close()


def cmd_check_duplicate(args: argparse.Namespace) -> None:
    paths = resolve_paths(args.workspace_root)
    bootstrap_if_missing(paths)
    conn = connect_db(paths.db_path)
    try:
        payload = fetch_json_arg(args.json_input, args.json_file, {})
        cfg = json.loads(paths.config_path.read_text()) if paths.config_path.exists() else {}
        threshold = args.threshold if args.threshold is not None else cfg.get("similarity_threshold", 0.75)
        result = check_duplicate(conn, payload, args.limit, threshold)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    finally:
        conn.close()


def cmd_summary(args: argparse.Namespace) -> None:
    paths = resolve_paths(args.workspace_root)
    bootstrap_if_missing(paths)
    conn = connect_db(paths.db_path)
    try:
        print(json.dumps(story_memory_summary(conn, args.limit), indent=2, ensure_ascii=False))
    finally:
        conn.close()


def cmd_store_story(args: argparse.Namespace) -> None:
    paths = resolve_paths(args.workspace_root)
    bootstrap_if_missing(paths)
    conn = connect_db(paths.db_path)
    try:
        payload = fetch_json_arg(args.json_input, args.json_file, {})
        if not payload.get("title"):
            raise MemoryError("store-story requires title")
        print(json.dumps(store_story(conn, paths, payload), indent=2, ensure_ascii=False))
    finally:
        conn.close()


def cmd_store_character(args: argparse.Namespace) -> None:
    paths = resolve_paths(args.workspace_root)
    bootstrap_if_missing(paths)
    conn = connect_db(paths.db_path)
    try:
        payload = fetch_json_arg(args.json_input, args.json_file, {})
        if not payload.get("name"):
            raise MemoryError("store-character requires name")
        print(json.dumps(store_character(conn, paths, payload), indent=2, ensure_ascii=False))
    finally:
        conn.close()


def cmd_get_characters(args: argparse.Namespace) -> None:
    paths = resolve_paths(args.workspace_root)
    bootstrap_if_missing(paths)
    conn = connect_db(paths.db_path)
    try:
        payload = fetch_json_arg(args.json_input, args.json_file, {})
        print(json.dumps(get_character_references(conn, payload, args.limit), indent=2, ensure_ascii=False))
    finally:
        conn.close()


def cmd_update_status(args: argparse.Namespace) -> None:
    paths = resolve_paths(args.workspace_root)
    bootstrap_if_missing(paths)
    conn = connect_db(paths.db_path)
    try:
        payload = fetch_json_arg(args.json_input, args.json_file, {})
        for required in ["story_id", "event_type"]:
            if not payload.get(required):
                raise MemoryError(f"update-status requires {required}")
        print(json.dumps(update_production_status(conn, payload), indent=2, ensure_ascii=False))
    finally:
        conn.close()


def cmd_recent(args: argparse.Namespace) -> None:
    paths = resolve_paths(args.workspace_root)
    bootstrap_if_missing(paths)
    conn = connect_db(paths.db_path)
    try:
        rows = conn.execute(
            "SELECT story_id, title, trope_primary, trope_secondary, status, updated_at FROM stories ORDER BY updated_at DESC, created_at DESC LIMIT ?",
            (args.limit,),
        ).fetchall()
        print(json.dumps({
            "stories": [
                {
                    "story_id": row["story_id"],
                    "title": row["title"],
                    "tropes": [v for v in [row["trope_primary"], row["trope_secondary"]] if v],
                    "status": row["status"],
                    "updated_at": row["updated_at"],
                }
                for row in rows
            ]
        }, indent=2, ensure_ascii=False))
    finally:
        conn.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Microdrama Memory Manager")
    parser.add_argument("--workspace-root", help="Workspace root (default: ./microdrama_workspace)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("bootstrap", help="Create workspace, db, config, folders, and default data")
    p.set_defaults(func=cmd_bootstrap)

    p = sub.add_parser("migrate", help="Run schema migrations")
    p.set_defaults(func=cmd_migrate)

    p = sub.add_parser("check-duplicate", help="Summarize duplicate risk for a candidate story")
    p.add_argument("--json-input")
    p.add_argument("--json-file")
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--threshold", type=float)
    p.set_defaults(func=cmd_check_duplicate)

    p = sub.add_parser("summary", help="Return compact story memory summary")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=cmd_summary)

    p = sub.add_parser("store-story", help="Store approved story metadata")
    p.add_argument("--json-input")
    p.add_argument("--json-file")
    p.set_defaults(func=cmd_store_story)

    p = sub.add_parser("store-character", help="Store character metadata and archive")
    p.add_argument("--json-input")
    p.add_argument("--json-file")
    p.set_defaults(func=cmd_store_character)

    p = sub.add_parser("create-episode", help="Create an episode state record")
    p.add_argument("--json-input")
    p.add_argument("--json-file")
    p.set_defaults(func=cmd_create_episode)

    p = sub.add_parser("update-episode-script", help="Update episode script progress and revision state")
    p.add_argument("--json-input")
    p.add_argument("--json-file")
    p.set_defaults(func=cmd_update_episode_script)

    p = sub.add_parser("approve-episode-script", help="Mark an episode script as approved")
    p.add_argument("--json-input")
    p.add_argument("--json-file")
    p.set_defaults(func=cmd_approve_episode_script)

    p = sub.add_parser("get-episode-status", help="Fetch concise episode production state")
    p.add_argument("--json-input")
    p.add_argument("--json-file")
    p.set_defaults(func=cmd_get_episode_status)

    p = sub.add_parser("create-storyboard-block", help="Create a storyboard block state record")
    p.add_argument("--json-input")
    p.add_argument("--json-file")
    p.set_defaults(func=cmd_create_storyboard_block)

    p = sub.add_parser("update-storyboard-prompt", help="Store or revise storyboard prompt state")
    p.add_argument("--json-input")
    p.add_argument("--json-file")
    p.set_defaults(func=cmd_update_storyboard_prompt)

    p = sub.add_parser("store-storyboard-image", help="Store storyboard image path and asset metadata")
    p.add_argument("--json-input")
    p.add_argument("--json-file")
    p.set_defaults(func=cmd_store_storyboard_image)

    p = sub.add_parser("approve-storyboard", help="Approve a storyboard block")
    p.add_argument("--json-input")
    p.add_argument("--json-file")
    p.set_defaults(func=cmd_approve_storyboard)

    p = sub.add_parser("reject-storyboard", help="Reject a storyboard block and increment revision tracking")
    p.add_argument("--json-input")
    p.add_argument("--json-file")
    p.set_defaults(func=cmd_reject_storyboard)

    p = sub.add_parser("create-video-block", help="Create a video block state record")
    p.add_argument("--json-input")
    p.add_argument("--json-file")
    p.set_defaults(func=cmd_create_video_block)

    p = sub.add_parser("store-seedance-prompt", help="Store or revise a Seedance prompt reference")
    p.add_argument("--json-input")
    p.add_argument("--json-file")
    p.set_defaults(func=cmd_store_seedance_prompt)

    p = sub.add_parser("store-raw-video", help="Store raw video path and asset metadata")
    p.add_argument("--json-input")
    p.add_argument("--json-file")
    p.set_defaults(func=cmd_store_raw_video)

    p = sub.add_parser("approve-video-block", help="Approve a video block")
    p.add_argument("--json-input")
    p.add_argument("--json-file")
    p.set_defaults(func=cmd_approve_video_block)

    p = sub.add_parser("reject-video-block", help="Reject a video block and increment revision tracking")
    p.add_argument("--json-input")
    p.add_argument("--json-file")
    p.set_defaults(func=cmd_reject_video_block)

    p = sub.add_parser("get-story-production-summary", help="Return concise multi-episode production progress")
    p.add_argument("--json-input")
    p.add_argument("--json-file")
    p.set_defaults(func=cmd_get_story_production_summary)

    p = sub.add_parser("get-characters", help="Retrieve concise character references")
    p.add_argument("--json-input")
    p.add_argument("--json-file")
    p.add_argument("--limit", type=int, default=10)
    p.set_defaults(func=cmd_get_characters)

    p = sub.add_parser("update-status", help="Store production workflow event")
    p.add_argument("--json-input")
    p.add_argument("--json-file")
    p.set_defaults(func=cmd_update_status)

    p = sub.add_parser("recent-stories", help="List recent stories as compact summaries")
    p.add_argument("--limit", type=int, default=10)
    p.set_defaults(func=cmd_recent)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
        return 0
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 2
    except MemoryError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
