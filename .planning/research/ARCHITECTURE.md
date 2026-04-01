# Architecture Patterns

**Domain:** Structural steel fire protection specification tool
**Researched:** 2026-04-01

## Recommended Architecture

```
+------------------+     +-------------------+     +-----------+
|   PyWebView      |     |   Flask Backend    |     |  SQLite   |
|   (Desktop Shell)|---->|   (API Server)     |<--->|  Database |
|                  |     |                    |     |           |
|  +------------+  |     |  /api/sections/*   |     | nullifire.db
|  | HTML/CSS/JS|  |     |  /api/projects/*   |     |  (reference)
|  | AG Grid    |  |     |  /api/dft/*        |     |           |
|  | Three.js   |<------->  /api/export/*     |     | projects.db
|  | Frontend   |  |     |  /api/import/*     |     |  (user data)
|  +------------+  |     +-------------------+     +-----------+
+------------------+              |
                         +--------+--------+
                         |                 |
                    +---------+      +-----------+
                    | openpyxl|      | WeasyPrint|
                    | (Excel) |      | (PDF)     |
                    +---------+      +-----------+
```

The frontend is a vanilla HTML/CSS/JS application that talks to Flask via REST API. PyWebView wraps the whole thing as a desktop window. When a web developer inherits this, they drop PyWebView and point the frontend at a hosted Flask server -- zero UI rewrite required.

### Why This Structure

1. **Clean separation**: Frontend knows nothing about Python. Backend knows nothing about DOM. They communicate via JSON over HTTP.
2. **Transfer-ready**: The web developer gets a working frontend + API contract. They can swap Flask for Django/FastAPI/Node without touching the UI.
3. **Testable**: API endpoints testable with pytest + requests. Frontend testable in any browser. No coupling.

### Component Boundaries

| Component | Responsibility | Communicates With | Does NOT Touch |
|-----------|---------------|-------------------|----------------|
| **PyWebView** | Native window shell, app lifecycle | Flask (HTTP on localhost:5000) | Everything else |
| **Flask Routes** | HTTP request/response, JSON serialization | Services | Database directly, DOM |
| **Services** | Business logic, DFT lookup chain, calculations | SQLite (via db.py) | HTTP, request objects |
| **Frontend Pages** | User interaction, DOM rendering | API module, AG Grid, SceneManager | Flask, SQLite, Python |
| **API Module** | All fetch() calls to backend, error handling | Flask routes | DOM, Three.js, AG Grid |
| **AG Grid** | Data table display, inline editing, sort/filter | Frontend JS (events + data) | API (caller provides data) |
| **SceneManager** | 3D viewport rendering, camera, interaction | Three.js groups | API, Flask, data tables |
| **Import Service** | CSV/Excel parsing, column detection, validation | openpyxl, csv stdlib | HTTP, DOM |
| **Export Service** | Excel/PDF file generation | openpyxl, WeasyPrint, Jinja2 | HTTP, DOM |

**Boundary Rule:** Every boundary is a function call that takes plain data and returns plain data. No component reaches through another component's internals.

## Flask Backend Structure

```
app/
    __init__.py              # create_app() factory
    config.py                # Config classes (Dev, Prod, Test)
    db.py                    # SQLite connection helpers (ref + project databases)
    
    api/
        __init__.py          # Blueprint registration
        sections.py          # GET /api/sections/search?q=UB305&origin=1
                             # GET /api/sections/<id>
                             # GET /api/sections/<id>/factors
        products.py          # GET /api/products
                             # GET /api/products/<id>/ratings
        dft.py               # POST /api/dft/lookup  (section + exposure + product + rating -> DFT)
                             # POST /api/dft/calculate  (DFT + dimensions -> litres/kg)
        projects.py          # CRUD /api/projects
                             # CRUD /api/projects/<id>/members
                             # GET  /api/projects/<id>/summary
        grid.py              # CRUD /api/projects/<id>/grid
                             # CRUD /api/projects/<id>/levels
        import_export.py     # POST /api/import/parse  (upload CSV/Excel, return columns)
                             # POST /api/import/map    (column mapping + validate -> members)
                             # GET  /api/export/excel/<project_id>
                             # GET  /api/export/pdf/<project_id>
    
    services/
        __init__.py
        section_service.py   # Steel section search, filtering, typeahead
        dft_service.py       # DFT lookup chain: section -> band -> Hp/A -> coverage -> DFT
        calc_service.py      # Surface area, volume, litres/kg calculations
        project_service.py   # Project CRUD, member management, summary totals
        grid_service.py      # Grid/level management
        import_service.py    # CSV/Excel parsing, column detection, validation
        export_service.py    # Excel (openpyxl) and PDF (WeasyPrint) generation
    
    models/
        __init__.py
        project.py           # Project, ProjectMember, GridLine, Level dataclasses
    
    templates/
        report.html          # Jinja2 template for PDF report (server-side only)
```

