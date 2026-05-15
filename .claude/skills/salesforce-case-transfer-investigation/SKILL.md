---
name: salesforce-case-transfer-investigation
description: Investigate exactly how a Salesforce Case was created, transferred, and reassigned throughout its lifecycle — who owned it, when, and which automation (Apex trigger, Flow, Workflow Rule, Assignment Rule, Escalation Rule, Entitlement Milestone, Omni-Channel, transferModal LWC, or manual UI) caused each ownership change. Use this whenever the user references a Case Number or Case Id and asks anything resembling "how did this case get reassigned", "why is this case in the wrong queue", "who transferred this", "trace the owner history", "audit the case lifecycle", "investigate case escalation", "debug case routing", "explain the ownership timeline", or supplies a Case Number with a request to understand its routing/escalation/transfer behavior. Trigger even when the user does not name a specific automation type — they often don't know which mechanism caused the move, and identifying that is the skill's primary job.
---

# Salesforce Case Transfer Investigation

You are investigating how ownership changed on a single Salesforce Case from creation to its current state. Most cases of this kind have **multiple concurrent transfer mechanisms** (manual `transferModal` clicks AND automatic milestone-violation routing both touch `Case.OwnerId`), so the goal is not to find "the" mechanism but to attribute **each** ownership change to its actual cause with a confidence level.

## Pre-flight

Before running queries, confirm with the user (one short ask, only if not obvious from context):

- **Which org/sandbox?** Default to **prod** via `mcp__salesforce__sf_query`. If the user is in a sandbox-investigation context, ask.
- **Declarative-only or include Apex debug logs?** Default to **declarative-only** (CaseHistory + CaseMilestone + Apex source code in repo). Logs require additional pulls.

If the Case Number/Id isn't provided, ask for it. Don't fabricate one.

## Investigation steps

Run these in the order below. Earlier steps inform what to look for in later steps. Use a TodoWrite list with one item per step so the user sees progress.

### 1. Core case details + ownership history (parallel)

Fire these two queries together. They are independent and the rest of the investigation can't start without both.

```sql
-- Core case
SELECT Id, CaseNumber, OwnerId, Owner.Type, CreatedById, CreatedDate,
       LastModifiedById, LastModifiedDate, Status, RecordTypeId,
       RecordType.DeveloperName, Origin, Priority, IsClosed, ClosedDate,
       Type, Reason, Subject, ParentId, AccountId, ContactId,
       Issue_Category__c, Issue_Details__c, Opportunity__c
FROM Case WHERE CaseNumber = '<CASE_NUMBER>'

-- Full ownership/field history — ORDER ASC, no WHERE on OldValue/NewValue
SELECT Id, CaseId, Field, OldValue, NewValue, CreatedById, CreatedDate
FROM CaseHistory WHERE Case.CaseNumber = '<CASE_NUMBER>'
ORDER BY CreatedDate ASC LIMIT 500
```

See [references/known-gotchas.md](references/known-gotchas.md) — `OldValue`/`NewValue` cannot be filtered, grouped, or sub-queried server-side in this org's API. Pull all rows and filter client-side.

Some fields may not exist on the org's Case schema (`IsEscalated` is missing in this org, for example). If a query fails with `INVALID_FIELD`, drop the offending field and retry rather than guessing custom field names. Custom fields you can rely on for PM cases: `Issue_Category__c`, `Issue_Details__c`, `Opportunity__c`, `CS_ags__c`, `MO_Owner_Before_Escalation__c`, `Escalation_Level__c`, `Skill_Type__c`, `Violated_Milestone__c`.

### 2. CaseMilestone — the smoking gun for SLA-violation reassignments

This is the single most important query for understanding auto-reassignments. Time-based owner changes in this org are almost always driven by Entitlement Milestone violations, not by time-based workflow rules.

```sql
SELECT Id, CaseId, MilestoneTypeId, MilestoneType.Name, StartDate, TargetDate,
       CompletionDate, IsViolated, ElapsedTimeInMins
FROM CaseMilestone WHERE Case.CaseNumber = '<CASE_NUMBER>'
ORDER BY StartDate ASC
```

After pulling, build a sorted list of all `Owner → Queue` transitions from CaseHistory. For each, scan CaseMilestone for any row where `CompletionDate` is within ~3 seconds of the Owner change AND `IsViolated = true`. A match is direct evidence the milestone violation drove the owner change.

Common milestone types in this org:
- `First Response Time` — 24h, mostly informational
- `Stale Case MS` — 12h business-hours, drives top-tier MO reassignments
- `Stale Case 48 hours` — 48h, drives generic stale reassignments
- `Stale Case Top Tier` — 24h, drives top-tier reassignments after April 2026
- `Stale Case MO` — special MO stale handling

### 3. Resolve user, queue, account IDs (declarative, PII-safe)

Use the Group object to resolve queue IDs (queue names are not PII):

```sql
SELECT Id, DeveloperName, Type FROM Group WHERE Id IN ('<QUEUE_ID_1>', ...)
```

For Users, the `sf_query` MCP tool **strips fields that contain personal info** (Name, FirstName, LastName, Email, Phone, Profile.Name, UserRole.Name, etc.) — these will error or be unavailable. Query only `Id, UserType, IsActive`:

```sql
SELECT Id, UserType, IsActive FROM User WHERE Id IN ('<UID_1>', ...)
```

The user's display names are already in CaseHistory `OldValue`/`NewValue` for Owner-type rows, so PII resolution is rarely needed. If the user explicitly asks "who is user X", point them at the Owner field history rows rather than running a Name query.

### 4. Identify automation sources

Many Tooling-API sObjects are **not exposed** through this org's MCP (see [references/known-gotchas.md](references/known-gotchas.md)). For those, fall back to grepping the local Salesforce DX project at `./force-app/main/default/`.

