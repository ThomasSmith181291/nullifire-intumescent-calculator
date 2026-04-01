# Phase 1: DFT Engine & Foundation - Context

**Gathered:** 2026-04-01
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase — discuss skipped)

<domain>
## Phase Boundary

A validated calculation engine that returns correct DFT values for any product/section/fire-rating combination, served through a Flask API in a PyWebView desktop window. This phase creates the entire backend foundation that all subsequent phases build on.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — pure infrastructure phase. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

Key technical context from project research:
- Flask 3.1 with app factory pattern and blueprints (api + main)
- Service layer owns business logic, routes are thin dispatchers
- PyWebView as dumb localhost wrapper — Flask in daemon thread, no JS-Python bridge
- SQLite database already exists at data/nullifire.db with verified schema
- DFT lookup chain verified: Section → Band → Hp/A → coverage_id (exact min=max match) → DFT
- AG Grid Community 35.2.0 for future data tables (Phase 2 will need these API endpoints)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `data/nullifire.db` — Complete SQLite database with steel sections, DFT data, products, section factors, coverage ranges
- `export_data.py` — Data extraction script (reference only, not part of the app)

### Established Patterns
- None yet — this is the first phase, establishing all patterns

### Integration Points
- Phase 2 will consume all API endpoints created here
- Phase 3 will add verification logic on top of DFT calculations
- Phase 4 will add import/export using the same data model
- Phase 5 will add 3D visualization using grid/level data

</code_context>

<specifics>
## Specific Ideas

- 5 active Nullifire products: SC601 (ID=278), SC801-120 (ID=283), SC802 (ID=266), SC804 (ID=324), SC901 (ID=284)
- DFT test harness should compare against known Steelcalc outputs — extract reference data from legacy app
- PyWebView must use Flask-in-daemon-thread pattern with ready_event synchronization
- API must be stateless and RESTful for future web migration

</specifics>

<deferred>
## Deferred Ideas

None — infrastructure phase.

</deferred>
