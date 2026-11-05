import urllib.request, json, subprocess, time, os, socket, base64

edge = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
if not os.path.exists(edge):
    edge = r'C:\Program Files\Microsoft\Edge\Application\msedge.exe'

port = 9340
proc = subprocess.Popen([edge, '--headless', f'--remote-debugging-port={port}', '--user-data-dir=C:\\Users\\AlparatY\\Desktop\\system ERP\\scratch\\temp_profile', 'about:blank'])
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
    page_tabs = [t for t in tabs if t.get('type') == 'page']
    erp_tab = page_tabs[0] if page_tabs else tabs[0]
    path = erp_tab['webSocketDebuggerUrl'].split(f':{port}')[1]
    print('Targeting tab:', erp_tab['title'], erp_tab['url'])
    
    ws_call(path, {'id': 1, 'method': 'Page.enable'})
    ws_call(path, {'id': 2, 'method': 'Runtime.enable'})
    
    ws_call(path, {'id': 3, 'method': 'Page.navigate', 'params': {'url': 'file:///C:/Users/AlparatY/Desktop/system%20ERP/index.html'}})
    time.sleep(4)
    
    expr = 'JSON.stringify({ href: window.location.href, readyState: document.readyState, hasWorkspace: !!document.getElementById("onyx-workspace"), workspaceLen: document.getElementById("onyx-workspace")?.innerHTML?.length, typeofOnyxApp: typeof window.onyxApp, title: document.title })'
    res = ws_call(path, {'id': 4, 'method': 'Runtime.evaluate', 'params': {'expression': expr}})
    print('Runtime check result:', res)
finally:
    proc.terminate()
