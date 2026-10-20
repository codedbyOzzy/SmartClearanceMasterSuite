// mail_export.js — "Mail Hazirla" butonlari icin: ARTIK mailto: KULLANMAZ.
// Sebep: ofisteki bilgisayarda mailto: linki oradaki varsayili mail
// programini/hesabini acmaya calisiyor ama kullanici kendi is mailine o
// bilgisayarda erisemiyor. Bunun yerine konu+govdeyi ekranda kucuk bir
// pencerede (kopyalanabilir) gosterir; kullanici kendi actigi mailde
// (hangi program/hesap olursa olsun) konuyu ve govdeyi yapistirir.

function mailModalKapat() {
    const overlay = document.getElementById("mail-modal-overlay");
    if (overlay) overlay.remove();
    document.removeEventListener("keydown", _mailModalEscDinle);
}

function _mailModalEscDinle(e) {
    if (e.key === "Escape") mailModalKapat();
}

function mailModalAc(subject, body) {
    mailModalKapat(); // varsa acik olan eski pencereyi kapat

    const overlay = document.createElement("div");
    overlay.id = "mail-modal-overlay";
    overlay.className = "mail-modal-overlay";
    overlay.innerHTML =
        '<div class="mail-modal card">' +
            '<button type="button" class="mail-modal-kapat" title="Kapat">✕</button>' +
            '<h3>✉ Mail Taslağı</h3>' +
            '<p class="hint">Konuyu ve içeriği kopyala, kendi mail programında/hesabında yeni bir mail oluştur, yapıştır ve gönder. Bu pencere sadece kopyalama için — mail buradan gönderilmez.</p>' +
            '<div class="field-row">' +
                '<span class="field-label">Konu</span>' +
                '<span class="field-value mail-modal-konu"></span>' +
                '<button type="button" class="btn-copy" title="Kopyala">⧉</button>' +
            '</div>' +
            '<div class="field-row" style="align-items:flex-start;">' +
                '<span class="field-label">İçerik</span>' +
                '<span class="field-value mail-modal-govde"></span>' +
                '<button type="button" class="btn-copy" title="Kopyala">⧉</button>' +
            '</div>' +
        '</div>';

    overlay.querySelector(".mail-modal-konu").textContent = subject;
    overlay.querySelector(".mail-modal-govde").textContent = body;

    document.body.appendChild(overlay);

    overlay.querySelector(".mail-modal-kapat").addEventListener("click", mailModalKapat);
    overlay.addEventListener("click", (e) => { if (e.target === overlay) mailModalKapat(); });
    document.addEventListener("keydown", _mailModalEscDinle);

    if (window.initCopyAndAccordion) window.initCopyAndAccordion(overlay);
}

function initMailButtons(root = document) {
    root.querySelectorAll(".btn-mail").forEach((btn) => {
        if (btn.dataset.mailInit) return;
        btn.dataset.mailInit = "1";
        btn.addEventListener("click", () => {
            mailModalAc(btn.dataset.mailSubject || "", btn.dataset.mailBody || "");
        });
    });
}

document.addEventListener("DOMContentLoaded", () => initMailButtons());
window.initMailButtons = initMailButtons;
