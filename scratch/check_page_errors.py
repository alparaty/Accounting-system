import urllib.request, json, subprocess, time, os, socket, base64

edge = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
if not os.path.exists(edge):
    edge = r'C:\Program Files\Microsoft\Edge\Application\msedge.exe'

port = 9341
temp_dir = r'C:\Users\AlparatY\Desktop\system ERP\scratch\temp_profile2'
proc = subprocess.Popen([edge, '--headless', f'--remote-debugging-port={port}', f'--user-data-dir={temp_dir}', 'about:blank'])
time.sleep(2)

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

def ws_read_all(s, duration=3.0):
    s.settimeout(0.5)
    messages = []
    end_time = time.time() + duration
    buf = bytearray()
    while time.time() < end_time:
        try:
            chunk = s.recv(65536)
            if not chunk:
                break
            buf.extend(chunk)
            # parse frames
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
                if len(buf) < offset + payload_len:
                    break
                payload = buf[offset:offset+payload_len].decode('utf-8', errors='ignore')
                messages.append(payload)
                buf = buf[offset+payload_len:]
        except socket.timeout:
            pass
    return messages

try:
    tabs = json.loads(urllib.request.urlopen(f'http://localhost:{port}/json').read())
    page_tabs = [t for t in tabs if t.get('type') == 'page']
    erp_tab = page_tabs[0] if page_tabs else tabs[0]
    path = erp_tab['webSocketDebuggerUrl'].split(f':{port}')[1]
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('localhost', port))
    key = base64.b64encode(os.urandom(16)).decode('utf-8')
    req = f'GET {path} HTTP/1.1\r\nHost: localhost:{port}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n'
    s.sendall(req.encode())
    s.recv(4096)
    
    ws_call(s, {'id': 1, 'method': 'Page.enable'})
    ws_call(s, {'id': 2, 'method': 'Runtime.enable'})
    ws_call(s, {'id': 3, 'method': 'Console.enable'})
    
    # Navigate
    ws_call(s, {'id': 4, 'method': 'Page.navigate', 'params': {'url': 'file:///C:/Users/AlparatY/Desktop/system%20ERP/index.html'}})
    
    events = ws_read_all(s, duration=4.0)
    print(f"Total events received: {len(events)}")
    for ev in events:
        try:
            parsed = json.loads(ev)
            method = parsed.get('method', '')
            if 'exception' in method.lower() or 'error' in ev.lower():
                print(">>> EXCEPTION/ERROR EVENT:", ev[:400])
            elif method == 'Runtime.consoleAPICalled':
                print(">>> CONSOLE:", parsed.get('params', {}).get('args'))
        except:
            pass

    # Now evaluate state
    expr = 'JSON.stringify({ readyState: document.readyState, hasWorkspace: !!document.getElementById("onyx-workspace"), workspaceLen: document.getElementById("onyx-workspace") ? document.getElementById("onyx-workspace").innerHTML.length : 0, typeofOnyxApp: typeof window.onyxApp })'
    ws_call(s, {'id': 100, 'method': 'Runtime.evaluate', 'params': {'expression': expr}})
    eval_res = ws_read_all(s, duration=1.5)
    for r in eval_res:
        if '"id":100' in r or '"id": 100' in r:
            print(">>> EVAL RESULT:", r)
finally:
    proc.terminate()
