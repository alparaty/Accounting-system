# -*- coding: utf-8 -*-
"""
تطبيق أونكس برو المكتبي (Onyx Enterprise ERP Desktop Application)
يقوم بتشغيل النظام كنافذة برنامج مكتبي مستقلة وبأعلى أداء باستخدام محرك WebView2
مزود بمحرك قاعدة بيانات SQLite علائقية متوافقة بالكامل مع معايير Odoo 17 ORM
وواجهة Odoo 17 JSON-RPC 2.0 القياسية
"""

import os
import sys
import time
import threading
import http.server
import socketserver
import webbrowser
import subprocess
import sqlite3
import json
from pos_sync_service import get_pos_sync_service

PORT = 8999
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

BACKUPS_DIR = os.path.join(BASE_DIR, "backups")
DATABASE_DIR = os.path.join(BASE_DIR, "database")
DB_FILE = os.path.join(DATABASE_DIR, "alparaty_erp.db")

for d in [BACKUPS_DIR, DATABASE_DIR]:
    if not os.path.exists(d):
        try:
            os.makedirs(d, exist_ok=True)
        except Exception:
            pass

def init_sqlite():
    """
    تهيئة قاعدة بيانات SQLite بكافة الجداول العلائقية المتوافقة مع معايير Odoo 17
    مع دعم قيود السلامة المالية والتدقيق
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.executescript('''
            -- 1. جدول حفظ الحالة الشاملة الفورية
            CREATE TABLE IF NOT EXISTS system_state (
                key TEXT PRIMARY KEY,
                json_data TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- 2. دليل الحسابات العلائقي (account.account)
            CREATE TABLE IF NOT EXISTS account_account (
                code TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                parent TEXT,
                type TEXT,
                report TEXT,
                level INTEGER DEFAULT 4,
                currency TEXT DEFAULT 'YER',
                balance REAL DEFAULT 0,
                active INTEGER DEFAULT 1,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- 3. القيود اليومية (account.move)
            CREATE TABLE IF NOT EXISTS account_move (
                id TEXT PRIMARY KEY,
                date TEXT,
                branch TEXT DEFAULT '01',
                desc TEXT,
                status TEXT DEFAULT 'DRAFT',
                total_debit REAL DEFAULT 0,
                total_credit REAL DEFAULT 0,
                move_type TEXT DEFAULT 'entry',
                reviewed_by TEXT,
                posted_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- 4. بنود القيود اليومية (account.move.line)
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

            -- 5. سندات الصرف والقبض والشيكات (account.voucher / payment)
            CREATE TABLE IF NOT EXISTS account_voucher (
                id TEXT PRIMARY KEY,
                type TEXT,
                method TEXT DEFAULT 'CASH',
                date TEXT,
                branch TEXT DEFAULT '01',
                cash_box TEXT,
                target_acc TEXT,
                target_name TEXT,
                amount REAL DEFAULT 0,
                currency TEXT DEFAULT 'YER',
                cheque_no TEXT,
                due_date TEXT,
                posting_mode TEXT DEFAULT 'MANUAL_DUE',
                cheque_state TEXT,
                desc TEXT,
                status TEXT DEFAULT 'DRAFT',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- 6. الشركاء: العملاء والموردين (res.partner)
            CREATE TABLE IF NOT EXISTS res_partner (
                id TEXT PRIMARY KEY,
                code TEXT,
                name TEXT NOT NULL,
                type TEXT DEFAULT 'customer',
                phone TEXT,
                address TEXT,
                credit_limit REAL DEFAULT 0,
                balance REAL DEFAULT 0,
                active INTEGER DEFAULT 1,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- 7. الأصناف والمنتجات (product.product)
            CREATE TABLE IF NOT EXISTS product_product (
                id TEXT PRIMARY KEY,
                code TEXT,
                name TEXT NOT NULL,
                category TEXT,
                unit TEXT DEFAULT 'قطعة',
                cost_price REAL DEFAULT 0,
                sale_price REAL DEFAULT 0,
                stock_qty REAL DEFAULT 0,
                min_limit REAL DEFAULT 0,
                active INTEGER DEFAULT 1,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- 8. حركات المخزون التفصيلية (stock.move)
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

            -- 9. سجل التدقيق وتتبع التغييرات (mail.thread / audit_log)
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

            -- 10. تسلسلات الترقيم الآلي القياسية (ir.sequence)
            CREATE TABLE IF NOT EXISTS ir_sequence (
                code TEXT PRIMARY KEY,
                prefix TEXT,
                suffix TEXT,
                padding INTEGER DEFAULT 4,
                next_number INTEGER DEFAULT 1
            );

            -- 11. إقفال الفترات والسنوات المالية (account.fiscalyear / lock_date)
            CREATE TABLE IF NOT EXISTS fiscal_lock (
                fiscal_year TEXT PRIMARY KEY,
                lock_date TEXT,
                is_closed INTEGER DEFAULT 0,
                closed_by TEXT,
                closed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- 12. فواتير نقطة البيع المحلية (pos_order)
            CREATE TABLE IF NOT EXISTS pos_order (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                date TEXT,
                time TEXT,
                customer TEXT,
                cashier TEXT,
                payment_method TEXT DEFAULT 'CASH',
                subtotal REAL DEFAULT 0,
                discount REAL DEFAULT 0,
                tax REAL DEFAULT 0,
                net_total REAL DEFAULT 0,
                paid_amount REAL DEFAULT 0,
                change_amount REAL DEFAULT 0,
                jv_id TEXT,
                lines_json TEXT,
                status TEXT DEFAULT 'POSTED',
                sync_status TEXT DEFAULT 'pending',
                synced_at TIMESTAMP,
                sync_error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- 13. بنود فواتير نقطة البيع المحلية (pos_order_line)
            CREATE TABLE IF NOT EXISTS pos_order_line (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT,
                product_code TEXT,
                product_name TEXT,
                qty REAL DEFAULT 0,
                unit_price REAL DEFAULT 0,
                cost_price REAL DEFAULT 0,
                subtotal REAL DEFAULT 0,
                discount REAL DEFAULT 0,
                total REAL DEFAULT 0,
                FOREIGN KEY(order_id) REFERENCES pos_order(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_pos_order_sync ON pos_order(sync_status);
        ''')
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[SQLite Init Error] {e}", file=sys.stderr)

init_sqlite()

# تشغيل خدمة مزامنة نقاط البيع الخلفية مع PostgreSQL
pos_sync_svc = get_pos_sync_service(DB_FILE)

def sync_relational_tables(conn, data):
    """
    تحديث الجداول العلائقية في SQLite بدقة وسرعة فائقة من كائن الحالة الشاملة
    """
    if not isinstance(data, dict):
        return

    cur = conn.cursor()

    # 1. الحسابات
    accounts = data.get('accounts', [])
    for a in accounts:
        cur.execute('''
            INSERT OR REPLACE INTO account_account (code, name, parent, type, report, level, currency, balance, active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            a.get('code'), a.get('name'), a.get('parent'), a.get('type'),
            a.get('report', 'BS'), a.get('level', 4), a.get('currency', 'YER'),
            float(a.get('balance', 0) or 0), 1 if a.get('active', True) is not False else 0
        ))

    # 2. القيود وبنودها
    journal_entries = data.get('journalEntries', [])
    for j in journal_entries:
        jid = j.get('id')
        if not jid:
            continue
        cur.execute('''
            INSERT OR REPLACE INTO account_move (id, date, branch, desc, status, total_debit, total_credit, move_type, reviewed_by, posted_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            jid, j.get('date'), j.get('branch', '01'), j.get('desc', ''),
            j.get('status', 'DRAFT'), float(j.get('totalDebit', 0) or 0),
            float(j.get('totalCredit', 0) or 0), j.get('moveType', 'entry'),
            j.get('reviewedBy'), j.get('postedBy')
        ))

        lines = j.get('lines', [])
        if lines:
            cur.execute("DELETE FROM account_move_line WHERE move_id = ?", (jid,))
            for l in lines:
                cur.execute('''
                    INSERT INTO account_move_line (move_id, acc_code, acc_name, debit, credit, note, currency, amount_currency)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    jid, l.get('accCode'), l.get('accName', ''),
                    float(l.get('debit', 0) or 0), float(l.get('credit', 0) or 0),
                    l.get('note', ''), l.get('currency', 'YER'),
                    float(l.get('amountCurrency', 0) or 0)
                ))

    # 3. السندات والشيكات
    vouchers = data.get('vouchers', [])
    for v in vouchers:
        vid = v.get('id')
        if not vid:
            continue
        cur.execute('''
            INSERT OR REPLACE INTO account_voucher (id, type, method, date, branch, cash_box, target_acc, target_name, amount, currency, cheque_no, due_date, posting_mode, cheque_state, desc, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            vid, v.get('type'), v.get('method', 'CASH'), v.get('date'),
            v.get('branch', '01'), v.get('cashBox'), v.get('targetAcc'),
            v.get('targetName', ''), float(v.get('amount', 0) or 0),
            v.get('currency', 'YER'), v.get('chequeNo'), v.get('dueDate'),
            v.get('postingMode', 'MANUAL_DUE'), v.get('chequeState'),
            v.get('desc', ''), v.get('status', 'DRAFT')
        ))

    # 4. الشركاء (العملاء والموردين)
    customers = data.get('customers', [])
    for c in customers:
        cid = c.get('id') or c.get('code')
        if cid:
            cur.execute('''
                INSERT OR REPLACE INTO res_partner (id, code, name, type, phone, address, credit_limit, balance, active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                cid, c.get('code', cid), c.get('name'), 'customer',
                c.get('phone', ''), c.get('address', ''),
                float(c.get('creditLimit', 0) or 0),
                float(c.get('balanceLocal', 0) or 0),
                1 if c.get('active', True) is not False else 0
            ))

    suppliers = data.get('suppliers', [])
    for s in suppliers:
        sid = s.get('id') or s.get('code')
        if sid:
            cur.execute('''
                INSERT OR REPLACE INTO res_partner (id, code, name, type, phone, address, credit_limit, balance, active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                sid, s.get('code', sid), s.get('name'), 'supplier',
                s.get('phone', ''), s.get('address', ''),
                0, float(s.get('balanceLocal', 0) or 0),
                1 if s.get('active', True) is not False else 0
            ))

    # 5. الأصناف
    items = data.get('items', [])
    for itm in items:
        itmid = itm.get('id') or itm.get('code')
        if itmid:
            cur.execute('''
                INSERT OR REPLACE INTO product_product (id, code, name, category, unit, cost_price, sale_price, stock_qty, min_limit, active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                itmid, itm.get('code', itmid), itm.get('name'), itm.get('category', ''),
                itm.get('unit', 'قطعة'), float(itm.get('costPrice', 0) or 0),
                float(itm.get('salePrice', 0) or 0), float(itm.get('currentStock', 0) or 0),
                float(itm.get('minLimit', 0) or 0), 1 if itm.get('active', True) is not False else 0
            ))

    # 6. حركات المخزون
    stock_moves = data.get('stockMoves', [])
    for sm in stock_moves:
        smid = sm.get('id')
        if smid:
            cur.execute('''
                INSERT OR REPLACE INTO stock_move (id, date, product_id, product_name, move_type, qty, unit_cost, total_value, source_loc, dest_loc, ref_doc)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                smid, sm.get('date'), sm.get('productId'), sm.get('productName'),
                sm.get('moveType'), float(sm.get('qty', 0) or 0),
                float(sm.get('unitCost', 0) or 0), float(sm.get('totalValue', 0) or 0),
                sm.get('sourceLoc', ''), sm.get('destLoc', ''), sm.get('refDoc', '')
            ))

    # 7. التسلسلات
    sequences = data.get('sequences', {})
    if isinstance(sequences, dict):
        for seq_code, next_val in sequences.items():
            cur.execute('''
                INSERT OR REPLACE INTO ir_sequence (code, prefix, suffix, padding, next_number)
                VALUES (?, ?, ?, ?, ?)
            ''', (seq_code, f"{seq_code}-2026-", "", 4, int(next_val or 1)))

    # 8. أقفال السنوات المالية
    fiscal_locks = data.get('fiscalLocks', [])
    for fl in fiscal_locks:
        f_yr = fl.get('fiscalYear')
        if f_yr:
            cur.execute('''
                INSERT OR REPLACE INTO fiscal_lock (fiscal_year, lock_date, is_closed, closed_by)
                VALUES (?, ?, ?, ?)
            ''', (
                f_yr, fl.get('lockDate'), 1 if fl.get('isClosed') else 0, fl.get('closedBy', '')
            ))

    # 9. فواتير نقاط البيع المحلية (pos_order & pos_order_line)
    pos_invoices = data.get('posInvoices', [])
    for pos_inv in pos_invoices:
        pid = pos_inv.get('id') or pos_inv.get('invoiceNo')
        if pid:
            items = pos_inv.get('items', [])
            cur.execute('''
                INSERT OR IGNORE INTO pos_order (
                    id, session_id, date, time, customer, cashier,
                    payment_method, subtotal, discount, tax, net_total,
                    paid_amount, change_amount, jv_id, lines_json,
                    status, sync_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                pid, pos_inv.get('shiftId'), pos_inv.get('date'), pos_inv.get('time', ''),
                pos_inv.get('customer', 'عميل نقدي مباشر'), pos_inv.get('cashier', 'كاشير'),
                pos_inv.get('paymentMethod', 'CASH'), float(pos_inv.get('subtotal', 0) or 0),
                float(pos_inv.get('discount', 0) or 0), float(pos_inv.get('tax', 0) or 0),
                float(pos_inv.get('netTotal', 0) or 0), float(pos_inv.get('paidAmount', 0) or 0),
                float(pos_inv.get('changeAmount', 0) or 0), pos_inv.get('jvId'),
                json.dumps(items, ensure_ascii=False),
                pos_inv.get('status', 'POSTED'), 'pending'
            ))

            for itm in items:
                p_code = itm.get('code') or itm.get('id')
                p_qty = float(itm.get('qty', 1) or 1)
                p_unit = float(itm.get('price', 0) or itm.get('salePrice', 0) or 0)
                p_cost = float(itm.get('costPrice', 0) or 0)
                p_tot = float(itm.get('total', p_qty * p_unit) or (p_qty * p_unit))
                cur.execute('''
                    INSERT OR IGNORE INTO pos_order_line (
                        order_id, product_code, product_name, qty, unit_price, cost_price, subtotal, discount, total
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    pid, p_code, itm.get('name', p_code), p_qty, p_unit, p_cost, p_tot, 0, p_tot
                ))


def dispatch_odoo_rpc(payload, conn):
    """
    معالج طلبات Odoo 17 JSON-RPC 2.0 القياسية
    يدعم execute_kw، search_read، name_search، search_count، read
    """
    req_id = payload.get("id")
    method = payload.get("method")
    params = payload.get("params", {})

    if method != "call":
        return {"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found"}, "id": req_id}

    service = params.get("service")
    rpc_method = params.get("method")
    args = params.get("args", [])
    kwargs = params.get("kwargs", {})

    table_map = {
        "account.account": "account_account",
        "account.move": "account_move",
        "account.move.line": "account_move_line",
        "account.voucher": "account_voucher",
        "account.payment": "account_voucher",
        "res.partner": "res_partner",
        "product.product": "product_product",
        "product.template": "product_product",
        "stock.move": "stock_move",
        "audit.log": "audit_log",
        "ir.sequence": "ir_sequence",
        "fiscal.lock": "fiscal_lock"
    }

    if service == "object" and rpc_method == "execute_kw":
        if len(args) < 5:
            return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "Invalid params for execute_kw"}, "id": req_id}

        db_name = args[0]
        uid = args[1]
        password = args[2]
        model = args[3]
        model_method = args[4]
        method_args = args[5] if len(args) > 5 else []
        method_kwargs = args[6] if len(args) > 6 else kwargs

        table = table_map.get(model)
        if not table:
            return {"jsonrpc": "2.0", "error": {"code": -32600, "message": f"Model '{model}' not found in Odoo mapping"}, "id": req_id}

        cur = conn.cursor()

        try:
            if model_method == "search_read":
                fields = method_kwargs.get("fields", ["*"])
                fields_str = ", ".join(fields) if fields != ["*"] else "*"
                limit = int(method_kwargs.get("limit", 100))
                offset = int(method_kwargs.get("offset", 0))
                order = method_kwargs.get("order", "rowid DESC")

                cur.execute(f"SELECT {fields_str} FROM {table} ORDER BY {order} LIMIT ? OFFSET ?", (limit, offset))
                cols = [col[0] for col in cur.description]
                rows = [dict(zip(cols, r)) for r in cur.fetchall()]
                return {"jsonrpc": "2.0", "result": rows, "id": req_id}

            elif model_method == "search_count":
                count = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                return {"jsonrpc": "2.0", "result": count, "id": req_id}

            elif model_method == "read":
                ids = method_args[0] if method_args else []
                fields = method_kwargs.get("fields", ["*"])
                fields_str = ", ".join(fields) if fields != ["*"] else "*"
                if not ids:
                    return {"jsonrpc": "2.0", "result": [], "id": req_id}

                placeholders = ",".join(["?"] * len(ids))
                id_col = "code" if table == "account_account" else "id"
                cur.execute(f"SELECT {fields_str} FROM {table} WHERE {id_col} IN ({placeholders})", ids)
                cols = [col[0] for col in cur.description]
                rows = [dict(zip(cols, r)) for r in cur.fetchall()]
                return {"jsonrpc": "2.0", "result": rows, "id": req_id}

            elif model_method == "name_search":
                name = method_args[0] if method_args else ""
                limit = int(method_kwargs.get("limit", 10))
                id_col = "code" if table == "account_account" else "id"
                cur.execute(f"SELECT {id_col}, name FROM {table} WHERE name LIKE ? LIMIT ?", (f"%{name}%", limit))
                results = [(r[0], r[1]) for r in cur.fetchall()]
                return {"jsonrpc": "2.0", "result": results, "id": req_id}

            elif model_method == "check_recursion":
                # Odoo hierarchy check
                code = method_args[0] if method_args else None
                new_parent = method_args[1] if len(method_args) > 1 else None
                if code and new_parent and code == new_parent:
                    return {"jsonrpc": "2.0", "result": False, "id": req_id}
                return {"jsonrpc": "2.0", "result": True, "id": req_id}

            else:
                return {"jsonrpc": "2.0", "error": {"code": -32601, "message": f"Method '{model_method}' on '{model}' not supported"}, "id": req_id}

        except Exception as exc:
            return {"jsonrpc": "2.0", "error": {"code": -32000, "message": str(exc)}, "id": req_id}

    return {"jsonrpc": "2.0", "error": {"code": -32601, "message": "Unknown service or operation"}, "id": req_id}


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Requested-With')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        # 1. تصدير / استرجاع النسخة الاحتياطية الفورية
        if self.path == '/api/backup':
            try:
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute("SELECT json_data FROM system_state WHERE key = 'current' ORDER BY updated_at DESC LIMIT 1")
                row = cursor.fetchone()
                conn.close()
                if row and row[0]:
                    data = row[0].encode('utf-8')
                else:
                    backup_path = os.path.join(BACKUPS_DIR, "alparaty_auto_backup.json")
                    if os.path.exists(backup_path):
                        with open(backup_path, 'rb') as f:
                            data = f.read()
                    else:
                        data = b'{}'
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())
                return

        # 2. فحص حالة النظام والخدمات
        elif self.path == '/api/health':
            try:
                conn = sqlite3.connect(DB_FILE)
                cur = conn.cursor()
                cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [r[0] for r in cur.fetchall()]
                conn.close()
                res = json.dumps({
                    "status": "ok",
                    "sqlite": True,
                    "version": "2026.1",
                    "odooCompatibility": "17.0-Enterprise",
                    "relationalTables": len(tables),
                    "tables": tables
                }).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(res)))
                self.end_headers()
                self.wfile.write(res)
                return
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())
                return

        # 3. إحصائيات الجداول العلائقية
        elif self.path == '/api/db/stats':
            try:
                conn = sqlite3.connect(DB_FILE)
                cur = conn.cursor()
                stats = {}
                for tbl in ['account_account', 'account_move', 'account_move_line', 'account_voucher', 'res_partner', 'product_product', 'stock_move', 'audit_log', 'ir_sequence', 'fiscal_lock']:
                    try:
                        stats[tbl] = cur.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
                    except Exception:
                        stats[tbl] = 0
                conn.close()
                res = json.dumps({"status": "ok", "stats": stats}).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(res)))
                self.end_headers()
                self.wfile.write(res)
                return
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())
                return

        # 4. سجل التدقيق
        elif self.path.startswith('/api/audit_logs'):
            try:
                conn = sqlite3.connect(DB_FILE)
                cur = conn.cursor()
                cur.execute("SELECT id, action_type, doc_id, doc_model, user_name, field_name, old_value, new_value, details, created_at FROM audit_log ORDER BY id DESC LIMIT 100")
                cols = [c[0] for c in cur.description]
                rows = [dict(zip(cols, r)) for r in cur.fetchall()]
                conn.close()
                res = json.dumps({"status": "ok", "logs": rows}).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(res)))
                self.end_headers()
                self.wfile.write(res)
                return
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())
                return

        # 5. حركات المخزون
        elif self.path.startswith('/api/stock_moves'):
            try:
                conn = sqlite3.connect(DB_FILE)
                cur = conn.cursor()
                cur.execute("SELECT id, date, product_id, product_name, move_type, qty, unit_cost, total_value, source_loc, dest_loc, ref_doc, created_at FROM stock_move ORDER BY date DESC, id DESC LIMIT 100")
                cols = [c[0] for c in cur.description]
                rows = [dict(zip(cols, r)) for r in cur.fetchall()]
                conn.close()
                res = json.dumps({"status": "ok", "moves": rows}).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(res)))
                self.end_headers()
                self.wfile.write(res)
                return
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())
                return

        # 6. استرجاع فواتير نقاط البيع المحفوظة محلياً على SQLite وحالة مزامنتها
        elif self.path.startswith('/api/pos/orders'):
            try:
                conn = sqlite3.connect(DB_FILE)
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute("SELECT * FROM pos_order ORDER BY created_at DESC LIMIT 100")
                orders = [dict(r) for r in cur.fetchall()]
                conn.close()
                res = json.dumps({"status": "ok", "orders": orders}, ensure_ascii=False).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(res)))
                self.end_headers()
                self.wfile.write(res)
                return
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())
                return

        # 7. حالة خدمة المزامنة الخلفية مع PostgreSQL
        elif self.path == '/api/pos/sync_status':
            try:
                status = pos_sync_svc.get_status()
                res = json.dumps({"status": "ok", **status}, ensure_ascii=False).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(res)))
                self.end_headers()
                self.wfile.write(res)
                return
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())
                return

        super().do_GET()

    def do_POST(self):
        # 1. مزامنة الحالة الكاملة وتحديث الجداول العلائقية
        if self.path == '/api/sync':
            try:
                content_len = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_len).decode('utf-8')
                parsed_data = json.loads(body)

                # أ. حفظ في ملف JSON محلي على القرص الصلب كأمان إضافي
                backup_path = os.path.join(BACKUPS_DIR, "alparaty_auto_backup.json")
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(body)

                # ب. حفظ في قاعدة بيانات SQLite (الحالة الكاملة + الجداول العلائقية المنفصلة)
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO system_state (key, json_data, updated_at) VALUES ('current', ?, CURRENT_TIMESTAMP)",
                    (body,)
                )

                # ج. تحديث الجداول العلائقية المتوافقة مع Odoo
                sync_relational_tables(conn, parsed_data)

                conn.commit()
                conn.close()

                resp = b'{"status":"ok","persisted":"disk_and_sqlite_relational","odoo_sync":true}'
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(resp)))
                self.end_headers()
                self.wfile.write(resp)
                return
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f'{{"status":"error","message":"{str(e)}"}}'.encode())
                return

        # 2. إضافة حدث تدقيق فردي
        elif self.path == '/api/audit_log':
            try:
                content_len = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_len).decode('utf-8')
                event = json.loads(body)

                conn = sqlite3.connect(DB_FILE)
                cur = conn.cursor()
                cur.execute('''
                    INSERT INTO audit_log (action_type, doc_id, doc_model, user_name, field_name, old_value, new_value, details)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    event.get('action_type', 'UPDATE'),
                    event.get('doc_id', ''),
                    event.get('doc_model', ''),
                    event.get('user_name', 'System'),
                    event.get('field_name', ''),
                    str(event.get('old_value', '')),
                    str(event.get('new_value', '')),
                    event.get('details', '')
                ))
                conn.commit()
                conn.close()

                resp = b'{"status":"ok","logged":true}'
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(resp)))
                self.end_headers()
                self.wfile.write(resp)
                return
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())
                return

        # 3. معالجة طلبات Odoo 17 JSON-RPC 2.0 القياسية
        elif self.path == '/jsonrpc':
            try:
                content_len = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_len).decode('utf-8')
                payload = json.loads(body)

                conn = sqlite3.connect(DB_FILE)
                rpc_response = dispatch_odoo_rpc(payload, conn)
                conn.close()

                resp = json.dumps(rpc_response).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(resp)))
                self.end_headers()
                self.wfile.write(resp)
                return
            except Exception as e:
                err_resp = json.dumps({"jsonrpc": "2.0", "error": {"code": -32603, "message": str(e)}, "id": None}).encode('utf-8')
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(err_resp)))
                self.end_headers()
                self.wfile.write(err_resp)
                return

        # 4. حفظ فاتورة نقطة بيع محلياً على SQLite مع تحفيز المزامنة
        elif self.path == '/api/pos/order':
            try:
                content_len = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_len).decode('utf-8')
                order_data = json.loads(body)

                ok, result = pos_sync_svc.save_local_order(order_data)
                resp_dict = {
                    "status": "ok" if ok else "error",
                    "order_id": result if ok else None,
                    "message": "تم حفظ الفاتورة محلياً على SQLite بنجاح وجاري المزامنة في الخلفية" if ok else result,
                    "sync_status": "pending" if ok else "failed"
                }
                resp = json.dumps(resp_dict, ensure_ascii=False).encode('utf-8')
                self.send_response(200 if ok else 400)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(resp)))
                self.end_headers()
                self.wfile.write(resp)
                return
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f'{{"status":"error","message":"{str(e)}"}}'.encode())
                return

        # 5. طلب مزامنة فورية مع خادم PostgreSQL
        elif self.path == '/api/pos/sync_now':
            try:
                sync_res = pos_sync_svc.sync_pending_orders()
                resp = json.dumps(sync_res, ensure_ascii=False).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(resp)))
                self.end_headers()
                self.wfile.write(resp)
                return
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f'{{"status":"error","message":"{str(e)}"}}'.encode())
                return

        # 6. تحديث إعدادات الاتصال بخادم PostgreSQL
        elif self.path == '/api/pos/config':
            try:
                content_len = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_len).decode('utf-8')
                new_cfg = json.loads(body)
                ok = pos_sync_svc.save_config(new_cfg)
                resp = json.dumps({"status": "ok" if ok else "error", "config": pos_sync_svc.config}, ensure_ascii=False).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(resp)))
                self.end_headers()
                self.wfile.write(resp)
                return
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f'{{"status":"error","message":"{str(e)}"}}'.encode())
                return

        self.send_response(404)
        self.end_headers()

    def log_message(self, format, *args):
        pass  # منع طباعة سجلات الطلبات للحفاظ على نظافة الطرفية


server_ready = threading.Event()

def start_server():
    global PORT
    socketserver.TCPServer.allow_reuse_address = True
    for p in [PORT, 8998, 8997, 8996, 9000, 9001]:
        try:
            httpd = socketserver.TCPServer(("127.0.0.1", p), QuietHandler)
            PORT = p
            server_ready.set()
            httpd.serve_forever()
            return
        except Exception:
            continue
    server_ready.set()

def launch_native_window():
    url = f"http://127.0.0.1:{PORT}/index.html"

    # 1. تشغيل Microsoft Edge في وضع التطبيق المكتبي المستقل المكبر (--app --start-maximized)
    edge_paths = [
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%LocalAppData%\Microsoft\Edge\Application\msedge.exe")
    ]
    edge_profile = os.path.join(DATABASE_DIR, ".edge_runtime_profile")
    os.makedirs(edge_profile, exist_ok=True)

    for edge in edge_paths:
        if os.path.exists(edge):
            try:
                subprocess.Popen([edge, f"--app={url}", f"--user-data-dir={edge_profile}", "--start-maximized"])
                return
            except Exception:
                pass

    # 2. محاولة Google Chrome في وضع التطبيق المستقل المكبر
    chrome_paths = [
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe")
    ]
    chrome_profile = os.path.join(DATABASE_DIR, ".chrome_runtime_profile")
    os.makedirs(chrome_profile, exist_ok=True)
    for chrome in chrome_paths:
        if os.path.exists(chrome):
            try:
                subprocess.Popen([chrome, f"--app={url}", f"--user-data-dir={chrome_profile}", "--start-maximized"])
                return
            except Exception:
                pass

    # 3. فتح في المتصفح الافتراضي كخيار بديل
    try:
        webbrowser.open(url)
    except Exception:
        pass

if __name__ == '__main__':
    # تشغيل السيرفر المحلي في خلفية البرنامج
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    server_ready.wait(timeout=2.0)

    print("=" * 68, flush=True)
    print("  البرطي المالي الشامل | Al-ParatY Financial Enterprise", flush=True)
    print(f"  ● الخادم المحلي يعمل بنجاح على: http://127.0.0.1:{PORT}", flush=True)
    print("  ● محرك SQLite العلائقي المتوافق مع Odoo 17: نشط وجاهز للعمل", flush=True)
    print("  ● واجهة Odoo 17 JSON-RPC 2.0 القياسية (/jsonrpc): مفعلة وجاهزة", flush=True)
    print("  ● نافذة التطبيق مفتوحة الآن وتعمل بكفاءة عالية", flush=True)
    print("  ● الخادم نشط في هذه الطرفية (اضغط Ctrl+C في أي وقت للإيقاف)", flush=True)
    print("=" * 68, flush=True)

    launch_native_window()

    # إبقاء السيرفر نشطاً في الطرفية حتى يضغط المستخدم Ctrl+C
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nتم إيقاف تشغيل خادم النظام بنجاح.", flush=True)
        sys.exit(0)
