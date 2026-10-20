# -*- coding: utf-8 -*-
"""GTB HTTP: timeout / bağlantı kopmasında kısa yeniden deneme."""
from __future__ import annotations

import time
import urllib.error
import urllib.request
import ssl

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE


def gtb_urlopen(req, timeout=10, retries=3, sleep_s=0.4):
    last = None
    attempts = max(1, int(retries))
    for i in range(attempts):
        try:
            return urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX)
        except (TimeoutError, urllib.error.URLError, OSError) as e:
            last = e
            if i + 1 < attempts:
                time.sleep(sleep_s * (i + 1))
    if last:
        raise last
    raise RuntimeError("GTB HTTP isteği başarısız")
