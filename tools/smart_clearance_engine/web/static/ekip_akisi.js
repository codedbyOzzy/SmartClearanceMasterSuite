/* ==========================================================================
   ekip_akisi.js — SmartClearance Ekip Akışı v2.0
   ES6 Class Mimarisi | AJAX Polling | Feed | Sohbet | Bağlam Paneli
   ========================================================================== */
"use strict";

const EA_POLL_MS = 5000;
const EA_KANAL_POLL_MS = 15000;
const EA_EMOJILER = [
  "😊","😂","👍","🙌","🔥","✅","❌","⚠️","📎","📋","🚀","💡",
  "🎯","📦","🛳️","✈️","📞","💬","📝","🔔","⏰","📅","💰","🏆",
  "👀","🤝","😅","🙏","💪","🎉","🔍","📊","⚡","🌟","📌","🔑",
];
const EA_RENKLER = ["#3b82f6","#8b5cf6","#f59e0b","#ef4444","#ec4899","#0ea5e9","#10b981","#6366f1"];

// ── Yardımcılar ──────────────────────────────────────────────────────────────
function xss(str) {
  const d = document.createElement("div");
  d.textContent = str ?? "";
  return d.innerHTML;
}

function zamanAgo(iso) {
  if (!iso) return "";
  try {
    const d = new Date(iso.replace(" ", "T"));
    const diff = Math.floor((Date.now() - d) / 60000);
    if (diff < 1)    return "şimdi";
    if (diff < 60)   return `${diff} dk`;
    if (diff < 1440) return `${Math.floor(diff / 60)} sa`;
    const gun = Math.floor(diff / 1440);
    if (gun < 7) return `${gun} gün`;
    return d.toLocaleDateString("tr-TR", { day: "2-digit", month: "short" });
  } catch { return iso.substring(0, 10); }
}

function avatarRenk(isim) {
  let s = 0;
  for (const ch of (isim || "")) s += ch.charCodeAt(0);
  return EA_RENKLER[Math.abs(s) % EA_RENKLER.length];
}

function avatarHarf(isim) {
  return (isim || "?").trim().replace(/[^\p{L}]/gu, "").charAt(0).toUpperCase() || "?";
}

// ── MesajFormatlayici ─────────────────────────────────────────────────────────
const MesajFmt = {
  isle(metin, yazan) {
    if (!metin) return "";
    // Ham HTML (AI kartları)
    if (metin.includes('<div class="ai-card') || metin.includes('<div class="po-bildirim-kart')) {
      return metin.replace(/\[PO-AKSIYON:([A-Za-z0-9_.\-]+)\]/gi, (_, po) =>
        `<div style="display:flex;gap:6px;flex-wrap:wrap;margin:6px 0;">
          <button onclick="eaPoModal('${po}')" style="background:rgba(56,189,248,0.12);border:1px solid #38bdf8;color:#38bdf8;padding:4px 10px;border-radius:6px;font-size:0.78rem;font-weight:700;cursor:pointer;font-family:inherit;">👁️ Gözat</button>
          <button onclick="location.href='/muhasebe-takip?po=${po}'" style="background:rgba(245,158,11,0.12);border:1px solid #f59e0b;color:#fcd34d;padding:4px 10px;border-radius:6px;font-size:0.78rem;font-weight:700;cursor:pointer;font-family:inherit;">💰 Muhasebe</button>
          <button onclick="location.href='/takip-raporu/${po}'" style="background:rgba(168,85,247,0.12);border:1px solid #a855f7;color:#c4b5fd;padding:4px 10px;border-radius:6px;font-size:0.78rem;font-weight:700;cursor:pointer;font-family:inherit;">📂 Detay</button>
        </div>`
      );
    }

    let s = xss(metin);

    // @mention vurgu
    s = s.replace(/@([\wÇçĞğİıÖöŞşÜü]+)/g, '<span class="ea-mention">@$1</span>');

    // PO numarası rozeti (42XXXXXXXX veya XX-XXXXXX)
    s = s.replace(/\b(42\d{8})\b/g,
      `<span class="ea-po-badge" onclick="eaPoModal('$1')" title="Canlı durum">📦 $1</span>`);
    s = s.replace(/\b(\d{2}-\d{6})\b/g,
      `<span class="ea-ref-badge" onclick="eaPoModal('$1')" title="Canlı durum">📂 $1</span>`);

    // **kalın**
    s = s.replace(/\*\*([^*\n]+)\*\*/g, '<strong style="color:#fff;font-weight:800;">$1</strong>');
    // *italik*
    s = s.replace(/\*([^*\n]+)\*/g, '<em>$1</em>');

    return `<div style="white-space:pre-wrap;word-break:break-word;line-height:1.6;">${s}</div>`;
  }
};

// ── KanalListesi ──────────────────────────────────────────────────────────────
class KanalListesi {
  constructor(el) {
    this.el = el;
    this.aktifId = null;
  }

  render(kanallar, aktifId) {
    this.aktifId = aktifId;
    const ekip = kanallar.filter(k => !this._sistemMi(k.baslik));
    const sistem = kanallar.filter(k => this._sistemMi(k.baslik));
    let h = "";
    if (ekip.length)   h += `<div class="ea-section-lbl">💬 Ekip Sohbetleri</div>${ekip.map(k => this._kart(k)).join("")}`;
    if (sistem.length) h += `<div class="ea-section-lbl">🤖 Sistem Kanalları</div>${sistem.map(k => this._sistemKart(k)).join("")}`;
    if (!h) h = `<div style="text-align:center;padding:28px 16px;color:var(--ea-text-dim);font-size:0.85rem;">Henüz grup yok.<br><br><button onclick="EA.modalAc()" style="background:rgba(255,255,255,0.07);border:1px solid var(--ea-border);color:var(--ea-text-muted);padding:7px 14px;border-radius:8px;cursor:pointer;font-family:inherit;font-size:0.82rem;">+ İlk Grubu Kur</button></div>`;
    this.el.innerHTML = h;
  }

