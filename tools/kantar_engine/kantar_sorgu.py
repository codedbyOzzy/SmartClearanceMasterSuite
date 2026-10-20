import json
# -*- coding: utf-8 -*-
"""
kantar_sorgu.py — DP World Körfez & Yarımca Birebir SmartClearance Kantar Scraper Motoru
"""
import http.client
import socket
import ssl
import urllib.parse
import urllib.request
import re
import html as html_lib
import datetime
import calendar
import os
import time
import threading
from typing import Dict, Optional, List, Tuple

KORFEZ_URL = "https://dpwekorfez.dpworld.com.tr/KantarTikesi"
KORFEZ_BASE = "https://dpwekorfez.dpworld.com.tr"
YARIMCA_URL = "https://dpweyarimca.dpworld.com.tr/KantarPublic.aspx"
YARIMCA_BASE = "https://dpweyarimca.dpworld.com.tr"
YILPORT_URL = "https://online.yilport.com/TRGEB/Unit"
YILPORT_TICKET_URL = "https://online.yilport.com/TRGEB/Unit/GetWeightBridgeTicket"
YILPORT_SESSION_FILE = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "SmartClearance", "yilport_session.json")
YILPORT_PDF_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "SmartClearance", "Kantar_Tickets")
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE
_DPW_GATE = threading.Semaphore(2)
_LOG_LOCK = threading.Lock()
_LAST_LOG = {}

try:
    from curl_cffi import requests as _cf_requests
except Exception:
    _cf_requests = None


def _log_throttle(key: str, msg: str, every_sec: float = 45.0):
    now = time.time()
    with _LOG_LOCK:
        last = _LAST_LOG.get(key, 0)
        if now - last < every_sec:
            return
        _LAST_LOG[key] = now
    print(msg)


def _is_reset(exc: Exception) -> bool:
    s = str(exc).lower()
    return any(x in s for x in ("10054", "10053", "10060", "timed out", "reset", "broken pipe", "eof"))


class _HTTPSConnectionIPv4(http.client.HTTPSConnection):
    """Ev ağında IPv6 RST alınca tarayıcı IPv4'e düşer; urllib düşmeyebilir."""

    def connect(self):
        infos = socket.getaddrinfo(self.host, self.port, socket.AF_INET, socket.SOCK_STREAM)
        err = None
        sock = None
        for af, socktype, proto, _canon, sa in infos:
            s = socket.socket(af, socktype, proto)
            s.settimeout(self.timeout)
            try:
                s.connect(sa)
                sock = s
                break
            except OSError as e:
                err = e
                s.close()
        if sock is None:
            raise err or OSError("IPv4 bağlantısı kurulamadı")
        ctx = self._context or _SSL_CTX
        self.sock = ctx.wrap_socket(sock, server_hostname=self.host)


class _IPv4HTTPSHandler(urllib.request.HTTPSHandler):
    def https_open(self, req):
        return self.do_open(lambda host, **kw: _HTTPSConnectionIPv4(host, context=_SSL_CTX, **kw), req)


_IPV4_OPENER = urllib.request.build_opener(_IPv4HTTPSHandler())


def _browser_headers(extra=None):
    hdrs = {
        "User-Agent": _UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Upgrade-Insecure-Requests": "1",
    }
    if extra:
        hdrs.update(extra)
    return hdrs


def _http_read_curl(url: str, data=None, headers=None, timeout=15):
    method = "POST" if data is not None else "GET"
    resp = _cf_requests.request(
        method,
        url,
        data=data,
        headers=headers,
        timeout=timeout,
        impersonate="chrome",
        verify=False,
        allow_redirects=True,
    )
    cookies = ""
    try:
        cookies = "; ".join(f"{k}={v}" for k, v in resp.cookies.items())
    except Exception:
        pass
    if not cookies:
        raw = resp.headers.get("Set-Cookie") or resp.headers.get("set-cookie") or ""
        if raw:
            cookies = "; ".join(p.split(";")[0].strip() for p in str(raw).split(",") if "=" in p)
    return resp.content, cookies


def _http_read_urllib(url: str, data=None, headers=None, timeout=15):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    with _IPV4_OPENER.open(req, timeout=timeout) as res:
        body = res.read()
        cookies = "; ".join([
            c.split(";")[0].strip()
            for c in (res.headers.get_all("Set-Cookie") or []) if c
        ])
        return body, cookies


def _http_read(url: str, data=None, headers=None, timeout=15, retries=4):
    hdrs = _browser_headers(headers)
    last = None
    for attempt in range(1, retries + 1):
        try:
            with _DPW_GATE:
                if _cf_requests is not None:
                    try:
                        return _http_read_curl(url, data=data, headers=hdrs, timeout=timeout)
                    except Exception:
                        pass
                return _http_read_urllib(url, data=data, headers=hdrs, timeout=timeout)
        except Exception as e:
            last = e
            if attempt < retries and _is_reset(e):
                time.sleep(0.8 * attempt)
                continue
            raise
    raise last


