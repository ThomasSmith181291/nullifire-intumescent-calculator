# Technology Stack

**Project:** Nullifire Intumescent Calculator
**Researched:** 2026-04-01

## Recommended Stack

### Core Backend

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python | 3.12+ | Runtime | Current stable, good performance, type hint maturity |
| Flask | 3.1.3 | API framework | Lightweight, API-first, web dev inherits directly. Factory pattern + blueprints for clean separation |
| SQLite | 3 (stdlib) | Database | Already built with product data. Zero config. Transfers to PostgreSQL for web via SQLAlchemy if needed |
| PyWebView | 6.1 | Desktop wrapper | Native window without Electron weight. HTML/JS frontend transfers to web unchanged |

### Frontend (No Build Step)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Vanilla JS (ES6+) | - | Application logic | No framework overhead. Web dev can wrap in React/Vue later. Simpler handoff than framework-specific code |
| AG Grid Community | 35.2.0 | Data tables | MIT licensed, free forever. Sorting, filtering, inline editing, 100+ rows trivially. Industry standard for engineering data grids |
| Three.js | 0.183.x | 3D structural preview | Only serious WebGL library. Works via CDN. Structural steel configurators actively built with it |
| CSS Custom Properties | - | Theming | Nullifire branding via CSS variables. No preprocessor needed for this scope |

### Data Processing Libraries

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| openpyxl | 3.1.5 | Excel read/write | Standard Python Excel library. Handles .xlsx formatting for Quantifire export templates |
| WeasyPrint | 62.x | PDF generation | HTML+CSS to PDF. Reuse frontend templates for reports. No browser dependency like wkhtmltopdf |
| Jinja2 | 3.1.x | HTML templating | Ships with Flask. Used for PDF report templates and any server-rendered HTML |

### Development Tools

| Tool | Version | Purpose | Why |
|------|---------|---------|-----|
| Flask-CORS | 5.x | CORS headers | Required when PyWebView makes requests to Flask on localhost |
| PyInstaller | 6.x | Desktop packaging | Bundle Python + Flask + PyWebView into single .exe for distribution |
| pytest | 8.x | Testing | Standard Python testing. Test API endpoints and calculation logic independently |

## Stack Decisions Explained

### Why Vanilla JS, Not a Framework

The project constraint says "web developer inherits this codebase." A vanilla JS frontend with AG Grid and Three.js is:
1. **Framework-agnostic** -- web dev picks their own framework and wraps existing logic
2. **No build toolchain** -- no webpack/vite/npm during POC phase. Just HTML/CSS/JS files served by Flask
3. **Simpler debugging** -- no virtual DOM, no reactivity magic, just DOM manipulation
4. **AG Grid handles the hard part** -- the complex UI (data tables with editing) is AG Grid, not custom code

The 3D viewer is self-contained Three.js. The data table is self-contained AG Grid. The glue between them is vanilla JS event handling. A web dev inherits working components, not a framework they might not want.

### Why AG Grid Over Alternatives

| Considered | Verdict | Reason |
|-----------|---------|--------|
| **AG Grid Community** | USE THIS | Free MIT license, inline editing, sorting, filtering, column resize/reorder, CSV export built-in. Handles 10K+ rows. Works with vanilla JS via CDN |
| Tabulator | Rejected | Similar features but smaller ecosystem. AG Grid has better docs and is the industry default for data-heavy apps |
| Handsontable | Rejected | License changed to non-free for commercial use. Not suitable |
| Custom HTML tables | Rejected | Would take weeks to build what AG Grid does out of the box (inline edit, sort, filter, virtual scrolling) |

### Why WeasyPrint Over Alternatives

| Considered | Verdict | Reason |
|-----------|---------|--------|
| **WeasyPrint** | USE THIS | Pure Python, no external binary dependencies. Renders HTML+CSS to PDF. Reuse Jinja2 templates. Supports @page rules for headers/footers |
| ReportLab | Rejected | Programmatic PDF construction (coordinates, not HTML). Much more work for report-style output |
| wkhtmltopdf | Rejected | Requires external binary. Deprecated upstream. Headless Chrome dependency is heavy |
| pdfkit | Rejected | Wrapper around wkhtmltopdf -- same problems |

### Why Flask, Not FastAPI

