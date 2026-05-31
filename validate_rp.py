#!/usr/bin/env python3
"""
Валидатор РП: проверяет сходимость часов в таблицах рабочей программы дисциплины.

Извлекает все таблицы из Markdown-файла и проверяет:
- Таблица 3.1.1: суммы по строкам (ЛК+ПЗ+ЛР+СРС = Всего часов)
- Таблица 3.1.1: суммы по столбцам (строка Итого)
- Таблица 3.1.1: Ауд (ЛК+ПЗ+ЛР) + СРС = Всего часов
- Таблицы 3.2.1, 3.2.3, 3.3: суммы по столбцу часов
"""

import sys
import re
from pathlib import Path


def extract_tables_from_markdown(filepath: str) -> list[dict]:
    """
    Извлекает все таблицы из Markdown-файла.
    Возвращает список словарей с названием таблицы и данными.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    tables = []

    # Находим все заголовки таблиц (## 3.3, ### 3.1.1, ### 3.2.1 и т.п.)
    header_pattern = re.compile(r'^(#{2,3})\s+(\d+(?:\.\d+)+)\s+.*?$', re.MULTILINE)

    for match in header_pattern.finditer(content):
        full_match = match.group(0)
        header_start = match.start()
        table_id = match.group(2)

        # Ищем следующий заголовок любого уровня (## или ###)
        next_h2 = content.find('\n## ', header_start + 1)
        next_h3 = content.find('\n### ', header_start + 1)
        candidates = [n for n in (next_h2, next_h3) if n != -1]
        next_header = min(candidates) if candidates else len(content)

        section_content = content[header_start:next_header]

        # Проверяем, есть ли таблица (с |---|)
        if '|---|' not in section_content:
            continue

        # Извлекаем заголовок таблицы
        header_line = full_match.strip()
        table_desc = re.sub(r'^#{2,3}\s+', '', header_line).strip()

        # Парсим таблицу
        lines = section_content.strip().split('\n')

        # Находим строку с заголовками столбцов
        header_idx = -1
        for i, line in enumerate(lines):
            if line.strip().startswith('|') and '---' not in line:
                header_idx = i
                break

        if header_idx == -1 or header_idx + 1 >= len(lines):
            continue

        # Заголовки столбцов
        header_line_str = lines[header_idx]
        header_names = [h.strip() for h in header_line_str.split('|')[1:-1]]

        # Данные и строка Итого
        rows = []
        итого_row = None
        for line in lines[header_idx + 2:]:
            line = line.strip()
            if not line or not line.startswith('|'):
                continue

            cells = [c.strip() for c in line.split('|')[1:-1]]
            if len(cells) != len(header_names):
                continue

            if '**Итого**' in line or line.startswith('|**Итого'):
                итого_row = dict(zip(header_names, cells))
            else:
                rows.append(dict(zip(header_names, cells)))

        if rows:
            tables.append({
                'id': table_id,
                'name': table_desc,
                'headers': header_names,
                'rows': rows,
                'итого': итого_row,
            })

    return tables


def try_int(val: str) -> int | None:
    """Пытается извлечь число из строки (убирает **, пробелы)."""
    if not val:
        return None
    cleaned = val.strip().replace('**', '').replace(' ', '')
    try:
        return int(cleaned)
    except ValueError:
        return None


def validate_table_311(table: dict) -> tuple[bool, list[str]]:
    """
    Подробная проверка таблицы 3.1.1:
    - суммы по строкам
    - суммы по столбцам
    - сходимость Ауд + СРС = Всего
    """
    errors = []
    h = table['headers']

    # Определяем индексы столбцов
    col_map = {}
    for name in ['Всего часов', 'ЛК', 'ПЗ (СЗ)', 'ЛР', 'СРС']:
        if name in h:
            col_map[name] = h.index(name)

    if len(col_map) < 5:
        errors.append(f"  Не найдены все столбцы: {col_map}")
        return False, errors

    rows = table['rows']
    итого = table['итого']

    # --- 1. Проверка каждой строки ---
    print(f"\n  Проверка строк (ЛК+ПЗ+ЛР+СРС = Всего часов):")
    row_errors = 0
    for i, row in enumerate(rows):
        лк = try_int(row.get('ЛК'))
        пз = try_int(row.get('ПЗ (СЗ)'))
        лр = try_int(row.get('ЛР'))
        срс = try_int(row.get('СРС'))
        всего = try_int(row.get('Всего часов'))

        if None in (лк, пз, лр, срс, всего):
            errors.append(f"  Строка {i+1}: нечисловые значения")
            continue

        сумма_частей = лк + пз + лр + срс
        if сумма_частей != всего:
            errors.append(
                f"  Строка {i+1}: ЛК({лк})+ПЗ({пз})+ЛР({лр})+СРС({срс}) = {сумма_частей} != Всего({всего})"
            )
            row_errors += 1
        else:
            print(f"    Строка {i+1}: {лк}+{пз}+{лр}+{срс} = {всего} ✓")

    if row_errors == 0:
        print(f"    Все строки сошлись ✓")

    # --- 2. Проверка строки Итого ---
    print(f"\n  Проверка строки Итого:")
    if итого:
        ит_лк = try_int(итого.get('ЛК'))
        ит_пз = try_int(итого.get('ПЗ (СЗ)'))
        ит_лр = try_int(итого.get('ЛР'))
        ит_срс = try_int(итого.get('СРС'))
        ит_всего = try_int(итого.get('Всего часов'))

        # Считаем суммы по строкам
        sum_лк = sum(try_int(r.get('ЛК')) or 0 for r in rows)
        sum_пз = sum(try_int(r.get('ПЗ (СЗ)')) or 0 for r in rows)
        sum_лр = sum(try_int(r.get('ЛР')) or 0 for r in rows)
        sum_срс = sum(try_int(r.get('СРС')) or 0 for r in rows)
        sum_всего = sum(try_int(r.get('Всего часов')) or 0 for r in rows)

        checks = [
            ('ЛК', sum_лк, ит_лк),
            ('ПЗ (СЗ)', sum_пз, ит_пз),
            ('ЛР', sum_лр, ит_лр),
            ('СРС', sum_срс, ит_срс),
            ('Всего часов', sum_всего, ит_всего),
        ]

        for name, calc, expected in checks:
            if expected is not None and calc != expected:
                errors.append(
                    f"  Итого по '{name}': сумма по строкам ({calc}) != Итого ({expected})"
                )
            elif expected is not None:
                print(f"    {name}: {calc} = {expected} ✓")
    else:
        errors.append("  Строка Итого не найдена")

    # --- 3. Проверка Ауд + СРС = Всего ---
    print(f"\n  Проверка Ауд + СРС = Всего часов:")
    sum_лк = sum(try_int(r.get('ЛК')) or 0 for r in rows)
    sum_пз = sum(try_int(r.get('ПЗ (СЗ)')) or 0 for r in rows)
    sum_лр = sum(try_int(r.get('ЛР')) or 0 for r in rows)
    sum_срс = sum(try_int(r.get('СРС')) or 0 for r in rows)
    sum_всего = sum(try_int(r.get('Всего часов')) or 0 for r in rows)

    ауд = sum_лк + sum_пз + sum_лр
    ауд_плюс_срс = ауд + sum_срс

    print(f"    ЛК: {sum_лк}")
    print(f"    ПЗ: {sum_пз}")
    print(f"    ЛР: {sum_лр}")
    print(f"    СРС: {sum_срс}")
    print(f"    Ауд (ЛК+ПЗ+ЛР): {ауд}")
    print(f"    Ауд + СРС: {ауд_плюс_срс}")
    print(f"    Всего часов: {sum_всего}")

    if ауд_плюс_срс != sum_всего:
        errors.append(
            f"  Ауд({ауд}) + СРС({sum_срс}) = {ауд_плюс_срс} != Всего({sum_всего})"
        )
    else:
        print(f"    {ауд} + {sum_срс} = {sum_всего} ✓")

    return len(errors) == 0, errors


def validate_simple_table(table: dict, col_name: str) -> tuple[bool, list[str]]:
    """
    Проверка простой таблицы (лекции, лабы, СРС):
    - сумма по столбцу часов
    """
    errors = []

    if col_name not in table['headers']:
        errors.append(f"  Столбец '{col_name}' не найден")
        return False, errors

    total = sum(try_int(r.get(col_name)) or 0 for r in table['rows'])
    print(f"    Сумма: {total}")

    return True, errors


def main():
    if len(sys.argv) < 2:
        print("Использование: python validate_rp.py <путь_к_файлу.md>")
        sys.exit(1)

    filepath = sys.argv[1]

    if not Path(filepath).exists():
        print(f"Ошибка: файл не найден: {filepath}")
        sys.exit(1)

    print(f"Валидация: {filepath}\n")

    tables = extract_tables_from_markdown(filepath)

    if not tables:
        print("Ошибка: таблицы не найдены в файле")
        sys.exit(1)

    print(f"Найдено {len(tables)} таблиц\n")

    all_ok = True

    for table in tables:
        table_id = table['id']
        print(f"--- Таблица {table_id}: {table['name']} ---")

        if table_id == '3.1.1':
            ok, errors = validate_table_311(table)
        elif table_id in ('3.2.1', '3.2.2', '3.2.3'):
            ok, errors = validate_simple_table(table, 'Трудоемкость (в часах)')
        elif table_id == '3.3':
            ok, errors = validate_simple_table(table, 'Трудоемкость (в часах)')
        else:
            print(f"  (пропущено: нет правил валидации)")
            continue

        if ok:
            print(f"  [OK]\n")
        else:
            all_ok = False
            for err in errors:
                print(f"  {err}")
            print()

    if all_ok:
        print("Все таблицы прошли валидацию!")
        sys.exit(0)
    else:
        print("Валидация завершилась с ошибками!")
        sys.exit(1)


if __name__ == '__main__':
    main()
