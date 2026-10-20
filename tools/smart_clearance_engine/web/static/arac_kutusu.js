const AK_TOOLS = {
    word_to_pdf: {
        title: "Word'den PDF'e Dönüştür",
        desc: "Word belgesini seçin, anında PDF'e çevirelim.",
        icon: "📄", accept: ".doc,.docx", multiple: false, endpoint: "/api/arac-kutusu/word-to-pdf"
    },
    img_to_pdf: {
        title: "Görselden PDF'e Çevir",
        desc: "Bir veya birden fazla görseli (.png, .jpg) seçerek PDF olarak birleştirin.",
        icon: "🖼️", accept: ".png,.jpg,.jpeg,.bmp", multiple: true, endpoint: "/api/arac-kutusu/img-to-pdf"
    },
    merge_pdf: {
        title: "PDF Dosyalarını Birleştir",
        desc: "Birden fazla PDF dosyasını seçin, birleştirip tek bir belge olarak indirelim.",
        icon: "🔗", accept: ".pdf", multiple: true, endpoint: "/api/arac-kutusu/merge-pdf"
    },
    pdf_to_word: {
        title: "PDF'ten Word'e Dönüştür",
        desc: "PDF dosyanızı düzenlenebilir Word formatına dönüştürün.",
        icon: "📝", accept: ".pdf", multiple: false, endpoint: "/api/arac-kutusu/pdf-to-word"
    },
    pdf_to_img: {
        title: "PDF'ten Görsele Dönüştür",
        desc: "PDF dosyanızın sayfalarını yüksek çözünürlüklü resimlere (ZIP) çevirin.",
        icon: "🎞️", accept: ".pdf", multiple: false, endpoint: "/api/arac-kutusu/pdf-to-img"
    },
    split_pdf: {
        title: "PDF Dosyasını Böl",
        desc: "Hangi sayfaları ayırmak istediğinizi belirtin (Örn: 1-3, 5).",
        icon: "✂️", accept: ".pdf", multiple: false, endpoint: "/api/arac-kutusu/split-pdf",
        optionsHTML: `
            <div class="form-group">
                <label>Bölünecek Sayfa Aralığı</label>
                <input type="text" id="ak_opt_pages" class="form-control" placeholder="Örn: 1-3, 5, 8-10" autocomplete="off">
            </div>
        `
    },
    rotate_pdf: {
        title: "PDF Döndür",
        desc: "PDF sayfalarınızı istediğiniz açıda kalıcı olarak döndürün.",
        icon: "🔄", accept: ".pdf", multiple: false, endpoint: "/api/arac-kutusu/rotate-pdf",
        optionsHTML: `
            <div class="form-group">
                <label>Döndürme Açısı</label>
                <select id="ak_opt_degree" class="form-control">
                    <option value="90">90° Sağa Döndür</option>
                    <option value="180">180° Ters Çevir</option>
                    <option value="270">90° Sola Döndür</option>
                </select>
            </div>
        `
    },
    protect_pdf: {
        title: "PDF Şifrele",
        desc: "PDF dosyanızı açılış parolası ile koruma altına alın.",
        icon: "🔒", accept: ".pdf", multiple: false, endpoint: "/api/arac-kutusu/protect-pdf",
        optionsHTML: `
            <div class="form-group">
                <label>Şifre Belirleyin</label>
                <input type="password" id="ak_opt_password" class="form-control" placeholder="Bir şifre girin" autocomplete="new-password">
            </div>
        `
    },
    unlock_pdf: {
        title: "PDF Şifre Kaldır",
        desc: "Şifresini bildiğiniz PDF dosyasının parolasını kalıcı olarak kaldırın.",
        icon: "🔓", accept: ".pdf", multiple: false, endpoint: "/api/arac-kutusu/unlock-pdf",
        optionsHTML: `
            <div class="form-group">
                <label>Mevcut Şifre</label>
                <input type="password" id="ak_opt_password_unlock" class="form-control" placeholder="Mevcut şifreyi girin">
            </div>
        `
    }
};

window.akCurrentTool = null;