Flask was already decided in PROJECT.md constraints. This is the right call because:
1. **Simpler for POC** -- no async complexity needed for a desktop calculator
2. **Jinja2 built-in** -- used for PDF report templates
3. **Web dev familiarity** -- Flask is universally understood
4. **PyWebView integration** -- well-documented Flask+PyWebView patterns exist

FastAPI would add unnecessary async complexity for a tool that does synchronous SQLite lookups and calculations.

## Frontend Architecture (No Build Step)

```
static/
  css/
    main.css              # Nullifire branding, layout
    ag-grid-theme.css     # AG Grid theme overrides
  js/
    app.js                # Main application controller
    api.js                # Flask API client (fetch wrapper)
    grid-manager.js       # AG Grid setup, column defs, event handlers
    three-viewer.js       # Three.js scene, camera, controls, member rendering
    import-mapper.js      # CSV/Excel column mapping UI
  vendor/
    ag-grid-community.min.js    # AG Grid (CDN or local)
    three.min.js                # Three.js (CDN or local)
    OrbitControls.js            # Three.js camera controls
templates/
  index.html              # Main SPA shell
  reports/
    specification.html    # PDF report template (Jinja2)
```

All JS files are ES6 modules loaded via `<script type="module">`. No bundler. No npm. No node_modules.

## Flask API Architecture

```
app/
  __init__.py             # create_app() factory
  config.py               # Configuration classes
  api/
    __init__.py           # Blueprint registration
    projects.py           # Project CRUD endpoints
    members.py            # Steel member endpoints
    calculations.py       # DFT lookup, Hp/A, litres calculation
    sections.py           # Steel section search/typeahead
    imports.py            # CSV/Excel upload + column mapping
    exports.py            # Excel export (Quantifire format), PDF generation
    grids.py              # Structural grid + levels endpoints
  services/
    dft_calculator.py     # Core DFT lookup chain logic
    section_service.py    # Section factor calculations
    import_service.py     # Parse uploaded CSV/Excel, apply column mapping
    export_service.py     # Generate Excel (openpyxl) and PDF (WeasyPrint)
    grid_service.py       # Grid/level business logic
  models/
    database.py           # SQLite connection manager
    queries.py            # SQL query functions
  static/                 # Frontend files (served by Flask)
  templates/              # Jinja2 templates
```

Use Flask Blueprints with URL prefix `/api/v1/`. All endpoints return JSON. Frontend communicates via `fetch()`.

## PyWebView Integration Pattern

```python
import webview
import threading
from app import create_app

def start_flask(ready_event):
    """Run Flask in background thread."""
    app = create_app()
    ready_event.set()  # Signal PyWebView that server is ready
    app.run(host='127.0.0.1', port=5000, use_reloader=False)

if __name__ == '__main__':
    ready_event = threading.Event()
    t = threading.Thread(target=start_flask, args=(ready_event,), daemon=True)
    t.start()
    ready_event.wait()  # Wait for Flask to be ready
    
    webview.create_window(
        'Nullifire Intumescent Calculator',
        'http://127.0.0.1:5000',
        width=1400,
        height=900,
        min_size=(1200, 700)
    )
    webview.start()
```

Key points:
- Flask runs in a daemon thread, PyWebView owns the main thread (GUI loop)
- `ready_event` ensures window doesn't open before Flask is serving
- `use_reloader=False` required -- reloader spawns processes that conflict with PyWebView
- No CSRF needed for desktop-only (localhost), but Flask-CORS needed for cross-origin fetch from PyWebView's webview context

## Three.js Integration Pattern for Structural Steel

```javascript
// Wireframe grid + members (Phase 1)
import * as THREE from './vendor/three.module.js';
import { OrbitControls } from './vendor/OrbitControls.js';

class StructuralViewer {
    constructor(container) {
        this.scene = new THREE.Scene();
        this.camera = new THREE.PerspectiveCamera(60, w/h, 0.1, 1000);
        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.controls = new OrbitControls(this.camera, this.renderer.domElement);
        this.gridGroup = new THREE.Group();   // Grid lines
        this.memberGroup = new THREE.Group(); // Steel members
        this.scene.add(this.gridGroup, this.memberGroup);
    }
    
    addMember(startPoint, endPoint, colorHex) {
        // Phase 1: Line geometry between grid intersections
        const geometry = new THREE.BufferGeometry().setFromPoints([start, end]);
        const material = new THREE.LineBasicMaterial({ color: colorHex });
        const line = new THREE.Line(geometry, material);
        line.userData = { memberId: id };  // Link to data table row
        this.memberGroup.add(line);
    }
    
    // Phase 2: Replace lines with ExtrudeGeometry using section profiles
    // Phase 3: Raycaster for click-to-place interaction
}
```

