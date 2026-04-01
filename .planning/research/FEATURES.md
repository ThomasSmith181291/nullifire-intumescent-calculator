# Feature Landscape

**Domain:** Intumescent coating specification / structural steel fire protection
**Researched:** 2026-04-01
**Overall confidence:** HIGH (domain well-understood from legacy Steelcalc data + competitor analysis)

## Table Stakes

Features users expect from an intumescent specification tool. Missing any of these and the tool is not viable for professional use.

### Core Specification Engine

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Steel section search with typeahead | Every competitor has this. Engineers type "UB 457x191x67" and expect instant results. Keyboard-driven is critical -- mouse-clicking through dropdowns is what makes Steelcalc slow. | Medium | Must handle all 3,545 sections across 15 steel types (UB, UC, CHS, RHS, SHS, PFC, etc.) and 4 origins (GB, US, EURO, AUST). Fuzzy matching on serial_size. |
| Exposure type / HP profile selection | Hp/A (section factor) changes based on how the steel is exposed to fire (3-sided beam vs 4-sided column, boxed, boarded, composite). This is the second critical input after section choice. | Medium | 50+ HP profiles in the data. Must filter to profiles valid for the selected steel type. Default to sensible option (e.g., "4 Sided Column" for UC, "3 Sided Beam" for UB). |
| Hp/A section factor auto-calculation | The section factor is the bridge between the physical steel and the DFT requirement. Must be instant, not manual lookup. | Low | Pre-computed in section_factors table (17,486 records). Pure lookup: section_id + hp_profile_name -> hp_over_a value. |
| DFT lookup from certification data | The core output. Given product + section factor + fire rating + failure temp, return the required dry film thickness in mm. | Medium | Lookup chain: Hp/A -> bands table (coverage_id) -> dft_data (product, failure_temp, fire_rating, coverage_id) -> dft_mm. 44,334 DFT records. Must handle "exceeds range" gracefully. |
| Fire rating selection (15-240 min) | Standard fire resistance periods. Per-member override from project default. | Low | 8 ratings in database (15, 30, 45, 60, 90, 120, 180, 240 min). Not all products support all ratings -- must filter by product capability. |
| Failure temperature selection | Critical temperature at which the steel member fails. Varies by load ratio and design approach. Per-member override from project default. | Low | ~30 failure temps in data (300-750 deg C plus BS 476 standard, plus specific EN temps like 512, 520, 539 deg C). |
| Product selection (Nullifire products) | User picks the intumescent product. Different products suit different environments (on-site vs off-site, water vs solvent based, internal vs external). | Low | SC601/SC602 (solvent, off/on-site), SC801-120 (water, internal), SC802 (water, internal), SC803, SC804, SC901. Some products have duplicate entries for BS 476 vs EN temp standards. |
| Surface area calculation per member | Given section dimensions, exposure type, and member length, calculate paintable surface area. | Medium | Heated perimeter from HP profile times member length. Must account for 3-sided vs 4-sided correctly. |
| Coating volume / litres calculation | How much product is needed per member. Key output for material procurement. | Medium | DFT (mm) x surface area (m2) / solid factor (%) = wet volume. Then convert to litres. Must use product-specific density and solid factor from products table. |
| Quantity column (member count) | A beam spec typically applies to multiple identical members. Multiply all quantities by count. | Low | Simple multiplier on all calculated values. |
| Verification status per row (RAG) | Engineers need instant visual feedback: is this spec within the product's tested range? Green = within limits, amber = near maximum Hp/A, red = exceeds tested data. | Medium | Compare member's Hp/A against the maximum Hp/A in the bands table for that product/fire-rating/temp combination. |
| Project summary totals | Running totals of litres, kg, and container counts across entire project. | Low | Sum of per-member litres. Convert to kg via density. Divide by container sizes (products table has container_1_litres, container_2_litres etc.). |
| Multiple steel origins | British (1,694 sections), European (513), American (552), Australasian (360). Engineers work across standards depending on project region. | Low | Already in database. UI needs origin filter that persists per-project. |
| Project save/load | Users work on specifications over days/weeks. Must persist. | Low | SQLite project database, separate from the product database. |

