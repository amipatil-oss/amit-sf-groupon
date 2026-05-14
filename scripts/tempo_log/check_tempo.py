import os
import json
import urllib.request
import urllib.parse


def check_existing_worklogs(date_str):
    """Check Tempo for worklogs already logged on date_str.

    Returns {total_seconds, already_logged, worklogs[{issue_key, seconds}]}
    Raises RuntimeError on 401.
    """
    token = os.environ["TEMPO_API_TOKEN"]
    account_id = os.environ["JIRA_ACCOUNT_ID"]
    params = urllib.parse.urlencode({"from": date_str, "to": date_str, "accountId": account_id})
    url = f"https://api.tempo.io/4/worklogs?{params}"

    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise RuntimeError("TEMPO_API_TOKEN is invalid or expired. Generate one at https://app.tempo.io/ → Settings → API integration") from e
        raise

    worklogs = data.get("results", [])
    total_seconds = sum(w.get("timeSpentSeconds", 0) for w in worklogs)

    return {
        "total_seconds": total_seconds,
        "already_logged": total_seconds >= 28800,
        "worklogs": [
            {"issue_key": w.get("issue", {}).get("key", "?"), "seconds": w.get("timeSpentSeconds", 0)}
            for w in worklogs
        ],
    }
