// ==============================================================================
// 🏛️ SMARTCLEARANCE MOBILE CONTROLLER (APPLE / VERCEL REACTIVE CORE)
// ==============================================================================

const tg = window.Telegram?.WebApp;

// Telegram TMA Başlatma
if (tg) {
  try {
    tg.ready();
    tg.expand();
    if (tg.enableClosingConfirmation) tg.enableClosingConfirmation();
    if (tg.setHeaderColor) tg.setHeaderColor('#000000');
    if (tg.setBackgroundColor) tg.setBackgroundColor('#000000');
  } catch (e) {
    console.warn("Telegram WebApp başlatma uyarısı:", e);
  }
}

// Dokunsal Geri Bildirim (Haptic Feedback)
function triggerHaptic(type = 'light') {
  try {
    if (tg?.HapticFeedback) {
      if (type === 'selection') tg.HapticFeedback.selectionChanged();
      else if (type === 'success') tg.HapticFeedback.notificationOccurred('success');
      else if (type === 'warning') tg.HapticFeedback.notificationOccurred('warning');
      else tg.HapticFeedback.impactOccurred(type);
    } else if (navigator.vibrate) {
      navigator.vibrate(12);
    }
  } catch (e) {}
}

// Uygulama Durumu
const state = {
  currentTab: 'cockpit',
  cockpitFilter: 'all',
  searchQuery: '',
  stats: {},
  cockpitItems: [],
  horizonItems: [],
  kantarItems: [],
  gtbItems: []
};

// ── VERİ ÇEKME METOTLARI ─────────────────────────────────────────────────────

async function fetchStats() {
  try {
    const res = await fetch('/api/stats');
    if (!res.ok) return;
    const data = await res.json();
    state.stats = data;

    document.getElementById('stat-active').textContent = data.active_files ?? '--';
    document.getElementById('stat-total-sub').textContent = `Toplam ${data.total_files ?? 0} dosya`;
    document.getElementById('stat-tax').textContent = data.tax_pending ?? '--';
    document.getElementById('stat-tescil').textContent = data.registered ?? '--';
    document.getElementById('stat-vessels').textContent = data.active_vessels ?? '--';
    document.getElementById('stat-containers-sub').textContent = `${data.active_containers ?? 0} konteyner radarda`;
  } catch (err) {
    console.error("Stats çekilemedi:", err);
  }
}

async function fetchCockpit() {
  const container = document.getElementById('cockpit-list');
  try {
    const res = await fetch(`/api/cockpit?filter_type=${state.cockpitFilter}&q=${encodeURIComponent(state.searchQuery)}`);
    if (!res.ok) throw new Error("API hatası");
    const data = await res.json();
    state.cockpitItems = data.items || [];

    renderCockpitList(state.cockpitItems);
  } catch (err) {
    container.innerHTML = `<div class="p-6 text-center text-red-400 text-xs">Veriler alınamadı: ${err.message}</div>`;
  }
}

