"""
PAKET_OLUSTUR.py
==================
MasterSuite'i başka bilgisayarda Python KURULMADAN çalışacak
Taşınabilir Paket olarak hazırlar.

Sonuç: Masaüstünde DogruerMasterSuite_Portable\ klasörü + ZIP
"""
import sys
import os
import shutil
import zipfile
import urllib.request
import subprocess
from pathlib import Path

# ─── AYARLAR ──────────────────────────────────────────────────────────────────
CALISMA_PYTHON = sys.executable
PYTHON_DIR     = Path(CALISMA_PYTHON).parent
SOURCE_TOOLS   = Path(r"C:\Users\ozan.gemici\OneDrive - DOGRUER GUMRUK MUSAVIRLIGI A.Ş\Belgeler\V1SmartClearance_Gumruk\tools")
DESKTOP        = Path(os.path.expanduser("~")) / "Desktop"
CIKTI_KLASORU  = DESKTOP / "DogruerMasterSuite_Portable"

EMBED_URL = "https://www.python.org/ftp/python/3.12.8/python-3.12.8-embed-amd64.zip"
EMBED_ZIP = DESKTOP / "python_embed_dl.zip"
EMBED_DIR = CIKTI_KLASORU / "python-embed"

PAKETLER = [
    "openpyxl",
    "pywin32",
    "pywebview",
    "requests",
    "beautifulsoup4",
    "lxml",
    "sv_ttk",
    "pillow",
    "pypdf",
]


def adim(n, baslik):
    print(f"\n{'='*60}")
    print(f"  Adim {n}: {baslik}")
    print(f"{'='*60}")


