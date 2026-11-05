import urllib.request
import json
import subprocess
import time
import os
import socket
import base64

edge = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
if not os.path.exists(edge):
    edge = r'C:\Program Files\Microsoft\Edge\Application\msedge.exe'

port = 9338
proc = subprocess.Popen([edge, '--headless', f'--remote-debugging-port={port}', '--user-data-dir=C:\\Users\\AlparatY\\Desktop\\system ERP\\scratch\\temp_profile_test2', 'file:///c:/Users/AlparatY/Desktop/system ERP/index.html'])
time.sleep(2)

def ws_call(path, method, params=None):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('localhost', port))
    key = base64.b64encode(os.urandom(16)).decode('utf-8')
    req = f'GET {path} HTTP/1.1\r\nHost: localhost:{port}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n'
    s.sendall(req.encode())
    s.recv(4096)
    
    msg = json.dumps({'id': 1, 'method': method, 'params': params or {}})
    data = msg.encode('utf-8')
    length = len(data)
    mask = os.urandom(4)
    frame = bytearray([0x81])
    if length <= 125:
        frame.append(0x80 | length)
    elif length <= 65535:
        frame.append(0x80 | 126)
        frame.extend(length.to_bytes(2, 'big'))
    else:
        frame.append(0x80 | 127)
        frame.extend(length.to_bytes(8, 'big'))
    frame.extend(mask)
    masked = bytearray(b ^ mask[i % 4] for i, b in enumerate(data))
    frame.extend(masked)
    s.sendall(frame)
    
    s.settimeout(5.0)
    raw = s.recv(65536)
    offset = 2
    l = raw[1] & 0x7f
    if l == 126:
        offset = 4
    elif l == 127:
        offset = 10
    payload = raw[offset:].decode('utf-8', errors='ignore')
    return payload

try:
    tabs = json.loads(urllib.request.urlopen(f'http://localhost:{port}/json').read())
    erp_tab = next(t for t in tabs if 'system' in t.get('url', ''))
    path = erp_tab['webSocketDebuggerUrl'].split(f':{port}')[1]
    
    # 1. Switch screen to expenses
    res = ws_call(path, 'Runtime.evaluate', {'expression': 'window.onyxApp.openScreen("expenses")'})
    print('Switch to expenses:', res)

    # 2. Run test assertions on expenses features
    test_code = """
    (function() {
        const store = window.onyxStore;
        store.resetToCleanState();
        const res = {};
        
        // Test 1: Categories
        const cats = store.getExpenseCategories();
        res.categoriesCount = cats.length;
        
        // Test 2: Try adding COGS expense (should throw error)
        try {
            store.addExpense({
                categoryId: 'CAT-01',
                amount: 500,
                paymentSource: 'cash_drawer',
                paymentStatus: 'paid'
            });
            res.cogsRejected = false;
        } catch(e) {
            res.cogsRejected = true;
            res.cogsErrorMsg = e.message;
        }
        
        // Test 3: Add regular cash expense
        try {
            const exp = store.addExpense({
                categoryId: 'CAT-04-1',
                amount: 15000,
                description: 'فاتورة كهرباء تجريبية',
                paymentSource: 'cash_drawer',
                paymentStatus: 'paid',
                date: '2026-10-07'
            });
            res.addCashExpenseSuccess = true;
            res.expenseNumber = exp.expenseNumber;
        } catch(e) {
            res.addCashExpenseSuccess = false;
            res.addCashExpenseError = e.message;
        }
        
        // Test 4: Check Shift deduction
        const shiftReport = store.getShiftClosingReport();
        res.shiftCashExpenses = shiftReport.cashExpensesTotal;
        res.shiftExpectedCash = shiftReport.expectedCash;
        res.shiftActualCash = shiftReport.actualCash;
        
        // Test 5: Add Employee Advance and verify payroll deduction
        const adv = store.addEmployeeAdvance({
            employeeId: 'EMP-01',
            amount: 25000,
            periodMonth: '10',
            periodYear: '2026',
            paymentSource: 'cash_drawer',
            notes: 'سلفة منتصف الشهر'
        });
        res.advanceAdded = !!adv;
        
        // Approve payroll
        const payRes = store.approvePayrollForEmployee({
            employeeId: 'emp_01',
            periodMonth: '10',
            periodYear: '2026',
            paymentSource: 'cash_drawer'
        });
        res.payrollApproved = true;
        res.payrollAdvancesDeducted = payRes.advancesDeducted;
        res.payrollNetSalary = payRes.netSalary;
        
        // Test 6: Fixed Asset depreciation
        const depRes = store.processMonthlyDepreciation('10', '2026');
        res.depreciationCount = depRes.length;
        res.depreciationTotal = depRes.reduce((s, d) => s + d.amount, 0);
        
        // Test 7: Dispose fixed asset
        const dispRes = store.disposeFixedAsset('AST-002', {
            disposalDate: '2026-10-07',
            disposalType: 'sale',
            disposalAmount: 500000,
            paymentSource: 'cash_drawer',
            reason: 'بيع أثاث مستعمل'
        });
        res.disposeSuccess = !!dispRes;
        res.gainLoss = dispRes.gainLoss;
        
        // Test 8: Comprehensive Income Statement
        const incStmt = store.getComprehensiveIncomeStatement('2026');
        res.netProfit = incStmt.netProfit;
        res.grossProfit = incStmt.grossProfit;
        res.totalExpenses = incStmt.totalOperatingExpenses;
        
        return JSON.stringify(res);
    })()
    """
    res2 = ws_call(path, 'Runtime.evaluate', {'expression': test_code})
    print('Test Results:', res2)

except Exception as e:
    print('Error:', e)
finally:
    proc.terminate()
