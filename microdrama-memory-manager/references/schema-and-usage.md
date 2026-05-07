# Microdrama Memory Manager Reference

## Purpose

Use this skill as the persistent memory backbone and production state tracker for a microdrama production system.
It manages workspace bootstrap, SQLite schema, migration safety, duplicate checks,
trope tracking, character references, production-event tracking, and detailed episode/storyboard/video state.

It does **not** create stories, scripts, storyboard prompts, Seedance prompts, or cinematic plans.

## Workspace bootstrap

Default root:

```text
./microdrama_workspace/
```

Created structure:

```text
microdrama_workspace/
├── memory/
│   ├── microdrama_memory.db
│   ├── stories/
│   ├── characters/
│   └── style_locks/
├── assets/
│   ├── storyboards/
│   ├── seedance_outputs/
│   └── final_videos/
├── configs/
└── logs/
```

Also created automatically:
- `configs/microdrama_config.json`
- `memory/style_locks/chinese_microdrama_v1.md`
- default trope library rows in `trope_usage`

## SQLite schema

Tables:
- `schema_version`
- `stories`
- `episodes`
- `characters`
- `storyboards`
- `videos`
- `trope_usage`
- `production_events`

Current schema version: `1`

Migration note:
- v1 covers `stories`, `episodes`, `characters`, `storyboards`, `videos`, `trope_usage`, `production_events`, and `schema_version`
- v2 adds detailed production-tracking fields to `episodes`, `storyboards`, and `videos`:
  - `approval_status`
  - `review_notes`
  - `revision_count`
  - `approved_at`
  - `asset_version`
  - `duration_seconds`

## ID formats

- Story: `DRAMA_001`
- Episode: `EP_001_01`
- Character: `CHAR_001`
- Storyboard: `SB_001_01_A`
- Video: `VID_001_01_A`

The helper CLI auto-generates story and character ids. Episode/storyboard/video ids can be generated upstream by workflow-specific skills if needed.

## Core commands

### Bootstrap

```bash
python3 skills/microdrama-memory-manager/scripts/microdrama_memory.py bootstrap
```

### Migrate

```bash
python3 skills/microdrama-memory-manager/scripts/microdrama_memory.py migrate
```

### Check duplicate story risk

```bash
python3 skills/microdrama-memory-manager/scripts/microdrama_memory.py check-duplicate \
  --json-input '{"candidate_title":"Gadis Miskin Dihina di Hotel","candidate_tropes":["hidden heiress","public humiliation"]}'
```

### Get summarized memory context

```bash
python3 skills/microdrama-memory-manager/scripts/microdrama_memory.py summary
```

### Store approved story

```bash
python3 skills/microdrama-memory-manager/scripts/microdrama_memory.py store-story \
  --json-input '{"title":"Gadis Miskin Dihina di Hotel","logline":"...","full_concept":"...","beats":"...","scripts":"...","revisions":"...","trope_primary":"hidden heiress","trope_secondary":"public humiliation","status":"approved"}'
```

### Store character

```bash
python3 skills/microdrama-memory-manager/scripts/microdrama_memory.py store-character \
  --json-input '{"story_id":"DRAMA_001","name":"Alya","role":"lead","archetype":"hidden heiress","character_lore":"...","references":"...","wardrobe":"..."}'
```

### Episode state tracking

```bash
python3 skills/microdrama-memory-manager/scripts/microdrama_memory.py create-episode \
  --json-input '{"story_id":"DRAMA_001","episode_number":1,"title":"Episode 1"}'

python3 skills/microdrama-memory-manager/scripts/microdrama_memory.py update-episode-script \
  --json-input '{"episode_id":"EP_001_01","beat_summary":"...","script_status":"draft"}'

python3 skills/microdrama-memory-manager/scripts/microdrama_memory.py approve-episode-script \
  --json-input '{"episode_id":"EP_001_01","review_notes":"approved"}'

python3 skills/microdrama-memory-manager/scripts/microdrama_memory.py get-episode-status \
  --json-input '{"episode_id":"EP_001_01"}'
```

### Storyboard state tracking

```bash
python3 skills/microdrama-memory-manager/scripts/microdrama_memory.py create-storyboard-block \
  --json-input '{"story_id":"DRAMA_001","episode_id":"EP_001_01","episode_number":1,"block_number":1}'

python3 skills/microdrama-memory-manager/scripts/microdrama_memory.py update-storyboard-prompt \
  --json-input '{"storyboard_id":"SB_001_01_A","prompt_text":"prompt from another skill"}'

python3 skills/microdrama-memory-manager/scripts/microdrama_memory.py store-storyboard-image \
  --json-input '{"storyboard_id":"SB_001_01_A","image_path":"./assets/storyboards/ep1_a.png"}'

python3 skills/microdrama-memory-manager/scripts/microdrama_memory.py approve-storyboard \
  --json-input '{"storyboard_id":"SB_001_01_A"}'

python3 skills/microdrama-memory-manager/scripts/microdrama_memory.py reject-storyboard \
  --json-input '{"storyboard_id":"SB_001_01_A","review_notes":"revise framing"}'
```

### Video state tracking

```bash
python3 skills/microdrama-memory-manager/scripts/microdrama_memory.py create-video-block \
  --json-input '{"story_id":"DRAMA_001","episode_id":"EP_001_01","episode_number":1,"block_number":1}'

python3 skills/microdrama-memory-manager/scripts/microdrama_memory.py store-seedance-prompt \
  --json-input '{"video_id":"VID_001_01_A","seedance_prompt":"prompt from another skill"}'

python3 skills/microdrama-memory-manager/scripts/microdrama_memory.py store-raw-video \
  --json-input '{"video_id":"VID_001_01_A","raw_video_path":"./assets/seedance_outputs/ep1_a.mp4","duration_seconds":6.2}'

python3 skills/microdrama-memory-manager/scripts/microdrama_memory.py approve-video-block \
  --json-input '{"video_id":"VID_001_01_A"}'

python3 skills/microdrama-memory-manager/scripts/microdrama_memory.py reject-video-block \
  --json-input '{"video_id":"VID_001_01_A","review_notes":"needs regeneration"}'
```

### Story production summary

```bash
python3 skills/microdrama-memory-manager/scripts/microdrama_memory.py get-story-production-summary \
  --json-input '{"story_id":"DRAMA_001"}'
```

### Get character references

```bash
python3 skills/microdrama-memory-manager/scripts/microdrama_memory.py get-characters \
  --json-input '{"story_id":"DRAMA_001"}'
```

### Update production status

```bash
python3 skills/microdrama-memory-manager/scripts/microdrama_memory.py update-status \
  --json-input '{"story_id":"DRAMA_001","event_type":"storyboard_approved","event_note":"Episode 1 approved","story_status":"in_production"}'
```

## Context-bloat rules

This skill should return compact summaries, not full dumps.

Preferred outputs:
- recent patterns
- overused tropes
- underused tropes
- duplicate risk
- trope analytics
- concise character references
- concise production status updates
- concise episode/storyboard/video progress summaries

Avoid returning full database rows beyond the small relevant set.

## Migration behavior

On startup or before query/update operations:
1. ensure workspace exists
2. ensure db exists
3. ensure schema tables exist
4. inspect `schema_version`
5. apply supported migrations if needed

If the db is newer than the helper understands, stop and report incompatibility.