# =========================================================================
# 1. KÖRFEZ KANTAR SORGU MOTORU (BİREBİR SMARTCLEARANCE)
# =========================================================================
def _korfez_sayfa_oturum_al():
    try:
        body, cookies = _http_read(KORFEZ_URL, timeout=18)
        html = body.decode("utf-8", "ignore")
        vs  = re.search(r'id="__VIEWSTATE"[^>]+value="([^"]+)"', html)
        vsg = re.search(r'id="__VIEWSTATEGENERATOR"[^>]+value="([^"]+)"', html)
        ev  = re.search(r'id="__EVENTVALIDATION"[^>]+value="([^"]+)"', html)
        return (
            vs.group(1) if vs else None,
            vsg.group(1) if vsg else None,
            ev.group(1) if ev else None,
            cookies,
            html
        )
    except Exception as e:
        _log_throttle("korfez-oturum", f"[KORFEZ-SORGU-HATA] Oturum alınamadı: {e}")
        return None, None, None, None, None


def _parse_korfez_sonuclar(html: str) -> List[Dict]:
    results = []
    rows = re.findall(r'class="dxgvDataRow_Mulberry"[^>]*>(.*?)</tr>', html, re.DOTALL)
    for row_html in rows:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row_html, re.DOTALL)
        def _temiz(s):
            return re.sub(r'<[^>]+>', '', s).replace("&nbsp;", " ").strip()

        pdf_m = re.search(r'href="([^"]*\.pdf)"', cells[0] if cells else "")
        pdf_url = None
        if pdf_m:
            url = pdf_m.group(1)
            if url.startswith("http"):
                pdf_url = url
            else:
                pdf_url = KORFEZ_BASE + ("" if url.startswith("/") else "/") + url

        konteyner  = _temiz(cells[1]) if len(cells) > 1 else ""
        tartim_no  = _temiz(cells[2]) if len(cells) > 2 else ""
        tarih      = _temiz(cells[3]) if len(cells) > 3 else ""
        plaka      = _temiz(cells[4]) if len(cells) > 4 else ""
        firma      = _temiz(cells[5]) if len(cells) > 5 else ""
        dba        = _temiz(cells[9]) if len(cells) > 9 else (_temiz(cells[8]) if len(cells) > 8 else "")

        results.append({
            "tartim_no"   : tartim_no,
            "tarih"       : tarih,
            "firma"       : firma,
            "plaka"       : plaka,
            "konteyner_no": konteyner,
            "agirlik"     : dba,
            "dba"         : dba,
            "pdf_url"     : pdf_url,
            "hazir"       : pdf_url is not None,
            "kaynak"      : "Körfez",
            "durum"       : "🟢 Tartım Hazır" if pdf_url else "⏳ Tartım Bekliyor"
        })
    return results


