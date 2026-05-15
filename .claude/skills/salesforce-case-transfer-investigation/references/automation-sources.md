# Automation sources — where each transfer mechanism lives

Reference for the `salesforce-case-transfer-investigation` skill. When you need to attribute an ownership change to a specific automation, this is the map.

## The trigger pipeline (CaseTrigger.trigger)

`force-app/main/default/triggers/CaseTrigger.trigger` is the entry point. It dispatches to handler classes via `TriggerServices.runTriggerWorkflow(...)`. Read this file first to see which handlers run in which trigger phase. Bypass switch: `TriggerBypassConstants.CASE_TRIGGER_BYPASS`.

Handlers that **mutate `Case.OwnerId`** (search for `OwnerId =` in their source):

| Handler | Phase | Trigger condition (rough) |
|---|---|---|
| `CasesAutoAssignmentWorkflow` | Before insert/update | Routes based on legacy auto-assignment rules |
| `CaseOwnerUpdatePartnerManagement` | Before insert/update | PM Case + email origin → routes to Merchant Consultant on the Account |
| `CaseOwnerUpdateMCSelfServiceWorkflow` | Before insert | MC Self Service record type routing |
| `CaseOwnerUpdateWorkflow` | Before update | Generic owner re-routing |
| `ReassignPMtoCSCaseWorkflow` | Before update | PM Case status: Closed → Re-open with CS tags → routes to CS queue |
| `CaseAccContactAssignmentWorkflow` | Before insert/update | Sets owner based on Account/Contact context |
| `CasePMAccountAssignmentWorkflow` | Before insert | PM Case account-owner inheritance |
| `SalesCaseSkipAssignmentRuleWorkflow` | Before insert | Sets `SkipAssignmentRule__c = true` for sales cases |
| `CaseRoutingWorkflow` | **After insert/update** | Routes based on `Issue_Category__c + Issue_Details__c → CaseRoutingHelper`. After update only fires when `CS_ags__c` transitions to `#AICategorization`. |
| `StaleCaseAssignmentToSalesManager` | **After update** | Reads `Violated_Milestone__c`. Reassigns to MO queue / Top Tier queue / case owner's ManagerId. **This is the milestone-violation auto-router.** |
| `CaseAssignmentRuleWorkflow` | After update | Re-fires assignment rule programmatically when needed |

When an ownership change has no matching milestone violation, walk this list (in trigger-phase order) and check each handler's qualification logic against the case state at the time of the change.

## The transferModal LWC + Apex escalation map

User-facing transfer surface. The LWC presents an "Escalation Level" dropdown; selecting a value calls a specific Apex method.

Source: `force-app/main/default/lwc/transferModal/transferModal.js`, around the `escalationActions` map (~lines 53-72):

| Escalation Level (picklist value) | Apex method | Target |
|---|---|---|
| `Merchant Operations` | `CustSupportCaseService.escalateToMO` | Country → MO queue mapping in `Country_Code_Owner_Queue__mdt`, defaults to US queue |
| `Merchant` | `Local3WTMerchantEscalation.escalateToMerchant` | 3WT merchant escalation |
| `Goods Merchant` | `CustSupportCaseService.escalateToGoods` | `System.label.Goods_Marketplace_Queue_ID` |
| `Risk` | `CustSupportCaseService.escalateToECE` | `System.label.ECE_Escalation_OwnerId` |
| `Team Lead` | `CustSupportCaseService.escalateToTL` | `System.label.TL_Escalation_OwnerId` |
| `Image Designer` | `CustSupportCaseService.escalateToID` | Image designer routing |
| `Sales` | `CustSupportCaseService.escalateToSales` | Account Manager / mapped sales owner |
| `Image Edit (CO)` / `Content Edit (CO)` | `CustSupportCaseService.escalateToCO` | Content Operations queue |
| `National Redemption` | `CustSupportCaseService.escalateToNR` | NR queue |
| `MO Goods (NAM)` | `CustSupportCaseService.escalateToMOGoodsNAM` | NAM MO Goods queue |
| `Send Back to MO` | `CustSupportCaseService.sendBackToMO` → `sendBackToMOCase` | `MO_Owner_Before_Escalation__c` if user profile == 'Account Management', else Merchant_Support queue |
| `Send to Sales` | `CustSupportCaseService.sendToSalesFromCO` | Sales send-back from Content Ops |
| `Send Back to CO` | `CustSupportCaseService.sendBackToCO` | Content Ops send-back |
| `Customer Support` | `GPN_SendBackToCSController.moveBackToCS` | CS queue based on country |
| `Travel Deal Admin` | `CustSupportCaseService.escalateToTravelAdmin` | `SSC Travel Deal Admin` queue |
| `Extranet Admin` | `CustSupportCaseService.escalateToExtranetAdmin` | `Extranet Admin` queue |
| `Signifyd - Rejected Transaction` | `CustSupportCaseService.updateSignifydCaseId` | Signifyd-specific update |

The `transferQuickAction` LWC is a sibling component used as a quick action button — same Apex backend, leaner UI.

