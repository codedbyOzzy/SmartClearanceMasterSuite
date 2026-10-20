/* ==========================================================================
   chat_hub.js — SmartClearance WhatsApp Web & Teams Hibrit Motoru (v65)
   AJAX Polling (5s) | Emoji & GIF | @Bahsetme | PO Bağlam Kartı | Grup Kartları
   ========================================================================== */
"use strict";

const POLL_ARALIK_MS = 5000;
const EMOJILER = [
    "😊","😂","👍","🙌","🔥","✅","❌","⚠️","📎","📋","🚀","💡",
    "🎯","📦","🛳️","✈️","📞","💬","📝","🔔","⏰","📅","💰","🏆",
    "👀","🤝","😅","🙏","💪","🎉","🔍","📊","⚡","🌟","📌","🔑",
];
const MENTION_LISTESI = [];
const GONDEREN_RENKLERI = ["#60A5FA", "#F472B6", "#34D399", "#FBBF24", "#A78BFA", "#38BDF8"];

let aktifKanalId = null;
let sonMesajId   = 0;
let pollTimer    = null;
let mevcutKullanici = null;
let baglamAcik   = false;

function avatarHarf(isim) {
    return (isim || "?").trim().charAt(0).toUpperCase();
}

function avatarRenkIndis(isim) {
    const s = (isim || "").trim();
    let sum = 0;
    for (let i = 0; i < s.length; i++) sum += s.charCodeAt(i);
    return Math.abs(sum) % GONDEREN_RENKLERI.length;
}

function zamanBicimle(iso) {
    if (!iso) return "";
    try {
        const d = new Date(iso.replace(" ", "T"));
        const simdi = new Date();
        const fark = Math.floor((simdi - d) / 60000);
        if (fark < 1)  return "az önce";
        if (fark < 60) return `${fark} dk`;
        if (fark < 1440) {
            const h = Math.floor(fark / 60), m = fark % 60;
            return `${h} sa önce`.trim();
        }
        return d.toLocaleDateString("tr-TR", { day:"2-digit", month:"short", hour:"2-digit", minute:"2-digit" });
    } catch { return iso.substring(0, 16); }
}

function xssTemizle(str) {
    const d = document.createElement("div");
    d.textContent = str || "";
    return d.innerHTML;
}

function bahsetmeVurgula(html) {
    return html.replace(/@([\wÇçĞğİıÖöŞşÜü]+)/g,
        '<span style="color:#FF4B5C;font-weight:700;">@$1</span>');
}

// ── Teams / WhatsApp Tarzı Zengin Mesaj ve Kart Biçimlendirme ─────────────────
function zenginMesajBicimle(metin, yazan = "") {
    if (!metin) return "";

    const aksiBtn = (s) => s.replace(/\[PO-AKSIYON:([A-Za-z0-9_.-]+)\]/gi,
        `<div class="ai-actions" style="margin: 6px 0;">
            <button onclick="window._asistanPeekAc('$1')" class="chat-kart-btn" style="color: #38bdf8;">👁️ Hızlı Gözat</button>
            <button onclick="window._asistanTalepAc('$1')" class="chat-kart-btn" style="color: #10b981;">📋 Talep Aç</button>
            <button onclick="window.location.href='/muhasebe-takip?po=$1'" class="chat-kart-btn" style="color: #f59e0b;">💰 Muhasebe</button>
            <button onclick="window.location.href='/takip-raporu/$1'" class="chat-kart-btn" style="color: #a855f7;">📂 Detaya Git</button>
        </div>`
    );

    // 0. Eğer AI Kartı ise (server-rendered raw HTML), rozet regexlerine ve XSS filtrelerine sokmadan sadece butonları aktifleştir ve döndür:
    if (metin.includes('<div class="ai-card') || metin.includes('<div class="po-bildirim-kart')) {
        return aksiBtn(metin);
    }

    let str = xssTemizle(metin);
    str = bahsetmeVurgula(str);

    // 1. Önce [PO-AKSIYON:PO_NO] butonlarını dönüştür (XSS temizliğinden hemen sonra!)
    str = aksiBtn(str);

    // 2. PO numarası ve Referans rozetleri (PO-AKSIYON ile çakışmaması için (?!AKSIYON) negative lookahead kullandık!)
    str = str.replace(/(PO-(?!AKSIYON)[A-Z0-9-]+|PO:\s*([A-Z0-9-]+)|\b\d{7}\b)/gi,
        '<span class="chat-rozet-po" onclick="chatPoOzetModal(\'$1\')" style="background:linear-gradient(135deg,rgba(59,130,246,0.25),rgba(30,58,138,0.45));border:1px solid #3b82f6;color:#60a5fa;padding:3px 9px;border-radius:8px;font-weight:700;font-size:0.84rem;display:inline-block;margin:2px 0;cursor:pointer;" title="Canlı dosya ve operasyon durumunu gör">📦 $1</span>');
    
    str = str.replace(/(Dosya Referansı:\s*[A-Z0-9-]+|Referans:\s*[A-Z0-9-]+|\b\d{2}-\d{6}\b)/gi,
        '<span class="chat-rozet-ref" onclick="chatPoOzetModal(\'$1\')" style="background:linear-gradient(135deg,rgba(16,185,129,0.22),rgba(6,78,59,0.45));border:1px solid #10b981;color:#34d399;padding:3px 9px;border-radius:8px;font-weight:700;font-size:0.84rem;display:inline-block;margin:2px 0;cursor:pointer;" title="Canlı dosya ve operasyon durumunu gör">📂 $1</span>');

    // 2. İşlemi Yapan / Kişi satırı
    str = str.replace(/([👤👤]\s*İşlemi Yapan:\s*[^\n]+)/gi,
        '<div style="color:#e2e8f0;font-weight:600;margin:5px 0;display:flex;align-items:center;gap:6px;background:rgba(255,255,255,0.05);padding:5px 10px;border-radius:8px;border-left:3px solid #6366f1;">$1</div>');

    // 3. Açıklama / Not satırları
    str = str.replace(/(💬\s*Açıklama:\s*[^\n]+|💬\s*Not:\s*[^\n]+)/gi,
        '<div style="background:rgba(255,255,255,0.06);border-left:3px solid #f59e0b;padding:8px 12px;border-radius:0 8px 8px 0;margin:6px 0;color:#f8fafc;font-style:italic;">$1</div>');

    // 4. Kalın yazı (**metin** -> <strong>metin</strong>)
    str = str.replace(/\*\*([^*]+)\*\*/g, '<strong style="color:#fff;font-weight:700;">$1</strong>');

    // 5. Satır kesmeleri (pre-wrap ile şık paragraf düzeni)
    return `<div class="chat-mesaj-metin-body" style="white-space: pre-wrap; word-break: break-word; line-height: 1.6; font-size: 0.92rem; color: #F1F5F9;">${str}</div>`;
}

