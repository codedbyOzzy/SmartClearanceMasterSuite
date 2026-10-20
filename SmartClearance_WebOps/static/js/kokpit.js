let filterType = "all";
let searchQ = "";
let selected = null;
let itemsCache = [];

function toast(msg, tip) {
  const el = document.createElement("div");
  el.className = "toast" + (tip === "err" ? " err" : "");
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 3200);
}

function stagePill(stage, title) {
  const t = (title || stage || "").toLowerCase();
  let cls = "info";
  if (t.includes("kapan")) cls = "ok";
  else if (t.includes("kırmızı") || t.includes("kirmizi") || t.includes("muayene")) cls = "bad";
  else if (t.includes("vergi") || t.includes("ordino") || t.includes("tareks")) cls = "warn";
  return `<span class="pill ${cls}">${title || stage || "—"}</span>`;
}

function showDetail(it) {
  selected = it;
  document.getElementById("c-detail-empty").hidden = true;
  document.getElementById("c-detail-body").hidden = false;
  document.getElementById("d-dosya").textContent = it.dosya || "—";
  document.getElementById("d-ref").textContent = it.ref || "—";
  document.getElementById("d-bl").textContent = it.bl || "—";
  document.getElementById("d-stage").innerHTML = stagePill(it.stage, it.stage_title);
  document.getElementById("d-hat").textContent = it.hat || "—";
  document.getElementById("d-bayi").textContent = it.bayi || "—";
  document.getElementById("d-liman").textContent = it.liman || "—";
  document.getElementById("d-beyan").textContent = it.beyanname_no || "—";
  document.getElementById("d-gtb").textContent = "—";
}

async function queryGtbForSelected() {
  if (!selected) return toast("Önce satır seçin", "err");
  let beyan = (selected.beyanname_no || "").trim();
  if (!beyan || beyan.length < 15) {
    // ref bazen 10 haneli Hankook ref olabilir — GTB 16 ister
    toast("Bu satırda 16 haneli beyanname yok", "err");
    return;
  }
  document.getElementById("d-gtb").textContent = "Sorgulanıyor…";
  try {
    const res = await fetch(`/api/cockpit/gtb/${encodeURIComponent(beyan)}`);
    const data = await res.json();
    if (data.success) {
      document.getElementById("d-gtb").textContent = data.durum || "OK";
      toast("GTB sonucu alındı");
    } else {
      document.getElementById("d-gtb").textContent = data.error || "Hata";
      toast(data.error || "GTB hatası", "err");
    }
  } catch {
    toast("GTB bağlantı hatası", "err");
  }
}

async function kokpitYenile() {
  const tbody = document.getElementById("kokpit-tbody");
  const url = `/api/cockpit?filter_type=${encodeURIComponent(filterType)}&q=${encodeURIComponent(searchQ)}&limit=400`;
  try {
    const res = await fetch(url, { cache: "no-store" });
    const data = await res.json();
    const stats = data.stats || {};
    document.getElementById("c-total").textContent = stats.total ?? data.count ?? 0;
    document.getElementById("c-active").textContent = stats.active ?? "—";
    document.getElementById("c-tax").textContent = stats.tax ?? "—";
    document.getElementById("c-closed").textContent = stats.closed ?? "—";
    document.getElementById("c-source-pill").textContent = `Kaynak: ${data.source || "—"}`;

    itemsCache = data.items || [];
    if (!itemsCache.length) {
      tbody.innerHTML = '<tr><td colspan="7" class="empty">Kayıt yok. Excel yolu, Evrim JSON veya data/Operasyon_Kokpiti.csv kontrol edin.</td></tr>';
      return;
    }
    tbody.innerHTML = itemsCache.map((it, idx) => `<tr data-i="${idx}">
      <td class="mono"><strong>${it.dosya || "—"}</strong></td>
      <td class="mono">${it.ref || "—"}</td>
      <td class="mono">${it.bl || "—"}</td>
      <td>${stagePill(it.stage, it.stage_title)}</td>
      <td>${it.hat || "—"}</td>
      <td>${it.bayi || "—"}</td>
      <td>${it.liman || "—"}</td>
    </tr>`).join("");

    tbody.querySelectorAll("tr[data-i]").forEach((tr) => {
      tr.addEventListener("click", () => {
        tbody.querySelectorAll("tr").forEach((r) => r.classList.remove("selected"));
        tr.classList.add("selected");
        showDetail(itemsCache[Number(tr.dataset.i)]);
      });
    });
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="7" class="empty">Yüklenemedi: ${e}</td></tr>`;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  if (!document.getElementById("kokpit-tbody")) return;

  document.querySelectorAll(".metric[data-f]").forEach((m) => {
    m.addEventListener("click", () => {
      filterType = m.dataset.f;
      document.querySelectorAll(".metric[data-f]").forEach((x) => x.classList.toggle("active", x.dataset.f === filterType));
      document.querySelectorAll("#c-filters button").forEach((b) => b.classList.toggle("active", b.dataset.f === filterType));
      kokpitYenile();
    });
  });

  document.getElementById("c-filters").addEventListener("click", (ev) => {
    const btn = ev.target.closest("button[data-f]");
    if (!btn) return;
    filterType = btn.dataset.f;
    document.querySelectorAll("#c-filters button").forEach((b) => b.classList.toggle("active", b === btn));
    document.querySelectorAll(".metric[data-f]").forEach((x) => x.classList.toggle("active", x.dataset.f === filterType));
    kokpitYenile();
  });

  let t = null;
  document.getElementById("c-search").addEventListener("input", (ev) => {
    clearTimeout(t);
    t = setTimeout(() => { searchQ = ev.target.value || ""; kokpitYenile(); }, 250);
  });

  document.getElementById("btn-c-refresh").onclick = () => { toast("Yenileniyor…"); kokpitYenile(); };
  document.getElementById("btn-c-gtb").onclick = () => queryGtbForSelected();
  document.getElementById("btn-d-gtb").onclick = () => queryGtbForSelected();
  document.getElementById("btn-c-export").onclick = () => {
    window.location.href = `/api/cockpit/export?filter_type=${encodeURIComponent(filterType)}&q=${encodeURIComponent(searchQ)}`;
  };

  kokpitYenile();
});
