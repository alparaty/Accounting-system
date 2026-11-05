import urllib.request, json, subprocess, time, os, socket, base64

edge = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
if not os.path.exists(edge):
    edge = r'C:\Program Files\Microsoft\Edge\Application\msedge.exe'

port = 9376
proc = subprocess.Popen([edge, '--headless', f'--remote-debugging-port={port}', '--window-size=1366,768', '--user-data-dir=C:\\Users\\AlparatY\\Desktop\\system ERP\\scratch\\test_colors_final', 'file:///C:/Users/AlparatY/Desktop/system%20ERP/index.html'])
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
    raw = bytearray()
    while True:
        try:
            chunk = s.recv(65536)
            if not chunk: break
            raw.extend(chunk)
            if b'"id":' in raw and raw.rstrip().endswith(b'}'): break
        except: break
    offset = 2
    l = raw[1] & 0x7f
    if l == 126: offset = 4
    elif l == 127: offset = 10
    return raw[offset:].decode('utf-8', errors='ignore')

try:
    tabs = json.loads(urllib.request.urlopen(f'http://localhost:{port}/json').read())
    page_tab = [t for t in tabs if t.get('type') == 'page'][0]
    path = page_tab['webSocketDebuggerUrl'].split(f':{port}')[1]
    ws_call(path, {'id': 1, 'method': 'Runtime.enable'})
    
    # 1. Login and Open branch invoice (Maximized by default)
    ws_call(path, {'id': 2, 'method': 'Runtime.evaluate', 'params': {'expression': '''
    (() => {
        document.getElementById('onyx-login-overlay').style.display = 'none';
        window.onyxApp.switchUser('USR-03');
        window.onyxApp.openBranchInvoiceWindow();
    })()
    '''}})
    time.sleep(1)
    
    shot1 = json.loads(ws_call(path, {'id': 3, 'method': 'Page.captureScreenshot', 'params': {'format': 'png'}}))['result']['data']
    with open('scratch/final_eye_friendly_maximized.png', 'wb') as f:
        f.write(base64.b64decode(shot1))
        
    # 2. Restore to floating to verify floating window border & titlebar
    ws_call(path, {'id': 4, 'method': 'Runtime.evaluate', 'params': {'expression': '''
    (() => {
        window.onyxApp.toggleMaximizeInvoiceWindow();
    })()
    '''}})
    time.sleep(1)
    
    shot2 = json.loads(ws_call(path, {'id': 5, 'method': 'Page.captureScreenshot', 'params': {'format': 'png'}}))['result']['data']
    with open('scratch/final_eye_friendly_floating.png', 'wb') as f:
        f.write(base64.b64decode(shot2))
        
    print('SUCCESS: Both final screenshots captured!')
finally:
    proc.terminate()
