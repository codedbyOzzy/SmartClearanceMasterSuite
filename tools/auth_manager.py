# -*- coding: utf-8 -*-
"""
tools/auth_manager.py
======================
Doğruer MasterSuite - Merkezi Kimlik Doğrulama, Rol Yönetimi & Canlı Yetki İzleyici
Firma: Doğruer Gümrük Müşavirliği A.Ş.
"""
import os
import json
import time
import hashlib
import secrets
import threading
import datetime
from typing import Dict, List, Optional, Tuple, Callable

try:
    from tools.storage_json import load_json, save_json_atomic
except Exception:
    try:
        from storage_json import load_json, save_json_atomic
    except Exception:
        load_json = None
        save_json_atomic = None

CONFIG_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "SmartClearance")
USERS_LOCAL_PATH = os.path.join(CONFIG_DIR, "users_store.json")
USERS_BACKUP_PATH = os.path.join(CONFIG_DIR, "users_store.json.bak")
AUTH_SESSION_PATH = os.path.join(CONFIG_DIR, "auth_session.json")

LEGACY_SALT = "dogruer_mastersuite_salt_2026"
DEFAULT_ADMIN_PASSWORD = "123456"
PBKDF2_ROUNDS = 120000
SESSION_DAYS = 14

DEFAULT_ADMIN = {
    "username": "admin",
    "password_hash": hashlib.sha256((DEFAULT_ADMIN_PASSWORD + LEGACY_SALT).encode("utf-8")).hexdigest(),
    "full_name": "Sistem Yöneticisi",
    "email": "ozan.gemici@dogruer.com",
    "role": "admin",
    "is_active": True,
    "created_at": datetime.datetime.now().isoformat(),
    "last_login": None,
    "must_change_password": True,
}


