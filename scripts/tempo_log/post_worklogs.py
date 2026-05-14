import os
import json
import sys
import base64
import urllib.request
import urllib.error
from datetime import datetime, timedelta


def _auth_header():
    email = os.environ.get("JIRA_USER_EMAIL", "amipatil@groupon.com")
    token = os.environ["JIRA_API_TOKEN"]
    encoded = base64.b64encode(f"{email}:{token}".encode()).decode()
    return f"Basic {encoded}"


def _adf_comment(text):
    """Wrap plain text in Atlassian Document Format for Jira worklog comment."""
    return {
        "type": "doc",
        "version": 1,
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": text}]}],
    }


def post_worklogs(entries, date_str):
    """POST each entry to Jira's native worklog API.

    entries: list of {ticket_key, scaled_minutes, description}
    Returns list of {status ("ok"|"error"), ticket_key, worklog_id or error}
    Start times distributed sequentially from 09:00.
    """
    domain = os.environ.get("JIRA_DOMAIN", "groupondev.atlassian.net")
    start_time = datetime.strptime(f"{date_str}T09:00:00", "%Y-%m-%dT%H:%M:%S")
    results = []

    for entry in entries:
        started = start_time.strftime("%Y-%m-%dT%H:%M:%S.000+0000")
        payload = json.dumps({
            "timeSpentSeconds": entry["scaled_minutes"] * 60,
            "started": started,
            "comment": _adf_comment(entry.get("description", "")),
        }).encode("utf-8")

        url = f"https://{domain}/rest/api/3/issue/{entry['ticket_key']}/worklog"
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Authorization": _auth_header(),
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req) as resp:
                body = json.load(resp)
            results.append({
                "status": "ok",
                "ticket_key": entry["ticket_key"],
                "worklog_id": body.get("id"),
            })
        except urllib.error.HTTPError as e:
            results.append({
                "status": "error",
                "ticket_key": entry["ticket_key"],
                "error": e.read().decode(),
            })

        start_time += timedelta(minutes=entry["scaled_minutes"])

    return results


if __name__ == "__main__":
    data = json.loads(sys.argv[1])
    results = post_worklogs(data["entries"], data["date"])
    print(json.dumps(results, indent=2))