// ── WhatsApp & Teams Tarzı Mesaj Satırı ──────────────────────────────────────
function mesajHtmlOlustur(m, benim, okunduId = 0) {
    const yon = benim ? "benim" : "";
    const sistemMesajiMi = m.yazan === "🤖 Sistem" || (m.metin && m.metin.includes("PO için işlem kaydedildi"));
    const aksiyonlar = (benim && !sistemMesajiMi)
        ? `<div class="chat-balon-aksiyonlar">
             <button class="chat-aksiyon-btn" onclick="chatDuzenleAc(${m.id}, this)" title="Düzenle">✎</button>
             <button class="chat-aksiyon-btn tehlikeli" onclick="chatMesajSil(${m.id})" title="Sil">🗑</button>
           </div>`
        : (!sistemMesajiMi
            ? `<div class="chat-balon-aksiyonlar">
                 <button class="chat-aksiyon-btn" title="Yanıtla (@Bahset)" onclick="chatMentionEkle('${xssTemizle(m.yazan)}')">↩</button>
               </div>`
            : ``);

    const gifHtml = m.gif_url
        ? `<img src="${xssTemizle(m.gif_url)}" alt="GIF" class="chat-balon-gif">`
        : "";

    const dosyaHtml = (m.dosyalar || []).map(d =>
        `<a href="/ekip-akisi/konu/${aktifKanalId}/dosya/${d.id}" class="chat-balon-dosya" target="_blank">
           📎 ${xssTemizle(d.dosya_adi)}
         </a>`
    ).join("");

    const renkIdx = avatarRenkIndis(m.yazan);
    const isimRenk = GONDEREN_RENKLERI[renkIdx];

    const tikHtml = benim
        ? (okunduId && m.id <= okunduId
            ? `<span class="chat-tik okundu" title="Okundu (Ekip tarafından görüldü)" style="color:#38bdf8;font-weight:700;">✓✓</span>`
            : `<span class="chat-tik teslim" title="Teslim Edildi (Sunucuya ulaştı)" style="color:#94a3b8;">✓</span>`)
        : ``;

    const botSinif = (m.metin && m.metin.includes("class=\"ai-card\"")) ? " bot-mesaj" : "";

    return `<div class="chat-mesaj-satir ${yon}" id="msg-${m.id}" data-mid="${m.id}">
      <div class="chat-balon-avatar avatar-c${renkIdx + 1}">${avatarHarf(m.yazan)}</div>
      <div class="chat-balon-kutu">
        <div class="chat-balon${botSinif}">
          ${aksiyonlar}
          <div class="chat-balon-gonderen" style="color:${isimRenk}">${xssTemizle(m.yazan)}</div>
          ${(m.gif_url && (!m.metin || m.metin === "📎 GIF" || m.metin === "GIF" || m.metin === "📎")) ? "" : `<div class="chat-mesaj-metin-${m.id}">${zenginMesajBicimle(m.metin, m.yazan)}</div>`}
          <form id="chat-duzenle-form-${m.id}" class="chat-duzenleme-alani" style="display:none;"
                method="post" action="/ekip-akisi/konu/${aktifKanalId}/mesaj-duzenle/${m.id}">
             <textarea name="metin" rows="2">${xssTemizle(m.metin)}</textarea>
             <div class="chat-duzenleme-btns">
               <button type="submit" class="chat-duzenleme-btn kaydet">✓ Kaydet</button>
               <button type="button" class="chat-duzenleme-btn" onclick="chatDuzenlemeKapat(${m.id})">Vazgeç</button>
             </div>
          </form>
          ${gifHtml}${dosyaHtml}
          <div class="chat-balon-alt">
            <span>${zamanBicimle(m.zaman)}</span>
            ${tikHtml}
          </div>
        </div>
      </div>
    </div>`;
}

