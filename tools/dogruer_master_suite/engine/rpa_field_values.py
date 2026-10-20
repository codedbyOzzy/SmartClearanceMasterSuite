# -*- coding: utf-8 -*-
"""Beyanname robotu: Excel/kuyruk satırından alan; global sabit yalnızca boşsa."""
from typing import Any, Dict, Optional

DEFAULT_SABIT_DEGERLER = {
    "beyan_4000": "4000",
    "giris_gumruk": "18",
    "fatura_bedeli": "1.000,00",
    "banka_bilgisi": "14661",
    "odeme_sekli": "7",
    "odeme_kisa": "71",
    "sinirdaki_25": "10",
    "dahili_26": "10",
    "t19_kntynr": "1",
    "tir_knt_sayisi": "1",
    "teslim_sekli": "CIP",
    "teslim_sehri": "KOCAELİ",
    "tasit_kimligi": "MAERSK EL BOSQUE",
    "tasit_kimligi_2": "MAERSK EL BOSQUE",
    "liman_kutu": "DP",
    "edi_karne": "30",
    "ek_bilgi_metin": "Tareks ve Kons. icin odenen damga vergisi tutari yurt ici diger gidere beyan edildi.",
    "diger_tutar": "3000",
    "diger_aciklama_metin": "Y.ICI",
    "liman_gider_tutar": "5000",
    "liman_gider_aciklama_metin": ".",
}


def _first_filled(src: Dict[str, Any], keys, default=""):
    for k in keys:
        v = src.get(k)
        if v is None:
            continue
        s = str(v).strip()
        if s and s.lower() not in ("none", "-"):
            return s
    return default


def resolve_beyanname_item_values(item: Dict[str, Any], defaults: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    p = dict(DEFAULT_SABIT_DEGERLER)
    if defaults:
        p.update({k: str(v) for k, v in defaults.items() if v is not None and str(v).strip()})
    item = item or {}
    gemi = _first_filled(item, ("gemi", "tasit", "tasit_kimligi"), p.get("tasit_kimligi", ""))
    return {
        "beyan_4000": _first_filled(item, ("beyan_4000",), p["beyan_4000"]),
        "giris_gumruk": _first_filled(item, ("giris_gumruk", "gumruk"), p["giris_gumruk"]),
        "fatura_bedeli": _first_filled(item, ("fatura_bedeli", "vergi"), p["fatura_bedeli"]),
        "banka_bilgisi": _first_filled(item, ("banka_bilgisi",), p["banka_bilgisi"]),
        "odeme_kisa": _first_filled(item, ("odeme_kisa",), p["odeme_kisa"]),
        "sinirdaki_25": _first_filled(item, ("sinirdaki_25",), p["sinirdaki_25"]),
        "dahili_26": _first_filled(item, ("dahili_26",), p["dahili_26"]),
        "t19_kntynr": _first_filled(item, ("t19_kntynr", "konteyner_sayisi"), p["t19_kntynr"]),
        "tir_knt_sayisi": _first_filled(item, ("tir_knt_sayisi",), p["tir_knt_sayisi"]),
        "teslim_sekli": _first_filled(item, ("teslim_sekli",), p["teslim_sekli"]),
        "teslim_sehri": _first_filled(item, ("teslim_sehri", "liman_sehir"), p["teslim_sehri"]),
        "gemi": gemi,
        "liman_kutu": _first_filled(item, ("liman", "liman_kutu"), p["liman_kutu"]),
        "edi_karne": _first_filled(item, ("edi_karne",), p["edi_karne"]),
        "ek_bilgi_metin": _first_filled(item, ("ek_bilgi_metin",), p["ek_bilgi_metin"]),
        "diger_tutar": _first_filled(item, ("diger_tutar",), p["diger_tutar"]),
        "diger_aciklama_metin": _first_filled(item, ("diger_aciklama_metin",), p["diger_aciklama_metin"]),
        "liman_gider_tutar": _first_filled(item, ("liman_gider_tutar",), p["liman_gider_tutar"]),
        "liman_gider_aciklama_metin": _first_filled(item, ("liman_gider_aciklama_metin",), p["liman_gider_aciklama_metin"]),
    }


def queue_item_from_record(item: Dict[str, Any], fallback_gemi: str = "") -> Dict[str, Any]:
    item = item or {}
    gemi = _first_filled(item, ("gemi", "tasit", "tasit_kimligi"), fallback_gemi)
    return {
        "dosya_no": _first_filled(item, ("dosya_no", "dosya")),
        "ref": _first_filled(item, ("ref", "hankook_ref")),
        "beyanname_no": _first_filled(item, ("beyanname_no", "beyan")),
        "gemi": gemi,
        "liman": _first_filled(item, ("liman", "liman_kutu")),
        "fatura_bedeli": _first_filled(item, ("fatura_bedeli", "vergi")),
        "beyan_4000": _first_filled(item, ("beyan_4000",)),
        "diger_tutar": _first_filled(item, ("diger_tutar",)),
        "liman_gider_tutar": _first_filled(item, ("liman_gider_tutar",)),
        "giris_gumruk": _first_filled(item, ("giris_gumruk", "gumruk")),
        "teslim_sehri": _first_filled(item, ("teslim_sehri",)),
        "t19_kntynr": _first_filled(item, ("t19_kntynr", "konteyner_sayisi")),
    }
