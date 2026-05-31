"""Тесты для scripts/validate_fos.py — проверка соответствия ФОС и РП."""

import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.validate_fos import (
    read_yaml,
    read_body,
    find_competencies,
    find_attestation_form,
    check_yaml,
    check_competencies,
    check_attestation,
)


# ─── Вспомогательные функции ──────────────────────────────────────


def _write_md(path: str, content: str):
    """Записать Markdown с YAML frontmatter во временный файл."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


# ─── read_yaml / read_body ────────────────────────────────────────


class TestReadYaml:
    def test_read_yaml_frontmatter(self):
        md = """---
title: "Рабочая программа дисциплины"
discipline:
  code: "Б1.О.01"
  name: "Тест"
direction:
  code: "09.03.01"
  name: "ИВТ"
profile: "ПО ВТ и АС"
year: 2025
semester: 6
---

# Тело документа
"""
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8")
        tmp.write(md)
        tmp.close()
        try:
            y = read_yaml(tmp.name)
            assert y["title"] == "Рабочая программа дисциплины"
            assert y["discipline"]["code"] == "Б1.О.01"
            assert y["direction"]["code"] == "09.03.01"
            assert y["year"] == 2025
        finally:
            os.unlink(tmp.name)

    def test_read_yaml_no_frontmatter_raises(self):
        md = "# Просто документ\n\nБез YAML\n"
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8")
        tmp.write(md)
        tmp.close()
        try:
            import pytest
            with pytest.raises(ValueError, match="Не найден YAML frontmatter"):
                read_yaml(tmp.name)
        finally:
            os.unlink(tmp.name)

    def test_read_yaml_with_discipline_hours(self):
        md = """---
title: "РП"
discipline:
  code: "Б1.В.01"
  name: "ТВП"
  hours: 144
  credits: 4
---

Содержание
"""
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8")
        tmp.write(md)
        tmp.close()
        try:
            y = read_yaml(tmp.name)
            assert y["discipline"]["hours"] == 144
            assert y["discipline"]["credits"] == 4
        finally:
            os.unlink(tmp.name)


class TestReadBody:
    def test_body_without_yaml(self):
        """read_body возвращает весь текст, если нет frontmatter."""
        content = "# Тело\n\nКакой-то текст\n"
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8")
        tmp.write(content)
        tmp.close()
        try:
            body = read_body(tmp.name)
            assert body == content
        finally:
            os.unlink(tmp.name)

    def test_body_excludes_yaml(self):
        md = """---
title: "РП"
---

