// arama_canli.js — sidebar'daki arama kutusuna, Enter'a basmadan yazarken
// canlı bir sonuç önerisi (açılır liste) ekler. Enter/submit hâlâ normal
// /arama sayfasına gider (tek kesin eşleşmede yönlendirme, kısmi eşleşmede
// tam liste) — bu SADECE hızlı bir ön izleme, tam arama akışının yerine
// geçmiyor. Sidebar pjax ile yeniden render edilmediği için (bkz.
// pjax.js yorumu) DOMContentLoaded'da bir kere bağlanması yeterli.

(function () {
    let debounceTimer = null;
    let mevcutIstek = 0;

    function kapatDropdown(kutu) {
        const eski = kutu.querySelector(".sidebar-search-dropdown");
        if (eski) eski.remove();
    }

    function ciz(kutu, veri) {
        kapatDropdown(kutu);
        const dd = document.createElement("div");
        dd.className = "sidebar-search-dropdown";

        if (!veri.sonuclar.length) {
            dd.innerHTML = '<div class="ssd-bos">Sonuç yok — Enter\'a basarak tam arama yapabilirsin.</div>';
            kutu.appendChild(dd);
            return;
        }

        veri.sonuclar.forEach((oge) => {
            const a = document.createElement("a");
            a.href = oge.url;
            a.setAttribute("data-pjax", "");
            a.className = "ssd-item";
            a.innerHTML =
                '<span class="ssd-ic">' + (oge.tur === "takip" ? "◷" : "⇄") + "</span>" +
                '<span class="ssd-metin">' +
                '<span class="ssd-baslik"></span>' +
                '<span class="ssd-alt"></span>' +
                "</span>";
            a.querySelector(".ssd-baslik").textContent = oge.baslik;
            const altEl = a.querySelector(".ssd-alt");
            altEl.textContent = oge.alt;
            if (oge.acilmamis) altEl.classList.add("ssd-acilmamis");
            dd.appendChild(a);
        });

        const toplam = veri.takip_toplam + veri.talep_toplam;
        if (toplam > veri.sonuclar.length) {
            const devam = document.createElement("div");
            devam.className = "ssd-devam";
            devam.textContent = "+" + (toplam - veri.sonuclar.length) + " sonuç daha — Enter'a bas";
            dd.appendChild(devam);
        }

        kutu.appendChild(dd);
        dd.addEventListener("click", () => kapatDropdown(kutu));
        window.bindPjaxLinks && window.bindPjaxLinks(dd);
    }

    function baglaAramaKutusu() {
        const form = document.querySelector(".sidebar-search");
        if (!form || form.dataset.canliBound) return;
        form.dataset.canliBound = "1";
        const input = form.querySelector("input[name=q]");
        if (!input) return;

        input.addEventListener("input", () => {
            clearTimeout(debounceTimer);
            const sorgu = input.value.trim();
            if (sorgu.length < 2) {
                kapatDropdown(form);
                return;
            }
            debounceTimer = setTimeout(() => {
                const istekNo = ++mevcutIstek;
                fetch("/arama/canli?q=" + encodeURIComponent(sorgu))
                    .then((r) => r.json())
                    .then((veri) => {
                        if (istekNo === mevcutIstek) ciz(form, veri);
                    })
                    .catch(() => {});
            }, 250);
        });

        input.addEventListener("keydown", (e) => {
            if (e.key === "Escape") kapatDropdown(form);
        });
        document.addEventListener("click", (e) => {
            if (!form.contains(e.target)) kapatDropdown(form);
        });
    }

    document.addEventListener("DOMContentLoaded", baglaAramaKutusu);
})();
