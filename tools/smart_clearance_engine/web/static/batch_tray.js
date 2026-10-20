// batch_tray.js — SmartClearance Canlı İşlem Sepeti (Floating Batch Action Tray)
// Tabloda birden fazla satır seçildiğinde alttan kayarak açılan şık komuta çubuğu.

(function() {
  function initBatchTray() {
    const tray = document.getElementById('sc-batch-tray');
    const selectAll = document.getElementById('muh-select-all');
    const table = document.getElementById('muhasebe-tablo');
    if (!tray || !table) return;
    if (table.dataset.trayBound) return;
    table.dataset.trayBound = "1";

    const countEl = document.getElementById('batch-tray-count');
    const btnKopyala = document.getElementById('batch-btn-kopyala');
    const btnExcel = document.getElementById('batch-btn-excel');
    const btnSil = document.getElementById('batch-btn-sil');
    const btnKapat = document.getElementById('batch-btn-kapat');

    function getVisibleRowCheckboxes() {
      return Array.from(table.querySelectorAll('tbody tr:not([style*="display: none"]) .muh-row-select'));
    }

    function getAllChecked() {
      return Array.from(table.querySelectorAll('tbody .muh-row-select:checked'));
    }

    function updateTray() {
      const checked = getAllChecked();
      if (checked.length > 0) {
        if (countEl) countEl.textContent = checked.length + ' satır seçildi';
        tray.style.display = 'flex';
      } else {
        tray.style.display = 'none';
        if (selectAll) selectAll.checked = false;
      }
    }

    // Tümünü seç checkbox'ı
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

    // Tekil satır checkbox değişikliği (Event delegation)
    table.addEventListener('change', function(e) {
      if (e.target && e.target.classList.contains('muh-row-select')) {
        const tr = e.target.closest('tr');
        if (tr) {
          if (e.target.checked) tr.classList.add('muh-row-selected');
          else tr.classList.remove('muh-row-selected');
        }
        updateTray();
      }
    });

    // 1. Dosya No'ları Kopyala
    if (btnKopyala) {
      btnKopyala.addEventListener('click', function() {
        const checked = getAllChecked();
        if (checked.length === 0) return;
        const dosyaNolar = checked.map(cb => cb.getAttribute('data-dosya')).filter(Boolean);
        const metin = dosyaNolar.join('\n');
        navigator.clipboard.writeText(metin).then(() => {
          if (typeof scBildirim === 'function') {
            scBildirim('Başarılı', checked.length + ' adet Dosya Numarası panoya kopyalandı!');
          } else {
            alert(checked.length + ' adet Dosya Numarası kopyalandı.');
          }
        });
      });
    }

    // 2. Seçilenleri Excel İndir
    if (btnExcel) {
      btnExcel.addEventListener('click', function() {
        const checked = getAllChecked();
        if (checked.length === 0) return;
        const dosyaNolar = checked.map(cb => cb.getAttribute('data-dosya')).filter(Boolean);
        
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = '/muhasebe-takip/excel-secili';
        form.style.display = 'none';

        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'secili_dosyalar';
        input.value = dosyaNolar.join(',');
        form.appendChild(input);

        document.body.appendChild(form);
        form.submit();
        document.body.removeChild(form);

        if (typeof scBildirim === 'function') {
          scBildirim('Excel İndiriliyor', checked.length + ' adet seçili satır Excel olarak aktarılıyor.');
        }
      });
    }

    // 3. Seçilenleri Sil (Sadece Muhasebeye Gönderilenler)
    if (btnSil) {
      btnSil.addEventListener('click', function() {
        const checked = getAllChecked();
        if (checked.length === 0) return;
        const silinecekIdler = checked
          .map(cb => cb.getAttribute('data-id'))
          .filter(id => id && id !== 'None' && id !== '' && id !== '0');

        if (silinecekIdler.length === 0) {
          if (typeof scBildirim === 'function') {
            scBildirim('Bilgi', 'Seçilen satırların hiçbiri sonradan eklenmiş muhasebe kaydı değil, sadece açık dosyalar listeleniyor.');
          } else {
            alert('Seçilen satırların hiçbiri silinebilir muhasebe kaydı değil.');
          }
          return;
        }

        if (!confirm('Seçilen ' + silinecekIdler.length + ' adet muhasebe kaydını silmek istediğinize emin misiniz?')) {
          return;
        }

        const form = document.createElement('form');
        form.method = 'POST';
        form.action = '/muhasebe-takip/toplu-sil';
        form.style.display = 'none';

        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'secili_idler';
        input.value = silinecekIdler.join(',');
        form.appendChild(input);

        document.body.appendChild(form);
        form.submit();
      });
    }

    // 4. Seçimi Temizle
    if (btnKapat) {
      btnKapat.addEventListener('click', function() {
        const checked = getAllChecked();
        checked.forEach(cb => {
          cb.checked = false;
          const tr = cb.closest('tr');
          if (tr) tr.classList.remove('muh-row-selected');
        });
        if (selectAll) selectAll.checked = false;
        tray.style.display = 'none';
      });
    }
  }

  window.initBatchTray = initBatchTray;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initBatchTray);
  } else {
    initBatchTray();
  }
  document.addEventListener('pjax:success', initBatchTray);
})();
