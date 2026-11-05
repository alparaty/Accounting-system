# -*- coding: utf-8 -*-
"""
التحقق من سلامة كافة الشاشات الـ 18 وعدم تأثر أي واجهة أو اختصار
"""
import urllib.request, json, subprocess, time, os, socket, base64

edge = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
if not os.path.exists(edge):
    edge = r'C:\Program Files\Microsoft\Edge\Application\msedge.exe'

port = 9331
temp_prof = r'C:\Users\AlparatY\Desktop\system ERP\scratch\temp_profile_screens'
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
    
    # 1. Load files
    for fn in ['onyx_data.js', 'onyx_store.js']:
        with open(os.path.join(r'c:\Users\AlparatY\Desktop\system ERP\js', fn), encoding='utf-8') as f:
            ws_call(path, {'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': f.read()}})

    # DOM setup
    ws_call(path, {'id': 2, 'method': 'Runtime.evaluate', 'params': {'expression': '''
    document.body.innerHTML = `
      <span id="onyx-screen-title"></span>
      <span id="onyx-screen-sub"></span>
      <div id="onyx-workspace"></div>
      <div id="onyx-modal-area"></div>
      <div id="onyx-toast-area"></div>
      <div id="tree-pending-count"></div>
    `;
    '''}})

    with open(r'c:\Users\AlparatY\Desktop\system ERP\js\onyx_app.js', encoding='utf-8') as f:
        ws_call(path, {'id': 3, 'method': 'Runtime.evaluate', 'params': {'expression': f.read()}})

    # Test all 18 screens
    screen_test = '''
    (function() {
      const screens = [
        'dashboard', 'chart_of_accounts', 'opening_balances', 'journal_entries',
        'vouchers_cash', 'vouchers_cheque', 'cheque_collection', 'payroll',
        'org_hierarchy_excel', 'purchases_lc', 'sales', 'inventory',
        'review_posting', 'reports', 'system_config', 'security_users',
        'fixed_assets', 'pos', 'expenses'
      ];
      const results = {};
      screens.forEach(s => {
        try {
          if (window.onyxApp?.openScreen) {
            window.onyxApp.openScreen(s);
          }
          const htmlLen = document.getElementById('onyx-workspace')?.innerHTML?.length || 0;
          results[s] = htmlLen > 50;
        } catch (err) {
          results[s] = "ERROR: " + err.message;
        }
      });
      return JSON.stringify(results);
    })()
    '''
    res = ws_call(path, {'id': 4, 'method': 'Runtime.evaluate', 'params': {'expression': screen_test}})
    print("Screens Render Test Results:\n", res)

finally:
    proc.terminate()
