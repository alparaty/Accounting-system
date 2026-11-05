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
temp_dir = r'C:\Users\AlparatY\Desktop\system ERP\scratch\temp_snap'
if not os.path.exists(temp_dir):
    os.makedirs(temp_dir)

proc = subprocess.Popen([edge, '--headless', f'--remote-debugging-port={CDP_PORT}', f'--user-data-dir={temp_dir}', '--window-size=1366,768', f'http://localhost:{HTTP_PORT}/index.html'])
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
    raw = b''
    while True:
        chunk = s.recv(65536)
        if not chunk: break
        raw += chunk
        if len(raw) > 4:
            # check if complete or timeout
            try:
                # search for end of json
                if raw.endswith(b'"}') or raw.endswith(b'"} \n'):
                    break
            except:
                pass
        if len(chunk) < 65536:
            break
    offset = 2
    l = raw[1] & 0x7f
    if l == 126: offset = 4
    elif l == 127: offset = 10
    return raw[offset:].decode('utf-8', errors='ignore')

try:
    tabs = json.loads(urllib.request.urlopen(f'http://localhost:{CDP_PORT}/json').read())
    erp_tab = next(t for t in tabs if 'index.html' in t.get('url', '') or str(HTTP_PORT) in t.get('url', ''))
    path = erp_tab['webSocketDebuggerUrl'].split(f':{CDP_PORT}')[1]
    time.sleep(1)
    
    # Close login modal and toggle to branch mode
    ws_call(path, {'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': 'document.getElementById("onyx-login-overlay").style.display = "none"; window.onyxApp.toggleInterfaceMode(); window.onyxApp.openBranchInvoiceWindow("prof_credit_purchases");'}})
    time.sleep(1)

    # Let's inspect properties of alameenInvoiceWindow
    res_info = ws_call(path, {'id': 2, 'method': 'Runtime.evaluate', 'params': {'expression': """
    (() => {
        const win = document.getElementById('alameenInvoiceWindow');
        const stage = document.getElementById('alameenDesktopStage');
        const rWin = win ? win.getBoundingClientRect() : {};
        const rStage = stage ? stage.getBoundingClientRect() : {};
        return {
            win: { top: rWin.top, left: rWin.left, width: rWin.width, height: rWin.height },
            stage: { top: rStage.top, left: rStage.left, width: rStage.width, height: rStage.height },
            classes: win ? win.className : '',
            maxBtnTitle: document.getElementById('btn-maximize-invoice-window')?.title,
            maxBtnText: document.getElementById('btn-maximize-invoice-window')?.textContent
        };
    })()
    """, 'returnByValue': True}})
    print("Window info:", json.loads(res_info)['result']['result']['value'])
finally:
    proc.terminate()
    server.shutdown()
