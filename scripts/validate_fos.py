#!/usr/bin/env python3
"""
validate_fos.py — проверка соответствия ФОС и РП.

Использование:
    python3 scripts/validate_fos.py docs/РП.БазыДанных.2025.md docs/ФОС.БазыДанных.2025.md

Проверяет:
  1. YAML-шапки (все общие поля должны совпадать)
  2. Набор компетенций (ОПК-*, ПК-*, УК-*)
  3. Форму промежуточной аттестации (экзамен / зачёт)
"""

import re
import sys
import yaml

# ─── вспомогательные ──────────────────────────────────────────────


def read_yaml(path: str) -> dict:
    """Извлекает YAML frontmatter из .md файла."""
    with open(path, encoding="utf-8") as f:
        content = f.read()
    # YAML между --- и ---
    m = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not m:
        raise ValueError(f"Не найден YAML frontmatter в {path}")
    return yaml.safe_load(m.group(1))


def read_body(path: str) -> str:
    """Возвращает тело файла (без YAML frontmatter)."""
    with open(path, encoding="utf-8") as f:
        content = f.read()
    m = re.match(r"^---\s*\n.*?\n---\s*\n", content, re.DOTALL)
    if m:
        return content[m.end():]
    return content


def find_competencies(text: str) -> set[str]:
    """Ищет коды компетенций вида ОПК-1, ПК-3, УК-2."""
    codes = set()
    for match in re.finditer(r"\b(ОПК|ПК|УК)-\d+", text):
        codes.add(match.group(0))
    return codes


def find_attestation_form(text: str) -> str | None:
    """Определяет форму аттестации: 'Экзамен' или 'Зачёт'."""
    # Ищем маркеры в sections, где говорится об аттестации
    # Приоритет — слово целиком в контексте формы контроля
    patterns = {
        "Экзамен": r"\bЭкзамен\b",
        "Зачёт":   r"\bЗачёт\b",
        "Зачет":   r"\bЗачет\b",
    }
    for form, pat in patterns.items():
        if re.search(pat, text):
            # Нормализуем Зачет → Зачёт
            return "Зачёт" if form in ("Зачёт", "Зачет") else form
    return None


# ─── проверки ─────────────────────────────────────────────────────


def check_yaml(rp: dict, fos: dict) -> list[str]:
    """Сравнение общих полей YAML-шапок."""
    common_fields: list[tuple[str, str, str]] = [
        ("Код дисциплины",   rp.get("discipline", {}).get("code"),
                              fos.get("discipline", {}).get("code")),
        ("Название дисциплины", rp.get("discipline", {}).get("name"),
                                fos.get("discipline", {}).get("name")),
        ("Часы",             rp.get("discipline", {}).get("hours"),
                              fos.get("discipline", {}).get("hours")),
        ("ЗЕТ",              rp.get("discipline", {}).get("credits"),
                              fos.get("discipline", {}).get("credits")),
        ("Код направления",  rp.get("direction", {}).get("code"),
                              fos.get("direction", {}).get("code")),
        ("Название направления", rp.get("direction", {}).get("name"),
                                 fos.get("direction", {}).get("name")),
        ("Профиль",          rp.get("profile"),
                              fos.get("profile")),
        ("Год набора",       rp.get("year"),
                              fos.get("year")),
        ("Форма обучения",   rp.get("form_of_study"),
                              fos.get("form_of_study")),
        ("Семестр",          rp.get("semester"),
                              fos.get("semester")),
        ("Университет",      rp.get("university"),
                              fos.get("university")),
        ("Факультет",        rp.get("faculty"),
                              fos.get("faculty")),
        ("Кафедра",          rp.get("department"),
                              fos.get("department")),
        ("Разработчик",      rp.get("developer"),
                              fos.get("developer")),
    ]

    errors: list[str] = []
    for name, rv, fv in common_fields:
        if rv != fv:
            errors.append(
                f"  ❌ {name}: РП = «{rv}»  ≠  ФОС = «{fv}»"
            )
    return errors


def check_competencies(rp_text: str, fos_text: str) -> list[str]:
    """Сверка набора компетенций."""
    rp_codes = find_competencies(rp_text)
    fos_codes = find_competencies(fos_text)

    errors: list[str] = []
    only_in_rp = rp_codes - fos_codes
    only_in_fos = fos_codes - rp_codes

    if only_in_rp:
        errors.append(
            f"  ❌ Компетенции есть в РП, но отсутствуют в ФОС: "
            f"{', '.join(sorted(only_in_rp))}"
        )
    if only_in_fos:
        errors.append(
            f"  ❌ Компетенции есть в ФОС, но отсутствуют в РП: "
            f"{', '.join(sorted(only_in_fos))}"
        )
    if not only_in_rp and not only_in_fos:
        codes_str = ", ".join(sorted(rp_codes)) if rp_codes else "(не найдены)"
        errors.append(f"  ✅ Компетенции совпадают: {codes_str}")

    return errors


def check_attestation(rp_text: str, fos_text: str) -> list[str]:
    """Проверка совпадения формы аттестации."""
    rp_form = find_attestation_form(rp_text)
    fos_form = find_attestation_form(fos_text)

    errors: list[str] = []
    if rp_form is None:
        errors.append("  ⚠️  Не удалось определить форму аттестации в РП")
        return errors
    if fos_form is None:
        errors.append("  ⚠️  Не удалось определить форму аттестации в ФОС")
        return errors

    if rp_form != fos_form:
        errors.append(
            f"  ❌ Форма аттестации: РП = «{rp_form}»  ≠  ФОС = «{fos_form}»"
        )
    else:
        errors.append(f"  ✅ Форма аттестации совпадает: «{rp_form}»")

    return errors


# ─── main ─────────────────────────────────────────────────────────


def main():
    if len(sys.argv) != 3:
        print("Использование: python3 scripts/validate_fos.py <путь_к_РП.md> <путь_к_ФОС.md>")
        sys.exit(1)

    rp_path, fos_path = sys.argv[1], sys.argv[2]
    exit_code = 0

    # YAML
    print("── 1. YAML-шапки ──")
    try:
        rp_yaml = read_yaml(rp_path)
        fos_yaml = read_yaml(fos_path)
        errors = check_yaml(rp_yaml, fos_yaml)
        for e in errors:
            print(e)
        if not errors:
            print("  ✅ Все поля совпадают")
        else:
            exit_code = 1
    except Exception as exc:
        print(f"  ❌ Ошибка чтения YAML: {exc}")
        exit_code = 1

    # Компетенции
    print("\n── 2. Компетенции ──")
    try:
        rp_body = read_body(rp_path)
        fos_body = read_body(fos_path)
        errors = check_competencies(rp_body, fos_body)
        for e in errors:
            print(e)
        if any(e.startswith("  ❌") for e in errors):
            exit_code = 1
    except Exception as exc:
        print(f"  ❌ Ошибка: {exc}")
        exit_code = 1

    # Форма аттестации
    print("\n── 3. Форма промежуточной аттестации ──")
    try:
        errors = check_attestation(rp_body, fos_body)
        for e in errors:
            print(e)
        if any(e.startswith("  ❌") for e in errors):
            exit_code = 1
    except Exception as exc:
        print(f"  ❌ Ошибка: {exc}")
        exit_code = 1

    print()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()