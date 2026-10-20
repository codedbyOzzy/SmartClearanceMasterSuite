// pdf_compare.js — Canli split-screen beyanname/fatura karsilastirmasi.
// PDF.js ile sayfalari tarayicida render eder (yakinlastir/uzaklastir,
// sayfa gezinme), karsilastirma verisine gore renkli kutular cizer ve
// "kalem karti" tiklaninca ilgili alana atlayip yanip soner.

import * as pdfjsLib from "/static/vendor/pdfjs/pdf.min.mjs";

pdfjsLib.GlobalWorkerOptions.workerSrc = "/static/vendor/pdfjs/pdf.worker.min.mjs";

const BASE_RENDER_SCALE = 1.5; // PDF puanindan piksele temel cevrim katsayisi
const ZOOM_STEP = 0.15;
const ZOOM_MIN = 0.4;
const ZOOM_MAX = 3.0;

class PdfPane {
    constructor(name, url, pageSizes) {
        this.name = name;
        this.url = url;
        this.pageSizes = pageSizes || [];
        this.scrollEl = document.getElementById(`scroll-${name}`);
        this.zoomLabel = document.getElementById(`zoom-label-${name}`);
        this.pageLabel = document.getElementById(`page-label-${name}`);
        this.scale = 1.0;
        this.currentPage = 0;
        this.doc = null;
        this.pageWrap = null;
        this.canvas = null;
        this.allBoxes = [];
    }

    setBoxes(boxes) {
        this.allBoxes = boxes;
    }

    async load() {
        if (!this.url) {
            this.scrollEl.innerHTML = '<p class="hint" style="padding:20px;">Bu belge bulunamadı.</p>';
            return;
        }
        try {
            this.doc = await pdfjsLib.getDocument({
                url: this.url,
                cMapUrl: "/static/vendor/pdfjs/cmaps/",
                cMapPacked: true,
                standardFontDataUrl: "/static/vendor/pdfjs/standard_fonts/",
            }).promise;
            await this._fitToWidth();
            await this.renderPage(0);
        } catch (e) {
            this.scrollEl.innerHTML = '<p class="msg-warn" style="padding:20px;">PDF yüklenemedi.</p>';
        }
    }

    // Ekran/pencere genisligi ne olursa olsun ilk acilista okunakli bir
    // baslangic zoom'u versin diye, panelin gercek genisligine gore
    // "sigdir" olcegi hesaplar (sabit scale=1.0 varsaymak yerine).
    async _fitToWidth() {
        const firstPage = await this.doc.getPage(1);
        const naturalWidth = firstPage.getViewport({ scale: BASE_RENDER_SCALE }).width;
        const available = this.scrollEl.clientWidth - 32; // .pdf-scroll padding (16px x2)
        if (available > 0 && naturalWidth > 0) {
            this.scale = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, available / naturalWidth));
        }
    }

    async renderPage(pageIndex) {
        if (!this.doc) return;
        this.currentPage = Math.max(0, Math.min(pageIndex, this.doc.numPages - 1));
        const page = await this.doc.getPage(this.currentPage + 1);
        const viewport = page.getViewport({ scale: this.scale * BASE_RENDER_SCALE });

        if (!this.pageWrap) {
            this.pageWrap = document.createElement("div");
            this.pageWrap.className = "pdf-page-wrap";
            this.canvas = document.createElement("canvas");
            this.pageWrap.appendChild(this.canvas);
            this.scrollEl.innerHTML = "";
            this.scrollEl.appendChild(this.pageWrap);
        }
        this.canvas.width = viewport.width;
        this.canvas.height = viewport.height;
        this.pageWrap.style.width = viewport.width + "px";
        this.pageWrap.style.height = viewport.height + "px";

        const ctx = this.canvas.getContext("2d");
        await page.render({ canvasContext: ctx, viewport }).promise;

        this._updateLabels();
        this._drawBoxes();
    }

    _updateLabels() {
        this.zoomLabel.textContent = Math.round(this.scale * 100) + "%";
        this.pageLabel.textContent = `${this.currentPage + 1}/${this.doc ? this.doc.numPages : 1}`;
    }

    _drawBoxes() {
        if (!this.pageWrap) return;
        this.pageWrap.querySelectorAll(".hl-box").forEach((el) => el.remove());
        const factor = this.scale * BASE_RENDER_SCALE;
        const pad = 3;
        this.allBoxes
            .filter((b) => b.page_index === this.currentPage)
            .forEach((b) => {
                const div = document.createElement("div");
                div.className = `hl-box hl-${b.status}`;
                div.dataset.kalem = b.kalem_no;
                div.style.left = (b.x0 * factor - pad) + "px";
                div.style.top = (b.top * factor - pad) + "px";
                div.style.width = (b.x1 - b.x0) * factor + pad * 2 + "px";
                div.style.height = (b.bottom - b.top) * factor + pad * 2 + "px";
                this.pageWrap.appendChild(div);
            });
    }

    async zoom(delta) {
        this.scale = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, this.scale + delta));
        await this.renderPage(this.currentPage);
    }

    async goToKalem(pageIndex, kalemNo) {
        if (pageIndex == null) return;
        if (pageIndex !== this.currentPage) {
            await this.renderPage(pageIndex);
        } else {
            this._drawBoxes();
        }
        requestAnimationFrame(() => this._highlightKalem(kalemNo));
    }

    _highlightKalem(kalemNo) {
        if (!this.pageWrap) return;
        const boxes = this.pageWrap.querySelectorAll(`.hl-box[data-kalem="${kalemNo}"]`);
        if (!boxes.length) return;
        boxes[0].scrollIntoView({ behavior: "smooth", block: "center", inline: "center" });
        boxes.forEach((el) => {
            el.classList.remove("pulse");
            void el.offsetWidth; // animasyonu yeniden baslatmak icin reflow
            el.classList.add("pulse");
        });
    }
}