  _sistemMi(b) { return b && (b.startsWith("📢 #") || b.startsWith("🤖")); }

  _robotTip(b) {
    if (b.includes("GTB")) return "gtb";
    if (b.includes("ETA") || b.includes("Gemi")) return "eta";
    if (b.includes("Kantar")) return "kantar";
    return "sistem";
  }

  _avSinif(id) { return `ea-av-${(id % 6) + 1}`; }

  _kart(k) {
    const aktif = k.id == this.aktifId ? "aktif" : "";
    const kapali = k.durum === "kapatildi" ? "kapali" : "";
    const z = zamanAgo(k.son_zaman || k.son_hareket_zamani);
    const oniz = k.son_yazan
      ? `<b>${xss(k.son_yazan)}:</b> ${xss(k.son_metin || "")}`
      : xss(k.son_metin || "Sohbet başladı");
    const rozet = k.okunmamis_sayisi > 0
      ? `<span class="ea-badge" id="ea-rz-${k.id}">${k.okunmamis_sayisi}</span>`
      : `<span class="ea-badge" id="ea-rz-${k.id}" style="display:none">0</span>`;
    const avH = (k.baslik || "").replace(/[^\p{L}]/gu, "").substring(0, 2).toUpperCase() || "?";
    return `
      <div class="ea-ch ${aktif} ${kapali}" data-id="${k.id}" data-q="${xss(k.baslik).toLowerCase()}"
           onclick="EA.kanalSec(${k.id})" title="${xss(k.baslik)}${kapali ? ' (Kapalı)' : ''}">
        <div class="ea-ch-av ${this._avSinif(k.id)}">${avH}</div>
        <div class="ea-ch-info">
          <div class="ea-ch-row1">
            <span class="ea-ch-name">${xss(k.baslik)}</span>
            <span class="ea-ch-time" id="ea-zt-${k.id}">${z}</span>
          </div>
          <div class="ea-ch-row2">
            <span class="ea-ch-preview" id="ea-pr-${k.id}">${oniz}</span>
            ${rozet}
          </div>
        </div>
      </div>`;
  }

  _sistemKart(k) {
    const aktif = k.id == this.aktifId ? "aktif" : "";
    const tip = this._robotTip(k.baslik);
    const z = zamanAgo(k.son_zaman || k.son_hareket_zamani);
    const rozet = k.okunmamis_sayisi > 0
      ? `<span class="ea-badge" id="ea-rz-${k.id}">${k.okunmamis_sayisi}</span>`
      : `<span class="ea-badge" id="ea-rz-${k.id}" style="display:none">0</span>`;
    const ikonlar = { gtb:"🏛️", eta:"🚢", kantar:"⚖️", sistem:"📢" };
    return `
      <div class="ea-ch ${aktif}" data-id="${k.id}" data-q="${xss(k.baslik).toLowerCase()}"
           onclick="EA.kanalSec(${k.id})" title="${xss(k.baslik)} — Salt Okunur">
        <div class="ea-ch-av ea-av-${tip}">${ikonlar[tip] || "📢"}</div>
        <div class="ea-ch-info">
          <div class="ea-ch-row1">
            <span class="ea-ch-name">${xss(k.baslik)}</span>
            <span class="ea-readonly-tag">SALT OKUNUR</span>
          </div>
          <div class="ea-ch-row2">
            <span class="ea-ch-preview" id="ea-pr-${k.id}">${xss(k.son_metin || "")}</span>
            ${rozet}
          </div>
        </div>
      </div>`;
  }

  araFiltre(q) {
    q = q.toLowerCase().trim();
    this.el.querySelectorAll(".ea-ch").forEach(el => {
      el.style.display = (!q || (el.dataset.q || "").includes(q)) ? "" : "none";
    });
  }

  aktifIsaretle(id) {
    this.aktifId = id;
    this.el.querySelectorAll(".ea-ch").forEach(el => {
      el.classList.toggle("aktif", Number(el.dataset.id) === id);
    });
    document.getElementById("ea-feed-btn")?.classList.toggle("aktif", !id);
  }

  rozGuncelle(kanallar) {
    for (const k of kanallar) {
      const rz = document.getElementById(`ea-rz-${k.id}`);
      if (rz) { rz.textContent = k.okunmamis_sayisi; rz.style.display = k.okunmamis_sayisi > 0 ? "" : "none"; }
      const zt = document.getElementById(`ea-zt-${k.id}`);
      if (zt) zt.textContent = zamanAgo(k.son_zaman || k.son_hareket_zamani);
      const pr = document.getElementById(`ea-pr-${k.id}`);
      if (pr && k.son_yazan) pr.innerHTML = `<b>${xss(k.son_yazan)}:</b> ${xss(k.son_metin || "")}`;
    }
  }
}

// ── MesajSahnesi ──────────────────────────────────────────────────────────────
class MesajSahnesi {
  constructor(container, kullanici) {
    this.el = container;
    this.kullanici = kullanici;
    this.kanalId = null;
    this.sonId = 0;
    this.pollTimer = null;
    this.okunduId = 0;
  }

  async yukle(id) {
    this.kanalId = id;
    this.sonId = 0;
    this.el.innerHTML = `<div class="ea-empty"><div class="ea-empty-inner"><span class="ea-empty-icon" style="animation:none;">⟳</span><div class="ea-empty-title" style="font-size:1rem;opacity:0.5;">Yükleniyor...</div></div></div>`;
    try {
      const res = await fetch(`/ekip-akisi/api/konu/${id}/mesajlar?son_id=0`);
      const data = await res.json();
      this.okunduId = data.okundu_id || 0;
      this._render(data.mesajlar || [], true);

      document.getElementById("ea-hdr-title").textContent = data.konu_baslik || "";
      const sayac = (data.mesajlar || []).length;
      document.getElementById("ea-hdr-sub").textContent = `${sayac} mesaj`;

      const tog = document.getElementById("ea-ai-toggle");
      if (tog) tog.checked = (data.ai_otomatik ?? 1) !== 0;

      fetch(`/ekip-akisi/api/konu/${id}/okundu`, { method: "POST" });
    } catch {
      this.el.innerHTML = `<div class="ea-empty"><div class="ea-empty-inner"><div class="ea-empty-title">Yüklenemedi</div></div></div>`;
    }
  }

