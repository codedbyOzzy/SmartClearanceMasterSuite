// bildirim.js — sidebar'daki "Anasayfa" rozetini periyodik olarak
// /bildirim/sayi'ya sorup gunceller. WebSocket YOK (3 kisilik ekipte
// gereksiz karmasiklik); 20 saniyede bir yoklama (polling) "anlik"
// hissini yeterince verir. PJAX sidebar'i yeniden yuklemedigi icin
// (sadece #page-content degisir) bu script sayfa boyunca calismaya
// devam eder, her sayfa gecisinde yeniden baslatilmaya gerek yoktur.
//
// Masaustu bildirimi (Notification API): TARAYICI izni + kullanicinin
// KENDI actigi bir tercih (localStorage, sunucuya hic gitmez — cihaza
// ozel) ikisi de gerekli. Kapaliyken de "en son gorulen bildirim id"si
// guncellenmeye devam eder ki kullanici SONRADAN acarsa gecmis
// bildirimler toplu halde patlamasin, sadece o andan sonrakiler gelsin.

const SC_BILDIRIM_TERCIH_ANAHTARI = "sc_masaustu_bildirim";
const SC_SON_GORULEN_ANAHTARI = "sc_son_bildirim_id";

function masaustuBildirimAcikMi() {
    return localStorage.getItem(SC_BILDIRIM_TERCIH_ANAHTARI) === "1";
}

function _enBuyukId(bildirimler, baslangic) {
    return bildirimler.reduce((m, b) => Math.max(m, b.id), baslangic);
}

const BILDIRIM_TUR_BASLIK = { talep: "Yeni Talep", konu: "Yeni Konu/Mesaj", not: "Yeni Not" };

function masaustuBildirimGoster(b) {
    if (!("Notification" in window) || Notification.permission !== "granted") return;
    const baslik = `${b.yazan_isim} — ${BILDIRIM_TUR_BASLIK[b.tur] || "Bildirim"}`;
    let bildirim;
    try {
        bildirim = new Notification(baslik, { body: b.ozet, tag: "sc-bildirim-" + b.id });
    } catch (e) {
        return; // bazi tarayicilarda kisitli baglamda Notification() firlatabilir
    }
    bildirim.onclick = () => {
        window.focus();
        const url = b.tur === "talep" ? `/talepler/${b.hedef}`
            : b.tur === "konu" ? `/ekip-akisi/konu/${b.hedef}`
            : `/takip-raporu/${b.hedef}#notlar`;
        window.location.href = url;
    };
}

async function bildirimRozetiniGuncelle() {
    const rozet = document.getElementById("bildirim-rozeti");
    try {
        const res = await fetch("/bildirim/sayi", {
            cache: "no-store",
            headers: {
                "Cache-Control": "no-cache",
                "Pragma": "no-cache"
            }
        });
        const veri = await res.json();

        if (rozet) {
            if (veri.adet > 0) {
                rozet.textContent = veri.adet;
                rozet.style.display = "inline-flex";
            } else {
                rozet.style.display = "none";
            }
        }

        const sonBildirimler = veri.son_bildirimler || [];
        if (sonBildirimler.length) {
            const sonGorulen = parseInt(localStorage.getItem(SC_SON_GORULEN_ANAHTARI) || "0", 10);
            if (masaustuBildirimAcikMi()) {
                sonBildirimler
                    .filter((b) => b.id > sonGorulen)
                    .sort((a, b) => a.id - b.id)
                    .forEach(masaustuBildirimGoster);
            }
            localStorage.setItem(SC_SON_GORULEN_ANAHTARI, String(_enBuyukId(sonBildirimler, sonGorulen)));
        }
    } catch (e) {
        // sessiz gec - agdaki gecici bir aksama bildirimi bozmasin
    }
}

function masaustuBildirimAyariniBagla(root = document) {
    const kutu = root.querySelector("#masaustu-bildirim-kutu");
    const testBtn = root.querySelector("#bildirim-test-btn");
    if (!kutu || kutu.dataset.bildirimBound) return;
    kutu.dataset.bildirimBound = "1";
    kutu.checked = masaustuBildirimAcikMi();

    if (testBtn) {
        testBtn.style.display = kutu.checked ? "inline" : "none";
        testBtn.addEventListener("click", (e) => {
            e.preventDefault();
            if (!("Notification" in window) || Notification.permission !== "granted") {
                alert("Önce bildirimlere izin vermen gerekiyor.");
                return;
            }
            try {
                new Notification("SmartClearance — Test Bildirimi 🔔", {
                    body: "Harika! Masaüstü bildirimlerin bu bilgisayarda sorunsuz çalışıyor.",
                    tag: "sc-test-" + Date.now()
                });
            } catch (err) {
                alert("Bildirim gösterilemedi: " + err.message);
            }
        });
    }

    kutu.addEventListener("change", async () => {
        if (!kutu.checked) {
            localStorage.setItem(SC_BILDIRIM_TERCIH_ANAHTARI, "0");
            if (testBtn) testBtn.style.display = "none";
            return;
        }
        if (!("Notification" in window)) {
            alert("Bu tarayıcı masaüstü bildirimlerini desteklemiyor.");
            kutu.checked = false;
            return;
        }
        let izin = Notification.permission;
        if (izin === "default") izin = await Notification.requestPermission();
        if (izin !== "granted") {
            alert("Bildirimlere izin verilmedi — açmak için tarayıcı site ayarlarından izin vermen gerekebilir.");
            kutu.checked = false;
            localStorage.setItem(SC_BILDIRIM_TERCIH_ANAHTARI, "0");
            if (testBtn) testBtn.style.display = "none";
            return;
        }
        localStorage.setItem(SC_BILDIRIM_TERCIH_ANAHTARI, "1");
        if (testBtn) testBtn.style.display = "inline";

        try {
            new Notification("SmartClearance — Bildirimler Aktif 🔔", {
                body: "Masaüstü bildirimleri açıldı. Yeni bir paslaşma notu veya soru eklendiğinde burada göreceksin.",
                tag: "sc-aktif-bildirim-" + Date.now()
            });
        } catch (e) {}

        try {
            const res = await fetch("/bildirim/sayi", {
                cache: "no-store",
                headers: {
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache"
                }
            });
            const veri = await res.json();
            const mevcut = parseInt(localStorage.getItem(SC_SON_GORULEN_ANAHTARI) || "0", 10);
            localStorage.setItem(SC_SON_GORULEN_ANAHTARI, String(_enBuyukId(veri.son_bildirimler || [], mevcut)));
        } catch (e) {}
    });
}

document.addEventListener("DOMContentLoaded", () => {
    bildirimRozetiniGuncelle();
    masaustuBildirimAyariniBagla();
    setInterval(bildirimRozetiniGuncelle, 10000);
});
window.masaustuBildirimAyariniBagla = masaustuBildirimAyariniBagla;
