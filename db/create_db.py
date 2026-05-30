"""
create_db.py — создание и наполнение SQLite БД дисциплин по учебным планам.

Назначение
----------
Скрипт создаёт/обновляет файл `disciplines.db` — единое хранилище
дисциплин и учебных планов для проекта CoursePlanMaker. БД позволяет
хранить дисциплины с учётом различий по:
- форме обучения (очная / заочная)
- году набора
- направлению подготовки (09.03.01 и т.п.)
- уровню образования (бакалавриат / магистратура)
- профилю подготовки

Схема БД
---------
Пять таблиц:

1. directions — справочник направлений подготовки
   - code (уник.) — шифр, напр. 09.03.01
   - name — полное название
   - level — уровень: бакалавриат / магистратура

2. profiles — справочник профилей (может быть NULL, если у направления
   нет разделения на профили)

3. study_plans — учебные планы. Одна запись = уникальная комбинация
   (год, форма обучения, направление, профиль).

4. disciplines — справочник дисциплин (код + название). Код может быть
   NULL, если дисциплина временная или без шифра.

5. disciplines_in_plans — связка «дисциплина в учебном плане».
   Хранит все параметры: семестр, часы по видам занятий, ЗЕТ,
   форму аттестации. Одна дисциплина может быть привязана к разным
   планам с разными часами и семестрами.

Функции для наполнения
-----------------------
- add_direction(conn, code, name, level) — добавить направление
- add_profile(conn, name) — добавить профиль
- add_study_plan(conn, year, form, direction_id, profile_id) — добавить
  учебный план (возвращает id существующего при дубликате)
- add_discipline(conn, code, name) — добавить дисциплину
- add_discipline_to_plan(conn, plan_id, discipline_id, ...) — привязать
  дисциплину к плану с часами, семестром и формой аттестации

Функции для чтения
-------------------
- get_study_plans(conn) — список всех учебных планов
- get_disciplines_for_plan(conn, plan_id) — дисциплины конкретного плана
- find_plan_id(conn, year, form, direction_code, profile_name) — найти
  ID плана по параметрам

Запуск
------
    python3 db/create_db.py

При первом запуске создаёт БД и наполняет тестовыми данными.
При повторном — обновляет схему (CREATE TABLE IF NOT EXISTS)
и дописывает данные, не удаляя существующие.

Зависимости: только стандартная библиотека Python (sqlite3, os).
"""

import sqlite3
import os

DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, "disciplines.db")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS directions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    code        TEXT    NOT NULL UNIQUE,
    name        TEXT    NOT NULL,
    level       TEXT    NOT NULL CHECK (level IN ('бакалавриат', 'магистратура'))
);