  async pollYeni() {
    if (!this.kanalId) return;
    try {
      const res = await fetch(`/ekip-akisi/api/konu/${this.kanalId}/mesajlar?son_id=${this.sonId}`);
      const data = await res.json();
      if (data.mesajlar?.length > 0) {
        this.okunduId = data.okundu_id || this.okunduId;
        this._render(data.mesajlar, false);
        fetch(`/ekip-akisi/api/konu/${this.kanalId}/okundu`, { method: "POST" });
      }
    } catch {}
  }

  pollBaslat() {
    this.pollDurdur();
    this.pollTimer = setInterval(() => this.pollYeni(), EA_POLL_MS);
  }
  pollDurdur() {
    if (this.pollTimer) { clearInterval(this.pollTimer); this.pollTimer = null; }
  }

  _render(mesajlar, temizle) {
    if (temizle) { this.el.innerHTML = ""; this.sonId = 0; }
    if (temizle && !mesajlar.length) {
      this.el.innerHTML = `<div class="ea-empty"><div class="ea-empty-inner"><span class="ea-empty-icon">💬</span><div class="ea-empty-title">Henüz mesaj yok</div><div class="ea-empty-desc">Bu kanalda ilk mesajı gönderin.</div></div></div>`;
      return;
    }
    const altMiydi = this._altaMiydi();
    // İlk boş durum div'ini kaldır
    const bos = this.el.querySelector(".ea-empty");
    if (bos) bos.remove();

    const frag = document.createDocumentFragment();
    for (const m of mesajlar) {
      if (m.id > this.sonId) this.sonId = m.id;
      const div = document.createElement("div");
      div.innerHTML = this._mesajHtml(m);
      if (div.firstElementChild) frag.appendChild(div.firstElementChild);
    }
    this.el.appendChild(frag);
    if (altMiydi) this._altaKaydir();
  }

  _altaMiydi() { return this.el.scrollHeight - this.el.scrollTop - this.el.clientHeight < 90; }
  _altaKaydir() { this.el.scrollTop = this.el.scrollHeight; }

  _mesajHtml(m) {
    const benimMi = m.yazan === this.kullanici;
    const sistemMi = m.yazan === "🤖 Sistem";
    const aiMi = m.yazan?.startsWith("🤖 SMART") || m.yazan?.startsWith("🤖 AI");
    const robotMu = !sistemMi && !aiMi && m.yazan?.includes("Robotu");

    let tip = benimMi ? "benim" : (aiMi ? "ai" : (robotMu ? "robot" : (sistemMi ? "sistem" : "diger")));

    const renk = avatarRenk(m.yazan);
    const harf = avatarHarf(m.yazan);
    const z = zamanAgo(m.zaman);

    let icerik = "";
    if (m.gif_url) {
      icerik = `<img src="${xss(m.gif_url)}" class="ea-gif-img" alt="GIF">`;
    } else {
      icerik = MesajFmt.isle(m.metin, m.yazan);
    }

    // Dosya ekleri
    if (m.dosyalar?.length > 0) {
      icerik += m.dosyalar.map(d =>
        `<a href="/ekip-akisi/konu/${this.kanalId}/dosya/${d.id}" class="ea-dosya-link">📎 ${xss(d.dosya_adi)}</a>`
      ).join("");
    }

    // Aksiyonlar
    let aksiyonlar = "";
    if (benimMi && !sistemMi && !robotMu) {
      aksiyonlar = `<div class="ea-balon-aksiyonlar">
        <button class="ea-aksiyon-ic" onclick="EA.sahne.duzenleAc(${m.id})" title="Düzenle">✎</button>
        <button class="ea-aksiyon-ic danger" onclick="EA.sahne.sil(${m.id})" title="Sil">🗑</button>
      </div>`;
    } else if (!sistemMi && !robotMu) {
      aksiyonlar = `<div class="ea-balon-aksiyonlar">
        <button class="ea-aksiyon-ic" onclick="EA.mentionEkle('${xss(m.yazan)}')" title="Yanıtla">↩</button>
      </div>`;
    }

    const okunduHtml = benimMi
      ? `<div class="ea-okundu ${m.id <= this.okunduId ? "" : "bekliyor"}">${m.id <= this.okunduId ? "✓✓" : "✓"}</div>`
      : "";

    const avHtml = `<div class="ea-msg-av" style="background:${renk}">${harf}</div>`;

    // Gönderici satırı (benim için ters, sistem için yok)
    let senderRow = "";
    if (!benimMi && !sistemMi) {
      senderRow = `<div class="ea-msg-sender">
        ${avHtml}
        <span class="ea-msg-yazan">${xss(m.yazan)}</span>
        <span class="ea-msg-zaman">${z}</span>
      </div>`;
    }
    const benimSender = benimMi ? `<div class="ea-msg-sender">
        <span class="ea-msg-zaman">${z}</span>
        <span class="ea-msg-yazan">${xss(m.yazan)}</span>
        ${avHtml}
      </div>` : "";

    return `
      <div class="ea-msg-group ${tip}" data-mid="${m.id}">
        ${senderRow}${benimSender}
        <div class="ea-msg-balon" id="ea-bl-${m.id}">
          ${icerik}
          ${aksiyonlar}
        </div>
        ${okunduHtml}
      </div>`;
  }

  ara(q) {
    q = q.toLowerCase().trim();
    this.el.querySelectorAll(".ea-msg-group").forEach(el => {
      el.style.display = (!q || el.textContent.toLowerCase().includes(q)) ? "" : "none";
    });
  }

