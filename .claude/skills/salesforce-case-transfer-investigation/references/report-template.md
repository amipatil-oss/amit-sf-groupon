# Investigation report template

Use this exact structure for the final report. Fill in sections; omit only when truly empty.

---

```
# Case Transfer Investigation Summary — Case <CASE_NUMBER>

## Case Overview

| Field | Value |
|---|---|
| Case Number | <CASE_NUMBER> |
| Case Id | <CASE_ID> |
| Record Type | <RECORD_TYPE_DEVELOPER_NAME> |
| Origin | <ORIGIN> |
| Priority | <PRIORITY> |
| Account | <ACCOUNT_ID> |
| Parent Case | <PARENT_ID or "—"> |
| Created By | User <CREATED_BY_ID> at <CREATED_DATE_UTC> |
| Initial Issue | Issue_Category__c = "<...>", Issue_Details__c = "<...>" |
| Final Issue | Issue_Category__c = "<...>", Issue_Details__c = "<...>" |
| Current Status | <STATUS> at <LAST_MODIFIED_DATE_UTC> |
| Final Owner | User/Queue <OWNER_ID> |
| Active assignment rule at create | <RULE_NAME or "none"> |

---

## Ownership Timeline (chronological)

| # | Time (UTC) | Old Owner | New Owner | Acting User (CreatedById) | Mechanism (confidence) |
|---|---|---|---|---|---|
| 0 | <YYYY-MM-DD HH:MM:SS> | — (create) | <Initial Owner Name> (<Id>) | <CreatedById> | <Mechanism> (High/Medium/Low) |
| 1 | ... | ... | ... | ... | ... |

Pair the two CaseHistory rows that Salesforce writes per Owner change into one timeline row. For automation-driven rows, write "(last toucher)" next to CreatedById to remind the reader why it's not the real actor.

---

## Automation Analysis

### Assignment Rule
- **Rule**: <name> (<id>)
- **Fired**: at create / never / re-fired at <time> via <Apex class>
- **Why**: <brief>

### Flow Analysis
- <Flow name>: <fired / did not fire / N/A> — <reason>
- ...

### Apex Analysis
- <Class.method (file:line)>: <triggered / did not trigger> — <condition matched or not>
- ...
- The handler(s) that actually mutated Owner during this lifecycle: <list>

### Entitlement Milestones
- <MilestoneType.Name> (<target_hours>h): <count> violations, drove rows #<list>
- ...

### transferModal LWC Analysis
- Escalation paths invoked during the lifecycle: <list of Apex methods>
- Rows attributable to user clicks: #<list>

### Manual UI edits
- Rows with no matching automation: #<list> — most likely manual Lightning page edits by <CreatedById>

---

## Final Root Cause

<2-4 sentence summary explaining the dominant pattern. If there are multiple cooperating mechanisms, describe how they interact. State confidence: High / Medium / Low and explain what evidence supports the level.>

---

## Notable findings / gotchas

(Include only if there's something surprising — otherwise omit this section.)

- <inactive user holding the case>
- <record type changed mid-lifecycle>
- <milestone clock paused for weekend>
- <conflicting automation that both tried to change owner in same transaction>

---

## SOQL queries used

```sql
-- Core case
SELECT ... FROM Case WHERE CaseNumber = '...'

-- Full ownership/field history
SELECT ... FROM CaseHistory WHERE Case.CaseNumber = '...' ORDER BY CreatedDate ASC

-- Milestone correlation
SELECT ... FROM CaseMilestone WHERE Case.CaseNumber = '...' ORDER BY StartDate ASC

-- Queue lookup
SELECT Id, DeveloperName, Type FROM Group WHERE Id IN (...)

-- (other queries actually used, in order)
```

The above queries are re-runnable; save them if you intend to re-investigate or build a parallel timeline.
```

---

## Field-by-field guidance

**Mechanism column values** (use these exact phrases for consistency):
- `Case Assignment Rule "<Name>"` — for the create event when an assignment rule was active
- `transferModal LWC → <Apex method>` — e.g., `transferModal LWC → CustSupportCaseService.escalateToMO`
- `transferModal LWC → sendBackToMO` — for the send-back pattern
- `Entitlement Milestone "<MilestoneType.Name>" violation → milestone violation action` — for the milestone auto-router
- `StaleCaseAssignmentToSalesManager (Violated_Milestone__c=<value>)` — when the Apex handler is the one routing
- `CaseRoutingWorkflow → CaseRoutingHelper Routing <N>` — for AI-categorization re-routes
- `Manual claim from queue (Lightning UI)` — for Queue → Person within minutes
- `Manual record-page edit` — when no other automation fits

**Confidence levels:**
- **High** — direct timestamp evidence: matching milestone violation (within 3s), same-transaction same-field changes that the Apex method writes, or Apex method's hard-coded queue Id matches the resulting Owner.
- **Medium** — pattern matches but evidence is circumstantial. Example: a "Queue → User" change where the user is in the queue's membership and the timing is plausible but no LWC click can be confirmed.
- **Low** — no automation matches and no plausible manual action. Flag for follow-up.

**When in doubt, write Low and explain.** The user can usually narrow it down once you surface what's missing.