## CaseRoutingHelper (the bulk routing engine)

`force-app/main/default/classes/CaseRoutingHelper.cls`

Maps `(Issue_Category__c, Issue_Details__c)` → `Case_Routing_Config__mdt.Routing_Name__c` → one of Routing 1/3/4/5/6. Each routing function evaluates account attributes (Top Tier check: country in FR/ES/DE/NL/BE + TMC_Wave A/B or Is_Premier__c + not Goods/Travel category) and returns either a queue Id or a user Id.

Top-tier merchants always route to `Merchant Support - High Priority`. Non-top-tier defaults to `Merchant Support`. Routing 6 is Content Operations and routes to country-specific Deal Edit queues.

Called from `CaseRoutingWorkflow` (the trigger handler) — not directly from user actions.

## Entitlement Milestones (the time-based auto-router)

Cases on entitlement-equipped record types have milestones tracked in `CaseMilestone` records. Milestone Types observed in this org:

| MilestoneType.Name | MilestoneTypeId (prod) | Target | Effect on violation |
|---|---|---|---|
| First Response Time | `557Uj0000000OqLIAU` | 24h | Mostly tracking; no owner change |
| Stale Case MS | `557Uj000000RbMrIAK` | 12h business-hours | Sets `Violated_Milestone__c` → milestone violation action reassigns to Merchant Support - High Priority queue |
| Stale Case 48 hours | `557Uj000000RbLFIA0` | 48h | Triggers `StaleCaseAssignmentToSalesManager`, branches on `StaleCaseTopTierUser` |
| Stale Case Top Tier | `557Uj000000F7HJIA0` | 24h | Routes to `MO_Top_Tier_Queue` = Merchant Support - High Priority |
| Stale Case MO | (varies) | varies | Posts OCR comment, clears `Violated_Milestone__c` |

The violation actions are configured **in Setup → Entitlement Management**, not in this repo's metadata. To see them, you'd need Setup audit trail access. For investigation purposes, the rule is: if `CaseMilestone.CompletionDate ≈ Owner-change time` and `IsViolated = true`, the milestone caused the move.

## Assignment Rules

`AssignmentRule WHERE SObjectType = 'Case' AND Active = true` — there is exactly one active rule in this org: `Main Case Assignment` (`01QC0000000HCs1MAG`). It fires once at insert (or when a trigger explicitly re-fires it via `Database.DMLOptions.assignmentRuleHeader`).

Most owner-mutating Apex handlers set `SkipAssignmentRule__c = true` to suppress re-firing on their own updates. So Assignment Rule activity is almost always limited to the initial create event.

## Escalation Rules

`force-app/main/default/escalationRules/Case.escalationRules-meta.xml` — one active rule: `MC Self Service Case Escalation`. Two rule entries (US vs INTL). 180-minute escalation to `US_Merchant_Support_Escalations` or `INTL_Merchant_Support_Escalations` queue. **Only fires for `RecordType.Name = 'MC Self Service'`** — does not apply to Partner Management Cases.

## Workflow Rules (declarative)

`force-app/main/default/workflows/Case.workflow-meta.xml` — large file with many rules. Time-based actions (`workflowTimeTriggers`) observed:
- 48h / 72h / 24h offsets from `Last_Inbound_Email_Received_Time__c` (merchant notify rules)
- 1h offsets from `LastModifiedDate` (status update rules)
- 24h / 48h offsets from `ClosedDate` (echo survey scheduling)

**No active workflow rule has an owner-changing field update with a 12h time trigger.** If you see a 12h-cycle ping-pong, it is almost certainly Entitlement Milestone driven, not workflow-rule driven.

## Flows

`force-app/main/default/flows/` — most Case-related flows are surveys or notifications. Relevant flows that touch ownership:

| Flow | Effect |
|---|---|
| `Reassign_cases_to_MO_queues_after_48_hours` | Misnamed — actually 7/10/17-day email notifications, NOT an owner change |
| `Update_Record_Owner_MD_Account_Prioritization` | Updates record owner on account prioritization changes |
| `CS_Merchant_Issue_Case_Reassignment_to_Creator` | Reassigns CS-tagged cases back to the creator |
| `Record_Triggered_Before_Save_Case_Flow` | Before-save record-triggered flow; check for OwnerId mutations |
| `Record_triggered_Case_create_After_save` | After-save record-triggered flow on Case create |

Pull flow XML and grep for `<targetReference>OwnerId</targetReference>` to confirm whether a flow mutates ownership.

## Omni-Channel Routing

Enabled in late April 2026 for Content Ops + 12 Deal Edit queues. If the case's current owner is one of those queues and the case was created/routed after the cutover date, expect Omni-Channel to have assigned the work item. Look for `PendingServiceRouting` records (if exposed) or correlate with the queue assignment timestamp.

## Manual UI edits

If a row has no matching milestone, no matching handler logic, and changes only `OwnerId` (no other fields in the same transaction), it's almost certainly a manual Lightning record-page edit by the user in `CreatedById`. Confidence: Medium unless the user's CreatedById matches a non-automation context.