window.akOpenTool = function(toolId) {
    const tool = AK_TOOLS[toolId];
    if(!tool) return;
    
    window.akCurrentTool = toolId;
    
    document.getElementById("ak-dashboard-view").style.display = "none";
    document.getElementById("ak-tool-view").style.display = "block";
    
    document.getElementById("ak-tool-title").innerText = tool.title;
    document.getElementById("ak-tool-desc").innerText = tool.desc;
    document.getElementById("ak-tool-icon").innerText = tool.icon;
    
    const fileInput = document.getElementById("ak-file-input");
    fileInput.accept = tool.accept;
    if(tool.multiple) fileInput.setAttribute("multiple", "multiple");
    else fileInput.removeAttribute("multiple");
    
    // Manage Options Area
    const optionsArea = document.getElementById("ak-options-area");
    if(tool.optionsHTML) {
        optionsArea.innerHTML = tool.optionsHTML;
        optionsArea.style.display = "block";
    } else {
        optionsArea.innerHTML = "";
        optionsArea.style.display = "none";
    }
    
    // Reset views
    document.getElementById("ak-upload-area").style.display = "block";
    document.getElementById("ak-loading").style.display = "none";
};

window.akBackToDashboard = function() {
    document.getElementById("ak-tool-view").style.display = "none";
    document.getElementById("ak-dashboard-view").style.display = "block";
    document.getElementById("ak-file-input").value = "";
    document.getElementById("ak-options-area").innerHTML = "";
    window.akCurrentTool = null;
};

