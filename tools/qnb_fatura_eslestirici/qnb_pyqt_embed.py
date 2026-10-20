import sys
import os
import threading
import json
import tempfile
import datetime
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QMessageBox, QFileDialog
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEngineScript, QWebEnginePage, QWebEngineDownloadRequest
from PyQt6.QtCore import QUrl, pyqtSignal, QObject, QMarginsF
from PyQt6.QtGui import QPageLayout, QPageSize
from PyQt6 import QtCore

def get_autofill_js():
    config_path = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "SmartClearance", "config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                if cfg.get("qnb_autofill", True):
                    u = cfg.get("qnb_user", "").replace('\\', '\\\\').replace('"', '\\"')
                    p = cfg.get("qnb_pass", "").replace('\\', '\\\\').replace('"', '\\"')
                    if u and p:
                        return f"""
                        (function() {{
                            function tryFill() {{
                                let uField = document.getElementById('userid') || document.querySelector("input[name='userid']");
                                let pField = document.getElementById('password') || document.querySelector("input[name='password']");
                                if (uField && pField) {{
                                    if (!uField.value) {{
                                        uField.value = "{u}";
                                        uField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                        uField.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                    }}
                                    if (!pField.value) {{
                                        pField.value = "{p}";
                                        pField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                        pField.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                    }}
                                }}
                            }}
                            tryFill();
                            setTimeout(tryFill, 800);
                            setTimeout(tryFill, 1800);
                        }})();
                        """
        except Exception:
            pass
    return ""

