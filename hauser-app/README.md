# Hauser Quoting MVP

Runnable local pilot for PDF upload, conservative text-label extraction, human quantity review, configurable pricing, and draft quotation exports.

## Run

Requires Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open **http://127.0.0.1:8000**. SQLite data and uploaded PDFs are stored in `data/` (ignored by Git). To override, set `HAUSER_DATA_DIR` to an absolute directory path.

## Test

```bash
pytest -q
```

## Workflow

1. Upload a PDF drawing (20 MB max).
2. Explicit text labels such as `Wall area: 120 m2`, `Floor area: 80 m2`, `Wall length: 50 m` are extracted as *candidates*.
3. Compare quantities against the PDF preview; fill missing values (including zeros), record notes, and approve.
4. The estimate uses editable rates, waste, contingency, fixed allowance, and VAT. The starting rates are **illustrative**, not Mayo-approved.
5. Export a draft quotation PDF or CSV only after approval.

## Calculation formula

- Line amount = reviewed quantity × rate
- Subtotal = sum of line amounts
- Waste = subtotal × waste percentage
- Contingency = subtotal × contingency percentage
- Net = subtotal + waste + contingency + fixed allowance
- VAT = net × VAT percentage
- Total = net + VAT

Rounding is to 2 decimal places at each subtotal component. Configure rates using the **Pricing rules** screen; new item keys must be lowercase letters, digits or underscores, starting with a letter. Editing rules recalculates all existing jobs, so exported quotes should be saved externally for an audit trail.

## Scope and limitations

- This is a **local MVP**, not production-ready. No authentication, multi-user access, audit log, backups, antivirus scanning, or access controls. Do not expose to the public internet or upload confidential customer drawings to a shared server.
- Only explicitly labelled values in selectable PDF text are extracted. No geometry/scale interpretation, wall recognition, automatic takeoff, OCR, scans, CAD/BIM, or roof/structural assessment.
- Ambiguous duplicate labels are flagged rather than automatically used. Every extracted value needs human verification.
- Rates and formula are placeholder defaults. Validate with Mayo's approved process and five pilot jobs (two held out for acceptance testing).
- The PDF export is a **draft**, not an approved customer quotation template. Currency setting is stored but the browser preview uses GBP formatting.
- No Salesforce or SharePoint integration, hosting, or AI credits included.

## Project structure

- `app/main.py` — FastAPI endpoints, SQLite, extraction, calculation, exports
- `app/static/index.html` — responsive browser UI
- `tests/test_app.py` — end-to-end API test
- `requirements.txt` — dependencies

## Next engineering milestones

1. Obtain 3 representative vector PDFs, exact fields, scale conventions and annotated ground truth.
2. Implement layout-specific vector geometry takeoff with traceable page coordinates and confidence flags.
3. Import approved rates/formulas, add versioned rate sheets and quote snapshots.
4. Add authentication, permissions, audit logs, deployment and acceptance tests against 2 reserved drawings.

## Expanded drawing intake (experimental)

The app now accepts vector PDFs, scanned PDFs, PNG/JPEG/TIFF images, DXF and IFC (IFC needs `pip install -r requirements-bim.txt`). Raster OCR uses **Tesseract OCR** installed on the operating system, plus `pytesseract`. If the Tesseract executable is absent, import succeeds with an OCR warning and manual review fields. DXF imports text and entity counts, not trustworthy measured quantities. IFC imports element counts, not quantities. **Native DWG and Revit RVT files are not supported**: export DXF or IFC from the source software first.

For pixel calibration use `POST /api/tools/pixel-scale` with JSON `{"measured_pixels": 300, "reference_pixels": 150, "reference_metres": 3}`. It returns 6 metres; this is a manual measurement helper, not automatic dimension detection or takeoff. Do not use uncalibrated pixel dimensions, image DPI, or title-block scales as substitutes for a verified reference. OCR labels are candidate values only.

Timber-frame-specific stud, plate, noggin, opening, panel, cassette and material rules are **not implemented** until the estimator supplies approved specifications and sample jobs. The current generic rates are illustrative. No live quotations without validation. Do not expose this unauthenticated local MVP to the public internet.

## Timber-frame specification library (new)

The MVP now includes four illustrative wall, floor and roof presets, editable layers, rates,
insulation descriptions, thickness and coverage parameters, timber spacing, sheet dimensions,
layer waste, project assignment snapshots, provisional material takeoff and approved BOM CSV.
Open a job and use **Timber-frame specifications & bill of materials**. Choose **Edit specification
library** to duplicate a preset and tailor it without changing existing job assignments.

API endpoints: `GET/POST /api/assemblies`, `PUT /api/assemblies/{id}`,
`POST /api/assemblies/{id}/duplicate`, `GET/POST /api/jobs/{id}/assemblies`,
`DELETE /api/jobs/{id}/assemblies/{assignment_id}`, `GET /api/jobs/{id}/bom`,
`GET /api/jobs/{id}/bom.csv`.

**Important:** the material BOM is separate from the original area-rate quotation estimate
and is **not automatically included** in its total, avoiding accidental double charging.
The BOM is provisional, and the current linear timber calculation is a simplified
rectangular takeoff, not a structural or manufacturing cut list. Openings, lintels,
plates, roof pitch, panelization, thermal bridging and approved fabrication rules
still require real project examples and validation.

## Estimator Review Workspace (new prototype)

Run `uvicorn app.main:app --reload` from the `hauser-mvp` directory and open **http://127.0.0.1:8000/review**.

This is a functional, **sample-data** review workspace. Select individual framing members or the opening in an interactive 2D elevation, log issues with comments, propose exact numeric changes to the window, apply or close issues, review the revision history, approve geometry and specifications in sequence, generate a **provisional** 1D timber cutting plan and export a lightweight **GLB** of the illustrative framing. The new API routes are under `/api/review/demo`.

**Important limitations:** This demonstration does not import a drawing into the review model, parse natural-language corrections into geometry, determine engineered lintel sizes, create structurally approved framing, optimise OSB sheets or insulation, or calculate a complete kit quotation. The cutting planner uses a first-fit-decreasing heuristic and is not mathematically guaranteed optimal. OSB quantity is only an area lower bound. Estimate approval is intentionally blocked pending structural verification and full kit costing. The older `/api/jobs` quotation workflow remains separate; this review prototype does not imply that legacy approvals are safe to use for manufacturing.
