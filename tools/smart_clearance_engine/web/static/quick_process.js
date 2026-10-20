// quick_process.js — Hizli Islem sayfasi: bir klasor secilince icindeki
// PDF'ler otomatik algilanir; kullanici hangi islemi yapmak istedigini
// secince ayni dosyalar o islemin mevcut endpoint'ine gonderilir. Beyanname
// Kontrol haric digerleri zaten var olan endpoint'leri aynen kullanir —
// beyanname/fatura ayrimi sunucu tarafinda (/hizli-islem/beyanname-kontrol)
// icerige bakilarak otomatik yapilir.

(function () {
    const input = document.getElementById("quick-folder-input");
    const zone = document.getElementById("quick-folder-zone");
    const list = document.getElementById("quick-file-list");
    const actions = document.getElementById("quick-actions");
    const grid = document.getElementById("quick-action-grid");
    const actionsLabel = document.getElementById("quick-actions-label");
    const processing = document.getElementById("quick-processing");
    const processingSub = document.getElementById("quick-processing-sub");
    const status = document.getElementById("quick-status");
    if (!input || !zone) return;

    const ENDPOINTS = {
        "excel-aktarim": { url: "/islem", field: "pdfler" },
        "beyanname-kontrol": { url: "/hizli-islem/beyanname-kontrol", field: "pdfler" },
        "master-kontrol": { url: "/master-kontrol", field: "faturalar" },
        "beyanname-taslak": { url: "/beyanname-taslak", field: "pdfler" },
    };

    const PROCESSING_MESSAGES = [
        "Dosyalar gönderiliyor...",
        "PDF'ler okunuyor...",
        "Kalemler ayrıştırılıyor...",
        "Sonuç hazırlanıyor...",
    ];
    let processingInterval = null;

    function showProcessing() {
        actionsLabel.style.display = "none";
        grid.style.display = "none";
        processing.style.display = "flex";
        let i = 0;
        processingSub.textContent = PROCESSING_MESSAGES[0];
        processingInterval = setInterval(() => {
            i = (i + 1) % PROCESSING_MESSAGES.length;
            processingSub.textContent = PROCESSING_MESSAGES[i];
        }, 1100);
    }

    function hideProcessing() {
        if (processingInterval) clearInterval(processingInterval);
        processingInterval = null;
        processing.style.display = "none";
        grid.style.display = "";
        actionsLabel.style.display = "";
    }

    let pdfFiles = [];

    zone.addEventListener("click", () => input.click());
    input.addEventListener("change", () => {
        pdfFiles = Array.from(input.files || []).filter(
            (f) => f.type === "application/pdf" || f.name.toLowerCase().endsWith(".pdf")
        );
        renderChips();
    });

    function renderChips() {
        list.innerHTML = "";
        pdfFiles.forEach((f) => {
            const chip = document.createElement("span");
            chip.className = "file-chip";
            chip.innerHTML = `<span>${f.name}</span>`;
            list.appendChild(chip);
        });
        actions.style.display = pdfFiles.length ? "block" : "none";
        status.textContent = pdfFiles.length
            ? `${pdfFiles.length} PDF algılandı.`
            : "Seçilen klasörde PDF bulunamadı.";
    }

    document.querySelectorAll(".quick-action-card").forEach((btn) => {
        btn.addEventListener("click", async () => {
            if (!pdfFiles.length) return;
            const cfg = ENDPOINTS[btn.dataset.action];
            if (!cfg) return;

            showProcessing();

            const formData = new FormData();
            pdfFiles.forEach((f) => formData.append(cfg.field, f));
            try {
                const res = await fetch(cfg.url, { method: "POST", body: formData });
                if (res.ok) {
                    window.location.href = res.url;
                    return;
                }
                let detail = "";
                try {
                    const data = await res.json();
                    if (data && data.detail) detail = ` (${data.detail})`;
                } catch (e) { /* yanit JSON degilse yoksay */ }
                hideProcessing();
                status.textContent = `İşlem başarısız oldu${detail}. Lütfen tekrar deneyin.`;
            } catch (e) {
                hideProcessing();
                status.textContent = "Bir hata oluştu, tekrar deneyin.";
            }
        });
    });
})();
