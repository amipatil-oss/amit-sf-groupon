# Google Calendar OAuth Setup (One-Time)

## Step 1: Create OAuth credentials in Google Cloud Console

1. Go to https://console.cloud.google.com/
2. Select or create a project
3. **APIs & Services → Library** → search "Google Calendar API" → Enable
4. **APIs & Services → Credentials** → Create Credentials → OAuth client ID
5. Application type: **Desktop app** | Name: `Claude Tempo Logger`
6. Download the JSON → save as `~/.google-calendar-credentials.json`

## Step 2: Configure OAuth Consent Screen

1. **APIs & Services → OAuth consent screen**
2. User Type: **Internal** (if Workspace/org account) or **External** (Gmail)
3. Add your email (`amipatil@groupon.com`) as a test user if External
4. Scopes: add `https://www.googleapis.com/auth/calendar.readonly`

## Step 3: Set env var

```bash
export GOOGLE_CALENDAR_CREDENTIALS="$HOME/.google-calendar-credentials.json"
```

Add to `~/.zshrc` to persist across sessions.

## Step 4: First Run — Browser Auth

Run `/log-tempo` once. A browser window opens. Sign in and grant "Read calendar" permission. Token saved at `~/.google-calendar-token.json`. All future runs auto-refresh.

## Troubleshooting

**"Access blocked: This app's request is invalid"**
→ Complete Step 2 and add your email as a test user.

**Token expired / auth fails after a few months**
→ `rm ~/.google-calendar-token.json` then re-run `/log-tempo`.

**Events missing / wrong calendar**
→ The skill reads your `primary` calendar. For a secondary work calendar, update `calendarId="primary"` in `fetch_calendar.py` to use the calendar's ID (found in Google Calendar settings → Integrate calendar).
