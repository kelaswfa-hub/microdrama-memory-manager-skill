# Microdrama Memory Manager Skill

![Release](https://img.shields.io/github/v/release/kelaswfa-hub/microdrama-memory-manager-skill?label=release)
![License](https://img.shields.io/github/license/kelaswfa-hub/microdrama-memory-manager-skill)
![Repo Size](https://img.shields.io/github/repo-size/kelaswfa-hub/microdrama-memory-manager-skill)
![Open Issues](https://img.shields.io/github/issues/kelaswfa-hub/microdrama-memory-manager-skill)

OpenClaw skill untuk **persistent memory backbone + production state tracker** pada workflow AI microdrama.

## Struktur Repo

- `microdrama-memory-manager/` — source skill
- `dist/microdrama-memory-manager.skill` — artifact siap install
- `CHANGELOG.md` — riwayat perubahan versi

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

## Quick Links

- Repo: <https://github.com/kelaswfa-hub/microdrama-memory-manager-skill>
- Releases: <https://github.com/kelaswfa-hub/microdrama-memory-manager-skill/releases>
- Latest `.skill`: <https://github.com/kelaswfa-hub/microdrama-memory-manager-skill/releases/latest>

## Skill Boundary

Skill ini **bukan** creative writer dan **bukan** production executor.

Skill ini tidak:
- menulis cerita
- menulis script kreatif
- membuat storyboard prompt kreatif
- membuat Seedance prompt kreatif
- generate asset

Skill ini hanya menyimpan, mengelola, merangkum, dan tracking state.

## Install Skill

### Opsi 1 — dari artifact `.skill`

Unduh file `dist/microdrama-memory-manager.skill`, atau ambil dari halaman release GitHub, lalu install sesuai alur skill OpenClaw yang kamu pakai.

### Opsi 2 — pakai source repo

Gunakan folder `microdrama-memory-manager/` sebagai source skill untuk pengembangan dan repackaging.

## Contoh Capability

Skill ini mendukung state management seperti:
- create/update episode state
- create/update storyboard block state
- create/update video block state
- duplicate concept check
- character reference retrieval
- production progress summary

## Source

Source skill utama ada di:
- `microdrama-memory-manager/SKILL.md`
- `microdrama-memory-manager/scripts/microdrama_memory.py`
- `microdrama-memory-manager/references/schema-and-usage.md`

## License

MIT