function renderCockpitList(items) {
  const container = document.getElementById('cockpit-list');
  if (!items || items.length === 0) {
    container.innerHTML = `
      <div class="glass-card p-8 text-center text-zinc-500">
        <span class="text-2xl block mb-1">📂</span>
        <p class="text-xs">Bu kritere uygun dosya bulunamadı.</p>
      </div>
    `;
    return;
  }

  let html = '';
  items.forEach(it => {
    // Hat Rozeti Rengi
    let hatBadge = '';
    const h = (it.hat || '').toUpperCase();
    if (h.includes('KIRMIZI')) {
      hatBadge = '<span class="px-2 py-0.5 text-[10px] font-bold rounded-full bg-rose-500/15 text-rose-400 border border-rose-500/30">🔴 Kırmızı Hat</span>';
    } else if (h.includes('SARI')) {
      hatBadge = '<span class="px-2 py-0.5 text-[10px] font-bold rounded-full bg-amber-500/15 text-amber-400 border border-amber-500/30">🟡 Sarı Hat</span>';
    } else if (h.includes('YEŞİL') || h.includes('YESIL')) {
      hatBadge = '<span class="px-2 py-0.5 text-[10px] font-bold rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">🟢 Yeşil Hat</span>';
    } else if (h.includes('MAVİ') || h.includes('MAVI')) {
      hatBadge = '<span class="px-2 py-0.5 text-[10px] font-bold rounded-full bg-sky-500/15 text-sky-400 border border-sky-500/30">🔵 Mavi Hat</span>';
    }

    // Vergi Rozeti
    let taxBadge = '';
    if (it.is_tax_pending) {
      taxBadge = '<span class="px-1.5 py-0.5 text-[10px] rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">✉️ Vergi Bekliyor</span>';
    }

    // Kapandı Rozeti
    let statusPill = '';
    if (it.kapandi) {
      statusPill = '<span class="text-[10px] text-zinc-500 font-medium">Kapandı</span>';
    } else {
      statusPill = '<span class="text-[10px] text-sky-400 font-medium">İşlemde</span>';
    }

    html += `
      <div class="glass-card p-3.5" onclick="openFileDetail(${JSON.stringify(it).replace(/"/g, '&quot;')})">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-2">
            <span class="font-mono-code font-bold text-sm text-white">${it.dosya_no || '—'}</span>
            ${hatBadge}
          </div>
          ${statusPill}
        </div>

        <div class="mt-1.5">
          <div class="text-xs font-medium text-zinc-200 truncate">${it.musteri || '—'}</div>
          <div class="text-[11px] text-zinc-400 font-mono-code mt-0.5">Ref: ${it.referans_no || '—'}</div>
        </div>

        <div class="mt-2.5 pt-2 border-t border-white/[0.06] flex items-center justify-between text-[11px]">
          <div class="flex items-center space-x-1.5">
            ${taxBadge}
            ${it.beyanname_no ? `<span class="text-zinc-500 font-mono-code text-[10px]">Beyan: ${it.beyanname_no}</span>` : ''}
          </div>
          <span class="text-zinc-400 font-mono-code text-[10px]">${it.tescil_no || it.eta || ''}</span>
        </div>
      </div>
    `;
  });

  container.innerHTML = html;
}

async function fetchHorizon() {
  const listContainer = document.getElementById('horizon-vessel-list');
  try {
    const res = await fetch('/api/horizon?active_only=true');
    if (!res.ok) throw new Error("API hatası");
    const data = await res.json();
    state.horizonItems = data.items || [];

    document.getElementById('horizon-count-badge').textContent = `${state.horizonItems.length} Aktif Gemi`;

    renderHorizonList(state.horizonItems);

    // Harita çizimi
    if (typeof renderVesselsOnMap === 'function') {
      renderVesselsOnMap(state.horizonItems);
    }
  } catch (err) {
    listContainer.innerHTML = `<div class="p-6 text-center text-red-400 text-xs">Radar verisi alınamadı: ${err.message}</div>`;
  }
}

function renderHorizonList(items) {
  const container = document.getElementById('horizon-vessel-list');
  if (!items || items.length === 0) {
    container.innerHTML = `
      <div class="glass-card p-6 text-center text-zinc-500 text-xs">Yolda aktif sefer bulunamadı.</div>
    `;
    return;
  }

  let html = '';
  items.slice(0, 40).forEach(v => {
    const coordsStr = v.coords ? `${v.coords[0]}, ${v.coords[1]}` : '';
    const hasCoords = Boolean(v.coords);

    html += `
      <div class="glass-card p-3 flex items-center justify-between" onclick="${hasCoords ? `flyToVessel(${v.coords[0]}, ${v.coords[1]}, '${v.vessel}')` : ''}">
        <div class="flex items-center space-x-2.5">
          <div class="w-9 h-9 rounded-xl bg-zinc-900 border border-white/10 flex items-center justify-center text-base">
            ${v.flag || '🚢'}
          </div>
          <div>
            <div class="font-semibold text-xs text-white flex items-center space-x-1.5">
              <span>${v.vessel || 'Bilinmeyen Gemi'}</span>
              <span class="text-[9px] px-1.5 py-0.2 rounded bg-white/5 text-zinc-400 font-mono-code">${v.carrier}</span>
            </div>
            <div class="text-[11px] text-zinc-400 font-mono-code mt-0.5">
              ${v.container_no || v.bl_no}
            </div>
          </div>
        </div>

        <div class="text-right">
          <div class="text-xs font-bold text-emerald-400">${v.kalan_gun || '—'}</div>
          <div class="text-[10px] text-zinc-500 font-mono-code">${v.live_eta || v.excel_eta || ''}</div>
        </div>
      </div>
    `;
  });

  container.innerHTML = html;
}

