#!/usr/bin/env python3

"""Lightweight result export helpers for Finder v8.

CSV uses UTF-8 with BOM and semicolon delimiters for convenient opening in
European Excel installations. XLSX is written with the Python standard
library only, keeping the Finder runtime dependency list unchanged.
"""

import csv
import re
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape


_XLSX_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
_CONTENT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"


def write_csv(path, headers, rows):
    path = Path(path)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(list(headers))
        writer.writerows(rows)


def _column_name(index):
    """Return the 1-based Excel column name for index."""
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _safe_sheet_name(value):
    value = re.sub(r"[\\/*?:\[\]]", "_", str(value or "Results")).strip()
    value = value.strip("'") or "Results"
    return value[:31]


def _xml_text(value):
    if value is None:
        return ""
    return escape(str(value), {'"': "&quot;"})


def _cell_xml(row_number, column_number, value, *, header=False):
    ref = f"{_column_name(column_number)}{row_number}"
    style = ' s="1"' if header else ""
    text = _xml_text(value)
    return (
        f'<c r="{ref}" t="inlineStr"{style}>'
        f'<is><t xml:space="preserve">{text}</t></is></c>'
    )


def _column_widths(headers, rows):
    widths = []
    for index, header in enumerate(headers):
        longest = len(str(header))
        for row in rows:
            if index < len(row):
                longest = max(longest, len(str(row[index] if row[index] is not None else "")))
        widths.append(min(max(longest + 2, 10), 42))
    return widths


def _sheet_xml(headers, rows):
    headers = list(headers)
    rows = [list(row) for row in rows]

    last_col = _column_name(max(len(headers), 1))
    last_row = max(len(rows) + 1, 1)
    dimension = f"A1:{last_col}{last_row}"

    widths = _column_widths(headers, rows)
    cols_xml = "".join(
        f'<col min="{index}" max="{index}" width="{width}" customWidth="1"/>'
        for index, width in enumerate(widths, start=1)
    )

    sheet_rows = []
    if headers:
        sheet_rows.append(
            '<row r="1">'
            + "".join(
                _cell_xml(1, index, header, header=True)
                for index, header in enumerate(headers, start=1)
            )
            + "</row>"
        )

    for row_number, row in enumerate(rows, start=2):
        sheet_rows.append(
            f'<row r="{row_number}">'
            + "".join(
                _cell_xml(row_number, index, value)
                for index, value in enumerate(row, start=1)
            )
            + "</row>"
        )

    auto_filter = f'<autoFilter ref="{dimension}"/>' if headers else ""

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<worksheet xmlns="{_XLSX_NS}" xmlns:r="{_REL_NS}">'
        f'<dimension ref="{dimension}"/>'
        '<sheetViews><sheetView workbookViewId="0">'
        '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
        '</sheetView></sheetViews>'
        '<sheetFormatPr defaultRowHeight="15"/>'
        f'<cols>{cols_xml}</cols>'
        f'<sheetData>{"".join(sheet_rows)}</sheetData>'
        f'{auto_filter}'
        '</worksheet>'
    )


def write_xlsx(path, headers, rows, *, sheet_name="Results"):
    path = Path(path)
    safe_name = _safe_sheet_name(sheet_name)

    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<Types xmlns="{_CONTENT_NS}">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        '</Types>'
    )

    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<Relationships xmlns="{_PACKAGE_REL_NS}">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        '</Relationships>'
    )

    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<workbook xmlns="{_XLSX_NS}" xmlns:r="{_REL_NS}">'
        '<sheets>'
        f'<sheet name="{_xml_text(safe_name)}" sheetId="1" r:id="rId1"/>'
        '</sheets>'
        '</workbook>'
    )

    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<Relationships xmlns="{_PACKAGE_REL_NS}">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
        '</Relationships>'
    )

    styles = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<styleSheet xmlns="{_XLSX_NS}">'
        '<fonts count="2">'
        '<font><sz val="11"/><name val="Calibri"/><family val="2"/></font>'
        '<font><b/><sz val="11"/><name val="Calibri"/><family val="2"/></font>'
        '</fonts>'
        '<fills count="2">'
        '<fill><patternFill patternType="none"/></fill>'
        '<fill><patternFill patternType="gray125"/></fill>'
        '</fills>'
        '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="2">'
        '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
        '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>'
        '</cellXfs>'
        '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
        '</styleSheet>'
    )

    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", root_rels)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        archive.writestr("xl/styles.xml", styles)
        archive.writestr("xl/worksheets/sheet1.xml", _sheet_xml(headers, rows))
