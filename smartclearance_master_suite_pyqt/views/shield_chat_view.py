# -*- coding: utf-8 -*-
"""
💬 SmartClearance MasterSuite - Akıllı Konuşma & Mail Gezgini (ShieldChatView PyQt6)
Koyu (Dark Obsidian) Temalı, Canlı Outlook Konuşma Zinciri Gezgini:
- engine.fetch_recent_threads() / search_outlook_conversations() ile gerçek zamanlı tarama
- Asenkron iş parçacığı (ThreadFetchWorker) ile UI donmalarını önleme
- Sol Panel: Konuşma konuları, adım sayıları, son tarih ve gönderen
- Sağ Panel: Kronolojik mesaj baloncukları, ekler havuzu ve tek tıkla Outlook'ta açma
- Hızlı Filtreler: Tümü, Sadece Ekli, Çok Aşamalı (2+ Adım)
"""

import os
import re
from typing import List, Dict, Any, Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTreeWidget, QTreeWidgetItem, QScrollArea,
    QFrame, QSplitter, QMessageBox, QHeaderView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QCursor, QFont

from .base_view import BaseView

try:
    import pythoncom
    HAS_PYTHONCOM = True
except ImportError:
    HAS_PYTHONCOM = False


class ThreadFetchWorker(QThread):
    """Outlook konuşma zincirlerini arka planda tarayan iş parçacığı."""
    threads_loaded = pyqtSignal(list, str)
    error_occurred = pyqtSignal(str)

    def __init__(self, engine, query: str = "", limit: int = 150):
        super().__init__()
        self.engine = engine
        self.query = query
        self.limit = limit

    def run(self):
        if HAS_PYTHONCOM:
            try:
                pythoncom.CoInitialize()
            except Exception:
                pass
        try:
            convs = []
            if self.engine:
                if hasattr(self.engine, "fetch_recent_threads") and not self.query:
                    convs = self.engine.fetch_recent_threads(limit=self.limit)
                elif hasattr(self.engine, "search_outlook_conversations"):
                    convs = self.engine.search_outlook_conversations(query=self.query, limit=self.limit)

            self.threads_loaded.emit(convs or [], self.query)
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            if HAS_PYTHONCOM:
                try:
                    pythoncom.CoUninitialize()
                except Exception:
                    pass


