# -*- coding: utf-8 -*-
"""Odaklı birim testleri: atomik JSON, to_number, Telegram yetki, indirme yolu."""
import json
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TestStorageJson(unittest.TestCase):
    def test_atomic_write_and_load(self):
        from tools.storage_json import load_json, save_json_atomic

        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "recs.json")
            lock = threading.RLock()
            data = [{"beyanname_no": "ABC123"}]
            save_json_atomic(path, data, snapshot_lock=lock)
            loaded = load_json(path, default=[])
            self.assertEqual(loaded, data)
            self.assertTrue(os.path.exists(path))
            leftovers = [n for n in os.listdir(td) if n.startswith(".tmp_")]
            self.assertEqual(leftovers, [])

    def test_corrupt_file_returns_default(self):
        from tools.storage_json import load_json

        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "bad.json")
            with open(path, "w", encoding="utf-8") as f:
                f.write("{not json")
            self.assertEqual(load_json(path, default=[]), [])


class TestToNumber(unittest.TestCase):
    def test_us_and_tr(self):
        from tools.smart_clearance_engine.parsers.common import to_number

        self.assertEqual(to_number("13,519.053"), 13519.053)
        self.assertAlmostEqual(to_number("9.088,97"), 9088.97)
        self.assertAlmostEqual(to_number("1234,56"), 1234.56)
        self.assertIsNone(to_number(None))
        self.assertIsNone(to_number(""))


class TestTelegramAllowlist(unittest.TestCase):
    def test_unknown_chat_denied(self):
        from tools.telegram_bridge.telegram_bot_service import TelegramBotService

        svc = TelegramBotService.__new__(TelegramBotService)
        svc.config = {"authorized_chat_ids": [111], "authorized_usernames": ["ops"]}
        self.assertTrue(svc._is_chat_authorized(111))
        self.assertTrue(svc._is_chat_authorized("111"))
        self.assertTrue(svc._is_chat_authorized(999, username="ops"))
        self.assertFalse(svc._is_chat_authorized(999))
        self.assertFalse(svc._is_chat_authorized(999, username="stranger"))

    def test_empty_allowlist_denies_all(self):
        from tools.telegram_bridge.telegram_bot_service import TelegramBotService

        svc = TelegramBotService.__new__(TelegramBotService)
        svc.config = {"authorized_chat_ids": [], "authorized_usernames": []}
        self.assertFalse(svc._is_chat_authorized(1))


class TestSafeOutputPath(unittest.TestCase):
    def test_containment(self):
        from tools.smart_clearance_engine.storage import safe_output_path

        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            outputs = run_dir / "outputs"
            outputs.mkdir()
            good = outputs / "fatura.xlsx"
            good.write_bytes(b"ok")
            (run_dir / "secret.txt").write_text("nope", encoding="utf-8")

            self.assertEqual(safe_output_path(run_dir, "fatura.xlsx"), good.resolve())
            self.assertIsNone(safe_output_path(run_dir, "..\\secret.txt"))
            self.assertIsNone(safe_output_path(run_dir, "../secret.txt"))
            self.assertIsNone(safe_output_path(run_dir, "missing.xlsx"))


class TestAuthHash(unittest.TestCase):
    def test_legacy_and_pbkdf2(self):
        from tools.auth_manager import AuthManager

        legacy = AuthManager.hash_password_legacy("123456")
        self.assertTrue(AuthManager.verify_password("123456", legacy))
        self.assertFalse(AuthManager.verify_password("wrong", legacy))
        modern = AuthManager.hash_password("newpass99")
        self.assertTrue(modern.startswith("pbkdf2$"))
        self.assertTrue(AuthManager.verify_password("newpass99", modern))
        unsalted = __import__("hashlib").sha256(b"123456").hexdigest()
        self.assertFalse(AuthManager.verify_password("123456", unsalted))


class TestCloudSyncRules(unittest.TestCase):
    def test_tombstone_and_lww(self):
        from tools.cloud_sync import is_tombstone, remote_is_newer, parse_ts

        self.assertTrue(is_tombstone({"durum": "TOMBSTONE"}))
        self.assertTrue(is_tombstone({"gtb_durum": "TOMBSTONE"}))
        self.assertFalse(is_tombstone({"durum": "⏳ Tartım Bekliyor"}))
        older = {"updated_at": "2026-01-01T10:00:00"}
        newer = {"updated_at": "2026-09-03T10:00:00"}
        self.assertTrue(remote_is_newer(newer, "01.01.2026 10:00"))
        self.assertFalse(remote_is_newer(older, "03.09.2026 12:00"))
        self.assertGreater(parse_ts("03.09.2026 12:00"), parse_ts("01.01.2026 10:00"))