async function fetchKantarAndGTB() {
  const kantarContainer = document.getElementById('kantar-list');
  const gtbContainer = document.getElementById('gtb-list');

  try {
    const [kRes, gRes] = await Promise.all([fetch('/api/kantar'), fetch('/api/gtb')]);
    const kData = await kRes.json();
    const gData = await gRes.json();

    state.kantarItems = kData.items || [];
    state.gtbItems = gData.items || [];

    document.getElementById('kantar-count').textContent = `${state.kantarItems.length} Kayıt`;
    document.getElementById('gtb-count').textContent = `${state.gtbItems.length} Beyanname`;

    // Kantar Render
    if (state.kantarItems.length === 0) {
      kantarContainer.innerHTML = '<div class="glass-card p-4 text-center text-zinc-500 text-xs">Aktif kantar kaydı yok.</div>';
    } else {
      let kHtml = '';
      state.kantarItems.slice(0, 20).forEach(k => {
        kHtml += `
          <div class="glass-card p-3 flex items-center justify-between">
            <div>
              <div class="font-mono-code font-bold text-xs text-white">${k.konteyner_no || '—'}</div>
              <div class="text-[11px] text-zinc-400">Dosya: ${k.dosya_no || '—'}</div>
            </div>
            <div class="text-right">
              <span class="text-xs font-bold text-sky-400">${k.kilo ? k.kilo + ' KG' : 'Tartım Bekliyor'}</span>
              <div class="text-[10px] text-zinc-500">${k.durum || ''}</div>
            </div>
          </div>
        `;
      });
      kantarContainer.innerHTML = kHtml;
    }

    // GTB Render
    if (state.gtbItems.length === 0) {
      gtbContainer.innerHTML = '<div class="glass-card p-4 text-center text-zinc-500 text-xs">Aktif GTB kaydı yok.</div>';
    } else {
      let gHtml = '';
      state.gtbItems.slice(0, 20).forEach(g => {
        gHtml += `
          <div class="glass-card p-3 flex items-center justify-between">
            <div>
              <div class="font-mono-code font-bold text-xs text-white">${g.beyanname_no || '—'}</div>
              <div class="text-[11px] text-zinc-400">${g.gumruk || 'Gümrük Md.'}</div>
            </div>
            <div class="text-right">
              <span class="text-xs font-bold ${g.hat === 'KIRMIZI' ? 'text-rose-400' : 'text-emerald-400'}">${g.hat || 'Tescilde'}</span>
              <div class="text-[10px] text-zinc-500">${g.durum || ''}</div>
            </div>
          </div>
        `;
      });
      gtbContainer.innerHTML = gHtml;
    }

  } catch (err) {
    console.error("Kantar/GTB yükleme hatası:", err);
  }
}

// ── FİLTRE VE ARAMA YÖNETİMİ ─────────────────────────────────────────────────

function setCockpitFilter(filterCode) {
  triggerHaptic('selection');
  state.cockpitFilter = filterCode;

  // Segment buton stilini güncelle
  document.querySelectorAll('.segment-btn').forEach(btn => {
    if (btn.getAttribute('data-filter') === filterCode) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });

  // Kokpit görünümüne geç
  if (state.currentTab !== 'cockpit') {
    switchTab('cockpit');
  }

  fetchCockpit();
}

let searchTimer = null;
function handleSearchInput(val) {
  state.searchQuery = val.trim();
  const clearBtn = document.getElementById('search-clear-btn');
  if (state.searchQuery) {
    clearBtn.classList.remove('hidden');
  } else {
    clearBtn.classList.add('hidden');
  }

  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    triggerHaptic();
    if (state.currentTab === 'search') {
      executeDeepSearch(state.searchQuery);
    } else if (state.currentTab === 'cockpit') {
      fetchCockpit();
    } else if (state.currentTab === 'horizon') {
      fetchHorizon();
    }
  }, 250);
}

function clearSearch() {
  triggerHaptic();
  document.getElementById('global-search-input').value = '';
  handleSearchInput('');
}

