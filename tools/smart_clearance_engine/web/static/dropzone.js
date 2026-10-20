// dropzone.js — surukle-birak dosya yukleme bileseni.
// Her .dropzone kendi gizli <input type=file>'ini ve (varsa) esleşen
// id'li dosya cip listesini yonetir. Kabul edilen dosya turleri input'un
// KENDI `accept` niteliginden okunur (orn. accept=".xlsx" ya da
// accept=".pdf,.xlsx,.doc,.png") — ESKIDEN her yerde SABIT olarak sadece
// PDF kabul ediliyordu; bu, Talep/Konu eklerinde accept=".xlsx,..." yazsa
// bile PDF olmayan bir dosyanin surukle-birakta (hatta tikla-sec'te de,
// ayni addFiles() fonksiyonundan gectigi icin) SESSIZCE reddedilmesine
// yol aciyordu — gercek bir bug, bu genellemeyle duzeldi.

function _dzKabulListesi(input) {
    return (input.getAttribute("accept") || "")
        .split(",").map((s) => s.trim().toLowerCase()).filter(Boolean);
}

function _dzDosyaKabulEdilir(file, kabulListesi) {
    if (!kabulListesi.length) return true; // accept belirtilmemisse hepsi kabul
    const adi = (file.name || "").toLowerCase();
    const tur = (file.type || "").toLowerCase();
    return kabulListesi.some((kural) => {
        if (kural.startsWith(".")) return adi.endsWith(kural);
        if (kural.endsWith("/*")) return tur.startsWith(kural.slice(0, -1));
        return tur === kural;
    });
}

function initDropzones(root = document) {
    root.querySelectorAll(".dropzone").forEach((zone) => {
        if (zone.dataset.dzInit) return; // pjax ile tekrar taranirsa iki kez baglanmasin
        if (zone.dataset.dzSkip) return; // kendi ozel mantigi olan alanlar (orn. klasor secme) icin
        zone.dataset.dzInit = "1";

        const input = zone.querySelector("input[type=file]");
        if (!input) return;
        const listId = zone.dataset.list;
        const list = listId ? document.getElementById(listId) : null;
        let files = [];

        function sync() {
            const dt = new DataTransfer();
            files.forEach((f) => dt.items.add(f));
            input.files = dt.files;
            renderChips();
        }

        function renderChips() {
            if (!list) return;
            list.innerHTML = "";
            files.forEach((f, idx) => {
                const chip = document.createElement("span");
                chip.className = "file-chip";
                chip.innerHTML = `<span>${f.name}</span>`;
                const btn = document.createElement("button");
                btn.type = "button";
                btn.innerHTML = "&times;";
                btn.title = "Kaldır";
                btn.addEventListener("click", (e) => {
                    e.stopPropagation();
                    files.splice(idx, 1);
                    sync();
                });
                chip.appendChild(btn);
                list.appendChild(chip);
            });
        }

        function addFiles(newFiles) {
            const kabulListesi = _dzKabulListesi(input);
            const kabul = newFiles.filter((f) => _dzDosyaKabulEdilir(f, kabulListesi));
            if (!kabul.length) return;
            if (input.multiple) {
                files.push(...kabul);
            } else {
                // Tek dosyali input (orn. Is Takip Raporu Excel'i): yeni
                // birakilan/secilen dosya ONCEKINI DEGISTIRIR, eklenmez.
                files = [kabul[kabul.length - 1]];
            }
            sync();
        }

        zone.addEventListener("click", (e) => {
            if (e.target.tagName !== "BUTTON") input.click();
        });
        input.addEventListener("change", () => addFiles(Array.from(input.files || [])));

        ["dragenter", "dragover"].forEach((evt) =>
            zone.addEventListener(evt, (e) => {
                e.preventDefault();
                zone.classList.add("dragover");
            })
        );
        ["dragleave", "drop"].forEach((evt) =>
            zone.addEventListener(evt, (e) => {
                e.preventDefault();
                zone.classList.remove("dragover");
            })
        );
        zone.addEventListener("drop", (e) => addFiles(Array.from(e.dataTransfer.files || [])));
    });
}

document.addEventListener("DOMContentLoaded", () => initDropzones());
// pjax.js, icerik degistiginde bunu tekrar cagirir (window uzerinden erisim icin disari acilir)
window.initDropzones = initDropzones;
