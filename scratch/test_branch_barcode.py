# -*- coding: utf-8 -*-
"""
اختبار وظيفة مسح الباركود وتحويل الباركود لاسم المنتج عند النقر على Enter في واجهة الفروع
"""

import os
import sys
import json
import time
import socket
import subprocess
import urllib.request

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if not os.path.exists(EDGE_PATH):
    EDGE_PATH = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"

def get_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 0))
    p = s.getsockname()[1]
    s.close()
    return p

def ws_call(port, path, method, params=None, msg_id=1):
    req = {"id": msg_id, "method": method, "params": params or {}}
    import base64
    sock = socket.create_connection(('127.0.0.1', port), timeout=10)
    key = base64.b64encode(os.urandom(16)).decode('ascii')
    handshake = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: 127.0.0.1:{port}\r\n"
        f"Upgrade: websocket\r\n"
        f"Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        f"Sec-WebSocket-Version: 13\r\n\r\n"
    )
    sock.sendall(handshake.encode('utf-8'))
    
    resp = b""
    while b"\r\n\r\n" not in resp:
        chunk = sock.recv(4096)
        if not chunk: break
        resp += chunk
    
    payload = json.dumps(req).encode('utf-8')
    frame = bytearray([0x81])
    length = len(payload)
    if length <= 125:
        frame.append(0x80 | length)
    elif length <= 65535:
        frame.append(0x80 | 126)
        frame.extend(length.to_bytes(2, 'big'))
    else:
        frame.append(0x80 | 127)
        frame.extend(length.to_bytes(8, 'big'))
    mask = os.urandom(4)
    frame.extend(mask)
    masked_payload = bytearray(b ^ mask[i % 4] for i, b in enumerate(payload))
    frame.extend(masked_payload)
    sock.sendall(frame)
    
    raw = sock.recv(65536)
    idx = 2
    b1 = raw[1]
    plen = b1 & 0x7F
    if plen == 126:
        plen = int.from_bytes(raw[2:4], 'big')
        idx = 4
    elif plen == 127:
        plen = int.from_bytes(raw[2:10], 'big')
        idx = 10
    msg_data = raw[idx:idx+plen].decode('utf-8', errors='ignore')
    sock.close()
    return json.loads(msg_data)

