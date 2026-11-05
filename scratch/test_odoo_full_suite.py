# -*- coding: utf-8 -*-
"""
اختبار شامل لكافة آليات Odoo 17 الجديدة ومطابقة سلامة واجهات المستخدم في نظام البرطي
"""
import urllib.request, json, subprocess, time, os, socket, base64

edge = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
if not os.path.exists(edge):
    edge = r'C:\Program Files\Microsoft\Edge\Application\msedge.exe'

port = 9332
temp_prof = r'C:\Users\AlparatY\Desktop\system ERP\scratch\temp_profile_odoo'
proc = subprocess.Popen([edge, '--headless', f'--remote-debugging-port={port}', f'--user-data-dir={temp_prof}', 'about:blank'])
time.sleep(2)

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
    s.settimeout(10.0)
    raw = s.recv(65536)
    offset = 2
    l = raw[1] & 0x7f
    if l == 126: offset = 4
    elif l == 127: offset = 10
    return raw[offset:].decode('utf-8', errors='ignore')

try:
    tabs = json.loads(urllib.request.urlopen(f'http://localhost:{port}/json').read())
    path = tabs[0]['webSocketDebuggerUrl'].split(f':{port}')[1]
    
    # 1. تحميل onyx_data.js
    with open(r'c:\Users\AlparatY\Desktop\system ERP\js\onyx_data.js', encoding='utf-8') as f:
        data_code = f.read()
    res1 = ws_call(path, {'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': data_code}})
    print('1. Evaluate onyx_data.js:', res1[:150])

    # 2. تحميل onyx_store.js
    with open(r'c:\Users\AlparatY\Desktop\system ERP\js\onyx_store.js', encoding='utf-8') as f:
        store_code = f.read()
    res2 = ws_call(path, {'id': 2, 'method': 'Runtime.evaluate', 'params': {'expression': store_code}})
    print('2. Evaluate onyx_store.js:', res2[:150])

    # 3. إعداد عناصر DOM لواجهات أونكس
    dom_setup = '''
    document.body.innerHTML = `
      <span id="onyx-screen-title"></span>
      <span id="onyx-screen-sub"></span>
      <div id="onyx-workspace"></div>
      <div id="onyx-modal-area"></div>
      <div id="onyx-toast-area"></div>
      <div id="tree-pending-count"></div>
    `;
    '''
    ws_call(path, {'id': 3, 'method': 'Runtime.evaluate', 'params': {'expression': dom_setup}})

    # 4. تحميل onyx_app.js
    with open(r'c:\Users\AlparatY\Desktop\system ERP\js\onyx_app.js', encoding='utf-8') as f:
        app_code = f.read()
    res4 = ws_call(path, {'id': 4, 'method': 'Runtime.evaluate', 'params': {'expression': app_code}})
    print('4. Evaluate onyx_app.js:', res4[:150])

    # 5. اختبار آليات Odoo 17 في Store
    test_script = '''
    (function() {
      const store = window.onyxStore;
      const results = {};

      // أ. اختبار تسلسلات Odoo (ir.sequence)
      const seq1 = store.getNextSequence('JV', 'JV', 3);
      const seq2 = store.getNextSequence('JV', 'JV', 3);
      results.sequenceWorks = seq1 !== seq2 && seq1.startsWith('JV-');

      // ب. اختبار دقة العملات (res.currency.round)
      results.currencyRounding = store.roundCurrency(1234.5678, 'YER') === 1234.57;

      // ج. اختبار فحص التكرار الهرمي (_check_recursion)
      let recursionCaught = false;
      try {
        store.checkAccountRecursion('11', '11');
      } catch (e) {
        recursionCaught = true;
      }
      results.recursionDetected = recursionCaught;

      // د. اختبار حركات المخزون (stock.move)
      const sm = store.recordStockMove({
        productId: 'ITM-TEST',
        productName: 'صنف تجريبي',
        moveType: 'PURCHASE_RECEIPT',
        qty: 10,
        unitCost: 500,
        sourceLoc: 'المورد',
        destLoc: 'WH01'
      });
      results.stockMoveRecorded = !!sm && sm.totalValue === 5000 && (store.state.stockMoves || []).length > 0;

      // هـ. اختبار سجل التدقيق (mail.thread / tracking)
      const audit = store.logAudit({
        actionType: 'TEST_ACTION',
        docId: 'DOC-01',
        docModel: 'test.model',
        details: 'تفاصيل تجريبية'
      });
      results.auditRecorded = !!audit && (store.state.auditLogs || []).length > 0;

      // و. اختبار معالج فروق العملات (Exchange Difference)
      const fxEntry = store.postExchangeDifference({
        docType: 'account.voucher',
        docId: 'PV-USD-01',
        currency: 'USD',
        transactionRate: 530,
        settlementRate: 535,
        foreignAmount: 100,
        partnerName: 'مورد أجنبي'
      });
      results.fxDifferencePosted = !!fxEntry && fxEntry.lines.length === 2;

      // ز. اختبار معالج الترحيل الجماعي (Batch Post Wizard)
      const draftJv = store.addJournalEntry({
        desc: 'قيد مراجع للترحيل الجماعي',
        lines: [
          { accCode: '1121010001', debit: 1000, credit: 0 },
          { accCode: '411101', debit: 0, credit: 1000 }
        ]
      });
      store.reviewDocument('JV', draftJv.id);
      const batchRes = store.batchPostWizard([{ type: 'JV', id: draftJv.id }]);
      results.batchPostSuccess = batchRes.postedCount === 1;

      // ح. اختبار إحصائيات الشريك والصنف (Smart Stat Counters)
      const partnerStats = store.getPartnerStats('1131010001');
      const itemStats = store.getItemStats('ITM-TEST');
      results.smartStatsWork = typeof partnerStats === 'object' && typeof itemStats === 'object';

      // ط. اختبار الأرشفة (Active / Soft delete)
      const archOk = store.archiveRecord('accounts', '1121010001');
      const archivedAcc = (store.state.accounts || []).find(a => a.code === '1121010001');
      results.archiveWorks = archOk && archivedAcc && archivedAcc.active === false;

      // ي. التأكد من بقاء واجهات المستخدم تعمل بامتياز
      results.hasOnyxApp = typeof window.onyxApp === 'object';
      results.workspaceLoaded = document.getElementById('onyx-workspace')?.innerHTML?.length > 0;

      return JSON.stringify(results);
    })()
    '''
    res5 = ws_call(path, {'id': 5, 'method': 'Runtime.evaluate', 'params': {'expression': test_script}})
    print('5. Odoo Test Suite Results:\n', res5)

finally:
    proc.terminate()
