"""Hauser quoting MVP. All amounts and extracted quantities require human review."""
import csv
import io
import json
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from .importers import process, pixels_to_metres
from .assemblies import PRESETS, validate_assembly, takeoff
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE = Path(__file__).resolve().parent.parent
DATA = Path(os.getenv("HAUSER_DATA_DIR", str(BASE / "data")))
UPLOADS = DATA / "uploads"
DB = DATA / "hauser.sqlite3"
DEFAULT_RULES = {
    "currency": "GBP",
    "vat_percent": 20,
    "waste_percent": 5,
    "contingency_percent": 0,
    "fixed_allowance": 0,
    "items": [
        {"key": "wall_area_m2", "label": "Wall area", "unit": "m²", "rate": 45},
        {"key": "floor_area_m2", "label": "Floor area", "unit": "m²", "rate": 35},
        {"key": "wall_length_m", "label": "Wall length", "unit": "m", "rate": 0},
    ],
}

app = FastAPI(title="Hauser Quoting MVP", version="0.1.0")
app.mount("/static", StaticFiles(directory=BASE / "app" / "static"), name="static")


def conn():
    DATA.mkdir(parents=True, exist_ok=True)
    UPLOADS.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, filename TEXT NOT NULL,
            created_at TEXT NOT NULL, status TEXT NOT NULL,
            extraction TEXT NOT NULL, quantities TEXT NOT NULL,
            notes TEXT NOT NULL DEFAULT '', approved INTEGER NOT NULL DEFAULT 0
        )""")
        c.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        c.execute("CREATE TABLE IF NOT EXISTS assemblies (id TEXT PRIMARY KEY, value TEXT NOT NULL)")
        c.execute("CREATE TABLE IF NOT EXISTS job_assemblies (job_id TEXT NOT NULL, assignment_id TEXT NOT NULL, value TEXT NOT NULL, PRIMARY KEY(job_id,assignment_id))")
        for preset in PRESETS:
            c.execute("INSERT OR IGNORE INTO assemblies VALUES (?,?)", (preset['id'], json.dumps(preset)))
        c.execute("INSERT OR IGNORE INTO settings VALUES ('rules', ?)", (json.dumps(DEFAULT_RULES),))


init_db()


class ScaleRequest(BaseModel):
    measured_pixels: float = Field(gt=0)
    reference_pixels: float = Field(gt=0)
    reference_metres: float = Field(gt=0)


@app.post("/api/tools/pixel-scale")
def pixel_scale(payload: ScaleRequest):
    return {"metres": round(pixels_to_metres(payload.measured_pixels, payload.reference_pixels, payload.reference_metres), 6), "review_required": True}


class JobUpdate(BaseModel):
    quantities: dict[str, float] = Field(default_factory=dict)
    notes: str = ""
    approved: bool = False


class RulesUpdate(BaseModel):
    currency: str = "GBP"
    vat_percent: float = Field(ge=0, le=100)
    waste_percent: float = Field(ge=0, le=100)
    contingency_percent: float = Field(ge=0, le=100)
    fixed_allowance: float = Field(ge=0)
    items: list[dict[str, Any]]


def rules():
    with conn() as c:
        return json.loads(c.execute("SELECT value FROM settings WHERE key='rules'").fetchone()[0])


def get_job(job_id: str):
    with conn() as c:
        row = c.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Job not found")
    job = dict(row)
    job["extraction"] = json.loads(job["extraction"])
    job["quantities"] = json.loads(job["quantities"])
    job["approved"] = bool(job["approved"])
    return job


def extract_pdf(data: bytes):
    """Conservative text-based candidates only. No inferred geometry or scale."""
    try:
        import fitz
        doc = fitz.open(stream=data, filetype="pdf")
        if doc.is_encrypted:
            raise ValueError("Encrypted PDFs are not supported")
        pages = len(doc)
        text = "\n".join(page.get_text(sort=True) for page in doc)
        doc.close()
    except Exception as exc:
        raise HTTPException(422, f"Cannot read PDF: {exc}") from exc
    patterns = {
        "wall_area_m2": r"(?:total\s+)?wall\s+area\s*[:=]?\s*([\d,]+(?:\.\d+)?)\s*(?:m2|m²|sqm)\b",
        "floor_area_m2": r"(?:total\s+)?floor\s+area\s*[:=]?\s*([\d,]+(?:\.\d+)?)\s*(?:m2|m²|sqm)\b",
        "wall_length_m": r"(?:total\s+)?wall\s+length\s*[:=]?\s*([\d,]+(?:\.\d+)?)\s*(?:m|metres|meters)\b",
    }
    candidates = {}
    warnings = []
    for key, pattern in patterns.items():
        matches = re.findall(pattern, text, flags=re.I)
        if len(matches) == 1:
            candidates[key] = float(matches[0].replace(",", ""))
        elif len(matches) > 1:
            warnings.append(f"Multiple {key} labels found; enter a reviewed value manually")
        else:
            warnings.append(f"No explicit {key} label found; enter a reviewed value manually")
    if not text.strip():
        warnings.append("No selectable text detected; scanned PDFs are outside MVP extraction scope")
    warnings.append("All candidate quantities must be reviewed; drawing geometry is not measured automatically")
    return {"pages": pages, "text_preview": text[:2000], "candidates": candidates, "warnings": warnings}


def estimate(job):
    r = rules()
    q = job["quantities"]
    lines = []
    subtotal = 0.0
    for item in r["items"]:
        key = item["key"]
        qty = float(q.get(key, 0))
        rate = float(item["rate"])
        amount = round(qty * rate, 2)
        lines.append({"key": key, "label": item["label"], "unit": item["unit"], "quantity": qty, "rate": rate, "amount": amount})
        subtotal += amount
    subtotal = round(subtotal, 2)
    waste = round(subtotal * r["waste_percent"] / 100, 2)
    contingency = round(subtotal * r["contingency_percent"] / 100, 2)
    allowance = round(float(r["fixed_allowance"]), 2)
    net = round(subtotal + waste + contingency + allowance, 2)
    vat = round(net * r["vat_percent"] / 100, 2)
    return {"currency": r["currency"], "lines": lines, "subtotal": subtotal, "waste": waste, "contingency": contingency, "fixed_allowance": allowance, "net": net, "vat": vat, "total": round(net + vat, 2), "rules": r, "approved": job["approved"]}


@app.get("/")
def index():
    return FileResponse(BASE / "app" / "static" / "index.html")


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/rules")
def get_rules():
    return rules()


@app.put("/api/rules")
def put_rules(payload: RulesUpdate):
    r = payload.model_dump()
    if not r["items"] or len(r["items"]) > 50:
        raise HTTPException(422, "Specify 1–50 rate items")
    keys = []
    for item in r["items"]:
        if not all(k in item for k in ("key", "label", "unit", "rate")):
            raise HTTPException(422, "Each item needs key, label, unit and rate")
        if not isinstance(item["key"], str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,49}", item["key"]):
            raise HTTPException(422, "Invalid item key")
        if not isinstance(item["rate"], (int, float)) or not 0 <= item["rate"] <= 1e9:
            raise HTTPException(422, "Invalid rate")
        keys.append(item["key"])
    if len(set(keys)) != len(keys):
        raise HTTPException(422, "Duplicate item keys")
    with conn() as c:
        c.execute("UPDATE settings SET value=? WHERE key='rules'", (json.dumps(r),))
    return r


@app.get("/api/jobs")
def jobs():
    with conn() as c:
        rows = c.execute("SELECT id,name,filename,created_at,status,approved FROM jobs ORDER BY created_at DESC").fetchall()
    return [dict(row) for row in rows]


@app.post("/api/jobs", status_code=201)
async def create_job(file: UploadFile = File(...)):
    filename = Path(file.filename or "drawing.pdf").name
    if Path(filename).suffix.lower() not in {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".dxf", ".ifc"}:
        raise HTTPException(400, "Supported: PDF, PNG, JPG, TIFF, DXF, IFC. Convert DWG/RVT externally")
    data = await file.read(20 * 1024 * 1024 + 1)
    if len(data) > 20 * 1024 * 1024:
        raise HTTPException(413, "PDF exceeds 20 MB")
    if filename.lower().endswith(".pdf") and not data.startswith(b"%PDF-"):
        raise HTTPException(400, "Not a PDF file")
    try:
        extraction = process(data, filename)
    except Exception as exc:
        raise HTTPException(422, f"Import failed: {exc}") from exc
    job_id = str(uuid.uuid4())
    (UPLOADS / f"{job_id}{Path(filename).suffix.lower()}").write_bytes(data)
    with conn() as c:
        c.execute("INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?)", (
            job_id, Path(filename).stem, filename, datetime.now(timezone.utc).isoformat(),
            "needs_review", json.dumps(extraction), json.dumps(extraction["candidates"]), "", 0
        ))
    return get_job(job_id)


@app.get("/api/jobs/{job_id}")
def job_detail(job_id: str):
    job = get_job(job_id)
    job["estimate"] = estimate(job)
    return job


@app.put("/api/jobs/{job_id}")
def update_job(job_id: str, payload: JobUpdate):
    get_job(job_id)
    allowed = {item["key"] for item in rules()["items"]}
    if any(k not in allowed or v < 0 or v > 1e9 for k, v in payload.quantities.items()):
        raise HTTPException(422, "Invalid quantity or unknown field")
    if payload.approved and any(k not in payload.quantities for k in allowed):
        raise HTTPException(422, "Enter every configured quantity, including zeros, before approval")
    with conn() as c:
        c.execute("UPDATE jobs SET quantities=?,notes=?,approved=?,status=? WHERE id=?", (
            json.dumps(payload.quantities), payload.notes[:4000], int(payload.approved),
            "approved" if payload.approved else "needs_review", job_id
        ))
    return job_detail(job_id)


@app.get("/api/jobs/{job_id}/drawing")
def drawing(job_id: str):
    get_job(job_id)
    from mimetypes import guess_type
    path = UPLOADS / f"{job_id}{Path(get_job(job_id)['filename']).suffix.lower()}"
    return FileResponse(path, media_type=guess_type(str(path))[0] or "application/octet-stream", headers={"Content-Disposition": "inline"})


@app.get("/api/jobs/{job_id}/export.csv")
def export_csv(job_id: str):
    job = get_job(job_id)
    if not job["approved"]:
        raise HTTPException(409, "Approve quantities before exporting")
    est = estimate(job)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Hauser quotation", job["name"]])
    writer.writerow(["Item", "Quantity", "Unit", "Rate", "Amount"])
    for line in est["lines"]:
        writer.writerow([line["label"], line["quantity"], line["unit"], line["rate"], line["amount"]])
    for key in ("subtotal", "waste", "contingency", "fixed_allowance", "net", "vat", "total"):
        writer.writerow([key, "", "", "", est[key]])
    return Response(output.getvalue(), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="hauser-{job_id[:8]}.csv"'})


@app.get("/api/jobs/{job_id}/export.pdf")
def export_pdf(job_id: str):
    job = get_job(job_id)
    if not job["approved"]:
        raise HTTPException(409, "Approve quantities before exporting")
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from xml.sax.saxutils import escape
    est = estimate(job)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=40, rightMargin=40)
    styles = getSampleStyleSheet()
    story = [Paragraph("HAUSER | DRAFT QUOTATION", styles["Title"]), Spacer(1, 12),
             Paragraph(f"Job: {escape(job['name'])}", styles["Normal"]),
             Paragraph(f"Source: {escape(job['filename'])}", styles["Normal"]), Spacer(1, 14)]
    rows = [["Description", "Quantity", "Rate", "Amount"]]
    for line in est["lines"]:
        rows.append([line["label"], f"{line['quantity']:,.2f} {line['unit']}", f"{line['rate']:,.2f}", f"{line['amount']:,.2f}"])
    for key, label in (("subtotal", "Subtotal"), ("waste", "Waste"), ("contingency", "Contingency"), ("fixed_allowance", "Allowance"), ("net", "Net"), ("vat", "VAT"), ("total", "TOTAL")):
        rows.append([label, "", "", f"{est[key]:,.2f}"])
    table = Table(rows, colWidths=[205, 110, 90, 100], repeatRows=1)
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#172b36")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f6f7")]), ("BOTTOMPADDING", (0, 0), (-1, -1), 9), ("TOPPADDING", (0, 0), (-1, -1), 9), ("ALIGN", (1, 0), (-1, -1), "RIGHT")]))
    story += [table, Spacer(1, 16), Paragraph(f"Currency: {escape(est['currency'])}. Rates and calculations are provisional pending client approval.", styles["Normal"]), Paragraph("Not a structural assessment. Review all quantities and scope before issue.", styles["Normal"])]
    if job["notes"]:
        story.append(Paragraph("Review notes: " + escape(job["notes"]), styles["Normal"]))
    doc.build(story)
    return Response(buffer.getvalue(), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="hauser-{job_id[:8]}.pdf"'})


class AssemblyPayload(BaseModel):
    name: str
    category: str
    description: str = ""
    layers: list[dict[str, Any]]

class AssignmentPayload(BaseModel):
    assembly_id: str
    area_m2: float = Field(default=0, ge=0)
    length_m: float = Field(default=0, ge=0)
    height_m: float = Field(default=2.4, gt=0)
    override: dict[str, Any] | None = None

@app.get("/api/assemblies")
def list_assemblies():
    with conn() as c:
        return [json.loads(row['value']) for row in c.execute("SELECT value FROM assemblies ORDER BY id")]

@app.post("/api/assemblies", status_code=201)
def create_assembly(payload: AssemblyPayload):
    a=validate_assembly({'id':str(uuid.uuid4()),**payload.model_dump()})
    with conn() as c:
        c.execute("INSERT INTO assemblies VALUES (?,?)",(a['id'],json.dumps(a)))
    return a

@app.put("/api/assemblies/{assembly_id}")
def update_assembly(assembly_id: str,payload: AssemblyPayload):
    a=validate_assembly({'id':assembly_id,**payload.model_dump()})
    with conn() as c:
        if not c.execute("SELECT 1 FROM assemblies WHERE id=?",(assembly_id,)).fetchone():
            raise HTTPException(404,'Assembly not found')
        c.execute("UPDATE assemblies SET value=? WHERE id=?",(json.dumps(a),assembly_id))
    return a

@app.post("/api/assemblies/{assembly_id}/duplicate",status_code=201)
def duplicate_assembly(assembly_id: str):
    with conn() as c:
        row=c.execute("SELECT value FROM assemblies WHERE id=?",(assembly_id,)).fetchone()
        if not row: raise HTTPException(404,'Assembly not found')
        a=json.loads(row['value']); a['id']=str(uuid.uuid4());a['name']+=' (copy)'
        c.execute("INSERT INTO assemblies VALUES (?,?)",(a['id'],json.dumps(a)))
    return a

@app.get("/api/jobs/{job_id}/assemblies")
def list_assignments(job_id: str):
    get_job(job_id)
    with conn() as c:
        rows=c.execute("SELECT value FROM job_assemblies WHERE job_id=? ORDER BY assignment_id",(job_id,)).fetchall()
    return [json.loads(r['value']) for r in rows]

@app.post("/api/jobs/{job_id}/assemblies",status_code=201)
def assign_assembly(job_id: str,payload: AssignmentPayload):
    get_job(job_id)
    with conn() as c:
        row=c.execute("SELECT value FROM assemblies WHERE id=?",(payload.assembly_id,)).fetchone()
        if not row: raise HTTPException(404,'Assembly not found')
        assembly=json.loads(row['value'])
        if payload.override is not None:
            assembly=validate_assembly({'id':assembly['id'],**payload.override})
        geometry={'area_m2':payload.area_m2,'length_m':payload.length_m,'height_m':payload.height_m}
        result=takeoff(assembly,geometry)
        assignment={'id':str(uuid.uuid4()),'source_assembly_id':payload.assembly_id,'assembly_snapshot':assembly,'geometry':geometry,'takeoff':result}
        c.execute("INSERT INTO job_assemblies VALUES (?,?,?)",(job_id,assignment['id'],json.dumps(assignment)))
        c.execute("UPDATE jobs SET approved=0,status='needs_review' WHERE id=?",(job_id,))
    return assignment

@app.delete("/api/jobs/{job_id}/assemblies/{assignment_id}")
def remove_assignment(job_id: str,assignment_id: str):
    get_job(job_id)
    with conn() as c:
        cur=c.execute("DELETE FROM job_assemblies WHERE job_id=? AND assignment_id=?",(job_id,assignment_id))
        if not cur.rowcount: raise HTTPException(404,'Assignment not found')
        c.execute("UPDATE jobs SET approved=0,status='needs_review' WHERE id=?",(job_id,))
    return {'deleted':True}

@app.get("/api/jobs/{job_id}/bom")
def bill_of_materials(job_id: str):
    assignments=list_assignments(job_id)
    lines=[]
    for a in assignments:
        for l in a['takeoff']['lines']:
            lines.append({'assignment_id':a['id'],'assembly':a['assembly_snapshot']['name'],**l})
    return {'job_id':job_id,'lines':lines,'subtotal':round(sum(l['amount'] for l in lines),2),'provisional':True,'assignments':len(assignments)}

@app.get("/api/jobs/{job_id}/bom.csv")
def export_bom(job_id: str):
    if not get_job(job_id)['approved']: raise HTTPException(409,'Approve the job before exporting the BOM')
    bom=bill_of_materials(job_id)
    output=io.StringIO();writer=csv.writer(output)
    writer.writerow(['Assembly','Material','Net quantity','Order quantity','Unit','Rate GBP','Amount GBP'])
    for l in bom['lines']:
        writer.writerow([l['assembly'],l['name'],l['net_quantity'],l['order_quantity'],l['unit'],l['rate'],l['amount']])
    writer.writerow(['','TOTAL','','','','',bom['subtotal']])
    return Response(output.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="hauser-bom.csv"'})

# Estimator-controlled review prototype (separate from legacy quote approvals).
from .review import router as review_router
app.include_router(review_router)

@app.get('/review')
def review_page():
    return FileResponse(BASE / 'app' / 'static' / 'review.html')
