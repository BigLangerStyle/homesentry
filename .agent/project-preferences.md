# Agent Preferences for HomeSentry Project

## 🚨 CRITICAL: Version Control Rules

**CURRENT VERSION: 0.1.0-dev**

### DO NOT increment version without explicit user instruction

All features currently listed in `PROJECT_SUMMARY.md` under **"In Progress (v0.1.0)"** are part of the **v0.1.0 release**.

**Do NOT create v0.1.1, v0.2.0, etc. unless the user explicitly says to move to the next version.**

### When Adding New Features

#### ✅ CORRECT Approach:
- Keep version at current version in all version-tracking files
- Add feature to existing version sections in CHANGELOG.md and README.md
- Mark feature as complete in PROJECT_SUMMARY.md under current version
- Keep the same date or update to current work date

#### ❌ WRONG Approach:
- Creating new version sections without explicit user instruction
- Incrementing version numbers spontaneously
- Creating new CHANGELOG entries with new versions

### Version Update Example

When adding "SMART monitoring" feature:

**CHANGELOG.md** - Add to EXISTING v0.1.0 section:
```markdown
## [0.1.0] - 2026-01-25

### Added
- **System monitoring** - CPU, RAM, disk usage (existing)
- **SMART monitoring** - Hard drive health checks  ← ADD HERE
  - Details about the feature...
```

**README.md** - Add to EXISTING v0.1.0 section:
```markdown
### 0.1.0 (January 25, 2026)

**Core Features:**
- **System monitoring** - (existing)
- **SMART monitoring** - Drive health tracking  ← ADD HERE
```

### Current Development Roadmap

**V0.1.0 (MVP) - In Progress:**
- [ ] FastAPI web server + basic routes
- [ ] System collector (CPU, RAM, disk usage)
- [ ] Service HTTP checks (Plex, Jellyfin)
- [ ] SQLite database + schema
- [ ] Basic HTML dashboard
- [ ] Discord webhook alerts
- [ ] Docker deployment

**V0.2.0 (Planned):**
- [ ] Docker container monitoring
- [ ] SMART health checks
- [ ] RAID status monitoring
- [ ] Events tracking + state changes

**V0.5.0 (Future):**
- [ ] Interactive installation wizard (auto-detect services)
- [ ] Modular collector system
- [ ] Configuration UI

**V1.0.0 (Future):**
- [ ] Historical charts
- [ ] Authentication
- [ ] UI polish

---

## 📝 Documentation Update Requirements

**CRITICAL: Always update documentation when completing features**

After implementing any new feature or fixing bugs, you MUST update the associated documentation files:

### Required Updates:
1. **CHANGELOG.md** - Add feature/fix details under the current version section
2. **README.md** - Update feature list if it affects user-facing functionality
3. **PROJECT_SUMMARY.md** - Mark feature as complete, move from "In Progress" to "Completed"

### Workflow:
- When presenting completed work, ALWAYS include both:
  - Code files (from `app/`, `docker/`, `scripts/`, etc.)
  - Documentation files (CHANGELOG.md, README.md, PROJECT_SUMMARY.md)
