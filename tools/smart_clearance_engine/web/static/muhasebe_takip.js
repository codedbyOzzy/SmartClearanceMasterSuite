// muhasebe_takip.js — Muhasebe Takip panelindeki sekme (Tümü/Eşleşenler/
// Boşta Kalanlar), canlı arama filtrelemesi, düzenleme modalı ve silme onayı.
// Bu sayfa tam yükleme yapar (pjax olmadan açılır), bu script DOMContentLoaded'da çalışır.

function initMuhasebeTakip() {
    const tablo = document.getElementById("muhasebe-tablo");
    if (!tablo) return;

    const satirlar = Array.from(tablo.querySelectorAll("tbody tr"));
    const sekmeler = document.querySelectorAll(".muh-tab");
    const aramaKutusu = document.getElementById("muhasebe-arama");
    const sonucYokMesaji = document.getElementById("muhasebe-sonuc-yok");
    let aktifFiltre = "tumu";

    function uygula() {
        const aramaMetni = (aramaKutusu.value || "").trim().toLowerCase();
        let gorunenSayisi = 0;

        satirlar.forEach((satir) => {
            const gonderildi = satir.dataset.gonderildi === "true";
            const filtreUyuyor =
                aktifFiltre === "tumu" ||
                (aktifFiltre === "eslesen" && gonderildi) ||
                (aktifFiltre === "bosta" && !gonderildi);

            const aramaUyuyor = !aramaMetni || satir.textContent.toLowerCase().includes(aramaMetni);

            const gorunsun = filtreUyuyor && aramaUyuyor;
            satir.style.display = gorunsun ? "" : "none";
            if (gorunsun) gorunenSayisi++;
        });

        if (sonucYokMesaji) sonucYokMesaji.style.display = gorunenSayisi === 0 ? "block" : "none";
    }

    sekmeler.forEach((sekme) => {
        sekme.addEventListener("click", () => {
            sekmeler.forEach((s) => s.classList.remove("active"));
            sekme.classList.add("active");
            aktifFiltre = sekme.dataset.filtre;
            uygula();
        });
    });

    if (aramaKutusu) {
        aramaKutusu.addEventListener("input", uygula);
    }

    // ── Silme Onayı ──
    document.querySelectorAll(".js-muh-sil-form").forEach((form) => {
        form.addEventListener("submit", (e) => {
            if (!confirm("Bu muhasebe kaydını silmek istediğinize emin misiniz?")) {
                e.preventDefault();
            }
        });
    });

    // ── Düzenleme Modalı ──
    const modal = document.getElementById("muhEditModal");
    const editForm = document.getElementById("muhEditForm");
    const dosyaInput = document.getElementById("modal_dosya_no");
    const kapatBtn = document.querySelector(".js-modal-kapat");

    if (modal && editForm && dosyaInput) {
        document.querySelectorAll(".js-muh-edit").forEach((btn) => {
            btn.addEventListener("click", (e) => {
                e.preventDefault();
                e.stopPropagation();
                const id = btn.dataset.id;
                const dosya = btn.dataset.dosya;
                editForm.action = "/muhasebe-takip/duzenle/" + id;
                dosyaInput.value = dosya || "";
                modal.style.display = "flex";
                setTimeout(() => {
                    dosyaInput.focus({ preventScroll: true });
                    dosyaInput.select();
                }, 10);
            });
        });

        if (kapatBtn) {
            kapatBtn.addEventListener("click", () => {
                modal.style.display = "none";
            });
        }

        modal.addEventListener("click", (e) => {
            if (e.target === modal) {
                modal.style.display = "none";
            }
        });
    }

    // ── URL Parametresinden (?po=... veya ?dosya=...) Akıllı Vurgulama & Zıplama ──
    const urlParams = new URLSearchParams(window.location.search);
    const hedefPo = urlParams.get("po") || urlParams.get("dosya") || urlParams.get("ref");
    if (hedefPo) {
        const h = hedefPo.trim().toLowerCase();
        let bulunanSatir = null;
        satirlar.forEach((satir) => {
            const poNo = (satir.dataset.po || "").toLowerCase();
            const dosyaNo = (satir.dataset.dosya || "").toLowerCase();
            const metin = satir.textContent.toLowerCase();
            if (poNo === h || dosyaNo === h || metin.includes(h)) {
                if (!bulunanSatir) bulunanSatir = satir;
                satir.classList.add("sc-muh-zimpla-vurgu");
            }
        });
        if (bulunanSatir) {
            if (aramaKutusu) {
                aramaKutusu.value = hedefPo;
                uygula();
            }
            setTimeout(() => {
                bulunanSatir.scrollIntoView({ behavior: "smooth", block: "center" });
            }, 200);
        }
    }
}

window.initMuhasebeTakip = initMuhasebeTakip;

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initMuhasebeTakip);
} else {
    initMuhasebeTakip();
}
document.addEventListener("pjax:success", initMuhasebeTakip);
