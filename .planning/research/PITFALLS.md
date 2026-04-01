# Domain Pitfalls

**Domain:** Intumescent coating specification tool (DFT lookup, 3D preview, Excel interop)
**Researched:** 2026-04-01

## Critical Pitfalls

Mistakes that cause rewrites, data errors, or failed handoff.

### Pitfall 1: DFT Lookup Returns Wrong Values Due to Band/Coverage Mapping Gaps

**What goes wrong:** The DFT lookup chain is: Section -> Exposure Profile -> Hp/A value -> Band -> Coverage ID -> DFT. The `bands` table maps `band_id + hp_over_a` to `coverage_id`, but coverage ranges have discrete Hp/A breakpoints (not continuous). An Hp/A value of 187 might fall between the nearest band entries of 180 and 190. If the code does exact-match lookup, it returns nothing. If it interpolates, it may return an unsafe (too-low) DFT.

**Why it happens:** The legacy Steelcalc used a specific rounding/banding strategy for Hp/A values that is not documented in the database schema. The bands table contains discrete Hp/A values with associated coverage IDs, and the matching logic is implicit in the VB.NET code (which is obfuscated with SmartAssembly).

**Consequences:** Under-specification of DFT is a fire safety liability. Over-specification wastes material and can cause delamination (coating too thick falls off in fire). Either direction is professionally unacceptable.

**Prevention:**
1. Extract the exact Hp/A matching logic from Steelcalc by testing boundary cases systematically: for a known section, record the DFT at every Hp/A breakpoint and the values just above/below
2. The safe default is "round UP to next band breakpoint" (conservative -- specifies slightly thicker coating)
3. Build a validation suite that compares every product/section/rating combination against Steelcalc output before shipping
4. Never interpolate between DFT values -- use the next-higher band entry (industry standard is conservative lookup, not interpolation)

**Detection:** Any DFT value that differs from Steelcalc by more than 0.01mm for the same inputs is a bug.

**Phase:** Phase 1 (core DFT engine). This must be bulletproof before any UI work matters.

**Confidence:** HIGH -- based on analysis of the database schema and industry practice for intumescent specification.

---

### Pitfall 2: Hp/A Section Factor Edge Cases for Non-Standard Exposure Types

**What goes wrong:** Each steel section has multiple Hp/A values depending on exposure type (3-sided beam, 4-sided column, composite deck, etc.). The `hp_profiles` table has ~30+ profile types per steel type, and the `section_factors` table is a wide pivot (one column per profile). Some section/profile combinations have no Hp/A value (NULL or 0). The UI shows an exposure type as available, user selects it, and the lookup silently returns no result or zero.

**Why it happens:** Not all exposure types apply to all sections. For example, a CHS (Circular Hollow Section) has no "3-sided" exposure -- it is always 4-sided. Board-only profiles (`board_only=1`) should not appear for intumescent products. Composite profiles only apply when `is_composite=1`.

**Consequences:** User gets no DFT result and does not understand why. Or worse, the code falls through to a default value that is wrong.

**Prevention:**
1. Pre-filter available exposure types per steel section: only show profiles that have a non-null, non-zero Hp/A in `section_factors` for that section
2. Pre-filter by product compatibility: exclude `board_only` profiles for intumescent products
3. Show clear "Not available for this section" messaging rather than empty results
4. Default to the most common exposure type for each steel type (e.g., "4-sided column" for UC/UB sections)

**Detection:** Test with at least one section from each steel type (UC, UB, CHS, RHS, SHS, Angles, Channels, Tees) and verify the exposure dropdown only shows valid options.

**Phase:** Phase 1 (DFT engine + section entry UI).

**Confidence:** HIGH -- verified from the database schema showing the wide pivot structure with sparse data.

---

### Pitfall 3: PyWebView Threading Deadlocks on Windows

**What goes wrong:** PyWebView's `webview.start()` blocks the main thread (the GUI loop). All Python API functions exposed to JavaScript execute in separate threads. If a JS-called Python function tries to update the UI (e.g., `window.evaluate_js()`), it can deadlock because the main thread is blocked in the GUI loop and the worker thread is waiting for the main thread.

