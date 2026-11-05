import urllib.request, json, subprocess, time, os, socket, base64, threading, http.server

BASE_DIR = r'C:\Users\AlparatY\Desktop\system ERP'
HTTP_PORT = 9995

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

CDP_PORT = 9349
temp_dir = r'C:\Users\AlparatY\Desktop\system ERP\scratch\temp_bg_test2'
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

    # Option 4: Full Charcoal Harmony (الخلفية الخارجية رمادي فحمي + خلفية رأس النافذة رمادي فحمي تيتانيوم مريح 100%)
    ws_call(path, {'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': '''
        const overlay = document.getElementById('onyx-login-overlay');
        overlay.style.background = 'radial-gradient(circle at 50% 35%, rgba(38, 42, 50, 0.97), rgba(18, 20, 24, 0.99))';
        const header = document.querySelector('.onyx-login-header');
        if (header) {
            header.style.background = 'linear-gradient(180deg, #374151 0%, #1f2937 100%)';
            header.style.borderBottom = '2px solid #111827';
        }
        const chip = document.querySelector('.onyx-login-preset-chip.active');
        if (chip) {
            chip.style.background = '#374151';
            chip.style.borderColor = '#1f2937';
        }
        const btnOk = document.querySelector('.onyx-login-btn-ok');
        if (btnOk) {
            btnOk.style.background = 'linear-gradient(180deg, #374151 0%, #1f2937 100%)';
            btnOk.style.borderColor = '#111827';
        }
    '''}})
    time.sleep(0.5)
    shot4 = ws_call(path, {'id': 2, 'method': 'Page.captureScreenshot', 'params': {'format': 'png'}})
    img4 = json.loads(shot4)['result']['data']
    with open(os.path.join(BASE_DIR, 'scratch', 'bg_opt4_full_charcoal.png'), 'wb') as f:
        f.write(base64.b64decode(img4))

    # Option 5: Soft Warm Classic Neutral (الخلفية الخارجية شبه شفافة هادئة + رأس النافذة رمادي دافئ مثل أونكس برو الأصلي)
    ws_call(path, {'id': 3, 'method': 'Runtime.evaluate', 'params': {'expression': '''
        const overlay = document.getElementById('onyx-login-overlay');
        overlay.style.background = 'rgba(20, 24, 30, 0.72)';
        overlay.style.backdropFilter = 'blur(16px)';
        const header = document.querySelector('.onyx-login-header');
        if (header) {
            header.style.background = 'linear-gradient(180deg, #334155 0%, #1e293b 100%)';
            header.style.borderBottom = '2px solid #0f172a';
        }
    '''}})
    time.sleep(0.5)
    shot5 = ws_call(path, {'id': 4, 'method': 'Page.captureScreenshot', 'params': {'format': 'png'}})
    img5 = json.loads(shot5)['result']['data']
    with open(os.path.join(BASE_DIR, 'scratch', 'bg_opt5_frosted_charcoal.png'), 'wb') as f:
        f.write(base64.b64decode(img5))

    print("CAPTURED_OPTIONS_4_AND_5")
finally:
    proc.terminate()
    server.shutdown()
