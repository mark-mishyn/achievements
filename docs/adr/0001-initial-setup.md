# ADR 0001: Simple Layered Architecture over Clean Architecture

**Date:** 2026-05-21
**Status:** Accepted

## Context

We needed to choose an architectural style for the Achievements API — a small, focused service running on AWS Lambda. The two main candidates were Clean Architecture (ports & adapters / hexagonal) and a simple layered structure (API → DB, with a separate front-end and infra layer).

## Decision

We adopt a **simple layered architecture** with four explicit layers:
1. API handlers (`src/api/`)
2. Database (`src/db/`)
3. Front-end (`src/frontend/`)
4. Infrastructure (`template.yaml`)

## Rationale

| Consideration | Simple Layered | Clean Architecture |
|---|---|---|
| Codebase size | Small, single service | Better suited to large, multi-domain systems |
| Team size | Small | Pays off with larger teams and many contributors |
| Onboarding speed | Fast — layers map directly to AWS primitives | Steeper — requires understanding ports, adapters, use-case boundaries |
| Boilerplate | Minimal | Significant (interfaces, adapters, use cases, entities) |
| Testability | Sufficient for this scope | Superior, but the overhead isn't justified here |
| Flexibility to change DB/framework | Low risk — DynamoDB and Lambda are stable choices | High — designed for swapping infrastructure |

Clean Architecture's main benefit is protecting the domain from infrastructure details. For a small Lambda service with a stable AWS stack, that isolation adds indirection without delivering meaningful value.

## Consequences

- The codebase stays lean and easy to navigate.
- If the service grows significantly (multiple domains, large team, frequent infrastructure changes), we should revisit and migrate toward a hexagonal style.
- Direct coupling between handlers and DB access is acceptable for now; avoid letting it become tangled as features are added.
