"""
apex_morning_briefing.py — SmartClearance Apex Sabah Operasyon & Günlük Eylem Brifingi Motoru
"""

import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QGridLayout, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor
from .apex_theme import (
    BG_BASE, BG_CARD, BG_INPUT, BORDER_SUBTLE, TEXT_WHITE, TEXT_PRIMARY,
    TEXT_MUTED, COLOR_CYAN, COLOR_GREEN, COLOR_RED, COLOR_ORANGE,
    COLOR_PURPLE, COLOR_YELLOW, COLOR_SLATE
)
from .apex_data_engine import Durum


class ApexMorningBriefingWidget(QWidget):
    """Sabah işe gelindiğinde yapılması gereken işleri ve ETA yakınlık sırasını gösteren kokpit."""
    shipmentSelected   = pyqtSignal(dict)
    filterRequested    = pyqtSignal(str)
    popoutRequested    = pyqtSignal()
    gotoTableRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.all_shipments = []
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(10)

        # Üst Brifing Başlık Barı
        top_bar = QFrame()
        top_bar.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER_SUBTLE};
                border-radius: 8px;
                padding: 6px 14px;
            }}
        """)
        tb_lay = QHBoxLayout(top_bar)
        tb_lay.setContentsMargins(8, 4, 8, 4)
        tb_lay.setSpacing(10)

        self.lbl_date_title = QLabel("🌅 GÜNLÜK SABAH OPERASYON BRİFİNGİ")
        self.lbl_date_title.setStyleSheet(f"font-size: 13.5px; font-weight: 800; color: {TEXT_WHITE}; letter-spacing: 0.5px;")
        tb_lay.addWidget(self.lbl_date_title)
        tb_lay.addStretch(1)

        self.lbl_summary_stat = QLabel("0 Dosya İncelendi")
        self.lbl_summary_stat.setStyleSheet("color: #38bdf8; font-size: 11.5px; font-weight: 700; margin-right: 8px;")
        tb_lay.addWidget(self.lbl_summary_stat)

        self.btn_goto_table = QPushButton("📋 Dosya Masasına Geç ➔")
        self.btn_goto_table.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_goto_table.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                color: #ffffff;
                border: 1px solid #38bdf8;
                border-radius: 6px;
                padding: 5px 12px;
                font-weight: 700;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #0369a1;
            }
        """)
        self.btn_goto_table.clicked.connect(self.gotoTableRequested.emit)
        tb_lay.addWidget(self.btn_goto_table)

        self.btn_popout = QPushButton("↗ Ayrı Pencere")
        self.btn_popout.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_popout.setToolTip("Sabah brifingini çift monitör veya yan ekran için bağımsız pencere olarak aç")
        self.btn_popout.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #94a3b8;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                padding: 5px 10px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #f8fafc;
            }
        """)
        self.btn_popout.clicked.connect(self.popoutRequested.emit)
        tb_lay.addWidget(self.btn_popout)

        root.addWidget(top_bar)

        # Kaydırılabilir Brifing Alanı
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background-color: transparent; border: none;")

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 4, 0)
        self.content_layout.setSpacing(10)
        scroll.setWidget(self.content_widget)

        root.addWidget(scroll, 1)

    def update_data(self, shipments):
        self.all_shipments = shipments

        # Önceki içeriği temizle
        while self.content_layout.count() > 0:
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        today = datetime.date.today()
        is_monday = today.weekday() == 0

        # Hafta sonu günlerini hesapla
        if is_monday:
            sat_d = today - datetime.timedelta(days=2)
            sun_d = today - datetime.timedelta(days=1)
        elif today.weekday() == 5:
            sat_d = today
            sun_d = today + datetime.timedelta(days=1)
        elif today.weekday() == 6:
            sat_d = today - datetime.timedelta(days=1)
            sun_d = today
        else:
            sat_d = today - datetime.timedelta(days=today.weekday() + 2)
            sun_d = today - datetime.timedelta(days=today.weekday() + 1)

        sat_str = sat_d.strftime("%d.%m")
        sun_str = sun_d.strftime("%d.%m")

        today_str = today.strftime("%d %B %Y").replace("January", "Ocak").replace("February", "Şubat").replace("March", "Mart").replace("April", "Nisan").replace("May", "Mayıs").replace("June", "Haziran").replace("July", "Temmuz").replace("August", "Ağustos").replace("September", "Eylül").replace("October", "Ekim").replace("November", "Kasım").replace("December", "Aralık")
        
        if is_monday:
            self.lbl_date_title.setText(f"🌅 YENİ HAFTA OPERASYON BRİFİNGİ — {today_str}, Pazartesi")
        else:
            day_tr = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"][today.weekday()]
            self.lbl_date_title.setText(f"🌅 GÜNLÜK OPERASYON BRİFİNGİ — {today_str}, {day_tr}")

        # Hafta sonu ve bugün filtreleri
        weekend_arrivals = [x for x in shipments if x.get("hafta_sonu_geldi", False)]
        today_arrivals   = [x for x in shipments if x.get("bugun_geldi", False)]
        weekend_unopened = [x for x in weekend_arrivals if x.get("hafta_sonu_dosyasiz", False)]

        # Gruplamalar
        demuraj_list = [x for x in shipments if x["durum"] == Durum.DEMURAJ_RISKI]
        banka_list   = [x for x in shipments if x["durum"] == Durum.BANKA_ID_BEKLER]
        tareks_list  = [x for x in shipments if x["durum"] == Durum.TAREKS_DENETIM]
        ordino_list  = [x for x in shipments if x["durum"] == Durum.ORDINO_BEKLER]

        # ETA'lar: Hafta sonu/bugün yeni yanaşanlar + gelecekteki varışlar
        recent_berthed = [x for x in shipments if x.get("hafta_sonu_geldi") or x.get("bugun_geldi")]
        future_etas = [x for x in shipments if x.get("eta_t", "—") != "—" and x.get("gun_kalan", -1) > 0 and x not in recent_berthed]
        future_etas.sort(key=lambda x: x.get("gun_kalan", 9999))
        upcoming_etas = recent_berthed + future_etas

        # Dosyası açılmamış olanlar
        no_file_list = [x for x in shipments if x["dosya_no"] == "—"]
        # Acilen açılması gerekenler (Gemi atanmış veya ETA ≤ 14 gün)
        urgent_open = [x for x in no_file_list if (x["gemi"] != "—" or (x["eta_t"] != "—" and 0 <= x.get("gun_kalan", 999) <= 14))]

        total_urgent = len(demuraj_list) + len(banka_list) + len(urgent_open)
        wk_summary = f" • 📅 {len(weekend_arrivals)} Hafta Sonu Girişi" if weekend_arrivals else ""
        self.lbl_summary_stat.setText(f"Toplam {len(shipments)} Sevkiyat{wk_summary} • 🚨 {total_urgent} Acil Eylem")

        # ── 1. HAFTA SONU OPERASYON & GEMİ GİRİŞ RADARI KARTI (TAM GENİŞLİK) ───
        weekend_card = self._build_weekend_intake_card(weekend_arrivals, today_arrivals, weekend_unopened, is_monday, sat_str, sun_str)
        self.content_layout.addWidget(weekend_card)

        # ── 2. İKİ KOLONLU FERAH DÜZEN ────────────────────────────────────────
        cols_container = QWidget()
        cols_layout = QHBoxLayout(cols_container)
        cols_layout.setContentsMargins(0, 0, 0, 0)
        cols_layout.setSpacing(14)

        # SOL KOLON: Yol Haritası ve Acil Eylemler
        col_left = QWidget()
        col_left_lay = QVBoxLayout(col_left)
        col_left_lay.setContentsMargins(0, 0, 0, 0)
        col_left_lay.setSpacing(12)
        col_left_lay.addWidget(self._build_narrative_box(demuraj_list, banka_list, urgent_open, upcoming_etas, weekend_arrivals, today_arrivals, weekend_unopened, is_monday, sat_str, sun_str))
        if demuraj_list or banka_list or tareks_list:
            col_left_lay.addWidget(self._build_critical_actions_card(demuraj_list, banka_list, tareks_list))
        col_left_lay.addStretch(1)

        # SAĞ KOLON: Dosya Açılma Matrisi ve Kronolojik ETA Radarı
        col_right = QWidget()
        col_right_lay = QVBoxLayout(col_right)
        col_right_lay.setContentsMargins(0, 0, 0, 0)
        col_right_lay.setSpacing(12)
        col_right_lay.addWidget(self._build_file_status_card(no_file_list, urgent_open, len(shipments)))
        col_right_lay.addWidget(self._build_eta_chronological_card(upcoming_etas, recent_berthed))
        col_right_lay.addStretch(1)

        cols_layout.addWidget(col_left, 1)
        cols_layout.addWidget(col_right, 1)

        self.content_layout.addWidget(cols_container)

    def _build_weekend_intake_card(self, weekend_arrivals, today_arrivals, weekend_unopened, is_monday, sat_str, sun_str):
        card = QFrame()
        has_weekend = len(weekend_arrivals) > 0
        has_unopened = len(weekend_unopened) > 0

        border_col = "rgba(244, 63, 94, 0.55)" if has_unopened else ("rgba(245, 158, 11, 0.5)" if has_weekend else "rgba(56, 189, 248, 0.25)")
        bg_col = "rgba(244, 63, 94, 0.06)" if has_unopened else ("rgba(245, 158, 11, 0.05)" if has_weekend else "rgba(15, 23, 42, 0.65)")

        card.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_col};
                border: 1.5px solid {border_col};
                border-radius: 8px;
                padding: 10px 14px;
            }}
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)

        # Üst Başlık Barı
        h_box = QHBoxLayout()
        h_box.setSpacing(8)

        badge_txt = "📅 PAZARTESİ HAFTA BAŞI RADARI" if is_monday else "📅 HAFTA SONU RADARI"
        badge_bg = "#f59e0b" if has_weekend else "#0284c7"
        lbl_badge = QLabel(badge_txt)
        lbl_badge.setStyleSheet(f"background: {badge_bg}; color: #ffffff; font-size: 9.5px; font-weight: 800; padding: 2px 8px; border-radius: 4px;")
        h_box.addWidget(lbl_badge)

        title_txt = f"HAFTA SONU OPERASYON & GEMİ GİRİŞ RADARI ({sat_str} — {sun_str})"
        lbl_title = QLabel(title_txt)
        lbl_title.setStyleSheet("font-size: 11.5px; font-weight: 800; color: #ffffff; letter-spacing: 0.5px;")
        h_box.addWidget(lbl_title)
        h_box.addStretch(1)

        if has_weekend:
            btn_show_weekend = QPushButton(f"📋 Hafta Sonu Gelenleri Gör ({len(weekend_arrivals)})")
            btn_show_weekend.setFixedHeight(24)
            btn_show_weekend.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn_show_weekend.setStyleSheet("background: #0284c7; color: white; font-size: 10.5px; font-weight: 700; border: 1px solid #38bdf8; border-radius: 4px; padding: 2px 8px;")
            btn_show_weekend.clicked.connect(lambda: self.filterRequested.emit("HAFTA_SONU"))
            h_box.addWidget(btn_show_weekend)

        if has_unopened:
            btn_show_unopened = QPushButton(f"🔴 Açılmamışları Filtrele ({len(weekend_unopened)})")
            btn_show_unopened.setFixedHeight(24)
            btn_show_unopened.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn_show_unopened.setStyleSheet("background: #e11d48; color: white; font-size: 10.5px; font-weight: 700; border: 1px solid #fda4af; border-radius: 4px; padding: 2px 8px;")
            btn_show_unopened.clicked.connect(lambda: self.filterRequested.emit("HAFTA_SONU_DOSYASIZ"))
            h_box.addWidget(btn_show_unopened)

        layout.addLayout(h_box)

        # Bilgilendirme / İkaz Metni
        all_recent = weekend_arrivals + [x for x in today_arrivals if x not in weekend_arrivals]
        if has_weekend:
            txt_parts = []
            txt_parts.append(f"⚠️ <b>Hafta Sonu Girişi:</b> Cumartesi ({sat_str}) ve Pazar ({sun_str}) günleri ofis kapalıyken limana <b>{len(weekend_arrivals)} adet sevkiyat</b> yanaştı. Serbest süre (demuraj/ardiye) sayacı hafta sonundan itibaren işlemeye başladığından bu dosyalara öncelik verilmelidir.")
            if has_unopened:
                txt_parts.append(f"🔴 <b>KRİTİK UYARI:</b> Hafta sonu gelen yüklerden <b>{len(weekend_unopened)} tanesinin</b> henüz Evrim'de dosya numarası açılmamıştır! Bu yüklerin limanda sahipsiz kalmaması için dosya açılışları acilen tamamlanmalıdır.")
            else:
                txt_parts.append("🟢 <b>Dosya Durumu İyi:</b> Hafta sonu gelen tüm yüklerin Evrim dosya numaraları açılmış durumdadır.")
            if today_arrivals:
                txt_parts.append(f"🚢 <b>Bugün Yanaşanlar:</b> Ayrıca bugün ({len(today_arrivals)} adet sevkiyat) limana yanaşmaktadır.")
            banner_msg = "<br>".join(txt_parts)
        else:
            if is_monday:
                banner_msg = f"✨ <b>Hafta Sonu Sakin Geçti:</b> Cumartesi ({sat_str}) ve Pazar ({sun_str}) günleri limana yeni yanaşan bir gemi bulunmuyor. Yeni haftaya planlı açık dosyalarınızla başlayabilirsiniz."
            else:
                banner_msg = f"ℹ️ En son hafta sonu ({sat_str} — {sun_str}) limana yanaşan yeni bir gemi bulunmuyor."
            if today_arrivals:
                banner_msg += f"<br>🚢 <b>Bugün Yanaşan Gemiler:</b> {len(today_arrivals)} adet sevkiyat bugün limana yanaşmaktadır ({', '.join(list(set(x['gemi'] for x in today_arrivals if x['gemi'] != '—'))[:2])})."

        lbl_banner = QLabel(banner_msg)
        lbl_banner.setStyleSheet("color: #e2e8f0; font-size: 11.5px; line-height: 1.5;")
        lbl_banner.setWordWrap(True)
        layout.addWidget(lbl_banner)

        # Gelen Gemilerin Mini Kart Listesi
        if all_recent:
            grid_f = QFrame()
            grid_f.setStyleSheet("background: transparent;")
            grid_lay = QVBoxLayout(grid_f)
            grid_lay.setContentsMargins(0, 4, 0, 0)
            grid_lay.setSpacing(4)

            for it in all_recent[:6]:
                row_f = QFrame()
                row_f.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                row_f.setStyleSheet("""
                    QFrame {
                        background-color: #0b111e;
                        border: 1px solid rgba(255, 255, 255, 0.08);
                        border-radius: 5px;
                        padding: 4px 8px;
                    }
                    QFrame:hover {
                        background-color: #131c31;
                        border-color: #f59e0b;
                    }
                """)
                rf = QHBoxLayout(row_f)
                rf.setContentsMargins(8, 3, 8, 3)
                rf.setSpacing(10)

                # Gün etiketi
                gun_txt = it.get("hafta_sonu_gunu") or ("Bugün" if it.get("bugun_geldi") else "Hafta Sonu")
                is_bg = "Bugün" in gun_txt
                tag_bg = "rgba(56, 189, 248, 0.2)" if is_bg else "rgba(245, 158, 11, 0.2)"
                tag_fg = "#38bdf8" if is_bg else "#facc15"
                lbl_gun = QLabel(f"📅 {gun_txt}")
                lbl_gun.setStyleSheet(f"background: {tag_bg}; color: {tag_fg}; font-size: 10px; font-weight: 800; padding: 2px 6px; border-radius: 3px;")
                rf.addWidget(lbl_gun)

                lbl_po = QLabel(f"PO: <b>{it['po']}</b>")
                lbl_po.setStyleSheet("color: #38bdf8; font-size: 11px;")
                rf.addWidget(lbl_po)

                lbl_v = QLabel(f"🚢 {it['gemi']} ({it['liman']})")
                lbl_v.setStyleSheet("color: #ffffff; font-size: 11px; font-weight: 600;")
                rf.addWidget(lbl_v)

                lbl_date = QLabel(f"Tarih: {it.get('varis_t') if it.get('varis_t') != '—' else it.get('eta_t')}")
                lbl_date.setStyleSheet("color: #94a3b8; font-size: 10.5px;")
                rf.addWidget(lbl_date)

                rf.addStretch(1)

                has_file = it["dosya_no"] != "—"
                if has_file:
                    f_badge = QLabel(f"🟢 Dosya: {it['dosya_no']}")
                    f_badge.setStyleSheet("color: #34d399; font-size: 10.5px; font-weight: 700;")
                else:
                    f_badge = QLabel("🔴 DOSYA AÇILMADI!")
                    f_badge.setStyleSheet("background: rgba(244, 63, 94, 0.2); color: #f43f5e; font-size: 10px; font-weight: 800; padding: 2px 6px; border-radius: 3px;")
                rf.addWidget(f_badge)

                row_f.mousePressEvent = lambda e, item=it: self.shipmentSelected.emit(item)
                grid_lay.addWidget(row_f)

            layout.addWidget(grid_f)

        return card

    def _build_narrative_box(self, demuraj, banka, urgent_open, etas, weekend, today_arrivals, weekend_unopened, is_monday, sat_str, sun_str):
        box = QFrame()
        box.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(56, 189, 248, 0.08);
                border: 1px solid rgba(56, 189, 248, 0.3);
                border-radius: 8px;
                padding: 10px 14px;
            }}
        """)
        layout = QVBoxLayout(box)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        lbl_h = QLabel("💡 GÜNÜN İLK İŞLERİ VE OPERATÖR YOL HARİTASI:")
        lbl_h.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 800; letter-spacing: 0.5px;")
        layout.addWidget(lbl_h)

        tips = []

        # 1. Hafta Başı & Hafta Sonu Değerlendirmesi
        if is_monday:
            if weekend:
                unopened_str = f" ve <b>{len(weekend_unopened)} tanesinin henüz dosyası açılmadı</b>" if weekend_unopened else ""
                tips.append(f"• 📅 <b>Pazartesi Hafta Başı Mesaisi:</b> Hafta sonu limana <b>{len(weekend)} adet sevkiyat</b> yanaştı{unopened_str}. Serbest süre (demuraj) kaybı yaşamamak için hafta sonu gelen yüklerin ordino ve tescil durumları sabahın ilk saatlerinde kontrol edilmelidir.")
            else:
                tips.append(f"• 📅 <b>Pazartesi Hafta Başı Mesaisi:</b> Hafta sonu ({sat_str} — {sun_str}) limana yeni yanaşan bir gemi olmadı. Hafta sonu sakin geçti; haftaya planlı açık dosyalarınızla başlayabilirsiniz.")
            if today_arrivals:
                v_names = ", ".join(list(set(x["gemi"] for x in today_arrivals if x["gemi"] != "—"))[:3])
                tips.append(f"• 🚢 <b>Bugün (Pazartesi) Yanaşan Gemiler:</b> <b>{len(today_arrivals)} adet sevkiyat</b> bugün limana varıyor ({v_names}).")
        elif weekend:
            tips.append(f"• 📅 <b>Son Hafta Sonu Girişleri:</b> Hafta sonu limana yanaşan <b>{len(weekend)} adet sevkiyat</b> bulunuyor.")

        # 2. Risk Grupları
        if demuraj:
            tips.append(f"• 🚨 <b>{len(demuraj)} adet dosyada</b> liman serbest süresi dolmuş veya aşılmak üzere. Demuraj maliyetini önlemek için bu dosyaların tescil/ordino işlemleri sabahın ilk saatlerinde ele alınmalıdır.")
        if banka:
            tips.append(f"• 🏦 <b>{len(banka)} adet dosyada</b> müşteri/finans departmanından banka referans numarası (ID) ve transfer teyidi beklenmektedir.")
        if urgent_open:
            tips.append(f"• ⚠️ <b>{len(urgent_open)} adet sevkiyatın</b> gemisi yolda olmasına rağmen henüz Evrim'de dosya numarası açılmamıştır. Dosyaları ivedilikle açılmalıdır.")
        if etas:
            first = etas[0]
            tips.append(f"• 🚢 En yakın varacak gemi: <b>{first['gemi']}</b> ({first['liman']} Limanı, ETA: <b>{first['eta_t']}</b> — {first['gun_kalan']} gün kaldı).")
        if not tips:
            tips.append("• ✨ <b>Harika!</b> Bugün acil eylem gerektiren riskli dosya veya açılmamış sevkiyat bulunmuyor. Tüm açık işler olağan seyrinde takip ediliyor.")

        narrative = "<br>".join(tips)
        lbl_text = QLabel(narrative)
        lbl_text.setStyleSheet(f"color: {TEXT_WHITE}; font-size: 11.5px; line-height: 1.5;")
        lbl_text.setWordWrap(True)
        layout.addWidget(lbl_text)

        return box

    def _build_file_status_card(self, no_file_list, urgent_open, total_count):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER_SUBTLE};
                border-radius: 8px;
                padding: 10px 14px;
            }}
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        # Başlık ve Hızlı Filtre Butonu
        h_box = QHBoxLayout()
        lbl_t = QLabel("📁 DOSYA AÇILMA / AÇILMAMA DURUM MATRİSİ")
        lbl_t.setStyleSheet("font-size: 11px; font-weight: 800; color: #94a3b8; letter-spacing: 0.5px;")
        h_box.addWidget(lbl_t)
        h_box.addStretch(1)

        btn_show_unopened = QPushButton(f"Görüntüle ({len(no_file_list)})")
        btn_show_unopened.setFixedHeight(24)
        btn_show_unopened.setStyleSheet("background: #1e293b; color: #38bdf8; font-size: 10.5px; font-weight: 700; border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 4px; padding: 2px 8px;")
        btn_show_unopened.clicked.connect(lambda: self.filterRequested.emit(Durum.DOSYA_YOK))
        h_box.addWidget(btn_show_unopened)
        layout.addLayout(h_box)

        opened_count = total_count - len(no_file_list)
        stats_box = QHBoxLayout()
        stats_box.setSpacing(8)

        # 3 Blok
        b1 = self._stat_mini_box("EVRİM'DE AÇILAN DOSYALAR", str(opened_count), "#34d399", "🟢 İşlemde")
        b2 = self._stat_mini_box("ACİLEN AÇILMASI GEREKENLER", str(len(urgent_open)), "#f43f5e", "🔴 Gemi Yolda / ETA Yakın")
        b3 = self._stat_mini_box("BEKLEYEN SİPARİŞLER (PO)", str(len(no_file_list) - len(urgent_open)), "#94a3b8", "⚪ Gemi Henüz Yok")

        stats_box.addWidget(b1)
        stats_box.addWidget(b2)
        stats_box.addWidget(b3)
        layout.addLayout(stats_box)

        # Acil açılması gerekenlerden ilk 3'ünü mini liste olarak ver
        if urgent_open:
            sub_title = QLabel("⚠️ ACİLEN DOSYASI AÇILMASI GEREKEN SEVKİYATLAR:")
            sub_title.setStyleSheet("font-size: 10px; font-weight: 800; color: #f43f5e; margin-top: 4px;")
            layout.addWidget(sub_title)

            for it in urgent_open[:4]:
                row_f = QFrame()
                row_f.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                row_f.setStyleSheet("background: #0f172a; border-radius: 4px; padding: 4px 8px;")
                rf_lay = QHBoxLayout(row_f)
                rf_lay.setContentsMargins(6, 3, 6, 3)

                lbl_po = QLabel(f"PO: <b>{it['po']}</b>")
                lbl_po.setStyleSheet("color: #38bdf8; font-size: 11px;")
                lbl_gemi = QLabel(f"🚢 {it['gemi']} ({it['liman']})")
                lbl_gemi.setStyleSheet("color: #e2e8f0; font-size: 11px;")
                lbl_eta = QLabel(f"ETA: {it['eta_t']} ({it['gun_kalan']}g)")
                lbl_eta.setStyleSheet("color: #facc15; font-size: 11px; font-weight: 700;")

                rf_lay.addWidget(lbl_po)
                rf_lay.addWidget(lbl_gemi)
                rf_lay.addStretch(1)
                rf_lay.addWidget(lbl_eta)

                row_f.mousePressEvent = lambda e, item=it: self.shipmentSelected.emit(item)
                layout.addWidget(row_f)

        return card

    def _build_eta_chronological_card(self, etas, recent_berthed=None):
        if recent_berthed is None:
            recent_berthed = []
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER_SUBTLE};
                border-radius: 8px;
                padding: 10px 14px;
            }}
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        # Başlık ve Filtre
        h_box = QHBoxLayout()
        lbl_t = QLabel("🚢 ETA & VARAN GEMİLER RADARI (KRONOLOJİK)")
        lbl_t.setStyleSheet("font-size: 11px; font-weight: 800; color: #38bdf8; letter-spacing: 0.5px;")
        h_box.addWidget(lbl_t)
        h_box.addStretch(1)

        lbl_c = QLabel(f"{len(etas)} Sefer Sırada")
        lbl_c.setStyleSheet("color: #64748b; font-size: 10.5px; font-weight: 600;")
        h_box.addWidget(lbl_c)
        layout.addLayout(h_box)

        if not etas:
            lbl_none = QLabel("Şu anda yaklaşan aktif bir ETA kaydı bulunmuyor.")
            lbl_none.setStyleSheet("color: #64748b; font-size: 11px; padding: 6px;")
            layout.addWidget(lbl_none)
            return card

        # İlk 8 yakın varışı göster
        for it in etas[:8]:
            row_f = QFrame()
            row_f.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            row_f.setStyleSheet("""
                QFrame {
                    background-color: #0d1424;
                    border: 1px solid rgba(255, 255, 255, 0.05);
                    border-radius: 5px;
                    padding: 4px 8px;
                }
                QFrame:hover {
                    background-color: #151f34;
                    border-color: #38bdf8;
                }
            """)
            rf_lay = QHBoxLayout(row_f)
            rf_lay.setContentsMargins(8, 4, 8, 4)
            rf_lay.setSpacing(10)

            # Kalan Gün Rozeti (Hafta sonu/bugün varışları dahil)
            is_recent = it in recent_berthed
            kalan = it.get("gun_kalan", 999)
            if is_recent:
                gun_label = it.get("hafta_sonu_gunu") or ("Bugün" if it.get("bugun_geldi") else "Yeni Yanaştı")
                badge_bg = "rgba(245, 158, 11, 0.25)"
                badge_fg = "#f59e0b"
                txt_k = f"⚓ {gun_label}"
            elif kalan <= 0:
                badge_bg = "rgba(244, 63, 94, 0.25)"
                badge_fg = "#f43f5e"
                txt_k = "🔥 Bugün!"
            elif kalan <= 3:
                badge_bg = "rgba(244, 63, 94, 0.2)"
                badge_fg = "#f43f5e"
                txt_k = f"⚡ {kalan} Gün"
            elif kalan <= 7:
                badge_bg = "rgba(250, 204, 21, 0.2)"
                badge_fg = "#facc15"
                txt_k = f"⏳ {kalan} Gün"
            else:
                badge_bg = "rgba(56, 189, 248, 0.15)"
                badge_fg = "#38bdf8"
                txt_k = f"{kalan} Gün"

            lbl_kalan = QLabel(txt_k)
            lbl_kalan.setStyleSheet(f"background: {badge_bg}; color: {badge_fg}; font-size: 10.5px; font-weight: 800; padding: 2px 6px; border-radius: 4px;")
            rf_lay.addWidget(lbl_kalan)

            date_str = it.get("eta_t") if it.get("eta_t") != "—" else it.get("varis_t", "—")
            lbl_date = QLabel(date_str)
            lbl_date.setStyleSheet("color: #ffffff; font-size: 11px; font-weight: 700;")
            rf_lay.addWidget(lbl_date)

            lbl_vessel = QLabel(f"🚢 {it['gemi']} ({it['liman']})")
            lbl_vessel.setStyleSheet("color: #cbd5e1; font-size: 11px;")
            rf_lay.addWidget(lbl_vessel)

            rf_lay.addStretch(1)

            # Dosya Durumu Rozeti
            has_file = it["dosya_no"] != "—"
            if has_file:
                file_status = f"🟢 Dosya: {it['dosya_no']}"
                f_color = "#34d399"
            else:
                file_status = f"🔴 Dosya Açılmadı! (PO: {it['po']})"
                f_color = "#f43f5e"

            lbl_f_status = QLabel(file_status)
            lbl_f_status.setStyleSheet(f"color: {f_color}; font-size: 10.5px; font-weight: 700;")
            rf_lay.addWidget(lbl_f_status)

            row_f.mousePressEvent = lambda e, item=it: self.shipmentSelected.emit(item)
            layout.addWidget(row_f)

        return card

    def _build_critical_actions_card(self, demuraj, banka, tareks):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER_SUBTLE};
                border-radius: 8px;
                padding: 10px 14px;
            }}
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        lbl_t = QLabel("🚨 ACİL MÜDAHALE GEREKTİREN DOSYALAR (LİMAN / BANKA)")
        lbl_t.setStyleSheet("font-size: 11px; font-weight: 800; color: #f43f5e; letter-spacing: 0.5px;")
        layout.addWidget(lbl_t)

        all_urgent = demuraj + banka + tareks
        for it in all_urgent[:6]:
            row_f = QFrame()
            row_f.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            row_f.setStyleSheet("""
                QFrame {
                    background-color: #0d1424;
                    border-radius: 4px;
                    padding: 4px 8px;
                }
                QFrame:hover {
                    background-color: #151f34;
                }
            """)
            rf_lay = QHBoxLayout(row_f)
            rf_lay.setContentsMargins(6, 3, 6, 3)

            durum_info = it["durum_info"]
            lbl_icon = QLabel(f"{durum_info['icon']} {durum_info['label']}")
            lbl_icon.setStyleSheet(f"color: {durum_info['color']}; font-size: 10.5px; font-weight: 700;")
            rf_lay.addWidget(lbl_icon)

            lbl_dosya = QLabel(f"Dosya: <b>{it['dosya_no']}</b> (PO: {it['po']})")
            lbl_dosya.setStyleSheet("color: #ffffff; font-size: 11px;")
            rf_lay.addWidget(lbl_dosya)

            rf_lay.addStretch(1)

            lbl_detail = QLabel(f"+{it['gun_gecti']} gün geçti • {it['gemi']}")
            lbl_detail.setStyleSheet("color: #94a3b8; font-size: 10.5px;")
            rf_lay.addWidget(lbl_detail)

            row_f.mousePressEvent = lambda e, item=it: self.shipmentSelected.emit(item)
            layout.addWidget(row_f)

        return card

    def _stat_mini_box(self, title, val, color, sub):
        f = QFrame()
        f.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_INPUT};
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 6px;
                padding: 6px 10px;
            }}
        """)
        l = QVBoxLayout(f)
        l.setContentsMargins(6, 4, 6, 4)
        l.setSpacing(1)

        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("color: #64748b; font-size: 9px; font-weight: 700;")
        lbl_v = QLabel(val)
        lbl_v.setStyleSheet(f"color: {color}; font-size: 16px; font-weight: 800;")
        lbl_s = QLabel(sub)
        lbl_s.setStyleSheet("color: #94a3b8; font-size: 9.5px;")

        l.addWidget(lbl_t)
        l.addWidget(lbl_v)
        l.addWidget(lbl_s)
        return f