def sorgula_korfez(konteyner_no: str) -> Dict:
    konteyner_no = (konteyner_no or "").strip().upper()
    if not konteyner_no:
        return {"success": False, "error": "Geçersiz konteyner numarası.", "kaynak": "Körfez"}

    for deneme in range(1, 4):
        vs, vsg, ev, cookies, _ = _korfez_sayfa_oturum_al()
        if not vs:
            time.sleep(0.8 * deneme)
            continue

        bugun = datetime.date.today()
        baslangic_ay = bugun.month - 3
        baslangic_yil = bugun.year
        if baslangic_ay <= 0:
            baslangic_ay += 12
            baslangic_yil -= 1
        try:
            son_gun = calendar.monthrange(baslangic_yil, baslangic_ay)[1]
            gun = min(bugun.day, son_gun)
            baslangic = datetime.date(baslangic_yil, baslangic_ay, gun)
        except Exception:
            baslangic = datetime.date(bugun.year - 1, bugun.month, bugun.day)
        baslangic_str = f"{baslangic.month}/{baslangic.day}/{baslangic.year}"
        bitis_str = f"{bugun.month}/{bugun.day}/{bugun.year}"

        data = (
            f"__VIEWSTATE={urllib.parse.quote(vs)}"
            f"&__VIEWSTATEGENERATOR={urllib.parse.quote(vsg or '')}"
            f"&__EVENTVALIDATION={urllib.parse.quote(ev or '')}"
            f"&ctl00%24MainContent%24ASPxDateEdit1={urllib.parse.quote(baslangic_str)}"
            f"&ctl00%24MainContent%24ASPxDateEdit2={urllib.parse.quote(bitis_str)}"
            f"&MainContent_ASPxComboBox1_VI=0"
            f"&ctl00%24MainContent%24ASPxComboBox1=Do%C4%9Frulanm%C4%B1%C5%9F+Br%C3%BCt+A%C4%9F%C4%B1rl%C4%B1k+(VGM/DBA)"
            f"&ctl00%24MainContent%24sorgumetin={urllib.parse.quote(konteyner_no)}"
            f"&ctl00%24MainContent%24ASPxButton1=Sorgula"
        ).encode("utf-8")

        headers = {
            "User-Agent"   : _UA,
            "Content-Type" : "application/x-www-form-urlencoded",
            "Referer"      : KORFEZ_URL,
        }
        if cookies:
            headers["Cookie"] = cookies
        try:
            body, _ = _http_read(KORFEZ_URL, data=data, headers=headers, timeout=20)
            html = body.decode("utf-8", "ignore")

            if "dxgvDataRow_Mulberry" not in html:
                # Tablo başarıyla yüklendi fakat kayıt yoksa (boş sonuç) boş yere retry yapma
                if "dxgvEmptyDataRow" in html or "dxgvTable" in html or "MainContent" in html:
                    return {"success": True, "hazir": False, "durum": "⏳ Tartım Bekliyor", "konteyner_no": konteyner_no, "kaynak": "Körfez", "tartim_no": "", "tarih": "", "plaka": "", "firma": "", "dba": "", "agirlik": "", "pdf_url": None}
                if deneme < 3:
                    time.sleep(0.5)
                    continue
                return {"success": True, "hazir": False, "durum": "⏳ Tartım Bekliyor", "konteyner_no": konteyner_no, "kaynak": "Körfez", "tartim_no": "", "tarih": "", "plaka": "", "firma": "", "dba": "", "agirlik": "", "pdf_url": None}

            sonuclar = _parse_korfez_sonuclar(html)
            if sonuclar:
                son = sonuclar[0].copy()
                son["success"] = True
                son["konteyner_no"] = konteyner_no
                son["tum_sonuclar"] = sonuclar
                return son
            else:
                return {"success": True, "hazir": False, "durum": "⏳ Tartım Bekliyor", "konteyner_no": konteyner_no, "kaynak": "Körfez"}
        except Exception as e:
            if deneme == 3:
                return {"success": False, "error": f"Körfez sorgu hatası: {e}", "kaynak": "Körfez"}

    return {"success": False, "error": "3 denemede de Körfez'e bağlanılamadı.", "kaynak": "Körfez"}


# =========================================================================
# 2. YARIMCA KANTAR SORGU MOTORU (BİREBİR SMARTCLEARANCE)
# =========================================================================
def _yarimca_sayfa_oturum_al():
    try:
        body, cookies = _http_read(YARIMCA_URL, timeout=18)
        html = body.decode("utf-8", "ignore")
        vs  = re.search(r'id="__VIEWSTATE"[^>]+value="([^"]+)"', html)
        vsg = re.search(r'id="__VIEWSTATEGENERATOR"[^>]+value="([^"]+)"', html)
        ev  = re.search(r'id="__EVENTVALIDATION"[^>]+value="([^"]+)"', html)
        return (
            vs.group(1) if vs else None,
            vsg.group(1) if vsg else None,
            ev.group(1) if ev else None,
            cookies
        )
    except Exception as e:
        _log_throttle("yarimca-oturum", f"[YARIMCA-SORGU-HATA] Oturum alınamadı: {e}")
        return None, None, None, None


def _tarih_guncel_mi(tarih_str: str, max_gun: int = 120) -> bool:
    """Eski seferlere ait (örn. geçen yılki) tartım fişlerinin yeni yüklemelerde
    yanlışlıkla 'Tartım Hazır' olarak algılanmasını önler."""
    if not tarih_str:
        return True
    m = re.search(r'(\d{1,2})[./-](\d{1,2})[./-](\d{4})', str(tarih_str))
    if not m:
        return True
    try:
        g, a, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        dt = datetime.date(y, a, g)
        fark = (datetime.date.today() - dt).days
        return fark <= max_gun
    except Exception:
        return True


