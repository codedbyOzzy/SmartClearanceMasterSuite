"""
================================================================================
SMARTCLEARANCE HORIZON — SEFER & OPERASYON BÜLTENİ (PDF MOTORU)
================================================================================
Tasarım Dili : Executive Briefing / Linear Clean Editorial
Teknoloji    : PyQt6.QtWebEngineCore (Vektörel PDF Çıktısı)
Özellikler   :
  - Tekil Konteyner Canlı ETA & Rota Yönetici Bülteni
  - Filo / Toplu Yük Liman ve Rötar Analiz Raporu
  - Boş Konteyner İade (Empty Return) ve Serbest Süre Bilgilendirmesi
================================================================================
"""

import os
import sys
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWebEngineCore import QWebEnginePage


class HorizonPdfGenerator(QObject):
    finished = pyqtSignal(str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.page = None
        self.target_path = ""

    def generate_single_brief(self, item, target_pdf_path):
        """Tek bir yük için minimalist Horizon Sefer Bülteni üretir."""
        self.target_path = target_pdf_path
        html_content = self._build_single_brief_html(item)
        self._render_html_to_pdf(html_content)

    def generate_fleet_summary(self, items, kpi_stats, target_pdf_path, title=None, subtitle=None):
        """Tüm takip listesi veya seçili armatörler için Horizon Filo & Operasyon Bülteni üretir."""
        self.target_path = target_pdf_path
        html_content = self._build_fleet_summary_html(items, kpi_stats, title=title, subtitle=subtitle)
        self._render_html_to_pdf(html_content)

    def _render_html_to_pdf(self, html_content):
        self.page = QWebEnginePage()
        self.page.loadFinished.connect(self._on_load_finished)
        self.page.pdfPrintingFinished.connect(self._on_pdf_finished)
        self.page.setHtml(html_content)

    def _on_load_finished(self, ok):
        if not ok:
            self.finished.emit(self.target_path, False)
            return
        # Sayfanın CSS render'ı tamamlanması için kısa gecikme
        QTimer.singleShot(150, lambda: self.page.printToPdf(self.target_path))

    def _on_pdf_finished(self, path, success):
        self.finished.emit(path, success)
        # Bellek temizliği
        if self.page:
            self.page.deleteLater()
            self.page = None

    # --------------------------------------------------------------------------
    # HTML ŞABLONLARI (EXECUTIVE BRIEFING AESTHETIC)
    # --------------------------------------------------------------------------

    def _build_single_brief_html(self, it):
        cntr = it.get("container_no", "—")
        bl = it.get("bl_no", "—")
        carrier = it.get("carrier", "—")
        dosya = it.get("dosya", "—")
        vessel = it.get("vessel", "—")
        pol = it.get("pol", "—")
        pod = it.get("pod", "—")
        excel_eta = it.get("excel_eta", "—")
        live_eta = it.get("live_eta", "—")
        diff = it.get("eta_diff", "—")
        kalan = it.get("kalan_gun", "—")
        now_str = datetime.now().strftime("%d.%m.%Y %H:%M")
        report_ref = f"SCH-{cntr}-{datetime.now().strftime('%Y%m%d')}"

        # Rötar Durumu Rengi
        diff_color = "#f43f5e" if ("Rötar" in diff or "+" in diff) else ("#10b981" if ("Zamanında" in diff or "Erken" in diff or "Aynı" in diff) else "#0284c7")
        diff_bg = "rgba(244, 63, 94, 0.08)" if ("Rötar" in diff or "+" in diff) else ("rgba(16, 185, 129, 0.08)" if ("Zamanında" in diff or "Erken" in diff or "Aynı" in diff) else "rgba(2, 132, 199, 0.08)")

        # Boş Konteyner İade Bilgisi
        empty_date = it.get("empty_return_date")
        empty_addr = it.get("empty_return_address")
        if empty_addr and str(empty_date)[:4] not in ("0001", "None", ""):
            clean_date = str(empty_date)[:10]
            empty_box_html = f"""
            <div class="info-card">
              <div class="card-label">BOŞ KONTEYNER İADE DEPOSU & SON TARİH</div>
              <div class="card-val" style="color: #0284c7;">{empty_addr}</div>
              <div class="card-sub">Son Teslim Tarihi: <b>{clean_date}</b> (Demuraj riskine karşı bu tarihten önce teslim edilmelidir)</div>
            </div>
            """
        else:
            empty_box_html = f"""
            <div class="info-card">
              <div class="card-label">BOŞ KONTEYNER İADE (EMPTY RETURN) DURUMU</div>
              <div class="card-val" style="color: #64748b;">⏳ Gemi Seyrinde / Tahliye Bekleniyor</div>
              <div class="card-sub">Konteyner {pod} limanına indikten sonra acenta tarafından boş iade deposu tayin edilecektir.</div>
            </div>
            """

        # Zaman Çizelgesi Adımları
        curr = it.get("current_moves") or []
        prov = it.get("provisional_moves") or []
        milestones_rows = ""

        for m in curr:
            loc = m.get("Location") or m.get("LocationTerminal") or "Liman"
            dt_s = m.get("DateString") or m.get("Date", "")[:10]
            desc = m.get("StatusDescription") or "Ayrıldı"
            v = m.get("Vessel") or vessel
            milestones_rows += f"""
            <tr>
              <td><span class="badge badge-done">TAMAMLANDI</span></td>
              <td><b>{loc}</b></td>
              <td>{desc}</td>
              <td>{dt_s}</td>
              <td>{v}</td>
            </tr>
            """

        if it.get("vessel_lat"):
            milestones_rows += f"""
            <tr style="background: rgba(56, 189, 248, 0.04);">
              <td><span class="badge badge-live">CANLI SEYİR</span></td>
              <td><b>Akdeniz Seyrinde</b></td>
              <td>Canlı AIS Telemetrisi ({it['vessel_lat']:.2f}°, {it['vessel_lng']:.2f}°)</td>
              <td>Anlık</td>
              <td>{vessel}</td>
            </tr>
            """

        for m in prov:
            loc = m.get("Location") or m.get("LocationTerminal") or "Varış Limanı"
            dt_s = m.get("DateString") or m.get("Date", "")[:10]
            desc = m.get("StatusDescription") or "Planlanan Varış"
            milestones_rows += f"""
            <tr>
              <td><span class="badge badge-pending">PLANLANAN</span></td>
              <td><b>{loc}</b></td>
              <td>{desc}</td>
              <td><b>{dt_s}</b></td>
              <td>{vessel}</td>
            </tr>
            """

        if not milestones_rows:
            milestones_rows = f"""
            <tr>
              <td><span class="badge badge-done">KALKIŞ</span></td>
              <td><b>{pol}</b></td>
              <td>Yola Çıktı</td>
              <td>—</td>
              <td>{vessel}</td>
            </tr>
            <tr>
              <td><span class="badge badge-pending">VARIŞ</span></td>
              <td><b>{pod}</b></td>
              <td>Planlanan Varış</td>
              <td><b>{live_eta}</b></td>
              <td>{vessel}</td>
            </tr>
            """

        return f"""
<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8">
  <title>SmartClearance Horizon Briefing - {cntr}</title>
  <style>
    @page {{ size: A4 portrait; margin: 18mm 16mm; }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      color: #0f172a;
      background: #ffffff;
      line-height: 1.45;
      font-size: 12px;
    }}
    
    /* Header */
    .header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      border-bottom: 2px solid #0f172a;
      padding-bottom: 12px;
      margin-bottom: 20px;
    }}
    .brand-title {{
      font-size: 20px;
      font-weight: 800;
      color: #0f172a;
      letter-spacing: -0.5px;
    }}
    .brand-sub {{
      font-size: 10px;
      font-weight: 700;
      color: #0284c7;
      text-transform: uppercase;
      letter-spacing: 0.8px;
      margin-top: 2px;
    }}
    .meta-box {{
      text-align: right;
      font-size: 10px;
      color: #64748b;
    }}
    .meta-box b {{ color: #0f172a; }}

    /* Hero Card */
    .hero-box {{
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 12px;
      padding: 16px 20px;
      margin-bottom: 20px;
    }}
    .hero-top {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 14px;
    }}
    .cntr-title {{
      font-size: 22px;
      font-weight: 800;
      color: #0f172a;
      letter-spacing: -0.5px;
    }}
    .carrier-tag {{
      background: #0f172a;
      color: #ffffff;
      font-size: 11px;
      font-weight: 700;
      padding: 4px 12px;
      border-radius: 6px;
      letter-spacing: 0.5px;
    }}

    /* ETA Comparison Grid */
    .eta-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr 1.2fr;
      gap: 12px;
      margin-bottom: 12px;
    }}
    .eta-card {{
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 10px 14px;
    }}
    .eta-label {{
      font-size: 10px;
      font-weight: 700;
      color: #64748b;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}
    .eta-value {{
      font-size: 16px;
      font-weight: 800;
      color: #0f172a;
      margin-top: 3px;
    }}

    .diff-pill {{
      display: flex;
      flex-direction: column;
      justify-content: center;
      background: {diff_bg};
      border: 1.5px solid {diff_color};
      border-radius: 8px;
      padding: 8px 14px;
    }}
    .diff-text {{
      font-size: 15px;
      font-weight: 800;
      color: {diff_color};
    }}
    .diff-sub {{
      font-size: 10px;
      font-weight: 600;
      color: {diff_color};
      margin-top: 2px;
    }}

    /* Voyage Specs */
    .specs-row {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 10px;
      padding-top: 10px;
      border-top: 1px solid #e2e8f0;
      font-size: 11px;
    }}
    .spec-item div:first-child {{ color: #64748b; font-size: 9px; font-weight: 700; text-transform: uppercase; }}
    .spec-item div:last-child {{ color: #0f172a; font-weight: 700; margin-top: 2px; }}

    /* Section Headers */
    .sec-title {{
      font-size: 12px;
      font-weight: 800;
      color: #0f172a;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 8px;
      display: flex;
      align-items: center;
      gap: 6px;
    }}

    /* Table */
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 11px;
      margin-bottom: 20px;
    }}
    th {{
      background: #f1f5f9;
      color: #475569;
      font-weight: 700;
      text-align: left;
      padding: 7px 10px;
      border-bottom: 1px solid #cbd5e1;
      font-size: 10px;
      text-transform: uppercase;
    }}
    td {{
      padding: 7px 10px;
      border-bottom: 1px solid #f1f5f9;
      color: #1e293b;
    }}

    /* Badges */
    .badge {{
      font-size: 9px;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 4px;
      letter-spacing: 0.5px;
    }}
    .badge-done {{ background: #dcfce7; color: #166534; }}
    .badge-live {{ background: #e0f2fe; color: #0369a1; }}
    .badge-pending {{ background: #fef3c7; color: #92400e; }}

    /* Info Cards (Empty Return & Notes) */
    .info-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      margin-bottom: 24px;
    }}
    .info-card {{
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 12px 14px;
    }}
    .card-label {{ font-size: 9px; font-weight: 800; color: #64748b; text-transform: uppercase; }}
    .card-val {{ font-size: 13px; font-weight: 800; color: #0f172a; margin-top: 3px; }}
    .card-sub {{ font-size: 10px; color: #64748b; margin-top: 4px; line-height: 1.35; }}

    /* Footer */
    .footer {{
      border-top: 1px solid #e2e8f0;
      padding-top: 10px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 10px;
      color: #94a3b8;
    }}
  </style>
</head>
<body>

  <!-- Header -->
  <div class="header">
    <div>
      <div class="brand-title">SmartClearance Horizon</div>
      <div class="brand-sub">Küresel Konteyner & Canlı ETA Operasyon Bülteni</div>
    </div>
    <div class="meta-box">
      <div>Rapor Ref: <b>{report_ref}</b></div>
      <div>Tarih / Saat: <b>{now_str}</b></div>
      <div style="color: #0284c7; font-weight: 700;">Canlı Telemetri Doğrulandı</div>
    </div>
  </div>

  <!-- Hero Box -->
  <div class="hero-box">
    <div class="hero-top">
      <div>
        <div style="font-size: 10px; font-weight: 700; color: #64748b; text-transform: uppercase;">YÜK REFERANSI & DOSYA</div>
        <div class="cntr-title">{cntr}</div>
      </div>
      <div class="carrier-tag">{carrier}</div>
    </div>

    <!-- ETA Comparison Grid -->
    <div class="eta-grid">
      <div class="eta-card">
        <div class="eta-label">Excel Planlanan ETA</div>
        <div class="eta-value">{excel_eta}</div>
      </div>
      <div class="eta-card">
        <div class="eta-label">Canlı Armatör ETA</div>
        <div class="eta-value" style="color: #0284c7;">{live_eta}</div>
      </div>
      <div class="diff-pill">
        <div class="diff-text">{diff}</div>
        <div class="diff-sub">{kalan}</div>
      </div>
    </div>

    <!-- Specs Row -->
    <div class="specs-row">
      <div class="spec-item">
        <div>Taşıyıcı Gemi</div>
        <div>{vessel}</div>
      </div>
      <div class="spec-item">
        <div>Yükleme Limanı (POL)</div>
        <div>{pol}</div>
      </div>
      <div class="spec-item">
        <div>Tahliye Limanı (POD)</div>
        <div>{pod}</div>
      </div>
      <div class="spec-item">
        <div>Konşimento (B/L) / Dosya</div>
        <div>{bl} / {dosya}</div>
      </div>
    </div>
  </div>

  <!-- Milestones Table -->
  <div class="sec-title">📍 Sefer Zaman Çizelgesi ve Ara Uğraklar (Milestones)</div>
  <table>
    <thead>
      <tr>
        <th style="width: 100px;">Durum</th>
        <th>Liman / Terminal</th>
        <th>Açıklama</th>
        <th style="width: 110px;">Tarih</th>
        <th style="width: 130px;">Gemi</th>
      </tr>
    </thead>
    <tbody>
      {milestones_rows}
    </tbody>
  </table>

  <!-- Empty Return & Free Time Section -->
  <div class="sec-title">🔄 Boş Konteyner İade (Empty Return) ve Operasyonel Notlar</div>
  <div class="info-grid">
    {empty_box_html}
    <div class="info-card">
      <div class="card-label">DEMURAJ / SERBEST SÜRE (FREE TIME) NOTU</div>
      <div class="card-val" style="color: #0f172a;">Liman İnişi: {live_eta}</div>
      <div class="card-sub">Geminin tahliyesini takiben armatör serbest süresi (Free Time) işlemeye başlayacaktır. Ardiye ve demuraj masraflarını önlemek için çekim evrakları hazırlanmalıdır.</div>
    </div>
  </div>

  <!-- Footer -->
  <div class="footer">
    <div>SmartClearance Horizon Intelligence System • Otomatik Canlı Acenta Doğrulaması</div>
    <div>Sayfa 1 / 1</div>
  </div>

</body>
</html>
"""

    def _build_fleet_summary_html(self, items, kpi_stats, title=None, subtitle=None):
        now_str = datetime.now().strftime("%d.%m.%Y %H:%M")
        report_ref = f"SCH-FLEET-{datetime.now().strftime('%Y%m%d_%H%M')}"
        title_text = title or "SmartClearance Horizon Filo & Operasyon Özeti"
        subtitle_text = subtitle or "Doğruer Gümrük Müşavirliği A.Ş. • Küresel Konteyner & Canlı Rota Radarı"

        rows_html = ""
        for it in items:
            c = it.get("carrier", "—")
            cntr = it.get("container_no", "—")
            bl = it.get("bl_no", "—")
            ex = it.get("excel_eta", "—")
            live = it.get("live_eta", "—")
            diff = it.get("eta_diff", "—")
            kalan = it.get("kalan_gun", "—")
            vessel = it.get("vessel", "—")

            diff_style = "color: #f43f5e; font-weight: 700;" if ("Rötar" in diff or "+" in diff) else ("color: #10b981; font-weight: 700;" if ("Zamanında" in diff or "Erken" in diff or "Aynı" in diff) else "color: #64748b;")

            rows_html += f"""
            <tr>
              <td><b>{it.get('dosya', '—')}</b></td>
              <td><span style="font-weight: 700; color: #0284c7;">{c}</span></td>
              <td><b>{cntr}</b></td>
              <td>{bl}</td>
              <td>{ex}</td>
              <td style="color: #0284c7; font-weight: 700;">{live}</td>
              <td style="{diff_style}">{diff}</td>
              <td>{kalan}</td>
              <td>{vessel}</td>
            </tr>
            """

        return f"""
<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8">
  <title>{title_text}</title>
  <style>
    @page {{ size: A4 landscape; margin: 14mm 14mm; }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      color: #0f172a;
      background: #ffffff;
      line-height: 1.4;
      font-size: 11px;
    }}
    .header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      border-bottom: 2px solid #0f172a;
      padding-bottom: 10px;
      margin-bottom: 14px;
    }}
    .brand-title {{ font-size: 18px; font-weight: 800; color: #0f172a; }}
    .brand-sub {{ font-size: 9px; font-weight: 700; color: #0284c7; text-transform: uppercase; }}
    .meta-box {{ text-align: right; font-size: 9px; color: #64748b; }}

    .kpi-row {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 10px;
      margin-bottom: 14px;
    }}
    .kpi-card {{
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 8px 12px;
    }}
    .kpi-title {{ font-size: 8px; font-weight: 800; color: #64748b; text-transform: uppercase; }}
    .kpi-val {{ font-size: 18px; font-weight: 800; color: #0f172a; margin-top: 2px; }}

    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 10px;
    }}
    th {{
      background: #0f172a;
      color: #ffffff;
      font-weight: 700;
      text-align: left;
      padding: 6px 8px;
      font-size: 9px;
      text-transform: uppercase;
    }}
    td {{
      padding: 5px 8px;
      border-bottom: 1px solid #e2e8f0;
      color: #1e293b;
    }}
    tr:nth-child(even) {{ background: #f8fafc; }}

    .footer {{
      border-top: 1px solid #e2e8f0;
      padding-top: 8px;
      margin-top: 14px;
      display: flex;
      justify-content: space-between;
      font-size: 9px;
      color: #94a3b8;
    }}
  </style>
</head>
<body>
  <div class="header">
    <div>
      <div class="brand-title">{title_text}</div>
      <div class="brand-sub">{subtitle_text}</div>
    </div>
    <div class="meta-box">
      <div>Rapor Ref: <b>{report_ref}</b></div>
      <div>Tarih / Saat: <b>{now_str}</b></div>
    </div>
  </div>

  <div class="kpi-row">
    <div class="kpi-card">
      <div class="kpi-title">Toplam Takipteki Yük</div>
      <div class="kpi-val">{kpi_stats.get('total', '0')}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-title">Rötar Tespit Edilenler</div>
      <div class="kpi-val" style="color: #f43f5e;">{kpi_stats.get('delayed', '0')}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-title">Erken / Zamanında</div>
      <div class="kpi-val" style="color: #10b981;">{kpi_stats.get('ontime', '0')}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-title">Canlı Telemetri Bağlı</div>
      <div class="kpi-val" style="color: #0284c7;">{kpi_stats.get('live', '0')}</div>
    </div>
  </div>

  <table>
    <thead>
      <tr>
        <th>Dosya No</th>
        <th>Armatör</th>
        <th>Konteyner No</th>
        <th>B/L No</th>
        <th>Excel ETA</th>
        <th>Canlı ETA</th>
        <th>Sapma</th>
        <th>Kalan Gün</th>
        <th>Gemi Adı</th>
      </tr>
    </thead>
    <tbody>
      {rows_html}
    </tbody>
  </table>

  <div class="footer">
    <div>SmartClearance Horizon • Otomatik Acenta Telemetrisi</div>
    <div>Gizli ve Şirkete Özel Operasyon Bülteni</div>
  </div>
</body>
</html>
"""