### Blueprint Organization

Use **two blueprints**, not one per file:

| Blueprint | Prefix | Purpose |
|-----------|--------|---------|
| `api_bp` | `/api` | All JSON API endpoints |
| `main_bp` | `/` | Serves the frontend `index.html` + static files |

Two blueprints is enough. This is not a large multi-team application -- do not over-engineer with a blueprint per resource. A single `api` blueprint with route files imported via `from .sections import *` etc. keeps it clean and navigable.

### Service Layer Rules

1. **Routes do HTTP only**: Parse request, call service, return JSON response
2. **Services do logic only**: No `request` object, no `jsonify`. Pure Python in, pure Python out
3. **Services return dicts or dataclasses**, never SQLite row tuples

Example flow for DFT lookup:

```
POST /api/dft/lookup
  Body: { section_id, hp_profile, product_id, fire_rating_id, failure_temp_id }

Route (dft.py):
  -> parse request JSON
  -> call dft_service.lookup(section_id, hp_profile, product_id, ...)
  -> return jsonify(result)

Service (dft_service.py):
  -> get section factor from section_factors table
  -> map Hp/A to coverage band via bands table
  -> find coverage_id for that Hp/A (exact match: min=max)
  -> look up DFT from dft_data table
  -> return { hp_over_a, coverage_id, dft_mm, status }
```

## Database Strategy

### Two Databases, Same SQLite Engine

| Database | Purpose | Access |
|----------|---------|--------|
| `data/nullifire.db` | Reference data (steel sections, DFT tables, products) | Read-only, shipped with app |
| `data/projects.db` | User projects, members, grids, levels | Read-write, created on first run |

**Why separate:** The reference database is a known-good artifact extracted from the legacy Access DB. Never write to it. Project data is user-generated and independently backupable. When migrating to PostgreSQL for web, reference data becomes a managed migration, and project data becomes per-user storage. Product data can be updated by replacing the .db file when new Nullifire certifications arrive.

### Project Database Schema

```sql
CREATE TABLE projects (
    id TEXT PRIMARY KEY,           -- UUID
    name TEXT NOT NULL,
    product_id INTEGER NOT NULL,   -- FK to nullifire.db products
    fire_rating_id INTEGER NOT NULL,
    failure_temp_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE project_members (
    id TEXT PRIMARY KEY,           -- UUID
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    section_id INTEGER NOT NULL,   -- FK to nullifire.db steel_sections
    hp_profile_name TEXT NOT NULL, -- Exposure type
    quantity INTEGER DEFAULT 1,
    length_m REAL,
    zone TEXT,                     -- User label ("Zone A", "Ground Floor")
    grid_x TEXT,                   -- Grid intersection label ("A")
    grid_y TEXT,                   -- Grid intersection label ("3")
    level_id TEXT REFERENCES project_levels(id),
    fire_rating_id INTEGER,        -- Per-member override (NULL = project default)
    failure_temp_id INTEGER,       -- Per-member override
    product_id INTEGER,            -- Per-member override
    sort_order INTEGER,
    created_at TEXT NOT NULL
);

CREATE TABLE project_gridlines (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    axis TEXT NOT NULL CHECK(axis IN ('x', 'y')),  -- x=columns (A,B,C), y=rows (1,2,3)
    label TEXT NOT NULL,
    position_m REAL NOT NULL,      -- Distance from origin in metres
    sort_order INTEGER
);

CREATE TABLE project_levels (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,            -- "Ground Floor", "Level 1", etc.
    height_m REAL NOT NULL,        -- Height above datum
    fire_rating_id INTEGER,        -- Level default override
    failure_temp_id INTEGER,       -- Level default override
    sort_order INTEGER
);
```

