---
name: log-tempo
description: Log today's 8 hours to Jira (native worklog API). Fetches Google Calendar + Jira tickets + today's git commits, infers ticket mapping via AI, scales to exactly 8h, shows a draft for review, and logs only after explicit confirmation. Also runs on cron at 8 PM IST — in that mode it emails a draft instead of logging interactively.
---

# Log Tempo Hours

## When to Invoke
User says "log tempo", "log my hours", "log time", or runs `/log-tempo`.
Also invoked by the daily 8 PM IST cron — in that case treat as SCHEDULED MODE (see Step 5b).

---

## Step 1 — Validate Credentials

Check these env vars. If any are missing, tell the user which one is missing and where to get it.

| Env Var | Required |
|---|---|
| `JIRA_API_TOKEN` | Yes — get at https://id.atlassian.com/manage-profile/security/api-tokens |
| `GOOGLE_CALENDAR_CREDENTIALS` | Yes — see references/gcal-auth.md |

---

## Step 2 — Fetch Today's Data

```bash
cd /Users/amipatil/Desktop/CoS && python3 scripts/tempo_log/main.py
```

Parse the JSON output:
- If `"error"` key present → tell user which env vars are missing and stop.
- Proceed with `calendar_events[]`, `jira_tickets[]`, and `git_commits[]`.

**First-run note:** If `GOOGLE_CALENDAR_CREDENTIALS` is set but no token file exists yet, a browser window will open for OAuth consent. Tell the user: "A browser window is opening for Google Calendar authorization — please sign in and grant calendar read access. This only happens once."

---

## Step 3 — Infer Ticket Mapping (Claude AI Step)

You have three data sources:
- `calendar_events[]` — meetings/events with `summary` and `duration_minutes`
- `jira_tickets[]` — recently updated tickets with `key`, `summary`, `status`
- `git_commits[]` — today's commits with `message` and `ticket_ids[]`

**Use all three signals together:**
- A commit that references `SFDC-1234` is strong evidence that ticket was worked on today → assign calendar time proportionally
- Calendar events named after a project → match to that project's Jira ticket
- `In Progress` tickets with no calendar match → include with `raw_minutes: 30` (default)
- If a commit references a ticket, prefer that ticket even if the calendar event title is vague
- Prefer `In Progress` status over `To Do` or `Done`

Output your inference as a JSON array:

```json
[
  {"ticket_key": "SFDC-1234", "raw_minutes": 90, "description": "Sprint planning", "source": "Calendar+Tempo"},
  {"ticket_key": "SFDC-5678", "raw_minutes": 60, "description": "Code review — 3 commits", "source": "Git+Tempo"},
  {"ticket_key": "SFDC-9012", "raw_minutes": 30, "description": "1:1 with manager", "source": "Calendar"}
]
```

Valid source values: `Calendar+Tempo`, `Calendar+Git`, `Git+Tempo`, `Calendar`, `Tempo`, `Git`, `Calendar+Git+Tempo`

Unmatched calendar events (if any):
```json
["Design sync (no matching ticket found)"]
```

If there is truly no activity and no tickets → say "No activity found for today — cannot log." and stop.

---

## Step 4 — Scale to Exactly 8h

```bash
cd /Users/amipatil/Desktop/CoS && python3 scripts/tempo_log/scale_hours.py '<INFERRED_JSON_FROM_STEP_3>'
```

Outputs same entries with `scaled_minutes` replacing `raw_minutes`, summing to exactly 480.

---

## Step 5 — Present Draft (Interactive Mode)

```bash
cd /Users/amipatil/Desktop/CoS && python3 scripts/tempo_log/format_draft.py \
  '<SCALED_JSON>' \
  '<UNMATCHED_JSON_OR_EMPTY_ARRAY>' \
  'YYYY-MM-DD'
```

Display the formatted table to the user.

**If unmatched events exist** → do NOT proceed to Step 6. Ask user to assign a ticket, re-run Steps 3–5.

Wait for response:
- `yes` / `confirm` → Step 6
- `edit` + corrections → update entries, re-run Step 4, re-display, wait again
- `cancel` / `no` → "Nothing was logged to Tempo." Stop.

---

## Step 5b — Scheduled Mode: Email Draft (CRON ONLY)

Use `mcp__claude_ai_Gmail__create_draft`:
- To: `amipatil@groupon.com`
- Subject: `Tempo Draft — <DATE> (run /log-tempo to confirm)`
- Body:
```
Your automated Tempo draft for <DATE>:

<FORMATTED DRAFT TABLE>

To log these hours, open Claude Code and run: /log-tempo
Confirm with "yes" to log. Run /log-tempo then cancel to skip.
```

After sending: "Tempo draft for <DATE> sent to amipatil@groupon.com."
Stop — do NOT log to Tempo yet.

---

## Step 6 — Log to Jira

```bash
cd /Users/amipatil/Desktop/CoS && python3 scripts/tempo_log/post_worklogs.py \
  '{"entries": <SCALED_ENTRIES>, "date": "YYYY-MM-DD"}'
```

Parse results:
- `status: "ok"` → logged
- `status: "error"` → failed

**All succeeded:**
```
✓ Logged 8h to Jira for YYYY-MM-DD
  SFDC-XXXX  Xh XXm — <description>
```

**Partial failure:**
```
⚠ Partial log:
  ✓ SFDC-XXXX — logged
  ✗ SFDC-YYYY — error: <message>
  Log manually: https://groupondev.atlassian.net/issues
```
