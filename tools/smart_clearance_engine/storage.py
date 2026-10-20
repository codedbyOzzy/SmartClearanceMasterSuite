# -*- coding: utf-8 -*-
"""
storage.py — SmartClearance Motoru Dosya ve Şablon Depolama Yöneticisi
"""
import os
import re
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from tools.smart_clearance_engine.config import (
    RUNS_DIR,
    TEMPLATE_XLSX, BUNDLED_DEFAULT_TEMPLATE,
    MASTER_KATALOG_XLSX,
    EKLENECEK_TEMPLATE_XLSX, BUNDLED_EKLENECEK_TEMPLATE,
)

_RUN_ID_RE = re.compile(r"^[A-Za-z0-9_]+$")
MAX_RUNS = 50

def new_run_dir():
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:6]
    run_dir = RUNS_DIR / run_id
    (run_dir / "uploads").mkdir(parents=True, exist_ok=True)
    (run_dir / "outputs").mkdir(parents=True, exist_ok=True)
    _prune_old_runs()
    return run_id, run_dir

def _prune_old_runs():
    try:
        run_dirs = sorted((d for d in RUNS_DIR.iterdir() if d.is_dir()), key=lambda d: d.name)
        for old_dir in run_dirs[:max(len(run_dirs) - MAX_RUNS, 0)]:
            shutil.rmtree(old_dir, ignore_errors=True)
    except Exception:
        pass

def run_dir_for(run_id):
    if not _RUN_ID_RE.match(run_id or ""):
        raise ValueError("Geçersiz işlem kimliği")
    d = RUNS_DIR / run_id
    if not d.exists():
        raise FileNotFoundError("Bu işlem artık bulunamıyor (silinmiş olabilir)")
    return d


def safe_output_path(run_dir, dosya_adi):
    """outputs/ altındaki indirme yolunu resolve + containment ile doğrular."""
    outputs = (Path(run_dir) / "outputs").resolve()
    name = Path(str(dosya_adi or "")).name
    if not name or name in (".", ".."):
        return None
    candidate = (outputs / name).resolve()
    try:
        candidate.relative_to(outputs)
    except ValueError:
        return None
    if not candidate.is_file():
        return None
    return candidate

def _save(uploaded_path, dest_path, prefix):
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    gecici = dest_path.with_name(f".{dest_path.name}.tmp-{uuid.uuid4().hex[:8]}")
    try:
        shutil.copy2(uploaded_path, gecici)
        gecici.replace(dest_path)
    finally:
        gecici.unlink(missing_ok=True)

def _ensure(dest_path, bundled_path):
    if not dest_path.exists() and bundled_path.exists():
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(bundled_path, dest_path)

def template_exists():
    return TEMPLATE_XLSX.exists()

def ensure_template():
    _ensure(TEMPLATE_XLSX, BUNDLED_DEFAULT_TEMPLATE)

def save_template(uploaded_path):
    _save(uploaded_path, TEMPLATE_XLSX, "sablon")

def master_katalog_exists():
    return MASTER_KATALOG_XLSX.exists()

def save_master_katalog(uploaded_path):
    _save(uploaded_path, MASTER_KATALOG_XLSX, "master_katalog")

def eklenecek_template_exists():
    return EKLENECEK_TEMPLATE_XLSX.exists()

def ensure_eklenecek_template():
    _ensure(EKLENECEK_TEMPLATE_XLSX, BUNDLED_EKLENECEK_TEMPLATE)

def save_eklenecek_template(uploaded_path):
    _save(uploaded_path, EKLENECEK_TEMPLATE_XLSX, "eklenecek_sablon")