### DFT Lookup Chain (Core Algorithm)

This is the most complex data operation. The chain follows the legacy Steelcalc logic:

```
Input: section_id, hp_profile_name, product_id, fire_rating_id, failure_temp_id

Step 1: Section Factor
  SELECT hp_over_a FROM section_factors 
  WHERE steel_section_id = ? AND hp_profile_name = ?
  -> hp_over_a value (e.g., 185 m^-1)

Step 2: Coverage Band
  SELECT coverage_id FROM bands 
  WHERE band_id = (product's catalogue_band) AND hp_over_a = ?
  -> coverage_id (exact match where hp_over_a falls in range)

Step 3: DFT Lookup
  SELECT dft_mm FROM dft_data 
  WHERE product_id = ? AND fire_rating_id = ? 
    AND failure_temp_id = ? AND coverage_id = ?
  -> dft_mm value (dry film thickness in mm)

Step 4: Calculate quantities
  perimeter = section profile perimeter for exposure type (from hp_profiles)
  surface_area_m2 = perimeter_m * length_m * quantity
  volume_litres = surface_area_m2 * (dft_mm / 1000) / product.solid_factor
  weight_kg = volume_litres * product.density

Output: { hp_over_a, coverage_id, dft_mm, surface_area_m2, volume_litres, 
          weight_kg, verification_status }
```

**Verification status** maps Hp/A against the product's certified range:
- Green: within certified range
- Amber: near maximum certified Hp/A
- Red: exceeds product certification (cannot specify)
- Grey: missing data (incomplete inputs)

## Frontend Structure

```
static/
    css/
        main.css                 # Layout, Nullifire branding (red/dark grey/white)
        tables.css               # AG Grid theme overrides
        forms.css                # Input, typeahead, modal styles
        three-viewport.css       # 3D viewport container
    
    js/
        app.js                   # App init, hash-based page routing, State object
        api.js                   # All fetch() calls to Flask API (single module)
        events.js                # Simple pub/sub event bus
        
        components/
            typeahead.js         # Section search with keyboard navigation
            column-mapper.js     # Import column mapping UI
            modal.js             # Modal dialog component
            toast.js             # Notification toasts
        
        pages/
            project-setup.js     # Project creation/settings page
            member-entry.js      # Main member entry table (AG Grid) + DFT results
            grid-setup.js        # Grid/level definition page
            import.js            # CSV/Excel import workflow
            summary.js           # Project summary with totals
        
        three/
            scene-manager.js     # Three.js scene, camera, renderer, OrbitControls
            grid-view.js         # Structural grid lines (named axes)
            level-view.js        # Level planes (transparent horizontal slabs)
            member-view.js       # Steel member visualization
            materials.js         # Shared Three.js materials (DFT color gradient)
        
        utils/
            formatting.js        # Number formatting, unit display
            validation.js        # Client-side input validation
    
    vendor/
        ag-grid-community.min.js # AG Grid (no npm, direct include)
        three.module.js          # Three.js ES module
        OrbitControls.js         # Three.js orbit controls
    
    index.html                   # Single HTML shell with page containers
```

### Why Vanilla JS with AG Grid (Not a Framework)

1. **Handoff target is a web developer** who will integrate into Nullifire's existing website -- which could be WordPress, .NET, or anything. Framework-free HTML/JS drops in anywhere.
2. **AG Grid handles the hard part**: The member entry table IS the core UI -- sort, filter, inline edit, virtual scrolling for large datasets. AG Grid Community Edition does all this without React/Angular/Vue.
3. **No build step**: The web developer can open `index.html` in a browser and understand everything. No webpack, no node_modules, no transpiling. Vendor libraries included as static files.

### Page Routing Pattern

Hash-based SPA routing. No library needed.

```javascript
// app.js
const routes = {
    '#/setup':   () => ProjectSetup.render(),
    '#/members': () => MemberEntry.render(),
    '#/grid':    () => GridSetup.render(),
    '#/import':  () => ImportPage.render(),
    '#/summary': () => SummaryPage.render(),
};

window.addEventListener('hashchange', () => {
    const handler = routes[location.hash] || routes['#/members'];
    handler();
});
```

