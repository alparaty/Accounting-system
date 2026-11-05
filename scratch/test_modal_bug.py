import urllib.request, json, subprocess, time, os, socket, base64

edge = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
if not os.path.exists(edge):
    edge = r'C:\Program Files\Microsoft\Edge\Application\msedge.exe'

port = 9348
proc = subprocess.Popen([edge, '--headless', f'--remote-debugging-port={port}', '--user-data-dir=C:\\Users\\AlparatY\\Desktop\\system ERP\\scratch\\temp_profile10', 'about:blank'])
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
    s.settimeout(5.0)
    raw = s.recv(65536)
    offset = 2
    l = raw[1] & 0x7f
    if l == 126: offset = 4
    elif l == 127: offset = 10
    return raw[offset:].decode('utf-8', errors='ignore')

try:
    tabs = json.loads(urllib.request.urlopen(f'http://localhost:{port}/json').read())
    path = tabs[0]['webSocketDebuggerUrl'].split(f':{port}')[1]
    
    ws_call(path, {'id': 1, 'method': 'Runtime.enable'})
    
    with open(r'c:\Users\AlparatY\Desktop\system ERP\js\onyx_data.js', encoding='utf-8') as f:
        ws_call(path, {'id': 2, 'method': 'Runtime.evaluate', 'params': {'expression': f.read()}})
    with open(r'c:\Users\AlparatY\Desktop\system ERP\js\onyx_store.js', encoding='utf-8') as f:
        ws_call(path, {'id': 3, 'method': 'Runtime.evaluate', 'params': {'expression': f.read()}})
    
    dom_setup = '''
    document.body.innerHTML = `
      <div id="onyx-screen-title"></div>
      <div id="onyx-screen-sub"></div>
      <div id="onyx-workspace"></div>
      <div id="onyx-modal-area" class="onyx-modal-backdrop"></div>
      <div id="tree-pending-count"></div>
      <div id="onyx-toast-area"></div>
    `;
    '''
    ws_call(path, {'id': 4, 'method': 'Runtime.evaluate', 'params': {'expression': dom_setup}})
    with open(r'c:\Users\AlparatY\Desktop\system ERP\js\onyx_app.js', encoding='utf-8') as f:
        ws_call(path, {'id': 5, 'method': 'Runtime.evaluate', 'params': {'expression': f.read()}})

    # Simulate opening QuickAddMenuModal then clicking "قيد محاسبي عام [F6]"
    sim_click = '''
    window.onyxApp.openQuickAddMenuModal();
    // Simulate what line 2605 does:
    window.onyxApp.closeModal();
    window.onyxApp.openAddJournalModal();
    '''
    ws_call(path, {'id': 6, 'method': 'Runtime.evaluate', 'params': {'expression': sim_click}})
    
    # Check immediately
    chk_immediate = 'JSON.stringify({ innerLen: document.getElementById("onyx-modal-area").innerHTML.length, active: document.getElementById("onyx-modal-area").classList.contains("active") })'
    res_imm = ws_call(path, {'id': 7, 'method': 'Runtime.evaluate', 'params': {'expression': chk_immediate}})
    print('IMMEDIATE:', res_imm)
    
    # Wait 300ms (after the 150ms timeout fires)
    time.sleep(0.3)
    chk_after = 'JSON.stringify({ innerLen: document.getElementById("onyx-modal-area").innerHTML.length, active: document.getElementById("onyx-modal-area").classList.contains("active") })'
    res_after = ws_call(path, {'id': 8, 'method': 'Runtime.evaluate', 'params': {'expression': chk_after}})
    print('AFTER 300ms:', res_after)
finally:
    proc.terminate()
