# -*- coding: utf-8 -*-
"""Tek bir PDF'i uctan uca isleyip EvrakSeti dondurur."""
from tools.smart_clearance_engine.domain.models import EvrakSeti
from tools.smart_clearance_engine.parsers.common import load_pages, split_documents
from tools.smart_clearance_engine.parsers.packing_list import parse_packing_list
from tools.smart_clearance_engine.parsers.invoice import parse_invoice
from tools.smart_clearance_engine.parsers.waybill import parse_waybill


def process_pdf(pdf_path) -> EvrakSeti:
    pages = load_pages(pdf_path)
    groups = split_documents(pages)
    result = EvrakSeti(source_pdf=str(pdf_path))
    if "PACKING_LIST" in groups:
        result.packing_list = parse_packing_list(groups["PACKING_LIST"])
    if "INVOICE" in groups:
        result.invoice = parse_invoice(groups["INVOICE"])
    if "WAYBILL" in groups:
        result.waybill = parse_waybill(groups["WAYBILL"])
    return result