def indir(url, hedef):
    if Path(hedef).exists():
        print(f"  [ATLA] Zaten mevcut: {Path(hedef).name}")
        return
    print(f"  Indiriliyor: {url}")
    last_pct = [0]
    def hook(b, bs, t):
        if t > 0:
            pct = min(b * bs * 100 // t, 100)
            if pct != last_pct[0]:
                print(f"\r  {pct}%", end="", flush=True)
                last_pct[0] = pct
    urllib.request.urlretrieve(url, hedef, reporthook=hook)
    print()


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print("\n" + "=" * 60)
    print("  DOGRUER MASTERSUITE - TASИНABILIR PAKET OLUSTURUCU")
    print("=" * 60)

    # ── Adim 1: Klasor yapisi
    adim(1, "Cikti klasoru hazirlaniyor")
    if CIKTI_KLASORU.exists():
        print(f"  Eski klasor siliniyor: {CIKTI_KLASORU}")
        shutil.rmtree(CIKTI_KLASORU)
    CIKTI_KLASORU.mkdir(parents=True)
    EMBED_DIR.mkdir(parents=True)
    print(f"  Klasor olusturuldu: {CIKTI_KLASORU}")

    # ── Adim 2: Python Embeddable indir + cikar
    adim(2, "Python 3.12 Embeddable indiriliyor")
    indir(EMBED_URL, EMBED_ZIP)
    print(f"  Aciliyor: {EMBED_ZIP} -> {EMBED_DIR}")
    with zipfile.ZipFile(EMBED_ZIP, "r") as z:
        z.extractall(EMBED_DIR)
    print("  Python Embed cikarildi!")

    # ── Adim 3: python312._pth duzenle (site-packages aktif et)
    adim(3, "Python Embed yapilandiriliyor")
    pth_file = EMBED_DIR / "python312._pth"
    if pth_file.exists():
        content = pth_file.read_text(encoding="utf-8")
        content = content.replace("#import site", "import site")
        content += "\n..\\Lib\\site-packages\n"
        pth_file.write_text(content, encoding="utf-8")
        print(f"  {pth_file.name} duzenlendi (site-packages aktif)")

    # ── Adim 4: tkinter dosyalarini kopyala
    adim(4, "tkinter dosyalari kopyalaniyor")
    tk_src = PYTHON_DIR / "Lib" / "tkinter"
    tk_dst = CIKTI_KLASORU / "Lib" / "tkinter"
    if tk_src.exists():
        shutil.copytree(tk_src, tk_dst, dirs_exist_ok=True)
        print(f"  tkinter/ kopyalandi")
    else:
        print(f"  UYARI: tkinter klasoru bulunamadi: {tk_src}")

    # tkinter icin DLL'ler
    dll_search_dirs = [PYTHON_DIR / "DLLs", PYTHON_DIR]
    for dll_name in ["_tkinter.pyd", "tcl90.dll", "tk90.dll", "tcl86.dll", "tk86.dll"]:
        for search_dir in dll_search_dirs:
            src_dll = search_dir / dll_name
            if src_dll.exists():
                shutil.copy2(src_dll, EMBED_DIR / dll_name)
                print(f"  {dll_name} kopyalandi")
                break

    # tcl/tk veri klasorleri (kritik: EMBED_DIR altında olmalı)
    for tk_data in ["tcl", "tk"]:
        src_d = PYTHON_DIR.parent / "tcl" / tk_data
        if not src_d.exists():
            src_d = PYTHON_DIR / tk_data
        if src_d.exists():
            shutil.copytree(src_d, CIKTI_KLASORU / tk_data, dirs_exist_ok=True)
            print(f"  {tk_data}/ kopyalandi")

    # ── Adim 5: pip kur
    adim(5, "pip embed Python icerisine kuruluyor")
    get_pip_url = "https://bootstrap.pypa.io/get-pip.py"
    get_pip_path = CIKTI_KLASORU / "get-pip.py"
    indir(get_pip_url, get_pip_path)
    embed_py = EMBED_DIR / "python.exe"
    result = subprocess.run(
        [str(embed_py), str(get_pip_path), "--no-warn-script-location"],
        capture_output=True, text=True, encoding="utf-8", errors="ignore"
    )
    if result.returncode == 0:
        print("  pip basariyla kuruldu!")
    else:
        print(f"  pip hata: {result.stderr[-300:]}")

    # ── Adim 6: Paketleri kur
    adim(6, "Gerekli Python paketleri kuruluyor")
    site_packages = CIKTI_KLASORU / "Lib" / "site-packages"
    site_packages.mkdir(parents=True, exist_ok=True)

    for paket in PAKETLER:
        print(f"  pip install {paket}...", end=" ", flush=True)
        result = subprocess.run(
            [str(embed_py), "-m", "pip", "install", paket,
             "--target", str(site_packages),
             "--no-warn-script-location", "-q"],
            capture_output=True, text=True, encoding="utf-8", errors="ignore"
        )
        if result.returncode == 0:
            print("OK")
        else:
            print(f"HATA: {result.stderr[-100:]}")

    # pywin32 post-install
    pywin32_postinstall = list(site_packages.glob("**/pywin32_postinstall.py"))
    if pywin32_postinstall:
        subprocess.run(
            [str(embed_py), str(pywin32_postinstall[0]), "-install", "-silent"],
            capture_output=True
        )
        print("  pywin32 post-install tamamlandi")

    # sv_ttk icin
    sv_ttk_src = Path(CALISMA_PYTHON).parent / "Lib" / "site-packages" / "sv_ttk"
    if sv_ttk_src.exists() and not (site_packages / "sv_ttk").exists():
        shutil.copytree(sv_ttk_src, site_packages / "sv_ttk", dirs_exist_ok=True)
        print("  sv_ttk kopyalandi (tema)")

    # ── Adim 7: MasterSuite kaynak dosyalari
    adim(7, "MasterSuite kaynak dosyalari kopyalaniyor")
    tools_dst = CIKTI_KLASORU / "tools"
    tools_dst.mkdir(exist_ok=True)

    gerekli_klasorler = [
        "dogruer_master_suite",
        "kantar_engine",
        "gtb_engine",
        "telegram_bridge",
    ]
    for klasor in gerekli_klasorler:
        src = SOURCE_TOOLS / klasor
        dst = tools_dst / klasor
        if src.exists():
            shutil.copytree(src, dst, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", ".git"))
            print(f"  tools/{klasor}/ kopyalandi")
        else:
            print(f"  UYARI: {src} bulunamadi")

    # ── Adim 8: BASLAT.bat
    adim(8, "BASLAT.bat olusturuluyor")
    baslat = "@echo off\r\nsetlocal enabledelayedexpansion\r\ncd /d \"%~dp0\"\r\ntitle Dogruer MasterSuite\r\n\r\necho ================================================\r\necho   Dogruer SmartClearance MasterSuite\r\necho   Dogruer Gumruk Musavirligi A.S.\r\necho ================================================\r\necho.\r\n\r\nset \"PY=python-embed\\python.exe\"\r\n\r\nif not exist \"%PY%\" (\r\n    echo HATA: python-embed\\python.exe bulunamadi!\r\n    echo Bu klasoru eksiksiz kopyaladiginizdan emin olun.\r\n    pause\r\n    exit /b 1\r\n)\r\n\r\necho Sistem baslatiliyor...\r\necho.\r\n\r\nset TCL_LIBRARY=%~dp0tcl\r\nset TK_LIBRARY=%~dp0tk\r\nset PYTHONPATH=%~dp0Lib\\site-packages;%~dp0tools\r\n\r\n\"%PY%\" tools\\dogruer_master_suite\\master_suite.py\r\n\r\necho.\r\necho Sistem kapatildi.\r\npause\r\n"
    (CIKTI_KLASORU / "BASLAT.bat").write_bytes(baslat.encode("utf-8"))
    print("  BASLAT.bat olusturuldu")

    # OKUBENI.txt
    readme = "Dogruer MasterSuite - Tasınabilir Versiyon\r\n==========================================\r\nKULLANIM:\r\n1. Bu klasoru herhangi bir yere kopyalayin\r\n2. BASLAT.bat dosyasina cift tiklayin\r\n3. Python veya baska bir kurulum GEREKMEZ!\r\n\r\nNOT: OneDrive, Masaustu gibi senkronize klasorler yerine\r\n     D:\\DogruerMasterSuite gibi yerel bir konuma kopyalayin.\r\n"
    (CIKTI_KLASORU / "OKUBENI.txt").write_bytes(readme.encode("utf-8"))

    # ── Adim 9: ZIP olustur
    adim(9, "ZIP arsivi olusturuluyor (bu biraz surebilir...)")
    zip_yolu = DESKTOP / "DogruerMasterSuite_Portable.zip"
    if zip_yolu.exists():
        zip_yolu.unlink()
    with zipfile.ZipFile(zip_yolu, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        file_count = 0
        for dosya in CIKTI_KLASORU.rglob("*"):
            if dosya.is_file():
                arcname = dosya.relative_to(CIKTI_KLASORU.parent)
                zf.write(dosya, arcname)
                file_count += 1
                if file_count % 500 == 0:
                    print(f"  {file_count} dosya eklendi...", end="\r")
    zip_mb = zip_yolu.stat().st_size / 1024 / 1024
    print(f"\n  ZIP olusturuldu: {zip_yolu}")
    print(f"  ZIP Boyutu: {zip_mb:.1f} MB ({file_count} dosya)")

    print("\n" + "=" * 60)
    print("  TAMAMLANDI!")
    print(f"  Klasor: {CIKTI_KLASORU}")
    print(f"  ZIP   : {zip_yolu}")
    print("  Arkadasiniza bu ZIP dosyasini gonderin.")
    print("  Acip BASLAT.bat'a cift tiklamasi yeterli!")
    print("=" * 60)

    os.startfile(str(DESKTOP))


if __name__ == "__main__":
    main()