class AuthManager:
    _instance = None
    _instance_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    inst = super(AuthManager, cls).__new__(cls)
                    inst._init_manager()
                    cls._instance = inst
        return cls._instance

    def _init_manager(self):
        self.current_user: Optional[Dict] = None
        self.users: List[Dict] = []
        self.lock = threading.RLock()
        self.watchdog_running = False
        self.watchdog_thread = None
        self.on_state_changed_callbacks: List[Callable[[Dict], None]] = []
        self.on_force_logout_callbacks: List[Callable[[str], None]] = []
        self._ui_dispatcher: Optional[Callable] = None

        self._load_local_users()
        self._sync_with_supabase_background()

    def set_ui_dispatcher(self, fn: Callable):
        """Tk ana thread'ine callback taşımak için root.after sarmalayıcısı."""
        self._ui_dispatcher = fn

    def _dispatch(self, cb, *args):
        try:
            if self._ui_dispatcher:
                self._ui_dispatcher(lambda: cb(*args))
            else:
                cb(*args)
        except Exception:
            try:
                cb(*args)
            except Exception:
                pass

    @staticmethod
    def hash_password(password: str) -> str:
        """Yeni parolaları PBKDF2-HMAC-SHA256 ile hashler."""
        salt = secrets.token_hex(16)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ROUNDS)
        return f"pbkdf2$sha256${PBKDF2_ROUNDS}${salt}${dk.hex()}"

    @staticmethod
    def hash_password_legacy(password: str) -> str:
        return hashlib.sha256((password + LEGACY_SALT).encode("utf-8")).hexdigest()

    @classmethod
    def verify_password(cls, password: str, stored: str) -> bool:
        stored = stored or ""
        if stored.startswith("pbkdf2$"):
            try:
                _scheme, _algo, rounds_s, salt, digest = stored.split("$", 4)
                rounds = int(rounds_s)
                dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), rounds)
                return secrets.compare_digest(dk.hex(), digest)
            except (ValueError, TypeError):
                return False
        if len(stored) == 64:
            return secrets.compare_digest(cls.hash_password_legacy(password), stored)
        return False

    def _load_local_users(self):
        with self.lock:
            loaded = None
            if load_json:
                loaded = load_json(USERS_LOCAL_PATH, default=None)
                if not loaded and os.path.exists(USERS_BACKUP_PATH):
                    loaded = load_json(USERS_BACKUP_PATH, default=None)
                    if loaded:
                        print("[AUTH] Yerel kullanıcı dosyası bozuktu, yedekten (.bak) başarıyla kurtarıldı.")
            else:
                if os.path.exists(USERS_LOCAL_PATH):
                    try:
                        with open(USERS_LOCAL_PATH, "r", encoding="utf-8") as f:
                            loaded = json.load(f)
                    except Exception as e:
                        print(f"[AUTH] Yerel kullanıcı okuma hatası: {e}")
                        if os.path.exists(USERS_BACKUP_PATH):
                            try:
                                with open(USERS_BACKUP_PATH, "r", encoding="utf-8") as bf:
                                    loaded = json.load(bf)
                                    print("[AUTH] Yedekten (.bak) başarıyla kurtarıldı.")
                            except Exception:
                                pass

            if isinstance(loaded, list) and len(loaded) > 0:
                self.users = loaded
            else:
                self.users = [DEFAULT_ADMIN.copy()]
                self._save_local_users()

    def _save_local_users(self):
        with self.lock:
            try:
                os.makedirs(CONFIG_DIR, exist_ok=True)
                if save_json_atomic:
                    save_json_atomic(USERS_LOCAL_PATH, self.users, snapshot_lock=self.lock)
                    save_json_atomic(USERS_BACKUP_PATH, self.users, snapshot_lock=self.lock)
                else:
                    with open(USERS_LOCAL_PATH, "w", encoding="utf-8") as f:
                        json.dump(self.users, f, ensure_ascii=False, indent=2)
                    with open(USERS_BACKUP_PATH, "w", encoding="utf-8") as bf:
                        json.dump(self.users, bf, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"[AUTH] Yerel kullanıcı kaydetme hatası: {e}")

    def login(self, username: str, password: str, remember_me: bool = False) -> Tuple[bool, str, Optional[Dict]]:
        """Kullanıcı adı ve şifreyi doğrular. Başarılıysa oturum açar."""
        u_clean = (username or "").strip().lower()
        if not u_clean:
            return False, "Kullanıcı adı boş bırakılamaz.", None

        with self.lock:
            user = next((u for u in self.users if u.get("username", "").lower() == u_clean), None)

            if not user:
                return False, "Kullanıcı adı bulunamadı.", None

            if not user.get("is_active", True):
                return False, "Bu kullanıcı hesabı yönetici tarafından devre dışı bırakılmıştır.", None

            if not self.verify_password(password, user.get("password_hash", "")):
                return False, "Hatalı şifre girdiniz. Lütfen tekrar deneyin.", None

            user["last_login"] = datetime.datetime.now().isoformat()
            if password == DEFAULT_ADMIN_PASSWORD:
                user["must_change_password"] = True
            self.current_user = user
            self._save_local_users()

            if remember_me:
                self._save_session(user)
            else:
                self._clear_session()

            self.start_live_watchdog()
            result_user = dict(user)

        threading.Thread(target=self._push_to_supabase_sync, args=(result_user,), daemon=True).start()
        welcome = f"Hoş geldiniz, {result_user.get('full_name')}!"
        return True, welcome, result_user

    def change_own_password(self, username: str, old_password: str, new_password: str) -> Tuple[bool, str]:
        if not new_password or len(new_password) < 8:
            return False, "Yeni şifre en az 8 karakter olmalıdır."
        if new_password == DEFAULT_ADMIN_PASSWORD:
            return False, "Varsayılan şifre kullanılamaz."
        u_clean = (username or "").strip().lower()
        with self.lock:
            user = next((u for u in self.users if u.get("username", "").lower() == u_clean), None)
            if not user:
                return False, "Kullanıcı bulunamadı."
            if not self.verify_password(old_password, user.get("password_hash", "")):
                return False, "Mevcut şifre hatalı."
            user["password_hash"] = self.hash_password(new_password)
            user["must_change_password"] = False
            user["updated_at"] = datetime.datetime.now().isoformat()
            self._save_local_users()
            if self.current_user and self.current_user.get("username", "").lower() == u_clean:
                self.current_user = user
            snapshot = dict(user)
        threading.Thread(target=self._push_to_supabase_sync, args=(snapshot,), daemon=True).start()
        return True, "Şifre güncellendi."

    def change_password(self, username: str, old_password: str, new_password: str) -> Tuple[bool, str]:
        """Eski UI çağrıları için takma ad."""
        return self.change_own_password(username, old_password, new_password)

    def logout(self):
        """Mevcut oturumu güvenle kapatır."""
        with self.lock:
            self.current_user = None
            self._clear_session()
            self.stop_live_watchdog()

    def get_saved_session(self) -> Optional[Dict]:
        """Beni Hatırla ile kaydedilmiş geçerli oturumu getirir."""
        if not os.path.exists(AUTH_SESSION_PATH):
            return None
        try:
            with open(AUTH_SESSION_PATH, "r", encoding="utf-8") as f:
                sess = json.load(f)
            saved_at = sess.get("saved_at")
            token = sess.get("token")
            if not token or not saved_at:
                self._clear_session()
                return None
            try:
                ts = datetime.datetime.fromisoformat(saved_at)
            except ValueError:
                self._clear_session()
                return None
            if datetime.datetime.now() - ts > datetime.timedelta(days=SESSION_DAYS):
                self._clear_session()
                return None
            u_name = sess.get("username")
            with self.lock:
                user = next((u for u in self.users if u.get("username", "").lower() == (u_name or "").lower()), None)
                if user and user.get("is_active", True) and user.get("session_token") == token:
                    if user.get("must_change_password"):
                        return None
                    self.current_user = user
                    self.start_live_watchdog()
                    return user
        except Exception:
            pass
        return None

    def _save_session(self, user: Dict):
        try:
            token = secrets.token_hex(32)
            user["session_token"] = token
            self._save_local_users()
            with open(AUTH_SESSION_PATH, "w", encoding="utf-8") as f:
                json.dump({
                    "username": user.get("username"),
                    "token": token,
                    "saved_at": datetime.datetime.now().isoformat(),
                }, f)
        except Exception:
            pass

    def _clear_session(self):
        if os.path.exists(AUTH_SESSION_PATH):
            try:
                os.remove(AUTH_SESSION_PATH)
            except Exception:
                pass

    def list_users(self) -> List[Dict]:
        """Tüm kayıtlı kullanıcıları listeler."""
        with self.lock:
            return list(self.users)

    def create_user(self, username: str, password: str, full_name: str, email: str = "", role: str = "operator") -> Tuple[bool, str]:
        """Yeni kullanıcı oluşturur (Sadece Admin)."""
        u_clean = (username or "").strip().lower()
        if not u_clean or len(u_clean) < 3:
            return False, "Kullanıcı adı en az 3 karakter olmalıdır."

        if not password or len(password) < 8:
            return False, "Şifre en az 8 karakter olmalıdır."

        with self.lock:
            if any(u.get("username", "").lower() == u_clean for u in self.users):
                return False, f"'{u_clean}' kullanıcı adı zaten kullanımda."

            new_u = {
                "username": u_clean,
                "password_hash": self.hash_password(password),
                "full_name": (full_name or u_clean).strip(),
                "email": (email or "").strip(),
                "role": role if role in ("admin", "operator", "viewer") else "operator",
                "is_active": True,
                "created_at": datetime.datetime.now().isoformat(),
                "last_login": None,
                "updated_at": datetime.datetime.now().isoformat(),
                "must_change_password": False,
            }
            self.users.append(new_u)
            self._save_local_users()
            threading.Thread(target=self._push_to_supabase_sync, args=(dict(new_u),), daemon=True).start()

            return True, f"'{new_u['full_name']}' kullanıcısı başarıyla oluşturuldu."

    def update_user(self, username: str, full_name: str = None, role: str = None, is_active: bool = None, new_password: str = None) -> Tuple[bool, str]:
        """Kullanıcı bilgilerini, rolünü veya durumunu günceller."""
        u_clean = (username or "").strip().lower()
        with self.lock:
            user = next((u for u in self.users if u.get("username", "").lower() == u_clean), None)
            if not user:
                return False, "Kullanıcı bulunamadı."

            if full_name is not None:
                user["full_name"] = full_name.strip()
            if role is not None and role in ("admin", "operator", "viewer"):
                user["role"] = role
            if is_active is not None:
                user["is_active"] = is_active
            if new_password:
                if len(new_password) < 8:
                    return False, "Şifre en az 8 karakter olmalıdır."
                user["password_hash"] = self.hash_password(new_password)
                user["must_change_password"] = False
            user["updated_at"] = datetime.datetime.now().isoformat()

            self._save_local_users()
            snapshot = dict(user)

        threading.Thread(target=self._push_to_supabase_sync, args=(snapshot,), daemon=True).start()
        return True, f"'{snapshot['full_name']}' bilgileri başarıyla güncellendi."

    def delete_user(self, username: str) -> Tuple[bool, str]:
        """Kullanıcıyı sistemden siler."""
        u_clean = (username or "").strip().lower()
        if u_clean == "admin":
            return False, "Ana yönetici (admin) hesabı silinemez."

        with self.lock:
            orig_len = len(self.users)
            self.users = [u for u in self.users if u.get("username", "").lower() != u_clean]
            if len(self.users) < orig_len:
                self._save_local_users()
                threading.Thread(target=self._delete_from_supabase_async, args=(u_clean,), daemon=True).start()
                return True, f"'{u_clean}' kullanıcısı silindi."
            return False, "Kullanıcı bulunamadı."

    def register_state_change_callback(self, cb: Callable[[Dict], None]):
        """Kullanıcının rolü veya durumu değiştiğinde tetiklenecek fonksiyonu kaydeder."""
        if cb not in self.on_state_changed_callbacks:
            self.on_state_changed_callbacks.append(cb)

    def register_force_logout_callback(self, cb: Callable[[str], None]):
        """Kullanıcı pasife alındığında oturumu zorla kapatacak fonksiyonu kaydeder."""
        if cb not in self.on_force_logout_callbacks:
            self.on_force_logout_callbacks.append(cb)

    def start_live_watchdog(self):
        """Arka planda her 8 saniyede bir Supabase'i yoklayarak kullanıcının anlık rolünü denetler."""
        if self.watchdog_running:
            return
        self.watchdog_running = True
        self.watchdog_thread = threading.Thread(target=self._watchdog_loop, daemon=True)
        self.watchdog_thread.start()

    def stop_live_watchdog(self):
        self.watchdog_running = False

    def _watchdog_loop(self):
        """Admin bir yetkiyi değiştirdiğinde uygulamanın kapanmadan anında güncellenmesini sağlar."""
        while self.watchdog_running:
            try:
                time.sleep(8)
                if not self.current_user:
                    continue

                curr_username = self.current_user.get("username", "").lower()
                remote_users = self._fetch_from_supabase_sync()

                if not remote_users:
                    continue

                updated_user = next((u for u in remote_users if u.get("username", "").lower() == curr_username), None)
                if not updated_user:
                    continue

                if not updated_user.get("is_active", True):
                    print(f"[AUTH-WATCHDOG] '{curr_username}' hesabı pasife alındı! Oturum kapatılıyor...")
                    self.logout()
                    for cb in list(self.on_force_logout_callbacks):
                        self._dispatch(cb, "Hesabınız yönetici tarafından devre dışı bırakıldı.")
                    break

                old_role = self.current_user.get("role")
                new_role = updated_user.get("role")
                old_name = self.current_user.get("full_name")
                new_name = updated_user.get("full_name")

                if old_role != new_role or old_name != new_name:
                    print(f"[AUTH-WATCHDOG] Yetki/Profil Değişikliği Algılandı: {old_role} -> {new_role}")
                    with self.lock:
                        keep_hash = self.current_user.get("password_hash")
                        self.current_user.update(updated_user)
                        if updated_user.get("password_hash") in (None, "", "HASHED_LOCALLY"):
                            self.current_user["password_hash"] = keep_hash
                    for cb in list(self.on_state_changed_callbacks):
                        self._dispatch(cb, self.current_user)

            except Exception:
                time.sleep(10)

    def _fetch_from_supabase_sync(self) -> List[Dict]:
        try:
            from tools.supabase_sync_manager import get_supabase_manager
            sb = get_supabase_manager()
            res = sb._request("GET", "ms_users?select=*")
            if isinstance(res, list) and len(res) > 0:
                with self.lock:
                    local_map = {u.get("username"): u for u in self.users}
                    merged = []
                    for rem in res:
                        uname = rem.get("username")
                        loc = local_map.get(uname)
                        if loc and (not rem.get("password_hash") or rem.get("password_hash") == "HASHED_LOCALLY"):
                            rem = dict(rem)
                            rem["password_hash"] = loc.get("password_hash")
                            rem["session_token"] = loc.get("session_token")
                            rem["must_change_password"] = loc.get("must_change_password", rem.get("must_change_password"))
                        merged.append(rem)
                    self.users = merged
                    self._save_local_users()
                return merged
        except Exception:
            pass
        return self.users

    def _sync_with_supabase_background(self):
        def _run():
            self._fetch_from_supabase_sync()
        threading.Thread(target=_run, daemon=True, name="AuthSupabaseSync").start()

    def _push_to_supabase_sync(self, user: Dict):
        try:
            from tools.supabase_sync_manager import get_supabase_manager
            sb = get_supabase_manager()
            safe_payload = {
                "username": user.get("username"),
                "full_name": user.get("full_name"),
                "email": user.get("email") or "",
                "role": user.get("role") or "operator",
                "is_active": bool(user.get("is_active", True)),
                "created_at": user.get("created_at"),
                "last_login": user.get("last_login"),
                "updated_at": user.get("updated_at") or datetime.datetime.now().isoformat(),
                "password_hash": "HASHED_LOCALLY",
            }
            safe_payload = {k: v for k, v in safe_payload.items() if v is not None}
            sb._request(
                "POST",
                "ms_users?on_conflict=username",
                data=safe_payload,
                extra_headers={"Prefer": "resolution=merge-duplicates,return=minimal"}
            )
        except Exception as e:
            print(f"[AUTH-SUPABASE-PUSH-ERR] {e}")

    def _delete_from_supabase_async(self, username: str):
        try:
            from tools.supabase_sync_manager import get_supabase_manager
            sb = get_supabase_manager()
            sb._request("DELETE", f"ms_users?username=eq.{username}")
        except Exception as e:
            print(f"[AUTH-SUPABASE-DELETE-ERR] {e}")


def get_auth_manager() -> AuthManager:
    return AuthManager()
