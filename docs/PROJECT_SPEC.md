# TrueIntent — Multi-Channel Fraud Intent Verification System

> The canonical product specification is [`../PROJECT_SPEC.md`](../PROJECT_SPEC.md).

This file previously held an abbreviated, silently divergent copy of the specification. Two copies of
a spec drift, so the copy was removed; the root document is the single source of truth for the
problem statement, personas, module definitions, architecture, tech stack, data requirements,
methodology, risk scoring, evaluation metrics, known limitations and deliverables.

| Document | Purpose |
|---|---|
| [`../PROJECT_SPEC.md`](../PROJECT_SPEC.md) | Full product specification (the original brief) |
| [`architecture.md`](architecture.md) | As-built system description |
| [`DECISIONS.md`](DECISIONS.md) | Build-time scoping decisions |
| [`decision_log.md`](decision_log.md) | Architecture decision records |
| [`LIMITATIONS.md`](LIMITATIONS.md) | Known limitations |
| [`AUDIT_REPORT.md`](AUDIT_REPORT.md) | Repository audit |

Note that the specification describes the *intended* system. Where the implementation deliberately
deviates — most importantly, Module A being an amount-only research benchmark rather than a
transaction-and-call risk engine — the deviation is recorded in
[`MODULE_A_CORRECTNESS.md`](MODULE_A_CORRECTNESS.md) and ADR-006, and this repository does not claim
the specified transaction-correlation behaviour.