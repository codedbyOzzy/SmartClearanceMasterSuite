/* ==========================================================================
   chat_gif.js — Tenor GIF Entegrasyon Modülü  (SmartClearance Chat Hub)
   Tenor Public API v2 (LIVDSRZULELA demo key — production'da değiştirin)
   ========================================================================== */
"use strict";

const ChatGif = (() => {

    const TENOR_API_KEY = "LIVDSRZULELA";
    const TENOR_BASE    = "https://tenor.googleapis.com/v2";
    let debounceTimer   = null;
    let seciliGifUrl    = null;
    let kapatCallback   = null;

    async function gifAra(arama) {
        try {
            const endpoint = `/ekip-akisi/api/gif-ara?q=${encodeURIComponent(arama || "")}`;
            const r = await fetch(endpoint);
            if (!r.ok) throw new Error("GIF API hatası");
            const json = await r.json();
            return json.results || [];
        } catch (e) {
            console.warn("[ChatGif] GIF API hatası:", e.message);
            return [
                { title: "👍 Onay / Tamamdır", url: "/static/gifs/onay.svg", preview: "/static/gifs/onay.svg" },
                { title: "👏 Alkış / Bravo", url: "/static/gifs/alkis.svg", "preview": "/static/gifs/alkis.svg" },
                { title: "🚀 Hızlı / Acil", url: "/static/gifs/hizli.svg", "preview": "/static/gifs/hizli.svg" }
            ];
        }
    }

    // ── Grid'i doldur ────────────────────────────────────────────────────────
    async function gridDoldur(picker, aramaMetni) {
        const grid = picker.querySelector(".chat-gif-grid");
        grid.innerHTML = `<div class="chat-gif-durum" style="grid-column:1/-1;">Yükleniyor…</div>`;
        const sonuclar = await gifAra(aramaMetni);
        if (!sonuclar.length) {
            grid.innerHTML = `<div class="chat-gif-durum" style="grid-column:1/-1;">GIF bulunamadı 😕</div>`;
            return;
        }
        grid.innerHTML = sonuclar.map(g =>
            `<div class="chat-gif-item" data-url="${g.url}" data-preview="${g.preview}" title="${g.title}">
               <img src="${g.preview}" alt="${g.title}" loading="lazy">
             </div>`
        ).join("");
        grid.querySelectorAll(".chat-gif-item").forEach(item => {
            item.addEventListener("click", () => {
                const url     = item.dataset.url;
                const preview = item.dataset.preview;
                _secGif(url, preview, picker);
            });
        });
    }

    // ── GIF seç → input'a yaz + önizleme göster ──────────────────────────────
    function _secGif(url, preview, picker) {
        seciliGifUrl = url;
        picker.classList.remove("acik");
        const hiddenInput = document.getElementById("chat-gif-hidden-input");
        if (hiddenInput) hiddenInput.value = url;
        const onizleme = document.querySelector(".chat-gif-onizleme");
        if (onizleme) {
            onizleme.querySelector("img").src = preview;
            onizleme.querySelector("span").textContent = "GIF seçildi";
            onizleme.style.display = "inline-flex";
        }
        if (typeof kapatCallback === "function") kapatCallback(url, preview);
    }

    // ── Dışarı tıklanınca kapat ──────────────────────────────────────────────
    function _disariClick(e, picker) {
        if (!picker.contains(e.target) && !e.target.closest("#chat-gif-toggle") && !e.target.closest(".chat-ic-btn[data-picker='gif']")) {
            picker.classList.remove("acik");
        }
    }

    // ── Public API: başlat ───────────────────────────────────────────────────
    function baslat(pickerId, onSecim) {
        const picker = document.getElementById(pickerId);
        if (!picker) return;
        kapatCallback = onSecim || null;

        // Arama kutusu
        const aramaInput = picker.querySelector(".chat-gif-arama-input");
        if (aramaInput) {
            aramaInput.addEventListener("input", () => {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(() => gridDoldur(picker, aramaInput.value.trim()), 420);
            });
        }

        if (!picker._ilkYukleme) {
            picker._ilkYukleme = true;
            gridDoldur(picker, "");
        }

        // Dışarı tıklama
        document.addEventListener("click", e => _disariClick(e, picker));
    }

    // ── GIF önizleme kapat / temizle ─────────────────────────────────────────
    function temizle() {
        seciliGifUrl = null;
        const hiddenInput = document.getElementById("chat-gif-hidden-input");
        if (hiddenInput) hiddenInput.value = "";
        const onizleme = document.querySelector(".chat-gif-onizleme");
        if (onizleme) {
            onizleme.style.display = "none";
            onizleme.querySelector("img").src = "";
        }
    }

    return { baslat, temizle, seciliUrl: () => seciliGifUrl };
})();

window.ChatGif = ChatGif;

