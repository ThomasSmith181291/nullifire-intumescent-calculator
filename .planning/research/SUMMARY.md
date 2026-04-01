# Research Summary: Nullifire Intumescent Calculator

**Domain:** Structural steel fire protection specification tool
**Researched:** 2026-04-01
**Overall confidence:** HIGH

## Executive Summary

This is an engineering calculation tool with a clear data pipeline: steel section lookup -> section factor calculation -> DFT lookup -> quantity estimation. The stack is already constrained (Flask + vanilla JS + PyWebView + SQLite + Three.js), so research focused on specific library versions, integration patterns, and pitfalls rather than technology selection.

The recommended stack is Flask 3.1.3 with blueprint/factory pattern, AG Grid Community 35.2.0 for data tables (free MIT license, inline editing, sorting, filtering out of the box), Three.js 0.183.x for 3D preview, openpyxl 3.1.5 for Excel I/O, and WeasyPrint 62.x for PDF reports. The frontend uses vanilla JS with ES6 modules and no build toolchain -- this is deliberate because the web developer who inherits the codebase should choose their own framework.

The single most important finding is that the DFT lookup chain must be validated against legacy Steelcalc output before any UI work matters. The database has 44,334 DFT records across complex band/coverage mappings, and getting the lookup wrong is a fire safety liability. Building a comparison test suite is Phase 1 priority number one.

The second key finding is that PyWebView + Flask threading requires a specific pattern (Flask in daemon thread, ready_event synchronization, never call evaluate_js from API threads) that must be established correctly from day one. Getting this wrong causes intermittent deadlocks that are extremely difficult to debug.

## Key Findings

**Stack:** Flask 3.1.3 + AG Grid Community 35.2.0 + Three.js 0.183.x + openpyxl 3.1.5 + WeasyPrint 62.x + PyWebView 6.1. No frontend framework -- vanilla JS with ES6 modules.

**Architecture:** API-first with service layer separation. Flask routes are thin dispatchers; business logic in services. Frontend communicates via fetch() to JSON endpoints. Single source of truth in Flask backend, not JavaScript state.

**Critical pitfall:** DFT lookup chain must match legacy Steelcalc exactly. Build comparison test suite before UI. Conservative (round-up) Hp/A band matching is the safe default.

## Implications for Roadmap

Based on research, suggested phase structure:

1. **Foundation + DFT Engine** - Get the calculation right first
   - Addresses: Flask app shell, PyWebView integration, SQLite connection, DFT lookup chain, comparison test suite
   - Avoids: Building UI on unvalidated calculations (Pitfall 1, 2, 5)
   - Rationale: Everything else depends on correct calculations

2. **Data Entry + Table UI** - Fast member entry is the core UX
   - Addresses: AG Grid setup, section typeahead search, member CRUD, per-member DFT display, verification status, project summary
   - Avoids: AG Grid column sprawl (Pitfall 3 in STACK context), cell editing focus loss
   - Rationale: The tool's value is fast specification; this is where users spend 80% of their time

3. **Import/Export** - Connect to real workflows
   - Addresses: CSV/Excel import with column mapper, Excel export (Quantifire format), PDF specification report
   - Avoids: Guessing Quantifire format (obtain template first), encoding issues on real schedules
   - Rationale: Users have existing data and downstream tools. Import/export connects this tool to their workflow

4. **Structural Grid + 3D Preview** - Visual confirmation layer
   - Addresses: Grid setup UI, level definitions, Three.js wireframe, members as colored lines, bidirectional sync
   - Avoids: Three.js memory leaks, coordinate system confusion, performance cliff with profiles
   - Rationale: 3D is a differentiator but the tool is fully functional without it. Build last so it does not block core functionality

5. **Packaging + Handoff** - Ship it
   - Addresses: PyInstaller build, WeasyPrint DLL bundling, HANDOFF.md documentation, clean Windows testing
   - Avoids: WeasyPrint packaging failures (test early), web dev confusion on data model
   - Rationale: Packaging issues surface late. Documentation is needed for the stated end-goal (web dev inherits codebase)

**Phase ordering rationale:**
- DFT engine first because it is safety-critical and everything displays its output
- Data entry second because it is the core UX and exercises the DFT engine through real usage
- Import/export third because it requires a working member data model (from Phase 2) and known Quantifire format
- 3D fourth because it is additive -- the tool is complete without it, and it requires grid/level data structures
- Packaging last because it should test the complete application, not a partial build

**Research flags for phases:**
- Phase 1: Needs careful investigation of legacy Steelcalc Hp/A matching logic (may require UI automation to extract reference data)
- Phase 3: Quantifire export format is a blocker -- obtain template before starting
- Phase 4: Three.js extruded profiles (if attempted) need performance testing with realistic member counts
- Phase 5: WeasyPrint + PyInstaller compatibility needs early testing (start in Phase 1 with a proof-of-concept)

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions verified current via PyPI/npm. Libraries are mature and well-documented |
| Features | HIGH | Requirements clearly defined in PROJECT.md. Table stakes vs differentiators are straightforward |
| Architecture | HIGH | Flask factory pattern, API-first, service layer -- well-established patterns with extensive documentation |
| Pitfalls | HIGH | DFT lookup and PyWebView threading are well-known problem areas. WeasyPrint packaging is a known issue |
| 3D Performance | MEDIUM | Wireframe phase is trivially fast. Extruded profiles need real-world testing |
| WeasyPrint Packaging | MEDIUM | Works on dev machine; PyInstaller bundling of GTK/Pango deps needs validation on clean Windows |

## Gaps to Address

- **Quantifire import format template**: Not yet available. Must be obtained before Phase 3 (export). This is a project blocker, not a research gap
- **Legacy Steelcalc Hp/A matching logic**: The exact rounding/banding strategy is unknown (obfuscated VB.NET). Need to extract reference data through testing
- **WeasyPrint + PyInstaller on Windows**: Needs proof-of-concept test early. If it fails, fallback is ReportLab or bundled wkhtmltopdf
- **Real structural schedule samples**: Need 3-5 real CSV/Excel files from engineers to test the import column mapper against real-world formatting
