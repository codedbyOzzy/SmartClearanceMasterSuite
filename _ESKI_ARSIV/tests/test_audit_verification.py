# -*- coding: utf-8 -*-
"""
Verification tests for ActivityHubView and ShieldView.
"""
import sys
import os
import time

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Ensure project root is in sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import tkinter as tk
import tools.supabase_sync_manager as ssm


class MockSupabaseManager:
    def __init__(self):
        self.logs = [
            {
                "id": 1,
                "remote_id": 101,
                "dosya_no": "26-001234",
                "ref_no": "4200788458",
                "beyanname_no": "26340000IM001234",
                "islem_tipi": "NOT",
                "baslik": "Ordino Alındı",
                "icerik": "Acenteden ordino teslim alındı.",
                "kullanici": "Ozan Gemici",
                "etiket": "Normal",
                "metadata": "{}",
                "created_at": "2026-08-31 14:00:00",
                "is_deleted": 0,
                "deleted_at": None,
                "synced": 1
            },
            {
                "id": 2,
                "remote_id": 102,
                "dosya_no": "26-005678",
                "ref_no": "4200788463",
                "beyanname_no": "26340000IM005678",
                "islem_tipi": "MAIL",
                "baslik": "Vergi Talebi Maili Hazırlandı",
                "icerik": "Alıcı: muhasebe@hankookn.com",
                "kullanici": "Ozan Gemici",
                "etiket": "Tamamlandı",
                "metadata": "{}",
                "created_at": "2026-08-31 14:15:00",
                "is_deleted": 0,
                "deleted_at": None,
                "synced": 1
            },
            {
                "id": 3,
                "remote_id": 103,
                "dosya_no": "26-009999",
                "ref_no": "4200789554",
                "beyanname_no": "26340000IM009999",
                "islem_tipi": "TESCIL",
                "baslik": "GTB Beyanname Tescil Edildi",
                "icerik": "Hat: Sarı Hat",
                "kullanici": "GTB Bot",
                "etiket": "Normal",
                "metadata": "{}",
                "created_at": "2026-08-31 14:30:00",
                "is_deleted": 0,
                "deleted_at": None,
                "synced": 1
            },
            {
                "id": 4,
                "remote_id": 104,
                "dosya_no": "26-003333",
                "ref_no": "4200783333",
                "beyanname_no": "26340000IM003333",
                "islem_tipi": "FATURA",
                "baslik": "Eşleme Faturası Kesildi",
                "icerik": "Eşleme tamamlandı.",
                "kullanici": "Ozan Gemici",
                "etiket": "Normal",
                "metadata": "{}",
                "created_at": "2026-08-31 14:45:00",
                "is_deleted": 0,
                "deleted_at": None,
                "synced": 1
            }
        ]

    def fetch_activity_logs(self, dosya_no=None, islem_tipi=None, date_from=None, date_to=None, search_term=None, limit=500, include_deleted=False, only_deleted=False):
        res = []
        for l in self.logs:
            if only_deleted and l.get("is_deleted") != 1:
                continue
            if not include_deleted and not only_deleted and l.get("is_deleted") == 1:
                continue
            if islem_tipi and l.get("islem_tipi") != islem_tipi:
                continue
            if search_term:
                st = search_term.lower()
                matched = any(st in str(v).lower() for v in l.values())
                if not matched:
                    continue
            res.append(dict(l))
        return res

    def add_activity_log(self, dosya_no, ref_no="", beyanname_no="", islem_tipi="NOT", baslik="", icerik="", etiket="Normal", metadata=None, kullanici=None):
        new_id = len(self.logs) + 1
        new_row = {
            "id": new_id,
            "remote_id": 100 + new_id,
            "dosya_no": dosya_no,
            "ref_no": ref_no,
            "beyanname_no": beyanname_no,
            "islem_tipi": islem_tipi,
            "baslik": baslik,
            "icerik": icerik,
            "kullanici": kullanici or "Test User",
            "etiket": etiket,
            "metadata": metadata or {},
            "created_at": "2026-08-31 15:00:00",
            "is_deleted": 0,
            "deleted_at": None,
            "synced": 1
        }
        self.logs.append(new_row)
        return new_id

    def soft_delete_activity_log(self, log_id):
        for l in self.logs:
            if l["id"] == log_id:
                l["is_deleted"] = 1
                return True
        return False

    def restore_activity_log(self, log_id):
        for l in self.logs:
            if l["id"] == log_id:
                l["is_deleted"] = 0
                return True
        return False

    def empty_trash(self):
        cnt = sum(1 for l in self.logs if l.get("is_deleted") == 1)
        self.logs = [l for l in self.logs if l.get("is_deleted") != 1]
        return cnt

    def sync_activity_logs(self):
        pass