- Never present code changes without the corresponding documentation updates
- Documentation updates follow the same version control rules (add to existing version, don't create new versions)

### Example:
```
User: "Implement SMART monitoring"

Response after completion:
1. Present app/collectors/smart.py (new collector)
2. Present app/main.py (if routes added)
3. Present requirements.txt (if new dependencies)
4. Present CHANGELOG.md (feature added to current version section)
5. Present README.md (if user-facing changes)
6. Present PROJECT_SUMMARY.md (marked as complete)
```

---

## 🔧 Line Ending Normalization

**CRITICAL WORKFLOW OPTIMIZATION:**

Handle line ending conversions automatically for Git-tracked files to prevent "LF will be replaced by CRLF" warnings.

### Two-Way Conversion Process:

**When READING uploaded files:**
1. Check if files are Git-tracked (not in `.gitignore`)
2. Convert CRLF → LF for clean internal processing:
   ```bash
   dos2unix <filename> 2>/dev/null || sed -i 's/\r$//' <filename>
   ```

**When PRESENTING files back to user:**
1. Check if files are Git-tracked (not in `.gitignore`)
2. Convert LF → CRLF to match Windows Git config:
   ```bash
   unix2dos <filename> 2>/dev/null || sed -i 's/$/\r/' <filename>
   ```
3. Then present the files

### Why:
- Prevents "LF will be replaced by CRLF" Git warnings
- Files you download already match your Windows Git expectations
- Work with clean LF internally, but deliver CRLF externally
- Saves time by fixing proactively instead of reactively
- User shouldn't need to ask for this - just do it automatically

### Git-Tracked Files in This Project:
- `app/**/*.py` (all Python source files)
- `*.md` files (README, CHANGELOG, PROJECT_SUMMARY)
- `.env.example`
- `requirements.txt`
- `docker-compose.yml`
- `Dockerfile`
- `scripts/*.sh`
- Any other source files not in .gitignore

---

## File Presentation Preferences

When presenting modified source files for Git commits:

### ❌ DON'T:
- Present files in a folder structure that requires "opening"
- Group files in a way that makes them hard to download individually
- Use generic names when there might be ambiguity

### ✅ DO:
- Present each file individually using `present_files` with one file at a time
- Use clear paths that show where files belong
- Include brief notes about where each file goes in the repo

### Example Workflow:

```
User: "Present the completed feature files"

Response:
1. Present app/collectors/smart.py
2. Present app/main.py
3. Present requirements.txt
4. Present CHANGELOG.md
5. Present PROJECT_SUMMARY.md
6. Present README.md (if needed)

Each file presented separately with context about what changed.
```

---

## Project Structure

```
homesentry/
├── .agent/
│   ├── project-preferences.md
│   └── workflows/          (if needed)
├── app/
│   ├── main.py            (FastAPI application)
│   ├── collectors/        (monitoring modules)
│   │   ├── __init__.py
│   │   ├── system.py      (CPU, RAM, disk)
│   │   ├── smart.py       (drive health)
│   │   ├── docker.py      (container monitoring)
│   │   ├── services.py    (HTTP health checks)
│   │   └── raid.py        (RAID status)
│   ├── storage/           (database)
│   │   ├── __init__.py
│   │   ├── db.py          (SQLite setup)
│   │   └── models.py      (schema definitions)
│   ├── alerts/            (notifications)
│   │   ├── __init__.py
│   │   ├── discord.py     (webhook integration)
│   │   └── rules.py       (alerting logic)
│   ├── templates/         (HTML templates)
│   │   └── dashboard.html
│   └── static/            (CSS, JS)
│       └── styles.css
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── scripts/
│   └── setup.sh           (future: interactive installer)
├── tests/
│   └── (unit tests)
├── .env.example           (configuration template)
├── .gitignore
├── README.md
├── CHANGELOG.md
├── PROJECT_SUMMARY.md
└── requirements.txt
```

---

## Development Workflow

### On Windows (Development Machine):
1. Edit code in Cursor/VSCode
2. Test changes locally (if possible)
3. Commit to Git
4. Push to GitHub (or your Git remote)

### On Linux Server (MediaServer):
1. SSH into server
2. `cd /path/to/homesentry`
3. `git pull`
4. `docker compose up --build -d`

This is a standard workflow for server applications. You develop on Windows, deploy to Linux.

---

## Docker Deployment

HomeSentry is designed to run in Docker for:
- **Isolation** - doesn't interfere with system packages
- **Portability** - same container works everywhere
- **Easy updates** - rebuild and restart
- **Host access** - Docker can still access host metrics via volume mounts

### Key Docker Considerations:
- Container needs access to host metrics (CPU, RAM via `/proc`, `/sys`)
- Container needs access to smartctl for SMART checks
- Container needs network access for service checks
- Database persists via Docker volume

---

## Version Management

### Files to Keep in Sync:
1. `CHANGELOG.md` - Latest version section header
2. `README.md` - Latest version in features/history
3. `PROJECT_SUMMARY.md` - "Version:" field at top

### When Updating Version (ONLY when user explicitly requests):
1. Update version in `PROJECT_SUMMARY.md`
2. Create new section in `CHANGELOG.md`
3. Update version history in `README.md`
4. Create Git tag: `git tag v0.2.0`

**REMINDER: Do not update version unless user explicitly says to release a new version!**

---

## Python Development Standards

### Code Style:
- Use **Black** for formatting (run before committing)
- Use **type hints** where practical
- Write **docstrings** for functions/classes
- Keep functions **short and focused**

### Error Handling:
- Collectors should **never crash the app**
- Catch exceptions, log errors, mark status as FAIL
- Use try/except generously in collector modules

### Comments:
- Explain **WHY**, not just WHAT
- This is a learning project - comments help future you
- Reference docs/specs when applicable

---

## Testing

### Approach:
- Start with manual testing (v0.1.0)
- Add unit tests for critical logic (v0.2.0+)
- Test on actual MediaServer hardware

### Test Coverage Goals:
- Collector result parsing
- Alert state-change logic
- Database operations
- Rollup/aggregation functions

---

## 🚫 Git Management

**CRITICAL: User manages Git separately in Cursor**

- **DO NOT** initialize Git repositories (`git init`)
- **DO NOT** create branches (`git checkout -b`)
- **DO NOT** commit changes (`git commit`)
- **DO NOT** perform any Git operations

The user has their own Git repository in Cursor and handles all version control operations themselves. Claude's job is to:
1. Prepare and present modified source files
2. Update documentation files
3. Ensure files are ready for the user to commit in their own environment

Even if workflow instructions mention Git operations, skip those steps. The user only needs the modified files presented.

---

## Future Enhancements (Ideas to Keep in Mind)

### Interactive Installer (v0.5.0+):
- Auto-detect services on MediaServer
- Present checklist of what can be monitored
- Generate `.env` config based on selections
- Use `whiptail` or `dialog` for console TUI

### Modular Architecture:
- Each collector is self-contained
- Collectors register themselves
- Easy to add new collectors without touching core code
- Collectors can be enabled/disabled via config

### Configuration UI (v1.0+):
- Web-based config editor
- Enable/disable collectors
- Adjust thresholds
- Test alerts

These are future goals - keep code structure flexible to accommodate them!