# Тело документа
"""
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8")
        tmp.write(md)
        tmp.close()
        try:
            body = read_body(tmp.name)
            assert "---" not in body
            assert "title" not in body
            assert "# Тело документа" in body
            # Тело начинается сразу после YAML frontmatter
            assert body.strip() == "# Тело документа"
        finally:
            os.unlink(tmp.name)


# ─── find_competencies ────────────────────────────────────────────


class TestFindCompetencies:
    def test_find_opc(self):
        text = "ОПК-1, ОПК-8, ОПК-9"
        assert find_competencies(text) == {"ОПК-1", "ОПК-8", "ОПК-9"}

    def test_find_pk(self):
        text = "ПК-1, ПК-12"
        assert find_competencies(text) == {"ПК-1", "ПК-12"}

    def test_find_uk(self):
        text = "УК-1, УК-2, УК-6"
        assert find_competencies(text) == {"УК-1", "УК-2", "УК-6"}

    def test_find_mixed(self):
        text = "ОПК-8, ПК-1, УК-1"
        assert find_competencies(text) == {"ОПК-8", "ПК-1", "УК-1"}

    def test_empty_text(self):
        assert find_competencies("") == set()

    def test_no_competencies(self):
        text = "Просто текст без кодов компетенций"
        assert find_competencies(text) == set()

    def test_deduplicates(self):
        text = "ОПК-1 и ещё раз ОПК-1"
        assert find_competencies(text) == {"ОПК-1"}

    def test_partial_word_not_matched(self):
        """Числа после дефиса не должны цепляться к словам без префикса."""
        text = "ОПК-1, какой-то текст ОПК-8"
        result = find_competencies(text)
        assert "ОПК-1" in result
        assert "ОПК-8" in result
        assert len(result) == 2


# ─── find_attestation_form ────────────────────────────────────────


class TestFindAttestationForm:
    def test_экзамен(self):
        assert find_attestation_form("Форма контроля: Экзамен") == "Экзамен"

    def test_зачёт(self):
        assert find_attestation_form("Форма контроля: Зачёт") == "Зачёт"

    def test_зачет_without_ё(self):
        assert find_attestation_form("Форма контроля: Зачет") == "Зачёт"

    def test_case_sensitive(self):
        """Функция регистрозависима — строчные не совпадают."""
        assert find_attestation_form("зачёт") is None

    def test_none_when_not_found(self):
        assert find_attestation_form("Нет формы аттестации") is None

    def test_empty_string(self):
        assert find_attestation_form("") is None


# ─── check_yaml ───────────────────────────────────────────────────


class TestCheckYaml:
    def test_all_fields_match(self):
        rp = {
            "discipline": {"code": "Б1.О.01", "name": "Тест", "hours": 144, "credits": 4},
            "direction": {"code": "09.03.01", "name": "ИВТ"},
            "profile": "ПО ВТ и АС",
            "year": 2025,
            "form_of_study": "Очная",
            "semester": 6,
            "university": "ЗабГУ",
            "faculty": "Энергетический",
            "department": "ИВТиПМ",
            "developer": "Иванов И.И.",
        }
        fos = dict(rp)  # точная копия
        errors = check_yaml(rp, fos)
        assert errors == []

    def test_fields_mismatch(self):
        rp = {"discipline": {"code": "Б1.О.01"}, "direction": {"code": "09.03.01"},
              "name": "РП", "profile": "Профиль X", "year": 2025, "form_of_study": "Очная",
              "semester": 6, "university": "ЗабГУ", "faculty": "ЭнФ", "department": "ИВТ",
              "developer": "Иванов"}
        fos = {"discipline": {"code": "Б1.О.02"}, "direction": {"code": "09.03.02"},
               "name": "ФОС", "profile": "Профиль Y", "year": 2024, "form_of_study": "Заочная",
               "semester": 7, "university": "ЧитГУ", "faculty": "Другой", "department": "Другая",
               "developer": "Петров"}
        errors = check_yaml(rp, fos)
        # Должны быть ошибки по всем полям, кроме 'name' (его нет в common_fields)
        # common_fields содержит 13 полей, из них 10 не совпадают
        assert len(errors) == 10
        assert any("Б1.О.01" in e for e in errors)

    def test_partial_mismatch(self):
        rp = {
            "discipline": {"code": "Б1.О.01", "name": "ТВП"},
            "direction": {"code": "09.03.01", "name": "ИВТ"},
            "profile": "ПО ВТ и АС",
            "year": 2025,
            "form_of_study": "Очная",
            "semester": 6,
            "university": "ЗабГУ",
            "faculty": "ЭнФ",
            "department": "ИВТ",
            "developer": "Иванов",
        }
        fos = dict(rp)
        fos["discipline"] = {"code": "Б1.О.01", "name": "Другое название"}
        errors = check_yaml(rp, fos)
        # Только одно поле не совпадает
        assert len(errors) == 1
        assert "Другое название" in errors[0]


# ─── check_competencies ───────────────────────────────────────────


class TestCheckCompetencies:
    def test_match(self):
        errors = check_competencies(
            "ОПК-8, ПК-1",
            "ПК-1, ОПК-8",
        )
        assert len(errors) == 1
        # Последняя строка — информация о совпадении
        assert "✅" in errors[0]

    def test_rp_has_more(self):
        errors = check_competencies(
            "ОПК-8, ПК-1, УК-1",
            "ОПК-8",
        )
        assert len(errors) == 1
        assert "❌" in errors[0]
        assert "УК-1" in errors[0] or "ПК-1" in errors[0]

    def test_fos_has_more(self):
        errors = check_competencies(
            "ОПК-8",
            "ОПК-8, ПК-1",
        )
        assert len(errors) == 1
        assert "❌" in errors[0]
        assert "ПК-1" in errors[0]

    def test_both_have_different(self):
        errors = check_competencies(
            "ОПК-8, УК-1",
            "ПК-1, ПК-2",
        )
        assert len(errors) == 2
        assert all("❌" in e for e in errors)

    def test_no_competencies_in_either(self):
        errors = check_competencies(
            "Нет компетенций",
            "Тоже нет",
        )
        assert len(errors) == 1
        assert "(не найдены)" in errors[0]


# ─── check_attestation ────────────────────────────────────────────


class TestCheckAttestation:
    def test_both_экзамен(self):
        errors = check_attestation("Форма: Экзамен", "Форма: Экзамен")
        assert len(errors) == 1
        assert "✅" in errors[0]

    def test_both_зачёт(self):
        errors = check_attestation("Форма: Зачёт", "Форма: Зачёт")
        assert len(errors) == 1
        assert "✅" in errors[0]

    def test_mismatch(self):
        errors = check_attestation("Форма: Экзамен", "Форма: Зачёт")
        assert len(errors) == 1
        assert "❌" in errors[0]

    def test_rp_missing(self):
        errors = check_attestation("Нет формы", "Форма: Экзамен")
        assert len(errors) == 1
        assert "РП" in errors[0]
        assert "не удалось" in errors[0].lower()

    def test_fos_missing(self):
        errors = check_attestation("Форма: Экзамен", "Нет формы")
        assert len(errors) == 1
        assert "ФОС" in errors[0]
        assert "не удалось" in errors[0].lower()

    def test_зачет_without_ё_matches(self):
        """'Зачет' и 'Зачёт' распознаются одинаково."""
        errors = check_attestation("Форма: Зачет", "Форма: Зачёт")
        assert len(errors) == 1
        assert "✅" in errors[0]


# ─── Интеграционный тест ──────────────────────────────────────────


class TestIntegration:
    def _make_rp_file(self, path: str):
        content = """---
