/**
 * peek_drawer.js — SmartClearance Yandan Kayan Ön İzleme Çekmecesi ("Hızlı Gözat")
 * PO detaylarına ve 5 aşamalı yaşam döngüsüne sayfadan ayrılmadan sağ çekmecede bakmayı sağlar.
 */

(function() {
  let activePoList = [];
  let currentIndex = -1;

  function injectDrawerHtml() {
    if (document.getElementById('sc-peek-drawer')) return;

    const div = document.createElement('div');
    div.id = 'sc-peek-drawer';
    div.className = 'sc-peek-drawer';
    div.innerHTML = `
      <div class="sc-peek-header">
        <div class="sc-peek-title-wrap">
          <span class="sc-peek-ic">👁</span>
          <span id="sc-peek-po-title" class="sc-peek-po-title">PO —</span>
          <span id="sc-peek-hat-badge" class="sc-peek-badge" style="display:none;"></span>
        </div>
        <div class="sc-peek-controls">
          <button type="button" id="sc-peek-prev" class="sc-peek-nav-btn" title="Önceki PO (↑)">↑</button>
          <button type="button" id="sc-peek-next" class="sc-peek-nav-btn" title="Sonraki PO (↓)">↓</button>
          <button type="button" id="sc-peek-close" class="sc-peek-close-btn" title="Kapat (ESC)">✕</button>
        </div>
      </div>
      <div id="sc-peek-body" class="sc-peek-body">
        <div class="sc-peek-loading">Yükleniyor...</div>
      </div>
      <div class="sc-peek-footer">
        <a id="sc-peek-goto-btn" href="#" class="sc-peek-btn-primary" data-pjax>📄 Tam Detay Sayfasına Git</a>
        <button type="button" id="sc-peek-copy-btn" class="sc-peek-btn-ghost">📋 PO Kopyala</button>
      </div>
    `;
    document.body.appendChild(div);

    const style = document.createElement('style');
    style.textContent = `
      .sc-peek-drawer {
        position: fixed; top: 0; right: 0; width: 420px; height: 100vh;
        background: #FFFFFF; z-index: 1080;
        border-left: 1px solid #E3E6EB;
        box-shadow: -12px 0 35px rgba(15,26,46,0.18);
        display: flex; flex-direction: column;
        transform: translateX(105%);
        transition: transform 0.28s cubic-bezier(0.16, 1, 0.3, 1);
      }
      html.dark-mode .sc-peek-drawer {
        background: #0F1A2E;
        border-left-color: #1E2E4A;
        box-shadow: -12px 0 35px rgba(0,0,0,0.45);
      }
      .sc-peek-drawer.open {
        transform: translateX(0);
      }
      .sc-peek-header {
        display: flex; align-items: center; justify-content: space-between;
        padding: 1.1rem 1.4rem; border-bottom: 1px solid #E3E6EB;
        background: #F7F8FA;
      }
      html.dark-mode .sc-peek-header {
        background: #17243B;
        border-bottom-color: #1E2E4A;
      }
      .sc-peek-title-wrap {
        display: flex; align-items: center; gap: 0.6rem;
      }
      .sc-peek-ic { font-size: 1.2rem; color: #3A7BD5; }
      .sc-peek-po-title {
        font-family: Georgia, serif; font-size: 1.15rem; font-weight: 700;
        color: #0F1A2E;
      }
      html.dark-mode .sc-peek-po-title { color: #EEF2F8; }
      .sc-peek-badge {
        font-size: 0.7rem; font-weight: 700; padding: 2px 8px;
        border-radius: 100px; text-transform: uppercase;
      }
      .sc-peek-controls { display: flex; align-items: center; gap: 0.4rem; }
      .sc-peek-nav-btn, .sc-peek-close-btn {
        width: 32px; height: 32px; border-radius: 6px; border: 1px solid #E3E6EB;
        background: #FFFFFF; color: #0F1A2E; font-weight: 700; cursor: pointer;
        display: flex; align-items: center; justify-content: center;
        transition: all 0.15s;
      }
      html.dark-mode .sc-peek-nav-btn, html.dark-mode .sc-peek-close-btn {
        background: #1E2E4A; border-color: #2D4268; color: #EEF2F8;
      }
      .sc-peek-nav-btn:hover, .sc-peek-close-btn:hover {
        background: #3A7BD5; color: #FFFFFF; border-color: #3A7BD5;
      }
      .sc-peek-body {
        flex: 1; overflow-y: auto; padding: 1.4rem;
      }
      .sc-peek-footer {
        padding: 1rem 1.4rem; border-top: 1px solid #E3E6EB;
        display: flex; gap: 0.6rem; background: #F7F8FA;
      }
      html.dark-mode .sc-peek-footer {
        background: #17243B; border-top-color: #1E2E4A;
      }
      .sc-peek-btn-primary {
        flex: 1; text-align: center; background: #3A7BD5; color: #FFFFFF;
        padding: 0.6rem; border-radius: 6px; font-weight: 700; font-size: 0.85rem;
        text-decoration: none; transition: background 0.15s;
      }
      .sc-peek-btn-primary:hover { background: #2A60B0; }
      .sc-peek-btn-ghost {
        background: transparent; border: 1px solid #E3E6EB; padding: 0.6rem 0.8rem;
        border-radius: 6px; font-weight: 600; font-size: 0.8rem; color: #6B7686;
        cursor: pointer;
      }
      html.dark-mode .sc-peek-btn-ghost { border-color: #2D4268; color: #A8B4C4; }
      .sc-peek-btn-ghost:hover { background: rgba(58,123,213,0.1); color: #3A7BD5; }
      
      .sc-peek-pipeline {
        display: flex; align-items: center; justify-content: space-between;
        margin-bottom: 1.3rem; padding: 0.8rem 0.6rem; background: rgba(58,123,213,0.06);
        border-radius: 8px; position: relative;
      }
      .sc-peek-step {
        display: flex; flex-direction: column; align-items: center; gap: 4px;
        position: relative; z-index: 2;
      }
      .sc-peek-step-dot {
        width: 22px; height: 22px; border-radius: 50%;
        background: #E3E6EB; color: #6B7686; font-size: 0.65rem; font-weight: 700;
        display: flex; align-items: center; justify-content: center;
      }
      html.dark-mode .sc-peek-step-dot { background: #2D4268; color: #A8B4C4; }
      .sc-peek-step.active .sc-peek-step-dot {
        background: #14A05C; color: #FFFFFF; box-shadow: 0 0 0 3px rgba(20,160,92,0.2);
      }
      .sc-peek-step.current .sc-peek-step-dot {
        background: #3A7BD5; color: #FFFFFF; box-shadow: 0 0 0 3px rgba(58,123,213,0.2);
      }
      .sc-peek-step-lbl { font-size: 0.64rem; font-weight: 600; color: #6B7686; }
      html.dark-mode .sc-peek-step-lbl { color: #A8B4C4; }
      
      .sc-peek-card {
        background: #F7F8FA; border: 1px solid #E3E6EB; border-radius: 8px;
        padding: 1rem; margin-bottom: 1rem;
      }
      html.dark-mode .sc-peek-card { background: #17243B; border-color: #1E2E4A; }
      .sc-peek-row {
        display: flex; justify-content: space-between; font-size: 0.82rem;
        padding: 0.35rem 0; border-bottom: 1px dashed rgba(0,0,0,0.06);
      }
      html.dark-mode .sc-peek-row { border-bottom-color: rgba(255,255,255,0.06); }
      .sc-peek-row:last-child { border-bottom: none; }
      .sc-peek-row-lbl { color: #6B7686; }
      html.dark-mode .sc-peek-row-lbl { color: #A8B4C4; }
      .sc-peek-row-val { font-weight: 700; color: #0F1A2E; }
      html.dark-mode .sc-peek-row-val { color: #EEF2F8; }
      
      .sc-peek-risk-box {
        background: rgba(220,47,62,0.08); border: 1px solid rgba(220,47,62,0.25);
        border-radius: 6px; padding: 0.8rem; margin-bottom: 1rem;
        color: #DC2F3E; font-size: 0.8rem;
      }
      .sc-peek-note-box {
        background: rgba(58,123,213,0.07); border: 1px solid rgba(58,123,213,0.2);
        border-radius: 6px; padding: 0.8rem; font-size: 0.8rem; color: #0F1A2E;
      }
      html.dark-mode .sc-peek-note-box { color: #EEF2F8; }
    `;
    document.head.appendChild(style);

    document.getElementById('sc-peek-close').addEventListener('click', closePeekDrawer);
    document.getElementById('sc-peek-prev').addEventListener('click', () => navigatePeek(-1));
    document.getElementById('sc-peek-next').addEventListener('click', () => navigatePeek(1));
    document.getElementById('sc-peek-copy-btn').addEventListener('click', () => {
      const po = document.getElementById('sc-peek-po-title').textContent.replace('PO #', '');
      if (po && window.copyTextToClipboard) window.copyTextToClipboard(po);
      else if (po) navigator.clipboard.writeText(po);
      alert('PO panoya kopyalandı: ' + po);
    });

    document.addEventListener('keydown', (e) => {
      const drawer = document.getElementById('sc-peek-drawer');
      if (!drawer || !drawer.classList.contains('open')) return;
      if (e.key === 'Escape') {
        closePeekDrawer();
      } else if (e.key === 'ArrowUp' && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {
        e.preventDefault();
        navigatePeek(-1);
      } else if (e.key === 'ArrowDown' && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {
        e.preventDefault();
        navigatePeek(1);
      }
    });
  }

  function closePeekDrawer() {
    const d = document.getElementById('sc-peek-drawer');
    if (d) d.classList.remove('open');
  }

  function navigatePeek(dir) {
    if (activePoList.length === 0 || currentIndex === -1) return;
    let nextIdx = currentIndex + dir;
    if (nextIdx < 0) nextIdx = 0;
    if (nextIdx >= activePoList.length) nextIdx = activePoList.length - 1;
    if (nextIdx !== currentIndex) {
      currentIndex = nextIdx;
      openPeekDrawer(activePoList[currentIndex]);
    }
  }

  function renderPeekContent(data) {
    const title = document.getElementById('sc-peek-po-title');
    const badge = document.getElementById('sc-peek-hat-badge');
    const body = document.getElementById('sc-peek-body');
    const gotoBtn = document.getElementById('sc-peek-goto-btn');

    title.textContent = 'PO #' + data.referans_no;
    gotoBtn.href = '/takip-raporu/' + data.referans_no;

    if (data.hat && data.hat !== '-') {
      badge.style.display = 'inline-block';
      badge.textContent = data.hat;
      if (data.hat.includes('YEŞ') || data.hat.includes('YES')) {
        badge.style.background = '#E8F8EF'; badge.style.color = '#14A05C';
      } else if (data.hat.includes('SARI')) {
        badge.style.background = '#FDF3E3'; badge.style.color = '#D97E0A';
      } else {
        badge.style.background = '#FEECEE'; badge.style.color = '#DC2F3E';
      }
    } else {
      badge.style.display = 'none';
    }

    const s = data.step || 1;
    const stepsHtml = [
      { num: 1, lbl: 'Tescil Bek.' },
      { num: 2, lbl: 'Tescil' },
      { num: 3, lbl: 'Hat' },
      { num: 4, lbl: 'İşlem' },
      { num: 5, lbl: 'Kapanış' }
    ].map(st => {
      let cls = 'sc-peek-step';
      if (st.num < s) cls += ' active';
      else if (st.num === s) cls += ' current';
      return `
        <div class="${cls}">
          <div class="sc-peek-step-dot">${st.num < s ? '✓' : st.num}</div>
          <div class="sc-peek-step-lbl">${st.lbl}</div>
        </div>
      `;
    }).join('');

    let riskHtml = '';
    if (data.risk_sayisi > 0 && data.riskler) {
      riskHtml = `
        <div class="sc-peek-risk-box">
          <strong>⚠️ Risk Uyarıları (${data.risk_sayisi}):</strong>
          <ul style="margin: 0.4rem 0 0 1.2rem; padding: 0;">
            ${data.riskler.map(r => `<li>${r.mesaj || ''}</li>`).join('')}
          </ul>
        </div>
      `;
    }

    let notHtml = '';
    if (data.son_not) {
      notHtml = `
        <div class="sc-peek-note-box">
          <div style="font-size:0.72rem; color:#6B7686; margin-bottom:4px;">
            💬 Son Not (${data.son_not.yazan || 'Ekip'}, ${data.son_not.zaman_metni || ''}):
          </div>
          <div style="font-style:italic;">"${data.son_not.metin || ''}"</div>
        </div>
      `;
    }

    body.innerHTML = `
      <div class="sc-peek-pipeline">
        ${stepsHtml}
      </div>
      
      <div class="sc-peek-card">
        <div class="sc-peek-row">
          <span class="sc-peek-row-lbl">Dosya No</span>
          <span class="sc-peek-row-val">${data.dosya_no || 'AÇILMAMIŞ'}</span>
        </div>
        <div class="sc-peek-row">
          <span class="sc-peek-row-lbl">Gümrük</span>
          <span class="sc-peek-row-val">${data.gumruk}</span>
        </div>
        <div class="sc-peek-row">
          <span class="sc-peek-row-lbl">Tescil Tarihi</span>
          <span class="sc-peek-row-val">${data.tescil}</span>
        </div>
        <div class="sc-peek-row">
          <span class="sc-peek-row-lbl">Kapanış Tarihi</span>
          <span class="sc-peek-row-val">${data.kapanis}</span>
        </div>
        <div class="sc-peek-row">
          <span class="sc-peek-row-lbl">Durum</span>
          <span class="sc-peek-row-val">${data.durum}</span>
        </div>
      </div>

      ${riskHtml}
      ${notHtml}
    `;
  }

  function openPeekDrawer(referansNo) {
    injectDrawerHtml();
    const d = document.getElementById('sc-peek-drawer');
    const body = document.getElementById('sc-peek-body');
    d.classList.add('open');
    body.innerHTML = '<div class="sc-peek-loading">Yükleniyor...</div>';

    fetch('/api/po-ozet/' + encodeURIComponent(referansNo))
      .then(r => r.json())
      .then(data => {
        if (data.error) {
          body.innerHTML = `<div style="color:#DC2F3E; font-weight:700;">Hata: ${data.error}</div>`;
        } else {
          renderPeekContent(data);
        }
      })
      .catch(err => {
        body.innerHTML = `<div style="color:#DC2F3E; font-weight:700;">Yüklenirken hata oluştu.</div>`;
      });
  }

  function initPeekListeners() {
    injectDrawerHtml();
    const rows = document.querySelectorAll('#takip-tablo tbody tr, .takip-satir');
    activePoList = [];
    rows.forEach(tr => {
      const po = tr.getAttribute('data-po');
      if (po && !activePoList.includes(po)) {
        activePoList.push(po);
      }
      const peekBtn = tr.querySelector('.sc-peek-btn');
      if (peekBtn) {
        peekBtn.onclick = (e) => {
          e.preventDefault();
          e.stopPropagation();
          currentIndex = activePoList.indexOf(po);
          openPeekDrawer(po);
        };
      }
    });
  }

  window.openPeekDrawer = openPeekDrawer;
  window.initPeekListeners = initPeekListeners;

  document.addEventListener('DOMContentLoaded', initPeekListeners);
  document.addEventListener('pjax:success', initPeekListeners);
})();
