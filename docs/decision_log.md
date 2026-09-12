# Decision Log

## ADR-001: Project Architecture & Scaffolding Strategy
- **Date**: 2026-09-12
- **Status**: Approved
- **Context**: TrueIntent requires a modular structure isolating ML model pipelines, backend API logic, frontend presentation, data stores, tests, and project documentation.
- **Decision**: 
  - Monorepo folder structure with `/backend` (FastAPI), `/frontend` (React), `/ml` (training scripts, notebooks, models), `/data` (raw & processed), `/tests`, and `/docs`.
  - Privacy-by-design: `data/raw/*` is strictly ignored in git to ensure zero user PII or raw transaction leaks into source control.
- **Consequences**: Enables clean separation of concerns and step-by-step modular implementation across iterations.