  duzenleAc(msgId) {
    const balon = document.getElementById(`ea-bl-${msgId}`);
    if (!balon) return;
    const orijinal = balon.innerHTML;
    const mevcutMetin = balon.querySelector("div")?.innerText || "";
    balon.innerHTML = `
      <form method="post" action="/ekip-akisi/konu/${this.kanalId}/mesaj-duzenle/${msgId}" style="width:100%">
        <textarea name="metin" rows="3" style="width:100%;background:rgba(0,0,0,0.32);border:1px solid var(--ea-accent);color:var(--ea-text);padding:8px;border-radius:8px;font-family:inherit;font-size:0.87rem;resize:none;outline:none;box-sizing:border-box;">${xss(mevcutMetin)}</textarea>
        <div style="display:flex;gap:7px;margin-top:5px;justify-content:flex-end;">
          <button type="button" style="background:rgba(255,255,255,0.08);border:none;color:var(--ea-text-muted);padding:4px 11px;border-radius:6px;cursor:pointer;font-family:inherit;font-size:0.78rem;"
            onclick="document.getElementById('ea-bl-${msgId}').innerHTML=this.closest('form').dataset.orig">İptal</button>
          <button type="submit" style="background:var(--ea-accent);border:none;color:#fff;padding:4px 11px;border-radius:6px;cursor:pointer;font-family:inherit;font-size:0.78rem;font-weight:700;">Kaydet</button>
        </div>
      </form>`;
    balon.querySelector("form").dataset.orig = orijinal;
    balon.querySelector("textarea").focus();
  }

  sil(msgId) {
    if (!confirm("Bu mesajı silmek istiyor musunuz?")) return;
    const f = document.createElement("form");
    f.method = "post";
    f.action = `/ekip-akisi/konu/${this.kanalId}/mesaj-sil/${msgId}`;
    document.body.appendChild(f);
    f.submit();
  }
}

// ── MesajEditor ───────────────────────────────────────────────────────────────
class MesajEditor {
  constructor(getKanalId) {
    this.getKanalId = getKanalId;
    this.gifUrl = null;
    this.mentionler = [];
    this._kurulum();
  }

