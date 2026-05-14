# Tempo API v4 Reference

## Base URL
`https://api.tempo.io/4/`

## Authentication
All requests: `Authorization: Bearer <TEMPO_API_TOKEN>`

## Get Your Tempo API Token
1. Go to https://app.tempo.io/
2. Profile icon → Settings → API integration
3. Generate a new token
4. `export TEMPO_API_TOKEN="your-token-here"`

## Get Your JIRA_ACCOUNT_ID
```bash
curl -s \
  -u "amipatil@groupon.com:$JIRA_API_TOKEN" \
  "https://groupondev.atlassian.net/rest/api/3/myself" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['accountId'])"
```
Then: `export JIRA_ACCOUNT_ID="<output>"`

## Key Endpoints

### Check today's logged hours
```bash
curl -s \
  -H "Authorization: Bearer $TEMPO_API_TOKEN" \
  "https://api.tempo.io/4/worklogs?from=$(date +%Y-%m-%d)&to=$(date +%Y-%m-%d)&accountId=$JIRA_ACCOUNT_ID" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(sum(w['timeSpentSeconds'] for w in d['results'])//3600, 'hours logged')"
```

### Create a worklog (manual test)
```bash
curl -s -X POST "https://api.tempo.io/4/worklogs" \
  -H "Authorization: Bearer $TEMPO_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"issueKey\": \"SFDC-1234\",
    \"timeSpentSeconds\": 3600,
    \"startDate\": \"$(date +%Y-%m-%d)\",
    \"startTime\": \"09:00:00\",
    \"authorAccountId\": \"$JIRA_ACCOUNT_ID\",
    \"description\": \"Test entry\"
  }"
```

## Error Codes
| Code | Meaning |
|---|---|
| 401 | Token invalid/expired — regenerate at https://app.tempo.io/ |
| 403 | No permission to log on this Jira issue |
| 404 | Jira issue key not found |
| 429 | Rate limited — wait 60s and retry |
