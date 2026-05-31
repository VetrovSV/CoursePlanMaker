"""Тесты для scripts/validate_rp.py — валидация часов в РП."""

import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.validate_rp import (
    extract_tables_from_markdown,
    try_int,
    validate_table_311,
    validate_simple_table,
)


# ─── Вспомогательные функции ──────────────────────────────────────


def _write_md(content: str) -> str:
    """Записать Markdown во временный файл, вернуть путь."""
    fd, path = tempfile.mkstemp(suffix=".md", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    return path


# ─── try_int ───────────────────────────────────────────────────────


class TestTryInt:
    def test_plain_number(self):
        assert try_int("42") == 42

    def test_with_bold_markers(self):
        assert try_int("**32**") == 32

    def test_with_spaces(self):
        assert try_int(" 16 ") == 16

    def test_empty_string(self):
        assert try_int("") is None

    def test_none(self):
        assert try_int(None) is None

    def test_non_numeric(self):
        assert try_int("abc") is None

    def test_negative(self):
        assert try_int("-5") == -5


# ─── extract_tables_from_markdown ─────────────────────────────────


class TestExtractTables:
    def test_no_tables(self):
        """Файл без таблиц — пустой результат."""
        path = _write_md("# Просто заголовок\n\nКакой-то текст\n")
        try:
            tables = extract_tables_from_markdown(path)
            assert tables == []
        finally:
            os.unlink(path)

    def test_single_table_311(self):
        """Таблица 3.1.1 с одной строкой."""
        md = """### 3.1.1 Структура дисциплины

| Модуль | Раздел | Всего часов | ЛК | ПЗ (СЗ) | ЛР | СРС |
|---|---|---|---|---|---|---|
| 1      | Тема 1 | 36         | 16 | 0       | 16 | 4   |
|**Итого**|       | **36**     |**16**|**0**  |**16**|**4**|
"""
        path = _write_md(md)
        try:
            tables = extract_tables_from_markdown(path)
            assert len(tables) == 1
            t = tables[0]
            assert t["id"] == "3.1.1"
            assert "Структура дисциплины" in t["name"]
            assert len(t["rows"]) == 1
            assert t["rows"][0]["Всего часов"] == "36"
            assert t["итого"] is not None
            assert t["итого"]["ЛК"] == "**16**"
        finally:
            os.unlink(path)

    def test_multiple_tables(self):
        """Несколько таблиц: 3.1.1 и 3.2.1."""
        md = """### 3.1.1 Структура дисциплины

| Всего часов | ЛК | ПЗ (СЗ) | ЛР | СРС |
|---|---|---|---|---|
| 36         | 16 | 0       | 16 | 4   |
|**Итого**|**36**|**16**|**0**|**16**|**4**|

### 3.2.1 Лекции

| № | Тема | Трудоемкость (в часах) |
|---|---|---|
| 1 | Тема 1 | 16 |
"""
        path = _write_md(md)
        try:
            tables = extract_tables_from_markdown(path)
            assert len(tables) == 2
            assert tables[0]["id"] == "3.1.1"
            assert tables[1]["id"] == "3.2.1"
        finally:
            os.unlink(path)

    def test_table_without_separator_ignored(self):
        """Строка без |---| не считается таблицей."""
        md = """### 3.1.1 Структура

| A | B |
| 1 | 2 |
"""
        path = _write_md(md)
        try:
            tables = extract_tables_from_markdown(path)
            assert tables == []
        finally:
            os.unlink(path)

    def test_table_unknown_id_skipped(self):
        """Таблица с id, для которого нет правил — не падает."""
        md = """### 4.1.1 Какая-то таблица

| A | B |
|---|---|
| 1 | 2 |
"""
        path = _write_md(md)
        try:
            tables = extract_tables_from_markdown(path)
            assert len(tables) == 1
            assert tables[0]["id"] == "4.1.1"
        finally:
            os.unlink(path)


# ─── validate_table_311 ───────────────────────────────────────────


class TestValidateTable311:
    def test_valid_table(self):
        """Все суммы сходятся."""
        table = {
            "id": "3.1.1",
            "name": "Структура дисциплины",
            "headers": ["Модуль", "Раздел", "Всего часов", "ЛК", "ПЗ (СЗ)", "ЛР", "СРС"],
            "rows": [
                {"Модуль": "1", "Раздел": "Тема 1", "Всего часов": "36", "ЛК": "16", "ПЗ (СЗ)": "0", "ЛР": "16", "СРС": "4"},
                {"Модуль": "2", "Раздел": "Тема 2", "Всего часов": "36", "ЛК": "16", "ПЗ (СЗ)": "0", "ЛР": "16", "СРС": "4"},
            ],
            "итого": {
                "Всего часов": "**72**", "ЛК": "**32**", "ПЗ (СЗ)": "**0**", "ЛР": "**32**", "СРС": "**8**",
            },
        }
        ok, errors = validate_table_311(table)
        assert ok is True
        assert errors == []

    def test_row_sum_mismatch(self):
        """Сумма ЛК+ПЗ+ЛР+СРС не равна Всего часов в строке."""
        table = {
            "id": "3.1.1",
            "name": "Структура дисциплины",
            "headers": ["Модуль", "Раздел", "Всего часов", "ЛК", "ПЗ (СЗ)", "ЛР", "СРС"],
            "rows": [
                {"Модуль": "1", "Раздел": "Тема 1", "Всего часов": "50", "ЛК": "16", "ПЗ (СЗ)": "0", "ЛР": "16", "СРС": "4"},
            ],
            "итого": {
                "Всего часов": "**50**", "ЛК": "**16**", "ПЗ (СЗ)": "**0**", "ЛР": "**16**", "СРС": "**4**",
            },
        }
        ok, errors = validate_table_311(table)
        assert ok is False
        assert any("50" in e for e in errors)

    def test_итого_mismatch(self):
        """Сумма по строкам не равна Итого."""
        table = {
            "id": "3.1.1",
            "name": "Структура дисциплины",
            "headers": ["Модуль", "Раздел", "Всего часов", "ЛК", "ПЗ (СЗ)", "ЛР", "СРС"],
            "rows": [
                {"Модуль": "1", "Раздел": "Тема 1", "Всего часов": "36", "ЛК": "16", "ПЗ (СЗ)": "0", "ЛР": "16", "СРС": "4"},
            ],
            "итого": {
                "Всего часов": "**99**", "ЛК": "**16**", "ПЗ (СЗ)": "**0**", "ЛР": "**16**", "СРС": "**4**",
            },
        }
        ok, errors = validate_table_311(table)
        assert ok is False
        assert any("99" in e for e in errors)

    def test_ауд_plus_срс_mismatch(self):
        """Ауд + СРС != Всего часов."""
        table = {
            "id": "3.1.1",
            "name": "Структура дисциплины",
            "headers": ["Модуль", "Раздел", "Всего часов", "ЛК", "ПЗ (СЗ)", "ЛР", "СРС"],
            "rows": [
                {"Модуль": "1", "Раздел": "Тема 1", "Всего часов": "100", "ЛК": "16", "ПЗ (СЗ)": "0", "ЛР": "16", "СРС": "4"},
            ],
            "итого": {
                "Всего часов": "**100**", "ЛК": "**16**", "ПЗ (СЗ)": "**0**", "ЛР": "**16**", "СРС": "**4**",
            },
        }
        ok, errors = validate_table_311(table)
        assert ok is False
        assert any("100" in e for e in errors)

    def test_missing_columns(self):
        """Не все столбцы найдены."""
        table = {
            "id": "3.1.1",
            "name": "Структура дисциплины",
            "headers": ["A", "B"],
            "rows": [],
            "итого": None,
        }
        ok, errors = validate_table_311(table)
        assert ok is False
        assert any("Не найдены" in e for e in errors)

    def test_missing_итого(self):
        """Нет строки Итого."""
        table = {
            "id": "3.1.1",
            "name": "Структура дисциплины",
            "headers": ["Модуль", "Раздел", "Всего часов", "ЛК", "ПЗ (СЗ)", "ЛР", "СРС"],
            "rows": [
                {"Модуль": "1", "Раздел": "Тема 1", "Всего часов": "36", "ЛК": "16", "ПЗ (СЗ)": "0", "ЛР": "16", "СРС": "4"},
            ],
            "итого": None,
        }
        ok, errors = validate_table_311(table)
        assert ok is False
        assert any("Итого" in e for e in errors)

    def test_non_numeric_values(self):
        """Нечисловые значения в ячейках."""
        table = {
            "id": "3.1.1",
            "name": "Структура дисциплины",
            "headers": ["Модуль", "Раздел", "Всего часов", "ЛК", "ПЗ (СЗ)", "ЛР", "СРС"],
            "rows": [
                {"Модуль": "1", "Раздел": "Тема 1", "Всего часов": "abc", "ЛК": "16", "ПЗ (СЗ)": "0", "ЛР": "16", "СРС": "4"},
            ],
            "итого": {
                "Всего часов": "**abc**", "ЛК": "**16**", "ПЗ (СЗ)": "**0**", "ЛР": "**16**", "СРС": "**4**",
            },
        }
        ok, errors = validate_table_311(table)
        assert ok is False
        assert any("нечисловые" in e for e in errors)


# ─── validate_simple_table ────────────────────────────────────────


class TestValidateSimpleTable:
    def test_valid_sum(self):
        table = {
            "headers": ["№", "Тема", "Трудоемкость (в часах)"],
            "rows": [
                {"№": "1", "Тема": "Тема 1", "Трудоемкость (в часах)": "16"},
                {"№": "2", "Тема": "Тема 2", "Трудоемкость (в часах)": "16"},
            ],
        }
        ok, errors = validate_simple_table(table, "Трудоемкость (в часах)")
        assert ok is True
        assert errors == []

    def test_missing_column(self):
        table = {
            "headers": ["№", "Тема"],
            "rows": [],
        }
        ok, errors = validate_simple_table(table, "Трудоемкость (в часах)")
        assert ok is False
        assert any("не найден" in e for e in errors)

    def test_empty_rows(self):
        table = {
            "headers": ["№", "Тема", "Трудоемкость (в часах)"],
            "rows": [],
        }
        ok, errors = validate_simple_table(table, "Трудоемкость (в часах)")
        assert ok is True
        assert errors == []


# ─── Интеграционный тест ──────────────────────────────────────────


class TestIntegration:
    def test_full_valid_rp(self):
        """Полный цикл: парсинг и валидация корректной РП."""
        md = """---
title: "РП"
discipline:
  code: "Б1.О.01"
  name: "Тест"
---

### 3.1.1 Структура дисциплины

| Модуль | Раздел | Всего часов | ЛК | ПЗ (СЗ) | ЛР | СРС |
|---|---|---|---|---|---|---|
| 1      | Тема 1 | 36         | 16 | 0       | 16 | 4   |
| 2      | Тема 2 | 36         | 16 | 0       | 16 | 4   |
|**Итого**|       | **72**     |**32**|**0** |**32**|**8**|

### 3.2.1 Лекции

| № | Тема | Трудоемкость (в часах) |
|---|---|---|
| 1 | Тема 1 | 16 |
| 2 | Тема 2 | 16 |
"""
        path = _write_md(md)
        try:
            tables = extract_tables_from_markdown(path)
            assert len(tables) == 2

            ok_311, err_311 = validate_table_311(tables[0])
            assert ok_311 is True, err_311

            ok_simple, err_simple = validate_simple_table(tables[1], "Трудоемкость (в часах)")
            assert ok_simple is True, err_simple
        finally:
            os.unlink(path)

    def test_full_invalid_rp(self):
        """Полный цикл: парсинг и валидация некорректной РП."""
        md = """### 3.1.1 Структура дисциплины

| Модуль | Раздел | Всего часов | ЛК | ПЗ (СЗ) | ЛР | СРС |
|---|---|---|---|---|---|---|
| 1      | Тема 1 | 50         | 16 | 0       | 16 | 4   |
|**Итого**|       | **50**     |**16**|**0** |**16**|**4**|
"""
        path = _write_md(md)
        try:
            tables = extract_tables_from_markdown(path)
            assert len(tables) == 1

            ok, errors = validate_table_311(tables[0])
            assert ok is False
            assert len(errors) > 0
        finally:
            os.unlink(path)


import pytest