  _kurulum() {
    const form = document.getElementById("ea-form");
    const ta = document.getElementById("ea-ta");
    if (!form || !ta) return;

    // Form action
    form.addEventListener("submit", e => {
      const id = this.getKanalId();
      if (!id) { e.preventDefault(); return; }
      form.action = `/ekip-akisi/konu/${id}/mesaj`;
    });

    // Enter gönder (Shift+Enter = satır)
    ta.addEventListener("keydown", e => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        const id = this.getKanalId();
        if (id && (ta.value.trim() || this.gifUrl)) {
          form.action = `/ekip-akisi/konu/${id}/mesaj`;
          form.submit();
        }
      }
    });

    // Otomatik boyutlandırma + mention + komut
    ta.addEventListener("input", () => {
      ta.style.height = "auto";
      ta.style.height = Math.min(ta.scrollHeight, 126) + "px";
      this._mentionKontrol(ta.value);
      this._komutKontrol(ta.value);
    });

    // Emoji
    document.getElementById("ea-emoji-btn")?.addEventListener("click", e => {
      e.stopPropagation();
      document.getElementById("ea-emoji-picker")?.classList.toggle("acik");
      document.getElementById("ea-gif-picker")?.classList.remove("acik");
    });

    // GIF
    document.getElementById("ea-gif-btn")?.addEventListener("click", e => {
      e.stopPropagation();
      document.getElementById("ea-gif-picker")?.classList.toggle("acik");
      document.getElementById("ea-emoji-picker")?.classList.remove("acik");
      this._gifYukle(document.querySelector(".ea-gif-search")?.value || "");
    });

    // Dosya
    document.getElementById("ea-dosya-btn")?.addEventListener("click", () => {
      document.getElementById("ea-dosya-inp")?.click();
    });
    document.getElementById("ea-dosya-inp")?.addEventListener("change", e => {
      const d = e.target.files[0];
      if (d) {
        document.getElementById("ea-dosya-prev-ad").textContent = `📎 ${d.name}`;
        document.getElementById("ea-dosya-prev")?.classList.add("goster");
      }
    });
    document.getElementById("ea-dosya-prev-kapat")?.addEventListener("click", () => {
      document.getElementById("ea-dosya-inp").value = "";
      document.getElementById("ea-dosya-prev")?.classList.remove("goster");
    });

    // GIF kapat
    document.getElementById("ea-gif-prev-kapat")?.addEventListener("click", () => {
      this.gifUrl = null;
      document.getElementById("ea-gif-hidden").value = "";
      document.getElementById("ea-gif-prev")?.classList.remove("goster");
    });

    // GIF arama
    document.querySelector(".ea-gif-search")?.addEventListener("input", e => {
      this._gifYukle(e.target.value);
    });

    // Picker dışına tıklama
    document.addEventListener("click", e => {
      if (!e.target.closest("#ea-emoji-picker") && !e.target.closest("#ea-emoji-btn")) {
        document.getElementById("ea-emoji-picker")?.classList.remove("acik");
      }
      if (!e.target.closest("#ea-gif-picker") && !e.target.closest("#ea-gif-btn")) {
        document.getElementById("ea-gif-picker")?.classList.remove("acik");
      }
      if (!e.target.closest("#ea-mention-dd") && !e.target.closest("#ea-ta")) {
        document.getElementById("ea-mention-dd")?.classList.remove("acik");
      }
      if (!e.target.closest("#ea-komut-dd") && !e.target.closest("#ea-ta")) {
        document.getElementById("ea-komut-dd")?.classList.remove("acik");
      }
    });

    this._emojiGrid();
  }

  _emojiGrid() {
    const g = document.querySelector(".ea-emoji-grid");
    if (!g) return;
    g.innerHTML = EA_EMOJILER.map(e =>
      `<button type="button" class="ea-emoji-btn" onclick="EA.editor.emojiEkle('${e}')">${e}</button>`
    ).join("");
  }

  async _gifYukle(q) {
    try {
      const res = await fetch(`/ekip-akisi/api/gif-ara?q=${encodeURIComponent(q)}`);
      const data = await res.json();
      const grid = document.querySelector(".ea-gif-grid");
      if (!grid) return;
      grid.innerHTML = (data.results || []).map(g =>
        `<div class="ea-gif-item" onclick="EA.editor.gifSec('${xss(g.url)}')">
          <img src="${xss(g.preview || g.url)}" alt="${xss(g.title)}" loading="lazy">
        </div>`
      ).join("");
    } catch {}
  }

  emojiEkle(emoji) {
    const ta = document.getElementById("ea-ta");
    if (!ta) return;
    const p = ta.selectionStart;
    ta.value = ta.value.substring(0, p) + emoji + ta.value.substring(p);
    ta.selectionStart = ta.selectionEnd = p + emoji.length;
    ta.focus();
    document.getElementById("ea-emoji-picker")?.classList.remove("acik");
  }

  gifSec(url) {
    this.gifUrl = url;
    document.getElementById("ea-gif-hidden").value = url;
    document.getElementById("ea-gif-prev")?.classList.add("goster");
    document.getElementById("ea-gif-prev-ad").textContent = "🎞 GIF seçildi";
    document.getElementById("ea-gif-picker")?.classList.remove("acik");
  }

  mentionEkle(isim) {
    const ta = document.getElementById("ea-ta");
    if (!ta) return;
    const s = isim.startsWith("@") ? isim : `@${isim}`;
    ta.value += `${s} `;
    ta.focus();
  }

  _mentionKontrol(metin) {
    const m = metin.match(/@([\wÇçĞğİıÖöŞşÜü]*)$/);
    const dd = document.getElementById("ea-mention-dd");
    if (!dd) return;
    if (!m) { dd.classList.remove("acik"); return; }
    const q = m[1].toLowerCase();
    const eslesme = this.mentionler.filter(k => k.toLowerCase().startsWith(q) || q === "");
    if (!eslesme.length) { dd.classList.remove("acik"); return; }
    dd.innerHTML = eslesme.slice(0, 8).map(k => {
      const r = avatarRenk(k); const h = avatarHarf(k);
      return `<div class="ea-dd-item" onclick="EA.editor._mentionSec('${xss(k)}')">
        <div class="ea-dd-av" style="background:${r}">${h}</div>
        <span>${xss(k)}</span>
      </div>`;
    }).join("");
    dd.classList.add("acik");
  }

  _mentionSec(isim) {
    const ta = document.getElementById("ea-ta");
    if (!ta) return;
    ta.value = ta.value.replace(/@[\wÇçĞğİıÖöŞşÜü]*$/, `@${isim} `);
    ta.focus();
    document.getElementById("ea-mention-dd")?.classList.remove("acik");
  }

  _komutKontrol(metin) {
    const dd = document.getElementById("ea-komut-dd");
    if (!dd) return;
    if (!metin.startsWith("/")) { dd.classList.remove("acik"); return; }
    const komutlar = [
      ["/darbogaz", "Darboğaz dosyaları listele"],
      ["/ozet",     "Genel durum özeti"],
      ["/gtb",      "GTB beyanname sorgula"],
      ["/ai",       "AI asistanı çağır"],
      ["/yardim",   "Komut listesi"],
    ];
    const q = metin.toLowerCase();
    const eslesen = komutlar.filter(([k]) => k.startsWith(q));
    if (!eslesen.length) { dd.classList.remove("acik"); return; }
    dd.innerHTML = eslesen.map(([k, a]) => `
      <div class="ea-dd-item" onclick="EA.editor._komutSec('${k}')">
        <div class="ea-dd-av" style="background:#6366f1;font-size:0.65rem;font-weight:800;">/</div>
        <div><div style="font-weight:700;font-size:0.83rem;">${k}</div><div class="ea-dd-sub">${a}</div></div>
      </div>`).join("");
    dd.classList.add("acik");
  }

  _komutSec(k) {
    const ta = document.getElementById("ea-ta");
    if (!ta) return;
    ta.value = `${k} `;
    ta.focus();
    document.getElementById("ea-komut-dd")?.classList.remove("acik");
  }
}

// ── BaglamPanel ───────────────────────────────────────────────────────────────
class BaglamPanel {
  constructor() {
    this.acik = false;
    this.kanalId = null;
  }

  goster(kanalId, baslik) {
    this.kanalId = kanalId;
    const panel = document.getElementById("ea-ctx");
    if (!panel) return;
    // Ad formu güncelle
    const adInp = document.getElementById("ea-ad-input");
    if (adInp) adInp.value = baslik || "";
    const adForm = document.getElementById("ea-ad-form");
    if (adForm) adForm.action = `/ekip-akisi/konu/${kanalId}/ad-degistir`;

    panel.classList.add("acik");
    this.acik = true;
    document.getElementById("ea-baglam-btn")?.classList.add("aktif");
  }

  kapat() {
    document.getElementById("ea-ctx")?.classList.remove("acik");
    this.acik = false;
    document.getElementById("ea-baglam-btn")?.classList.remove("aktif");
  }

  toggle(kanalId, baslik) {
    (this.acik && this.kanalId === kanalId) ? this.kapat() : this.goster(kanalId, baslik);
  }

