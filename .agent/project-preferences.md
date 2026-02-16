# Agent Preferences for HomeSentry Project

## ÃƒÂ°Ã…Â¸Ã…Â¡Ã‚Â¨ CRITICAL: Version Control Rules

**CURRENT VERSION: 0.3.0-dev**

### DO NOT increment version without explicit user instruction

All features currently listed in `PROJECT_SUMMARY.md` under **"In Progress (v0.3.0)"** are part of the **v0.3.0 release**.

**Do NOT create v0.1.1, v0.2.0, etc. unless the user explicitly says to move to the next version.**

### When Adding New Features

#### ÃƒÂ¢Ã…â€œÃ¢â‚¬Â¦ CORRECT Approach:

- Keep version at current version in all version-tracking files

- Add feature to existing version sections in CHANGELOG.md and README.md

- Mark feature as complete in PROJECT_SUMMARY.md under current version

- Keep the same date or update to current work date

#### ÃƒÂ¢Ã‚ÂÃ…â€™ WRONG Approach:

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

- **SMART monitoring** - Hard drive health checks  ÃƒÂ¢Ã¢â‚¬Â Ã‚Â ADD HERE

  - Details about the feature...

```

**README.md** - Add to EXISTING v0.1.0 section:

```markdown

### 0.1.0 (January 25, 2026)

**Core Features:**

- **System monitoring** - (existing)

- **SMART monitoring** - Drive health tracking  ÃƒÂ¢Ã¢â‚¬Â Ã‚Â ADD HERE

```

### Current Development Roadmap

**V0.1.0 (MVP) - Completed:**

- [x] FastAPI web server + basic routes

- [x] System collector (CPU, RAM, disk)

- [x] Service HTTP checks (Plex, Jellyfin)

- [x] SQLite database + schema

- [x] Basic HTML dashboard

- [x] Discord webhook alerts

- [x] Docker deployment

**V0.2.0 - In Progress:**

- [ ] Docker container monitoring

- [ ] SMART drive health checks

- [ ] RAID status monitoring

- [ ] Enhanced event tracking

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

---

## ÃƒÂ°Ã…Â¸Ã…â€™Ã‚Â³ Git Workflow & Branch Strategy

**CRITICAL: This project uses a structured branching workflow for clean history and professional development practices.**

### Branch Structure

```

main

 ÃƒÂ¢Ã¢â‚¬ÂÃ…â€œÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ release/v0.1.0

 ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬Å¡    ÃƒÂ¢Ã¢â‚¬ÂÃ…â€œÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ feature/fastapi-skeleton

 ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬Å¡    ÃƒÂ¢Ã¢â‚¬ÂÃ…â€œÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ feature/system-collector

 ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬Å¡    ÃƒÂ¢Ã¢â‚¬ÂÃ…â€œÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ feature/discord-alerts

 ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬Å¡    ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬ÂÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ fix/database-connection

 ÃƒÂ¢Ã¢â‚¬ÂÃ…â€œÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ release/v0.2.0

 ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬Å¡    ÃƒÂ¢Ã¢â‚¬ÂÃ…â€œÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ feature/smart-monitoring

 ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬Å¡    ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬ÂÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ feature/docker-collector

 ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬ÂÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ (future releases)

```

### Workflow Rules

#### 1. **Initial Setup** (One-time)

- Commit documentation/config directly to `main`

- Examples: README, .gitignore, LICENSE, initial project structure

- No PR needed for bootstrap commits

#### 2. **Release Branches**

When starting a new version (e.g., v0.1.0):

```bash

# Create release branch from main

git checkout main

git pull origin main

git checkout -b release/v0.1.0

git push origin release/v0.1.0

```

**Release Branch Chat:**

- Create new Claude chat named: `release/v0.1.0`

- This chat tracks ALL work for that release

- Pin important context/decisions in this chat

#### 3. **Feature/Fix Branches**

All development work branches off the **release branch**:

```bash

# Branch from release, not main!

git checkout release/v0.1.0

git checkout -b feature/system-collector