class TestAuthGate(unittest.TestCase):
    def test_missing_auth_does_not_open_admin(self):
        from tools.dogruer_master_suite.auth_gate import resolve_startup_user

        self.assertIsNone(resolve_startup_user(None, lambda: None))
        self.assertIsNone(resolve_startup_user(lambda: {"username": "x"}, None))

    def test_login_exception_does_not_open_admin(self):
        from tools.dogruer_master_suite.auth_gate import resolve_startup_user

        def boom():
            raise RuntimeError("dialog crashed")

        self.assertIsNone(resolve_startup_user(boom, object))

    def test_cancel_returns_none(self):
        from tools.dogruer_master_suite.auth_gate import resolve_startup_user

        self.assertIsNone(resolve_startup_user(lambda: None, object))
        self.assertIsNone(resolve_startup_user(lambda: {}, object))

    def test_success_returns_user(self):
        from tools.dogruer_master_suite.auth_gate import resolve_startup_user

        user = {"username": "ozan", "role": "admin"}
        self.assertEqual(resolve_startup_user(lambda: user, object), user)


class TestKantarTelegramAllowlist(unittest.TestCase):
    def test_no_hardcoded_chat_id_in_source(self):
        from pathlib import Path

        src = Path(__file__).resolve().parents[1] / "tools" / "kantar_engine" / "kantar_tracker_service.py"
        text = src.read_text(encoding="utf-8")
        self.assertNotIn("7931396367", text)
        self.assertIn("authorized_chat_ids", text)

    def test_empty_allowlist_does_not_send(self):
        from tools.kantar_engine.kantar_tracker_service import KantarTrackerService

        class FakeTg:
            config = {"authorized_chat_ids": []}
            sent = []

            def send_message(self, cid, msg):
                self.sent.append((cid, msg))

            def send_document(self, cid, path, caption=None):
                self.sent.append((cid, caption))

        svc = KantarTrackerService.__new__(KantarTrackerService)
        svc.telegram_service = FakeTg()
        svc._send_telegram_kantar_alert("TEST123", "1", "bugün", "34ABC", "FIRMA", "1000", None)
        self.assertEqual(FakeTg.sent, [])

    def test_sends_only_to_allowlist(self):
        from tools.kantar_engine.kantar_tracker_service import KantarTrackerService

        class FakeTg:
            config = {"authorized_chat_ids": [111, 222]}
            sent = []

            def send_message(self, cid, msg):
                self.sent.append(cid)

        svc = KantarTrackerService.__new__(KantarTrackerService)
        svc.telegram_service = FakeTg()
        svc._send_telegram_kantar_alert("TEST123", "1", "bugün", "34ABC", "FIRMA", "1000", None)
        self.assertEqual(FakeTg.sent, [111, 222])


class TestSecretsNotInSource(unittest.TestCase):
    FORBIDDEN = (
        "8865057176",
        "AAGxv2FV8Xt8WnqPK",
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
        "kdzijyslkammvznxbpdj",
    )

    def test_tools_and_templates_have_no_live_secrets(self):
        root = Path(__file__).resolve().parents[1]
        scan = list(root.joinpath("tools").rglob("*")) + list(root.joinpath("data_templates").rglob("*"))
        skip_suffix = {".pyc", ".png", ".jpg", ".pdf", ".exe"}
        for path in scan:
            if not path.is_file() or path.suffix.lower() in skip_suffix:
                continue
            if "site-packages" in path.parts or "python-embed" in str(path):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for needle in self.FORBIDDEN:
                self.assertNotIn(needle, text, msg=str(path))

    def test_empty_secrets_file_does_not_invent_token(self):
        import tools.secrets_store as ss

        with tempfile.TemporaryDirectory() as td:
            old_dir, old_path, old_cache = ss.CONFIG_DIR, ss.SECRETS_PATH, ss._cache
            try:
                ss.CONFIG_DIR = td
                ss.SECRETS_PATH = os.path.join(td, "secrets.json")
                ss._cache = None
                self.assertEqual(ss.get_secret("telegram_bot_token"), "")
                self.assertFalse(os.path.exists(ss.SECRETS_PATH))
            finally:
                ss.CONFIG_DIR = old_dir
                ss.SECRETS_PATH = old_path
                ss._cache = old_cache


