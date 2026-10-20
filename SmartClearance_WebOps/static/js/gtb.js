let gFilter = "ALL";
let gSearch = "";

function toast(msg, tip) {
  const el = document.createElement("div");
  el.className = "toast" + (tip === "err" ? " err" : "");
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 3800);
}
function openModal(id) { document.getElementById(id)?.classList.add("acik"); }
function closeModal(id) { document.getElementById(id)?.classList.remove("acik"); }
function selectedBeyans() {
  return [...document.querySelectorAll("#gtb-tbody input.row-check:checked")].map((x) => x.value);
}
function durumPill(kapandi, durum) {
  const d = (durum || "").toLowerCase();
  let cls = "info";
  if (kapandi || d.includes("kapan") || d.includes("tamamlan")) cls = "ok";
  else if (d.includes("kırmızı") || d.includes("hata") || d.includes("bloke")) cls = "bad";
  else if (d.includes("işlemde") || d.includes("bekliyor") || d.includes("tescil")) cls = "warn";
  return `<span class="pill ${cls}">${durum || "—"}</span>`;
}

async function gtbYenile() {
  const tbody = document.getElementById("gtb-tbody");
  const url = `/api/gtb/takip/listele?filtre=${encodeURIComponent(gFilter)}&q=${encodeURIComponent(gSearch)}`;
  try {
    const res = await fetch(url, { cache: "no-store" });
    const data = await res.json();
    const st = data.stats || {};
    document.getElementById("g-total").textContent = st.total ?? 0;
    document.getElementById("g-proc").textContent = st.in_proc ?? 0;
    document.getElementById("g-closed").textContent = st.closed ?? 0;
    document.getElementById("g-scan").textContent = st.last_scan || "—";
    const status = document.getElementById("g-status");
    status.textContent = st.scanning ? "Tarama sürüyor…" : (gFilter === "CLOSED" ? "Filtre: Kapananlar" : gFilter === "IN_PROC" ? "Filtre: İşlemde" : "10 dk otonom izleme");
    status.classList.toggle("warn", !!st.scanning || gFilter === "IN_PROC");

    // legacy ids for compatibility
    const o1 = document.getElementById("ozet-toplam");
    if (o1) o1.textContent = st.total ?? 0;

    const items = data.beyannameler || [];
    if (!items.length) {
      tbody.innerHTML = '<tr><td colspan="9" class="empty">Havuz boş. Manuel ekleyin veya Evrim/Excel’den aktarın.</td></tr>';
      return;
    }
    tbody.innerHTML = items.map((it) => {
      const b = it.beyanname_no || "";
      return `<tr data-b="${b}">
        <td><input type="checkbox" class="row-check" value="${b}" /></td>
        <td class="mono"><strong>${b}</strong></td>
        <td class="mono">${it.dosya_no || "—"}</td>
        <td class="mono">${it.ref || "—"}</td>
        <td>${it.firma || "—"}</td>
        <td>${durumPill(it.kapandi, it.durum)}</td>
        <td>${it.son_kontrol || "—"}</td>
        <td>${it.degisim_tarihi || "—"}</td>
        <td style="white-space:nowrap">
          <button type="button" class="icon-btn" title="Canlı sorgula" data-q="${b}">🔍</button>
          <button type="button" class="icon-btn" title="Sil" data-del="${b}">✕</button>
        </td>
      </tr>`;
    }).join("");

    tbody.querySelectorAll("[data-q]").forEach((b) => b.addEventListener("click", () => canliSorgula(b.dataset.q)));
    tbody.querySelectorAll("[data-del]").forEach((b) => b.addEventListener("click", () => gtbSil(b.dataset.del)));
    tbody.querySelectorAll("tr[data-b]").forEach((tr) => {
      tr.addEventListener("click", (e) => {
        if (e.target.closest("input,button")) return;
        const cb = tr.querySelector(".row-check");
        if (cb) { cb.checked = !cb.checked; tr.classList.toggle("selected", cb.checked); }
      });
    });
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="9" class="empty">Liste hatası: ${e}</td></tr>`;
  }
}

async function canliSorgula(no) {
  const modal = document.getElementById("modalCanliSonuc");
  const box = document.getElementById("canli-sorgu-icerik");
  modal.classList.add("acik");
  box.innerHTML = `<p class="mono">${no}</p><p>GTB’ye bağlanılıyor, captcha çözülüyor…</p>`;
  try {
    const res = await fetch(`/api/gtb/takip/sorgula/${encodeURIComponent(no)}`);
    const data = await res.json();
    if (data.success) {
      box.innerHTML = `<div style="font-size:2rem">✅</div><p class="mono"><strong>${no}</strong></p>
        ${durumPill(data.kapandi, data.durum)}
        <p class="note" style="margin-top:12px">${data.timestamp || ""}</p>`;
      gtbYenile();
    } else {
      box.innerHTML = `<div style="font-size:2rem">❌</div><p><strong>Sorgu hatası</strong></p><p class="note">${data.error || "Bilinmeyen hata"}</p>`;
    }
  } catch {
    box.innerHTML = `<p>Bağlantı hatası</p>`;
  }
}

async function gtbSil(no) {
  if (!confirm(`${no} silinsin mi?`)) return;
  const res = await fetch(`/api/gtb/takip/sil/${encodeURIComponent(no)}`, { method: "POST" });
  const data = await res.json();
  if (data.success) { toast("Silindi"); gtbYenile(); }
  else toast(data.error || "Silinemedi", "err");
}

// aliases expected by older snippets
window.canliSorgula = canliSorgula;
window.listeyiYenile = () => gtbYenile();
window.topluTakibeEkle = async function () {};
window.tumunuKontrolEt = async function () {};
window.tekliAnlikSorgula = function () {};

document.addEventListener("DOMContentLoaded", () => {
  if (!document.getElementById("gtb-tbody")) return;

  document.querySelectorAll(".metric[data-f]").forEach((m) => {
    m.addEventListener("click", () => {
      gFilter = m.dataset.f;
      document.querySelectorAll(".metric[data-f]").forEach((x) => x.classList.toggle("active", x === m));
      gtbYenile();
    });
  });

  let t;
  document.getElementById("g-search").addEventListener("input", (e) => {
    clearTimeout(t);
    t = setTimeout(() => { gSearch = e.target.value || ""; gtbYenile(); }, 220);
  });
  document.getElementById("g-check-all").addEventListener("change", (e) => {
    document.querySelectorAll("#gtb-tbody .row-check").forEach((c) => { c.checked = e.target.checked; });
  });
  document.querySelectorAll("[data-close]").forEach((b) => b.addEventListener("click", () => closeModal(b.dataset.close)));
  document.querySelectorAll(".modal-bg").forEach((bg) => {
    bg.addEventListener("click", (e) => { if (e.target === bg) bg.classList.remove("acik"); });
  });

  document.getElementById("btn-g-add").onclick = () => openModal("modal-g-add");
  document.getElementById("btn-g-refresh").onclick = () => gtbYenile();

  document.getElementById("g-add-save").onclick = async () => {
    const body = {
      beyannameler: document.getElementById("g-add-text").value,
      dosya_no: document.getElementById("g-add-dosya").value,
      ref: document.getElementById("g-add-ref").value,
      firma: document.getElementById("g-add-firma").value,
    };
    const res = await fetch("/api/gtb/takip/ekle", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const data = await res.json();
    if (data.success) {
      toast(`${data.eklenen_sayisi} eklendi`);
      closeModal("modal-g-add");
      document.getElementById("g-add-text").value = "";
      gtbYenile();
      if (data.eklenenler?.[0]) canliSorgula(data.eklenenler[0]);
    } else toast(data.error || "Eklenemedi", "err");
  };

  document.getElementById("btn-g-sync").onclick = async () => {
    toast("Evrim/Excel aktarılıyor…");
    const res = await fetch("/api/gtb/takip/sync", { method: "POST" });
    const data = await res.json();
    if (data.success) { toast(`${data.eklenen || 0} beyanname aktarıldı`); gtbYenile(); }
    else toast(data.error || "Aktarım hatası", "err");
  };

  document.getElementById("btn-g-scan").onclick = async () => {
    const btn = document.getElementById("btn-g-scan");
    btn.disabled = true;
    toast("GTB havuzu taranıyor…");
    try {
      const res = await fetch("/api/gtb/takip/kontrol-et", { method: "POST" });
      const data = await res.json();
      toast(data.success ? `Tarama tamam (${data.total_checked || 0})` : (data.error || "Hata"), data.success ? undefined : "err");
      await gtbYenile();
    } finally { btn.disabled = false; }
  };

  document.getElementById("btn-g-query").onclick = async () => {
    const sel = selectedBeyans();
    if (!sel.length) return toast("Sorgulanacak satır seçin", "err");
    for (const b of sel) await canliSorgula(b);
  };

  document.getElementById("btn-g-mail").onclick = async () => {
    const sel = selectedBeyans();
    if (!sel.length) return toast("Mail için satır seçin", "err");
    const res = await fetch("/api/gtb/takip/vergi-mail-taslak", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ beyannameler: sel }),
    });
    const data = await res.json();
    if (data.success) {
      try { await navigator.clipboard.writeText(data.body); toast("Mail metni panoya kopyalandı"); } catch { /* ignore */ }
      window.location.href = data.mailto;
    } else toast(data.error || "Taslak oluşturulamadı", "err");
  };

  document.getElementById("btn-g-copy").onclick = async () => {
    const sel = selectedBeyans();
    if (!sel.length) return toast("Kopyalanacak satır seçin", "err");
    const text = sel.join("\n");
    try { await navigator.clipboard.writeText(text); toast("Kopyalandı"); }
    catch { toast("Pano erişilemedi", "err"); }
  };

  document.getElementById("btn-g-del").onclick = async () => {
    const sel = selectedBeyans();
    if (!sel.length) return toast("Silinecek satır seçin", "err");
    if (!confirm(`${sel.length} beyanname silinsin mi?`)) return;
    const res = await fetch("/api/gtb/takip/sil-coklu", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ beyannameler: sel }) });
    const data = await res.json();
    if (data.success) { toast(`${data.removed} silindi`); gtbYenile(); }
    else toast(data.error || "Silinemedi", "err");
  };

  document.getElementById("btn-g-clear").onclick = async () => {
    if (!confirm("Tüm GTB havuzu temizlensin mi?")) return;
    const res = await fetch("/api/gtb/takip/temizle", { method: "POST" });
    const data = await res.json();
    if (data.success) { toast(`Temizlendi (${data.cleared})`); gtbYenile(); }
    else toast(data.error || "Temizlenemedi", "err");
  };

  gtbYenile();
  setInterval(gtbYenile, 60000);
});