```

**Feature Branch Chat:**

- Create new Claude chat named: `feature/system-collector`

- Copy task description (provided by previous chat)

- Complete feature in this dedicated chat

- When done, create PR to merge back into release branch

#### 4. **Merge to Main**

When release is complete and tested:

```bash

# Merge release branch into main via PR

# This brings all features into main at once

git checkout main

git merge release/v0.1.0

git tag v0.1.0

git push origin main --tags

```

### Branch Naming Convention

**Release branches:**

- Format: `release/v{version}`

- Examples: `release/v0.1.0`, `release/v0.2.0`, `release/v1.0.0`

**Feature branches:**

- Format: `feature/{descriptive-name}`

- Examples: `feature/system-collector`, `feature/discord-alerts`, `feature/smart-monitoring`

**Bug fix branches:**

- Format: `fix/{descriptive-name}`

- Examples: `fix/memory-leak`, `fix/disk-threshold`, `fix/database-connection`

**Documentation branches:**

- Format: `docs/{descriptive-name}`

- Examples: `docs/api-documentation`, `docs/deployment-guide`

### Task Handoff Format

When creating a new branch/task, provide a **Task Description** that includes:

```markdown

## Task: [Brief Title]

**Branch Name:** feature/example-feature

**Parent Branch:** release/v0.1.0

**Estimated Scope:** Small/Medium/Large

### Context

[What is this feature? Why are we building it?]

### Requirements

- [ ] Requirement 1

- [ ] Requirement 2

- [ ] Requirement 3

### Technical Details

[Implementation notes, architecture decisions, dependencies]

### Files to Create/Modify

- `app/example.py` - Description

- `tests/test_example.py` - Unit tests

- `requirements.txt` - Add new dependencies

### Acceptance Criteria

- [ ] Feature works as specified

- [ ] Code follows project standards (Black formatting, type hints)

- [ ] Documentation updated (CHANGELOG.md, README.md if user-facing)

- [ ] Ready for PR review

### Related Files/Context

- See: PROJECT_SUMMARY.md section X

- Reference: MediaServerInformation.md for server details

```

### Pull Request Process

1. **Create PR** on GitHub

2. **Title format:** `[Feature] Brief description` or `[Fix] Brief description`

3. **Description:** Copy task requirements + what was completed

4. **Self-review:** Check diff, look for issues

5. **Merge:** Squash and merge into release branch

6. **Delete branch:** Clean up after merge

### Why This Workflow?

**Benefits:**

- ÃƒÂ¢Ã…â€œÃ¢â‚¬Â¦ Clean, organized Git history

- ÃƒÂ¢Ã…â€œÃ¢â‚¬Â¦ Each chat has focused context (no mixing features)

- ÃƒÂ¢Ã…â€œÃ¢â‚¬Â¦ Easy to track what went into each release

- ÃƒÂ¢Ã…â€œÃ¢â‚¬Â¦ Professional workflow (resume/portfolio value)

- ÃƒÂ¢Ã…â€œÃ¢â‚¬Â¦ Easy rollback (revert a PR if needed)

- ÃƒÂ¢Ã…â€œÃ¢â‚¬Â¦ Parallel work possible (multiple feature branches)

**Example Timeline:**

```

Day 1: Create release/v0.1.0 branch + chat

Day 2: Create feature/fastapi-skeleton ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ complete ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ PR ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ merge

Day 3: Create feature/system-collector ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ complete ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ PR ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ merge

Day 4: Create feature/discord-alerts ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ complete ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ PR ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ merge

Day 5: Test release branch ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ merge to main ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ tag v0.1.0 ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ ship it!