class TestExcelReadGuard(unittest.TestCase):
    def test_lock_error_detection(self):
        from tools.dogruer_master_suite.engine.excel_read_guard import is_excel_lock_error

        self.assertTrue(is_excel_lock_error(PermissionError("denied")))
        self.assertTrue(is_excel_lock_error(OSError("WinError 32 The process cannot access")))
        self.assertFalse(is_excel_lock_error(ValueError("bad cell")))

    def test_prune_skip_rules(self):
        from tools.dogruer_master_suite.engine.excel_read_guard import should_skip_hankook_prune

        self.assertTrue(should_skip_hankook_prune(False, 40, 40))
        self.assertTrue(should_skip_hankook_prune(True, 0, 12))
        self.assertTrue(should_skip_hankook_prune(True, 4, 20))
        self.assertFalse(should_skip_hankook_prune(True, 18, 20))


class TestHankookPruneFlag(unittest.TestCase):
    def test_prune_missing_false_skips_delete(self):
        from tools.supabase_sync_manager import SupabaseSyncManager

        sm = SupabaseSyncManager.__new__(SupabaseSyncManager)
        calls = []

        def _request(method, path, data=None, extra_headers=None):
            calls.append((method, path))
            return {"ok": True}

        sm._request = _request
        sm.fetch_all_rows = lambda *a, **k: [{"id": 99, "referans": "OLD / X"}]
        recs = [{"dosya": "D1", "ref": "R1", "stage_title": "İşlemde"}]
        self.assertTrue(sm.sync_hankook_board(recs, prune_missing=False))
        self.assertFalse(any(m == "DELETE" for m, _ in calls))
        self.assertTrue(any(m == "POST" and "on_conflict" not in p for m, p in calls))
        calls.clear()
        self.assertTrue(sm.sync_hankook_board(recs, prune_missing=True))
        self.assertTrue(any(m == "DELETE" for m, _ in calls))

    def test_existing_row_is_patched_not_on_conflict(self):
        from tools.supabase_sync_manager import SupabaseSyncManager, plan_hankook_board_writes

        patches, inserts, dups = plan_hankook_board_writes(
            [{"referans": "D1 / R1", "gemi": "X"}],
            [{"id": 7, "referans": "D1 / R1"}, {"id": 3, "referans": "D1 / R1"}],
        )
        self.assertEqual(len(patches), 1)
        self.assertEqual(patches[0][0], "7")
        self.assertEqual(inserts, [])
        self.assertEqual(dups, ["3"])

        sm = SupabaseSyncManager.__new__(SupabaseSyncManager)
        calls = []

        def _request(method, path, data=None, extra_headers=None):
            calls.append((method, path))
            return True

        sm._request = _request
        sm.fetch_all_rows = lambda *a, **k: [{"id": 7, "referans": "D1 / R1"}]
        self.assertTrue(sm.sync_hankook_board(
            [{"dosya": "D1", "ref": "R1", "gemi": "EVER"}],
            prune_missing=False,
        ))
        self.assertTrue(any(m == "PATCH" and "id=eq.7" in p for m, p in calls))
        self.assertFalse(any("on_conflict" in p for _, p in calls))


class TestSingleInstance(unittest.TestCase):
    def test_second_copy_rejected(self):
        from tools.dogruer_master_suite import single_instance as si

        old_name, old_handle = si.MUTEX_NAME, si._handle
        si.MUTEX_NAME = "Local\\DogruerMasterSuite_unittest_%s" % os.getpid()
        si._handle = None
        try:
            self.assertTrue(si.acquire_single_instance())
            self.assertFalse(si.acquire_single_instance())
        finally:
            si.release_single_instance()
            si.MUTEX_NAME = old_name
            si._handle = old_handle


