// gtb_takip.js — GTB Otonom Beyanname Takibi ve Canlı Bakanlık Sorgusu Sayfa Kontrolcüsü (Glassmorphism UI)

let tumBeyannameler = [];

function initGtbTakipSayfasi() {
  const gtbTablo = document.getElementById("beyanname-tablo-govde");
  if (!gtbTablo) return; // GTB Takip sayfasında değilsek işlem yapma
  listeyiYenile(false);
}

// Sayfa ilk açıldığında veya PJAX navigasyonundan sonra otomatik çalıştır
document.addEventListener("DOMContentLoaded", initGtbTakipSayfasi);
document.addEventListener("pjax:success", initGtbTakipSayfasi);

window.listeyiYenile = async function(gosterBildirim = false) {
  const gtbTablo = document.getElementById("beyanname-tablo-govde");
  if (!gtbTablo) return;

  try {
    const res = await fetch("/api/gtb/takip/listele?sadece_aktif=true", {
      cache: "no-store",
      headers: { "Cache-Control": "no-cache", "Pragma": "no-cache" }
    });
    const data = await res.json();
    if (data.success) {
      tumBeyannameler = data.beyannameler || [];
      tabloyuCiz(tumBeyannameler);
      istatistikleriGuncelle(tumBeyannameler);
      const saat = new Date().toLocaleTimeString("tr-TR");
      const saatEl = document.getElementById("son-guncelleme-saat");
      if (saatEl) saatEl.textContent = "Son Yenileme: " + saat;
      if (gosterBildirim) {
        showToast("Liste başarıyla yenilendi.", "ok");
      }
    }
  } catch (err) {
    console.error("GTB listesi alınırken hata:", err);
  }
};

function istatistikleriGuncelle(liste) {
  let islemde = 0;
  let tamamlandi = 0;
  liste.forEach(item => {
    const durumMetni = (item.durum || item.son_durum || "").toLowerCase();
    if (item.kapanma_tarihi || durumMetni.includes("kapanm") || durumMetni.includes("tamamlan")) {
      tamamlandi++;
    } else {
      islemde++;
    }
  });
  
  // Count up animation logic
  animateValue("ozet-toplam", parseInt(document.getElementById("ozet-toplam")?.innerText || 0), liste.length, 500);
  animateValue("ozet-islemde", parseInt(document.getElementById("ozet-islemde")?.innerText || 0), islemde, 500);
  animateValue("ozet-tamamlandi", parseInt(document.getElementById("ozet-tamamlandi")?.innerText || 0), tamamlandi, 500);
}

function animateValue(id, start, end, duration) {
    if (start === end) return;
    const obj = document.getElementById(id);
    if (!obj) return;
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        obj.innerHTML = Math.floor(progress * (end - start) + start);
        if (progress < 1) {
            window.requestAnimationFrame(step);
        } else {
            obj.innerHTML = end;
        }
    };
    window.requestAnimationFrame(step);
}

