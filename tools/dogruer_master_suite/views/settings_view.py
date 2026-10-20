# -*- coding: utf-8 -*-
import os
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from .base_view import BaseView
from tools.dogruer_master_suite.engine import (
    DEFAULT_CONFIG, load_app_config, save_app_config,
)


class SettingsView(BaseView):
    """
    Sistem Ayarları ve Entegrasyon Yapılandırma Görünümü
    - Excel Dosya Yolu
    - PDF Klasörü
    - E-Posta Alıcı ve Bilgi (CC)
    - QNB, Hankook GLP, Doğruer Online Otomatik Giriş
    - Telegram & Windows Masaüstü Bildirimleri
    """

    def __init__(self, parent, app, *args, **kwargs):
        super().__init__(parent, app, *args, **kwargs)
        self._build_ui()

    def on_activate(self):
        if not self.is_alive():
            return
        self.load_settings_into_ui()

    def on_deactivate(self):
        self._silent_save_settings_from_ui()

    def _build_ui(self):
        canvas = tk.Canvas(self, bg="#f8fafc", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#f8fafc", padx=10, pady=10)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 1. KART: EXCEL DOSYA YOLU
        card_excel = tk.Frame(scrollable_frame, bg="#ffffff", padx=16, pady=16, relief=tk.FLAT, bd=0)
        card_excel.pack(fill=tk.X, pady=(0, 14))

        tk.Label(card_excel, text="📊 İş Takip Raporu (Excel Dosyası)", font=("Segoe UI", 11, "bold"), fg="#0f172a", bg="#ffffff").pack(anchor="w")
        tk.Label(card_excel, text="Sistemin gümrük tescil, ordino, tareks ve beyanname aşamalarını anlık okuduğu ana Excel dosyası.", font=("Segoe UI", 8), fg="#64748b", bg="#ffffff").pack(anchor="w", pady=(2, 8))

        row_e = tk.Frame(card_excel, bg="#ffffff")
        row_e.pack(fill=tk.X)

        self.txt_set_excel = tk.Entry(row_e, font=("Consolas", 10), bd=1, relief=tk.SOLID)
        self.txt_set_excel.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, padx=(0, 8))

        btn_browse_excel = tk.Button(
            row_e, text="📁 Dosya Seç...", font=("Segoe UI", 9, "bold"), bg="#f1f5f9", fg="#0f172a",
            relief=tk.FLAT, bd=0, padx=12, pady=3, cursor="hand2", command=self.browse_excel_path
        )
        btn_browse_excel.pack(side=tk.LEFT, padx=(0, 4))

        btn_open_excel_dir = tk.Button(
            row_e, text="📂 Klasörü Aç", font=("Segoe UI", 8), bg="#ffffff", fg="#475569",
            relief=tk.FLAT, bd=0, padx=8, pady=3, cursor="hand2", command=lambda: self.open_folder_of_file(self.txt_set_excel.get())
        )
        btn_open_excel_dir.pack(side=tk.LEFT)

        # 2. KART: VERGİ MAİLİ PDF KLASÖRÜ
        card_pdf = tk.Frame(scrollable_frame, bg="#ffffff", padx=16, pady=16, relief=tk.FLAT, bd=0)
        card_pdf.pack(fill=tk.X, pady=(0, 14))

        tk.Label(card_pdf, text="📁 Otomatik Vergi Maili PDF Klasörü (Kapanan / Hazır PDF'ler)", font=("Segoe UI", 11, "bold"), fg="#0f172a", bg="#ffffff").pack(anchor="w")
        tk.Label(card_pdf, text="Tek tıkla veya toplu vergi maili oluşturulurken beyanname ve vergi PDF'lerinin otomatik taranıp maile ekleneceği klasör.", font=("Segoe UI", 8), fg="#64748b", bg="#ffffff").pack(anchor="w", pady=(2, 8))

        row_p = tk.Frame(card_pdf, bg="#ffffff")
        row_p.pack(fill=tk.X)

        self.txt_set_pdf = tk.Entry(row_p, font=("Consolas", 10), bd=1, relief=tk.SOLID)
        self.txt_set_pdf.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, padx=(0, 8))

        btn_browse_pdf = tk.Button(
            row_p, text="📁 Klasör Seç...", font=("Segoe UI", 9, "bold"), bg="#f1f5f9", fg="#0f172a",
            relief=tk.FLAT, bd=0, padx=12, pady=3, cursor="hand2", command=self.browse_pdf_folder
        )
        btn_browse_pdf.pack(side=tk.LEFT, padx=(0, 4))

        btn_open_pdf_dir = tk.Button(
            row_p, text="📂 Klasörü Aç", font=("Segoe UI", 8), bg="#ffffff", fg="#475569",
            relief=tk.FLAT, bd=0, padx=8, pady=3, cursor="hand2", command=lambda: self.open_folder_of_file(self.txt_set_pdf.get())
        )
        btn_open_pdf_dir.pack(side=tk.LEFT)

        # 3. KART: E-POSTA ALICI VE BİLGİ LİSTESİ
        card_mail = tk.Frame(scrollable_frame, bg="#ffffff", padx=16, pady=16, relief=tk.FLAT, bd=0)
        card_mail.pack(fill=tk.X, pady=(0, 14))

        tk.Label(card_mail, text="📧 Otomatik Vergi Maili Alıcı & Bilgi (CC) Ayarları", font=("Segoe UI", 11, "bold"), fg="#0f172a", bg="#ffffff").pack(anchor="w")
        tk.Label(card_mail, text="Taslak mail oluşturulduğunda varsayılan olarak yazılacak e-posta adresleri (noktalı virgül ';' ile ayırın).", font=("Segoe UI", 8), fg="#64748b", bg="#ffffff").pack(anchor="w", pady=(2, 8))

        tk.Label(card_mail, text="Kime (To):", font=("Segoe UI", 9, "bold"), fg="#334155", bg="#ffffff").pack(anchor="w")
        self.txt_set_to = tk.Entry(card_mail, font=("Consolas", 10), bd=1, relief=tk.SOLID)
        self.txt_set_to.pack(fill=tk.X, ipady=3, pady=(2, 8))

        tk.Label(card_mail, text="Bilgi (CC):", font=("Segoe UI", 9, "bold"), fg="#334155", bg="#ffffff").pack(anchor="w")
        self.txt_set_cc = tk.Entry(card_mail, font=("Consolas", 10), bd=1, relief=tk.SOLID)
        self.txt_set_cc.pack(fill=tk.X, ipady=3, pady=(2, 4))

        # 4. KART: QNB OTOMATİK GİRİŞ BİLGİLERİ
        card_qnb = tk.Frame(scrollable_frame, bg="#ffffff", padx=16, pady=16, relief=tk.FLAT, bd=0)
        card_qnb.pack(fill=tk.X, pady=(0, 14))

        tk.Label(card_qnb, text="🔑 QNB eSolutions Portalı Otomatik Giriş Bilgileri", font=("Segoe UI", 11, "bold"), fg="#0f172a", bg="#ffffff").pack(anchor="w")
        tk.Label(card_qnb, text="Buraya girdiğiniz kullanıcı kodu ve şifreniz kendi bilgisayarınızda güvenle saklanır ve QNB portalı açıldığında giriş alanlarına otomatik yazılır.", font=("Segoe UI", 8), fg="#64748b", bg="#ffffff").pack(anchor="w", pady=(2, 8))

        row_q1 = tk.Frame(card_qnb, bg="#ffffff")
        row_q1.pack(fill=tk.X, pady=(0, 6))

        tk.Label(row_q1, text="Kullanıcı Kodu / T.C. / Kullanıcı Adı:", font=("Segoe UI", 9, "bold"), fg="#334155", bg="#ffffff", width=32, anchor="w").pack(side=tk.LEFT)
        self.txt_qnb_user = tk.Entry(row_q1, font=("Consolas", 10), bd=1, relief=tk.SOLID)
        self.txt_qnb_user.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)

        row_q2 = tk.Frame(card_qnb, bg="#ffffff")
        row_q2.pack(fill=tk.X, pady=(0, 8))

        tk.Label(row_q2, text="Portal Şifresi:", font=("Segoe UI", 9, "bold"), fg="#334155", bg="#ffffff", width=32, anchor="w").pack(side=tk.LEFT)
        self.txt_qnb_pass = tk.Entry(row_q2, font=("Consolas", 10), bd=1, relief=tk.SOLID, show="*")
        self.txt_qnb_pass.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)

        self.var_qnb_autofill = tk.BooleanVar(value=True)
        chk_qnb = tk.Checkbutton(
            card_qnb, text="⚡ QNB Portalı açıldığında kullanıcı adı ve şifremi otomatik doldur",
            variable=self.var_qnb_autofill, font=("Segoe UI", 9), bg="#ffffff", activebackground="#ffffff"
        )
        chk_qnb.pack(anchor="w")

        # 5. KART: HANKOOK GLP OTOMATİK GİRİŞ BİLGİLERİ
        card_glp = tk.Frame(scrollable_frame, bg="#ffffff", padx=16, pady=16, relief=tk.FLAT, bd=0)
        card_glp.pack(fill=tk.X, pady=(0, 14))

        tk.Label(card_glp, text="🚛 Hankook GLP Lojistik Portalı Otomatik Giriş Bilgileri", font=("Segoe UI", 11, "bold"), fg="#0f172a", bg="#ffffff").pack(anchor="w")
        tk.Label(card_glp, text="Buraya girdiğiniz GLP kullanıcı kodu ve şifreniz kendi bilgisayarınızda güvenle saklanır ve GLP portalı açıldığında giriş alanlarına otomatik yazılır.", font=("Segoe UI", 8), fg="#64748b", bg="#ffffff").pack(anchor="w", pady=(2, 8))

        row_g1 = tk.Frame(card_glp, bg="#ffffff")
        row_g1.pack(fill=tk.X, pady=(0, 6))

        tk.Label(row_g1, text="GLP User ID / Kullanıcı Adı:", font=("Segoe UI", 9, "bold"), fg="#334155", bg="#ffffff", width=32, anchor="w").pack(side=tk.LEFT)
        self.txt_glp_user = tk.Entry(row_g1, font=("Consolas", 10), bd=1, relief=tk.SOLID)
        self.txt_glp_user.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)

        row_g2 = tk.Frame(card_glp, bg="#ffffff")
        row_g2.pack(fill=tk.X, pady=(0, 8))

        tk.Label(row_g2, text="GLP Şifresi:", font=("Segoe UI", 9, "bold"), fg="#334155", bg="#ffffff", width=32, anchor="w").pack(side=tk.LEFT)
        self.txt_glp_pass = tk.Entry(row_g2, font=("Consolas", 10), bd=1, relief=tk.SOLID, show="*")
        self.txt_glp_pass.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)

        self.var_glp_autofill = tk.BooleanVar(value=True)
        chk_glp = tk.Checkbutton(
            card_glp, text="⚡ GLP Portalı açıldığında kullanıcı adı ve şifremi otomatik doldur",
            variable=self.var_glp_autofill, font=("Segoe UI", 9), bg="#ffffff", activebackground="#ffffff"
        )
        chk_glp.pack(anchor="w")

        # 6. KART: DOĞRUER ONLİNE OTOMATİK GİRİŞ BİLGİLERİ
        card_dogruer = tk.Frame(scrollable_frame, bg="#ffffff", padx=16, pady=16, relief=tk.FLAT, bd=0)
        card_dogruer.pack(fill=tk.X, pady=(0, 14))

        tk.Label(card_dogruer, text="🌐 Doğruer Online (dogruer.online) Otomatik Giriş Bilgileri", font=("Segoe UI", 11, "bold"), fg="#0f172a", bg="#ffffff").pack(anchor="w")
        tk.Label(card_dogruer, text="Doğruer Online kullanıcı adı ve şifreniz kendi bilgisayarınızda güvenle saklanır ve Doğruer Online sekmesi açıldığında otomatik doldurulur.", font=("Segoe UI", 8), fg="#64748b", bg="#ffffff").pack(anchor="w", pady=(2, 8))

        row_d1 = tk.Frame(card_dogruer, bg="#ffffff")
        row_d1.pack(fill=tk.X, pady=(0, 6))

        tk.Label(row_d1, text="Doğruer Kullanıcı Kodu / E-Posta:", font=("Segoe UI", 9, "bold"), fg="#334155", bg="#ffffff", width=32, anchor="w").pack(side=tk.LEFT)
        self.txt_dogruer_user = tk.Entry(row_d1, font=("Consolas", 10), bd=1, relief=tk.SOLID)
        self.txt_dogruer_user.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)

        row_d2 = tk.Frame(card_dogruer, bg="#ffffff")
        row_d2.pack(fill=tk.X, pady=(0, 8))

        tk.Label(row_d2, text="Doğruer Şifresi:", font=("Segoe UI", 9, "bold"), fg="#334155", bg="#ffffff", width=32, anchor="w").pack(side=tk.LEFT)
        self.txt_dogruer_pass = tk.Entry(row_d2, font=("Consolas", 10), bd=1, relief=tk.SOLID, show="*")
        self.txt_dogruer_pass.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)

        self.var_dogruer_autofill = tk.BooleanVar(value=True)
        chk_dogruer = tk.Checkbutton(
            card_dogruer, text="⚡ Doğruer Portalı açıldığında kullanıcı adı ve şifremi otomatik doldur",
            variable=self.var_dogruer_autofill, font=("Segoe UI", 9), bg="#ffffff", activebackground="#ffffff"
        )
        chk_dogruer.pack(anchor="w")

        # ── YENİ: IMAP / Mail OTP Otomasyonu ─────────────────────────────
        tk.Frame(card_dogruer, bg="#e2e8f0", height=1).pack(fill=tk.X, pady=(14, 10))

        tk.Label(
            card_dogruer,
            text="📬 Mail OTP Otomasyonu (2FA Aktivasyon Kodu Okuyucu)",
            font=("Segoe UI", 10, "bold"), fg="#0f172a", bg="#ffffff"
        ).pack(anchor="w")
        tk.Label(
            card_dogruer,
            text="Sistem önce bilgisayarınızdaki Outlook uygulamasından (COM API) kodu okur — IMAP şifresi gerekmez!\n"
                 "Outlook açık değilse yedek olarak IMAP dener. Microsoft 365'te Basic Auth kapalıysa yalnızca Outlook yöntemi çalışır.\n"
                 "IMAP (yedek): host = outlook.office365.com, port = 993",
            font=("Segoe UI", 8), fg="#64748b", bg="#ffffff", justify="left"
        ).pack(anchor="w", pady=(2, 8))

        row_imap1 = tk.Frame(card_dogruer, bg="#ffffff")
        row_imap1.pack(fill=tk.X, pady=(0, 4))
        tk.Label(row_imap1, text="IMAP Sunucusu (Host):", font=("Segoe UI", 9, "bold"), fg="#334155", bg="#ffffff", width=32, anchor="w").pack(side=tk.LEFT)
        self.txt_imap_host = tk.Entry(row_imap1, font=("Consolas", 10), bd=1, relief=tk.SOLID)
        self.txt_imap_host.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)

        row_imap2 = tk.Frame(card_dogruer, bg="#ffffff")
        row_imap2.pack(fill=tk.X, pady=(0, 4))
        tk.Label(row_imap2, text="IMAP Port (varsayılan: 993):", font=("Segoe UI", 9, "bold"), fg="#334155", bg="#ffffff", width=32, anchor="w").pack(side=tk.LEFT)
        self.txt_imap_port = tk.Entry(row_imap2, font=("Consolas", 10), bd=1, relief=tk.SOLID, width=8)
        self.txt_imap_port.pack(side=tk.LEFT, ipady=3)

        row_imap3 = tk.Frame(card_dogruer, bg="#ffffff")
        row_imap3.pack(fill=tk.X, pady=(0, 4))
        tk.Label(row_imap3, text="Mail Kullanıcı Adı (e-posta):", font=("Segoe UI", 9, "bold"), fg="#334155", bg="#ffffff", width=32, anchor="w").pack(side=tk.LEFT)
        self.txt_imap_user = tk.Entry(row_imap3, font=("Consolas", 10), bd=1, relief=tk.SOLID)
        self.txt_imap_user.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)

        row_imap4 = tk.Frame(card_dogruer, bg="#ffffff")
        row_imap4.pack(fill=tk.X, pady=(0, 8))
        tk.Label(row_imap4, text="Mail Şifresi / App Password:", font=("Segoe UI", 9, "bold"), fg="#334155", bg="#ffffff", width=32, anchor="w").pack(side=tk.LEFT)
        self.txt_imap_pass = tk.Entry(row_imap4, font=("Consolas", 10), bd=1, relief=tk.SOLID, show="*")
        self.txt_imap_pass.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)

        row_imap_test = tk.Frame(card_dogruer, bg="#ffffff")
        row_imap_test.pack(fill=tk.X, pady=(0, 4))

        self.lbl_imap_test_result = tk.Label(
            row_imap_test, text="", font=("Segoe UI", 8), fg="#16a34a", bg="#ffffff", anchor="w"
        )
        self.lbl_imap_test_result.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Button(
            row_imap_test,
            text="🔌 Bağlantıyı Test Et",
            font=("Segoe UI", 9, "bold"),
            bg="#0f172a", fg="#ffffff",
            activebackground="#1e293b", activeforeground="#ffffff",
            relief=tk.FLAT, padx=10, pady=4, cursor="hand2",
            command=self.test_imap_connection
        ).pack(side=tk.RIGHT)
        # ──────────────────────────────────────────────────────────────────

        # 7. KART: 📱 TELEGRAM MOBİL OPERASYON ASİSTANI
        card_telegram = tk.Frame(scrollable_frame, bg="#ffffff", padx=16, pady=16, relief=tk.FLAT, bd=0)
        card_telegram.pack(fill=tk.X, pady=(0, 14))

        tk.Label(card_telegram, text="📱 Telegram Mobil Operasyon Asistanı (@scMASTERSUITbot)", font=("Segoe UI", 11, "bold"), fg="#0f172a", bg="#ffffff").pack(anchor="w")
        tk.Label(card_telegram, text="Telefonunuzdan @scMASTERSUITbot botuna herhangi bir Dosya No (örn: 26-085915), Referans veya /durum, /kirmizi komutlarını göndererek 7/24 canlı bilgi alabilirsiniz.", font=("Segoe UI", 8), fg="#64748b", bg="#ffffff").pack(anchor="w", pady=(2, 8))

        row_tel_btn = tk.Frame(card_telegram, bg="#ffffff")
        row_tel_btn.pack(fill=tk.X, pady=(4, 0))

        btn_open_tg = tk.Button(
            row_tel_btn, text="📱 Telegram'da Botu Aç (@scMASTERSUITbot)", font=("Segoe UI", 9, "bold"),
            bg="#0284c7", fg="#ffffff", activebackground="#0369a1", activeforeground="#ffffff",
            relief=tk.FLAT, padx=14, pady=6, cursor="hand2",
            command=lambda: webbrowser.open("https://t.me/scMASTERSUITbot")
        )
        btn_open_tg.pack(side=tk.LEFT, padx=(0, 10))

        btn_test_tg = tk.Button(
            row_tel_btn, text="🤖 Telegram Test Mesajı Gönder", font=("Segoe UI", 9, "bold"),
            bg="#f1f5f9", fg="#0f172a", relief=tk.FLAT, bd=0, padx=12, pady=5, cursor="hand2",
            command=self.send_telegram_test_notification
        )
        btn_test_tg.pack(side=tk.LEFT)

        # 7.5. KART: 🔔 WINDOWS MASAÜSTÜ BİLDİRİMLERİ (TOAST)
        card_notify = tk.Frame(scrollable_frame, bg="#ffffff", padx=16, pady=16, relief=tk.FLAT, bd=0)
        card_notify.pack(fill=tk.X, pady=(0, 14))

        tk.Label(card_notify, text="🔔 Windows Masaüstü Balon / Toast Bildirimleri", font=("Segoe UI", 11, "bold"), fg="#0f172a", bg="#ffffff").pack(anchor="w")
        tk.Label(
            card_notify,
            text="GTB beyanname tescil/statü değişimlerinde ve DP World kantar sonuçları çıktığında ekranınızın sağ alt köşesinde Windows bildirimi gösterir.",
            font=("Segoe UI", 8), fg="#64748b", bg="#ffffff"
        ).pack(anchor="w", pady=(2, 8))

        row_notify = tk.Frame(card_notify, bg="#ffffff")
        row_notify.pack(fill=tk.X, pady=(4, 0))

        self.var_desktop_notify = tk.BooleanVar(value=True)
        chk_notify = tk.Checkbutton(
            row_notify,
            text="🔔 Masaüstü bildirimlerini etkinleştir (GTB Tescil & Kantar Sonuçları)",
            variable=self.var_desktop_notify,
            font=("Segoe UI", 9, "bold"),
            fg="#0f172a",
            bg="#ffffff",
            activebackground="#ffffff"
        )
        chk_notify.pack(side=tk.LEFT, padx=(0, 15))

        btn_test_toast = tk.Button(
            row_notify,
            text="🔔 Test Bildirimi Gönder",
            font=("Segoe UI", 9, "bold"),
            bg="#f1f5f9",
            fg="#0f172a",
            relief=tk.FLAT,
            bd=0,
            padx=12,
            pady=5,
            cursor="hand2",
            command=self.send_desktop_test_notification
        )
        btn_test_toast.pack(side=tk.LEFT)

        # 8. BUTONLAR: KAYDET & SIFIRLA
        card_actions = tk.Frame(scrollable_frame, bg="#ffffff", padx=16, pady=16, relief=tk.FLAT, bd=0)
        card_actions.pack(fill=tk.X)

        btn_save = tk.Button(
            card_actions, text="💾 Ayarları Kaydet", font=("Segoe UI", 10, "bold"),
            bg="#334155", fg="#ffffff", activebackground="#475569", activeforeground="#ffffff",
            relief=tk.FLAT, padx=18, pady=8, cursor="hand2", command=self.save_settings_from_ui
        )
        btn_save.pack(side=tk.LEFT, padx=(0, 10))

        btn_reset = tk.Button(
            card_actions, text="↩️ Varsayılana Dön", font=("Segoe UI", 9, "bold"),
            bg="#f1f5f9", fg="#475569", activebackground="#e2e8f0",
            relief=tk.FLAT, bd=0, padx=14, pady=7, cursor="hand2", command=self.reset_settings_to_default
        )
        btn_reset.pack(side=tk.LEFT)

        self.load_settings_into_ui()

    def send_desktop_test_notification(self):
        """Masaüstü bildirim testini çalıştırır."""
        try:
            from tools.dogruer_master_suite.windows_notifier import send_desktop_notification
            send_desktop_notification(
                title="🏛️ Doğruer MasterSuite Test Bildirimi",
                message="✅ Windows masaüstü bildirim sistemi aktif ve başarıyla çalışıyor!",
                force=True
            )
            messagebox.showinfo("Bildirim Gönderildi", "Ekranınızın sağ alt köşesine test bildirimi gönderildi!")
        except Exception as e:
            messagebox.showerror("Hata", f"Bildirim gönderilemedi: {e}")

    def send_telegram_test_notification(self):
        tg_svc = getattr(self.app, "telegram_service", None)
        if tg_svc:
            chat_ids = getattr(tg_svc, "config", {}).get("authorized_chat_ids", [])
            if not chat_ids:
                messagebox.showinfo("Telegram Bildirimi", "Önce telefonunuzdan Telegram uygulamasında @scMASTERSUITbot botuna girip /start mesajı atmanız gerekmektedir.")
                webbrowser.open("https://t.me/scMASTERSUITbot")
                return
            if hasattr(tg_svc, "notify_critical_event"):
                tg_svc.notify_critical_event(
                    "TEST BİLDİRİMİ",
                    "✅ SmartClearance MasterSuite Telegram Mobil Asistanınız başarıyla bağlandı ve canlı çalışıyor!"
                )
            messagebox.showinfo("Başarılı", "✅ Test bildirimi telefonunuza gönderildi!")
        else:
            messagebox.showwarning("Uyarı", "Telegram servisi aktif değil.")

    def load_settings_into_ui(self):
        if not self.is_alive():
            return
        try:
            if not hasattr(self, "txt_set_excel") or not self.txt_set_excel.winfo_exists():
                return
        except Exception:
            return
        cfg = load_app_config()
        if hasattr(self.app, "config"):
            self.app.config = cfg

        self.txt_set_excel.delete(0, tk.END)
        self.txt_set_excel.insert(0, cfg.get("excel_path", ""))

        self.txt_set_pdf.delete(0, tk.END)
        self.txt_set_pdf.insert(0, cfg.get("pdf_folder", ""))

        self.txt_set_to.delete(0, tk.END)
        self.txt_set_to.insert(0, cfg.get("mail_to", ""))

        self.txt_set_cc.delete(0, tk.END)
        self.txt_set_cc.insert(0, cfg.get("mail_cc", ""))

        self.txt_qnb_user.delete(0, tk.END)
        self.txt_qnb_user.insert(0, cfg.get("qnb_user", ""))

        self.txt_qnb_pass.delete(0, tk.END)
        self.txt_qnb_pass.insert(0, cfg.get("qnb_pass", ""))

        self.var_qnb_autofill.set(cfg.get("qnb_autofill", True))

        self.txt_glp_user.delete(0, tk.END)
        self.txt_glp_user.insert(0, cfg.get("glp_user", ""))

        self.txt_glp_pass.delete(0, tk.END)
        self.txt_glp_pass.insert(0, cfg.get("glp_pass", ""))

        self.var_glp_autofill.set(cfg.get("glp_autofill", True))

        self.txt_dogruer_user.delete(0, tk.END)
        self.txt_dogruer_user.insert(0, cfg.get("dogruer_user", ""))

        self.txt_dogruer_pass.delete(0, tk.END)
        self.txt_dogruer_pass.insert(0, cfg.get("dogruer_pass", ""))

        self.var_dogruer_autofill.set(cfg.get("dogruer_autofill", True))

        # IMAP alanları
        if hasattr(self, "txt_imap_host"):
            self.txt_imap_host.delete(0, tk.END)
            self.txt_imap_host.insert(0, cfg.get("imap_host", "outlook.office365.com"))
        if hasattr(self, "txt_imap_port"):
            self.txt_imap_port.delete(0, tk.END)
            self.txt_imap_port.insert(0, str(cfg.get("imap_port", 993)))
        if hasattr(self, "txt_imap_user"):
            self.txt_imap_user.delete(0, tk.END)
            self.txt_imap_user.insert(0, cfg.get("imap_user", cfg.get("dogruer_user", "")))
        if hasattr(self, "txt_imap_pass"):
            self.txt_imap_pass.delete(0, tk.END)
            self.txt_imap_pass.insert(0, cfg.get("imap_pass", ""))

        if hasattr(self, "var_desktop_notify"):
            self.var_desktop_notify.set(cfg.get("enable_desktop_notifications", True))


    def browse_excel_path(self):
        filename = filedialog.askopenfilename(
            title="İş Takip Raporu Excel Dosyasını Seçin",
            filetypes=[("Excel Dosyaları", "*.xlsx;*.xls"), ("Tüm Dosyalar", "*.*")]
        )
        if filename:
            self.txt_set_excel.delete(0, tk.END)
            self.txt_set_excel.insert(0, filename)
            self._silent_save_settings_from_ui()
            self.apply_live_config()

    def browse_pdf_folder(self):
        folder = filedialog.askdirectory(title="Vergi Maili PDF Klasörünü Seçin")
        if folder:
            self.txt_set_pdf.delete(0, tk.END)
            self.txt_set_pdf.insert(0, folder)
            self._silent_save_settings_from_ui()
            self.apply_live_config()

    def open_folder_of_file(self, path):
        if not path:
            return
        target = path if os.path.isdir(path) else os.path.dirname(path)
        if os.path.exists(target):
            try:
                os.startfile(target)
            except Exception as e:
                messagebox.showerror("Hata", f"Klasör açılamadı: {e}")
        else:
            messagebox.showwarning("Uyarı", f"Klasör bulunamadı:\n{target}")

    def reset_settings_to_default(self):
        if messagebox.askyesno("Onay", "Tüm ayarları varsayılan değerlere sıfırlamak istiyor musunuz?"):
            cfg = DEFAULT_CONFIG.copy()
            save_app_config(cfg)
            if hasattr(self.app, "config"):
                self.app.config = cfg
            self.load_settings_into_ui()
            self.apply_live_config()
            messagebox.showinfo("Başarılı", "✅ Ayarlar varsayılan değerlerine sıfırlandı!")

    def _silent_save_settings_from_ui(self):
        """Sekme değişiminde ayarları sessizce kaydeder; boş şifre alanları mevcut değeri silmez."""
        self._apply_settings_from_ui(preserve_empty_passwords=True)

    def _apply_settings_from_ui(self, preserve_empty_passwords=True):
        if not hasattr(self, "txt_set_excel"):
            return

        cfg = getattr(self.app, "config", {})
        excel_p = self.txt_set_excel.get().strip()
        pdf_p = self.txt_set_pdf.get().strip()
        mail_to = self.txt_set_to.get().strip()
        mail_cc = self.txt_set_cc.get().strip()

        if excel_p: cfg["excel_path"] = excel_p
        if pdf_p: cfg["pdf_folder"] = pdf_p
        if mail_to: cfg["mail_to"] = mail_to
        if mail_cc: cfg["mail_cc"] = mail_cc

        if hasattr(self, "txt_qnb_user"):
            cfg["qnb_user"] = self.txt_qnb_user.get().strip()
        if hasattr(self, "txt_qnb_pass"):
            qnb_pass = self.txt_qnb_pass.get().strip()
            if qnb_pass or not preserve_empty_passwords:
                cfg["qnb_pass"] = qnb_pass
        if hasattr(self, "var_qnb_autofill"):
            cfg["qnb_autofill"] = self.var_qnb_autofill.get()

        if hasattr(self, "txt_glp_user"):
            cfg["glp_user"] = self.txt_glp_user.get().strip()
        if hasattr(self, "txt_glp_pass"):
            glp_pass = self.txt_glp_pass.get().strip()
            if glp_pass or not preserve_empty_passwords:
                cfg["glp_pass"] = glp_pass
        if hasattr(self, "var_glp_autofill"):
            cfg["glp_autofill"] = self.var_glp_autofill.get()

        if hasattr(self, "txt_dogruer_user"):
            cfg["dogruer_user"] = self.txt_dogruer_user.get().strip()
        if hasattr(self, "txt_dogruer_pass"):
            dogruer_pass = self.txt_dogruer_pass.get().strip()
            if dogruer_pass or not preserve_empty_passwords:
                cfg["dogruer_pass"] = dogruer_pass
        if hasattr(self, "var_dogruer_autofill"):
            cfg["dogruer_autofill"] = self.var_dogruer_autofill.get()

        # IMAP ayarlarını kaydet
        if hasattr(self, "txt_imap_host"):
            cfg["imap_host"] = self.txt_imap_host.get().strip() or "outlook.office365.com"
        if hasattr(self, "txt_imap_port"):
            try:
                cfg["imap_port"] = int(self.txt_imap_port.get().strip())
            except ValueError:
                cfg["imap_port"] = 993
        if hasattr(self, "txt_imap_user"):
            cfg["imap_user"] = self.txt_imap_user.get().strip()
        if hasattr(self, "txt_imap_pass"):
            imap_pass = self.txt_imap_pass.get().strip()
            if imap_pass or not preserve_empty_passwords:
                cfg["imap_pass"] = imap_pass

        if hasattr(self, "var_desktop_notify"):
            cfg["enable_desktop_notifications"] = self.var_desktop_notify.get()

        save_app_config(cfg)
        if hasattr(self.engine, "config"):
            self.engine.config = cfg
        if hasattr(self.engine, "excel_path"):
            self.engine.excel_path = cfg.get("excel_path", "")

    def save_settings_from_ui(self):
        excel_p = self.txt_set_excel.get().strip()
        if excel_p and not os.path.exists(excel_p):
            if not messagebox.askyesno("Uyarı", f"Seçilen Excel dosyası bulunamadı:\n{excel_p}\n\nYine de kaydetmek istiyor musunuz?"):
                return

        self._apply_settings_from_ui(preserve_empty_passwords=False)
        self.apply_live_config()
        messagebox.showinfo("Başarılı", "✅ Ayarlar başarıyla kaydedildi ve tüm sistem anlık olarak yeni ayarlara göre güncellendi!")

    def apply_live_config(self):
        cfg = getattr(self.app, "config", load_app_config())
        if hasattr(self.engine, "config"):
            self.engine.config = cfg
        if hasattr(self.engine, "excel_path"):
            self.engine.excel_path = cfg.get("excel_path", "")
        if hasattr(self.app, "trigger_sync_async"):
            self.app.trigger_sync_async()

    def test_imap_connection(self):
        """'🔌 Bağlantıyı Test Et' butonuna basıldığında çağrılır."""
        import threading
        # Önce mevcut UI değerlerini geçici olarak kaydet
        self._apply_settings_from_ui(preserve_empty_passwords=True)

        if hasattr(self, "lbl_imap_test_result"):
            self.lbl_imap_test_result.config(text="⏳ Test ediliyor...", fg="#f59e0b")

        def _run_test():
            try:
                from tools.dogruer_online_bridge.evrim_imap_reader import EvrimImapReader
                reader = EvrimImapReader()
                ok, msg = reader.test_connection()
                color = "#16a34a" if ok else "#dc2626"
                self.after(0, lambda: self.lbl_imap_test_result.config(text=msg, fg=color)
                           if hasattr(self, "lbl_imap_test_result") else None)
            except Exception as e:
                self.after(0, lambda: self.lbl_imap_test_result.config(
                    text=f"❌ Hata: {e}", fg="#dc2626")
                    if hasattr(self, "lbl_imap_test_result") else None)

        threading.Thread(target=_run_test, daemon=True).start()
