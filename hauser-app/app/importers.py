"""Conservative multi-format import. Candidates are never approved automatically."""
import io
import re
from pathlib import Path

LABELS = {
    'wall_area_m2': r'(?:total\s+)?wall\s+area\s*[:=]?\s*([\d,]+(?:\.\d+)?)\s*(?:m2|m²|sqm)\b',
    'floor_area_m2': r'(?:total\s+)?floor\s+area\s*[:=]?\s*([\d,]+(?:\.\d+)?)\s*(?:m2|m²|sqm)\b',
    'wall_length_m': r'(?:total\s+)?wall\s+length\s*[:=]?\s*([\d,]+(?:\.\d+)?)\s*(?:m|metres|meters)\b',
}

def candidates_from_text(text):
    values, warnings = {}, []
    for key, pattern in LABELS.items():
        matches = re.findall(pattern, text, flags=re.I)
        if len(matches) == 1:
            values[key] = float(matches[0].replace(',', ''))
        else:
            warnings.append(f'{key}: {"multiple labels" if matches else "no explicit label"}; enter reviewed quantity')
    return values, warnings

def ocr_image(image):
    try:
        import pytesseract
        return pytesseract.image_to_string(image)
    except (ImportError, OSError, RuntimeError) as exc:
        return '', f'OCR unavailable ({exc}); install Tesseract and pytesseract'

def process(data: bytes, filename: str):
    ext = Path(filename).suffix.lower()
    warnings, metadata, text, pages = [], {}, '', 1
    if ext == '.pdf':
        import fitz
        doc = fitz.open(stream=data, filetype='pdf')
        if doc.is_encrypted:
            raise ValueError('Encrypted PDF not supported')
        pages = len(doc)
        for page in doc:
            selectable = page.get_text(sort=True)
            text += selectable + '\n'
            if len(selectable.strip()) < 20:
                try:
                    from PIL import Image
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                    image = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
                    result = ocr_image(image)
                    if isinstance(result, tuple): warnings.append(result[1])
                    else: text += result + '\n'
                except ImportError:
                    warnings.append('Pillow not installed; scanned page OCR skipped')
        doc.close()
    elif ext in ('.png', '.jpg', '.jpeg', '.tif', '.tiff'):
        from PIL import Image
        image = Image.open(io.BytesIO(data))
        metadata['image_pixels'] = list(image.size)
        result = ocr_image(image)
        if isinstance(result, tuple): warnings.append(result[1])
        else: text = result
    elif ext == '.dxf':
        import ezdxf
        doc = ezdxf.read(io.StringIO(data.decode('utf-8', errors='replace')))
        model = doc.modelspace()
        metadata['units_code'] = doc.header.get('$INSUNITS', 0)
        metadata['entity_counts'] = {}
        for entity in model:
            kind = entity.dxftype()
            metadata['entity_counts'][kind] = metadata['entity_counts'].get(kind, 0) + 1
            if kind in ('TEXT', 'MTEXT'):
                text += (entity.dxf.text if kind == 'TEXT' else entity.plain_text()) + '\n'
        warnings.append('DXF geometry is imported as metadata only; layer mapping and unit verification are required before takeoff')
    elif ext == '.ifc':
        try:
            import ifcopenshell
        except ImportError as exc:
            raise ValueError('IFC support requires optional ifcopenshell package') from exc
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix='.ifc', delete=False) as temp:
            temp.write(data); path = temp.name
        try:
            model = ifcopenshell.open(path)
            metadata['entity_counts'] = {k: len(model.by_type(k)) for k in ('IfcWall', 'IfcSlab', 'IfcRoof', 'IfcDoor', 'IfcWindow')}
        finally:
            os.unlink(path)
        warnings.append('IFC model entities counted only; quantities and timber specifications require a verified model mapping')
    else:
        raise ValueError('Unsupported file type. DWG and RVT need conversion to DXF/IFC by a licensed CAD/BIM tool')
    candidates, missing = candidates_from_text(text)
    warnings.extend(missing)
    warnings.append('All quantities require human verification; OCR and pixel scale are not reliable without calibration')
    return {'pages': pages, 'text_preview': text[:2000], 'candidates': candidates,
            'warnings': list(dict.fromkeys(warnings)), 'metadata': metadata, 'format': ext.lstrip('.')}

def pixels_to_metres(pixel_distance: float, reference_pixels: float, reference_metres: float) -> float:
    """A manually identified reference dimension calibrates pixel distance; never infer scale from DPI."""
    if min(pixel_distance, reference_pixels, reference_metres) <= 0:
        raise ValueError('All calibration inputs must be positive')
    return pixel_distance * reference_metres / reference_pixels
