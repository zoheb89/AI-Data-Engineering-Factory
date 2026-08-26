# C INVENT Full Build Fix

## Engineering Gateway Timeout

AI Engineering Factory no longer sends one large Medallion-generation request to the Capgemini gateway.

Engineering is generated as resumable bounded components:

- Bronze
- Silver
- Gold
- Data Quality
- Orchestration
- Testing
- Code Artifacts

Each component is persisted as it completes. A timeout/failure records the failed component and a generation checkpoint. Retry resumes from the failed component and does not regenerate successful components.

The engineering orchestrator no longer performs a second full retry after `invoke_json`; the LLM adapter already performs bounded gateway retries with smaller requests.

## Control Plane Gate Fix

Direct navigation cannot authorize downstream execution.

Metadata and Engineering require:

- Current Architecture approval
- Customer target platform `VERIFIED`
- Environment Assessment refreshed after platform verification
- Current-State Assessment refreshed from that Environment Assessment
- Metadata generated from the approved Architecture before Engineering

`PLAN_READY` is not sufficient for Metadata/Engineering because it does not prove a customer environment exists.

## Platform Verification Lifecycle

After Databricks verification, Platform Workspace directs the user to refresh Environment Assessment. Current-State Assessment must then be refreshed before Metadata/Engineering execution.

Databricks Free / workspace-only testing remains supported through host + secret reference/PAT. Production cloud ownership is still captured separately when the customer environment is provisioned.

## Safety

- Customer PAT values are never persisted or displayed.
- C INVENT POC/global Databricks credentials are never used as customer evidence.
- AI generation does not deploy to Databricks.
- Deployment remains a separate validated/approved lifecycle step.

## Validation

`34` automated tests pass in the supplied build after the fixes.