function tabloyuCiz(liste) {
  const tbody = document.getElementById("beyanname-tablo-govde");
  if (!tbody) return;

  if (!liste || liste.length === 0) {
    tbody.innerHTML = `
      <tr class="fade-in">
        <td colspan="5" style="text-align: center; padding: 60px 0; color: #64748b; background: transparent !important; border: none !important;">
          <div style="font-size: 3rem; margin-bottom: 12px; filter: drop-shadow(0 4px 6px rgba(0,0,0,0.05));">📭</div>
          <div style="font-size: 1.1rem; font-weight: 500;">Henüz takip listesinde beyanname bulunmuyor.</div>
          <div style="font-size: 0.95rem; margin-top: 8px;">Sol panelden ekleyebilirsiniz.</div>
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = liste.map((item, index) => {
    let durumMetni = item.durum || item.son_durum || "Bekleniyor...";
    let rozetSinifi = "st-pill";

    if (item.kapanma_tarihi || durumMetni.toLowerCase().includes("kapanm") || durumMetni.toLowerCase().includes("tamamlan")) {
      rozetSinifi = "st-pill st-tamam";
    } else if (durumMetni.toLowerCase().includes("işlemde") || durumMetni.toLowerCase().includes("islemde") || durumMetni.toLowerCase().includes("bekliyor")) {
      rozetSinifi = "st-pill st-islemde";
    } else {
      rozetSinifi = "st-pill st-hata"; // varsayılan
    }

    const zamanMetni = item.son_kontrol_zamani || item.son_kontrol || item.durum_degisim_tarihi || "Kontrol Edilmedi";
    const ekleyenMetni = item.ekleyen_kullanici || "Sistem";
    const delay = index * 0.05; // Staggered fade in

    return `
      <tr class="fade-in" style="animation-delay: ${delay}s;">
        <td>
          <strong style="font-family: monospace; font-size: 1.05rem; color: #1e293b; letter-spacing: 0.03em;">${item.beyanname_no}</strong>
        </td>
        <td>
          <span class="${rozetSinifi}">
            <span class="dot"></span>
            <span>${durumMetni}</span>
          </span>
        </td>
        <td style="color: #64748b; font-size: 0.9rem;">
          ${zamanMetni}
        </td>
        <td>
          <span style="display:inline-block; padding:4px 10px; background:#f1f5f9; color:#475569; border-radius:8px; font-size:0.85rem; font-weight:600;">${ekleyenMetni}</span>
        </td>
        <td style="text-align: center; white-space: nowrap;">
          <button type="button" class="btn-action" style="color: #3b82f6;" title="Canlı Sorgula" onclick="canliSorgula('${item.beyanname_no}')">🔍</button>
          <button type="button" class="btn-action red" style="color: #ef4444;" title="Takipten Çıkar" onclick="takiptenSil('${item.beyanname_no}')">✕</button>
        </td>
      </tr>
    `;
  }).join('');
}

window.topluTakibeEkle = async function(btnEl) {
  const metinEl = document.getElementById("txt-beyannameler");
  if (!metinEl) return;
  const metin = metinEl.value.trim();
  if (!metin) {
    showToast("Lütfen en az bir beyanname numarası girin.", "err");
    return;
  }

  const btn = btnEl || document.querySelector("button[onclick*='topluTakibeEkle']");
  const originalHtml = btn ? btn.innerHTML : "Ekle";
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner" style="width:20px;height:20px;border-width:2px;margin:0;"></span> <span>Ekleniyor...</span>`;
  }

  try {
    const res = await fetch("/api/gtb/takip/ekle", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        beyannameler: metin,
        ekleyen_kullanici: "Otonom"
      })
    });
    const data = await res.json();
    const eklenenAdet = data.eklenen_sayisi || data.eklenen || 0;
    if (data.success && eklenenAdet > 0) {
      showToast(`${eklenenAdet} adet beyanname takibe eklendi!`, "ok");
      metinEl.value = "";
      await listeyiYenile(true);
      
      const ilkEklenen = (data.eklenenler && data.eklenenler[0]) ? data.eklenenler[0] : null;
      if (ilkEklenen) {
        canliSorgula(ilkEklenen);
      } else {
        tumunuKontrolEt(true);
      }
    } else {
      showToast(data.error || "Geçerli bir beyanname numarası bulunamadı.", "err");
    }
  } catch (err) {
    showToast("Bağlantı hatası: " + err, "err");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = originalHtml;
    }
  }
};

window.takiptenSil = async function(beyannameNo) {
  if (!confirm(`${beyannameNo} numaralı beyannameyi takipten çıkarmak istediğinize emin misiniz?`)) return;
  try {
    const res = await fetch(`/api/gtb/takip/sil/${beyannameNo}`, { method: "POST" });
    const data = await res.json();
    if (data.success) {
      showToast("Beyanname takipten kaldırıldı.", "ok");
      listeyiYenile(false);
    }
  } catch (err) {
    showToast("Silme hatası.", "err");
  }
};

