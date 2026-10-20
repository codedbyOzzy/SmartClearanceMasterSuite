# -*- coding: utf-8 -*-
"""Ortak bulut senkron kuralları: tombstone, last-write-wins, zaman damgası."""
from datetime import datetime

TOMBSTONE = "TOMBSTONE"


def is_tombstone(rec) -> bool:
    if not isinstance(rec, dict):
        return False
    for key in ("durum", "gtb_durum"):
        val = str(rec.get(key) or "").strip().upper()
        if val == TOMBSTONE or val.startswith("TOMBSTONE"):
            return True
    return False


def parse_ts(val) -> float:
    s = str(val or "").strip()
    if not s or s in ("—", "-", "None", "null"):
        return 0.0
    raw = s.replace("Z", "+00:00")
    if "T" in raw and raw[:4].isdigit():
        try:
            if "+" in raw[10:]:
                main = raw
            elif raw.endswith("+00:00"):
                main = raw
            else:
                main = raw
            if "." in main:
                left, rest = main.split(".", 1)
                frac = ""
                tz = ""
                for i, ch in enumerate(rest):
                    if ch.isdigit():
                        frac += ch
                    else:
                        tz = rest[i:]
                        break
                frac = (frac + "000000")[:6]
                main = f"{left}.{frac}{tz}"
            return datetime.fromisoformat(main).timestamp()
        except Exception:
            pass
    for fmt in ("%d.%m.%Y %H:%M", "%d.%m.%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[:19], fmt).timestamp()
        except Exception:
            continue
    return 0.0


def remote_is_newer(remote, local_ts_val) -> bool:
    return parse_ts(remote.get("updated_at") if isinstance(remote, dict) else None) >= parse_ts(local_ts_val)


def local_record_ts(rec) -> str:
    if not isinstance(rec, dict):
        return ""
    return rec.get("updated_at") or rec.get("degisim_tarihi") or rec.get("son_kontrol") or rec.get("son_sorgu_zamani") or ""


def utc_now_iso() -> str:
    from datetime import timezone
    return datetime.now(timezone.utc).isoformat()