**Why it happens:** PyWebView on Windows uses the MSHTML/EdgeChromium backend. The GUI loop owns the window. Worker threads cannot safely call `evaluate_js()` during certain states. File dialogs (`window.create_file_dialog()`) are especially problematic -- they block the calling thread AND can freeze the main window if called from the wrong thread.

**Consequences:** Application hangs with no error message. User must kill the process. Happens intermittently, making it hard to reproduce.

**Prevention:**
1. Never call `window.evaluate_js()` from a thread that was triggered by a JS->Python API call. Instead, use a message queue pattern: Python function sets state, returns result to JS, JS updates its own UI
2. For file dialogs, always call `window.create_file_dialog()` from the main thread or from the function passed to `webview.start(func)`. Never call it from a JS-invoked API function directly
3. Use the `pywebviewready` event (not `window.onload`) to initialize JS->Python communication
4. Keep all API functions fast -- do heavy work in background threads and poll from JS, or return futures
5. Test every file dialog (open CSV, save Excel, save PDF) on Windows specifically

**Detection:** If any user action causes a >2 second hang, investigate the threading model for that code path.

**Phase:** Phase 1 (application shell). Get the threading pattern right from day one.

**Confidence:** HIGH -- documented in PyWebView issues and official architecture guide.

---

### Pitfall 4: Flask API Designed for Desktop, Breaks on Web Migration

**What goes wrong:** The Flask API stores state in Python globals, uses file paths, or relies on `localhost` assumptions. When the web developer inherits the codebase, the API cannot handle multiple concurrent users, the file paths do not exist on a server, and session state is lost between requests.

**Why it happens:** Desktop app has one user. It is tempting to store the "current project" in a Python variable, store temp files in `%APPDATA%`, and assume the browser and server are on the same machine.

**Consequences:** The web developer has to rewrite the entire API layer. The frontend JS that was supposed to "transfer directly" also breaks because it assumed single-user state.

**Prevention:**
1. Design the Flask API as if it were already multi-user from day one:
   - Every endpoint receives a `project_id` parameter (no "current project" global)
   - All data goes through the API, never through direct file access from JS
   - Use proper REST conventions: `GET /api/projects/{id}/members`, `POST /api/projects/{id}/members`
   - Return JSON responses with consistent error format: `{"error": "message", "code": "ERROR_CODE"}`
2. No file system side effects in API handlers -- file uploads go to a configurable storage path, downloads are served through the API
3. Use Flask blueprints to organize routes (not everything in one file)
4. Include OpenAPI/Swagger documentation so the web developer can see all endpoints
5. Never embed business logic in route handlers -- keep it in service modules that the routes call

**Detection:** Grep the codebase for global variables, `os.path` in route handlers, and any endpoint that does not accept a project identifier.

**Phase:** Phase 1 (API design). The URL structure and response format are the hardest things to change later.

**Confidence:** HIGH -- this is the most common pitfall in "desktop-first, web-later" projects.

---

### Pitfall 5: Legacy Steelcalc Validation Without Systematic Comparison

**What goes wrong:** The new calculator is "close enough" for a handful of manually tested cases, but produces different results for edge cases that nobody tested. The tool ships, a contractor specifies coating based on the output, and the DFT is wrong for their specific section/product/rating combination.

**Why it happens:** 44,334 DFT records across 5 products, 4 fire ratings, multiple failure temps, and 3,545 sections. Manual testing covers maybe 50 combinations. The remaining 99%+ is untested.

**Consequences:** Professional liability. If a building uses an incorrectly specified DFT and fails a fire inspection (or worse, a fire), the tool and its publisher are liable.

**Prevention:**
1. Build an automated comparison harness: for every valid combination of (product, section, exposure, fire_rating, failure_temp), query both the new tool's API and record the expected value from Steelcalc
2. Since Steelcalc is obfuscated, generate the reference dataset by driving it via UI automation (AutoIt/pyautogui) or by exhaustively querying its Access database with the same logic
3. Store the reference dataset as a fixture file (CSV). Run comparison on every build
4. Flag any deviation > 0.0mm as a test failure -- DFT lookup should be deterministic, not approximate
5. Pay special attention to boundary Hp/A values and products with `offset_dft` (SC901 has a non-zero offset)

**Detection:** Comparison test suite fails. Should run in CI or at minimum before every release.

