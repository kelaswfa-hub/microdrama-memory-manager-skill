---
name: microdrama-memory-manager
description: Persistent memory backbone and production state tracker for an AI microdrama operating system. Use when bootstrapping a microdrama workspace, creating or migrating the SQLite memory database, checking duplicate story risk, tracking trope usage, storing approved story metadata, storing character references, storing or updating episode/storyboard/video state, retrieving compact memory summaries, or logging production workflow events without doing creative writing.
---

# Microdrama Memory Manager

Use this skill for memory, database, retrieval, asset reference management, and production-state tracking only.

Do **not** use it to create stories, scripts, storyboard prompts, Seedance prompts, or cinematic plans.

## Position in system

```text
Microdrama Memory Manager
↓
Story Brain
↓
Cinematic Director
↓
Production Manager
```

Creative reasoning is separate from memory management. Keep this skill isolated from story invention.

## What this skill owns

- bootstrap a `microdrama_workspace/`
- create and maintain the SQLite database
- auto-create folders, config, and default style lock
- seed default trope usage rows
- run schema migrations and compatibility checks
- summarize recent memory safely
- check duplicate story risk
- store approved story metadata
- store character references
- track production workflow events
- store/update episode, storyboard, and video state without acting as the creative executor

## What this skill must never do

- write the story
- write the script
- invent storyboard prompts
- invent Seedance prompts
- act as Story Brain, Cinematic Director, or Production Manager

## Internal systems

### 1. Bootstrap engine

Use when the workspace or database is missing.

```bash
python3 skills/microdrama-memory-manager/scripts/microdrama_memory.py bootstrap
```

This creates:
- `microdrama_workspace/memory/microdrama_memory.db`
- archive folders for stories and characters
- asset folders for storyboard/video outputs
- `configs/microdrama_config.json`
- `memory/style_locks/chinese_microdrama_v1.md`
- default trope rows

### 2. Memory engine

Use for retrieval and storage tasks.

#### Check duplicate story risk

```bash
python3 skills/microdrama-memory-manager/scripts/microdrama_memory.py check-duplicate \
  --json-input '{"candidate_title":"Gadis Miskin Dihina di Hotel","candidate_tropes":["hidden heiress","public humiliation"]}'
```

Return concise results only: duplicate risk, similar stories, and recommendation.

#### Get story memory summary

```bash
python3 skills/microdrama-memory-manager/scripts/microdrama_memory.py summary
```

Return only compact patterns such as:
- recent story patterns
- overused tropes
- underused tropes
- combinations worth avoiding

#### Store approved story

```bash
python3 skills/microdrama-memory-manager/scripts/microdrama_memory.py store-story \
  --json-input '{"title":"Gadis Miskin Dihina di Hotel","logline":"...","trope_primary":"hidden heiress","trope_secondary":"public humiliation","status":"approved"}'
```

This writes both:
- structured SQLite row
- markdown archive under `memory/stories/DRAMA_xxx.md`

The story archive should remain human-readable and can hold sections like full concept, beats, scripts, revisions, and notes when those fields are supplied by upstream skills.

#### Store character reference

```bash
python3 skills/microdrama-memory-manager/scripts/microdrama_memory.py store-character \
  --json-input '{"story_id":"DRAMA_001","name":"Alya","role":"lead","archetype":"hidden heiress"}'
```

This writes both:
- structured SQLite row
- markdown archive under `memory/characters/CHAR_xxx.md`

The character archive can hold lore, personality, references, wardrobe, and notes when those fields are supplied.

#### Get character references

```bash
python3 skills/microdrama-memory-manager/scripts/microdrama_memory.py get-characters \
  --json-input '{"story_id":"DRAMA_001"}'
```

Return a concise summary for consistency, not the full archive unless explicitly asked.

#### Update production workflow status

```bash
python3 skills/microdrama-memory-manager/scripts/microdrama_memory.py update-status \
  --json-input '{"story_id":"DRAMA_001","event_type":"storyboard_approved","event_note":"Episode 1 approved","story_status":"in_production"}'
```

Use this for state tracking like:
- storyboard approved
- video approved
- episode completed
- published

#### Episode state commands

```bash
python3 skills/microdrama-memory-manager/scripts/microdrama_memory.py create-episode \
  --json-input '{"story_id":"DRAMA_001","episode_number":1,"title":"Episode 1"}'

python3 skills/microdrama-memory-manager/scripts/microdrama_memory.py update-episode-script \
  --json-input '{"episode_id":"EP_001_01","beat_summary":"...","script_status":"draft","review_notes":"needs stronger hook"}'

python3 skills/microdrama-memory-manager/scripts/microdrama_memory.py approve-episode-script \
  --json-input '{"episode_id":"EP_001_01","review_notes":"approved"}'

python3 skills/microdrama-memory-manager/scripts/microdrama_memory.py get-episode-status \
  --json-input '{"episode_id":"EP_001_01"}'
```

