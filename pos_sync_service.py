# -*- coding: utf-8 -*-
"""
خدمة المزامنة الخلفية لفواتير نقاط البيع (POS Offline-First & PostgreSQL Sync Service)
-----------------------------------------------------------------------------------
1. حفظ فواتير نقطة البيع فورياً ومحلياً على قاعدة بيانات SQLite خفيفة (وضع العمل المستقل دون اتصال).
2. خدمة خلفية ذكية تراقب الاتصال بخادم PostgreSQL باستمرار دون إبطاء أو تجميد الكاشير.
3. فور عودة الاتصال بخادم PostgreSQL:
   - رفع الفواتير المعلقة آلياً بحركة ذرية واحدة (Atomically in a DB Transaction).
   - تحديث أرصدة الحسابات المالية في الخادم (الصندوق/البنك/العملاء وحساب إيرادات المبيعات).
   - تحديث أرصدة المخزون وحركات الصرف (stock_move & product stock).
   - تعليم الفواتير المحلية كمزامنة بنجاح (synced) مع توثيق وقت المزامنة.
"""

import os
import sys
import time
import json
import sqlite3
import threading
import socket
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

# استيراد محرك اتصال PostgreSQL (يدعم pg8000 أو psycopg2 تلقائياً)
PG_DRIVER = None
try:
    import pg8000.dbapi as pg_engine
    PG_DRIVER = 'pg8000'
except ImportError:
    try:
        import psycopg2 as pg_engine
        PG_DRIVER = 'psycopg2'
    except ImportError:
        PG_DRIVER = None