**Phase:** Phase 1 (DFT engine). Build the test harness alongside the engine, not after.

**Confidence:** HIGH -- this is standard practice for replacing certified engineering calculation tools.

## Moderate Pitfalls

### Pitfall 6: Three.js Performance Cliff with Extruded Steel Profiles

**What goes wrong:** Phase 1 wireframe (lines between grid points) runs smoothly with hundreds of members. Phase 2 adds extruded cross-section profiles (I-beams, channels, hollow sections), and performance drops to <10 FPS because each member is a unique mesh with complex geometry.

**Why it happens:** A typical steel project has 200-500 members. An I-beam cross-section has ~20-30 vertices in the profile, extruded into ~60-100 faces per member. Without instancing, that is 200+ draw calls. With different section sizes, naive instancing does not apply because geometries differ.

**Prevention:**
1. Phase 1 wireframe: use `THREE.LineSegments` with a single `BufferGeometry` for ALL members. One draw call total
2. Phase 2 profiles: group members by section size. All "254x254x73 UC" members share one `InstancedMesh`. Different sizes get different instance groups. This reduces draw calls from N to (number of unique sections)
3. Use `THREE.LOD` -- show extruded profiles only when camera is close, wireframe when zoomed out
4. Limit Phase 2 to the active level or visible zone, not the entire building
5. Never create/dispose `THREE.Geometry` objects in a render loop -- pre-create all section geometries at project load

**Detection:** Monitor `renderer.info.render.calls` in the console. If it exceeds 100, instancing is not working correctly.

**Phase:** Phase 2 (3D extruded profiles). Phase 1 wireframe will not hit this.

**Confidence:** MEDIUM -- based on Three.js documentation and community guidance; actual performance depends on target hardware.

---

### Pitfall 7: Excel/CSV Import Fails on Real-World Structural Schedules

**What goes wrong:** The column mapper works with clean test CSVs but fails on real engineer exports: merged header rows, inconsistent section naming (e.g., "254x254x73UC" vs "254 x 254 x 73 UC" vs "254X254X73"), BOM/encoding issues, blank rows between groups, numeric values stored as text with leading spaces.

**Why it happens:** Every structural engineer formats their schedule differently. There is no standard format for steel schedules. Some export from Tekla, some from ETABS, some from hand-typed Excel.

**Consequences:** Users cannot import their schedules and fall back to manual entry, defeating the tool's core value proposition of speed.

**Prevention:**
1. Section name matching must be fuzzy: strip spaces, normalize case, handle "x" vs "X" vs unicode multiply sign, handle "UC 254x254x73" and "254x254x73 UC" and "254X254X73UC"
2. Build a section name normalizer that maps any reasonable variant to the canonical `serial_size` in the database
3. Header detection: scan first 10 rows for keywords ("Section", "Size", "Member", "Mark", "Qty", "Length", "Level", "Fire Rating") rather than assuming row 1 is headers
4. Handle merged cells: use `openpyxl` with `data_only=True` and manually unmerge + forward-fill before parsing
5. Encoding: try UTF-8 first, fall back to `latin-1`, then `cp1252` (Windows default for UK engineers)
6. Preview step: show the user what the mapper detected and let them confirm/adjust before importing
7. Collect 3-5 real structural schedules from different engineers during development and test against all of them

**Detection:** If the import preview shows garbled text, wrong column alignment, or missing rows, the parser has a problem.

**Phase:** Phase 2 (import/export). But collect sample files from Phase 1 onward.

**Confidence:** HIGH -- this is universally the hardest part of any data import tool.

---

### Pitfall 8: Quantifire Export Format is Undocumented

**What goes wrong:** The Excel export is built to a guessed format. When the contractor imports it into Quantifire, columns are wrong, values are in the wrong units, or required fields are missing. The export is useless.

**Why it happens:** PROJECT.md says "Quantifire import format template TBD." Without a definitive format spec, the developer guesses based on inspection of sample Quantifire files.

**Consequences:** The export feature -- a core requirement -- does not work with its only consumer. Users must manually reformat, which defeats the purpose.

