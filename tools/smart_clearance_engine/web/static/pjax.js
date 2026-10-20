// pjax.js — hafif "sahte SPA" gecisleri.
// SADECE data-pjax ile isaretlenmis link/formlar bu davranisi kullanir
// (sidebar navigasyonu + ana yukleme formlari + basit "geri" linkleri).
// Isaretlenmemis her sey (indirme linkleri, gorsel karsilastirma sayfasi
// gibi ozel script'i olan sayfalar) NORMAL calismaya devam eder — boylece
// PDF.js gibi modul script'lerini yeniden calistirma karmasikligina hic
// girilmez.

const PROCESSING_MESSAGES = [
    "PDF'ler okunuyor...",
    "Kalemler ayrıştırılıyor...",
    "Belgeler karşılaştırılıyor...",
    "Sonuç hazırlanıyor...",
];

function showProcessingScreen() {
    const el = document.getElementById("page-content");
    el.className = "container";
    el.innerHTML = `
      <div class="processing-screen">
        <div class="scan-doc"><div class="scan-beam"></div></div>
        <div class="processing-title">İşleniyor</div>
        <div class="processing-sub" id="processing-sub"></div>
      </div>`;
    const sub = document.getElementById("processing-sub");
    let i = 0;
    sub.textContent = PROCESSING_MESSAGES[0];
    const interval = setInterval(() => {
        i = (i + 1) % PROCESSING_MESSAGES.length;
        sub.textContent = PROCESSING_MESSAGES[i];
    }, 1100);
    return () => clearInterval(interval);
}

function updateSidebarActive(url) {
    document.querySelectorAll(".sidebar-nav a").forEach((a) => {
        const path = new URL(a.href, window.location.origin).pathname;
        const match = url === path || url.startsWith(path + "/");
        a.classList.toggle("active", match);
    });
}

async function swapContent(html, url, pushHistory) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, "text/html");
    const newContent = doc.getElementById("page-content");
    const current = document.getElementById("page-content");
    if (!newContent) {
        window.location.href = url;
        return;
    }

    current.classList.add("pc-leaving");
    await new Promise((r) => setTimeout(r, 120));

    // Önceki sayfadan body altına taşınmış olabilecek modal kalıntılarını (zombie modalları) temizle:
    document.querySelectorAll("body > .muh-modal-overlay, body > #muhEditModal").forEach(el => el.remove());

    current.innerHTML = newContent.innerHTML;
    current.className = newContent.className;
    current.classList.add("pc-entering");
    document.title = doc.title;

    const path = new URL(url, window.location.origin).pathname;
    updateSidebarActive(path);
    if (pushHistory) window.history.pushState({ pjax: true }, "", url);

    window.initDropzones && window.initDropzones(current);
    window.initCopyAndAccordion && window.initCopyAndAccordion(current);
    window.initMailButtons && window.initMailButtons(current);
    window.masaustuBildirimAyariniBagla && window.masaustuBildirimAyariniBagla(current);
    window.initTakipRaporu && window.initTakipRaporu();
    window.initPeekListeners && window.initPeekListeners();
    window.initBreadcrumb && window.initBreadcrumb();
    window.initBatchTray && window.initBatchTray();
    window.initSpotlight && window.initSpotlight();
    bindPjaxLinks(current);
    bindPjaxForms(current);
    document.dispatchEvent(new Event("pjax:success"));
}

async function navigateTo(url, pushHistory = true) {
    try {
        const res = await fetch(url, {
            cache: "no-store",
            headers: {
                "Cache-Control": "no-cache",
                "Pragma": "no-cache"
            }
        });
        const html = await res.text();
        await swapContent(html, res.url, pushHistory);
    } catch (e) {
        window.location.href = url;
    }
}

async function submitPjaxForm(form) {
    const stop = showProcessingScreen();
    try {
        const res = await fetch(form.action, { method: "POST", body: new FormData(form) });
        const html = await res.text();
        stop();
        await swapContent(html, res.url, true);
    } catch (e) {
        stop();
        window.location.reload();
    }
}

function bindPjaxLinks(root = document) {
    root.querySelectorAll("a[data-pjax]").forEach((a) => {
        if (a.dataset.pjaxBound) return;
        a.dataset.pjaxBound = "1";
        a.addEventListener("click", (e) => {
            if (e.metaKey || e.ctrlKey || e.shiftKey) return;
            e.preventDefault();
            navigateTo(a.href);
        });
    });
}

function bindPjaxForms(root = document) {
    root.querySelectorAll("form[data-pjax]").forEach((f) => {
        if (f.dataset.pjaxBound) return;
        f.dataset.pjaxBound = "1";
        f.addEventListener("submit", (e) => {
            e.preventDefault();
            submitPjaxForm(f);
        });
    });
}

window.addEventListener("popstate", () => navigateTo(window.location.href, false));

document.addEventListener("DOMContentLoaded", () => {
    bindPjaxLinks();
    bindPjaxForms();

    const toggle = document.getElementById("sidebar-toggle");
    if (toggle) {
        toggle.addEventListener("click", () => document.getElementById("sidebar").classList.toggle("open"));
    }
});
