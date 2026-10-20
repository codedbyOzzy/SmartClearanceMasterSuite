let filterType = "all";
let searchQ = "";

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

async function kokpitYenile() {
  const tbody = document.getElementById("kokpit-tbody");
  const url = `/api/cockpit?filter_type=${encodeURIComponent(filterType)}&q=${encodeURIComponent(searchQ)}&limit=300`;
  try {
    const res = await fetch(url, { cache: "no-store" });
    const data = await res.json();
    const stats = data.stats || {};
    document.getElementById("c-total").textContent = stats.total ?? data.count ?? 0;
    document.getElementById("c-active").textContent = stats.active ?? "—";
    document.getElementById("c-tax").textContent = stats.tax ?? "—";
    document.getElementById("c-source").textContent = data.source || "—";

    const items = data.items || [];
    if (!items.length) {
      tbody.innerHTML = '<tr><td colspan="7" class="empty">Kayıt yok. Excel yolu, Evrim JSON veya Operasyon_Kokpiti.csv kontrol edin.</td></tr>';
      return;
    }
    tbody.innerHTML = items.map((it) => `<tr>
      <td class="mono"><strong>${it.dosya || "—"}</strong></td>
      <td class="mono">${it.ref || "—"}</td>
      <td class="mono">${it.bl || "—"}</td>
      <td>${stagePill(it.stage, it.stage_title)}</td>
      <td>${it.hat || "—"}</td>
      <td>${it.bayi || "—"}</td>
      <td>${it.liman || "—"}</td>
    </tr>`).join("");
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="7" class="empty">Yüklenemedi: ${e}</td></tr>`;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  if (!document.getElementById("kokpit-tbody")) return;

  document.getElementById("c-filters").addEventListener("click", (ev) => {
    const btn = ev.target.closest("button[data-f]");
    if (!btn) return;
    filterType = btn.getAttribute("data-f");
    document.querySelectorAll("#c-filters button").forEach((b) => b.classList.toggle("active", b === btn));
    kokpitYenile();
  });

  let t = null;
  document.getElementById("c-search").addEventListener("input", (ev) => {
    clearTimeout(t);
    t = setTimeout(() => {
      searchQ = ev.target.value || "";
      kokpitYenile();
    }, 250);
  });

  document.getElementById("btn-c-yenile").addEventListener("click", () => {
    toast("Yenileniyor…");
    kokpitYenile();
  });

  kokpitYenile();
});
