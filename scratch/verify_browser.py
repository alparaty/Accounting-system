import urllib.request, json, subprocess, time, os, socket, base64

edge = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
if not os.path.exists(edge):
    edge = r'C:\Program Files\Microsoft\Edge\Application\msedge.exe'

CDP_PORT = 9345
temp_dir = r'C:\Users\AlparatY\Desktop\system ERP\scratch\temp_profile6'
proc = subprocess.Popen([edge, '--headless', f'--remote-debugging-port={CDP_PORT}', f'--user-data-dir={temp_dir}', 'about:blank'])
time.sleep(2)

def ws_send(s, msg):
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

def ws_recv(s, timeout=1.0):
    s.settimeout(timeout)
    buf = bytearray()
    messages = []
    start = time.time()
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
                messages.append(payload)
                buf = buf[offset+payload_len:]
        except socket.timeout:
            break
    return messages

try:
    tabs = json.loads(urllib.request.urlopen(f'http://localhost:{CDP_PORT}/json').read())
    page_tabs = [t for t in tabs if t.get('type') == 'page']
    target_tab = page_tabs[0]
    print("Using tab:", target_tab['title'], target_tab['url'])
    
    path = target_tab['webSocketDebuggerUrl'].split(f':{CDP_PORT}')[1]
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('localhost', CDP_PORT))
    key = base64.b64encode(os.urandom(16)).decode('utf-8')
    req = f'GET {path} HTTP/1.1\r\nHost: localhost:{CDP_PORT}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n'
    s.sendall(req.encode())
    s.recv(4096)
    
    ws_send(s, {'id': 1, 'method': 'Page.enable'})
    ws_send(s, {'id': 2, 'method': 'Runtime.enable'})
    ws_send(s, {'id': 3, 'method': 'Log.enable'})
    ws_recv(s, 0.5)
    
    # Navigate to index.html directly via file URL
    file_url = 'file:///C:/Users/AlparatY/Desktop/system%20ERP/index.html'
    ws_send(s, {'id': 4, 'method': 'Page.navigate', 'params': {'url': file_url}})
    
    # Wait and collect all events for 4 seconds
    events = []
    for _ in range(8):
        events.extend(ws_recv(s, 0.5))
    
    for ev in events:
        try:
            p = json.loads(ev)
            m = p.get('method', '')
            if 'exception' in m.lower() or 'error' in ev.lower():
                print(">>> EXCEPTION/ERROR:", ev)
            elif 'console' in m.lower():
                print(">>> CONSOLE:", ev)
        except:
            pass
            
    # Now check window and elements
    check_code = '''({
        title: document.title,
        readyState: document.readyState,
        hasWorkspace: !!document.getElementById('onyx-workspace'),
        workspaceHTML_len: document.getElementById('onyx-workspace') ? document.getElementById('onyx-workspace').innerHTML.length : -1,
        activeScreen: window.onyxApp ? (window.onyxApp.getActiveScreen ? window.onyxApp.getActiveScreen() : "no_getActiveScreen") : "no_onyxApp",
        storeLoaded: typeof window.onyxStore,
        dataLoaded: typeof window.ONYX_INITIAL_DATA
    })'''
    ws_send(s, {'id': 99, 'method': 'Runtime.evaluate', 'params': {'expression': check_code, 'returnByValue': True}})
    res = ws_recv(s, 1.5)
    for r in res:
        if '"id":99' in r:
            print("RESULT 99:", r)
finally:
    proc.terminate()
