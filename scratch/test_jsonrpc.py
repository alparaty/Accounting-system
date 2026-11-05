# -*- coding: utf-8 -*-
"""
اختبار Odoo 17 JSON-RPC 2.0
"""
import json

def handle_odoo_rpc(payload, conn):
    """
    محاكي Odoo 17 JSON-RPC execute_kw
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
    
    if service == "object" and rpc_method == "execute_kw":
        # args: [db, uid, password, model, method, method_args, method_kwargs]
        if len(args) < 5:
            return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "Invalid params"}, "id": req_id}
        db = args[0]
        uid = args[1]
        password = args[2]
        model = args[3]
        model_method = args[4]
        method_args = args[5] if len(args) > 5 else []
        method_kwargs = args[6] if len(args) > 6 else kwargs
        
        table_map = {
            "account.account": "account_account",
            "account.move": "account_move",
            "account.move.line": "account_move_line",
            "account.voucher": "account_voucher",
            "res.partner": "res_partner",
            "product.product": "product_product",
            "stock.move": "stock_move",
            "audit.log": "audit_log",
            "ir.sequence": "ir_sequence"
        }
        
        table = table_map.get(model)
        if not table:
            return {"jsonrpc": "2.0", "error": {"code": -32600, "message": f"Model {model} not found"}, "id": req_id}
        
        cur = conn.cursor()
        if model_method == "search_read":
            fields = method_kwargs.get("fields", ["*"])
            fields_str = ", ".join(fields) if fields != ["*"] else "*"
            limit = method_kwargs.get("limit", 100)
            cur.execute(f"SELECT {fields_str} FROM {table} LIMIT ?", (limit,))
            cols = [col[0] for col in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
            return {"jsonrpc": "2.0", "result": rows, "id": req_id}
            
        elif model_method == "search_count":
            count = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            return {"jsonrpc": "2.0", "result": count, "id": req_id}
            
        elif model_method == "name_search":
            name = method_args[0] if method_args else ""
            cur.execute(f"SELECT id, name FROM {table} WHERE name LIKE ? LIMIT 10", (f"%{name}%",))
            results = [(r[0], r[1]) for r in cur.fetchall()]
            return {"jsonrpc": "2.0", "result": results, "id": req_id}
            
    return {"jsonrpc": "2.0", "error": {"code": -32601, "message": "Unsupported RPC operation"}, "id": req_id}

print("JSON-RPC handler logic defined successfully.")
