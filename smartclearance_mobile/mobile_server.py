# -*- coding: utf-8 -*-
"""
smartclearance_mobile.mobile_server
Kurumsal Mobil API & Web Sunucusu (FastAPI + Uvicorn)
Doğruer Gümrük Müşavirliği A.Ş. & Hankook Lastikleri A.Ş.
"""

import os
import sys
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

# Modül yollarını dahil et
_current_dir = os.path.dirname(os.path.abspath(__file__))
_root_dir = os.path.abspath(os.path.join(_current_dir, ".."))
if _root_dir not in sys.path:
    sys.path.insert(0, _root_dir)
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

from api_routes import router as api_router

app = FastAPI(
    title="SmartClearance Mobile Platform",
    description="Apple/Vercel Standartlarında Kurumsal Mobil Kokpit (TMA & PWA)",
    version="5.0.0-PRO"
)

# CORS ayarları (Tüm mobil cihazlar ve webviews için açık)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Uç Noktalarını Bağla
app.include_router(api_router)

# Statik Dosyalar (HTML, CSS, JS, Manifest)
STATIC_DIR = os.path.join(_current_dir, "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
async def serve_mobile_home():
    """Mobil ana sayfasını (PWA / TMA) döner."""
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"error": "Mobil arayüz bulunamadı", "path": index_file}

@app.get("/manifest.json")
async def serve_manifest():
    """PWA Manifest dosyasını döner."""
    manifest_file = os.path.join(STATIC_DIR, "manifest.json")
    if os.path.exists(manifest_file):
        return FileResponse(manifest_file, media_type="application/manifest+json")
    return {"error": "Manifest bulunamadı"}

def start_mobile_server(host="0.0.0.0", port=8888):
    """Mobil sunucuyu başlatır."""
    print(f"=====================================================================")
    print(f" 📱 SmartClearance Mobile Server (Apple/Vercel Obsidian TMA & PWA)")
    print(f" Yerel Erişim (PC) : http://localhost:{port}")
    print(f" Ağ Erişimi (Mobil): http://{host}:{port}")
    print(f"=====================================================================")
    uvicorn.run(app, host=host, port=port, log_level="warning")

if __name__ == "__main__":
    start_mobile_server()