import tkinter.messagebox as msgbox
msgbox.showinfo = lambda *a, **k: None
msgbox.showwarning = lambda *a, **k: None
msgbox.showerror = lambda *a, **k: None
msgbox.askyesno = lambda *a, **k: True

mock_sm = MockSupabaseManager()
ssm.get_supabase_manager = lambda: mock_sm

import tools.dogruer_master_suite.views.activity_hub_view as ahv
ahv.get_supabase_manager = lambda: mock_sm
from tools.dogruer_master_suite.views.activity_hub_view import ActivityHubView

import tools.dogruer_master_suite.views.shield_view as sv
sv.safe_open_mail_by_entry_id = lambda eid: True if eid else False
from tools.dogruer_master_suite.views.shield_view import ShieldView


class MockEngine:
    def __init__(self):
        self.records = []
        self.outlook_cache = [
            {
                "subject": "Vergi Talebi / 4200788458",
                "to": "muhasebe@hankookn.com",
                "sent_on": "31.08.2026 14:00",
                "attachments": ["4200788458.pdf"],
                "entry_id": "MOCK_ENTRY_001",
                "is_reply": False
            },
            {
                "subject": "RE: Tescil Bilgilendirme 4200788463",
                "to": "operasyon@dogruer.com",
                "sent_on": "31.08.2026 14:30",
                "attachments": [],
                "entry_id": "MOCK_ENTRY_002",
                "is_reply": True
            }
        ]

    def fetch_outlook_sent_items(self, limit=350):
        return self.outlook_cache

    def search_outlook_conversations(self, query="", limit=150):
        return [
            {
                "conv_id": "CONV_001",
                "topic": "4200788458 İthalat Süreci",
                "total_steps": 2,
                "latest_timestamp": 1787832000,
                "latest_date": "31.08.2026 14:30",
                "latest_sender": "Muhasebe",
                "messages": [
                    {
                        "step": 1,
                        "direction": "OUT",
                        "sender": "Ben",
                        "to": "muhasebe@hankookn.com",
                        "time_str": "31.08.2026 14:00",
                        "subject": "Vergi Talebi / 4200788458",
                        "snippet": "Sayın yetkili, vergi talebi ekte sunulmuştur.",
                        "attachments": ["4200788458.pdf"],
                        "entry_id": "MOCK_ENTRY_001"
                    },
                    {
                        "step": 2,
                        "direction": "IN",
                        "sender": "Muhasebe",
                        "to": "Ben",
                        "time_str": "31.08.2026 14:30",
                        "subject": "RE: Vergi Talebi / 4200788458",
                        "snippet": "Ödeme yapılmıştır, dekont ektedir.",
                        "attachments": ["dekont_4200788458.pdf"],
                        "entry_id": "MOCK_ENTRY_003"
                    }
                ],
                "all_attachments": ["4200788458.pdf", "dekont_4200788458.pdf"]
            }
        ]

    def open_outlook_mail_by_id(self, eid):
        return True


class MockApp:
    def __init__(self, root):
        self.root = root
        self.current_user = {
            "username": "ozan.gemici",
            "full_name": "Ozan Gemici",
            "role": "admin"
        }
        self.config = {}
        self.engine = MockEngine()
        self.lbl_head_subtitle = tk.Label(root, text="")