### Import / Export

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Excel export for Quantifire | This is the primary downstream output. Quantifire import format is the contract. | Medium | Template TBD from Quantifire team, but standard pattern: one row per member, columns for section, DFT, litres, area, zone. openpyxl handles any format. |
| PDF specification report | Engineers and contractors need a printable document for site records, building control submissions, and insurance sign-off. | Medium | Professional layout with project header, member schedule table, product details, totals, and Nullifire branding. WeasyPrint from Jinja2 template. |

### Project Setup

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Project metadata (name, client, date, ref) | Professional documentation. Every report needs this header. | Low | Simple form fields stored in project DB. |
| Default product, fire rating, failure temp | Most projects use one product throughout with one fire rating. Setting defaults avoids repetitive per-member entry. | Low | Project-level settings that pre-populate new member rows. Per-member overrides allowed. |

## Differentiators

Features that set this tool apart from competitors (Steelcalc, Hempel HEET Dynamic, Promat Calculator, Tikkurila). Not expected, but create competitive advantage.

### Speed and UX (Primary Differentiator)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Keyboard-driven member entry flow | **THE differentiator.** Tab through: section (typeahead) -> exposure (auto-default) -> fire rating (pre-filled from project) -> quantity -> length -> zone -> Enter to add next. What takes 8+ clicks in Steelcalc takes one fluid keyboard sequence. | High | Requires careful tab order, smart defaults, and instant feedback. The typeahead must be fast (<50ms) across 3,545 sections. |
| Inline editing in data table | Click any cell to edit. No modal dialogs, no separate "edit member" forms. See result change instantly. | Medium | Editable grid with live recalculation on every change. |
| Batch operations on selected rows | Select 20 beams, change all to 90 min fire rating at once. Bulk product change when switching suppliers. | Medium | Multi-select in table + bulk edit toolbar/context menu. Steelcalc's "Copy Store" for 24 records is a poor workaround for this missing feature. |
| Smart defaults from steel type | When user selects a UB section, auto-set exposure to "3 Sided Beam". When UC, auto-set to "4 Sided Column". Saves one decision per member. | Low | Simple mapping from steel_type_id to default HP profile. |
| Live calculation with no "Calculate" button | DFT, surface area, litres all update as inputs change. Zero-latency feedback loop. | Low | Recalculate on every cell change event. All lookups are in-memory from SQLite. |

### 3D Structural Grid Preview

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Structural grid setup (gridlines + levels) | Engineers think in grid coordinates (A/1, B/3). Every structural drawing uses this system. Provides spatial context that spreadsheet-only tools lack. | Medium | Named gridlines in two orthogonal directions with spacings. Standard convention: letters one direction, numbers the other. Levels with heights (Ground, First, Roof, etc.). Follows Revit/ETABS pattern. |
| 3D wireframe member visualization | Members appear as lines between grid intersections as they are added to the table. Spatial awareness of where steel actually is in the building. No competitor has this. | High | Three.js WebGL. Members as line segments between grid node pairs. Color by verification status (green/amber/red). Camera orbit/pan/zoom. |
| Bidirectional table-3D sync | Click a member in 3D to select it in the table. Add in table with grid references, see it appear in 3D. | High | Requires grid intersection addressing (e.g., "A1-B1 @ Level 1"). Event system between table and 3D view. |
| DFT color gradient on 3D members | Phase 2 3D: extrude actual section profiles, color by DFT thickness. Thick = red, thin = green. Instant visual identification of problem areas. | Very High | Requires section profile geometry generation from steel dimensions (depth, width, flange, web from steel_sections table). |
| Click-to-place in 3D | Phase 3 3D: click two grid intersections to place a member, fills in the table row automatically. | Very High | Full 3D interaction with snap-to-grid. Raycasting, grid snapping, member creation from 3D clicks. |

