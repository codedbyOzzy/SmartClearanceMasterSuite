import os, fitz, cv2, numpy as np, re
from rapidocr_onnxruntime import RapidOCR

ocr = RapidOCR()

pdf_path = r"C:\Users\ozan.gemici\Downloads\HANKOOK_GELEN_TARAMALAR\SKM_301i26091415471.pdf"
doc = fitz.open(pdf_path)

print(f"File: {os.path.basename(pdf_path)}, Total pages: {len(doc)}", flush=True)

for pno in [3, 4, 5, 6]:
    page = doc[pno]
    pix = page.get_pixmap(dpi=150)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
    if pix.n == 4: img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)
    elif pix.n == 1: img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
    res, _ = ocr(img)
    print(f"\n================ PAGE {pno+1} ================", flush=True)
    if not res:
        print("No text detected", flush=True)
        continue
    boxes = []
    for box, text, score in res:
        y = (box[0][1] + box[2][1]) / 2.0
        x = (box[0][0] + box[1][0]) / 2.0
        boxes.append({'text': text.strip(), 'x': x, 'y': y, 'score': score})
    boxes.sort(key=lambda b: (b['y'], b['x']))
    for b in boxes:
        print(f"y={b['y']:6.1f}, x={b['x']:6.1f} : {b['text']}", flush=True)
