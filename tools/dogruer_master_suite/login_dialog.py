"""
tools/dogruer_master_suite/login_dialog.py
==========================================
Doğruer MasterSuite - Modern Kullanıcı Giriş Ekranı (Login Dialog)
Firma: Doğruer Gümrük Müşavirliği A.Ş.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os
from typing import Optional, Dict

# Ensure the root workspace directory is in sys.path for embedded Python
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

try:
    from tools.auth_manager import get_auth_manager
except Exception as e:
    print(f"Error importing auth_manager in login_dialog: {e}")
    try:
        from auth_manager import get_auth_manager
    except Exception:
        get_auth_manager = None

class LoginDialog:
    def __init__(self, parent=None):
        self.auth = get_auth_manager() if get_auth_manager else None
        self.authenticated_user = None
        self.is_success = False

        self.root = tk.Tk() if parent is None else tk.Toplevel(parent)
        self.root.title("Giriş Yap — Doğruer MasterSuite")
        self.root.geometry("440x540")
        self.root.resizable(False, False)
        self.root.configure(bg="#0f172a")

        # Ekranın ortasına konumlandır
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        ws = self.root.winfo_screenwidth()
        hs = self.root.winfo_screenheight()
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2) - 40
        self.root.geometry(f"+{x}+{y}")

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        # 1. HEADER (BRANDING)
        header_frame = tk.Frame(self.root, bg="#0f172a", pady=25)
        header_frame.pack(fill=tk.X)

        lbl_icon = tk.Label(header_frame, text="🛡️", font=("Segoe UI Emoji", 32), bg="#0f172a", fg="#38bdf8")
        lbl_icon.pack()

        lbl_title = tk.Label(header_frame, text="SmartClearance MasterSuite", font=("Segoe UI", 16, "bold"), bg="#0f172a", fg="#ffffff")
        lbl_title.pack(pady=(6, 2))

        lbl_sub = tk.Label(header_frame, text="Doğruer Gümrük Müşavirliği A.Ş. — Kullanıcı Girişi", font=("Segoe UI", 8), bg="#0f172a", fg="#94a3b8")
        lbl_sub.pack()

        # 2. CARD CONTAINER
        card = tk.Frame(self.root, bg="#1e293b", padx=28, pady=24, relief=tk.FLAT, bd=0)
        card.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 24))

        # Kullanıcı Adı
        tk.Label(card, text="Kullanıcı Adı", font=("Segoe UI", 9, "bold"), bg="#1e293b", fg="#cbd5e1").pack(anchor="w", pady=(0, 4))
        self.ent_user = tk.Entry(card, font=("Segoe UI", 11), bg="#0f172a", fg="#ffffff", insertbackground="#ffffff", relief=tk.FLAT, bd=6)
        self.ent_user.pack(fill=tk.X, pady=(0, 14))
        self.ent_user.focus_set()

        # Şifre
        tk.Label(card, text="Şifre", font=("Segoe UI", 9, "bold"), bg="#1e293b", fg="#cbd5e1").pack(anchor="w", pady=(0, 4))
        
        pwd_container = tk.Frame(card, bg="#0f172a")
        pwd_container.pack(fill=tk.X, pady=(0, 14))

        self.ent_pass = tk.Entry(pwd_container, font=("Segoe UI", 11), bg="#0f172a", fg="#ffffff", insertbackground="#ffffff", show="•", relief=tk.FLAT, bd=6)
        self.ent_pass.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.btn_show_pwd = tk.Button(pwd_container, text="👁️", font=("Segoe UI", 9), bg="#0f172a", fg="#94a3b8", activebackground="#0f172a", activeforeground="#ffffff", relief=tk.FLAT, bd=0, cursor="hand2", command=self._toggle_password)
        self.btn_show_pwd.pack(side=tk.RIGHT, padx=6)

        # Beni Hatırla
        self.var_remember = tk.BooleanVar(value=True)
        chk_rem = tk.Checkbutton(
            card,
            text="Beni Hatırla (Oturumu Açık Tut)",
            variable=self.var_remember,
            font=("Segoe UI", 8),
            bg="#1e293b",
            fg="#94a3b8",
            selectcolor="#0f172a",
            activebackground="#1e293b",
            activeforeground="#ffffff"
        )
        chk_rem.pack(anchor="w", pady=(0, 14))

        # Hata Mesajı Alanı
        self.lbl_error = tk.Label(card, text="", font=("Segoe UI", 8, "bold"), bg="#1e293b", fg="#f87171", wraplength=340)
        self.lbl_error.pack(fill=tk.X, pady=(0, 10))

        # Giriş Butonu
        self.btn_login = tk.Button(
            card,
            text="Giriş Yap  ➔",
            font=("Segoe UI", 11, "bold"),
            bg="#2563eb",
            fg="#ffffff",
            activebackground="#1d4ed8",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            bd=0,
            pady=8,
            cursor="hand2",
            command=self._do_login
        )
        self.btn_login.pack(fill=tk.X)

        # Enter tuşu bağlama
        self.root.bind("<Return>", lambda e: self._do_login())

        # Varsayılan ilk kurulum bilgisi
        if self.auth and len(self.auth.users) == 1 and self.auth.users[0].get("username") == "admin":
            self.ent_user.insert(0, "admin")
            self.ent_pass.focus_set()

    def _toggle_password(self):
        if self.ent_pass.cget("show") == "":
            self.ent_pass.config(show="•")
            self.btn_show_pwd.config(text="👁️")
        else:
            self.ent_pass.config(show="")
            self.btn_show_pwd.config(text="🙈")

    def _do_login(self):
        username = self.ent_user.get().strip()
        password = self.ent_pass.get().strip()

        if not username:
            self._show_error("Lütfen kullanıcı adınızı girin.")
            self.ent_user.focus_set()
            return

        if not password:
            self._show_error("Lütfen şifrenizi girin.")
            self.ent_pass.focus_set()
            return

        self.btn_login.config(text="Doğrulanıyor...", state=tk.DISABLED, bg="#1e3a8a")
        self.root.update_idletasks()

        if not self.auth:
            self.btn_login.config(text="Giriş Yap  ➔", state=tk.NORMAL, bg="#2563eb")
            self._show_error("Kimlik doğrulama servisi yüklenemedi. Giriş yapılamaz.")
            return

        ok, msg, user = self.auth.login(username, password, remember_me=self.var_remember.get())

        if ok:
            if password == "123456" or (user and user.get("must_change_password")):
                if not self._force_password_change(username, password):
                    self.btn_login.config(text="Giriş Yap  ➔", state=tk.NORMAL, bg="#2563eb")
                    self._show_error("İlk girişte varsayılan şifreyi değiştirmeniz zorunludur.")
                    return
                user = self.auth.current_user or user
            self.authenticated_user = user
            self.is_success = True
            self.root.destroy()
        else:
            self.btn_login.config(text="Giriş Yap  ➔", state=tk.NORMAL, bg="#2563eb")
            self._show_error(msg)
            self.ent_pass.delete(0, tk.END)
            self.ent_pass.focus_set()

    def _force_password_change(self, username: str, old_password: str) -> bool:
        dlg = tk.Toplevel(self.root)
        dlg.title("Şifre Değiştir — Zorunlu")
        dlg.geometry("380x280")
        dlg.configure(bg="#1e293b")
        dlg.transient(self.root)
        dlg.grab_set()
        result = {"ok": False}

        tk.Label(dlg, text="Varsayılan şifre ile giriş yapılamaz.\nLütfen en az 8 karakterlik yeni bir şifre belirleyin.",
                 font=("Segoe UI", 9), bg="#1e293b", fg="#e2e8f0", justify="left", wraplength=340).pack(padx=16, pady=(16, 8))
        tk.Label(dlg, text="Yeni şifre", font=("Segoe UI", 8, "bold"), bg="#1e293b", fg="#cbd5e1").pack(anchor="w", padx=16)
        ent_n = tk.Entry(dlg, show="•", font=("Segoe UI", 11), bg="#0f172a", fg="#ffffff")
        ent_n.pack(fill=tk.X, padx=16, pady=(0, 8))
        tk.Label(dlg, text="Yeni şifre (tekrar)", font=("Segoe UI", 8, "bold"), bg="#1e293b", fg="#cbd5e1").pack(anchor="w", padx=16)
        ent_n2 = tk.Entry(dlg, show="•", font=("Segoe UI", 11), bg="#0f172a", fg="#ffffff")
        ent_n2.pack(fill=tk.X, padx=16, pady=(0, 8))
        err = tk.Label(dlg, text="", font=("Segoe UI", 8), bg="#1e293b", fg="#f87171")
        err.pack(fill=tk.X, padx=16)

        def _save():
            n1, n2 = ent_n.get().strip(), ent_n2.get().strip()
            if n1 != n2:
                err.config(text="Şifreler eşleşmiyor.")
                return
            ok, msg = self.auth.change_own_password(username, old_password, n1)
            if not ok:
                err.config(text=msg)
                return
            result["ok"] = True
            dlg.destroy()

        tk.Button(dlg, text="Şifreyi Kaydet", command=_save, bg="#2563eb", fg="#ffffff",
                  font=("Segoe UI", 10, "bold"), relief=tk.FLAT, pady=6).pack(fill=tk.X, padx=16, pady=12)
        ent_n.focus_set()
        dlg.wait_window()
        return result["ok"]

    def _show_error(self, text: str):
        self.lbl_error.config(text=f"⚠️ {text}")

    def _on_close(self):
        self.is_success = False
        self.authenticated_user = None
        self.root.destroy()

    def show(self) -> Optional[Dict]:
        """Giriş ekranını modal olarak açar ve giriş yapılan kullanıcıyı döner."""
        self.root.mainloop()
        return self.authenticated_user


def prompt_login_dialog(force_prompt: bool = False) -> Optional[Dict]:
    """Uygulama açılışında çağrılan yardımcı fonksiyon."""
    auth = get_auth_manager() if get_auth_manager else None
    
    # 1. Önceden 'Beni Hatırla' ile kaydedilmiş aktif oturum var mı?
    if auth and not force_prompt:
        saved_user = auth.get_saved_session()
        if saved_user:
            return saved_user

    # 2. Yoksa veya Çıkış Yapıldıysa Giriş Ekranını Aç
    dlg = LoginDialog()
    return dlg.show()


if __name__ == "__main__":
    user = prompt_login_dialog()
    print("Giriş Yapılan Kullanıcı:", user)
