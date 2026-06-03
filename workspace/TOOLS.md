# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

## Wiki Tools (memory-wiki, isolated mode)

The memory-wiki plugin exposes five tools — use these instead of raw filesystem reads when you need wiki content. Vault lives at `~/.openclaw/wiki/main`.

- `wiki_status` — check vault mode, health, and Obsidian CLI availability. Run before first wiki write each session.
- `wiki_search` — search wiki pages (and shared memory corpora when needed). Use for person lookup, question routing, source evidence, or raw claim drilldown via the mode flags.
- `wiki_get` — read a wiki page by id/path; falls back to shared memory corpus.
- `wiki_apply` — narrow synthesis or metadata mutations. Prefer this over freeform page surgery from the host filesystem.
- `wiki_lint` — structural checks for provenance gaps, contradictions, and open questions. Run before declaring a wiki update done.

Dashboards land under `~/.openclaw/wiki/main/reports/` (e.g. `open-questions.md`, `contradictions.md`, `stale-pages.md`) — read them with `wiki_get`, not the filesystem.

---

Add whatever helps you do your job. This is your cheat sheet.
