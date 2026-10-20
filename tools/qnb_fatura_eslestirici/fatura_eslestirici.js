// ==============================================================================
// 📦 QNB eSolutions - e-Fatura & Konşimento Otomatik Eşleştirici v3.6
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
        let foundRecordIds = new Set(); // hedef KAYIT id'leri (aynı BL'li farklı kayıtlar birleşmez)
        let isScanning = false;
        let scanState = { page: 0, pages: 0, onPage: 0, done: 0, scanned: 0, filtered: 0, failed: [], warning: '', finished: false };
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
        const sleep = (ms) => new Promise(r => setTimeout(r, ms));
        const tick = () => new Promise(r => setTimeout(r, 0)); // UI'nin yeniden çizilebilmesi için nefes payı
        const HANKOOK_VKN = '4570543930'; // Alıcı (biz) — ASLA gönderen sayılmamalı

        // Bilinen satıcı VKN → görünen ad / liman mı?
        const SELLER_VKN_MAP = {
            '1030050950': { name: 'EVYAP DENİZ İŞLETMECİLİĞİ A.Ş. (DP WORLD KÖRFEZ)', port: true },
            '9380022882': { name: 'DP WORLD YARIMCA LİMAN İŞL.', port: true },
            '7580022041': { name: 'YILPORT KONTEYNER TERMİNALİ VE LİMAN İŞL. A.Ş.', port: true },
            '9240896606': { name: 'VAVİEN LOJİSTİK A.Ş.', port: false }
        };

        function escHtml(s) {
            return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        }

        // Fatura HTML'ini, hücre/satır sınırları ayrılmış düz metne çevirir (kaynak yüklemeden, script/style hariç)
        function htmlToText(html) {
            try {
                const spaced = String(html)
                    .replace(/<br\s*\/?>/gi, '\n')
                    .replace(/<\/(td|th|tr|div|p|li|h[1-6]|table)>/gi, '$&\n');
                const doc = new DOMParser().parseFromString(spaced, 'text/html');
                doc.querySelectorAll('script,style').forEach(n => n.remove());
                return (doc.body ? doc.body.textContent : doc.documentElement.textContent) || '';
            } catch (e) {
                const d = document.createElement('div');
                d.innerHTML = html;
                return d.textContent || '';
            }
        }

        // Konteyner No'ları: "TGCU5456667" ve "UETU 642793_8" (boşluklu/alt çizgili kontrol hanesi) yazımları
        function extractContainers(text) {
            const up = normalizeTurkish(text).toUpperCase();
            const set = new Set();
            const re = /\b([A-Z]{4})[ ]?(\d{6})[ _\-]?(\d)\b/g;
            let m;
            while ((m = re.exec(up)) !== null) set.add(m[1] + m[2] + m[3]);
            return Array.from(set);
        }

        // Beyanname No'ları (26410500IM00115605 biçimi; konsolide faturada birden fazla olabilir)
        function extractBeyanNos(text) {
            const up = normalizeTurkish(text).toUpperCase();
            const set = new Set();
            let m;
            const re = /\b(\d{8}(?:IM|EX)\d{6,10})\b/g;
            while ((m = re.exec(up)) !== null) set.add(m[1]);
            if (set.size === 0) {
                const fallbacks = [/\b(264103[0-9A-Z]{10,16})\b/, /\b(26[0-9]{2}[A-Z0-9]{10,18})\b/];
                for (const fp of fallbacks) { const fm = up.match(fp); if (fm) { set.add(fm[1]); break; } }
            }
            return Array.from(set);
        }

        // Faturanın kendi üzerinde yazan konşimento: "#B/L:BUP0208349#", "Konşimento :BUP0208246", "MBL no : 9021119590", Evyap "SELG..."
        function extractInvoiceBls(normText) {
            const set = new Set();
            let m;
            const pats = [/B\/L\s*:\s*([A-Z0-9]{5,})/g, /KONSIMENTO\s*:\s*([A-Z0-9]{5,})/g, /MBL\s*NO\s*:\s*([A-Z0-9]{5,})/g, /\b(SELG[A-Z0-9]{6,})\b/g];
            pats.forEach(re => { while ((m = re.exec(normText)) !== null) set.add(m[1]); });
            return Array.from(set);
        }

        // Satıcıyı tespit et: önce etiketli VKN (Hankook'un kendi VKN'si hariç), sonra metin
        function detectSeller(text, fallbackName) {
            const normText = normalizeTurkish(text).toUpperCase();
            const vkns = [];
            const re = /VKN[^0-9]{0,40}?(\d{10})\b/gi;
            let m;
            while ((m = re.exec(text)) !== null) {
                if (m[1] !== HANKOOK_VKN && !vkns.includes(m[1])) vkns.push(m[1]);
            }
            for (const v of vkns) {
                if (SELLER_VKN_MAP[v]) return { name: SELLER_VKN_MAP[v].name, isPort: SELLER_VKN_MAP[v].port, vkn: v };
            }
            for (const v of Object.keys(SELLER_VKN_MAP)) {
                if (text.includes(v)) return { name: SELLER_VKN_MAP[v].name, isPort: SELLER_VKN_MAP[v].port, vkn: v };
            }
            const kw = [
                [/EVYAP/, 'EVYAP DENİZ İŞLETMECİLİĞİ A.Ş.'],
                [/DP\s*WORLD|YARIMCA/, 'DP WORLD YARIMCA LİMAN İŞL.'],
                [/MERSIN|\bMIP\b/, 'MERSİN ULUSLARARASI LİMAN İŞL. (MIP)'],
                [/LIMAK/, 'LİMAK İSKENDERUN LİMAN İŞL.'],
                [/MARPORT/, 'MARPORT LİMAN İŞLETMELERİ'],
                [/KUMPORT/, 'KUMPORT LİMAN HİZMETLERİ'],
                [/ASYAPORT/, 'ASYAPORT LİMAN A.Ş.'],
                [/YILPORT/, 'YILPORT HOLDİNG A.Ş.'],
                [/SAFIPORT/, 'SAFİPORT DERİNCE'],
                [/KORFEZ/, 'DP WORLD KÖRFEZ LİMAN İŞL.']
            ];
            for (const [r, name] of kw) {
                if (r.test(normText)) return { name, isPort: true, vkn: vkns[0] || '' };
            }
            if (/SUBASI/.test(normText)) return { name: 'SUBAŞI GÜMRÜK MÜŞAVİRLİĞİ', isPort: false, vkn: vkns[0] || '' };
            return { name: fallbackName || (vkns[0] ? 'VKN ' + vkns[0] : ''), isPort: null, vkn: vkns[0] || '' };
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
                    <h4 style="margin:0; color:#6b21a8; font-size:16px; font-weight:bold;">📦 Hankook Fatura Eşleştirici v3.6</h4>
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
                        <span>🎯 Bulunan Hedefler:</span>
                        <span id="progress-count" style="color:#16a34a; font-size:16px; background:#dcfce7; padding:2px 8px; border-radius:6px; border:1px solid #86efac;">0 / 0</span>
                    </div>
                    <div style="background:#e2e8f0; border-radius:10px; height:12px; overflow:hidden; position:relative;">
                        <div id="progress-bar-fill" style="background:linear-gradient(90deg, #6b21a8, #16a34a); width:0%; height:100%; transition:width 0.3s ease; border-radius:10px;"></div>
                    </div>
                    <div style="display:flex; justify-content:space-between; font-size:11px; color:#64748b; margin-top:4px;">
                        <span id="progress-status">Beklemede...</span>
                        <span id="progress-percent" style="font-weight:bold; color:#6b21a8;">%0</span>
                    </div>
                    <div style="display:flex; justify-content:space-between; font-size:11px; color:#475569; margin-top:6px;">
                        <span id="progress-invoices">📄 0 fatura bulundu</span>
                        <span id="progress-scan">🔎 Tarama: —</span>
                    </div>
                    <div style="background:#e2e8f0; border-radius:10px; height:5px; overflow:hidden; margin-top:3px;">
                        <div id="scan-bar-fill" style="background:#0ea5e9; width:0%; height:100%; transition:width 0.3s ease; border-radius:10px;"></div>
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
                const current = foundRecordIds.size;
                const percent = total > 0 ? Math.min(100, Math.round((current / total) * 100)) : 0;

                // Tarama ilerlemesi (hedef sayısından bağımsız): sayfa + sayfa içi fatura
                let scanPct = 0;
                if (scanState.finished) scanPct = 100;
                else if (scanState.pages > 0) {
                    const inPage = scanState.onPage ? scanState.done / scanState.onPage : 0;
                    scanPct = Math.min(100, Math.round(((Math.max(scanState.page - 1, 0) + inPage) / scanState.pages) * 100));
                }

                const countEl = document.getElementById('progress-count');
                const fillEl = document.getElementById('progress-bar-fill');
                const percentEl = document.getElementById('progress-percent');
                const statusEl = document.getElementById('progress-status');
                const invEl = document.getElementById('progress-invoices');
                const scanEl = document.getElementById('progress-scan');
                const scanFill = document.getElementById('scan-bar-fill');

                if (countEl) countEl.innerText = `${current} / ${total}`;
                if (fillEl) fillEl.style.width = `${percent}%`;
                if (percentEl) percentEl.innerText = `%${percent}`;
                if (statusEl && statusText) statusEl.innerText = statusText;
                if (invEl) invEl.innerText = `📄 ${allScannedResults.length} fatura bulundu`;
                if (scanEl) scanEl.innerText = scanState.pages > 0 ? `🔎 Sayfa ${scanState.page}/${scanState.pages} • ${scanState.scanned} fatura okundu` : '🔎 Tarama: —';
                if (scanFill) scanFill.style.width = `${scanPct}%`;
            }

            function parsePastedData() {
                const raw = document.getElementById('konsimento-listesi')?.value || '';
                const lines = raw.split(/\r?\n/).map(l => l.trim()).filter(l => l.length > 0);
                excelRecords = [];
                const seen = new Set();
                // Aynı hedef birden fazla yapıştırılırsa tekrar sayma; her kayda benzersiz id ver
                const addRecord = (r) => {
                    const key = [r.cleanBl, r.cleanRef, r.beyanNo, r.containerNo, r.faturaNo].join('|');
                    if (seen.has(key)) return;
                    seen.add(key);
                    r.id = excelRecords.length;
                    excelRecords.push(r);
                };

                lines.forEach(line => {
                    // Excel'den yapıştırma = sekme; elle/boşlukla yazılan satırlar da desteklenir
                    const hasTab = line.indexOf('\t') !== -1;
                    let cols = (hasTab ? line.split('\t') : line.split(/[\s,;]+/))
                        .map(c => c.trim().replace(/^["']+|["']+$/g, ''))
                        .filter(c => c.length > 0);
                    if (!hasTab && cols.length > 1) {
                        cols = cols.filter(c => c.length >= 5 && /\d/.test(c)); // yalnız kod benzeri parçalar
                    }
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
                        // 1. Beyanname No: 26xxxx...IMxxxxxxxx (Gebze 264103, Derince 264105 vb.)
                        if (/^26[0-9]{2}[0-9A-Z]{8,16}(?:IM[0-9]{4,10})?$/i.test(val) || /^\d{8}(?:IM|EX)\d{6,10}$/i.test(val)) {
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

                    // Evrim sütun sıralaması fallback'leri (yalnız sekmeli/Excel satırlarında anlamlı)
                    if (hasTab && !detectedBl && cols.length >= 6) {
                        detectedDosya = detectedDosya || cols[0];
                        detectedRef = detectedRef || cols[2];
                        detectedBl = cols[5];
                    } else if (hasTab && !detectedBl && cols.length === 3) {
                        detectedDosya = detectedDosya || cols[0];
                        detectedRef = detectedRef || cols[1];
                        detectedBl = cols[2];
                    } else if (hasTab && !detectedBl && cols.length === 2) {
                        detectedDosya = detectedDosya || cols[0];
                        detectedBl = cols[1];
                    } else if (!detectedBl && !detectedContainer && !detectedBeyan && !detectedFatura && !detectedRef) {
                        // Serbest metin satırı (örn. BUP0208349 gibi tanınmayan armatör kodları)
                        cols.forEach(c => {
                            if (c.length >= 4) {
                                addRecord({
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
                        addRecord({
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

            function isPortAllowed(details, fullText) {
                const filterEl = document.querySelector('input[name="liman-filter"]:checked');
                const filterVal = filterEl ? filterEl.value : 'ALL';
                if (filterVal === 'ALL') return true;

                // Satıcı VKN'den kesin biliniyorsa onu kullan
                if (details && typeof details.isPort === 'boolean') return details.isPort;

                // PORT_ONLY: Limanlar (Evyap/DP World, Yılport, Safiport, Kumport, Marport, Limak vb.)
                const combined = normalizeTurkish(((details && details.gonderen) || '') + ' ' + (fullText || '')).toUpperCase();
                return /EVYAP|1030050950|DP\s*WORLD|YARIMCA|KORFEZ|9380022882|7580022041|SAFIPORT|KUMPORT|MARPORT|ASYAPORT|YILPORT|LIMAK|MERSIN|\bMIP\b/.test(combined);
            }

            function getPageInvoices() {
                const UUID_RE = /[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{10,12}/;
                const rows = Array.from(document.querySelectorAll('.brow, [rowid], tr')).filter(r => r.querySelector("input.csc-mini-button[rel='mbAc']") || r.getAttribute('rowid'));
                const invoiceItems = [];
                const seenUuids = new Set(); // iç içe satır seçicilerinin aynı faturayı iki kez üretmesini önle

                rows.forEach(row => {
                    const text = row.innerText || '';
                    const html = row.innerHTML || '';
                    const match = html.match(UUID_RE) || text.match(UUID_RE) || row.getAttribute('rowid');
                    const uuid = typeof match === 'string' ? match : (match ? match[0] : null);
                    if (!uuid || seenUuids.has(uuid.toLowerCase())) return;
                    seenUuids.add(uuid.toLowerCase());

                    const cells = Array.from(row.querySelectorAll('.cell, td, .in-cell')).map(c => c.innerText.trim()).filter(c => c.length > 0);
                    const faturaNoMatch = text.match(/\b([A-Z0-9]{3}202\d{10}|[A-Z0-9]{16})\b/);
                    const tarihMatch = text.match(/\b\d{2}\/\d{2}\/\d{4}\b/);
                    const tutarMatch = text.match(/([\d\.]+,[\d]{2})\s*(TRY|TL|USD|EUR|\$|€)?/i);

                    invoiceItems.push({
                        rowElement: row,
                        ettn: uuid,
                        faturaNo: faturaNoMatch ? faturaNoMatch[0] : (cells[3] || ''),
                        tarih: tarihMatch ? tarihMatch[0] : (cells[4] || ''),
                        gonderen: cells[6] || cells[5] || '',
                        tutar: tutarMatch ? tutarMatch[1] : (cells[9] || cells[8] || '')
                    });
                });
                return invoiceItems;
            }

            function extractDetailsFromHtml(html, text, fallbackItem) {
                let tutar = fallbackItem.tutar || '';
                let doviz = 'TL';

                // 1. Tutar + Para birimi: sadece "Ödenecek Tutar" gibi toplam satırındaki birime güvenilir.
                //    (Eski sürüm gövdede/banka listesinde geçen "USD"yi görüp faturayı USD sanabiliyordu.)
                const tutarPatterns = [
                    /Ödenecek\s*Tutar\s*[:\s]*([\d\.]+,\d{2})\s*(TRY|TL|USD|EUR|\$|€)?/i,
                    /Vergiler\s*Dahil\s*Toplam(?:\s*Tutar)?\s*[:\s]*([\d\.]+,\d{2})\s*(TRY|TL|USD|EUR|\$|€)?/i,
                    /KDV\s*Dahil\s*Toplam\s*Tutar\s*[:\s]*([\d\.]+,\d{2})\s*(TRY|TL|USD|EUR|\$|€)?/i,
                    /MAL\s*HİZMET\s*TOPLAM\s*TUTARI\s*[:\s]*([\d\.]+,\d{2})\s*(TRY|TL|USD|EUR|\$|€)?/i,
                    /TOPLAM\s*TUTAR\s*[:\s]*([\d\.]+,\d{2})\s*(TRY|TL|USD|EUR|\$|€)?/i,
                    // QR JSON içinden odenecek değeri
                    /"odenecek":"([\d\.]+)"/i
                ];

                for (let p of tutarPatterns) {
                    const m = text.match(p) || html.match(p);
                    if (m) {
                        // QR JSON'dan gelen değer virgül yerine nokta kullanıyor, düzelt
                        tutar = m[1].includes(',') ? m[1] : m[1].replace('.', ',');
                        if (m[2]) {
                            const cur = m[2].toUpperCase();
                            if (cur === 'USD' || cur === '$') doviz = 'USD';
                            else if (cur === 'EUR' || cur === '€') doviz = 'EUR';
                            else doviz = 'TL';
                        } else {
                            // Birim toplam satırında yoksa UBL para birimi etiketine bak
                            const tag = html.match(/currencyID\s*=\s*["'](USD|EUR|TRY)["']/i) || html.match(/DocumentCurrencyCode[^>]*>\s*(USD|EUR|TRY)\b/i);
                            if (tag) {
                                const c = tag[1].toUpperCase();
                                doviz = (c === 'USD' || c === 'EUR') ? c : 'TL';
                            }
                        }
                        break;
                    }
                }

                // 2. Gönderen: KENDİ VKN'miz (4570543930) hariç, satıcı VKN'sine göre kesin tespit
                const seller = detectSeller(text, fallbackItem.gonderen);

                // 3. Beyanname No (birden fazla olabilir), Konteyner No(lar), faturadaki BL
                const beyanList = extractBeyanNos(text);
                const containers = extractContainers(text);
                const faturaBl = extractInvoiceBls(normalizeTurkish(text).toUpperCase()).join(', ');

                const dosyaMatch = text.match(/\b(26-\d{5,7})\b/i);
                const dosyaNo = dosyaMatch ? dosyaMatch[0] : '';

                return { tutar, doviz, gonderen: seller.name, isPort: seller.isPort, beyanNo: beyanList.join(', '), dosyaNo, containers, faturaBl };
            }

            // ---- Fatura HTML'ini çek (zaman aşımı + 3 strateji + yeniden deneme) ----
            async function fetchInvoiceHtml(ettn) {
                const base = `/efatura/display?cmd=GELEN_FATURA_GOSTER&invoiceUuid=${ettn}&type=html`;
                const urls = [base + '&alternativeTransformer=false', base + '&alternativeTransformer=true', base];
                for (let attempt = 0; attempt < 2; attempt++) {
                    if (shouldStop) return '';
                    for (let u = 0; u < urls.length; u++) {
                        const ctrl = new AbortController();
                        const to = setTimeout(() => ctrl.abort(), 20000);
                        try {
                            const res = await fetch(urls[u], { signal: ctrl.signal, credentials: 'same-origin' });
                            if (res.ok) {
                                const t = await res.text();
                                // Gerçek fatura mı? (e-Fatura'da VKN/ETTN zorunludur; login/hata sayfalarını ele)
                                if (t && t.length > (u === 2 ? 200 : 500) && /VKN|ETTN|Fatura|FATURA|Invoice/.test(t) && !/type=["']password["']/i.test(t)) {
                                    return t;
                                }
                            }
                        } catch (e) {
                            /* zaman aşımı / ağ hatası → sıradaki strateji */
                        } finally {
                            clearTimeout(to);
                        }
                    }
                    await sleep(600 * (attempt + 1));
                }
                return '';
            }

            // Bir hedef kaydın faturayla eşleşme nedenini döndürür ('' = eşleşmedi)
            function matchRecord(rec, ctx, item) {
                const alnum = (s) => s.replace(/[^A-Z0-9]/g, '');
                const bRaw = normalizeTurkish(rec.blNo || '').toUpperCase();
                const bClean = rec.cleanBl || '';
                const rRaw = normalizeTurkish(rec.refNo || '').toUpperCase();
                const rClean = rec.cleanRef || '';
                const byRaw = normalizeTurkish(rec.beyanNo || '').toUpperCase();
                const cRaw = normalizeTurkish(rec.containerNo || '').toUpperCase();
                const fRaw = normalizeTurkish(rec.faturaNo || '').toUpperCase();
                const { normText, cleanText, normHtml, cleanHtml } = ctx;

                // 1. Fatura No
                if (fRaw && fRaw.length >= 10) {
                    if ((item.faturaNo && item.faturaNo.toUpperCase().includes(fRaw)) || cleanText.includes(alnum(fRaw))) return 'Fatura No';
                }

                // 2. ETTN
                const ettnU = (item.ettn || '').toUpperCase();
                if (ettnU && (bRaw === ettnU || rRaw === ettnU)) return 'ETTN';

                // 3. Konteyner (boşluklu/alt çizgili "UETU 642793_8" yazımları dahil: yalnız harf+rakam karşılaştırılır)
                const cntTarget = cRaw || (/^[A-Z]{4}[0-9]{7}$/.test(bRaw) ? bRaw : '');
                if (cntTarget && cleanText.includes(alnum(cntTarget))) return 'Konteyner';

                // 4. Beyanname
                const byTarget = byRaw || ((bRaw.startsWith('264') && bRaw.length >= 14) ? bRaw : '');
                if (byTarget) {
                    const t = alnum(byTarget);
                    if (cleanText.includes(t) || cleanHtml.includes(t)) return 'Beyanname';
                }

                // 5. Konşimento (BL)
                if (bRaw && bRaw.length >= 5) {
                    if (normText.includes(bRaw) || normHtml.includes(bRaw)) return 'BL';
                    // Armatör prefix'i faturada yazılmamış olabilir (HLCUSEL2605AUXF3 → SEL2605AUXF3, COEU9021119590 → 9021119590).
                    if (bClean && bClean.length >= 8 && bClean !== alnum(bRaw)) {
                        if (/[A-Z]/.test(bClean)) {
                            if (cleanText.includes(bClean) || cleanHtml.includes(bClean)) return 'BL';
                        } else {
                            // Sadece rakamlı kodlarda birleştirilmiş metin yanlış pozitif üretir; kelime sınırı şart
                            if (new RegExp('(^|[^A-Z0-9])' + bClean + '([^A-Z0-9]|$)').test(normText)) return 'BL';
                        }
                    }
                    if (bRaw.length < 8) {
                        const escaped = bRaw.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
                        const reg = new RegExp('(^|[^A-Z0-9])' + escaped + '([^A-Z0-9]|$)', 'i');
                        if (reg.test(normText) || reg.test(normHtml)) return 'BL';
                    }
                }

                // 6. Hankook Referans No
                if (rRaw && rRaw.length >= 5 && rRaw !== bRaw) {
                    if (normText.includes(rRaw) || normHtml.includes(rRaw)) return 'Referans';
                    if (rClean && rClean.length >= 8 && (cleanText.includes(rClean) || cleanHtml.includes(rClean))) return 'Referans';
                }
                return '';
            }

            // Tek bir faturayı çek, ayrıştır, hedeflerle eşleştir. 'match' | 'nomatch' | 'dup' | 'fail'
            async function processItem(item) {
                if (foundInvoiceUuids.has(item.ettn)) return 'dup';

                const html = await fetchInvoiceHtml(item.ettn);
                if (!html) {
                    if (!shouldStop && !scanState.failed.some(f => f.ettn === item.ettn)) scanState.failed.push(item);
                    return 'fail';
                }
                foundInvoiceUuids.add(item.ettn);
                scanState.failed = scanState.failed.filter(f => f.ettn !== item.ettn);
                scanState.scanned++;

                try {
                    const text = htmlToText(html);
                    const normText = normalizeTurkish(text).toUpperCase();
                    const normHtml = normalizeTurkish(html).toUpperCase();
                    const ctx = {
                        normText, normHtml,
                        cleanText: normText.replace(/[^A-Z0-9]/g, ''),
                        cleanHtml: normHtml.replace(/[^A-Z0-9]/g, '')
                    };

                    const details = extractDetailsFromHtml(html, text, item);
                    const matched = [];
                    if (isPortAllowed(details, text)) {
                        for (const rec of excelRecords) {
                            const reason = matchRecord(rec, ctx, item);
                            if (reason) {
                                matched.push({ rec, reason });
                                foundRecordIds.add(rec.id); // her hedef kayıt ayrı sayılır (aynı BL'li kayıtlar artık birleşmez)
                            }
                        }
                    } else {
                        scanState.filtered++;
                    }

                    const isOurs = matched.length > 0;
                    if (item.rowElement) {
                        item.rowElement.setAttribute('data-bizim-mi', isOurs ? 'true' : 'false');
                        if (isOurs) {
                            item.rowElement.style.background = '#dcfce7';
                            item.rowElement.style.borderLeft = '6px solid #16a34a';
                        }
                    }

                    if (isOurs && !allScannedResults.some(r => r.ettn === item.ettn)) {
                        const recs = matched.map(m => m.rec);
                        const matchedBls = Array.from(new Set(recs.map(r => r.blNo).filter(Boolean))).join(', ');
                        const matchedRefs = Array.from(new Set(recs.map(r => r.refNo).filter(Boolean))).join(', ');
                        const reasons = Array.from(new Set(matched.map(m => m.reason))).join(' + ');

                        let dNo = recs.find(r => r.dosyaNo && r.dosyaNo !== 'Listeden')?.dosyaNo || details.dosyaNo || '';
                        if (!dNo && matchedBls) dNo = lookupEvrimDosya(matchedBls.split(',')[0].trim());

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
                            faturaBl: details.faturaBl || '',
                            eslesme: reasons,
                            rawHtml: html
                        });
                        updateProgress(`🎯 Fatura bulundu: ${finalFaturaNo || item.faturaNo || item.ettn}`);
                        scheduleModalRefresh();
                    }
                    return isOurs ? 'match' : 'nomatch';
                } catch (err) {
                    console.error("Fatura işleme hatası:", item.ettn, err);
                    foundInvoiceUuids.delete(item.ettn);
                    scanState.scanned--;
                    if (!scanState.failed.some(f => f.ettn === item.ettn)) scanState.failed.push(item);
                    return 'fail';
                }
            }

            async function scanCurrentPage(pageNumDisplay, totalPages) {
                const invoiceItems = getPageInvoices();
                scanState.onPage = invoiceItems.length;
                scanState.done = 0;
                let basarili = 0;
                let eslesen = 0;
                const pageLabel = `Sayfa ${pageNumDisplay}${totalPages ? '/' + totalPages : ''}`;

                const batchSize = 4;
                for (let i = 0; i < invoiceItems.length; i += batchSize) {
                    if (shouldStop) break;
                    const batch = invoiceItems.slice(i, i + batchSize);
                    updateProgress(`${pageLabel} taranıyor (${Math.min(i + batchSize, invoiceItems.length)} / ${invoiceItems.length})`);

                    await Promise.all(batch.map(async (item) => {
                        const r = await processItem(item);
                        scanState.done++;
                        if (r === 'match') eslesen++;
                        if (r !== 'fail') basarili++;
                        updateProgress(); // her fatura sonrası sayaçları anında yenile
                        await tick();     // UI thread'e nefes ver (donma hissini önler)
                    }));
                    await tick();
                }

                return { basarili, eslesen };
            }

            // ---- Sonuç penceresi yardımcıları (tarama sürerken canlı yenilenir) ----
            function modalTitleText(list) {
                return `✅ Hankook - Bulunan Faturalar (${list.length} Fatura • ${foundRecordIds.size} / ${excelRecords.length} Hedef)`;
            }

            function missingTargetsHtml() {
                const missing = excelRecords.filter(r => !foundRecordIds.has(r.id));
                if (excelRecords.length === 0) return '';
                if (missing.length === 0) return `<span style="color:#16a34a; font-weight:bold;">🎉 Tüm hedefler bulundu.</span>`;
                const names = missing.map(r => escHtml(r.containerNo || r.blNo || r.beyanNo || r.refNo)).join(', ');
                return `<span style="color:#b45309;"><b>⚠️ Bulunamayan ${missing.length} hedef:</b> ${names}</span>`;
            }

            function resultRowsHtml(list) {
                if (list.length === 0) {
                    return `<tr><td colspan="11" style="text-align:center; padding:30px; color:#888;">Aradığınız konşimento numaralarıyla eşleşen fatura bulunamadı.</td></tr>`;
                }
                return list.map((inv, i) => {
                    const curDisplay = inv.doviz ? ` ${inv.doviz}` : ' TL';
                    const faturadaBl = (inv.faturaBl && inv.faturaBl !== inv.blNo)
                        ? `<div style="font-size:10px; color:#94a3b8; font-weight:normal;">Faturada: ${escHtml(inv.faturaBl)}</div>` : '';
                    return `
                        <tr style="border-bottom:1px solid #eee; background:${i % 2 === 0 ? '#ffffff' : '#f9fafb'};">
                            <td style="padding:10px 8px; font-weight:bold; color:#16a34a;">${i + 1}</td>
                            <td style="padding:10px 8px; font-weight:bold;">${escHtml(inv.faturaNo)}</td>
                            <td style="padding:10px 8px; color:#333;">${escHtml(inv.gonderen) || '—'}</td>
                            <td style="padding:10px 8px; font-weight:bold; color:#16a34a;">${escHtml(inv.tutar) || '—'}${curDisplay}</td>
                            <td style="padding:10px 8px; font-weight:bold; color:#2563eb;">${escHtml(inv.dosyaNo) || '—'}</td>
                            <td style="padding:10px 8px; font-weight:bold; color:#7c3aed;">${escHtml(inv.blNo) || '—'}${faturadaBl}</td>
                            <td style="padding:10px 8px; color:#0d9488; font-family:monospace; font-weight:bold;">${escHtml(inv.konteynerNo) || '—'}</td>
                            <td style="padding:10px 8px; color:#b45309; font-family:monospace;">${escHtml(inv.beyanNo) || '—'}</td>
                            <td style="padding:10px 8px; color:#555;">${escHtml(inv.refNo) || '—'}</td>
                            <td style="padding:10px 8px; color:#475569; font-size:11px;">${escHtml(inv.eslesme) || '—'}</td>
                            <td style="padding:10px 8px; text-align:center;">
                                <button onclick="window.open('/efatura/display?cmd=GELEN_FATURA_GOSTER&invoiceUuid=${inv.ettn}&type=html&alternativeTransformer=false', '_blank', 'width=900,height=800')" style="background:#6b21a8; color:#fff; border:none; padding:5px 10px; border-radius:4px; cursor:pointer; font-size:11px; font-weight:bold;">
                                    🔍 Aç
                                </button>
                            </td>
                        </tr>
                    `;
                }).join('');
            }

            function refreshResultsModal() {
                if (!document.getElementById('gumruk-sonuc-modal')) return;
                const list = allScannedResults.filter(r => r.isOurs === 'EVET');
                const tb = document.getElementById('modal-tbody');
                if (tb) tb.innerHTML = resultRowsHtml(list);
                const ti = document.getElementById('modal-title');
                if (ti) ti.textContent = modalTitleText(list);
                const ms = document.getElementById('modal-missing');
                if (ms) ms.innerHTML = missingTargetsHtml();
                const bp = document.getElementById('modal-para-talep-aktar');
                if (bp) bp.innerText = `💰 Para Talep Kuyruğuna Aktar (${list.length} Fatura)`;
            }

            let modalRefreshTimer = null;
            function scheduleModalRefresh() {
                if (modalRefreshTimer || !document.getElementById('gumruk-sonuc-modal')) return;
                modalRefreshTimer = setTimeout(() => { modalRefreshTimer = null; refreshResultsModal(); }, 700);
            }

            function getCurrentPageText() {
                const pageInput = document.querySelector('input.csc-dt-paging-text');
                const pageSpan = document.querySelector('.csc-dt-paging-text');
                return ((pageInput ? pageInput.value : (pageSpan ? pageSpan.innerText : '')) || '').trim();
            }

            // Sayfadaki tüm faturaların imzası: sadece ilk satıra bakmak yerine tüm liste değişmeli
            function pageSignature() {
                return getPageInvoices().map(i => i.ettn).join('|');
            }

            async function waitForNewPage(oldSig, targetPageNum) {
                const maxWaitMs = 20000;
                const startTime = Date.now();
                await sleep(500); // geçişin başlaması için başlangıç gecikmesi

                let lastSig = '';
                let stable = 0;
                while (Date.now() - startTime < maxWaitMs) {
                    if (shouldStop) return false;

                    const sig = pageSignature();
                    const pageNo = parseInt(getCurrentPageText(), 10);
                    const pageMatches = !isNaN(pageNo) && pageNo === targetPageNum;
                    const changed = sig.length > 0 && sig !== oldSig;

                    if (changed) {
                        // Liste değişti: DOM'un yazılması bitsin diye iki ardışık okumada aynı kalmasını bekle
                        stable = (sig === lastSig) ? stable + 1 : 0;
                        lastSig = sig;
                        if (stable >= 1 && (pageMatches || isNaN(pageNo))) return true;
                        if (stable >= 5) return true;
                    } else if (pageMatches && sig.length > 0 && Date.now() - startTime > 3500) {
                        // Sayfa no hedefe ulaştı ama içerik aynı (tek sayfalık / aynı içerikli tablo)
                        await sleep(500);
                        return true;
                    }
                    await sleep(350);
                }
                return false;
            }

            // 0 = bilinmiyor (artık sabit 25 sayfa sınırı yok; "sonraki" butonu bitene kadar gidilir)
            function getTotalPages() {
                const pagingContainer = document.querySelector('.csc-dt-paging-text')?.parentElement;
                if (pagingContainer) {
                    const match = (pagingContainer.innerText || '').match(/\/\s*(\d+)/);
                    if (match && match[1]) return parseInt(match[1], 10);
                }
                return 0;
            }

            document.getElementById('btn-durdur').onclick = function() {
                shouldStop = true;
                this.style.display = 'none';
                updateProgress('Kullanıcı tarafından durduruldu');
            };

            document.getElementById('btn-tara-hepsi').onclick = async function() {
                if (isScanning) return; // çift tıklama koruması
                parsePastedData();
                if (excelRecords.length === 0) { alert("Lütfen aranacak konşimentoları yapıştırın."); return; }

                isScanning = true;
                shouldStop = false;
                foundRecordIds.clear();
                foundInvoiceUuids.clear();
                allScannedResults = [];
                scanState = { page: 0, pages: 0, onPage: 0, done: 0, scanned: 0, filtered: 0, failed: [], warning: '', finished: false };

                const btnTara = this;
                const btnDurdur = document.getElementById('btn-durdur');
                const txtList = document.getElementById('konsimento-listesi');
                btnTara.disabled = true;
                btnTara.style.opacity = '0.6';
                btnDurdur.style.display = 'block';
                if (txtList) txtList.readOnly = true; // tarama sırasında hedef listesi değişmesin
                updateProgress('Hazırlanıyor...');

                try {
                    // Sayfa 1'e dön
                    const curPageText = getCurrentPageText();
                    const firstBtn = document.querySelector('.csc-dt-paging-btn.csc-dt-seek-first:not(.csc-dt-paging-btn-disabled)');
                    if (curPageText && curPageText !== '1' && firstBtn) {
                        updateProgress("Sayfa 1'e dönülüyor...");
                        const oldSig = pageSignature();
                        firstBtn.click();
                        await waitForNewPage(oldSig, 1);
                    }

                    updateProgress("Tarama başladı...");
                    const scanAllPages = document.getElementById('chk-scan-all-pages')?.checked ?? true;
                    let pageNum = 1;

                    while (!shouldStop) {
                        const totalPages = getTotalPages();
                        scanState.page = pageNum;
                        scanState.pages = totalPages || pageNum;
                        const sigBefore = pageSignature();

                        await scanCurrentPage(pageNum, totalPages);

                        if (!scanAllPages && foundRecordIds.size >= excelRecords.length && excelRecords.length > 0) {
                            break; // Tüm hedefler bulundu
                        }

                        updateProgress(`Sayfa ${pageNum}${totalPages ? '/' + totalPages : ''} tamamlandı (${foundRecordIds.size}/${excelRecords.length} Hedef, ${allScannedResults.length} Fatura)`);

                        const nextBtn = document.querySelector('.csc-dt-paging-btn.csc-dt-seek-next:not(.csc-dt-paging-btn-disabled)');
                        if (!nextBtn || (totalPages && pageNum >= totalPages) || shouldStop) break;

                        nextBtn.click();
                        pageNum++;
                        let pageLoaded = await waitForNewPage(sigBefore, pageNum);
                        if (!pageLoaded && !shouldStop) {
                            updateProgress(`⏳ Sayfa ${pageNum} yavaş yükleniyor, bekleniyor...`);
                            pageLoaded = await waitForNewPage(sigBefore, pageNum);
                        }
                        if (!pageLoaded && !shouldStop) {
                            // Eski içeriği tekrar tarayıp sayfaları atlamak yerine durup kullanıcıyı uyar
                            scanState.warning = `Sayfa ${pageNum} yüklenemedi, tarama durdu`;
                            break;
                        }
                    }

                    // Okunamayan faturaları yeniden dene (ETTN ile her sayfadan çekilebilir)
                    for (let round = 0; round < 2 && !shouldStop && scanState.failed.length > 0; round++) {
                        const retryList = scanState.failed.slice();
                        updateProgress(`🔁 ${retryList.length} okunamayan fatura yeniden deneniyor...`);
                        for (let i = 0; i < retryList.length && !shouldStop; i += 3) {
                            await Promise.all(retryList.slice(i, i + 3).map(async (it) => { await processItem(it); updateProgress(); }));
                        }
                    }
                } catch (err) {
                    console.error("Tarama hatası:", err);
                    scanState.warning = 'Hata: ' + (err && err.message ? err.message : err);
                } finally {
                    btnDurdur.style.display = 'none';
                    btnTara.disabled = false;
                    btnTara.style.opacity = '1';
                    if (txtList) txtList.readOnly = false;
                    isScanning = false;
                    scanState.finished = true;
                }

                const failedN = scanState.failed.length;
                updateProgress(
                    `${shouldStop ? '⏹️ Durduruldu' : '✅ Tamamlandı'}: ${foundRecordIds.size}/${excelRecords.length} hedef • ${allScannedResults.length} fatura` +
                    (failedN ? ` • ⚠️ ${failedN} fatura okunamadı` : '') +
                    (scanState.warning ? ` • ⚠️ ${scanState.warning}` : '')
                );
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

                const rowsHtml = resultRowsHtml(ourInvoices);

                modal.innerHTML = `
                    <div style="background:#16a34a; color:#fff; padding:14px 20px; border-radius:12px 12px 0 0; display:flex; justify-content:space-between; align-items:center;">
                        <h3 id="modal-title" style="margin:0; font-size:16px;">${modalTitleText(ourInvoices)}</h3>
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
                                    <th style="padding:8px;">Eşleşme</th>
                                    <th style="padding:8px; text-align:center;">İşlem</th>
                                </tr>
                            </thead>
                            <tbody id="modal-tbody">${rowsHtml}</tbody>
                        </table>
                    </div>
                    <div style="padding:12px 20px; background:#f9fafb; border-top:1px solid #eee; border-radius:0 0 12px 12px; display:flex; justify-content:space-between; align-items:center; gap:12px;">
                        <div id="modal-missing" style="font-size:12px; color:#666; max-width:420px; max-height:70px; overflow-y:auto;">${missingTargetsHtml()}</div>
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
                        let ptQueue = allScannedResults.filter(r => r.isOurs === 'EVET').map(inv => {
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

                const q = (v) => '"' + String(v == null ? '' : v).replace(/"/g, '""') + '"';
                let csv = "\uFEFFETTN;Fatura No;Fatura Tarihi;Gonderen Firma;Tutar;Para Birimi;Dosya No;Eslesen BL;Konteyner No;Beyanname No;Referans No;Faturadaki BL;Eslesme Nedeni\n";
                ourInvoices.forEach(r => {
                    let cleanTutar = (r.tutar || '').replace(/\./g, '');
                    csv += [r.ettn, r.faturaNo, r.tarih, r.gonderen, cleanTutar, r.doviz || 'TL', r.dosyaNo, r.blNo, r.konteynerNo || '', r.beyanNo || '', r.refNo, r.faturaBl || '', r.eslesme || ''].map(q).join(';') + "\n";
                });

                const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
                const link = document.createElement('a');
                link.href = URL.createObjectURL(blob);
                link.download = `Hankook_Bulunan_Faturalar_${new Date().toISOString().slice(0,10)}.csv`;
                link.click();
            };

            console.log("🚀 QNB Fatura & Konşimento Eşleştirici v3.6 Hazır!");

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