function executeDeepSearch(query) {
  const container = document.getElementById('search-results-list');
  if (!query) {
    container.innerHTML = '<div class="text-center py-10 text-zinc-500 text-xs">Aramak istediğiniz dosya, beyanname veya konteyneri yazın.</div>';
    return;
  }

  const q = query.toUpperCase();
  const matchedFiles = state.cockpitItems.filter(it => 
    `${it.dosya_no} ${it.referans_no} ${it.musteri} ${it.beyanname_no}`.toUpperCase().includes(q)
  );
  const matchedContainers = state.horizonItems.filter(it => 
    `${it.container_no} ${it.bl_no} ${it.vessel} ${it.carrier}`.toUpperCase().includes(q)
  );

  let html = '';
  if (matchedFiles.length > 0) {
    html += `<div class="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider mb-2">📁 Dosyalar (${matchedFiles.length})</div>`;
    matchedFiles.forEach(it => {
      html += `
        <div class="glass-card p-3 mb-2" onclick="openFileDetail(${JSON.stringify(it).replace(/"/g, '&quot;')})">
          <div class="font-mono-code font-bold text-xs text-white">${it.dosya_no} — ${it.musteri}</div>
          <div class="text-[11px] text-zinc-400 font-mono-code mt-0.5">Ref: ${it.referans_no} | Beyan: ${it.beyanname_no || '—'}</div>
        </div>
      `;
    });
  }

  if (matchedContainers.length > 0) {
    html += `<div class="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider mt-4 mb-2">🚢 Konteyner & Gemiler (${matchedContainers.length})</div>`;
    matchedContainers.forEach(c => {
      html += `
        <div class="glass-card p-3 mb-2">
          <div class="font-semibold text-xs text-white flex items-center gap-1.5">
            <span>${c.flag || '🚢'}</span> <span>${c.vessel || 'Gemi'}</span>
            <span class="text-[9px] px-1 rounded bg-white/10 text-zinc-300 font-mono-code">${c.carrier}</span>
          </div>
          <div class="text-[11px] text-zinc-400 font-mono-code mt-0.5">Konteyner: ${c.container_no} | BL: ${c.bl_no}</div>
        </div>
      `;
    });
  }

  if (!html) {
    container.innerHTML = `<div class="glass-card p-8 text-center text-zinc-500 text-xs">"${query}" ile eşleşen kayıt bulunamadı.</div>`;
  } else {
    container.innerHTML = html;
  }
}

// ── SEKME GEÇİŞİ ─────────────────────────────────────────────────────────────