  async poAra() {
    const inp = document.getElementById("ea-po-input");
    const alan = document.getElementById("ea-po-kart");
    if (!inp || !alan) return;
    const q = inp.value.trim();
    if (!q) return;
    alan.innerHTML = "<div style='color:var(--ea-text-dim);font-size:0.8rem;padding:8px 0;'>⟳ Aranıyor...</div>";
    try {
      const res = await fetch(`/ekip-akisi/api/po-ozet?q=${encodeURIComponent(q)}`);
      const d = await res.json();
      if (!d.bulundu) {
        alan.innerHTML = `<div style='color:var(--ea-text-dim);font-size:0.8rem;'>Kayıt bulunamadı: <b>${xss(q)}</b></div>`;
        return;
      }
      alan.innerHTML = `
        <div class="ea-po-kart">
          ${d.po_no   ? `<div class="ea-po-kart-satir"><span class="ea-po-kart-lbl">PO No</span><span class="ea-po-kart-val">${xss(d.po_no)}</span></div>` : ""}
          ${d.dosya_no? `<div class="ea-po-kart-satir"><span class="ea-po-kart-lbl">Dosya</span><span class="ea-po-kart-val">${xss(d.dosya_no)}</span></div>` : ""}
          ${d.bayi    ? `<div class="ea-po-kart-satir"><span class="ea-po-kart-lbl">Bayi</span><span class="ea-po-kart-val">${xss(d.bayi)}</span></div>` : ""}
          ${d.gumruk  ? `<div class="ea-po-kart-satir"><span class="ea-po-kart-lbl">Gümrük</span><span class="ea-po-kart-val">${xss(d.gumruk)}</span></div>` : ""}
          ${d.durum   ? `<div class="ea-po-kart-satir"><span class="ea-po-kart-lbl">Durum</span><span class="ea-po-kart-val">${xss(d.durum)}</span></div>` : ""}
          <div class="ea-po-kart-satir"><span class="ea-po-kart-lbl">Muhasebe</span><span class="ea-po-kart-val" style="font-size:0.75rem;">${xss(d.muhasebe_durum)}</span></div>
          <div style="margin-top:8px;text-align:right;">
            <a href="/takip-raporu/${xss(d.po_no)}" style="font-size:0.76rem;color:var(--ea-accent-lt);text-decoration:none;">Detaya Git →</a>
          </div>
        </div>`;
    } catch {
      alan.innerHTML = `<div style='color:var(--ea-danger);font-size:0.8rem;'>Sorgulama başarısız</div>`;
    }
  }
}

// ── FeedTimeline ──────────────────────────────────────────────────────────────
class FeedTimeline {
  constructor(el) { this.el = el; }

  render(ogeler) {
    if (!ogeler?.length) {
      this.el.innerHTML = `<div class="ea-empty"><div class="ea-empty-inner"><span class="ea-empty-icon">📡</span><div class="ea-empty-title">Aktivite yok</div><div class="ea-empty-desc">Sistem henüz bir hareket kaydetmedi.</div></div></div>`;
      return;
    }

    const tipCfg = {
      "not":         { ikon:"📝", renk:"#3b82f6", bg:"rgba(59,130,246,0.13)", eylem:"not ekledi" },
      "talep_olay":  { ikon:"⇄",  renk:"#10b981", bg:"rgba(16,185,129,0.13)", eylem:"" },
      "talep_dosya": { ikon:"📎",  renk:"#f59e0b", bg:"rgba(245,158,11,0.13)", eylem:"dosya yükledi" },
      "talep_not":   { ikon:"💬",  renk:"#06b6d4", bg:"rgba(6,182,212,0.13)",  eylem:"not yazdı" },
      "konu_ilk":    { ikon:"✦",  renk:"#8b5cf6", bg:"rgba(139,92,246,0.13)", eylem:"grup açtı" },
      "konu_mesaj":  { ikon:"💬",  renk:"#64748b", bg:"rgba(100,116,139,0.12)", eylem:"mesaj gönderdi" },
    };

    let h = `
      <div class="ea-feed-hero">
        <div class="ea-feed-hero-title">
          <span style="color:var(--ea-success);">✦</span>
          Sistem Aktivite Akışı
        </div>
        <div class="ea-feed-hero-sub">${ogeler.length} son hareket · canlı güncelleniyor</div>
      </div>`;

    for (const o of ogeler) {
      const cfg = tipCfg[o.tur] || tipCfg["konu_mesaj"];
      const eylem = o.tur === "talep_olay" ? (o.icerik || "") : cfg.eylem;
      const z = zamanAgo(o.zaman);
      const link = o.link || "#";

      const poTaglar = (o.po_numaralari || []).slice(0, 3).map(p =>
        `<span class="ea-tl-tag">📦 ${xss(p)}</span>`
      ).join("");
      const baslikTag = o.baslik
        ? `<span class="ea-tl-tag tag-kanal">💬 ${xss(o.baslik)}</span>` : "";

      h += `
        <a href="${xss(link)}" class="ea-tl-card t-${o.tur}">
          <div class="ea-tl-icon" style="background:${cfg.bg}">${cfg.ikon}</div>
          <div class="ea-tl-body">
            <div class="ea-tl-meta">
              <span class="ea-tl-yazan">${xss(o.yazan || "?")}</span>
              ${eylem ? `<span class="ea-tl-eylem">${xss(eylem)}</span>` : ""}
              <span class="ea-tl-zaman">${z}</span>
            </div>
            <div class="ea-tl-metin">${xss(o.icerik || "")}</div>
            ${poTaglar || baslikTag ? `<div class="ea-tl-tags">${poTaglar}${baslikTag}</div>` : ""}
          </div>
        </a>`;
    }
    this.el.innerHTML = h;
  }
}

// ── Ana Kontrolcü ─────────────────────────────────────────────────────────────
class EkipAkisi {
  constructor() {
    this.kanalId = null;
    this.gorununum = "feed";
    this.kanalData = [];
    this.kanalListesi = null;
    this.sahne = null;
    this.editor = null;
    this.baglam = null;
    this.feed = null;
    this.kullanici = "";
    this._kanalPoll = null;
  }

