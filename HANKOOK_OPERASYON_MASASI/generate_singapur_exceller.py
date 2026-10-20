import openpyxl, os, datetime, re, fitz, shutil
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

base_dir = r'C:\Users\ozan.gemici\OneDrive - DOGRUER GUMRUK MUSAVIRLIGI A.Ş\Belgeler\HANKOOK_ONCELIKLI_DOSYALAR\SINGAPUR_SEVKIYATLARI'
sablon_path = r'c:\Users\ozan.gemici\OneDrive - DOGRUER GUMRUK MUSAVIRLIGI A.Ş\Belgeler\V1SmartClearance_Gumruk\SmartClearance_Gumruk\SmartClearance_Gumruk\data\sablon.xlsx'

# 1. Parse items function
def get_shipment_items(ci_path, pl_path):
    doc_ci = fitz.open(ci_path)
    text_ci = '\n'.join([p.get_text() for p in doc_ci])
    doc_pl = fitz.open(pl_path)
    text_pl = '\n'.join([p.get_text() for p in doc_pl])
    
    items = []
    # Pattern: 3002802 295/80R22.5,16,AH31+,L,B,-,HK 48 EA TRY 14,365.94 TRY 689,565.12 KR
    pattern = re.compile(r'(\d{7})\s+([0-9/R.,\-+A-Za-z]+)\s+(\d+)\s+EA\s+TRY\s+([0-9,.]+)\s+TRY\s+([0-9,.]+)\s+([A-Z]{2})')
    for m in pattern.finditer(text_ci):
        cmmf, desc, qty, u_price, total_price, origin = m.groups()
        items.append({
            'cmmf': cmmf,
            'desc': desc,
            'qty': int(qty),
            'unit_price': float(u_price.replace(',', '')),
            'total_price': float(total_price.replace(',', '')),
            'origin': origin,
            'gross_wt': 0.0,
            'net_wt': 0.0
        })
    
    # Weights from PL
    pl_pattern = re.compile(r'(\d{7})\s+([0-9/R.,\-+A-Za-z]+)\s+(\d+)\s+EA\s+([0-9,.]+)\s+KG\s+([0-9,.]+)\s+KG')
    for m in pl_pattern.finditer(text_pl):
        cmmf, desc, qty, net_w, gross_w = m.groups()
        for it in items:
            if it['cmmf'] == cmmf and it['net_wt'] == 0.0:
                it['net_wt'] = float(net_w.replace(',', ''))
                it['gross_wt'] = float(gross_w.replace(',', ''))
                break
                
    return items

f1_ci = os.path.join(base_dir, '1_PO_4200829207_INV_3100262515_MSC_ZOE', 'SG CI # 3100262515 (TRY).pdf')
f1_pl = os.path.join(base_dir, '1_PO_4200829207_INV_3100262515_MSC_ZOE', 'SG PL # 3100262515 (TRY).pdf')
items1 = get_shipment_items(f1_ci, f1_pl)

f2_ci = os.path.join(base_dir, '2_PO_4200831766_INV_3100262594_MISSOURI_EXPRESS', 'SG CI # 3100262594 (TRY).pdf')
f2_pl = os.path.join(base_dir, '2_PO_4200831766_INV_3100262594_MISSOURI_EXPRESS', 'SG PL # 3100262594 (TRY).pdf')
items2 = get_shipment_items(f2_ci, f2_pl)

print(f'Items in Shipment 1: {len(items1)}, Total Qty: {sum(x["qty"] for x in items1)}, Total Amount: {sum(x["total_price"] for x in items1):.2f}, Total Wt: {sum(x["gross_wt"] for x in items1):.3f}')
print(f'Items in Shipment 2: {len(items2)}, Total Qty: {sum(x["qty"] for x in items2)}, Total Amount: {sum(x["total_price"] for x in items2):.2f}, Total Wt: {sum(x["gross_wt"] for x in items2):.3f}')

