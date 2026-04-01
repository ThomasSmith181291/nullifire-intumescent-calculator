"""
Export service — Excel (Quantifire) and PDF report generation.
"""
import io
import os
from datetime import datetime

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side


NULLIFIRE_RED = 'E31937'
HEADER_FILL = PatternFill(start_color=NULLIFIRE_RED, end_color=NULLIFIRE_RED, fill_type='solid')
HEADER_FONT = Font(bold=True, color='FFFFFF', size=10)
DATA_FONT = Font(size=10)
THIN_BORDER = Border(
    left=Side(style='thin'), right=Side(style='thin'),
    top=Side(style='thin'), bottom=Side(style='thin')
)


def export_excel(project, members, product):
    """Export project to Excel workbook. Returns bytes."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Steel Schedule'

    # Project header
    ws.merge_cells('A1:L1')
    ws['A1'] = f'Nullifire Intumescent Specification — {project["name"]}'
    ws['A1'].font = Font(bold=True, size=14, color=NULLIFIRE_RED)

    ws['A2'] = f'Client: {project.get("client", "")}'
    ws['A3'] = f'Product: {product["name"] if product else "N/A"}'
    ws['A4'] = f'Date: {datetime.now().strftime("%d/%m/%Y")}'
    ws['A5'] = f'Reference: {project.get("reference", "")}'

    # Column headers
    headers = ['Section', 'Type', 'Exposure', 'Hp/A (m-1)', 'Fire Rating',
               'Temp (C)', 'DFT (mm)', 'DFT (um)', 'Qty', 'Length (m)',
               'Area (m2)', 'Litres', 'Zone', 'Level', 'Status']

    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=7, column=col, value=header)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal='center')
        cell.border = THIN_BORDER

    # Data rows
    for i, m in enumerate(members, 8):
        values = [
            m.get('section_name', ''),
            m.get('steel_type', ''),
            m.get('hp_profile_name', ''),
            m.get('hp_over_a'),
            '',  # fire rating description (would need lookup)
            '',  # failure temp description
            m.get('dft_mm'),
            round(m['dft_mm'] * 1000) if m.get('dft_mm') else None,
            m.get('quantity', 1),
            m.get('length_m', 0),
            m.get('surface_area_m2', 0),
            m.get('volume_litres', 0),
            m.get('zone', ''),
            m.get('level', ''),
            m.get('status', ''),
        ]
        for col, val in enumerate(values, 1):
            cell = ws.cell(row=i, column=col, value=val)
            cell.font = DATA_FONT
            cell.border = THIN_BORDER
            if isinstance(val, float):
                cell.number_format = '0.000' if col in (7,) else '0.00'

    # Summary row
    last_row = 8 + len(members)
    ws.cell(row=last_row + 1, column=1, value='TOTALS').font = Font(bold=True)
    ws.cell(row=last_row + 1, column=11, value=sum(m.get('surface_area_m2', 0) or 0 for m in members))
    ws.cell(row=last_row + 1, column=12, value=sum(m.get('volume_litres', 0) or 0 for m in members))

    # Column widths
    widths = [18, 6, 12, 8, 12, 8, 10, 10, 6, 10, 10, 10, 12, 10, 8]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()


def export_pdf_html(project, members, product, summary):
    """Generate HTML for PDF report. Returns HTML string.
    Note: WeasyPrint not included in POC — this generates printable HTML
    that can be opened in browser and printed to PDF."""
    total_litres = summary.get('total_litres', 0)
    total_kg = summary.get('total_kg', 0)
    total_area = summary.get('total_area_m2', 0)

    rows_html = ''
    for m in members:
        dft = m.get('dft_mm')
        dft_str = f'{dft:.3f} ({int(dft*1000)}um)' if dft else '—'
        status_color = {'ok': '#22c55e', 'warning': '#f59e0b', 'exceeds': '#ef4444'}.get(m.get('status', ''), '#9ca3af')
        rows_html += f'''<tr>
            <td>{m.get('section_name', '')}</td>
            <td>{m.get('steel_type', '')}</td>
            <td>{m.get('hp_profile_name', '')}</td>
            <td style="text-align:right">{int(m.get('hp_over_a', 0) or 0)}</td>
            <td style="text-align:right">{dft_str}</td>
            <td style="text-align:right">{m.get('quantity', 1)}</td>
            <td style="text-align:right">{m.get('length_m', 0):.2f}</td>
            <td style="text-align:right">{m.get('surface_area_m2', 0):.2f}</td>
            <td style="text-align:right">{m.get('volume_litres', 0):.2f}</td>
            <td>{m.get('zone', '')}</td>
            <td style="text-align:center"><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:{status_color}"></span></td>
        </tr>'''

    return f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<title>Nullifire Specification — {project["name"]}</title>
<style>
    body {{ font-family: Arial, sans-serif; font-size: 11px; color: #333; margin: 20px; }}
    .header {{ background: #E31937; color: white; padding: 16px 20px; margin: -20px -20px 20px; }}
    .header h1 {{ font-size: 18px; margin: 0; }}
    .meta {{ display: flex; gap: 40px; margin-bottom: 16px; }}
    .meta-item {{ }}
    .meta-label {{ font-size: 10px; color: #666; text-transform: uppercase; }}
    .meta-value {{ font-size: 13px; font-weight: bold; }}
    table {{ width: 100%; border-collapse: collapse; margin-bottom: 16px; }}
    th {{ background: #E31937; color: white; padding: 6px 8px; text-align: left; font-size: 10px; }}
    td {{ padding: 4px 8px; border-bottom: 1px solid #eee; font-size: 10px; }}
    tr:nth-child(even) {{ background: #f9f9f9; }}
    .totals {{ background: #f0f0f0; padding: 12px 16px; border-radius: 4px; display: flex; gap: 40px; }}
    .total-item {{ }}
    .total-label {{ font-size: 10px; color: #666; }}
    .total-value {{ font-size: 16px; font-weight: bold; }}
    .footer {{ margin-top: 20px; font-size: 9px; color: #999; border-top: 1px solid #ddd; padding-top: 8px; }}
    @media print {{ body {{ margin: 0; }} .header {{ margin: 0 0 20px; }} }}
</style></head><body>
<div class="header">
    <h1>Nullifire Intumescent Specification</h1>
</div>
<div class="meta">
    <div class="meta-item"><div class="meta-label">Project</div><div class="meta-value">{project["name"]}</div></div>
    <div class="meta-item"><div class="meta-label">Client</div><div class="meta-value">{project.get("client", "—")}</div></div>
    <div class="meta-item"><div class="meta-label">Product</div><div class="meta-value">{product["name"] if product else "—"}</div></div>
    <div class="meta-item"><div class="meta-label">Date</div><div class="meta-value">{datetime.now().strftime("%d/%m/%Y")}</div></div>
    <div class="meta-item"><div class="meta-label">Reference</div><div class="meta-value">{project.get("reference", "—")}</div></div>
</div>
<table>
<thead><tr>
    <th>Section</th><th>Type</th><th>Exposure</th><th>Hp/A</th><th>DFT</th>
    <th>Qty</th><th>Length</th><th>Area m2</th><th>Litres</th><th>Zone</th><th>Status</th>
</tr></thead>
<tbody>{rows_html}</tbody>
</table>
<div class="totals">
    <div class="total-item"><div class="total-label">Total Area</div><div class="total-value">{total_area:.1f} m2</div></div>
    <div class="total-item"><div class="total-label">Total Litres</div><div class="total-value">{total_litres:.1f} L</div></div>
    <div class="total-item"><div class="total-label">Total Weight</div><div class="total-value">{total_kg:.1f} kg</div></div>
    <div class="total-item"><div class="total-label">Members</div><div class="total-value">{len(members)}</div></div>
</div>
<div class="footer">
    Generated by Nullifire Intumescent Calculator | {datetime.now().strftime("%d/%m/%Y %H:%M")} | Tremco CPG
</div>
</body></html>'''