def _parse_yarimca_sonuc(html: str) -> Optional[Dict]:
    # 1. Yeni modern kart tasarımı (cnt-card / wt-card)
    for card_m in re.finditer(r'<article[^>]*class=["\'][^"\']*wt-card[^"\']*["\'][^>]*>(.*?)</article>', html, re.DOTALL | re.IGNORECASE):
        card_full = html[card_m.start():card_m.end()]
        card_content = card_m.group(1)

        def get_attr(attr):
            m = re.search(r'data-' + attr + r'=["\']([^"\']*)["\']', card_full, re.IGNORECASE)
            return m.group(1).strip() if m else ""

        oid = get_attr("oid")
        cn = get_attr("cn")
        no = get_attr("no")
        date = get_attr("date")
        plate = get_attr("plate")
        weight = get_attr("weight")

        def get_dd(label_pattern):
            m = re.search(r'<div[^>]*class=["\']cnt-row["\'][^>]*>\s*<dt>' + label_pattern + r'</dt>\s*<dd[^>]*>(.*?)</dd>', card_content, re.IGNORECASE | re.DOTALL)
            if m:
                return re.sub(r'<[^>]+>', '', m.group(1)).replace("&nbsp;", " ").strip()
            return ""

        tartim_no = no or get_dd(r'Tart[ıiİI]m\s*No')
        tarih = date or get_dd(r'Kantar[a-z\s]*')
        if not _tarih_guncel_mi(tarih):
            continue

        firma = get_dd(r'Firma')
        plaka = plate or get_dd(r'Plaka')
        brut = get_dd(r'Br[üuÜU]t\s*a[ğgĞG][ıiİI]rl[ıiİI]k')
        kantar_farki = get_dd(r'Kantar\s*fark[ıiİI]')
        net = weight or get_dd(r'Net\s*Kargo\s*A[ğgĞG][ıiİI]rl[ıiİI][ğgĞG][ıiİI]')

        # PDF URL
        pdf_url = None
        pdf_m = re.search(r'href=["\']([^"\']*KantarPublic\.aspx\?wt=[^"\']*)["\']', card_content, re.IGNORECASE)
        if pdf_m:
            raw_url = html_lib.unescape(pdf_m.group(1)).strip()
            if raw_url.startswith("http"):
                pdf_url = raw_url
            else:
                pdf_url = f"{YARIMCA_BASE}/{raw_url.lstrip('/')}"
        elif oid:
            pdf_url = f"{YARIMCA_URL}?wt={oid}&signed=0&Type=Customer"
        elif tartim_no:
            pdf_url = f"{YARIMCA_URL}?wt={tartim_no}&signed=0&Type=Customer"

        agirlik = brut or kantar_farki or net or ""
        return {
            "tartim_no"   : tartim_no,
            "tarih"       : tarih,
            "firma"       : firma,
            "plaka"       : plaka,
            "konteyner_no": cn,
            "agirlik"     : agirlik,
            "dba"         : agirlik,
            "pdf_url"     : pdf_url,
            "hazir"       : pdf_url is not None,
            "kaynak"      : "Yarımca",
            "durum"       : "🟢 Tartım Hazır" if pdf_url else "⏳ Tartım Bekliyor"
        }

    # 2. Eski DevExpress Grid yapısı (geriye dönük uyumluluk)
    for row_m in re.finditer(r'class="dxgvDataRow_DPWorld"[^>]*>(.*?)</tr>', html, re.DOTALL):
        row_html = row_m.group(1)
        link_m = re.search(r"href=['\"](KantarPublic\.aspx\?wt=(\d+)[^'\"]*)['\"]", row_html)
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row_html, re.DOTALL)
        def _temiz(s):
            return re.sub(r'<[^>]+>', '', s).replace("&nbsp;", " ").strip()

        tartim_no = _temiz(cells[1]) if len(cells) > 1 else ""
        tarih     = _temiz(cells[2]) if len(cells) > 2 else ""
        if not _tarih_guncel_mi(tarih):
            continue

        firma     = _temiz(cells[3]) if len(cells) > 3 else ""
        plaka     = _temiz(cells[4]) if len(cells) > 4 else ""
        konteyner = _temiz(cells[5]) if len(cells) > 5 else ""
        agirlik   = _temiz(cells[6]) if len(cells) > 6 else ""

        pdf_url = None
        if link_m:
            wt = link_m.group(2)
            pdf_url = f"{YARIMCA_URL}?wt={wt}&signed=0&Type=Customer"
        elif tartim_no:
            pdf_url = f"{YARIMCA_URL}?wt={tartim_no}&signed=0&Type=Customer"

        return {
            "tartim_no"   : tartim_no,
            "tarih"       : tarih,
            "firma"       : firma,
            "plaka"       : plaka,
            "konteyner_no": konteyner,
            "agirlik"     : agirlik,
            "dba"         : agirlik,
            "pdf_url"     : pdf_url,
            "hazir"       : pdf_url is not None,
            "kaynak"      : "Yarımca",
            "durum"       : "🟢 Tartım Hazır" if pdf_url else "⏳ Tartım Bekliyor"
        }

    return None