// ── Kanal Mesajlarını Yükle ──────────────────────────────────────────────────
async function kanalMesajlariYukle(kanalId, ilkYukleme = false) {
    const akis = document.getElementById("chat-mesaj-akis");
    if (!akis) return;
    try {
        const url = `/ekip-akisi/api/konu/${kanalId}/mesajlar?son_id=${ilkYukleme ? 0 : sonMesajId}`;
        const resp = await fetch(url);
        if (!resp.ok) return;
        const data = await resp.json();

        const baslik = data.konu_baslik || "";
        const baslikLow = baslik.toLowerCase();
        const sistemGrupMu = baslikLow.includes("sistem-islem") || baslikLow.includes("takip-değişim") || baslikLow.includes("takip-degisim") || baslikLow.includes("gtb-beyanname") || baslikLow.includes("gemi-eta") || baslikLow.includes("eta-ve-liman") || baslikLow.includes("sistem-") || baslikLow.includes("rapor-değişim");
        const ta = document.getElementById("chat-mesaj-textarea");
        const solBtn = document.querySelector(".chat-giris-butonlar-sol");
        const sendBtn = document.querySelector(".chat-gonder-btn");
        if (ta) {
            if (sistemGrupMu) {
                ta.disabled = true;
                ta.placeholder = "🔒 Bu resmi sistem bildirim kanalı salt okunurdur. Mesaj, dosya veya emoji gönderilemez.";
                ta.style.background = "rgba(15, 23, 42, 0.85)";
                ta.style.cursor = "not-allowed";
                if (solBtn) solBtn.style.display = "none";
                if (sendBtn) sendBtn.style.display = "none";
                document.querySelectorAll(".chat-emoji-picker, .chat-gif-picker, #chat-gif-onizleme, #chat-dosya-onizleme").forEach(el => el.style.display = "none");
            } else {
                ta.disabled = false;
                ta.placeholder = "Bu gruba mesaj yazın... (@İsim ile bahset, Enter = gönder, Shift+Enter = yeni satır)";
                ta.style.background = "";
                if (solBtn) solBtn.style.display = "";
                if (sendBtn) sendBtn.style.display = "";
            }
        }

        // Okundu bilgisini sol listeden ve ekrandan temizle/güncelle
        const aktifKartRozet = document.querySelector(`.chat-grup-kart[data-kanal-id="${kanalId}"] .chat-kanal-rozet`);
        if (aktifKartRozet) aktifKartRozet.style.display = "none";

        const okunduId = data.okundu_id || 0;
        document.querySelectorAll(".chat-tik.teslim").forEach(el => {
            const row = el.closest(".chat-mesaj-satir");
            if (row && parseInt(row.dataset.mid || 0) <= okunduId) {
                el.className = "chat-tik okundu";
                el.title = "Okundu (Ekip tarafından görüldü)";
                el.innerHTML = "✓✓";
                el.style.color = "#38bdf8";
                el.style.fontWeight = "700";
            }
        });

        if (ilkYukleme) {
            akis.innerHTML = "";
            const baslikEl = document.getElementById("chat-kanal-baslik");
            const avatarEl = document.getElementById("chat-header-avatar");
            const altEl = document.getElementById("chat-mesaj-sayi");
            if (baslikEl && data.konu_baslik) {
                baslikEl.textContent = data.konu_baslik;
            }
            if (avatarEl && data.konu_baslik) {
                avatarEl.textContent = data.konu_baslik.substring(0, 2).toUpperCase();
                avatarEl.className = `chat-grup-avatar header-avatar avatar-c${(kanalId % 6) + 1}`;
            }
            if (altEl) {
                const adet = (data.mesajlar || []).length;
                altEl.textContent = `🟢 Çevrimiçi · ${adet} mesaj · Gümrük İş Akışı`;
            }
            if (!data.mesajlar?.length) {
                akis.innerHTML = `
                  <div class="chat-bos-durum">
                    <div class="chat-bos-ic">💬</div>
                    <h3>Sohbete Başlayın</h3>
                    <p>Bu grupta henüz mesaj bulunmuyor. İlk mesajınızı aşağıdan yazarak grubun akışını başlatın.</p>
                  </div>`;
                return;
            }
        }

        if (!data.mesajlar?.length) return;
        const altaYakindi = akis.scrollHeight - akis.scrollTop - akis.clientHeight < 140;

        // Mesajları ekle
        data.mesajlar.forEach(m => {
            if (document.getElementById(`msg-${m.id}`)) return;
            if (m.id > sonMesajId) sonMesajId = m.id;
            const benim = mevcutKullanici && m.yazan === mevcutKullanici;
            akis.insertAdjacentHTML("beforeend", mesajHtmlOlustur(m, benim, okunduId));
        });

        if (altaYakindi || ilkYukleme) {
            akis.scrollTo({ top: akis.scrollHeight, behavior: ilkYukleme ? "auto" : "smooth" });
        }
    } catch (e) {
        console.warn("[ChatHub] Mesaj yüklenemedi:", e);
    }
}

// ── AJAX Polling ─────────────────────────────────────────────────────────────
function pollingBaslat(kanalId) {
    pollingDurdur();
    pollTimer = setInterval(() => {
        if (aktifKanalId === kanalId) kanalMesajlariYukle(kanalId);
    }, POLL_ARALIK_MS);
}
function pollingDurdur() {
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
}

// ── Grup (Kanal) Seç ──────────────────────────────────────────────────────────
async function kanalSec(kanalId) {
    if (!kanalId) return;
    pollingDurdur();
    aktifKanalId = kanalId;
    sonMesajId   = 0;

    document.querySelectorAll(".chat-grup-kart").forEach(el => {
        el.classList.toggle("aktif", parseInt(el.dataset.kanalId) === kanalId);
    });

    const akis = document.getElementById("chat-mesaj-akis");
    if (akis) {
        akis.innerHTML = `<div class="chat-bos-durum"><div class="chat-bos-ic">💬</div><h3>Grup Sohbeti Yükleniyor…</h3></div>`;
    }

    const form = document.getElementById("chat-mesaj-form");
    if (form) form.action = `/ekip-akisi/konu/${kanalId}/mesaj`;

    await kanalMesajlariYukle(kanalId, true);
    baglamPaneliGuncelle(kanalId);
    pollingBaslat(kanalId);
    history.replaceState(null, "", `/ekip-akisi#${kanalId}`);
}

