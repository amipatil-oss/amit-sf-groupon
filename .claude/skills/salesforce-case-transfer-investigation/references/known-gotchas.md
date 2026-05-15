# Known gotchas — Salesforce MCP + this org's Case schema

Reference for the `salesforce-case-transfer-investigation` skill. Updates here apply on the next skill invocation — no code change required.

## 1. PII guardrails on `mcp__salesforce__sf_query`

The MCP tool strips fields whose names suggest personal info. The following will error or return empty:

- `User.Name`, `User.FirstName`, `User.LastName`, `User.FullName`
- `User.Email`, `User.Phone`, `User.MobilePhone`
- `User.Profile.Name`, `User.UserRole.Name`
- `Case.SuppliedName`, `Case.SuppliedEmail`, `Case.SuppliedPhone` (occasionally — depends on field-level metadata)
- Any join through these relationships (`Owner.Name`, `Account.Owner.Profile.Name`, etc.)

**Workaround:** Query Ids only and resolve via context. For users, the display names are already in `CaseHistory.OldValue`/`NewValue` for `Field='Owner'` rows — use those instead of joining to `User.Name`. For queue names, `Group.DeveloperName` is **not** blocked.

Safe User fields: `Id, UserType, IsActive`.

## 2. `CaseHistory.OldValue` and `NewValue` cannot be filtered server-side

In this org's API, these fields cannot appear in `WHERE`, `GROUP BY`, or sub-queries. Queries like `WHERE NewValue = '...'` fail.

**Workaround:** Pull all rows for the case ordered ASC by `CreatedDate`, filter client-side. Use `LIMIT 500` as a sanity cap — long-running cases can have hundreds of history rows.

## 3. Tooling API sObjects NOT exposed by this MCP

These return `sObject type 'X' is not supported`:

- `ApexClass`
- `ApexTrigger`
- `LightningComponentBundle`
- `CronTrigger` (so no direct way to enumerate scheduled jobs)
- `EscalationRule` (the standard API one — but the metadata XML in the repo works)
- `FlowDefinitionView`
- `Layout`, `CustomField`, and most metadata sObjects

These **do** work via Tooling API: `FlowDefinition` (without `View`).

**Workaround:** Grep `./force-app/main/default/` in the local SFDX project. Key paths:
- `triggers/` — `CaseTrigger.trigger`, `CaseJunctionTrigger.trigger`, `CaseLifecycleEventTrigger.trigger`
- `classes/` — `CustSupportCaseService.cls`, `CaseRoutingHelper.cls`, `CaseRoutingWorkflow.cls`, `CaseOwnerUpdatePartnerManagement.cls`, `StaleCaseAssignmentToSalesManager.cls`, etc.
- `lwc/transferModal/`, `lwc/transferQuickAction/`
- `workflows/Case.workflow-meta.xml`
- `escalationRules/Case.escalationRules-meta.xml`
- `flows/` — flow XML files

## 4. `CaseHistory.CreatedById` is misleading for automation rows

When a CaseHistory row results from any of:
- An Entitlement Milestone violation action
- A time-based workflow rule action
- A scheduled Apex job
- A platform event-driven update

…Salesforce attributes the resulting field-change history row to the **user who last modified the record**, not to `Automated Process`. So the "Owner → Queue" rows you see during a milestone violation cycle will show the previous claim user, not a system user.

**Workaround:** Correlate the `CreatedDate` against `CaseMilestone.CompletionDate` where `IsViolated = true`. A match within ~3 seconds means the row was milestone-driven regardless of what `CreatedById` says.

## 5. Cases routinely have multiple concurrent transfer mechanisms

A single Case lifecycle commonly mixes:
- Initial **Case Assignment Rule** (only fires once, at insert)
- Manual **transferModal LWC** clicks (Escalation Level dropdown → Apex method)
- Automatic **Entitlement Milestone violation** routing (`StaleCaseAssignmentToSalesManager` reads `Violated_Milestone__c`)
- Manual **OwnerId edits** from the Lightning record page
- **Omni-Channel** routing (post-April 2026 cutover for Content Ops + 12 Deal Edit queues)
- **CaseRoutingWorkflow** re-routing on `CS_ags__c → '#AICategorization'` transition

Don't try to pin "the cause" — attribute each row individually. A single 60-day case can have 30+ owner changes with 5+ distinct mechanisms.

## 6. Case Owner field history writes TWO rows per change

Salesforce writes:
- One row with `OldValue` / `NewValue` containing the display **name** (e.g., "Jesus Cortiña Varela")
- One row with `OldValue` / `NewValue` containing the **Id** (e.g., `005C0000005OfZjIAK`)

Both share the same `CreatedDate` and `CreatedById`. When building the timeline, pair them so each visible transition is one row, not two.

## 7. Custom field availability (this org)

Confirmed available on Case:
- `Issue_Category__c`, `Issue_Details__c`
- `Opportunity__c` (lookup)
- `CS_ags__c` — tag string, contains escalation flags like `CStoMOesc`, `MOdirectesc`, `CStoGMesc`, `#AICategorization`
- `MO_Owner_Before_Escalation__c` (User lookup, used for send-back-to-MO)
- `Escalation_Level__c` (picklist, drives transferModal action map)
- `Skill_Type__c` (e.g., 'Top Tier Stale', 'CS Email')
- `Violated_Milestone__c` (string, set by milestone violation actions)
- `CS_Country__c`, `CS_ags__c`, `Feature_Country_Account__c`
- `SkipAssignmentRule__c` (set true by Apex routing to suppress assignment rules)

Confirmed NOT on Case in this org: `IsEscalated` (standard field is disabled or removed). Don't include it.

## 8. Org context (as of 2026-05)

- Omni-Channel Routing was enabled for Content Ops + 12 Deal Edit queues in late April 2026 cutover.
- The `MO_Top_Tier_Queue` custom label resolves to **Merchant Support - High Priority** queue (`00GUj000009HQ5lMAG`).
- The `Merchant_Support_Queue` custom label resolves to **Merchant Support** queue (different from High Priority).
- The `StaleCaseTopTierUser` custom label is a comma-separated list of User Ids treated as top-tier MOs; ownership held by these users triggers the `Stale Case Top Tier` milestone (24h) instead of the generic stale milestones.
