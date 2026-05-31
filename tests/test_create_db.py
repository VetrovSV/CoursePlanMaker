"""Тесты для db/create_db.py — работа с SQLite БД дисциплин."""

import sqlite3
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from db.create_db import (
    create_db,
    add_direction,
    add_profile,
    add_study_plan,
    add_discipline,
    add_discipline_to_plan,
    get_study_plans,
    get_disciplines_for_plan,
    find_plan_id,
)


# ---- Фикстура ----


def conn():
    """Создать in-memory БД со схемой для каждого теста."""
    c = create_db(":memory:")
    yield c
    c.close()


# ---- Направления ----


class TestDirections:
    def test_add_and_get_direction(self):
        c = next(conn())
        dir_id = add_direction(c, "09.03.01", "Информатика и вычислительная техника", "бакалавриат")
        assert dir_id > 0

        row = c.execute("SELECT code, name, level FROM directions WHERE id = ?", (dir_id,)).fetchone()
        assert row == ("09.03.01", "Информатика и вычислительная техника", "бакалавриат")

    def test_add_duplicate_direction_returns_existing_id(self):
        c = next(conn())
        id1 = add_direction(c, "09.03.01", "Информатика и вычислительная техника", "бакалавриат")
        id2 = add_direction(c, "09.03.01", "Информатика и вычислительная техника", "бакалавриат")
        assert id1 == id2

    def test_level_constraint(self):
        c = next(conn())
        with pytest.raises(sqlite3.IntegrityError):
            c.execute("INSERT INTO directions (code, name, level) VALUES (?, ?, ?)",
                      ("00.00.00", "Тест", "неверный_уровень"))


# ---- Профили ----


class TestProfiles:
    def test_add_and_get_profile(self):
        c = next(conn())
        prof_id = add_profile(c, "Программное обеспечение ВТ и АС")
        assert prof_id > 0

        row = c.execute("SELECT name FROM profiles WHERE id = ?", (prof_id,)).fetchone()
        assert row[0] == "Программное обеспечение ВТ и АС"

    def test_add_duplicate_profile_returns_existing_id(self):
        c = next(conn())
        id1 = add_profile(c, "Профиль X")
        id2 = add_profile(c, "Профиль X")
        assert id1 == id2

    def test_add_profile_none(self):
        """Профиль может быть None (если у направления нет профилей)."""
        c = next(conn())
        # Проверим, что NULL в profile_id допустим
        dir_id = add_direction(c, "01.01.01", "Тест", "бакалавриат")
        plan_id = add_study_plan(c, 2025, "очная", dir_id, None)
        assert plan_id > 0

        plans = get_study_plans(c)
        assert len(plans) == 1
        assert plans[0]["profile"] is None


# ---- Дисциплины ----


class TestDisciplines:
    def test_add_discipline_with_code(self):
        c = next(conn())
        disc_id = add_discipline(c, "Б1.О.01", "Теория вычислительных процессов")
        assert disc_id > 0

        row = c.execute("SELECT code, name FROM disciplines WHERE id = ?", (disc_id,)).fetchone()
        assert row == ("Б1.О.01", "Теория вычислительных процессов")

    def test_add_discipline_without_code(self):
        c = next(conn())
        disc_id = add_discipline(c, None, "Временная дисциплина")
        assert disc_id > 0

    def test_add_duplicate_code_different_name_creates_new(self):
        """Один код может быть у разных дисциплин — создаётся новая запись."""
        c = next(conn())
        id1 = add_discipline(c, "Б1.О.01", "Старое имя")
        id2 = add_discipline(c, "Б1.О.01", "Новое имя")
        assert id1 != id2
        assert id1 == 1
        assert id2 == 2

    def test_add_duplicate_code_and_name_returns_existing(self):
        """Тот же (code, name) возвращает существующий id."""
        c = next(conn())
        id1 = add_discipline(c, "Б1.О.01", "ТВП")
        id2 = add_discipline(c, "Б1.О.01", "ТВП")
        assert id1 == id2


# ---- Учебные планы ----


