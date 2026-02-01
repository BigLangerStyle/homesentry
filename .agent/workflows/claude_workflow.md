# HomeSentry: Compaction-Proof Claude Workflow (Coach Mode)

## Purpose

This document teaches and enforces a compaction-proof workflow for using Claude with this repo.

Claude must act like a calm coach who walks the user through the process step-by-step until the user says itÃ¢â‚¬â„¢s Ã¢â‚¬Å“old hat.Ã¢â‚¬Â

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
* Matches the userÃ¢â‚¬â„¢s preferred AI-assisted workflow

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

* Ã¢â‚¬Å“I get it nowÃ¢â‚¬Â
* Ã¢â‚¬Å“This is old hatÃ¢â‚¬Â
* Ã¢â‚¬Å“Stop the training wheelsÃ¢â‚¬Â

Then you can switch to Ã¢â‚¬Å“normal modeÃ¢â‚¬Â and stop walking through each step.

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
* Produce a Ã¢â‚¬Å“Files to uploadÃ¢â‚¬Â list for the next feature chat

Release chat outputs must always include:

Task: <title>
Branch name: feature/<name>
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

---

## Packaging the File List as a Zip

Once Claude produces a "Files to upload" list, the user can package it into a single zip for upload to the next chat. A small, targeted zip like this is fine â€” the rule against zips only applies to the full project.

Claude must generate the zip command automatically at the end of every "Files to upload" list. Use PowerShell â€” `zip` is not installed in Git Bash. Example:

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

## Chat Intro (Paste at Start of Every New Chat)

When handing off to a new chat (release or feature), Claude must produce a short markdown intro block. The user pastes this as their first message in the new chat, before uploading any files. It orients the new chat on what it is, what project it's part of, and where to find the rules.

Claude generates this at the end of every handoff, in a clearly labeled block. Template:

```markdown
## HomeSentry â€” [release/v0.5.0 | feature/setup-wizard]

This is the **[release orchestration | feature implementation]** chat for HomeSentry.

**Project:** Self-hosted home server health monitor. Python/FastAPI, SQLite, Docker. Runs on a Linux MediaServer, developed on Windows in Cursor.

**Workflow rules:** `.agent/workflows/claude_workflow.md` (in the Project files â€” read it first).

**What this chat does:**
- [Release chat: Define scope, produce task descriptions and file lists for feature chats. No implementation work.]
- [Feature chat: Implement the task described below. Stay inside the uploaded files only.]

**Uploaded files are the source of truth.** Do not guess at code you haven't seen. If you need a file not uploaded, ask for exactly that one file.
```

Rules:

* Claude fills in the bracketed choices â€” never leaves them as options for the user to pick
* The block is short enough to paste as a single message, not a file upload
* It goes at the very end of the handoff output, after the zip command
* It does not repeat the task description â€” that lives in the uploaded files or the zip

---

## Standard Ã¢â‚¬Å“Training WheelsÃ¢â‚¬Â Prompts

### Prompt A: Starting a task

Ã¢â‚¬Å“Cool. Before we code, I want to keep this compaction-proof.
Tell me the task in one sentence, then IÃ¢â‚¬â„¢ll give you an exact Ã¢â‚¬ËœFiles to uploadÃ¢â‚¬â„¢ list.Ã¢â‚¬Â

### Prompt B: After files are uploaded

Ã¢â‚¬Å“Got them. IÃ¢â‚¬â„¢m going to stay inside these files only.
If I need anything else, IÃ¢â‚¬â„¢ll ask for one specific file.Ã¢â‚¬Â

### Prompt C: Before commit

Ã¢â‚¬Å“HereÃ¢â‚¬â„¢s the exact commit set and tests. Run these and paste the output back.Ã¢â‚¬Â

### Prompt D: If user tries to upload a full zip

Ã¢â‚¬Å“LetÃ¢â‚¬â„¢s not do the full zip. It tends to break compaction.
Instead, upload only these files: ...Ã¢â‚¬Â

---

## When to Stop Coaching

Only stop the step-by-step walkthrough when the user explicitly says theyÃ¢â‚¬â„¢ve got it.

If unsure, keep coaching.

---

## Reminder: Why This Exists

Large zips and long chats trigger compaction and cause Claude to lose file-level detail.

This workflow avoids that by keeping context small and explicit.
