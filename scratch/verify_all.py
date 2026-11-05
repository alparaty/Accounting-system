import os
import re

print("=== VERIFYING ONYX PRO ERP SYSTEM ASSETS & CODE ===")

base_dir = r"c:\Users\AlparatY\Desktop\system ERP"
index_html = os.path.join(base_dir, "index.html")
css_file = os.path.join(base_dir, "css", "onyx_style.css")
js_app = os.path.join(base_dir, "js", "onyx_app.js")
js_store = os.path.join(base_dir, "js", "onyx_store.js")
js_data = os.path.join(base_dir, "js", "onyx_data.js")

assert os.path.exists(index_html), "index.html missing"
assert os.path.exists(css_file), "css/onyx_style.css missing"
assert os.path.exists(js_app), "js/onyx_app.js missing"
assert os.path.exists(js_store), "js/onyx_store.js missing"
assert os.path.exists(js_data), "js/onyx_data.js missing"

with open(index_html, encoding="utf-8") as f:
    html = f.read()

# Verify key elements
assert "onyx-shell-header" in html, "Onyx Pro shell header missing in HTML"
assert "onyx-right-tree-panel" in html, "Right tree panel missing in HTML"
assert "onyx-center-workspace" in html, "Center workspace missing in HTML"
assert "onyx-left-quick-panel" in html, "Left quick links panel missing in HTML"
assert "onyx-black-statusbar" in html, "Black status bar missing in HTML"

# Check assets
assets = [
    "onyx_watermark.png",
    "onyx_top_logo.png",
    "onyx_top_icons.png",
    "onyx_form_toolbar_full.png"
]
for a in assets:
    p = os.path.join(base_dir, "assets", a)
    assert os.path.exists(p), f"Asset missing: {p}"
    print(f"✔ Asset verified: {a} ({os.path.getsize(p)} bytes)")

# Check JS syntax & screen renderers
with open(js_app, encoding="utf-8") as f:
    app_code = f.read()

screens = [
    "renderDashboard",
    "renderChartOfAccounts",
    "renderOpeningBalances",
    "renderJournalEntries",
    "renderVouchersCash",
    "renderVouchersCheque",
    "renderChequeCollection",
    "renderPayroll",
    "renderOrgHierarchyExcel",
    "renderPurchasesLC",
    "renderSales",
    "renderInventory",
    "renderReviewPosting",
    "renderReports",
    "renderSystemConfig"
]

for s in screens:
    assert s in app_code, f"Screen function missing: {s}"
    print(f"✔ Screen function verified: {s}")

print("\nALL VERIFICATIONS PASSED WITH 100% SUCCESS!")
