import yaml
import os
from typing import List, Dict, Optional

# Пути к данным
DATA_DIR = "data"
DISCIPLINES_FILE = os.path.join(DATA_DIR, "disciplines.yaml")

def load_disciplines() -> List[Dict]:
    """Загружает список всех дисциплин из YAML файла."""
    if not os.path.exists(DISCIPLINES_FILE):
        return []
    
    with open(DISCIPLINES_FILE, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
        return data.get('disciplines', []) if data else []

def save_disciplines(disciplines: List[Dict]):
    """Сохраняет список дисциплин в YAML файл."""
    data = {'disciplines': disciplines}
    with open(DISCIPLINES_FILE, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False)

def get_discipline_by_code(code: str) -> Optional[Dict]:
    """Ищет одну дисциплину по её коду."""
    disciplines = load_disciplines()
    for d in disciplines:
        if d.get('code') == code:
            return d
    return None

def validate_discipline_hours(discipline: Dict) -> bool:
    """
    Проверяет консистентность часов: 
    Сумма всех видов работ должна быть равна total.
    """
    hours = discipline.get('hours', {})
    total = hours.get('total', 0)
    
    sum_hours = (
        hours.get('lecture', 0) +
        hours.get('practice', 0) +
        hours.get('laboratory', 0) +
        hours.get('srs', 0) +
        hours.get('attestation', 0)
    )
    
    return sum_hours == total

def check_all_disciplines():
    """Проверяет все дисциплины в базе на ошибки в часах."""
    disciplines = load_disciplines()
    errors = []
    
    for d in disciplines:
        if not validate_discipline_hours(d):
            errors.append(f"Ошибка в часах дисциплины {d.get('code')} {d.get('name')}: "
                          f"сумма {sum(d.get('hours', {}).values()) - d.get('hours', {}).get('total', 0)} "
                          f"не совпадает с total={d.get('hours', {}).get('total')}")
    
    return errors

if __name__ == "__main__":
    # Простой тест при запуске скрипта напрямую
    print("Проверка базы данных дисциплин...")
    errs = check_all_disciplines()
    if not errs:
        print("✅ Все дисциплины валидны.")
    else:
        for e in errs:
            print(f"❌ {e}")
