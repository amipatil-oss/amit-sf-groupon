---
name: cos-welcome
description: Session startup orientation — interactive project picker and workspace navigation. Invoke at the start of any session in CoS root directory.
---

# CoS Welcome

Show an interactive menu at session start when launched in the CoS root directory.

## Steps

### 1. Gather recent projects

Run this command to get the 5 most recently used projects by prompt history:

```bash
for f in $(find /PATH/TO/YOUR/CoS/projects -name "prompt-history.jsonl" -maxdepth 4 2>/dev/null); do
  project=$(echo "$f" | sed 's|.*/projects/[^/]*/\([^/]*\)/.*|\1|')
  last_ts=$(tail -1 "$f" | python3 -c "import sys,json; print(json.load(sys.stdin).get('ts',''))" 2>/dev/null)
  echo "$last_ts $project"
done | sort -r | head -5
```

If fewer than 5 results, supplement with git log:

```bash
git log --name-only --pretty=format: --since="14 days ago" -- "projects/" | grep -oP 'projects/[^/]+/\K[^/]+' | sort -u
```

### 2. Calculate relative dates

For each project's timestamp, calculate relative time (e.g., "2 days ago", "1 week ago").

### 3. Display the menu

Show this format (substitute actual data):

```
[today's date]

What would you like to do?

  [1] Talk to CoS — ask questions, review setup, manage the workspace
  [2] New project — scaffold a new project
  [3] Switch to recent project:
      a. PROJECT_A (X days ago)
      b. PROJECT_B (X days ago)
      c. PROJECT_C (X days ago)
      d. PROJECT_D (X days ago)
      e. PROJECT_E (X days ago)
  [4] Switch to another project — browse full registry
```

Then wait for user input.

### 4. Handle user choice

- **[1] Talk to CoS:** Stay in CoS root context. Respond to whatever the user asks.
- **[2] New project:** Invoke the `new-project` skill via the Skill tool.
- **[3a-e] Switch to recent project:** Read that project's CLAUDE.md, announce the context switch, check `inputs/` for unprocessed files.
- **[4] Browse registry:** Show ALL projects sorted by last touched date (most recent first). Get dates using this command:

```bash
# Get last prompt timestamp for all projects (primary signal)
for f in $(find /PATH/TO/YOUR/CoS/projects -name "prompt-history.jsonl" -maxdepth 4 2>/dev/null); do
  project=$(echo "$f" | sed 's|.*/projects/[^/]*/\([^/]*\)/.*|\1|')
  category=$(echo "$f" | sed 's|.*/projects/\([^/]*\)/.*|\1|')
  last_ts=$(tail -1 "$f" | python3 -c "import sys,json; print(json.load(sys.stdin).get('ts','')[:10])" 2>/dev/null)
  echo "$last_ts $category/$project"
done | sort -r
```

For projects without prompt history, use git log to find last commit date touching that project directory. Projects with no activity at all show "—" for date.

Display format:
```
  2026-03-21  GRPN_SalesCalls
  2026-03-20  GRPN_CEOWeeklyReview
  2026-03-20  GRPN_AISummaries
  ...
  —           GRPN_QASetup
```

Then ask which project to switch to.
- **Free text:** If the user types a task or project name instead of a number, infer intent. If ambiguous, ask.

### 5. On project switch

When switching to a project:
1. Read `projects/<category>/<project>/CLAUDE.md`
2. Announce: "Switched to **PROJECT_NAME** — [one-line description from CLAUDE.md]"
3. Check `projects/<category>/<project>/inputs/` for unprocessed files per the existing CLAUDE.md auto-processing rule
4. All subsequent work scopes to that project