title: "Рабочая программа дисциплины"
discipline:
  code: "Б1.О.01"
  name: "Тестовая дисциплина"
  hours: 144
  credits: 4
direction:
  code: "09.03.01"
  name: "Информатика и вычислительная техника"
profile: "ПО ВТ и АС"
year: 2025
form_of_study: "Очная"
semester: 6
university: "Забайкальский государственный университет"
faculty: "Энергетический факультет"
department: "ИВТиПМ"
developer: "Иванов И.И."
---

# Рабочая программа

Компетенции: ОПК-8, ПК-1.

Форма промежуточной аттестации: Экзамен.
"""
        _write_md(path, content)

    def _make_fos_file(self, path: str):
        content = """---
title: "Фонд оценочных средств"
discipline:
  code: "Б1.О.01"
  name: "Тестовая дисциплина"
  hours: 144
  credits: 4
direction:
  code: "09.03.01"
  name: "Информатика и вычислительная техника"
profile: "ПО ВТ и АС"
year: 2025
form_of_study: "Очная"
semester: 6
university: "Забайкальский государственный университет"
faculty: "Энергетический факультет"
department: "ИВТиПМ"
developer: "Иванов И.И."
---

# Фонд оценочных средств

Компетенции: ОПК-8, ПК-1.

Форма промежуточной аттестации: Экзамен.
"""
        _write_md(path, content)

    def test_matching_rp_and_fos(self):
        """Полностью согласованные РП и ФОС — без ошибок."""
        tmpdir = tempfile.mkdtemp()
        try:
            rp_path = os.path.join(tmpdir, "rp.md")
            fos_path = os.path.join(tmpdir, "fos.md")
            self._make_rp_file(rp_path)
            self._make_fos_file(fos_path)

            rp_yaml = read_yaml(rp_path)
            fos_yaml = read_yaml(fos_path)
            errors = check_yaml(rp_yaml, fos_yaml)
            assert errors == [], f"YAML errors: {errors}"

            rp_body = read_body(rp_path)
            fos_body = read_body(fos_path)
            errors = check_competencies(rp_body, fos_body)
            assert errors and "✅" in errors[0], f"Competency errors: {errors}"

            errors = check_attestation(rp_body, fos_body)
            assert errors and "✅" in errors[0], f"Attestation errors: {errors}"
        finally:
            import shutil
            shutil.rmtree(tmpdir)

    def test_mismatched_rp_and_fos(self):
        """Расходящиеся РП и ФОС — должны быть ошибки."""
        tmpdir = tempfile.mkdtemp()
        try:
            rp_path = os.path.join(tmpdir, "rp.md")
            fos_path = os.path.join(tmpdir, "fos.md")
            self._make_rp_file(rp_path)
            # ФОС с другими данными
            content = """---
title: "Фонд оценочных средств"
discipline:
  code: "Б1.О.99"
  name: "Другая дисциплина"
  hours: 100
  credits: 3
direction:
  code: "09.03.02"
  name: "Другое направление"
profile: "Другой профиль"
year: 2024
form_of_study: "Заочная"
semester: 8
university: "Другой вуз"
faculty: "Другой факультет"
department: "Другая кафедра"
developer: "Петров П.П."
---

# ФОС

Компетенции: ОПК-1, ПК-2.

Форма промежуточной аттестации: Зачёт.
"""
            _write_md(fos_path, content)

            rp_yaml = read_yaml(rp_path)
            fos_yaml = read_yaml(fos_path)
            errors = check_yaml(rp_yaml, fos_yaml)
            assert len(errors) > 0

            rp_body = read_body(rp_path)
            fos_body = read_body(fos_path)
            errors = check_competencies(rp_body, fos_body)
            assert any("❌" in e for e in errors)

            errors = check_attestation(rp_body, fos_body)
            assert "❌" in errors[0]
        finally:
            import shutil
            shutil.rmtree(tmpdir)


import pytest