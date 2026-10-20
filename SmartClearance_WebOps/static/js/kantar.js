let kFilter = "ALL";
let kSearch = "";
let kItems = [];

function toast(msg, tip) {
  const el = document.createElement("div");
  el.className = "toast" + (tip === "err" ? " err" : "");
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 3800);
}

function openModal(id) { document.getElementById(id)?.classList.add("acik"); }
function closeModal(id) { document.getElementById(id)?.classList.remove("acik"); }

function selectedCntrs() {
  return [...document.querySelectorAll("#kantar-tbody input.row-check:checked")].map((x) => x.value);
}

function pill(hazir, durum) {
  const cls = hazir ? "ok" : "warn";
  return `<span class="pill ${cls}">${durum || (hazir ? "Hazır" : "Bekliyor")}</span>`;
}

async function kantarYenile() {
  const tbody = document.getElementById("kantar-tbody");
  const url = `/api/kantar/takip/listele?filtre=${encodeURIComponent(kFilter)}&q=${encodeURIComponent(kSearch)}`;
  try {
    const res = await fetch(url, { cache: "no-store" });
    const data = await res.json();
    const st = data.stats || {};
    document.getElementById("k-total").textContent = st.total ?? 0;
    document.getElementById("k-ready").textContent = st.ready ?? 0;
    document.getElementById("k-pending").textContent = st.pending ?? 0;
    document.getElementById("k-scan").textContent = st.last_scan || "—";
    const status = document.getElementById("k-status");
    if (st.scanning) {
      status.textContent = "Tarama sürüyor…";
      status.classList.add("warn");
    } else {
      status.textContent = kFilter === "READY" ? "Filtre: Hazır" : kFilter === "PENDING" ? "Filtre: Bekleyen" : "10 dk otonom izleme";
      status.classList.toggle("warn", kFilter === "PENDING");
    }
    document.getElementById("k-yilport-note").textContent = st.yilport_session
      ? "Yılport oturumu: kayıtlı"
      : "Yılport oturumu yok — Yılport konteynerleri için oturum kaydedin.";

    kItems = data.items || [];
    if (!kItems.length) {
      tbody.innerHTML = '<tr><td colspan="12" class="empty">Takip listesi boş. Konteyner ekleyin veya Evrim/Excel’den aktarın.</td></tr>';
      return;
    }
    tbody.innerHTML = kItems.map((it) => {
      const cn = it.konteyner_no || "";
      return `<tr data-cn="${cn}">
        <td><input type="checkbox" class="row-check" value="${cn}" /></td>
        <td class="mono"><strong>${cn}</strong></td>
        <td class="mono">${it.dosya_no || "—"}</td>
        <td>${it.kaynak || "—"}</td>
        <td class="mono">${it.tartim_no || "—"}</td>
        <td>${it.tarih || "—"}</td>
        <td class="mono">${it.plaka || "—"}</td>
        <td>${it.firma || "—"}</td>
        <td class="mono">${it.dba || "—"}</td>
        <td>${pill(it.hazir, it.durum)}</td>
        <td>${it.son_kontrol || "—"}</td>
        <td style="white-space:nowrap">
          <button type="button" class="icon-btn" title="Sorgula" data-q="${cn}">🔍</button>
          <button type="button" class="icon-btn" title="PDF" data-pdf="${cn}">📥</button>
        </td>
      </tr>`;
    }).join("");

    tbody.querySelectorAll("[data-q]").forEach((b) => b.addEventListener("click", () => kantarSorgula(b.dataset.q)));
    tbody.querySelectorAll("[data-pdf]").forEach((b) => b.addEventListener("click", () => kantarPdf(b.dataset.pdf)));
    tbody.querySelectorAll("tr[data-cn]").forEach((tr) => {
      tr.addEventListener("click", (e) => {
        if (e.target.closest("input,button")) return;
        const cb = tr.querySelector(".row-check");
        if (cb) cb.checked = !cb.checked;
        tr.classList.toggle("selected", cb?.checked);
      });
    });
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="12" class="empty">Liste hatası: ${e}</td></tr>`;
  }
}

async function kantarSorgula(no) {
  toast(`${no} sorgulanıyor…`);
  try {
    const res = await fetch(`/api/kantar/takip/sorgula/${encodeURIComponent(no)}`);
    const data = await res.json();
    if (data.success) toast(data.hazir ? `${no}: tike hazır` : `${no}: henüz yok`);
    else toast(data.error || "Sorgu başarısız", "err");
    await kantarYenile();
  } catch {
    toast("Sorgu hatası", "err");
  }
}

function kantarPdf(no) {
  window.open(`/api/kantar/takip/pdf/${encodeURIComponent(no)}`, "_blank");
}

async function kantarMerge() {
  const cntrs = selectedCntrs();
  toast(cntrs.length ? `${cntrs.length} seçili birleştiriliyor…` : "Hazır PDF’ler birleştiriliyor…");
  try {
    const res = await fetch("/api/kantar/takip/pdf-birlestir", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ konteynerler: cntrs.length ? cntrs : null }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      toast(err.error || "Birleştirme başarısız", "err");
      return;
    }
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `Kantar_Birlesik_${Date.now()}.pdf`;
    a.click();
    URL.revokeObjectURL(a.href);
    toast("Birleşik PDF indirildi");
  } catch {
    toast("Birleştirme hatası", "err");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  if (!document.getElementById("kantar-tbody")) return;

  document.querySelectorAll(".metric[data-f]").forEach((m) => {
    m.addEventListener("click", () => {
      kFilter = m.dataset.f;
      document.querySelectorAll(".metric[data-f]").forEach((x) => x.classList.toggle("active", x === m));
      kantarYenile();
    });
  });

  let t;
  document.getElementById("k-search").addEventListener("input", (e) => {
    clearTimeout(t);
    t = setTimeout(() => { kSearch = e.target.value || ""; kantarYenile(); }, 220);
  });

  document.getElementById("k-check-all").addEventListener("change", (e) => {
    document.querySelectorAll("#kantar-tbody .row-check").forEach((c) => { c.checked = e.target.checked; });
  });

  document.querySelectorAll("[data-close]").forEach((b) => {
    b.addEventListener("click", () => closeModal(b.dataset.close));
  });
  document.querySelectorAll(".modal-bg").forEach((bg) => {
    bg.addEventListener("click", (e) => { if (e.target === bg) bg.classList.remove("acik"); });
  });

  document.getElementById("btn-k-add").onclick = () => openModal("modal-k-add");
  document.getElementById("btn-k-yilport").onclick = () => openModal("modal-k-yilport");
  document.getElementById("btn-k-refresh").onclick = () => kantarYenile();

  document.getElementById("k-add-save").onclick = async () => {
    const body = {
      konteynerler: document.getElementById("k-add-cntrs").value,
      dosya_no: document.getElementById("k-add-dosya").value,
      ref: document.getElementById("k-add-ref").value,
      firma: document.getElementById("k-add-firma").value,
      kaynak: document.getElementById("k-add-kaynak").value,
    };
    const res = await fetch("/api/kantar/takip/ekle", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const data = await res.json();
    if (data.success) {
      toast(`${data.eklenen_sayisi} eklendi`);
      closeModal("modal-k-add");
      document.getElementById("k-add-cntrs").value = "";
      kantarYenile();
    } else toast(data.error || "Eklenemedi", "err");
  };

  document.getElementById("k-cookie-save").onclick = async () => {
    const cookie = document.getElementById("k-cookie").value;
    const res = await fetch("/api/kantar/yilport/oturum", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ cookie }) });
    const data = await res.json();
    if (data.success) { toast("Yılport oturumu kaydedildi"); closeModal("modal-k-yilport"); kantarYenile(); }
    else toast(data.error || "Kayıt başarısız", "err");
  };

  document.getElementById("btn-k-sync").onclick = async () => {
    toast("Evrim/Excel aktarılıyor…");
    const res = await fetch("/api/kantar/takip/sync", { method: "POST" });
    const data = await res.json();
    if (data.success) { toast(`${data.eklenen || 0} konteyner aktarıldı`); kantarYenile(); }
    else toast(data.error || "Aktarım hatası", "err");
  };

  document.getElementById("btn-k-scan").onclick = async () => {
    const btn = document.getElementById("btn-k-scan");
    btn.disabled = true;
    toast("Havuz taranıyor…");
    try {
      const res = await fetch("/api/kantar/takip/kontrol-et", { method: "POST" });
      const data = await res.json();
      toast(data.success ? "Tarama tamamlandı" : (data.error || "Tarama sonucu belirsiz"), data.success ? undefined : "err");
      await kantarYenile();
    } finally { btn.disabled = false; }
  };

  document.getElementById("btn-k-pdf").onclick = () => {
    const sel = selectedCntrs();
    if (!sel.length) return toast("PDF için satır seçin", "err");
    sel.forEach((c) => kantarPdf(c));
  };
  document.getElementById("btn-k-merge").onclick = () => kantarMerge();
  document.getElementById("btn-k-query").onclick = async () => {
    const sel = selectedCntrs();
    if (!sel.length) return toast("Sorgulanacak satır seçin", "err");
    for (const c of sel) await kantarSorgula(c);
  };
  document.getElementById("btn-k-del").onclick = async () => {
    const sel = selectedCntrs();
    if (!sel.length) return toast("Silinecek satır seçin", "err");
    if (!confirm(`${sel.length} konteyner silinsin mi?`)) return;
    const res = await fetch("/api/kantar/takip/sil-coklu", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ konteynerler: sel }) });
    const data = await res.json();
    if (data.success) { toast(`${data.removed} silindi`); kantarYenile(); }
    else toast(data.error || "Silinemedi", "err");
  };
  document.getElementById("btn-k-clear").onclick = async () => {
    if (!confirm("Tüm kantar havuzu temizlensin mi?")) return;
    const res = await fetch("/api/kantar/takip/temizle", { method: "POST" });
    const data = await res.json();
    if (data.success) { toast(`Temizlendi (${data.cleared})`); kantarYenile(); }
    else toast(data.error || "Temizlenemedi", "err");
  };

  kantarYenile();
  setInterval(kantarYenile, 60000);
});