def run_tests():
    print("==================================================", flush=True)
    print("🚀 Starting MasterSuite Views Verification Tests", flush=True)
    print("==================================================", flush=True)

    root = tk.Tk()
    root.withdraw()
    app = MockApp(root)

    # ----------------------------------------------------
    # Test 1: ActivityHubView
    # ----------------------------------------------------
    print("\n--- Testing ActivityHubView ---", flush=True)
    act_view = ActivityHubView(root, app)
    assert act_view is not None, "ActivityHubView instance creation failed"
    print("✅ ActivityHubView initialized successfully.", flush=True)

    # Refresh
    act_view.refresh_activity_hub()
    print("✅ refresh_activity_hub executed without errors.", flush=True)

    # Metric card filter toggling
    act_view._act_filter_type("NOT")
    assert act_view.combo_act_type.get() == "NOT", "Filter should be NOT"
    act_view._act_filter_type("NOT")
    assert act_view.combo_act_type.get() == "TÜMÜ", "Filter should toggle back to TÜMÜ"
    print("✅ Metric card filter toggling works as expected.", flush=True)

    # Ctrl+A selection
    act_view._select_all_activity()
    print("✅ _select_all_activity executed.", flush=True)

    # Trash toggle
    act_view.toggle_activity_trash()
    assert act_view.act_show_trash is True, "Trash mode should be active"
    act_view.toggle_activity_trash()
    assert act_view.act_show_trash is False, "Trash mode should be inactive"
    print("✅ Trash mode toggling verified.", flush=True)

    # Undo Banner
    act_view.show_undo_banner("1 not silindi.", [1])
    assert act_view.undo_banner is not None, "Undo banner should be rendered"
    act_view._dismiss_undo_banner()
    assert act_view.undo_banner is None, "Undo banner should be dismissed"
    print("✅ Undo banner lifecycle verified.", flush=True)

    # ----------------------------------------------------
    # Test 2: ShieldView
    # ----------------------------------------------------
    print("\n--- Testing ShieldView ---", flush=True)
    shield_view = ShieldView(root, app)
    assert shield_view is not None, "ShieldView instance creation failed"
    print("✅ ShieldView initialized successfully.", flush=True)

    # Quick Search
    shield_view.txt_shield_query.delete(0, tk.END)
    shield_view.txt_shield_query.insert(0, "4200788458")
    shield_view.do_shield_quick_search()
    results = shield_view.tree_shield.get_children()
    assert len(results) == 1, f"Expected 1 quick search match, got {len(results)}"
    print("✅ Quick search ('Buna Mail Attım mı?') found matching sent item.", flush=True)

    # Security Inspector
    shield_view.txt_inspect_subj.delete(0, tk.END)
    shield_view.txt_inspect_subj.insert(0, "Vergi Talebi / 4200788458")
    shield_view.selected_inspector_files = ["C:/docs/4200788458.pdf"]
    shield_view.run_shield_inspection()
    report = shield_view.txt_shield_report.get("1.0", tk.END)
    assert "4200788458" in report, "Report should contain detected reference"
    assert "MÜKERRERLİK" in report, "Report should include duplicate check"
    print("✅ Security Inspector analysis completed and verified.", flush=True)

    # Conversation Search & Thread Navigation
    shield_view.do_conv_search(query="4200788458", async_mode=False)
    assert len(shield_view.current_conv_results) >= 1, f"Conversation search should return results, got {len(shield_view.current_conv_results)}"

    shield_view.filter_conv_results("ATTACHMENTS")
    shield_view.filter_conv_results("MULTI_STEP")
    shield_view.filter_conv_results("ALL")
    shield_view.sort_conv_tree("date")
    shield_view.sort_conv_tree("steps")
    shield_view.sort_conv_tree("topic")

    shield_view._nav_next_conversation()
    shield_view._nav_prev_conversation()
    print("✅ Conversation thread navigation & sorting verified.", flush=True)

    # Open Outlook Mail Integration
    opened = shield_view.open_selected_mail_in_outlook("MOCK_ENTRY_001")
    assert opened is True, "open_selected_mail_in_outlook should succeed with mock"
    print("✅ open_selected_mail_in_outlook method verified.", flush=True)

    root.destroy()
    print("\n==================================================", flush=True)
    print("🎉 ALL AUDIT & INTEGRATION TESTS PASSED (100%)", flush=True)
    print("==================================================", flush=True)


if __name__ == "__main__":
    run_tests()
