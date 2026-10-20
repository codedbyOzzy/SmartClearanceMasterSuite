// tema.js — SmartClearance Gece / Gündüz Modu (Dark Theme) Yönetimi
// Kullanıcının tercihini localStorage'da saklar ve anında uygular.

function scTemaUygula(darkMi) {
    const root = document.documentElement;
    const body = document.body;
    const icon = document.getElementById("tema-icon");
    const metin = document.getElementById("tema-metin");

    if (darkMi) {
        root.setAttribute("data-theme", "dark");
        root.classList.add("dark-mode");
        if (body) body.classList.add("dark-mode");
        localStorage.setItem("sc_tema", "dark");
        if (icon) icon.textContent = "☀️";
        if (metin) metin.textContent = "Gündüz Modu";
    } else {
        root.removeAttribute("data-theme");
        root.classList.remove("dark-mode");
        if (body) body.classList.remove("dark-mode");
        localStorage.setItem("sc_tema", "light");
        if (icon) icon.textContent = "🌙";
        if (metin) metin.textContent = "Gece Modu";
    }
}

function scTemaBaslat() {
    const tercih = localStorage.getItem("sc_tema") === "dark";
    scTemaUygula(tercih);

    const btn = document.getElementById("tema-toggle-btn");
    if (btn && !btn.dataset.temaBound) {
        btn.dataset.temaBound = "1";
        btn.addEventListener("click", () => {
            const mevcutDark = document.documentElement.getAttribute("data-theme") === "dark";
            scTemaUygula(!mevcutDark);
        });
    }
}

function scSidebarToggleUygula(collapsedMi) {
    const root = document.documentElement;
    const body = document.body;
    const btn = document.getElementById("sidebar-collapse-toggle");

    if (collapsedMi) {
        root.classList.add("sidebar-collapsed");
        if (body) body.classList.add("sidebar-collapsed");
        localStorage.setItem("sc_sidebar_collapsed", "1");
        if (btn) btn.setAttribute("title", "Yan Paneli Genişlet (Ctrl + B)");
    } else {
        root.classList.remove("sidebar-collapsed");
        if (body) body.classList.remove("sidebar-collapsed");
        localStorage.setItem("sc_sidebar_collapsed", "0");
        if (btn) btn.setAttribute("title", "Yan Paneli Daralt (Ctrl + B)");
    }
}

function scSidebarToggleBaslat() {
    const tercih = localStorage.getItem("sc_sidebar_collapsed") === "1";
    scSidebarToggleUygula(tercih);

    const btn = document.getElementById("sidebar-collapse-toggle");
    if (btn && !btn.dataset.toggleBound) {
        btn.dataset.toggleBound = "1";
        btn.addEventListener("click", () => {
            const mevcutCollapsed = document.documentElement.classList.contains("sidebar-collapsed");
            scSidebarToggleUygula(!mevcutCollapsed);
        });
    }

    if (!window._scSidebarKeyBound) {
        window._scSidebarKeyBound = true;
        document.addEventListener("keydown", (e) => {
            if ((e.ctrlKey || e.metaKey) && (e.key === "b" || e.key === "B")) {
                e.preventDefault();
                const mevcutCollapsed = document.documentElement.classList.contains("sidebar-collapsed");
                scSidebarToggleUygula(!mevcutCollapsed);
            }
        });
    }
}

function scSidebarTooltipBaslat() {
    const hud = document.getElementById("sc-sidebar-tooltip-hud");
    const titleEl = document.getElementById("sc-hud-title");
    const badgeEl = document.getElementById("sc-hud-badge");
    if (!hud || !titleEl || !badgeEl) return;

    const hedefler = document.querySelectorAll(".sidebar [data-title]");
    hedefler.forEach(el => {
        if (el.dataset.hudBound) return;
        el.dataset.hudBound = "1";

        el.addEventListener("mouseenter", () => {
            if (!document.documentElement.classList.contains("sidebar-collapsed")) {
                hud.classList.remove("hud-aktif");
                return;
            }
            const baslik = el.getAttribute("data-title") || "";
            const kisayol = el.getAttribute("data-shortcut") || "";
            titleEl.textContent = baslik;

            if (kisayol) {
                badgeEl.textContent = kisayol;
                badgeEl.style.display = "inline-block";
            } else {
                badgeEl.style.display = "none";
            }

            const rect = el.getBoundingClientRect();
            const topPos = rect.top + (rect.height / 2);
            hud.style.top = `${topPos}px`;
            hud.classList.add("hud-aktif");
        });

        el.addEventListener("mouseleave", () => {
            hud.classList.remove("hud-aktif");
        });
    });

    const sidebar = document.getElementById("sidebar");
    if (sidebar && !sidebar.dataset.hudLeaveBound) {
        sidebar.dataset.hudLeaveBound = "1";
        sidebar.addEventListener("mouseleave", () => {
            hud.classList.remove("hud-aktif");
        });
    }
}

// Sayfa ilk yüklendiğinde ve PJAX ile gezinirken temayı, kenar çubuğunu ve animasyonlu HUD aracını başlat:
document.addEventListener("DOMContentLoaded", () => {
    scTemaBaslat();
    scSidebarToggleBaslat();
    scSidebarTooltipBaslat();
});
document.addEventListener("pjax:success", () => {
    scTemaBaslat();
    scSidebarToggleBaslat();
    scSidebarTooltipBaslat();
});
window.scTemaBaslat = scTemaBaslat;
window.scSidebarToggleBaslat = scSidebarToggleBaslat;
window.scSidebarToggleUygula = scSidebarToggleUygula;
window.scSidebarTooltipBaslat = scSidebarTooltipBaslat;


