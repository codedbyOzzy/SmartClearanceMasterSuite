/**
 * ============================================================================
 * SMARTCLEARANCE AI 2.0 - GLOBAL FLOATING & DRAGGABLE COPILOT WIDGET
 * ============================================================================
 * Her ekranda sağ alt köşede (veya kullanıcının sürüklediği yerde) yaşayan,
 * Alt+A kısayolu ile açılıp gizlenebilen, şık ve akıcı AI Canlı Destek Modülü.
 */
(function () {
  "use strict";

  let fab, drawer, bodyEl, inputEl, sendBtn, closeBtn, clearBtn;
  let isDragging = false;
  let dragStartX = 0, dragStartY = 0;
  let initialLeft = 0, initialTop = 0;
  let didMove = false;

  // 1. DOM Kurulumu & Bileşenlerin Entegrasyonu
  function initAiWidget() {
    if (document.getElementById("sc-ai-fab")) return;

    // A. FAB (Yüzen Buton)
    fab = document.createElement("div");
    fab.id = "sc-ai-fab";
    fab.title = "SMART — Gümrük Asistanı (Sürükleyebilirsiniz | Alt+A)";
    fab.innerHTML = `
      <div class="sc-ai-fab-icon">🤖</div>
      <div class="sc-ai-fab-label">
        <span class="sc-ai-fab-title">SMART <span class="sc-ai-fab-kbd">Alt+A</span></span>
        <span class="sc-ai-fab-sub">Gümrük Asistanı</span>
      </div>
    `;
    document.body.appendChild(fab);

    // B. DRAWER (Açılır Pencere)
    drawer = document.createElement("div");
    drawer.id = "sc-ai-drawer";
    drawer.innerHTML = `
      <div class="sc-ai-drawer-header" id="sc-ai-drawer-header">
        <div class="sc-ai-header-left">
          <div class="sc-ai-header-icon">🤖</div>
          <div class="sc-ai-header-info">
            <span class="sc-ai-header-title">SMART</span>
            <span class="sc-ai-header-status">Gümrük Asistanı • Çevrimiçi</span>
          </div>
        </div>
        <div class="sc-ai-header-actions">
          <button class="sc-ai-hdr-btn" id="sc-ai-hdr-clear" title="Sohbeti Temizle">🗑️</button>
          <button class="sc-ai-hdr-btn" id="sc-ai-hdr-close" title="Kapat (ESC)">✕</button>
        </div>
      </div>
      <div class="sc-ai-drawer-body" id="sc-ai-drawer-body"></div>
      <div class="sc-ai-drawer-footer">
        <div class="sc-ai-chips-panel">
          <div class="sc-ai-chips-cats" id="sc-ai-chips-cats">
            <button class="sc-ai-cat-btn is-active" data-cat="all">Tümü</button>
            <button class="sc-ai-cat-btn" data-cat="sorgula">🔍 Sorgula</button>
            <button class="sc-ai-cat-btn" data-cat="islem">⚡ İşlem</button>
            <button class="sc-ai-cat-btn" data-cat="rapor">📊 Rapor</button>
            <button class="sc-ai-cat-btn" data-cat="gtb">🏢 GTB</button>
          </div>
          <div class="sc-ai-chips-scroll-wrap">
            <div class="sc-ai-chips-scroll" id="sc-ai-chips-scroll">
              <span class="sc-ai-chip" data-cmd="/darbogaz" data-cat="rapor"><span class="sc-ai-chip-icon">⚠️</span>Darboğaz Tara</span>
              <span class="sc-ai-chip" data-cmd="/ozet" data-cat="rapor"><span class="sc-ai-chip-icon">📋</span>Günlük Özet</span>
              <span class="sc-ai-chip" data-cmd="işler nasıl gidiyor" data-cat="rapor"><span class="sc-ai-chip-icon">📈</span>Genel Durum</span>
              <span class="sc-ai-chip" data-cmd="kırmızı hattaki dosyalar" data-cat="sorgula"><span class="sc-ai-chip-icon">🔴</span>Kırmızı Hat</span>
              <span class="sc-ai-chip" data-cmd="açık talepler" data-cat="sorgula"><span class="sc-ai-chip-icon">📝</span>Açık Talepler</span>
              <span class="sc-ai-chip" data-cmd="akşam kapanış brifing" data-cat="rapor"><span class="sc-ai-chip-icon">🌙</span>Kapanış Brifingi</span>
              <span class="sc-ai-chip" data-cmd="talep aç" data-cat="islem"><span class="sc-ai-chip-icon">📋</span>Talep Aç</span>
              <span class="sc-ai-chip" data-cmd="muhasebeye bildir" data-cat="islem"><span class="sc-ai-chip-icon">💰</span>Muhasebe Bildir</span>
              <span class="sc-ai-chip" data-cmd="excel raporu indir" data-cat="islem"><span class="sc-ai-chip-icon">📥</span>Excel İndir</span>
              <span class="sc-ai-chip" data-cmd="takipteki beyannameler" data-cat="gtb"><span class="sc-ai-chip-icon">📊</span>Aktif Takip</span>
              <span class="sc-ai-chip" data-cmd="beyanname takibe al" data-cat="gtb"><span class="sc-ai-chip-icon">➕</span>Takibe Ekle</span>
              <span class="sc-ai-chip" data-cmd="/yardim" data-cat="all"><span class="sc-ai-chip-icon">❓</span>Ne Yapabilirsin?</span>
            </div>
          </div>
        </div>
        <div class="sc-ai-input-row">
          <input type="text" id="sc-ai-input" class="sc-ai-input" placeholder="SMART'a bir şey sor... (Enter ↵)" autocomplete="off" />
          <button class="sc-ai-send-btn" id="sc-ai-send-btn">Gönder 🚀</button>
        </div>
      </div>
    `;
    document.body.appendChild(drawer);

    // Referanslar
    bodyEl = document.getElementById("sc-ai-drawer-body");
    inputEl = document.getElementById("sc-ai-input");
    sendBtn = document.getElementById("sc-ai-send-btn");
    closeBtn = document.getElementById("sc-ai-hdr-close");
    clearBtn = document.getElementById("sc-ai-hdr-clear");

    // Konum Geri Yükleme (localStorage)
    restorePosition();

    // Gizli mi kontrolü
    const isHidden = localStorage.getItem("sc_ai_widget_hidden") === "true";
    if (isHidden) {
      fab.style.display = "none";
    }

    // Olay Dinleyicileri (Event Listeners)
    bindEvents();
    // İlk mesaj geçmişini çek
    fetchHistory();
  }

  // 2. Konum Saklama & Geri Yükleme
  function restorePosition() {
    try {
      const pos = JSON.parse(localStorage.getItem("sc_ai_widget_pos"));
      if (pos && typeof pos.left === "number" && typeof pos.top === "number") {
        // Ekran dışına taşmayı engelle
        const maxLeft = window.innerWidth - 180;
        const maxTop = window.innerHeight - 60;
        const left = Math.max(10, Math.min(pos.left, maxLeft));
        const top = Math.max(10, Math.min(pos.top, maxTop));
        fab.style.left = left + "px";
        fab.style.top = top + "px";
        fab.style.right = "auto";
        fab.style.bottom = "auto";
        updateDrawerPosition(left, top);
      }
    } catch (e) {}
  }

  function savePosition(left, top) {
    try {
      localStorage.setItem("sc_ai_widget_pos", JSON.stringify({ left, top }));
    } catch (e) {}
  }

  function updateDrawerPosition(fabLeft, fabTop) {
    if (!drawer) return;
    const w = window.innerWidth;
    const h = window.innerHeight;
    const drawerW = 410;
    const drawerH = 560;

    let left = fabLeft - drawerW + 160;
    let top = fabTop - drawerH - 14;

    if (left + drawerW > w - 16) left = w - drawerW - 16;
    if (left < 16) left = 16;
    if (top < 16) top = fabTop + 54;
    if (top + drawerH > h - 16) top = h - drawerH - 16;

    drawer.style.left = left + "px";
    drawer.style.top = top + "px";
    drawer.style.right = "auto";
    drawer.style.bottom = "auto";
  }

  // 3. Sürükleme (Drag & Drop) Mekanizması
  function bindEvents() {
    // Fare & Dokunmatik Başlama
    fab.addEventListener("mousedown", onDragStart);
    fab.addEventListener("touchstart", onDragStart, { passive: false });

    // FAB Tıklama (Drawer Açma)
    fab.addEventListener("click", function (e) {
      if (didMove) {
        didMove = false;
        return;
      }
      toggleDrawer();
    });

    // Kapatma & Temizleme
    closeBtn.addEventListener("click", () => setDrawerOpen(false));
    clearBtn.addEventListener("click", clearHistory);

    // Kısayol Tuşları (Alt+A veya Ctrl+Shift+A ile Toggle, ESC ile kapat)
    window.addEventListener("keydown", function (e) {
      if ((e.altKey && (e.key === "a" || e.key === "A" || e.code === "KeyA")) ||
          (e.ctrlKey && e.shiftKey && (e.key === "a" || e.key === "A" || e.code === "KeyA"))) {
        e.preventDefault();
        toggleWidgetComplete();
      } else if (e.key === "Escape" && drawer.classList.contains("is-open")) {
        setDrawerOpen(false);
      }
    });

    // Mesaj Gönderme
    sendBtn.addEventListener("click", sendMessage);
    inputEl.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });

    // Hızlı Çip Butonları — Kategori Filtresi + Yatay Scroll
    const chipsScroll = document.getElementById("sc-ai-chips-scroll");
    const catBtns = document.querySelectorAll(".sc-ai-cat-btn");
    const allChips = drawer.querySelectorAll(".sc-ai-chip");

    // Kategori seçimi
    catBtns.forEach((btn) => {
      btn.addEventListener("click", function () {
        catBtns.forEach((b) => b.classList.remove("is-active"));
        this.classList.add("is-active");
        const cat = this.getAttribute("data-cat");
        allChips.forEach((chip) => {
          const chipCat = chip.getAttribute("data-cat");
          chip.style.display = (cat === "all" || chipCat === cat || chipCat === "all") ? "" : "none";
        });
        if (chipsScroll) chipsScroll.scrollLeft = 0;
      });
    });

    // Chip tıklama → komut gönder
    allChips.forEach((chip) => {
      chip.addEventListener("click", function () {
        const cmd = this.getAttribute("data-cmd");
        if (cmd) {
          inputEl.value = cmd;
          sendMessage();
        }
      });
    });

    // Yatay fare tekerleği scroll desteği
    if (chipsScroll) {
      chipsScroll.addEventListener("wheel", function (e) {
        if (Math.abs(e.deltaY) > 0) {
          e.preventDefault();
          this.scrollLeft += e.deltaY;
        }
      }, { passive: false });

      // Sürükleyerek scroll (grab-to-drag)
      let isChipDrag = false, chipDragX = 0, chipScrollStart = 0;
      chipsScroll.addEventListener("mousedown", function (e) {
        isChipDrag = true;
        chipDragX = e.pageX;
        chipScrollStart = this.scrollLeft;
        this.style.cursor = "grabbing";
        this.style.userSelect = "none";
      });
      document.addEventListener("mousemove", function (e) {
        if (!isChipDrag) return;
        const dx = e.pageX - chipDragX;
        chipsScroll.scrollLeft = chipScrollStart - dx;
      });
      document.addEventListener("mouseup", function () {
        if (isChipDrag) {
          isChipDrag = false;
          chipsScroll.style.cursor = "grab";
          chipsScroll.style.userSelect = "";
        }
      });
    }
  }

  function onDragStart(e) {
    if (e.target.closest(".sc-ai-fab-kbd")) return;
    isDragging = true;
    didMove = false;

    const evt = e.touches ? e.touches[0] : e;
    dragStartX = evt.clientX;
    dragStartY = evt.clientY;

    const rect = fab.getBoundingClientRect();
    initialLeft = rect.left;
    initialTop = rect.top;

    fab.classList.add("is-dragging");

    document.addEventListener("mousemove", onDragMove);
    document.addEventListener("mouseup", onDragEnd);
    document.addEventListener("touchmove", onDragMove, { passive: false });
    document.addEventListener("touchend", onDragEnd);
  }

  function onDragMove(e) {
    if (!isDragging) return;
    const evt = e.touches ? e.touches[0] : e;
    const dx = evt.clientX - dragStartX;
    const dy = evt.clientY - dragStartY;

    if (Math.abs(dx) > 4 || Math.abs(dy) > 4) {
      didMove = true;
    }

    let left = initialLeft + dx;
    let top = initialTop + dy;

    // Ekran sınırlarında tut
    const maxLeft = window.innerWidth - fab.offsetWidth - 10;
    const maxTop = window.innerHeight - fab.offsetHeight - 10;
    left = Math.max(10, Math.min(left, maxLeft));
    top = Math.max(10, Math.min(top, maxTop));

    fab.style.left = left + "px";
    fab.style.top = top + "px";
    fab.style.right = "auto";
    fab.style.bottom = "auto";

    updateDrawerPosition(left, top);
  }

  function onDragEnd() {
    if (!isDragging) return;
    isDragging = false;
    fab.classList.remove("is-dragging");

    document.removeEventListener("mousemove", onDragMove);
    document.removeEventListener("mouseup", onDragEnd);
    document.removeEventListener("touchmove", onDragMove);
    document.removeEventListener("touchend", onDragEnd);

    if (didMove) {
      const rect = fab.getBoundingClientRect();
      savePosition(rect.left, rect.top);
    }
  }

  // 4. Pencere Aç / Kapat & Tamamen Gizle (Alt+A)
  function toggleDrawer() {
    const open = !drawer.classList.contains("is-open");
    setDrawerOpen(open);
  }

  function setDrawerOpen(open) {
    if (open) {
      const rect = fab.getBoundingClientRect();
      updateDrawerPosition(rect.left, rect.top);
      drawer.classList.add("is-open");
      setTimeout(() => inputEl.focus(), 150);
      scrollToBottom();
    } else {
      drawer.classList.remove("is-open");
    }
  }

  function toggleWidgetComplete() {
    const isHidden = fab.style.display === "none";
    if (isHidden) {
      fab.style.display = "flex";
      localStorage.setItem("sc_ai_widget_hidden", "false");
      setDrawerOpen(true);
    } else {
      setDrawerOpen(false);
      fab.style.display = "none";
      localStorage.setItem("sc_ai_widget_hidden", "true");
    }
  }

  // 5. Sunucu Haberleşmesi & Mesaj Render
  function fetchHistory() {
    fetch("/ekip-akisi/api/ai-widget/gecmis")
      .then((res) => res.json())
      .then((data) => {
        if (data && data.success) {
          renderMessages(data.mesajlar || []);
        }
      })
      .catch((e) => console.error("AI Widget geçmiş yüklenemedi:", e));
  }

  function clearHistory() {
    if (!confirm("AI Canlı Destek sohbet geçmişi temizlensin mi?")) return;
    fetch("/ekip-akisi/api/ai-widget/temizle", { method: "POST" })
      .then((res) => res.json())
      .then((data) => {
        if (data && data.success) {
          renderMessages(data.mesajlar || []);
        }
      })
      .catch((e) => console.error("AI Widget temizleme hatası:", e));
  }

  function sendMessage() {
    const soru = inputEl.value.trim();
    if (!soru) return;

    inputEl.value = "";
    // Geçici kullanıcı mesajı balonu ekle
    appendBubble("user", "Siz", soru);
    scrollToBottom();

    fetch("/ekip-akisi/api/ai-widget/sor", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ soru }),
    })
      .then((res) => res.json())
      .then((data) => {
        if (data && data.success) {
          renderMessages(data.mesajlar || []);
        } else {
          appendBubble("bot", "🤖 SmartClearance AI", "❌ Yanıt alınırken bir hata oluştu: " + (data.hata || "Bilinmeyen hata"));
        }
      })
      .catch((e) => {
        appendBubble("bot", "🤖 SmartClearance AI", "❌ Sunucu ile bağlantı kurulamadı.");
      })
      .finally(() => {
        scrollToBottom();
      });
  }

  function renderMessages(mesajlar) {
    bodyEl.innerHTML = "";
    mesajlar.forEach((m) => {
      const isUser = m.yazan !== "🤖 SmartClearance AI" && !m.yazan.includes("🤖");
      appendBubble(isUser ? "user" : "bot", m.yazan || "Asistan", m.metin || "");
    });
    scrollToBottom();
  }

  function appendBubble(role, sender, text) {
    const el = document.createElement("div");
    el.className = `sc-ai-msg is-${role}`;

    // AI mesajları backend'den HTML olarak gelir, User mesajları ise düz metindir (escape edilir).
    const contentHtml = (role === "bot" || role === "ai") ? (window.zenginMesajBicimle ? window.zenginMesajBicimle(text) : text) : escapeHtml(text);

    el.innerHTML = `
      <div class="sc-ai-msg-header">
        <span style="font-weight:700;">${sender}</span>
      </div>
      <div class="sc-ai-msg-bubble">${contentHtml}</div>
    `;
    bodyEl.appendChild(el);
  }

  function escapeHtml(s) {
    return (s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function scrollToBottom() {
    setTimeout(() => {
      bodyEl.scrollTop = bodyEl.scrollHeight;
    }, 50);
  }

  // Başlat
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAiWidget);
  } else {
    initAiWidget();
  }
})();
