// takip_raporu.js — İş Takip Raporu Anında Sayfalama (Performans Çözümü) & Canlı İşlem Sepeti

(function() {
  let currentPage = 1;
  let pageSize = 50;

  function initTakipRaporu() {
    const table = document.getElementById('takip-tablo');
    if (!table) return;
    if (table.dataset.takipBound) return;
    table.dataset.takipBound = "1";

    const tbody = table.querySelector('tbody');
    if (!tbody) return;

    // TÜM veri satırları (empty colspan satırı hariç)
    const allRows = Array.from(tbody.querySelectorAll('tr')).filter(tr => !tr.querySelector('td[colspan]'));

    // ── 1. ANINDA SAYFALAMA (PERFORMANS HIZLANDIRICI) ──
    const pagBar = document.getElementById('takip-pagination-top');
    const pageNumEl = document.getElementById('tp-page-num');
    const infoEl = document.getElementById('tp-info');
    const prevBtn = document.getElementById('tp-prev');
    const nextBtn = document.getElementById('tp-next');
    const sizeSelect = document.getElementById('tp-size-select');

    if (allRows.length > 0 && pagBar) {
      pagBar.style.display = 'flex';
    }

    function renderPage() {
      const total = allRows.length;
      let maxPage = 1;
      if (pageSize !== 'all') {
        maxPage = Math.ceil(total / pageSize) || 1;
      }
      if (currentPage > maxPage) currentPage = maxPage;
      if (currentPage < 1) currentPage = 1;

      const start = pageSize === 'all' ? 0 : (currentPage - 1) * pageSize;
      const end = pageSize === 'all' ? total : start + pageSize;

      // Sadece aktif sayfadaki satırları görünür yap (Geri kalan satırlar render/layout hesaplamasından tasarruf ettirir!)
      allRows.forEach((tr, idx) => {
        if (idx >= start && idx < end) {
          tr.style.display = '';
        } else {
          tr.style.display = 'none';
        }
      });

      if (pageNumEl) {
        pageNumEl.textContent = pageSize === 'all' ? 'Tümü (' + total + ')' : 'Sayfa ' + currentPage + ' / ' + maxPage;
      }
      if (infoEl) {
        infoEl.textContent = 'Toplam ' + total + ' kayıt listeleniyor';
      }
      if (prevBtn) prevBtn.disabled = (currentPage <= 1 || pageSize === 'all');
      if (nextBtn) nextBtn.disabled = (currentPage >= maxPage || pageSize === 'all');
      updateTray();
    }

    if (prevBtn) {
      prevBtn.onclick = function() {
        if (currentPage > 1) {
          currentPage--;
          renderPage();
        }
      };
    }

    if (nextBtn) {
      nextBtn.onclick = function() {
        currentPage++;
        renderPage();
      };
    }

    if (sizeSelect) {
      sizeSelect.onchange = function() {
        const val = sizeSelect.value;
        pageSize = val === 'all' ? 'all' : parseInt(val, 10);
        currentPage = 1;
        renderPage();
      };
    }

    // ── 2. CANLI İŞLEM SEPETİ & TOPLU TALEP AÇMA ──
    const tray = document.getElementById('sc-takip-batch-tray');
    const selectAll = document.getElementById('takip-select-all');
    const countEl = document.getElementById('takip-batch-count');
    const btnTalep = document.getElementById('takip-btn-talep');
    const btnKopyala = document.getElementById('takip-btn-kopyala');
    const btnExcel = document.getElementById('takip-btn-excel');
    const btnKapat = document.getElementById('takip-btn-kapat');

    function getVisibleRowCheckboxes() {
      return Array.from(table.querySelectorAll('tbody tr:not([style*="display: none"]) .takip-row-select'));
    }

    function getAllChecked() {
      return Array.from(table.querySelectorAll('tbody .takip-row-select:checked'));
    }

    function updateTray() {
      if (!tray) return;
      const checked = getAllChecked();
      if (checked.length > 0) {
        if (countEl) countEl.textContent = checked.length + ' PO seçildi';
        tray.style.display = 'flex';
      } else {
        tray.style.display = 'none';
        if (selectAll) selectAll.checked = false;
      }
    }

    if (selectAll) {
      selectAll.addEventListener('change', function() {
        const visibleBoxes = getVisibleRowCheckboxes();
        visibleBoxes.forEach(cb => {
          cb.checked = selectAll.checked;
          const tr = cb.closest('tr');
          if (tr) {
            if (selectAll.checked) tr.classList.add('muh-row-selected');
            else tr.classList.remove('muh-row-selected');
          }
        });
        updateTray();
      });
    }

    table.addEventListener('change', function(e) {
      if (e.target && e.target.classList.contains('takip-row-select')) {
        const tr = e.target.closest('tr');
        if (tr) {
          if (e.target.checked) tr.classList.add('muh-row-selected');
          else tr.classList.remove('muh-row-selected');
        }
        updateTray();
      }
    });

    // 1. Seçilenlere Toplu Dosya Talebi Aç (/talepler/yeni?po=...)
    if (btnTalep) {
      btnTalep.addEventListener('click', function() {
        const checked = getAllChecked();
        if (checked.length === 0) return;
        const polar = checked.map(cb => cb.getAttribute('data-po')).filter(Boolean);
        const url = '/talepler/yeni?po=' + encodeURIComponent(polar.join(','));
        window.location.href = url;
      });
    }

    // 2. PO No'ları Kopyala
    if (btnKopyala) {
      btnKopyala.addEventListener('click', function() {
        const checked = getAllChecked();
        if (checked.length === 0) return;
        const polar = checked.map(cb => cb.getAttribute('data-po')).filter(Boolean);
        const metin = polar.join('\n');
        navigator.clipboard.writeText(metin).then(() => {
          if (typeof scBildirim === 'function') {
            scBildirim('Başarılı', checked.length + ' adet PO Numarası panoya kopyalandı!');
          } else {
            alert(checked.length + ' adet PO Numarası kopyalandı.');
          }
        });
      });
    }

    // 3. Seçilenleri Excel İndir
    if (btnExcel) {
      btnExcel.addEventListener('click', function() {
        const checked = getAllChecked();
        if (checked.length === 0) return;
        const polar = checked.map(cb => cb.getAttribute('data-po')).filter(Boolean);
        
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = '/takip-raporu/excel-secili';
        form.style.display = 'none';

        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'secili_polar';
        input.value = polar.join(',');
        form.appendChild(input);

        document.body.appendChild(form);
        form.submit();
        document.body.removeChild(form);

        if (typeof scBildirim === 'function') {
          scBildirim('Excel İndiriliyor', checked.length + ' adet seçili PO Excel olarak aktarılıyor.');
        }
      });
    }

    // 4. Temizle
    if (btnKapat) {
      btnKapat.addEventListener('click', function() {
        const checked = getAllChecked();
        checked.forEach(cb => {
          cb.checked = false;
          const tr = cb.closest('tr');
          if (tr) tr.classList.remove('muh-row-selected');
        });
        if (selectAll) selectAll.checked = false;
        if (tray) tray.style.display = 'none';
      });
    }

    // İlk açılışta sayfalamayı hesapla
    renderPage();
  }

  window.initTakipRaporu = initTakipRaporu;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initTakipRaporu);
  } else {
    initTakipRaporu();
  }
  document.addEventListener('pjax:success', initTakipRaporu);
})();
