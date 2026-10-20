"""
apex_suite_overlay.py — SmartClearance Master Suite Sinematik Gecis Motoru (v2.0 Pro)
SmartClearance APEX ve HORIZON arasinda gercek 60 FPS, havacilik/denizcilik seviyesinde
akici (buttery smooth easing), vektor grafikli, ozel HUD ve telemetri gecis perdesi.
"""

import time
import math
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPoint, QRect, QPointF
from PyQt6.QtGui import (
    QPainter, QColor, QFont, QPen, QBrush, QRadialGradient,
    QLinearGradient, QPainterPath, QPolygonF
)


class SuiteTransitionOverlay(QWidget):
    """
    Apex <-> Horizon arasi yuksek prestijli, 60 FPS sinematik gecis perdesi.
    Vektor cizimler, radar iz birakma (phosphor persistence), AIS hedef pingleri,
    siber lazer tarama ve hassas telemetri gostergeleri icerir.
    """
    transitionCompleted = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.target_system = "HORIZON"
        self.progress = 0.0
        self.start_time = 0.0
        self.duration = 2.0  # Tam 2.0 saniyelik sinematik sure
        self.opacity = 1.0
        self.is_fading_out = False
        self.fade_start_time = 0.0
        self.fade_duration = 0.32  # 320ms ipeksi cozunme

        # AIS simulated vessels (r_ratio, angle_rad, base_alpha, last_ping_time)
        self.horizon_targets = [
            {"r": 0.38, "angle": 0.85, "alpha": 0.2, "label": "MSC OSCAR"},
            {"r": 0.62, "angle": 2.20, "alpha": 0.2, "label": "CMA CGM MARCO POLO"},
            {"r": 0.78, "angle": 3.75, "alpha": 0.2, "label": "MAERSK MC-KINNEY"},
            {"r": 0.50, "angle": 5.10, "alpha": 0.2, "label": "HANKOOK EXPRESS"},
        ]

        # 60 FPS Hassas Zamanlayici
        self.timer = QTimer(self)
        self.timer.setInterval(16)  # ~60 FPS
        self.timer.timeout.connect(self._on_tick)

        self.hide()

    def start_transition(self, target_system):
        """Gecis animasyonunu baslatir."""
        self.target_system = target_system.upper()
        self.progress = 0.0
        self.opacity = 1.0
        self.is_fading_out = False
        self.start_time = time.perf_counter()

        if self.parent():
            self.resize(self.parent().size())

        self.show()
        self.raise_()
        self.timer.start()
        self.update()

    def _on_tick(self):
        now = time.perf_counter()
        elapsed = now - self.start_time

        if not self.is_fading_out:
            raw_p = min(1.0, elapsed / self.duration)
            self.progress = raw_p

            if self.progress >= 1.0:
                self.is_fading_out = True
                self.fade_start_time = time.perf_counter()
                self.transitionCompleted.emit(self.target_system)
        else:
            fade_elapsed = now - self.fade_start_time
            fade_p = min(1.0, fade_elapsed / self.fade_duration)
            # Smoothstep fade out
            self.opacity = max(0.0, 1.0 - (fade_p * fade_p * (3.0 - 2.0 * fade_p)))
            if self.opacity <= 0.0:
                self.timer.stop()
                self.hide()
                return

        self.update()

    @staticmethod
    def _ease_in_out(t):
        """Kupik yumusak ivmelenme ve yavaslama egvisi."""
        if t <= 0.0:
            return 0.0
        if t >= 1.0:
            return 1.0
        return t * t * (3.0 - 2.0 * t)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        painter.setOpacity(self.opacity)

        w = self.width()
        h = self.height()
        center = QPoint(w // 2, h // 2)

        # 1. Secilen Sisteme Ozel Gorsel Motor
        if self.target_system == "HORIZON":
            self._paint_horizon_radar(painter, w, h, center)
        else:
            self._paint_apex_clearance(painter, w, h, center)

        # 2. Ortak HUD Kose Cerceveleri ve Telemetri Yazilari (En Ust Katman)
        self._paint_common_hud_frame(painter, w, h)

    # --------------------------------------------------------------------------
    # ORTAK HAVACILIK / SAVUNMA SANAYII HUD KOSE CERCEVELERI
    # --------------------------------------------------------------------------
    def _paint_common_hud_frame(self, painter, w, h):
        pad = 28
        bracket_len = 32
        accent_col = QColor("#38bdf8") if self.target_system == "HORIZON" else QColor("#10b981")

        pen = QPen(QColor(accent_col.red(), accent_col.green(), accent_col.blue(), 140), 2)
        painter.setPen(pen)

        # Sol-Ust Kose
        painter.drawLine(pad, pad, pad + bracket_len, pad)
        painter.drawLine(pad, pad, pad, pad + bracket_len)

        # Sag-Ust Kose
        painter.drawLine(w - pad, pad, w - pad - bracket_len, pad)
        painter.drawLine(w - pad, pad, w - pad, pad + bracket_len)

        # Sol-Alt Kose
        painter.drawLine(pad, h - pad, pad + bracket_len, h - pad)
        painter.drawLine(pad, h - pad, pad, h - pad - bracket_len)

        # Sag-Alt Kose
        painter.drawLine(w - pad, h - pad, w - pad - bracket_len, h - pad)
        painter.drawLine(w - pad, h - pad, w - pad, h - pad - bracket_len)

        # Telemetri Bilgi Metinleri
        painter.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        dim_text = QColor(148, 163, 184, 160)
        painter.setPen(dim_text)

        # Sol Ust
        painter.drawText(pad + 8, pad + 16, "SMARTCLEARANCE // PROTOCOL v4.82 PRO")
        painter.drawText(pad + 8, pad + 30, "ENCLAVE STATUS: SECURE (TLS 1.3)")

        # Sag Ust
        painter.drawText(w - pad - 230, pad + 16, "CORE TELEMETRY: 60 FPS ULTRA")
        painter.drawText(w - pad - 230, pad + 30, f"TARGET SYSTEM: {self.target_system}")

        # Sol Alt
        painter.drawText(pad + 8, h - pad - 20, "GPS RADAR: 40°58'24\"N 028°49'18\"E")
        painter.drawText(pad + 8, h - pad - 6, "MARITIME LOGISTICS ENGINE ACTIVE")

        # Sag Alt
        pulse = 0.5 + 0.5 * math.sin(time.perf_counter() * 8.0)
        pulse_col = QColor(accent_col.red(), accent_col.green(), accent_col.blue(), int(140 + 115 * pulse))
        painter.setPen(pulse_col)
        painter.drawText(w - pad - 180, h - pad - 6, "● LIVE LINK SYNCHRONIZED")

    # --------------------------------------------------------------------------
    # 1. HORIZON GEÇİŞİ: DERİN DENİZ, DONANMA RADARI & AIS HEDEF PİNGLERİ
    # --------------------------------------------------------------------------
    def _paint_horizon_radar(self, painter, w, h, center):
        # 1. Derin Okyanus Obsidian Degrade
        grad = QRadialGradient(QPointF(center.x(), center.y()), max(w, h) * 0.75)
        grad.setColorAt(0.0, QColor("#08172e"))
        grad.setColorAt(0.5, QColor("#040b17"))
        grad.setColorAt(1.0, QColor("#02050b"))
        painter.fillRect(0, 0, w, h, QBrush(grad))

        # 2. Donanma Radar Pusula Cemberi ve Mesafe Halkalari
        max_r = min(w, h) // 2 - 80
        ring_radii = [int(max_r * 0.33), int(max_r * 0.66), max_r]
        range_labels = ["50 NM", "100 NM", "200 NM"]

        # Arka plan konsantrik halkalari
        for idx, r in enumerate(ring_radii):
            painter.setPen(QPen(QColor(56, 189, 248, 45), 1, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(center, r, r)

            painter.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
            painter.setPen(QColor(56, 189, 248, 110))
            painter.drawText(center.x() + 6, center.y() - r + 14, range_labels[idx])

        # Ana Dis Cember ve Aci Cetveli (Compass Rose Ticks)
        painter.setPen(QPen(QColor(56, 189, 248, 120), 1.5))
        painter.drawEllipse(center, max_r, max_r)

        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Black))
        for deg in range(0, 360, 30):
            rad = math.radians(deg - 90)
            inner_len = 10 if deg % 90 == 0 else 5
            x1 = center.x() + int((max_r - inner_len) * math.cos(rad))
            y1 = center.y() + int((max_r - inner_len) * math.sin(rad))
            x2 = center.x() + int(max_r * math.cos(rad))
            y2 = center.y() + int(max_r * math.sin(rad))
            painter.setPen(QPen(QColor(56, 189, 248, 180 if deg % 90 == 0 else 90), 1.5))
            painter.drawLine(x1, y1, x2, y2)

            # Yon etiketleri: N, E, S, W
            if deg == 0:
                painter.drawText(center.x() - 6, center.y() - max_r - 8, 14, 14, Qt.AlignmentFlag.AlignCenter, "N")
            elif deg == 90:
                painter.drawText(center.x() + max_r + 8, center.y() - 7, 14, 14, Qt.AlignmentFlag.AlignCenter, "E")
            elif deg == 180:
                painter.drawText(center.x() - 6, center.y() + max_r + 8, 14, 14, Qt.AlignmentFlag.AlignCenter, "S")
            elif deg == 270:
                painter.drawText(center.x() - max_r - 20, center.y() - 7, 14, 14, Qt.AlignmentFlag.AlignCenter, "W")

        # 3. Genlesen Sonar Dalgalari (Pulsing Sonar Waves)
        now = time.perf_counter()
        for i in range(3):
            wave_phase = ((now * 0.9) + (i * 0.33)) % 1.0
            wave_r = int(wave_phase * max_r)
            wave_alpha = int((1.0 - wave_phase) * 120)
            painter.setPen(QPen(QColor(6, 182, 212, wave_alpha), 1.5))
            painter.drawEllipse(center, wave_r, wave_r)

        # 4. Donen Radar Tarama Isini ve Fosfor Isik Kuyrugu (Phosphor Persistence Sweep)
        sweep_rad = (now * 3.8) % (2.0 * math.pi)  # Pruzssuz, surekli donus
        beam_x = center.x() + int(max_r * math.cos(sweep_rad))
        beam_y = center.y() + int(max_r * math.sin(sweep_rad))

        # Fosfor Işık Yelpazesi (45 derecelik yumusak degrade kuyruk)
        sweep_path = QPainterPath()
        sweep_path.moveTo(QPointF(center.x(), center.y()))
        sweep_path.arcTo(
            center.x() - max_r, center.y() - max_r,
            max_r * 2, max_r * 2,
            -math.degrees(sweep_rad), 48
        )
        sweep_path.closeSubpath()

        # Yelpaze degrade dolgusu
        pie_grad = QRadialGradient(QPointF(center.x(), center.y()), max_r)
        pie_grad.setColorAt(0.0, QColor(56, 189, 248, 80))
        pie_grad.setColorAt(0.7, QColor(6, 182, 212, 35))
        pie_grad.setColorAt(1.0, QColor(6, 182, 212, 0))
        painter.fillPath(sweep_path, QBrush(pie_grad))

        # Keskin On Isin Cizgisi
        painter.setPen(QPen(QColor(255, 255, 255, 240), 2))
        painter.drawLine(center.x(), center.y(), beam_x, beam_y)

        # 5. AIS Gemi Hedef Pingleri (Vessel Radar Blips with Flare)
        for target in self.horizon_targets:
            tx = center.x() + int(max_r * target["r"] * math.cos(target["angle"]))
            ty = center.y() + int(max_r * target["r"] * math.sin(target["angle"]))

            # Tarayici isin bu hedefin uzerinden gecti mi hesapla
            angle_diff = (sweep_rad - target["angle"]) % (2.0 * math.pi)
            if angle_diff < 0.6:  # Isin yeni gecti, parliyor
                flare_p = 1.0 - (angle_diff / 0.6)
                target["alpha"] = 0.3 + 0.7 * flare_p
                # Radar halkasi halesi
                painter.setPen(QPen(QColor(56, 189, 248, int(180 * flare_p)), 1))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(QPoint(tx, ty), int(6 + 10 * (1 - flare_p)), int(6 + 10 * (1 - flare_p)))
            else:
                target["alpha"] = max(0.25, target["alpha"] * 0.96)

            # Hedef Noktasi ve Etiketi
            blip_col = QColor(56, 189, 248, int(255 * target["alpha"]))
            painter.setBrush(QBrush(blip_col))
            painter.setPen(QPen(QColor(255, 255, 255, int(200 * target["alpha"])), 1))
            painter.drawRect(tx - 3, ty - 3, 6, 6)

            painter.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
            painter.setPen(QColor(148, 163, 184, int(220 * target["alpha"])))
            painter.drawText(tx + 8, ty + 4, target["label"])

        # 6. Merkez Vektor Gemi Logosu (Enterprise Emblem)
        self._paint_horizon_central_emblem(painter, center)

        # 7. Alt Bilgi HUD Karti, Status Ticker ve Yukleme Bari
        self._paint_telemetry_card(
            painter, center,
            brand_title="H O R I Z O N",
            sub_title="GLOBAL MARITIME RADAR // AIS VESSEL TELEMETRY",
            accent_col=QColor("#38bdf8"),
            glow_col=QColor(56, 189, 248, 90),
            steps=[
                "INITIALIZING SATELLITE AIS MESH NETWORK...",
                "SYNCHRONIZING CONTAINER FLEET TELEMETRY & GPS...",
                "ESTABLISHING HIGH-PRECISION MARITIME COCKPIT"
            ]
        )

    def _paint_horizon_central_emblem(self, painter, center):
        """Vektor donanma gemisi ve donen altigen rozet."""
        r = 38
        # Cift dis halka
        now = time.perf_counter()
        rot = now * 40.0

        painter.save()
        painter.translate(center.x(), center.y())

        # Dis parlama
        glow = QRadialGradient(QPointF(0, 0), r * 1.5)
        glow.setColorAt(0.0, QColor(56, 189, 248, 50))
        glow.setColorAt(1.0, QColor(56, 189, 248, 0))
        painter.fillRect(-int(r * 1.5), -int(r * 1.5), int(r * 3), int(r * 3), QBrush(glow))

        # Donen altigen halka
        poly = QPolygonF()
        for i in range(6):
            a = math.radians(rot + i * 60)
            poly.append(QPointF(r * math.cos(a), r * math.sin(a)))
        painter.setPen(QPen(QColor(56, 189, 248, 180), 1.5))
        painter.setBrush(QBrush(QColor(10, 25, 47, 240)))
        painter.drawPolygon(poly)

        # Temiz Modern Vektor Gemi Silueti
        ship_path = QPainterPath()
        ship_path.moveTo(0, -18)      # Pruva (burun)
        ship_path.lineTo(14, 10)      # Sag borda
        ship_path.lineTo(8, 14)       # Sag kici
        ship_path.lineTo(-8, 14)      # Sol kici
        ship_path.lineTo(-14, 10)     # Sol borda
        ship_path.closeSubpath()

        painter.setBrush(QBrush(QColor(56, 189, 248, 220)))
        painter.setPen(QPen(QColor(255, 255, 255, 255), 1.5))
        painter.drawPath(ship_path)

        # Gemi kokpiti
        painter.setBrush(QBrush(QColor("#020610")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(-4, -4, 8, 8)

        painter.restore()

    # --------------------------------------------------------------------------
    # 2. APEX GEÇİŞİ: SİBER GÜMRÜK, LAZER TARAYICI & MASTER DATA ÇEKİRDEĞİ
    # --------------------------------------------------------------------------
    def _paint_apex_clearance(self, painter, w, h, center):
        # 1. Dark Obsidian Matrix Degrade
        grad = QRadialGradient(QPointF(center.x(), center.y()), max(w, h) * 0.75)
        grad.setColorAt(0.0, QColor("#091813"))
        grad.setColorAt(0.5, QColor("#050c09"))
        grad.setColorAt(1.0, QColor("#020504"))
        painter.fillRect(0, 0, w, h, QBrush(grad))

        # 2. Siber Izgara (Cyber Matrix Grid)
        grid_pen = QPen(QColor(16, 185, 129, 20), 1)
        painter.setPen(grid_pen)
        grid_step = 45
        for x in range(0, w, grid_step):
            painter.drawLine(x, 0, x, h)
        for y in range(0, h, grid_step):
            painter.drawLine(0, y, w, y)

        # Yan Marjinlerde Kayan Hex Telemetri Akisi (HUD Koselerine degmeyecek sekilde)
        y_min = 70
        y_max = h - 70
        y_span = max(100, y_max - y_min)
        now = time.perf_counter()
        painter.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        painter.setPen(QColor(16, 185, 129, 65))
        hex_tokens = ["0x4A1F", "CMMF-OK", "GTIP-4011", "TEU-40HC", "BEYAN-26", "TAREKS-VLD"]
        for idx, token in enumerate(hex_tokens):
            y_pos = y_min + int((idx * 55 + now * 40) % y_span)
            painter.drawText(60, y_pos, token)
            painter.drawText(w - 140, y_pos, token)

        # 3. Ipeksi Harmonik Lazer Tarama Isini (Harmonic Vertical Laser Scanner)
        # Sinus dalgasiyla yukaridan asagiya ve geri salinimli gercek optik tarama
        scan_ratio = (math.sin(now * 3.2) + 1.0) * 0.5  # 0.0 - 1.0 arasi pruzssuz
        scan_y = int(80 + scan_ratio * (h - 160))

        # Lazer Isima Degradesi (Gaussian Falloff Glow)
        laser_glow_h = 50
        laser_grad = QLinearGradient(0, scan_y - laser_glow_h, 0, scan_y + laser_glow_h)
        laser_grad.setColorAt(0.0, QColor(16, 185, 129, 0))
        laser_grad.setColorAt(0.5, QColor(16, 185, 129, 75))
        laser_grad.setColorAt(1.0, QColor(16, 185, 129, 0))
        painter.fillRect(0, scan_y - laser_glow_h, w, laser_glow_h * 2, QBrush(laser_grad))

        # Ana Keskin Lazer Cizgisi
        painter.setPen(QPen(QColor(52, 211, 153, 255), 2.5))
        painter.drawLine(0, scan_y, w, scan_y)

        # Lazer Uzerinde Kayan Hedefleme Arti Retikulleri
        reticle_x = int((math.cos(now * 4.5) + 1.0) * 0.5 * (w - 200) + 100)
        painter.setPen(QPen(QColor(255, 255, 255, 230), 1.5))
        painter.drawLine(reticle_x - 14, scan_y, reticle_x + 14, scan_y)
        painter.drawLine(reticle_x, scan_y - 14, reticle_x, scan_y + 14)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPoint(reticle_x, scan_y), 8, 8)

        # 4. Merkez Gumruk Zekasi ve CMMF Altigen Muhru
        self._paint_apex_central_emblem(painter, center)

        # 5. Alt Bilgi HUD Karti, Status Ticker ve Yukleme Bari
        self._paint_telemetry_card(
            painter, center,
            brand_title="A P E X",
            sub_title="INTELLIGENT CUSTOMS CLEARANCE // CMMF MASTER ENGINE",
            accent_col=QColor("#10b981"),
            glow_col=QColor(16, 185, 129, 90),
            steps=[
                "VERIFYING HANKOOK LOGISTICS PIPELINE...",
                "SYNCHRONIZING CMMF MASTER DATA & CUSTOMS MATRIX...",
                "OPERATIONS DESK & INVOICE STUDIO READY"
            ]
        )

    def _paint_apex_central_emblem(self, painter, center):
        """Kriptografik Gumruk Zekasi Muhru ve Parildayan Simsek Cekirdegi."""
        r = 38
        now = time.perf_counter()
        rot = -now * 40.0

        painter.save()
        painter.translate(center.x(), center.y())

        # Dis parlama halesi
        glow = QRadialGradient(QPointF(0, 0), r * 1.5)
        glow.setColorAt(0.0, QColor(16, 185, 129, 50))
        glow.setColorAt(1.0, QColor(16, 185, 129, 0))
        painter.fillRect(-int(r * 1.5), -int(r * 1.5), int(r * 3), int(r * 3), QBrush(glow))

        # Ters donen cift sekizgen
        for i_pass, sign in [(0, 1), (1, -1)]:
            poly = QPolygonF()
            for i in range(8):
                a = math.radians(rot * sign + i * 45)
                cur_r = r if i_pass == 0 else r - 8
                poly.append(QPointF(cur_r * math.cos(a), cur_r * math.sin(a)))
            pen_col = QColor(16, 185, 129, 200 if i_pass == 0 else 100)
            painter.setPen(QPen(pen_col, 1.5))
            painter.setBrush(QBrush(QColor(6, 20, 15, 235)) if i_pass == 0 else Qt.BrushStyle.NoBrush)
            painter.drawPolygon(poly)

        # Geometrik Vektor Simsek / Dijital Guc Logosu
        bolt = QPainterPath()
        bolt.moveTo(2, -18)
        bolt.lineTo(-12, 0)
        bolt.lineTo(-2, 0)
        bolt.lineTo(-4, 18)
        bolt.lineTo(12, -2)
        bolt.lineTo(2, -2)
        bolt.closeSubpath()

        painter.setBrush(QBrush(QColor(52, 211, 153, 235)))
        painter.setPen(QPen(QColor(255, 255, 255, 255), 1.5))
        painter.drawPath(bolt)

        painter.restore()

    # --------------------------------------------------------------------------
    # 3. YUKSEK PRESTIJLI TELEMETRI HUD KARTI & BUTTERY SMOOTH PROGRESS BAR
    # --------------------------------------------------------------------------
    def _paint_telemetry_card(self, painter, center, brand_title, sub_title, accent_col, glow_col, steps):
        card_w = 600
        card_h = 168
        card_x = center.x() - card_w // 2
        card_y = center.y() + 85

        # Buzlu Cam (Frosted Dark Obsidian Glass Panel)
        card_bg = QColor(8, 14, 24, 245)
        painter.setBrush(QBrush(card_bg))
        painter.setPen(QPen(glow_col, 1.2))
        painter.drawRoundedRect(card_x, card_y, card_w, card_h, 12, 12)

        # Kart Kose Cetvelleri
        ret_len = 12
        painter.setPen(QPen(accent_col, 2))
        painter.drawLine(card_x, card_y, card_x + ret_len, card_y)
        painter.drawLine(card_x, card_y, card_x, card_y + ret_len)
        painter.drawLine(card_x + card_w, card_y, card_x + card_w - ret_len, card_y)
        painter.drawLine(card_x + card_w, card_y, card_x + card_w, card_y + ret_len)

        # 1. Ust Marka Etiketi
        painter.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        painter.setPen(QColor(148, 163, 184, 200))
        painter.drawText(card_x, card_y + 20, card_w, 14, Qt.AlignmentFlag.AlignCenter, "S M A R T C L E A R A N C E")

        # 2. Ana Sistem Basligi
        painter.setFont(QFont("Segoe UI", 20, QFont.Weight.Black))
        painter.setPen(accent_col)
        painter.drawText(card_x, card_y + 36, card_w, 36, Qt.AlignmentFlag.AlignCenter, brand_title)

        # 3. Alt Baslik
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        painter.setPen(QColor(148, 163, 184, 180))
        painter.drawText(card_x, card_y + 72, card_w, 16, Qt.AlignmentFlag.AlignCenter, sub_title)

        # 4. Dinamik Asama Yazisi (3 Asamali Gecis)
        eased_p = self._ease_in_out(self.progress)
        if eased_p < 0.40:
            active_step = steps[0]
            step_idx = "01/03"
        elif eased_p < 0.82:
            active_step = steps[1]
            step_idx = "02/03"
        else:
            active_step = steps[2]
            step_idx = "03/03"

        # Canli Yesil Yanip Sonen Pulse
        now = time.perf_counter()
        pulse = 0.5 + 0.5 * math.sin(now * 10.0)
        pulse_alpha = int(140 + 115 * pulse)

        painter.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        painter.setPen(QColor(52, 211, 153, pulse_alpha))
        status_line = f"● [{step_idx}] {active_step}"
        painter.drawText(card_x, card_y + 98, card_w, 20, Qt.AlignmentFlag.AlignCenter, status_line)

        # 5. Ultra Akici Ilerleme Cubugu (Smooth Progress Bar + Percentage)
        pb_w = card_w - 70
        pb_h = 5
        pb_x = card_x + 35
        pb_y = card_y + 130

        # Zemin
        painter.setBrush(QBrush(QColor(255, 255, 255, 18)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(pb_x, pb_y, pb_w, pb_h, 3, 3)

        # Eased Fill
        fill_w = max(4, int(pb_w * eased_p))
        bar_grad = QLinearGradient(pb_x, pb_y, pb_x + pb_w, pb_y)
        if self.target_system == "HORIZON":
            bar_grad.setColorAt(0.0, QColor("#0284c7"))
            bar_grad.setColorAt(1.0, QColor("#38bdf8"))
        else:
            bar_grad.setColorAt(0.0, QColor("#059669"))
            bar_grad.setColorAt(1.0, QColor("#34d399"))

        painter.setBrush(QBrush(bar_grad))
        painter.drawRoundedRect(pb_x, pb_y, fill_w, pb_h, 3, 3)

        # Parlayan Uç (Glowing Leading Tip)
        tip_x = pb_x + fill_w
        tip_glow = QRadialGradient(QPointF(tip_x, pb_y + 2), 8)
        tip_glow.setColorAt(0.0, QColor(255, 255, 255, 220))
        tip_glow.setColorAt(0.5, QColor(accent_col.red(), accent_col.green(), accent_col.blue(), 180))
        tip_glow.setColorAt(1.0, QColor(accent_col.red(), accent_col.green(), accent_col.blue(), 0))
        painter.fillRect(tip_x - 8, pb_y - 6, 16, 16, QBrush(tip_glow))

        # Yuzde Metni
        pct = int(eased_p * 100)
        painter.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        painter.setPen(QColor(148, 163, 184, 200))
        painter.drawText(pb_x, pb_y + 10, pb_w, 14, Qt.AlignmentFlag.AlignRight, f"{pct}%")