// ── Bağlam Paneli (Grup Bilgisi & Ekler) ─────────────────────────────────────
async function baglamPaneliGuncelle(kanalId) {
    const panel = document.getElementById("chat-baglam-icerik");
    if (!panel) return;
    try {
        const resp = await fetch(`/ekip-akisi/api/konu/${kanalId}/mesajlar?son_id=0`);
        if (!resp.ok) return;
        const data = await resp.json();

        const baslik = data.konu_baslik || "";
        const baslikLow = baslik.toLowerCase();
        const sistemGrupMu = baslikLow.includes("sistem-islem") || baslikLow.includes("takip-değişim") || baslikLow.includes("takip-degisim") || baslikLow.includes("gtb-beyanname") || baslikLow.includes("gemi-eta") || baslikLow.includes("eta-ve-liman") || baslikLow.includes("sistem-") || baslikLow.includes("rapor-değişim");
        
        const yonetimKutu = document.getElementById("chat-grup-yonetim-kutu");
        if (yonetimKutu) {
            if (sistemGrupMu) {
                yonetimKutu.innerHTML = `
                  <div style="background:rgba(239,68,68,0.12);border:1px solid rgba(239,68,68,0.35);border-radius:12px;padding:12px;color:#fca5a5;font-size:0.83rem;">
                    <div style="font-weight:700;margin-bottom:5px;display:flex;align-items:center;gap:6px;color:#f87171;">
                      🔒 Sabit Sistem Akışı (Salt Okunur)
                    </div>
                    Bu kanal sistem tarafından otomatik bildirim yayınlamak amacıyla kilitlenmiştir. Kullanıcı mesajlarına, evrak/dosya veya emoji yüklenmesine kapalıdır.
                  </div>`;
            } else {
                const aiOtomatikChecked = (data.ai_otomatik !== 0 && data.ai_otomatik !== false) ? 'checked' : '';
                yonetimKutu.innerHTML = `
                  <div class="chat-ekler-baslik" style="margin-bottom:10px;">⚙️ Grup Yönetimi</div>
                  <form id="chat-grup-ad-form" method="POST" action="/ekip-akisi/konu/${kanalId}/ad-degistir" style="display:flex;gap:6px;margin-bottom:12px;">
                    <input type="text" id="chat-grup-ad-input" name="yeni_baslik" value="${xssTemizle(baslik)}" required
                           placeholder="Grup adı..." style="flex:1;background:rgba(255,255,255,0.06);border:1px solid #334155;border-radius:10px;padding:6px 10px;color:#fff;font-size:0.85rem;">
                    <button type="submit" class="chat-po-ara-btn" style="background:#10b981;font-size:0.8rem;padding:6px 12px;">Kaydet</button>
                  </form>
                  <div class="ai-grup-ayar-box" style="margin:10px 0;padding:10px 12px;background:rgba(59, 130, 246, 0.08);border:1px solid rgba(59, 130, 246, 0.28);border-radius:10px;display:flex;align-items:center;justify-content:space-between;box-shadow:0 2px 8px rgba(0,0,0,0.15);">
                    <div style="display:flex;align-items:center;gap:10px;">
                      <div style="width:32px;height:32px;border-radius:8px;background:linear-gradient(135deg, #3B82F6, #1D4ED8);display:flex;align-items:center;justify-content:center;font-size:16px;color:#fff;box-shadow:0 2px 6px rgba(59,130,246,0.3);">🤖</div>
                      <div>
                        <div style="font-size:0.82rem;font-weight:700;color:#f8fafc;letter-spacing:-0.2px;">AI Otomatik Referans Yanıtı</div>
                        <div style="font-size:0.72rem;color:#94a3b8;line-height:1.3;">Sohbette PO / Dosya no geçince AI bilgi versin</div>
                      </div>
                    </div>
                    <label class="ai-toggle-switch" style="position:relative;display:inline-block;width:46px;height:24px;cursor:pointer;flex-shrink:0;">
                      <input type="checkbox" id="ai-otomatik-yanit-toggle" class="ai-toggle-input" ${aiOtomatikChecked} onchange="aiOtomatikYanitAyarla(${kanalId}, this.checked)" style="opacity:0;width:0;height:0;">
                      <span class="ai-toggle-slider" style="position:absolute;top:0;left:0;right:0;bottom:0;background-color:#475569;border-radius:24px;transition:.3s;border:2px solid rgba(255,255,255,0.1);">
                        <span class="ai-toggle-dot" style="position:absolute;content:'';height:16px;width:16px;left:2px;bottom:2px;background-color:white;border-radius:50%;transition:.3s;box-shadow:0 1px 3px rgba(0,0,0,0.3);"></span>
                      </span>
                    </label>
                  </div>
                  <div style="display:flex;gap:8px;margin-top:4px;">
                    <button type="button" class="btn-grup-temizle" onclick="sohbetiTemizle()" style="flex:1;background:rgba(234, 179, 8, 0.15);color:#facc15;border:1px solid rgba(234, 179, 8, 0.4);padding:8px 10px;border-radius:6px;cursor:pointer;font-weight:600;display:flex;align-items:center;justify-content:center;gap:6px;transition:all 0.2s;font-size:0.82rem;" title="Grup kalır, yalnızca içindeki mesajlar ve ekler temizlenir">🧹 Sohbeti Temizle</button>
                    <button type="button" class="btn-grup-sil" onclick="grupSil()" style="flex:1;margin:0;">🗑️ Grubu Sil</button>
                  </div>`;
            }
        }

        const tumEkler = [];
        (data.mesajlar || []).forEach(m => {
            (m.dosyalar || []).forEach(d => {
                tumEkler.push({ ...d, mesaj_id: m.id });
            });
        });

        const eklerEl = document.getElementById("chat-baglam-ekler");
        if (eklerEl) {
            if (tumEkler.length) {
                eklerEl.innerHTML = tumEkler.map(d =>
                    `<a href="/ekip-akisi/konu/${kanalId}/dosya/${d.id}" class="chat-ek-item" target="_blank" style="display:block;padding:8px;background:rgba(255,255,255,0.06);border-radius:10px;margin-bottom:6px;color:#fff;text-decoration:none;font-size:0.82rem;">
                       📎 ${xssTemizle(d.dosya_adi)}
                     </a>`
                ).join("");
            } else {
                eklerEl.innerHTML = `<span style="font-size:0.78rem;color:#64748B;">Henüz paylaşılan dosya yok.</span>`;
            }
        }
    } catch (e) {}
}

// ── PO Kartı Arama ───────────────────────────────────────────────────────────
async function poAra() {
    const input = document.getElementById("chat-po-ara-input");
    const kart  = document.getElementById("chat-po-kart-alani");
    if (!input || !kart) return;
    const po = input.value.trim();
    if (!po) return;

    kart.innerHTML = `<div style="font-size:0.78rem;color:#64748B;">PO Sorgulanıyor…</div>`;
    try {
        const resp = await fetch(`/takip-raporu/api/durum?referans_no=${encodeURIComponent(po)}`);
        if (!resp.ok) throw new Error("Bulunamadı");
        const data = await resp.json();
        if (!data || !data.referans_no) throw new Error("Kayıt yok");
        kart.innerHTML = `
          <div class="chat-po-kart">
            <div class="chat-po-kart-baslik">📦 ${xssTemizle(data.referans_no)}</div>
            ${poSatir("Dosya No", data.dosya_no)}
            ${poSatir("Bayi", data.bayi)}
            ${poSatir("Gümrük", data.gumruk)}
            ${poSatir("Hat Bilgisi", data.hat_bilgisi)}
            ${poSatir("Konteyner", data.konteyner)}
            ${poSatir("Kapanış", data.kapanis_tarihi || "—")}
            <a href="/takip-raporu/${encodeURIComponent(data.referans_no)}" 
               style="display:inline-block;margin-top:10px;font-size:0.78rem;font-weight:700;color:#FF4B5C;text-decoration:none;" target="_blank">
              → Gümrük Raporuna Git
            </a>
          </div>`;
    } catch (e) {
        kart.innerHTML = `<div style="font-size:0.78rem;color:#FF4B5C;">PO bulunamadı.</div>`;
    }
}

function poSatir(etiket, deger) {
    if (!deger) return "";
    return `<div class="chat-po-kart-satir">
              <span style="font-weight:700;color:#CBD5E1;">${etiket}:</span> ${xssTemizle(String(deger))}
            </div>`;
}