class POSSyncService:
    def __init__(self, sqlite_path: str, config_path: Optional[str] = None):
        self.sqlite_path = sqlite_path
        self.config_path = config_path or os.path.join(os.path.dirname(sqlite_path), "postgres_config.json")
        self.config = self._load_config()
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.sync_event = threading.Event()
        self.lock = threading.Lock()

        # إحصائيات المزامنة الحية
        self.is_online = False
        self.last_sync_time: Optional[str] = None
        self.last_error: Optional[str] = None
        self.last_status_msg = "الخدمة قيد التهيئة..."
        self.synced_count = 0
        self.pending_count = 0
        self.failed_count = 0

        self._ensure_sqlite_tables()

    def _load_config(self) -> Dict[str, Any]:
        """تحميل إعدادات الاتصال بخادم PostgreSQL مع دعم المتغيرات البيئية"""
        default_cfg = {
            "enabled": True,
            "host": os.environ.get("PGHOST", "localhost"),
            "port": int(os.environ.get("PGPORT", 5432)),
            "dbname": os.environ.get("PGDATABASE", "alparaty_erp"),
            "user": os.environ.get("PGUSER", "postgres"),
            "password": os.environ.get("PGPASSWORD", "password"),
            "sync_interval_seconds": 10,
            "batch_size": 50,
            "auto_create_schema": True
        }

        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    user_cfg = json.load(f)
                    default_cfg.update(user_cfg)
            except Exception as e:
                print(f"[POS Sync] Warning loading config: {e}", file=sys.stderr)
        else:
            try:
                os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
                with open(self.config_path, "w", encoding="utf-8") as f:
                    json.dump(default_cfg, f, indent=2, ensure_ascii=False)
            except Exception:
                pass

        return default_cfg

    def save_config(self, new_cfg: Dict[str, Any]) -> bool:
        """تحديث إعدادات خادم PostgreSQL"""
        with self.lock:
            self.config.update(new_cfg)
            try:
                with open(self.config_path, "w", encoding="utf-8") as f:
                    json.dump(self.config, f, indent=2, ensure_ascii=False)
                self.trigger_immediate_sync()
                return True
            except Exception as e:
                self.last_error = str(e)
                return False

    def _ensure_sqlite_tables(self):
        """التأكد من وجود جداول فواتير نقاط البيع المحلية في SQLite"""
        try:
            conn = sqlite3.connect(self.sqlite_path)
            cur = conn.cursor()
            cur.executescript('''
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
            print(f"[POS Sync] SQLite Init Error: {e}", file=sys.stderr)

    def save_local_order(self, order_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        حفظ فاتورة نقطة البيع فورياً في قاعدة بيانات SQLite المحلية
        مع تسجيل بنودها وتحديث المخزون المحلي
        """
        try:
            conn = sqlite3.connect(self.sqlite_path)
            cur = conn.cursor()

            order_id = order_data.get("id") or order_data.get("invoiceNo")
            if not order_id:
                order_id = f"POS-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

            today = order_data.get("date") or datetime.now().strftime("%Y-%m-%d")
            time_now = order_data.get("time") or datetime.now().strftime("%I:%M:%S %p")
            items = order_data.get("items", [])
            lines_json = json.dumps(items, ensure_ascii=False)

            cur.execute('''
                INSERT OR REPLACE INTO pos_order (
                    id, session_id, date, time, customer, cashier,
                    payment_method, subtotal, discount, tax, net_total,
                    paid_amount, change_amount, jv_id, lines_json,
                    status, sync_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                order_id,
                order_data.get("shiftId") or order_data.get("session_id"),
                today,
                time_now,
                order_data.get("customer", "عميل نقدي مباشر"),
                order_data.get("cashier", "كاشير"),
                order_data.get("paymentMethod", "CASH"),
                float(order_data.get("subtotal", 0) or 0),
                float(order_data.get("discount", 0) or 0),
                float(order_data.get("tax", 0) or 0),
                float(order_data.get("netTotal", 0) or 0),
                float(order_data.get("paidAmount", 0) or 0),
                float(order_data.get("changeAmount", 0) or 0),
                order_data.get("jvId"),
                lines_json,
                order_data.get("status", "POSTED"),
                "pending"
            ))

            # حفظ البنود التفصيلية
            cur.execute("DELETE FROM pos_order_line WHERE order_id = ?", (order_id,))
            for itm in items:
                p_code = itm.get("code") or itm.get("id")
                qty = float(itm.get("qty", 1) or 1)
                u_price = float(itm.get("price", 0) or itm.get("salePrice", 0) or 0)
                c_price = float(itm.get("costPrice", 0) or 0)
                tot = float(itm.get("total", qty * u_price) or (qty * u_price))

                cur.execute('''
                    INSERT INTO pos_order_line (
                        order_id, product_code, product_name, qty, unit_price, cost_price, subtotal, discount, total
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    order_id, p_code, itm.get("name", p_code), qty, u_price, c_price, tot, 0, tot
                ))

                # خفض رصيد الصنف المحلي في SQLite
                if p_code:
                    try:
                        cur.execute('''
                            UPDATE product_product
                            SET stock_qty = MAX(0, stock_qty - ?)
                            WHERE code = ? OR id = ?
                        ''', (qty, p_code, p_code))
                    except Exception:
                        try:
                            cur.execute('''
                                UPDATE product_product
                                SET stock_qty = MAX(0, stock_qty - ?)
                                WHERE code = ?
                            ''', (qty, p_code))
                        except Exception:
                            pass

            # تسجيل قيد التدقيق
            try:
                cur.execute('''
                    INSERT INTO audit_log (action_type, doc_id, user_name, details)
                    VALUES (?, ?, ?, ?)
                ''', (
                    'POS_LOCAL_SAVE',
                    order_id,
                    order_data.get("cashier", "كاشير"),
                    f"حفظ فاتورة نقطة بيع محلياً على SQLite برقم [{order_id}] بمبلغ {order_data.get('netTotal', 0)}"
                ))
            except Exception:
                pass

            conn.commit()
            conn.close()

            # تحفيز المزامنة فوراً مع PostgreSQL في الخلفية
            self.trigger_immediate_sync()
            return True, order_id

        except Exception as e:
            err_msg = f"خطأ في حفظ الفاتورة محلياً: {e}"
            print(f"[POS Sync] {err_msg}", file=sys.stderr)
            return False, str(e)

    def check_postgres_connection(self) -> Tuple[bool, Optional[Any], str]:
        """
        فحص سريع للاتصال بخادم PostgreSQL دون تجميد
        يتحقق أولاً من منفذ الشبكة (TCP Port) مع مهلة ثانية واحدة
        """
        if not self.config.get("enabled", True):
            return False, None, "المزامنة مع PostgreSQL معطلة من الإعدادات."

        host = self.config.get("host", "localhost")
        port = int(self.config.get("port", 5432))

        # 1. فحص المنفذ السريع (1s socket timeout)
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.2)
            res = sock.connect_ex((host, port))
            sock.close()
            if res != 0:
                return False, None, f"خادم PostgreSQL غير متاح على {host}:{port} (المنفذ مغلق أو الخادم متوقف)."
        except Exception as e:
            return False, None, f"تعذر الوصول لعنوان خادم PostgreSQL {host}:{port}: {e}"

        # 2. إنشاء الاتصال الفعلي عبر محرك PG المتاح
        if not PG_DRIVER:
            return False, None, "لم يتم العثور على مكتبة اتصال PostgreSQL (pg8000 أو psycopg2)."

        try:
            dbname = self.config.get("dbname", "alparaty_erp")
            user = self.config.get("user", "postgres")
            password = self.config.get("password", "")

            if PG_DRIVER == 'pg8000':
                conn = pg_engine.connect(
                    host=host,
                    port=port,
                    database=dbname,
                    user=user,
                    password=password,
                    timeout=3
                )
            else: # psycopg2
                conn = pg_engine.connect(
                    host=host,
                    port=port,
                    dbname=dbname,
                    user=user,
                    password=password,
                    connect_timeout=3
                )
            return True, conn, "الاتصال بخادم PostgreSQL نشط وفعال."
        except Exception as e:
            return False, None, f"فشل مصادقة أو اتصال PostgreSQL: {e}"

    def ensure_postgres_schema(self, pg_conn):
        """
        إنشاء وتأكيد وجود الجداول المالية والمخزنية في خادم PostgreSQL
        إذا لم تكن موجودة مسبقاً
        """
        cur = pg_conn.cursor()
        cur.execute('''
            -- 1. جدول فواتير نقطة البيع
            CREATE TABLE IF NOT EXISTS pos_order (
                id VARCHAR(100) PRIMARY KEY,
                session_id VARCHAR(100),
                date DATE,
                time VARCHAR(50),
                customer VARCHAR(200),
                cashier VARCHAR(100),
                payment_method VARCHAR(50) DEFAULT 'CASH',
                subtotal NUMERIC(15, 2) DEFAULT 0,
                discount NUMERIC(15, 2) DEFAULT 0,
                tax NUMERIC(15, 2) DEFAULT 0,
                net_total NUMERIC(15, 2) DEFAULT 0,
                paid_amount NUMERIC(15, 2) DEFAULT 0,
                change_amount NUMERIC(15, 2) DEFAULT 0,
                jv_id VARCHAR(100),
                status VARCHAR(50) DEFAULT 'POSTED',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- 2. بنود فواتير نقطة البيع
            CREATE TABLE IF NOT EXISTS pos_order_line (
                id SERIAL PRIMARY KEY,
                order_id VARCHAR(100) REFERENCES pos_order(id) ON DELETE CASCADE,
                product_code VARCHAR(100),
                product_name VARCHAR(200),
                qty NUMERIC(15, 2) DEFAULT 0,
                unit_price NUMERIC(15, 2) DEFAULT 0,
                cost_price NUMERIC(15, 2) DEFAULT 0,
                subtotal NUMERIC(15, 2) DEFAULT 0,
                discount NUMERIC(15, 2) DEFAULT 0,
                total NUMERIC(15, 2) DEFAULT 0
            );

            -- 3. دليل الحسابات المالية
            CREATE TABLE IF NOT EXISTS account_account (
                code VARCHAR(50) PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                type VARCHAR(50),
                balance NUMERIC(18, 2) DEFAULT 0,
                currency VARCHAR(10) DEFAULT 'YER',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- 4. القيود اليومية
            CREATE TABLE IF NOT EXISTS account_move (
                id VARCHAR(100) PRIMARY KEY,
                date DATE,
                branch VARCHAR(50) DEFAULT '01',
                description TEXT,
                status VARCHAR(50) DEFAULT 'POSTED',
                total_debit NUMERIC(18, 2) DEFAULT 0,
                total_credit NUMERIC(18, 2) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- 5. بنود القيود اليومية المزدوجة
            CREATE TABLE IF NOT EXISTS account_move_line (
                id SERIAL PRIMARY KEY,
                move_id VARCHAR(100) REFERENCES account_move(id) ON DELETE CASCADE,
                acc_code VARCHAR(50),
                acc_name VARCHAR(200),
                debit NUMERIC(18, 2) DEFAULT 0,
                credit NUMERIC(18, 2) DEFAULT 0,
                note TEXT
            );

            -- 6. الأصناف والمخزون
            CREATE TABLE IF NOT EXISTS product_product (
                code VARCHAR(100) PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                cost_price NUMERIC(15, 2) DEFAULT 0,
                sale_price NUMERIC(15, 2) DEFAULT 0,
                stock_qty NUMERIC(15, 2) DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- 7. حركات المخزون التفصيلية
            CREATE TABLE IF NOT EXISTS stock_move (
                id VARCHAR(100) PRIMARY KEY,
                date DATE,
                product_id VARCHAR(100),
                product_name VARCHAR(200),
                move_type VARCHAR(50),
                qty NUMERIC(15, 2) DEFAULT 0,
                unit_cost NUMERIC(15, 2) DEFAULT 0,
                total_value NUMERIC(15, 2) DEFAULT 0,
                source_loc VARCHAR(100),
                dest_loc VARCHAR(100),
                ref_doc VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        pg_conn.commit()

    def sync_pending_orders(self) -> Dict[str, Any]:
        """
        العملية الجوهرية: رفع كافة الفواتير المعلقة فور عودة الاتصال بخادم PostgreSQL
        وتحديث أرصدة الحسابات والمخزون ذرياً (Atomically)
        """
        with self.lock:
            # 1. إحصاء الفواتير المعلقة محلياً
            try:
                sq_conn = sqlite3.connect(self.sqlite_path)
                sq_conn.row_factory = sqlite3.Row
                sq_cur = sq_conn.cursor()
                sq_cur.execute("SELECT COUNT(*) as cnt FROM pos_order WHERE sync_status = 'pending'")
                self.pending_count = sq_cur.fetchone()['cnt']
            except Exception as e:
                sq_conn.close()
                return {"status": "error", "message": f"خطأ في قراءة SQLite: {e}"}

            if self.pending_count == 0:
                self.last_status_msg = "جميع فواتير نقاط البيع متزامنة تماماً مع الخادم."
                sq_conn.close()
                return {"status": "idle", "pending": 0, "synced": 0}

            # 2. فحص الاتصال بخادم PostgreSQL
            is_ok, pg_conn, conn_msg = self.check_postgres_connection()
            if not is_ok:
                self.is_online = False
                self.last_error = conn_msg
                self.last_status_msg = f"وضع دون اتصال (Offline): {self.pending_count} فاتورة معلقة محلياً في انتظار عودة الاتصال."
                sq_conn.close()
                return {"status": "offline", "pending": self.pending_count, "synced": 0, "message": conn_msg}

            self.is_online = True
            batch_limit = self.config.get("batch_size", 50)
            sq_cur.execute('''
                SELECT * FROM pos_order
                WHERE sync_status = 'pending'
                ORDER BY created_at ASC
                LIMIT ?
            ''', (batch_limit,))
            orders = sq_cur.fetchall()

            uploaded = 0
            failed = 0

            try:
                if self.config.get("auto_create_schema", True):
                    self.ensure_postgres_schema(pg_conn)

                pg_cur = pg_conn.cursor()

                for ord_row in orders:
                    o_id = ord_row['id']
                    o_date = ord_row['date']
                    o_method = ord_row['payment_method'] or 'CASH'
                    o_net = float(ord_row['net_total'] or 0)
                    o_sub = float(ord_row['subtotal'] or 0)
                    o_disc = float(ord_row['discount'] or 0)
                    o_tax = float(ord_row['tax'] or 0)
                    o_paid = float(ord_row['paid_amount'] or 0)
                    o_change = float(ord_row['change_amount'] or 0)
                    o_cust = ord_row['customer'] or 'عميل نقدي مباشر'
                    o_cashier = ord_row['cashier'] or 'كاشير'
                    o_time = ord_row['time'] or ''
                    o_jv = ord_row['jv_id'] or f"JV-POS-{o_id}"

                    # قراءة بنود الفاتورة من SQLite
                    sq_cur.execute("SELECT * FROM pos_order_line WHERE order_id = ?", (o_id,))
                    lines = sq_cur.fetchall()

                    # إذا لم تكن البنود في جدول البنود، استخرجها من JSON
                    parsed_lines = []
                    if lines:
                        for l in lines:
                            parsed_lines.append({
                                "code": l['product_code'],
                                "name": l['product_name'],
                                "qty": float(l['qty'] or 1),
                                "unit_price": float(l['unit_price'] or 0),
                                "cost_price": float(l['cost_price'] or 0),
                                "total": float(l['total'] or 0)
                            })
                    elif ord_row['lines_json']:
                        try:
                            parsed_lines = json.loads(ord_row['lines_json'])
                        except Exception:
                            parsed_lines = []

                    try:
                        # -------------------------------------------------------------
                        # بداية المعاملة الذرية في PostgreSQL (Transaction)
                        # -------------------------------------------------------------

                        # 1. إدراج أو تحديث الفاتورة في pos_order
                        pg_cur.execute('''
                            INSERT INTO pos_order (
                                id, session_id, date, time, customer, cashier,
                                payment_method, subtotal, discount, tax, net_total,
                                paid_amount, change_amount, jv_id, status, synced_at
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                            ON CONFLICT (id) DO UPDATE SET
                                net_total = EXCLUDED.net_total,
                                synced_at = CURRENT_TIMESTAMP
                        ''', (
                            o_id, ord_row['session_id'], o_date, o_time, o_cust, o_cashier,
                            o_method, o_sub, o_disc, o_tax, o_net, o_paid, o_change, o_jv,
                            ord_row['status'] or 'POSTED'
                        ))

                        # 2. إدراج بنود الفاتورة في pos_order_line
                        pg_cur.execute("DELETE FROM pos_order_line WHERE order_id = %s", (o_id,))
                        for pl in parsed_lines:
                            p_code = pl.get("code") or pl.get("id") or "UNKNOWN"
                            p_name = pl.get("name") or p_code
                            p_qty = float(pl.get("qty", 1) or 1)
                            p_unit = float(pl.get("unit_price", 0) or pl.get("price", 0) or 0)
                            p_cost = float(pl.get("cost_price", 0) or 0)
                            p_tot = float(pl.get("total", p_qty * p_unit) or (p_qty * p_unit))

                            pg_cur.execute('''
                                INSERT INTO pos_order_line (
                                    order_id, product_code, product_name, qty, unit_price, cost_price, subtotal, discount, total
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ''', (
                                o_id, p_code, p_name, p_qty, p_unit, p_cost, p_tot, 0, p_tot
                            ))

                            # 3. تحديث رصيد المخزون في PostgreSQL (stock_qty)
                            pg_cur.execute('''
                                INSERT INTO product_product (code, name, cost_price, sale_price, stock_qty)
                                VALUES (%s, %s, %s, %s, %s)
                                ON CONFLICT (code) DO UPDATE SET
                                    stock_qty = GREATEST(0, product_product.stock_qty - EXCLUDED.stock_qty),
                                    updated_at = CURRENT_TIMESTAMP
                            ''', (p_code, p_name, p_cost, p_unit, p_qty))

                            # 4. تسجيل حركة المخزون في PostgreSQL (stock_move)
                            sm_id = f"SM-POS-{o_id}-{p_code}"
                            pg_cur.execute('''
                                INSERT INTO stock_move (
                                    id, date, product_id, product_name, move_type, qty, unit_cost, total_value, source_loc, dest_loc, ref_doc
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (id) DO NOTHING
                            ''', (
                                sm_id, o_date, p_code, p_name, 'POS_SALE', p_qty, p_cost, p_qty * p_cost,
                                'WH01 - صالة العرض', o_cust, o_id
                            ))

                        # 5. تحديث الأرصدة المحاسبية في PostgreSQL (الحسابات المالية)
                        # تحديد حساب القبض: صندوق نقدي أو بنك أو عميل آجل
                        target_acc_code = '1121010001' if o_method == 'CASH' else ('1121020001' if o_method == 'CARD' else '1131010001')
                        target_acc_name = 'صندوق نقطة البيع الرئيسي' if o_method == 'CASH' else ('بنك التضامن الإسلامي' if o_method == 'CARD' else 'العملاء المدينون')
                        revenue_acc_code = '411101'
                        revenue_acc_name = 'إيرادات المبيعات العامة'

                        # تحديث رصيد حساب الصندوق/البنك (مدين بالصافي)
                        pg_cur.execute('''
                            INSERT INTO account_account (code, name, type, balance)
                            VALUES (%s, %s, 'ASSET', %s)
                            ON CONFLICT (code) DO UPDATE SET
                                balance = account_account.balance + EXCLUDED.balance,
                                updated_at = CURRENT_TIMESTAMP
                        ''', (target_acc_code, target_acc_name, o_net))

                        # تحديث رصيد حساب إيرادات المبيعات (دائن بالصافي)
                        pg_cur.execute('''
                            INSERT INTO account_account (code, name, type, balance)
                            VALUES (%s, %s, 'INCOME', %s)
                            ON CONFLICT (code) DO UPDATE SET
                                balance = account_account.balance + EXCLUDED.balance,
                                updated_at = CURRENT_TIMESTAMP
                        ''', (revenue_acc_code, revenue_acc_name, o_net))

                        # 6. تسجيل القيد اليومي المزدوج في PostgreSQL (account_move)
                        pg_cur.execute('''
                            INSERT INTO account_move (id, date, branch, description, status, total_debit, total_credit)
                            VALUES (%s, %s, '01', %s, 'POSTED', %s, %s)
                            ON CONFLICT (id) DO NOTHING
                        ''', (o_jv, o_date, f"مبيعات نقطة البيع رقم [{o_id}] - {o_method}", o_net, o_net))

                        # بنود القيد
                        pg_cur.execute("DELETE FROM account_move_line WHERE move_id = %s", (o_jv,))
                        pg_cur.execute('''
                            INSERT INTO account_move_line (move_id, acc_code, acc_name, debit, credit, note)
                            VALUES (%s, %s, %s, %s, 0, %s)
                        ''', (o_jv, target_acc_code, target_acc_name, o_net, f"قبض مبيعات كاشير {o_id}"))

                        pg_cur.execute('''
                            INSERT INTO account_move_line (move_id, acc_code, acc_name, debit, credit, note)
                            VALUES (%s, %s, %s, 0, %s, %s)
                        ''', (o_jv, revenue_acc_code, revenue_acc_name, o_net, f"إيراد مبيعات الفاتورة {o_id}"))

                        # تأكيد المعاملة في PostgreSQL
                        pg_conn.commit()

                        # 7. تحديث حالة الفاتورة محلياً في SQLite كمزامنة ناجحة
                        now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        sq_cur.execute('''
                            UPDATE pos_order
                            SET sync_status = 'synced', synced_at = ?, sync_error = NULL
                            WHERE id = ?
                        ''', (now_ts, o_id))
                        sq_conn.commit()

                        uploaded += 1

                    except Exception as order_err:
                        pg_conn.rollback()
                        failed += 1
                        err_str = f"خطأ رفع الفاتورة {o_id}: {order_err}"
                        print(f"[POS Sync] {err_str}", file=sys.stderr)
                        sq_cur.execute('''
                            UPDATE pos_order
                            SET sync_status = 'failed', sync_error = ?
                            WHERE id = ?
                        ''', (str(order_err), o_id))
                        sq_conn.commit()

                # إغلاق اتصالات قواعد البيانات
                try:
                    pg_conn.close()
                except Exception:
                    pass
                sq_conn.close()

                self.synced_count += uploaded
                self.failed_count += failed
                self.last_sync_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                remaining = max(0, self.pending_count - uploaded)
                self.pending_count = remaining

                if uploaded > 0:
                    self.last_status_msg = f"تمت المزامنة بنجاح: تم رفع {uploaded} فاتورة وتحديث الحسابات والمخزون في PostgreSQL (المتبقي: {remaining})."
                elif failed > 0:
                    self.last_status_msg = f"فشلت مزامنة {failed} فاتورة. سيتم إعادة المحاولة آلياً."

                return {
                    "status": "success",
                    "synced": uploaded,
                    "failed": failed,
                    "remaining": remaining,
                    "last_sync": self.last_sync_time
                }

            except Exception as e:
                try:
                    pg_conn.close()
                except Exception:
                    pass
                sq_conn.close()
                self.last_error = str(e)
                self.last_status_msg = f"خطأ عام أثناء عملية المزامنة: {e}"
                return {"status": "error", "message": str(e)}

    def trigger_immediate_sync(self):
        """إيقاظ الخيط الخلفي فوراً لتنفيذ المزامنة دون انتظار انتهاء المؤقت"""
        self.sync_event.set()

    def _worker_loop(self):
        """حلقة العمل المستمرة في الخلفية (Daemon Worker)"""
        while self.running:
            interval = int(self.config.get("sync_interval_seconds", 10))
            try:
                # محاولة المزامنة
                self.sync_pending_orders()
            except Exception as e:
                print(f"[POS Sync Daemon Error] {e}", file=sys.stderr)

            # الانتظار حتى انتهاء الفاصل الزمني أو ورود إشعار فاتورة جديدة
            self.sync_event.wait(timeout=max(2, interval))
            self.sync_event.clear()

    def start(self):
        """بدء تشغيل خدمة المزامنة الخلفية"""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._worker_loop, daemon=True, name="POS_Postgres_Sync_Worker")
        self.thread.start()
        print(f"[POS Sync] Service started successfully (Interval: {self.config.get('sync_interval_seconds', 10)}s)")

    def stop(self):
        """إيقاف خدمة المزامنة الخلفية بأمان"""
        self.running = False
        self.sync_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)
        print("[POS Sync] Service stopped.")

    def get_status(self) -> Dict[str, Any]:
        """الحصول على إحصائيات المزامنة الحالية"""
        # إعادة فحص الفواتير المعلقة في SQLite
        try:
            conn = sqlite3.connect(self.sqlite_path)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM pos_order WHERE sync_status = 'pending'")
            pending = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM pos_order WHERE sync_status = 'synced'")
            synced = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM pos_order WHERE sync_status = 'failed'")
            failed = cur.fetchone()[0]
            conn.close()
            self.pending_count = pending
        except Exception:
            pending = self.pending_count
            synced = self.synced_count
            failed = self.failed_count

        return {
            "online": self.is_online,
            "target": f"PostgreSQL ({self.config.get('host')}:{self.config.get('port')}/{self.config.get('dbname')})",
            "driver": PG_DRIVER or "None",
            "pending_count": pending,
            "synced_count": synced,
            "failed_count": failed,
            "last_sync": self.last_sync_time,
            "status_message": self.last_status_msg,
            "last_error": self.last_error,
            "sync_interval": self.config.get("sync_interval_seconds", 10)
        }

# مثيل عام للخدمة
_pos_sync_instance: Optional[POSSyncService] = None

def get_pos_sync_service(sqlite_path: str, config_path: Optional[str] = None) -> POSSyncService:
    global _pos_sync_instance
    if _pos_sync_instance is None:
        _pos_sync_instance = POSSyncService(sqlite_path, config_path)
        _pos_sync_instance.start()
    return _pos_sync_instance