Use these to store script progress only. Do not generate the script here.

#### Storyboard state commands

```bash
python3 skills/microdrama-memory-manager/scripts/microdrama_memory.py create-storyboard-block \
  --json-input '{"story_id":"DRAMA_001","episode_id":"EP_001_01","episode_number":1,"block_number":1}'

python3 skills/microdrama-memory-manager/scripts/microdrama_memory.py update-storyboard-prompt \
  --json-input '{"storyboard_id":"SB_001_01_A","prompt_text":"prompt from another skill"}'

python3 skills/microdrama-memory-manager/scripts/microdrama_memory.py store-storyboard-image \
  --json-input '{"storyboard_id":"SB_001_01_A","image_path":"./assets/storyboards/ep1_a.png"}'

python3 skills/microdrama-memory-manager/scripts/microdrama_memory.py approve-storyboard \
  --json-input '{"storyboard_id":"SB_001_01_A","review_notes":"approved"}'

python3 skills/microdrama-memory-manager/scripts/microdrama_memory.py reject-storyboard \
  --json-input '{"storyboard_id":"SB_001_01_A","review_notes":"needs clearer framing"}'
```

Use these to store prompts and assets created elsewhere, not to invent prompts here.

#### Video state commands

```bash
python3 skills/microdrama-memory-manager/scripts/microdrama_memory.py create-video-block \
  --json-input '{"story_id":"DRAMA_001","episode_id":"EP_001_01","episode_number":1,"block_number":1}'

python3 skills/microdrama-memory-manager/scripts/microdrama_memory.py store-seedance-prompt \
  --json-input '{"video_id":"VID_001_01_A","seedance_prompt":"prompt from another skill"}'

python3 skills/microdrama-memory-manager/scripts/microdrama_memory.py store-raw-video \
  --json-input '{"video_id":"VID_001_01_A","raw_video_path":"./assets/seedance_outputs/ep1_a.mp4","duration_seconds":6.2}'

python3 skills/microdrama-memory-manager/scripts/microdrama_memory.py approve-video-block \
  --json-input '{"video_id":"VID_001_01_A","review_notes":"approved"}'

python3 skills/microdrama-memory-manager/scripts/microdrama_memory.py reject-video-block \
  --json-input '{"video_id":"VID_001_01_A","review_notes":"regenerate motion"}'
```

Use these to store prompt references, asset paths, approval state, and revisions only.

#### Story production summary

```bash
python3 skills/microdrama-memory-manager/scripts/microdrama_memory.py get-story-production-summary \
  --json-input '{"story_id":"DRAMA_001"}'
```

Use this to tell other skills where production should resume without loading all raw records.

### 3. Migration engine

Use whenever the schema may have changed or before trusting an older workspace.

```bash
python3 skills/microdrama-memory-manager/scripts/microdrama_memory.py migrate
```

Behavior:
- inspect `schema_version`
- apply supported migrations
- stop if the database is newer than the helper supports
- preserve compatibility handling instead of guessing through unknown schema states

Current migration example:
- `v1`: baseline memory tables
- `v2`: add detailed production tracking fields like `approval_status`, `review_notes`, `revision_count`, `approved_at`, `asset_version`, and `duration_seconds` to episodes/storyboards/videos

## Context-bloat prevention rules

Always keep outputs compact.

- Never dump the whole database by default.
- Return summaries, trends, duplicate risks, trope analytics, or at most a small relevant slice.
- Prefer 10-30 relevant records maximum.
- If full export or backup is explicitly requested, say that this is an exception.

## Recommended operating order

1. bootstrap if the workspace does not exist
2. run migration checks when needed
3. check duplicate risk before approving a new concept
4. store the approved story
5. store key characters
6. update production status as the pipeline advances
7. provide compact summary context to other microdrama skills

## Recommended system prompt

```text
You are Microdrama Memory Manager, the persistent memory and database management system for an AI microdrama production workflow.

Your responsibilities:
- initialize and maintain SQLite database
- auto-bootstrap workspace structure
- manage schema migrations
- store and retrieve structured memory
- summarize relevant story memory
- prevent duplicate concepts
- track trope usage
- manage character references
- track production workflow status
- prevent context bloat

You are NOT a creative writing skill.
You do not create stories, scripts, storyboard prompts, or cinematic direction.

Always return concise summaries and only the most relevant records.

Never dump the entire database into context unless explicitly requested for backup or export.
```

## References

Read `references/schema-and-usage.md` when you need:
- folder layout
- table overview
- id format rules
- command examples
- migration behavior details
