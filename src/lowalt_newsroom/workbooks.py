"""只读OOXML；读取全部行，避免受已有Excel筛选范围影响。"""

from pathlib import Path, PurePosixPath
from zipfile import ZipFile
import posixpath
import re
import xml.etree.ElementTree as ET

NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def read_workbook(path: str | Path) -> dict:
    with ZipFile(path) as archive:
        strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            strings = ["".join(x.itertext()) for x in ET.fromstring(archive.read("xl/sharedStrings.xml"))]
        relationships = {x.attrib["Id"]: x.attrib["Target"]
                         for x in ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))}
        result = {}
        for sheet in ET.fromstring(archive.read("xl/workbook.xml")).findall("s:sheets/s:sheet", NS):
            target = relationships[sheet.attrib[f"{{{REL}}}id"]]
            member = target.lstrip("/") if target.startswith("/") else posixpath.normpath("xl/" + target)
            if ".." in PurePosixPath(member).parts:
                raise ValueError("工作表路径越界")
            root = ET.fromstring(archive.read(member))
            rows = []
            for row in root.findall("s:sheetData/s:row", NS):
                values = {}
                for cell in row.findall("s:c", NS):
                    column = re.match(r"[A-Z]+", cell.attrib["r"])[0]
                    value = cell.find("s:v", NS)
                    text = (value.text or "") if value is not None else ""
                    if cell.get("t") == "s":
                        text = strings[int(text)]
                    elif cell.get("t") == "inlineStr":
                        inline = cell.find("s:is", NS)
                        text = "".join(inline.itertext()) if inline is not None else ""
                    values[column] = text
                rows.append({"row": int(row.attrib["r"]), "cells": values})
            result[sheet.attrib["name"]] = rows
        return result


def table_records(path: str | Path, sheet: str, key: str) -> list[dict]:
    rows = read_workbook(path)[sheet]
    header = next((r for r in rows if key in r["cells"].values()), None)
    if header is None:
        raise ValueError(f"找不到表头：{sheet}/{key}")
    key_column = next(c for c, value in header["cells"].items() if value == key)
    result, seen = [], set()
    for row in rows:
        if row["row"] <= header["row"] or not row["cells"].get(key_column):
            continue
        record = {label: row["cells"].get(column, "") for column, label in header["cells"].items() if label}
        identifier = record[key]
        if identifier in seen:
            raise ValueError(f"重复ID：{identifier}")
        seen.add(identifier)
        result.append(record)
    return result
