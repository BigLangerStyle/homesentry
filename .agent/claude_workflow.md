# HomeSentry: Claude Code (IDE) Workflow

## How This Works

Claude Code reads and edits files directly in the repo. No uploads, no zips, no copy-pasting full files back.

You review changes as diffs in VS Code's Source Control panel. You run git yourself.

---

## Why We Do It This Way

**One branch per task** — keeps `main` always clean and working. If something goes wrong, the branch is throwaway.

**One concern per task** — small diffs are easy to review and safe to revert. Large unfocused changes are hard to reason about and harder to undo.

**Review the diff, not the explanation** — the diff is what actually changed. Claude's explanation is a summary. Always verify against the diff.

**Verify before committing** — run the linter and tests after every change. Catching a broken import before it hits `main` is much cheaper than after.

**Conventional commits** — `type(scope): description` format makes git history useful for debugging and changelog generation. Common types: `fix`, `feat`, `refactor`, `chore`, `docs`.

---

## Scope Reference

- `alerts/` — alert logic, Discord, sleep schedule, maintenance windows
- `collectors/` — system, services, docker, SMART, RAID metric collection
- `collectors/modules/` — app-specific integrations (Jellyfin, Plex, etc.)
- `storage/` — database layer, schema, migrations
- `app/main.py` — FastAPI routes, dashboard API
- `app/scheduler.py` — background polling loop
- `docker/` — container config, deployment
- `docs/` — documentation updates
