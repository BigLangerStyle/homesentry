# HomeSentry: Compaction-Proof Claude Workflow (Coach Mode)

## Purpose

This document teaches and enforces a compaction-proof workflow for using Claude with this repo.

Claude must act like a calm coach who walks the user through the process step-by-step until the user says itâ€™s â€œold hat.â€

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
* Matches the userâ€™s preferred AI-assisted workflow

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

* â€œI get it nowâ€
* â€œThis is old hatâ€
* â€œStop the training wheelsâ€

Then you can switch to â€œnormal modeâ€ and stop walking through each step.

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
* Produce a â€œFiles to uploadâ€ list for the next feature chat

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

Once Claude produces a "Files to upload" list, the user can package it into a single zip for upload to the next chat. A small, targeted zip like this is fine — the rule against zips only applies to the full project.

Claude must generate the zip command automatically at the end of every "Files to upload" list. Use PowerShell — `zip` is not installed in Git Bash. Example:

```powershell
cd "C:\Users\slanger\Documents\Git\homesentry"
Compress-Archive -Path PROJECT_SUMMARY.md, CHANGELOG.md, app/main.py, app/collectors/__init__.py -DestinationPath release_v050_files.zip
```

Rules for the generated command:

* Always starts with `cd` to the repo root
* Zip filename describes what it contains (e.g. `release_v050_files.zip`, `feature_setup_wizard_files.zip`)
* File paths are exactly as they appear in the repo (forward slashes, works in PowerShell)
* Never includes `.env`, `data/`, or files not in the "Files to upload" list

---

## Complete Handoff Format

When handing off to a new release or feature chat, Claude must produce three distinct outputs in this order:

### 1. Git Commands

Commands to create and push the branch. For release branches:

```bash
git checkout main
git pull origin main
git checkout -b release/v0.X.0
git push origin release/v0.X.0
```

For feature branches:

```bash
git checkout release/v0.X.0
git pull origin release/v0.X.0
git checkout -b feature/descriptive-name
git push origin feature/descriptive-name
```

### 2. PowerShell Zip Command

Command to package the context files for upload:

```powershell
cd "C:\Users\slanger\Documents\Git\homesentry"
Compress-Archive -Path file1.md, file2.py, dir/file3.py -DestinationPath release_v0X0_files.zip
```

Rules:
* Filename describes what it contains (e.g., `release_v070_files.zip`, `feature_charts_api_files.zip`)
* Only includes files from the "Files to upload" list
* Never includes `.env`, `data/`, or files not relevant to the task

### 3. Chat Intro Block

Short markdown block to paste as the first message in the new chat:

```markdown
## HomeSentry — [branch name]

This is the **[release orchestration | feature implementation]** chat for HomeSentry.

**Project:** Self-hosted home server health monitor. Python/FastAPI, SQLite, Docker. Runs on a Linux MediaServer, developed on Windows in Cursor.

**Workflow rules:** `.agent/workflows/claude_workflow.md` (in the Project files — read it first).

**What this chat does:**
- [Release chat: Define scope, produce task descriptions and file lists for feature chats. No implementation work.]
- [Feature chat: Implement the task described below. Stay inside the uploaded files only.]

**Uploaded files are the source of truth.** Do not guess at code you haven't seen. If you need a file not uploaded, ask for exactly that one file.
```

Rules:
* Claude fills in all bracketed choices — never leaves them as options for the user
* Block is short enough to paste as a single message, not a file upload
* Does not repeat task descriptions — those live in uploaded files

---

## Standard â€œTraining Wheelsâ€ Prompts

### Prompt A: Starting a task

â€œCool. Before we code, I want to keep this compaction-proof.
Tell me the task in one sentence, then Iâ€™ll give you an exact â€˜Files to uploadâ€™ list.â€

### Prompt B: After files are uploaded

â€œGot them. Iâ€™m going to stay inside these files only.
If I need anything else, Iâ€™ll ask for one specific file.â€

### Prompt C: Before commit

â€œHereâ€™s the exact commit set and tests. Run these and paste the output back.â€

### Prompt D: If user tries to upload a full zip

â€œLetâ€™s not do the full zip. It tends to break compaction.
Instead, upload only these files: ...â€

---

## When to Stop Coaching

Only stop the step-by-step walkthrough when the user explicitly says theyâ€™ve got it.

If unsure, keep coaching.

---

## Reminder: Why This Exists

Large zips and long chats trigger compaction and cause Claude to lose file-level detail.

This workflow avoids that by keeping context small and explicit.
