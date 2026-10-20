# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox

from .base_view import BaseView

try:
    from tools.auth_manager import get_auth_manager
except Exception:
    try:
        from auth_manager import get_auth_manager
    except Exception:
        get_auth_manager = None


class UsersView(BaseView):
    """
    Kullanıcı ve Yetki Yönetim Merkezi Görünümü (Admin Panel)
    - Kullanıcı Listesi ve Durumları
    - Yeni Kullanıcı Ekleme
    - Kullanıcı Düzenleme / Şifre Sıfırlama
    - Aktif / Pasif Durum Değiştirme
    - Kullanıcı Silme
    """

    def __init__(self, parent, app, *args, **kwargs):
        super().__init__(parent, app, *args, **kwargs)
        self._build_ui()

    def on_activate(self):
        if not self.is_alive():
            return
        self.refresh_users_table()

    @property
    def auth(self):
        return getattr(self.app, "auth", None) or (get_auth_manager() if get_auth_manager else None)

    def _build_ui(self):
        # 1. Üst Aksiyon & Bilgi Barı
        top_bar = tk.Frame(self, bg="#ffffff", padx=16, pady=12, relief=tk.FLAT, bd=0)
        top_bar.pack(fill=tk.X, pady=(0, 10))

        tk.Label(
            top_bar,
            text="👥 Kullanıcı & Yetki Yönetim Merkezi",
            font=("Segoe UI", 12, "bold"),
            bg="#ffffff",
            fg="#0f172a"
        ).pack(side=tk.LEFT)

        btn_box = tk.Frame(top_bar, bg="#ffffff")
        btn_box.pack(side=tk.RIGHT)

        btn_add = tk.Button(
            btn_box,
            text="➕ Yeni Kullanıcı Ekle",
            font=("Segoe UI", 9, "bold"),
            bg="#2563eb",
            fg="#ffffff",
            activebackground="#1d4ed8",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=10,
            pady=4,
            cursor="hand2",
            command=self.show_add_user_dialog
        )
        btn_add.pack(side=tk.LEFT, padx=3)

        btn_edit = tk.Button(
            btn_box,
            text="✏️ Düzenle",
            font=("Segoe UI", 9, "bold"),
            bg="#0284c7",
            fg="#ffffff",
            activebackground="#0369a1",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=10,
            pady=4,
            cursor="hand2",
            command=self.show_edit_user_dialog
        )
        btn_edit.pack(side=tk.LEFT, padx=3)

        btn_reset_pwd = tk.Button(
            btn_box,
            text="🔑 Şifre Sıfırla",
            font=("Segoe UI", 9, "bold"),
            bg="#475569",
            fg="#ffffff",
            activebackground="#334155",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=10,
            pady=4,
            cursor="hand2",
            command=self.show_reset_password_dialog
        )
        btn_reset_pwd.pack(side=tk.LEFT, padx=3)

        btn_toggle = tk.Button(
            btn_box,
            text="🔒 Durum Değiştir (Aktif/Pasif)",
            font=("Segoe UI", 9, "bold"),
            bg="#d97706",
            fg="#ffffff",
            activebackground="#b45309",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=10,
            pady=4,
            cursor="hand2",
            command=self.toggle_selected_user_status
        )
        btn_toggle.pack(side=tk.LEFT, padx=3)

        btn_del = tk.Button(
            btn_box,
            text="🗑️ Sil",
            font=("Segoe UI", 9, "bold"),
            bg="#dc2626",
            fg="#ffffff",
            activebackground="#b91c1c",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=10,
            pady=4,
            cursor="hand2",
            command=self.delete_selected_user
        )
        btn_del.pack(side=tk.LEFT, padx=3)

        btn_ref = tk.Button(
            btn_box,
            text="🔄 Yenile",
            font=("Segoe UI", 9),
            bg="#f1f5f9",
            fg="#334155",
            activebackground="#e2e8f0",
            relief=tk.FLAT,
            padx=8,
            pady=4,
            cursor="hand2",
            command=self.refresh_users_table
        )
        btn_ref.pack(side=tk.LEFT, padx=3)

        # 2. Kullanıcı Tablosu
        tbl_frame = tk.Frame(self, bg="#ffffff", relief=tk.FLAT, bd=0)
        tbl_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("username", "full_name", "role", "email", "status", "last_login", "created_at")
        self.tree_users = ttk.Treeview(tbl_frame, columns=cols, show="headings", height=15)

        self.tree_users.heading("username", text="Kullanıcı Adı")
        self.tree_users.heading("full_name", text="Adı Soyadı")
        self.tree_users.heading("role", text="Yetki / Rol")
        self.tree_users.heading("email", text="E-Posta")
        self.tree_users.heading("status", text="Hesap Durumu")
        self.tree_users.heading("last_login", text="Son Giriş")
        self.tree_users.heading("created_at", text="Kayıt Tarihi")

        self.tree_users.column("username", width=120, anchor="center")
        self.tree_users.column("full_name", width=180, anchor="w")
        self.tree_users.column("role", width=120, anchor="center")
        self.tree_users.column("email", width=180, anchor="w")
        self.tree_users.column("status", width=110, anchor="center")
        self.tree_users.column("last_login", width=140, anchor="center")
        self.tree_users.column("created_at", width=140, anchor="center")

        sb_v = ttk.Scrollbar(tbl_frame, orient="vertical", command=self.tree_users.yview)
        self.tree_users.configure(yscrollcommand=sb_v.set)

        self.tree_users.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb_v.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree_users.tag_configure("admin_tag", background="#eff6ff", foreground="#1e3a8a")
        self.tree_users.tag_configure("passive_tag", background="#fef2f2", foreground="#991b1b")
        self.tree_users.bind("<Double-1>", lambda e: self.show_edit_user_dialog())

        self.refresh_users_table()

    def refresh_users_table(self):
        if not hasattr(self, "tree_users"):
            return
        try:
            if not self.tree_users.winfo_exists():
                return
        except Exception:
            return
        for item in self.tree_users.get_children():
            try:
                self.tree_users.delete(item)
            except Exception:
                pass

        if not self.auth:
            return
        users = self.auth.list_users()

        for u in users:
            role_map = {"admin": "👑 Yönetici (Admin)", "operator": "🛠️ Operatör", "viewer": "👁️ İzleyici"}
            role_text = role_map.get(u.get("role"), u.get("role"))
            is_active = u.get("is_active", True)
            status_text = "🟢 Aktif" if is_active else "🔴 Pasif / Donduruldu"

            tag = "normal"
            if u.get("role") == "admin":
                tag = "admin_tag"
            elif not is_active:
                tag = "passive_tag"

            last_login = u.get("last_login") or "—"
            if len(last_login) > 16:
                last_login = last_login[:16].replace("T", " ")

            created_at = u.get("created_at") or "—"
            if len(created_at) > 16:
                created_at = created_at[:16].replace("T", " ")

            self.tree_users.insert("", tk.END, values=(
                u.get("username"),
                u.get("full_name") or "—",
                role_text,
                u.get("email") or "—",
                status_text,
                last_login,
                created_at
            ), tags=(tag,), iid=u.get("username"))

    def show_add_user_dialog(self):
        root = self.winfo_toplevel()
        dlg = tk.Toplevel(root)
        dlg.title("➕ Yeni Kullanıcı Tanımla")
        dlg.geometry("380x420")
        dlg.resizable(False, False)
        dlg.configure(bg="#ffffff", padx=20, pady=20)
        dlg.grab_set()

        tk.Label(dlg, text="Yeni Kullanıcı Bilgileri", font=("Segoe UI", 12, "bold"), bg="#ffffff", fg="#0f172a").pack(anchor="w", pady=(0, 14))

        tk.Label(dlg, text="Kullanıcı Adı (Giriş için):", font=("Segoe UI", 9, "bold"), bg="#ffffff").pack(anchor="w")
        ent_uname = tk.Entry(dlg, font=("Segoe UI", 10))
        ent_uname.pack(fill=tk.X, pady=(2, 8))

        tk.Label(dlg, text="Ad Soyad:", font=("Segoe UI", 9, "bold"), bg="#ffffff").pack(anchor="w")
        ent_fname = tk.Entry(dlg, font=("Segoe UI", 10))
        ent_fname.pack(fill=tk.X, pady=(2, 8))

        tk.Label(dlg, text="E-Posta:", font=("Segoe UI", 9, "bold"), bg="#ffffff").pack(anchor="w")
        ent_email = tk.Entry(dlg, font=("Segoe UI", 10))
        ent_email.pack(fill=tk.X, pady=(2, 8))

        tk.Label(dlg, text="Şifre:", font=("Segoe UI", 9, "bold"), bg="#ffffff").pack(anchor="w")
        ent_pwd = tk.Entry(dlg, font=("Segoe UI", 10), show="•")
        ent_pwd.pack(fill=tk.X, pady=(2, 8))

        tk.Label(dlg, text="Kullanıcı Rolü / Yetki:", font=("Segoe UI", 9, "bold"), bg="#ffffff").pack(anchor="w")
        var_role = tk.StringVar(value="operator")
        cb_role = ttk.Combobox(dlg, textvariable=var_role, values=["operator", "admin", "viewer"], state="readonly", font=("Segoe UI", 9))
        cb_role.pack(fill=tk.X, pady=(2, 16))

        def _save():
            u = ent_uname.get().strip()
            p = ent_pwd.get().strip()
            fn = ent_fname.get().strip()
            em = ent_email.get().strip()
            r = var_role.get()

            if not u or not p or not fn:
                messagebox.showwarning("Eksik Bilgi", "Lütfen Kullanıcı Adı, Ad Soyad ve Şifre alanlarını doldurun!", parent=dlg)
                return
            if len(p) < 8:
                messagebox.showwarning("Geçersiz Şifre", "Şifre en az 8 karakter olmalıdır.", parent=dlg)
                return

            if self.auth:
                ok, msg = self.auth.create_user(username=u, password=p, full_name=fn, email=em, role=r)
                if ok:
                    messagebox.showinfo("Başarılı", msg, parent=dlg)
                    dlg.destroy()
                    self.refresh_users_table()
                else:
                    messagebox.showerror("Hata", msg, parent=dlg)

        btn_save = tk.Button(
            dlg, text="💾 Kullanıcıyı Kaydet", font=("Segoe UI", 10, "bold"),
            bg="#2563eb", fg="#ffffff", activebackground="#1d4ed8",
            relief=tk.FLAT, pady=6, cursor="hand2", command=_save
        )
        btn_save.pack(fill=tk.X)

    def show_edit_user_dialog(self):
        sel = self.tree_users.selection()
        if not sel:
            messagebox.showinfo("Seçim Yapın", "Lütfen düzenlemek istediğiniz bir kullanıcıyı tablodan seçin.")
            return

        username = sel[0]
        user = next((u for u in self.auth.list_users() if u.get("username") == username), None) if self.auth else None
        if not user:
            return

        root = self.winfo_toplevel()
        dlg = tk.Toplevel(root)
        dlg.title(f"✏️ Kullanıcı Düzenle: {username}")
        dlg.geometry("380x380")
        dlg.resizable(False, False)
        dlg.configure(bg="#ffffff", padx=20, pady=20)
        dlg.grab_set()

        tk.Label(dlg, text=f"'{username}' Bilgilerini Düzenle", font=("Segoe UI", 12, "bold"), bg="#ffffff", fg="#0f172a").pack(anchor="w", pady=(0, 14))

        tk.Label(dlg, text="Ad Soyad:", font=("Segoe UI", 9, "bold"), bg="#ffffff").pack(anchor="w")
        ent_fname = tk.Entry(dlg, font=("Segoe UI", 10))
        ent_fname.insert(0, user.get("full_name") or "")
        ent_fname.pack(fill=tk.X, pady=(2, 8))

        tk.Label(dlg, text="Yeni Şifre (Boş bırakılırsa değişmez):", font=("Segoe UI", 9, "bold"), bg="#ffffff").pack(anchor="w")
        ent_pwd = tk.Entry(dlg, font=("Segoe UI", 10), show="•")
        ent_pwd.pack(fill=tk.X, pady=(2, 8))

        tk.Label(dlg, text="Kullanıcı Rolü / Yetki:", font=("Segoe UI", 9, "bold"), bg="#ffffff").pack(anchor="w")
        var_role = tk.StringVar(value=user.get("role", "operator"))
        cb_role = ttk.Combobox(dlg, textvariable=var_role, values=["operator", "admin", "viewer"], state="readonly", font=("Segoe UI", 9))
        cb_role.pack(fill=tk.X, pady=(2, 16))

        def _update():
            fn = ent_fname.get().strip()
            p = ent_pwd.get().strip()
            r = var_role.get()

            if self.auth:
                ok, msg = self.auth.update_user(username=username, full_name=fn, role=r, new_password=p if p else None)
                if ok:
                    messagebox.showinfo("Başarılı", msg, parent=dlg)
                    dlg.destroy()
                    self.refresh_users_table()
                else:
                    messagebox.showerror("Hata", msg, parent=dlg)

        btn_up = tk.Button(
            dlg, text="💾 Güncellemeleri Kaydet", font=("Segoe UI", 10, "bold"),
            bg="#0284c7", fg="#ffffff", activebackground="#0369a1",
            relief=tk.FLAT, pady=6, cursor="hand2", command=_update
        )
        btn_up.pack(fill=tk.X)

    def show_reset_password_dialog(self):
        sel = self.tree_users.selection()
        if not sel:
            messagebox.showinfo("Seçim Yapın", "Lütfen şifresini sıfırlamak istediğiniz bir kullanıcıyı tablodan seçin.")
            return

        username = sel[0]
        user = next((u for u in self.auth.list_users() if u.get("username") == username), None) if self.auth else None
        if not user:
            return

        root = self.winfo_toplevel()
        dlg = tk.Toplevel(root)
        dlg.title(f"🔑 Şifre Sıfırla: {username}")
        dlg.geometry("380x280")
        dlg.resizable(False, False)
        dlg.configure(bg="#ffffff", padx=20, pady=20)
        dlg.grab_set()

        tk.Label(dlg, text=f"'{user.get('full_name')}' Şifresini Sıfırla", font=("Segoe UI", 11, "bold"), bg="#ffffff", fg="#0f172a").pack(anchor="w", pady=(0, 14))

        tk.Label(dlg, text="Yeni Şifre:", font=("Segoe UI", 9, "bold"), bg="#ffffff").pack(anchor="w")
        ent_p1 = tk.Entry(dlg, font=("Segoe UI", 10), show="•")
        ent_p1.pack(fill=tk.X, pady=(2, 10))

        tk.Label(dlg, text="Yeni Şifre (Tekrar):", font=("Segoe UI", 9, "bold"), bg="#ffffff").pack(anchor="w")
        ent_p2 = tk.Entry(dlg, font=("Segoe UI", 10), show="•")
        ent_p2.pack(fill=tk.X, pady=(2, 16))

        def _reset():
            p1 = ent_p1.get().strip()
            p2 = ent_p2.get().strip()
            if not p1 or len(p1) < 8:
                messagebox.showwarning("Geçersiz Şifre", "Yeni şifre en az 8 karakter olmalıdır.", parent=dlg)
                return
            if p1 != p2:
                messagebox.showwarning("Uyuşmazlık", "Girdiğiniz şifreler birbiriyle eşleşmiyor.", parent=dlg)
                return

            if self.auth:
                ok, msg = self.auth.update_user(username=username, new_password=p1)
                if ok:
                    messagebox.showinfo("Başarılı", f"'{username}' kullanıcısının şifresi başarıyla sıfırlandı!", parent=dlg)
                    dlg.destroy()
                    self.refresh_users_table()
                else:
                    messagebox.showerror("Hata", msg, parent=dlg)

        btn_save = tk.Button(
            dlg, text="🔑 Şifreyi Sıfırla & Kaydet", font=("Segoe UI", 10, "bold"),
            bg="#2563eb", fg="#ffffff", activebackground="#1d4ed8",
            relief=tk.FLAT, pady=6, cursor="hand2", command=_reset
        )
        btn_save.pack(fill=tk.X)

    def toggle_selected_user_status(self):
        sel = self.tree_users.selection()
        if not sel:
            return
        username = sel[0]
        user = next((u for u in self.auth.list_users() if u.get("username") == username), None) if self.auth else None
        if not user:
            return

        curr_status = user.get("is_active", True)
        new_status = not curr_status
        action_text = "PASİFE ALMAK" if curr_status else "AKTİF ETMEK"

        if messagebox.askyesno("Durum Değiştir", f"'{user.get('full_name')}' kullanıcısını {action_text} istediğinize emin misiniz?"):
            ok, msg = self.auth.update_user(username=username, is_active=new_status)
            if ok:
                self.refresh_users_table()
                messagebox.showinfo("Güncellendi", msg)

    def delete_selected_user(self):
        sel = self.tree_users.selection()
        if not sel:
            return
        username = sel[0]
        if messagebox.askyesno("Kullanıcıyı Sil", f"'{username}' kullanıcısını sistemden tamamen silmek istediğinize emin misiniz?"):
            ok, msg = self.auth.delete_user(username)
            if ok:
                self.refresh_users_table()
                messagebox.showinfo("Silindi", msg)
            else:
                messagebox.showerror("Hata", msg)