class TestGtbHttpRetry(unittest.TestCase):
    def test_retries_then_succeeds(self):
        from unittest.mock import patch
        import urllib.error
        from tools.gtb_engine.gtb_http import gtb_urlopen

        n = {"i": 0}

        def flaky(req, timeout=10):
            n["i"] += 1
            if n["i"] < 3:
                raise urllib.error.URLError("timed out")
            return "OK"

        with patch("urllib.request.urlopen", side_effect=flaky):
            self.assertEqual(gtb_urlopen("req", retries=3, sleep_s=0), "OK")
        self.assertEqual(n["i"], 3)

    def test_raises_after_retries(self):
        from unittest.mock import patch
        import urllib.error
        from tools.gtb_engine.gtb_http import gtb_urlopen

        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("down")):
            with self.assertRaises(urllib.error.URLError):
                gtb_urlopen("req", retries=2, sleep_s=0)


class TestRpaFieldValues(unittest.TestCase):
    def test_per_file_overrides_defaults(self):
        from tools.dogruer_master_suite.engine.rpa_field_values import (
            resolve_beyanname_item_values,
            queue_item_from_record,
        )

        vals = resolve_beyanname_item_values(
            {"gemi": "EVER GIVEN", "liman": "AMBARLI", "fatura_bedeli": "12.000,00"},
            {"tasit_kimligi": "MAERSK EL BOSQUE", "liman_kutu": "DP"},
        )
        self.assertEqual(vals["gemi"], "EVER GIVEN")
        self.assertEqual(vals["liman_kutu"], "AMBARLI")
        self.assertEqual(vals["fatura_bedeli"], "12.000,00")
        self.assertEqual(vals["beyan_4000"], "4000")

        row = queue_item_from_record({"dosya": "D99", "gemi": "ONE PIECE", "liman": "DPW"}, fallback_gemi="DEFAULT")
        self.assertEqual(row["dosya_no"], "D99")
        self.assertEqual(row["gemi"], "ONE PIECE")
        self.assertEqual(row["liman"], "DPW")

    def test_empty_item_uses_fallback_gemi(self):
        from tools.dogruer_master_suite.engine.rpa_field_values import queue_item_from_record

        row = queue_item_from_record({"dosya_no": "X1"}, fallback_gemi="PANEL GEMİ")
        self.assertEqual(row["gemi"], "PANEL GEMİ")


class TestAppLifecycle(unittest.TestCase):
    def test_report_critical_sets_last_error(self):
        from tools.ops_log import get_last_error
        from tools.dogruer_master_suite.app_lifecycle import report_critical

        report_critical("sync", "excel kilitli", RuntimeError("lock"))
        last = get_last_error() or ""
        self.assertIn("sync", last)
        self.assertIn("excel kilitli", last)

    def test_prepare_shutdown_stops_services(self):
        import threading
        from tools.dogruer_master_suite.app_lifecycle import prepare_shutdown

        class Svc:
            def __init__(self):
                self.is_running = True

            def stop_worker(self):
                self.is_running = False

            def stop_polling(self):
                self.is_running = False

        class RPA:
            def __init__(self):
                self.stopped = False

            def trigger_emergency_stop(self):
                self.stopped = True

        class Bar:
            def __init__(self):
                self.ticker_stopped = False

            def stop_ticker(self):
                self.ticker_stopped = True

        class App:
            pass

        app = App()
        app._closed = False
        app._sync_stop = threading.Event()
        app.status_bar = Bar()
        app.supervisor = type("Sup", (), {"watchdog_running": True})()
        app.gtb_tracker = Svc()
        app.kantar_tracker = Svc()
        app.telegram_service = Svc()
        rpa = RPA()
        app.views = {"RPA_STATION": type("V", (), {"rpa": rpa})()}

        prepare_shutdown(app, logout_auth=False)

        self.assertTrue(app._closed)
        self.assertTrue(app._sync_stop.is_set())
        self.assertTrue(app.status_bar.ticker_stopped)
        self.assertFalse(app.gtb_tracker.is_running)
        self.assertFalse(app.kantar_tracker.is_running)
        self.assertFalse(app.telegram_service.is_running)
        self.assertFalse(app.supervisor.watchdog_running)
        self.assertTrue(rpa.stopped)

    def test_app_py_has_no_hard_exit(self):
        text = (Path(__file__).resolve().parents[1] / "tools" / "dogruer_master_suite" / "app.py").read_text(encoding="utf-8")
        self.assertNotIn("os._exit", text)


if __name__ == "__main__":
    unittest.main()
