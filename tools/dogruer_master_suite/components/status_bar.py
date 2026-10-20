# -*- coding: utf-8 -*-
import tkinter as tk

class MasterSuiteStatusBar(tk.Frame):
    """Pencerenin en altindaki canlilik servis nabzi ve sistem durum cubugu."""
    def __init__(self, parent, app, *args, **kwargs):
        super().__init__(parent, bg="#0b1120", height=28, padx=12, pady=4, *args, **kwargs)
        self.app = app
        self.stat_badges = {}
        self._ticker_after = None
        self._build_ui()
        self.bind("<Configure>", self._on_status_resize)

    def _build_ui(self):
        # Sol: Canlilik Gostergeleri
        self.f_stat_left = tk.Frame(self, bg="#0b1120")
        self.f_stat_left.pack(side=tk.LEFT)

        lbl_pulse = tk.Label(self.f_stat_left, text="💓 CANLILIK:", font=("Segoe UI", 8, "bold"), fg="#94a3b8", bg="#0b1120")
        lbl_pulse.pack(side=tk.LEFT, padx=(0, 6))

        for s_id, s_name in [("gtb", "GTB"), ("kantar", "Kantar"), ("telegram", "TG")]:
            lbl = tk.Label(
                self.f_stat_left,
                text=f"● {s_name}: Başlatılıyor...",
                font=("Segoe UI", 8),
                fg="#64748b",
                bg="#1e293b",
                padx=6,
                pady=1,
                cursor="hand2"
            )
            lbl.pack(side=tk.LEFT, padx=3)
            lbl.bind("<Button-1>", lambda e: self.show_supervisor_dialog())
            self.stat_badges[s_id] = lbl

        # Sag: Bulut Durumu, son hata & Detay Butonu
        self.f_stat_right = tk.Frame(self, bg="#0b1120")
        self.f_stat_right.pack(side=tk.RIGHT)

        self.lbl_last_error = tk.Label(
            self.f_stat_right,
            text="",
            font=("Segoe UI", 8),
            fg="#fca5a5",
            bg="#0b1120",
            wraplength=280,
            justify="right",
        )
        self.lbl_last_error.pack(side=tk.RIGHT, padx=8)

        btn_rep = tk.Label(
            self.f_stat_right,
            text="📊 Servis Sağlık Raporu",
            font=("Segoe UI", 8, "bold"),
            fg="#38bdf8",
            bg="#0b1120",
            cursor="hand2"
        )
        btn_rep.pack(side=tk.RIGHT, padx=4)
        btn_rep.bind("<Button-1>", lambda e: self.show_supervisor_dialog())

    def start_ticker(self):
        try:
            if not self.winfo_exists() or getattr(self.app, "_closed", False):
                return
        except Exception:
            return
        self.update_status()
        try:
            self._ticker_after = self.after(10000, self.start_ticker)
        except Exception:
            self._ticker_after = None

    def stop_ticker(self):
        aid = getattr(self, "_ticker_after", None)
        self._ticker_after = None
        if aid:
            try:
                self.after_cancel(aid)
            except Exception:
                pass

    def update_status(self):
        try:
            from tools.dogruer_master_suite.service_supervisor import get_supervisor
            sup = get_supervisor()
            summary = sup.get_status_summary()
            for item in summary:
                s_id = item["id"]
                if s_id in self.stat_badges:
                    self.stat_badges[s_id].config(text=item["text"], fg=item["color"], bg="#0f172a")
            try:
                from tools.ops_log import get_last_error
                last = get_last_error()
                if last:
                    short = last.replace("\n", " ")
                    max_len = 70
                    try:
                        max_len = max(28, min(90, (self.winfo_width() - 520) // 8))
                    except Exception:
                        pass
                    if len(short) > max_len:
                        short = short[:max_len] + "…"
                    self.lbl_last_error.config(text=f"⚠ {short}")
                else:
                    self.lbl_last_error.config(text="")
            except Exception:
                pass
        except Exception:
            pass

    def _on_status_resize(self, event=None):
        try:
            w = max(160, self.winfo_width() - 520)
            self.lbl_last_error.config(wraplength=w)
        except Exception:
            pass

    def show_supervisor_dialog(self):
        """Tum arka plan servislerinin detayli saglik raporunu goruntuler."""
        dlg = tk.Toplevel(self.app.root)
        dlg.title("💓 Arka Plan Servisleri Canlilik Raporu")
        dlg.geometry("540x360")
        dlg.configure(bg="#f8fafc")
        dlg.transient(self.app.root)

        top_f = tk.Frame(dlg, bg="#0f172a", padx=16, pady=12)
        top_f.pack(fill=tk.X)
        tk.Label(top_f, text="💓 Arka Plan Servisleri Canlılık & Bekçi Raporu", font=("Segoe UI", 11, "bold"), fg="#ffffff", bg="#0f172a").pack(anchor="w")
        tk.Label(top_f, text="Watchdog Bekçi Köpeği devrededir; donan veya kapanan servisler otomatik diriltilir.", font=("Segoe UI", 8), fg="#94a3b8", bg="#0f172a").pack(anchor="w")

        body_f = tk.Frame(dlg, bg="#f8fafc", padx=16, pady=12)
        body_f.pack(fill=tk.BOTH, expand=True)

        try:
            from tools.dogruer_master_suite.service_supervisor import get_supervisor
            sup = get_supervisor()
            summary = sup.get_status_summary()
            for item in summary:
                c = tk.Frame(body_f, bg="#ffffff", bd=1, relief=tk.SOLID, padx=12, pady=8)
                c.pack(fill=tk.X, pady=4)
                r1 = tk.Frame(c, bg="#ffffff")
                r1.pack(fill=tk.X)
                tk.Label(r1, text=f"{item['icon']} {item['label']}", font=("Segoe UI", 10, "bold"), fg="#0f172a", bg="#ffffff").pack(side=tk.LEFT)
                tk.Label(r1, text=item["text"], font=("Segoe UI", 9, "bold"), fg=item["color"], bg="#ffffff").pack(side=tk.RIGHT)

                r2 = tk.Frame(c, bg="#ffffff")
                r2.pack(fill=tk.X, pady=(2, 0))
                det_txt = f"Durum: {item['detail']} | Döngü Sayısı: #{item['cycles']} | Otomatik Diriltme: {item['restarts']}"
                tk.Label(r2, text=det_txt, font=("Segoe UI", 8), fg="#64748b", bg="#ffffff").pack(anchor="w")
        except Exception as e:
            tk.Label(body_f, text=f"Hata: {e}", fg="red").pack()

        tk.Button(dlg, text="Kapat", command=dlg.destroy, bg="#0f172a", fg="#ffffff", font=("Segoe UI", 9, "bold"), padx=16, pady=4, cursor="hand2", relief=tk.FLAT).pack(pady=10)
