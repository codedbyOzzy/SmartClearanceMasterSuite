/**
 * breadcrumb.js — SmartClearance Akıllı Ekmek Kırıntısı & Hızlı Zıplama Menüsü
 * Sayfaların üst başlığına otomatik breadcrumb çubuğu ve PO numaraları için bağlam (context) menüsü katar.
 */

(function() {
  function createBreadcrumbStyle() {
    if (document.getElementById('sc-breadcrumb-style')) return;
    const style = document.createElement('style');
    style.id = 'sc-breadcrumb-style';
    style.textContent = `
      .sc-breadcrumb-bar {
        display: flex; align-items: center; gap: 0.5rem;
        padding: 0.5rem 0; margin-bottom: 0.8rem;
        font-size: 0.82rem; font-weight: 600; color: #6B7686;
        border-bottom: 1px solid rgba(0,0,0,0.06);
      }
      html.dark-mode .sc-breadcrumb-bar {
        color: #A8B4C4; border-bottom-color: rgba(255,255,255,0.06);
      }
      .sc-breadcrumb-item {
        display: flex; align-items: center; gap: 0.35rem;
        color: inherit; text-decoration: none; transition: color 0.15s;
      }
      .sc-breadcrumb-item:hover { color: #3A7BD5; }
      .sc-breadcrumb-sep { color: #D1D5DB; font-size: 0.75rem; }
      html.dark-mode .sc-breadcrumb-sep { color: #4A5568; }
      .sc-breadcrumb-current {
        color: #0F1A2E; font-weight: 700;
        display: flex; align-items: center; gap: 4px;
        position: relative;
      }
      html.dark-mode .sc-breadcrumb-current { color: #EEF2F8; }
      .sc-breadcrumb-dropdown-btn {
        background: rgba(58,123,213,0.12); color: #3A7BD5; border: none;
        border-radius: 4px; padding: 1px 6px; font-size: 0.75rem;
        cursor: pointer; font-weight: 700; display: inline-flex;
        align-items: center; gap: 2px;
      }
      .sc-breadcrumb-dropdown-btn:hover { background: rgba(58,123,213,0.25); }
      
      .sc-breadcrumb-menu {
        position: absolute; top: 100%; left: 0; margin-top: 6px;
        background: #FFFFFF; border: 1px solid #E3E6EB;
        border-radius: 8px; box-shadow: 0 10px 25px rgba(15,26,46,0.15);
        min-width: 230px; z-index: 1020; display: none;
        flex-direction: column; padding: 0.4rem 0;
      }
      html.dark-mode .sc-breadcrumb-menu {
        background: #17243B; border-color: #1E2E4A;
        box-shadow: 0 10px 25px rgba(0,0,0,0.45);
      }
      .sc-breadcrumb-menu.show { display: flex; animation: breadcrumb-fade 0.15s ease; }
      @keyframes breadcrumb-fade {
        from { opacity: 0; transform: translateY(-4px); }
        to { opacity: 1; transform: translateY(0); }
      }
      .sc-breadcrumb-menu-item {
        padding: 0.5rem 1rem; font-size: 0.8rem; font-weight: 600;
        color: #0F1A2E; text-decoration: none; display: flex;
        align-items: center; gap: 0.5rem; transition: background 0.15s;
        cursor: pointer; border: none; background: transparent;
        width: 100%; text-align: left;
      }
      html.dark-mode .sc-breadcrumb-menu-item { color: #EEF2F8; }
      .sc-breadcrumb-menu-item:hover {
        background: #F7F8FA; color: #3A7BD5;
      }
      html.dark-mode .sc-breadcrumb-menu-item:hover {
        background: #1E2E4A;
      }
    `;
    document.head.appendChild(style);
  }

  function getPageTitle(path) {
    if (path.startsWith('/takip-raporu/')) return 'İş Takip Raporu';
    if (path === '/takip-raporu') return 'İş Takip Raporu';
    if (path.startsWith('/muhasebe-takip')) return '₺ Muhasebe Takip';
    if (path.startsWith('/performans')) return '◈ Performans Paneli';
    if (path.startsWith('/talepler')) return '⇄ Talepler';
    if (path.startsWith('/excel-aktarim')) return '▤ Excel Aktarım';
    if (path.startsWith('/beyanname-taslak')) return '✎ TAREKS Taslağı';
    if (path.startsWith('/beyanname')) return '▦ Beyanname Kontrol';
    if (path.startsWith('/master-kontrol')) return '☰ Master Data Kontrol';
    if (path.startsWith('/islem-kayitlari')) return '✓ İşlem Kayıtları';
    if (path.startsWith('/arama')) return '⌕ Arama Sonuçları';
    return '';
  }

  function initBreadcrumb() {
    createBreadcrumbStyle();
    const path = window.location.pathname;
    const title = getPageTitle(path);
    if (!title) return; // Anasayfa vb. gösterme

    const content = document.getElementById('page-content');
    if (!content) return;

    let bar = document.getElementById('sc-breadcrumb-bar');
    if (!bar) {
      bar = document.createElement('div');
      bar.id = 'sc-breadcrumb-bar';
      bar.className = 'sc-breadcrumb-bar';
      content.insertBefore(bar, content.firstChild);
    }

    let poMatch = path.match(/^\/takip-raporu\/([A-Za-z0-9_-]+)$/);
    let html = `
      <a href="/" class="sc-breadcrumb-item" data-pjax>🏠 Anasayfa</a>
      <span class="sc-breadcrumb-sep">/</span>
      <a href="${path.startsWith('/takip-raporu/') ? '/takip-raporu' : path}" class="sc-breadcrumb-item" data-pjax>${title}</a>
    `;

    if (poMatch) {
      const po = poMatch[1];
      html += `
        <span class="sc-breadcrumb-sep">/</span>
        <div class="sc-breadcrumb-current">
          <span>PO #${po}</span>
          <button type="button" id="sc-bc-dropdown-btn" class="sc-breadcrumb-dropdown-btn">Zıpla ▾</button>
          <div id="sc-bc-menu" class="sc-breadcrumb-menu">
            <a href="/muhasebe-takip?po=${po}" class="sc-breadcrumb-menu-item">₺ Muhasebe Kaydına Git →</a>
            <a href="/talepler/yeni?po=${po}" class="sc-breadcrumb-menu-item" data-pjax>⇄ Bu PO İçin Talep Aç →</a>
            <a href="/arama?q=${po}" class="sc-breadcrumb-menu-item" data-pjax>⌕ Sistemde Bu PO'yu Ara</a>
            <button type="button" class="sc-breadcrumb-menu-item" id="sc-bc-copy-po">📋 PO Numarasını Kopyala</button>
            <button type="button" class="sc-breadcrumb-menu-item" id="sc-bc-open-peek">👁 Hızlı Gözat (Ön İzleme)</button>
          </div>
        </div>
      `;
    }

    bar.innerHTML = html;

    if (poMatch) {
      const po = poMatch[1];
      const btn = document.getElementById('sc-bc-dropdown-btn');
      const menu = document.getElementById('sc-bc-menu');

      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        menu.classList.toggle('show');
      });

      document.addEventListener('click', () => {
        menu.classList.remove('show');
      });

      document.getElementById('sc-bc-copy-po').addEventListener('click', () => {
        if (window.copyTextToClipboard) window.copyTextToClipboard(po);
        else navigator.clipboard.writeText(po);
        alert('PO panoya kopyalandı: ' + po);
      });

      document.getElementById('sc-bc-open-peek').addEventListener('click', () => {
        if (window.openPeekDrawer) window.openPeekDrawer(po);
      });
    }
  }

  window.initBreadcrumb = initBreadcrumb;

  document.addEventListener('DOMContentLoaded', initBreadcrumb);
  document.addEventListener('pjax:success', initBreadcrumb);
})();
