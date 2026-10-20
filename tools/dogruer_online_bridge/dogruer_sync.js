// dogruer_sync.js - Evrim Veri Çekici (735 Dosya Garantili Motor)
(async function syncAllEvrimData() {
    console.log("🚀 Evrim Veri Merkezi için tam senkronizasyon başlatıldı...");
    
    // Status banner
    let banner = document.getElementById("evrim_sync_banner");
    if (!banner) {
        banner = document.createElement("div");
        banner.id = "evrim_sync_banner";
        banner.style.cssText = "position:fixed; top:20px; right:20px; background:#0f172a; color:#38bdf8; border:2px solid #38bdf8; border-radius:10px; padding:15px 25px; z-index:999999; font-family:'Segoe UI',sans-serif; font-size:14px; box-shadow:0 10px 25px rgba(0,0,0,0.5); font-weight:bold;";
        document.body.appendChild(banner);
    }
    banner.style.background = "#0f172a";
    banner.style.color = "#38bdf8";
    banner.innerText = "⏳ Evrim Verileri Taranıyor... Lütfen Bekleyin.";
    banner.style.display = "block";

    let allData = [];
    
    // 1. En başa (1. Sayfaya) git
    let firstBtn = document.querySelector(".e-pager a[title*='İlk'], .e-pager a[title*='First'], .e-pager .e-firstpage, .e-pager .e-fp, .e-pager a:first-child");
    if (firstBtn && !firstBtn.classList.contains("e-currentitem") && !firstBtn.classList.contains("e-active")) {
        firstBtn.click();
        await new Promise(r => setTimeout(r, 1000));
    }

    for (let targetPage = 1; targetPage <= 25; targetPage++) {
        let pageBtn = Array.from(document.querySelectorAll(".e-pager a.e-numericitem")).find(a => a.innerText.trim() === targetPage.toString());
        
        if (!pageBtn) {
            let nextCluster = document.querySelector(".e-pager .e-np, .e-pager [title*='Sonraki çağrı']");
            if (nextCluster && !nextCluster.classList.contains("e-disable")) {
                nextCluster.click();
                await new Promise(r => setTimeout(r, 900));
                pageBtn = Array.from(document.querySelectorAll(".e-pager a.e-numericitem")).find(a => a.innerText.trim() === targetPage.toString());
            }
        }

        if (pageBtn && !pageBtn.classList.contains("e-currentitem") && !pageBtn.classList.contains("e-active")) {
            let firstRowBefore = document.querySelector("table tbody tr td:nth-child(3)")?.innerText.trim();
            pageBtn.click();
            
            for (let i = 0; i < 20; i++) {
                await new Promise(r => setTimeout(r, 200));
                let firstRowAfter = document.querySelector("table tbody tr td:nth-child(3)")?.innerText.trim();
                if (firstRowAfter && firstRowAfter !== firstRowBefore) break;
            }
            await new Promise(r => setTimeout(r, 300));
        }

        let rows = Array.from(document.querySelectorAll("table tr")).map(r => Array.from(r.querySelectorAll("th, td")).map(td => td.innerText.trim())).filter(r => r.length > 3);
        let pageData = rows.slice(1).map(r => ({
            dosya_no: r[2] || "",
            hankook_ref: r[3] || "",
            yurt_disi_firma: r[4] || "",
            gumruk: r[5] || "",
            liman: r[6] || "",
            rejim: r[7] || "",
            beyanname_tarihi: r[8] || "",
            beyanname_no: r[9] || "",
            statu: r[10] || "",
            teslim_tarihi: r[11] || "",
            asama: r[12] || "",
            ilerleme: r[13] || "",
            not: r[14] || ""
        })).filter(x => x.dosya_no && x.dosya_no.length > 3);

        let added = 0;
        for (let item of pageData) {
            if (!allData.some(d => d.dosya_no === item.dosya_no)) {
                allData.push(item);
                added++;
            }
        }

        banner.innerText = `🔄 Evrim Taranıyor: Sayfa ${targetPage} (Toplam: ${allData.length} Dosya)`;
        console.log(`✅ Sayfa ${targetPage} çekildi (+${added} dosya). Toplam: ${allData.length}`);

        let maxPage = Math.max(...Array.from(document.querySelectorAll(".e-pager a.e-numericitem")).map(a => parseInt(a.innerText.trim()) || 0));
        let hasNext = document.querySelector(".e-pager .e-np:not(.e-disable)");
        if (targetPage >= maxPage && !hasNext) {
            break;
        }
    }

    banner.style.background = "#16a34a";
    banner.style.color = "#ffffff";
    banner.innerText = `✅ BAŞARILI! ${allData.length} Dosya Evrim'den Çekildi!`;
    setTimeout(() => { banner.style.display = "none"; }, 5000);

    // Sonucu DOM'a ve Title'a bildir
    window.__ALL_EVRIM_DATA = allData;
    document.body.setAttribute("data-sync-result", JSON.stringify(allData));
    document.title = "DOGRUER_SYNC_DONE:" + allData.length;
    console.log(`🎉 Senkronizasyon Tamamlandı: Toplam ${allData.length} dosya.`);
    return allData;
})();
