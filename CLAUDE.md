<!-- GSD:project-start source:PROJECT.md -->
## Project

**Nullifire Intumescent Calculator**

A modern intumescent coating specification tool for Nullifire products that replaces the legacy Steelcalc VB.NET application. Users — both sales/technical reps and contractors — can rapidly specify DFT coatings for structural steel members, verify compliance, and export specifications for Quantifire. Includes a 3D structural grid preview that builds as members are added.

**Core Value:** Fast, component-by-component steel member input with instant DFT verification — what takes dozens of clicks in Steelcalc should take seconds here.

### Constraints

- **Architecture**: Python backend (Flask API) + HTML/CSS/JS frontend + PyWebView desktop wrapper — chosen so UI transfers directly to web app
- **No costing**: This is a specification tool, not a costing tool — Quantifire handles that downstream
- **Nullifire only**: Only Nullifire products (SupplierID=4) — not multi-supplier like Steelcalc
- **Data**: SQLite for POC — PostgreSQL for web app migration
- **3D Library**: Three.js (WebGL) — runs in browser, transfers to web app
- **Branding**: Nullifire brand colors (red/dark grey/white)
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

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
## Frontend Architecture (No Build Step)
## Flask API Architecture
## PyWebView Integration Pattern
- Flask runs in a daemon thread, PyWebView owns the main thread (GUI loop)
- `ready_event` ensures window doesn't open before Flask is serving
- `use_reloader=False` required -- reloader spawns processes that conflict with PyWebView
- No CSRF needed for desktop-only (localhost), but Flask-CORS needed for cross-origin fetch from PyWebView's webview context
## Three.js Integration Pattern for Structural Steel
## Installation
# Create virtual environment
# Core
# Data processing
# Development
# Packaging (when ready)
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
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
