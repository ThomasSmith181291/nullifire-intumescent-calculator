# Nullifire Intumescent Calculator

## What This Is

A modern intumescent coating specification tool for Nullifire products that replaces the legacy Steelcalc VB.NET application. Users — both sales/technical reps and contractors — can rapidly specify DFT coatings for structural steel members, verify compliance, and export specifications for Quantifire. Includes a 3D structural grid preview that builds as members are added.

## Core Value

Fast, component-by-component steel member input with instant DFT verification — what takes dozens of clicks in Steelcalc should take seconds here.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Project creation with name, default product, fire rating, and failure temperature
- [ ] Fast steel member entry with typeahead section search (keyboard-driven)
- [ ] Per-member: section, exposure type, fire rating, failure temp, quantity, length, zone
- [ ] Auto-calculation of Hp/A section factor from steel section + exposure
- [ ] DFT lookup from Nullifire product certification data (5 products: SC601, SC801-120, SC802, SC804, SC901)
- [ ] Surface area, coating volume, and litres calculation per member
- [ ] Live verification column (green/amber/red) per row — within limits, near max, exceeds
- [ ] Project summary with running totals (litres, kg, containers)
- [ ] All 4 steel origins: British (1,694), European (513), American (552), Australasian (360)
- [ ] CSV/Excel import with column mapping UI for structural schedules
- [ ] Excel export formatted for Quantifire import
- [ ] PDF specification report
- [ ] Structural grid setup (named gridlines A-F / 1-5 with spacings)
- [ ] Level definitions with heights and optional default fire rating/temp per level
- [ ] 3D wireframe preview — members appear as lines between grid intersections (Phase 1)
- [ ] 3D extruded section profiles with DFT color gradient (Phase 2)
- [ ] Click-to-place members in 3D view, synced with data table (Phase 3)
- [ ] Bidirectional sync — add in table OR 3D, both stay updated

### Out of Scope

- Material costing (price/litre, labour, overheads) — Quantifire handles costing
- PDF structural schedule import — complex OCR/AI parsing, deferred to web dev team
- DXF/CAD grid import — future enhancement
- Freeform point placement for grids — future enhancement
- Multi-user/cloud sync — web app phase
- Licence/activation system — not needed for POC

## Context

- **Data source**: Extracted from legacy Steelcalc Access database (NulliLib.mdb) into clean SQLite
- **Data volume**: 3,545 steel sections, 17,486 section factors, 44,334 DFT records, 1,323 coverage ranges
- **DFT lookup chain**: Section → Exposure Band → Hp/A → Coverage ID (exact match min=max) → DFT
- **Legacy app**: VB.NET WinForms with Infragistics grids, SmartAssembly-obfuscated, Access/.mdb storage
- **Existing code**: `export_data.py` (Access→SQLite exporter) and `data/nullifire.db` already built
- **End goal**: Professional web developer inherits this codebase to build Nullifire website integration
- **Quantifire**: Downstream costing tool — our Excel export must be compatible with its import format (template TBD)

## Constraints

- **Architecture**: Python backend (Flask API) + HTML/CSS/JS frontend + PyWebView desktop wrapper — chosen so UI transfers directly to web app
- **No costing**: This is a specification tool, not a costing tool — Quantifire handles that downstream
- **Nullifire only**: Only Nullifire products (SupplierID=4) — not multi-supplier like Steelcalc
- **Data**: SQLite for POC — PostgreSQL for web app migration
- **3D Library**: Three.js (WebGL) — runs in browser, transfers to web app
- **Branding**: Nullifire brand colors (red/dark grey/white)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Flask + HTML/JS over PyQt6 | UI code transfers directly to web app — web dev inherits working frontend | — Pending |
| PyWebView for desktop wrapper | Native window feel without Electron weight; HTML/JS still the actual UI | — Pending |
| SQLite extracted from Access | Portable, fast, clean schema vs legacy Access + MDW workgroup security | — Pending |
| Phased 3D approach | Phase 1 wireframe → Phase 2 profiles+colors → Phase 3 click-to-place. Each phase is independently usable | — Pending |
| Column mapper for imports | Engineers format schedules differently — mapping UI handles any CSV/Excel layout | — Pending |
| No costing — Quantifire export | Keep tools focused — this specifies, Quantifire costs. Excel bridge between them | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-01 after initialization*
