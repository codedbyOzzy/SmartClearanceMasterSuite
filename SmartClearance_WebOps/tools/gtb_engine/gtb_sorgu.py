# -*- coding: utf-8 -*-
"""
tools/gtb_engine/gtb_sorgu.py
Ticaret Bakanlığı (GTB) Beyanname Sorgulama & Otonom Aritmetik Güvenlik Kodu Çözücü Motoru v2.5 (Yüksek Hızlı & Optimize)
Firma: Doğruer Gümrük Müşavirliği A.Ş.
"""

import urllib.request
import urllib.parse
import re
import base64
import io
import time
import datetime
from typing import Dict, Optional, Tuple
from tools.gtb_engine.gtb_http import gtb_urlopen

try:
    from PIL import Image, ImageOps
except ImportError:
    Image = None
    ImageOps = None

try:
    import ddddocr
    _GLOBAL_OCR = ddddocr.DdddOcr(show_ad=False)
except Exception:
    _GLOBAL_OCR = None

GTB_URL = "https://uygulama.gtb.gov.tr/BeyannameSorgulama/"
GTB_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def gtb_sayfa_oturum_al() -> Tuple[Optional[str], Optional[str], Optional[str], Optional[bytes], Optional[str]]:
    """GTB Beyanname Sorgulama sayfasını açarak ASP.NET VIEWSTATE token'larını, session çerezini ve güvenlik kodu resmini çeker."""
    try:
        req = urllib.request.Request(GTB_URL, headers={"User-Agent": GTB_USER_AGENT})
        res = gtb_urlopen(req, timeout=10, retries=3)
        html = res.read().decode("utf-8", "ignore")
        raw_cookies = res.headers.get_all("Set-Cookie") or []
        cookies = "; ".join([c.split(";")[0].strip() for c in raw_cookies if c])
        
        vs_match = re.search(r'id="__VIEWSTATE" value="([^"]+)"', html)
        vsg_match = re.search(r'id="__VIEWSTATEGENERATOR" value="([^"]+)"', html)
        ev_match = re.search(r'id="__EVENTVALIDATION" value="([^"]+)"', html)
        img_match = re.search(r'src="data:image/[^;]+;base64,([^"]+)"', html)
        
        vs = vs_match.group(1) if vs_match else None
        vsg = vsg_match.group(1) if vsg_match else None
        ev = ev_match.group(1) if ev_match else None
        img_bytes = base64.b64decode(img_match.group(1)) if img_match else None
        
        return vs, vsg, ev, img_bytes, cookies
    except Exception as e:
        return None, None, None, None, None


def _clean_image_for_ocr(img, border: int = 20):
    """GTB güvenlik kodu resmindeki 1px gürültü halkalarını temizler ve marj ekler."""
    if not img or not Image:
        return img
    threshold = 150
    cleaned = None
    try:
        import numpy as np
        arr = np.array(img.convert("L"), dtype=np.uint8)
        dark = arr < threshold
        padded = np.pad(dark.astype(np.uint8), 1, mode="constant")
        neighbors = (
            padded[0:-2, 0:-2] + padded[0:-2, 1:-1] + padded[0:-2, 2:]
            + padded[1:-1, 0:-2] + padded[1:-1, 2:]
            + padded[2:, 0:-2] + padded[2:, 1:-1] + padded[2:, 2:]
        )
        keep = dark & (neighbors >= 3)
        cleaned_arr = np.where(keep, 0, 255).astype(np.uint8)
        cleaned = Image.fromarray(cleaned_arr, mode="L")
    except Exception:
        w, h = img.size
        cleaned = Image.new("L", (w, h), 255)
        for x in range(1, w - 1):
            for y in range(1, h - 1):
                if img.getpixel((x, y)) < threshold:
                    neighbors = sum(
                        1 for dx in [-1, 0, 1] for dy in [-1, 0, 1]
                        if (dx != 0 or dy != 0) and img.getpixel((x + dx, y + dy)) < threshold
                    )
                    if neighbors >= 3:
                        cleaned.putpixel((x, y), 0)
    if border > 0 and ImageOps:
        cleaned = ImageOps.expand(cleaned, border=border, fill=255)
    return cleaned


def _normalize_gtb_ocr_text(raw: str) -> str:
    """OCR modelinden gelen karakterleri sayılara/sembollere dönüştürür."""
    text = raw.replace("一", "1").replace("二", "2").replace("四", "4").replace("五", "5").replace("六", "6").replace("七", "7").replace("八", "8").replace("九", "9")
    text = text.replace("i", "1").replace("l", "1").replace("I", "1")
    text = text.replace("o", "0").replace("O", "0")
    text = text.replace("s", "5").replace("S", "5")
    text = text.replace("z", "2").replace("Z", "2")
    text = text.replace("q", "9").replace("Q", "9")
    text = text.replace("十", "+").replace("了", "7").replace(">", "7")
    return text