class PopupWebEngineView(QWebEngineView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.popups = []

    def createWindow(self, type):
        # Popup fatura pencereleri için kullanıcı betikleri (eslestirici panel) içermeyen temiz profil oluştur
        popup = QWebEngineView()
        clean_popup_profile = QWebEngineProfile(f"QNB_PopupProfile_{id(popup)}", popup)
        popup_page = SilentWebEnginePage(clean_popup_profile, popup)
        popup.setPage(popup_page)
        popup.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
        popup.resize(780, 680)
        popup.setMinimumSize(600, 500)
        popup.setWindowTitle("e-Fatura Görüntüleyici")
        popup.titleChanged.connect(lambda t: popup.setWindowTitle(f"e-Fatura: {t}" if t and t != "about:blank" else "e-Fatura"))
        
        # JS'den window.print() çağrıldığında tetiklenir
        def handle_print():
            file_path, _ = QFileDialog.getSaveFileName(popup, "PDF Kaydet", "Fatura.pdf", "PDF Dosyaları (*.pdf)")
            if file_path:
                def on_pdf_done(file_path_res, success):
                    if success:
                        QMessageBox.information(popup, "Başarılı", "PDF başarıyla kaydedildi!")
                        try:
                            os.startfile(file_path)
                        except Exception:
                            pass
                        popup.close() # Yazdırma bitince popup'ı kapat
                layout = QPageLayout(
                    QPageSize(QPageSize.PageSizeId.A4),
                    QPageLayout.Orientation.Portrait,
                    QMarginsF(0, 0, 0, 0)
                )
                popup.page().printToPdf(file_path, layout)
                popup.page().pdfPrintingFinished.connect(on_pdf_done)
                
        popup.page().printRequested.connect(handle_print)
        popup.show()
        self.popups.append(popup)
        return popup

class SilentWebEnginePage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        pass

class InvoicePdfMerger(QObject):
    finished = pyqtSignal(str, bool, str)

    def __init__(self, invoices, output_path, profile=None, parent=None):
        super().__init__(parent)
        self.invoices = invoices
        self.output_path = output_path
        self.temp_dir = tempfile.mkdtemp(prefix="qnb_invoices_")
        self.temp_pdfs = []
        self.current_idx = 0
        # PDF oluşturma motoru için panel betiklerinden tamamen izole edilmiş temiz profil
        self.clean_profile = QWebEngineProfile(f"QNB_PdfMerger_{id(self)}", self)
        self.page = QWebEnginePage(self.clean_profile, self)
        self.page.pdfPrintingFinished.connect(self._on_pdf_printed)

    def start(self):
        self._process_current()

    def _process_current(self):
        if self.current_idx >= len(self.invoices):
            self._merge_all()
            return

        inv = self.invoices[self.current_idx]
        temp_pdf = os.path.join(self.temp_dir, f"inv_{self.current_idx}.pdf")
        self.temp_pdfs.append(temp_pdf)

        raw_html = inv.get("html", "")
        # Fatura HTML'inin içine hiçbir arayüz kutusunun girmemesi için kesin CSS kuralları ekle
        no_panel_style = """
        <style>
            #gumruk-eslestirici-panel,
            #gumruk-sonuc-modal,
            .gumruk-no-print,
            [id^="gumruk-"] {
                display: none !important;
                visibility: hidden !important;
                opacity: 0 !important;
            }
        </style>
        """
        if "</head>" in raw_html:
            clean_html = raw_html.replace("</head>", f"{no_panel_style}</head>")
        else:
            clean_html = f"{no_panel_style}{raw_html}"

        def _on_loaded(ok):
            try:
                self.page.loadFinished.disconnect(_on_loaded)
            except Exception:
                pass
            layout = QPageLayout(
                QPageSize(QPageSize.PageSizeId.A4),
                QPageLayout.Orientation.Portrait,
                QMarginsF(0, 0, 0, 0)
            )
            self.page.printToPdf(temp_pdf, layout)

        self.page.loadFinished.connect(_on_loaded)
        self.page.setHtml(clean_html, QUrl("https://portal.qnbesolutions.com.tr/"))

    def _on_pdf_printed(self, file_path, success):
        self.current_idx += 1
        self._process_current()

    def _merge_all(self):
        try:
            valid_pdfs = [p for p in self.temp_pdfs if os.path.exists(p) and os.path.getsize(p) > 0]
            if not valid_pdfs:
                raise Exception("Birleştirilecek geçerli PDF dosyası bulunamadı.")

            merged_successfully = False
            last_err = ""

            # 1. Yöntem: pypdf (Standart ve hızlı)
            if not merged_successfully:
                try:
                    from pypdf import PdfWriter
                    writer = PdfWriter()
                    for p in valid_pdfs:
                        writer.append(p)
                    with open(self.output_path, "wb") as f:
                        writer.write(f)
                    writer.close()
                    merged_successfully = True
                except Exception as e:
                    last_err = str(e)

            # 2. Yöntem: PyPDF2
            if not merged_successfully:
                try:
                    from PyPDF2 import PdfMerger
                    merger = PdfMerger()
                    for p in valid_pdfs:
                        merger.append(p)
                    merger.write(self.output_path)
                    merger.close()
                    merged_successfully = True
                except Exception as e:
                    last_err = str(e)

            # 3. Yöntem: PyMuPDF (fitz)
            if not merged_successfully:
                try:
                    try:
                        import pymupdf as fitz
                    except ImportError:
                        import fitz
                    merged = fitz.open()
                    for p in valid_pdfs:
                        doc = fitz.open(p)
                        merged.insert_pdf(doc)
                        doc.close()
                    merged.save(self.output_path)
                    merged.close()
                    merged_successfully = True
                except Exception as e:
                    last_err = str(e)

            # Geçici dosyaları temizle
            for p in self.temp_pdfs:
                try: os.remove(p)
                except Exception: pass
            try: os.rmdir(self.temp_dir)
            except Exception: pass

            if merged_successfully and os.path.exists(self.output_path) and os.path.getsize(self.output_path) > 0:
                self.finished.emit(self.output_path, True, "")
            else:
                self.finished.emit(self.output_path, False, f"PDF birleştirme başarısız oldu: {last_err}")
        except Exception as e:
            self.finished.emit(self.output_path, False, str(e))

class StdinListener(QObject):
    inject_signal = pyqtSignal()
    set_beyan_signal = pyqtSignal(str)
    refresh_signal = pyqtSignal()
    quit_signal = pyqtSignal()
    
    def listen(self):
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    self.quit_signal.emit()
                    break
                if line.startswith("SET_BEYAN:"):
                    code = line.split("SET_BEYAN:")[1].strip()
                    self.set_beyan_signal.emit(code)
                elif "REFRESH" in line:
                    self.refresh_signal.emit()
                elif "INJECT" in line:
                    self.inject_signal.emit()
                elif "QUIT" in line:
                    self.quit_signal.emit()
                    break
            except:
                self.quit_signal.emit()
                break

class QNBPortalEmbed(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("QNB_PYQT_EMBED_WINDOW")
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Kalıcı Profil & Çerez/Giriş Bilgisi Depolama
        base_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "SmartClearance", "QNB_Profile")
        storage_dir = os.path.join(base_dir, "Storage")
        cache_dir = os.path.join(base_dir, "Cache")
        os.makedirs(storage_dir, exist_ok=True)
        os.makedirs(cache_dir, exist_ok=True)
        
        self.browser = PopupWebEngineView()
        self.profile = QWebEngineProfile("SmartClearance_QNB_Storage", self.browser)
        self.profile.setPersistentStoragePath(storage_dir)
        self.profile.setCachePath(cache_dir)
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies)
        self.page = SilentWebEnginePage(self.profile, self.browser)
        self.browser.setPage(self.page)
        
        # Setup File Downloads
        self.browser.page().profile().downloadRequested.connect(self.on_download_requested)
        
        js_path = os.path.join(os.path.dirname(__file__), "fatura_eslestirici.js")
        self.js_code = ""
        if os.path.exists(js_path):
            with open(js_path, "r", encoding="utf-8") as f:
                self.js_code = f.read()
                
            script = QWebEngineScript()
            script.setName("FaturaEslestirici")
            script.setSourceCode(self.js_code)
            script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentReady)
            script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
            script.setRunsOnSubFrames(False)
            self.page.profile().scripts().insert(script)

        def on_load_finished(ok):
            if ok:
                autofill_js = get_autofill_js()
                if autofill_js:
                    self.browser.page().runJavaScript(autofill_js)
                self.browser.page().runJavaScript("window.__IS_PYQT_EMBED = true;")
                try:
                    app_data = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
                    evrim_path = os.path.join(app_data, "SmartClearance", "evrim_live_data.json")
                    if os.path.exists(evrim_path):
                        with open(evrim_path, "r", encoding="utf-8") as ef:
                            ev_data = json.load(ef)
                            clean_ev = [{"dosya_no": x.get("dosya_no") or x.get("dosya", ""), "bl": x.get("bl", ""), "ref": x.get("hankook_ref") or x.get("ref", ""), "beyan": x.get("beyanname_no", "")} for x in ev_data if isinstance(x, dict)]
                            self.browser.page().runJavaScript(f"window.__ALL_EVRIM_DATA = {json.dumps(clean_ev)};")
                except Exception:
                    pass
                if self.js_code:
                    self.browser.page().runJavaScript(self.js_code)

        def on_title_changed(title):
            if title.startswith("PT_QUEUE_EXPORT:"):
                def on_queue_data(data_json):
                    if data_json:
                        try:
                            app_data = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
                            q_path = os.path.join(app_data, "SmartClearance", "talep_queue.json")
                            os.makedirs(os.path.dirname(q_path), exist_ok=True)
                            with open(q_path, "w", encoding="utf-8") as f:
                                f.write(data_json)
                            print(f"PT_QUEUE_SAVED:{q_path}", flush=True)

                            # Aktivite Günlüğüne kaydet
                            try:
                                from tools.supabase_sync_manager import get_supabase_manager
                                sm = get_supabase_manager()
                                items = json.loads(data_json)
                                if sm and isinstance(items, list):
                                    for itm in items:
                                        d_no = itm.get("dosya_no") or itm.get("dosya", "")
                                        f_no = itm.get("fatura_no") or itm.get("fatura", "")
                                        tutar = itm.get("tutar") or ""
                                        sm.add_activity_log(
                                            dosya_no=d_no,
                                            islem_tipi="FATURA",
                                            baslik=f"Fatura Talep Kuyruğuna Eklendi ({f_no})",
                                            icerik=f"Fatura No: {f_no} | Tutar: {tutar} TL | Para Talep Kuyruğuna Aktarıldı",
                                            etiket="Tamamlandı",
                                            metadata=itm
                                        )
                            except Exception:
                                pass
                        except Exception as e:
                            print(f"ERROR_SAVING_PT_QUEUE:{e}", flush=True)
                self.browser.page().runJavaScript("document.body.getAttribute('data-pt-queue')", on_queue_data)
            elif title.startswith("PDF_MERGE_EXPORT:"):
                def on_pdf_data(data_json):
                    if not data_json:
                        self.browser.page().runJavaScript("if (window.onPdfExportFinished) window.onPdfExportFinished(false);")
                        return
                    try:
                        invoices = json.loads(data_json)
                        if not invoices:
                            self.browser.page().runJavaScript("if (window.onPdfExportFinished) window.onPdfExportFinished(false);")
                            return

                        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M")
                        if len(invoices) == 1:
                            f_no = invoices[0].get("faturaNo", "Belge")
                            default_name = f"Fatura_{f_no}.pdf"
                        else:
                            default_name = f"Hankook_Toplu_Faturalar_{len(invoices)}_Adet_{now_str}.pdf"

                        desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
                        default_path = os.path.join(desktop_dir, default_name)

                        file_path, _ = QFileDialog.getSaveFileName(
                            self, "Tüm Faturaları Tek PDF Olarak Kaydet", default_path, "PDF Dosyaları (*.pdf)"
                        )
                        if not file_path:
                            self.browser.page().runJavaScript("if (window.onPdfExportFinished) window.onPdfExportFinished(false);")
                            return

                        self.current_merger = InvoicePdfMerger(invoices, file_path, self.profile, self)

                        def on_merge_done(out_path, success, err_msg):
                            self.browser.page().runJavaScript("if (window.onPdfExportFinished) window.onPdfExportFinished(true);")
                            if success:
                                QMessageBox.information(
                                    self, "Başarılı",
                                    f"✅ Toplam {len(invoices)} adet fatura başarıyla tek PDF olarak birleştirildi!\n\nDosya Adı: {os.path.basename(out_path)}"
                                )
                                try:
                                    os.startfile(out_path)
                                except Exception:
                                    pass
                            else:
                                QMessageBox.critical(self, "Hata", f"PDF birleştirme hatası:\n{err_msg}")

                        self.current_merger.finished.connect(on_merge_done)
                        self.current_merger.start()
                    except Exception as err:
                        print(f"Error in on_pdf_data: {err}", flush=True)
                        self.browser.page().runJavaScript("if (window.onPdfExportFinished) window.onPdfExportFinished(false);")
                        QMessageBox.critical(self, "Hata", f"PDF verisi işlenirken hata oluştu:\n{err}")

                self.browser.page().runJavaScript("document.body.getAttribute('data-pdf-queue')", on_pdf_data)

        self.browser.titleChanged.connect(on_title_changed)
        self.browser.loadFinished.connect(on_load_finished)
        self.browser.setUrl(QUrl("https://portal.qnbesolutions.com.tr/yonetim/"))
        layout.addWidget(self.browser)
        self.resize(1000, 800)
        
        self.listener = StdinListener()
        self.listener.inject_signal.connect(self.manual_inject)
        self.listener.set_beyan_signal.connect(self.set_beyanname_input)
        self.listener.refresh_signal.connect(self.refresh_page)
        self.listener.quit_signal.connect(QApplication.instance().quit)
        threading.Thread(target=self.listener.listen, daemon=True).start()

    def on_download_requested(self, download_item: QWebEngineDownloadRequest):
        # Save dialog for the user
        default_path = os.path.join(os.path.expanduser("~"), "Downloads", download_item.downloadFileName())
        file_path, _ = QFileDialog.getSaveFileName(self, "Dosyayı Kaydet", default_path)
        if file_path:
            download_item.setDownloadDirectory(os.path.dirname(file_path))
            download_item.setDownloadFileName(os.path.basename(file_path))
            download_item.accept()

    def manual_inject(self):
        # QMessageBox.information(self, "DEBUG", "IPC sinyali alındı! JS enjekte ediliyor...")
        self.browser.page().runJavaScript("window.__IS_PYQT_EMBED = true;")
        if self.js_code:
            self.browser.page().runJavaScript(self.js_code)
        else:
            QMessageBox.critical(self, "HATA", "js_code boş! Dosya okunamadı.")

    def refresh_page(self):
        """QNB eSolutions sayfasını yeniler (F5 / REFRESH komutu)."""
        self.browser.reload()

    def keyPressEvent(self, event):
        """F5 tuşuyla sayfa yenileme desteği."""
        from PyQt6.QtCore import Qt
        if event.key() == Qt.Key.Key_F5:
            self.refresh_page()
        else:
            super().keyPressEvent(event)

    def set_beyanname_input(self, beyan_no):
        self.browser.page().runJavaScript("window.__IS_PYQT_EMBED = true;")
        if self.js_code:
            self.browser.page().runJavaScript(self.js_code)
        
        inject_js = f"""
        (function() {{
            window.__ACTIVE_BEYAN_NO = "{beyan_no}";
            if (typeof window.setKonsimentoList === 'function') {{
                window.setKonsimentoList("{beyan_no}");
            }} else {{
                function trySet() {{
                    let txt = document.getElementById('konsimento-listesi');
                    if (txt) {{
                        txt.value = "{beyan_no}";
                        txt.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        txt.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        txt.style.borderColor = '#16a34a';
                        txt.style.boxShadow = '0 0 10px #16a34a';
                        setTimeout(() => {{
                            txt.style.borderColor = '#c4b5fd';
                            txt.style.boxShadow = 'none';
                        }}, 2500);
                        return true;
                    }}
                    return false;
                }}
                trySet();
                let cnt = 0;
                let iv = setInterval(() => {{
                    cnt++;
                    if (trySet() || cnt > 30) clearInterval(iv);
                }}, 300);
            }}
        }})();
        """
        self.browser.page().runJavaScript(inject_js)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False) # Kapatılan pop-up'ların ana programı kapatmasını engelle
    window = QNBPortalEmbed()
    window.show()
    sys.exit(app.exec())



