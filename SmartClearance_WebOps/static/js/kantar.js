function toast(msg, tip) {
  const el = document.createElement("div");
  el.className = "toast" + (tip === "err" ? " err" : "");
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

async function kantarYenile() {
  const tbody = document.getElementById("kantar-tbody");
  try {
    const res = await fetch("/api/kantar/takip/listele?sadece_aktif=true", { cache: "no-store" });
    const data = await res.json();
    const items = data.items || [];
    document.getElementById("k-total").textContent = items.length;
    const ready = items.filter((x) => x.hazir).length;
    document.getElementById("k-ready").textContent = ready;
    document.getElementById("k-pending").textContent = items.length - ready;
    document.getElementById("k-scan").textContent = data.last_scan || "—";

    if (!items.length) {
      tbody.innerHTML = '<tr><td colspan="6" class="empty">Takip listesi boş. Konteyner ekleyin.</td></tr>';
      return;
    }
    tbody.innerHTML = items.map((it) => {
      const durum = it.durum || (it.hazir ? "Hazır" : "Bekliyor");
      const pill = it.hazir ? "ok" : "warn";
      const dba = it.dba || it.agirlik || "—";
      return `<tr>
        <td class="mono"><strong>${it.konteyner_no || ""}</strong></td>
        <td>${it.dosya_no || "—"}</td>
        <td>${it.kaynak || "—"}</td>
        <td><span class="pill ${pill}">${durum}</span> <span class="mono" style="margin-left:6px;color:#64748b;">${dba}</span></td>
        <td>${it.son_kontrol || "—"}</td>
        <td style="text-align:center;white-space:nowrap;">
          <button type="button" class="btn ghost" data-q="${it.konteyner_no}">Sorgula</button>
          <button type="button" class="btn danger" data-del="${it.konteyner_no}">Sil</button>
        </td>
      </tr>`;
    }).join("");

    tbody.querySelectorAll("[data-q]").forEach((btn) => {
      btn.addEventListener("click", () => kantarSorgula(btn.getAttribute("data-q")));
    });
    tbody.querySelectorAll("[data-del]").forEach((btn) => {
      btn.addEventListener("click", () => kantarSil(btn.getAttribute("data-del")));
    });
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="6" class="empty">Liste alınamadı: ${e}</td></tr>`;
  }
}

async function kantarEkle() {
  const metin = (document.getElementById("txt-konteynerler").value || "").trim();
  if (!metin) return toast("Konteyner girin.", "err");
  const btn = document.getElementById("btn-k-ekle");
  btn.disabled = true;
  try {
    const res = await fetch("/api/kantar/takip/ekle", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ konteynerler: metin }),
    });
    const data = await res.json();
    if (data.success) {
      toast(`${data.eklenen_sayisi} konteyner eklendi.`);
      document.getElementById("txt-konteynerler").value = "";
      await kantarYenile();
    } else {
      toast(data.error || "Eklenemedi.", "err");
    }
  } catch (e) {
    toast("Bağlantı hatası.", "err");
  } finally {
    btn.disabled = false;
  }
}

async function kantarSil(no) {
  if (!confirm(`${no} silinsin mi?`)) return;
  const res = await fetch(`/api/kantar/takip/sil/${encodeURIComponent(no)}`, { method: "POST" });
  const data = await res.json();
  if (data.success) {
    toast("Silindi.");
    kantarYenile();
  } else {
    toast("Silinemedi.", "err");
  }
}

async function kantarSorgula(no) {
  toast(`${no} sorgulanıyor…`);
  try {
    const res = await fetch(`/api/kantar/takip/sorgula/${encodeURIComponent(no)}`);
    const data = await res.json();
    if (data.success) {
      toast(data.hazir ? `${no}: tike hazır` : `${no}: henüz yok`);
      kantarYenile();
    } else {
      toast(data.error || "Sorgu başarısız.", "err");
    }
  } catch (e) {
    toast("Sorgu hatası.", "err");
  }
}

async function kantarTara() {
  const btn = document.getElementById("btn-k-tara");
  btn.disabled = true;
  toast("Kantar havuzu taranıyor…");
  try {
    const res = await fetch("/api/kantar/takip/kontrol-et", { method: "POST" });
    const data = await res.json();
    if (data.success || data.status === "ok") {
      toast("Tarama tamamlandı.");
    } else {
      toast(data.error || "Tarama sonucu belirsiz.", data.error ? "err" : undefined);
    }
    await kantarYenile();
  } catch (e) {
    toast("Tarama hatası.", "err");
  } finally {
    btn.disabled = false;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  if (!document.getElementById("kantar-tbody")) return;
  document.getElementById("btn-k-ekle").addEventListener("click", kantarEkle);
  document.getElementById("btn-k-yenile").addEventListener("click", kantarYenile);
  document.getElementById("btn-k-tara").addEventListener("click", kantarTara);
  kantarYenile();
});