// ── Emoji Picker ─────────────────────────────────────────────────────────────
function emojiPickerOlustur() {
    const picker = document.getElementById("chat-emoji-picker");
    if (!picker || picker._dolduruldu) return;
    picker._dolduruldu = true;
    picker.innerHTML = EMOJILER.map(e =>
        `<button class="chat-emoji-btn" data-emoji="${e}" title="${e}">${e}</button>`
    ).join("");
    picker.querySelectorAll(".chat-emoji-btn").forEach(btn => {
        btn.addEventListener("click", e => {
            e.stopPropagation();
            const ta = document.getElementById("chat-mesaj-textarea");
            if (ta) {
                ta.value += btn.dataset.emoji;
                ta.focus();
                textareaOtoYukseklik(ta);
            }
        });
    });
}

function emojiToggle(e) {
    e.stopPropagation();
    const picker = document.getElementById("chat-emoji-picker");
    if (!picker) return;
    emojiPickerOlustur();
    picker.classList.toggle("acik");
    document.getElementById("chat-gif-picker")?.classList.remove("acik");
}

// ── @Bahsetme ────────────────────────────────────────────────────────────────
function mentionKontrol(textarea) {
    const val = textarea.value;
    const pos = textarea.selectionStart;
    const oncesiText = val.substring(0, pos);
    const match = oncesiText.match(/@(\w*)$/);
    const dropdown = document.getElementById("chat-mention-dropdown");
    if (!dropdown) return;

    if (match && MENTION_LISTESI.length) {
        const aranan = match[1].toLowerCase();
        const eslesmeler = MENTION_LISTESI.filter(k =>
            k.toLowerCase().includes(aranan)
        );
        if (eslesmeler.length) {
            dropdown.innerHTML = eslesmeler.map(k =>
                `<div class="chat-mention-item" data-isim="${k}">
                   <div class="chat-balon-avatar avatar-c1" style="width:24px;height:24px;font-size:0.7rem;">${avatarHarf(k)}</div>
                   ${xssTemizle(k)}
                 </div>`
            ).join("");
            dropdown.querySelectorAll(".chat-mention-item").forEach(item => {
                item.addEventListener("click", () => {
                    chatMentionEkle(item.dataset.isim);
                    dropdown.classList.remove("acik");
                });
            });
            dropdown.classList.add("acik");
            return;
        }
    }
    dropdown.classList.remove("acik");
}

window.chatMentionEkle = function(isim) {
    const ta = document.getElementById("chat-mesaj-textarea");
    if (!ta) return;
    const pos = ta.selectionStart;
    const oncesi = ta.value.substring(0, pos).replace(/@\w*$/, "");
    ta.value = oncesi + `@${isim} ` + ta.value.substring(pos);
    ta.focus();
};

// ── /? AI Komutları Yukarı Açılır Hover Popover Menu ─────────────────────────
const AI_KOMUT_LISTESI = [
    { komut: "/ai", etiket: "/ai [soru/konu]", aciklama: "🤖 AI Asistanına serbest operasyonel veya gümrük sorusu sorun (Örn: /ai 4200806399 neden bekliyor?)" },
    { komut: "/po", etiket: "/po [PO_NO]", aciklama: "📦 PO numarasına ait 360° Excel Röntgeni, lojistik bilgileri ve 5 aşamalı gümrük yaşantısı" },
    { komut: "/ozet", etiket: "/ozet", aciklama: "📊 Sistemdeki tüm dosya, hat (Kırmızı/Sarı/Yeşil) ve iş takip durumunun anlık genel özeti" },
    { komut: "/darbogaz", etiket: "/darbogaz", aciklama: "⚠️ Kırmızı hat beklemeleri, muhasebe sevk gecikmeleri ve riskli dosya anormallik denetimi" },
    { komut: "/kirmizi", etiket: "/kirmizi", aciklama: "🔴 Kırmızı hatta olan tüm dosyaların listesi ve risk durum analizi" },
    { komut: "/bayi", etiket: "/bayi [Bayi_Adı]", aciklama: "🏢 Belirli bir bayiye ait (Örn: HANKOOK) aktif dosyaların performans analizi" },
    { komut: "/talep", etiket: "/talep [PO_NO]", aciklama: "📋 İlgili PO için hızlı ve otomatik bir ekip işlem talebi açın" },
    { komut: "/?", etiket: "/?", aciklama: "💡 Tüm AI komutlarının listesini ve rehberini sohbete yazın" }
];

function aiKomutMenuKontrol(textarea) {
    const val = (textarea.value || "").trimStart();
    const dropdown = document.getElementById("chat-ai-komut-dropdown");
    if (!dropdown) return;

    if (val.startsWith("/") && val.length <= 15) {
        const arama = val.split(" ")[0].toLocaleLowerCase("tr");
        const filtreli = AI_KOMUT_LISTESI.filter(k => k.komut.startsWith(arama) || arama === "/?" || arama === "/");
        if (filtreli.length > 0) {
            dropdown.innerHTML = filtreli.map(k => `
                <div class="chat-ai-komut-item" onclick="window.aiKomutSec('${k.komut}')">
                    <div class="komut-baslik">⚡ <code>${k.etiket}</code></div>
                    <div class="komut-aciklama">${k.aciklama}</div>
                </div>
            `).join("");
            dropdown.classList.add("acik");
            return;
        }
    }
    dropdown.classList.remove("acik");
}

window.aiKomutSec = function(komut) {
    const ta = document.getElementById("chat-mesaj-textarea");
    const dropdown = document.getElementById("chat-ai-komut-dropdown");
    if (ta) {
        ta.value = komut + " ";
        ta.focus();
    }
    if (dropdown) dropdown.classList.remove("acik");
};

// ── Mesaj Düzenleme & Silme ──────────────────────────────────────────────────
window.chatDuzenleAc = function(mesajId, btn) {
    const form = document.getElementById(`chat-duzenle-form-${mesajId}`);
    const span = document.querySelector(`.chat-mesaj-metin-${mesajId}`);
    if (!form || !span) return;
    form.style.display = "block";
    span.style.display = "none";
};
window.chatDuzenlemeKapat = function(mesajId) {
    const form = document.getElementById(`chat-duzenle-form-${mesajId}`);
    const span = document.querySelector(`.chat-mesaj-metin-${mesajId}`);
    if (!form || !span) return;
    form.style.display = "none";
    span.style.display = "";
};
window.chatMesajSil = function(mesajId) {
    if (!confirm("Bu mesajı silmek istediğinize emin misiniz?")) return;
    const form = document.createElement("form");
    form.method = "post";
    form.action = `/ekip-akisi/konu/${aktifKanalId}/mesaj-sil/${mesajId}`;
    document.body.appendChild(form);
    form.submit();
};

