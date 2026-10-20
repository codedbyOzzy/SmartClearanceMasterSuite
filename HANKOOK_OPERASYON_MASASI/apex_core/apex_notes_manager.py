"""
apex_notes_manager.py — SmartClearance Apex Kalıcı Operasyon Günlüğü & Not Defteri
"""

import os
import json
import uuid
from datetime import datetime

DEFAULT_NOTES_FILE = r"C:\HANKOOK_OPERASYON_MASASI\operasyon_notlari.json"


class ApexNotesManager:
    """Her dosya veya PO için zaman damgalı notları kalıcı olarak yönetir."""

    def __init__(self, file_path=DEFAULT_NOTES_FILE):
        self.file_path = file_path
        self._data = {}
        self.load()

    def _make_key(self, dosya_no, po):
        d = str(dosya_no or "").strip()
        p = str(po or "").strip()
        if d and d != "—":
            return f"DOSYA_{d}"
        if p and p != "—":
            return f"PO_{p}"
        return "GENEL"

    def load(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except Exception:
                self._data = {}
        else:
            self._data = {}

    def save(self):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def get_notes(self, dosya_no, po):
        key = self._make_key(dosya_no, po)
        # Eğer dosya key'inde yoksa PO key'ine de bak
        if key.startswith("DOSYA_") and key not in self._data and po and po != "—":
            alt_key = f"PO_{po}"
            if alt_key in self._data:
                return self._data[alt_key]
        return self._data.get(key, [])

    def add_note(self, dosya_no, po, text, tag="Genel", stage=""):
        if not text or not text.strip():
            return None
        key = self._make_key(dosya_no, po)
        if key not in self._data:
            self._data[key] = []

        note = {
            "id": str(uuid.uuid4())[:8],
            "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "author": "Operasyon",
            "tag": tag,
            "stage": stage,
            "text": text.strip()
        }
        # En yeni not en başta görünsün
        self._data[key].insert(0, note)
        self.save()
        return note

    def update_note(self, dosya_no, po, note_id, new_text, new_tag=None):
        key = self._make_key(dosya_no, po)
        # Check alternate PO key if needed
        if key not in self._data and po and po != "—":
            alt_key = f"PO_{po}"
            if alt_key in self._data:
                key = alt_key

        if key in self._data:
            for n in self._data[key]:
                if n.get("id") == note_id:
                    n["text"] = new_text.strip()
                    if new_tag:
                        n["tag"] = new_tag
                    n["updated_at"] = datetime.now().strftime("%d.%m.%Y %H:%M")
                    self.save()
                    return True
        return False

    def delete_note(self, dosya_no, po, note_id):
        key = self._make_key(dosya_no, po)
        # Check alternate PO key if needed
        if key not in self._data and po and po != "—":
            alt_key = f"PO_{po}"
            if alt_key in self._data:
                key = alt_key

        if key in self._data:
            self._data[key] = [n for n in self._data[key] if n.get("id") != note_id]
            if not self._data[key]:
                del self._data[key]
            self.save()
            return True
        return False

    def clear_all_notes(self, dosya_no, po):
        key = self._make_key(dosya_no, po)
        removed = False
        if key in self._data:
            del self._data[key]
            removed = True
        if po and po != "—":
            alt_key = f"PO_{po}"
            if alt_key in self._data:
                del self._data[alt_key]
                removed = True
        if removed:
            self.save()
        return removed

    def has_notes(self, dosya_no, po):
        notes = self.get_notes(dosya_no, po)
        return len(notes) > 0

    def get_last_note_summary(self, dosya_no, po):
        notes = self.get_notes(dosya_no, po)
        if notes:
            n = notes[0]
            return f"[{n.get('tag', 'Not')}] {n.get('text', '')[:45]}..."
        return ""