window.tumunuKontrolEt = async function(sessiz = false) {
  if (!sessiz) {
    showToast("Bakanlık sistemi taranıyor, otonom süreç başladı...", "ok");
  }
  try {
    const res = await fetch("/api/gtb/takip/kontrol-et", { method: "POST" });
    const data = await res.json();
    if (data.success) {
      if (!sessiz) {
        showToast("Tüm beyannameler başarıyla sorgulandı!", "ok");
      }
      listeyiYenile(false);
    }
  } catch (err) {
    if (!sessiz) {
      showToast("Kontrol sırasında hata oluştu.", "err");
    }
  }
};

window.acCanliModal = function() {
  const overlay = document.getElementById("modalCanliSonuc");
  if (overlay) overlay.classList.add("acik");
};

window.kapatCanliModal = function() {
  const overlay = document.getElementById("modalCanliSonuc");
  if (overlay) overlay.classList.remove("acik");
};

window.canliSorgula = async function(no) {
  acCanliModal();
  const icerik = document.getElementById("canli-sorgu-icerik");
  
  const yukleniyorHtml = `
    <div class="spinner" style="width: 50px; height: 50px; border-width: 4px; border-top-color: #3b82f6; border-right-color: rgba(59,130,246,0.2); border-bottom-color: rgba(59,130,246,0.2); border-left-color: rgba(59,130,246,0.2); animation: spin 1s linear infinite; margin-bottom: 20px;"></div>
    <h4 style="margin: 0 0 12px 0; font-family: monospace; font-size: 1.5rem; color:#1e293b;">${no}</h4>
    <p style="color:#64748b; font-size: 1.05rem;">Bakanlık sunucusuna otonom bağlanılıyor...</p>
    <div style="background: rgba(59, 130, 246, 0.1); color: #3b82f6; display: inline-block; padding: 6px 12px; border-radius: 999px; font-size: 0.85rem; font-weight: 600; margin-top: 12px;">Yapay zeka captcha'yı çözüyor...</div>
  `;
  
  if (icerik) icerik.innerHTML = yukleniyorHtml;

  try {
    const res = await fetch(`/api/gtb/takip/sorgula/${no}`);
    const data = await res.json();
    
    if (data.success) {
      let pillSinif = "st-pill";
      if (data.kapandi || data.durum.toLowerCase().includes("kapanm")) {
        pillSinif = "st-pill st-tamam";
      } else if (data.durum.toLowerCase().includes("işlemde") || data.durum.toLowerCase().includes("bekliyor")) {
        pillSinif = "st-pill st-islemde";
      } else {
        pillSinif = "st-pill st-hata";
      }

      const basariliHtml = `
        <div style="animation: fadeInRow 0.4s ease-out;">
          <div style="font-size: 3.5rem; margin-bottom: 12px; line-height:1;">✅</div>
          <h4 style="margin: 0 0 16px 0; font-family: monospace; font-size: 1.4rem; color: #1e293b;">${no}</h4>
          
          <div style="display:inline-flex; align-items:center; justify-content:center; gap:8px; padding:12px 24px; background:#f8fafc; border:1px solid #e2e8f0; border-radius:16px; margin-bottom:20px; box-shadow:inset 0 2px 4px rgba(0,0,0,0.02);">
             <span class="${pillSinif}" style="font-size: 1.05rem;">
               <span class="dot"></span> ${data.durum}
             </span>
          </div>
          
          <div style="background: rgba(241, 245, 249, 0.8); border: 1px solid #e2e8f0; border-radius: 16px; padding: 16px; text-align: left; font-size: 0.95rem; color:#475569;">
            <div style="display:flex; justify-content:space-between; margin-bottom:8px; border-bottom:1px solid #e2e8f0; padding-bottom:8px;">
              <strong>Detaylı Durum:</strong> <span>${data.durum}</span>
            </div>
            <div style="display:flex; justify-content:space-between;">
              <strong>Canlı Sorgu:</strong> <span>${new Date().toLocaleTimeString("tr-TR")}</span>
            </div>
          </div>
        </div>
      `;
      if (icerik) icerik.innerHTML = basariliHtml;
      listeyiYenile(false);
    } else {
      const hataHtml = `
        <div style="animation: fadeInRow 0.4s ease-out;">
          <div style="font-size: 3.5rem; margin-bottom: 12px; line-height:1;">❌</div>
          <h4 style="color: #ef4444; margin: 0 0 12px 0; font-size:1.3rem;">Bağlantı veya Captcha Hatası</h4>
          <p style="color: #64748b; font-size:1rem; padding: 0 20px;">${data.error || "Güvenlik kodu çözülemedi veya bakanlık sunucusu yanıt vermedi. Lütfen birazdan tekrar deneyin."}</p>
        </div>
      `;
      if (icerik) icerik.innerHTML = hataHtml;
    }
  } catch (err) {
    const baglantiHataHtml = `
      <div style="animation: fadeInRow 0.4s ease-out;">
        <div style="font-size: 3.5rem; margin-bottom: 12px; line-height:1;">⚠️</div>
        <h4 style="color: #f59e0b; margin: 0 0 12px 0; font-size:1.3rem;">Sunucu Bağlantı Hatası</h4>
        <p style="color: #64748b; font-size:1rem;">İnternet bağlantınızda veya lokal sunucuda geçici bir kesinti oluştu.</p>
      </div>
    `;
    if (icerik) icerik.innerHTML = baglantiHataHtml;
  }
};