### Column Mapping UI for CSV/Excel Import

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Visual column mapper | Upload CSV/Excel, see preview of source columns with sample data, map to target fields via dropdowns. Handles any schedule format without requiring a fixed template. | High | Two-panel layout: left shows detected source columns with 3-5 sample values, right shows target fields (Section, Quantity, Length, Level, Zone, Fire Rating). Auto-match by header name similarity (e.g., "Steel Size" -> Section), manual override via dropdown. |
| Import preview with validation | After mapping, show preview of parsed rows with inline errors (unrecognized section names highlighted, missing required fields flagged). Fix before committing. | Medium | Preview table with row-level validation. Highlight errors in red with tooltip explanation. Allow skip/fix per row. |
| Saved mapping profiles | If the engineer imports from the same Revit/Tekla export format every time, remember the column mapping. | Low | Save mapping profiles by name. Auto-suggest matching profile when headers look familiar. |
| Downloadable import template | Provide a blank Excel template with correct headers and example data, so users who prefer fixed formats can use it. | Low | Reduces support requests. Template includes column descriptions in row 2. |

### Data and Verification

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Zone/location tagging per member | Tag members by building zone (e.g., "Zone A - Warehouse", "Zone B - Office"). Groups members for partial ordering and zone-specific reporting. | Low | Free-text or pick-list zone field per member. Filter and subtotal by zone. |
| Level assignment per member | Assign members to building levels. Natural grouping for structural engineers who think floor-by-floor. | Low | Dropdown from defined levels. |
| Container optimization | Given total litres, recommend optimal container mix (e.g., 3x 20L + 1x 5L rather than 4x 5L + 1x 2.5L). Products have up to 4 container sizes. | Low | Greedy algorithm on container sizes from products table (container_1 through container_4 fields). |
| Product comparison mode | Spec the same schedule with two different products side-by-side. Shows DFT and litres difference. Helps technical reps demonstrate Nullifire advantages. | High | Duplicate project data with different product selection, show comparison table. Hempel HEET Dynamic has this as a premium "Structural Fire Design" upgrade feature. |

## Anti-Features

Features to explicitly NOT build in the POC. These either belong in Quantifire, belong in a future web phase, or add complexity without value.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Material costing (price/litre, labour rates, overheads) | This is Quantifire's job. Building costing here creates a competing tool and maintenance burden for two price databases. | Export clean data to Quantifire via Excel. Include litres, kg, and container counts -- let Quantifire apply pricing. |
| Multi-supplier product database | Legacy Steelcalc supports all manufacturers. This Nullifire tool is a brand-specific tool, not a comparison tool. Supporting competitors' products defeats the purpose. | Nullifire products only (SupplierID=4). If cross-supplier comparison is needed, that is Steelcalc's job. |
| PDF structural schedule import (OCR/AI) | Complex OCR/AI parsing of scanned drawings. Unreliable, expensive, and the web dev team has this on their roadmap. | Support CSV/Excel import with column mapping. Engineers can usually get a digital schedule from their structural model. |
| DXF/CAD grid import | Parsing AutoCAD/Revit DXF for grid extraction is a deep rabbit hole with dozens of edge cases. | Manual grid setup UI with named gridlines and spacings. Takes 2 minutes for a typical building. |
| User authentication / licence system | Not needed for POC. Adds complexity without validation value. | Ship as a standalone desktop app. Add auth when it moves to web. |
| Multi-user / real-time collaboration | Cloud sync, concurrent editing, conflict resolution. Web app phase concern. | Single-user desktop app. Project files can be shared manually. |
| Freeform point placement for grids | Irregular grid layouts where gridlines are not parallel or evenly spaced. Niche use case. | Regular rectangular grids with named gridlines and variable spacings cover 95% of buildings. |
| Topcoat / primer specification | The database has topseals data, but the POC should focus purely on intumescent basecoat DFT. Topcoat is a separate purchasing decision. | Note in export that topcoat is required per product datasheet, but do not spec it. |
| Application method guidance (spray vs brush, coats, drying times) | Product datasheets cover this. Duplicating it in the tool creates maintenance burden when datasheets update. | Link to Nullifire product datasheets from within the app. |
| Cellular beam / Westok web opening calculations | Special section factor calculations for beams with web openings. Complex engineering logic. | Flag cellular beams (steel_type_id=14) as requiring specialist assessment. Hempel HEET charges extra for this via their SFD upgrade. |
| Structural Fire Design (custom critical temperatures) | EN 1993-1-2 allows engineers to calculate member-specific critical temperatures based on load ratio. Advanced feature requiring structural engineering knowledge. | Use standard failure temperatures from the database. Note that SFD is a future premium feature opportunity. |
| Custom section creation | Engineers almost never have non-standard sections. Database covers 3,545 sections across all 4 origins. | Flag if section not found. Suggest closest match. |
| Full undo/redo system | Engineering complexity for modest benefit in a data-entry focused tool. | Cell-level undo in the data grid is sufficient. Full project-level undo/redo is over-engineering for POC. |

