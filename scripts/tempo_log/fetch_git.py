import os
import re
import subprocess
import json
import sys
from datetime import date

REPOS = [
    {
        "name": "SFDC",
        "path": "/Users/amipatil/Documents/New SFRepo 2026/SFDC",
    },
    {
        "name": "CoS",
        "path": "/Users/amipatil/Desktop/CoS",
    },
]

TICKET_PATTERN = re.compile(r"\b([A-Z][A-Z0-9]+-\d+)\b")


def _git_log_today(repo_path, date_str):
    """Run git log for date_str in repo_path. Returns list of commit dicts."""
    if not os.path.isdir(repo_path):
        return []
    try:
        result = subprocess.run(
            [
                "git", "log",
                f"--after={date_str} 00:00:00",
                f"--before={date_str} 23:59:59",
                "--format=%H|%s",
                "--all",
            ],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=15,
        )
        commits = []
        for line in result.stdout.strip().splitlines():
            if "|" not in line:
                continue
            sha, message = line.split("|", 1)
            ticket_ids = TICKET_PATTERN.findall(message)
            commits.append({
                "hash": sha[:8],
                "message": message.strip(),
                "ticket_ids": list(dict.fromkeys(ticket_ids)),  # deduplicated, order preserved
            })
        return commits
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []


def fetch_git_commits(date_str=None):
    """Return today's commits across all known repos.

    Returns list of {repo, hash, message, ticket_ids[]}
    """
    if date_str is None:
        date_str = date.today().isoformat()

    all_commits = []
    for repo in REPOS:
        commits = _git_log_today(repo["path"], date_str)
        for c in commits:
            all_commits.append({
                "repo": repo["name"],
                "hash": c["hash"],
                "message": c["message"],
                "ticket_ids": c["ticket_ids"],
            })
    return all_commits


if __name__ == "__main__":
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    print(json.dumps(fetch_git_commits(date_arg), indent=2))