```

## ÃƒÂ°Ã…Â¸Ã¢â‚¬Å“Ã‚Â Documentation Update Requirements

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

## ÃƒÂ°Ã…Â¸Ã¢â‚¬ÂÃ‚Â§ Line Ending Normalization

**CRITICAL WORKFLOW OPTIMIZATION:**

Handle line ending conversions automatically for Git-tracked files to prevent "LF will be replaced by CRLF" warnings.

### Two-Way Conversion Process:

**When READING uploaded files:**

1. Check if files are Git-tracked (not in `.gitignore`)

2. Convert CRLF ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ LF for clean internal processing:

   ```bash

   dos2unix <filename> 2>/dev/null || sed -i 's/\r$//' <filename>

   ```

**When PRESENTING files back to user:**

1. Check if files are Git-tracked (not in `.gitignore`)

2. Convert LF ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ CRLF to match Windows Git config:

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

---

## Ã°Å¸â€â€ž CRITICAL: Complete Development to Deployment Workflow

**This is the ACTUAL workflow - follow this exactly every time:**

### Step 1: Claude Makes Changes (In Claude's Environment)

Claude works in `/home/claude/` to:

1. Create/modify source files

2. Update documentation (CHANGELOG.md, PROJECT_SUMMARY.md, etc.)

3. Convert all Git-tracked files to CRLF line endings

4. Copy files to `/mnt/user-data/outputs/`

### Step 2: Claude Presents Files (End of Task)

Claude uses `present_files` tool to share:

- All modified source files (e.g., `app/collectors/services.py`)

- All modified documentation files (e.g., `CHANGELOG.md`)

- All modified configuration files (e.g., `docker-compose.yml`, `.env.example`)

**IMPORTANT:** Files are named clearly with their repo path in the description.

#### Special Rule: .env File Handling

**Whenever `.env.example` is modified, Claude MUST also provide an updated `.env` file** with the same changes applied. This allows the user to:
1. Download `.env` to Windows
2. Transfer it to MediaServer via WinSCP
3. Avoid manually editing `.env` on the server

The `.env` file should:
- Include all the same variables as `.env.example`
- Use placeholder values (e.g., `YOUR_WEBHOOK_HERE`) for any new secrets
- Preserve existing configuration values where possible
- Be clearly labeled as `.env` (not `.env.example`) in the presentation

**Why:** The user workflow involves downloading configuration updates to Windows and transferring them to the Linux MediaServer. Providing both `.env.example` (for Git tracking) and `.env` (for deployment) in one step eliminates manual file editing on the server.

### Step 3: Claude Provides Git Commit Command

Claude suggests a commit message following conventional commits format:

```bash

git commit -m "feat: Brief description

- Bullet point of what was added/changed

- Another detail

- Fix or improvement made"

```

### Step 4: User Downloads and Commits (On Windows Workstation - Cursor)

User:

1. Downloads files from Claude's outputs

2. Copies files to correct locations in local repo (following paths Claude specified)

3. Uses git commands in Cursor terminal:

   ```bash

   git add <files>

   git commit -m "<message Claude provided>"

   git push origin <branch-name>

   ```

### Step 5: User Deploys to Server (On Linux MediaServer)

User SSHs to MediaServer and:

```bash

# Pull latest code

cd ~/git/homesentry

git pull origin <branch-name>

# Update .env if needed (first time or when .env.example changed)

cp .env.example .env

nano .env  # Edit to add Discord webhook, etc.

# Rebuild and restart

docker compose -f docker/docker-compose.yml down

docker compose -f docker/docker-compose.yml up --build -d

# Check logs

docker compose -f docker/docker-compose.yml logs -f

```

### Step 6: User Tests (On Linux MediaServer)

User runs test commands Claude provides, such as:

```bash

# Test API endpoints

curl http://192.168.1.8:8000/api/collect/services | jq

# Check database

docker exec -it homesentry sh

sqlite3 /app/data/homesentry.db

# ... run queries ...

.quit

exit