def sorgula_yarimca(konteyner_no: str) -> Dict:
    konteyner_no = (konteyner_no or "").strip().upper()
    if not konteyner_no:
        return {"success": False, "error": "Geçersiz konteyner numarası.", "kaynak": "Yarımca"}

    for deneme in range(1, 4):
        vs, vsg, ev, cookies = _yarimca_sayfa_oturum_al()
        if not vs:
            time.sleep(0.8 * deneme)
            continue

        et = urllib.parse.quote("ctl01$ContentPlaceHolder1$searchbutton")
        data = (
            f"__VIEWSTATE={urllib.parse.quote(vs)}"
            f"&__VIEWSTATEGENERATOR={vsg or ''}"
            f"&__EVENTVALIDATION={urllib.parse.quote(ev or '')}"
            f"&__EVENTTARGET={et}&__EVENTARGUMENT="
            f"&ctl01%24ContentPlaceHolder1%24searchtext={urllib.parse.quote(konteyner_no)}"
        ).encode("utf-8")

        headers = {
            "User-Agent"   : _UA,
            "Content-Type" : "application/x-www-form-urlencoded",
            "Referer"      : YARIMCA_URL,
        }
        if cookies:
            headers["Cookie"] = cookies
        try:
            body, _ = _http_read(YARIMCA_URL, data=data, headers=headers, timeout=20)
            html = body.decode("utf-8", "ignore")

            # 1. Önce kart veya satır sonucu parse etmeyi dene
            sonuc = _parse_yarimca_sonuc(html)
            if sonuc:
                sonuc["success"] = True
                sonuc["konteyner_no"] = sonuc.get("konteyner_no") or konteyner_no
                return sonuc

            # 2. Sayfa başarıyla döndü fakat sonuç bulunamadıysa (boş sonuç)
            if "searchtext" in html or "ContentPlaceHolder1" in html or "dxgvTable" in html:
                return {
                    "success": True,
                    "hazir": False,
                    "durum": "⏳ Tartım Bekliyor",
                    "konteyner_no": konteyner_no,
                    "kaynak": "Yarımca",
                    "tartim_no": "",
                    "tarih": "",
                    "plaka": "",
                    "firma": "",
                    "dba": "",
                    "agirlik": "",
                    "pdf_url": None
                }

            if deneme < 3:
                time.sleep(0.5)
                continue
            return {
                "success": True,
                "hazir": False,
                "durum": "⏳ Tartım Bekliyor",
                "konteyner_no": konteyner_no,
                "kaynak": "Yarımca",
                "tartim_no": "",
                "tarih": "",
                "plaka": "",
                "firma": "",
                "dba": "",
                "agirlik": "",
                "pdf_url": None
            }
        except Exception as e:
            if deneme == 3:
                return {"success": False, "error": f"Yarımca sorgu hatası: {e}", "kaynak": "Yarımca"}

    return {"success": False, "error": "3 denemede de Yarımca'ya bağlanılamadı.", "kaynak": "Yarımca"}


