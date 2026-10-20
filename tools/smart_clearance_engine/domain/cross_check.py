# -*- coding: utf-8 -*-
"""
cross_check.py — Bir evrak setinin (PL + Invoice + Waybill) kendi icinde
ve birbiriyle tutarli olup olmadigini kontrol eder.
"""

TOL = 0.05


def _close(a, b, tol=TOL):
    if a is None or b is None:
        return None
    return abs(a - b) <= tol


def check_evrak_seti(evrak):
    """Donen: (warnings, infos) — ikisi de string listesi."""
    warnings, infos = [], []
    pl, inv, wb = evrak.packing_list, evrak.invoice, evrak.waybill

    _check_invoice_no_consistency(pl, inv, wb, warnings)
    _check_pl_internal(pl, warnings)
    _check_pl_vs_invoice(pl, inv, warnings, infos)
    _check_pl_vs_waybill(pl, inv, wb, warnings, infos)
    _check_presence(pl, inv, wb, warnings, infos)

    return warnings, infos


def _check_invoice_no_consistency(pl, inv, wb, warnings):
    nos = {"PL": pl.invoice_no if pl else None,
           "INV": inv.invoice_no if inv else None,
           "WB": wb.invoice_ref if wb else None}
    present = {k: v for k, v in nos.items() if v}
    if len(set(present.values())) > 1:
        warnings.append(f"Fatura numarasi belgeler arasinda TUTARSIZ: {present}")


def _check_pl_internal(pl, warnings):
    if not (pl and pl.items):
        return
    qty_sum = sum(it.quantity or 0 for it in pl.items)
    net_sum = sum(it.net_weight or 0 for it in pl.items)
    if pl.sub_total_qty is not None and not _close(qty_sum, pl.sub_total_qty, 0.5):
        warnings.append(
            f"Packing List: kalem miktarlari toplami ({qty_sum}) alt toplamla "
            f"({pl.sub_total_qty}) UYUSMUYOR."
        )
    if pl.sub_total_net is not None and not _close(net_sum, pl.sub_total_net, 0.5):
        warnings.append(
            f"Packing List: kalem net agirlik toplami ({net_sum}) alt toplamla "
            f"({pl.sub_total_net}) UYUSMUYOR."
        )


def _check_pl_vs_invoice(pl, inv, warnings, infos):
    if not (pl and inv):
        return
    if pl.sub_total_qty is not None and inv.sub_total_qty is not None:
        if not _close(pl.sub_total_qty, inv.sub_total_qty, 0.5):
            warnings.append(
                f"Packing List miktari ({pl.sub_total_qty}) ile Fatura miktari "
                f"({inv.sub_total_qty}) UYUSMUYOR."
            )
        else:
            infos.append(f"Miktar OK: PL={pl.sub_total_qty} EA = Fatura={inv.sub_total_qty} EA")

    if not (pl.items and inv.items):
        return
    pl_codes = {it.code: it.quantity for it in pl.items}
    inv_codes = {it.code: it.quantity for it in inv.items}
    only_pl = set(pl_codes) - set(inv_codes)
    only_inv = set(inv_codes) - set(pl_codes)
    if only_pl:
        warnings.append(f"Sadece Packing List'te olan kalem kodlari: {sorted(only_pl)}")
    if only_inv:
        warnings.append(f"Sadece Faturada olan kalem kodlari: {sorted(only_inv)}")
    for code in set(pl_codes) & set(inv_codes):
        if pl_codes[code] and inv_codes[code] and not _close(pl_codes[code], inv_codes[code], 0.01):
            warnings.append(f"Kalem {code}: PL miktari {pl_codes[code]} != Fatura miktari {inv_codes[code]}")


def _check_pl_vs_waybill(pl, inv, wb, warnings, infos):
    if not wb:
        return
    ref_qty = (pl.sub_total_qty if pl else None) or (inv.sub_total_qty if inv else None)
    if ref_qty is not None and wb.package_count is not None:
        if not _close(ref_qty, wb.package_count, 0.5):
            warnings.append(
                f"Konsimentodaki paket adedi ({wb.package_count}) fatura/packing list "
                f"miktariyla ({ref_qty}) UYUSMUYOR."
            )
        else:
            infos.append(f"Paket adedi OK: {wb.package_count} (konsimento = PL/Fatura)")

    ref_gross = pl.sub_total_gross if pl else None
    if ref_gross is not None and wb.gross_weight is not None:
        if not _close(ref_gross, wb.gross_weight, 1.0):
            warnings.append(
                f"Konsimento brut agirligi ({wb.gross_weight} KG) packing list brut "
                f"agirligiyla ({ref_gross} KG) UYUSMUYOR."
            )
        else:
            infos.append(f"Brut agirlik OK: {wb.gross_weight} KG (konsimento = PL)")


def _check_presence(pl, inv, wb, warnings, infos):
    if not pl:
        warnings.append("Bu dosyada Packing List bulunamadi/okunamadi.")
    if not inv:
        warnings.append("Bu dosyada Commercial Invoice bulunamadi/okunamadi.")
    if not wb:
        pl_inv_ok = (pl and inv and pl.sub_total_qty is not None
                     and inv.sub_total_qty is not None
                     and _close(pl.sub_total_qty, inv.sub_total_qty, 0.5))
        if pl_inv_ok:
            infos.append("Bu sevkiyatta konsimento/waybill yok (kara/RoRo tasima olabilir); "
                          "Packing List ve Fatura miktarlari birbiriyle dogrulandi.")
        else:
            warnings.append("Bu dosyada konsimento/waybill bulunamadi.")
    elif wb.template == "UNKNOWN":
        warnings.append("Konsimento sablonu TANINMADI — alanlar eksik/yanlis cikmis olabilir.")
