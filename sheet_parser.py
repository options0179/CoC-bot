import io

import openpyxl

INFO_LABELS = {
    "이름": "name",
    "직업": "occupation",
    "나이": "age",
    "성별": "sex",
    "거주지": "residence",
    "출생지": "birthplace",
}

ATTRIBUTE_LABELS = {
    "근력": "str",
    "민첩": "dex",
    "정신": "pow",
    "건강": "con",
    "외모": "app",
    "교육": "edu",
    "크기": "siz",
    "지능": "int",
    "이동력": "mov",
}

_INT_FIELDS = set(ATTRIBUTE_LABELS.values()) | {"age"}


def _build_label_index(ws) -> dict:
    index = {}
    for row in ws.iter_rows():
        for cell in row:
            if isinstance(cell.value, str):
                label = cell.value.strip()
                if label and label not in index:
                    index[label] = cell
    return index


def _adjacent_value(ws, cell):
    return ws.cell(row=cell.row, column=cell.column + 1).value


def _to_int(value, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"'{label}' 값이 숫자가 아닙니다: {value!r}")
    return int(value)


def parse_character_sheet(file_bytes: bytes) -> dict:
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
    ws = wb.active
    labels = _build_label_index(ws)

    result = {}
    for label, field in {**INFO_LABELS, **ATTRIBUTE_LABELS}.items():
        cell = labels.get(label)
        if cell is None:
            raise ValueError(f"'{label}' 항목을 시트에서 찾을 수 없습니다.")
        value = _adjacent_value(ws, cell)
        result[field] = _to_int(value, label) if field in _INT_FIELDS else value

    result["skills"] = {}
    return result