// ── Textarea Otomatik Yükseklik ──────────────────────────────────────────────
function textareaOtoYukseklik(ta) {
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 140) + "px";
}

// ── Grup Listesini Dinamik Çek ───────────────────────────────────────────────
async function kanalListesiYukle() {
    try {
        const resp = await fetch("/ekip-akisi/api/kanallar");
        if (!resp.ok) return;
        const data = await resp.json();
        (data.kanallar || []).forEach(k => {
            const el = document.querySelector(`.chat-grup-kart[data-kanal-id="${k.id}"]`);
            if (el) {
                const rozet = el.querySelector(".chat-kanal-rozet");
                const zaman = el.querySelector(".chat-grup-saat");
                const onizleme = el.querySelector(".chat-grup-onizleme");
                if (rozet) {
                    if (k.id === aktifKanalId) {
                        rozet.style.display = "none";
                    } else if (k.okunmamis_sayisi > 0) {
                        rozet.textContent = k.okunmamis_sayisi;
                        rozet.style.display = "";
                    } else {
                        rozet.style.display = "none";
                    }
                }
                if (zaman && k.son_zaman) zaman.textContent = zamanBicimle(k.son_zaman);
                if (onizleme) {
                    const kim = k.son_yazan ? `<b>${xssTemizle(k.son_yazan)}:</b> ` : "";
                    onizleme.innerHTML = kim + xssTemizle(k.son_metin || "Sohbet başladı...");
                }
            }
            if (k.acan_isim && !MENTION_LISTESI.includes(k.acan_isim)) {
                MENTION_LISTESI.push(k.acan_isim);
            }
        });
    } catch (e) {}
}

// ── Başlat ───────────────────────────────────────────────────────────────────
function chatHubBaslat() {
    const ta = document.getElementById("chat-mesaj-textarea");
    if (ta) {
        ta.addEventListener("input", () => {
            textareaOtoYukseklik(ta);
            mentionKontrol(ta);
            aiKomutMenuKontrol(ta);
        });
        ta.addEventListener("keydown", e => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                document.getElementById("chat-mesaj-form")?.requestSubmit();
            }
        });
    }

    const baglamBtn = document.getElementById("chat-baglam-toggle");
    if (baglamBtn) {
        baglamBtn.addEventListener("click", () => {
            baglamAcik = !baglamAcik;
            const panel = document.getElementById("chat-baglam-panel");
            panel?.classList.toggle("acik", baglamAcik);
        });
    }

    const emojiBtn = document.getElementById("chat-emoji-toggle");
    if (emojiBtn) emojiBtn.addEventListener("click", emojiToggle);

    const gifBtn = document.getElementById("chat-gif-toggle");
    if (gifBtn) {
        gifBtn.addEventListener("click", e => {
            e.stopPropagation();
            const picker = document.getElementById("chat-gif-picker");
            if (!picker) return;
            const acik = picker.classList.toggle("acik");
            document.getElementById("chat-emoji-picker")?.classList.remove("acik");
            if (acik && window.ChatGif && !picker._ilkYukleme) {
                picker._ilkYukleme = true;
                window.ChatGif.baslat("chat-gif-picker");
            }
        });
    }

    // Dosya butonu işleyicisi
    const dosyaBtn = document.getElementById("chat-dosya-btn");
    const dosyaInput = document.getElementById("chat-dosya-input");
    const dosyaOnizleme = document.getElementById("chat-dosya-onizleme");
    const dosyaAdSpan = document.getElementById("chat-dosya-onizleme-ad");
    const dosyaKapatBtn = document.getElementById("chat-dosya-onizleme-kapat-btn");

    if (dosyaBtn && dosyaInput) {
        dosyaBtn.addEventListener("click", () => dosyaInput.click());
        dosyaInput.addEventListener("change", () => {
            if (dosyaInput.files && dosyaInput.files.length > 0) {
                const isimler = Array.from(dosyaInput.files).map(f => f.name).join(", ");
                if (dosyaAdSpan) dosyaAdSpan.textContent = `📎 ${isimler}`;
                if (dosyaOnizleme) dosyaOnizleme.style.display = "inline-flex";
            }
        });
    }
    if (dosyaKapatBtn && dosyaInput) {
        dosyaKapatBtn.addEventListener("click", () => {
            dosyaInput.value = "";
            if (dosyaOnizleme) dosyaOnizleme.style.display = "none";
        });
    }

    document.querySelectorAll(".chat-grup-kart[data-kanal-id]").forEach(item => {
        item.addEventListener("click", e => {
            e.preventDefault();
            const idVal = item.dataset.kanalId;
            if (idVal === "__akis__") {
                window.location.href = "/ekip-akisi";
                return;
            }
            kanalSec(parseInt(idVal));
        });
    });

    const gifKapatBtn = document.querySelector("#chat-gif-onizleme-kapat-btn");
    if (gifKapatBtn) gifKapatBtn.addEventListener("click", () => {
        window.ChatGif?.temizle();
    });

    window.ChatGif?.baslat("chat-gif-picker");

    document.addEventListener("click", e => {
        if (!e.target.closest(".chat-emoji-picker") && !e.target.closest("#chat-emoji-toggle")) {
            document.getElementById("chat-emoji-picker")?.classList.remove("acik");
        }
        if (!e.target.closest(".chat-gif-picker") && !e.target.closest("#chat-gif-toggle") && !e.target.closest(".chat-ic-btn[data-picker='gif']")) {
            document.getElementById("chat-gif-picker")?.classList.remove("acik");
        }
        if (!e.target.closest(".chat-mention-dropdown")) {
            document.getElementById("chat-mention-dropdown")?.classList.remove("acik");
        }
        if (!e.target.closest(".chat-ai-komut-dropdown")) {
            document.getElementById("chat-ai-komut-dropdown")?.classList.remove("acik");
        }
    });

    const userData = document.getElementById("chat-dock");
    if (userData) mevcutKullanici = userData.dataset.kullanici || null;

    const hashMatch = location.hash.match(/^#(\d+)$/);
    const hashKanalId = hashMatch ? parseInt(hashMatch[1]) : null;

    kanalListesiYukle();

    const ilkKanal = document.querySelector(".chat-grup-kart[data-kanal-id]:not(.genel-akis-kart)");
    const baslangicId = hashKanalId || (ilkKanal ? parseInt(ilkKanal.dataset.kanalId) : null);
    if (baslangicId) {
        kanalSec(baslangicId);
    }

    window.addEventListener("focus", () => {
        if (aktifKanalId) {
            fetch(`/ekip-akisi/api/konu/${aktifKanalId}/okundu`, { method: "POST" });
            kanalMesajlariYukle(aktifKanalId);
            kanalListesiYukle();
        }
    });
    document.addEventListener("visibilitychange", () => {
        if (!document.hidden && aktifKanalId) {
            fetch(`/ekip-akisi/api/konu/${aktifKanalId}/okundu`, { method: "POST" });
            kanalMesajlariYukle(aktifKanalId);
            kanalListesiYukle();
        }
    });
}

