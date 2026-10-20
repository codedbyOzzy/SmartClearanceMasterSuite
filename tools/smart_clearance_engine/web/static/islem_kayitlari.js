// islem_kayitlari.js — "İşlem Kaydı" sayfasındaki toplu giriş formu:
// satır ekle/sil, tür seçimine göre "diğer" metin kutusunu göster/gizle,
// PO alanına yazarken (Enter'sız) şefin Excel'inden gelen canlı öneri.
// Sidebar'daki arama kutusundan (arama_canli.js) FARKI: burada bir
// sonuca tıklamak bir yere GİTMEZ, sadece o satırın PO alanını doldurur.
//
// Öneri kutusu BİLEREK document.body'ye (position:fixed, ekran koordinatlı)
// eklenir, PO input'unun içinde bulunduğu <td>'ye DEĞİL — ".card" giriş
// animasyonu (card-in) bitişte "transform: translateY(0)" bıraktığı için
// her .card kendi z-index katmanını oluşturuyor; tablo hücresi içine
// eklenen bir dropdown, bir SONRAKİ .card'ın (Kayıtlar listesi) ARKASINDA
// kalıyordu. body'ye eklemek bu tuzağı tamamen atlar.

function initIslemKayitlari(root = document) {
    const govde = root.querySelector("#satir-govde");
    const sablon = root.querySelector("#satir-sablon");
    const ekleBtn = root.querySelector("#satir-ekle");
    if (!govde || !sablon || !ekleBtn || govde.dataset.ikInit) return;
    govde.dataset.ikInit = "1";

    let aktifDropdown = null;

    function kapatOneri() {
        if (aktifDropdown) {
            aktifDropdown.remove();
            aktifDropdown = null;
        }
    }

    function oneriCiz(poInput, sonuclar) {
        kapatOneri();
        if (!sonuclar.length) return;

        // PO alanı tablo hücresinde dar (~100px) olabilir — PO numaraları
        // (10+ hane) + "AÇILMAMIŞ" gibi metinler orada kesilirdi. Dropdown
        // artık input'un genişliğine değil, sabit/geniş bir genişliğe
        // sahip (ekran kenarından taşarsa sola kaydırılır).
        const GENISLIK = 260;
        const rect = poInput.getBoundingClientRect();
        const sol = Math.min(rect.left, window.innerWidth - GENISLIK - 8);
        const dd = document.createElement("div");
        dd.className = "sidebar-search-dropdown ik-dropdown-fixed";
        dd.style.position = "fixed";
        dd.style.top = (rect.bottom + 4) + "px";
        dd.style.left = Math.max(8, sol) + "px";
        dd.style.width = GENISLIK + "px";

        sonuclar.forEach((s) => {
            const a = document.createElement("a");
            a.href = "#";
            a.className = "ssd-item";
            a.innerHTML =
                '<span class="ssd-ic">◷</span>' +
                '<span class="ssd-metin"><span class="ssd-baslik"></span><span class="ssd-alt"></span></span>';
            a.querySelector(".ssd-baslik").textContent = s.baslik;
            const altEl = a.querySelector(".ssd-alt");
            altEl.textContent = s.alt;
            if (s.acilmamis) altEl.classList.add("ssd-acilmamis");
            a.addEventListener("click", (e) => {
                e.preventDefault();
                poInput.value = s.baslik;
                kapatOneri();
            });
            dd.appendChild(a);
        });

        document.body.appendChild(dd);
        aktifDropdown = dd;
    }

    function satirBagla(satir) {
        const turSelect = satir.querySelector("select[name=tur]");
        const ozelInput = satir.querySelector("input[name=tur_ozel]");
        const poInput = satir.querySelector("input[name=po_no]");
        const silBtn = satir.querySelector(".ik-satir-sil");

        function ozelGoster() {
            const gosterilsin = turSelect.value === "diger";
            ozelInput.style.display = gosterilsin ? "" : "none";
            ozelInput.required = gosterilsin;
        }
        turSelect.addEventListener("change", ozelGoster);
        ozelGoster();

        silBtn.addEventListener("click", () => satir.remove());

        let debounceTimer = null;
        poInput.addEventListener("input", () => {
            clearTimeout(debounceTimer);
            const sorgu = poInput.value.trim();
            kapatOneri();
            if (sorgu.length < 2) return;
            debounceTimer = setTimeout(() => {
                fetch("/arama/canli?q=" + encodeURIComponent(sorgu))
                    .then((r) => r.json())
                    .then((veri) => {
                        const takipSonuclari = veri.sonuclar.filter((s) => s.tur === "takip");
                        oneriCiz(poInput, takipSonuclari);
                    })
                    .catch(() => {});
            }, 250);
        });
    }

    document.addEventListener("click", (e) => {
        if (aktifDropdown && !aktifDropdown.contains(e.target) && e.target.name !== "po_no") kapatOneri();
    });
    // capture:true GEREKLİ (sayfa scroll'u alt kapsayıcılarda olabilir, "scroll"
    // olayı yukarı balonlamaz) — ama bu yüzden listenin KENDİ İÇİNDEKİ kaydırması
    // da (overflow-y:auto) buraya düşer; e.target dropdown'ın kendisiyse görmezden
    // gel, yoksa fare listenin üzerinde kaydırılınca liste hemen kapanıp scroll'u
    // engelliyordu (kullanıcı bunu gerçek kullanımda fark etti).
    document.addEventListener("scroll", (e) => {
        if (aktifDropdown && e.target !== aktifDropdown) kapatOneri();
    }, true);
    window.addEventListener("resize", () => kapatOneri());

    govde.querySelectorAll(".ik-satir").forEach(satirBagla);

    ekleBtn.addEventListener("click", () => {
        const yeni = sablon.content.cloneNode(true);
        govde.appendChild(yeni);
        satirBagla(govde.lastElementChild);
    });
}

document.addEventListener("DOMContentLoaded", () => initIslemKayitlari());
window.initIslemKayitlari = initIslemKayitlari;
