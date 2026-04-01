# Phase 2: Project & Member Entry - Context

**Gathered:** 2026-04-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can create projects and rapidly add steel members with typeahead search, getting instant DFT calculations as they type. This is the core UX phase — where the tool becomes usable for real specification work.

</domain>

<decisions>
## Implementation Decisions

### Data Table & Entry UX
- Inline new row at bottom of AG Grid table — tab into empty row, type section, tab through fields, Enter to confirm
- 14 columns visible: Section, Type, Exposure, Hp/A, Fire Rating, Temp, DFT(mm), Qty, Length(m), Area(m2), Litres, Zone, Level, Status
- Custom AG Grid cell editor for section typeahead — dropdown filters as you type, shows serial_size + steel_type + weight
- Exposure auto-selects default (UB→3-sided, UC→4-sided) but is editable via dropdown showing all valid profiles

### Project Management
- SQLite database per project, file extension `.nfc` (Nullifire Calculator)
- Sidebar panel on left shows project settings (name, client, product, fire rating, temp, origin). Member table fills remaining space on right.
- Changing default product recalculates all members using that default (confirmation dialog). Per-member overrides preserved.

### Page Layout
- Single page: header (Nullifire branding + project name) + sidebar (project settings) + main area (AG Grid)
- Future Phase 5 3D preview: resizable split pane below table with draggable divider, collapsible
- Light theme: white background, Nullifire red (#E31937) header, dark grey (#333) text

### Claude's Discretion
- AG Grid column widths and resize behavior
- Exact keyboard shortcut mappings
- Project file dialog behavior (save as vs auto-save)
- Error toast/notification style

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/services/section_service.py` — search_sections(), get_section_profiles(), get_section_factor()
- `app/services/product_service.py` — get_products(), get_product_fire_ratings(), get_product_failure_temps()
- `app/services/dft_service.py` — lookup_dft() returns full result dict with all intermediate values
- `app/api/` — All reference data endpoints already built and tested
- `static/index.html` — Minimal shell with Nullifire branding CSS

### Established Patterns
- Flask API returns JSON, frontend uses fetch()
- Services return plain dicts, no Flask objects
- All DB access via get_ref_db() with Row factory

### Integration Points
- Phase 3 adds verification (RAG status) — needs a status field in the member data model
- Phase 4 adds import/export — needs clean member data model accessible from services
- Phase 5 adds 3D preview — needs grid/level/member position data, split pane UI placeholder

</code_context>

<specifics>
## Specific Ideas

- AG Grid Community 35.2.0 via CDN — no npm/build step
- Typeahead must be <50ms across 3,545 sections
- Tab order: Section → Exposure → Fire Rating → Temp → Qty → Length → Zone → (auto-calc fields skip)
- Project SQLite DB separate from reference DB (nullifire.db is read-only)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>
