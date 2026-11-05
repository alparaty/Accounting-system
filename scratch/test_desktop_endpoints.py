# -*- coding: utf-8 -*-
"""
فحص واختبار مسارات desktop_app.py الجديدة
"""
import urllib.request
import json
import threading
import time
import sys
import os

BASE_DIR = r'c:\Users\AlparatY\Desktop\system ERP'
sys.path.insert(0, BASE_DIR)
import desktop_app

import socketserver
PORT = 9988
httpd = socketserver.TCPServer(("127.0.0.1", PORT), desktop_app.QuietHandler)
t = threading.Thread(target=httpd.serve_forever, daemon=True)
t.start()
time.sleep(1)

try:
    # 1. Test /api/health
    res = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/health")
    data = json.loads(res.read().decode('utf-8'))
    print("1. Health Response:", data)
    assert data['sqlite'] is True
    assert data['odooCompatibility'] == '17.0-Enterprise'

    # 2. Test /api/sync with full seed payload
    sync_payload = {
        "accounts": [
            {"code": "111101", "name": "صندوق المركز الرئيسي", "type": "SUB", "balance": 750000}
        ],
        "journalEntries": [
            {
                "id": "JV-2026-001",
                "date": "2026-10-14",
                "branch": "01",
                "desc": "قيد تجريبي",
                "status": "POSTED",
                "totalDebit": 20000,
                "totalCredit": 20000,
                "lines": [
                    {"accCode": "111101", "accName": "صندوق", "debit": 20000, "credit": 0},
                    {"accCode": "311101", "accName": "رأس المال", "debit": 0, "credit": 20000}
                ]
            }
        ],
        "vouchers": [
            {"id": "PV-2026-001", "type": "PAYMENT", "amount": 5000, "targetAcc": "520101", "status": "POSTED"}
        ],
        "customers": [
            {"code": "CUST-01", "name": "شركة الجزيرة", "balanceLocal": 120000, "creditLimit": 500000}
        ],
        "items": [
            {"code": "ITM-01", "name": "طابعة كانون", "costPrice": 65000, "currentStock": 8}
        ],
        "stockMoves": [
            {"id": "STK-2026-0001", "date": "2026-10-14", "productId": "ITM-01", "productName": "طابعة كانون", "moveType": "PURCHASE_RECEIPT", "qty": 8, "unitCost": 65000, "totalValue": 520000}
        ],
        "sequences": {"JV": 2, "PV": 2, "RV": 1, "STK": 2}
    }
    
    req = urllib.request.Request(
        f"http://127.0.0.1:{PORT}/api/sync",
        data=json.dumps(sync_payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    s_res = urllib.request.urlopen(req)
    s_data = json.loads(s_res.read().decode('utf-8'))
    print("2. Sync Response:", s_data)
    assert s_data['status'] == 'ok'
    assert s_data['persisted'] == 'disk_and_sqlite_relational'

    # 3. Test /api/db/stats
    st_res = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/db/stats")
    st_data = json.loads(st_res.read().decode('utf-8'))
    print("3. DB Stats:", st_data)
    assert st_data['stats']['account_account'] >= 1
    assert st_data['stats']['account_move'] >= 1
    assert st_data['stats']['stock_move'] >= 1

    # 4. Test /jsonrpc (Odoo 17 JSON-RPC 2.0 execute_kw)
    rpc_payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "service": "object",
            "method": "execute_kw",
            "args": [
                "alparaty_erp",
                1,
                "admin",
                "account.account",
                "search_read",
                [],
                {"fields": ["code", "name", "balance"], "limit": 5}
            ]
        },
        "id": 99
    }
    rpc_req = urllib.request.Request(
        f"http://127.0.0.1:{PORT}/jsonrpc",
        data=json.dumps(rpc_payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    rpc_res = urllib.request.urlopen(rpc_req)
    rpc_data = json.loads(rpc_res.read().decode('utf-8'))
    print("4. JSON-RPC Response:", rpc_data)
    assert rpc_data['jsonrpc'] == '2.0'
    assert len(rpc_data['result']) >= 1
    assert rpc_data['result'][0]['code'] == '111101'

    # 5. Test name_search RPC
    name_rpc_payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "service": "object",
            "method": "execute_kw",
            "args": [
                "alparaty_erp",
                1,
                "admin",
                "product.product",
                "name_search",
                ["طابعة"],
                {}
            ]
        },
        "id": 100
    }
    name_res = urllib.request.urlopen(urllib.request.Request(
        f"http://127.0.0.1:{PORT}/jsonrpc",
        data=json.dumps(name_rpc_payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    ))
    name_data = json.loads(name_res.read().decode('utf-8'))
    print("5. Name Search RPC Response:", name_data)
    assert len(name_data['result']) >= 1

    print("\n>>> ALL DESKTOP ENDPOINT TESTS PASSED! <<<")

finally:
    httpd.shutdown()
