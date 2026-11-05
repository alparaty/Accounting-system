import urllib.request, json, subprocess, time, os, socket, base64

edge = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
if not os.path.exists(edge):
    edge = r'C:\Program Files\Microsoft\Edge\Application\msedge.exe'

port = 9339
proc = subprocess.Popen([edge, '--headless', f'--remote-debugging-port={port}', '--user-data-dir=C:\\Users\\AlparatY\\Desktop\\system ERP\\scratch\\temp_profile7', 'about:blank'])
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
    
    # 1. Execute onyx_data.js
    with open(r'c:\Users\AlparatY\Desktop\system ERP\js\onyx_data.js', encoding='utf-8') as f:
        data_code = f.read()
    res1 = ws_call(path, {'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': data_code}})
    print('1. Execute onyx_data.js:', res1[:200])

    # 2. Execute onyx_store.js
    with open(r'c:\Users\AlparatY\Desktop\system ERP\js\onyx_store.js', encoding='utf-8') as f:
        store_code = f.read()
    res2 = ws_call(path, {'id': 2, 'method': 'Runtime.evaluate', 'params': {'expression': store_code}})
    print('2. Execute onyx_store.js:', res2[:200])

    # 3. Inject dummy HTML DOM elements needed by onyx_app.js
    dom_setup = '''
    document.body.innerHTML = `
      <span id="onyx-screen-title"></span>
      <span id="onyx-screen-sub"></span>
      <div id="onyx-workspace"></div>
      <div id="onyx-modal-area"></div>
      <div id="tree-pending-count"></div>
    `;
    '''
    ws_call(path, {'id': 3, 'method': 'Runtime.evaluate', 'params': {'expression': dom_setup}})

    # 4. Execute onyx_app.js
    with open(r'c:\Users\AlparatY\Desktop\system ERP\js\onyx_app.js', encoding='utf-8') as f:
        app_code = f.read()
    res4 = ws_call(path, {'id': 4, 'method': 'Runtime.evaluate', 'params': {'expression': app_code}})
    print('4. Execute onyx_app.js:', res4[:300])

    # 5. Check workspace and window.onyxApp
    check_expr = '''JSON.stringify({
        hasOnyxApp: typeof window.onyxApp === "object",
        activeScreen: window.onyxApp?.getActiveScreen ? window.onyxApp.getActiveScreen() : null,
        workspaceLength: document.getElementById("onyx-workspace")?.innerHTML?.length,
        workspaceContainsDashboard: document.getElementById("onyx-workspace")?.innerHTML?.includes("لوحة")
    })'''
    res5 = ws_call(path, {'id': 5, 'method': 'Runtime.evaluate', 'params': {'expression': check_expr}})
    print('5. Check result:', res5)

finally:
    proc.terminate()