  init() {
    this.kullanici = document.getElementById("ea-shell")?.dataset.kullanici || "";

    // Widget'lar
    this.kanalListesi = new KanalListesi(document.getElementById("ea-kanal-liste"));
    this.sahne = new MesajSahnesi(document.getElementById("ea-mesajlar"), this.kullanici);
    this.editor = new MesajEditor(() => this.kanalId);
    this.baglam = new BaglamPanel();
    this.feed = new FeedTimeline(document.getElementById("ea-feed-icerik"));

    // Kanalları yükle (JSON data'dan)
    this._kanalDataYukle();

    // Feed başlangıçta göster
    this._feedGoster();

    // URL hash'e göre kanal aç
    const hash = parseInt(window.location.hash.substring(1));
    if (hash) setTimeout(() => this.kanalSec(hash), 80);

    // Kanal listesi periyodik yenileme
    this._kanalPoll = setInterval(() => this._kanalPollYenile(), EA_KANAL_POLL_MS);

    // Event'ler
    this._eventlerBagla();

    // Mention listesi
    this.editor.mentionler = window.__EA_KULLANICILAR__ || [];
  }

  _kanalDataYukle() {
    try {
      this.kanalData = JSON.parse(document.getElementById("ea-kanal-data")?.textContent || "[]");
    } catch { this.kanalData = []; }
    this.kanalListesi.render(this.kanalData, this.kanalId);
  }

  async _kanalPollYenile() {
    try {
      const res = await fetch("/ekip-akisi/api/kanallar");
      const data = await res.json();
      this.kanalData = data.kanallar || [];
      this.kanalListesi.rozGuncelle(this.kanalData);
    } catch {}
  }

  async kanalSec(id) {
    id = Number(id);
    this.kanalId = id;
    this.gorununum = "kanal";

    history.replaceState(null, "", `${window.location.pathname}#${id}`);

    // Panel geçişi
    document.getElementById("ea-feed-view")?.classList.add("d-none");
    document.getElementById("ea-msg-panel")?.classList.remove("d-none");

    // Sidebar
    this.kanalListesi.aktifIsaretle(id);

    // Başlık header
    const kanalVeri = this.kanalData.find(k => k.id == id);
    const sistemMi = kanalVeri && this._sistemKanalMi(kanalVeri.baslik);
    document.getElementById("ea-hdr-title").textContent = kanalVeri?.baslik || "";
    document.getElementById("ea-baglam-btn").style.display = sistemMi ? "none" : "";

    // Input gizle/göster (sistem kanalı = salt okunur)
    const inputArea = document.getElementById("ea-input-area");
    if (inputArea) inputArea.style.display = sistemMi ? "none" : "";
    document.getElementById("ea-search-msg").style.display = "";

    // Mesajları yükle & poll başlat
    await this.sahne.yukle(id);
    this.sahne.pollBaslat();

    // Bağlam paneli kanal değiştiyse kapat
    if (this.baglam.acik && this.baglam.kanalId !== id) this.baglam.kapat();
  }

  _sistemKanalMi(baslik) {
    return !!(baslik && (
      baslik.startsWith("📢 #") ||
      baslik.includes("Robotu") ||
      baslik.includes("Sistem-Islem")
    ));
  }

  _feedGoster() {
    this.gorununum = "feed";
    this.kanalId = null;
    this.sahne.pollDurdur();

    history.replaceState(null, "", window.location.pathname);

    document.getElementById("ea-feed-view")?.classList.remove("d-none");
    document.getElementById("ea-msg-panel")?.classList.add("d-none");
    document.getElementById("ea-input-area") && (document.getElementById("ea-input-area").style.display = "none");
    document.getElementById("ea-baglam-btn").style.display = "none";
    document.getElementById("ea-search-msg").style.display = "none";

    this.kanalListesi.aktifIsaretle(null);

    document.getElementById("ea-hdr-title").textContent = "Sistem Aktivite Akışı";
    document.getElementById("ea-hdr-sub").textContent = "Tüm sistem hareketleri";

    // Feed render
    this.feed.render(window.__EA_AKIS__ || []);
    this.baglam.kapat();
  }

  mentionEkle(isim) { this.editor?.mentionEkle(isim); }

  modalAc() {
    document.getElementById("ea-modal")?.classList.add("acik");
    document.getElementById("ea-modal-baslik")?.focus();
  }
  modalKapat() { document.getElementById("ea-modal")?.classList.remove("acik"); }

  _eventlerBagla() {
    // Keyboard
    document.addEventListener("keydown", e => {
      if (e.key === "Escape") {
        this.baglam.kapat();
        document.getElementById("ea-emoji-picker")?.classList.remove("acik");
        document.getElementById("ea-gif-picker")?.classList.remove("acik");
        document.getElementById("ea-modal")?.classList.remove("acik");
      }
    });

    // Feed butonu
    document.getElementById("ea-feed-btn")?.addEventListener("click", () => this._feedGoster());

    // Yeni grup butonu
    document.getElementById("ea-yeni-btn")?.addEventListener("click", () => this.modalAc());

    // Modal backdrop
    document.getElementById("ea-modal")?.addEventListener("click", e => {
      if (e.target === e.currentTarget) this.modalKapat();
    });
    document.getElementById("ea-modal-kapat")?.addEventListener("click", () => this.modalKapat());
    document.getElementById("ea-modal-iptal")?.addEventListener("click", () => this.modalKapat());

    // Bağlam panel toggle
    document.getElementById("ea-baglam-btn")?.addEventListener("click", () => {
      if (!this.kanalId) return;
      const baslik = document.getElementById("ea-hdr-title")?.textContent || "";
      this.baglam.toggle(this.kanalId, baslik);
    });

    // Bağlam kapat
    document.getElementById("ea-ctx-kapat")?.addEventListener("click", () => this.baglam.kapat());

    // AI Toggle
    document.getElementById("ea-ai-toggle")?.addEventListener("change", e => {
      if (!this.kanalId) return;
      fetch(`/ekip-akisi/konu/${this.kanalId}/ai-otomatik-ayarla`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ durum: e.target.checked }),
      });
    });

    // Sidebar arama
    document.getElementById("ea-sidebar-ara")?.addEventListener("input", e => {
      this.kanalListesi.araFiltre(e.target.value);
    });

    // Mesaj içi arama
    document.getElementById("ea-search-msg")?.addEventListener("input", e => {
      this.sahne.ara(e.target.value);
    });

    // PO sorgula
    document.getElementById("ea-po-ara-btn")?.addEventListener("click", () => this.baglam.poAra());
    document.getElementById("ea-po-input")?.addEventListener("keydown", e => {
      if (e.key === "Enter") this.baglam.poAra();
    });

    // Sohbet temizle
    document.getElementById("ea-temizle-btn")?.addEventListener("click", () => {
      if (!this.kanalId) return;
      if (!confirm("Tüm sohbet geçmişi silinecek. Emin misiniz?")) return;
      const f = document.createElement("form");
      f.method = "post"; f.action = `/ekip-akisi/konu/${this.kanalId}/sohbet-temizle`;
      document.body.appendChild(f); f.submit();
    });

    // Kanal sil
    document.getElementById("ea-sil-btn")?.addEventListener("click", () => {
      if (!this.kanalId) return;
      if (!confirm("Bu grup kalıcı olarak silinecek! Emin misiniz?")) return;
      const f = document.createElement("form");
      f.method = "post"; f.action = `/ekip-akisi/konu/${this.kanalId}/sil`;
      document.body.appendChild(f); f.submit();
    });

    // Ad formu action
    document.getElementById("ea-ad-form")?.addEventListener("submit", e => {
      if (!this.kanalId) { e.preventDefault(); return; }
      e.currentTarget.action = `/ekip-akisi/konu/${this.kanalId}/ad-degistir`;
    });
  }
}