// ── Global ve PJAX Etkinleştirme ─────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
    if (document.getElementById("chat-dock")) chatHubBaslat();
});
document.addEventListener("pjax:success", () => {
    if (document.getElementById("chat-dock")) chatHubBaslat();
});
function grupSil() {
    if (!aktifKanalId) return;
    if (!confirm("Bu grubu ve içindeki tüm mesajları/ekleri silmek istediğinizden emin misiniz?")) return;
    const form = document.createElement("form");
    form.method = "POST";
    form.action = `/ekip-akisi/konu/${aktifKanalId}/sil`;
    document.body.appendChild(form);
    form.submit();
}
function sohbetiTemizle() {
    if (!aktifKanalId) return;
    if (!confirm("Bu gruptaki tüm sohbet geçmişi (mesajlar ve ekler) kalıcı olarak silinecek. Emin misiniz?")) return;
    const form = document.createElement("form");
    form.method = "POST";
    form.action = `/ekip-akisi/konu/${aktifKanalId}/sohbet-temizle`;
    document.body.appendChild(form);
    form.submit();
}
async function aiOtomatikYanitAyarla(kanalId, durum) {
    if (!kanalId && aktifKanalId) kanalId = aktifKanalId;
    if (!kanalId) return;
    try {
        const res = await fetch(`/ekip-akisi/konu/${kanalId}/ai-otomatik-ayarla`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ durum: durum ? 1 : 0 })
        });
        const data = await res.json();
        if (data && data.success) {
            const el = document.getElementById("ai-otomatik-yanit-toggle");
            if (el) el.checked = !!data.durum;
        }
    } catch (e) {
        console.error("AI otomatik yanıt ayarı güncellenemedi:", e);
    }
}
window.aiOtomatikYanitAyarla = aiOtomatikYanitAyarla;

// ── Sol Panel Grup Arama ─────────────────────────────────────────────────────
window.chatGrupAra = function(arama) {
    const kelime = (arama || "").trim().toLocaleLowerCase("tr");
    document.querySelectorAll(".chat-grup-kart").forEach(kart => {
        const ad = kart.querySelector(".chat-grup-ad")?.textContent || "";
        const son = kart.querySelector(".chat-grup-onizleme")?.textContent || "";
        const tumu = (ad + " " + son).toLocaleLowerCase("tr");
        if (!kelime || tumu.includes(kelime)) {
            kart.style.display = "";
        } else {
            kart.style.display = "none";
        }
    });
};

// ── Sağ Panel Mesaj İçi Arama ────────────────────────────────────────────────
window.chatMesajIciAra = function(arama) {
    const kelime = (arama || "").trim().toLocaleLowerCase("tr");
    const satirlar = document.querySelectorAll(".chat-mesaj-satir");
    let buldu = false;

    satirlar.forEach(satir => {
        const metinEl = satir.querySelector('[class^="chat-mesaj-metin-"]');
        const gonderenEl = satir.querySelector(".chat-balon-gonderen");
        const icerik = ((metinEl?.textContent || "") + " " + (gonderenEl?.textContent || "")).toLocaleLowerCase("tr");

        if (!kelime || icerik.includes(kelime)) {
            satir.style.display = "";
            satir.style.opacity = "1";
            buldu = true;
            if (kelime) {
                satir.style.boxShadow = "0 0 0 2px #3B82F6, 0 4px 16px rgba(59,130,246,0.3)";
                satir.style.borderRadius = "12px";
            } else {
                satir.style.boxShadow = "";
            }
        } else {
            satir.style.display = "none";
            satir.style.boxShadow = "";
        }
    });

    // Sonuç bulunamazsa bilgi ver
    const akis = document.getElementById("chat-mesaj-akis");
    let bosUyari = document.getElementById("chat-ara-bos-uyari");
    if (!buldu && kelime && satirlar.length > 0) {
        if (!bosUyari) {
            bosUyari = document.createElement("div");
            bosUyari.id = "chat-ara-bos-uyari";
            bosUyari.className = "chat-bos-durum";
            bosUyari.innerHTML = `<div class="chat-bos-ic">🔍</div><h3>Sonuç Bulunamadı</h3><p>"${xssTemizle(arama)}" ifadesine uygun mesaj yok.</p>`;
            akis?.appendChild(bosUyari);
        } else {
            bosUyari.innerHTML = `<div class="chat-bos-ic">🔍</div><h3>Sonuç Bulunamadı</h3><p>"${xssTemizle(arama)}" ifadesine uygun mesaj yok.</p>`;
            bosUyari.style.display = "";
        }
    } else if (bosUyari) {
        bosUyari.style.display = "none";
    }
};

