#!/usr/bin/env python3
"""Extract metadata from each study plan PDF."""
import subprocess, os, glob

pdf_dir = os.path.dirname(os.path.abspath(__file__))
for pdf_path in sorted(glob.glob(os.path.join(pdf_dir, "*.pdf"))):
    fname = os.path.basename(pdf_path)
    result = subprocess.run(
        ["pdftotext", "-layout", pdf_path, "-"],
        capture_output=True, text=True
    )
    text = result.stdout

    year_begin = ""
    m = __import__('re').search(r'Год начала подготовки:\s*(\d+)', text)
    if m: year_begin = m.group(1)

    direction = ""
    m = __import__('re').search(r'Направление подготовки\s+([\d.]+)', text)
    if m: direction = m.group(1)

    form = ""
    m = __import__('re').search(r'Форма обучения\s*[-–—]\s*(\w+)', text)
    if m: form = m.group(1)

    profile = ""
    m = __import__('re').search(r'(?:Профиль|Направленность)\s+"([^"]*)"', text)
    if m: profile = m.group(1)

    level = ""
    m = __import__('re').search(r'Программа подготовки:\s*(\w+)', text)
    if m: level = m.group(1)

    print(f"{fname}|{year_begin}|{direction}|{level}|{form}|{profile}")