Run these searches in parallel:

**Active assignment rule** (declarative API works):
```sql
SELECT Id, Name FROM AssignmentRule WHERE SObjectType = 'Case' AND Active = true
```

**Active flows** (Tooling API, `FlowDefinition` works; `FlowDefinitionView` does not):
```sql
SELECT Id, DeveloperName, ActiveVersionId, Description
FROM FlowDefinition
WHERE DeveloperName LIKE '%Case%' OR DeveloperName LIKE '%Owner%'
   OR DeveloperName LIKE '%Transfer%' OR DeveloperName LIKE '%Assign%'
   OR DeveloperName LIKE '%Queue%' OR DeveloperName LIKE '%Escalat%'
```

**Apex triggers, classes, LWC, workflows, escalation rules** — Tooling API does NOT expose these. Grep the repo instead:

```bash
find ./force-app/main/default/triggers -type f -name '*Case*'
find ./force-app/main/default/classes -name 'Case*' -o -name '*CaseAssign*' \
     -o -name '*CaseOwner*' -o -name '*CaseRouting*' -o -name 'CustSupport*' \
     -o -name '*Stale*' -o -name '*Escalat*'
find ./force-app/main/default/lwc -type d \( -name 'transfer*' -o -name '*Escalat*' \)
ls ./force-app/main/default/workflows/Case.workflow-meta.xml
ls ./force-app/main/default/escalationRules/Case.escalationRules-meta.xml
ls ./force-app/main/default/flows/ | grep -iE 'case|owner|reassign|escalat'
```

Read [references/automation-sources.md](references/automation-sources.md) for the canonical map of where each automation type lives and which Apex handlers are known to mutate `Case.OwnerId`.

### 5. Inspect transferModal LWC + Apex escalation paths

The `transferModal` LWC is the primary user-facing transfer surface in this org. It maps user-selected Escalation Level → an Apex method in `CustSupportCaseService` (and a few peer classes).

- LWC source: [transferModal.js](../../../../Documents/New SFRepo 2026/SFDC/force-app/main/default/lwc/transferModal/transferModal.js) — read the `escalationActions` map (around lines 53-72) to see which Escalation Level invokes which Apex method.
- Apex source: [CustSupportCaseService.cls](../../../../Documents/New SFRepo 2026/SFDC/force-app/main/default/classes/CustSupportCaseService.cls) — `escalateToMO`, `sendBackToMOCase`, `escalateToCO`, `escalateToTL`, `escalateToECE`, `escalateToTravelAdmin`, `escalateToExtranetAdmin`, etc. Each writes a known queue ID or a `MO_Owner_Before_Escalation__c` restore.

Pattern recognition for the timeline:
- **Queue → Person** within minutes = manual claim from queue (Lightning UI)
- **Person → MO user** with `Issue_Category__c`/`Issue_Details__c` changed in the same second = transferModal "Escalate to MO"
- **Person → MO user** with no other field changes and `Status: Re-open → New` = transferModal "Send Back to MO" (`sendBackToMOCase`)
- **Person → Queue** with no other field changes AND a matching `CaseMilestone.CompletionDate` with `IsViolated=true` within 3 seconds = milestone-violation auto-route (NOT a user click)

### 6. Build the report

Use the structure in [references/report-template.md](references/report-template.md). Key requirements:

- One row per `OwnerId` change in CaseHistory. Group paired rows (Salesforce writes two `Field=Owner` history rows per change — one with names, one with IDs) into a single timeline entry.
- For each row, name the **mechanism** and assign a **confidence level** (High/Medium/Low). High means there's direct timestamp evidence (a matching milestone, a same-transaction field-change, an Apex method whose code matches the resulting queue ID).
- Include the **SOQL queries used** at the end of the report so the user can re-run or extend the investigation.
- Note any **gotchas observed** (inactive owner, cross-record-type transitions, milestone clock pauses for business hours/weekends).

## Important rules

- **Never guess.** If evidence is insufficient for a row, mark confidence Low and explain what's missing. Insufficient evidence ≠ "automated process did it."
- **CaseHistory CreatedById is misleading for automation-driven owner changes.** When an Entitlement Milestone violation, time-based workflow action, or scheduled job fires, Salesforce attributes the resulting CaseHistory row to the user who *last* modified the record — not to the `Automated Process` user. Do not treat the CreatedById as the acting user for milestone-driven rows. The CaseMilestone correlation in step 2 is authoritative.
- **A case usually has multiple concurrent transfer mechanisms.** Don't pick "the one cause" — attribute each row independently. Manual `transferModal` clicks and milestone-violation auto-routing routinely interleave on the same case (this is normal in this org's PM Case lifecycle).
- **Don't query Profile.Name / UserRole.Name / User.Name / .Email / .Phone.** The MCP tool blocks fields whose names suggest PII. The display names of users involved are already present in CaseHistory `OldValue`/`NewValue` for Owner rows.
- **Convert relative dates to absolute UTC** in the report. Salesforce returns UTC; note this and let the user mentally convert if they need their local zone.
- **Prefer the live org over the repo for state, prefer the repo over the org for logic.** Live SOQL tells you what happened; the repo tells you which Apex class made it happen.

## Output format

Produce the final report inline in the chat using the template at [references/report-template.md](references/report-template.md). Do not write the report to a file unless the user asks. Do, however, mention that the SOQL queries are available for re-use.

Keep the report scannable — a table for the timeline, separate sections for each automation type, and a clearly-labeled "Final Root Cause" with confidence. End with "Notable findings / gotchas" only when there's something genuinely surprising (inactive user, abandoned record type, milestone clock anomaly).
