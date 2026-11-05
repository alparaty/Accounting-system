import urllib.request, json, subprocess, time, os, socket, base64, threading, http.server

BASE_DIR = r'C:\Users\AlparatY\Desktop\system ERP'
HTTP_PORT = 9994

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

CDP_PORT = 9348
temp_dir = r'C:\Users\AlparatY\Desktop\system ERP\scratch\temp_bg_test'
if not os.path.exists(temp_dir):
    os.makedirs(temp_dir)

proc = subprocess.Popen([edge, '--headless', f'--remote-debugging-port={CDP_PORT}', f'--user-data-dir={temp_dir}', '--window-size=1280,800', f'http://localhost:{HTTP_PORT}/index.html'])
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
    tabs = json.loads(urllib.request.urlopen(f'http://localhost:{CDP_PORT}/json').read())
    erp_tab = next(t for t in tabs if t.get('type') == 'page')
    path = erp_tab['webSocketDebuggerUrl'].split(f':{CDP_PORT}')[1]
    time.sleep(1)

    # Test Background Option 1: Charcoal / Graphite (خلفية رمادي فحمي دافئ مريح للعين)
    ws_call(path, {'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': '''
        document.getElementById('onyx-login-overlay').style.background = 'radial-gradient(circle at 50% 35%, rgba(40, 44, 52, 0.97), rgba(18, 20, 24, 0.99))';
    '''}})
    time.sleep(0.5)
    shot1 = ws_call(path, {'id': 2, 'method': 'Page.captureScreenshot', 'params': {'format': 'png'}})
    img1 = json.loads(shot1)['result']['data']
    with open(os.path.join(BASE_DIR, 'scratch', 'bg_opt1_charcoal.png'), 'wb') as f:
        f.write(base64.b64decode(img1))

    # Test Background Option 2: Soft Smoked Frosted Glass (رمادي مدخن ناعم شفاف مع بلور يريح العين)
    ws_call(path, {'id': 3, 'method': 'Runtime.evaluate', 'params': {'expression': '''
        document.getElementById('onyx-login-overlay').style.background = 'rgba(26, 29, 35, 0.82)';
        document.getElementById('onyx-login-overlay').style.backdropFilter = 'blur(16px)';
    '''}})
    time.sleep(0.5)
    shot2 = ws_call(path, {'id': 4, 'method': 'Page.captureScreenshot', 'params': {'format': 'png'}})
    img2 = json.loads(shot2)['result']['data']
    with open(os.path.join(BASE_DIR, 'scratch', 'bg_opt2_frosted.png'), 'wb') as f:
        f.write(base64.b64decode(img2))

    # Test Background Option 3: Deep Slate Warm Titanium (تيتانيوم وسليت حيادي دافئ)
    ws_call(path, {'id': 5, 'method': 'Runtime.evaluate', 'params': {'expression': '''
        document.getElementById('onyx-login-overlay').style.background = 'radial-gradient(circle at 50% 35%, #30353f 0%, #15171c 100%)';
        document.getElementById('onyx-login-overlay').style.backdropFilter = 'blur(8px)';
    '''}})
    time.sleep(0.5)
    shot3 = ws_call(path, {'id': 6, 'method': 'Page.captureScreenshot', 'params': {'format': 'png'}})
    img3 = json.loads(shot3)['result']['data']
    with open(os.path.join(BASE_DIR, 'scratch', 'bg_opt3_titanium.png'), 'wb') as f:
        f.write(base64.b64decode(img3))

    print("ALL_BG_OPTIONS_CAPTURED")
finally:
    proc.terminate()
    server.shutdown()
