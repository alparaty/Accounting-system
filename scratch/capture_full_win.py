import urllib.request, json, subprocess, time, os, socket, base64

edge = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
if not os.path.exists(edge):
    edge = r'C:\Program Files\Microsoft\Edge\Application\msedge.exe'

port = 9357
proc = subprocess.Popen([edge, '--headless', f'--remote-debugging-port={port}', '--window-size=1920,1080', '--user-data-dir=C:\\Users\\AlparatY\\Desktop\\system ERP\\scratch\\test_full_win8', 'file:///C:/Users/AlparatY/Desktop/system%20ERP/index.html'])
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
            if b'"id":' in raw and raw.rstrip().endswith(b'}'):
                break
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
    
    # Do NOT set maxWidth: 'none', leave it as the current code does!
    ws_call(path, {'id': 2, 'method': 'Runtime.evaluate', 'params': {'expression': '''
    (() => {
        const overlay = document.getElementById('onyx-login-overlay');
        if (overlay) overlay.style.display = 'none';
        window.onyxApp.switchUser('USR-03');
        window.onyxApp.openBranchInvoiceWindow();
    })()
    '''}})
    time.sleep(1)
    
    shot_res = ws_call(path, {'id': 3, 'method': 'Page.captureScreenshot', 'params': {'format': 'png'}})
    res_obj = json.loads(shot_res)
    img_b64 = res_obj['result']['data']
    out_path = r'C:\Users\AlparatY\.gemini\antigravity-ide\brain\09a141c3-34f1-4110-8559-56f5c5c681d6\scratch\before_win_shot.png'
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'wb') as f:
        f.write(base64.b64decode(img_b64))
    print('SUCCESS: Saved before screenshot to:', out_path)
finally:
    proc.terminate()