function switchTab(tabName) {
  if (state.currentTab === tabName) return;
  triggerHaptic('selection');
  state.currentTab = tabName;

  // Görünümleri gizle/göster
  document.querySelectorAll('.tab-view').forEach(v => v.classList.add('hidden'));
  const activeView = document.getElementById(`view-${tabName}`);
  if (activeView) activeView.classList.remove('hidden');

  // Alt çubuk butonlarını güncelle
  document.querySelectorAll('.nav-item').forEach(item => {
    if (item.getAttribute('data-tab') === tabName) {
      item.classList.add('active');
    } else {
      item.classList.remove('active');
    }
  });

  // İlgili sekmenin verisini tazele
  if (tabName === 'cockpit') {
    fetchCockpit();
  } else if (tabName === 'horizon') {
    fetchHorizon();
    setTimeout(() => {
      if (typeof mobileMap !== 'undefined' && mobileMap) {
        mobileMap.invalidateSize();
      }
    }, 200);
  } else if (tabName === 'kantar') {
    fetchKantarAndGTB();
  } else if (tabName === 'search') {
    const input = document.getElementById('global-search-input');
    if (input) input.focus();
  }

  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ── iOS BOTTOM SHEET DETAY ÇEKMECESİ ─────────────────────────────────────────

function openFileDetail(it) {
  triggerHaptic('medium');
  const sheet = document.getElementById('bottom-sheet');
  const backdrop = document.getElementById('bottom-sheet-backdrop');
  const content = document.getElementById('sheet-content');

  let hatBadge = '<span class="text-zinc-400 font-medium">Bilinmiyor</span>';
  const h = (it.hat || '').toUpperCase();
  if (h.includes('KIRMIZI')) hatBadge = '<span class="text-rose-400 font-bold">🔴 Kırmızı Hat (Muayene)</span>';
  else if (h.includes('SARI')) hatBadge = '<span class="text-amber-400 font-bold">🟡 Sarı Hat (Belge Kontrol)</span>';
  else if (h.includes('YEŞİL') || h.includes('YESIL')) hatBadge = '<span class="text-emerald-400 font-bold">🟢 Yeşil Hat (Serbest)</span>';
  else if (h.includes('MAVİ') || h.includes('MAVI')) hatBadge = '<span class="text-sky-400 font-bold">🔵 Mavi Hat</span>';

  content.innerHTML = `
    <div class="flex items-start justify-between pb-3 border-b border-white/10">
      <div>
        <div class="text-[11px] text-zinc-400 uppercase tracking-wider font-semibold">Dosya Detayı</div>
        <div class="font-mono-code font-extrabold text-lg text-white mt-0.5">${it.dosya_no || '—'}</div>
      </div>
      <button onclick="closeDetailSheet()" class="p-1.5 rounded-full bg-white/5 text-zinc-400 hover:text-white">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
        </svg>
      </button>
    </div>

    <div class="py-3 space-y-2.5 text-xs">
      <div>
        <span class="text-zinc-400 block text-[10px] uppercase font-semibold">Müşteri / Firma</span>
        <span class="text-white font-medium">${it.musteri || '—'}</span>
      </div>

      <div class="grid grid-cols-2 gap-2">
        <div class="glass-card p-2.5">
          <span class="text-zinc-400 block text-[10px] uppercase font-semibold">Referans No</span>
          <span class="font-mono-code text-white">${it.referans_no || '—'}</span>
        </div>
        <div class="glass-card p-2.5">
          <span class="text-zinc-400 block text-[10px] uppercase font-semibold">Beyanname No</span>
          <span class="font-mono-code text-white">${it.beyanname_no || '—'}</span>
        </div>
      </div>

      <div class="grid grid-cols-2 gap-2">
        <div class="glass-card p-2.5">
          <span class="text-zinc-400 block text-[10px] uppercase font-semibold">Hat Durumu</span>
          ${hatBadge}
        </div>
        <div class="glass-card p-2.5">
          <span class="text-zinc-400 block text-[10px] uppercase font-semibold">Gümrük Md.</span>
          <span class="text-zinc-200">${it.gumruk || 'Erenköy Gümrük Md.'}</span>
        </div>
      </div>

      <div class="grid grid-cols-2 gap-2">
        <div class="glass-card p-2.5">
          <span class="text-zinc-400 block text-[10px] uppercase font-semibold">Rejim</span>
          <span class="text-zinc-200">${it.rejim || 'İthalat'}</span>
        </div>
        <div class="glass-card p-2.5">
          <span class="text-zinc-400 block text-[10px] uppercase font-semibold">Kalem / Tutar</span>
          <span class="font-mono-code text-sky-400">${it.kalem_sayisi || 1} Kalem ${it.fatura_tutar ? '| ' + it.fatura_tutar + ' ' + it.fatura_doviz : ''}</span>
        </div>
      </div>

      ${it.aciklama ? `
        <div class="glass-card p-2.5">
          <span class="text-zinc-400 block text-[10px] uppercase font-semibold">Operasyonel Not</span>
          <p class="text-zinc-300 text-[11px] mt-0.5">${it.aciklama}</p>
        </div>
      ` : ''}
    </div>

    <div class="pt-3 border-t border-white/10 flex space-x-2">
      <button onclick="copyToClipboard('${it.dosya_no}')" class="flex-1 py-2.5 rounded-xl bg-zinc-800 text-white font-semibold text-xs border border-white/10 active:scale-95 transition-all">
        Dosya No Kopyala
      </button>
      <button onclick="copyToClipboard('${it.beyanname_no || it.referans_no}')" class="flex-1 py-2.5 rounded-xl bg-sky-600 text-white font-semibold text-xs active:scale-95 transition-all">
        Beyanname Kopyala
      </button>
    </div>
  `;

  backdrop.classList.add('open');
  sheet.classList.add('open');
}

function closeDetailSheet() {
  triggerHaptic();
  document.getElementById('bottom-sheet').classList.remove('open');
  document.getElementById('bottom-sheet-backdrop').classList.remove('open');
}

function copyToClipboard(text) {
  if (!text) return;
  triggerHaptic('success');
  navigator.clipboard.writeText(text);
  if (tg?.showAlert) {
    tg.showAlert(`Kopyalandı: ${text}`);
  } else {
    alert(`Kopyalandı: ${text}`);
  }
}

// ── YENİLEME VE BAŞLATMA ─────────────────────────────────────────────────────

function refreshData() {
  triggerHaptic('medium');
  const ind = document.getElementById('live-indicator');
  ind.textContent = 'Yenileniyor...';

  Promise.all([fetchStats(), fetchCockpit(), fetchHorizon(), fetchKantarAndGTB()]).then(() => {
    ind.textContent = 'Canlı';
  });
}

// İlk Yükleme
document.addEventListener('DOMContentLoaded', () => {
  fetchStats();
  fetchCockpit();

  // 25 saniyede bir otomatik arka plan senkronizasyonu
  setInterval(() => {
    fetchStats();
    if (state.currentTab === 'cockpit') fetchCockpit();
  }, 25000);
});
