# Requirements: Nullifire Intumescent Calculator

**Defined:** 2026-04-01
**Core Value:** Fast, component-by-component steel member input with instant DFT verification

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Foundation

- [ ] **FOUND-01**: Flask API serves JSON endpoints for all data operations
- [ ] **FOUND-02**: SQLite reference database (nullifire.db) provides steel sections, DFT data, and product info
- [ ] **FOUND-03**: DFT lookup chain returns correct thickness for any product + section factor + fire rating + failure temp combination
- [ ] **FOUND-04**: DFT test harness validates calculations against legacy Steelcalc reference data
- [ ] **FOUND-05**: PyWebView wraps Flask app as native desktop window

### Project Setup

- [ ] **PROJ-01**: User can create a new project with name, client, date, and reference number
- [ ] **PROJ-02**: User can set project defaults for product, fire rating, and failure temperature
- [ ] **PROJ-03**: User can set default steel origin filter (GB, EURO, US, AUST)
- [ ] **PROJ-04**: User can save and load projects from local files

### Steel Member Entry

- [ ] **ENTRY-01**: User can search steel sections with typeahead across all 3,545 sections (<50ms response)
- [ ] **ENTRY-02**: User can select exposure type (HP profile) for each member, filtered to valid profiles for that steel type
- [ ] **ENTRY-03**: System auto-defaults exposure based on steel type (UB → 3-sided beam, UC → 4-sided column)
- [ ] **ENTRY-04**: New members inherit fire rating and failure temp from project defaults
- [ ] **ENTRY-05**: User can override fire rating and failure temp per member
- [ ] **ENTRY-06**: User can set quantity, length, and zone/location per member
- [ ] **ENTRY-07**: User can tab through all fields keyboard-only to add a member (no mouse required)
- [ ] **ENTRY-08**: User can inline-edit any cell in the member table with live recalculation
- [ ] **ENTRY-09**: User can select multiple rows and batch-edit fire rating, product, or failure temp
- [ ] **ENTRY-10**: User can delete members individually or in batch

### Calculations

- [ ] **CALC-01**: Hp/A section factor auto-calculated from section + exposure selection
- [ ] **CALC-02**: DFT looked up instantly from product certification data for the member's parameters
- [ ] **CALC-03**: Surface area calculated from heated perimeter x member length
- [ ] **CALC-04**: Coating volume calculated from DFT x surface area / solid factor
- [ ] **CALC-05**: All calculations update live on every input change (no "Calculate" button)

### Verification

- [ ] **VER-01**: Each member row shows RAG status — green (within limits), amber (near max Hp/A), red (exceeds tested range)
- [ ] **VER-02**: Members with Hp/A exceeding the product's tested range are flagged clearly
- [ ] **VER-03**: Project summary shows count of green/amber/red members

### Summary & Totals

- [ ] **SUM-01**: Running project totals: total litres, total kg, total surface area
- [ ] **SUM-02**: Container count optimization using product container sizes (up to 4 sizes per product)
- [ ] **SUM-03**: Subtotals by zone/location
- [ ] **SUM-04**: Subtotals by level (when levels defined)

### Import

- [ ] **IMP-01**: User can import CSV or Excel files containing structural schedules
- [ ] **IMP-02**: Column mapping UI shows source columns with sample data and lets user map to target fields
- [ ] **IMP-03**: Import preview shows parsed rows with validation errors highlighted
- [ ] **IMP-04**: User can skip or fix invalid rows before committing import
- [ ] **IMP-05**: User can save and reuse column mapping profiles

### Export

- [ ] **EXP-01**: User can export project to Excel formatted for Quantifire import
- [ ] **EXP-02**: User can export PDF specification report with Nullifire branding
- [ ] **EXP-03**: PDF includes project header, member schedule table, product details, and totals

### Structural Grid

- [ ] **GRID-01**: User can define named gridlines in two orthogonal directions with variable spacings
- [ ] **GRID-02**: User can define building levels with names and heights
- [ ] **GRID-03**: Levels can have optional default fire rating and failure temp (members inherit)
- [ ] **GRID-04**: Members can be assigned to grid positions (from-to intersections) and levels

### 3D Preview

- [ ] **3D-01**: 3D wireframe view shows grid, levels, and members as colored lines (Phase 1 3D)
- [ ] **3D-02**: Camera orbit, pan, zoom controls
- [ ] **3D-03**: Members colored by verification status (green/amber/red)
- [ ] **3D-04**: Clicking a member in 3D selects it in the data table
- [ ] **3D-05**: Adding/editing a member in the table updates the 3D view live

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### 3D Enhanced

- **3D-V2-01**: Extruded section profiles (actual I-beam, channel shapes) instead of lines
- **3D-V2-02**: DFT color gradient on extruded profiles (thickness visualization)
- **3D-V2-03**: Click-to-place members by clicking two grid intersections in 3D view

### Advanced Features

- **ADV-01**: Product comparison mode — same schedule with two products side-by-side
- **ADV-02**: Saved import mapping auto-suggestion based on header similarity
- **ADV-03**: Downloadable blank import template with headers and example data
- **ADV-04**: Topcoat/primer specification alongside intumescent basecoat

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Material costing | Quantifire handles costing downstream — this is a specification tool |
| Multi-supplier products | This is a Nullifire brand tool, not a comparison tool |
| PDF structural schedule import | Complex OCR/AI — deferred to web development team |
| DXF/CAD grid import | Deep rabbit hole with edge cases — manual grid setup takes 2 minutes |
| User authentication/licensing | Not needed for POC desktop app |
| Multi-user/cloud sync | Web app phase concern |
| Freeform grid point placement | Regular rectangular grids cover 95% of buildings |
| Application method guidance | Product datasheets cover this — link to them instead |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| (To be filled by roadmapper) | | |

---
*Defined: 2026-04-01*
