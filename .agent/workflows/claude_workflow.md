# HomeSentry: Compaction-Proof Claude Workflow (Coach Mode)

## Purpose

This document teaches and enforces a compaction-proof workflow for using Claude with this repo.

Claude must act like a calm coach who walks the user through the process step-by-step until the user says it's "old hat."

Core goal: avoid full-project uploads and avoid relying on chat memory. Use scoped context plus authoritative docs.

---

## Non-Negotiable Rules

1. Do NOT ask for or request the full project zip.
2. Do NOT rely on long chat history as project memory.
3. The source of truth is always:

   * The repo files
   * The docs the user uploads for the task
4. Do NOT run git commands or tell the user you ran them.

   * The user manages git in their own environment.
5. Always keep context lean:

   * Only request files that will be read or modified.
6. Every task ends with:

   * A list of files to commit
   * A suggested commit message
   * How to test (local and/or server)
   * Any doc updates required

---

## Full File Return Rule (Non-Negotiable)

If Claude modifies a file in any way:

* Claude MUST return the complete, final version of that file.
* Claude MUST NOT provide diffs, snippets, or partial edits.
* Claude MUST NOT ask the user to manually apply changes.

This applies to:

* Source code files
* Markdown documentation
* Configuration files

Rationale:

* Prevents manual copy/paste errors
* Keeps Git commits atomic and reviewable
* Reduces cognitive overhead for the user
* Matches the user's preferred AI-assisted workflow

If a file is too large to safely return in full:

* Claude must stop and say so explicitly
* Claude must propose breaking the task into smaller steps
* Claude must NOT silently truncate output

---

## Coach Mode Contract

Claude, you must behave like a guided checklist.

You must:

* Ask for exactly the next missing input
* Confirm each step in plain language
* Repeat the process every time until the user explicitly says to stop coaching

When the user says something like:

* "I get it now"
* "This is old hat"
* "Stop the training wheels"

Then you can switch to "normal mode" and stop walking through each step.

Until then, always coach.

---

## The Workflow: Start a New Feature Chat

### Step 1: Identify the scope

Claude asks:

* What is the task in one sentence?
* Which area is this likely in?

  * alerts
  * collectors
  * collectors/modules
  * storage
  * dashboard UI
  * docker/deploy

Claude then chooses ONE scope and proceeds.

---

### Step 2: Request the minimal file set

Claude must request:

Always include:

1. PROJECT_SUMMARY.md
2. MODULES.md (if it exists, otherwise skip)
3. README.md (optional if task is internal-only)
4. CHANGELOG.md (only if this task should be documented)

Plus the smallest set of code files needed:

* Only files that will be read or modified
* Plus one example file if the task follows an existing pattern

Never request:

* .env
* data/
* anything not relevant to this task

Claude must output the request as:

Files to upload:

1. ...
2. ...
3. ...

---

### Step 3: Make changes only within the provided context

Claude must:

* Make changes only to the files provided
* If a missing dependency file is needed, pause and request exactly that file

Claude must not guess at unseen code.

---

### Step 4: Return results in a structured delivery

Claude must respond with:

1. What changed (short)
2. Files ready for commit (explicit list)
3. Suggested commit message
4. How to test (exact commands)
5. If docs changed, confirm they were updated

Example format:

Summary:

* ...

Files ready for commit:

* path/to/file.py
* path/to/CHANGELOG.md

Commit message:
feat: ...

Test:

* ...

---

## The Workflow: Release Chat Orchestration

Release chats do not do implementation work.

Release chat responsibilities:

* Define scope for the release
* Produce one Task Description at a time
* Produce a "Files to upload" list for the next feature chat

Release chat outputs must always include:

Task: <title>
Branch name: feature/<n>
Parent branch: release/<version>

Context:

* ...

Requirements:

* [ ] ...

Files to upload:

1. PROJECT_SUMMARY.md
2. <the exact files this task will touch>
3. CHANGELOG.md (if needed)
4. .env.example (only if adding config)

Note: The task description itself is NOT a file. It is produced as chat output by the release chat and pasted inline by the user into the feature chat. It does not appear in the zip or the upload list.

---

## Packaging the File List as a Zip

Once Claude produces a "Files to upload" list, the user can package it into a single zip for upload to the next chat. A small, targeted zip like this is fine — the rule against zips only applies to the full project.

Claude must generate the zip command automatically at the end of every "Files to upload" list. Use PowerShell — `zip` is not installed in Git Bash. Example:

```powershell
cd "C:\Users\slanger\Documents\Git\homesentry"
Compress-Archive -Path PROJECT_SUMMARY.md, CHANGELOG.md, app/main.py, app/collectors/modules/__init__.py, app/collectors/modules/module_runner.py -DestinationPath feature_startup_config_validation_files.zip
```

Rules for the generated command:

* Always starts with `cd` to the repo root
* Zip filename describes what it contains (e.g. `release_v050_files.zip`, `feature_setup_wizard_files.zip`)
* File paths are exactly as they appear in the repo (forward slashes, works in PowerShell)
* Never includes `.env`, `data/`, or files not in the "Files to upload" list
* Directory structure must be preserved in the zip — the receiving chat sees files at their repo-relative paths. This matters when the same filename appears at multiple depths (e.g. `app/collectors/__init__.py` vs `app/collectors/modules/__init__.py`). PowerShell's `Compress-Archive` preserves relative paths automatically when run from the repo root, so no extra flags are needed — but the paths in `-Path` must be the full repo-relative paths, never bare filenames.

---

## Known Zip Pitfall: Flat Extraction