// ── Canlı Gümrük & Muhasebe PO Özet Modalı ───────────────────────────────────
window.chatPoOzetModal = async function(sorgu) {
    const temiz = (sorgu || "").replace(/^(PO-|PO:\s*|Dosya Referansı:\s*|Referans:\s*)/i, "").trim();
    if (!temiz) return;

    let modal = document.getElementById("chat-po-modal");
    if (!modal) {
        modal = document.createElement("div");
        modal.id = "chat-po-modal";
        modal.className = "chat-konu-modal-overlay acik";
        modal.innerHTML = `
          <div class="chat-konu-modal" style="max-width:520px;border:1px solid rgba(59,130,246,0.4);background:#0F172A;">
            <div class="chat-modal-header" style="border-bottom:1px solid rgba(255,255,255,0.1);padding-bottom:12px;">
              <h3 style="color:#60A5FA;display:flex;align-items:center;gap:8px;">
                <span>⚡ CANLI DOSYA & PO OPERASYON KARTI</span>
              </h3>
              <button type="button" class="chat-modal-kapat-ic" onclick="document.getElementById('chat-po-modal').classList.remove('acik')">✕</button>
            </div>
            <div id="chat-po-modal-ic" style="padding:16px 0;color:#E2E8F0;font-size:0.92rem;min-height:120px;">
              <div style="text-align:center;padding:20px;color:#94A3B8;">⌛ Canlı gümrük ve muhasebe durumu sorgulanıyor...</div>
            </div>
            <div class="chat-konu-modal-btns" style="border-top:1px solid rgba(255,255,255,0.1);padding-top:12px;">
              <button type="button" class="button-ghost" onclick="document.getElementById('chat-po-modal').classList.remove('acik')">Kapat</button>
              <button type="button" class="btn-kirmizi" id="chat-po-sohbete-gonder-btn" style="background:#3B82F6;">💬 Sohbete Özet Paylaş</button>
            </div>
          </div>`;
        document.body.appendChild(modal);
    } else {
        modal.classList.add("acik");
    }

    const ic = document.getElementById("chat-po-modal-ic");
    const btn = document.getElementById("chat-po-sohbete-gonder-btn");
    ic.innerHTML = `<div style="text-align:center;padding:20px;color:#94A3B8;">⌛ Canlı gümrük ve muhasebe durumu sorgulanıyor...</div>`;

    try {
        const resp = await fetch(`/ekip-akisi/api/po-ozet?q=${encodeURIComponent(temiz)}`);
        const data = await resp.json();

        let islemHtml = "";
        if (data.islem_kayitlari && data.islem_kayitlari.length > 0) {
            islemHtml = data.islem_kayitlari.map(ik =>
                `<div style="background:rgba(255,255,255,0.04);padding:8px 10px;border-radius:6px;margin-top:6px;border-left:3px solid #6366F1;font-size:0.85rem;">
                   <b style="color:#A5B4FC;">[${ik.zaman || ""} - ${xssTemizle(ik.yazan || "")}]:</b> ${xssTemizle(ik.aciklama || ik.tur || "")}
                 </div>`
            ).join("");
        } else {
            islemHtml = `<div style="color:#64748B;font-size:0.85rem;margin-top:4px;">Henüz ekip işlemi girilmemiş.</div>`;
        }

        ic.innerHTML = `
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px;">
            <div style="background:rgba(59,130,246,0.12);padding:10px;border-radius:8px;border:1px solid rgba(59,130,246,0.3);">
              <div style="color:#94A3B8;font-size:0.75rem;text-transform:uppercase;">PO NUMARASI</div>
              <div style="color:#60A5FA;font-weight:700;font-size:1.1rem;">${xssTemizle(data.po_no || temiz)}</div>
            </div>
            <div style="background:rgba(16,185,129,0.12);padding:10px;border-radius:8px;border:1px solid rgba(16,185,129,0.3);">
              <div style="color:#94A3B8;font-size:0.75rem;text-transform:uppercase;">DOSYA NO</div>
              <div style="color:#34D399;font-weight:700;font-size:1.1rem;">${xssTemizle(data.dosya_no || "-")}</div>
            </div>
          </div>
          <div style="background:rgba(255,255,255,0.03);padding:12px;border-radius:8px;margin-bottom:12px;">
            <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
              <span>🏢 <b>Bayi:</b> ${xssTemizle(data.bayi || "Belirtilmemiş")}</span>
              <span>🏛️ <b>Gümrük:</b> ${xssTemizle(data.gumruk || "-")}</span>
            </div>
            <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
              <span>🚦 <b>Hat:</b> <b style="color:#FBBF24;">${xssTemizle(data.hat || "-")}</b></span>
              <span>💰 <b>Muhasebe:</b> ${xssTemizle(data.muhasebe_durum || "-")}</span>
            </div>
            <div style="margin-top:8px;padding-top:8px;border-top:1px dashed rgba(255,255,255,0.1);">
              <span>📈 <b>Gümrük Son Durumu:</b> <span style="color:#38BDF8;font-weight:600;">${xssTemizle(data.durum || "Kayıt bulunamadı")}</span></span>
            </div>
          </div>
          <div>
            <div style="font-weight:700;color:#F1F5F9;font-size:0.88rem;">📋 Son İşlem Kayıtları</div>
            ${islemHtml}
          </div>`;

        btn.onclick = () => {
            const input = document.getElementById("chat-mesaj-input");
            if (input) {
                input.value = `/po ${data.po_no || temiz}`;
                document.getElementById("chat-mesaj-gonder-btn")?.click();
                modal.classList.remove("acik");
            }
        };
    } catch (e) {
        ic.innerHTML = `<div style="color:#EF4444;text-align:center;padding:20px;">Durum bilgisi alınamadı.</div>`;
    }
};

window.ChatHub = { poAra, grupSil, sohbetiTemizle, chatGrupAra, chatMesajIciAra, chatPoOzetModal, aiOtomatikYanitAyarla };

// ── SmartClearance AI Etkileşimli Eylem Butonu İşlevleri (Sürüm v80) ─────────
window._asistanPeekAc = function(poNo) {
    if (typeof chatPoOzetModal === 'function') {
        chatPoOzetModal(poNo);
    } else if (typeof openPeekDrawer === 'function') {
        openPeekDrawer(poNo);
    } else {
        window.location.href = '/takip-raporu/' + poNo;
    }
};

window._asistanTalepAc = function(poNo) {
    const notTxt = prompt("📋 '" + poNo + "' için Dosya Açma Talebi oluşturulacak.\nİsteğe bağlı bir açıklama / not yazabilirsiniz:");
    if (notTxt === null) return; // İptale basıldı
    
    const fd = new FormData();
    fd.append("po_numaralari", poNo);
    fd.append("not_metni", notTxt || "Ekip akışı üzerinden AI butonuyla hızlı talep oluşturuldu.");

    fetch("/talepler/yeni", {
        method: "POST",
        body: fd
    })
    .then(r => {
        if (r.ok || r.status === 303 || r.status === 200) {
            alert("✅ " + poNo + " için talep başarıyla oluşturuldu!\n(Bildirim #Sistem-Islem-Kayitlari kanalına da gönderildi)");
        } else {
            alert("⚠️ Talep oluşturulurken sunucudan beklenmeyen bir yanıt alındı.");
        }
    })
    .catch(err => {
        alert("❌ Talep bağlantı hatası: " + err);
    });
};



