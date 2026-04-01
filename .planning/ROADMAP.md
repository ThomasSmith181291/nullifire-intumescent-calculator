# Roadmap: Nullifire Intumescent Calculator

## Overview

Build a structural steel intumescent coating specification tool that replaces legacy Steelcalc. Start with the safety-critical DFT calculation engine and validate it against legacy data. Layer on fast keyboard-driven member entry with live calculations, then verification and project summaries. Connect to real workflows via import/export. Finish with the 3D structural grid preview as an additive visual layer.

## Phases

- [x] **Phase 1: DFT Engine & Foundation** - Flask API, SQLite database, validated DFT lookup chain, PyWebView shell *(completed 2026-04-01)*
- [x] **Phase 2: Project & Member Entry** - Project creation, fast typeahead section search, member table with live calculations *(completed 2026-04-01)*
- [x] **Phase 3: Verification & Summary** - RAG status per member, project totals, container optimization, zone/level subtotals *(completed 2026-04-01)*
- [ ] **Phase 4: Import & Export** - CSV/Excel import with column mapper, Quantifire Excel export, PDF specification report
- [ ] **Phase 5: Structural Grid & 3D Preview** - Grid/level definitions, Three.js wireframe, bidirectional table-3D sync

## Phase Details

### Phase 1: DFT Engine & Foundation
**Goal**: A validated calculation engine that returns correct DFT values for any product/section/fire-rating combination, served through a Flask API in a PyWebView desktop window
**Depends on**: Nothing (first phase)
**Requirements**: FOUND-01, FOUND-02, FOUND-03, FOUND-04, FOUND-05
**Success Criteria** (what must be TRUE):
  1. Flask API returns steel section data, product info, and DFT values via JSON endpoints
  2. DFT lookup for any valid product + section factor + fire rating + failure temp returns the correct thickness, matching legacy Steelcalc output
  3. Test harness runs against reference data and reports pass/fail with specific mismatches identified
  4. Application launches as a native desktop window via PyWebView with Flask serving content
**Plans**: 4 plans
Plans:
- [ ] 01-PLAN-01.md — Flask app shell, database layer, PyWebView desktop wrapper
- [ ] 01-PLAN-02.md — Steel section and product reference data API endpoints
- [ ] 01-PLAN-03.md — DFT calculation engine and lookup API endpoint
- [ ] 01-PLAN-04.md — DFT test harness with reference data validation

### Phase 2: Project & Member Entry
**Goal**: Users can create projects and rapidly add steel members with typeahead search, getting instant DFT calculations as they type
**Depends on**: Phase 1
**Requirements**: PROJ-01, PROJ-02, PROJ-03, PROJ-04, ENTRY-01, ENTRY-02, ENTRY-03, ENTRY-04, ENTRY-05, ENTRY-06, ENTRY-07, ENTRY-08, ENTRY-09, ENTRY-10, CALC-01, CALC-02, CALC-03, CALC-04, CALC-05
**Success Criteria** (what must be TRUE):
  1. User can create a project with defaults and save/load it from disk
  2. User can type a partial section name and get filtered results across all 3,545 sections in under 50ms
  3. User can add a member entirely by keyboard (tab through fields) and see DFT, surface area, and litres calculated live
  4. User can inline-edit any cell in the member table and see all dependent values recalculate immediately
  5. User can select multiple rows and batch-edit shared properties (fire rating, product, failure temp)
**Plans**: TBD
**UI hint**: yes

### Phase 3: Verification & Summary
**Goal**: Users can see at a glance which members are within specification limits and get accurate project totals for ordering
**Depends on**: Phase 2
**Requirements**: VER-01, VER-02, VER-03, SUM-01, SUM-02, SUM-03, SUM-04
**Success Criteria** (what must be TRUE):
  1. Every member row displays a green/amber/red indicator based on whether its Hp/A is within, near, or beyond the product's tested range
  2. Project summary shows total litres, total kg, total surface area, and container counts updated live
  3. User can view subtotals broken down by zone/location and by level
**Plans**: TBD
**UI hint**: yes

### Phase 4: Import & Export
**Goal**: Users can import existing structural schedules and export specifications for downstream tools (Quantifire) and documentation (PDF)
**Depends on**: Phase 3
**Requirements**: IMP-01, IMP-02, IMP-03, IMP-04, IMP-05, EXP-01, EXP-02, EXP-03
**Success Criteria** (what must be TRUE):
  1. User can import a CSV or Excel file, map its columns to target fields using a visual UI with sample data preview, and commit valid rows
  2. User can save and reuse column mapping profiles for recurring schedule formats
  3. User can export an Excel file formatted for Quantifire import (NOTE: Quantifire template format is TBD -- blocker for EXP-01)
  4. User can export a branded PDF specification report with project header, member schedule, product details, and totals
**Plans**: TBD
**UI hint**: yes

### Phase 5: Structural Grid & 3D Preview
**Goal**: Users can define a building's structural grid and see members rendered in 3D, with bidirectional sync between the data table and the 3D view
**Depends on**: Phase 2
**Requirements**: GRID-01, GRID-02, GRID-03, GRID-04, 3D-01, 3D-02, 3D-03, 3D-04, 3D-05
**Success Criteria** (what must be TRUE):
  1. User can define named gridlines in two directions with variable spacings, and define building levels with heights
  2. 3D wireframe view renders the grid, levels, and all members as colored lines with orbit/pan/zoom controls
  3. Members in 3D are colored by verification status (green/amber/red) matching the data table
  4. Clicking a member in 3D selects it in the table, and adding/editing a member in the table updates the 3D view live
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. DFT Engine & Foundation | 0/4 | Planning complete | - |
| 2. Project & Member Entry | 0/TBD | Not started | - |
| 3. Verification & Summary | 0/TBD | Not started | - |
| 4. Import & Export | 0/TBD | Not started | - |
| 5. Structural Grid & 3D Preview | 0/TBD | Not started | - |