### API Module (Single Point of Contact)

All backend communication goes through one module. This is the contract the web developer inherits.

```javascript
// api.js
const API = {
    baseUrl: '',  // Same origin for PyWebView; change for hosted deployment
    
    async get(path) {
        const res = await fetch(`${this.baseUrl}${path}`);
        if (!res.ok) throw new Error(await res.text());
        return res.json();
    },
    
    async post(path, body) { /* ... */ },
    
    // Steel sections
    searchSections: (q, originId) => API.get(`/api/sections/search?q=${q}&origin=${originId}`),
    getSectionFactors: (id) => API.get(`/api/sections/${id}/factors`),
    
    // DFT
    lookupDFT: (params) => API.post('/api/dft/lookup', params),
    
    // Projects
    createProject: (data) => API.post('/api/projects', data),
    getMembers: (projectId) => API.get(`/api/projects/${projectId}/members`),
    addMember: (projectId, data) => API.post(`/api/projects/${projectId}/members`, data),
    
    // Export
    downloadExcel: (projectId) => window.open(`/api/export/excel/${projectId}`),
    downloadPDF: (projectId) => window.open(`/api/export/pdf/${projectId}`),
};
```

### Frontend State

One global state object holds the current project context. No state management library.

```javascript
// app.js
const State = {
    projectId: null,
    project: null,
    members: [],
    gridlines: [],
    levels: [],
    
    async loadProject(id) {
        this.projectId = id;
        this.project = await API.getProject(id);
        this.members = await API.getMembers(id);
        this.gridlines = await API.getGridlines(id);
        this.levels = await API.getLevels(id);
        events.emit('project:loaded', this.project);
    }
};
```

### Event Bus for Component Communication

```javascript
// events.js -- Simple pub/sub
const handlers = {};
export function on(event, fn) { (handlers[event] ??= []).push(fn); }
export function emit(event, data) { (handlers[event] ?? []).forEach(fn => fn(data)); }
```

AG Grid, Three.js viewer, and summary panel all listen to the same events. They never import each other.

```javascript
// In member-entry.js (AG Grid)
events.emit('member:added', memberData);
events.emit('member:selected', memberId);

// In scene-manager.js (Three.js)
events.on('member:added', (m) => sceneManager.addMember(m));
events.on('member:selected', (id) => sceneManager.highlightMember(id));
```

## Three.js Scene Architecture

### Scene Graph Hierarchy

```
Scene
  |
  +-- GridGroup (THREE.Group)
  |     +-- X-axis lines (A, B, C, D...)    -- vertical planes in XZ
  |     +-- Y-axis lines (1, 2, 3, 4...)    -- vertical planes in XZ
  |     +-- Grid labels (CSS2DRenderer or Sprite)
  |
  +-- LevelsGroup (THREE.Group)
  |     +-- Ground plane (transparent grey)
  |     +-- Level 1 plane (transparent blue)
  |     +-- Level labels
  |
  +-- MembersGroup (THREE.Group)
        +-- Member_uuid_001 (THREE.Line or THREE.Mesh)
        +-- Member_uuid_002
        +-- ...
```

### Scene Manager

```javascript
// three/scene-manager.js
class SceneManager {
    constructor(container) {
        this.scene = new THREE.Scene();
        this.camera = new THREE.PerspectiveCamera(60, w/h, 0.1, 1000);
        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.controls = new OrbitControls(this.camera, this.renderer.domElement);
        
        // Separate groups -- add/remove members without touching grid
        this.gridGroup = new THREE.Group();
        this.levelsGroup = new THREE.Group();
        this.membersGroup = new THREE.Group();
        
        this.scene.add(this.gridGroup);
        this.scene.add(this.levelsGroup);
        this.scene.add(this.membersGroup);
    }
    
    updateGrid(gridlines) { GridView.rebuild(this.gridGroup, gridlines); }
    updateLevels(levels) { LevelView.rebuild(this.levelsGroup, levels); }
    addMember(member) { MemberView.add(this.membersGroup, member); }
    removeMember(id) { MemberView.remove(this.membersGroup, id); }
    highlightMember(id) { MemberView.highlight(this.membersGroup, id); }
}
```

