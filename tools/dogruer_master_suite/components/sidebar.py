# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk


class MasterSuiteSidebar(tk.Frame):
    """Sol navigasyon menusu ve kullanici profil karti."""
    def __init__(self, parent, app, *args, **kwargs):
        super().__init__(parent, bg="#0f172a", width=240, *args, **kwargs)
        self.app = app
        self.pack_propagate(False)
        self.sidebar_is_collapsed = False
        self.nav_buttons = {}
        self.category_headers = []
        self._build_ui()

    def _build_ui(self):
        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # 1. MARKA
        self.brand_box = tk.Frame(self, bg="#0b1120", padx=10, pady=10)
        self.brand_box.grid(row=0, column=0, sticky="ew")

        logo_frame = tk.Frame(self.brand_box, bg="#0b1120")
        logo_frame.pack(fill=tk.X)

        self.lbl_logo_icon = tk.Label(logo_frame, text="⚡", font=("Segoe UI", 14), fg="#38bdf8", bg="#0b1120")
        self.lbl_logo_icon.pack(side=tk.LEFT, padx=(0, 4))

        self.lbl_logo_smart = tk.Label(logo_frame, text="Smart", font=("Segoe UI", 12, "bold"), fg="#f8fafc", bg="#0b1120", bd=0)
        self.lbl_logo_smart.pack(side=tk.LEFT)

        self.lbl_logo_clearance = tk.Label(logo_frame, text="Clearance", font=("Segoe UI", 12, "bold"), fg="#38bdf8", bg="#0b1120", bd=0)
        self.lbl_logo_clearance.pack(side=tk.LEFT)

        self.lbl_sub_badge = tk.Label(
            self.brand_box, text="MASTER SUITE v4.0", font=("Segoe UI", 7, "bold"),
            fg="#e0f2fe", bg="#0284c7", padx=8, pady=3, relief=tk.FLAT
        )
        self.lbl_sub_badge.pack(anchor="w", pady=(6, 0))

        # 2. DARALT
        self.btn_toggle_sidebar = tk.Button(
            self, text="◀ Menüyü Daralt", font=("Segoe UI", 8),
            bg="#1e293b", fg="#94a3b8", activebackground="#334155", activeforeground="#ffffff",
            relief=tk.FLAT, bd=0, pady=3, cursor="hand2", command=self.toggle_collapse
        )
        self.btn_toggle_sidebar.grid(row=1, column=0, sticky="ew", padx=6, pady=(4, 4))

        sep = tk.Frame(self, bg="#1e293b", height=1)
        sep.grid(row=2, column=0, sticky="ew", padx=8)

        # 3. KAYDIRILABİLİR MENÜ (orta, esnek)
        nav_wrap = tk.Frame(self, bg="#0f172a")
        nav_wrap.grid(row=3, column=0, sticky="nsew")
        nav_wrap.grid_rowconfigure(0, weight=1)
        nav_wrap.grid_columnconfigure(0, weight=1)
        self.nav_wrap = nav_wrap

        self.nav_canvas = tk.Canvas(
            nav_wrap, bg="#0f172a", highlightthickness=0, bd=0,
            width=220
        )
        try:
            style = ttk.Style()
            style.configure(
                "Sidebar.Vertical.TScrollbar",
                background="#1e293b",
                troughcolor="#0f172a",
                arrowcolor="#94a3b8",
                bordercolor="#0f172a",
                lightcolor="#1e293b",
                darkcolor="#0f172a"
            )
            self.nav_scroll = ttk.Scrollbar(
                nav_wrap, orient=tk.VERTICAL, command=self.nav_canvas.yview,
                style="Sidebar.Vertical.TScrollbar"
            )
        except Exception:
            self.nav_scroll = tk.Scrollbar(nav_wrap, orient=tk.VERTICAL, command=self.nav_canvas.yview, width=12)

        self.nav_inner = tk.Frame(self.nav_canvas, bg="#0f172a")
        self._nav_win = self.nav_canvas.create_window((0, 0), window=self.nav_inner, anchor="nw")
        self.nav_canvas.configure(yscrollcommand=self.nav_scroll.set)

        self.nav_canvas.grid(row=0, column=0, sticky="nsew")
        self.nav_scroll.grid(row=0, column=1, sticky="ns")

        self.nav_inner.bind("<Configure>", self._refresh_nav_scroll)
        self.nav_canvas.bind("<Configure>", self._on_nav_canvas_configure)
        self.bind("<MouseWheel>", self._on_nav_mousewheel)
        self.nav_canvas.bind("<MouseWheel>", self._on_nav_mousewheel)
        self.nav_inner.bind("<MouseWheel>", self._on_nav_mousewheel)

        nav_groups = [
            ("📌  OPERASYON MERKEZİ", [
                ("COCKPIT", "📊", "Operasyon Kokpiti"),
                ("AI_ASSISTANT", "🧠", "Gemini AI Danışmanı"),
                ("ACTIVITY_HUB", "📋", "İşlem & Not Günlüğü"),
                ("EXCEL_AKTARIM", "📑", "Excel Aktarım"),
                ("RPA_STATION", "🤖", "Otonom RPA İstasyonu"),
                ("MASTER_KONTROL", "🔍", "Master Data Kontrol"),
                ("GTB_TAKIP", "🏛️", "GTB Beyanname Takip"),
                ("KANTAR_TAKIP", "⚖️", "Kantar & DBA Takip"),
                ("ETA_YAKLASANLAR", "⏳", "ETA Yaklaşanlar"),
                ("EVRIM_EXPLORER", "🏛️", "Evrim Veri Merkezi"),
                ("SHIELD", "📧", "Akıllı Konuşma Gezgini"),
            ]),
            ("🌐  ENTEGRE PORTALLAR", [
                ("QNB_PORTAL", "🌐", "QNB eSolutions"),
                ("GLP_PORTAL", "🚛", "Hankook GLP Portalı"),
                ("DOGRUER_PORTAL", "🏢", "Doğruer Online"),
                ("TALEP", "💸", "Finansal Talepler"),
            ]),
            ("⚙️  YÖNETİM & AYARLAR", [
                ("SUMMARY", "📈", "Günlük İş Özeti"),
                ("SETTINGS", "⚙️", "Sistem Ayarları"),
                ("USERS", "👥", "Kullanıcı & Yetki"),
            ]),
        ]

        for group_title, items in nav_groups:
            f_grp = tk.Frame(self.nav_inner, bg="#0f172a")
            f_grp.pack(fill=tk.X, padx=6, pady=(12, 4))
            self.category_headers.append(f_grp)

            lbl_grp = tk.Label(
                f_grp, text=group_title, font=("Segoe UI", 7, "bold"),
                fg="#38bdf8", bg="#0f172a", anchor="w", padx=8, pady=2, relief=tk.FLAT
            )
            lbl_grp.pack(fill=tk.X)
            self._bind_wheel_tree(f_grp)

            for code, icon, title in items:
                btn_frame = tk.Frame(self.nav_inner, bg="#0f172a", cursor="hand2")
                btn_frame.pack(fill=tk.X, padx=4, pady=1)

                bar = tk.Frame(btn_frame, bg="#0f172a", width=3)
                bar.pack(side=tk.LEFT, fill=tk.Y)

                lbl_icon = tk.Label(
                    btn_frame, text=icon, font=("Segoe UI", 10),
                    fg="#94a3b8", bg="#0f172a", width=2, anchor="center", cursor="hand2"
                )
                lbl_icon.pack(side=tk.LEFT, padx=(2, 2))

                f_text = tk.Frame(btn_frame, bg="#0f172a", cursor="hand2", padx=2, pady=5)
                f_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

                lbl_t = tk.Label(
                    f_text, text=title, font=("Segoe UI", 9, "bold"),
                    fg="#94a3b8", bg="#0f172a", anchor="w", cursor="hand2"
                )
                lbl_t.pack(fill=tk.X)

                for w in (btn_frame, bar, lbl_icon, f_text, lbl_t):
                    w.bind("<Button-1>", lambda e, c=code: self.app.switch_tab(c))

                def _make_hover(b_frame, l_ic, f_tx, l_title, c_code):
                    def _enter(e):
                        if getattr(self.app, "current_tab", "") != c_code:
                            b_frame.config(bg="#1e293b")
                            l_ic.config(bg="#1e293b", fg="#ffffff")
                            f_tx.config(bg="#1e293b")
                            l_title.config(bg="#1e293b", fg="#f8fafc")
                    def _leave(e):
                        if getattr(self.app, "current_tab", "") != c_code:
                            b_frame.config(bg="#0f172a")
                            l_ic.config(bg="#0f172a", fg="#94a3b8")
                            f_tx.config(bg="#0f172a")
                            l_title.config(bg="#0f172a", fg="#94a3b8")
                    return _enter, _leave

                _ent, _lv = _make_hover(btn_frame, lbl_icon, f_text, lbl_t, code)
                btn_frame.bind("<Enter>", _ent)
                btn_frame.bind("<Leave>", _lv)

                self.nav_buttons[code] = {
                    "frame": btn_frame,
                    "bar": bar,
                    "icon_lbl": lbl_icon,
                    "text_frame": f_text,
                    "title": lbl_t,
                    "icon": icon,
                    "full_title": title
                }
                self._bind_wheel_tree(btn_frame)

                if code == "USERS":
                    self.btn_nav_users = btn_frame
                    if getattr(self.app, "current_user", {}).get("role") != "admin":
                        btn_frame.pack_forget()

        # 4. PROFİL + ÇIKIŞ — her zaman en altta, menünün üstüne binmez
        self._build_bottom_box()
        self.bottom_box.grid(row=4, column=0, sticky="ew")

        self.after(50, self._refresh_nav_scroll)

    def _build_bottom_box(self):
        self.bottom_box = tk.Frame(self, bg="#0b1120", padx=8, pady=8)

        f_prof = tk.Frame(self.bottom_box, bg="#1e293b", padx=8, pady=6, relief=tk.FLAT)
        f_prof.pack(fill=tk.X, pady=(0, 6))
        self.profile_card = f_prof

        u_name = getattr(self.app, "current_user", {}).get("full_name") or getattr(self.app, "current_user", {}).get("username", "Kullanıcı")
        u_role = getattr(self.app, "current_user", {}).get("role", "operator")
        role_map = {"admin": "👑 Yönetici", "operator": "🛠️ Operatör", "viewer": "👁️ İzleyici"}
        r_text = role_map.get(u_role, u_role.capitalize())

        self.lbl_user_profile_name = tk.Label(f_prof, text=u_name, font=("Segoe UI", 8, "bold"), fg="#ffffff", bg="#1e293b", anchor="w")
        self.lbl_user_profile_name.pack(fill=tk.X)

        self.lbl_user_profile_role = tk.Label(f_prof, text=r_text, font=("Segoe UI", 7), fg="#93c5fd", bg="#1e293b", anchor="w")
        self.lbl_user_profile_role.pack(fill=tk.X, pady=(1, 4))

        self.btn_change_pwd = tk.Button(
            f_prof,
            text="🔑 Şifre Değiştir",
            font=("Segoe UI", 7, "bold"),
            bg="#0f172a",
            fg="#cbd5e1",
            activebackground="#1e293b",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            pady=2,
            cursor="hand2",
            command=self.app.show_change_password_dialog
        )
        self.btn_change_pwd.pack(fill=tk.X, pady=(0, 4))

        self.btn_logout = tk.Button(
            f_prof,
            text="🚪 Güvenli Çıkış",
            font=("Segoe UI", 8, "bold"),
            bg="#7f1d1d",
            fg="#fecaca",
            activebackground="#991b1b",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            pady=5,
            cursor="hand2",
            command=self.app.do_logout
        )
        self.btn_logout.pack(fill=tk.X)

        self.lbl_side_sync = tk.Label(
            self.bottom_box,
            text="⚡ Canlı İzleme Aktif\n(Excel & Outlook)",
            font=("Segoe UI", 7),
            fg="#4ade80",
            bg="#0b1120",
            justify=tk.LEFT
        )
        self.lbl_side_sync.pack(anchor="w", pady=(2, 0))

    def _bind_wheel_tree(self, widget):
        widget.bind("<MouseWheel>", self._on_nav_mousewheel, add="+")
        for child in widget.winfo_children():
            self._bind_wheel_tree(child)

    def _pointer_over_sidebar(self, event):
        try:
            w = self.winfo_containing(event.x_root, event.y_root)
        except Exception:
            return False
        while w is not None:
            if w == self:
                return True
            try:
                w = w.master
            except Exception:
                break
        return False

    def _on_nav_mousewheel(self, event):
        if not self._pointer_over_sidebar(event):
            return
        try:
            steps = int(-1 * (event.delta / 120))
            if steps == 0:
                steps = -1 if event.delta > 0 else 1
            self.nav_canvas.yview_scroll(steps, "units")
        except Exception:
            pass
        return "break"

    def _refresh_nav_scroll(self, event=None):
        try:
            self.nav_canvas.update_idletasks()
            bbox = self.nav_canvas.bbox("all")
            if bbox:
                self.nav_canvas.configure(scrollregion=bbox)
        except Exception:
            pass

    def _on_nav_canvas_configure(self, event):
        try:
            self.nav_canvas.itemconfigure(self._nav_win, width=max(1, event.width))
            self._refresh_nav_scroll()
        except Exception:
            pass

    def toggle_collapse(self):
        self.sidebar_is_collapsed = not self.sidebar_is_collapsed
        if self.sidebar_is_collapsed:
            self.config(width=64)
            if hasattr(self, "lbl_logo_smart"):
                self.lbl_logo_smart.pack_forget()
            if hasattr(self, "lbl_logo_clearance"):
                self.lbl_logo_clearance.pack_forget()
            self.lbl_sub_badge.pack_forget()
            self.btn_toggle_sidebar.config(text="▶", font=("Segoe UI", 9, "bold"))
            for grp in self.category_headers:
                grp.pack_forget()
            for code, btn in self.nav_buttons.items():
                btn["text_frame"].pack_forget()
                btn["icon_lbl"].config(font=("Segoe UI", 11), width=2)
            if hasattr(self, "lbl_user_profile_name"):
                self.lbl_user_profile_name.pack_forget()
            if hasattr(self, "lbl_user_profile_role"):
                self.lbl_user_profile_role.pack_forget()
            if hasattr(self, "btn_change_pwd"):
                self.btn_change_pwd.pack_forget()
            if hasattr(self, "lbl_side_sync"):
                self.lbl_side_sync.pack_forget()
            if hasattr(self, "btn_logout"):
                self.btn_logout.config(text="🚪")
            self.after(30, self._refresh_nav_scroll)
        else:
            self.config(width=240)
            for child in self.winfo_children():
                child.destroy()
            self.nav_buttons = {}
            self.category_headers = []
            self._build_ui()
            self.update_active_tab(getattr(self.app, "current_tab", "COCKPIT"))

    def update_active_tab(self, active_tab_code):
        for code, btn in self.nav_buttons.items():
            is_active = (code == active_tab_code)
            bg_color = "#1e293b" if is_active else "#0f172a"
            bar_color = "#38bdf8" if is_active else "#0f172a"
            t_color = "#38bdf8" if is_active else "#94a3b8"
            i_color = "#38bdf8" if is_active else "#94a3b8"

            btn["frame"].config(bg=bg_color)
            btn["bar"].config(bg=bar_color)
            btn["icon_lbl"].config(bg=bg_color, fg=i_color)
            if "text_frame" in btn and btn["text_frame"].winfo_exists():
                try:
                    btn["text_frame"].config(bg=bg_color)
                except Exception:
                    pass
            btn["title"].config(fg=t_color, bg=bg_color)
