import re
from pathlib import Path
from tools.smart_clearance_engine.domain.models import EvrakSeti


def group_by_invoice(evrak_list):
    """Donen: {invoice_no: EvrakSeti} — her deger, o faturaya ait tum
    dosyalardan birlestirilmis tek bir EvrakSeti'dir.
    """
    groups = {}
    for evrak in evrak_list:
        key = _invoice_key(evrak)
        if key not in groups:
            groups[key] = EvrakSeti(source_pdf=key)
        g = groups[key]
        g.files.append(evrak.source_pdf)
        g.packing_list = g.packing_list or evrak.packing_list
        g.invoice = g.invoice or evrak.invoice
        g.waybill = g.waybill or evrak.waybill
    return groups


def _invoice_key(evrak):
    # Eger PDF dosyasinin adi dogrudan bir fatura/siparis numarasi ise (orn. 3611996685.PDF),
    # her dosya bagimsiz bir cikti grubu olarak islenir ve dosya adindaki numara esas alinir.
    stem = Path(str(evrak.source_pdf or "")).stem
    if re.match(r"^\d{6,12}$", stem):
        if evrak.invoice:
            evrak.invoice.invoice_no = stem
        if evrak.packing_list:
            evrak.packing_list.invoice_no = stem
        if evrak.waybill:
            evrak.waybill.invoice_ref = stem
        return stem

    no = (
        (evrak.packing_list.invoice_no if evrak.packing_list else None)
        or (evrak.invoice.invoice_no if evrak.invoice else None)
        or (evrak.waybill.invoice_ref if evrak.waybill else None)
    )
    return no or f"BILINMEYEN-{evrak.source_pdf}"
