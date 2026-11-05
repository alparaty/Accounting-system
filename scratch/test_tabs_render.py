import urllib.request
import json
import subprocess
import time
import os
import socket
import base64

edge = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
if not os.path.exists(edge):
    edge = r'C:\Program Files\Microsoft\Edge\Application\msedge.exe'

port = 9341
proc = subprocess.Popen([edge, '--headless', f'--remote-debugging-port={port}', '--user-data-dir=C:\\Users\\AlparatY\\Desktop\\system ERP\\scratch\\temp_profile_tabs', 'file:///c:/Users/AlparatY/Desktop/system ERP/index.html'])
time.sleep(2)

def ws_call(path, method, params=None):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('localhost', port))
    key = base64.b64encode(os.urandom(16)).decode('utf-8')
    req = f'GET {path} HTTP/1.1\r\nHost: localhost:{port}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n'
    s.sendall(req.encode())
    s.recv(4096)
    
    msg = json.dumps({'id': 1, 'method': method, 'params': params or {}})
    data = msg.encode('utf-8')
    length = len(data)
    mask = os.urandom(4)
    frame = bytearray([0x81])
    if length <= 125:
        frame.append(0x80 | length)
    elif length <= 65535:
        frame.append(0x80 | 126)
        frame.extend(length.to_bytes(2, 'big'))
    else:
        frame.append(0x80 | 127)
        frame.extend(length.to_bytes(8, 'big'))
    frame.extend(mask)
    masked = bytearray(b ^ mask[i % 4] for i, b in enumerate(data))
    frame.extend(masked)
    s.sendall(frame)
    
    s.settimeout(5.0)
    raw = s.recv(65536)
    offset = 2
    l = raw[1] & 0x7f
    if l == 126:
        offset = 4
    elif l == 127:
        offset = 10
    payload = raw[offset:].decode('utf-8', errors='ignore')
    return payload

try:
    tabs = json.loads(urllib.request.urlopen(f'http://localhost:{port}/json').read())
    erp_tab = next(t for t in tabs if 'system' in t.get('url', ''))
    path = erp_tab['webSocketDebuggerUrl'].split(f':{port}')[1]
    
    # 1. Switch screen to expenses
    ws_call(path, 'Runtime.evaluate', {'expression': 'window.onyxApp.openScreen("expenses")'})
    
    # 2. Check tab switching
    test_tabs = """
    (function() {
        const tabs = ['exp_log', 'exp_due', 'exp_recurring', 'exp_payroll', 'exp_assets', 'exp_categories', 'exp_reports'];
        const results = {};
        tabs.forEach(t => {
            window.onyxApp.switchExpensesTab(t);
            const content = document.getElementById('expenses-tab-content');
            results[t] = content ? (content.children.length > 0 && content.innerHTML.length > 50) : false;
        });
        return JSON.stringify(results);
    })()
    """
    res = ws_call(path, 'Runtime.evaluate', {'expression': test_tabs})
    print('Tabs Render Result:', res)

finally:
    proc.terminate()
