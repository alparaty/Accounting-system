import fitz

doc = fitz.open(r"C:\Users\AlparatY\Desktop\Bluetooth\ERPمحاضرات الاونكس برو .pdf")
pos_pages = []
for i, page in enumerate(doc):
    text = page.get_text()
    if any(k in text for k in ['نقطة', 'نقاط', 'الكاشير', 'المبيعات', 'فاتورة المبيعات']):
        pos_pages.append(i + 1)

print(f"Total matching pages: {len(pos_pages)}")
for p in pos_pages[:8]:
    text = doc[p-1].get_text()
    lines = [line.strip() for line in text.split('\n') if any(w in line for w in ['نقطة', 'نقاط', 'الكاشير', 'مبيعات', 'فاتورة', 'عمولة'])]
    if lines:
        print(f"--- Page {p} ---")
        print("\n".join(lines[:6]))
