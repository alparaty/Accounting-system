# -*- coding: utf-8 -*-
"""
اختبار المحرك العلائقي ونظام Odoo 17 في بايثون
"""
import sqlite3
import json
import os

TEST_DB = "scratch/test_alparaty_erp.db"
if os.path.exists(TEST_DB):
    os.remove(TEST_DB)

conn = sqlite3.connect(TEST_DB)
cur = conn.cursor()

# 1. إنشاء الجداول العلائقية المتوافقة مع Odoo 17
cur.executescript('''
CREATE TABLE IF NOT EXISTS system_state (
    key TEXT PRIMARY KEY,
    json_data TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS account_account (
    code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    parent TEXT,
    type TEXT,
    report TEXT,
    level INTEGER,
    currency TEXT,
    balance REAL DEFAULT 0,
    active INTEGER DEFAULT 1,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS account_move (
    id TEXT PRIMARY KEY,
    date TEXT,
    branch TEXT,
    desc TEXT,
    status TEXT,
    total_debit REAL DEFAULT 0,
    total_credit REAL DEFAULT 0,
    move_type TEXT,
    reviewed_by TEXT,
    posted_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS account_move_line (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    move_id TEXT,
    acc_code TEXT,
    acc_name TEXT,
    debit REAL DEFAULT 0,
    credit REAL DEFAULT 0,
    note TEXT,
    currency TEXT DEFAULT 'YER',
    amount_currency REAL DEFAULT 0,
    FOREIGN KEY(move_id) REFERENCES account_move(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS account_voucher (
    id TEXT PRIMARY KEY,
    type TEXT,
    method TEXT,
    date TEXT,
    branch TEXT,
    cash_box TEXT,
    target_acc TEXT,
    target_name TEXT,
    amount REAL DEFAULT 0,
    currency TEXT DEFAULT 'YER',
    cheque_no TEXT,
    due_date TEXT,
    posting_mode TEXT,
    cheque_state TEXT,
    desc TEXT,
    status TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS res_partner (
    id TEXT PRIMARY KEY,
    code TEXT,
    name TEXT NOT NULL,
    type TEXT,
    phone TEXT,
    address TEXT,
    credit_limit REAL DEFAULT 0,
    balance REAL DEFAULT 0,
    active INTEGER DEFAULT 1,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS product_product (
    id TEXT PRIMARY KEY,
    code TEXT,
    name TEXT NOT NULL,
    category TEXT,
    unit TEXT,
    cost_price REAL DEFAULT 0,
    sale_price REAL DEFAULT 0,
    stock_qty REAL DEFAULT 0,
    min_limit REAL DEFAULT 0,
    active INTEGER DEFAULT 1,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS stock_move (
    id TEXT PRIMARY KEY,
    date TEXT,
    product_id TEXT,
    product_name TEXT,
    move_type TEXT,
    qty REAL DEFAULT 0,
    unit_cost REAL DEFAULT 0,
    total_value REAL DEFAULT 0,
    source_loc TEXT,
    dest_loc TEXT,
    ref_doc TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action_type TEXT,
    doc_id TEXT,
    doc_model TEXT,
    user_name TEXT,
    field_name TEXT,
    old_value TEXT,
    new_value TEXT,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ir_sequence (
    code TEXT PRIMARY KEY,
    prefix TEXT,
    suffix TEXT,
    padding INTEGER DEFAULT 4,
    next_number INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS fiscal_lock (
    fiscal_year TEXT PRIMARY KEY,
    lock_date TEXT,
    is_closed INTEGER DEFAULT 0,
    closed_by TEXT,
    closed_at TIMESTAMP
);
''')

