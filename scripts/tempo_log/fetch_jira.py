import os
import json
import base64
import urllib.request
import urllib.parse


def _auth_header():
    email = os.environ.get("JIRA_USER_EMAIL", "amipatil@groupon.com")
    token = os.environ["JIRA_API_TOKEN"]
    encoded = base64.b64encode(f"{email}:{token}".encode()).decode()
    return f"Basic {encoded}"


def fetch_jira_tickets():
    """Return recently updated Jira tickets assigned to current user.

    Each dict: {key, summary, status}
    Raises RuntimeError on 401 (bad token).
    """
    domain = os.environ.get("JIRA_DOMAIN", "groupondev.atlassian.net")
    params = urllib.parse.urlencode({
        "jql": "assignee = currentUser() AND updated >= -7d ORDER BY updated DESC",
        "fields": "key,summary,status",
        "maxResults": "50",
    })
    url = f"https://{domain}/rest/api/3/search?{params}"

    req = urllib.request.Request(
        url,
        headers={"Authorization": _auth_header(), "Accept": "application/json"},
    )

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise RuntimeError("JIRA_API_TOKEN is invalid. Get one at https://id.atlassian.com/manage-profile/security/api-tokens") from e
        raise

    return [
        {
            "key": issue["key"],
            "summary": issue["fields"]["summary"],
            "status": issue["fields"]["status"]["name"],
        }
        for issue in data.get("issues", [])
    ]
