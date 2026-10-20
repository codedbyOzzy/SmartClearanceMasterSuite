// favoriler.js — sol menüdeki "Favorilerim" kısayolları. Kişiye/cihaza özel,
// localStorage'da tutulur (sunucuya hiç gitmez) — masaüstü bildirim
// tercihiyle aynı desen (bkz. bildirim.js::sc_masaustu_bildirim).

const SC_FAVORI_ANAHTARI = "sc_favori_menuler";

function favorileriOku() {
    try {
        const ham = localStorage.getItem(SC_FAVORI_ANAHTARI);
        const liste = ham ? JSON.parse(ham) : [];
        return Array.isArray(liste) ? liste : [];
    } catch (e) {
        return [];
    }
}

function favorileriYaz(liste) {
    try {
        localStorage.setItem(SC_FAVORI_ANAHTARI, JSON.stringify(liste));
    } catch (e) {
        // localStorage kapalı/dolu olsa bile sayfa çalışmaya devam etsin
    }
}

function favoriDegistir(href) {
    const liste = favorileriOku();
    const idx = liste.indexOf(href);
    if (idx === -1) liste.push(href);
    else liste.splice(idx, 1);
    favorileriYaz(liste);
    favorileriCiz();
}

function favorileriCiz() {
    const kutu = document.getElementById("sidebar-favoriler");
    const govde = document.getElementById("sidebar-favoriler-govde");
    if (!kutu || !govde) return;
    const favoriler = favorileriOku();

    // Tam listedeki yildiz ikonlarini guncel favori durumuna gore boya
    document.querySelectorAll(".sidebar-nav-satir").forEach((satir) => {
        const link = satir.querySelector("a");
        const yildiz = satir.querySelector(".favori-yildiz");
        if (!link || !yildiz) return;
        const aktif = favoriler.indexOf(link.getAttribute("href")) !== -1;
        yildiz.textContent = aktif ? "★" : "☆";
        yildiz.classList.toggle("favori-aktif", aktif);
        yildiz.title = aktif ? "Favorilerden çıkar" : "Favorilere ekle";
    });

    if (!favoriler.length) {
        kutu.style.display = "none";
        return;
    }

    govde.innerHTML = "";
    favoriler.forEach((href) => {
        const kaynak = document.querySelector('.sidebar-nav-satir a[href="' + CSS.escape(href) + '"]');
        if (!kaynak) return;
        const kopya = kaynak.cloneNode(true);
        // Kopyalanan dugumde (orn. bildirim-rozeti) yinelenen id kalmasin
        kopya.removeAttribute("id");
        kopya.querySelectorAll("[id]").forEach((el) => el.removeAttribute("id"));
        govde.appendChild(kopya);
    });
    kutu.style.display = "";

    if (window.bindPjaxLinks) window.bindPjaxLinks(govde);
    if (window.updateSidebarActive) window.updateSidebarActive(window.location.pathname);
}

function favorilerBagla() {
    document.querySelectorAll(".favori-yildiz").forEach((yildiz) => {
        if (yildiz.dataset.favoriBound) return;
        yildiz.dataset.favoriBound = "1";
        yildiz.addEventListener("click", (e) => {
            e.preventDefault();
            e.stopPropagation();
            const satir = yildiz.closest(".sidebar-nav-satir");
            const link = satir && satir.querySelector("a");
            if (link) favoriDegistir(link.getAttribute("href"));
        });
    });
    favorileriCiz();
}

document.addEventListener("DOMContentLoaded", favorilerBagla);
