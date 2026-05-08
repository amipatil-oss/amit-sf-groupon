---
name: weekly-515-report
description: Use when filling or automating the weekly 5/15 report for Amit Patil in Asana. Covers finding the current week's task, pulling data from Jira and Git, and updating all five sections.
---

# Weekly 5/15 Report Automation

## Overview

Automates filling Amit Patil's weekly 5/15 Asana report by collecting data from Jira, Git commits, and the previous week's task. Sections 1 and 3 are required; sections 2, 4, 5 are updated if data is available.

## Report Structure

```
1) What happened this week?          ← REQUIRED — pull from Jira + Git
2) What was planned and wasn't done? ← based on last week's section 3 vs actual status
3) What are the key priorities for next week (3-5 tasks)? ← REQUIRED — open/upcoming Jira tickets
4) Top achievement/breakthrough      ← best completed item + AI use
5) Suggestions and improvement ideas ← optional, update if relevant
```

## Step-by-Step Workflow

### Step 1 — Find this week's Asana task

Use Asana MCP (`get_task`) on the parent task **1209800320344517** ("5/15 - Amit Patil") to get its subtasks, then find the subtask whose name matches the current Friday's date (`5/15 - Amit Patil - YYYY-MM-DD`).

- Parent task GID: `1209800320344517`
- Task name pattern: `5/15 - Amit Patil - YYYY-MM-DD` where the date is the **Friday of the current week**
- Use `get_tasks` or inspect subtasks of the parent if needed

### Step 2 — Read the existing task content

Call `get_task` on the found subtask GID. Note:
- The current content of all 5 sections
- Section 3 from the **previous** week becomes the baseline for "what was planned" this week

### Step 3 — Pull Jira data

**Query Jira for Amit Patil's tickets this week:**
- Cloud ID: `groupondev.atlassian.net`
- Assignee: `amipatil@groupon.com`
- JQL: `assignee = currentUser() AND updated >= -7d ORDER BY updated DESC`
- For each ticket extract: key, summary, status (Done / In Progress / To Do), description summary

**Completed this week** → Section 1 ("What happened this week")
**Planned but still open** → Section 2 ("What was planned and wasn't done")
**In Progress or upcoming** → Section 3 ("Key priorities for next week")

### Step 4 — Pull Git commit data

Run git log on the SF repo (`/Users/amipatil/Documents/New SFRepo 2026/SFDC`):

```bash
git log --since="last monday" --until="today" --oneline --all
```

Extract ticket IDs (e.g. `SFDC-XXXXX`) from commit messages. Cross-reference with Jira data to enrich section 1 entries.

### Step 5 — Synthesize and format sections

**Section 1 format** (group by initiative/project):
```
[Initiative Name]
    https://groupondev.atlassian.net/browse/SFDC-XXXX : <summary of what was done> - completed/in progress
```

**Section 2 format**:
```
https://groupondev.atlassian.net/browse/SFDC-XXXX : <summary> - <reason not done if known>
If nothing was missed: "All planned items were completed as per timeline."
```

**Section 3 format** (3-5 items):
```
[Initiative Name] - <description>
https://groupondev.atlassian.net/browse/SFDC-XXXX : <target or brief description>
```

**Section 4** — Pick the single most impactful completed ticket. Always mention Claude AI / MCP tool use if any was done.

**Section 5** — Leave as "NA" unless a specific insight or AI opportunity was identified during the week.

### Step 6 — Update the Asana task

Call `update_tasks` with the task GID and the full updated `notes` field.

**CRITICAL: Never set `completed: true`** — the task must remain open.

## Key Resources

| Resource | Value |
|---|---|
| Asana parent task | GID `1209800320344517` |
| Jira cloud ID | `groupondev.atlassian.net` |
| SF Git repo | `/Users/amipatil/Documents/New SFRepo 2026/SFDC` |
| Assignee email | `amipatil@groupon.com` |
| Report due | Every Friday |

## Common Mistakes

| Mistake | Fix |
|---|---|
| Marking task complete | Always keep `completed: false` |
| Only updating section 1 | Always update sections 1 AND 3 at minimum |
| Using stale "next week" priorities | Pull fresh Jira data — don't rely solely on old section 3 |
| Missing git-only work | Some tickets only show up in Git commits, not Jira — check both |
| Wrong Friday date | Calculate Friday of current week, not today's date if today isn't Friday |
