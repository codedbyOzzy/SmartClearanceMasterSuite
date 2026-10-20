# -*- coding: utf-8 -*-
"""
config.py — SmartClearance Motoru Dosya Yolları ve Sabitleri
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# SmartClearance verileri kullanıcı yerel uygulama dizininde saklanır
DATA_DIR = Path(os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))) / "SmartClearance"
DATA_DIR.mkdir(parents=True, exist_ok=True)

RUNS_DIR = DATA_DIR / "runs"
RUNS_DIR.mkdir(parents=True, exist_ok=True)

# Evrim Beyanname Şablonu
TEMPLATE_XLSX = DATA_DIR / "sablon.xlsx"
BUNDLED_DEFAULT_TEMPLATE = BASE_DIR / "assets" / "sablon_varsayilan.xlsx"

# Master Ürün Kataloğu
MASTER_KATALOG_XLSX = DATA_DIR / "master_katalog.xlsx"

# Master'a Eklenecek Ürünler Şablonu
EKLENECEK_TEMPLATE_XLSX = DATA_DIR / "eklenecek_sablon.xlsx"
BUNDLED_EKLENECEK_TEMPLATE = BASE_DIR / "assets" / "eklenecek_sablon_varsayilan.xlsx"

# Web ve Şablon Yolları
TEMPLATES_DIR = BASE_DIR / "web" / "templates"
STATIC_DIR = BASE_DIR / "web" / "static"
REGULATIONS_DIR = BASE_DIR / "regulations"
