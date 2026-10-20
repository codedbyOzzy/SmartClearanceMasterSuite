"""
main.py — Hankook Gümrük Operasyon Masası
Çalıştır: python main.py
"""

import sys
import traceback
import os

LOG_FILE = r"C:\HANKOOK_OPERASYON_MASASI\hata_log.txt"

def main():
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QFont
    from app.main_window import MainWindow

    app = QApplication(sys.argv)
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    try:
        main()
    except Exception:
        err = traceback.format_exc()
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write(err)
        print("HATA OLUŞTU — Log dosyasına yazıldı:")
        print(LOG_FILE)
        print()
        print(err)
        input("Devam etmek için Enter'a basın...")
