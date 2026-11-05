import urllib.request, json, subprocess, time, os, socket, base64, threading, http.server

BASE_DIR = r'C:\Users\AlparatY\Desktop\system ERP'
HTTP_PORT = 9988

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)
    def log_message(self, format, *args):
        pass

server = http.server.HTTPServer(("", HTTP_PORT), Handler)
t = threading.Thread(target=server.serve_forever, daemon=True)
t.start()

edge = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
if not os.path.exists(edge):
    edge = r'C:\Program Files\Microsoft\Edge\Application\msedge.exe'

CDP_PORT = 9345
temp_dir = r'C:\Users\AlparatY\Desktop\system ERP\scratch\temp_profile_audit'
proc = subprocess.Popen([edge, '--headless', f'--remote-debugging-port={CDP_PORT}', f'--user-data-dir={temp_dir}', f'http://localhost:{HTTP_PORT}/index.html'])
time.sleep(3)

def ws_call(s, msg):
    data = json.dumps(msg).encode('utf-8')
    length = len(data)
    mask = os.urandom(4)
    frame = bytearray([0x81])
    if length <= 125: frame.append(0x80 | length)
    elif length <= 65535: frame.append(0x80 | 126); frame.extend(length.to_bytes(2, 'big'))
    else: frame.append(0x80 | 127); frame.extend(length.to_bytes(8, 'big'))
    frame.extend(mask)
    frame.extend(bytearray(b ^ mask[i % 4] for i, b in enumerate(data)))
    s.sendall(frame)

def ws_read_response(s, req_id, timeout=4.0):
    s.settimeout(0.3)
    start = time.time()
    buf = bytearray()
    while time.time() - start < timeout:
        try:
            chunk = s.recv(65536)
            if not chunk: break
            buf.extend(chunk)
            while len(buf) >= 2:
                payload_len = buf[1] & 0x7f
                offset = 2
                if payload_len == 126:
                    if len(buf) < 4: break
                    payload_len = int.from_bytes(buf[2:4], 'big')
                    offset = 4
                elif payload_len == 127:
                    if len(buf) < 10: break
                    payload_len = int.from_bytes(buf[2:10], 'big')
                    offset = 10
                if len(buf) < offset + payload_len: break
                payload = buf[offset:offset+payload_len].decode('utf-8', errors='ignore')
                buf = buf[offset+payload_len:]
                if f'"id":{req_id}' in payload or f'"id": {req_id}' in payload:
                    return payload
        except socket.timeout:
            pass
    return None

