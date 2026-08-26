# C INVENT Current-State Assessment Model

## Purpose

The Assessment stage is a delivery-readiness gate. It is not a generic LLM summary and it is not the same as Environment Assessment.

- **Discovery** asks: what does the customer want and what do we know about the current business/data landscape?
- **Environment Assessment** asks: what current/target environment is established and what platform capability/access evidence is actually verified?
- **Assessment** asks: given those two evidence sets, is the engagement ready to proceed to architecture, and what gaps must be resolved?

## Assessment dimensions

1. **Business / Use Case** — objectives, processes/use cases, actors, requirements and open decisions.
2. **Data / Sources** — current systems, sources, inventory evidence, migration inputs and data-specific unknowns.
3. **Platform / Environment** — discovered target platform, access status, verified capabilities, constraints and platform gaps.
4. **Governance / Delivery** — security, privacy, compliance, SLA, RPO/RTO, retention and delivery dependencies.

## Evidence rules

Every finding is tied to an evidence source. C INVENT distinguishes customer-stated facts, discovered evidence, verified platform evidence, assumptions and unknowns. Missing evidence is reported as unknown/conditional rather than invented.

## LLM dependency

The Assessment gate is **deterministic and evidence-first**. Capgemini AI can enrich later artifacts, but a Capgemini gateway timeout must not prevent the lifecycle from creating the Assessment artifact or displaying its findings.

## Decisions

- `GO TO ARCHITECTURE` — sufficient evidence for the next stage.
- `CONDITIONAL GO` — architecture can proceed only with recorded gaps/conditions.
- `NO-GO / MORE DISCOVERY REQUIRED` — critical evidence is missing.


## Target platform and provisioning boundary

C INVENT must distinguish four states: **customer-stated direction**, **selected but not provisioned**, **selected and existing**, and **provisioned and verified**. A statement such as “Azure/Databricks target” in Discovery is a customer target direction, not proof that a Databricks workspace exists.

The POC Databricks connector is control-plane/test infrastructure. Its connectivity must never be reported as customer-environment evidence unless the project explicitly records that the connected workspace is the customer's selected existing/provisioned environment.

Provisioning occurs after the target decision and architecture approval through the Platform Workspace. The execution path is either (1) connect and verify a customer-provisioned environment, or (2) execute an approved cloud/IaC provisioning plan using authorized credentials. After provisioning, Environment Assessment is re-run to create the verified customer-environment evidence snapshot.


## Platform Workspace operating model

After Architecture approval, the engagement explicitly confirms the final target platform. Platform Workspace then collects only project configuration (platform, cloud/hosting, existing-vs-provision path, endpoint and secret references). Secrets are never stored in the project database.

C INVENT derives an explainable onboarding state such as `NOT_SELECTED`, `ENDPOINT_REQUIRED`, `CREDENTIALS_REQUIRED`, `READY_TO_VERIFY`, `PROVISIONING_PLAN_REQUIRED`, `PLAN_READY` or `VERIFIED`. Endpoint patterns may auto-detect the platform, but detection is not verification.

For an existing environment, C INVENT verifies through a customer-owned adapter/credential reference. For a new environment, C INVENT generates a reviewable platform-specific provisioning/IaC plan; execution requires authorized customer/cloud credentials and human approval. Only after verification is Environment Assessment allowed to claim customer-environment capability evidence.