def _solve_gtb_math_captcha(img_bytes: bytes) -> Optional[str]:
    """GTB Güvenlik Kodu resmindeki (2-haneli sayı) + (1-haneli sayı) denklemini çözer."""
    try:
        if not img_bytes or not _GLOBAL_OCR:
            return None
        
        # 1. Hızlı Doğrudan OCR (40 ms)
        raw_text = _GLOBAL_OCR.classification(img_bytes)
        text = _normalize_gtb_ocr_text(raw_text)
        m = re.search(r"(\d{2})\s*[+xXtT]\s*(\d{1})", text)
        if m:
            n1, n2 = int(m.group(1)), int(m.group(2))
            if 10 <= n1 <= 99 and 0 <= n2 <= 9:
                return str(n1 + n2)

        m_loose = re.search(r"(\d{2})[^\d]*(\d{1})", text)
        if m_loose:
            n1, n2 = int(m_loose.group(1)), int(m_loose.group(2))
            if 10 <= n1 <= 99 and 0 <= n2 <= 9:
                return str(n1 + n2)

        # 2. İkinci Aşama: Görüntü filtreleme ve marj ile kurtarma
        if Image:
            img = Image.open(io.BytesIO(img_bytes)).convert("L")
            variants = [
                _clean_image_for_ocr(img, border=2),
                ImageOps.expand(img, border=2, fill=255) if ImageOps else img
            ]
            for v in variants:
                b = io.BytesIO()
                v.save(b, format="PNG")
                raw_text = _GLOBAL_OCR.classification(b.getvalue())
                text = _normalize_gtb_ocr_text(raw_text)
                m = re.search(r"(\d{2})\s*[+xXtT]\s*(\d{1})", text) or re.search(r"(\d{2})[^\d]*(\d{1})", text)
                if m:
                    n1, n2 = int(m.group(1)), int(m.group(2))
                    if 10 <= n1 <= 99 and 0 <= n2 <= 9:
                        return str(n1 + n2)
                    
        return None
    except Exception as e:
        return None


def gtb_beyanname_sorgula(beyanname_no: str, dogrulama_kodu: Optional[str] = None) -> Dict:
    """
    Belirtilen Beyanname numarasını GTB sisteminden sorgular ve sonucu döndürür.
    Başarısız güvenlik kodlarında 6 defaya kadar otomatik dener.
    """
    beyanname_no = (beyanname_no or "").strip().upper()
    clean_no = re.sub(r"[^A-Z0-9]", "", beyanname_no)
    if not clean_no or clean_no.startswith("BEYAN") or len(clean_no) < 15:
        return {"success": False, "error": "Geçersiz beyanname numarası formatı (16 haneli olmalı)."}
        
    for attempt in range(1, 7):
        if attempt > 1:
            time.sleep(0.15)
            
        vs, vsg, ev, img_bytes, cookies = gtb_sayfa_oturum_al()
        if not vs:
            if attempt == 6:
                return {"success": False, "error": "GTB Bakanlık sunucusuna bağlanılamadı."}
            continue
            
        cozulmus_kod = dogrulama_kodu or _solve_gtb_math_captcha(img_bytes)
        if not cozulmus_kod:
            continue
            
        data = urllib.parse.urlencode({
            "__VIEWSTATE": vs,
            "__VIEWSTATEGENERATOR": vsg or "",
            "__EVENTVALIDATION": ev or "",
            "Sorgu": "rdBeyanname",
            "txtBeyannameNo": clean_no,
            "txtDogrulamaKodu": cozulmus_kod,
            "btnSorgula": "Sorgula"
        }).encode("utf-8")
        
        try:
            headers = {
                "User-Agent": GTB_USER_AGENT,
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": GTB_URL
            }
            if cookies:
                headers["Cookie"] = cookies
                
            req = urllib.request.Request(GTB_URL, data=data, headers=headers)
            res = gtb_urlopen(req, timeout=10, retries=3)
            html = res.read().decode("utf-8", "ignore")
            
            durum_m = re.search(r'id="lblBeyannameDurum"[^>]*>([^<]+)', html)
            detay_text = durum_m.group(1).strip() if durum_m else None
            
            if any(k in html for k in ["Güvenlik Kodu Hatalı", "Güvenlik Kodu Hatal", "GÜVENLİK KODU YANLIŞ", "GÜVENLİK KODU YANLI", "KODU YANLI", "Kodu Yanlış"]):
                continue
            elif "Beyannamenin işlemleri tamamlanmıştır" in html or (detay_text and "kapanm" in detay_text.lower()):
                return {
                    "success": True,
                    "durum": detay_text or "[TAMAMLANDI] Beyanname işlemleri tamamlanmıştır (Kapanmış).",
                    "beyanname_no": clean_no,
                    "kapandi": True,
                    "islemde": False,
                    "timestamp": datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
                }
            elif "Beyanname işlemdedir" in html or (detay_text and "işlemde" in detay_text.lower()):
                return {
                    "success": True,
                    "durum": detay_text or "[İŞLEMDE] Beyanname işlemdedir.",
                    "beyanname_no": clean_no,
                    "kapandi": False,
                    "islemde": True,
                    "timestamp": datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
                }
            elif detay_text and len(detay_text) > 3:
                is_kap = "kapan" in detay_text.lower() or "tamamlan" in detay_text.lower()
                return {
                    "success": True,
                    "durum": detay_text,
                    "beyanname_no": clean_no,
                    "kapandi": is_kap,
                    "islemde": not is_kap,
                    "timestamp": datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
                }
            else:
                continue
        except Exception as e:
            if attempt == 6:
                return {"success": False, "error": f"Sorgulama hatası: {e}"}
                
    return {
        "success": False,
        "error": "Güvenlik kodu 6 denemede de çözülemedi veya sayfa yanıt vermedi.",
        "beyanname_no": clean_no
    }