window.tekliAnlikSorgula = function() {
  const metinEl = document.getElementById("txt-beyannameler");
  if (!metinEl) return;
  const metin = metinEl.value.trim();
  const ilkNo = metin.split(/[\r\n,]/)[0].trim();
  if (!ilkNo || ilkNo.length < 10) {
    showToast("Lütfen kutuya geçerli bir beyanname numarası yazın.", "err");
    return;
  }
  canliSorgula(ilkNo);
};

// Toast notification (Modernized)
function showToast(mesaj, tip="ok") {
  const div = document.createElement("div");
  div.style.position = "fixed";
  div.style.bottom = "24px";
  div.style.right = "24px";
  div.style.zIndex = "999999";
  div.style.padding = "16px 24px";
  div.style.borderRadius = "12px";
  div.style.boxShadow = "0 10px 40px -10px rgba(0,0,0,0.3)";
  div.style.color = "white";
  div.style.fontWeight = "600";
  div.style.fontSize = "1rem";
  div.style.display = "flex";
  div.style.alignItems = "center";
  div.style.gap = "12px";
  div.style.transform = "translateY(100px)";
  div.style.opacity = "0";
  div.style.transition = "all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275)";
  
  if (tip === "err") {
    div.style.background = "linear-gradient(135deg, #ef4444, #dc2626)";
    div.innerHTML = `<span style="font-size:1.4rem;line-height:1;">⚠️</span> <span>${mesaj}</span>`;
  } else {
    div.style.background = "linear-gradient(135deg, #10b981, #059669)";
    div.innerHTML = `<span style="font-size:1.4rem;line-height:1;">✅</span> <span>${mesaj}</span>`;
  }
  
  document.body.appendChild(div);
  
  // Animate in
  setTimeout(() => {
    div.style.transform = "translateY(0)";
    div.style.opacity = "1";
  }, 50);
  
  // Animate out
  setTimeout(() => {
    div.style.transform = "translateY(20px)";
    div.style.opacity = "0";
    setTimeout(() => div.remove(), 400);
  }, 4000);
}