**Prevention:**
1. Obtain the exact Quantifire import template BEFORE building the export feature. This is a blocker, not a nice-to-have
2. If a template is not available, export a project FROM Steelcalc in Quantifire format and reverse-engineer the exact column layout, units, and data types
3. Build the export to match the template exactly: column names, column order, data types, number formatting (decimal places matter for DFT)
4. Test the round-trip: export from new tool -> import into Quantifire -> verify all values match

**Detection:** First Quantifire import attempt fails.

**Phase:** Phase 2 (export). But obtain the template in Phase 1 so the data model can accommodate it.

---

### Pitfall 9: PyWebView State Lost on Window Reload

**What goes wrong:** The user's unsaved project data (member list, grid setup) lives in JavaScript variables. They accidentally close the window, hit F5, or the WebView crashes. All data is lost.

**Why it happens:** PyWebView's HtmlDialog is a browser -- it has no persistent state by default. Unlike a desktop app with a save-on-close handler, the WebView can be killed without warning.

**Prevention:**
1. Auto-save project state to a temp file every 30 seconds (via a Flask endpoint, not localStorage)
2. On window load, check for a recovery file and offer to restore
3. Use the `pywebview` `closing` event to prompt for save if there are unsaved changes
4. Never store critical state only in JS variables -- mirror it to the Flask backend after every significant change
5. The Flask backend should maintain the canonical project state; the frontend is just a view

**Detection:** Kill the PyWebView process mid-session and restart. Is the data recoverable?

**Phase:** Phase 1 (application architecture). The state management pattern must be established early.

**Confidence:** MEDIUM -- depends on how state is architected.

## Minor Pitfalls

### Pitfall 10: SQLite Lock Contention Between Flask and Background Tasks

**What goes wrong:** Flask serves API requests while a background thread runs a bulk calculation or import. SQLite allows only one writer at a time. The background thread holds a write lock, and Flask requests timeout or error with "database is locked."

**Prevention:**
1. Use `check_same_thread=False` in the connection string
2. Set `PRAGMA journal_mode=WAL` (Write-Ahead Logging) -- allows concurrent reads during writes
3. Keep write transactions short -- batch inserts with `executemany`, commit promptly
4. For the desktop app with one user, this is unlikely to be a real problem. But WAL mode is good practice for web migration anyway

**Phase:** Phase 1 (database layer setup).

**Confidence:** MEDIUM -- unlikely to manifest in desktop app, but relevant for web migration.

---

### Pitfall 11: Product Offset DFT Ignored in Calculations

**What goes wrong:** Some products have a non-zero `offset_dft` value (visible in the `products` table). This offset must be added to (or subtracted from) the looked-up DFT value to get the final specification thickness. If the code ignores it, SC901 specifications will be wrong.

**Prevention:**
1. Always apply `product.offset_dft` to the raw DFT lookup result
2. Verify the direction: does Steelcalc ADD or SUBTRACT the offset? Test with SC901 specifically
3. Include offset_dft in the comparison test suite (Pitfall 5)

**Detection:** SC901 DFT values differ from Steelcalc.

**Phase:** Phase 1 (DFT engine).

**Confidence:** MEDIUM -- the field exists in the schema but the application logic is unknown.

---

### Pitfall 12: Container Size Calculation Rounding Errors

**What goes wrong:** The litres calculation (surface area x DFT x solid_factor / density) accumulates floating-point errors across hundreds of members, and the "number of containers needed" rounds wrong (e.g., 4.001 containers rounds to 5 instead of recognizing the 0.001 as a rounding artifact).

**Prevention:**
1. Use `decimal.Decimal` for all quantity calculations, not float
2. Round litres to 2 decimal places before container calculation
3. Container count = `math.ceil(total_litres / container_size)` -- always round up (you cannot buy partial containers)
4. Show both the exact calculated litres and the rounded container count so users can verify

**Phase:** Phase 1 (calculation engine).

**Confidence:** LOW -- may not manifest with typical project sizes, but is a known issue in quantity estimation tools.

---

### Pitfall 13: Handoff Codebase Lacks Context for Web Developer

**What goes wrong:** The web developer receives a working desktop app but cannot understand the data model, the DFT lookup chain, or the business rules. They rewrite things that were correct, or break the lookup logic while "improving" the code.