## Feature Dependencies

```
Project Setup (metadata, defaults)
  |
  +-> Steel Member Entry (section search, exposure, DFT lookup)
  |     |
  |     +-> Verification (RAG status per row, Hp/A range check)
  |     |
  |     +-> Quantity Calculations (surface area, litres, kg, containers)
  |     |
  |     +-> Zone/Level Assignment
  |
  +-> Grid & Level Setup
  |     |
  |     +-> 3D Wireframe Preview (requires grid + levels + members with grid refs)
  |           |
  |           +-> 3D Extruded Profiles (Phase 2 3D, requires wireframe working)
  |                 |
  |                 +-> Click-to-Place (Phase 3 3D, requires extruded profiles)
  |
  +-> CSV/Excel Import (requires column mapper -> feeds into member entry)
  |
  +-> Export (Excel for Quantifire, PDF report -- requires member data + project metadata)
```

Key dependency insight: The 3D preview is an enhancement layer on top of the core specification engine. The core engine (search -> DFT lookup -> quantities -> export) must work standalone before any 3D work begins.

## MVP Recommendation

### Phase 1 - Core Specification Engine (must ship first)

Prioritize:
1. **Project setup** with defaults (product, fire rating, failure temp, steel origin)
2. **Keyboard-driven member entry** with typeahead section search and smart defaults
3. **Instant DFT lookup and verification** (the core value loop: add member -> see DFT -> see RAG status)
4. **Quantity calculations** (surface area, litres, kg, containers per member + project totals)
5. **Excel export** formatted for Quantifire
6. **PDF specification report**

### Phase 2 - Import and Spatial

7. **CSV/Excel import with column mapping** (unlocks large projects with 200+ members)
8. **Grid and level setup** UI
9. **3D wireframe preview** (members as lines between grid intersections)
10. **Batch operations** on selected rows

### Phase 3 - Advanced 3D

11. **3D extruded section profiles with DFT color gradient**
12. **Click-to-place members in 3D**
13. **Bidirectional sync** (table and 3D)

Defer: Product comparison mode (nice-to-have after core is proven).

## What Makes a Specification Tool "Fast" vs "Slow"

This is critical UX insight from analyzing Steelcalc and competitors:

### Fast Tools

