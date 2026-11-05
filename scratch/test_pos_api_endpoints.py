# -*- coding: utf-8 -*-
"""
اختبار نقاط النهاية البرمجية (REST API) لفواتير نقاط البيع والمزامنة
"""

import os
import sys
import json
import urllib.request
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import desktop_app

def test_api():
    print("=" * 60)
    print(">>> اختبار نقاط النهاية البرمجية لخدمة نقاط البيع والمزامنة <<<")
    print("=" * 60)

    # تشغيل الخادم في خيط خلفي
    t = threading.Thread(target=desktop_app.start_server, daemon=True)
    t.start()
    desktop_app.server_ready.wait(timeout=3)
    time.sleep(0.5)

    base_url = f"http://127.0.0.1:{desktop_app.PORT}"
    print(f"Server is running on {base_url}")

    # 1. GET /api/pos/sync_status
    print("\n1. اختبار فحص حالة خدمة المزامنة:")
    req = urllib.request.Request(f"{base_url}/api/pos/sync_status")
    with urllib.request.urlopen(req, timeout=5) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode('utf-8'))
        print("   Response:", data)
        assert data.get("status") == "ok"
        assert "target" in data
        assert "driver" in data

    # 2. POST /api/pos/order (حفظ فاتورة نقطة بيع محلياً على SQLite)
    print("\n2. اختبار حفظ فاتورة نقطة بيع محلياً عبر API:")
    sample_order = {
        "id": f"POS-API-{int(time.time())}",
        "date": "2026-10-15",
        "time": "11:15 AM",
        "customer": "عميل تجريبي عبر API",
        "cashier": "كاشير الصالة",
        "paymentMethod": "CASH",
        "subtotal": 22000,
        "discount": 0,
        "tax": 0,
        "netTotal": 22000,
        "paidAmount": 22000,
        "changeAmount": 0,
        "items": [
            {"code": "10101", "name": "شاشة سامسونج", "qty": 1, "price": 22000, "costPrice": 16000, "total": 22000}
        ]
    }
    body = json.dumps(sample_order).encode('utf-8')
    req = urllib.request.Request(
        f"{base_url}/api/pos/order",
        data=body,
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode('utf-8'))
        print("   Response:", data)
        assert data.get("status") == "ok"
        assert data.get("sync_status") == "pending"

    # 3. GET /api/pos/orders (استرجاع الفواتير المحفوظة في SQLite)
    print("\n3. اختبار استرجاع الفواتير المحفوظة في SQLite:")
    req = urllib.request.Request(f"{base_url}/api/pos/orders")
    with urllib.request.urlopen(req, timeout=5) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode('utf-8'))
        orders = data.get("orders", [])
        print(f"   عدد الفواتير في SQLite: {len(orders)}")
        assert len(orders) > 0
        found = any(o['id'] == sample_order['id'] for o in orders)
        assert found is True, "لم يتم العثور على الفاتورة التي تم حفظها"

    # 4. POST /api/pos/sync_now (طلب محاولة المزامنة الفورية)
    print("\n4. اختبار طلب المزامنة الفورية:")
    req = urllib.request.Request(
        f"{base_url}/api/pos/sync_now",
        data=b"{}",
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode('utf-8'))
        print("   Response:", data)
        assert "status" in data

    print("\n" + "=" * 60)
    print(">>> اكتملت جميع اختبارات API بنجاح تام 100%! <<<")
    print("=" * 60)

if __name__ == "__main__":
    test_api()
