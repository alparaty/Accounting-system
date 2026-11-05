import urllib.request, json, subprocess, time, os, socket, base64

edge = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
if not os.path.exists(edge):
    edge = r'C:\Program Files\Microsoft\Edge\Application\msedge.exe'

port = 9339
temp_profile = r'c:\Users\AlparatY\Desktop\system ERP\scratch\temp_profile_sales'
index_url = 'file:///' + os.path.abspath(r'c:\Users\AlparatY\Desktop\system ERP\index.html').replace('\\', '/')

proc = subprocess.Popen([edge, '--headless', f'--remote-debugging-port={port}', f'--user-data-dir={temp_profile}', index_url])
time.sleep(2.5)

def ws_call(path, msg):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('localhost', port))
    key = base64.b64encode(os.urandom(16)).decode('utf-8')
    req = f'GET {path} HTTP/1.1\r\nHost: localhost:{port}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n'
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
    tabs = json.loads(urllib.request.urlopen(f'http://localhost:{port}/json').read())
    erp_tab = next(t for t in tabs if 'index.html' in t.get('url', '') or 'system' in t.get('url', ''))
    path = erp_tab['webSocketDebuggerUrl'].split(f':{port}')[1]

    for _ in range(20):
        check = eval_js(path, 'typeof window.onyxApp !== "undefined" && typeof window.store !== "undefined"')
        if check:
            break
        time.sleep(0.5)

    print("--- 1. Testing Review & Posting on Initial Load ---")
    res1 = eval_js(path, """
    (() => {
        window.onyxApp.openScreen('review_posting');
        const salesInvoices = window.store.state.salesInvoices;
        const rows = document.querySelectorAll('.onyx-grid tbody tr');
        return {
            salesCount: salesInvoices.length,
            firstInv: salesInvoices[0] ? salesInvoices[0].invNo : null,
            rowCount: rows.length,
            hasSalesInTable: Array.from(rows).some(r => r.innerText.includes('فاتورة مبيعات'))
        };
    })()
    """)
    print("Step 1 Initial Review:", res1)
    assert res1['salesCount'] >= 1, "Should have initial sales invoices"
    assert res1['hasSalesInTable'], "Table must display sales invoice in Review & Posting Center"

    print("\n--- 2. Testing Filter SALES tab in Review & Posting ---")
    res2 = eval_js(path, """
    (() => {
        window.onyxApp.setReviewFilter('SALES');
        const rows = document.querySelectorAll('.onyx-grid tbody tr');
        return {
            rowCount: rows.length,
            tableText: document.querySelector('.onyx-grid tbody').innerText
        };
    })()
    """)
    print("Step 2 SALES Tab Rows:", res2['rowCount'])
    assert 'فاتورة مبيعات' in res2['tableText'], "SALES tab must show sales invoices"
    assert 'اعتماد' in res2['tableText'], "Should show review button"

    print("\n--- 3. Testing Adding Invoice via Excel Row in Sales Screen ---")
    res3 = eval_js(path, """
    (() => {
        window.onyxApp.openScreen('sales');
        const countBefore = window.store.state.salesInvoices.length;
        window.onyxApp.insertSalesExcelRow();
        const countAfter = window.store.state.salesInvoices.length;
        return {
            countBefore,
            countAfter,
            newestInv: window.store.state.salesInvoices[window.store.state.salesInvoices.length - 1]
        };
    })()
    """)
    print("Step 3 Insert Excel Row:", res3)
    assert res3['countAfter'] > res3['countBefore'], "insertSalesExcelRow must add to store.state.salesInvoices"

    print("\n--- 4. Testing Adding Invoice via Modal [F6] ---")
    res4 = eval_js(path, """
    (() => {
        window.onyxApp.openAddSalesInvoiceModal();
        const statusSelect = document.getElementById('sinv-status');
        const defaultStatus = statusSelect ? statusSelect.value : null;
        document.getElementById('sinv-gross').value = '350000';
        document.getElementById('sinv-discount').value = '15000';
        window.onyxApp.onSalesModalCalc();
        window.onyxApp.submitSalesInvoice();
        const newest = window.store.state.salesInvoices[0];
        return {
            defaultStatus,
            newestId: newest.id,
            newestInvNo: newest.invNo,
            newestStatus: newest.status,
            netAmount: newest.netAmount
        };
    })()
    """)
    print("Step 4 Modal Add:", res4)
    assert res4['defaultStatus'] == 'قيد المراجعة', "Default status in modal must be 'قيد المراجعة'"
    assert res4['newestStatus'] == 'قيد المراجعة', "Added invoice must be 'قيد المراجعة'"
    assert res4['netAmount'] == 335000, "Net amount must be 335,000"

    print("\n--- 5. Review & Post Workflow in Review & Posting Center ---")
    res5 = eval_js(path, f"""
    (() => {{
        window.onyxApp.openScreen('review_posting');
        window.onyxApp.setReviewFilter('SALES');
        const targetInv = '{res4["newestInvNo"]}';
        // 1. Review doc
        window.onyxApp.reviewDoc('SALES_INVOICE', targetInv);
        const statusAfterReview = window.store.state.salesInvoices.find(s => s.invNo === targetInv).status;
        // 2. Post doc
        window.onyxApp.postDoc('SALES_INVOICE', targetInv);
        const statusAfterPost = window.store.state.salesInvoices.find(s => s.invNo === targetInv).status;
        const jv = window.store.state.journalEntries.find(j => j.id === `JV-INV-${{targetInv}}`);
        return {{
            statusAfterReview,
            statusAfterPost,
            jvCreated: !!jv,
            jvDesc: jv ? jv.desc : null
        }};
    }})()
    """)
    print("Step 5 Review & Post Result:", res5)
    assert res5['statusAfterReview'] == 'REVIEWED', "Invoice should be REVIEWED"
    assert res5['statusAfterPost'] == 'POSTED', "Invoice should be POSTED"
    assert res5['jvCreated'], "Journal entry JV-INV must be created"

    print("\n--- 6. One-Click Review & Post (reviewAndPostDoc) ---")
    res6 = eval_js(path, """
    (() => {
        window.onyxApp.insertSalesExcelRow();
        const newest = window.store.state.salesInvoices[window.store.state.salesInvoices.length - 1];
        window.onyxApp.openScreen('review_posting');
        window.onyxApp.setReviewFilter('SALES');
        window.onyxApp.reviewAndPostDoc('SALES_INVOICE', newest.invNo);
        const inv = window.store.state.salesInvoices.find(s => s.invNo === newest.invNo);
        const jv = window.store.state.journalEntries.find(j => j.id === `JV-INV-${newest.invNo}`);
        return {
            invStatus: inv.status,
            jvCreated: !!jv
        };
    })()
    """)
    print("Step 6 Quick Review & Post Result:", res6)
    assert res6['invStatus'] == 'POSTED', "Invoice should be POSTED"
    assert res6['jvCreated'], "Journal entry must be created"

    print("\n--- 7. View Journal Modal Check ---")
    res7 = eval_js(path, f"""
    (() => {{
        window.onyxApp.viewJournal('{res4["newestInvNo"]}');
        const modalTitle = document.querySelector('.onyx-modal-title')?.innerText;
        const modalBody = document.querySelector('.onyx-modal-body')?.innerText;
        window.onyxApp.closeModal();
        return {{
            hasModal: !!modalTitle,
            title: modalTitle,
            hasCreditDebit: modalBody ? (modalBody.includes('مدين') || modalBody.includes('دائن')) : false
        }};
    }})()
    """)
    print("Step 7 View Journal Modal:", res7)
    assert res7['hasModal'], "Modal must open for journal"

    print("\n--- 8. Trial Balance Balance Check ---")
    res8 = eval_js(path, """
    (() => {
        const trial = window.store.generateTrialBalance();
        const sumDebit = trial.reduce((s, r) => s + r.debit, 0);
        const sumCredit = trial.reduce((s, r) => s + r.credit, 0);
        const isBalanced = Math.abs(sumDebit - sumCredit) < 0.01;
        return {
            sumDebit,
            sumCredit,
            isBalanced
        };
    })()
    """)
    print("Step 8 Trial Balance:", res8)
    assert res8['isBalanced'], f"Trial balance must balance! Debit={res8['sumDebit']}, Credit={res8['sumCredit']}"

    print("\n🎉 ALL TESTS PASSED SUCCESSFULLY! Sales invoices appear correctly across all screens, filters, and audit stages.")

finally:
    proc.terminate()