```

---

## Ã¢Å¡Â Ã¯Â¸Â What Claude Should NOT Do

- Ã¢ÂÅ’ Do NOT run git commands (`git init`, `git add`, `git commit`, `git push`)

- Ã¢ÂÅ’ Do NOT assume files are committed just because they're presented

- Ã¢ÂÅ’ Do NOT ask "should I commit this?" - just present files and suggest commit message

- Ã¢ÂÅ’ Do NOT give instructions for steps the user hasn't reached yet

- Ã¢ÂÅ’ Do NOT ask user to test before they've deployed to the server

## Ã¢Å“â€¦ What Claude SHOULD Do

- Ã¢Å“â€¦ Present all modified files clearly with repo paths

- Ã¢Å“â€¦ Provide a ready-to-use git commit message

- Ã¢Å“â€¦ Provide deployment commands for MediaServer

- Ã¢Å“â€¦ Provide test commands to verify functionality

- Ã¢Å“â€¦ Wait for user feedback after they've tested

---

## Ã°Å¸â€œâ€¹ Standard Response Template (End of Task)

When a feature is complete, Claude should respond like this:

```

[Brief summary of what was implemented]

Files ready for commit:

1. app/collectors/example.py - [what it does]

2. app/main.py - [what changed]

3. .env.example - [what was added]

4. CHANGELOG.md - [documented changes]

5. PROJECT_SUMMARY.md - [marked complete]

Git commit command:

```bash

git commit -m "feat: Description

- Detail 1

- Detail 2"

```

After you commit and push, deploy on MediaServer with:

```bash

cd ~/git/homesentry

git pull

docker compose -f docker/docker-compose.yml up --build -d

```

Then test with:

```bash

[test commands specific to feature]

```

