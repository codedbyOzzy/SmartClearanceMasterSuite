"""
==============================================================================
🛡️ DOĞRUER - OPERASYON & MAİL GÜVENLİK KALKANI v2.0 (Modern & Ultra Net Görünüm)
Firma: Doğruer Gümrük Müşavirliği A.Ş. & Hankook Lastikleri A.Ş.
Geliştirici: Antigravity AI
Yenilikler:
1. 🎨 Kristal Netliğinde Modern Arayüz (Kartlı ve Renkli Durum Rozetleri)
2. 🧩 Çoklu Referans Parçalama (Örn: 4200788458 + 4200788463 yapıştırıldığında tek tek ayırıp inceler)
3. 📎 Asıl PDF Maili vs Yanıt (RE:) Ayrımı (Yanıt maillerini "Boş Ek" diye yanıltmaz, asıl PDF tarihini gösterir)
4. 🚦 Renkli Tablo Satırları (Yeşil: PDF Gönderildi, Sarı: Yanıt/Metin, Kırmızı: Atılmadı)
5. 🛡️ Görsel Güvenlik Rapor Kartları (Kritik Uyarılar Kırmızı, Temiz Durumlar Yeşil)
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

# Outlook COM & Excel
try:
    import win32com.client
    import pythoncom
except ImportError:
    win32com = None

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
except ImportError:
    openpyxl = None


def get_outlook_sent_items(limit=350):
    """Outlook Gönderilmiş Öğeler klasöründen son mailleri çeker"""
    sent_records = []
    try:
        pythoncom.CoInitialize()
        outlook = win32com.client.Dispatch("Outlook.Application")
        namespace = outlook.GetNamespace("MAPI")
        sent_folder = namespace.GetDefaultFolder(5) # 5 = olFolderSentMail
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

                sent_records.append({
                    "subject": subj,
                    "to": to_addr,
                    "sent_on": sent_str,
                    "attachments": attachments,
                    "has_real_att": len(attachments) > 0,
                    "is_reply": subj.strip().upper().startswith("RE:") or subj.strip().upper().startswith("FW:")
                })
                count += 1
            except Exception:
                continue

    except Exception as e:
        print(f"Outlook Sent Items Hatası: {e}")
    finally:
        pythoncom.CoUninitialize()

    return sent_records


def extract_references_from_text(text):
    """Metin içindeki tüm 10 haneli referansları, dosya numaralarını ve konşimentoları ayıklar"""
    patterns = [
        r"\b(26-\d{6})\b",                        # Dosya No (26-080030)
        r"\b(4200\d{6})\b",                       # Hankook Ref (4200788458)
        r"\b([A-Z]{4}\d{7})\b",                   # Konşimento (HAMU2071693)
        r"\b(\d{8}[A-Z]{2}\d{8})\b"              # Tescil No
    ]
    found = []
    for pat in patterns:
        matches = re.findall(pat, text.upper())
        for m in matches:
            if m not in found:
                found.append(m)
    return found


class ModernMailSafetyShieldApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🛡️ Doğruer - Operasyon & Mail Güvenlik Kalkanı v2.0")
        self.root.geometry("920x760")
        self.root.minsize(860, 680)

        self.sent_cache = []
        self.last_cache_time = None
        self.selected_inspector_files = []

        self.setup_styles()
        self.setup_ui()
        self.refresh_sent_cache_async()

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")

        # Tab stilleri
        self.style.configure("TNotebook", background="#f8fafc")
        self.style.configure("TNotebook.Tab", font=("Segoe UI", 10, "bold"), padding=[16, 8], background="#e2e8f0")
        self.style.map("TNotebook.Tab", background=[("selected", "#1e3a8a")], foreground=[("selected", "#ffffff")])

        # Treeview stilleri
        self.style.configure(
            "Treeview",
            font=("Segoe UI", 9),
            rowheight=28,
            background="#ffffff",
            fieldbackground="#ffffff"
        )
        self.style.configure(
            "Treeview.Heading",
            font=("Segoe UI", 9, "bold"),
            background="#1e293b",
            foreground="#ffffff",
            relief="flat"
        )
        self.style.map("Treeview.Heading", background=[("active", "#334155")])

    def setup_ui(self):
        # 1. Header (Koyu Lacivert / Kurumsal)
        header_frame = tk.Frame(self.root, bg="#0f172a", height=70)
        header_frame.pack(fill=tk.X)

        title_box = tk.Frame(header_frame, bg="#0f172a")
        title_box.pack(side=tk.LEFT, padx=18, pady=12)

        lbl_title = tk.Label(
            title_box,
            text="🛡️ DOĞRUER - OPERASYON & MAİL GÜVENLİK KALKANI",
            font=("Segoe UI", 13, "bold"),
            fg="#ffffff",
            bg="#0f172a"
        )
        lbl_title.pack(anchor="w")

        self.lbl_outlook_status = tk.Label(
            title_box,
            text="🔄 Outlook mailleri taranıyor...",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#0f172a"
        )
        self.lbl_outlook_status.pack(anchor="w", pady=(2, 0))

        btn_refresh = tk.Button(
            header_frame,
            text="🔄 Mailleri Yenile",
            font=("Segoe UI", 9, "bold"),
            bg="#2563eb",
            fg="#ffffff",
            activebackground="#1d4ed8",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=12,
            pady=6,
            cursor="hand2",
            command=self.refresh_sent_cache_async
        )
        btn_refresh.pack(side=tk.RIGHT, padx=18, pady=16)

        # 2. Notebook (Sekmeler)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=14, pady=10)

        # 1. SEKME: "Buna Mail Attım mı?" Hızlı Sorgu
        self.tab_search = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_search, text="  🔍 'Buna Mail Attım mı?' Sorgula  ")
        self.setup_search_tab()

        # 2. SEKME: Gönderim Öncesi Güvenlik Denetçisi
        self.tab_inspector = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_inspector, text="  🛡️ Göndermeden Önce Denetle  ")
        self.setup_inspector_tab()

        # 3. SEKME: Toplu İş & Mail Takip Matrisi
        self.tab_matrix = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_matrix, text="  📊 Toplu İş & Mail Takip Matrisi  ")
        self.setup_matrix_tab()

        # 3. Status Bar
        self.status_bar = tk.Label(
            self.root,
            text="🟢 Sistem Hazır | Bir referans veya konşimento aratarak anında geçmişini görebilirsiniz.",
            bd=1,
            relief=tk.SUNKEN,
            anchor=tk.W,
            font=("Segoe UI", 9),
            bg="#f1f5f9",
            fg="#334155",
            padx=10,
            pady=4
        )
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    def refresh_sent_cache_async(self):
        self.lbl_outlook_status.config(text="🔄 Outlook Gönderilmiş Öğeler taranıyor...", fg="#fbbf24")
        threading.Thread(target=self._cache_worker, daemon=True).start()

    def _cache_worker(self):
        records = get_outlook_sent_items(limit=350)
        self.sent_cache = records
        self.last_cache_time = datetime.now()
        msg = f"🟢 Outlook Bağlantısı Aktif ({len(records)} Gönderilmiş Mail Hafızada) - {self.last_cache_time.strftime('%H:%M:%S')}"
        self.root.after(0, lambda: self.lbl_outlook_status.config(text=msg, fg="#4ade80"))
        self.root.after(0, lambda: self.status_bar.config(text="✅ Outlook gönderim geçmişi güncellendi.", fg="#16a34a"))

    # =========================================================================
    # 1. SEKME: HIZLI MAİL SORGULAYICI (MODERNLEŞTİRİLDİ)
    # =========================================================================
    def setup_search_tab(self):
        frame = tk.Frame(self.tab_search, bg="#f8fafc", padx=16, pady=16)
        frame.pack(fill=tk.BOTH, expand=True)

        # Üst Arama Kutusu
        search_card = tk.Frame(frame, bg="#ffffff", padx=15, pady=12, relief=tk.SOLID, bd=1)
        search_card.pack(fill=tk.X, pady=(0, 12))

        lbl = tk.Label(
            search_card,
            text="🔎 Sorgulamak İstediğiniz Referans / Dosya / Konşimento No (Birden fazla da yapıştırabilirsiniz):",
            font=("Segoe UI", 10, "bold"),
            bg="#ffffff",
            fg="#0f172a"
        )
        lbl.pack(anchor="w", pady=(0, 6))

        input_row = tk.Frame(search_card, bg="#ffffff")
        input_row.pack(fill=tk.X)

        self.txt_query = tk.Entry(input_row, font=("Consolas", 12), bd=1, relief=tk.SOLID)
        self.txt_query.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10), ipady=4)
        self.txt_query.bind("<Return>", lambda e: self.do_quick_search())
        self.txt_query.insert(0, "4200788458 + 4200788463 + 4200789554")

        btn_search = tk.Button(
            input_row,
            text="🔍 Geçmişi Tara & Göster",
            font=("Segoe UI", 10, "bold"),
            bg="#1e3a8a",
            fg="#ffffff",
            activebackground="#1e40af",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=18,
            pady=4,
            cursor="hand2",
            command=self.do_quick_search
        )
        btn_search.pack(side=tk.RIGHT)

        # Sonuç Kartı (Renkli ve Dinamik)
        self.result_container = tk.Frame(frame, bg="#ffffff", padx=15, pady=12, relief=tk.SOLID, bd=1)
        self.result_container.pack(fill=tk.X, pady=(0, 12))

        self.lbl_res_banner = tk.Label(
            self.result_container,
            text="💡 Lütfen yukarıdaki alana sorgulamak istediğiniz numaraları girip [Geçmişi Tara] butonuna basın.",
            font=("Segoe UI", 11, "bold"),
            fg="#475569",
            bg="#ffffff",
            anchor="w"
        )
        self.lbl_res_banner.pack(fill=tk.X, pady=(0, 4))

        self.lbl_res_details = tk.Label(
            self.result_container,
            text="",
            font=("Segoe UI", 9),
            fg="#334155",
            bg="#ffffff",
            justify=tk.LEFT,
            anchor="w"
        )
        self.lbl_res_details.pack(fill=tk.X)

        # Tablo Başlığı
        lbl_tbl = tk.Label(
            frame,
            text="📬 Outlook'ta Tespit Edilen İlgili Gönderilmiş Mailler:",
            font=("Segoe UI", 10, "bold"),
            bg="#f8fafc",
            fg="#0f172a"
        )
        lbl_tbl.pack(anchor="w", pady=(0, 6))

        # Eşleşen Mailler Tablosu
        columns = ("durum", "tarih", "kime", "ek_sayisi", "ek_listesi", "konu")
        self.tree_search = ttk.Treeview(frame, columns=columns, show="headings", height=8)

        self.tree_search.heading("durum", text="Durum Rozeti")
        self.tree_search.heading("tarih", text="Tarih / Saat")
        self.tree_search.heading("kime", text="Alıcı (Kime)")
        self.tree_search.heading("ek_sayisi", text="Ek Adedi")
        self.tree_search.heading("ek_listesi", text="Gönderilen PDF Ekleri")
        self.tree_search.heading("konu", text="Mail Konusu")

        self.tree_search.column("durum", width=130, anchor="center")
        self.tree_search.column("tarih", width=115, anchor="center")
        self.tree_search.column("kime", width=160, anchor="w")
        self.tree_search.column("ek_sayisi", width=75, anchor="center")
        self.tree_search.column("ek_listesi", width=220, anchor="w")
        self.tree_search.column("konu", width=200, anchor="w")

        # Tag Renklendirme
        self.tree_search.tag_configure("has_pdf", background="#dcfce7", foreground="#166534")      # Yeşil
        self.tree_search.tag_configure("is_reply", background="#fef9c3", foreground="#854d0e")     # Sarı (RE: Maili)
        self.tree_search.tag_configure("no_att", background="#fee2e2", foreground="#991b1b")       # Kırmızı (Boş Ek)

        sc_y = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.tree_search.yview)
        self.tree_search.configure(yscroll=sc_y.set)
        sc_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_search.pack(fill=tk.BOTH, expand=True)

    def do_quick_search(self):
        raw_query = self.txt_query.get().strip()
        if not raw_query:
            return

        for item in self.tree_search.get_children():
            self.tree_search.delete(item)

        refs = extract_references_from_text(raw_query)
        if not refs:
            # Düz metin araması yap
            refs = [raw_query.upper()]

        all_matches = []
        ref_status_summary = {}

        for ref in refs:
            clean_ref = re.sub(r"[^A-Z0-9]", "", ref)
            ref_status_summary[ref] = {"found": False, "has_pdf": False, "last_date": "", "pdf_names": []}

            for mail in self.sent_cache:
                subj_clean = re.sub(r"[^A-Z0-9]", "", mail["subject"].upper())
                att_clean = re.sub(r"[^A-Z0-9]", "", " ".join(mail["attachments"]).upper())

                if (clean_ref in subj_clean) or (clean_ref in att_clean):
                    if mail not in all_matches:
                        all_matches.append(mail)

                    if not ref_status_summary[ref]["found"]:
                        ref_status_summary[ref]["found"] = True
                        ref_status_summary[ref]["last_date"] = mail["sent_on"]

                    matching_atts = [a for a in mail["attachments"] if clean_ref in re.sub(r"[^A-Z0-9]", "", a.upper())]
                    if matching_atts:
                        ref_status_summary[ref]["has_pdf"] = True
                        for ma in matching_atts:
                            if ma not in ref_status_summary[ref]["pdf_names"]:
                                ref_status_summary[ref]["pdf_names"].append(ma)

        if all_matches:
            # Banner Güncelle
            found_count = sum(1 for r in ref_status_summary.values() if r["found"])
            pdf_count = sum(1 for r in ref_status_summary.values() if r["has_pdf"])

            self.lbl_res_banner.config(
                text=f"✅ BU REFERANSLAR İÇİN MAİL GÖNDERİLMİŞ! ({len(refs)} Referanstan {found_count} Tanesi Bulundu)",
                fg="#15803d"
            )

            detail_lines = []
            for r_name, r_info in ref_status_summary.items():
                if r_info["has_pdf"]:
                    detail_lines.append(f"  • {r_name}: ✅ PDF ile Gönderildi ({', '.join(r_info['pdf_names'])}) - Son İşlem: {r_info['last_date']}")
                elif r_info["found"]:
                    detail_lines.append(f"  • {r_name}: ✉️ Mail Atıldı (Yanıt/Metin) - Tarih: {r_info['last_date']}")
                else:
                    detail_lines.append(f"  • {r_name}: ⏳ Henüz Gönderilmemiş")

            self.lbl_res_details.config(text="\n".join(detail_lines))

            # Tabloya Ekle
            for m in all_matches:
                att_cnt = len(m["attachments"])
                att_str = ", ".join(m["attachments"]) if att_cnt > 0 else "—"

                if att_cnt > 0:
                    badge = "🟢 PDF Gönderildi"
                    tag = "has_pdf"
                elif m["is_reply"]:
                    badge = "🟡 Yanıt Maili (RE:)"
                    tag = "is_reply"
                else:
                    badge = "⚠️ Ek Yok (Metin)"
                    tag = "no_att"

                self.tree_search.insert("", tk.END, values=(
                    badge,
                    m["sent_on"],
                    m["to"],
                    f"{att_cnt} Adet" if att_cnt > 0 else "0",
                    att_str,
                    m["subject"]
                ), tags=(tag,))

        else:
            self.lbl_res_banner.config(
                text="⏳ BU REFERANSLAR İÇİN GÖNDERİLMİŞ BİR MAİL BULUNAMADI.",
                fg="#b91c1c"
            )
            self.lbl_res_details.config(
                text=f"Sorgulanan numaralar ({', '.join(refs)}) son 350 gönderilen mail içerisinde bulunamadı.\nGüvenle mail atabilirsiniz."
            )

    # =========================================================================
    # 2. SEKME: GÖNDERİM ÖNCESİ GÜVENLİK DENETÇİSİ (MODERNLEŞTİRİLDİ)
    # =========================================================================
    def setup_inspector_tab(self):
        frame = tk.Frame(self.tab_inspector, bg="#f8fafc", padx=16, pady=16)
        frame.pack(fill=tk.BOTH, expand=True)

        guide_box = tk.Label(
            frame,
            text="🛡️ Göndereceğiniz maili Outlook'tan [Gönder]'e basmadan önce buraya yapıştırıp denetletin.\nSistem boş ek, mükerrer mail ve yanlış dosya ekleme risklerini anında yakalar.",
            font=("Segoe UI", 9, "bold"),
            bg="#eff6ff",
            fg="#1d4ed8",
            padx=12,
            pady=8,
            relief=tk.SOLID,
            bd=1,
            justify=tk.LEFT,
            anchor="w"
        )
        guide_box.pack(fill=tk.X, pady=(0, 12))

        # 1. Adım Kartı
        step1_card = tk.Frame(frame, bg="#ffffff", padx=14, pady=10, relief=tk.SOLID, bd=1)
        step1_card.pack(fill=tk.X, pady=(0, 10))

        lbl_s1 = tk.Label(step1_card, text="1. Hazırladığınız Mail Konusu veya Gövdesi:", font=("Segoe UI", 10, "bold"), bg="#ffffff", fg="#0f172a")
        lbl_s1.pack(anchor="w", pady=(0, 4))

        self.txt_inspect_subj = tk.Entry(step1_card, font=("Segoe UI", 10), bd=1, relief=tk.SOLID)
        self.txt_inspect_subj.pack(fill=tk.X, ipady=3)
        self.txt_inspect_subj.insert(0, "Vergi Talebi / 4200788458 + 4200788463 + 4200789554")

        # 2. Adım Kartı
        step2_card = tk.Frame(frame, bg="#ffffff", padx=14, pady=10, relief=tk.SOLID, bd=1)
        step2_card.pack(fill=tk.X, pady=(0, 12))

        lbl_s2 = tk.Label(step2_card, text="2. Mailin Ekine Ekleyeceğiniz PDF Dosyaları:", font=("Segoe UI", 10, "bold"), bg="#ffffff", fg="#0f172a")
        lbl_s2.pack(anchor="w", pady=(0, 4))

        file_row = tk.Frame(step2_card, bg="#ffffff")
        file_row.pack(fill=tk.X)

        self.lbl_selected_files_count = tk.Label(
            file_row,
            text="Henüz PDF seçilmedi (0 Dosya)",
            font=("Segoe UI", 9, "bold"),
            fg="#64748b",
            bg="#ffffff"
        )
        self.lbl_selected_files_count.pack(side=tk.LEFT)

        btn_select = tk.Button(
            file_row,
            text="📁 PDF Dosyalarını Seç...",
            font=("Segoe UI", 9, "bold"),
            bg="#f1f5f9",
            fg="#1e293b",
            relief=tk.SOLID,
            bd=1,
            padx=12,
            pady=4,
            cursor="hand2",
            command=self.select_inspector_files
        )
        btn_select.pack(side=tk.RIGHT)

        # Denetle Butonu
        btn_run_inspect = tk.Button(
            frame,
            text="🛡️ GÜVENLİK DENETİMİNİ BAŞLAT (KONTROL ET)",
            font=("Segoe UI", 11, "bold"),
            bg="#4f46e5",
            fg="#ffffff",
            activebackground="#4338ca",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            pady=10,
            cursor="hand2",
            command=self.run_security_inspection
        )
        btn_run_inspect.pack(fill=tk.X, pady=(0, 12))

        # Denetim Rapor Alanı (Görsel Kartlar)
        self.report_container = tk.Frame(frame, bg="#ffffff", padx=14, pady=12, relief=tk.SOLID, bd=1)
        self.report_container.pack(fill=tk.BOTH, expand=True)

        lbl_rep_title = tk.Label(self.report_container, text="📋 Denetim Sonuç Özeti:", font=("Segoe UI", 10, "bold"), bg="#ffffff", fg="#0f172a")
        lbl_rep_title.pack(anchor="w", pady=(0, 6))

        self.txt_inspection_report = tk.Text(
            self.report_container,
            font=("Segoe UI", 10),
            bg="#f8fafc",
            bd=1,
            relief=tk.SOLID,
            padx=12,
            pady=10
        )
        self.txt_inspection_report.pack(fill=tk.BOTH, expand=True)

    def select_inspector_files(self):
        files = filedialog.askopenfilenames(
            title="Mail Ekine Koyulacak PDF Dosyalarını Seçin",
            filetypes=[("PDF Dosyaları", "*.pdf"), ("Tüm Dosyalar", "*.*")]
        )
        if files:
            self.selected_inspector_files = list(files)
            names = [os.path.basename(f) for f in files]
            self.lbl_selected_files_count.config(
                text=f"✅ {len(files)} Adet PDF Seçildi: {', '.join(names[:3])}{'...' if len(names) > 3 else ''}",
                fg="#15803d"
            )

    def run_security_inspection(self):
        subj = self.txt_inspect_subj.get().strip()
        att_names = [os.path.basename(f) for f in self.selected_inspector_files]

        self.txt_inspection_report.delete("1.0", tk.END)
        report_lines = []
        has_critical_error = False

        detected_refs = extract_references_from_text(subj)
        report_lines.append(f"📌 Konuda Tespit Edilen Referanslar ({len(detected_refs)} Adet): {', '.join(detected_refs) if detected_refs else 'Yok'}")

        # 1. BOŞ EK KONTROLÜ
        is_talep_mail = any(k in subj.upper() for k in ["VERGİ", "VERGI", "FATURA", "TALEP", "TALEBİ", "DEKONT", "ORDİNO"])
        if is_talep_mail and len(att_names) == 0:
            report_lines.append("\n❌ [KRİTİK UYARI] BOŞ EK RİSKİ:")
            report_lines.append("   Konuda 'Vergi/Fatura Talebi' geçiyor ancak mailin ekine HİÇBİR PDF EKLENMEMİŞ!")
            has_critical_error = True
        else:
            report_lines.append(f"\n✅ [EK DURUMU] Toplam {len(att_names)} adet ek dosya seçildi.")

        # 2. MÜKERRERLİK KONTROLÜ
        duplicate_warnings = []
        for ref in detected_refs:
            for mail in self.sent_cache:
                clean_ref = re.sub(r"[^A-Z0-9]", "", ref)
                subj_clean = re.sub(r"[^A-Z0-9]", "", mail["subject"].upper())
                att_clean = re.sub(r"[^A-Z0-9]", "", " ".join(mail["attachments"]).upper())

                if (clean_ref in subj_clean) or (clean_ref in att_clean):
                    duplicate_warnings.append(f"   ⚠️ Referans [{ref}] için {mail['sent_on']} tarihinde [{mail['to']}] adresine zaten mail atılmış!")
                    break

        if duplicate_warnings:
            report_lines.append("\n⚠️ [MÜKERRER MAİL UYARISI]:")
            report_lines.extend(duplicate_warnings)
        else:
            report_lines.append("\n✅ [MÜKERRERLİK TEMİZ] Konudaki referanslar için mükerrer gönderim bulunamadı.")

        # 3. EKSİK PDF KONTROLÜ
        if detected_refs and att_names:
            missing_pdfs = []
            for ref in detected_refs:
                clean_ref = re.sub(r"[^A-Z0-9]", "", ref)
                matched = any(clean_ref in re.sub(r"[^A-Z0-9]", "", a.upper()) for a in att_names)
                if not matched:
                    missing_pdfs.append(ref)

            if missing_pdfs:
                report_lines.append("\n⚠️ [EKSİK PDF UYARISI]:")
                report_lines.append(f"   Konuda geçen şu referansların karşılığı olan PDF eklenmemiş: {', '.join(missing_pdfs)}")
            else:
                report_lines.append("\n✅ [TAM EŞLEŞME] Konudaki tüm referansların karşılığı olan PDF ekleri mevcut.")

        # SONUÇ
        report_lines.append("\n" + "=" * 60)
        if has_critical_error:
            report_lines.append("🛑 GENEL DEĞERLENDİRME: MAİLİ GÖNDERMEDEN ÖNCE EKLERİ MUTLAKA KONTROL EDİN!")
        elif duplicate_warnings or (detected_refs and len(att_names) < len(detected_refs)):
            report_lines.append("⚠️ GENEL DEĞERLENDİRME: DİKKAT EDİLMESİ GEREKEN UYARILAR VAR (Yukarıyı İnceleyin).")
        else:
            report_lines.append("🎉 GENEL DEĞERLENDİRME: %100 GÜVENLİ! Mail ve ekler kusursuz uyumlu.")

        self.txt_inspection_report.insert("1.0", "\n".join(report_lines))

    # =========================================================================
    # 3. SEKME: TOPLU İŞ & MAİL TAKİP MATRİSİ (MODERNLEŞTİRİLDİ)
    # =========================================================================
    def setup_matrix_tab(self):
        frame = tk.Frame(self.tab_matrix, bg="#f8fafc", padx=16, pady=16)
        frame.pack(fill=tk.BOTH, expand=True)

        input_card = tk.Frame(frame, bg="#ffffff", padx=14, pady=10, relief=tk.SOLID, bd=1)
        input_card.pack(fill=tk.X, pady=(0, 10))

        lbl = tk.Label(
            input_card,
            text="📋 Takip Edilecek Referans / Dosya / Konşimento Listesini Yapıştırın:",
            font=("Segoe UI", 10, "bold"),
            bg="#ffffff",
            fg="#0f172a"
        )
        lbl.pack(anchor="w", pady=(0, 4))

        self.txt_matrix_input = tk.Text(input_card, height=4, font=("Consolas", 10), bd=1, relief=tk.SOLID)
        self.txt_matrix_input.pack(fill=tk.X, pady=(0, 6))
        self.txt_matrix_input.insert("1.0", "4200788458\n4200788463\n4200786947\n4200800551\nHAMU2071693")

        btn_row = tk.Frame(input_card, bg="#ffffff")
        btn_row.pack(fill=tk.X)

        btn_scan_matrix = tk.Button(
            btn_row,
            text="🚀 Canlı Durumları Tara",
            font=("Segoe UI", 10, "bold"),
            bg="#16a34a",
            fg="#ffffff",
            activebackground="#15803d",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=14,
            pady=5,
            cursor="hand2",
            command=self.run_matrix_scan
        )
        btn_scan_matrix.pack(side=tk.LEFT)

        btn_export = tk.Button(
            btn_row,
            text="📊 Excel Raporu Al",
            font=("Segoe UI", 10, "bold"),
            bg="#0284c7",
            fg="#ffffff",
            activebackground="#0369a1",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=14,
            pady=5,
            cursor="hand2",
            command=self.export_matrix_to_excel
        )
        btn_export.pack(side=tk.RIGHT)

        # Tablo
        columns = ("ref", "durum", "tarih", "kime", "pdf_durumu", "konu")
        self.tree_matrix = ttk.Treeview(frame, columns=columns, show="headings", height=11)

        self.tree_matrix.heading("ref", text="Referans / Dosya")
        self.tree_matrix.heading("durum", text="Mail Durumu")
        self.tree_matrix.heading("tarih", text="Son Gönderim")
        self.tree_matrix.heading("kime", text="Alıcı")
        self.tree_matrix.heading("pdf_durumu", text="PDF Ek Durumu")
        self.tree_matrix.heading("konu", text="Mail Konusu")

        self.tree_matrix.column("ref", width=120, anchor="center")
        self.tree_matrix.column("durum", width=130, anchor="center")
        self.tree_matrix.column("tarih", width=110, anchor="center")
        self.tree_matrix.column("kime", width=150, anchor="w")
        self.tree_matrix.column("pdf_durumu", width=160, anchor="w")
        self.tree_matrix.column("konu", width=180, anchor="w")

        self.tree_matrix.tag_configure("sent_ok", background="#dcfce7", foreground="#166534")      # Yeşil
        self.tree_matrix.tag_configure("sent_reply", background="#fef9c3", foreground="#854d0e")   # Sarı
        self.tree_matrix.tag_configure("not_sent", background="#fee2e2", foreground="#991b1b")     # Kırmızı

        sc_y = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.tree_matrix.yview)
        self.tree_matrix.configure(yscroll=sc_y.set)
        sc_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_matrix.pack(fill=tk.BOTH, expand=True)

        self.matrix_results_data = []

    def run_matrix_scan(self):
        raw = self.txt_matrix_input.get("1.0", tk.END).strip()
        lines = [l.strip() for l in raw.split("\n") if len(l.strip()) > 0]
        if not lines:
            messagebox.showwarning("Uyarı", "Lütfen taranacak referans listesini girin.")
            return

        for item in self.tree_matrix.get_children():
            self.tree_matrix.delete(item)

        self.matrix_results_data = []

        for ref in lines:
            clean_ref = re.sub(r"[^A-Z0-9]", "", ref.upper())
            found_mail = None
            found_pdf_mail = None

            for mail in self.sent_cache:
                subj_clean = re.sub(r"[^A-Z0-9]", "", mail["subject"].upper())
                att_clean = re.sub(r"[^A-Z0-9]", "", " ".join(mail["attachments"]).upper())

                if (clean_ref in subj_clean) or (clean_ref in att_clean):
                    if not found_mail:
                        found_mail = mail
                    if mail["attachments"] and not found_pdf_mail:
                        found_pdf_mail = mail
                        break

            # Eğer yanıt maili varsa ama asıl PDF önceki mailde gittiyse onu öne çıkar
            target_mail = found_pdf_mail or found_mail

            if target_mail:
                if target_mail["attachments"]:
                    durum_str = "🟢 PDF Gönderildi"
                    tag = "sent_ok"
                    pdf_str = ", ".join(target_mail["attachments"])
                elif target_mail["is_reply"]:
                    durum_str = "🟡 Yanıt Maili (RE:)"
                    tag = "sent_reply"
                    pdf_str = "— (Metin Yanıtı)"
                else:
                    durum_str = "⚠️ Ek Yok (Metin)"
                    tag = "sent_reply"
                    pdf_str = "—"

                res = {
                    "ref": ref,
                    "durum": durum_str,
                    "tarih": target_mail["sent_on"],
                    "kime": target_mail["to"],
                    "pdf_durumu": pdf_str,
                    "konu": target_mail["subject"],
                    "tag": tag
                }
            else:
                res = {
                    "ref": ref,
                    "durum": "🔴 Henüz Atılmadı",
                    "tarih": "—",
                    "kime": "—",
                    "pdf_durumu": "—",
                    "konu": "—",
                    "tag": "not_sent"
                }

            self.matrix_results_data.append(res)
            self.tree_matrix.insert("", tk.END, values=(
                res["ref"],
                res["durum"],
                res["tarih"],
                res["kime"],
                res["pdf_durumu"],
                res["konu"]
            ), tags=(res["tag"],))

        self.status_bar.config(text=f"✅ {len(lines)} referansın canlı durumu tarandı.", fg="#16a34a")

    def export_matrix_to_excel(self):
        if not openpyxl or not self.matrix_results_data:
            messagebox.showinfo("Bilgi", "Dışa aktarılacak sonuç bulunamadı.")
            return

        try:
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            out_path = os.path.join(desktop, f"Hankook_Mail_Takip_Matrisi_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx")

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Mail Takip Matrisi"

            headers = ["Sıra", "Referans / Dosya No", "Mail Durumu", "Son Gönderim Tarihi", "Alıcı (Kime)", "PDF Ek Durumu", "Mail Konusu"]
            ws.append(headers)

            header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
            header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")

            for col_idx in range(1, len(headers) + 1):
                cell = ws.cell(row=1, column=col_idx)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center")

            for idx, r in enumerate(self.matrix_results_data, 1):
                ws.append([
                    idx,
                    r["ref"],
                    r["durum"],
                    r["tarih"],
                    r["kime"],
                    r["pdf_durumu"],
                    r["konu"]
                ])

            wb.save(out_path)
            os.startfile(out_path)
        except Exception as e:
            messagebox.showerror("Hata", f"Excel kayıt hatası: {e}")


def main():
    root = tk.Tk()
    app = ModernMailSafetyShieldApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