window.akHandleFileSelect = async function(e) {
    const files = e.target.files;
    if(!files || files.length === 0) return;
    
    const tool = AK_TOOLS[window.akCurrentTool];
    
    // Check required options before uploading
    let formData = new FormData();
    if(window.akCurrentTool === 'split_pdf') {
        const pages = document.getElementById("ak_opt_pages").value.trim();
        if(!pages) { alert("Lütfen bölünecek sayfa aralığını girin."); e.target.value = ''; return; }
        formData.append("pages", pages);
    } else if(window.akCurrentTool === 'rotate_pdf') {
        const degree = document.getElementById("ak_opt_degree").value;
        formData.append("degree", degree);
    } else if(window.akCurrentTool === 'protect_pdf') {
        const pass = document.getElementById("ak_opt_password").value;
        if(!pass) { alert("Lütfen bir şifre girin."); e.target.value = ''; return; }
        formData.append("password", pass);
    } else if(window.akCurrentTool === 'unlock_pdf') {
        const pass = document.getElementById("ak_opt_password_unlock").value;
        if(!pass) { alert("Lütfen mevcut şifreyi girin."); e.target.value = ''; return; }
        formData.append("password", pass);
    }
    
    // Start processing
    document.getElementById("ak-upload-area").style.display = "none";
    document.getElementById("ak-options-area").style.display = "none";
    document.getElementById("ak-loading").style.display = "block";
    
    for(let i=0; i<files.length; i++) {
        formData.append(tool.multiple ? 'files' : 'file', files[i]);
    }
    
    try {
        const res = await fetch(tool.endpoint, { method: 'POST', body: formData });
        
        if(!res.ok) {
            const data = await res.json();
            throw new Error(data.error || "İşlem başarısız.");
        }
        
        // Extract filename from Content-Disposition if possible
        let dlName = "Sonuc.pdf";
        const disposition = res.headers.get('Content-Disposition');
        if (disposition && disposition.indexOf('filename=') !== -1) {
            const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
            const matches = filenameRegex.exec(disposition);
            if (matches != null && matches[1]) { 
                dlName = matches[1].replace(/['"]/g, '');
            }
        }
        
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        
        a.download = dlName;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        
        // Go back
        setTimeout(() => { window.akBackToDashboard(); }, 1000);
        
    } catch(err) {
        document.getElementById("ak-loading").style.display = "none";
        alert("Hata: " + err.message);
        window.akBackToDashboard();
    }
};

// ====== HAVUZ LOGIC ======
window.akOpenHavuz = async function() {
    document.getElementById("ak-dashboard-view").style.display = "none";
    document.getElementById("ak-tool-view").style.display = "none";
    document.getElementById("ak-havuz-view").style.display = "block";
    window.akBackToHavuzList();
    await window.akLoadHavuzList();
};

window.akBackToHavuzList = function() {
    document.getElementById("ak-havuz-editor-area").style.display = "none";
    document.getElementById("ak-havuz-list-area").style.display = "block";
};

window.akLoadHavuzList = async function() {
    try {
        const res = await fetch('/api/arac-kutusu/havuz/list');
        const data = await res.json();
        const listDiv = document.getElementById("ak-havuz-list");
        listDiv.innerHTML = "";
        
        if(data.files.length === 0) {
            listDiv.innerHTML = "<div style='color:#64748b; padding:20px; border:2px dashed #cbd5e1; border-radius:12px;'>Henüz hiç şablon yüklenmemiş.</div>";
            return;
        }
        
        data.files.forEach(f => {
            listDiv.innerHTML += `
            <div style="border:1px solid #e2e8f0; border-radius:16px; padding:24px; background:rgba(255,255,255,0.8); backdrop-filter:blur(5px); cursor:pointer; transition:all 0.2s; box-shadow:0 4px 6px -1px rgba(0,0,0,0.05);" onmouseover="this.style.transform='translateY(-4px)';this.style.borderColor='#3b82f6'" onmouseout="this.style.transform='translateY(0)';this.style.borderColor='#e2e8f0'" onclick="window.akHavuzEdit('${f}')">
                <div style="font-size:2.5rem; margin-bottom:12px; filter:drop-shadow(0 2px 4px rgba(0,0,0,0.1));">📄</div>
                <div style="font-weight:600; color:#1e293b; word-break:break-all; font-size:1.1rem;">${f}</div>
            </div>
            `;
        });
    } catch(err) {
        alert("Havuz listesi alınamadı: " + err.message);
    }
};

window.akHavuzUpload = async function(e) {
    const file = e.target.files[0];
    if(!file) return;
    
    const formData = new FormData();
    formData.append("file", file);
    
    try {
        const res = await fetch('/api/arac-kutusu/havuz/upload', { method: 'POST', body: formData });
        const data = await res.json();
        if(!res.ok || !data.success) throw new Error(data.error);
        await window.akLoadHavuzList();
    } catch(err) {
        alert("Yükleme hatası: " + err.message);
    }
};

window.akHavuzEdit = async function(filename) {
    document.getElementById("ak-havuz-list-area").style.display = "none";
    document.getElementById("ak-havuz-editor-area").style.display = "block";
    document.getElementById("ak-havuz-editor-title").innerText = filename + " Düzenleniyor";
    document.getElementById("ak_havuz_filename").value = filename;
    
    const blocksContainer = document.getElementById("ak-havuz-blocks");
    blocksContainer.innerHTML = "<div class='spinner'></div> <span style='color:#3b82f6; font-weight:600;'>Şablon yükleniyor...</span>";
    
    try {
        const res = await fetch('/api/arac-kutusu/havuz/read?filename=' + encodeURIComponent(filename));
        const data = await res.json();
        if(!res.ok || !data.success) throw new Error(data.error);
        
        blocksContainer.innerHTML = "";
        data.blocks.forEach(b => {
            blocksContainer.innerHTML += `
            <div style="display:flex; flex-direction:column; gap:6px;">
                <textarea data-bid="${b.id}" class="form-control" style="resize:vertical; min-height:80px; font-family:serif; line-height:1.5;">${b.text}</textarea>
            </div>
            `;
        });
        
    } catch(err) {
        blocksContainer.innerHTML = "<div style='color:#ef4444; font-weight:bold;'>Hata: " + err.message + "</div>";
    }
};

window.akHavuzSave = async function(format) {
    const filename = document.getElementById("ak_havuz_filename").value;
    const textareas = document.querySelectorAll("#ak-havuz-blocks textarea");
    
    let editedBlocks = {};
    textareas.forEach(ta => {
        editedBlocks[ta.dataset.bid] = ta.value;
    });
    
    const formData = new FormData();
    formData.append("filename", filename);
    formData.append("blocks_json", JSON.stringify(editedBlocks));
    formData.append("format", format);
    
    const origHtml = document.getElementById("ak-havuz-editor-area").innerHTML;
    document.getElementById("ak-havuz-editor-area").innerHTML = `
      <div style="text-align:center; padding:60px 20px;">
         <div class="spinner" style="width:40px;height:40px;border-width:5px;"></div>
         <h3 style="margin-top:24px; color:#1e293b;">Belge Oluşturuluyor...</h3>
         <p style="color:#64748b; font-size:1.1rem;">Lütfen bekleyin, orijinal tasarım korunarak metinler yerleştiriliyor.</p>
      </div>
    `;
    
    try {
        const res = await fetch('/api/arac-kutusu/havuz/save', { method: 'POST', body: formData });
        if(!res.ok) throw new Error("Kaydetme başarısız!");
        
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename.split('.')[0] + "_Duzenlenmis." + format;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        
        window.akBackToHavuzList();
    } catch(err) {
        alert(err.message);
    } finally {
        setTimeout(() => { document.getElementById("ak-havuz-editor-area").innerHTML = origHtml; }, 100);
    }
};
