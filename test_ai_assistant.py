# -*- coding: utf-8 -*-
"""
test_ai_assistant.py — SmartClearance Gemini AI Danışmanı Test Çalıştırıcısı
Sistemi açmadan doğrudan AI Asistan penceresini açıp denemenizi sağlar.
"""
import sys
import os
import tkinter as tk

# Proje ana dizinini sys.path'e ekle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.dogruer_master_suite.views.ai_assistant_view import AIAssistantView

class MockApp:
    def __init__(self, root):
        self.root = root
        self.config = {}
        self.engine = None
        self.current_user = {"username": "admin", "full_name": "Test Operatör", "role": "admin"}
        self._closed = False

    def is_alive(self):
        return not self._closed

def main():
    root = tk.Tk()
    root.title("SmartClearance — Gemini AI Operasyon Danışmanı (Demo)")
    root.geometry("900x700")
    root.minsize(800, 600)
    root.configure(bg="#f8fafc")

    app = MockApp(root)
    view = AIAssistantView(root, app)
    view.pack(fill=tk.BOTH, expand=True)

    def on_closing():
        app._closed = True
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