class TestStudyPlans:
    def test_add_and_get_plans(self):
        c = next(conn())
        dir_id = add_direction(c, "09.03.01", "ИВТ", "бакалавриат")
        prof_id = add_profile(c, "ПО ВТ и АС")

        plan_id = add_study_plan(c, 2025, "очная", dir_id, prof_id)
        assert plan_id > 0

        plans = get_study_plans(c)
        assert len(plans) == 1
        p = plans[0]
        assert p["year"] == 2025
        assert p["form"] == "очная"
        assert p["direction_code"] == "09.03.01"
        assert p["profile"] == "ПО ВТ и АС"

    def test_duplicate_plan_returns_existing_id(self):
        c = next(conn())
        dir_id = add_direction(c, "09.03.01", "ИВТ", "бакалавриат")
        prof_id = add_profile(c, "Профиль")

        id1 = add_study_plan(c, 2025, "очная", dir_id, prof_id)
        id2 = add_study_plan(c, 2025, "очная", dir_id, prof_id)
        assert id1 == id2

    def test_form_constraint(self):
        c = next(conn())
        with pytest.raises(sqlite3.IntegrityError):
            c.execute("""INSERT INTO study_plans (year, form, direction_id)
                         VALUES (?, ?, ?)""", (2025, "вечерняя", 1))


# ---- Дисциплины в планах ----


class TestDisciplinesInPlans:
    def setup_plan(self, c):
        dir_id = add_direction(c, "09.03.01", "ИВТ", "бакалавриат")
        prof_id = add_profile(c, "ПО ВТ и АС")
        plan_id = add_study_plan(c, 2025, "очная", dir_id, prof_id)
        disc_id = add_discipline(c, "Б1.О.01", "ТВП")
        return plan_id, disc_id

    def test_add_discipline_to_plan(self):
        c = next(conn())
        plan_id, disc_id = self.setup_plan(c)
        link_id = add_discipline_to_plan(
            c, plan_id, disc_id,
            semester=5, hours_total=144, hours_lecture=32,
            hours_lab=32, hours_self_study=80, credits=4, exam_form="зачёт",
        )
        assert link_id > 0

        disc_list = get_disciplines_for_plan(c, plan_id)
        assert len(disc_list) == 1
        d = disc_list[0]
        assert d["code"] == "Б1.О.01"
        assert d["semester"] == 5
        assert d["hours_total"] == 144
        assert d["hours_lecture"] == 32
        assert d["credits"] == 4.0
        assert d["exam_form"] == "зачёт"

    def test_duplicate_link_returns_minus_one(self):
        c = next(conn())
        plan_id, disc_id = self.setup_plan(c)
        id1 = add_discipline_to_plan(c, plan_id, disc_id, semester=1)
        assert id1 > 0
        id2 = add_discipline_to_plan(c, plan_id, disc_id, semester=1)
        assert id2 == -1

    def test_same_discipline_different_semester(self):
        """Одна дисциплина в одном плане, но в разных семестрах — допустимо."""
        c = next(conn())
        plan_id, disc_id = self.setup_plan(c)
        id1 = add_discipline_to_plan(c, plan_id, disc_id, semester=1)
        id2 = add_discipline_to_plan(c, plan_id, disc_id, semester=2)
        assert id1 > 0
        assert id2 > 0
        assert id1 != id2

        disc_list = get_disciplines_for_plan(c, plan_id)
        assert len(disc_list) == 2


# ---- Поиск ----


class TestFindPlan:
    def test_find_plan_by_params(self):
        c = next(conn())
        dir_id = add_direction(c, "09.03.01", "ИВТ", "бакалавриат")
        prof_id = add_profile(c, "ПО ВТ и АС")
        plan_id = add_study_plan(c, 2025, "очная", dir_id, prof_id)

        found = find_plan_id(c, 2025, "очная", "09.03.01", "ПО ВТ и АС")
        assert found == plan_id

    def test_find_plan_without_profile(self):
        c = next(conn())
        dir_id = add_direction(c, "09.03.01", "ИВТ", "бакалавриат")
        plan_id = add_study_plan(c, 2025, "заочная", dir_id, None)

        found = find_plan_id(c, 2025, "заочная", "09.03.01", None)
        assert found == plan_id

    def test_find_plan_not_found(self):
        c = next(conn())
        found = find_plan_id(c, 9999, "очная", "00.00.00")
        assert found is None


# ---- Индексы ----


class TestSchema:
    def test_tables_exist(self):
        c = next(conn())
        tables = c.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        table_names = [r[0] for r in tables]
        assert "directions" in table_names
        assert "profiles" in table_names
        assert "study_plans" in table_names
        assert "disciplines" in table_names
        assert "disciplines_in_plans" in table_names

    def test_indexes_exist(self):
        c = next(conn())
        indexes = c.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
        ).fetchall()
        index_names = [r[0] for r in indexes]
        assert "idx_disciplines_in_plans_plan" in index_names
        assert "idx_disciplines_in_plans_discipline" in index_names


# pytest требуется для запуска
import pytest