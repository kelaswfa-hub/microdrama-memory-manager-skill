# Changelog

All notable changes to this project will be documented in this file.

The format is loosely based on Keep a Changelog and uses semantic-version style tags when practical.

## [0.1.0] - 2026-05-07

### Added
- Initial public release of the Microdrama Memory Manager OpenClaw skill
- `microdrama-memory-manager/SKILL.md` with strict non-creative memory-manager boundaries
- `microdrama-memory-manager/scripts/microdrama_memory.py` helper CLI for bootstrap, storage, retrieval, migration, and production-state tracking
- `microdrama-memory-manager/references/schema-and-usage.md` with schema and command reference
- Packaged artifact `dist/microdrama-memory-manager.skill`
- MIT license
- README with badges, release links, and install guidance

### Changed
- Extended the skill from pure memory backbone into memory backbone + production state tracker
- Added migration v2 for detailed production-tracking fields across episodes, storyboards, and videos
- Added commands for episode, storyboard, video, and production-summary state management