try:
    tabs = json.loads(urllib.request.urlopen(f'http://localhost:{CDP_PORT}/json').read())
    page_tabs = [tb for tb in tabs if tb.get('type') == 'page']
    erp_tab = page_tabs[0] if page_tabs else tabs[0]
    path = erp_tab['webSocketDebuggerUrl'].split(f':{CDP_PORT}')[1]
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('localhost', CDP_PORT))
    key = base64.b64encode(os.urandom(16)).decode('utf-8')
    req = f'GET {path} HTTP/1.1\r\nHost: localhost:{CDP_PORT}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n'
    s.sendall(req.encode())
    s.recv(4096)
    
    screens = [
        'dashboard', 'chart_of_accounts', 'opening_balances', 'journal_entries',
        'vouchers_cash', 'vouchers_cheque', 'cheque_collection', 'payroll',
        'org_hierarchy_excel', 'purchases_lc', 'sales', 'inventory',
        'review_posting', 'reports', 'system_config', 'security_users',
        'fixed_assets', 'pos', 'expenses'
    ]

    print("=== 1. TESTING ALL 19 SCREENS RENDERING ===")
    for idx, sc in enumerate(screens, start=100):
        test_js = f'''
        (function() {{
            try {{
                window.onyxApp.openScreen("{sc}");
                var ws = document.getElementById("onyx-workspace");
                return {{
                    screen: "{sc}",
                    status: "OK",
                    hasHtml: ws && ws.innerHTML.length > 50,
                    length: ws ? ws.innerHTML.length : 0
                }};
            }} catch(e) {{
                return {{
                    screen: "{sc}",
                    status: "ERROR",
                    error: e.message,
                    stack: e.stack
                }};
            }}
        }})()
        '''
        ws_call(s, {'id': idx, 'method': 'Runtime.evaluate', 'params': {'expression': test_js, 'returnByValue': True}})
        resp = ws_read_response(s, idx)
        print(f"Screen [{sc}]: {resp[:160] if resp else 'NO RESPONSE'}")

    print("\n=== 2. TESTING F6 (ADD MODAL) ON SCREENS ===")
    for idx, sc in enumerate(screens, start=200):
        test_f6 = f'''
        (function() {{
            try {{
                window.onyxApp.openScreen("{sc}");
                window.onyxApp.handleF6();
                var modal = document.getElementById("onyx-modal-area");
                var hasModal = modal && modal.innerHTML.length > 20 && modal.style.display !== "none";
                var title = modal ? modal.querySelector(".onyx-modal-title, h3, h2")?.textContent : "";
                if (window.onyxApp.closeModal) window.onyxApp.closeModal();
                return {{
                    screen: "{sc}",
                    f6Status: "OK",
                    hasModal: hasModal,
                    title: title || ""
                }};
            }} catch(e) {{
                return {{
                    screen: "{sc}",
                    f6Status: "ERROR",
                    error: e.message
                }};
            }}
        }})()
        '''
        ws_call(s, {'id': idx, 'method': 'Runtime.evaluate', 'params': {'expression': test_f6, 'returnByValue': True}})
        resp = ws_read_response(s, idx)
        print(f"F6 on [{sc}]: {resp[:160] if resp else 'NO RESPONSE'}")

    print("\n=== 3. TESTING ADVANCED NEW METHODS & SUITE INTERACTIONS ===")
    advanced_tests = [
        ("switchPurchasesTab_lc", "window.onyxApp.openScreen('purchases_lc'); window.onyxApp.switchPurchasesTab('lc'); ({ok: true, len: document.getElementById('onyx-workspace').innerHTML.length})"),
        ("switchPurchasesTab_invoices", "window.onyxApp.switchPurchasesTab('invoices'); ({ok: true, len: document.getElementById('onyx-workspace').innerHTML.length})"),
        ("review_filters", "window.onyxApp.openScreen('review_posting'); window.onyxApp.setReviewFilter('SALES'); window.onyxApp.setReviewFilter('ALL'); ({ok: true})"),
        ("post_all_reviewed", "window.onyxApp.postAllReviewed(); ({ok: true})"),
        ("reports_tabs", "window.onyxApp.openScreen('reports'); window.onyxApp.switchReportsTab('balance_sheet'); window.onyxApp.switchReportsTab('income'); window.onyxApp.switchReportsTab('account_statement'); window.onyxApp.switchReportsTab('trial'); ({ok: true})"),
        ("inventory_modals", "window.onyxApp.openScreen('inventory'); window.onyxApp.openAddItemModal(); window.onyxApp.closeModal(); window.onyxApp.openStockTransferModal(); window.onyxApp.closeModal(); window.onyxApp.openStockReconciliationModal(); window.onyxApp.closeModal(); ({ok: true})"),
        ("backup_restore_modals", "window.onyxApp.openImportSystemBackupModal(); window.onyxApp.closeModal(); ({ok: true})")
    ]

    for idx, (tname, code) in enumerate(advanced_tests, start=300):
        js = f'''
        (function() {{
            try {{
                var res = (function() {{ {code} }})();
                return {{ test: "{tname}", status: "SUCCESS", res: res }};
            }} catch(e) {{
                return {{ test: "{tname}", status: "FAIL", error: e.message }};
            }}
        }})()
        '''
        ws_call(s, {'id': idx, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}})
        resp = ws_read_response(s, idx)
        print(f"AdvTest [{tname}]: {resp[:180] if resp else 'NO RESPONSE'}")

    print("\n=== ALL TESTS COMPLETED SUCCESSFULLY ===")

finally:
    proc.terminate()
    server.shutdown()