Members stored as lines between grid intersection points. Color encodes DFT status (green/amber/red). `userData` links 3D objects to data table rows for bidirectional sync.

## Installation

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# Core
pip install flask==3.1.3 pywebview==6.1 flask-cors==5.0.0

# Data processing
pip install openpyxl==3.1.5 weasyprint==62.3 

# Development
pip install pytest==8.3.4

# Packaging (when ready)
pip install pyinstaller==6.11.1
```

```html
<!-- Frontend vendor libraries (CDN or local copy) -->
<script src="https://cdn.jsdelivr.net/npm/ag-grid-community@35.2.0/dist/ag-grid-community.min.js"></script>
<script type="importmap">
{
  "imports": {
    "three": "https://cdn.jsdelivr.net/npm/three@0.183.0/build/three.module.js",
    "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.183.0/examples/jsm/"
  }
}
</script>
```

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Backend | Flask 3.1.3 | FastAPI | Async unnecessary for desktop calculator; Flask simpler for handoff |
| Frontend | Vanilla JS | Alpine.js | Adds a dependency without enough value; AG Grid handles complex UI |
| Frontend | Vanilla JS | React/Vue | Framework lock-in; web dev should choose their own |
| Data grid | AG Grid Community | Tabulator | Smaller ecosystem, less documentation |
| Data grid | AG Grid Community | Handsontable | Non-free commercial license |
| PDF | WeasyPrint | ReportLab | Programmatic layout vs HTML templates; HTML templates reuse existing styling |
| PDF | WeasyPrint | Puppeteer/Chrome | Requires Chrome binary; heavy dependency for PDF |
| Excel | openpyxl | xlsxwriter | openpyxl reads AND writes; xlsxwriter is write-only |
| Desktop | PyWebView | Electron | 200MB+ runtime vs ~30MB; Python already needed for backend |
| 3D | Three.js | Babylon.js | Three.js is lighter, more examples for structural viz, larger community |

## Confidence Assessment

| Component | Confidence | Notes |
|-----------|------------|-------|
| Flask 3.1.3 | HIGH | Verified current on PyPI. Factory pattern well-documented |
| PyWebView 6.1 | HIGH | Verified current. Flask integration pattern well-established |
| AG Grid Community 35.2.0 | HIGH | Verified current on npm/CDN. Free MIT license confirmed |
| Three.js 0.183.x | HIGH | Verified current on npm. Active structural engineering use confirmed |
| openpyxl 3.1.5 | HIGH | Verified current on PyPI. Standard Excel library |
| WeasyPrint 62.x | MEDIUM | Active and well-documented. Note: has system-level dependencies (GTK/Pango on some platforms) that may complicate PyInstaller packaging |
| Vanilla JS approach | HIGH | Correct for handoff scenario. No framework debt |

## Sources

- [Flask PyPI](https://pypi.org/project/Flask/) -- version 3.1.3 confirmed
- [Flask Changelog](https://flask.palletsprojects.com/en/stable/changes/)
- [AG Grid Community npm](https://www.npmjs.com/package/ag-grid-community) -- version 35.2.0 confirmed
- [AG Grid JavaScript Installation](https://www.ag-grid.com/javascript-data-grid/installation/)
- [Three.js Releases](https://github.com/mrdoob/three.js/releases)
- [pywebview PyPI](https://pypi.org/project/pywebview/) -- version 6.1 confirmed
- [pywebview Flask Architecture](https://pywebview.flowrl.com/guide/architecture.html)
- [openpyxl PyPI](https://pypi.org/project/openpyxl/) -- version 3.1.5 confirmed
- [WeasyPrint](https://weasyprint.org/)
- [Flask Best Practices 2025](https://dev.to/gajanan0707/how-to-structure-a-large-flask-application-best-practices-for-2025-9j2)
- [pywebview + Flask Boilerplate](https://github.com/ClimenteA/pywebview-flask-boilerplate-for-python-desktop-apps)
