# Canonical SOQL queries

Copy-pasteable queries for the `salesforce-case-transfer-investigation` skill. Every query here has been verified against this org's MCP and avoids known PII / Tooling-API restrictions.

## Step 1 — Core case + history (run in parallel)

### Core case

```sql
SELECT Id, CaseNumber, OwnerId, Owner.Type, CreatedById, CreatedDate,
       LastModifiedById, LastModifiedDate, Status, RecordTypeId,
       RecordType.DeveloperName, Origin, Priority, IsClosed, ClosedDate,
       Type, Reason, Subject, ParentId, AccountId, ContactId,
       Issue_Category__c, Issue_Details__c, Opportunity__c,
       CS_ags__c, MO_Owner_Before_Escalation__c, Escalation_Level__c,
       Skill_Type__c, Violated_Milestone__c, CS_Country__c,
       SkipAssignmentRule__c
FROM Case WHERE CaseNumber = '<CASE_NUMBER>'
```

If any custom field on the SELECT list errors with `INVALID_FIELD`, drop it and retry. Don't include `IsEscalated` — it's not on Case in this org.

### CaseHistory

```sql
SELECT Id, CaseId, Field, OldValue, NewValue, CreatedById, CreatedDate
FROM CaseHistory WHERE Case.CaseNumber = '<CASE_NUMBER>'
ORDER BY CreatedDate ASC LIMIT 500
```

**Never** include `WHERE OldValue = '...'` or `WHERE NewValue = '...'` — those columns are non-filterable in this org's API. Filter client-side after retrieval.

## Step 2 — CaseMilestone (the smoking gun)

```sql
SELECT Id, CaseId, MilestoneTypeId, MilestoneType.Name,
       StartDate, TargetDate, CompletionDate, IsViolated, ElapsedTimeInMins
FROM CaseMilestone WHERE Case.CaseNumber = '<CASE_NUMBER>'
ORDER BY StartDate ASC
```

After fetching, build a list of `Owner → Queue` transitions from CaseHistory and find any CaseMilestone row where:
- `IsViolated = true`
- `CompletionDate` is within 3 seconds of the transition's `CreatedDate`

A match is direct evidence of milestone-driven reassignment.

## Step 3 — ID resolution

### Queues

```sql
SELECT Id, DeveloperName, Type FROM Group WHERE Id IN ('<QUEUE_ID_1>', '<QUEUE_ID_2>', ...)
```

`Group.DeveloperName` is **not** blocked by PII guardrails — queue names are not personal data.

### Users (PII-safe subset only)

```sql
SELECT Id, UserType, IsActive FROM User WHERE Id IN ('<UID_1>', ...)
```

Do **not** add `Name`, `FirstName`, `LastName`, `Email`, `Profile.Name`, `UserRole.Name`. They will be stripped or error. The display names you need are already in `CaseHistory.OldValue` / `NewValue` for `Field='Owner'` rows.

### Active assignment rule

```sql
SELECT Id, Name FROM AssignmentRule WHERE SObjectType = 'Case' AND Active = true
```

## Step 4 — Active flows on Case

```sql
SELECT Id, DeveloperName, ActiveVersionId, LatestVersionId, Description
FROM FlowDefinition
WHERE DeveloperName LIKE '%Case%'
   OR DeveloperName LIKE '%Owner%'
   OR DeveloperName LIKE '%Transfer%'
   OR DeveloperName LIKE '%Assign%'
   OR DeveloperName LIKE '%Queue%'
   OR DeveloperName LIKE '%Escalat%'
   OR DeveloperName LIKE '%Reassign%'
```

Use the Tooling-API endpoint (`mcp__salesforce__sf_tooling_query`). `FlowDefinitionView` is NOT supported in this MCP — use `FlowDefinition`.

To inspect the actual flow logic, read the corresponding XML in `./force-app/main/default/flows/`.

## Step 5 — EmailMessage correlation (optional)

If the case is email-driven and you want to correlate inbound emails with owner changes:

```sql
SELECT Id, Incoming, FromAddress, CreatedDate, MessageDate
FROM EmailMessage WHERE ParentId = '<CASE_ID>' ORDER BY MessageDate ASC
```

Note: `FromAddress` is a string; it is not stripped by the PII guardrail in practice, but treat it as sensitive in any report. Don't dump full email bodies into the chat — summarize.

## Step 6 — Entitlement context (optional)

```sql
SELECT Id, EntitlementId, SlaStartDate, SlaExitDate, BusinessHoursId
FROM Case WHERE CaseNumber = '<CASE_NUMBER>'
```

If `EntitlementId` is null, the case is not on an entitlement and no milestones should exist. If non-null, the milestones come from that entitlement's process.

## What does NOT work via MCP

These sObjects return `not supported`. Don't waste a query — fall back to local repo grep:

- `ApexClass` — grep `./force-app/main/default/classes/`
- `ApexTrigger` — grep `./force-app/main/default/triggers/`
- `LightningComponentBundle` — list `./force-app/main/default/lwc/`
- `CronTrigger` — no fallback; scheduled jobs cannot be enumerated declaratively here
- `EscalationRule` (the API sObject) — read `./force-app/main/default/escalationRules/Case.escalationRules-meta.xml`
- `FlowDefinitionView` — use `FlowDefinition` instead
- `Layout` / `CustomField` and most metadata — use the repo

## Re-running this investigation later

When closing out, list the queries you actually ran (with concrete values substituted). The user may want to feed them to a colleague or re-run six months later. Keep the SOQL portable — avoid hard-coded record Ids except for the queue/user lookups that are unavoidable.