### Phased 3D Implementation

| Phase | Visual | Geometry | Complexity |
|-------|--------|----------|------------|
| Phase 1 | Wireframe | `THREE.Line` between grid intersections | Low |
| Phase 2 | Extruded profiles | `THREE.ExtrudeGeometry` with DFT color gradient | Medium |
| Phase 3 | Click-to-place | Raycasting + snap to grid + drag placement | High |

Phase 1 is the MVP target. The scene manager infrastructure supports all three phases without refactoring because members are always objects in `membersGroup` -- only the geometry creation function changes between phases.

### DFT Color Gradient on Members

| Status | Color | Hex | Meaning |
|--------|-------|-----|---------|
| Green | Safe | `#4CAF50` | DFT within product limits |
| Amber | Near limit | `#FF9800` | Approaching maximum Hp/A |
| Red | Exceeds | `#F44336` | Exceeds product certification |
| Grey | Incomplete | `#9E9E9E` | Missing lookup inputs |

## Data Flow Diagrams

### Member Entry Flow (the core loop)

```
User types "UB305" in AG Grid typeahead
    -> typeahead.js calls API.searchSections("UB305", originId)
    -> Flask: section_service.search("UB305", originId) queries steel_sections
    -> Returns: [{ id, serial_size, depth, width, weight, ... }]
    
User selects "UB305x165x40", sets exposure to "3-sided column"
    -> API.lookupDFT({ section_id, hp_profile, product_id, fire_rating_id, failure_temp_id })
    -> Flask: dft_service.lookup() runs the 4-step chain
    -> Returns: { hp_over_a: 185, dft_mm: 1.2, status: "green" }
    
User enters quantity=4, length=6.0m
    -> API.addMember(projectId, { section_id, hp_profile, quantity, length_m, ... })
    -> Flask: project_service.add_member() saves + calc_service calculates quantities
    -> Returns: complete member with { surface_area_m2, volume_litres, weight_kg }
    
Frontend updates:
    -> AG Grid: new row with all computed fields
    -> events.emit('member:added', member)
    -> Three.js: addMember() renders line in 3D view
    -> Summary: recalculates running totals
```

### Import Flow

```
User uploads CSV/Excel
    -> POST /api/import/parse (multipart file upload)
    -> import_service.parse_file() reads headers + first 10 preview rows
    -> Returns: { columns: ["Section", "Qty", ...], preview: [[...], ...] }
    
User maps columns via column-mapper UI (dropdowns)
    -> POST /api/import/map { mapping: { section: "Col A", quantity: "Col B" }, data: [...] }
    -> import_service.validate_and_import():
         For each row:
           - Fuzzy-match section serial_size against steel_sections
           - Validate numeric fields (quantity, length)
           - Run DFT lookup for each valid row
           - Flag unresolvable rows with reason
    -> Returns: { imported: 42, warnings: [{row: 5, msg: "Unknown section"}], errors: [...] }
```

### Export Flow

```
User clicks "Export Excel"
    -> GET /api/export/excel/<project_id>
    -> export_service.generate_excel(project_id):
         - Queries all members with computed DFT values
         - Builds openpyxl Workbook in Quantifire import format
         - Writes to BytesIO
    -> Returns: Excel file (Content-Disposition: attachment)

User clicks "Export PDF"
    -> GET /api/export/pdf/<project_id>
    -> export_service.generate_pdf(project_id):
         - Queries all members + summary totals
         - Renders Jinja2 template (report.html) with data
         - Converts HTML to PDF via WeasyPrint
    -> Returns: PDF file (Content-Disposition: attachment)
```

## Patterns to Follow

### Pattern 1: Service Functions Are Pure -- No HTTP Objects