// ── PO Özet Modal ─────────────────────────────────────────────────────────────
window.eaPoModal = async function(q) {
  const overlay = document.getElementById("ea-po-modal");
  const icerik = document.getElementById("ea-po-modal-icerik");
  if (!overlay) return;
  overlay.classList.add("acik");
  if (icerik) icerik.innerHTML = "<div style='text-align:center;padding:18px;color:var(--ea-text-muted);'>⟳ Aranıyor...</div>";
  try {
    const res = await fetch(`/ekip-akisi/api/po-ozet?q=${encodeURIComponent(q)}`);
    const d = await res.json();
    if (!icerik) return;
    if (!d.bulundu) { icerik.innerHTML = `<div style='color:var(--ea-text-muted);text-align:center;padding:12px;'>Kayıt bulunamadı: <b>${xss(q)}</b></div>`; return; }
    icerik.innerHTML = `
      <div class="ea-po-kart">
        ${d.po_no    ? `<div class="ea-po-kart-satir"><span class="ea-po-kart-lbl">PO No</span><span class="ea-po-kart-val">${xss(d.po_no)}</span></div>` : ""}
        ${d.dosya_no ? `<div class="ea-po-kart-satir"><span class="ea-po-kart-lbl">Dosya</span><span class="ea-po-kart-val">${xss(d.dosya_no)}</span></div>` : ""}
        ${d.bayi     ? `<div class="ea-po-kart-satir"><span class="ea-po-kart-lbl">Bayi</span><span class="ea-po-kart-val">${xss(d.bayi)}</span></div>` : ""}
        ${d.gumruk   ? `<div class="ea-po-kart-satir"><span class="ea-po-kart-lbl">Gümrük</span><span class="ea-po-kart-val">${xss(d.gumruk)}</span></div>` : ""}
        ${d.durum    ? `<div class="ea-po-kart-satir"><span class="ea-po-kart-lbl">Durum</span><span class="ea-po-kart-val">${xss(d.durum)}</span></div>` : ""}
        <div class="ea-po-kart-satir"><span class="ea-po-kart-lbl">Muhasebe</span><span class="ea-po-kart-val" style="font-size:0.76rem;">${xss(d.muhasebe_durum)}</span></div>
        ${d.islem_kayitlari?.length ? `
          <div style="margin-top:9px;font-size:0.68rem;color:var(--ea-text-dim);font-weight:800;text-transform:uppercase;letter-spacing:0.07em;margin-bottom:5px;">Son İşlemler</div>
          ${d.islem_kayitlari.map(k => `<div class="ea-po-kart-satir"><span class="ea-po-kart-lbl" style="font-size:0.76rem;">${xss(k.tur)}</span><span class="ea-po-kart-val" style="font-size:0.76rem;">${xss((k.aciklama||"").substring(0,45))}</span></div>`).join("")}
        ` : ""}
      </div>
      <div style="margin-top:11px;display:flex;gap:7px;flex-wrap:wrap;">
        <a href="/takip-raporu/${xss(d.po_no)}" style="background:var(--ea-accent);color:#fff;padding:6px 13px;border-radius:8px;font-size:0.8rem;font-weight:700;text-decoration:none;">📂 Detaya Git</a>
        <a href="/muhasebe-takip?po=${xss(d.po_no)}" style="background:rgba(245,158,11,0.12);color:#fcd34d;border:1px solid rgba(245,158,11,0.28);padding:6px 13px;border-radius:8px;font-size:0.8rem;font-weight:700;text-decoration:none;">💰 Muhasebe</a>
      </div>`;
  } catch {
    if (icerik) icerik.innerHTML = `<div style='color:var(--ea-danger);text-align:center;padding:12px;'>Sorgulama başarısız</div>`;
  }
};

document.getElementById("ea-po-modal")?.addEventListener("click", e => {
  if (e.target === e.currentTarget) e.currentTarget.classList.remove("acik");
});
document.getElementById("ea-po-modal-kapat")?.addEventListener("click", () => {
  document.getElementById("ea-po-modal")?.classList.remove("acik");
});

// ── Başlat ───────────────────────────────────────────────────────────────────
window.EA = new EkipAkisi();
document.addEventListener("DOMContentLoaded", () => window.EA.init());
