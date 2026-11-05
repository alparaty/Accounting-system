import urllib.request, json, subprocess, time, os, socket, base64, threading, http.server

BASE_DIR = r'C:\Users\AlparatY\Desktop\system ERP'
HTTP_PORT = 9982

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
temp_dir = r'C:\Users\AlparatY\Desktop\system ERP\scratch\temp_profile_login'
if not os.path.exists(temp_dir):
    os.makedirs(temp_dir)

proc = subprocess.Popen([edge, '--headless', f'--remote-debugging-port={CDP_PORT}', f'--user-data-dir={temp_dir}', f'http://localhost:{HTTP_PORT}/index.html'])
time.sleep(2.5)

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
        chunk = s.recv(65536)
        if not chunk: break
        raw.extend(chunk)
        if len(chunk) < 65536: break
    offset = 2
    l = raw[1] & 0x7f
    if l == 126: offset = 4
    elif l == 127: offset = 10
    s.close()
    return raw[offset:].decode('utf-8', errors='ignore')

tabs = json.loads(urllib.request.urlopen(f'http://localhost:{CDP_PORT}/json').read().decode())
page_tab = next(t for t in tabs if t.get('type') == 'page')
ws_url = page_tab['webSocketDebuggerUrl']
ws_path = ws_url.split(f':{CDP_PORT}')[1]

def eval_js(expr):
    res_str = ws_call(ws_path, {
        'id': 1,
        'method': 'Runtime.evaluate',
        'params': {'expression': expr, 'returnByValue': True}
    })
    parsed = json.loads(res_str)
    if 'exceptionDetails' in parsed.get('result', {}):
        print("JS EXCEPTION:", parsed['result']['exceptionDetails'])
    return parsed.get('result', {}).get('result', {}).get('value')

try:



    print("--- 1. Testing Store Authenticate Logic ---")
    r1 = eval_js("window.onyxStore.authenticate('1', '1')")
    print("User 1 auth:", r1.get('success'), r1.get('user', {}).get('fullName'))
    assert r1.get('success') == True

    r2 = eval_js("window.onyxStore.authenticate('2', '1')")
    print("User 2 auth:", r2.get('success'), r2.get('user', {}).get('fullName'))
    assert r2.get('success') == True

    r3 = eval_js("window.onyxStore.authenticate('1', 'badpass')")
    print("Bad pass test:", r3.get('success'), r3.get('message'))
    assert r3.get('success') == False

    print("\n--- 2. Testing Login UI DOM Elements ---")
    elements = eval_js("""
        ({
            overlay: !!document.getElementById('onyx-login-overlay'),
            modal: !!document.getElementById('onyxLoginModal'),
            year: !!document.getElementById('login-year'),
            lang: !!document.getElementById('login-lang'),
            accUnit: !!document.getElementById('login-acc-unit'),
            userCode: !!document.getElementById('login-user-code'),
            userSelect: !!document.getElementById('login-user-select'),
            password: !!document.getElementById('login-password'),
            branch: !!document.getElementById('login-branch'),
            company: !!document.getElementById('login-company'),
            systemModule: !!document.getElementById('login-system-module'),
            drawer: !!document.getElementById('onyxLoginDrawer'),
            btnOk: !!document.querySelector('.onyx-login-btn-ok'),
            btnExit: !!document.querySelector('.onyx-login-btn-exit')
        })
    """)
    print("Elements presence:", json.dumps(elements, indent=2))
    assert all(elements.values())

    print("\n--- 3. Testing Quick Fill & Presets ---")
    eval_js("window.onyxApp.quickFillLogin('2', '01', '2')")
    qf_state = eval_js("""
        ({
            userCode: document.getElementById('login-user-code').value,
            branch: document.getElementById('login-branch').value,
            module: document.getElementById('login-system-module').value
        })
    """)
    print("Quick-fill state:", qf_state)
    assert qf_state['userCode'] == '2'
    assert qf_state['branch'] == '01'
    assert qf_state['module'] == '2'

    print("\n--- 4. Testing Drawer Toggle ---")
    eval_js("window.onyxApp.toggleLoginDrawer()")
    drawer_display = eval_js("document.getElementById('onyxLoginDrawer').style.display")
    print("Drawer display after toggle:", drawer_display)
    assert drawer_display == 'block'

    print("\n--- 5. Testing Login Execution into Branch Hub ---")
    eval_js("window.onyxApp.handleLoginSubmit()")
    post_login = eval_js("""
        ({
            overlayDisplay: document.getElementById('onyx-login-overlay').style.display,
            currentUser: window.onyxStore.getCurrentUser().fullName,
            uiMode: window.onyxStore.getCurrentUser().uiMode,
            branchHubVisible: document.getElementById('branch-hub-container').style.display !== 'none'
        })
    """)
    print("Post-login status:", post_login)
    assert post_login['overlayDisplay'] == 'none'
    assert post_login['uiMode'] == 'BRANCH_HUB'
    assert post_login['branchHubVisible'] == True

    print("\n--- 6. Testing Return to Login Modal ---")
    eval_js("window.onyxApp.showLoginModal()")
    reopened = eval_js("document.getElementById('onyx-login-overlay').style.display")
    print("Re-opened modal display:", reopened)
    assert reopened == 'flex'

    print("\n--- 7. Testing Login Execution into Enterprise Classic ---")
    eval_js("window.onyxApp.quickFillLogin('1', '01', '1')")
    eval_js("window.onyxApp.handleLoginSubmit()")
    post_hq = eval_js("""
        ({
            overlayDisplay: document.getElementById('onyx-login-overlay').style.display,
            currentUser: window.onyxStore.getCurrentUser().fullName,
            uiMode: window.onyxStore.getCurrentUser().uiMode,
            enterpriseVisible: document.getElementById('enterprise-app-container').style.display !== 'none'
        })
    """)
    print("Post-HQ status:", post_hq)
    assert post_hq['overlayDisplay'] == 'none'
    assert post_hq['uiMode'] == 'ENTERPRISE'
    assert post_hq['enterpriseVisible'] == True

    print("\nALL LOGIN SUITE TESTS PASSED 100%!")

finally:
    proc.terminate()
    server.shutdown()