CREATE TABLE IF NOT EXISTS profiles (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT    NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS study_plans (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    year         INTEGER NOT NULL,
    form         TEXT    NOT NULL CHECK (form IN ('очная', 'заочная')),
    direction_id INTEGER NOT NULL REFERENCES directions(id),
    profile_id   INTEGER REFERENCES profiles(id),
    UNIQUE(year, form, direction_id, profile_id)
);

CREATE TABLE IF NOT EXISTS disciplines (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT    UNIQUE,
    name TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS disciplines_in_plans (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id        INTEGER NOT NULL REFERENCES study_plans(id),
    discipline_id  INTEGER NOT NULL REFERENCES disciplines(id),
    semester       INTEGER NOT NULL,
    hours_total    INTEGER DEFAULT 0,
    hours_lecture  INTEGER DEFAULT 0,
    hours_practice  INTEGER DEFAULT 0,
    hours_lab      INTEGER DEFAULT 0,
    hours_self_study INTEGER DEFAULT 0,
    hours_exam     INTEGER DEFAULT 0,
    credits        REAL    DEFAULT 0,
    exam_form      TEXT    CHECK (exam_form IN ('зачёт', 'экзамен', 'зачёт с оценкой')),
    UNIQUE(plan_id, discipline_id, semester)
);

CREATE INDEX IF NOT EXISTS idx_disciplines_in_plans_plan
    ON disciplines_in_plans(plan_id);

CREATE INDEX IF NOT EXISTS idx_disciplines_in_plans_discipline
    ON disciplines_in_plans(discipline_id);
"""


def create_db(path: str | None = None) -> sqlite3.Connection:
    """Создать/открыть БД и применить схему."""
    db_path = path or DB_PATH
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    return conn


# ---- Вспомогательные функции для вставки/чтения ----


def add_direction(
    conn: sqlite3.Connection, code: str, name: str, level: str
) -> int:
    row = conn.execute(
        "SELECT id FROM directions WHERE code = ?", (code,)
    ).fetchone()
    if row:
        return row[0]
    cur = conn.execute(
        "INSERT INTO directions (code, name, level) VALUES (?, ?, ?)",
        (code, name, level),
    )
    return cur.lastrowid


def add_profile(conn: sqlite3.Connection, name: str) -> int:
    row = conn.execute(
        "SELECT id FROM profiles WHERE name = ?", (name,)
    ).fetchone()
    if row:
        return row[0]
    cur = conn.execute(
        "INSERT INTO profiles (name) VALUES (?)", (name,)
    )
    return cur.lastrowid


def add_study_plan(
    conn: sqlite3.Connection,
    year: int,
    form: str,
    direction_id: int,
    profile_id: int | None = None,
) -> int:
    try:
        cur = conn.execute(
            """INSERT INTO study_plans (year, form, direction_id, profile_id)
               VALUES (?, ?, ?, ?)""",
            (year, form, direction_id, profile_id),
        )
        return cur.lastrowid
    except sqlite3.IntegrityError:
        row = conn.execute(
            """SELECT id FROM study_plans
               WHERE year = ? AND form = ? AND direction_id = ?
               AND (profile_id = ? OR (profile_id IS NULL AND ? IS NULL))""",
            (year, form, direction_id, profile_id, profile_id),
        ).fetchone()
        return row[0] if row else -1


def add_discipline(conn: sqlite3.Connection, code: str | None, name: str) -> int:
    if code:
        row = conn.execute(
            "SELECT id FROM disciplines WHERE code = ?", (code,)
        ).fetchone()
        if row:
            return row[0]
    cur = conn.execute(
        "INSERT INTO disciplines (code, name) VALUES (?, ?)", (code, name)
    )
    return cur.lastrowid


def add_discipline_to_plan(
    conn: sqlite3.Connection,
    plan_id: int,
    discipline_id: int,
    semester: int,
    hours_total: int = 0,
    hours_lecture: int = 0,
    hours_practice: int = 0,
    hours_lab: int = 0,
    hours_self_study: int = 0,
    hours_exam: int = 0,
    credits: float = 0,
    exam_form: str | None = None,
) -> int:
    try:
        cur = conn.execute(
            """INSERT INTO disciplines_in_plans
               (plan_id, discipline_id, semester, hours_total,
                hours_lecture, hours_practice, hours_lab,
                hours_self_study, hours_exam, credits, exam_form)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                plan_id, discipline_id, semester,
                hours_total, hours_lecture, hours_practice, hours_lab,
                hours_self_study, hours_exam, credits, exam_form,
            ),
        )
        return cur.lastrowid
    except sqlite3.IntegrityError:
        return -1


# ---- Чтение ----


def get_study_plans(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """SELECT sp.id, sp.year, sp.form,
                  d.code AS dir_code, d.name AS dir_name, d.level,
                  p.name AS profile_name
           FROM study_plans sp
           JOIN directions d ON d.id = sp.direction_id
           LEFT JOIN profiles p ON p.id = sp.profile_id
           ORDER BY sp.year DESC, sp.form, d.code"""
    ).fetchall()
    return [
        {
            "id": r[0],
            "year": r[1],
            "form": r[2],
            "direction_code": r[3],
            "direction_name": r[4],
            "level": r[5],
            "profile": r[6],
        }
        for r in rows
    ]


