import fitz, os, re, pandas as pd

# 1. Read Master Data
master_path = r'C:\Users\ozan.gemici\Downloads\mastergtip (17).xls'
df_master = pd.read_html(master_path)[0]

master_dict = {}
for idx, row in df_master.iterrows():
    raw_code = str(row.iloc[8])
    code = re.sub(r'[^\w]', '', raw_code).strip()
    if code.isdigit():
        master_dict[code] = {
            'desc': row.iloc[6],
            'gtip': row.iloc[10],
            'status': row.iloc[13] if len(row) > 13 else 'OK'
        }

print('Total unique CMMFs in Master:', len(master_dict))

base_dir = r'C:\Users\ozan.gemici\OneDrive - DOGRUER GUMRUK MUSAVIRLIGI A.Ş\Belgeler\HANKOOK_ONCELIKLI_DOSYALAR\SINGAPUR_SEVKIYATLARI'
f1_ci = os.path.join(base_dir, '1_PO_4200829207_INV_3100262515_MSC_ZOE', 'SG CI # 3100262515 (TRY).pdf')
f1_pl = os.path.join(base_dir, '1_PO_4200829207_INV_3100262515_MSC_ZOE', 'SG PL # 3100262515 (TRY).pdf')

f2_ci = os.path.join(base_dir, '2_PO_4200831766_INV_3100262594_MISSOURI_EXPRESS', 'SG CI # 3100262594 (TRY).pdf')
f2_pl = os.path.join(base_dir, '2_PO_4200831766_INV_3100262594_MISSOURI_EXPRESS', 'SG PL # 3100262594 (TRY).pdf')

def parse_items(ci_path, pl_path):
    doc_ci = fitz.open(ci_path)
    text_ci = '\n'.join([p.get_text() for p in doc_ci])
    doc_pl = fitz.open(pl_path)
    text_pl = '\n'.join([p.get_text() for p in doc_pl])
    
    items = []
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
    
    pl_pattern = re.compile(r'(\d{7})\s+([0-9/R.,\-+A-Za-z]+)\s+(\d+)\s+EA\s+([0-9,.]+)\s+KG\s+([0-9,.]+)\s+KG')
    for m in pl_pattern.finditer(text_pl):
        cmmf, desc, qty, net_w, gross_w = m.groups()
        for it in items:
            if it['cmmf'] == cmmf and it['net_wt'] == 0.0:
                it['net_wt'] = float(net_w.replace(',', ''))
                it['gross_wt'] = float(gross_w.replace(',', ''))
                break
                
    return items

items1 = parse_items(f1_ci, f1_pl)
items2 = parse_items(f2_ci, f2_pl)

print('\n=== SHIPMENT 1 (3100262515 / PO: 4200829207) ===')
print('Items count:', len(items1))
for it in items1:
    in_m = it['cmmf'] in master_dict
    gtip = master_dict[it['cmmf']]['gtip'] if in_m else 'YOK'
    st = 'MEVCUT' if in_m else 'EKSIK'
    print(f"{it['cmmf']} | {it['desc'][:30]:30} | {it['qty']:3} EA | {it['total_price']:12.2f} TRY | {it['gross_wt']:10.3f} KG | {st:7} | GTIP: {gtip}")

print('\n=== SHIPMENT 2 (3100262594 / PO: 4200831766) ===')
print('Items count:', len(items2))
for it in items2:
    in_m = it['cmmf'] in master_dict
    gtip = master_dict[it['cmmf']]['gtip'] if in_m else 'YOK'
    st = 'MEVCUT' if in_m else 'EKSIK'
    print(f"{it['cmmf']} | {it['desc'][:30]:30} | {it['qty']:3} EA | {it['total_price']:12.2f} TRY | {it['gross_wt']:10.3f} KG | {st:7} | GTIP: {gtip}")
