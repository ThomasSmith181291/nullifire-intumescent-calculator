"""
Export service — Professional branded Excel and PDF/HTML reports.
Follows Nullifire brand guidelines and BEEDS professional output patterns.
"""
import io
from datetime import datetime

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, numbers
from openpyxl.utils import get_column_letter

# ── Nullifire Brand Constants ──
NF_RED = 'E6332A'
NF_NAVY = '1E3480'
NF_NAVY_LT = '2A4399'
DARK_GREY = '333333'
MID_GREY = '666666'
LIGHT_GREY = 'F2F2F7'
ALT_ROW = 'F8F8FB'
WHITE = 'FFFFFF'
STATUS_GREEN = '10B981'
STATUS_AMBER = 'F59E0B'
STATUS_RED = 'EF4444'

# Styles
THIN_BORDER = Border(
    left=Side(style='thin', color=NF_NAVY),
    right=Side(style='thin', color=NF_NAVY),
    top=Side(style='thin', color=NF_NAVY),
    bottom=Side(style='thin', color=NF_NAVY),
)
BOTTOM_BORDER = Border(bottom=Side(style='medium', color=NF_RED))


def _style_header_cell(cell):
    cell.font = Font(name='Calibri', bold=True, color=WHITE, size=10)
    cell.fill = PatternFill(start_color=NF_NAVY, end_color=NF_NAVY, fill_type='solid')
    cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    cell.border = THIN_BORDER


def _style_data_cell(cell, row_idx, is_number=False):
    cell.font = Font(name='Calibri', size=10, color=DARK_GREY)
    bg = ALT_ROW if row_idx % 2 == 0 else WHITE
    cell.fill = PatternFill(start_color=bg, end_color=bg, fill_type='solid')
    cell.alignment = Alignment(horizontal='right' if is_number else 'left', vertical='center')
    cell.border = Border(
        bottom=Side(style='hair', color='D0D0D0'),
        left=Side(style='hair', color='E0E0E0'),
        right=Side(style='hair', color='E0E0E0'),
    )


def _style_total_cell(cell, is_label=False):
    cell.font = Font(name='Calibri', bold=True, size=11, color=NF_NAVY)
    cell.fill = PatternFill(start_color=LIGHT_GREY, end_color=LIGHT_GREY, fill_type='solid')
    cell.alignment = Alignment(horizontal='left' if is_label else 'right', vertical='center')
    cell.border = Border(
        top=Side(style='medium', color=NF_NAVY),
        bottom=Side(style='medium', color=NF_NAVY),
    )


