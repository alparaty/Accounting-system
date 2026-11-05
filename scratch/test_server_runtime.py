import urllib.request, json, subprocess, time, os, socket, base64, threading, http.server

BASE_DIR = r'C:\Users\AlparatY\Desktop\system ERP'
HTTP_PORT = 9876

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

CDP_PORT = 9342
temp_dir = r'C:\Users\AlparatY\Desktop\system ERP\scratch\temp_profile3'
proc = subprocess.Popen([edge, '--headless', f'--remote-debugging-port={CDP_PORT}', f'--user-data-dir={temp_dir}', f'http://localhost:{HTTP_PORT}/index.html'])
time.sleep(3)

def ws_call(s, msg):
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

def ws_read_all(s, duration=2.0):
    s.settimeout(0.5)
    messages = []
    end_time = time.time() + duration
    buf = bytearray()
    while time.time() < end_time:
        try:
            chunk = s.recv(65536)
            if not chunk: break
            buf.extend(chunk)
            while len(buf) >= 2:
                payload_len = buf[1] & 0x7f
                offset = 2
                if payload_len == 126:
                    if len(buf) < 4: break
                    payload_len = int.from_bytes(buf[2:4], 'big')
                    offset = 4
                elif payload_len == 127:
                    if len(buf) < 10: break
                    payload_len = int.from_bytes(buf[2:10], 'big')
                    offset = 10
                if len(buf) < offset + payload_len: break
                payload = buf[offset:offset+payload_len].decode('utf-8', errors='ignore')
                messages.append(payload)
                buf = buf[offset+payload_len:]
        except socket.timeout:
            pass
    return messages

try:
    tabs = json.loads(urllib.request.urlopen(f'http://localhost:{CDP_PORT}/json').read())
    page_tabs = [tb for tb in tabs if tb.get('type') == 'page']
    erp_tab = page_tabs[0] if page_tabs else tabs[0]
    path = erp_tab['webSocketDebuggerUrl'].split(f':{CDP_PORT}')[1]
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('localhost', CDP_PORT))
    key = base64.b64encode(os.urandom(16)).decode('utf-8')
    req = f'GET {path} HTTP/1.1\r\nHost: localhost:{CDP_PORT}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n'
    s.sendall(req.encode())
    s.recv(4096)
    
    ws_call(s, {'id': 1, 'method': 'Runtime.enable'})
    ws_call(s, {'id': 2, 'method': 'Console.enable'})
    
    # Check evaluate
    expr = '''JSON.stringify({
        readyState: document.readyState,
        hasWorkspace: !!document.getElementById("onyx-workspace"),
        workspaceChildren: document.getElementById("onyx-workspace")?.children?.length,
        typeofOnyxApp: typeof window.onyxApp,
        typeofOnyxStore: typeof window.onyxStore,
        activeScreen: window.onyxApp?.getActiveScreen ? window.onyxApp.getActiveScreen() : "N/A",
        errors: window.__errors || []
    })'''
    ws_call(s, {'id': 10, 'method': 'Runtime.evaluate', 'params': {'expression': expr}})
    msgs = ws_read_all(s, duration=3.0)
    for m in msgs:
        if '"id":10' in m or '"id": 10' in m:
            print("EVALUATION RESULT:\n", m)
finally:
    proc.terminate()
    server.shutdown()
