"""
==============================================================================
🏛️ HANKOOK & DOĞRUER - CANLI OPERASYON KOKPİTİ v2.0 (Ultra Modern Tasarım)
Firma: Doğruer Gümrük Müşavirliği A.Ş. & Hankook Lastikleri A.Ş.
Geliştirici: Antigravity AI
Tasarım Yenilikleri:
1. 💎 Modern SaaS Görünümü (Genişletilmiş 1260px Ekran, Ferah Kartlar)
2. 🎴 İnteraktif Metrik Kartları (Büyük İstatistikler, Vurgulu Kenarlıklar, Hover Efekti)
3. 📊 Sütun Genişlikleri ve Hizalamaları Kusursuz Tablo (Sıfır Metin Kesilmesi)
4. 📋 Özel Tasarım Sağ Detay Kartı (Düz Metin Yerine Şık Grid Kart Tasarımı)
5. ⚡ Çift Canlı İzleyici (Outlook & Excel Anlık Senkronizasyonu)
==============================================================================
"""

import sys
import os
import re
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime

# Excel & Outlook
try:
    import openpyxl
except ImportError:
    openpyxl = None

try:
    import win32com.client
    import pythoncom
except ImportError:
    win32com = None

DEFAULT_EXCEL_PATH = r"C:\Users\ozan.gemici\OneDrive - DOGRUER GUMRUK MUSAVIRLIGI A.Ş\Resimler\HANKOOK İŞ TAKİP RAPORU.xlsx"


def read_outlook_sent_cache(limit=350):
    """Outlook Gönderilmiş Öğeler önbelleği oluşturur"""
    cache = []
    if not win32com:
        return cache
    try:
        pythoncom.CoInitialize()
        outlook = win32com.client.Dispatch("Outlook.Application")
        namespace = outlook.GetNamespace("MAPI")
        sent_folder = namespace.GetDefaultFolder(5)
        items = sent_folder.Items
        items.Sort("[SentOn]", True)

        count = 0
        for item in items:
            if count >= limit:
                break
            try:
                subj = str(item.Subject or "")
                to_addr = str(item.To or "")
                sent_time = item.SentOn
                try:
                    sent_str = sent_time.strftime("%d.%m.%Y %H:%M")
                except Exception:
                    sent_str = str(sent_time)[:16]

                attachments = []
                for att in item.Attachments:
                    fname = att.FileName
                    if not re.match(r"^image\d+\.(png|jpg|gif)$", fname, re.I):
                        attachments.append(fname)

                cache.append({
                    "subject": subj,
                    "to": to_addr,
                    "sent_on": sent_str,
                    "attachments": attachments,
                    "is_reply": subj.strip().upper().startswith("RE:") or subj.strip().upper().startswith("FW:")
                })
                count += 1
            except Exception:
                continue
    except Exception as e:
        print(f"Outlook Okuma Hatası: {e}")
    finally:
        pythoncom.CoUninitialize()

    return cache


