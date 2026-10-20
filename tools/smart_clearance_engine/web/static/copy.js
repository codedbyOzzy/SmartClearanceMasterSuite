// copy.js — alan degerlerini tek tikla panoya kopyalayan kucuk yardimci
// + akordiyon listelerinde "Tumunu Ac/Kapat" toplu kontrolu
// + sonuc tablolarini Excel'e yapistirilabilir (TAB ile ayrilmis) formatta
// panoya kopyalayan "Tabloyu Kopyala" butonu.

function initCopyButtons(root = document) {
    root.querySelectorAll(".btn-copy").forEach((btn) => {
        if (btn.dataset.copyInit) return;
        btn.dataset.copyInit = "1";
        btn.addEventListener("click", async (e) => {
            e.preventDefault();
            e.stopPropagation();
            const row = btn.closest(".field-row");
            const valueEl = row ? row.querySelector(".field-value") : null;
            const text = valueEl ? valueEl.textContent.trim() : "";
            if (!text || text === "—") return;
            try {
                await navigator.clipboard.writeText(text);
            } catch (err) {
                return;
            }
            btn.classList.add("copied");
            setTimeout(() => btn.classList.remove("copied"), 1100);
        });
    });
}

function initAccordionToolbars(root = document) {
    root.querySelectorAll("[data-acc-toggle]").forEach((btn) => {
        if (btn.dataset.accInit) return;
        btn.dataset.accInit = "1";
        btn.addEventListener("click", () => {
            const list = document.getElementById(btn.dataset.accToggle);
            if (!list) return;
            const openAll = btn.dataset.accAction === "open";
            list.querySelectorAll(":scope > details").forEach((d) => { d.open = openAll; });
        });
    });
}

function initTableCopyButtons(root = document) {
    root.querySelectorAll(".btn-copy-table").forEach((btn) => {
        if (btn.dataset.copyInit) return;
        btn.dataset.copyInit = "1";
        btn.addEventListener("click", async () => {
            const table = document.getElementById(btn.dataset.copyTable);
            if (!table) return;
            const tsv = Array.from(table.querySelectorAll("tr"))
                .map((tr) =>
                    Array.from(tr.querySelectorAll("th,td"))
                        .map((cell) => cell.textContent.trim().replace(/\s+/g, " "))
                        .join("\t")
                )
                .join("\n");
            try {
                await navigator.clipboard.writeText(tsv);
            } catch (err) {
                return;
            }
            btn.classList.add("copied");
            setTimeout(() => btn.classList.remove("copied"), 1100);
        });
    });
}

function initCopyAndAccordion(root = document) {
    initCopyButtons(root);
    initAccordionToolbars(root);
    initTableCopyButtons(root);
}

document.addEventListener("DOMContentLoaded", () => initCopyAndAccordion());
window.initCopyAndAccordion = initCopyAndAccordion;