def export_excel(project, members, product):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Specification'
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.orientation = 'landscape'
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_margins.left = 0.4
    ws.page_margins.right = 0.4
    ws.page_margins.top = 0.5
    ws.page_margins.bottom = 0.5

    # ── Header Section ──
    # Title
    ws.merge_cells('A1:O1')
    title_cell = ws['A1']
    title_cell.value = 'NULLIFIRE INTUMESCENT SPECIFICATION'
    title_cell.font = Font(name='Calibri', bold=True, size=18, color=NF_NAVY)
    title_cell.alignment = Alignment(vertical='center')
    ws.row_dimensions[1].height = 32

    # Red accent bar
    ws.merge_cells('A2:O2')
    accent = ws['A2']
    accent.fill = PatternFill(start_color=NF_RED, end_color=NF_RED, fill_type='solid')
    ws.row_dimensions[2].height = 4

    # Project details - 2 column layout
    details = [
        ('Project:', project.get('name', ''), 'Client:', project.get('client', '')),
        ('Product:', product['name'] if product else 'N/A', 'Date:', datetime.now().strftime('%d %B %Y')),
        ('Reference:', project.get('reference', ''), 'Members:', str(len(members))),
    ]

    row = 4
    for label1, val1, label2, val2 in details:
        for col, (label, val) in enumerate([(label1, val1), (label2, val2)]):
            lc = 1 + col * 4  # A or E
            vc = lc + 1
            cell_l = ws.cell(row=row, column=lc, value=label)
            cell_l.font = Font(name='Calibri', bold=True, size=10, color=NF_NAVY)
            cell_l.alignment = Alignment(horizontal='right', vertical='center')
            cell_v = ws.cell(row=row, column=vc, value=val)
            cell_v.font = Font(name='Calibri', size=10, color=DARK_GREY)
            cell_v.alignment = Alignment(vertical='center')
            ws.merge_cells(start_row=row, start_column=vc, end_row=row, end_column=vc + 1)
        row += 1

    # ── Column Headers ──
    row += 1
    headers = [
        ('Section', 18), ('Type', 7), ('Exposure', 9), ('Hp/A', 7),
        ('Fire Rating', 12), ('Temp', 8), ('Product', 14),
        ('DFT (mm)', 10), ('DFT (µm)', 9),
        ('Qty', 5), ('Length (m)', 10),
        ('Area (m²)', 10), ('Litres', 8), ('Weight (kg)', 10),
        ('Status', 8),
    ]

    header_row = row
    for col, (name, width) in enumerate(headers, 1):
        cell = ws.cell(row=header_row, column=col, value=name)
        _style_header_cell(cell)
        ws.column_dimensions[get_column_letter(col)].width = width
    ws.row_dimensions[header_row].height = 24

    # ── Data Rows ──
    for i, m in enumerate(members):
        r = header_row + 1 + i
        dft = m.get('dft_mm')
        status = m.get('status', '')

        values = [
            (m.get('section_name', ''), False),
            (m.get('steel_type', ''), False),
            (m.get('hp_profile_name', ''), False),
            (round(m['hp_over_a']) if m.get('hp_over_a') else None, True),
            ('', False),  # fire rating description would need lookup
            ('', False),  # failure temp description
            ('', False),  # product name
            (dft, True),
            (round(dft * 1000) if dft else None, True),
            (m.get('quantity', 1), True),
            (m.get('length_m', 0), True),
            (m.get('surface_area_m2', 0), True),
            (m.get('volume_litres', 0), True),
            (m.get('weight_kg', 0), True),
            (status.upper() if status else '', False),
        ]

        for col, (val, is_num) in enumerate(values, 1):
            cell = ws.cell(row=r, column=col, value=val)
            _style_data_cell(cell, i, is_num)
            if col == 8 and val:  # DFT mm
                cell.number_format = '0.000'
            elif col in (11, 12) and val:  # Length, Area
                cell.number_format = '0.00'
            elif col in (13, 14) and val:  # Litres, Weight
                cell.number_format = '0.00'

        # Color the status cell
        status_cell = ws.cell(row=r, column=15)
        color_map = {'ok': STATUS_GREEN, 'warning': STATUS_AMBER, 'exceeds': STATUS_RED}
        if status in color_map:
            status_cell.font = Font(name='Calibri', bold=True, size=10, color=color_map[status])

    # ── Totals Row ──
    total_row = header_row + 1 + len(members)
    ws.merge_cells(start_row=total_row, start_column=1, end_row=total_row, end_column=11)
    total_label = ws.cell(row=total_row, column=1, value='TOTALS')
    _style_total_cell(total_label, is_label=True)

    for col in range(2, 12):
        _style_total_cell(ws.cell(row=total_row, column=col))

    total_area = ws.cell(row=total_row, column=12, value=sum(m.get('surface_area_m2', 0) or 0 for m in members))
    total_area.number_format = '0.00'
    _style_total_cell(total_area)

    total_litres = ws.cell(row=total_row, column=13, value=sum(m.get('volume_litres', 0) or 0 for m in members))
    total_litres.number_format = '0.00'
    _style_total_cell(total_litres)

    total_weight = ws.cell(row=total_row, column=14, value=sum(m.get('weight_kg', 0) or 0 for m in members))
    total_weight.number_format = '0.00'
    _style_total_cell(total_weight)

    _style_total_cell(ws.cell(row=total_row, column=15))

    # ── Footer ──
    footer_row = total_row + 2
    ws.merge_cells(start_row=footer_row, start_column=1, end_row=footer_row, end_column=15)
    footer = ws.cell(row=footer_row, column=1,
                     value=f'Tremco CPG UK Limited  |  Generated {datetime.now().strftime("%d/%m/%Y %H:%M")}  |  Nullifire Intumescent Calculator')
    footer.font = Font(name='Calibri', size=8, color=MID_GREY, italic=True)
    footer.alignment = Alignment(horizontal='center')

    # Freeze panes at header
    ws.freeze_panes = ws.cell(row=header_row + 1, column=1)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()


def export_pdf_html(project, members, product, summary):
    total_litres = summary.get('total_litres', 0)
    total_kg = summary.get('total_kg', 0)
    total_area = summary.get('total_area_m2', 0)

    rows_html = ''
    for i, m in enumerate(members):
        dft = m.get('dft_mm')
        dft_str = f'{dft:.3f} mm ({int(dft*1000)} &micro;m)' if dft else '&mdash;'
        status = m.get('status', '')
        status_colors = {'ok': '#10b981', 'warning': '#f59e0b', 'exceeds': '#ef4444'}
        sc = status_colors.get(status, '#9ca3af')
        bg = '#f8f8fb' if i % 2 == 0 else '#ffffff'

        rows_html += f'''<tr style="background:{bg}">
            <td>{m.get('section_name','')}</td>
            <td>{m.get('steel_type','')}</td>
            <td>{m.get('hp_profile_name','')}</td>
            <td class="r">{int(m.get('hp_over_a',0) or 0)}</td>
            <td class="r">{dft_str}</td>
            <td class="r">{m.get('quantity',1)}</td>
            <td class="r">{m.get('length_m',0):.2f}</td>
            <td class="r">{m.get('surface_area_m2',0):.2f}</td>
            <td class="r">{m.get('volume_litres',0):.2f}</td>
            <td class="r">{m.get('weight_kg',0):.1f}</td>
            <td style="text-align:center"><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:{sc}"></span></td>
        </tr>'''

    return f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<title>Nullifire Specification &mdash; {project["name"]}</title>