```

This makes it clear Claude's job ends at presenting files, and the user handles everything after that.

## File Presentation Preferences

When presenting modified source files for Git commits:

### ÃƒÂ¢Ã‚ÂÃ…â€™ DON'T:

- Present files in a folder structure that requires "opening"

- Group files in a way that makes them hard to download individually

- Use generic names when there might be ambiguity

### ÃƒÂ¢Ã…â€œÃ¢â‚¬Â¦ DO:

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

ÃƒÂ¢Ã¢â‚¬ÂÃ…â€œÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ .agent/

ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬Å¡   ÃƒÂ¢Ã¢â‚¬ÂÃ…â€œÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ project-preferences.md

ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬Å¡   ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬ÂÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ workflows/          (if needed)

ÃƒÂ¢Ã¢â‚¬ÂÃ…â€œÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ app/

ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬Å¡   ÃƒÂ¢Ã¢â‚¬ÂÃ…â€œÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ main.py            (FastAPI application)

ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬Å¡   ÃƒÂ¢Ã¢â‚¬ÂÃ…â€œÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ collectors/        (monitoring modules)

ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬Å¡   ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬Å¡   ÃƒÂ¢Ã¢â‚¬ÂÃ…â€œÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ __init__.py

ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬Å¡   ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬Å¡   ÃƒÂ¢Ã¢â‚¬ÂÃ…â€œÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ system.py      (CPU, RAM, disk)

ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬Å¡   ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬Å¡   ÃƒÂ¢Ã¢â‚¬ÂÃ…â€œÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ smart.py       (drive health)

ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬Å¡   ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬Å¡   ÃƒÂ¢Ã¢â‚¬ÂÃ…â€œÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ docker.py      (container monitoring)

ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬Å¡   ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬Å¡   ÃƒÂ¢Ã¢â‚¬ÂÃ…â€œÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ services.py    (HTTP health checks)

ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬Å¡   ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬Å¡   ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬ÂÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ raid.py        (RAID status)

ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬Å¡   ÃƒÂ¢Ã¢â‚¬ÂÃ…â€œÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ storage/           (database)

ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬Å¡   ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬Å¡   ÃƒÂ¢Ã¢â‚¬ÂÃ…â€œÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ __init__.py

ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬Å¡   ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬Å¡   ÃƒÂ¢Ã¢â‚¬ÂÃ…â€œÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ db.py          (SQLite setup)

ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬Å¡   ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬Å¡   ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬ÂÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ models.py      (schema definitions)

ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬Å¡   ÃƒÂ¢Ã¢â‚¬ÂÃ…â€œÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ alerts/            (notifications)

ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬Å¡   ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬Å¡   ÃƒÂ¢Ã¢â‚¬ÂÃ…â€œÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ __init__.py

ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬Å¡   ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬Å¡   ÃƒÂ¢Ã¢â‚¬ÂÃ…â€œÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ discord.py     (webhook integration)

ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬Å¡   ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬Å¡   ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬ÂÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ rules.py       (alerting logic)

ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬Å¡   ÃƒÂ¢Ã¢â‚¬ÂÃ…â€œÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ templates/         (HTML templates)

ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬Å¡   ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬Å¡   ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬ÂÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ dashboard.html

ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬Å¡   ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬ÂÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ static/            (CSS, JS)

ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬Å¡       ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬ÂÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ styles.css

ÃƒÂ¢Ã¢â‚¬ÂÃ…â€œÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ docker/

ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬Å¡   ÃƒÂ¢Ã¢â‚¬ÂÃ…â€œÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ Dockerfile

ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬Å¡   ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬ÂÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ docker-compose.yml

ÃƒÂ¢Ã¢â‚¬ÂÃ…â€œÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ scripts/

ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬Å¡   ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬ÂÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ setup.sh           (future: interactive installer)

ÃƒÂ¢Ã¢â‚¬ÂÃ…â€œÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ tests/

ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬Å¡   ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬ÂÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ (unit tests)

ÃƒÂ¢Ã¢â‚¬ÂÃ…â€œÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ .env.example           (configuration template)

ÃƒÂ¢Ã¢â‚¬ÂÃ…â€œÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ .gitignore

ÃƒÂ¢Ã¢â‚¬ÂÃ…â€œÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ README.md

ÃƒÂ¢Ã¢â‚¬ÂÃ…â€œÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ CHANGELOG.md

ÃƒÂ¢Ã¢â‚¬ÂÃ…â€œÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ PROJECT_SUMMARY.md

ÃƒÂ¢Ã¢â‚¬ÂÃ¢â‚¬ÂÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ requirements.txt

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

## ÃƒÂ°Ã…Â¸Ã…Â¡Ã‚Â« Git Management

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

---

## 📦 Task Completion & Chat Handoff

When the main chat produces a task description for a new release/feature chat, it MUST also produce an explicit **"Files to upload"** list. Do NOT tell the user to upload the whole project zip — large zips can cause "No compactable messages" errors that prevent the chat from starting.

### Why Not Just Zip Everything?

Uploading the full project zip as context can exceed Claude's compaction limit, which breaks chat creation entirely. Uploading only the files the task actually touches keeps context lean and the chat reliable.

### What to Include

The main chat (or release chat spinning off a feature chat) should always produce a list like this alongside the task description:

```
Files to upload for this chat:
1. TASK_example.md                          — the task description (paste as text or upload)
2. app/collectors/modules/base.py           — base class the new module extends
3. app/collectors/modules/jellyfin.py       — example module to follow as a pattern
4. CHANGELOG.md                             — needs updating when task is done
5. PROJECT_SUMMARY.md                       — needs updating when task is done
```

### Rules for Building the List

**Always include:**
- The task description itself (TASK file or pasted text)
- Every source file the task will **create or modify**
- `CHANGELOG.md` and `PROJECT_SUMMARY.md` (these update with every task)
- Any base class or interface the task implements/extends

**Include when relevant:**
- One example implementation if the task is following an existing pattern (e.g., a second module can reference the first as a template)
- `.env.example` if the task adds new config variables
- `docker-compose.yml` or `Dockerfile` if deployment config changes

**Do NOT include:**
- Files the task won't read or modify
- The full project zip
- Database files or data directories
- `media-server-information.md` or `project-preferences.md` — these live in the Project and are always available automatically

### Claude's Task Completion Checklist

When a task is complete, Claude should:

1. **Present completed work files** (for git commit)
   - Modified source files
   - Updated documentation files (CHANGELOG.md, PROJECT_SUMMARY.md)
   - Git commit message

2. **If spinning off a follow-up task:** produce the task description AND the "Files to upload" list together, so the user can start the next chat immediately.

---
