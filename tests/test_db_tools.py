"""Тесты для scripts/db_tools.py — работа с YAML-файлом дисциплин."""

import os
import sys
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Переопределяем пути ДО импорта модуля, чтобы тесты не трогали реальные файлы
import scripts.db_tools as db_tools


# ---- Фикстура: временная директория с YAML ----


def _patch_data_dir(data: dict):
    """Создать временную директорию с disciplines.yaml, подменить db_tools.DATA_DIR."""
    tmpdir = tempfile.mkdtemp()
    yaml_path = os.path.join(tmpdir, "disciplines.yaml")

    db_tools.DATA_DIR = tmpdir
    db_tools.DISCIPLINES_FILE = yaml_path

    if data is not None:
        import yaml
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)

    return tmpdir


# ---- load_disciplines ----


class TestLoadDisciplines:
    def test_load_empty_when_no_file(self):
        tmpdir = _patch_data_dir(None)
        try:
            disc = db_tools.load_disciplines()
            assert disc == []
        finally:
            shutil.rmtree(tmpdir)

    def test_load_empty_list(self):
        tmpdir = _patch_data_dir({"disciplines": []})
        try:
            disc = db_tools.load_disciplines()
            assert disc == []
        finally:
            shutil.rmtree(tmpdir)

    def test_load_one_discipline(self):
        data = {"disciplines": [{"code": "Б1.О.01", "name": "ТВП"}]}
        tmpdir = _patch_data_dir(data)
        try:
            disc = db_tools.load_disciplines()
            assert len(disc) == 1
            assert disc[0]["code"] == "Б1.О.01"
            assert disc[0]["name"] == "ТВП"
        finally:
            shutil.rmtree(tmpdir)

    def test_load_multiple_disciplines(self):
        data = {"disciplines": [
            {"code": "A", "name": "Alpha"},
            {"code": "B", "name": "Beta"},
        ]}
        tmpdir = _patch_data_dir(data)
        try:
            disc = db_tools.load_disciplines()
            assert len(disc) == 2
        finally:
            shutil.rmtree(tmpdir)


# ---- save_disciplines ----


class TestSaveDisciplines:
    def test_save_and_reload(self):
        tmpdir = _patch_data_dir({"disciplines": []})
        try:
            expected = [
                {"code": "Б1.О.01", "name": "ТВП"},
                {"code": None, "name": "Временная"},
            ]
            db_tools.save_disciplines(expected)
            loaded = db_tools.load_disciplines()
            assert loaded == expected
        finally:
            shutil.rmtree(tmpdir)

    def test_save_overwrites_old_data(self):
        tmpdir = _patch_data_dir({"disciplines": [{"code": "OLD", "name": "Старая"}]})
        try:
            db_tools.save_disciplines([{"code": "NEW", "name": "Новая"}])
            loaded = db_tools.load_disciplines()
            assert len(loaded) == 1
            assert loaded[0]["code"] == "NEW"
        finally:
            shutil.rmtree(tmpdir)


# ---- get_discipline_by_code ----


class TestGetDisciplineByCode:
    def test_find_existing(self):
        data = {"disciplines": [
            {"code": "A1", "name": "First"},
            {"code": "B2", "name": "Second"},
        ]}
        tmpdir = _patch_data_dir(data)
        try:
            disc = db_tools.get_discipline_by_code("B2")
            assert disc is not None
            assert disc["name"] == "Second"
        finally:
            shutil.rmtree(tmpdir)

    def test_find_missing(self):
        data = {"disciplines": [{"code": "A1", "name": "First"}]}
        tmpdir = _patch_data_dir(data)
        try:
            disc = db_tools.get_discipline_by_code("NONEXISTENT")
            assert disc is None
        finally:
            shutil.rmtree(tmpdir)

    def test_find_code_none(self):
        """Дисциплины с code=None — поиск по None должен находить."""
        data = {"disciplines": [
            {"code": None, "name": "Без кода"},
            {"code": "A1", "name": "С кодом"},
        ]}
        tmpdir = _patch_data_dir(data)
        try:
            disc = db_tools.get_discipline_by_code(None)
            assert disc is not None
            assert disc["name"] == "Без кода"
        finally:
            shutil.rmtree(tmpdir)


# ---- validate_discipline_hours ----


class TestValidateHours:
    def test_valid_hours(self):
        disc = {
            "hours": {
                "total": 144,
                "lecture": 32,
                "practice": 0,
                "laboratory": 32,
                "srs": 80,
                "attestation": 0,
            }
        }
        assert db_tools.validate_discipline_hours(disc) is True

    def test_invalid_hours(self):
        disc = {
            "hours": {
                "total": 100,
                "lecture": 32,
                "practice": 0,
                "laboratory": 32,
                "srs": 80,
                "attestation": 0,
            }
        }
        assert db_tools.validate_discipline_hours(disc) is False

    def test_zero_hours(self):
        disc = {
            "hours": {
                "total": 0,
                "lecture": 0,
                "practice": 0,
                "laboratory": 0,
                "srs": 0,
                "attestation": 0,
            }
        }
        assert db_tools.validate_discipline_hours(disc) is True

    def test_missing_fields_default_to_zero(self):
        """Пропущенные поля считаются как 0, сумма 32 < total 144 — невалидно."""
        disc = {"hours": {"total": 144, "lecture": 32}}
        assert db_tools.validate_discipline_hours(disc) is False


# ---- check_all_disciplines ----


class TestCheckAll:
    def test_no_errors_when_valid(self):
        data = {"disciplines": [
            {"code": "A", "name": "Alpha", "hours": {"total": 4, "lecture": 2, "practice": 0, "laboratory": 0, "srs": 2, "attestation": 0}},
            {"code": "B", "name": "Beta",  "hours": {"total": 8, "lecture": 4, "practice": 0, "laboratory": 0, "srs": 4, "attestation": 0}},
        ]}
        tmpdir = _patch_data_dir(data)
        try:
            errors = db_tools.check_all_disciplines()
            assert errors == []
        finally:
            shutil.rmtree(tmpdir)

    def test_errors_when_invalid(self):
        data = {"disciplines": [
            {"code": "A", "name": "Alpha", "hours": {"total": 10, "lecture": 2, "practice": 0, "laboratory": 0, "srs": 2, "attestation": 0}},
        ]}
        tmpdir = _patch_data_dir(data)
        try:
            errors = db_tools.check_all_disciplines()
            assert len(errors) == 1
            assert "A" in errors[0]
            assert "Alpha" in errors[0]
        finally:
            shutil.rmtree(tmpdir)

    def test_empty_list_no_errors(self):
        tmpdir = _patch_data_dir({"disciplines": []})
        try:
            errors = db_tools.check_all_disciplines()
            assert errors == []
        finally:
            shutil.rmtree(tmpdir)

    def test_missing_hours_considered_valid(self):
        """Дисциплина без поля 'hours' — все часы = 0, это валидно."""
        data = {"disciplines": [
            {"code": "X", "name": "NoHours"},
        ]}
        tmpdir = _patch_data_dir(data)
        try:
            errors = db_tools.check_all_disciplines()
            assert errors == []
        finally:
            shutil.rmtree(tmpdir)


import pytest