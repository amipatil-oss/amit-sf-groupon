# log-tempo Skill — Design Spec

**Date:** 2026-05-13
**Status:** Approved

## Overview

A Claude Code skill that automates daily Tempo time logging. It reads today's Google Calendar events and Tempo's "My Work" suggestions, uses Claude to infer which Jira ticket each activity maps to, scales all durations proportionally to exactly 8h, presents a draft for review, and only logs to Tempo after explicit user confirmation.

---

## Goals

- Zero manual effort for daily time logging
- Always logs exactly 8h per day (no over/under)
- User reviews and can cancel before anything is written to Tempo
- Matches the pattern of existing CoS skills (weekly-515-report)

## Non-Goals

- Multi-day backfill (today only)
- Logging to multiple calendars or workspaces
- Creating new Jira tickets

---

## Credentials Required

| Env Var | Purpose |
|---|---|
| `TEMPO_API_TOKEN` | Tempo API v4 bearer token |
| `GOOGLE_CALENDAR_CREDENTIALS` | Path to OAuth 2.0 JSON credentials file |
| `JIRA_ACCOUNT_ID` | Atlassian account ID (used to filter Tempo results) |

---

## Workflow

### Step 1 — Fetch Google Calendar Events

Call the Google Calendar REST API for today's events:

```
GET https://www.googleapis.com/calendar/v3/calendars/primary/events
  ?timeMin=<today 00:00 UTC>
  &timeMax=<today 23:59 UTC>
  &singleEvents=true
  &orderBy=startTime
```

Extract per event: `summary`, `start.dateTime`, `end.dateTime`, `description` (if any).
Skip all-day events (no `dateTime`). Skip events marked as "Free" or declined.

### Step 2 — Fetch Tempo Worklogs + Jira Ticket Candidates

**Check existing worklogs (via Tempo API v4):**
```
GET https://api.tempo.io/4/worklogs?from=YYYY-MM-DD&to=YYYY-MM-DD&accountId=<JIRA_ACCOUNT_ID>
Authorization: Bearer <TEMPO_API_TOKEN>
```
If total `timeSpentSeconds` across returned worklogs ≥ 28800 (8h), alert the user and exit — already logged.

**Fetch active Jira tickets (via Jira REST API):**
```
GET https://groupondev.atlassian.net/rest/api/3/search
  ?jql=assignee=currentUser() AND updated>=-7d ORDER BY updated DESC
  &fields=key,summary,status
```
These recently-updated tickets serve as the candidate pool for ticket matching in Step 3.

Extract per ticket: `key`, `summary`, `status`.

### Step 3 — Claude Inference: Match Events → Jira Tickets

Claude receives:
- List of calendar events (title, duration, time of day)
- List of Tempo suggestions (Jira key, summary)

Claude outputs a merged list with:
- Each calendar event matched to the most relevant Jira ticket (by title similarity + Tempo suggestions)
- A raw duration weight for each entry (from calendar event duration, or equal share if no calendar match)
- Source label: `Calendar+Tempo`, `Tempo`, or `Calendar`

If a calendar event cannot be matched to any Jira ticket, it is flagged as `(unmatched)` in the draft and the user must assign it before logging proceeds.

### Step 4 — Scale Durations to 8h

Treat all raw durations as proportional weights:

```
scaled_duration[i] = (raw_duration[i] / sum(all_raw_durations)) × 8h
```

Round each to the nearest minute. Assign any rounding remainder (±1 min) to the ticket with the largest allocation.

Minimum ticket duration: 15 minutes. If scaling produces a ticket below 15 min, fold it into the closest related ticket.

### Step 5 — Present Draft for Review

Output a formatted table:

```
Date: YYYY-MM-DD  |  Total: 8h 00m

| Jira Ticket  | Duration | Description               | Source         |
|--------------|----------|---------------------------|----------------|
| SFDC-XXXX    | Xh XXm   | <inferred description>    | Calendar+Tempo |
| SFDC-YYYY    | Xh XXm   | <inferred description>    | Tempo          |
| SFDC-ZZZZ    | Xh XXm   | <inferred description>    | Calendar       |

⚠ Unmatched events: none  (or list them)

Confirm to log to Tempo? (yes / edit / cancel)
```

Wait for user response:
- `yes` → proceed to Step 6
- `edit` → user provides corrections inline, re-render draft, loop back to confirm
- `cancel` → exit, nothing logged

### Step 6 — Log to Tempo

For each row in the confirmed draft, POST a worklog:

```
POST https://api.tempo.io/4/worklogs
Authorization: Bearer <TEMPO_API_TOKEN>
Content-Type: application/json

{
  "issueKey": "SFDC-XXXX",
  "timeSpentSeconds": <duration in seconds>,
  "startDate": "YYYY-MM-DD",
  "startTime": "09:00:00",
  "authorAccountId": "<JIRA_ACCOUNT_ID>",
  "description": "<inferred description>"
}
```

Start times are distributed sequentially from 09:00 (each entry starts when the previous ends).

After all POSTs succeed, output a confirmation summary:

```
✓ Logged 8h to Tempo for YYYY-MM-DD
  SFDC-XXXX  Xh XXm
  SFDC-YYYY  Xh XXm
  SFDC-ZZZZ  Xh XXm
```

If any POST fails, report the error and list which entries were NOT logged so the user can retry manually.

---

## Skill File Structure

```
.claude/skills/log-tempo/
  SKILL.md                     # Skill body — full workflow steps
  references/
    tempo-api.md               # Tempo API v4 endpoint reference + curl examples
    gcal-auth.md               # Google Calendar OAuth setup instructions
```

---

## Edge Cases

| Scenario | Behavior |
|---|---|
| 8h already logged in Tempo today | Alert user, exit without changes |
| No calendar events AND no Tempo suggestions | Alert user: "No activity found for today" |
| Calendar event with no Jira match | Flag as unmatched in draft; block logging until resolved |
| Single ticket matches all activity | That ticket gets all 8h |
| Tempo API returns 401 | Prompt user to check `TEMPO_API_TOKEN` |
| Google Calendar API returns 401 | Prompt user to refresh `GOOGLE_CALENDAR_CREDENTIALS` |

---

## Scheduled Execution (8 PM IST Daily)

The skill runs automatically at **8 PM IST (14:30 UTC)** via `CronCreate`.

Since no user is present at run time, the confirmation step works differently in scheduled mode vs. manual mode:

### Scheduled Mode (8 PM IST cron)
1. Steps 1–4 run as normal (fetch Calendar, fetch Jira/Tempo, infer, scale to 8h)
2. Instead of interactive confirmation, the draft is **emailed to `amipatil@groupon.com`** via Gmail MCP
3. Email subject: `Tempo Draft — YYYY-MM-DD (pending confirmation)`
4. Email body: the full draft table + a note to reply `/log-tempo confirm` or `/log-tempo cancel`
5. Nothing is logged to Tempo until the user manually runs `/log-tempo confirm` in Claude Code

### Manual Mode (user-triggered)
- Interactive draft → `yes / edit / cancel` confirmation as designed
- Logs immediately on `yes`

### Cron Schedule
```
Cron expression: 30 14 * * 1-5     (14:30 UTC = 8:00 PM IST, weekdays only)
```

This is registered via the `schedule` skill / `CronCreate` tool during skill setup.

---

## Out of Scope (Future)

- Week-level view or backfill mode
- Multiple Jira projects / workspaces
- Editing logged worklogs (update/delete)
- Auto-confirm without draft review