def parse_hankook_excel(excel_path):
    """HANKOOK İŞ TAKİP RAPORU.xlsx dosyasını okur"""
    if not os.path.exists(excel_path) or not openpyxl:
        return []

    records = []
    try:
        wb = openpyxl.load_workbook(excel_path, data_only=True)
        sheet_name = "GÜNCEL RAPOR" if "GÜNCEL RAPOR" in wb.sheetnames else wb.sheetnames[0]
        ws = wb[sheet_name]

        for r in range(2, ws.max_row + 1):
            dosya = str(ws.cell(r, 1).value or "").strip()
            gumruk = str(ws.cell(r, 2).value or "").strip()
            ref = str(ws.cell(r, 3).value or "").strip()
            bayi = str(ws.cell(r, 4).value or "").strip()
            acenta = str(ws.cell(r, 5).value or "").strip()
            bl = str(ws.cell(r, 6).value or "").strip()
            ordino = str(ws.cell(r, 7).value or "").strip()
            transfer = str(ws.cell(r, 8).value or "").strip()
            tareks = str(ws.cell(r, 9).value or "").strip()
            tareks_sonuc = str(ws.cell(r, 10).value or "").strip()
            tescil = str(ws.cell(r, 12).value or "").strip()
            hat = str(ws.cell(r, 13).value or "").strip().upper()
            kapanis = str(ws.cell(r, 14).value or "").strip()
            vergi = str(ws.cell(r, 15).value or "").strip()
            liman = str(ws.cell(r, 22).value or "").strip()
            aciklama = str(ws.cell(r, 17).value or "").strip()

            def clean_date(d_val):
                if not d_val or d_val.lower() == "none": return ""
                if "00:00:00" in d_val:
                    parts = d_val.split()[0].split("-")
                    if len(parts) == 3:
                        return f"{parts[2]}.{parts[1]}.{parts[0]}"
                return d_val

            ordino_clean = clean_date(ordino)
            tareks_clean = clean_date(tareks)
            tescil_clean = clean_date(tescil)
            kapanis_clean = clean_date(kapanis)
            vergi_clean = clean_date(vergi)

            if dosya or ref or bl:
                is_tescil_stage = bool(tescil_clean) or ("TESCIL" in aciklama.upper()) or ("TESCİL" in aciklama.upper())
                is_tax_pending = is_tescil_stage and (not vergi_clean)

                if kapanis_clean:
                    stage = "5_KAPANDI"
                    stage_title = "🟢 Kapandı / Arşiv"
                elif is_tescil_stage:
                    if hat == "KIRMIZI":
                        stage = "3_MUAYENE"
                        stage_title = "🔴 Kırmızı Hat (Muayenede)"
                    else:
                        stage = "3_TESCILDE"
                        stage_title = "🔵 Tescilde / Tescil Oldu"
                elif ordino_clean or tareks_clean:
                    stage = "2_ORDINO_TAREKS"
                    stage_title = "🟠 Ordino / Tareks İşlemde"
                else:
                    stage = "1_EVRAK"
                    stage_title = "🟡 Yeni Evrak / Hazırlık"

                records.append({
                    "row_idx": r,
                    "dosya": dosya,
                    "gumruk": gumruk,
                    "ref": ref,
                    "bayi": bayi,
                    "acenta": acenta,
                    "bl": bl,
                    "ordino": ordino_clean,
                    "transfer": transfer,
                    "tareks": tareks_clean,
                    "tareks_sonuc": tareks_sonuc,
                    "tescil": tescil_clean,
                    "hat": hat,
                    "kapanis": kapanis_clean,
                    "vergi": vergi_clean,
                    "liman": liman,
                    "aciklama": aciklama,
                    "stage": stage,
                    "stage_title": stage_title,
                    "is_tescil_stage": is_tescil_stage,
                    "is_tax_pending": is_tax_pending,
                    "mail_status": "⏳ Kontrol Ediliyor...",
                    "mail_date": "",
                    "mail_badge": "grey"
                })

    except Exception as e:
        print(f"Excel Okuma Hatası: {e}")

    return records


class HankookOperationCockpitApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🏛️ Hankook & Doğruer - Canlı Operasyon Kokpiti v2.0")
        self.root.geometry("1280x820")
        self.root.minsize(1050, 720)

        self.excel_path = DEFAULT_EXCEL_PATH
        self.last_excel_mtime = 0
        self.last_outlook_sent_count = 0
        self.all_records = []
        self.filtered_records = []
        self.outlook_cache = []
        self.current_stage_filter = "ALL_ACTIVE"
        self.is_reloading = False

        self.setup_styles()
        self.setup_ui()
        self.reload_data_async()

        self.start_dual_live_watcher()
        self.root.bind("<FocusIn>", lambda e: self.check_live_changes())

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")

        # Treeview modernleştirme
        self.style.configure(
            "Treeview",
            font=("Segoe UI", 9),
            rowheight=30,
            background="#ffffff",
            fieldbackground="#ffffff",
            borderwidth=0
        )
        self.style.configure(
            "Treeview.Heading",
            font=("Segoe UI", 9, "bold"),
            background="#0f172a",
            foreground="#ffffff",
            padding=[8, 8],
            relief="flat"
        )
        self.style.map("Treeview.Heading", background=[("active", "#1e293b")])

    def setup_ui(self):
        # 1. HEADER (Koyu Lacivert / Premium)
        header = tk.Frame(self.root, bg="#0f172a", height=75)
        header.pack(fill=tk.X)

        title_box = tk.Frame(header, bg="#0f172a")
        title_box.pack(side=tk.LEFT, padx=20, pady=12)

        lbl_title = tk.Label(
            title_box,
            text="🏛️ HANKOOK & DOĞRUER - CANLI OPERASYON KOKPİTİ",
            font=("Segoe UI", 14, "bold"),
            fg="#ffffff",
            bg="#0f172a"
        )
        lbl_title.pack(anchor="w")

        self.lbl_file_status = tk.Label(
            title_box,
            text="⚡ Canlı İzleyici Aktif (Excel & Outlook Bağlanıyor...)",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#0f172a"
        )
        self.lbl_file_status.pack(anchor="w", pady=(2, 0))

        btn_box = tk.Frame(header, bg="#0f172a")
        btn_box.pack(side=tk.RIGHT, padx=20, pady=14)

        btn_open_excel = tk.Button(
            btn_box,
            text="📊 Excel Dosyasını Aç",
            font=("Segoe UI", 9, "bold"),
            bg="#107c41",
            fg="#ffffff",
            activebackground="#0b5e31",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=14,
            pady=6,
            cursor="hand2",
            command=self.open_excel_file
        )
        btn_open_excel.pack(side=tk.LEFT, padx=(0, 10))

        btn_reload = tk.Button(
            btn_box,
            text="🔄 Şimdi Yenile",
            font=("Segoe UI", 9, "bold"),
            bg="#2563eb",
            fg="#ffffff",
            activebackground="#1d4ed8",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=14,
            pady=6,
            cursor="hand2",
            command=self.reload_data_async
        )
        btn_reload.pack(side=tk.LEFT)

        # 2. MAIN CONTAINER
        main_content = tk.Frame(self.root, bg="#f1f5f9", padx=16, pady=12)
        main_content.pack(fill=tk.BOTH, expand=True)

        # 3. METRİK FİLTRE KARTLARI (Modern Gölgeli Kartlar)
        metric_bar = tk.Frame(main_content, bg="#f1f5f9")
        metric_bar.pack(fill=tk.X, pady=(0, 12))

        self.btn_card_active = self.create_modern_metric_card(
            metric_bar, "AÇIK DOSYALAR", "0", "Toplam Aktif", "#1e3a8a", "#dbeafe", lambda: self.set_filter("ALL_ACTIVE")
        )
        self.btn_card_mail_wait = self.create_modern_metric_card(
            metric_bar, "VERGİ MAİLİ BEKLEYEN", "0", "Acil Gönderim", "#dc2626", "#fee2e2", lambda: self.set_filter("MAIL_WAITING")
        )
        self.btn_card_tescil = self.create_modern_metric_card(
            metric_bar, "TESCİL / MUAYENE", "0", "Sarı / Kırmızı Hat", "#2563eb", "#eff6ff", lambda: self.set_filter("3_TESCILDE")
        )
        self.btn_card_ordino = self.create_modern_metric_card(
            metric_bar, "ORDİNO / TAREKS", "0", "İşlem Aşamasında", "#7c3aed", "#f3e8ff", lambda: self.set_filter("2_ORDINO_TAREKS")
        )
        self.btn_card_closed = self.create_modern_metric_card(
            metric_bar, "KAPANDI / ARŞİV", "0", "Tamamlananlar", "#16a34a", "#dcfce7", lambda: self.set_filter("5_KAPANDI")
        )

        # 4. ARAMA & FİLTRELEME BARI
        search_bar = tk.Frame(main_content, bg="#ffffff", padx=14, pady=10, relief=tk.SOLID, bd=1)
        search_bar.pack(fill=tk.X, pady=(0, 12))

        lbl_s = tk.Label(search_bar, text="🔍 Hızlı Ara & Süzgeç:", font=("Segoe UI", 10, "bold"), bg="#ffffff", fg="#0f172a")
        lbl_s.pack(side=tk.LEFT, padx=(0, 10))

        self.txt_search = tk.Entry(search_bar, font=("Segoe UI", 10), bd=1, relief=tk.SOLID)
        self.txt_search.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 12), ipady=4)
        self.txt_search.bind("<KeyRelease>", lambda e: self.apply_text_filter())

        self.lbl_filtered_count = tk.Label(
            search_bar,
            text="0 Kayıt Gösteriliyor",
            font=("Segoe UI", 9, "bold"),
            fg="#1e40af",
            bg="#eff6ff",
            padx=10,
            pady=3,
            relief=tk.GROOVE
        )
        self.lbl_filtered_count.pack(side=tk.RIGHT)

        # 5. SPLIT PANEL (Sol: Tablo, Sağ: Şık Detay Kartı)
        paned = tk.PanedWindow(main_content, orient=tk.HORIZONTAL, bg="#f1f5f9", sashwidth=6)
        paned.pack(fill=tk.BOTH, expand=True)

        # SOL PANEL: TABLO
        table_frame = tk.Frame(paned, bg="#ffffff", relief=tk.SOLID, bd=1)
        paned.add(table_frame, minsize=760, stretch="always")

        columns = ("dosya", "ref", "bl", "asama", "hat", "mail", "bayi", "liman")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=14)

        self.tree.heading("dosya", text="Dosya No")
        self.tree.heading("ref", text="Referans No")
        self.tree.heading("bl", text="Konşimento (B/L)")
        self.tree.heading("asama", text="Operasyonel Aşama")
        self.tree.heading("hat", text="Hat")
        self.tree.heading("mail", text="Vergi Maili Durumu")
        self.tree.heading("bayi", text="Bayi / Alıcı")
        self.tree.heading("liman", text="Liman")

        # Genişlikler optimize edildi (Kesilme tamamen engellendi)
        self.tree.column("dosya", width=90, anchor="center")
        self.tree.column("ref", width=105, anchor="center")
        self.tree.column("bl", width=145, anchor="center")
        self.tree.column("asama", width=175, anchor="w")
        self.tree.column("hat", width=70, anchor="center")
        self.tree.column("mail", width=180, anchor="w")
        self.tree.column("bayi", width=130, anchor="w")
        self.tree.column("liman", width=95, anchor="center")

        # Tag Renkleri
        self.tree.tag_configure("kirmizi_hat", background="#fee2e2", foreground="#991b1b")
        self.tree.tag_configure("tescil_ok", background="#f0fdf4", foreground="#166534")
        self.tree.tag_configure("mail_ok", background="#ecfdf5", foreground="#047857")
        self.tree.tag_configure("mail_warning", background="#fef2f2", foreground="#b91c1c")
        self.tree.tag_configure("closed", background="#f8fafc", foreground="#94a3b8")

        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        sc_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=sc_y.set)
        sc_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)

        # SAĞ PANEL: DETAY DOSYASI (ŞIK MODERN KART)
        self.detail_frame = tk.Frame(paned, bg="#ffffff", padx=16, pady=14, relief=tk.SOLID, bd=1)
        paned.add(self.detail_frame, minsize=380, stretch="never")

        self.setup_modern_detail_card()

        # 6. ALT DURUM ÇUBUĞU
        self.status_bar = tk.Label(
            self.root,
            text="🟢 Çift Canlı İzleyici Aktif | Outlook'tan mail attığınız veya Excel'e kaydettiğiniz anda kokpit otomatik güncellenir.",
            bd=1,
            relief=tk.SUNKEN,
            anchor=tk.W,
            font=("Segoe UI", 9),
            bg="#ffffff",
            fg="#475569",
            padx=12,
            pady=5
        )
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    def create_modern_metric_card(self, parent, title, val, subtitle, accent_color, bg_tint, command):
        card = tk.Frame(parent, bg="#ffffff", padx=14, pady=10, relief=tk.SOLID, bd=1, cursor="hand2")
        card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)

        top_strip = tk.Frame(card, bg=accent_color, height=3)
        top_strip.pack(fill=tk.X, pady=(0, 6))

        lbl_t = tk.Label(card, text=title, font=("Segoe UI", 8, "bold"), fg="#64748b", bg="#ffffff", cursor="hand2")
        lbl_t.pack(anchor="w")

        lbl_v = tk.Label(card, text=val, font=("Segoe UI", 16, "bold"), fg=accent_color, bg="#ffffff", cursor="hand2")
        lbl_v.pack(anchor="w", pady=(1, 1))

        lbl_sub = tk.Label(card, text=subtitle, font=("Segoe UI", 8), fg="#94a3b8", bg="#ffffff", cursor="hand2")
        lbl_sub.pack(anchor="w")

        for w in (card, top_strip, lbl_t, lbl_v, lbl_sub):
            w.bind("<Button-1>", lambda e, cmd=command: cmd())

        return {"card": card, "val_lbl": lbl_v, "title": title}

    def setup_modern_detail_card(self):
        head_box = tk.Frame(self.detail_frame, bg="#ffffff")
        head_box.pack(fill=tk.X, pady=(0, 10))

        lbl_head = tk.Label(head_box, text="📋 SEÇİLİ DOSYA DETAYI", font=("Segoe UI", 11, "bold"), fg="#0f172a", bg="#ffffff")
        lbl_head.pack(side=tk.LEFT)

        self.lbl_det_dosya_badge = tk.Label(
            head_box,
            text="—",
            font=("Segoe UI", 10, "bold"),
            fg="#2563eb",
            bg="#eff6ff",
            padx=8,
            pady=2,
            relief=tk.GROOVE
        )
        self.lbl_det_dosya_badge.pack(side=tk.RIGHT)

        # Bilgi Satırları
        info_scroll = tk.Frame(self.detail_frame, bg="#f8fafc", padx=12, pady=10, relief=tk.SOLID, bd=1)
        info_scroll.pack(fill=tk.BOTH, expand=True)

        self.lbl_det_ref = self.add_detail_row(info_scroll, "🔖 Referans No:", "—")
        self.lbl_det_bl = self.add_detail_row(info_scroll, "🚢 Konşimento (B/L):", "—")
        self.lbl_det_bayi = self.add_detail_row(info_scroll, "🏢 Bayi / Alıcı:", "—")
        self.lbl_det_liman = self.add_detail_row(info_scroll, "📍 Gümrük / Liman:", "—")
        
        sep1 = tk.Frame(info_scroll, bg="#e2e8f0", height=1)
        sep1.pack(fill=tk.X, pady=6)

        self.lbl_det_stage = self.add_detail_row(info_scroll, "⚡ Operasyonel Aşama:", "—")
        self.lbl_det_hat = self.add_detail_row(info_scroll, "🚦 Hat Durumu:", "—")
        self.lbl_det_tescil = self.add_detail_row(info_scroll, "📅 Tescil Tarihi:", "—")
        self.lbl_det_ordino = self.add_detail_row(info_scroll, "📦 Ordino Teslim:", "—")
        self.lbl_det_tareks = self.add_detail_row(info_scroll, "📋 Tareks Başvuru:", "—")
        self.lbl_det_vergi_odeme = self.add_detail_row(info_scroll, "💰 Vergi Ödeme:", "—")

        sep2 = tk.Frame(info_scroll, bg="#e2e8f0", height=1)
        sep2.pack(fill=tk.X, pady=6)

        lbl_mail_title = tk.Label(info_scroll, text="📬 OUTLOOK VERGİ MAİL DURUMU", font=("Segoe UI", 9, "bold"), fg="#1e3a8a", bg="#f8fafc")
        lbl_mail_title.pack(anchor="w", pady=(2, 4))

        self.lbl_det_mail_status = self.add_detail_row(info_scroll, "• Gönderim Durumu:", "—")
        self.lbl_det_mail_time = self.add_detail_row(info_scroll, "• Gönderim Saati:", "—")
        self.lbl_det_mail_to = self.add_detail_row(info_scroll, "• Alıcı (Kime):", "—")
        self.lbl_det_mail_atts = self.add_detail_row(info_scroll, "• Gönderilen PDF'ler:", "—")

        sep3 = tk.Frame(info_scroll, bg="#e2e8f0", height=1)
        sep3.pack(fill=tk.X, pady=6)

        self.lbl_det_aciklama = self.add_detail_row(info_scroll, "📝 Açıklama:", "—")

    def add_detail_row(self, parent, label_text, default_val):
        row = tk.Frame(parent, bg="#f8fafc")
        row.pack(fill=tk.X, pady=2)

        lbl_k = tk.Label(row, text=label_text, font=("Segoe UI", 9), fg="#64748b", bg="#f8fafc", width=18, anchor="w")
        lbl_k.pack(side=tk.LEFT)

        lbl_v = tk.Label(row, text=default_val, font=("Segoe UI", 9, "bold"), fg="#0f172a", bg="#f8fafc", anchor="w", wraplength=200, justify=tk.LEFT)
        lbl_v.pack(side=tk.LEFT, fill=tk.X, expand=True)

        return lbl_v

    def start_dual_live_watcher(self):
        def watcher():
            while True:
                time.sleep(2.5)
                try:
                    needs_refresh = False

                    if os.path.exists(self.excel_path):
                        mtime = os.path.getmtime(self.excel_path)
                        if self.last_excel_mtime != 0 and mtime > self.last_excel_mtime:
                            needs_refresh = True

                    if win32com and not needs_refresh:
                        try:
                            pythoncom.CoInitialize()
                            ol = win32com.client.Dispatch("Outlook.Application")
                            ns = ol.GetNamespace("MAPI")
                            sent_f = ns.GetDefaultFolder(5)
                            curr_count = sent_f.Items.Count
                            if self.last_outlook_sent_count != 0 and curr_count != self.last_outlook_sent_count:
                                needs_refresh = True
                        except Exception:
                            pass
                        finally:
                            pythoncom.CoUninitialize()

                    if needs_refresh and not self.is_reloading:
                        self.root.after(0, self.reload_data_async)

                except Exception:
                    pass

        threading.Thread(target=watcher, daemon=True).start()

    def check_live_changes(self):
        try:
            needs_refresh = False
            if os.path.exists(self.excel_path):
                mtime = os.path.getmtime(self.excel_path)
                if self.last_excel_mtime != 0 and mtime > self.last_excel_mtime:
                    needs_refresh = True

            if needs_refresh and not self.is_reloading:
                self.reload_data_async()
        except Exception:
            pass

    def reload_data_async(self):
        if self.is_reloading:
            return
        self.is_reloading = True
        self.lbl_file_status.config(text="🔄 Veriler senkronize ediliyor...", fg="#fbbf24")
        threading.Thread(target=self._reload_worker, daemon=True).start()

    def _reload_worker(self):
        try:
            if os.path.exists(self.excel_path):
                self.last_excel_mtime = os.path.getmtime(self.excel_path)
        except Exception:
            pass

        try:
            if win32com:
                pythoncom.CoInitialize()
                ol = win32com.client.Dispatch("Outlook.Application")
                ns = ol.GetNamespace("MAPI")
                sent_f = ns.GetDefaultFolder(5)
                self.last_outlook_sent_count = sent_f.Items.Count
                pythoncom.CoUninitialize()
        except Exception:
            pass

        records = parse_hankook_excel(self.excel_path)
        outlook_records = read_outlook_sent_cache(limit=350)
        self.outlook_cache = outlook_records

        for r in records:
            ref_clean = re.sub(r"[^A-Z0-9]", "", r["ref"].upper())
            dosya_clean = re.sub(r"[^A-Z0-9]", "", r["dosya"].upper())
            bl_clean = re.sub(r"[^A-Z0-9]", "", r["bl"].upper())

            found_mail = None
            for m in outlook_records:
                subj_c = re.sub(r"[^A-Z0-9]", "", m["subject"].upper())
                att_c = re.sub(r"[^A-Z0-9]", "", " ".join(m["attachments"]).upper())

                is_vergi_mail = "VERG" in m["subject"].upper() or "VERGI" in m["subject"].upper()

                if (ref_clean and (ref_clean in subj_c or ref_clean in att_c)) or \
                   (dosya_clean and len(dosya_clean) >= 6 and (dosya_clean in subj_c or dosya_clean in att_c)) or \
                   (bl_clean and len(bl_clean) >= 7 and (bl_clean in subj_c or bl_clean in att_c)):
                    found_mail = m
                    break

            if found_mail:
                if found_mail["attachments"]:
                    r["mail_status"] = f"🟢 Atıldı ({found_mail['sent_on'][-5:]})"
                    r["mail_badge"] = "green"
                else:
                    r["mail_status"] = f"🟡 Yanıt ({found_mail['sent_on'][-5:]})"
                    r["mail_badge"] = "yellow"
                r["mail_date"] = found_mail["sent_on"]
                r["mail_to"] = found_mail["to"]
                r["mail_attachments"] = found_mail["attachments"]
                r["mail_subject"] = found_mail["subject"]
            else:
                if r["is_tax_pending"]:
                    r["mail_status"] = "🔴 Vergi Maili Bekliyor"
                    r["mail_badge"] = "red"
                elif r["stage"] == "2_ORDINO_TAREKS":
                    r["mail_status"] = "⏳ Tareks/Ordino Aşamasında"
                    r["mail_badge"] = "grey"
                else:
                    r["mail_status"] = "⏳ Hazırlık Aşamasında"
                    r["mail_badge"] = "grey"

                r["mail_date"] = ""
                r["mail_to"] = ""
                r["mail_attachments"] = []
                r["mail_subject"] = ""

        self.all_records = records
        self.is_reloading = False
        self.root.after(0, self.update_dashboard_ui)

    def update_dashboard_ui(self):
        total_open = sum(1 for r in self.all_records if not r["kapanis"])
        tescil_count = sum(1 for r in self.all_records if not r["kapanis"] and (r["stage"] in ["3_TESCILDE", "3_MUAYENE"]))
        mail_waiting_count = sum(1 for r in self.all_records if not r["kapanis"] and r["is_tax_pending"] and r["mail_badge"] == "red")
        ordino_count = sum(1 for r in self.all_records if not r["kapanis"] and r["stage"] == "2_ORDINO_TAREKS")
        closed_count = sum(1 for r in self.all_records if r["kapanis"])

        self.btn_card_active["val_lbl"].config(text=str(total_open))
        self.btn_card_mail_wait["val_lbl"].config(text=str(mail_waiting_count))
        self.btn_card_tescil["val_lbl"].config(text=str(tescil_count))
        self.btn_card_ordino["val_lbl"].config(text=str(ordino_count))
        self.btn_card_closed["val_lbl"].config(text=str(closed_count))

        self.lbl_file_status.config(
            text=f"⚡ Canlı İzlemede ({len(self.all_records)} Toplam / {total_open} Açık / {mail_waiting_count} Vergi Maili Bekleyen) - {datetime.now().strftime('%H:%M:%S')}",
            fg="#4ade80"
        )
        self.status_bar.config(text=f"⚡ Otomatik senkronize edildi! Son güncelleme: {datetime.now().strftime('%H:%M:%S')}", fg="#16a34a")

        self.apply_filter()

    def set_filter(self, stage_code):
        self.current_stage_filter = stage_code
        self.apply_filter()

    def apply_filter(self):
        st = self.current_stage_filter

        if st == "ALL_ACTIVE":
            self.filtered_records = [r for r in self.all_records if not r["kapanis"]]
        elif st == "MAIL_WAITING":
            self.filtered_records = [r for r in self.all_records if not r["kapanis"] and r["is_tax_pending"] and r["mail_badge"] == "red"]
        elif st == "3_TESCILDE":
            self.filtered_records = [r for r in self.all_records if not r["kapanis"] and r["stage"] in ["3_TESCILDE", "3_MUAYENE"]]
        elif st == "2_ORDINO_TAREKS":
            self.filtered_records = [r for r in self.all_records if not r["kapanis"] and r["stage"] == "2_ORDINO_TAREKS"]
        elif st == "5_KAPANDI":
            self.filtered_records = [r for r in self.all_records if r["kapanis"]]
        else:
            self.filtered_records = self.all_records[:]

        self.apply_text_filter()

    def apply_text_filter(self):
        query = self.txt_search.get().strip().upper()

        final_list = []
        for r in self.filtered_records:
            full_str = f"{r['dosya']} {r['ref']} {r['bl']} {r['bayi']} {r['liman']} {r['hat']} {r['stage_title']} {r['aciklama']}".upper()
            if not query or query in full_str:
                final_list.append(r)

        for item in self.tree.get_children():
            self.tree.delete(item)

        for r in final_list:
            tag = "normal"
            if r["kapanis"]:
                tag = "closed"
            elif r["hat"] == "KIRMIZI":
                tag = "kirmizi_hat"
            elif r["mail_badge"] == "red":
                tag = "mail_warning"
            elif r["stage"] in ["3_TESCILDE", "3_MUAYENE"]:
                tag = "tescil_ok"
            elif r["mail_badge"] == "green":
                tag = "mail_ok"

            self.tree.insert("", tk.END, values=(
                r["dosya"] or "—",
                r["ref"] or "—",
                r["bl"] or "—",
                r["stage_title"],
                r["hat"] or "—",
                r["mail_status"],
                r["bayi"] or "—",
                r["liman"] or "—"
            ), tags=(tag,), iid=str(r["row_idx"]))

        self.lbl_filtered_count.config(text=f"{len(final_list)} Kayıt Listeleniyor")

    def on_tree_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return

        row_idx = int(sel[0])
        rec = next((r for r in self.all_records if r["row_idx"] == row_idx), None)
        if not rec:
            return

        self.lbl_det_dosya_badge.config(text=rec["dosya"] or "Dosya No Yok")
        self.lbl_det_ref.config(text=rec["ref"] or "—")
        self.lbl_det_bl.config(text=rec["bl"] or "—")
        self.lbl_det_bayi.config(text=rec["bayi"] or "—")
        self.lbl_det_liman.config(text=f"{rec['gumruk'] or '—'} / {rec['liman'] or '—'}")

        self.lbl_det_stage.config(text=rec["stage_title"])
        self.lbl_det_hat.config(text=rec["hat"] or "—")
        self.lbl_det_tescil.config(text=rec["tescil"] or "—")
        self.lbl_det_ordino.config(text=rec["ordino"] or "—")
        self.lbl_det_tareks.config(text=rec["tareks"] or "—")
        self.lbl_det_vergi_odeme.config(text=rec["vergi"] or "—")

        self.lbl_det_mail_status.config(text=rec["mail_status"])
        self.lbl_det_mail_time.config(text=rec["mail_date"] or "—")
        self.lbl_det_mail_to.config(text=rec["mail_to"] or "—")
        self.lbl_det_mail_atts.config(text=", ".join(rec["mail_attachments"]) if rec["mail_attachments"] else "—")
        self.lbl_det_aciklama.config(text=rec["aciklama"] or "Yok")

    def open_excel_file(self):
        if os.path.exists(self.excel_path):
            os.startfile(self.excel_path)
        else:
            messagebox.showerror("Hata", f"Excel dosyası bulunamadı:\n{self.excel_path}")


def main():
    root = tk.Tk()
    app = HankookOperationCockpitApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
