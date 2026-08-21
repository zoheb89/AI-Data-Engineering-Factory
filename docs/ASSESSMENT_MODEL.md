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
