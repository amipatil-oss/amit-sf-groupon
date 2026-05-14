# Jira Native Worklog API Reference

## Base URL
`https://groupondev.atlassian.net/rest/api/3/`

## Authentication
All requests: `Authorization: Basic base64(email:JIRA_API_TOKEN)`

## Get Your JIRA_API_TOKEN
1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Create API token → copy value
3. `export JIRA_API_TOKEN="your-token-here"`

## Key Endpoints

### Log time on an issue
```bash
curl -s -X POST \
  -u "amipatil@groupon.com:$JIRA_API_TOKEN" \
  -H "Content-Type: application/json" \
  "https://groupondev.atlassian.net/rest/api/3/issue/SFDC-1234/worklog" \
  -d '{
    "timeSpentSeconds": 3600,
    "started": "2026-05-13T09:00:00.000+0000",
    "comment": {
      "type": "doc", "version": 1,
      "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Sprint planning"}]}]
    }
  }'
```

### View worklogs for an issue
```bash
curl -s -u "amipatil@groupon.com:$JIRA_API_TOKEN" \
  "https://groupondev.atlassian.net/rest/api/3/issue/SFDC-1234/worklog"
```

## Error Codes
| Code | Meaning |
|---|---|
| 401 | Token invalid — regenerate at https://id.atlassian.com/manage-profile/security/api-tokens |
| 403 | No permission to log time on this issue |
| 404 | Issue key not found |