```python
# services/dft_service.py
def lookup(section_id: int, hp_profile: str, product_id: int, 
           fire_rating_id: int, failure_temp_id: int) -> dict:
    """Pure lookup: IDs in, result dict out. No request object."""
    db = get_reference_db()
    
    # Step 1: Get Hp/A section factor
    row = db.execute(
        "SELECT hp_over_a FROM section_factors "
        "WHERE steel_section_id=? AND hp_profile_name=?",
        (section_id, hp_profile)
    ).fetchone()
    if not row:
        return {"error": "No section factor", "status": "grey"}
    
    hp_over_a = row[0]
    # ... chain continues through steps 2-4
    
    return {"hp_over_a": hp_over_a, "dft_mm": dft_mm, "status": status}
```

**Why:** When web dev inherits this, they keep the service layer and replace Flask routes with their framework. Zero business logic rewriting.

### Pattern 2: Data Table is Source of Truth, 3D Renders From It

The AG Grid data (backed by API responses) is the single source of truth. The Three.js viewer renders FROM the data, never maintains its own independent list. Use `userData` on Three.js objects to link back to member IDs.

### Pattern 3: Event Bus Decouples Components

AG Grid, Three.js, and summary panel communicate through events, never direct imports. Web dev can replace the event bus with Redux, Pinia, or whatever their framework provides.

## Anti-Patterns to Avoid

### Anti-Pattern 1: PyWebView JS-Python Bridge Instead of HTTP API

**What:** Using `pywebview.api` to call Python functions directly from JavaScript.
**Why bad:** Creates desktop-only coupling. The web developer cannot use `window.pywebview.api.searchSections()` on a website -- they would rewrite every call.
**Instead:** Standard `fetch()` calls to Flask endpoints. PyWebView just wraps the browser window.

### Anti-Pattern 2: Business Logic in Frontend JS

**What:** Calculating DFT, Hp/A, or litres in JavaScript.
**Why bad:** Duplicates logic. Import/export endpoints need the same calculations server-side. Two sources of truth.
**Instead:** All calculations in Flask services. Frontend displays results from API.

### Anti-Pattern 3: Jinja2 Templates for Main UI

**What:** Using `render_template()` for page rendering instead of static HTML + API calls.
**Why bad:** Creates Python-coupled frontend the web developer must understand Jinja2 to modify.
**Instead:** Flask serves `index.html` as static. All data via JSON API. Reserve Jinja2 ONLY for PDF report template.

### Anti-Pattern 4: SQLite Queries in Route Handlers

**What:** Writing SQL directly in Flask route functions.
**Why bad:** Mixes HTTP concerns with data access. Cannot reuse queries or unit test without Flask context.
**Instead:** All SQL in service functions. Routes call services.

### Anti-Pattern 5: Monolithic Three.js File

**What:** All 3D logic in one file (scene setup, grid, members, interaction).
**Why bad:** Unmaintainable as Phase 2 and Phase 3 add complexity.
**Instead:** Separate files: scene-manager.js (coordinator), grid-view.js, level-view.js, member-view.js (workers).

## PyWebView Integration

```python
# run.py (entry point)
import webview
import threading
from app import create_app

def start_server(app):
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)

if __name__ == '__main__':
    app = create_app()
    
    # Start Flask in background thread
    server = threading.Thread(target=start_server, args=(app,), daemon=True)
    server.start()
    
    # Create native window pointing at Flask
    webview.create_window(
        'Nullifire Intumescent Calculator',
        'http://127.0.0.1:5000',
        width=1400, height=900,
        min_size=(1024, 700)
    )
    webview.start()
```

**Key Principle:** PyWebView is a dumb window. It launches Flask, opens a browser pointed at localhost, and gets out of the way. No `js_api`, no bridge, no special hooks. The frontend is a web app that happens to run inside a native frame. Developing in a regular browser is faster than developing inside PyWebView.

## Suggested Build Order

Build order follows data dependencies -- each layer depends on the one before it.

### Phase 1: Foundation (no UI)

1. Flask app shell -- `create_app()`, config, blueprints, health check
2. Database layer -- `db.py` with connection helpers for both databases
3. Project database schema -- projects, members, gridlines, levels tables

**Depends on:** Existing `nullifire.db` (already built)

### Phase 2: Core Data API

4. Section service + routes -- search, get, get_factors (typeahead backend)
5. DFT service + routes -- the lookup chain (the hard part, multi-table join logic)
6. Calculation service -- surface area, volume, litres from DFT + dimensions
7. Project service + routes -- CRUD for projects and members