function collectBoxes(data, side) {
    const boxes = [];
    data.kalemler.forEach((k) => {
        const info = k[side];
        if (!info) return;
        Object.values(info.fields).forEach((bbox) => {
            boxes.push({
                page_index: bbox.page_index !== undefined ? bbox.page_index : info.page_index,
                x0: bbox.x0, top: bbox.top, x1: bbox.x1, bottom: bbox.bottom,
                status: bbox.status,
                kalem_no: k.kalem_no,
            });
        });
    });
    return boxes;
}

function renderIssueStrip(data, onSelect) {
    const strip = document.getElementById("issue-strip");
    strip.innerHTML = "";
    data.kalemler.forEach((k) => {
        const chip = document.createElement("div");
        chip.className = `issue-chip st-${k.durum_genel}`;
        chip.innerHTML = `<span class="k-no">Kalem ${k.kalem_no}</span><span class="k-durum">${k.durum_genel}</span>`;
        chip.addEventListener("click", () => {
            strip.querySelectorAll(".issue-chip").forEach((c) => c.classList.remove("active"));
            chip.classList.add("active");
            onSelect(k);
        });
        strip.appendChild(chip);
        k._chipEl = chip;
    });
}

async function main() {
    const dataEl = document.getElementById("karsilastirma-data");
    const data = JSON.parse(dataEl.textContent);
    if (data.hata) {
        document.getElementById("issue-strip").innerHTML = `<p class="msg-warn">${data.hata}</p>`;
        return;
    }

    const beyannamePane = new PdfPane("beyanname", data.beyanname_pdf_url, data.beyanname_page_sizes);
    const faturaPane = new PdfPane("fatura", data.fatura_pdf_url, data.fatura_page_sizes);
    beyannamePane.setBoxes(collectBoxes(data, "beyanname"));
    faturaPane.setBoxes(collectBoxes(data, "fatura"));

    async function focusKalem(k) {
        if (k.beyanname) await beyannamePane.goToKalem(k.beyanname.page_index, k.kalem_no);
        if (k.fatura) await faturaPane.goToKalem(k.fatura.page_index, k.kalem_no);
    }

    renderIssueStrip(data, focusKalem);

    document.querySelectorAll(".pdf-controls button").forEach((btn) => {
        btn.addEventListener("click", async () => {
            const pane = btn.dataset.pane === "beyanname" ? beyannamePane : faturaPane;
            const act = btn.dataset.act;
            if (act === "zoom-in") await pane.zoom(ZOOM_STEP);
            else if (act === "zoom-out") await pane.zoom(-ZOOM_STEP);
            else if (act === "next") await pane.renderPage(pane.currentPage + 1);
            else if (act === "prev") await pane.renderPage(pane.currentPage - 1);
        });
    });

    await Promise.all([beyannamePane.load(), faturaPane.load()]);

    const params = new URLSearchParams(window.location.search);
    const initialKalem = params.get("kalem");
    if (initialKalem) {
        const k = data.kalemler.find((x) => String(x.kalem_no) === initialKalem);
        if (k) {
            k._chipEl?.classList.add("active");
            focusKalem(k);
        }
    }
}

main();
