// spotlight.js — SmartClearance Ctrl + K (Command Palette & Hızlı Işınlanma Merkezi)
// Klavyeden Ctrl+K veya Cmd+K basıldığında camsı bir komut paneli açar.
// Hem hızlı sistem komutlarını çalıştırır hem de canlı olarak /arama/canli üzerinden dosyaları getirir.

(function() {
  const SC_SPOTLIGHT_COMMANDS = [
    { id: 'perf', tur: 'komut', baslik: '◈ Performans Paneli', alt: 'Anlık gümrük ve ekip KPI özetine git', url: '/performans', ic: '◈' },
    { id: 'muh', tur: 'komut', baslik: '₺ Muhasebe Takip', alt: 'Referans ve fatura eşleştirme paneline git', url: '/muhasebe-takip', ic: '₺' },
    { id: 'hizli', tur: 'komut', baslik: '⚡ Hızlı İşlem Merkezi', alt: 'Beyanname kontrol ve aktarım merkezi', url: '/hizli-islem', ic: '⚡' },
    { id: 'takip', tur: 'komut', baslik: '📋 İş Takip Raporu', alt: 'Tüm açık ve kapanan referans dosyaları', url: '/takip-raporu', ic: '📋' },
    { id: 'excel', tur: 'komut', baslik: '📊 Excel Aktarım', alt: 'Gümrük verisi aktarım paneli', url: '/excel-aktarim', ic: '📊' },
    { id: 'beyanname', tur: 'komut', baslik: '📁 Beyanname Kontrol', alt: 'Beyanname XML kontrol ve analizi', url: '/beyanname', ic: '📁' },
    { id: 'master', tur: 'komut', baslik: '📦 Master Data Kontrol', alt: 'Katalog ve referans veri kontrolü', url: '/master-kontrol', ic: '📦' },
    { id: 'tema', tur: 'komut', baslik: '🌙 Gece / Gündüz Modu Değiştir', alt: 'Sistem temasını anında değiştir', action: 'toggle-theme', ic: '🌙' },
    { id: 'muh-excel', tur: 'komut', baslik: '⬇ Muhasebe Excel İndir', alt: 'Muhasebe tablosunu Excel olarak indir', url: '/muhasebe-takip/excel', ic: '⬇' },
    { id: 'home', tur: 'komut', baslik: '🏠 Ana Sayfaya Dön', alt: 'Kontrol üssü ana sayfasına git', url: '/', ic: '🏠' }
  ];

  let selectedIndex = 0;
  let currentItems = [];
  let fetchTimer = null;

  function initSpotlight() {
    const backdrop = document.getElementById('sc-spotlight-backdrop');
    const input = document.getElementById('sc-spotlight-input');
    const resultsContainer = document.getElementById('sc-spotlight-results');
    if (!backdrop || !input || !resultsContainer) return;

    // Ctrl+K veya Cmd+K ile açma / ESC ile kapatma
    window.addEventListener('keydown', function(e) {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        toggleSpotlight(true);
      } else if (e.key === 'Escape' && backdrop.style.display === 'flex') {
        toggleSpotlight(false);
      }
    });

    // Kenara tıklayınca kapat
    backdrop.addEventListener('click', function(e) {
      if (e.target === backdrop) {
        toggleSpotlight(false);
      }
    });

    // Sol menüdeki hızlı açma butonunu bağla (varsa)
    const hintBtn = document.getElementById('open-spotlight-btn');
    if (hintBtn) {
      hintBtn.addEventListener('click', function(e) {
        e.preventDefault();
        toggleSpotlight(true);
      });
    }

    // Daraltılmış modda arama ikonuna basınca da Spotlight aç
    const sidebarSearch = document.querySelector('.sidebar-search');
    if (sidebarSearch) {
      sidebarSearch.addEventListener('click', function(e) {
        if (document.documentElement.classList.contains('sidebar-collapsed')) {
          e.preventDefault();
          toggleSpotlight(true);
        }
      });
    }

    // Inputta tuşla yönlendirme
    input.addEventListener('keydown', function(e) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        selectedIndex = (selectedIndex + 1) % Math.max(1, currentItems.length);
        renderSelection();
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        selectedIndex = (selectedIndex - 1 + Math.max(1, currentItems.length)) % Math.max(1, currentItems.length);
        renderSelection();
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (currentItems[selectedIndex]) {
          executeItem(currentItems[selectedIndex]);
        }
      }
    });

    // Yazarken anlık filtreleme ve canlı dosya arama
    input.addEventListener('input', function() {
      const q = input.value.trim();
      selectedIndex = 0;

      // Yerel komutlar içinde ara
      const matchedCommands = SC_SPOTLIGHT_COMMANDS.filter(cmd => {
        const t = (cmd.baslik + " " + cmd.alt).toLowerCase();
        return t.includes(q.toLowerCase());
      });

      if (q.length < 2) {
        currentItems = matchedCommands;
        renderList(currentItems);
        return;
      }

      // 2+ karakterde /arama/canli'dan dosya getir
      clearTimeout(fetchTimer);
      fetchTimer = setTimeout(() => {
        fetch('/arama/canli?q=' + encodeURIComponent(q))
          .then(r => r.json())
          .then(data => {
            const liveItems = (data.sonuclar || []).map(item => ({
              id: item.url,
              tur: item.tur === 'takip' ? 'dosya' : 'talep',
              baslik: (item.tur === 'takip' ? '🗂 Dosya: ' : '📨 ') + item.baslik,
              alt: item.alt,
              url: item.url,
              ic: item.tur === 'takip' ? '🗂' : '📨'
            }));
            currentItems = [...liveItems, ...matchedCommands];
            renderList(currentItems);
          })
          .catch(() => {
            currentItems = matchedCommands;
            renderList(currentItems);
          });
      }, 140);
    });
  }

  function toggleSpotlight(open) {
    const backdrop = document.getElementById('sc-spotlight-backdrop');
    const input = document.getElementById('sc-spotlight-input');
    if (!backdrop || !input) return;

    if (open) {
      backdrop.style.display = 'flex';
      input.value = '';
      currentItems = [...SC_SPOTLIGHT_COMMANDS];
      selectedIndex = 0;
      renderList(currentItems);
      setTimeout(() => input.focus(), 10);
    } else {
      backdrop.style.display = 'none';
    }
  }

  function renderList(items) {
    const container = document.getElementById('sc-spotlight-results');
    if (!container) return;

    if (items.length === 0) {
      container.innerHTML = '<div class="sc-spotlight-empty">Sonuç bulunamadı...</div>';
      return;
    }

    let html = '';
    items.forEach((item, index) => {
      const isSel = index === selectedIndex ? ' selected' : '';
      const badge = item.tur === 'komut' ? '<span class="sp-badge sp-badge-cmd">Komut</span>' :
                    item.tur === 'dosya' ? '<span class="sp-badge sp-badge-file">Dosya</span>' :
                    '<span class="sp-badge sp-badge-req">Talep</span>';
      html += `
        <div class="sc-spotlight-item${isSel}" data-index="${index}">
          <div class="sp-icon">${item.ic}</div>
          <div class="sp-text">
            <div class="sp-title">${item.baslik}</div>
            <div class="sp-alt">${item.alt}</div>
          </div>
          <div class="sp-meta">${badge}</div>
        </div>
      `;
    });
    container.innerHTML = html;

    // Tıklama ile seçme
    container.querySelectorAll('.sc-spotlight-item').forEach(el => {
      el.addEventListener('click', function() {
        const idx = parseInt(el.getAttribute('data-index'), 10);
        if (currentItems[idx]) {
          executeItem(currentItems[idx]);
        }
      });
    });

    renderSelection();
  }

  function renderSelection() {
    const container = document.getElementById('sc-spotlight-results');
    if (!container) return;
    const items = container.querySelectorAll('.sc-spotlight-item');
    items.forEach((el, index) => {
      if (index === selectedIndex) {
        el.classList.add('selected');
        el.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      } else {
        el.classList.remove('selected');
      }
    });
  }

  function executeItem(item) {
    toggleSpotlight(false);
    if (item.action === 'toggle-theme') {
      const current = localStorage.getItem("sc_tema") === "dark";
      if (typeof scTemaUygula === "function") {
        scTemaUygula(!current);
      }
    } else if (item.url) {
      window.location.href = item.url;
    }
  }

  // Sayfa yüklendiğinde başlat
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSpotlight);
  } else {
    initSpotlight();
  }
})();