def test_barcode():
    print("=" * 65)
    print(">>> اختبار دعم مسح الباركود وتحويله لاسم المنتج في واجهة الفروع <<<")
    print("=" * 65)

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    port = get_free_port()
    user_data = os.path.join(base_dir, "database", ".edge_barcode_profile")

    cmd = [
        EDGE_PATH,
        "--headless=new",
        f"--remote-debugging-port={port}",
        f"--user-data-dir={user_data}",
        "--no-first-run",
        "about:blank"
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)

    try:
        tabs_url = f"http://127.0.0.1:{port}/json"
        with urllib.request.urlopen(tabs_url, timeout=5) as r:
            tabs = json.loads(r.read().decode())
        ws_path = tabs[0]["webSocketDebuggerUrl"].split(f":{port}")[1]

        # 1. تحميل ملفات النظام (onyx_data, onyx_store, onyx_app)
        for fn in ['onyx_data.js', 'onyx_store.js', 'onyx_app.js']:
            with open(os.path.join(base_dir, 'js', fn), encoding='utf-8') as f:
                content = f.read()
                ws_call(port, ws_path, "Runtime.evaluate", {"expression": content}, msg_id=1)

        # 2. تهيئة عناصر واجهة الفروع في الـ DOM
        dom_setup = """
        document.body.innerHTML = `
          <div id="onyx-workspace"></div>
          <div id="onyx-toast-area"></div>
          <div id="alameenInvoiceWindow" style="display:none;">
            <div id="alameenInvoiceContentArea"></div>
          </div>
        `;
        window.showOnyxToast = (msg, icon) => console.log('Toast:', icon, msg);
        """
        ws_call(port, ws_path, "Runtime.evaluate", {"expression": dom_setup}, msg_id=2)

        # 3. فتح نافذة فواتير الفروع
        print("\n1. توليد وفتح نافذة فواتير الفروع...")
        js_open = """
        const profile = store.getInvoiceProfile('prof_credit_purchases') || store.getAllActiveProfiles()[0];
        window.onyxApp.currentBranchProfile = profile;
        const contentArea = document.getElementById('alameenInvoiceContentArea');
        window.onyxApp.renderAlameenInvoiceView(profile, contentArea);
        document.getElementById('alameenInvoiceWindow').style.display = 'block';
        """
        ws_call(port, ws_path, "Runtime.evaluate", {"expression": js_open}, msg_id=3)

        # 4. اختبار إدخال باركود في حقل المادة والنقر على Enter
        print("\n2. محاكاة كتابة الباركود '628100101' في سطر المادة وضغط Enter:")
        js_test_item_enter = """
        (function() {
            const tbody = document.getElementById('alameenActiveInvoiceTbody');
            const row1 = tbody.querySelector('tr[data-row-idx="1"]');
            const itemInput = row1.querySelector('.al-cell-item');
            
            // كتابة الباركود في حقل المادة
            itemInput.value = '628100101';
            
            // محاكاة حدث ضغط مفتاح Enter
            const enterEvent = new KeyboardEvent('keydown', {
                key: 'Enter',
                code: 'Enter',
                keyCode: 13,
                which: 13,
                bubbles: true,
                cancelable: true
            });
            window.onyxApp.onAlameenItemKeydown(enterEvent, itemInput);
            
            const transformedName = itemInput.value;
            const code = row1.dataset.itemCode;
            const qty = row1.querySelector('.al-cell-qty').value;
            const price = row1.querySelector('.al-cell-price').value;
            const total = row1.querySelector('.al-cell-total').textContent.trim();

            return {
                transformedName,
                code,
                qty,
                price,
                total,
                isTransformed: (transformedName === 'كمبيوتر محمول Dell Latitude Core i7')
            };
        })();
        """
        res1 = ws_call(port, ws_path, "Runtime.evaluate", {"expression": js_test_item_enter, "returnByValue": True}, msg_id=4)
        val1 = res1.get("result", {}).get("result", {}).get("value", {})
        print("   النتيجة بعد ضغط Enter:")
        print(f"   - القيمة تحولت إلى اسم المنتج: '{val1.get('transformedName')}'")
        print(f"   - كود الصنف المحدد: '{val1.get('code')}'")
        print(f"   - الكمية: {val1.get('qty')}, السعر: {val1.get('price')}, الإجمالي: {val1.get('total')}")
        assert val1.get("isTransformed") is True, f"فشل تحويل الباركود إلى اسم المنتج: {val1}"

        # 5. اختبار كود الصنف 'ITM-103'
        print("\n3. اختبار إدخال كود الصنف 'ITM-103' في السطر الثاني وضغط Enter:")
        js_test_code_enter = """
        (function() {
            const tbody = document.getElementById('alameenActiveInvoiceTbody');
            const row2 = tbody.querySelector('tr[data-row-idx="2"]');
            const itemInput = row2.querySelector('.al-cell-item');
            
            itemInput.value = 'ITM-103';
            const enterEvent = new KeyboardEvent('keydown', { key: 'Enter', keyCode: 13, bubbles: true, cancelable: true });
            window.onyxApp.onAlameenItemKeydown(enterEvent, itemInput);
            
            return {
                transformedName: itemInput.value,
                code: row2.dataset.itemCode,
                qty: row2.querySelector('.al-cell-qty').value,
                isTransformed: (itemInput.value === 'طابعة ليزرية HP LaserJet Pro شبكية')
            };
        })();
        """
        res2 = ws_call(port, ws_path, "Runtime.evaluate", {"expression": js_test_code_enter, "returnByValue": True}, msg_id=5)
        val2 = res2.get("result", {}).get("result", {}).get("value", {})
        print(f"   - القيمة تحولت إلى اسم المنتج: '{val2.get('transformedName')}'")
        assert val2.get("isTransformed") is True, f"فشل تحويل الكود إلى اسم المنتج: {val2}"

        # 6. اختبار شريط المسح السريع للباركود (Quick Barcode Scanner Box)
        print("\n4. اختبار صندوق مسح الباركود السريع '628100102':")
        js_quick_scan = """
        (function() {
            const quickInput = document.getElementById('al-barcode-quick-input');
            quickInput.value = '628100102';
            window.onyxApp.onAlameenBarcodeScan(quickInput);

            const tbody = document.getElementById('alameenActiveInvoiceTbody');
            const matchedRow = Array.from(tbody.querySelectorAll('tr')).find(r => r.dataset.itemCode === 'ITM-102');
            
            return {
                foundRow: !!matchedRow,
                productName: matchedRow ? matchedRow.querySelector('.al-cell-item').value : '',
                quickInputCleared: (quickInput.value === '')
            };
        })();
        """
        res3 = ws_call(port, ws_path, "Runtime.evaluate", {"expression": js_quick_scan, "returnByValue": True}, msg_id=6)
        val3 = res3.get("result", {}).get("result", {}).get("value", {})
        print(f"   - تم العثور على الصنف وإدراجه: '{val3.get('productName')}'")
        print(f"   - تم تصفير حقل المسح لاستقبال الباركود التالي: {val3.get('quickInputCleared')}")
        assert val3.get("foundRow") is True
        assert val3.get("quickInputCleared") is True

        print("\n" + "=" * 65)
        print(">>> اكتمل اختبار دعم الباركود وتحويله لاسم المنتج بنجاح تام 100%! <<<")
        print("=" * 65)

    finally:
        proc.kill()

if __name__ == "__main__":
    test_barcode()
