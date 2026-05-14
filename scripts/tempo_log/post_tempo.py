import os
import json
import sys
import urllib.request
import urllib.error
from datetime import datetime, timedelta


def post_worklogs(entries, date_str):
    """POST each entry to Tempo API v4.

    entries: list of {ticket_key, scaled_minutes, description}
    Returns list of {status ("ok"|"error"), ticket_key, worklog_id or error}
    Start times distributed sequentially from 09:00.
    """
    token = os.environ["TEMPO_API_TOKEN"]
    account_id = os.environ["JIRA_ACCOUNT_ID"]
    start_time = datetime(2000, 1, 1, 9, 0, 0)
    results = []

    for entry in entries:
        payload = json.dumps({
            "issueKey": entry["ticket_key"],
            "timeSpentSeconds": entry["scaled_minutes"] * 60,
            "startDate": date_str,
            "startTime": start_time.strftime("%H:%M:%S"),
            "authorAccountId": account_id,
            "description": entry.get("description", ""),
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.tempo.io/4/worklogs",
            data=payload,
            headers={
                "Authorization": f"Bearer {token}",
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
                "worklog_id": body.get("tempoWorklogId"),
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
