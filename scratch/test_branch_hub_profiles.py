import urllib.request, json, subprocess, time, os, socket, base64, threading, http.server

BASE_DIR = r'C:\Users\AlparatY\Desktop\system ERP'
HTTP_PORT = 9989

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

CDP_PORT = 9349
temp_dir = r'C:\Users\AlparatY\Desktop\system ERP\scratch\temp_profile_branch'
if not os.path.exists(temp_dir):
    os.makedirs(temp_dir)

proc = subprocess.Popen([edge, '--headless', f'--remote-debugging-port={CDP_PORT}', f'--user-data-dir={temp_dir}', f'http://localhost:{HTTP_PORT}/index.html'])
time.sleep(3)

def ws_call(path, msg):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('localhost', CDP_PORT))
    key = base64.b64encode(os.urandom(16)).decode('utf-8')
    req = f'GET {path} HTTP/1.1\r\nHost: localhost:{CDP_PORT}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n'
    s.sendall(req.encode())
    s.recv(4096)
    
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
    s.settimeout(6.0)
    raw = s.recv(65536)
    offset = 2
    l = raw[1] & 0x7f
    if l == 126: offset = 4
    elif l == 127: offset = 10
    return raw[offset:].decode('utf-8', errors='ignore')

def eval_js(path, expr):
    res_str = ws_call(path, {'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': expr, 'returnByValue': True}})
    parsed = json.loads(res_str)
    if 'exceptionDetails' in parsed.get('result', {}):
        print("JS EXCEPTION:", parsed['result']['exceptionDetails'])
    return parsed.get('result', {}).get('result', {}).get('value')

