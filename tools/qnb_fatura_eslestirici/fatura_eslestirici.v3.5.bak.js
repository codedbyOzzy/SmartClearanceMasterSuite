// ==============================================================================
// 📦 QNB eSolutions - e-Fatura & Konşimento Otomatik Eşleştirici v3.5
// Firma: Doğruer Gümrük Müşavirliği A.Ş. & Hankook Lastikleri A.Ş.
// Güncelleme: Güçlendirilmiş Eşleştirici, Aktif Liman Filtresi, Döviz (USD/EUR) Desteği,
//             Akıllı Sayfalama Senkronizasyonu & Çoklu Fatura (Multi-Invoice) Desteği
// ==============================================================================

(function() {
    // 1. PDF Yazdırma veya Fatura Görüntüleme ekranı kontrolü
    const href = window.location.href || "";
    const isInvoicePage = (
        href.includes("/efatura/display") ||
        href.includes("cmd=GELEN_FATURA_GOSTER") ||
        href.includes("invoiceUuid=") ||
        href.includes("type=html") ||
        document.title === "Hankook_Birlesik_Faturalar" ||
        href === "about:blank" ||
        window.name === "_blank" ||
        window.opener !== null
    );
    if (isInvoicePage) return;

    // Yazdırma (Ctrl+P, printToPdf) durumunda panelin kesinlikle gizlenmesi için global stil ekle
    try {
        if (!document.getElementById('gumruk-eslestirici-print-style')) {
            const pStyle = document.createElement('style');
            pStyle.id = 'gumruk-eslestirici-print-style';
            pStyle.textContent = `
                @media print {
                    #gumruk-eslestirici-panel,
                    #gumruk-sonuc-modal,
                    .gumruk-no-print,
                    [id^="gumruk-"] {
                        display: none !important;
                        visibility: hidden !important;
                        opacity: 0 !important;
                    }
                }
            `;
            (document.head || document.documentElement).appendChild(pStyle);
        }
    } catch (e) {}

    try {
        let manualClosed = false;
        let excelRecords = [];
        let allScannedResults = [];
        let shouldStop = false;
        let foundTargetCodes = new Set();
        let foundInvoiceUuids = new Set();
        let isMinimized = false;

        // Türkçe Karakter Normalizasyonu
        function normalizeTurkish(str) {
            if (!str) return '';
            return String(str)
                .replace(/İ/g, 'I')
                .replace(/ı/g, 'i')
                .replace(/ş/g, 's')
                .replace(/Ş/g, 'S')
                .replace(/ğ/g, 'g')
                .replace(/Ğ/g, 'G')
                .replace(/ü/g, 'u')
                .replace(/Ü/g, 'U')
                .replace(/ö/g, 'o')
                .replace(/Ö/g, 'O')
                .replace(/ç/g, 'c')
                .replace(/Ç/g, 'C');
        }

        // Temizleme ve Prefix Ayıklama
        function cleanCode(str) {
            if (!str) return '';
            let s = normalizeTurkish(str).toUpperCase().trim();
            s = s.replace(/^(ONEY|HLCU|MSCU|MEDU|MAEU|COSU|COEU|CMAU|MSMU|ARKAS|TURKON)/i, '');
            return s.replace(/[^A-Z0-9]/g, '');
        }

        // Evrim Verisinden Dosya No Sorgulama
        function lookupEvrimDosya(code) {
            if (!code || !window.__ALL_EVRIM_DATA || !Array.isArray(window.__ALL_EVRIM_DATA)) return '';
            const cClean = cleanCode(code);
            if (!cClean || cClean.length < 5) return '';

            const found = window.__ALL_EVRIM_DATA.find(e => {
                const bC = cleanCode(e.bl || e.bl_no || '');
                const rC = cleanCode(e.ref || e.hankook_ref || '');
                const byC = cleanCode(e.beyan || e.beyanname_no || '');
                return (bC && (bC === cClean || bC.includes(cClean) || cClean.includes(bC))) ||
                       (rC && (rC === cClean || rC.includes(cClean) || cClean.includes(rC))) ||
                       (byC && byC === cClean);
            });
            return found ? (found.dosya_no || found.dosya || '') : '';
        }

        function initGumrukEslestirici() {
            if (manualClosed) return; // Kullanıcı manuel kapattıysa zorla açma
            
            const curHref = window.location.href || "";
            if (curHref.includes("/efatura/display") || curHref.includes("GELEN_FATURA_GOSTER") || curHref.includes("invoiceUuid=")) return;
            if (document.querySelector('.invoice-container') || document.getElementById('faturaTablosu')) return;

            const oldPanel = document.getElementById('gumruk-eslestirici-panel');
            if (oldPanel) return; // Zaten açık
            const oldModal = document.getElementById('gumruk-sonuc-modal');
            if (oldModal) oldModal.remove();

            const panel = document.createElement('div');
            panel.id = 'gumruk-eslestirici-panel';
            panel.className = 'gumruk-no-print';
            panel.style.cssText = `
                position: fixed; top: 15px; right: 15px; z-index: 9999999;
                background: #ffffff; border: 2px solid #6b21a8; border-radius: 12px;
                padding: 16px; box-shadow: 0 12px 40px rgba(0,0,0,0.35);
                font-family: Arial, sans-serif; width: 440px; max-height: 92vh; overflow-y: auto;
                transition: all 0.3s ease;
            `;

            panel.innerHTML = `
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                    <h4 style="margin:0; color:#6b21a8; font-size:16px; font-weight:bold;">📦 Hankook Fatura Eşleştirici v3.5</h4>
                    <div>
                        <span id="min-eslestirici" style="cursor:pointer; font-weight:bold; font-size:16px; color:#888; margin-right:12px; display:inline-block; transform:translateY(-2px);">_</span>
                        <span id="close-eslestirici" style="cursor:pointer; font-weight:bold; font-size:18px; color:#888;">✕</span>
                    </div>
                </div>
                
                <div id="eslestirici-icerik">
                    <div style="background:#f5f3ff; border:1px solid #ddd6fe; border-radius:8px; padding:10px; margin-bottom:10px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                        <div style="font-size:12px; font-weight:bold; color:#6b21a8;">
                            📋 Aranacak Konşimento / Ref Listesi (Ctrl + V):
                        </div>
                    </div>
                    <textarea id="konsimento-listesi" placeholder="HLCUSEL2605AUXF3&#10;HLCUSEL260566379&#10;26410300IM00103169&#10;SELG51548500..." style="width:95%; height:70px; font-size:12px; padding:6px; border:1px solid #c4b5fd; border-radius:4px; font-family:monospace;"></textarea>
                    
                    <div style="margin-top:6px; font-size:11px; color:#4c1d95; background:#ede9fe; padding:6px 8px; border-radius:6px; display:flex; flex-direction:column; gap:4px;">
                        <div style="display:flex; gap:10px; align-items:center;">
                            <span style="font-weight:bold;">⚓ Liman / Hat Filtresi:</span>
                            <label style="cursor:pointer;"><input type="radio" name="liman-filter" value="ALL" checked> <b>Tümü (Liman + Armatör)</b></label>
                            <label style="cursor:pointer;"><input type="radio" name="liman-filter" value="PORT_ONLY"> Sadece Limanlar</label>
                        </div>
                        <label style="cursor:pointer; display:flex; align-items:center; gap:4px; margin-top:2px; font-size:11px; color:#312e81;">
                            <input type="checkbox" id="chk-scan-all-pages" checked>
                            <span>📑 <b>Çoklu Fatura Modu</b> (Aynı BL'ye ait birden fazla faturayı kaçırmamak için tüm sayfaları tara)</span>
                        </label>
                    </div>
                    <div id="veri-ozet" style="font-size:11px; color:#6b21a8; font-weight:bold; margin-top:4px;"></div>
                </div>

                <div id="progress-container" style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:10px; margin-bottom:10px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; font-size:13px; font-weight:bold; margin-bottom:6px;">
                        <span>🎯 Bulunan Faturalar:</span>
                        <span id="progress-count" style="color:#16a34a; font-size:16px; background:#dcfce7; padding:2px 8px; border-radius:6px; border:1px solid #86efac;">0 / 0</span>
                    </div>
                    <div style="background:#e2e8f0; border-radius:10px; height:12px; overflow:hidden; position:relative;">
                        <div id="progress-bar-fill" style="background:linear-gradient(90deg, #6b21a8, #16a34a); width:0%; height:100%; transition:width 0.3s ease; border-radius:10px;"></div>
                    </div>
                    <div style="display:flex; justify-content:space-between; font-size:11px; color:#64748b; margin-top:4px;">
                        <span id="progress-status">Beklemede...</span>
                        <span id="progress-percent" style="font-weight:bold; color:#6b21a8;">%0</span>
                    </div>
                </div>

                <div style="margin-top:10px; display:flex; flex-direction:column; gap:6px;">
                    <div style="display:flex; gap:6px;">
                        <button id="btn-tara-hepsi" style="flex:2; background:#4f46e5; color:#fff; border:none; padding:10px; border-radius:6px; font-weight:bold; cursor:pointer; font-size:13px;">
                            🔄 Faturaları Ara & Bul
                        </button>
                        <button id="btn-durdur" style="flex:1; background:#dc2626; color:#fff; border:none; padding:10px; border-radius:6px; font-weight:bold; cursor:pointer; font-size:12px; display:none;">
                            ⏹️ Durdur
                        </button>
                    </div>
                    <div style="display:flex; gap:6px;">
                        <button id="btn-sonuc-goster" style="flex:1.2; background:#16a34a; color:#fff; border:none; padding:9px; border-radius:6px; font-weight:bold; cursor:pointer; font-size:12px;">
                            👁️ Bulunanları Listele
                        </button>
                        <button id="btn-indir-excel" style="flex:1; background:#107c41; color:#fff; border:none; padding:9px; border-radius:6px; font-weight:bold; cursor:pointer; font-size:12px;">
                            📊 Excel İndir
                        </button>
                    </div>
                </div>
                <div id="eslestirici-durum" style="margin-top:10px; font-size:12px; font-weight:bold;"></div>
                </div> <!-- End of eslestirici-icerik -->
            `;

            document.body.appendChild(panel);
            
            document.getElementById('min-eslestirici').onclick = () => {
                isMinimized = !isMinimized;
                const content = document.getElementById('eslestirici-icerik');
                const minBtn = document.getElementById('min-eslestirici');
                if (isMinimized) {
                    content.style.display = 'none';
                    minBtn.innerText = '□';
                    minBtn.style.transform = 'translateY(0px)';
                    panel.style.width = '280px';
                } else {
                    content.style.display = 'block';
                    minBtn.innerText = '_';
                    minBtn.style.transform = 'translateY(-2px)';
                    panel.style.width = '440px';
                }
            };

            document.getElementById('close-eslestirici').onclick = () => {
                panel.remove();
                manualClosed = true;
                setTimeout(() => { manualClosed = false; }, 30000);
            };

            function updateProgress(statusText) {
                const total = excelRecords.length;
                const current = foundTargetCodes.size;
                const percent = total > 0 ? Math.min(100, Math.round((current / total) * 100)) : 0;

                const countEl = document.getElementById('progress-count');
                const fillEl = document.getElementById('progress-bar-fill');
                const percentEl = document.getElementById('progress-percent');
                const statusEl = document.getElementById('progress-status');

                if (countEl) countEl.innerText = `${current} / ${total}`;
                if (fillEl) fillEl.style.width = `${percent}%`;
                if (percentEl) percentEl.innerText = `%${percent}`;
                if (statusEl && statusText) statusEl.innerText = statusText;
            }

            function parsePastedData() {
                const raw = document.getElementById('konsimento-listesi')?.value || '';
                const lines = raw.split('\n').map(l => l.trim()).filter(l => l.length > 0);
                excelRecords = [];

                lines.forEach(line => {
                    const cols = line.split('\t').map(c => c.trim()).filter(c => c.length > 0);
                    if (cols.length === 0) return;

                    let detectedDosya = '';
                    let detectedRef = '';
                    let detectedBl = '';
                    let detectedBeyan = '';
                    let detectedContainer = '';
                    let detectedFatura = '';

                    // Her bir sütunun içeriğini akıllı regex ile sınıflandır
                    cols.forEach(val => {
                        const vUpper = val.toUpperCase();
                        // 1. Beyanname No: 26xxxx...
                        if (/^26[0-9]{2}[0-9A-Z]{8,16}(?:IM[0-9]{4,10})?$/i.test(val) || /^26410300IM\d{6,10}$/i.test(val)) {
                            detectedBeyan = vUpper;
                        }
                        // 2. Konteyner No: 4 harf + 7 rakam
                        else if (/^[A-Z]{4}[0-9]{7}$/i.test(val)) {
                            detectedContainer = vUpper;
                        }
                        // 3. Fatura No: 16 hane
                        else if (/^[A-Z0-9]{3}202[0-9]{10}$/i.test(val)) {
                            detectedFatura = vUpper;
                        }
                        // 4. Dosya No: 26-01234 veya 2026-12345
                        else if (/^(?:26|2026)-\d{4,7}$/i.test(val)) {
                            detectedDosya = val;
                        }
                        // 5. Armatör Konşimento No
                        else if (/^(?:HLCU|MSCU|MEDU|MAEU|COSU|COEU|CMAU|ONEY|SELG|MSMU|ARKAS|TURKON)[A-Z0-9]+$/i.test(val)) {
                            detectedBl = vUpper;
                        }
                        // 6. Hankook Ref: TRYAR-...
                        else if (/^TRYAR-[A-Z0-9\-]+$/i.test(val)) {
                            detectedRef = val;
                        }
                    });

                    // Evrim sütun sıralaması fallback'leri
                    if (!detectedBl && cols.length >= 6) {
                        detectedDosya = detectedDosya || cols[0];
                        detectedRef = detectedRef || cols[2];
                        detectedBl = cols[5];
                    } else if (!detectedBl && cols.length === 3) {
                        detectedDosya = detectedDosya || cols[0];
                        detectedRef = detectedRef || cols[1];
                        detectedBl = cols[2];
                    } else if (!detectedBl && cols.length === 2) {
                        detectedDosya = detectedDosya || cols[0];
                        detectedBl = cols[1];
                    } else if (!detectedBl && !detectedContainer && !detectedBeyan && !detectedFatura && !detectedRef) {
                        // Serbest metin satırı
                        cols.forEach(c => {
                            if (c.length >= 4) {
                                excelRecords.push({
                                    dosyaNo: lookupEvrimDosya(c) || '',
                                    refNo: c,
                                    blNo: c,
                                    cleanBl: cleanCode(c),
                                    cleanRef: cleanCode(c),
                                    beyanNo: '',
                                    containerNo: '',
                                    faturaNo: ''
                                });
                            }
                        });
                        return;
                    }

                    const primaryKey = detectedBl || detectedContainer || detectedBeyan || detectedFatura || detectedRef;
                    if (primaryKey) {
                        excelRecords.push({
                            dosyaNo: detectedDosya || lookupEvrimDosya(primaryKey),
                            refNo: detectedRef || primaryKey,
                            blNo: detectedBl || primaryKey,
                            cleanBl: cleanCode(detectedBl || primaryKey),
                            cleanRef: cleanCode(detectedRef || primaryKey),
                            beyanNo: detectedBeyan,
                            containerNo: detectedContainer,
                            faturaNo: detectedFatura
                        });
                    }
                });

                const vo = document.getElementById('veri-ozet');
                if (vo) vo.innerText = `🎯 Toplam ${excelRecords.length} hedef kayıt yüklendi.`;
                updateProgress("Aramaya hazır");
            }

            document.getElementById('konsimento-listesi').oninput = parsePastedData;

            function isPortAllowed(gonderen, fullText) {
                const filterEl = document.querySelector('input[name="liman-filter"]:checked');
                const filterVal = filterEl ? filterEl.value : 'ALL';
                if (filterVal === 'ALL') return true;

                // PORT_ONLY seçiliyse: Limanlar (Evyap, DP World, Safiport, Kumport, Marport, Limak vb.)
                const combined = ((gonderen || '') + ' ' + (fullText || '')).toUpperCase();
                const isPort = combined.includes('EVYAP') || combined.includes('1030050950') ||
                               combined.includes('DP WORLD') || combined.includes('DPWORLD') || 
                               combined.includes('YARIMCA') || combined.includes('KORFEZ') ||
                               combined.includes('KÖRFEZ') || combined.includes('9380022882') ||
                               combined.includes('SAFİPORT') || combined.includes('SAFIPORT') ||
                               combined.includes('KUMPORT') || combined.includes('MARPORT') ||
                               combined.includes('ASYAPORT') || combined.includes('YILPORT') ||
                               combined.includes('LİMAK') || combined.includes('LIMAK') ||
                               combined.includes('MERSİN') || combined.includes('MIP');
                return isPort;
            }

            function getPageInvoices() {
                const rows = Array.from(document.querySelectorAll('.brow, [rowid], tr')).filter(r => r.querySelector("input.csc-mini-button[rel='mbAc']") || r.getAttribute('rowid'));
                const invoiceItems = [];

                rows.forEach(row => {
                    const text = row.innerText || '';
                    const html = row.innerHTML || '';
                    const match = html.match(/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{10,12}/) || text.match(/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{10,12}/) || row.getAttribute('rowid');
                    const uuid = typeof match === 'string' ? match : (match ? match[0] : null);

                    const cells = Array.from(row.querySelectorAll('.cell, td, .in-cell')).map(c => c.innerText.trim()).filter(c => c.length > 0);
                    const faturaNoMatch = text.match(/\b([A-Z0-9]{3}202\d{10}|[A-Z0-9]{16})\b/);
                    const tarihMatch = text.match(/\b\d{2}\/\d{2}\/\d{4}\b/);
                    const tutarMatch = text.match(/([\d\.]+,[\d]{2})\s*(TRY|TL|USD|EUR|\$|€)?/i);

                    if (uuid) {
                        invoiceItems.push({
                            rowElement: row,
                            ettn: uuid,
                            faturaNo: faturaNoMatch ? faturaNoMatch[0] : (cells[3] || ''),
                            tarih: tarihMatch ? tarihMatch[0] : (cells[4] || ''),
                            gonderen: cells[6] || cells[5] || '',
                            tutar: tutarMatch ? tutarMatch[1] : (cells[9] || cells[8] || '')
                        });
                    }
                });
                return invoiceItems;
            }

            function extractDetailsFromHtml(html, fallbackItem) {
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = html;
                const text = tempDiv.innerText;

                let tutar = fallbackItem.tutar || '';
                let doviz = 'TL';

                // 1. Döviz / Para Birimi Tespiti
                if (/\b(USD|\$)\b/i.test(text) || /Amerikan\s*Dolar/i.test(text)) {
                    doviz = 'USD';
                } else if (/\b(EUR|€)\b/i.test(text) || /Euro/i.test(text)) {
                    doviz = 'EUR';
                } else if (/\b(TRY|TL)\b/i.test(text) || /Türk\s*Lirası/i.test(text)) {
                    doviz = 'TL';
                }

                const tutarPatterns = [
                    /Ödenecek\s*Tutar\s*[:\s]*([\d\.]+,\d{2})\s*(TRY|TL|USD|EUR|\$|€)?/i,
                    /Vergiler\s*Dahil\s*Toplam\s*[:\s]*([\d\.]+,\d{2})\s*(TRY|TL|USD|EUR|\$|€)?/i,
                    /MAL\s*HİZMET\s*TOPLAM\s*TUTARI\s*[:\s]*([\d\.]+,\d{2})\s*(TRY|TL|USD|EUR|\$|€)?/i,
                    /TOPLAM\s*TUTAR\s*[:\s]*([\d\.]+,\d{2})\s*(TRY|TL|USD|EUR|\$|€)?/i,
                    // QR JSON içinden odenecek değeri
                    /"odenecek":"([\d\.]+)"/i
                ];

                for (let p of tutarPatterns) {
                    const m = text.match(p) || html.match(p);
                    if (m) {
                        // QR JSON'dan gelen değer noktalı virgül yerine nokta kullanıyor, düzelt
                        tutar = m[1].includes(',') ? m[1] : m[1].replace('.', ',');
                        if (m[2]) {
                            const cur = m[2].toUpperCase();
                            if (cur === 'USD' || cur === '$') doviz = 'USD';
                            else if (cur === 'EUR' || cur === '€') doviz = 'EUR';
                            else if (cur === 'TRY' || cur === 'TL') doviz = 'TL';
                        }
                        break;
                    }
                }

                // 2. Gönderen tespiti — önce VKN bazlı (kesin), sonra metin bazlı
                let gonderen = fallbackItem.gonderen || '';
                // VKN bazlı kesin tespit
                if (/4570543930/.test(html) || /4570543930/.test(text)) gonderen = 'EVYAP DENİZ İŞLETMECİLİĞİ A.Ş.';
                else if (/9380022882/.test(html) || /9380022882/.test(text)) gonderen = 'DP WORLD YARIMCA LİMAN İŞL.';
                else if (/DP World Properties/.test(html) || /DP World Properties/.test(text)) gonderen = 'DP WORLD YARIMCA LİMAN İŞL.';
                // Metin bazlı
                else if (/EVYAP/i.test(text)) gonderen = 'EVYAP DENİZ İŞLETMECİLİĞİ A.Ş.';
                else if (/DP\s*WORLD|YARIMCA/i.test(text)) gonderen = 'DP WORLD YARIMCA LİMAN İŞL.';
                else if (/MERSİN|MIP/i.test(text)) gonderen = 'MERSİN ULUSLARARASI LİMAN İŞL. (MIP)';
                else if (/SUBAŞI/i.test(text)) gonderen = 'SUBAŞI GÜMRÜK MÜŞAVİRLİĞİ';
                else if (/LİMAK/i.test(text)) gonderen = 'LİMAK İSKENDERUN LİMAN İŞL.';
                else if (/MARPORT/i.test(text)) gonderen = 'MARPORT LİMAN İŞLETMELERİ';
                else if (/KUMPORT/i.test(text)) gonderen = 'KUMPORT LİMAN HİZMETLERİ';
                else if (/ASYAPORT/i.test(text)) gonderen = 'ASYAPORT LİMAN A.Ş.';
                else if (/YILPORT/i.test(text)) gonderen = 'YILPORT HOLDİNG A.Ş.';
                else if (/SAFİPORT/i.test(text)) gonderen = 'SAFİPORT DERİNCE';
                else if (/KORFEZ|KÖRFEZ/i.test(text)) gonderen = 'DP WORLD KORFEZ LİMAN İŞL.';

                // 3. Beyanname No — gelişmiş pattern (26xxxxIMxxxxxxxx formatı dahil)
                let beyanNo = '';
                const beyanPatterns = [
                    /\b(26410300IM[0-9]{6,12})\b/i,
                    /\b(264103[0-9A-Z]{10,16})\b/i,
                    /\b(26[0-9]{2}[0-9A-Z]{8,16}IM[0-9]{4,10})\b/i,
                    /\b(26[0-9]{2}[A-Z0-9]{10,18})\b/i
                ];
                for (let bp of beyanPatterns) {
                    const bm = text.match(bp);
                    if (bm) { beyanNo = bm[1]; break; }
                }

                // 4. Konteyner No listesi (HTML fatura notlarından)
                const containerPattern = /\b([A-Z]{4}[0-9]{7})\b/g;
                const containers = [];
                let cm;
                while ((cm = containerPattern.exec(text)) !== null) {
                    if (!containers.includes(cm[1])) containers.push(cm[1]);
                }

                let dosyaMatch = text.match(/\b(26-\d{5,7})\b/i);
                let dosyaNo = dosyaMatch ? dosyaMatch[0] : '';

                return { tutar, doviz, gonderen, beyanNo, dosyaNo, containers };
            }

            async function scanCurrentPage(pageNumDisplay) {
                const invoiceItems = getPageInvoices();
                let basarili = 0;
                let eslesen = 0;

                const batchSize = 5;
                for (let i = 0; i < invoiceItems.length; i += batchSize) {
                    if (shouldStop) break;

                    const batch = invoiceItems.slice(i, i + batchSize);
                    updateProgress(`Sayfa ${pageNumDisplay} taranıyor (${Math.min(i + batchSize, invoiceItems.length)} / ${invoiceItems.length})`);

                    await Promise.all(batch.map(async (item) => {
                        if (foundInvoiceUuids.has(item.ettn)) return;

                        let html = '';
                        let fetchOk = false;

                        // Strateji 1: alternativeTransformer=false (standart)
                        for (let retry = 0; retry < 2 && !fetchOk; retry++) {
                            try {
                                const res = await fetch(`/efatura/display?cmd=GELEN_FATURA_GOSTER&invoiceUuid=${item.ettn}&type=html&alternativeTransformer=false`);
                                if (res.ok) {
                                    const text = await res.text();
                                    // İçerik doğrulaması: Gerçek fatura HTML'i en az 500 karakter olmalı
                                    if (text && text.length > 500 && (text.includes('DOCTYPE') || text.includes('Fatura') || text.includes('fatura') || text.includes('VKN') || text.includes('TL') || text.includes('body'))) {
                                        html = text;
                                        fetchOk = true;
                                    }
                                }
                            } catch (e) {
                                await new Promise(r => setTimeout(r, 600));
                            }
                        }

                        // Strateji 2: alternativeTransformer=true (bazı özel faturalar için)
                        if (!fetchOk) {
                            for (let retry = 0; retry < 2 && !fetchOk; retry++) {
                                try {
                                    const res = await fetch(`/efatura/display?cmd=GELEN_FATURA_GOSTER&invoiceUuid=${item.ettn}&type=html&alternativeTransformer=true`);
                                    if (res.ok) {
                                        const text = await res.text();
                                        if (text && text.length > 500 && (text.includes('DOCTYPE') || text.includes('Fatura') || text.includes('VKN') || text.includes('TL') || text.includes('body'))) {
                                            html = text;
                                            fetchOk = true;
                                        }
                                    }
                                } catch (e) {
                                    await new Promise(r => setTimeout(r, 800));
                                }
                            }
                        }

                        // Strateji 3: Sadece type=html (transformer parametresiz)
                        if (!fetchOk) {
                            try {
                                const res = await fetch(`/efatura/display?cmd=GELEN_FATURA_GOSTER&invoiceUuid=${item.ettn}&type=html`);
                                if (res.ok) {
                                    const text = await res.text();
                                    if (text && text.length > 200) {
                                        html = text;
                                        fetchOk = true;
                                    }
                                }
                            } catch (e) {}
                        }

                        if (!fetchOk || !html) return;
                        foundInvoiceUuids.add(item.ettn);

                        try {
                            const tempDiv = document.createElement('div');
                            tempDiv.innerHTML = html;
                            // Chromium WebEngine ortamında detached DOM düğümlerinde textContent çok daha kararlıdır:
                            const textContent = tempDiv.textContent || tempDiv.innerText || '';
                            const normFullText = normalizeTurkish(textContent).toUpperCase();
                            const cleanFullText = normFullText.replace(/[^A-Z0-9]/g, '');

                            // Ham HTML'i de normalize et (QR JSON, özel not etiketleri ve nitelikler için)
                            const normHtml = normalizeTurkish(html).toUpperCase();
                            const cleanHtml = normHtml.replace(/[^A-Z0-9]/g, '');

                            const details = extractDetailsFromHtml(html, item);

                            // Liman Filtresi Kontrolü
                            const portAllowed = isPortAllowed(details.gonderen, textContent);

                            let matchedRecords = [];

                            if (portAllowed) {
                                for (let rec of excelRecords) {
                                    const bRaw = normalizeTurkish(rec.blNo || '').toUpperCase();
                                    const bClean = rec.cleanBl || '';
                                    const rRaw = normalizeTurkish(rec.refNo || '').toUpperCase();
                                    const rClean = rec.cleanRef || '';
                                    const byRaw = normalizeTurkish(rec.beyanNo || '').toUpperCase();
                                    const cRaw = normalizeTurkish(rec.containerNo || '').toUpperCase();
                                    const fRaw = normalizeTurkish(rec.faturaNo || '').toUpperCase();

                                    let isMatch = false;

                                    // 1. Doğrudan Fatura No Eşleştirmesi (Fatura no arandıysa)
                                    if (fRaw && fRaw.length >= 10) {
                                        if ((item.faturaNo && item.faturaNo.toUpperCase().includes(fRaw)) || normHtml.includes(fRaw)) {
                                            isMatch = true;
                                        }
                                    }

                                    // 2. Doğrudan ETTN / UUID Eşleştirmesi
                                    if (!isMatch && item.ettn && (bRaw === item.ettn.toUpperCase() || rRaw === item.ettn.toUpperCase())) {
                                        isMatch = true;
                                    }

                                    // 3. Konteyner No Eşleştirmesi (örn. ONEU6662130, MSDU8875122, OOCU8938284)
                                    if (!isMatch && (cRaw || /^[A-Z]{4}[0-9]{7}$/.test(bRaw))) {
                                        const targetCnt = cRaw || bRaw;
                                        if (normFullText.includes(targetCnt) || normHtml.includes(targetCnt) || (details.containers && details.containers.includes(targetCnt))) {
                                            isMatch = true;
                                        }
                                    }

                                    // 4. Beyanname No Eşleştirmesi (örn. 26410300IM00114312)
                                    if (!isMatch && (byRaw || (bRaw && bRaw.startsWith('264') && bRaw.length >= 14))) {
                                        const targetBeyan = byRaw || bRaw;
                                        if (normFullText.includes(targetBeyan) || normHtml.includes(targetBeyan) || cleanFullText.includes(targetBeyan)) {
                                            isMatch = true;
                                        }
                                    }

                                    // 5. Konşimento (BL) No Eşleştirmesi
                                    if (!isMatch && bRaw && bRaw.length >= 5) {
                                        // A) Tam kod metin veya HTML içinde
                                        if (normFullText.includes(bRaw) || normHtml.includes(bRaw)) {
                                            isMatch = true;
                                        }
                                        // B) Prefix temizlenmiş kod (en az 8 karakter ise güvenle ara)
                                        else if (bClean && bClean.length >= 8 && (cleanFullText.includes(bClean) || cleanHtml.includes(bClean))) {
                                            isMatch = true;
                                        }
                                        // C) 5-7 karakter kısa kodlar için kelime sınırı kontrolü
                                        else if (bRaw.length >= 5 && bRaw.length < 8) {
                                            const escaped = bRaw.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
                                            const reg = new RegExp('(^|[^A-Z0-9])' + escaped + '([^A-Z0-9]|$)', 'i');
                                            if (reg.test(normFullText) || reg.test(normHtml)) {
                                                isMatch = true;
                                            }
                                        }
                                    }

                                    // 6. Hankook Referans No Eşleştirmesi
                                    if (!isMatch && rRaw && rRaw.length >= 5 && rRaw !== bRaw) {
                                        if (normFullText.includes(rRaw) || normHtml.includes(rRaw)) {
                                            isMatch = true;
                                        } else if (rClean && rClean.length >= 8 && (cleanFullText.includes(rClean) || cleanHtml.includes(rClean))) {
                                            isMatch = true;
                                        }
                                    }

                                    if (isMatch) {
                                        matchedRecords.push(rec);
                                        foundTargetCodes.add(rec.cleanBl || rec.cleanRef || rec.blNo || rec.containerNo || rec.beyanNo);
                                    }
                                }
                            }

                            const isOurs = matchedRecords.length > 0;
                            if (isOurs) {
                                eslesen++;
                                updateProgress(`🎯 Yeni Fatura Bulundu!`);
                            }

                            if (item.rowElement) {
                                item.rowElement.setAttribute('data-bizim-mi', isOurs ? 'true' : 'false');
                                if (isOurs) {
                                    item.rowElement.style.background = '#dcfce7';
                                    item.rowElement.style.borderLeft = '6px solid #16a34a';
                                }
                            }

                            if (isOurs && !allScannedResults.some(r => r.ettn === item.ettn)) {
                                // Eşleşen tüm BL'leri virgülle birleştir (Konsolide fatura desteği)
                                const matchedBls = Array.from(new Set(matchedRecords.map(r => r.blNo).filter(Boolean))).join(', ');
                                const matchedRefs = Array.from(new Set(matchedRecords.map(r => r.refNo).filter(Boolean))).join(', ');
                                
                                // Dosya no: Kayıttan veya faturadan veya Evrim lookup'tan
                                let dNo = matchedRecords.find(r => r.dosyaNo && r.dosyaNo !== 'Listeden')?.dosyaNo || details.dosyaNo || '';
                                if (!dNo && matchedBls) {
                                    dNo = lookupEvrimDosya(matchedBls.split(',')[0].trim());
                                }

                                // faturaNo: HTML'den de almaya çalış (daha güvenilir)
                                let finalFaturaNo = item.faturaNo || '';
                                if (!finalFaturaNo || finalFaturaNo.length < 10) {
                                    const fnPatterns = [
                                        /"no":"([^"]+)"/,
                                        /\b([A-Z0-9]{2,3}202[0-9]{10,13})\b/,
                                        /\b([0-9][A-Z]{2}202[0-9]{10,13})\b/
                                    ];
                                    for (let fp of fnPatterns) {
                                        const fm = html.match(fp);
                                        if (fm) { finalFaturaNo = fm[1]; break; }
                                    }
                                }

                                allScannedResults.push({
                                    ettn: item.ettn,
                                    faturaNo: finalFaturaNo || item.faturaNo,
                                    tarih: item.tarih,
                                    gonderen: details.gonderen,
                                    tutar: details.tutar,
                                    doviz: details.doviz,
                                    isOurs: 'EVET',
                                    dosyaNo: dNo,
                                    blNo: matchedBls,
                                    refNo: matchedRefs,
                                    beyanNo: details.beyanNo || '',
                                    konteynerNo: (details.containers || []).join(', '),
                                    rawHtml: html
                                });
                            }

                            basarili++;
                        } catch (err) {
                            console.error("Fatura işleme hatası:", item.ettn, err);
                        }
                    }));
                }

                return { basarili, eslesen };
            }

            async function waitForNewPage(oldFirstEttn, targetPageNum) {
                const maxWaitMs = 16000;
                const startTime = Date.now();

                // Sayfa geçişinin başlaması ve DOM'un değişmeye başlaması için başlangıç gecikmesi
                await new Promise(r => setTimeout(r, 600));

                while (Date.now() - startTime < maxWaitMs) {
                    if (shouldStop) return false;

                    const currentInvoices = getPageInvoices();
                    const pageInput = document.querySelector('input.csc-dt-paging-text');
                    const pageSpan = document.querySelector('.csc-dt-paging-text');
                    const pageText = (pageInput ? pageInput.value : (pageSpan ? pageSpan.innerText : '')).trim();

                    // Sağlam kontrol: Yeni faturalar geldi mi?
                    const hasNewInvoices = currentInvoices.length > 0 && currentInvoices[0].ettn !== oldFirstEttn;
                    const pageMatches = pageText === String(targetPageNum);

                    // Eğer ilk faturanın UUID'si değiştiyse veya sayfa no eşleştiğinde liste yenilendiyse
                    if (hasNewInvoices && (pageMatches || !pageText)) {
                        await new Promise(r => setTimeout(r, 600)); // DOM stabilizasyon payı
                        return true;
                    }

                    // Tek sayfalık tablolarda veya son sayfada timeout koruması
                    if (pageMatches && Date.now() - startTime > 3500) {
                        await new Promise(r => setTimeout(r, 500));
                        return true;
                    }

                    await new Promise(r => setTimeout(r, 400));
                }
                return false;
            }

            function getTotalPages() {
                const pagingContainer = document.querySelector('.csc-dt-paging-text')?.parentElement;
                if (pagingContainer) {
                    const text = pagingContainer.innerText || '';
                    const match = text.match(/\/\s*(\d+)/);
                    if (match && match[1]) return parseInt(match[1]);
                }
                return 25; // Güvenli varsayılan sayfa sınırı
            }

            document.getElementById('btn-durdur').onclick = function() {
                shouldStop = true;
                this.style.display = 'none';
                updateProgress('Kullanıcı tarafından durduruldu');
            };

            document.getElementById('btn-tara-hepsi').onclick = async function() {
                parsePastedData();
                if (excelRecords.length === 0) { alert("Lütfen aranacak konşimentoları yapıştırın."); return; }
                
                shouldStop = false;
                foundTargetCodes.clear();
                foundInvoiceUuids.clear();
                allScannedResults = [];

                const btnDurdur = document.getElementById('btn-durdur');
                btnDurdur.style.display = 'block';

                let curPageInput = document.querySelector('input.csc-dt-paging-text')?.value || document.querySelector('.csc-dt-paging-text')?.innerText.trim();
                const firstBtn = document.querySelector('.csc-dt-paging-btn.csc-dt-seek-first:not(.csc-dt-paging-btn-disabled)');
                
                if (curPageInput && curPageInput !== '1' && firstBtn) {
                    updateProgress("Sayfa 1'e dönülüyor...");
                    const curInvoices = getPageInvoices();
                    const oldFirstEttn = curInvoices.length > 0 ? curInvoices[0].ettn : '';
                    firstBtn.click();
                    await waitForNewPage(oldFirstEttn, 1);
                }

                updateProgress("Tarama başladı...");

                let pageNum = 1;
                const maxPages = getTotalPages();

                while (pageNum <= maxPages && !shouldStop) {
                    const curInvoices = getPageInvoices();
                    const oldFirstEttn = curInvoices.length > 0 ? curInvoices[0].ettn : '';
                    
                    await scanCurrentPage(pageNum);

                    // Çoklu fatura modu seçili değilse ve hedeflerin hepsi bulunduysa dur
                    const scanAllPages = document.getElementById('chk-scan-all-pages')?.checked ?? true;
                    if (!scanAllPages && foundTargetCodes.size >= excelRecords.length && excelRecords.length > 0) {
                        updateProgress(`🎉 TÜM ${excelRecords.length} HEDEF FATURA BULUNDU! (%100)`);
                        break;
                    }

                    updateProgress(`Sayfa ${pageNum}/${maxPages} tamamlandı (${foundTargetCodes.size}/${excelRecords.length} Hedef, ${allScannedResults.length} Fatura)`);

                    const nextBtn = document.querySelector('.csc-dt-paging-btn.csc-dt-seek-next:not(.csc-dt-paging-btn-disabled)');

                    if (nextBtn && pageNum < maxPages && !shouldStop) {
                        pageNum++;
                        nextBtn.click();
                        const pageLoaded = await waitForNewPage(oldFirstEttn, pageNum);
                        if (!pageLoaded) {
                            console.warn("Sayfa geçişi beklenirken timeout oluştu, mevcut içerikle devam ediliyor...");
                        }
                    } else {
                        break;
                    }
                }

                btnDurdur.style.display = 'none';
                updateProgress(`Tamamlandı: ${foundTargetCodes.size} / ${excelRecords.length} Bulundu`);
                
                openResultsModal();
            };

            async function downloadMergedPdf() {
                const ourInvoices = allScannedResults.filter(r => r.isOurs === 'EVET');
                if (ourInvoices.length === 0) {
                    alert("Bize ait bulunan fatura yok.");
                    return;
                }

                const btn = document.getElementById('modal-pdf-indir');
                if (btn) {
                    btn.disabled = true;
                    btn.innerText = '⏳ Faturalar Hazırlanıyor...';
                }

                // Tüm faturaların tam rawHtml içeriğinin bulunduğunu garanti et
                for (let inv of ourInvoices) {
                    if (!inv.rawHtml || inv.rawHtml.length < 100) {
                        try {
                            const res = await fetch(`/efatura/display?cmd=GELEN_FATURA_GOSTER&invoiceUuid=${inv.ettn}&type=html&alternativeTransformer=false`);
                            inv.rawHtml = await res.text();
                        } catch (err) {
                            console.error("Fatura HTML alma hatası:", inv.ettn, err);
                        }
                    }
                }

                // 1. PyQt Embed ortamındaysa (MasterSuite) -> Yüksek kaliteli PyMuPDF birleştiricisini çalıştır
                if (window.__IS_PYQT_EMBED) {
                    const payload = ourInvoices.map(inv => ({
                        faturaNo: inv.faturaNo,
                        dosyaNo: inv.dosyaNo,
                        blNo: inv.blNo,
                        ettn: inv.ettn,
                        html: inv.rawHtml
                    }));

                    window.onPdfExportFinished = function(success) {
                        if (btn) {
                            btn.disabled = false;
                            btn.innerText = '📑 Tümünü Tek PDF Yap & İndir';
                        }
                    };

                    document.body.setAttribute('data-pdf-queue', JSON.stringify(payload));
                    document.title = 'PDF_MERGE_EXPORT:' + payload.length + ':' + Date.now();
                    return;
                }

                // 2. Bağımsız Tarayıcı (Chrome/Edge Bookmarklet) Fallback:
                const printWindow = window.open('', '_blank', 'width=950,height=900');
                
                let headContent = '';
                const firstHtml = ourInvoices[0].rawHtml || '';
                const headMatch = firstHtml.match(/<head[^>]*>([\s\S]*?)<\/head>/i);
                if (headMatch) {
                    headContent = headMatch[1];
                }

                let combinedHtml = `
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>Hankook_Birlesik_Faturalar</title>
                        <meta charset="UTF-8">
                        ${headContent}
                        <style>
                            @page { size: A4 portrait; margin: 0; }
                            body { margin: 0; padding: 0; background: #fff; }
                            .fatura-page {
                                page-break-after: always;
                                break-after: page;
                                width: 800px;
                                margin: 0 auto;
                                box-sizing: border-box;
                                padding: 20px 0;
                            }
                            @media print {
                                body { margin: 0; padding: 0; }
                                .fatura-page {
                                    page-break-after: always;
                                    break-after: page;
                                    margin: 0 auto;
                                    padding: 0;
                                }
                            }
                        </style>
                    </head>
                    <body>
                `;

                ourInvoices.forEach((inv, index) => {
                    let cleanBody = inv.rawHtml;
                    const bodyMatch = inv.rawHtml.match(/<body[^>]*>([\s\S]*?)<\/body>/i);
                    if (bodyMatch) cleanBody = bodyMatch[1];

                    cleanBody = cleanBody.replace(/id=["']qrcode["']/g, `id="qrcode_${index}"`);
                    cleanBody = cleanBody.replace(/id=["']qrvalue["']/g, `id="qrvalue_${index}"`);
                    cleanBody = cleanBody.replace(/document\.getElementById\(["']qrcode["']\)/g, `document.getElementById("qrcode_${index}")`);
                    cleanBody = cleanBody.replace(/document\.getElementById\(["']qrvalue["']\)/g, `document.getElementById("qrvalue_${index}")`);

                    combinedHtml += `<div class="fatura-page">${cleanBody}</div>`;
                });

                combinedHtml += `</body></html>`;
                printWindow.document.open();
                printWindow.document.write(combinedHtml);
                printWindow.document.close();

                if (btn) {
                    btn.disabled = false;
                    btn.innerText = '📑 Tümünü Tek PDF Yap & İndir';
                }

                setTimeout(() => {
                    printWindow.focus();
                    printWindow.print();
                }, 1200);
            }

            function openResultsModal() {
                const oldModal = document.getElementById('gumruk-sonuc-modal');
                if (oldModal) oldModal.remove();

                const ourInvoices = allScannedResults.filter(r => r.isOurs === 'EVET');

                const modal = document.createElement('div');
                modal.id = 'gumruk-sonuc-modal';
                modal.className = 'gumruk-no-print';
                modal.style.cssText = `
                    position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
                    z-index: 10000000; background: #ffffff; border-radius: 12px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.5); width: 940px; max-width: 95vw;
                    max-height: 85vh; display: flex; flex-direction: column; font-family: Arial, sans-serif;
                `;

                let rowsHtml = '';
                if (ourInvoices.length === 0) {
                    rowsHtml = `<tr><td colspan="8" style="text-align:center; padding:30px; color:#888;">Aradığınız konşimento numaralarıyla eşleşen fatura bulunamadı.</td></tr>`;
                } else {
                    ourInvoices.forEach((inv, i) => {
                        const curDisplay = inv.doviz ? ` ${inv.doviz}` : ' TL';
                        rowsHtml += `
                            <tr style="border-bottom:1px solid #eee; background:${i % 2 === 0 ? '#ffffff' : '#f9fafb'};">
                                <td style="padding:10px 8px; font-weight:bold; color:#16a34a;">${i + 1}</td>
                                <td style="padding:10px 8px; font-weight:bold;">${inv.faturaNo}</td>
                                <td style="padding:10px 8px; color:#333;">${inv.gonderen || '—'}</td>
                                <td style="padding:10px 8px; font-weight:bold; color:#16a34a;">${inv.tutar || '—'}${curDisplay}</td>
                                <td style="padding:10px 8px; font-weight:bold; color:#2563eb;">${inv.dosyaNo || '—'}</td>
                                <td style="padding:10px 8px; font-weight:bold; color:#7c3aed;">${inv.blNo || '—'}</td>
                                <td style="padding:10px 8px; color:#0d9488; font-family:monospace; font-weight:bold;">${inv.konteynerNo || '—'}</td>
                                <td style="padding:10px 8px; color:#b45309; font-family:monospace;">${inv.beyanNo || '—'}</td>
                                <td style="padding:10px 8px; color:#555;">${inv.refNo || '—'}</td>
                                <td style="padding:10px 8px; text-align:center;">
                                    <button onclick="window.open('/efatura/display?cmd=GELEN_FATURA_GOSTER&invoiceUuid=${inv.ettn}&type=html&alternativeTransformer=false', '_blank', 'width=900,height=800')" style="background:#6b21a8; color:#fff; border:none; padding:5px 10px; border-radius:4px; cursor:pointer; font-size:11px; font-weight:bold;">
                                        🔍 Aç
                                    </button>
                                </td>
                            </tr>
                        `;
                    });
                }

                modal.innerHTML = `
                    <div style="background:#16a34a; color:#fff; padding:14px 20px; border-radius:12px 12px 0 0; display:flex; justify-content:space-between; align-items:center;">
                        <h3 style="margin:0; font-size:16px;">✅ Hankook - Bulunan Faturalar (${ourInvoices.length} / ${excelRecords.length} Hedef)</h3>
                        <span id="close-modal-btn" style="cursor:pointer; font-size:20px; font-weight:bold;">✕</span>
                    </div>
                    <div style="padding:15px; overflow-y:auto; flex:1;">
                        <table style="width:100%; border-collapse:collapse; font-size:12px; text-align:left;">
                            <thead>
                                <tr style="background:#f3f4f6; border-bottom:2px solid #ddd; color:#4b5563;">
                                    <th style="padding:8px;">#</th>
                                    <th style="padding:8px;">Fatura No</th>
                                    <th style="padding:8px;">Gönderen Firma</th>
                                    <th style="padding:8px;">Tutar</th>
                                    <th style="padding:8px;">Dosya No</th>
                                    <th style="padding:8px;">Konşimento (BL)</th>
                                    <th style="padding:8px;">Konteyner No</th>
                                    <th style="padding:8px;">Beyanname No</th>
                                    <th style="padding:8px;">Referans No</th>
                                    <th style="padding:8px; text-align:center;">İşlem</th>
                                </tr>
                            </thead>
                            <tbody>${rowsHtml}</tbody>
                        </table>
                    </div>
                    <div style="padding:12px 20px; background:#f9fafb; border-top:1px solid #eee; border-radius:0 0 12px 12px; display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-size:12px; color:#666;">Toplam tespit edilen faturalar.</span>
                        <div style="display:flex; gap:8px;">
                            <button id="modal-para-talep-aktar" style="background:#15803d; color:#fff; border:none; padding:8px 14px; border-radius:6px; font-weight:bold; cursor:pointer; font-size:12px;">
                                💰 Para Talep Kuyruğuna Aktar (${ourInvoices.length} Fatura)
                            </button>
                            <button id="modal-pdf-indir" style="background:#dc2626; color:#fff; border:none; padding:8px 14px; border-radius:6px; font-weight:bold; cursor:pointer; font-size:12px;">
                                📑 Tümünü Tek PDF Yap & İndir
                            </button>
                            <button id="modal-excel-indir" style="background:#107c41; color:#fff; border:none; padding:8px 14px; border-radius:6px; font-weight:bold; cursor:pointer; font-size:12px;">
                                📊 Excel İndir
                            </button>
                        </div>
                    </div>
                `;

                document.body.appendChild(modal);
                document.getElementById('close-modal-btn').onclick = () => modal.remove();
                document.getElementById('modal-excel-indir').onclick = () => document.getElementById('btn-indir-excel').click();
                document.getElementById('modal-pdf-indir').onclick = downloadMergedPdf;
                
                let btnPt = document.getElementById('modal-para-talep-aktar');
                if (btnPt) {
                    btnPt.onclick = function() {
                        let ptQueue = ourInvoices.map(inv => {
                            let fNo = inv.faturaNo || '';
                            let match = fNo.match(/0*(\d{1,8})$/);
                            let shortDigits = match && match[1] ? match[1] : (fNo.replace(/[^0-9]/g, '').slice(-5) || fNo);
                            let curNote = inv.doviz && inv.doviz !== 'TL' ? ` ${inv.doviz}` : '';
                            let note = `${shortDigits} FATURA${curNote}`;
                            
                            let targetDosya = inv.dosyaNo && inv.dosyaNo !== 'Listeden' ? inv.dosyaNo : '';
                            if (!targetDosya) {
                                targetDosya = lookupEvrimDosya(inv.blNo || inv.refNo || inv.beyanNo || inv.konteynerNo);
                            }
                            if (!targetDosya) targetDosya = inv.refNo || inv.blNo || '';
                            let cleanTutar = (inv.tutar || '').replace(/\./g, '').replace(',', '.');
                            
                            return {
                                faturaNo: inv.faturaNo,
                                tutar: cleanTutar,
                                doviz: inv.doviz || 'TL',
                                dosyaNo: targetDosya,
                                ref: inv.refNo || targetDosya,
                                bl: inv.blNo || '',
                                blNo: inv.blNo || '',
                                beyanNo: inv.beyanNo || '',
                                liman: inv.gonderen || '',
                                aciklama: note
                            };
                        });
                        
                        let jsonStr = JSON.stringify(ptQueue);
                        document.body.setAttribute('data-pt-queue', jsonStr);
                        document.title = 'PT_QUEUE_EXPORT:' + ptQueue.length;
                        alert(`✅ ${ptQueue.length} adet fatura Para Talep kuyruğuna aktarıldı!\n\nŞimdi Finansal Talepler sekmesinde üst barda 'Faturayı Doldur' butonuna basabilirsiniz.`);
                    };
                }
            }

            document.getElementById('btn-sonuc-goster').onclick = openResultsModal;

            document.getElementById('btn-indir-excel').onclick = function() {
                const ourInvoices = allScannedResults.filter(r => r.isOurs === 'EVET');
                if (ourInvoices.length === 0) {
                    alert("Bize ait bulunan fatura yok.");
                    return;
                }

                let csv = "\uFEFFETTN;Fatura No;Fatura Tarihi;Gonderen Firma;Tutar;Para Birimi;Dosya No;Eslesen BL;Konteyner No;Beyanname No;Referans No\n";
                ourInvoices.forEach(r => {
                    let cleanTutar = (r.tutar || '').replace(/\./g, '');
                    csv += `"${r.ettn}";"${r.faturaNo}";"${r.tarih}";"${r.gonderen}";"${cleanTutar}";"${r.doviz || 'TL'}";"${r.dosyaNo}";"${r.blNo}";"${r.konteynerNo || ''}";"${r.beyanNo || ''}";"${r.refNo}"\n`;
                });

                const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
                const link = document.createElement('a');
                link.href = URL.createObjectURL(blob);
                link.download = `Hankook_Bulunan_Faturalar_${new Date().toISOString().slice(0,10)}.csv`;
                link.click();
            };

            console.log("🚀 QNB Fatura & Konşimento Eşleştirici v3.5 Hazır!");

            if (window.__ACTIVE_BEYAN_NO) {
                const txt = document.getElementById('konsimento-listesi');
                if (txt) {
                    txt.value = window.__ACTIVE_BEYAN_NO;
                    parsePastedData();
                }
            }
        }

        window.initGumrukEslestirici = initGumrukEslestirici;
        window.setKonsimentoList = function(code) {
            window.__ACTIVE_BEYAN_NO = code;
            initGumrukEslestirici();
            const txt = document.getElementById('konsimento-listesi');
            if (txt) {
                txt.value = code;
                parsePastedData();
                txt.style.borderColor = '#16a34a';
                txt.style.boxShadow = '0 0 10px #16a34a';
                setTimeout(() => {
                    txt.style.borderColor = '#c4b5fd';
                    txt.style.boxShadow = 'none';
                }, 2500);
            }
        };

        // Otomatik Panel Enjeksiyon Kontrolü (SPA Navigasyonu)
        function enforcePanelVisible() {
            initGumrukEslestirici();
        }

        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', enforcePanelVisible);
        } else {
            enforcePanelVisible();
        }
        
        setInterval(enforcePanelVisible, 3000);
    } catch (e) {
        alert("Eşleştirici Başlatma Hatası: " + e.toString());
    }
})();