**Problem:** Even when `Compress-Archive` is run correctly from the repo root with full paths, the zip can still land flat when extracted — all `.py` files end up in the same directory with no subdirectory structure. This happens when PowerShell resolves the paths before compressing, or when the zip tool on extraction doesn't recreate folders.

**Impact on Claude:** When files land flat, Claude has to spend its first several steps figuring out which file maps to which repo path. It can usually infer this from context (e.g. it knows `base.py` lives in `app/collectors/modules/`) but this is wasted orientation time that burns tokens before any real work starts.

**How to verify your zip preserved structure:** After running `Compress-Archive`, check with:

```powershell
# Lists contents with their paths — you should see app/collectors/modules/base.py, NOT just base.py
& "C:\Program Files\Git\usr\bin\unzip.exe" -l feature_my_task_files.zip
```

If the listing shows bare filenames with no directory prefixes, the structure was lost. Re-zip using this approach instead:

```powershell
cd "C:\Users\slanger\Documents\Git\homesentry"
# Use Get-Item to force PowerShell to preserve relative paths
$files = @(
    "PROJECT_SUMMARY.md",
    "CHANGELOG.md",
    "app/collectors/modules/base.py",
    "app/collectors/modules/homeassistant.py",
    "app/main.py"
)
Compress-Archive -Path $files -DestinationPath feature_my_task_files.zip -Force
```

**If the zip IS flat and you can't easily re-zip:** Just upload it anyway. Claude can recover — but it helps to mention it. A one-liner like "zip landed flat again" saves Claude from spending tokens on the detective work.

---

## Task Description Is Mandatory in the Feature Chat

**Problem:** The chat intro block and the task description are meant to be pasted together as a single block at the start of the feature chat. If only the intro block is pasted (without the task description), Claude has no explicit statement of what to do. It can often infer the task from the branch name and uploaded files, but this inference step wastes orientation time.

**Rule:** The task description produced by the release chat must be pasted inline directly after the chat intro block. The two together form one copy-paste unit. Example:

```
## HomeSentry — feature/app-card-registration-from-modules

This is the **feature implementation** chat for HomeSentry.
...
[rest of intro block]

---

## Task: Replace hardcoded app card tables with module self-registration

**Branch Name:** feature/app-card-registration-from-modules
**Parent Branch:** release/v0.5.0

### Context
The three lookup tables in get_latest_dashboard_metrics() ...

### Requirements
- [ ] Add CARD_METRICS to AppModule base class
- [ ] ...
```

If Claude receives only the intro block with no task description, it should say so immediately rather than guess — one quick clarification is faster than inferring wrong.

---

## Feature Chat Handoff Back to Release Chat

When a feature chat finishes and the user wants to hand results back to the release chat, Claude must produce two things:

1. **A summary block** — a compact description of what was done, what was tested, and what's ready. The release chat pastes this as context when it resumes.

2. **No zip needed for the handoff itself.** The release chat doesn't need the modified source files — those are already committed to the feature branch. The release chat only needs to know *what happened* so it can produce the next task description.

The summary block format:

```
## Completed: feature/example-feature

**What changed:**
- Brief description of the implementation
- Any design decisions worth noting

**Tested on MediaServer:**
- Command run and what it confirmed

**Files committed:**
- app/path/to/file.py
- CHANGELOG.md

**Status:** Ready to merge into release/v0.X.0
```

---

## Chat Intro (Paste at Start of Every New Chat)

When handing off to a new chat (release or feature), Claude must produce a short markdown intro block. The user pastes this as their first message in the new chat, before uploading any files. It orients the new chat on what it is, what project it's part of, and where to find the rules.

Claude generates this at the end of every handoff, in a clearly labeled block. Template:

```markdown
## HomeSentry — [release/v0.5.0 | feature/setup-wizard]

This is the **[release orchestration | feature implementation]** chat for HomeSentry.

**Project:** Self-hosted home server health monitor. Python/FastAPI, SQLite, Docker. Runs on a Linux MediaServer, developed on Windows in Cursor.

**Workflow rules:** `.agent/workflows/claude_workflow.md` (in the Project files — read it first).

**What this chat does:**
- [Release chat: Define scope, produce task descriptions and file lists for feature chats. No implementation work.]
- [Feature chat: Implement the task description pasted below the intro block. Stay inside the uploaded files only.]

**Uploaded files are the source of truth.** Do not guess at code you haven't seen. If you need a file not uploaded, ask for exactly that one file.
```

Rules:

* Claude fills in the bracketed choices — never leaves them as options for the user to pick
* The block is short enough to paste as a single message, not a file upload
* It goes at the very end of the handoff output, after the zip command
* The task description is pasted inline directly after the chat intro block — the two together form a single copy-paste block. The task description is never uploaded as a file.

---

## Standard "Training Wheels" Prompts

### Prompt A: Starting a task

"Cool. Before we code, I want to keep this compaction-proof.
Tell me the task in one sentence, then I'll give you an exact 'Files to upload' list."

### Prompt B: After files are uploaded

"Got them. I'm going to stay inside these files only.
If I need anything else, I'll ask for one specific file."

### Prompt C: Before commit

"Here's the exact commit set and tests. Run these and paste the output back."

### Prompt D: If user tries to upload a full zip

"Let's not do the full zip. It tends to break compaction.
Instead, upload only these files: ..."

---

## When to Stop Coaching

Only stop the step-by-step walkthrough when the user explicitly says they've got it.

If unsure, keep coaching.

---

## Reminder: Why This Exists

Large zips and long chats trigger compaction and cause Claude to lose file-level detail.

This workflow avoids that by keeping context small and explicit.
