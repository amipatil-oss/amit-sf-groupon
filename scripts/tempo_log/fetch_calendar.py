import os
from datetime import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


def _get_service():
    creds_path = os.environ.get(
        "GOOGLE_CALENDAR_CREDENTIALS",
        os.path.expanduser("~/.google-calendar-credentials.json"),
    )
    token_path = os.path.join(os.path.dirname(creds_path), "google-calendar-token.json")

    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as f:
            f.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def fetch_calendar_events(date_str):
    """Return today's timed, non-declined, non-free events as a list of dicts.

    Each dict: {summary, start, end, duration_minutes}
    """
    service = _get_service()
    result = service.events().list(
        calendarId="primary",
        timeMin=f"{date_str}T00:00:00Z",
        timeMax=f"{date_str}T23:59:59Z",
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    events = []
    for item in result.get("items", []):
        start = item.get("start", {})
        end = item.get("end", {})

        if "dateTime" not in start:
            continue
        if item.get("transparency") == "transparent":
            continue

        declined = any(
            a.get("self") and a.get("responseStatus") == "declined"
            for a in item.get("attendees", [])
        )
        if declined:
            continue

        start_dt = datetime.fromisoformat(start["dateTime"].replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end["dateTime"].replace("Z", "+00:00"))
        duration = int((end_dt - start_dt).total_seconds() // 60)

        if duration <= 0:
            continue

        events.append({
            "summary": item.get("summary", "(No title)"),
            "start": start["dateTime"],
            "end": end["dateTime"],
            "duration_minutes": duration,
        })

    return events