**Depends on:** Phase 1

### Phase 3: Frontend Shell + Member Entry

8. `index.html` shell -- navigation, page containers, Nullifire branding CSS
9. API module -- all fetch() calls
10. AG Grid integration -- community edition, configured for member data
11. Typeahead component -- section search with keyboard navigation
12. Member entry page -- AG Grid + typeahead + DFT display + verification colors

**Depends on:** Phase 2 (working API endpoints)

### Phase 4: Project Setup + Grid + Summary

13. Project setup page -- create/edit project, product/rating/temp defaults
14. Grid setup page -- define named gridlines + levels with heights
15. Summary page -- running totals, verification overview, litres/kg/containers

**Depends on:** Phase 3

### Phase 5: 3D Viewport (wireframe)

16. Scene manager -- Three.js init, camera, OrbitControls, resize
17. Grid view -- render named gridlines as 3D lines with labels
18. Level view -- render level planes as transparent horizontal slabs
19. Member view -- render members as lines between grid intersections
20. Table-3D sync via event bus -- highlight on select, add/remove sync

**Depends on:** Phase 4 (grid/level data), Phase 3 (member data)

### Phase 6: Import/Export

21. Import service -- CSV/Excel parsing with openpyxl
22. Column mapper UI -- dropdown mapping interface with preview
23. Export service -- Excel generation (Quantifire format)
24. PDF report -- Jinja2 template + WeasyPrint

**Depends on:** Phase 3 (members to export), Phase 2 (DFT data for report)

### Phase 7: Desktop Wrapper

25. `run.py` -- PyWebView + Flask threading
26. Packaging -- PyInstaller or similar for distribution

**Depends on:** Everything else

### Why This Order

- **Phases 1-2** build the data backbone everything else depends on
- **Phase 3** is the core user experience -- fast member entry with instant DFT is the product's core value
- **Phase 4** adds project context (settings, grid, summary) around the core
- **Phase 5** (3D) is visual enhancement, independently useful but not blocking the core workflow
- **Phase 6** (import/export) needs working member data to import into or export from
- **Phase 7** (desktop wrapper) is literally one file; developing in a browser is faster

## Scalability Considerations

| Concern | Desktop POC (now) | Web App (future) |
|---------|-------------------|-------------------|
| Database | SQLite (single user) | PostgreSQL (multi-user, connection pool) |
| Auth | None | User accounts, project ownership |
| File storage | Local filesystem | S3/blob for uploaded imports |
| Concurrency | Single user | Flask -> async framework, worker pool |
| 3D performance | Client-side WebGL | Same (no server-side 3D) |
| PDF generation | Synchronous | Celery task queue for large reports |
| Data volume | 3,545 sections, 44K DFT | Same reference data, many user projects |

The architecture handles this migration because the service layer has no HTTP dependency, the frontend is already a web app, SQLite queries are standard SQL portable to PostgreSQL, and Three.js runs entirely client-side.

## Sources

- [Flask Blueprints Documentation](https://flask.palletsprojects.com/en/stable/blueprints/) -- HIGH confidence
- [Flask Application Structure Best Practices](https://dev.to/gajanan0707/how-to-structure-a-large-flask-application-best-practices-for-2025-9j2) -- MEDIUM confidence
- [Three.js Scene Graph](https://threejs.org/manual/en/scenegraph.html) -- HIGH confidence
- [Organizing Three.js with Groups](https://discoverthreejs.com/book/first-steps/organizing-with-group/) -- HIGH confidence
- [PyWebView Architecture Guide](https://pywebview.flowrl.com/guide/architecture.html) -- HIGH confidence
- [AG Grid Vanilla JS Quick Start](https://www.ag-grid.com/javascript-data-grid/getting-started/) -- HIGH confidence
- [openpyxl Documentation](https://openpyxl.readthedocs.io/) -- HIGH confidence
- [WeasyPrint + Flask PDF Generation](https://pbpython.com/pdf-reports.html) -- MEDIUM confidence
- [Three.js Steel Building Configurator (forum)](https://discourse.threejs.org/t/looking-for-a-three-js-developer-to-enhance-steel-building-configurator/61500) -- LOW confidence (job post, not technical docs)