# 2. Excel production function
def build_aktarim_excel(items, inv_no, inv_date_dt, po_no, output_path):
    wb = openpyxl.load_workbook(sablon_path)
    ws = wb.active
    
    # Fill from row 2
    for idx, it in enumerate(items, start=2):
        ws[f'F{idx}'] = it['qty']
        ws[f'G{idx}'] = 'AD'
        
        c_i = ws[f'I{idx}']
        c_i.value = str(it['cmmf'])
        c_i.number_format = '@'
        
        c_k = ws[f'K{idx}']
        c_k.value = float(it['total_price'])
        c_k.number_format = '0.00'
        
        ws[f'L{idx}'] = 'TRY'
        ws[f'M{idx}'] = '728'  # Evrim Korea country code
        
        c_n = ws[f'N{idx}']
        c_n.value = float(it['gross_wt'])
        c_n.number_format = '0.000'
        
        c_o = ws[f'O{idx}']
        c_o.value = float(it['net_wt'])
        c_o.number_format = '0.000'
        
        c_p = ws[f'P{idx}']
        c_p.value = str(inv_no)
        c_p.number_format = '@'
        
        c_q = ws[f'Q{idx}']
        c_q.value = inv_date_dt
        c_q.number_format = 'mm-dd-yy'
        
        ws[f'R{idx}'] = f'{po_no}/HNKRE'
        ws[f'S{idx}'] = 11
        ws[f'T{idx}'] = 'K1'
        ws[f'U{idx}'] = 9
        
        c_x = ws[f'X{idx}']
        c_x.value = '0100'
        c_x.number_format = '@'

    # Set column widths
    for col in ws.columns:
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = 20

    wb.save(output_path)
    print('Generated:', output_path)

# Build Shipment 1
out1 = os.path.join(base_dir, '1_PO_4200829207_INV_3100262515_MSC_ZOE', '3100262515_Aktarim.xlsx')
build_aktarim_excel(items1, '3100262515', datetime.datetime(2026, 8, 31), '4200829207', out1)

# Build Shipment 2
out2 = os.path.join(base_dir, '2_PO_4200831766_INV_3100262594_MISSOURI_EXPRESS', '3100262594_Aktarim.xlsx')
build_aktarim_excel(items2, '3100262594', datetime.datetime(2026, 9, 1), '4200831766', out2)

# Copy to downloads as backup
dl_dir = r'C:\Users\ozan.gemici\Downloads\HANKOOK_SINGAPUR_GELEN'
shutil.copy2(out1, os.path.join(dl_dir, '3100262515_Aktarim.xlsx'))
shutil.copy2(out2, os.path.join(dl_dir, '3100262594_Aktarim.xlsx'))

# 3. Build mastera_eklenecek for Singapore missing item (3003993)
sample_template = r'C:\Users\ozan.gemici\Downloads\mastera_eklenecek.xlsx'
wb_m = openpyxl.load_workbook(sample_template)
ws_m = wb_m.active

# Delete existing rows 3 to 6
ws_m.delete_rows(3, 10)

# Add row 3 for 3003993
row_data = [
    9122,                                       # 1. Firma Evrim No
    413049,                                     # 2. İhracatçı Evrim No (Hankook Tire & Tech)
    '205/65R17.5,18,TH31,L,B,-,HK',             # 3. Yabancı Tanım
    'RADYAL KAMYON LASTİĞİ',                    # 4. Türkçe Tanım
    '3003993',                                  # 5. Ürün Kodu
    None,                                       # 6.
    401120900011,                               # 7. GTİP (Noktasız - Ağır vasıta)
    None,                                       # 8.
    None,                                       # 9.
    'Kore Cumhuriyeti',                         # 10. Menşei
    None,                                       # 11.
    'KORE',                                     # 12. Anlaşma Kodu
    None,                                       # 13.
    'VAR',                                      # 14. İlişki
    'YOK',                                      # 15. Royalti
    'YOK',                                      # 16. DFİF
    'YOK',                                      # 17. Ambargo
    20,                                         # 18. KDV Oran
    None, None, None, None, None, None, None, None, None, None,
    None, None, None, None, None,               # 19-33
    'T',                                        # 34. Tip (İthalat)
    None, None, None                            # 35-37
]

for c_idx, val in enumerate(row_data, start=1):
    ws_m.cell(row=3, column=c_idx, value=val)

out_master = r'C:\Users\ozan.gemici\Downloads\mastera_eklenecek_singapur.xlsx'
wb_m.save(out_master)
print('Generated mastera_eklenecek:', out_master)