class ShieldChatView(BaseView):
    """Akıllı Güvenlik Kalkanı & Konuşma Gezgini Görünümü (PyQt6 - Dark Obsidian)."""

    def __init__(self, parent=None, main_window=None):
        super().__init__(parent, main_window)
        self.all_threads: List[Dict[str, Any]] = []
        self.filtered_threads: List[Dict[str, Any]] = []
        self.current_conv: Optional[Dict[str, Any]] = None
        self._worker: Optional[ThreadFetchWorker] = None
        self.active_filter = "ALL"
        self._build_ui()

    def on_activate(self):
        """Sekmeye tıklandığında otomatik olarak son konuşmaları tara."""
        if not self.all_threads:
            self.do_search(query="")

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(8)

        # ── 1. ÜST ARAMA VE KONTROL ÇUBUĞU ─────────────────────────────────
        top_bar = QFrame(self)
        top_bar.setStyleSheet("""
            QFrame {
                background-color: #111827;
                border: 1px solid #1e293b;
                border-radius: 8px;
                padding: 6px 12px;
            }
        """)
        tb_layout = QVBoxLayout(top_bar)
        tb_layout.setContentsMargins(8, 6, 8, 6)
        tb_layout.setSpacing(6)

        # Arama Satırı
        search_row = QHBoxLayout()
        search_row.setSpacing(8)

        lbl_icon = QLabel("🔍", top_bar)
        lbl_icon.setStyleSheet("font-size: 14px; border: none;")
        search_row.addWidget(lbl_icon)

        self.txt_search = QLineEdit(top_bar)
        self.txt_search.setPlaceholderText("Konu, firma, dosya no, konşimento veya kişi adı ile ara... (Enter)")
        self.txt_search.setStyleSheet("""
            QLineEdit {
                background-color: #0b0f19;
                border: 1px solid #334155;
                border-radius: 6px;
                color: #f8fafc;
                padding: 7px 12px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #38bdf8;
            }
        """)
        self.txt_search.returnPressed.connect(lambda: self.do_search())
        search_row.addWidget(self.txt_search, stretch=1)

        btn_search = QPushButton("🔍 Konuşmaları Ara", top_bar)
        btn_search.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                border: 1px solid #38bdf8;
                border-radius: 6px;
                color: #ffffff;
                padding: 7px 14px;
                font-weight: 700;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #0369a1;
            }
        """)
        btn_search.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_search.clicked.connect(lambda: self.do_search())
        search_row.addWidget(btn_search)

        btn_recent = QPushButton("⚡ Son Konuşmalar", top_bar)
        btn_recent.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 6px;
                color: #f1f5f9;
                padding: 7px 12px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #334155;
            }
        """)
        btn_recent.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_recent.clicked.connect(lambda: self.do_search(query=""))
        search_row.addWidget(btn_recent)

        tb_layout.addLayout(search_row)

        # Filtre ve Durum Satırı
        filter_row = QHBoxLayout()
        self.lbl_status = QLabel("Hazır. Konuşmaları listelemek için arama yapın veya 'Son Konuşmalar'a basın.", top_bar)
        self.lbl_status.setStyleSheet("font-size: 11px; color: #94a3b8; border: none;")
        filter_row.addWidget(self.lbl_status, stretch=1)

        # Filtre Butonları
        self.btn_f_all = self._make_filter_chip("Tümü", "ALL")
        self.btn_f_att = self._make_filter_chip("📎 Sadece Ekli", "ATTACHMENTS")
        self.btn_f_multi = self._make_filter_chip("🧵 Çok Aşamalı (2+ Adım)", "MULTI_STEP")

        filter_row.addWidget(self.btn_f_all)
        filter_row.addWidget(self.btn_f_att)
        filter_row.addWidget(self.btn_f_multi)
        tb_layout.addLayout(filter_row)

        layout.addWidget(top_bar)

        # ── 2. ANA BÖLÜCÜ: SOL LİSTE & SAĞ SOHBET AKIŞI ─────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #1e293b;
                width: 2px;
            }
        """)

        # SOL: Konuşma Konu Listesi (TreeWidget)
        left_container = QFrame(splitter)
        left_container.setStyleSheet("""
            QFrame {
                background-color: #111827;
                border: 1px solid #1e293b;
                border-radius: 8px;
            }
        """)
        lc_layout = QVBoxLayout(left_container)
        lc_layout.setContentsMargins(6, 8, 6, 8)
        lc_layout.setSpacing(6)

        lbl_lc_title = QLabel("📋 BULUNAN KONUŞMA ZİNCİRLERİ", left_container)
        lbl_lc_title.setStyleSheet("font-size: 11px; font-weight: 800; color: #38bdf8; padding: 4px 6px; border: none;")
        lc_layout.addWidget(lbl_lc_title)

        self.tree_threads = QTreeWidget(left_container)
        self.tree_threads.setHeaderLabels(["Konuşma Konusu", "Adım", "Son Tarih", "Son Gönderen"])
        self.tree_threads.setRootIsDecorated(False)
        self.tree_threads.setSortingEnabled(True)
        self.tree_threads.setStyleSheet("""
            QTreeWidget {
                background-color: #0b0f19;
                border: 1px solid #1e293b;
                border-radius: 6px;
                color: #f8fafc;
                font-size: 11px;
            }
            QTreeWidget::item {
                padding: 8px 4px;
                border-bottom: 1px solid #161f30;
            }
            QTreeWidget::item:selected {
                background-color: #0369a1;
                color: #ffffff;
                font-weight: bold;
            }
            QTreeWidget::item:hover:!selected {
                background-color: #1e293b;
            }
            QHeaderView::section {
                background-color: #111827;
                color: #94a3b8;
                font-weight: 700;
                font-size: 11px;
                padding: 6px;
                border: none;
                border-bottom: 1px solid #1e293b;
            }
        """)
        header = self.tree_threads.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.resizeSection(1, 60)
        header.resizeSection(2, 110)
        header.resizeSection(3, 110)
        self.tree_threads.itemSelectionChanged.connect(self._on_thread_selected)
        lc_layout.addWidget(self.tree_threads)

        splitter.addWidget(left_container)

        # SAĞ: Mesaj Baloncukları & Detay Çerçevesi
        right_container = QFrame(splitter)
        right_container.setStyleSheet("""
            QFrame {
                background-color: #111827;
                border: 1px solid #1e293b;
                border-radius: 8px;
            }
        """)
        rc_layout = QVBoxLayout(right_container)
        rc_layout.setContentsMargins(10, 10, 10, 10)
        rc_layout.setSpacing(8)

        # Konuşma Başlık & Meta Kartı
        self.f_header = QFrame(right_container)
        self.f_header.setStyleSheet("""
            QFrame {
                background-color: #0f172a;
                border: 1px solid #1e293b;
                border-radius: 6px;
                padding: 10px;
            }
        """)
        fh_layout = QVBoxLayout(self.f_header)
        fh_layout.setContentsMargins(8, 6, 8, 6)
        fh_layout.setSpacing(4)

        self.lbl_conv_title = QLabel("Lütfen soldaki listeden bir konuşma zinciri seçin.", self.f_header)
        self.lbl_conv_title.setStyleSheet("font-size: 13px; font-weight: 800; color: #38bdf8; border: none;")
        self.lbl_conv_title.setWordWrap(True)
        fh_layout.addWidget(self.lbl_conv_title)

        self.lbl_conv_meta = QLabel("", self.f_header)
        self.lbl_conv_meta.setStyleSheet("font-size: 11px; color: #94a3b8; border: none;")
        fh_layout.addWidget(self.lbl_conv_meta)

        self.f_att_chips = QWidget(self.f_header)
        self.f_att_chips_layout = QHBoxLayout(self.f_att_chips)
        self.f_att_chips_layout.setContentsMargins(0, 4, 0, 0)
        self.f_att_chips_layout.setSpacing(6)
        fh_layout.addWidget(self.f_att_chips)

        rc_layout.addWidget(self.f_header)

        # Kaydırılabilir Baloncuk Alanı
        self.scroll_bubbles = QScrollArea(right_container)
        self.scroll_bubbles.setWidgetResizable(True)
        self.scroll_bubbles.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_bubbles.setStyleSheet("background: transparent; border: none;")

        self.bubble_content = QWidget()
        self.bubble_content.setStyleSheet("background: transparent;")
        self.bubble_layout = QVBoxLayout(self.bubble_content)
        self.bubble_layout.setContentsMargins(4, 4, 8, 12)
        self.bubble_layout.setSpacing(10)
        self.bubble_layout.addStretch()

        self.scroll_bubbles.setWidget(self.bubble_content)
        rc_layout.addWidget(self.scroll_bubbles, stretch=1)

        splitter.addWidget(right_container)
        splitter.setSizes([460, 640])
        layout.addWidget(splitter, stretch=1)

    def _make_filter_chip(self, text: str, filter_type: str) -> QPushButton:
        btn = QPushButton(text, self)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 4px;
                color: #cbd5e1;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #f8fafc;
            }
        """)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda: self.apply_filter(filter_type))
        return btn

    def apply_filter(self, filter_type: str):
        self.active_filter = filter_type
        if filter_type == "ALL":
            self.filtered_threads = list(self.all_threads)
        elif filter_type == "ATTACHMENTS":
            self.filtered_threads = [c for c in self.all_threads if len(c.get("all_attachments", [])) > 0]
        elif filter_type == "MULTI_STEP":
            self.filtered_threads = [c for c in self.all_threads if c.get("total_steps", 0) >= 2]

        self._populate_tree()
        if self.filtered_threads:
            self.tree_threads.setCurrentItem(self.tree_threads.topLevelItem(0))

    def do_search(self, query: Optional[str] = None):
        """Outlook üzerinden konuşma zincirlerini asenkron tara."""
        if query is None:
            query = self.txt_search.text().strip()

        self.lbl_status.setText(f"⏳ Outlook konuşma zincirleri taranıyor ('{query or 'Son Konuşmalar'}')...")
        self.lbl_status.setStyleSheet("font-size: 11px; color: #f59e0b; border: none;")

        engine = getattr(self.main_window, "engine", None) if self.main_window else None
        self._worker = ThreadFetchWorker(engine=engine, query=query, limit=120)
        self._worker.threads_loaded.connect(self._on_threads_loaded)
        self._worker.error_occurred.connect(self._on_threads_error)
        self._worker.start()

    def _on_threads_loaded(self, threads: list, query: str):
        self.all_threads = threads
        self.filtered_threads = list(threads)
        if not threads:
            self.lbl_status.setText(f"❌ '{query}' aramasıyla eşleşen Outlook konuşması bulunamadı.")
            self.lbl_status.setStyleSheet("font-size: 11px; color: #f87171; border: none;")
        else:
            self.lbl_status.setText(f"✅ Toplam {len(threads)} adet konuşma konusu bulundu.")
            self.lbl_status.setStyleSheet("font-size: 11px; color: #34d399; border: none;")

        self._populate_tree()
        if self.filtered_threads:
            self.tree_threads.setCurrentItem(self.tree_threads.topLevelItem(0))

    def _on_threads_error(self, err_msg: str):
        self.lbl_status.setText(f"❌ Tarama hatası: {err_msg}")
        self.lbl_status.setStyleSheet("font-size: 11px; color: #f87171; border: none;")

    def _populate_tree(self):
        self.tree_threads.clear()
        for idx, conv in enumerate(self.filtered_threads):
            topic = conv.get("topic") or "Konu Yok"
            steps = f"{conv.get('total_steps', 1)} Adım"
            date = conv.get("latest_date") or "—"
            sender = conv.get("latest_sender") or "—"

            item = QTreeWidgetItem([topic, steps, date, sender])
            item.setData(0, Qt.ItemDataRole.UserRole, idx)
            self.tree_threads.addTopLevelItem(item)

    def _on_thread_selected(self):
        items = self.tree_threads.selectedItems()
        if not items:
            return
        idx = items[0].data(0, Qt.ItemDataRole.UserRole)
        if 0 <= idx < len(self.filtered_threads):
            self.current_conv = self.filtered_threads[idx]
            self.render_conversation(self.current_conv)

    def render_conversation(self, conv: Dict[str, Any]):
        """Seçilen konuşma zincirini sağ panelde kronolojik mesaj baloncukları olarak çizer."""
        topic = conv.get("topic") or "Konuşma"
        self.lbl_conv_title.setText(f"💬 {topic}")

        messages = conv.get("messages", [])
        all_senders = list(set([m.get("sender", "—") for m in messages if m.get("sender")]))
        senders_str = ", ".join(all_senders[:3]) + (f" (+{len(all_senders)-3} kişi)" if len(all_senders) > 3 else "")
        self.lbl_conv_meta.setText(
            f"📊 Toplam {len(messages)} Adım  |  👥 Katılımcılar: {senders_str}  |  📅 Son Tarih: {conv.get('latest_date', '—')}"
        )

        # Ekler Havuzu
        while self.f_att_chips_layout.count():
            item = self.f_att_chips_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        all_atts = conv.get("all_attachments", [])
        if all_atts:
            lbl_att = QLabel(f"📎 Ekler ({len(all_atts)}):", self.f_att_chips)
            lbl_att.setStyleSheet("font-size: 11px; font-weight: 700; color: #cbd5e1; border: none;")
            self.f_att_chips_layout.addWidget(lbl_att)

            for a_name in all_atts[:4]:
                chip = QPushButton(f"📄 {a_name[:24]}", self.f_att_chips)
                chip.setStyleSheet("""
                    QPushButton {
                        background-color: #0369a1;
                        border: 1px solid #38bdf8;
                        border-radius: 4px;
                        color: #ffffff;
                        padding: 2px 8px;
                        font-size: 10px;
                        font-weight: 600;
                    }
                    QPushButton:hover {
                        background-color: #0284c7;
                    }
                """)
                chip.setCursor(Qt.CursorShape.PointingHandCursor)
                chip.clicked.connect(lambda _, a=a_name: self.copy_to_clipboard(a))
                self.f_att_chips_layout.addWidget(chip)
            self.f_att_chips_layout.addStretch()

        # Baloncukları temizle
        while self.bubble_layout.count():
            item = self.bubble_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Adım adım mesaj baloncukları
        for m in messages:
            step_num = m.get("step", 1)
            is_out = m.get("direction") == "OUT"

            card = QFrame(self.bubble_content)
            border_color = "#059669" if is_out else "#0284c7"
            bg_color = "#06281e" if is_out else "#0b1e36"
            header_bg = "#093d2e" if is_out else "#0e2b4d"

            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {bg_color};
                    border: 1px solid {border_color};
                    border-radius: 8px;
                    padding: 8px;
                }}
            """)
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(6, 6, 6, 6)
            c_layout.setSpacing(6)

            # Üst Bilgi Satırı
            head_frame = QFrame(card)
            head_frame.setStyleSheet(f"background-color: {header_bg}; border: none; border-radius: 4px; padding: 4px 8px;")
            h_row = QHBoxLayout(head_frame)
            h_row.setContentsMargins(4, 2, 4, 2)

            dir_text = "📤 [GİDEN - BİZ]" if is_out else "📥 [GELEN - YANIT]"
            dir_color = "#34d399" if is_out else "#38bdf8"
            lbl_step = QLabel(f"Adım {step_num}: {dir_text}  {m.get('sender', '—')} ➡️ {m.get('to', '—')[:32]}", head_frame)
            lbl_step.setStyleSheet(f"font-size: 11px; font-weight: 800; color: {dir_color}; border: none;")
            h_row.addWidget(lbl_step, stretch=1)

            lbl_time = QLabel(f"📅 {m.get('time_str', '—')}", head_frame)
            lbl_time.setStyleSheet("font-size: 11px; color: #94a3b8; border: none;")
            h_row.addWidget(lbl_time)

            eid = m.get("entry_id")
            if eid:
                btn_open = QPushButton("✉️ Outlook'ta Aç", head_frame)
                btn_open.setStyleSheet("""
                    QPushButton {
                        background-color: #1e293b;
                        border: 1px solid #475569;
                        border-radius: 4px;
                        color: #f1f5f9;
                        padding: 3px 8px;
                        font-size: 10px;
                        font-weight: 700;
                    }
                    QPushButton:hover {
                        background-color: #334155;
                        color: #38bdf8;
                    }
                """)
                btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_open.clicked.connect(lambda _, entry_id=eid: self.open_mail_in_outlook(entry_id))
                h_row.addWidget(btn_open)

            c_layout.addWidget(head_frame)

            # Konu Satırı
            lbl_subj = QLabel(f"Konu: {m.get('subject', '—')}", card)
            lbl_subj.setStyleSheet("font-size: 11px; font-weight: 700; color: #e2e8f0; border: none;")
            lbl_subj.setWordWrap(True)
            c_layout.addWidget(lbl_subj)

            # Mesaj Gövdesi / Snippet
            snippet_box = QLabel(m.get("snippet") or "(Metin içeriği yok)", card)
            snippet_box.setStyleSheet("""
                background-color: #0b0f19;
                border: 1px solid #1e293b;
                border-radius: 4px;
                color: #cbd5e1;
                padding: 8px 10px;
                font-size: 11px;
                line-height: 1.4;
            """)
            snippet_box.setWordWrap(True)
            c_layout.addWidget(snippet_box)

            # Ekler Satırı
            m_atts = m.get("attachments", [])
            if m_atts:
                att_row = QHBoxLayout()
                att_row.setSpacing(4)
                lbl_att_icon = QLabel("📎 Ekler:", card)
                lbl_att_icon.setStyleSheet("font-size: 10px; font-weight: 700; color: #94a3b8; border: none;")
                att_row.addWidget(lbl_att_icon)

                for a_name in m_atts:
                    a_chip = QPushButton(f"📄 {a_name}", card)
                    a_chip.setStyleSheet("""
                        QPushButton {
                            background-color: #1e293b;
                            border: 1px solid #334155;
                            border-radius: 4px;
                            color: #38bdf8;
                            padding: 2px 6px;
                            font-size: 10px;
                        }
                        QPushButton:hover {
                            background-color: #334155;
                        }
                    """)
                    a_chip.setCursor(Qt.CursorShape.PointingHandCursor)
                    a_chip.clicked.connect(lambda _, a=a_name: self.copy_to_clipboard(a))
                    att_row.addWidget(a_chip)
                att_row.addStretch()
                c_layout.addLayout(att_row)

            self.bubble_layout.addWidget(card)

        self.bubble_layout.addStretch()

    def open_mail_in_outlook(self, entry_id: str):
        """Outlook COM API üzerinden e-postayı açar."""
        if not entry_id:
            self.show_warning("Uyarı", "Geçerli bir EntryID bulunamadı.")
            return

        engine = getattr(self.main_window, "engine", None) if self.main_window else None
        try:
            from tools.dogruer_master_suite.outlook_memory_guard import safe_open_mail_by_entry_id
            ok = safe_open_mail_by_entry_id(entry_id)
            if not ok and engine and hasattr(engine, "open_outlook_mail_by_id"):
                ok = engine.open_outlook_mail_by_id(entry_id)

            if not ok:
                self.show_warning("Outlook Uyarısı", "Mail açılamadı. Outlook uygulamasının açık olduğundan emin olun.")
        except Exception as e:
            self.show_error("Hata", f"Mail açılırken hata: {e}")

