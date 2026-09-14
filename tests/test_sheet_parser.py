import io

import openpyxl
import pytest

from sheet_parser import INFO_LABELS, parse_character_sheet

_BASE_FIELDS = {
    "이름": "탐사자",
    "직업": "사립탐정",
    "나이": 32,
    "성별": "여",
    "거주지": "서울",
    "출생지": "부산",
    "근력": 50,
    "민첩": 60,
    "정신": 55,
    "건강": 65,
    "외모": 45,
    "교육": 70,
    "크기": 50,
    "지능": 80,
    "이동력": 8,
}


def _build_workbook(fields: dict, skills: dict | None = None, junk_rows: list | None = None) -> bytes:
    """Models the real-world sheet layout: info fields sit two columns to
    the right of their label (a blank spacer column between), attributes
    sit one column to the right, and each skill row is
    [checkbox, name, base, total, ...] with the checkbox immediately left
    of the name."""
    wb = openpyxl.Workbook()
    ws = wb.active
    row = 1
    for label, value in fields.items():
        offset = 2 if label in INFO_LABELS else 1
        ws.cell(row=row, column=1, value=label)
        ws.cell(row=row, column=1 + offset, value=value)
        row += 1
    for name, total in (skills or {}).items():
        ws.cell(row=row, column=1, value="□")
        ws.cell(row=row, column=2, value=name)
        ws.cell(row=row, column=3, value=1)  # base value, distinct from total
        ws.cell(row=row, column=4, value=total)
        row += 1
    for junk_row in junk_rows or []:
        for col, value in enumerate(junk_row, start=1):
            ws.cell(row=row, column=col, value=value)
        row += 1
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def test_parse_character_sheet_extracts_info_fields():
    result = parse_character_sheet(_build_workbook(_BASE_FIELDS))
    assert result["name"] == "탐사자"
    assert result["occupation"] == "사립탐정"
    assert result["age"] == 32
    assert result["sex"] == "여"
    assert result["residence"] == "서울"
    assert result["birthplace"] == "부산"


def test_parse_character_sheet_extracts_attributes():
    result = parse_character_sheet(_build_workbook(_BASE_FIELDS))
    assert result["str"] == 50
    assert result["dex"] == 60
    assert result["pow"] == 55
    assert result["con"] == 65
    assert result["app"] == 45
    assert result["edu"] == 70
    assert result["siz"] == 50
    assert result["int"] == 80
    assert result["mov"] == 8


def test_parse_character_sheet_missing_label_raises():
    fields = dict(_BASE_FIELDS)
    del fields["직업"]
    with pytest.raises(ValueError, match="직업"):
        parse_character_sheet(_build_workbook(fields))


def test_parse_character_sheet_non_numeric_attribute_raises():
    fields = dict(_BASE_FIELDS, 근력="abc")
    with pytest.raises(ValueError, match="근력"):
        parse_character_sheet(_build_workbook(fields))


def test_parse_character_sheet_extracts_skills_total_column_not_base():
    result = parse_character_sheet(
        _build_workbook(_BASE_FIELDS, skills={"회계": 40, "심리학": 50, "회피": 32})
    )
    assert result["skills"] == {"회계": 40, "심리학": 50, "회피": 32}


def test_parse_character_sheet_ignores_zero_valued_skills():
    result = parse_character_sheet(
        _build_workbook(_BASE_FIELDS, skills={"회계": 0, "심리학": 10})
    )
    assert result["skills"] == {"심리학": 10}


def test_parse_character_sheet_skills_default_empty_when_none_present():
    result = parse_character_sheet(_build_workbook(_BASE_FIELDS))
    assert result["skills"] == {}


def test_parse_character_sheet_recognizes_skill_name_not_in_fixed_list():
    # 사진술 is a player-added custom skill, not in sheet_parser.SKILL_NAMES —
    # the checkbox marker is what identifies it as a skill row, not the name.
    result = parse_character_sheet(
        _build_workbook(_BASE_FIELDS, skills={"사진술": 35})
    )
    assert result["skills"] == {"사진술": 35}


def test_parse_character_sheet_recognizes_skill_spelling_variant():
    # Real sheets abbreviate differently from sheet_parser.SKILL_NAMES's
    # canonical spelling (e.g. "근접전(격투)" instead of "근접전투(격투)").
    # Checkbox-based detection doesn't care about the exact name.
    result = parse_character_sheet(
        _build_workbook(_BASE_FIELDS, skills={"근접전(격투)": 35})
    )
    assert result["skills"] == {"근접전(격투)": 35}


def test_parse_character_sheet_ignores_labeled_number_without_checkbox():
    # A header like "직업 기능 점수" sits next to a point-budget number but
    # has no checkbox to its left — must not be picked up as a skill.
    result = parse_character_sheet(
        _build_workbook(_BASE_FIELDS, junk_rows=[["직업 기능 점수", None, 320]])
    )
    assert result["skills"] == {}


def test_parse_character_sheet_non_xlsx_raises_value_error():
    with pytest.raises(ValueError, match="xlsx"):
        parse_character_sheet(b"not an xlsx file at all")


def test_parse_character_sheet_empty_name_raises():
    fields = dict(_BASE_FIELDS, 이름="   ")
    with pytest.raises(ValueError, match="이름"):
        parse_character_sheet(_build_workbook(fields))
