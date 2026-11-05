import urllib.request, json, time, os, sqlite3, threading, http.server
import sys

BASE_DIR = r'C:\Users\AlparatY\Desktop\system ERP'
sys.path.insert(0, BASE_DIR)
import desktop_app

DB_PATH = os.path.join(BASE_DIR, "database", "alparaty_erp.db")
BACKUP_PATH = os.path.join(BASE_DIR, "backups", "alparaty_auto_backup.json")

PORT = 8995
server = http.server.HTTPServer(("", PORT), desktop_app.QuietHandler)
desktop_app.init_sqlite()

t = threading.Thread(target=server.serve_forever, daemon=True)
t.start()
time.sleep(1)

try:
    # 1. Test /api/health
    h_resp = urllib.request.urlopen(f'http://localhost:{PORT}/api/health')
    h_data = json.loads(h_resp.read().decode('utf-8'))
    print("HEALTH CHECK:", h_data)
    assert h_data.get('status') == 'ok', "Health check failed"

    # 2. Test /api/sync POST
    test_payload = {
        "accounts": [{"code": "111101", "name": "نقد بالصندوق", "type": "SUB"}],
        "items": [{"code": "ITM-001", "name": "لابتوب تجريبي", "currentStock": 10}],
        "system": {"activeYear": "2026"}
    }
    data = json.dumps(test_payload).encode('utf-8')
    req = urllib.request.Request(f'http://localhost:{PORT}/api/sync', data=data, headers={'Content-Type': 'application/json'})
    s_resp = urllib.request.urlopen(req)
    s_data = json.loads(s_resp.read().decode('utf-8'))
    print("SYNC RESPONSE:", s_data)
    assert s_data.get('persisted') == 'disk_and_sqlite', "Sync did not report persistence"

    # 3. Test /api/backup GET
    b_resp = urllib.request.urlopen(f'http://localhost:{PORT}/api/backup')
    b_data = json.loads(b_resp.read().decode('utf-8'))
    print("BACKUP RETRIEVAL items count:", len(b_data.get('items', [])))
    assert b_data['items'][0]['code'] == 'ITM-001', "Backup payload mismatch"

    # 4. Verify SQLite Table
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT json_data FROM system_state WHERE key = 'current'")
    row = cursor.fetchone()
    conn.close()
    assert row is not None, "SQLite row not found"
    db_json = json.loads(row[0])
    assert db_json['system']['activeYear'] == '2026', "SQLite JSON activeYear mismatch"
    print("SQLITE VERIFICATION: PASSED!")

    # 5. Verify Disk JSON file
    assert os.path.exists(BACKUP_PATH), "Disk backup file does not exist"
    with open(BACKUP_PATH, 'r', encoding='utf-8') as f:
        file_json = json.load(f)
    assert file_json['accounts'][0]['code'] == '111101', "Disk backup accounts mismatch"
    print("DISK JSON VERIFICATION: PASSED!")

    print("\nALL PYTHON BACKEND TESTS PASSED 100%!")
finally:
    server.shutdown()
