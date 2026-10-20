// ==============================================================================
// 💰 Doğruer Online - Otomatik Para Talep Form Doldurucu v3.9
// Firma: Doğruer Gümrük Müşavirliği A.Ş.
// ==============================================================================

(function() {
    function parseSafeAmount(val) {
        if (!val && val !== 0) return 0;
        let s = String(val).trim().replace(/\s/g, '').replace('TL', '').replace('TRY', '');
        if (s.includes('.') && s.includes(',')) {
            if (s.indexOf('.') < s.indexOf(',')) {
                s = s.replace(/\./g, '').replace(',', '.');
            } else {
                s = s.replace(/,/g, '');
            }
        } else if (s.includes(',')) {
            s = s.replace(',', '.');
        }
        let n = parseFloat(s);
        return isNaN(n) ? 0 : n;
    }

    function getFaturaShortNote(faturaNo) {
        if (!faturaNo) return "FATURA";
        let clean = String(faturaNo).trim();
        let numOnly = clean.replace(/[^0-9]/g, '');
        let shortDigits = numOnly.replace(/^0+/, '') || clean;
        if (shortDigits.length > 7) {
            shortDigits = shortDigits.slice(-5);
        }
        return `${shortDigits} FATURA`;
    }

    function detectLimanAccount(str) {
        const s = (str || '').toUpperCase();
        if (s.includes('DP WORLD') || s.includes('9380022882')) return '336-01-001-197';
        if (s.includes('EVYAP') || s.includes('1030050950')) return '336-01-001-252';
        if (s.includes('MERSIN') || s.includes('MIP') || s.includes('6180387068')) return '336-01-001-008';
        if (s.includes('SUBASI') || s.includes('SUBAŞI') || s.includes('7821346709')) return '336-01-001-081';
        return '336-01-001-252';
    }

    function setAmountValue(tutarVal) {
        let num = parseSafeAmount(tutarVal);
        if (!num || num <= 0) return;

        let amountEl = document.getElementById('Amount');
        if (!amountEl) return;

        let trFormatted = num.toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        let rawComma = num.toFixed(2).replace('.', ','); // Örn: "66731,32"

        // 1. autoNumeric kontrolü
        if (window.jQuery && $(amountEl).data('autoNumeric')) {
            try { $(amountEl).autoNumeric('set', num); } catch(e){}
        } else {
            amountEl.value = rawComma;
            if (window.jQuery) {
                $(amountEl).val(rawComma);
            }
        }

        // 2. Doğruer'in parantez içindeki (₺...) etiketini ve para birimi hesaplayıcısını tetikleyen tüm olaylar
        amountEl.focus();
        amountEl.dispatchEvent(new Event('focus', { bubbles: true }));
        amountEl.dispatchEvent(new Event('input', { bubbles: true }));
        amountEl.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true, key: 'Enter', keyCode: 13 }));
        amountEl.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true, key: 'Enter', keyCode: 13 }));
        amountEl.dispatchEvent(new Event('change', { bubbles: true }));
        amountEl.dispatchEvent(new Event('blur', { bubbles: true }));
        amountEl.dispatchEvent(new Event('focusout', { bubbles: true }));

        if (window.jQuery) {
            $(amountEl).trigger('focus')
                       .trigger('input')
                       .trigger('change')
                       .trigger('keyup')
                       .trigger('blur')
                       .trigger('focusout');
        }

        // 3. Parantez içindeki (₺0,00) etiketini doğrudan güncelle
        setTimeout(() => {
            try {
                const currencySpans = Array.from(document.querySelectorAll('label span, div span, p span, span'))
                    .filter(s => s.innerText && (s.innerText.includes('₺') || s.innerText.includes('TL')));
                
                currencySpans.forEach(s => {
                    if (s.innerText.includes('(') || s.innerText.includes('₺')) {
                        s.innerText = `(₺${trFormatted})`;
                    }
                });
            } catch(e){}
        }, 150);
    }

    function applyForm(item) {
        if (!item) return;
        console.log("💰 Para Talep Formu Dolduruluyor:", item);

        // 1. Önce Tip = T seçilir
        try {
            $('#Type').val('T').trigger('change');
            try { $('#Type').select2('val', 'T'); } catch(e){}
            $('#s2id_Type .select2-chosen').text('T');
            $('#s2id_Type').removeClass('select2-default');
        } catch(e){}

        // 2. Referans (Dosya No / Hankook Ref) doldur ve AJAX'ı tetikle
        let refVal = item.dosyaNo || item.ref || item.referans || '';
        const refEl = document.getElementById('Referance');
        if (refEl && refVal && refVal !== 'Listeden') {
            refEl.value = refVal;
            refEl.dispatchEvent(new Event('input', { bubbles: true }));
            refEl.dispatchEvent(new Event('change', { bubbles: true }));
            refEl.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true, key: ' ' }));
            refEl.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true, key: 'Backspace' }));
            refEl.dispatchEvent(new Event('blur', { bubbles: true }));
            refEl.dispatchEvent(new Event('focusout', { bubbles: true }));
            if (window.jQuery) {
                $(refEl).val(refVal).trigger('input').trigger('change').trigger('keyup').trigger('blur').trigger('focusout');
            }
        }

        // 3. Kademeli alan doldurma
        setTimeout(() => {
            try {
                // Cins = 1 (1-GARANTİ)
                $('#KindOf').val('1').trigger('change');
                try { $('#KindOf').select2('val', '1'); } catch(e){}
                $('#s2id_KindOf .select2-chosen').text('1-GARANTİ');
                $('#s2id_KindOf').removeClass('select2-default');

                // Para Birimi = TL
                $('#Currency').val('TL').trigger('change');
                try { $('#Currency').select2('val', 'TL'); } catch(e){}

                // MC = 257 (Yalnızca MIP ise 202)
                let limanStr = item.liman || '';
                let seciliLiman = item.hesapKodu || detectLimanAccount(limanStr);
                let isMip = seciliLiman === '336-01-001-008' || /MIP|MERSIN/i.test(limanStr);
                let targetMcVal = isMip ? '202' : '257';

                let mcOpt = Array.from(document.getElementById('MCCode')?.options || []).find(o => o.value === targetMcVal || o.text.startsWith(targetMcVal));
                let mcVal = mcOpt ? mcOpt.value : targetMcVal;
                let mcTxt = mcOpt ? mcOpt.text : (isMip ? '202-MiP Ardiye ödemesi' : '257-Ardiye Ücreti (TL)');

                $('#MCCode').val(mcVal).trigger('change');
                try { $('#MCCode').select2('val', mcVal); } catch(e){}
                $('#s2id_MCCode .select2-chosen').text(mcTxt);
                $('#s2id_MCCode').removeClass('select2-default');

                // Cins Açıklama (Hesap Seçimi)
                if (seciliLiman && seciliLiman !== 'DIGER') {
                    try {
                        $('#1account_selector_selector').select2('data', { id: seciliLiman, text: seciliLiman });
                    } catch(e){}
                    $('#1account_selector_selector').val(seciliLiman).trigger('change');
                    $('#PaymentNumber').val(seciliLiman).trigger('change');
                    $('[name="1Account_Selector_Field"]').val('PaymentNumber');
                    $('#s2id_1account_selector_selector .select2-chosen').text(seciliLiman);
                    $('#s2id_1account_selector_selector').removeClass('select2-default');
                }

                // Miktar (Doğruer parantez etiketi senkronu ile)
                if (item.tutar) {
                    setAmountValue(item.tutar);
                }

                // Açıklama: Örn: "20966 FATURA"
                let noteText = item.aciklama || '';
                if (!noteText && item.faturaNo) {
                    noteText = getFaturaShortNote(item.faturaNo);
                } else if (!noteText) {
                    noteText = "ARDİYE FATURASI";
                }
                $('#Note').val(noteText).trigger('input').trigger('change');

                // Re-confirm Cins after AJAX delay
                setTimeout(() => {
                    try {
                        $('#KindOf').val('1').trigger('change');
                        try { $('#KindOf').select2('val', '1'); } catch(e){}
                        $('#s2id_KindOf .select2-chosen').text('1-GARANTİ');
                    } catch(e){}
                    if (item.tutar) {
                        setAmountValue(item.tutar);
                    }
                }, 500);

                // Odaklanma
                setTimeout(() => {
                    const refEl = document.getElementById('Referance');
                    if (refEl) {
                        refEl.focus();
                    }
                }, 200);

                // Bildirim bannerı
                let banner = document.getElementById("pt_success_banner");
                if (!banner) {
                    banner = document.createElement("div");
                    banner.id = "pt_success_banner";
                    banner.style.cssText = "position:fixed; bottom:20px; right:20px; background:#16a34a; color:#fff; padding:12px 20px; border-radius:8px; z-index:999999; font-weight:bold; box-shadow:0 8px 25px rgba(0,0,0,0.3);";
                    document.body.appendChild(banner);
                }
                let realParsedAmount = parseSafeAmount(item.tutar);
                let displayAmount = realParsedAmount.toLocaleString('tr-TR', { minimumFractionDigits: 2 });
                banner.innerText = `✅ ${refVal || 'Fatura'} (${noteText} - ${displayAmount} TL) dolduruldu!`;
                banner.style.display = "block";
                setTimeout(() => { banner.style.display = "none"; }, 4000);
            } catch(err) {
                console.error("Form doldurma hatası:", err);
            }
        }, 300);
    }

    window.fillMoneyRequestForm = applyForm;
    window.detectLimanAccount = detectLimanAccount;
    window.getFaturaShortNote = getFaturaShortNote;
    window.setAmountValue = setAmountValue;
    window.parseSafeAmount = parseSafeAmount;

    console.log("🚀 Doğruer Para Talep Otomasyonu v3.9 Hazır!");
})();
