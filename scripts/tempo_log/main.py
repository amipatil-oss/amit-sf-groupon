"""
Fetch today's tempo log data and output as JSON.

Usage:
  python scripts/tempo_log/main.py
  python scripts/tempo_log/main.py --date 2026-05-13

Output JSON fields:
  date, already_logged, existing_seconds, calendar_events[], jira_tickets[], git_commits[]
"""
import argparse
import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(__file__))

from fetch_calendar import fetch_calendar_events
from fetch_jira import fetch_jira_tickets
from check_tempo import check_existing_worklogs
from fetch_git import fetch_git_commits


REQUIRED_ENV = ["TEMPO_API_TOKEN", "JIRA_ACCOUNT_ID", "JIRA_API_TOKEN"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=date.today().isoformat())
    args = parser.parse_args()

    missing = [v for v in REQUIRED_ENV if not os.environ.get(v)]
    if missing:
        print(json.dumps({"error": f"Missing env vars: {', '.join(missing)}"}))
        sys.exit(1)

    tempo_status = check_existing_worklogs(args.date)
    calendar_events = fetch_calendar_events(args.date)
    jira_tickets = fetch_jira_tickets()
    git_commits = fetch_git_commits(args.date)

    print(json.dumps({
        "date": args.date,
        "already_logged": tempo_status["already_logged"],
        "existing_seconds": tempo_status["total_seconds"],
        "calendar_events": calendar_events,
        "jira_tickets": jira_tickets,
        "git_commits": git_commits,
    }, indent=2))


if __name__ == "__main__":
    main()
