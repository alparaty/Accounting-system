import urllib.request, json, subprocess, time, os, socket, base64, threading, http.server

BASE_DIR = r'C:\Users\AlparatY\Desktop\system ERP'
HTTP_PORT = 9991
server = http.server.HTTPServer(('', HTTP_PORT), http.server.SimpleHTTPRequestHandler)
threading.Thread(target=server.serve_forever, daemon=True).start()

edge = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
if not os.path.exists(edge):
    edge = r'C:\Program Files\Microsoft\Edge\Application\msedge.exe'

CDP_PORT = 9348
temp_dir = r'C:\Users\AlparatY\Desktop\system ERP\scratch\temp_keys_inspect'
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

def ws_read_response(s, req_id, timeout=4.0):
    s.settimeout(0.3)
    start = time.time()
    buf = bytearray()
    while time.time() - start < timeout:
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
                buf = buf[offset+payload_len:]
                if f'"id":{req_id}' in payload or f'"id": {req_id}' in payload:
                    return payload
        except socket.timeout:
            pass
    return None

try:
    tabs = json.loads(urllib.request.urlopen(f'http://localhost:{CDP_PORT}/json').read())
    erp_tab = [tb for tb in tabs if tb.get('type') == 'page'][0]
    path = erp_tab['webSocketDebuggerUrl'].split(f':{CDP_PORT}')[1]
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('localhost', CDP_PORT))
    key = base64.b64encode(os.urandom(16)).decode('utf-8')
    s.sendall(f'GET {path} HTTP/1.1\r\nHost: localhost:{CDP_PORT}\r\nUpgrade: websocket\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n'.encode())
    s.recv(4096)
    
    ws_call(s, {'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': 'Object.keys(window.onyxApp)', 'returnByValue': True}})
    resp = ws_read_response(s, 1)
    print('KEYS IN ONYXAPP:', resp)

    ws_call(s, {'id': 2, 'method': 'Runtime.evaluate', 'params': {'expression': 'typeof window.onyxApp.switchPurchasesTab', 'returnByValue': True}})
    resp2 = ws_read_response(s, 2)
    print('TYPEOF switchPurchasesTab:', resp2)
finally:
    proc.terminate()