def get_disciplines_for_plan(
    conn: sqlite3.Connection, plan_id: int
) -> list[dict]:
    rows = conn.execute(
        """SELECT dp.id, d.code, d.name, dp.semester,
                  dp.hours_total, dp.hours_lecture, dp.hours_practice,
                  dp.hours_lab, dp.hours_self_study, dp.hours_exam,
                  dp.credits, dp.exam_form
           FROM disciplines_in_plans dp
           JOIN disciplines d ON d.id = dp.discipline_id
           WHERE dp.plan_id = ?
           ORDER BY dp.semester, d.code""",
        (plan_id,),
    ).fetchall()
    return [
        {
            "id": r[0],
            "code": r[1],
            "name": r[2],
            "semester": r[3],
            "hours_total": r[4],
            "hours_lecture": r[5],
            "hours_practice": r[6],
            "hours_lab": r[7],
            "hours_self_study": r[8],
            "hours_exam": r[9],
            "credits": r[10],
            "exam_form": r[11],
        }
        for r in rows
    ]


def find_plan_id(
    conn: sqlite3.Connection,
    year: int,
    form: str,
    direction_code: str,
    profile_name: str | None = None,
) -> int | None:
    """
    Найти ID учебного плана по параметрам.
    """
    row = conn.execute(
        """SELECT sp.id
           FROM study_plans sp
           JOIN directions d ON d.id = sp.direction_id
           LEFT JOIN profiles p ON p.id = sp.profile_id
           WHERE sp.year = ? AND sp.form = ? AND d.code = ?
           AND (p.name = ? OR (p.name IS NULL AND ? IS NULL))""",
        (year, form, direction_code, profile_name, profile_name),
    ).fetchone()
    return row[0] if row else None


STUDY_PLANS = [
    # (год_набора, форма, код_направления, название_направления, уровень, профиль)
    (2023, "очная",   "09.03.01", "Информатика и вычислительная техника", "бакалавриат", "Программное обеспечение вычислительной техники и автоматизированных систем"),
    (2023, "заочная", "09.03.01", "Информатика и вычислительная техника", "бакалавриат", "Программное обеспечение вычислительной техники и автоматизированных систем"),
    (2024, "очная",   "09.03.01", "Информатика и вычислительная техника", "бакалавриат", "Автоматизированные системы и вычислительные машины в промышленных комплексах"),
    (2025, "очная",   "09.04.01", "Информатика и вычислительная техника", "магистратура", "Технологии разработки и сопровождения систем искусственного интеллекта"),
]


if __name__ == "__main__":
    conn = create_db()
    print(f"БД создана: {DB_PATH}")
    print()

    # ---- Наполнение из учебных планов ----
    for year, form, dir_code, dir_name, level, profile_name in STUDY_PLANS:
        dir_id = add_direction(conn, dir_code, dir_name, level)
        prof_id = add_profile(conn, profile_name) if profile_name else None
        plan_id = add_study_plan(conn, year, form, dir_id, prof_id)
        print(f"  Учебный план #{plan_id}: {year} / {form} / {dir_code} {dir_name} ({level})"
              + (f" / {profile_name}" if profile_name else ""))

    conn.commit()
    print()

    # ---- Вывод для проверки ----
    print("=== Итоговый перечень учебных планов ===")
    for plan in get_study_plans(conn):
        plan_id = plan["id"]
        print(f"План #{plan_id}: {plan['year']} г.н. / {plan['form']} / "
              f"{plan['direction_code']} {plan['direction_name']} ({plan['level']})"
              + (f" / {plan['profile']}" if plan["profile"] else ""))
        for disc in get_disciplines_for_plan(conn, plan_id):
            print(f"  [{disc['semester']} сем] {disc['code'] or '—'} "
                  f"{disc['name']} — {disc['hours_total']} ч, "
                  f"{disc['credits']} ЗЕТ, {disc['exam_form']}")
        print()