try:
    tabs = json.loads(urllib.request.urlopen(f'http://localhost:{CDP_PORT}/json').read())
    erp_tab = next(t for t in tabs if 'index.html' in t.get('url', '') or '9989' in t.get('url', ''))
    path = erp_tab['webSocketDebuggerUrl'].split(f':{CDP_PORT}')[1]

    # Wait for Onyx to initialize
    for _ in range(20):
        check = eval_js(path, 'typeof window.onyxApp !== "undefined" && typeof window.store !== "undefined"')
        if check: break
        time.sleep(0.5)

    print("==================================================")
    print("TEST 1: Admin Mode (HQ Enterprise Classic)")
    print("==================================================")
    t1 = eval_js(path, """
    (() => {
        window.onyxApp.switchUser('USR-01');
        const ent = document.getElementById('enterprise-app-container');
        const branch = document.getElementById('branch-hub-container');
        const user = window.store.getCurrentUser();
        const treeItems = document.querySelectorAll('.onyx-tree-item');
        return {
            userId: user.id,
            uiMode: user.uiMode,
            entVisible: ent && ent.style.display !== 'none',
            branchHidden: branch && branch.style.display === 'none',
            classicScreensCount: treeItems.length
        };
    })()
    """)
    print("Admin Mode Check:", t1)
    assert t1['uiMode'] == 'ENTERPRISE', "Admin must have ENTERPRISE mode"
    assert t1['entVisible'], "Enterprise container must be visible"
    assert t1['branchHidden'], "Branch hub container must be hidden"
    assert t1['classicScreensCount'] >= 18, "Classic 18 screens must be present"

    print("\n==================================================")
    print("TEST 2: Cashier Mode (Branch Retail Hub)")
    print("==================================================")
    t2 = eval_js(path, """
    (() => {
        window.onyxApp.switchUser('USR-02');
        const ent = document.getElementById('enterprise-app-container');
        const branch = document.getElementById('branch-hub-container');
        const user = window.store.getCurrentUser();
        const btns = document.querySelectorAll('.profile-action-btn');
        return {
            userId: user.id,
            uiMode: user.uiMode,
            entHidden: ent && ent.style.display === 'none',
            branchVisible: branch && branch.style.display !== 'none',
            profilesCount: btns.length
        };
    })()
    """)
    print("Cashier Mode Check:", t2)
    assert t2['uiMode'] == 'BRANCH_HUB', "Cashier must have BRANCH_HUB mode"
    assert t2['entHidden'], "Enterprise container must be hidden for Cashier"
    assert t2['branchVisible'], "Branch hub container must be visible for Cashier"
    assert t2['profilesCount'] >= 4, "Must have profile buttons in sidebar"

    print("\n==================================================")
    print("TEST 3: Profile Switching & Theme Colors")
    print("==================================================")
    t3 = eval_js(path, """
    (() => {
        // 1. Click Cash Retail Profile
        window.onyxApp.renderDynamicInvoiceScreen('prof_cash_retail');
        const header1 = document.querySelector('.branch-invoice-header');
        const color1 = header1 ? header1.style.backgroundColor : '';
        const hasSerial1 = !!document.querySelector('.branch-row-serial');
        const hasGift1 = !!document.querySelector('.branch-row-gift');

        // 2. Click Serialized Devices Profile
        window.onyxApp.renderDynamicInvoiceScreen('prof_serialized_devices');
        const header2 = document.querySelector('.branch-invoice-header');
        const color2 = header2 ? header2.style.backgroundColor : '';
        const hasSerial2 = !!document.querySelector('.branch-row-serial');
        const hasGift2 = !!document.querySelector('.branch-row-gift');

        return {
            color1,
            hasSerial1,
            hasGift1,
            color2,
            hasSerial2,
            hasGift2
        };
    })()
    """)
    print("Profile Switching Check:", t3)
    assert not t3['hasSerial1'], "Retail cash profile must NOT have serial tracking"
    assert not t3['hasGift1'], "Retail cash profile must NOT have gift column"
    assert t3['hasSerial2'], "Serialized profile MUST have serial tracking column"
    assert t3['hasGift2'], "Serialized profile MUST have gift column"

    print("\n==================================================")
    print("TEST 4: Price Intelligence Context & Right-Click Dropdown")
    print("==================================================")
    t4 = eval_js(path, """
    (() => {
        const ctx = window.store.getItemPriceContext('ITM-101', '1131010001');
        
        // Test context menu opening on table row
        const tr = document.querySelector('#branchItemsTableBody tr');
        const priceInputBefore = tr.querySelector('.branch-row-price').value;
        
        // Trigger bindGridContextMenu directly
        const dummyEvent = { preventDefault: () => {}, stopPropagation: () => {}, pageX: 200, pageY: 200 };
        window.onyxApp.bindGridContextMenu(dummyEvent, tr);
        
        const menu = document.getElementById('gridContextMenu');
        const menuVisible = menu && menu.style.display !== 'none';
        
        // Drop wholesale price
        window.onyxApp.dropPriceIntoRow(ctx.priceTiers.wholesale, 'سعر الجملة');
        const priceInputAfter = tr.querySelector('.branch-row-price').value;

        return {
            itemName: ctx.itemName,
            retail: ctx.priceTiers.retail,
            wholesale: ctx.priceTiers.wholesale,
            semiWholesale: ctx.priceTiers.semiWholesale,
            distributor: ctx.priceTiers.distributor,
            marginAmount: ctx.profitMargins.expectedProfitAmount,
            menuVisible,
            priceInputBefore,
            priceInputAfter
        };
    })()
    """)
    print("Price Intelligence & Dropdown Check:", t4)
    assert t4['wholesale'] > 0, "Wholesale price must be greater than zero"
    assert t4['marginAmount'] > 0, "Profit margin must be greater than zero"
    assert t4['menuVisible'], "Context menu should have been rendered and displayed"
    assert str(t4['wholesale']) == str(t4['priceInputAfter']), f"Wholesale price should drop into input ({t4['wholesale']} vs {t4['priceInputAfter']})"

    print("\n==================================================")
    print("TEST 5: Branch Data Scoping")
    print("==================================================")
    t5 = eval_js(path, """
    (() => {
        // User 02 is Branch 01 (Sanaa)
        window.store.setCurrentUser('USR-02');
        const wh1 = window.store.getScopedWarehouses();
        const cb1 = window.store.getScopedCashBoxes();

        // User 03 is Branch 02 (Aden)
        window.store.setCurrentUser('USR-03');
        const wh2 = window.store.getScopedWarehouses();
        const cb2 = window.store.getScopedCashBoxes();

        // User 01 is Admin (HQ)
        window.store.setCurrentUser('USR-01');
        const whAdmin = window.store.getScopedWarehouses();
        const cbAdmin = window.store.getScopedCashBoxes();

        return {
            wh1Codes: wh1.map(w => w.code),
            cb1Codes: cb1.map(c => c.code),
            wh2Codes: wh2.map(w => w.code),
            cb2Codes: cb2.map(c => c.code),
            whAdminCount: whAdmin.length,
            cbAdminCount: cbAdmin.length
        };
    })()
    """)
    print("Branch Scoping Check:", t5)
    assert 'WH01' in t5['wh1Codes'] and 'WH02' not in t5['wh1Codes'], "Branch 01 cashier should only see WH01"
    assert '0101' in t5['cb1Codes'] and '0201' not in t5['cb1Codes'], "Branch 01 cashier should only see 0101 cashbox"
    assert 'WH02' in t5['wh2Codes'] and 'WH01' not in t5['wh2Codes'], "Branch 02 cashier should only see WH02"
    assert '0201' in t5['cb2Codes'] and '0101' not in t5['cb2Codes'], "Branch 02 cashier should only see 0201 cashbox"
    assert t5['whAdminCount'] >= 2, "Admin should see all warehouses"

    print("\n==================================================")
    print("TEST 6: Invoice Submission & Review Center Integration")
    print("==================================================")
    t6 = eval_js(path, """
    (() => {
        window.onyxApp.switchUser('USR-02');
        window.onyxApp.renderDynamicInvoiceScreen('prof_serialized_devices');
        
        // Submit invoice
        const invNo = document.getElementById('branch-inv-no').value;
        window.onyxApp.submitBranchInvoice();
        
        // Switch to Admin and check review & posting center
        window.onyxApp.switchUser('USR-01');
        window.onyxApp.openScreen('review_posting');
        
        const invoice = window.store.state.salesInvoices.find(s => s.invNo === invNo);
        return {
            invNo,
            invFound: !!invoice,
            status: invoice ? invoice.status : null,
            serial: (invoice && invoice.items[0]) ? invoice.items[0].serial : null,
            branch: invoice ? invoice.branch : null
        };
    })()
    """)
    print("Invoice Lifecycle in Review Center:", t6)
    assert t6['invFound'], "Branch invoice must be stored in salesInvoices"
    assert t6['status'] == 'قيد المراجعة', "Invoice status must be 'قيد المراجعة' for review & posting"
    assert t6['branch'] == '01', "Invoice must be recorded under user branch '01'"
    assert t6['serial'] and 'SN-' in t6['serial'], "Serialized invoice must record serial numbers"

    print("\n🎉 ALL ACCEPTANCE TESTS PASSED 100%! SYSTEM FULLY CERTIFIED!")

finally:
    proc.terminate()
    server.shutdown()