**Prevention:**
1. Document the DFT lookup chain with a diagram: Section -> Exposure -> Hp/A -> Band -> Coverage ID -> DFT record
2. Include inline comments explaining WHY each step exists, not just WHAT it does
3. Write a HANDOFF.md explaining: what the data model is, how the lookup works, what the Flask API endpoints do, what the JS frontend expects, and what SQLite-specific code needs to change for PostgreSQL
4. Keep the Flask API clean enough that the web developer can swap out PyWebView for a real web server and the frontend "just works"
5. No PyWebView-specific code in the frontend JS -- use standard `fetch()` to Flask endpoints, never `pywebview.api.*` for data operations

**Detection:** Ask someone unfamiliar with the project to read the code and explain the DFT lookup. If they cannot, the documentation is insufficient.

**Phase:** All phases, but especially Phase 1 (architecture) and final phase (handoff preparation).

**Confidence:** HIGH -- this is the stated end-goal of the project.

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| DFT Engine (Phase 1) | Band/Hp/A matching logic wrong | Build comparison test suite against Steelcalc from day one |
| DFT Engine (Phase 1) | Offset DFT ignored | Test SC901 specifically, verify offset direction |
| Application Shell (Phase 1) | PyWebView threading deadlock | Establish message-queue pattern, never call evaluate_js from API threads |
| API Design (Phase 1) | Globals/file paths prevent web migration | REST design with project_id on every endpoint, no global state |
| State Management (Phase 1) | Data loss on crash/reload | Flask backend owns canonical state, auto-save to temp file |
| CSV/Excel Import (Phase 2) | Real schedules do not match test data | Collect real samples early, fuzzy section name matching |
| Quantifire Export (Phase 2) | Format is guessed, import fails | Obtain template BEFORE building export |
| 3D Preview - Profiles (Phase 2) | Performance cliff with extruded geometry | InstancedMesh grouped by section, LOD for distance |
| 3D Click-to-Place (Phase 3) | Bidirectional sync bugs between table and 3D | Single source of truth in Flask, both views subscribe to it |
| Handoff (Final) | Web developer cannot understand the code | HANDOFF.md, inline comments on business logic, no PyWebView coupling in frontend |

## Sources

- [PyWebView Architecture Guide](https://pywebview.flowrl.com/guide/architecture.html)
- [PyWebView JS-Python Bridge](https://pywebview.flowrl.com/guide/interdomain)
- [PyWebView Threading Issue #627](https://github.com/r0x0r/pywebview/issues/627)
- [PyWebView Thread Safety Issue #257](https://github.com/r0x0r/pywebview/issues/257)
- [Three.js InstancedMesh Docs](https://threejs.org/docs/pages/InstancedMesh.html)
- [Three.js Performance Optimization (Codrops, Feb 2025)](https://tympanus.net/codrops/2025/02/11/building-efficient-three-js-scenes-optimize-performance-while-maintaining-quality/)
- [Three.js LOD Discussion](https://discourse.threejs.org/t/when-is-it-actually-beneficial-to-use-lod-in-three-js-for-performance/87697)
- [Specifying Intumescent Coating Film Thicknesses (Construction Specifier)](https://www.constructionspecifier.com/specifying-intumescent-coating-film-thicknesses/)
- [Steel Section Factor in Intumescent Paint Specification](https://www.intumescentcoatingsystems.com.au/learning-centre/steel-section-factor)
- [Survey of Commercial Intumescent Coating Performance (ScienceDirect, 2025)](https://www.sciencedirect.com/science/article/pii/S0379711225002954)
- [DFT 3D Interpolation Issues (Structure Magazine)](https://www.structuremag.org/article/thickness-for-passive-fire-protection-coatings/)
- [openpyxl Merged Cells Handling](https://gist.github.com/tchen/01d1d61a985190ff6b71fc14c45f95c9)
- [Flask API Best Practices (Auth0)](https://auth0.com/blog/best-practices-for-flask-api-development/)
- [Flask Application Structure 2025 (DEV)](https://dev.to/gajanan0707/how-to-structure-a-large-flask-application-best-practices-for-2025-9j2)
- [SQLite Query Optimizer Overview](https://sqlite.org/optoverview.html)
- [SQLite WAL Mode Optimizations (PowerSync)](https://www.powersync.com/blog/sqlite-optimizations-for-ultra-high-performance)