<style>
    @page {{ size: A4 landscape; margin: 15mm; }}
    body {{ font-family: Calibri, 'Segoe UI', Arial, sans-serif; font-size: 10px; color: #333; margin: 0; padding: 20px; }}

    .header-bar {{ background: #1E3480; color: white; padding: 16px 24px; margin: -20px -20px 0; display: flex; align-items: center; justify-content: space-between; }}
    .header-bar h1 {{ font-size: 18px; font-weight: 700; letter-spacing: 1px; margin: 0; }}
    .header-bar .subtitle {{ font-size: 11px; opacity: 0.7; }}

    .accent-bar {{ height: 4px; background: #E6332A; margin: 0 -20px 16px; }}

    .meta {{ display: flex; gap: 40px; margin-bottom: 14px; padding: 0 4px; }}
    .meta-item {{ }}
    .meta-label {{ font-size: 9px; color: #666; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 700; }}
    .meta-value {{ font-size: 13px; font-weight: 600; color: #1E3480; }}

    table {{ width: 100%; border-collapse: collapse; margin-bottom: 12px; }}
    th {{ background: #1E3480; color: white; padding: 6px 8px; text-align: left; font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.3px; }}
    td {{ padding: 4px 8px; border-bottom: 1px solid #e8e8ee; font-size: 10px; }}
    .r {{ text-align: right; }}

    .totals {{ background: #f2f2f7; padding: 12px 16px; border-radius: 6px; display: flex; gap: 40px; border-top: 3px solid #1E3480; }}
    .total-item {{ }}
    .total-label {{ font-size: 9px; color: #666; text-transform: uppercase; font-weight: 700; }}
    .total-value {{ font-size: 18px; font-weight: 800; color: #E6332A; }}

    .footer {{ margin-top: 16px; font-size: 8px; color: #999; border-top: 2px solid #E6332A; padding-top: 8px; text-align: center; }}
    .footer b {{ color: #1E3480; }}

    @media print {{
        body {{ margin: 0; padding: 10px; }}
        .header-bar {{ margin: -10px -10px 0; }}
        .accent-bar {{ margin: 0 -10px 12px; }}
    }}
</style></head><body>

<div class="header-bar">
    <div>
        <h1>NULLIFIRE INTUMESCENT SPECIFICATION</h1>
        <div class="subtitle">Structural Steel Fire Protection</div>
    </div>
    <div style="text-align:right;font-size:10px">
        <div style="font-weight:700">Tremco CPG UK Limited</div>
        <div style="opacity:0.7;font-size:9px">protect@nullifire.com | www.nullifire.com</div>
    </div>
</div>
<div class="accent-bar"></div>

<div class="meta">
    <div class="meta-item"><div class="meta-label">Project</div><div class="meta-value">{project["name"]}</div></div>
    <div class="meta-item"><div class="meta-label">Client</div><div class="meta-value">{project.get("client","&mdash;")}</div></div>
    <div class="meta-item"><div class="meta-label">Product</div><div class="meta-value">{product["name"] if product else "&mdash;"}</div></div>
    <div class="meta-item"><div class="meta-label">Date</div><div class="meta-value">{datetime.now().strftime("%d %B %Y")}</div></div>
    <div class="meta-item"><div class="meta-label">Members</div><div class="meta-value">{len(members)}</div></div>
</div>

<table>
<thead><tr>
    <th>Section</th><th>Type</th><th>Exposure</th><th style="text-align:right">Hp/A</th><th style="text-align:right">DFT</th>
    <th style="text-align:right">Qty</th><th style="text-align:right">Length</th><th style="text-align:right">Area m&sup2;</th>
    <th style="text-align:right">Litres</th><th style="text-align:right">Weight kg</th><th>Status</th>
</tr></thead>
<tbody>{rows_html}</tbody>
</table>

<div class="totals">
    <div class="total-item"><div class="total-label">Total Area</div><div class="total-value">{total_area:.1f} m&sup2;</div></div>
    <div class="total-item"><div class="total-label">Total Litres</div><div class="total-value">{total_litres:.1f} L</div></div>
    <div class="total-item"><div class="total-label">Total Weight</div><div class="total-value">{total_kg:.1f} kg</div></div>
    <div class="total-item"><div class="total-label">Members</div><div class="total-value">{len(members)}</div></div>
</div>

<div class="footer">
    <b>Tremco CPG UK Limited</b> &nbsp;|&nbsp; Torrington Avenue, Coventry, CV4 9TJ &nbsp;|&nbsp; protect@nullifire.com &nbsp;|&nbsp; www.nullifire.com<br>
    Generated {datetime.now().strftime("%d/%m/%Y %H:%M")} &nbsp;|&nbsp; Nullifire Intumescent Calculator
</div>

</body></html>'''