- **Typeahead search** instead of hierarchical dropdowns (don't make users pick Origin -> Steel Type -> Group -> Section in 4 steps)
- **Smart defaults** that pre-fill 3 of 6 fields (exposure from steel type, fire rating from project, failure temp from project)
- **Tab-through entry** where Enter/Tab moves to next field and next row
- **Live calculation** with no "Calculate" button -- DFT updates as inputs change
- **Inline editing** -- click a cell, change it, move on. No modal edit dialogs.
- **Bulk operations** -- change 30 rows at once instead of editing one by one

### Slow Tools (Steelcalc pain points)

- **SmartAssembly-obfuscated VB.NET** with Infragistics grids that feel sluggish
- **Multiple dialogs** to add a single member (select section dialog -> set properties dialog -> confirm)
- **No keyboard-driven workflow** -- heavy mouse dependency
- **Separate "Calculate" step** before seeing results
- **No batch editing** -- changing fire rating on 50 members means 50 individual edits
- **Copy/paste as the only bulk mechanism** -- Steelcalc's "Copy Store" for up to 24 records is a workaround for missing batch edit

### Design Principles

1. **One-row-at-a-time should take under 10 seconds** (type section, tab, tab, tab, enter)
2. **Never require a modal dialog** for member entry or editing
3. **Show the money number (litres) immediately** -- don't make users navigate to a summary screen
4. **RAG status visible without scrolling** -- verification column always in view
5. **Typeahead must respond in under 50ms** -- pre-load all 3,545 sections into client-side index

## Competitor Landscape

| Tool | Vendor | Type | Key Strengths | Key Weaknesses |
|------|--------|------|---------------|----------------|
| Steelcalc 7.2 | FPSI | Desktop (VB.NET) | Multi-supplier, comprehensive, industry standard | Slow UI, no visualization, obfuscated, feels dated |
| HEET Dynamic | Hempel | Desktop (Windows) | 10x faster calcs, BIM plugin, SFD upgrade, project dashboard | Hempel products only, paid SFD upgrade for advanced features |
| Promat Calculator | Promat | Mobile/Web app | Basic + Advanced tiers, mobile-friendly, timber support | Board/spray focus, not intumescent-centric |
| Tikkurila Calculator | Tikkurila | Web | Simple, free, quick DFT lookup with Hp/A calculator | Single product only (Fontefire), no project management |

**Gap to exploit:** No competitor has 3D structural visualization. HEET Dynamic is the closest competitor in UX quality but is Hempel-branded. A fast, modern, Nullifire-branded tool with 3D preview would be unique.

## Sources

- [Steelcalc - Estimating and Comparison Software](https://steelcalc.co.uk/) - Legacy multi-supplier tool being partially replaced
- [Nullifire Product Calculator](https://www.nullifire.com/en-gb/technical-hub/tools-calculators/steelcalc-product-calculator/)
- [Hempel HEET Dynamic - Intumescent Estimation Software](https://www.hempel.com/news/2023/leading-intumescent-coating-estimation-software) - Key competitor with BIM plugin and SFD upgrade
- [HEET Dynamic Product Page](https://www.hempel.com/en-us/knowledge-center/tools/heet-dynamic)
- [Promat Structural Protection Calculator](https://www.promat.com/en/construction/tools-services/software-apps/structural-protection-calculator/)
- [Tikkurila Intumescent Calculator](https://tikkurila.com/industry/intumescent-calculator-for-steel)
- [Calculating Section Factors - SteelConstruction.info](https://www.steelconstruction.info/Calculating_section_factors)
- [Thickness for Passive Fire Protection Coatings - STRUCTURE Magazine](https://www.structuremag.org/article/thickness-for-passive-fire-protection-coatings/)
- [Specifying Intumescent Coating Film Thicknesses - Construction Specifier](https://www.constructionspecifier.com/specifying-intumescent-coating-film-thicknesses/)
- [Designing An Attractive Data Importer - Smashing Magazine](https://www.smashingmagazine.com/2020/12/designing-attractive-usable-data-importer-app/) - Column mapping UI patterns
- [Best Practices for Building a CSV Uploader - OneSchema](https://www.oneschema.co/blog/building-a-csv-uploader)
- [Revit Grids in Structure - Autodesk](https://www.autodesk.com/learn/ondemand/tutorial/grids-in-revit-structure) - Grid/level conventions
- [Modeling Structure in Revit: Set Levels and Grids - engipedia](https://www.engipedia.com/modeling-structure-in-revit-2-set-levels-and-grids/)
- Legacy Nullifire Steelcalc database analysis (NulliLib.mdb extracted to nullifire.db -- 3,545 sections, 17,486 section factors, 44,334 DFT records)