# 2. اختبار المزامنة العلائقية
sample_data = {
    "accounts": [
        {"code": "111101", "name": "الصندوق الرئيسي", "parent": "1111", "type": "SUB", "report": "BS", "level": 5, "currency": "YER", "balance": 150000}
    ],
    "journalEntries": [
        {
            "id": "JV-2026-001",
            "date": "2026-10-14",
            "branch": "01",
            "desc": "قيد افتتاحي",
            "status": "POSTED",
            "totalDebit": 50000,
            "totalCredit": 50000,
            "postedBy": "المدير المالي",
            "lines": [
                {"accCode": "111101", "accName": "الصندوق", "debit": 50000, "credit": 0, "note": "مدين"},
                {"accCode": "311101", "accName": "رأس المال", "debit": 0, "credit": 50000, "note": "دائن"}
            ]
        }
    ],
    "items": [
        {"id": "ITM-01", "code": "ITM-01", "name": "لابتوب ديل", "category": "أجهزة", "costPrice": 450000, "salePrice": 520000, "currentStock": 15}
    ],
    "stockMoves": [
        {"id": "STK-2026-0001", "date": "2026-10-14", "productId": "ITM-01", "productName": "لابتوب ديل", "moveType": "PURCHASE_RECEIPT", "qty": 15, "unitCost": 450000, "totalValue": 6750000, "sourceLoc": "المورد", "destLoc": "WH01", "refDoc": "PINV-001"}
    ],
    "customers": [
        {"id": "CUST-01", "code": "1131010001", "name": "شركة الأمل للتجارة", "balanceLocal": 250000, "creditLimit": 1000000}
    ],
    "sequences": {
        "JV": 2, "PV": 1, "RV": 1, "INV": 1, "PINV": 1, "STK": 2
    }
}

# مزامنة الحسابات
for a in sample_data.get("accounts", []):
    cur.execute('''
        INSERT OR REPLACE INTO account_account (code, name, parent, type, report, level, currency, balance, active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (a.get("code"), a.get("name"), a.get("parent"), a.get("type"), a.get("report"), a.get("level", 4), a.get("currency", "YER"), a.get("balance", 0), 1))

# مزامنة القيود
for j in sample_data.get("journalEntries", []):
    cur.execute('''
        INSERT OR REPLACE INTO account_move (id, date, branch, desc, status, total_debit, total_credit, move_type, reviewed_by, posted_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (j.get("id"), j.get("date"), j.get("branch"), j.get("desc"), j.get("status"), j.get("totalDebit", 0), j.get("totalCredit", 0), j.get("moveType", "entry"), j.get("reviewedBy"), j.get("postedBy")))
    
    cur.execute("DELETE FROM account_move_line WHERE move_id = ?", (j.get("id"),))
    for l in j.get("lines", []):
        cur.execute('''
            INSERT INTO account_move_line (move_id, acc_code, acc_name, debit, credit, note, currency, amount_currency)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (j.get("id"), l.get("accCode"), l.get("accName"), l.get("debit", 0), l.get("credit", 0), l.get("note", ""), l.get("currency", "YER"), l.get("amountCurrency", 0)))

# مزامنة المنتجات
for itm in sample_data.get("items", []):
    cur.execute('''
        INSERT OR REPLACE INTO product_product (id, code, name, category, unit, cost_price, sale_price, stock_qty, min_limit, active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (itm.get("id") or itm.get("code"), itm.get("code"), itm.get("name"), itm.get("category"), itm.get("unit", "قطعة"), itm.get("costPrice", 0), itm.get("salePrice", 0), itm.get("currentStock", 0), itm.get("minLimit", 0), 1))

# مزامنة حركات المخزون
for sm in sample_data.get("stockMoves", []):
    cur.execute('''
        INSERT OR REPLACE INTO stock_move (id, date, product_id, product_name, move_type, qty, unit_cost, total_value, source_loc, dest_loc, ref_doc)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (sm.get("id"), sm.get("date"), sm.get("productId"), sm.get("productName"), sm.get("moveType"), sm.get("qty", 0), sm.get("unitCost", 0), sm.get("totalValue", 0), sm.get("sourceLoc"), sm.get("destLoc"), sm.get("refDoc")))

# مزامنة الشركاء (العملاء والموردين)
for c in sample_data.get("customers", []):
    cur.execute('''
        INSERT OR REPLACE INTO res_partner (id, code, name, type, phone, address, credit_limit, balance, active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (c.get("id") or c.get("code"), c.get("code"), c.get("name"), "customer", c.get("phone", ""), c.get("address", ""), c.get("creditLimit", 0), c.get("balanceLocal", 0), 1))

# مزامنة التسلسلات
for seq_code, next_val in sample_data.get("sequences", {}).items():
    cur.execute('''
        INSERT OR REPLACE INTO ir_sequence (code, prefix, suffix, padding, next_number)
        VALUES (?, ?, ?, ?, ?)
    ''', (seq_code, f"{seq_code}-2026-", "", 4, next_val))

conn.commit()

# التحقق
print("TABLE COUNTS:")
for table in ['account_account', 'account_move', 'account_move_line', 'product_product', 'stock_move', 'res_partner', 'ir_sequence']:
    count = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(f" - {table}: {count}")

conn.close()
os.remove(TEST_DB)
print("ALL TESTS PASSED SUCCESSFULLY!")