# =========================================================================
# 3. YILPORT KANTAR SORGU MOTORU (BİREBİR SMARTCLEARANCE)
# =========================================================================
def _get_yilport_cookies() -> Dict[str, str]:
    if os.path.exists(YILPORT_SESSION_FILE):
        try:
            with open(YILPORT_SESSION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
    return {"Location": "TR", "Port": "201"}


def _generate_yilport_pdf(ticket_data: Dict, hedef_dosya_yolu: str) -> bool:
    """Yılport kantar fişi verilerini kullanarak resmi A4 tike PDF'i üretir."""
    try:
        try:
            import pymupdf as fitz
        except ImportError:
            import fitz

        doc = fitz.open()
        page = doc.new_page(width=595.3, height=841.9)

        font_file = None
        font_file_bold = None
        for cand, cand_b in [
            (r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\arialbd.ttf"),
            (r"C:\Windows\Fonts\calibri.ttf", r"C:\Windows\Fonts\calibrib.ttf"),
            (r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\segoeuib.ttf"),
        ]:
            if os.path.exists(cand):
                font_file = cand
                font_file_bold = cand_b if os.path.exists(cand_b) else cand
                break

        font_regular = "tr_regular" if font_file else "helv"
        font_bold = "tr_bold" if font_file_bold else "helv"
        if font_file:
            page.insert_font(fontname=font_regular, fontfile=font_file)
        if font_file_bold:
            page.insert_font(fontname=font_bold, fontfile=font_file_bold)

        # Başlık & Üst Bilgi
        page.insert_text(
            fitz.Point(50, 60),
            "YILPORT KONTEYNER TERMİNALİ VE LİMAN İŞLETMECİLİĞİ A.Ş.",
            fontsize=11,
            fontname=font_bold,
            fontfile=font_file_bold,
            color=(0.1, 0.1, 0.1)
        )
        page.insert_text(
            fitz.Point(50, 75),
            "KANTAR TARTIM VE DOĞRULANMIŞ BRÜT AĞIRLIK (DBA/VGM) TİKESİ",
            fontsize=9,
            fontname=font_regular,
            fontfile=font_file,
            color=(0.2, 0.35, 0.6)
        )
        page.draw_line(fitz.Point(50, 95), fitz.Point(545, 95), color=(0.7, 0.7, 0.7), width=1)

        fields = [
            ("TARTIM NO", ticket_data.get("tartim_no") or "—"),
            ("TARİH / SAAT", ticket_data.get("tarih") or "—"),
            ("PLAKA", ticket_data.get("plaka") or "—"),
            ("MÜŞTERİ ADI", ticket_data.get("firma") or "—"),
            ("BEYANNAME NO", ticket_data.get("beyanname_no") or "—"),
            ("KONTEYNER NO", ticket_data.get("konteyner_no") or "—"),
            ("KANTAR MEMURU", ticket_data.get("kantar_memuru") or "YILPORT"),
            ("NET TARTIM (DBA)", f"{ticket_data.get('agirlik') or ticket_data.get('dba') or '—'} KG"),
            ("KONTEYNER DARA", f"{ticket_data.get('dara') or '—'} KG"),
            ("ÜRÜN AĞIRLIĞI", f"{ticket_data.get('net_agirlik') or '—'} KG"),
            ("AÇIKLAMA", ticket_data.get("aciklama") or "—"),
        ]

        y = 125
        row_height = 24
        for i, (label, val) in enumerate(fields):
            if i % 2 == 0:
                page.draw_rect(fitz.Rect(50, y - 16, 545, y + 8), color=None, fill=(0.96, 0.97, 0.99))

            page.insert_text(
                fitz.Point(60, y),
                label,
                fontsize=9,
                fontname=font_bold if any(k in label for k in ["TARTIM NO", "KONTEYNER NO", "NET TARTIM"]) else font_regular,
                fontfile=font_file_bold if any(k in label for k in ["TARTIM NO", "KONTEYNER NO", "NET TARTIM"]) else font_file,
                color=(0.3, 0.3, 0.3)
            )
            page.insert_text(fitz.Point(200, y), ":", fontsize=9, fontname=font_regular, fontfile=font_file, color=(0.4, 0.4, 0.4))

            is_highlight = any(k in label for k in ["TARTIM NO", "KONTEYNER NO", "NET TARTIM"])
            f_use = font_bold if is_highlight else font_regular
            ff_use = font_file_bold if is_highlight else font_file
            c_use = (0.05, 0.2, 0.5) if is_highlight else (0.1, 0.1, 0.1)
            f_size = 10 if is_highlight else 9

            page.insert_text(fitz.Point(220, y), str(val), fontsize=f_size, fontname=f_use, fontfile=ff_use, color=c_use)
            y += row_height

        page.draw_line(fitz.Point(50, y + 10), fitz.Point(545, y + 10), color=(0.85, 0.85, 0.85), width=0.5)

        os.makedirs(os.path.dirname(hedef_dosya_yolu), exist_ok=True)
        doc.save(hedef_dosya_yolu)
        doc.close()
        return os.path.exists(hedef_dosya_yolu)
    except Exception as e:
        _log_throttle("yilport-pdf-gen", f"[YILPORT-PDF-HATA] {e}")
        return False


def _parse_yilport_modal_fields(modal_html: str) -> Dict[str, str]:
    fields = {
        "tartim_no": "",
        "tarih": "",
        "plaka": "",
        "firma": "",
        "beyanname_no": "",
        "konteyner_no": "",
        "kantar_memuru": "YILPORT",
        "agirlik": "",
        "dba": "",
        "dara": "",
        "net_agirlik": "",
        "aciklama": ""
    }
    pattern = r'class=["\']column-1\s*["\']>(.*?)</div>\s*<div\s+class=["\']column-2\s*["\']>(.*?)</div>'
    rows = re.findall(pattern, modal_html, re.DOTALL)
    for c1, c2 in rows:
        label = re.sub(r'<[^>]+>', '', c1).replace(':', '').strip().upper()
        val = html_lib.unescape(re.sub(r'<[^>]+>', '', c2).strip())
        if "TARTIM" in label and "NO" in label:
            fields["tartim_no"] = val
        elif "TAR" in label and ("SAAT" in label or "H" in label):
            fields["tarih"] = val
        elif "PLAKA" in label:
            fields["plaka"] = val
        elif "TER" in label: # MÜŞTERİ ADI
            fields["firma"] = val
        elif "BEYANNAME" in label:
            fields["beyanname_no"] = val
        elif "KONTEYNER" in label and "NO" in label:
            fields["konteyner_no"] = val
        elif "MEMUR" in label:
            fields["kantar_memuru"] = val
        elif "NET" in label and "TARTIM" in label:
            fields["agirlik"] = val
            fields["dba"] = val
        elif "DARA" in label:
            fields["dara"] = val
        elif "AĞIRLIĞ" in label or "AGIRLIG" in label or "RÜN" in label:
            fields["net_agirlik"] = val
        elif "AÇIKLAMA" in label or "ACIKLAMA" in label:
            fields["aciklama"] = val

    return fields


def sorgula_yilport(konteyner_no: str) -> Dict:
    """
    Yılport Online Service (online.yilport.com/TRGEB/Unit) sorgu motoru.
    Konteynerin kantar/weighbridge tikesini çeker, PDF oluşturur ve sonuç döndürür.
    """
    import json as _json
    konteyner_no = (konteyner_no or "").strip().upper()
    if not konteyner_no:
        return {"success": False, "error": "Geçersiz konteyner numarası.", "kaynak": "Yılport"}

    cookies_dict = _get_yilport_cookies()
    cookie_str = "; ".join([f"{k}={v}" for k, v in cookies_dict.items()])

    url = f"{YILPORT_URL}?ExportFile=False&SearchType=UNITNO&SearchQuery={urllib.parse.quote(konteyner_no)}"
    headers = {
        "User-Agent": _UA,
        "Referer": YILPORT_URL,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Cookie": cookie_str
    }

    try:
        body, _ = _http_read(url, headers=headers, timeout=20)
        html = body.decode("utf-8", "ignore")

        # 1. Doğrulama (reCAPTCHA) engeli var mı?
        if "frmVerification" in html or "g-recaptcha" in html:
            _log_throttle("yilport-auth", "[YILPORT] Doğrulama oturumu yenilenmeli (reCAPTCHA aktif).")
            return {
                "success": False,
                "needs_auth": True,
                "hazir": False,
                "durum": "⏳ Yılport Doğrulaması Gerekli",
                "konteyner_no": konteyner_no,
                "kaynak": "Yılport",
                "error": "Yılport oturumu doğrulanmalı. Lütfen 'Yılport Oturumu Aç' butonuna basın."
            }

        # 2. Konteyner kaydı var mı?
        if konteyner_no not in html and "Records Found" not in html:
            return {
                "success": True,
                "hazir": False,
                "durum": "⏳ Tartım Bekliyor",
                "konteyner_no": konteyner_no,
                "kaynak": "Yılport",
                "tartim_no": "",
                "tarih": "",
                "plaka": "",
                "firma": "",
                "dba": "",
                "agirlik": "",
                "pdf_url": None
            }

        # 3. GetWeighBridgeTicket çağrısı veya data-container-id
        gkey = ""
        m_call = re.search(r"GetWeighBridgeTicket\([^,]+,\s*['\"]([^'\"]*)['\"]", html, re.I)
        if m_call:
            gkey = m_call.group(1).strip()
        else:
            m_gkey = re.search(r'data-container-id=["\']([^"\']+)["\']', html)
            if m_gkey:
                gkey = m_gkey.group(1).strip()

        # Eğer konteyner gkey bulunamadıysa
        if not gkey:
            return {
                "success": True,
                "hazir": False,
                "durum": "⏳ Tartım Bekliyor",
                "konteyner_no": konteyner_no,
                "kaynak": "Yılport",
                "tartim_no": "",
                "tarih": "",
                "plaka": "",
                "firma": "",
                "dba": "",
                "agirlik": "",
                "pdf_url": None
            }

        # 4. POST /TRGEB/Unit/GetWeightBridgeTicket
        ajax_headers = {
            "User-Agent": _UA,
            "Content-Type": "application/json; charset=utf-8",
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": url,
            "Cookie": cookie_str
        }
        payload = _json.dumps({"UnitId": konteyner_no, "GKey": gkey}).encode("utf-8")
        b_res, _ = _http_read(YILPORT_TICKET_URL, data=payload, headers=ajax_headers, timeout=20)
        res_json_str = b_res.decode("utf-8", "ignore")

        try:
            res_data = _json.loads(res_json_str)
        except Exception:
            res_data = {}

        if res_data.get("Status") == "OK" and res_data.get("Message"):
            modal_html = res_data.get("Message", "")
            fields = _parse_yilport_modal_fields(modal_html)
            if not fields.get("konteyner_no"):
                fields["konteyner_no"] = konteyner_no

            t_no = fields.get("tartim_no") or "TIKE"
            clean_tno = re.sub(r"[^A-Za-z0-9]", "_", t_no)[:25]
            pdf_path = os.path.join(YILPORT_PDF_DIR, f"Kantar_{konteyner_no}_{clean_tno}.pdf")

            _generate_yilport_pdf(fields, pdf_path)
            agirlik = fields.get("agirlik", "")

            return {
                "success": True,
                "hazir": True,
                "durum": "🟢 Tartım Hazır",
                "konteyner_no": konteyner_no,
                "kaynak": "Yılport",
                "tartim_no": fields.get("tartim_no", ""),
                "tarih": fields.get("tarih", ""),
                "plaka": fields.get("plaka", ""),
                "firma": fields.get("firma", ""),
                "dba": agirlik,
                "agirlik": agirlik,
                "pdf_url": pdf_path,
                "yerel_pdf_yolu": pdf_path
            }
        else:
            return {
                "success": True,
                "hazir": False,
                "durum": "⏳ Tartım Bekliyor",
                "konteyner_no": konteyner_no,
                "kaynak": "Yılport",
                "tartim_no": "",
                "tarih": "",
                "plaka": "",
                "firma": "",
                "dba": "",
                "agirlik": "",
                "pdf_url": None
            }

    except Exception as e:
        _log_throttle("yilport-sorgu", f"[YILPORT-SORGU-HATA] {e}")
        return {"success": False, "error": f"Yılport sorgu hatası: {e}", "kaynak": "Yılport"}


# =========================================================================
# 4. BİRLEŞİK OTONOM KANTAR MOTORU
# =========================================================================
def kantar_otomatik_sorgula(konteyner_no: str, tercih_edilen_kaynak: str = "otomatik") -> Dict:
    """
    Tüm limanları (Yarımca, Körfez/Evyap, Yılport) sırayla sorgular, tartım tikesi hazır olanı döndürür.
    """
    cntr = re.sub(r"[^A-Z0-9]", "", str(konteyner_no or "").upper())
    if not cntr:
        return {"success": False, "error": "Konteyner numarası boş."}

    kaynak = (tercih_edilen_kaynak or "otomatik").lower()

    if kaynak in ("yarımca", "yarimca"):
        return sorgula_yarimca(cntr)
    elif kaynak in ("körfez", "korfez", "evyap"):
        return sorgula_korfez(cntr)
    elif kaynak in ("yılport", "yilport", "gebze", "dilovası", "dilovasi"):
        return sorgula_yilport(cntr)

    # Otomatik Sıralı Arama:
    # 1. DP World Yarımca
    res_y = sorgula_yarimca(cntr)
    if res_y.get("success") and res_y.get("hazir"):
        return res_y

    # 2. DP World Körfez (Evyap)
    res_k = sorgula_korfez(cntr)
    if res_k.get("success") and res_k.get("hazir"):
        return res_k

    # 3. Yılport
    res_yil = sorgula_yilport(cntr)
    if res_yil.get("success") and res_yil.get("hazir"):
        return res_yil

    return {
        "success": True,
        "hazir": False,
        "durum": "⏳ Tartım Bekliyor",
        "konteyner_no": cntr,
        "kaynak": "otomatik",
        "tartim_no": "",
        "tarih": "",
        "plaka": "",
        "firma": "",
        "dba": "",
        "agirlik": "",
        "pdf_url": None
    }


def kantar_pdf_indir(pdf_url: str, hedef_dosya_yolu: str) -> bool:
    if not pdf_url:
        return False

    # Zaten yerel dosya ise ve mevcutsa doğrudan kopyala / onayla
    if os.path.exists(pdf_url) and pdf_url.endswith(".pdf"):
        if os.path.abspath(pdf_url) != os.path.abspath(hedef_dosya_yolu):
            import shutil
            shutil.copyfile(pdf_url, hedef_dosya_yolu)
        return True

    hedef_dir = os.path.dirname(hedef_dosya_yolu)
    if hedef_dir:
        os.makedirs(hedef_dir, exist_ok=True)
    try:
        ref_header = YARIMCA_URL if "yarimca" in pdf_url.lower() else KORFEZ_URL
        body, _ = _http_read(
            pdf_url,
            headers={"Referer": ref_header, "Accept": "application/pdf,*/*"},
            timeout=30,
            retries=4,
        )
        with open(hedef_dosya_yolu, "wb") as out_f:
            out_f.write(body)
        return os.path.exists(hedef_dosya_yolu) and os.path.getsize(hedef_dosya_yolu) > 100
    except Exception as e:
        _log_throttle("pdf-indir", f"[PDF-INDIRME-HATA] {pdf_url} -> {e}")
        return False

    hedef_dir = os.path.dirname(hedef_dosya_yolu)
    if hedef_dir:
        os.makedirs(hedef_dir, exist_ok=True)
    try:
        ref_header = YARIMCA_URL if "yarimca" in pdf_url.lower() else KORFEZ_URL
        body, _ = _http_read(
            pdf_url,
            headers={"Referer": ref_header, "Accept": "application/pdf,*/*"},
            timeout=30,
            retries=4,
        )
        with open(hedef_dosya_yolu, "wb") as out_f:
            out_f.write(body)
        return os.path.exists(hedef_dosya_yolu) and os.path.getsize(hedef_dosya_yolu) > 100
    except Exception as e:
        _log_throttle("pdf-indir", f"[PDF-INDIRME-HATA] {pdf_url} -> {e}")
        return False
