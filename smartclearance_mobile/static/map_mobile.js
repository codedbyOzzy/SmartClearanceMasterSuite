// ==============================================================================
// 🚢 HORIZON MOBILE MARITIME RADAR (LEAFLET DARK TILES)
// ==============================================================================

let mobileMap = null;
let vesselMarkers = [];
let routePolyline = null;

function initMobileMap() {
  if (mobileMap) return;
  const container = document.getElementById('mobile-map-container');
  if (!container) return;

  // Harita başlatma (Akdeniz & Türkiye merkezli)
  mobileMap = L.map('mobile-map-container', {
    center: [38.5, 27.5],
    zoom: 5,
    zoomControl: false,
    attributionControl: false
  });

  // Koyu Obsidian Deniz Haritası Katmanı (CartoDB Dark Matter)
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 18,
    subdomains: 'abcd'
  }).addTo(mobileMap);

  // Mobil için sağ üste küçük zoom kontrolleri
  L.control.zoom({ position: 'topright' }).addTo(mobileMap);

  // Resize adaptasyonu
  setTimeout(() => {
    mobileMap.invalidateSize();
  }, 300);
}

function renderVesselsOnMap(vessels) {
  if (!mobileMap) initMobileMap();
  if (!mobileMap) return;

  // Eski işaretçileri temizle
  vesselMarkers.forEach(m => mobileMap.removeLayer(m));
  vesselMarkers = [];

  const validBounds = [];

  vessels.forEach(v => {
    if (!v.coords || !Array.isArray(v.coords)) return;
    const lat = v.coords[0];
    const lng = v.coords[1];
    if (isNaN(lat) || isNaN(lng)) return;

    validBounds.push([lat, lng]);

    // Özel Parlayan İkon
    const customIcon = L.divIcon({
      className: 'custom-vessel-div',
      html: `<div class="vessel-marker-pin">${v.flag || '🚢'}</div>`,
      iconSize: [28, 28],
      iconAnchor: [14, 14],
      popupAnchor: [0, -14]
    });

    const marker = L.marker([lat, lng], { icon: customIcon }).addTo(mobileMap);

    // Popup içeriği (Dark glassmorphism)
    const popupHtml = `
      <div style="background:#090d16; color:#f8fafc; border-radius:12px; padding:10px; font-family:-apple-system,sans-serif; min-width:180px; border:1px solid rgba(255,255,255,0.15);">
        <div style="font-weight:700; font-size:13px; color:#38bdf8; display:flex; align-items:center; gap:5px;">
          <span>${v.flag || '🚢'}</span> <span>${v.vessel || 'Bilinmeyen Gemi'}</span>
        </div>
        <div style="font-size:11px; color:#94a3b8; margin-top:3px;">Acente: <b>${v.carrier || '—'}</b></div>
        <div style="font-size:11px; color:#94a3b8;">Konteyner: <span style="font-family:monospace; color:#e2e8f0;">${v.container_no || '—'}</span></div>
        <div style="margin-top:6px; padding-top:6px; border-top:1px solid rgba(255,255,255,0.1); display:flex; justify-content:space-between; align-items:center;">
          <span style="font-size:10px; color:#64748b;">ETA: ${v.live_eta || v.excel_eta || '—'}</span>
          <span style="font-size:11px; font-weight:700; color:#34d399;">${v.kalan_gun || ''}</span>
        </div>
      </div>
    `;

    marker.bindPopup(popupHtml, {
      className: 'dark-glass-popup',
      closeButton: false
    });

    marker.on('click', () => {
      triggerHaptic();
      mobileMap.flyTo([lat, lng], 8, { duration: 0.8 });
    });

    vesselMarkers.push(marker);
  });

  // Tüm gemileri kapsayacak şekilde haritayı otomatik sığdır
  if (validBounds.length > 1) {
    try {
      mobileMap.fitBounds(validBounds, { padding: [30, 30], maxZoom: 7 });
    } catch(e) {}
  }
}

function flyToVessel(lat, lng, vesselName) {
  if (!mobileMap) return;
  triggerHaptic();
  mobileMap.flyTo([lat, lng], 8, { duration: 1.0 });

  // İlgili işaretçinin popup'ını aç
  vesselMarkers.forEach(m => {
    const pos = m.getLatLng();
    if (Math.abs(pos.lat - lat) < 0.001 && Math.abs(pos.lng - lng) < 0.001) {
      m.openPopup();
    }
  });

  // Harita alanına yumuşak kaydır
  const mapEl = document.getElementById('mobile-map-container');
  if (mapEl) {
    mapEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
}
