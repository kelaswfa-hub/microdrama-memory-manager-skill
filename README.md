# Microdrama Memory Manager Skill

OpenClaw skill untuk **persistent memory backbone + production state tracker** pada workflow AI microdrama.

## Struktur Repo

- `microdrama-memory-manager/` — source skill
- `dist/microdrama-memory-manager.skill` — artifact siap install

## Fitur

- bootstrap `microdrama_workspace/`
- buat dan maintain SQLite database
- migration schema otomatis
- duplicate story detection
- trope usage analytics
- character reference storage/retrieval
- episode, storyboard, dan video production-state tracking
- summarized production progress
- anti context-bloat memory retrieval

## Skill Boundary

Skill ini **bukan** creative writer dan **bukan** production executor.

Skill ini tidak:
- menulis cerita
- menulis script kreatif
- membuat storyboard prompt kreatif
- membuat Seedance prompt kreatif
- generate asset

Skill ini hanya menyimpan, mengelola, merangkum, dan tracking state.

## Artifact

Gunakan file release/package berikut untuk install:

- `dist/microdrama-memory-manager.skill`

## Source

Source skill utama ada di:

- `microdrama-memory-manager/SKILL.md`
- `microdrama-memory-manager/scripts/microdrama_memory.py`
- `microdrama-memory-manager/references/schema-and-usage.md`
