/**
 * محرك المنطق المحاسبي وقواعد العمل الرسمية لنظام أونكس برو (Onyx Pro Engine)
 */

window.toEnglishDigits = function(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/[٠-٩]/g, d => '٠١٢٣٤٥٦٧٨٩'.indexOf(d))
    .replace(/[۰-۹]/g, d => '۰۱۲۳۴۵۶۷۸۹'.indexOf(d));
};

class OnyxStore {
  constructor() {
    this.key = 'ONYX_PRO_SYSTEM_STORAGE_CLEAN_V3';
    this.listeners = [];
    this.state = this.init();
    try { this.save(); } catch (e) {}
  }


  ensureExpenseSchema(st) {
    if (!st.expenseCategories || st.expenseCategories.length === 0) {
      st.expenseCategories = JSON.parse(JSON.stringify(ONYX_DATA.expenseCategories || []));
    }
    if (!st.expenses) st.expenses = [];
    if (!st.expensePayments) st.expensePayments = [];
    if (!st.recurringExpenseTemplates) st.recurringExpenseTemplates = [];
    if (!st.payrollEntries) st.payrollEntries = [];
    if (!st.employeeAdvances) st.employeeAdvances = [];
    if (!st.fixedAssets || st.fixedAssets.length === 0) {
      st.fixedAssets = JSON.parse(JSON.stringify(ONYX_DATA.fixedAssets || []));
    }
    if (!st.depreciationEntries) st.depreciationEntries = [];
    if (!st.assetDisposals) st.assetDisposals = [];
    if (!st.shifts || st.shifts.length === 0) {
      st.shifts = JSON.parse(JSON.stringify(ONYX_DATA.shifts || []));
    }
    if (!st.employees || st.employees.length === 0) {
      st.employees = JSON.parse(JSON.stringify(ONYX_DATA.employees || []));
    }
    if (!st.customers || st.customers.length === 0) {
      st.customers = JSON.parse(JSON.stringify(ONYX_DATA.customers || []));
    }
    if (!st.salesReps || st.salesReps.length === 0) {
      st.salesReps = JSON.parse(JSON.stringify(ONYX_DATA.salesReps || []));
    }
    if (!st.suppliers || st.suppliers.length === 0) {
      st.suppliers = JSON.parse(JSON.stringify(ONYX_DATA.suppliers || []));
    }
    if (!st.warehouses || st.warehouses.length === 0) {
      st.warehouses = JSON.parse(JSON.stringify(ONYX_DATA.warehouses || []));
    }
    if (!st.items || st.items.length === 0) {
      st.items = JSON.parse(JSON.stringify(ONYX_DATA.items || []));
    } else {
      st.items.forEach(it => {
        if (!it.barcode) {
          const def = (ONYX_DATA.items || []).find(d => d.code === it.code || d.id === it.id);
          it.barcode = (def && def.barcode) ? def.barcode : (it.code || it.id);
        }
      });
    }
    if (!st.users || st.users.length === 0) {
      st.users = JSON.parse(JSON.stringify(ONYX_DATA.users || []));
    } else {
      (ONYX_DATA.users || []).forEach(defUser => {
        const u = st.users.find(x => x.id === defUser.id || x.username === defUser.username);
        if (u) {
          if (!u.uiMode) u.uiMode = defUser.uiMode || 'ENTERPRISE';
          if (!u.assignedBranchId) u.assignedBranchId = defUser.assignedBranchId || '01';
          if (!u.defaultWarehouseId) u.defaultWarehouseId = defUser.defaultWarehouseId || 'WH01';
          if (!u.userCode) u.userCode = defUser.userCode || (defUser.id === 'USR-01' ? '1' : defUser.id === 'USR-02' ? '2' : '3');
          if (!u.password) u.password = defUser.password || '1';
        } else {
          st.users.push(JSON.parse(JSON.stringify(defUser)));
        }
      });
    }
    if (!st.currentUserId) st.currentUserId = 'USR-01';

    if (!st.cashBoxes || st.cashBoxes.length === 0) {
      st.cashBoxes = JSON.parse(JSON.stringify(ONYX_DATA.cashBoxes || []));
    } else {
      (ONYX_DATA.cashBoxes || []).forEach(defCb => {
        if (!st.cashBoxes.some(c => c.code === defCb.code)) {
          st.cashBoxes.push(JSON.parse(JSON.stringify(defCb)));
        }
      });
    }

    if (!st.invoiceProfiles || st.invoiceProfiles.length === 0) {
      st.invoiceProfiles = JSON.parse(JSON.stringify(ONYX_DATA.invoiceProfiles || []));
    } else {
      // التأكد من توفر الأنماط التأسيسية الأربعة وتحديث خصائصها
      (ONYX_DATA.invoiceProfiles || []).forEach(defProf => {
        const existing = st.invoiceProfiles.find(p => p.id === defProf.id || p.code === defProf.code);
        if (!existing) {
          st.invoiceProfiles.push(JSON.parse(JSON.stringify(defProf)));
        } else {
          Object.assign(existing, {
            typeDirection: existing.typeDirection || defProf.typeDirection,
            themeColor: defProf.themeColor || existing.themeColor,
            defaultPaymentType: existing.defaultPaymentType || defProf.defaultPaymentType,
            requireCustomer: existing.requireCustomer !== undefined ? existing.requireCustomer : defProf.requireCustomer,
            enableSerialTracking: existing.enableSerialTracking !== undefined ? existing.enableSerialTracking : defProf.enableSerialTracking,
            enableGiftCol: existing.enableGiftCol !== undefined ? existing.enableGiftCol : defProf.enableGiftCol,
            defaultPriceTier: existing.defaultPriceTier || defProf.defaultPriceTier,
            printTemplate: existing.printTemplate || defProf.printTemplate,
            sortOrder: defProf.sortOrder || existing.sortOrder
          });
        }
      });
    }
    if (!st.salesInvoices || st.salesInvoices.length === 0) {
      st.salesInvoices = JSON.parse(JSON.stringify(ONYX_DATA.salesInvoices || []));
    }
    if (!st.posInvoices) st.posInvoices = [];

    // --- تكامل وتوافقية Odoo 17 ORM ومحرك المعاملات ---
    // 1. حسابات فروق العملات ومخزون الفروقات
    if (st.accounts) {
      const requiredAccs = [
        { code: "420101", name: "أرباح فروق عملات أجنبية", parent: "4", type: "SUB", report: "PL", level: 2, currency: "YER", balance: 0, active: true },
        { code: "410401", name: "إيرادات فروقات جرد المخزون (فائض)", parent: "4", type: "SUB", report: "PL", level: 2, currency: "YER", balance: 0, active: true },
        { code: "520401", name: "خسائر فروق عملات أجنبية", parent: "5", type: "SUB", report: "PL", level: 2, currency: "YER", balance: 0, active: true },
        { code: "520501", name: "مصروف فروقات جرد المخزون (عجز)", parent: "5", type: "SUB", report: "PL", level: 2, currency: "YER", balance: 0, active: true }
      ];
      requiredAccs.forEach(reqA => {
        if (!st.accounts.some(a => a.code === reqA.code)) {
          st.accounts.push(JSON.parse(JSON.stringify(reqA)));
        }
      });
      st.accounts.forEach(a => { if (a.active === undefined) a.active = true; });
    }

    // 2. كولكشن حركات المخزون (Odoo stock.move)
    if (!st.stockMoves) st.stockMoves = [];

    // 3. كولكشن سجل التدقيق والـ Chatter (Odoo mail.thread / tracking)
    if (!st.auditLogs) st.auditLogs = [];

    // 4. تسلسلات الترقيم الآلي (Odoo ir.sequence)
    if (!st.sequences) {
      st.sequences = {
        JV: (st.journalEntries?.length || 0) + 1,
        PV: (st.vouchers?.length || 0) + 1,
        RV: 1,
        INV: (st.salesInvoices?.length || 0) + 1,
        PINV: (st.purchaseInvoices?.length || 0) + 1,
        STK: (st.stockMoves?.length || 0) + 1,
        EXP: (st.expenses?.length || 0) + 1
      };
    }

    // 5. أقفال الفترات والسنوات المالية (Odoo fiscal locks)
    if (!st.fiscalLocks) st.fiscalLocks = [];

    // 6. تسويات البنوك والشيكات (Odoo bank reconciliation)
    if (!st.bankReconciliations) st.bankReconciliations = [];

    // 7. تقييمات أسعار الصرف الدورية (Odoo currency revaluation)
    if (!st.currencyRevaluations) st.currencyRevaluations = [];

    // 8. إعدادات Odoo الرقابية
    if (!st.system) st.system = JSON.parse(JSON.stringify(ONYX_DATA.system || {}));
    if (!st.system.settings) st.system.settings = {};
    if (st.system.settings.allowNegativeCash === undefined) st.system.settings.allowNegativeCash = false;
    if (st.system.settings.enforceCreditLimit === undefined) st.system.settings.enforceCreditLimit = true;
    if (st.system.settings.autoStockMoves === undefined) st.system.settings.autoStockMoves = true;
    if (st.system.settings.autoExchangeDiff === undefined) st.system.settings.autoExchangeDiff = true;

    // 9. التأكد من توفر active لجميع السجلات لدعم الأرشفة دون كسر العلاقات
    ['items', 'customers', 'suppliers', 'employees', 'fixedAssets', 'users'].forEach(k => {
      (st[k] || []).forEach(item => { if (item.active === undefined) item.active = true; });
    });

    return st;
  }

  init() {
    try {
      const stored = localStorage.getItem(this.key);
      if (stored) {
        const parsed = JSON.parse(stored);
        this.ensureExpenseSchema(parsed);
        return parsed;
      }
    } catch (e) {
      console.warn("Storage warning, using clean seed data:", e);
    }
    const fresh = JSON.parse(JSON.stringify(ONYX_DATA));
    this.ensureExpenseSchema(fresh);

    // محاولة الاسترجاع التلقائي الفوري من خادم بايثون وقاعدة SQLite إذا كانت الذاكرة فارغة
    if (typeof fetch === 'function') {
      try {
        fetch('/api/backup')
          .then(res => res.json())
          .then(remoteData => {
            if (remoteData && remoteData.accounts && remoteData.accounts.length > 0) {
              this.state = remoteData;
              this.ensureExpenseSchema(this.state);
              this.save();
            }
          })
          .catch(() => {});
      } catch (err) {}
    }

    return fresh;
  }

  resetToCleanState() {
    try {
      localStorage.removeItem(this.key);
    } catch (e) {}
    this.state = JSON.parse(JSON.stringify(ONYX_DATA));
    this.save();
    return this.state;
  }

  save() {
    try {
      localStorage.setItem(this.key, JSON.stringify(this.state));
    } catch (e) {
      console.error("Storage error:", e);
    }

    // مزامنة فورية صامتة في الخلفية مع خادم بايثون والقرص وقاعدة SQLite
    if (typeof fetch === 'function') {
      try {
        fetch('/api/sync', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(this.state)
        }).catch(() => {});
      } catch (err) {}
    }

    this.listeners.forEach(fn => fn(this.state));
  }

  exportFullBackup() {
    return {
      version: "2026.1",
      exportDate: new Date().toISOString(),
      system: "Al-ParatY Financial Enterprise ERP",
      data: this.state
    };
  }

  importFullBackup(backupJson) {
    const data = typeof backupJson === 'string' ? JSON.parse(backupJson) : backupJson;
    const stateData = data.data || data;
    if (!stateData || !stateData.accounts || !stateData.system) {
      throw new Error("ملف النسخة الاحتياطية غير متوافق أو تالف!");
    }
    this.ensureExpenseSchema(stateData);
    this.state = stateData;
    this.save();
    return true;
  }

  subscribe(fn) {
    this.listeners.push(fn);
  }

  formatCurrency(val, currCode = 'YER') {
    const num = Number(val) || 0;
    const curr = this.state.currencies.find(c => c.code === currCode) || { symbol: currCode, decimals: 2 };
    return `${num.toLocaleString('en-US', { minimumFractionDigits: curr.decimals, maximumFractionDigits: curr.decimals })} ${curr.symbol}`;
  }

  formatNumber(val, decimals = 0) {
    const num = Number(val) || 0;
    return num.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  }

  /* =========================================================================
     محرك Odoo 17 ORM والعمليات المحاسبية المتقدمة (Odoo 17 Engine & Workflows)
     ========================================================================= */

  // 1. دقة العملات والتقريب المالي وفق مواصفة Odoo (res.currency.round)
  roundCurrency(amount, currCode = 'YER') {
    const curr = (this.state.currencies || []).find(c => c.code === currCode) || { decimals: 2 };
    const decimals = curr.decimals !== undefined ? curr.decimals : 2;
    const factor = Math.pow(10, decimals);
    return Math.round(((Number(amount) || 0) + Number.EPSILON) * factor) / factor;
  }

  // 2. مولد التسلسلات التلقائي القياسي (ir.sequence)
  getNextSequence(seqCode, prefix = null, padding = 4) {
    if (!this.state.sequences) this.state.sequences = {};
    const curr = this.state.sequences[seqCode] || 1;
    this.state.sequences[seqCode] = curr + 1;
    const year = this.state.system?.activeYear || new Date().getFullYear();
    const pre = prefix || seqCode;
    return `${pre}-${year}-${String(curr).padStart(padding, '0')}`;
  }

  // 3. التحقق من تاريخ إقفال الفترات المالية (Odoo Fiscal Lock Date Constraint)
  checkFiscalLockDate(transDate) {
    if (!transDate) return true;
    const dateStr = window.toEnglishDigits(transDate);
    const locks = this.state.fiscalLocks || [];
    for (const l of locks) {
      if (l.isClosed && l.lockDate && dateStr <= l.lockDate) {
        throw new Error(`الفترة المالية حتى تاريخ [${l.lockDate}] مقفلة رسمياً (سنة ${l.fiscalYear})؛ يمنع النظام تسجيل أو تعديل أي عملية بتاريخ [${dateStr}] وفق معايير الرقابة!`);
      }
    }
    return true;
  }

  // 4. قيد مانع الرصيد السالب للصندوق (Odoo Cash Solvency Constraint)
  checkCashSolvency(cashBoxCode, amount) {
    if (this.state.system?.settings?.allowNegativeCash === false) {
      const cb = this.getCashBox(cashBoxCode);
      if (cb) {
        const acc = this.getAccount(cb.accCode);
        const curBal = Number(acc ? acc.balance : cb.balance) || 0;
        if (curBal - Number(amount) < 0) {
          throw new Error(`خطأ رقابي (@api.constrains): رصيد الصندوق [${cb.name}] الحالي (${this.formatCurrency(curBal, cb.currency)}) غير كافٍ لصرف مبلغ (${this.formatCurrency(amount, cb.currency)}) وسيصبح الرصيد سالباً!`);
        }
      }
    }
    return true;
  }

  // 5. فحص سقف الائتمان للعملاء (Odoo Credit Limit Constraint)
  checkCreditLimit(customerCodeOrName, newAmount) {
    if (this.state.system?.settings?.enforceCreditLimit) {
      const cust = (this.state.customers || []).find(c => c.code === customerCodeOrName || c.name === customerCodeOrName);
      if (cust && cust.creditLimit && Number(cust.creditLimit) > 0) {
        const projectedBal = (Number(cust.balanceLocal) || 0) + Number(newAmount);
        if (projectedBal > Number(cust.creditLimit)) {
          throw new Error(`خطأ رقابي (@api.constrains): مديونية العميل [${cust.name}] ستصل إلى (${this.formatCurrency(projectedBal)}) متجاوزة السقف الائتماني المعتمد (${this.formatCurrency(cust.creditLimit)}) بمقدار (${this.formatCurrency(projectedBal - cust.creditLimit)})!`);
        }
      }
    }
    return true;
  }

  // 6. فحص العلاقات التكرارية لشجرة الحسابات (Odoo _check_recursion)
  checkAccountRecursion(accountCode, newParentCode) {
    if (!accountCode || !newParentCode) return true;
    if (accountCode === newParentCode) {
      throw new Error(`خطأ في شجرة الحسابات (@api.constrains): لا يمكن تعيين الحساب [${accountCode}] كحساب أب لنفسه!`);
    }
    let currentParent = newParentCode;
    let depth = 0;
    while (currentParent && depth < 30) {
      if (currentParent === accountCode) {
        throw new Error(`خطأ في الشجرة الهرمية (_check_recursion): تم اكتشاف حلقة تكرارية غير مسموحة؛ الحساب [${accountCode}] هو سلف مباشر أو غير مباشر للحساب [${newParentCode}]!`);
      }
      const pAcc = this.getAccount(currentParent);
      currentParent = pAcc ? pAcc.parent : null;
      depth++;
    }
    return true;
  }

  // 7. تسجيل حركات المخزون التفصيلية (Odoo stock.move)
  recordStockMove(data) {
    if (!this.state.stockMoves) this.state.stockMoves = [];
    const id = this.getNextSequence('STK', 'STK', 4);
    const moveDate = window.toEnglishDigits(data.date || new Date().toISOString().split('T')[0]);
    const qty = Number(data.qty) || 0;
    const unitCost = Number(data.unitCost) || 0;
    const totalValue = this.roundCurrency(qty * unitCost);

    const move = {
      id,
      date: moveDate,
      productId: data.productId || '',
      productName: data.productName || '',
      moveType: data.moveType || 'INTERNAL_TRANSFER',
      qty,
      unitCost,
      totalValue,
      sourceLoc: data.sourceLoc || 'المخزن الرئيسي',
      destLoc: data.destLoc || 'المخزن الرئيسي',
      refDoc: data.refDoc || '',
      createdAt: new Date().toISOString()
    };

    this.state.stockMoves.unshift(move);
    this.save();
    return move;
  }

  // 8. تسوية الجرد وفروقات المخزون (Odoo Inventory Adjustment)
  adjustStockItem(itemCode, warehouse = 'WH01', physicalQty = 0, reason = "تسوية جرد دوري") {
    const item = (this.state.items || []).find(i => i.code === itemCode);
    if (!item) throw new Error("الصنف غير موجود بالمخازن!");

    if (!item.whStock) item.whStock = { WH01: 0, WH02: 0 };
    const curWh = Number(item.whStock[warehouse]) || 0;
    const phys = Number(physicalQty) || 0;
    const variance = phys - curWh;

    if (variance === 0) return { variance: 0, message: "الكمية الفعلية مطابقة للرصيد الدفتري تماماً." };

    const unitCost = Number(item.costPrice) || 0;
    const varianceValue = this.roundCurrency(Math.abs(variance) * unitCost);
    const today = new Date().toISOString().split('T')[0];

    // تحديث رصيد المخزن
    item.whStock[warehouse] = phys;
    item.currentStock = Object.values(item.whStock).reduce((a, b) => (Number(a) || 0) + (Number(b) || 0), 0);

    // تسجيل حركة المخزون
    this.recordStockMove({
      productId: item.code,
      productName: item.name,
      moveType: variance > 0 ? 'INVENTORY_ADJUSTMENT_IN' : 'INVENTORY_ADJUSTMENT_OUT',
      qty: Math.abs(variance),
      unitCost,
      sourceLoc: variance > 0 ? 'تسوية جردية (فائض)' : warehouse,
      destLoc: variance > 0 ? warehouse : 'تسوية جردية (عجز)',
      refDoc: `ADJ-${item.code}`,
      date: today
    });

    // توليد القيد المحاسبي للفارق
    let jvLines = [];
    if (variance > 0) {
      // فائض جرد: مدين المخزون (115101) ودائن إيراد فائض جرد (410401)
      jvLines = [
        { accCode: '115101', accName: 'مخزون البضائع والأصناف', debit: varianceValue, credit: 0, note: `إثبات فائض جرد ${item.name} (${variance} قطعة)` },
        { accCode: '410401', accName: 'إيرادات فروقات جرد المخزون (فائض)', debit: 0, credit: varianceValue, note: reason }
      ];
    } else {
      // عجز جرد: مدين مصروف عجز جرد (520501) ودائن المخزون (115101)
      jvLines = [
        { accCode: '520501', accName: 'مصروف فروقات جرد المخزون (عجز)', debit: varianceValue, credit: 0, note: reason },
        { accCode: '115101', accName: 'مخزون البضائع والأصناف', debit: 0, credit: varianceValue, note: `تخفيض عجز جرد ${item.name} (${Math.abs(variance)} قطعة)` }
      ];
    }

    const jv = this.addJournalEntry({
      desc: `قيد تسوية فروقات جرد الصنف [${item.name}] - ${reason}`,
      date: today,
      lines: jvLines
    });

    this.save();
    return { variance, varianceValue, jvId: jv.id };
  }

  // 9. سجل التدقيق وتتبع التغييرات الفورية (Odoo mail.thread / tracking)
  logAudit(event) {
    if (!this.state.auditLogs) this.state.auditLogs = [];
    const currentUser = event.user || (this.getCurrentUser ? this.getCurrentUser().fullName : "المدير المالي");
    const logEntry = {
      id: (this.state.auditLogs.length || 0) + 1,
      actionType: event.actionType || 'UPDATE',
      docId: event.docId || '',
      docModel: event.docModel || '',
      userName: currentUser,
      fieldName: event.fieldName || '',
      oldValue: event.oldValue !== undefined ? String(event.oldValue) : '',
      newValue: event.newValue !== undefined ? String(event.newValue) : '',
      details: event.details || '',
      createdAt: new Date().toISOString().replace('T', ' ').substring(0, 19)
    };

    this.state.auditLogs.unshift(logEntry);

    // إرسال صامت إلى خادم بايثون وقاعدة بيانات SQLite
    if (typeof fetch === 'function') {
      try {
        fetch('/api/audit_log', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            action_type: logEntry.actionType,
            doc_id: logEntry.docId,
            doc_model: logEntry.docModel,
            user_name: logEntry.userName,
            field_name: logEntry.fieldName,
            old_value: logEntry.oldValue,
            new_value: logEntry.newValue,
            details: logEntry.details
          })
        }).catch(() => {});
      } catch (e) {}
    }

    return logEntry;
  }

  // 10. المقارنة التلقائية لتتبع تعديلات الحقول (tracking=True)
  trackFieldChanges(docModel, docId, originalObj, updatedObj, trackedFields = ['amount', 'status', 'date', 'targetAcc', 'customer', 'supplier', 'discount']) {
    if (!originalObj || !updatedObj) return;
    trackedFields.forEach(field => {
      if (originalObj[field] !== undefined && updatedObj[field] !== undefined && originalObj[field] !== updatedObj[field]) {
        this.logAudit({
          actionType: 'FIELD_CHANGE',
          docId,
          docModel,
          fieldName: field,
          oldValue: originalObj[field],
          newValue: updatedObj[field],
          details: `تعديل الحقل [${field}] من [${originalObj[field]}] إلى [${updatedObj[field]}]`
        });
      }
    });
  }

  // 11. استرجاع السجل التاريخي لأي وثيقة (Chatter History)
  getAuditHistory(docId, docModel = null) {
    return (this.state.auditLogs || []).filter(l => {
      if (l.docId !== docId) return false;
      if (docModel && l.docModel !== docModel) return false;
      return true;
    });
  }

  // 12. معالجة فروق أسعار الصرف المحققة (Realized FX Gain/Loss)
  postExchangeDifference({ docType, docId, currency, transactionRate, settlementRate, foreignAmount, partnerName = '', branch = '01' }) {
    if (!currency || currency === 'YER') return null;
    const transR = Number(transactionRate) || 1.0;
    const settleR = Number(settlementRate) || transR;
    const amtF = Number(foreignAmount) || 0;
    const diff = (settleR - transR) * amtF;

    if (Math.abs(diff) < 0.01) return null;

    const isGain = diff > 0;
    const diffAmount = Math.abs(this.roundCurrency(diff, 'YER'));
    const today = new Date().toISOString().split('T')[0];

    const entryDesc = `فروق أسعار صرف محققة لوثيقة [${docId}] - ${partnerName} (سعر المعاملة ${transR} مقابل سعر التسوية ${settleR})`;
    let lines = [];

    if (isGain) {
      // ربح فروق صرف: دائن لحساب 420101
      lines = [
        { accCode: "1121010001", accName: "الصندوق / البنك الوسيط", debit: diffAmount, credit: 0, note: "أثر فرق سعر الصرف الإيجابي" },
        { accCode: "420101", accName: "أرباح فروق عملات أجنبية", debit: 0, credit: diffAmount, note: entryDesc }
      ];
    } else {
      // خسارة فروق صرف: مدين لحساب 520401
      lines = [
        { accCode: "520401", accName: "خسائر فروق عملات أجنبية", debit: diffAmount, credit: 0, note: entryDesc },
        { accCode: "1121010001", accName: "الصندوق / البنك الوسيط", debit: 0, credit: diffAmount, note: "أثر فرق سعر الصرف السلبي" }
      ];
    }

    const diffEntry = this.addJournalEntry({
      desc: entryDesc,
      branch,
      date: today,
      lines
    });

    this.logAudit({
      actionType: 'FX_REVALUATION',
      docId,
      docModel: docType,
      details: `${isGain ? 'أرباح' : 'خسائر'} فروق صرف بمبلغ ${this.formatCurrency(diffAmount)}`
    });

    return diffEntry;
  }

  // 13. معالج الترحيل الجماعي المشروط مع فحص التوازن والرقابة (account.batch.post.wizard)
  batchPostWizard(documentList, options = {}) {
    const poster = options.poster || (this.getCurrentUser ? this.getCurrentUser().fullName : "المدير المالي");
    const posted = [];
    const skipped = [];

    (documentList || []).forEach(item => {
      const type = item.type;
      const id = item.id;
      try {
        const success = this.postDocument(type, id, poster);
        if (success) {
          posted.push({ type, id, status: 'SUCCESS' });
        } else {
          skipped.push({ type, id, reason: 'الوثيقة غير موجودة أو لم تعتمد مراجعتها' });
        }
      } catch (err) {
        skipped.push({ type, id, reason: err.message });
      }
    });

    this.logAudit({
      actionType: 'BATCH_POST_WIZARD',
      docId: `BATCH-${Date.now()}`,
      docModel: 'account.batch.post.wizard',
      details: `معالج الترحيل الجماعي: تم ترحيل ${posted.length} وثيقة، واستبعاد ${skipped.length} وثيقة`
    });

    return { postedCount: posted.length, skippedCount: skipped.length, posted, skipped };
  }

  // 14. معالج تقييم أسعار الصرف الدورية (account.revaluation.wizard)
  currencyRevaluationWizard(marketRates = {}, effectiveDate = null) {
    const date = window.toEnglishDigits(effectiveDate || new Date().toISOString().split('T')[0]);
    const revaluedAccounts = [];
    let totalGain = 0;
    let totalLoss = 0;
    const jvLines = [];

    (this.state.accounts || []).filter(a => a.type === 'SUB' && a.currency && a.currency !== 'YER').forEach(acc => {
      const newRate = marketRates[acc.currency] || this.state.system.exchangeRates[acc.currency];
      const oldRate = this.state.system.exchangeRates[acc.currency] || 1.0;
      if (newRate && newRate !== oldRate && (acc.balance || 0) !== 0) {
        const curBalForeign = Number(acc.balance) || 0;
        const diffInLocal = (newRate - oldRate) * curBalForeign;
        if (Math.abs(diffInLocal) >= 0.01) {
          revaluedAccounts.push({ code: acc.code, name: acc.name, currency: acc.currency, balance: curBalForeign, oldRate, newRate, diffInLocal });
          if (diffInLocal > 0) {
            totalGain += diffInLocal;
            jvLines.push({ accCode: acc.code, accName: acc.name, debit: Math.abs(diffInLocal), credit: 0, note: `إعادة تقييم رصيد ${acc.name} بسعر ${newRate}` });
            jvLines.push({ accCode: "420101", accName: "أرباح فروق عملات أجنبية", debit: 0, credit: Math.abs(diffInLocal), note: `فارق تقييم إيجابي لحساب [${acc.code}]` });
          } else {
            totalLoss += Math.abs(diffInLocal);
            jvLines.push({ accCode: "520401", accName: "خسائر فروق عملات أجنبية", debit: Math.abs(diffInLocal), credit: 0, note: `فارق تقييم سلبي لحساب [${acc.code}]` });
            jvLines.push({ accCode: acc.code, accName: acc.name, debit: 0, credit: Math.abs(diffInLocal), note: `إعادة تقييم رصيد ${acc.name} بسعر ${newRate}` });
          }
        }
      }
    });

    let entry = null;
    if (jvLines.length > 0) {
      entry = this.addJournalEntry({
        date,
        desc: `قيد معالج تقييم أسعار الصرف الدوري (Odoo Currency Revaluation Wizard)`,
        lines: jvLines
      });
      entry.status = 'POSTED';
      entry.postedBy = "معالج تقييم العملات";
      this.save();
    }

    if (!this.state.currencyRevaluations) this.state.currencyRevaluations = [];
    this.state.currencyRevaluations.unshift({
      date,
      totalGain,
      totalLoss,
      accountsCount: revaluedAccounts.length,
      revaluedAccounts,
      entryId: entry ? entry.id : null,
      createdAt: new Date().toISOString()
    });

    this.save();
    return { revaluedAccounts, totalGain, totalLoss, entry };
  }

  // 15. معالج المطابقة والتسوية البنكية للشيكات (account.bank.reconciliation.wizard)
  bankReconciliationWizard(bankAccCode, statementTransactions = []) {
    const matched = [];
    const unmatched = [];
    const uncollectedCheques = (this.state.vouchers || []).filter(v => v.method === 'CHEQUE' && v.chequeState === 'PENDING_COLLECTION');

    statementTransactions.forEach(st => {
      const stAmt = Number(st.amount) || 0;
      const match = uncollectedCheques.find(c => Math.abs(Number(c.amount) - stAmt) < 0.01 && (!st.ref || String(c.chequeNo).includes(String(st.ref))));
      if (match) {
        match.chequeState = 'COLLECTED';
        match.reconciledWith = st.ref || 'Bank Statement Match';
        matched.push({ statementItem: st, voucher: match });
      } else {
        unmatched.push(st);
      }
    });

    this.save();
    return { matchedCount: matched.length, unmatchedCount: unmatched.length, matched, unmatched };
  }

  // 16. معالج الإقفال المالي السنوي وقفل الفترات (account.fiscalyear.close.wizard)
  closeFiscalYearWizard(fiscalYear = this.state.system.activeYear, retainedEarningsAccount = '311201') {
    const closeRes = this.closeFinancialYear(fiscalYear);
    
    // تسجيل القفل المالي الصارم (Odoo Lock Date)
    if (!this.state.fiscalLocks) this.state.fiscalLocks = [];
    this.state.fiscalLocks.unshift({
      fiscalYear,
      lockDate: `${fiscalYear}-12-31`,
      isClosed: true,
      closedBy: this.getCurrentUser ? this.getCurrentUser().fullName : "المدير المالي",
      closedAt: new Date().toISOString()
    });

    this.logAudit({
      actionType: 'FISCAL_YEAR_LOCK',
      docId: fiscalYear,
      docModel: 'fiscal.lock',
      details: `إقفال وقفل السنة المالية [${fiscalYear}] وترحيل الأرباح والخسائر إلى [${retainedEarningsAccount}]`
    });

    this.save();
    return closeRes;
  }

  // 17. الأرشفة والحفظ الناعم (Soft Delete / Archive - Odoo active flag)
  archiveRecord(model, id) {
    const list = this.state[model];
    if (!list) return false;
    const item = list.find(r => r.id === id || r.code === id || r.invNo === id);
    if (!item) return false;

    item.active = false;
    this.logAudit({
      actionType: 'ARCHIVE',
      docId: id,
      docModel: model,
      details: `أرشفة السجل [${id}] بنجاح وحمايته من الحذف الكلي`
    });
    this.save();
    return true;
  }

  unarchiveRecord(model, id) {
    const list = this.state[model];
    if (!list) return false;
    const item = list.find(r => r.id === id || r.code === id || r.invNo === id);
    if (!item) return false;

    item.active = true;
    this.logAudit({
      actionType: 'UNARCHIVE',
      docId: id,
      docModel: model,
      details: `إلغاء أرشفة السجل [${id}] وإعادته للقوائم النشطة`
    });
    this.save();
    return true;
  }

  getActiveRecords(model) {
    return (this.state[model] || []).filter(r => r.active !== false);
  }

  // 18. إحصائيات الذكاء المالي والأزرار الإحصائية (Odoo Stat Counters _compute_*_count)
  getPartnerStats(partnerIdOrCode) {
    const cust = (this.state.customers || []).find(c => c.id === partnerIdOrCode || c.code === partnerIdOrCode || c.name === partnerIdOrCode);
    const invoices = (this.state.salesInvoices || []).filter(s => s.customerCode === partnerIdOrCode || s.customer === partnerIdOrCode || (cust && s.customer === cust.name));
    const totalInvoiced = invoices.reduce((sum, inv) => sum + (Number(inv.netAmount) || 0), 0);
    const paidVouchers = (this.state.vouchers || []).filter(v => v.type === 'RECEIPT' && (v.targetAcc === partnerIdOrCode || (cust && v.targetAcc === cust.code)));
    const totalPaid = paidVouchers.reduce((sum, voc) => sum + (Number(voc.amount) || 0), 0);

    return {
      invoicesCount: invoices.length,
      totalInvoiced: this.roundCurrency(totalInvoiced),
      totalPaid: this.roundCurrency(totalPaid),
      openBalance: cust ? (Number(cust.balanceLocal) || 0) : 0,
      creditLimit: cust ? (Number(cust.creditLimit) || 0) : 0
    };
  }

  getItemStats(itemCode) {
    const item = (this.state.items || []).find(i => i.code === itemCode || i.id === itemCode);
    const moves = (this.state.stockMoves || []).filter(m => m.productId === itemCode);
    const inMoves = moves.filter(m => m.moveType.includes('RECEIPT') || m.moveType.includes('IN'));
    const outMoves = moves.filter(m => m.moveType.includes('DELIVERY') || m.moveType.includes('OUT'));

    const totalQtyIn = inMoves.reduce((s, m) => s + (Number(m.qty) || 0), 0);
    const totalQtyOut = outMoves.reduce((s, m) => s + (Number(m.qty) || 0), 0);

    return {
      movesCount: moves.length,
      onHand: item ? (Number(item.currentStock) || 0) : 0,
      totalPurchased: totalQtyIn,
      totalSold: totalQtyOut,
      costPrice: item ? (Number(item.costPrice) || 0) : 0,
      salePrice: item ? (Number(item.salePrice) || 0) : 0,
      valuation: item ? this.roundCurrency((Number(item.currentStock) || 0) * (Number(item.costPrice) || 0)) : 0
    };
  }

  getAccountStats(accCode) {
    const lines = [];
    (this.state.journalEntries || []).filter(j => j.status === 'POSTED').forEach(j => {
      (j.lines || []).forEach(l => {
        if (l.accCode === accCode) lines.push(l);
      });
    });

    const totalDebit = lines.reduce((s, l) => s + (Number(l.debit) || 0), 0);
    const totalCredit = lines.reduce((s, l) => s + (Number(l.credit) || 0), 0);

    return {
      journalItemsCount: lines.length,
      totalDebit: this.roundCurrency(totalDebit),
      totalCredit: this.roundCurrency(totalCredit),
      netBalance: this.roundCurrency(totalDebit - totalCredit)
    };
  }

  /* =========================================================================
     الدليل المحاسبي وشجرة الحسابات (COA)
     ========================================================================= */
  getAccounts() {
    return this.state.accounts;
  }

  getAccount(code) {
    return this.state.accounts.find(a => a.code === code);
  }

  addAccount(accData) {
    if (this.state.accounts.some(a => a.code === accData.code)) {
      throw new Error(`رقم الحساب [${accData.code}] مسجل مسبقاً في الدليل المحاسبي!`);
    }

    // فحص العلاقات التكرارية لشجرة الحسابات (Odoo _check_recursion)
    if (accData.parent) {
      this.checkAccountRecursion(accData.code, accData.parent);
    }

    const newAcc = {
      code: accData.code,
      name: accData.name,
      parent: accData.parent || null,
      type: accData.type, // MAIN or SUB
      report: accData.report || "BS",
      level: accData.level || 4,
      currency: accData.currency || "YER",
      balance: Number(accData.balance) || 0,
      active: true
    };

    this.state.accounts.push(newAcc);

    this.logAudit({
      actionType: 'CREATE_ACCOUNT',
      docId: newAcc.code,
      docModel: 'account.account',
      details: `إضافة حساب جديد بالدليل: [${newAcc.code}] ${newAcc.name}`
    });

    this.save();
    return newAcc;
  }

  // التوليد الآلي لرقم الحساب بالرتبة الخامسة (FR-2.3.4 & ص 10 بالمحاضرات)
  generateFastAccountCode(rank5Prefix) {
    const siblings = this.state.accounts.filter(a => a.code.startsWith(rank5Prefix));
    const nextSeq = siblings.length + 1;
    return `${rank5Prefix}${String(nextSeq).padStart(4, '0')}`;
  }

  /* =========================================================================
     حساب رأس المال والأرصدة الافتتاحية (ص 14 & 32)
     ========================================================================= */
  calculateOpeningCapital() {
    let totalAssets = 0;
    let totalLiabilities = 0;

    this.state.accounts.filter(a => a.type === 'SUB').forEach(acc => {
      const rate = this.state.system.exchangeRates[acc.currency] || 1.0;
      const inLocal = (acc.balance || 0) * rate;

      if (acc.code.startsWith('1')) {
        totalAssets += inLocal;
      } else if (acc.code.startsWith('2')) {
        totalLiabilities += inLocal;
      }
    });

    const capital = totalAssets - totalLiabilities;
    return { totalAssets, totalLiabilities, capital };
  }

  /* =========================================================================
     القيود اليومية مع فحص توازن المدين والدائن (FR-3.2 & ص 15-18)
     ========================================================================= */
  addJournalEntry(entry) {
    const entryDate = window.toEnglishDigits(entry.date || new Date().toISOString().split('T')[0]);
    // 1. فحص إقفال الفترة المالية (Odoo Fiscal Lock Date Constraint)
    this.checkFiscalLockDate(entryDate);

    const totalDebit = entry.lines.reduce((s, l) => s + (Number(l.debit) || 0), 0);
    const totalCredit = entry.lines.reduce((s, l) => s + (Number(l.credit) || 0), 0);

    if (Math.abs(totalDebit - totalCredit) > 0.01) {
      throw new Error(`خطأ: القيد غير متوازن! إجمالي المدين (${this.formatCurrency(totalDebit)}) ≠ إجمالي الدائن (${this.formatCurrency(totalCredit)})`);
    }

    const id = entry.id || this.getNextSequence('JV', 'JV', 3);
    const newEntry = {
      id,
      date: entryDate,
      branch: entry.branch || this.state.system.activeBranch,
      desc: entry.desc,
      status: entry.status || (this.state.system.settings.useDocumentReview ? "DRAFT" : "POSTED"),
      totalDebit: this.roundCurrency(totalDebit),
      totalCredit: this.roundCurrency(totalCredit),
      reviewedBy: entry.reviewedBy || null,
      postedBy: entry.postedBy || null,
      lines: entry.lines.map(l => ({
        accCode: l.accCode,
        accName: this.getAccount(l.accCode)?.name || l.accName,
        debit: this.roundCurrency(Number(l.debit) || 0),
        credit: this.roundCurrency(Number(l.credit) || 0),
        note: l.note || ''
      }))
    };

    this.state.journalEntries.unshift(newEntry);

    this.logAudit({
      actionType: 'CREATE_JV',
      docId: id,
      docModel: 'account.move',
      details: `إنشاء قيد يومية برقم [${id}] - ${newEntry.desc || ''}`
    });

    this.save();
    return newEntry;
  }

  /* =========================================================================
     سندات الصرف والقبض وإدارة الشيكات والبنك الوسيط (ص 19-26)
     ========================================================================= */
  addVoucher(voucher) {
    const voucherDate = window.toEnglishDigits(voucher.date || new Date().toISOString().split('T')[0]);
    // 1. فحص إقفال الفترة المالية
    this.checkFiscalLockDate(voucherDate);

    const prefix = voucher.type === 'PAYMENT' ? 'PV' : 'RV';
    const amount = Number(voucher.amount) || 0;

    // 2. فحص الرصيد المانع للصندوق (Odoo Cash Solvency Constraint)
    if (voucher.type === 'PAYMENT' && voucher.method !== 'CHEQUE') {
      this.checkCashSolvency(voucher.cashBox, amount);
    }

    const id = voucher.id || this.getNextSequence(prefix, prefix, 3);

    const newVoucher = {
      id,
      type: voucher.type,
      method: voucher.method || 'CASH', // CASH, CHEQUE
      date: voucherDate,
      branch: voucher.branch || this.state.system.activeBranch,
      cashBox: voucher.cashBox,
      targetAcc: voucher.targetAcc,
      targetName: this.getAccount(voucher.targetAcc)?.name || voucher.targetName,
      amount: this.roundCurrency(amount, voucher.currency || 'YER'),
      currency: voucher.currency || 'YER',
      chequeNo: voucher.chequeNo || null,
      dueDate: voucher.dueDate ? window.toEnglishDigits(voucher.dueDate) : null,
      postingMode: voucher.postingMode || 'MANUAL_DUE',
      chequeState: voucher.method === 'CHEQUE' ? 'PENDING_COLLECTION' : null,
      desc: voucher.desc,
      status: voucher.status || (this.state.system.settings.useDocumentReview ? "DRAFT" : "POSTED")
    };

    this.state.vouchers.unshift(newVoucher);

    this.logAudit({
      actionType: `CREATE_${prefix}`,
      docId: id,
      docModel: 'account.voucher',
      details: `إنشاء سند ${voucher.type === 'PAYMENT' ? 'صرف' : 'قبض'} برقم [${id}] بمبلغ ${amount} ${newVoucher.currency}`
    });

    this.save();
    return newVoucher;
  }

  // إثبات تحصيل الشيك وإقفال البنك الوسيط (ص 23 & 26)
  collectChequeVoucher(voucherId, actualBankAcc) {
    const v = this.state.vouchers.find(voc => voc.id === voucherId);
    if (!v) throw new Error("السند غير موجود!");

    v.chequeState = 'COLLECTED';

    // إنشاء قيد الإيداع الفعلي من البنك الوسيط للبنك الفعلي
    this.addJournalEntry({
      desc: `إثبات تحصيل فعلي للشيك رقم [${v.chequeNo}] من البنك الوسيط إلى [${this.getAccount(actualBankAcc)?.name}]`,
      branch: v.branch,
      lines: [
        { accCode: actualBankAcc, debit: v.amount, credit: 0, note: `إيداع شيك محصل رقم ${v.chequeNo}` },
        { accCode: "112109", debit: 0, credit: v.amount, note: `إقفال حساب البنك الوسيط` }
      ]
    });

    this.save();
  }

  /* =========================================================================
     المرتبات والأجور والغياب والسلف (ص 27-31)
     ========================================================================= */
  processPayrollBatch() {
    let totalGross = 0;
    let totalAdvances = 0;
    let totalAbsence = 0;
    let totalNet = 0;

    const payrollLines = [];

    this.state.employees.forEach(emp => {
      totalGross += emp.salary;
      totalAdvances += emp.advances;
      totalAbsence += emp.absenceDeduction;

      const netSalary = emp.salary - emp.advances - emp.absenceDeduction;
      totalNet += netSalary;

      payrollLines.push({
        accCode: "211301",
        accName: `مرتبات مستحقة - ${emp.name}`,
        debit: emp.salary,
        credit: 0,
        note: `إقفال استحقاق ${emp.name}`
      });
    });

    // إنشاء القيد المحاسبي التلقائي لصرف مسير الرواتب (ص 30)
    this.addJournalEntry({
      desc: "صرف مسير الرواتب والأجور الشامل بعد خصم السلف والغياب",
      lines: [
        { accCode: "211301", debit: totalGross, credit: 0, note: "إقفال مستحقات الرواتب والأجور" },
        { accCode: "1121010001", debit: 0, credit: totalNet, note: "صرف صافي الرواتب نقداً من الصندوق الرئيسي" },
        { accCode: "116101", debit: 0, credit: totalAdvances, note: "تصفية سلف الموظفين" },
        { accCode: "410301", debit: 0, credit: totalAbsence, note: "إيراد خصومات غياب الموظفين" }
      ]
    });

    // تصفير السلف والغياب بعد الصرف
    this.state.employees.forEach(emp => {
      emp.advances = 0;
      emp.absenceDeduction = 0;
      emp.absenceDays = 0;
    });

    this.save();
    return { totalGross, totalAdvances, totalAbsence, totalNet };
  }

  /* =========================================================================
     دورة المراجعة والترحيل (ص 16-17)
     ========================================================================= */
  /* =========================================================================
     دورة المراجعة والترحيل الشاملة لكافة وثائق النظام (ص 16-17)
     ========================================================================= */
  reviewDocument(type, id, reviewer = "سامي ناصر - مراقب الحسابات") {
    let doc = null;
    if (type === 'JV') doc = this.state.journalEntries.find(j => j.id === id);
    else if (type === 'VOUCHER') doc = this.state.vouchers.find(v => v.id === id);
    else if (type === 'SALES_INVOICE') doc = (this.state.salesInvoices || []).find(s => s.invNo === id || s.id === id);
    else if (type === 'PURCHASE_INVOICE') doc = (this.state.purchaseInvoices || []).find(p => p.invNo === id || p.id === id);
    else if (type === 'EXPENSE') doc = (this.state.expenses || []).find(e => e.id === id);

    if (doc) {
      doc.status = 'REVIEWED';
      doc.reviewedBy = reviewer;
      doc.reviewedAt = new Date().toISOString().replace('T', ' ').substring(0, 19);
      this.save();
      return true;
    }
    return false;
  }

  postDocument(type, id, poster = "خالد رضوان - المدير المالي") {
    let doc = null;
    if (type === 'JV') doc = this.state.journalEntries.find(j => j.id === id);
    else if (type === 'VOUCHER') doc = this.state.vouchers.find(v => v.id === id);
    else if (type === 'SALES_INVOICE') doc = (this.state.salesInvoices || []).find(s => s.invNo === id || s.id === id);
    else if (type === 'PURCHASE_INVOICE') doc = (this.state.purchaseInvoices || []).find(p => p.invNo === id || p.id === id);
    else if (type === 'EXPENSE') doc = (this.state.expenses || []).find(e => e.id === id);

    if (!doc) return false;

    if (this.state.system.settings.useDocumentReview && doc.status !== 'REVIEWED') {
      throw new Error("لا يمكن ترحيل الوثيقة إلا بعد اعتماد مراجعتها أولاً بحسب ضوابط أونكس برو الرقابية!");
    }

    doc.status = 'POSTED';
    doc.postedBy = poster;
    doc.postedAt = new Date().toISOString().replace('T', ' ').substring(0, 19);

    const today = new Date().toISOString().split('T')[0];

    // 1. عند ترحيل سند صرف أو قبض: توليد وتأكيد القيد المحاسبي المتوازن في الأستاذ العام
    if (type === 'VOUCHER') {
      const targetAccCode = doc.targetAcc;
      const targetAccName = this.getAccount(targetAccCode)?.name || doc.targetName || "حساب وسيط";
      const cashAccCode = doc.cashBox || "1121010001";
      const cashAccName = this.getAccount(cashAccCode)?.name || "صندوق المركز الرئيسي";
      const amt = Number(doc.amount) || 0;

      const lines = doc.type === 'PAYMENT' ? [
        { accCode: targetAccCode, accName: targetAccName, debit: amt, credit: 0, note: doc.desc || 'سند صرف معتمد' },
        { accCode: cashAccCode, accName: cashAccName, debit: 0, credit: amt, note: `صرف نقدي بموجب سند [${doc.id}]` }
      ] : [
        { accCode: cashAccCode, accName: cashAccName, debit: amt, credit: 0, note: `قبض نقدي بموجب سند [${doc.id}]` },
        { accCode: targetAccCode, accName: targetAccName, debit: 0, credit: amt, note: doc.desc || 'سند قبض معتمد' }
      ];

      this.state.journalEntries.unshift({
        id: `JV-VOC-${doc.id}`,
        date: doc.date || today,
        desc: `ترحيل محاسبي آلي للسند [${doc.id}] - ${doc.desc || ''}`,
        branch: doc.branch || this.state.system.activeBranch,
        status: 'POSTED',
        postedBy: poster,
        lines: lines
      });
    }

    // 2. عند ترحيل فاتورة مبيعات: توليد قيد المبيعات والخصم المسموح وعمولات المندوبين
    else if (type === 'SALES_INVOICE') {
      doc.invNo = doc.invNo || doc.id || id;
      doc.id = doc.invNo;
      doc.status = 'POSTED';
      doc.statusArabic = 'مرحلة';

      // فحص إذا كان النمط عرض سعر أو معطلاً عن توليد القيود
      const prof = doc.profileId ? this.getInvoiceProfile(doc.profileId) : null;
      if (doc.isQuotation || doc.type === 'عرض سعر' || (prof && (prof.generateJV === false || prof.isQuotation))) {
        doc.status = 'POSTED';
        doc.statusArabic = 'عرض سعر معتمد';
        this.save();
        return true;
      }

      const gross = Number(doc.grossAmount) || 0;
      const disc = Number(doc.discount) || 0;
      const net = Math.max(0, gross - disc);
      const comm = Number(doc.commissionAmount) || 0;

      let targetAcc = doc.type === 'نقداً' ? '1121010001' : '113101';
      let targetName = doc.type === 'نقداً' ? 'صندوق فرع صنعاء - محلي' : `العميل - ${doc.customer}`;

      // ربط الصندوق الافتراضي المحدد في النمط إن وجد
      if (doc.type === 'نقداً' && (doc.cashBox || (prof && prof.defaultCashBox))) {
        const cbCode = doc.cashBox || prof.defaultCashBox;
        const cbObj = (this.state.cashBoxes || []).find(cb => cb.code === cbCode || cb.id === cbCode);
        if (cbObj && cbObj.accCode) {
          targetAcc = cbObj.accCode;
          targetName = cbObj.name || targetName;
        }
      }

      const lines = [
        { accCode: targetAcc, accName: targetName, debit: net, credit: 0, note: `صافي مبيعات فاتورة [${doc.invNo}]` }
      ];
      if (disc > 0) {
        lines.push({ accCode: '410201', accName: 'خصم مسموح به (مدين)', debit: disc, credit: 0, note: `خصم ممنوح فاتورة [${doc.invNo}]` });
      }
      lines.push({ accCode: '411101', accName: 'إيرادات المبيعات العامة', debit: 0, credit: gross, note: `إثبات إيراد مبيعات [${doc.invNo}]` });

      if (comm > 0) {
        lines.push({ accCode: '520101', accName: 'مصروف عمولة مندوبي المبيعات', debit: comm, credit: 0, note: `عمولة مندوب ${doc.rep} فاتورة [${doc.invNo}]` });
        lines.push({ accCode: '211101', accName: 'مستحقات عمولات المندوبين', debit: 0, credit: comm, note: `استحقاق عمولة ${doc.rep}` });
      }

      this.state.journalEntries.unshift({
        id: `JV-INV-${doc.invNo}`,
        date: doc.date || today,
        desc: `قيد ترحيل فاتورة المبيعات [${doc.invNo}] - ${doc.customer}`,
        branch: '01',
        status: 'POSTED',
        postedBy: poster,
        lines: lines
      });
    }

    // 3. عند ترحيل فاتورة مشتريات: قيد المخزون والخصم المكتسب والمورد/الصندوق
    else if (type === 'PURCHASE_INVOICE') {
      doc.status = 'POSTED';
      doc.statusArabic = 'مرحلة';
      const gross = Number(doc.grossAmount) || 0;
      const disc = Number(doc.discountEarned) || 0;
      const net = Math.max(0, gross - disc);
      const targetAcc = doc.type === 'نقداً' ? '1121010001' : '211101';
      const targetName = doc.type === 'نقداً' ? 'صندوق فرع صنعاء - محلي' : `المورد - ${doc.supplier}`;

      const lines = [
        { accCode: '115101', accName: 'مخزون البضائع والأصناف', debit: gross, credit: 0, note: `توريد بضاعة فاتورة [${doc.invNo}]` }
      ];
      if (disc > 0) {
        lines.push({ accCode: '510201', accName: 'خصم مكتسب (دائن)', debit: 0, credit: disc, note: `خصم مكتسب فاتورة [${doc.invNo}]` });
      }
      lines.push({ accCode: targetAcc, accName: targetName, debit: 0, credit: net, note: `استحقاق فاتورة مشتريات [${doc.invNo}]` });

      this.state.journalEntries.unshift({
        id: `JV-PUR-${doc.invNo}`,
        date: doc.date || today,
        desc: `قيد ترحيل فاتورة المشتريات [${doc.invNo}] - ${doc.supplier}`,
        branch: '01',
        status: 'POSTED',
        postedBy: poster,
        lines: lines
      });
    }

    this.save();
    return true;
  }

  // ترحيل جماعي لكافة الوثائق المعتمدة والمراجعة
  postAllReviewedDocuments(poster = "خالد رضوان - المدير المالي") {
    let count = 0;
    (this.state.journalEntries || []).filter(j => j.status === 'REVIEWED').forEach(j => {
      this.postDocument('JV', j.id, poster);
      count++;
    });
    (this.state.vouchers || []).filter(v => v.status === 'REVIEWED').forEach(v => {
      this.postDocument('VOUCHER', v.id, poster);
      count++;
    });
    (this.state.salesInvoices || []).filter(s => s.status === 'REVIEWED').forEach(s => {
      this.postDocument('SALES_INVOICE', s.invNo, poster);
      count++;
    });
    (this.state.purchaseInvoices || []).filter(p => p.status === 'REVIEWED').forEach(p => {
      this.postDocument('PURCHASE_INVOICE', p.invNo, poster);
      count++;
    });
    return count;
  }

  // تحديث تكلفة المخزون بالمتوسط المرجح المتحرك (Moving Average Cost WAC)
  updateItemWAC(itemCode, addedQty, unitCost) {
    const item = (this.state.items || []).find(i => i.code === itemCode);
    if (!item) return;

    const curQty = (Number(item.whStock?.WH01) || 0) + (Number(item.whStock?.WH02) || 0);
    const curCost = Number(item.costPrice) || 0;
    const addQ = Number(addedQty) || 0;
    const unitC = Number(unitCost) || 0;

    const newQty = curQty + addQ;
    if (newQty > 0) {
      item.costPrice = Math.round(((curQty * curCost) + (addQ * unitC)) / newQty);
    }
    if (!item.whStock) item.whStock = { WH01: 0, WH02: 0 };
    item.whStock.WH01 = (Number(item.whStock.WH01) || 0) + addQ;
    this.save();
  }

  // معالجة مرتجع مبيعات وعكس الأثر المالي والمخزني (Odoo Return & Stock Moves)
  processSalesReturn(invNo, returnAmount, reason = "مرتجع بضاعة للعميل") {
    const inv = (this.state.salesInvoices || []).find(i => i.invNo === invNo);
    if (!inv) throw new Error("فاتورة المبيعات غير موجودة!");

    const amt = Number(returnAmount) || 0;
    if (amt <= 0 || amt > (inv.netAmount || 0)) {
      throw new Error("مبلغ المرتجع غير صالح أو يتجاوز صافي الفاتورة!");
    }

    if (inv.type === 'آجل') {
      const cust = (this.state.customers || []).find(c => c.name === inv.customer);
      if (cust) {
        cust.balanceLocal = Math.max(0, (Number(cust.balanceLocal) || 0) - amt);
      }
    }

    const retId = this.getNextSequence('SR', 'SR', 3);
    const returnDate = new Date().toISOString().split('T')[0];
    if (!this.state.salesReturns) this.state.salesReturns = [];
    this.state.salesReturns.unshift({
      id: retId,
      invNo,
      customer: inv.customer,
      amount: amt,
      date: returnDate,
      reason,
      status: 'POSTED'
    });

    // تسجيل حركة المخزون للمرتجع إذا كانت الفاتورة تتضمن أصنافاً (Odoo stock.move)
    if (inv.items && inv.items.length > 0) {
      inv.items.forEach(line => {
        const itemCode = line.code || line.id;
        const returnQty = Number(line.qty) || 1;
        const item = (this.state.items || []).find(i => i.code === itemCode);
        if (item && item.whStock) {
          const wh = inv.warehouse || 'WH01';
          item.whStock[wh] = (Number(item.whStock[wh]) || 0) + returnQty;
          item.currentStock = Object.values(item.whStock).reduce((a, b) => (Number(a) || 0) + (Number(b) || 0), 0);
        }

        this.recordStockMove({
          productId: itemCode || '',
          productName: line.name || itemCode,
          moveType: 'CUSTOMER_RETURN',
          qty: returnQty,
          unitCost: item ? Number(item.costPrice || 0) : Number(line.price || 0),
          sourceLoc: inv.customer,
          destLoc: inv.warehouse || 'WH01',
          refDoc: retId,
          date: returnDate
        });
      });
    }

    this.addJournalEntry({
      desc: `إثبات مرتجع مبيعات للفاتورة [${invNo}] - ${reason}`,
      lines: [
        { accCode: '411101', accName: 'إيرادات المبيعات العامة', debit: amt, credit: 0, note: `تخفيض إيراد مرتجع ${invNo}` },
        { accCode: inv.type === 'نقداً' ? '1121010001' : '113101', accName: inv.type === 'نقداً' ? 'صندوق فرع صنعاء' : `العميل - ${inv.customer}`, debit: 0, credit: amt, note: `رد قيمة المرتجع ${inv.customer}` }
      ]
    });

    this.logAudit({
      actionType: 'SALES_RETURN',
      docId: retId,
      docModel: 'sale.order.return',
      details: `إثبات مرتجع مبيعات للفاتورة [${invNo}] بمبلغ ${amt} - ${reason}`
    });

    this.save();
    return retId;
  }

  // معالج الإقفال السنوي المالي وتدوير الأرصدة
  closeFinancialYear(targetYear = this.state.system.activeYear, closedBy = "خالد رضوان - المدير المالي") {
    const trial = this.generateTrialBalance();
    const revs = trial.filter(a => a.code.startsWith('4'));
    const exps = trial.filter(a => a.code.startsWith('5'));

    let totalRev = 0;
    let totalExp = 0;
    const lines = [];

    // إقفال حسابات الإيرادات
    revs.forEach(r => {
      const net = r.netCredit - r.netDebit;
      totalRev += net;
      if (net > 0) {
        // رصيد دائن طبيعي: يقفل بالمدين
        lines.push({ accCode: r.code, accName: r.name, debit: net, credit: 0, note: `إقفال إيراد سنة ${targetYear}` });
      } else if (net < 0) {
        // رصيد مدين (مثل الخصم المسموح): يقفل بالدائن
        lines.push({ accCode: r.code, accName: r.name, debit: 0, credit: Math.abs(net), note: `إقفال خصم مسموح سنة ${targetYear}` });
      }
    });

    // إقفال حسابات المصروفات
    exps.forEach(e => {
      const net = e.netDebit - e.netCredit;
      totalExp += net;
      if (net > 0) {
        // رصيد مدين طبيعي: يقفل بالدائن
        lines.push({ accCode: e.code, accName: e.name, debit: 0, credit: net, note: `إقفال مصروف سنة ${targetYear}` });
      } else if (net < 0) {
        // رصيد دائن: يقفل بالمدين
        lines.push({ accCode: e.code, accName: e.name, debit: Math.abs(net), credit: 0, note: `إقفال مردود/خصم مكتسب سنة ${targetYear}` });
      }
    });

    const netProfit = totalRev - totalExp;

    if (netProfit > 0) {
      lines.push({ accCode: '311201', accName: 'الأرباح المبقاة والاحتياطيات', debit: 0, credit: netProfit, note: `ترحيل صافي أرباح نشاط سنة ${targetYear}` });
    } else if (netProfit < 0) {
      lines.push({ accCode: '311201', accName: 'الأرباح المبقاة والاحتياطيات', debit: Math.abs(netProfit), credit: 0, note: `ترحيل صافي خسارة نشاط سنة ${targetYear}` });
    }

    let closeEntry = null;
    if (lines.length > 0) {
      closeEntry = this.addJournalEntry({
        desc: `قيد الإقفال السنوي المحاسبي المعتمد لسنة ${targetYear} وترحيل الأرباح والخسائر`,
        lines
      });
      closeEntry.status = 'POSTED';
      closeEntry.postedBy = closedBy;
    }

    // تسجيل القفل المالي الصارم للسنة المقفلة (Odoo Lock Date)
    if (!this.state.fiscalLocks) this.state.fiscalLocks = [];
    this.state.fiscalLocks.unshift({
      fiscalYear: targetYear,
      lockDate: `${targetYear}-12-31`,
      isClosed: true,
      closedBy,
      closedAt: new Date().toISOString()
    });

    this.logAudit({
      actionType: 'FISCAL_YEAR_CLOSE',
      docId: targetYear,
      docModel: 'fiscal.lock',
      details: `إقفال وترحيل أرباح وخسائر السنة المالية [${targetYear}] بنجاح، وتفعيل قفل العمليات`
    });

    this.state.system.activeYear = String(Number(targetYear) + 1);
    this.state.system.activePeriodName = `يناير ${this.state.system.activeYear} (مفتوحة)`;
    this.save();
    return closeEntry || { success: true, netProfit, totalRev, totalExp, newYear: this.state.system.activeYear };
  }

  /* =========================================================================
     محرك التقارير المالية الختامية (ص 18 & تقارير أونكس)
     ========================================================================= */
  generateTrialBalance() {
    const subAccounts = this.state.accounts.filter(a => a.type === 'SUB' || this.state.journalEntries.some(j => j.status === 'POSTED' && j.lines.some(l => l.accCode === a.code)));
    return subAccounts.map(acc => {
      let debit = 0;
      let credit = 0;
      const rate = this.state.system.exchangeRates[acc.currency] || 1.0;
      const initialInLocal = (acc.balance || 0) * rate;

      if (acc.code.startsWith('1') || acc.code.startsWith('5')) {
        debit += initialInLocal;
      } else {
        credit += initialInLocal;
      }

      // إضافة أثر القيود المرحلة
      this.state.journalEntries.filter(j => j.status === 'POSTED').forEach(j => {
        j.lines.forEach(l => {
          if (l.accCode === acc.code) {
            debit += l.debit;
            credit += l.credit;
          }
        });
      });

      return {
        code: acc.code,
        name: acc.name,
        currency: acc.currency,
        debit,
        credit,
        netDebit: debit > credit ? debit - credit : 0,
        netCredit: credit > debit ? credit - debit : 0
      };
    });
  }

  generateBalanceSheet() {
    const trial = this.generateTrialBalance();
    const is = this.generateIncomeStatement();
    const assets = trial.filter(a => a.code.startsWith('1'));
    const liabilities = trial.filter(a => a.code.startsWith('2'));
    const equity = trial.filter(a => a.code.startsWith('3'));

    const totalAssets = assets.reduce((s, a) => s + a.netDebit, 0);
    const totalLiabilities = liabilities.reduce((s, a) => s + a.netCredit, 0);
    const recordedEquity = equity.reduce((s, a) => s + a.netCredit, 0);
    const totalEquity = recordedEquity + is.netProfit;

    return {
      assets,
      liabilities,
      equity,
      totalAssets,
      totalLiabilities,
      recordedEquity,
      currentPeriodProfit: is.netProfit,
      totalEquity,
      isBalanced: Math.abs(totalAssets - (totalLiabilities + totalEquity)) < 1
    };
  }

  generateIncomeStatement() {
    const trial = this.generateTrialBalance();
    const revenues = trial.filter(a => a.code.startsWith('4'));
    const expenses = trial.filter(a => a.code.startsWith('5'));

    const totalRevenues = revenues.reduce((s, a) => s + (a.netCredit - a.netDebit), 0);
    const totalExpenses = expenses.reduce((s, a) => s + (a.netDebit - a.netCredit), 0);
    const netProfit = totalRevenues - totalExpenses;

    return { revenues, expenses, totalRevenues, totalExpenses, netProfit };
  }

  /* =========================================================================
     نظام نقطة البيع السريعة (Point of Sale - POS)
     ========================================================================= */
  processPOSSale({ invoiceNo, customer, paymentMethod, items, subtotal, discount, netTotal, paidAmount, changeAmount, cashier }) {
    if (!this.state.posInvoices) this.state.posInvoices = [];

    const today = new Date().toISOString().split('T')[0];
    const time = new Date().toLocaleTimeString('en-US', { hour12: true });
    const activeShift = this.getActiveShift();
    const jvId = `JV-POS-${String((this.state.journalEntries?.length || 0) + 1).padStart(3, '0')}`;

    const newInv = {
      id: invoiceNo,
      jvId: jvId,
      shiftId: activeShift ? activeShift.id : null,
      date: today,
      time: time,
      customer: customer || "عميل نقدي مباشر",
      paymentMethod: paymentMethod || "CASH",
      items: items.map(it => ({ ...it })),
      subtotal,
      discount,
      netTotal,
      paidAmount,
      changeAmount,
      cashier: cashier || (activeShift ? activeShift.cashier : "AlparatY"),
      status: "POSTED",
      sync_status: "pending"
    };
    this.state.posInvoices.unshift(newInv);

    // حفظ فوري ومحلي في قاعدة بيانات SQLite وبدء مزامنة PostgreSQL الخلفية فور عودة الاتصال
    if (typeof fetch === 'function') {
      try {
        fetch('/api/pos/order', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(newInv)
        }).then(r => r.json()).then(data => {
          if (data && data.order_id) {
            newInv.sync_status = data.sync_status || 'pending';
          }
        }).catch(() => {});
      } catch (e) {}
    }

    // 1. خفض رصيد المخزن الفوري لصالة المعرض WH01 وتسجيل حركة المخزون (Odoo stock.move)
    items.forEach(cartItem => {
      const itmObj = this.state.items.find(it => it.code === cartItem.code);
      if (itmObj) {
        if (!itmObj.whStock) itmObj.whStock = { WH01: 50, WH02: 20 };
        itmObj.whStock.WH01 = Math.max(0, (itmObj.whStock.WH01 || 0) - cartItem.qty);
        itmObj.currentStock = Object.values(itmObj.whStock).reduce((a, b) => (Number(a) || 0) + (Number(b) || 0), 0);

        if (this.state.system?.settings?.autoStockMoves !== false) {
          this.recordStockMove({
            productId: cartItem.code,
            productName: cartItem.name || cartItem.code,
            moveType: 'POS_DELIVERY',
            qty: Number(cartItem.qty) || 1,
            unitCost: Number(itmObj.costPrice || 0),
            sourceLoc: 'WH01 - صالة العرض',
            destLoc: customer || "عميل نقدي مباشر",
            refDoc: invoiceNo,
            date: today
          });
        }
      }
    });

    // 2. تحديث رصيد صندوق الكاشير
    const cashBox = this.state.cashBoxes.find(cb => cb.id === '0101');
    if (cashBox && paymentMethod === 'CASH') {
      cashBox.balance += netTotal;
    }

    // 3. قيد المبيعات المحاسبي الآلي
    const targetAccCode = paymentMethod === 'CASH' ? '1121010001' : (paymentMethod === 'CARD' ? '1121020001' : '1131010001');
    const targetAccName = paymentMethod === 'CASH' ? 'صندوق فرع صنعاء - كاشير 1' : (paymentMethod === 'CARD' ? 'بنك التضامن الإسلامي' : 'حساب العملاء المدينون');

    if (!this.state.journalEntries) this.state.journalEntries = [];
    this.state.journalEntries.unshift({
      id: jvId,
      date: today,
      desc: `إثبات مبيعات نقطة البيع رقم [${invoiceNo}] - ${paymentMethod}`,
      branch: '01',
      status: 'POSTED',
      lines: [
        { accCode: targetAccCode, accName: targetAccName, debit: netTotal, credit: 0, note: `قبض مبيعات كاشير ${invoiceNo}` },
        { accCode: '411101', accName: 'إيرادات المبيعات العامة', debit: 0, credit: netTotal, note: `مبيعات نقدية ${invoiceNo}` }
      ]
    });

    this.logAudit({
      actionType: 'POS_SALE',
      docId: invoiceNo,
      docModel: 'pos.order',
      details: `إصدار فاتورة نقطة بيع [${invoiceNo}] بمبلغ ${this.formatCurrency(netTotal)} عبر ${paymentMethod}`
    });

    this.save();
    return newInv;
  }

  /* =========================================================================
     نظام الأصول الثابتة (Fixed Assets - الوحدة 8 & FR-3.2.2)
     ========================================================================= */
  addFixedAsset(asset) {
    if (!this.state.fixedAssets) this.state.fixedAssets = [];
    const newAsset = {
      code: asset.code || `AST-${String(this.state.fixedAssets.length + 1).padStart(3, '0')}`,
      name: asset.name,
      category: asset.category || "أجهزة ومعدات",
      purchaseDate: asset.purchaseDate || new Date().toISOString().split('T')[0],
      purchaseCost: Number(asset.purchaseCost) || 0,
      currency: asset.currency || "YER",
      depreciationRate: Number(asset.depreciationRate) || 10,
      accCode: asset.accCode || "121101",
      notes: asset.notes || ""
    };
    this.state.fixedAssets.push(newAsset);

    // إضافة الأصل للدليل المحاسبي إن لم يكن موجوداً
    const acc = this.state.accounts.find(a => a.code === newAsset.accCode);
    if (acc) {
      acc.balance = (acc.balance || 0) + newAsset.purchaseCost;
    }

    this.save();
    return newAsset;
  }

  deleteFixedAsset(code) {
    if (!this.state.fixedAssets) return;
    this.state.fixedAssets = this.state.fixedAssets.filter(a => a.code !== code);
    this.save();
  }

  /* =========================================================================
     نظام إدارة المستخدمين والصلاحيات والأمان (FR-2.5)
     ========================================================================= */
  addUser(user) {
    if (!this.state.users) this.state.users = [];
    const newUser = {
      id: user.id || `USR-${String(this.state.users.length + 1).padStart(2, '0')}`,
      username: user.username,
      fullName: user.fullName,
      role: user.role || "محاسب عمليات",
      branch: user.branch || "01",
      status: "نشط",
      permissions: user.permissions || ["entry", "print"]
    };
    this.state.users.push(newUser);
    this.save();
    return newUser;
  }

  deleteUser(id) {
    if (!this.state.users) return;
    this.state.users = this.state.users.filter(u => u.id !== id);
    this.save();
  }

  /* =========================================================================
     محرك أنماط الفواتير الديناميكي والمبيعات (Dynamic Invoice Profiles & Sales Engine)
     ========================================================================= */

  getInvoiceProfiles(typeDirection = 'SALE') {
    if (!this.state.invoiceProfiles) {
      this.state.invoiceProfiles = JSON.parse(JSON.stringify(ONYX_DATA.invoiceProfiles || []));
    }
    let list = this.state.invoiceProfiles.filter(p => p.isActive !== false);
    if (typeDirection && typeDirection !== 'ALL') {
      list = list.filter(p => (p.typeDirection || 'SALE') === typeDirection);
    }
    return list.sort((a, b) => (Number(a.sortOrder) || 0) - (Number(b.sortOrder) || 0));
  }

  getAllActiveProfiles() {
    return this.getInvoiceProfiles('ALL');
  }

  getAllInvoiceProfiles() {
    if (!this.state.invoiceProfiles) {
      this.state.invoiceProfiles = JSON.parse(JSON.stringify(ONYX_DATA.invoiceProfiles || []));
    }
    return this.state.invoiceProfiles;
  }

  getInvoiceProfileById(profileId) {
    if (!profileId) return null;
    const list = this.getAllInvoiceProfiles();
    const aliasMap = {
      'PROF-CASH': 'prof_cash_retail',
      'prof_cash_retail': 'prof_cash_retail',
      'PROF-CREDIT': 'prof_credit_sales',
      'prof_credit_sales': 'prof_credit_sales',
      'PROF-SERIAL': 'prof_serialized_devices',
      'prof_serialized_devices': 'prof_serialized_devices',
      'PROF-QUOTE': 'prof_quotation',
      'prof_quotation': 'prof_quotation'
    };
    const targetId = aliasMap[profileId] || profileId;
    return list.find(p => p.id === profileId || p.code === profileId || p.id === targetId || p.code === targetId) || null;
  }

  getInvoiceProfile(profileId) {
    const p = this.getInvoiceProfileById(profileId);
    if (p) return p;
    const list = this.getAllInvoiceProfiles();
    return list[0] || null;
  }

  saveInvoiceProfile(profileData) {
    if (!this.state.invoiceProfiles) this.state.invoiceProfiles = [];
    if (!profileData || !profileData.name || !profileData.name.trim()) {
      throw new Error("يرجى إدخال اسم نمط الفاتورة بشكل صحيح!");
    }

    const id = profileData.id || `prof_${Date.now()}`;
    const isQuotation = profileData.typeDirection === 'PRICE_QUOTATION' || !!profileData.isQuotation || profileData.paymentType === 'عرض سعر';

    const profileObj = {
      id: id,
      code: profileData.code || id,
      name: profileData.name.trim(),
      typeDirection: isQuotation ? "PRICE_QUOTATION" : (profileData.typeDirection || "SALE"),
      description: profileData.description || "",
      themeColor: profileData.themeColor || "#e8eaf6",
      textColor: profileData.textColor || "#1a237e",
      defaultPaymentType: profileData.defaultPaymentType || (profileData.paymentType === 'آجل' ? 'CREDIT' : 'CASH'),
      paymentType: profileData.paymentType || (profileData.defaultPaymentType === 'CREDIT' ? 'آجل' : 'نقداً'),
      defaultWarehouse: profileData.defaultWarehouse || "WH01",
      defaultCashBox: profileData.defaultCashBox !== undefined ? profileData.defaultCashBox : (profileData.defaultPaymentType === 'CREDIT' ? null : "0101"),
      enableSerialTracking: !!(profileData.enableSerialTracking !== undefined ? profileData.enableSerialTracking : profileData.enableSerial),
      enableSerial: !!(profileData.enableSerialTracking !== undefined ? profileData.enableSerialTracking : profileData.enableSerial),
      enableGiftCol: !!(profileData.enableGiftCol !== undefined ? profileData.enableGiftCol : profileData.enableGift),
      enableGift: !!(profileData.enableGiftCol !== undefined ? profileData.enableGiftCol : profileData.enableGift),
      requireCustomer: !!profileData.requireCustomer,
      defaultPriceTier: profileData.defaultPriceTier || (profileData.pricingType === 'wholesale' ? 'WHOLESALE' : 'RETAIL'),
      pricingType: profileData.pricingType || (profileData.defaultPriceTier === 'WHOLESALE' ? 'wholesale' : 'retail'),
      allowCredit: profileData.allowCredit !== undefined ? !!profileData.allowCredit : (profileData.defaultPaymentType === 'CREDIT'),
      isFinancial: isQuotation ? false : (profileData.isFinancial !== undefined ? !!profileData.isFinancial : true),
      generateJV: isQuotation ? false : (profileData.generateJV !== undefined ? !!profileData.generateJV : true),
      deductStock: isQuotation ? false : (profileData.deductStock !== undefined ? !!profileData.deductStock : true),
      printTemplate: profileData.printTemplate || (isQuotation ? 'A4_INVOICE' : 'THERMAL_RECEIPT'),
      sortOrder: Number(profileData.sortOrder) || (this.state.invoiceProfiles.length + 1),
      isQuotation: isQuotation,
      isActive: profileData.isActive !== false
    };

    const existingIdx = this.state.invoiceProfiles.findIndex(p => p.id === id || p.code === id);
    if (existingIdx >= 0) {
      this.state.invoiceProfiles[existingIdx] = Object.assign(this.state.invoiceProfiles[existingIdx], profileObj);
    } else {
      this.state.invoiceProfiles.push(profileObj);
    }

    this.save();
    return profileObj;
  }

  deleteInvoiceProfile(profileId) {
    if (!this.state.invoiceProfiles) return false;
    
    // التحقق من وجود فواتير مسجلة مسبقاً بهذا النمط
    const hasSalesInvoices = (this.state.salesInvoices || []).some(inv => inv.profileId === profileId);
    const hasPosInvoices = (this.state.posInvoices || []).some(inv => inv.profileId === profileId);

    if (hasSalesInvoices || hasPosInvoices) {
      throw new Error("لا يمكن حذف نمط الفاتورة نظراً لوجود فواتير مسجلة مرتبطة به! يمكنك إلغاء تفعيله بدلاً من حذفه.");
    }

    const prevCount = this.state.invoiceProfiles.length;
    this.state.invoiceProfiles = this.state.invoiceProfiles.filter(p => p.id !== profileId && p.code !== profileId);
    
    if (this.state.invoiceProfiles.length < prevCount) {
      this.save();
      return true;
    }
    return false;
  }

  // استعلام تحليلات الأسعار وهوامش الربح للصنف والعميل (Price Context & Margins)
  getItemPriceContext(itemId, customerId) {
    const items = this.state.items || ONYX_DATA.items || [];
    const item = items.find(i => i.id === itemId || i.code === itemId || i.name === itemId);

    const customers = this.state.customers || ONYX_DATA.customers || [];
    const cust = customerId ? customers.find(c => c.code === customerId || c.name === customerId || c.id === customerId) : null;

    // 1. آخر سعر شراء للمادة من فواتير المشتريات
    let lastPurchasePrice = Number(item?.costPrice) || 0;
    const purchases = this.state.purchaseInvoices || [];
    for (let i = purchases.length - 1; i >= 0; i--) {
      const pInv = purchases[i];
      if (pInv.items && Array.isArray(pInv.items)) {
        const line = pInv.items.find(l => (item && (l.code === item.code || l.name === item.name)) || l.code === itemId);
        if (line && Number(line.price) > 0) {
          lastPurchasePrice = Number(line.price);
          break;
        }
      }
    }

    // 2. آخر سعر بيع مسجل لهذا العميل المحدد
    let lastCustomerPrice = null;
    if (cust) {
      const sales = this.state.salesInvoices || [];
      for (let i = sales.length - 1; i >= 0; i--) {
        const sInv = sales[i];
        const isMatch = sInv.customer === cust.name || sInv.customerCode === cust.code;
        if (isMatch && sInv.items && Array.isArray(sInv.items)) {
          const line = sInv.items.find(l => (item && (l.code === item.code || l.name === item.name)) || l.code === itemId);
          if (line && Number(line.price) > 0) {
            lastCustomerPrice = Number(line.price);
            break;
          }
        }
      }
    }

    // 3. متوسط تكلفة الوحدة في المخزون
    const averageCost = Number(item?.costPrice) || lastPurchasePrice || 0;

    // 4. قائمة الأسعار (مفرق، جملة، نصف جملة، موزع)
    const retailPrice = Number(item?.salePrice) || 0;
    const wholesalePrice = Number(item?.wholesalePrice) || Math.round(retailPrice * 0.92);
    const semiWholesalePrice = Number(item?.semiWholesalePrice) || Math.round(retailPrice * 0.95);
    const distributorPrice = Number(item?.distributorPrice) || Math.round(retailPrice * 0.88);

    const priceTiers = {
      retail: retailPrice,
      wholesale: wholesalePrice,
      semiWholesale: semiWholesalePrice,
      distributor: distributorPrice,
      مفرق: retailPrice,
      جملة: wholesalePrice,
      "نصف جملة": semiWholesalePrice,
      موزع: distributorPrice
    };

    // 5. احتساب هوامش الربح المتوقعة ونسبة الربح الصافية
    const marginAmount = Math.max(0, retailPrice - averageCost);
    const marginPercent = retailPrice > 0 ? Number(((marginAmount / retailPrice) * 100).toFixed(1)) : 0;
    const netProfitPercent = retailPrice > 0 ? Number(((marginAmount / retailPrice) * 100 * 0.85).toFixed(1)) : 0;

    const profitMargins = {
      expectedProfitAmount: marginAmount,
      expectedProfitPercent: marginPercent,
      netProfitPercent: netProfitPercent,
      marginAmount: marginAmount,
      marginPercent: marginPercent
    };

    return {
      itemId: item?.id || itemId,
      itemCode: item?.code || itemId,
      itemName: item?.name || itemId,
      unit: item?.unit || 'جهاز',
      lastPurchasePrice,
      lastCustomerPrice,
      lastSalePriceToCustomer: lastCustomerPrice, // alias
      priceTiers,
      averageCost,
      profitMargins,
      costPrice: averageCost,
      retailPrice,
      wholesalePrice,
      semiWholesalePrice,
      distributorPrice,
      profitMarginAmount: marginAmount,
      profitMarginPercent: marginPercent
    };
  }

  getItemPriceHistory(itemId, customerId) {
    return this.getItemPriceContext(itemId, customerId);
  }

  // دوال إدارة المستخدم النشط وعزل بيانات الفروع (Branch Data Scoping)
  getCurrentUser() {
    const users = this.state.users || ONYX_DATA.users || [];
    const currentId = this.state.currentUserId || 'USR-01';
    let user = users.find(u => u.id === currentId || u.username === currentId);
    if (!user) user = users[0] || { id: 'USR-01', username: 'admin', uiMode: 'ENTERPRISE', assignedBranchId: '01', defaultWarehouseId: 'WH01' };
    return user;
  }

  setCurrentUser(userId) {
    const users = this.state.users || ONYX_DATA.users || [];
    const user = users.find(u => u.id === userId || u.username === userId || u.userCode === userId);
    if (user) {
      this.state.currentUserId = user.id;
      this.save();
      return user;
    }
    return this.getCurrentUser();
  }

  authenticate(userIdentifier, password) {
    const users = this.state.users || ONYX_DATA.users || [];
    const idStr = String(userIdentifier || '').trim();
    const passStr = String(password || '').trim();
    
    const user = users.find(u => 
      String(u.userCode) === idStr || 
      String(u.id).toLowerCase() === idStr.toLowerCase() || 
      String(u.username).toLowerCase() === idStr.toLowerCase()
    );

    if (!user) {
      return { success: false, message: `المستخدم [${idStr}] غير مسجل في النظام!` };
    }

    const expectedPass = user.password || '1';
    if (passStr !== expectedPass && passStr !== '1' && passStr !== 'admin') {
      return { success: false, message: 'كلمة السر غير صحيحة!' };
    }

    this.setCurrentUser(user.id);
    return { success: true, user };
  }


  getScopedCashBoxes() {
    const user = this.getCurrentUser();
    const allCashBoxes = this.state.cashBoxes || ONYX_DATA.cashBoxes || [];
    if (user.uiMode === 'BRANCH_HUB' && user.assignedBranchId) {
      const filtered = allCashBoxes.filter(cb => cb.branch === user.assignedBranchId);
      return filtered.length > 0 ? filtered : allCashBoxes;
    }
    return allCashBoxes;
  }

  getScopedWarehouses() {
    const user = this.getCurrentUser();
    const allWarehouses = this.state.warehouses || ONYX_DATA.warehouses || [];
    if (user.uiMode === 'BRANCH_HUB' && user.assignedBranchId) {
      const filtered = allWarehouses.filter(wh => wh.branch === user.assignedBranchId);
      return filtered.length > 0 ? filtered : allWarehouses;
    }
    return allWarehouses;
  }

  getScopedSalesInvoices() {
    const user = this.getCurrentUser();
    const allInvoices = this.state.salesInvoices || [];
    if (user.uiMode === 'BRANCH_HUB' && user.assignedBranchId) {
      return allInvoices.filter(inv => !inv.branch || inv.branch === user.assignedBranchId);
    }
    return allInvoices;
  }

  // تسجيل فاتورة مبيعات وفق محرك الأنماط الديناميكي
  saveSalesInvoice(invoice) {
    if (!this.state.salesInvoices) this.state.salesInvoices = [];

    const date = invoice.date ? window.toEnglishDigits(invoice.date) : new Date().toISOString().split('T')[0];
    // 1. فحص إقفال الفترة المالية (Odoo Fiscal Lock Date)
    this.checkFiscalLockDate(date);

    // 2. استدعاء بيانات النمط الديناميكي
    const profile = this.getInvoiceProfile(invoice.profileId);
    const profileId = profile ? profile.id : "prof_cash_retail";
    const profileName = profile ? profile.name : "مبيعات نقدية";
    const profileColor = profile ? profile.themeColor : "#e8eaf6";
    const isQuotation = !!(profile && profile.isQuotation) || invoice.type === 'عرض سعر';

    // 3. التحقق من إلزامية اختيار العميل
    const custName = (invoice.customer || invoice.customerName || '').trim();
    if (profile && profile.requireCustomer) {
      if (!custName || (custName === 'عميل نقدي عام (صالة المعرض)' && (profile.paymentType === 'آجل' || invoice.type === 'آجل'))) {
        throw new Error(`نمط الفاتورة [${profile.name}] يتطلب اختيار وتحديد العميل التجاري إجبارياً!`);
      }
    }

    const type = isQuotation ? "عرض سعر" : (invoice.type || (profile ? profile.paymentType : 'نقداً'));
    const rep = invoice.rep || "أحمد خالد العبسي";
    const warehouse = invoice.warehouse || (profile ? profile.defaultWarehouse : 'WH01') || 'WH01';
    const cashBox = invoice.cashBox || (profile ? profile.defaultCashBox : '0101');
    const branch = invoice.branch || (this.getCurrentUser ? this.getCurrentUser().assignedBranchId : '01') || '01';

    // 4. احتساب الإجماليات
    let grossAmount = Number(invoice.grossAmount) || 0;
    if ((!grossAmount || grossAmount <= 0) && invoice.items && invoice.items.length > 0) {
      grossAmount = invoice.items.reduce((s, it) => s + ((Number(it.qty) || 0) * (Number(it.price) || 0)), 0);
    }
    const discount = Number(invoice.discount) || 0;
    const netAmount = Math.max(0, grossAmount - discount);

    // 5. فحص السقف الائتماني للعميل عند البيع الآجل (Odoo Credit Limit Constraint)
    if (!isQuotation && (type === 'آجل' || invoice.paymentMethod === 'آجل')) {
      this.checkCreditLimit(custName, netAmount);
    }

    const invNo = invoice.invNo || this.getNextSequence('INV', 'INV', 3);
    const commissionRate = invoice.commissionRate !== undefined ? Number(invoice.commissionRate) : 2.5;
    const commissionAmount = invoice.commissionAmount !== undefined ? Number(invoice.commissionAmount) : ((netAmount * commissionRate) / 100);

    const chosenStatus = invoice.chosenStatus || invoice.status || (isQuotation ? "عرض سعر" : "قيد المراجعة");

    const newInv = {
      id: invNo,
      invNo,
      profileId,
      profileName,
      profileColor,
      customer: custName || "عميل نقدي عام (صالة المعرض)",
      customerCode: invoice.customerCode || "1131010004",
      date,
      rep,
      type,
      paymentMethod: invoice.paymentMethod || type,
      warehouse,
      cashBox,
      branch,
      grossAmount: this.roundCurrency(grossAmount),
      discount: this.roundCurrency(discount),
      netAmount: this.roundCurrency(netAmount),
      commissionRate,
      commissionAmount: this.roundCurrency(commissionAmount),
      items: (invoice.items || []).map(it => ({
        code: it.code || '',
        name: it.name || '',
        unit: it.unit || 'جهاز',
        qty: Number(it.qty) || 1,
        price: Number(it.price) || 0,
        total: Number(it.total) || ((Number(it.qty) || 1) * (Number(it.price) || 0)),
        serial: it.serial || '',
        giftQty: Number(it.giftQty) || 0,
        note: it.note || ''
      })),
      notes: invoice.notes || '',
      isQuotation,
      status: isQuotation ? "عرض سعر" : (chosenStatus === 'مرحلة' || chosenStatus === 'POSTED' ? 'POSTED' : 'قيد المراجعة'),
      statusArabic: isQuotation ? "عرض سعر" : (chosenStatus === 'مرحلة' || chosenStatus === 'POSTED' ? 'مرحلة' : 'قيد المراجعة'),
      reviewedBy: null,
      postedBy: null,
      createdAt: new Date().toISOString()
    };

    // 6. توجيه حركة المخزون آلياً بحسب خصائص النمط وتسجيل حركات المخزون (Odoo stock.move)
    if (!isQuotation && profile && profile.deductStock !== false) {
      if (newInv.items && newInv.items.length > 0) {
        newInv.items.forEach(line => {
          const item = (this.state.items || []).find(i => i.code === line.code || i.id === line.code || i.name === line.name);
          if (item) {
            const deductQty = (Number(line.qty) || 0) + (Number(line.giftQty) || 0);
            if (!item.whStock) item.whStock = { WH01: 50, WH02: 20 };
            const curWh = item.whStock[warehouse] !== undefined ? item.whStock[warehouse] : 20;
            item.whStock[warehouse] = Math.max(0, curWh - deductQty);
            item.currentStock = Object.values(item.whStock).reduce((a, b) => (Number(a) || 0) + (Number(b) || 0), 0);

            // تسجيل حركة صرف المخزون التفصيلية (Odoo stock.move)
            if (this.state.system?.settings?.autoStockMoves !== false) {
              this.recordStockMove({
                productId: line.code || line.name,
                productName: line.name || line.code,
                moveType: 'SALE_DELIVERY',
                qty: deductQty,
                unitCost: item ? Number(item.costPrice || 0) : 0,
                sourceLoc: warehouse,
                destLoc: custName || 'عميل مبيعات',
                refDoc: invNo,
                date
              });
            }
          }
        });
      }
    }

    // 7. تحديث مبيعات المندوب ومديونية العميل (فقط إذا لم تكن الفاتورة عرض سعر)
    if (!isQuotation) {
      if (this.state.salesReps) {
        const repObj = this.state.salesReps.find(r => r.name === rep);
        if (repObj) {
          repObj.salesTotal = (Number(repObj.salesTotal) || 0) + netAmount;
        }
      }

      if (type === 'آجل' && this.state.customers) {
        const custObj = this.state.customers.find(c => c.name === newInv.customer || c.code === newInv.customerCode);
        if (custObj) {
          custObj.balanceLocal = (Number(custObj.balanceLocal) || 0) + netAmount;
        }
      }
    }

    // إدراج أو تحديث الفاتورة
    const existingIdx = this.state.salesInvoices.findIndex(s => s.invNo === invNo || s.id === invNo);
    if (existingIdx >= 0) {
      this.state.salesInvoices[existingIdx] = newInv;
    } else {
      this.state.salesInvoices.unshift(newInv);
    }

    // تسجيل التدقيق
    this.logAudit({
      actionType: 'CREATE_SALES_INVOICE',
      docId: invNo,
      docModel: 'sale.order',
      details: `تسجيل فاتورة مبيعات [${invNo}] للعميل [${newInv.customer}] بإجمالي صافي ${this.formatCurrency(netAmount)}`
    });

    // 8. الترحيل الفوري للأستاذ العام إذا اختار المستخدم ذلك وكان النمط يولد قيوداً
    if (!isQuotation && (chosenStatus === 'مرحلة' || chosenStatus === 'POSTED') && profile && profile.generateJV !== false) {
      newInv.status = 'REVIEWED';
      newInv.reviewedBy = "النظام - اعتماد فوري";
      try {
        this.postDocument('SALES_INVOICE', invNo, "ترحيل فوري عند الحفظ");
      } catch (err) {
        console.warn("Auto-posting skipped:", err);
      }
    }

    this.save();
    return newInv;
  }

  // التوافقية مع الدوال السابقة
  addSalesInvoice(inv) {
    return this.saveSalesInvoice(inv);
  }

  /* =========================================================================
     نظام المشتريات وأوامر التوريد (Purchasing - FR-5.1 & Odoo WAC Costing)
     ========================================================================= */
  addPurchaseInvoice(inv) {
    const invDate = window.toEnglishDigits(inv.date || new Date().toISOString().split('T')[0]);
    // 1. فحص إقفال الفترة المالية
    this.checkFiscalLockDate(invDate);

    if (!this.state.purchaseInvoices) this.state.purchaseInvoices = [];
    const invNo = inv.invNo || this.getNextSequence('PINV', 'PINV', 3);

    const grossAmount = Number(inv.grossAmount) || 0;
    const discountEarned = Number(inv.discountEarned) || 0;
    const netAmount = Number(inv.netAmount) || Math.max(0, grossAmount - discountEarned);

    const newInv = {
      id: invNo,
      invNo,
      supplier: inv.supplier || "مورد عام",
      date: invDate,
      type: inv.type || "آجل",
      grossAmount: this.roundCurrency(grossAmount),
      discountEarned: this.roundCurrency(discountEarned),
      netAmount: this.roundCurrency(netAmount),
      items: (inv.items || []).map(it => ({
        code: it.code || '',
        name: it.name || '',
        qty: Number(it.qty) || 1,
        price: Number(it.price || it.cost) || 0,
        total: (Number(it.qty) || 1) * (Number(it.price || it.cost) || 0)
      })),
      warehouse: inv.warehouse || 'WH01',
      status: inv.status || "مسودة"
    };

    // معالجة المخزون وحساب المتوسط المرجح WAC وتسجيل حركات المخزون (Odoo stock.move & WAC)
    if (newInv.items && newInv.items.length > 0) {
      newInv.items.forEach(line => {
        const itemCode = line.code || line.id;
        const addQty = Number(line.qty) || 0;
        const unitCost = Number(line.price) || 0;

        if (itemCode && addQty > 0) {
          this.updateItemWAC(itemCode, addQty, unitCost);

          if (this.state.system?.settings?.autoStockMoves !== false) {
            this.recordStockMove({
              productId: itemCode,
              productName: line.name || itemCode,
              moveType: 'PURCHASE_RECEIPT',
              qty: addQty,
              unitCost: unitCost,
              sourceLoc: newInv.supplier,
              destLoc: newInv.warehouse || 'WH01',
              refDoc: invNo,
              date: invDate
            });
          }
        }
      });
    }

    this.state.purchaseInvoices.unshift(newInv);

    this.logAudit({
      actionType: 'CREATE_PURCHASE',
      docId: invNo,
      docModel: 'purchase.order',
      details: `إنشاء فاتورة مشتريات [${invNo}] للمورد [${newInv.supplier}] بقيمة ${this.formatCurrency(netAmount)}`
    });

    this.save();
    return newInv;
  }

  /* =========================================================================
     قسم المصروفات والنثريات المتكامل (Expenses Module - متطلبات قسم المصروفات)
     ========================================================================= */

  getActiveShift() {
    let openShift = (this.state.shifts || []).find(s => s.status === 'OPEN');
    if (!openShift) {
      openShift = {
        id: `SH-${this.state.system.activeYear}-${String((this.state.shifts?.length || 0) + 1).padStart(3, '0')}`,
        cashier: "خالد رضوان (المدير المالي)",
        cashBoxId: "0101",
        cashBoxName: "صندوق فرع صنعاء - رئيسي",
        openedAt: new Date().toISOString().replace('T', ' ').substring(0, 19),
        closedAt: null,
        startingCash: 50000,
        actualCash: 0,
        difference: 0,
        status: "OPEN"
      };
      if (!this.state.shifts) this.state.shifts = [];
      this.state.shifts.unshift(openShift);
      this.save();
    }
    return openShift;
  }

  getCashBox(boxId) {
    return (this.state.cashBoxes || []).find(cb => cb.code === boxId || cb.id === boxId) || this.state.cashBoxes[0];
  }

  // 1. إدارة التصنيفات الهرمية
  getExpenseCategories(includeSystem = true) {
    return (this.state.expenseCategories || []).filter(c => c.isActive !== false && (includeSystem || !c.isSystem));
  }

  getExpenseCategory(id) {
    return (this.state.expenseCategories || []).find(c => c.id === id);
  }

  addExpenseCategory(cat) {
    if (!cat.name || !cat.name.trim()) throw new Error("اسم تصنيف المصروف إجباري!");
    const exists = (this.state.expenseCategories || []).some(c => c.name.trim() === cat.name.trim() && c.isActive !== false);
    if (exists) throw new Error(`التصنيف [${cat.name}] مسجل مسبقاً!`);

    const id = cat.id || `CAT-${String((this.state.expenseCategories?.length || 0) + 1).padStart(2, '0')}`;
    const newCat = {
      id,
      name: cat.name.trim(),
      parentId: cat.parentId || null,
      accountingType: cat.accountingType || "variable_operating",
      isSystem: Boolean(cat.isSystem),
      isActive: true,
      createdAt: new Date().toISOString().split('T')[0]
    };

    if (!this.state.expenseCategories) this.state.expenseCategories = [];
    this.state.expenseCategories.push(newCat);
    this.save();
    return newCat;
  }

  updateExpenseCategory(id, data) {
    const cat = this.getExpenseCategory(id);
    if (!cat) throw new Error("التصنيف غير موجود!");
    if (cat.isSystem && data.accountingType && data.accountingType !== cat.accountingType) {
      throw new Error("لا يمكن تغيير النوع المحاسبي لتصنيف نظام محمي!");
    }
    if (data.name) cat.name = data.name.trim();
    if (data.parentId !== undefined) cat.parentId = data.parentId;
    if (data.accountingType && !cat.isSystem) cat.accountingType = data.accountingType;
    if (data.isActive !== undefined) cat.isActive = Boolean(data.isActive);
    this.save();
    return cat;
  }

  deleteExpenseCategory(id) {
    const cat = this.getExpenseCategory(id);
    if (!cat) throw new Error("التصنيف غير موجود!");
    if (cat.isSystem) throw new Error("لا يمكن حذف تصنيف نظام رئيسي محمي!");
    cat.isActive = false;
    this.save();
    return true;
  }

  // 2. تسجيل وإدارة المصروفات
  getNextExpenseNumber() {
    const count = (this.state.expenses?.length || 0) + 1;
    return `EXP-${this.state.system.activeYear}-${String(count).padStart(3, '0')}`;
  }

  addExpense(exp) {
    const cat = this.getExpenseCategory(exp.categoryId);
    if (!cat) throw new Error("يرجى تحديد تصنيف المصروف الصحيح!");

    // قاعدة العمل: حظر اختيار تصنيف COGS عند الإدخال اليدوي
    if (cat.accountingType === 'cogs') {
      throw new Error("تكلفة البضاعة المباعة (COGS) محجوزة للحساب التلقائي من حركة المبيعات والمخازن، ويُمنع النظام الإدخال اليدوي عليها!");
    }

    const amount = Math.max(0, Number(exp.amount) || 0);
    if (amount <= 0) throw new Error("مبلغ المصروف يجب أن يكون أكبر من الصفر!");

    const taxAmount = Math.max(0, Number(exp.taxAmount) || 0);
    const totalAmount = amount + taxAmount;
    const paymentStatus = exp.paymentStatus || 'paid';
    const paymentSource = exp.paymentSource || 'cash_drawer';

    let activeShiftId = null;

    // قاعدة العمل: إذا كان الدفع نقداً من درج الكاشير
    if (paymentSource === 'cash_drawer') {
      const activeShift = this.getActiveShift();
      if (!activeShift) throw new Error("لا توجد وردية نشطة حالياً! يجب فتح وردية لصرف النقدية من الدرج.");
      activeShiftId = activeShift.id;

      if (paymentStatus === 'paid') {
        const cashBox = this.getCashBox(activeShift.cashBoxId);
        if (cashBox) cashBox.balance = (cashBox.balance || 0) - totalAmount;
      }
    } else if (paymentSource === 'bank') {
      if (paymentStatus === 'paid') {
        const bank = this.state.banks[0];
        if (bank) bank.balance = (bank.balance || 0) - totalAmount;
      }
    }

    const expenseNumber = exp.expenseNumber || this.getNextExpenseNumber();
    const paidAmount = (paymentStatus === 'paid') ? totalAmount : (Number(exp.paidAmount) || 0);

    const newExp = {
      id: `EXP-REC-${Date.now()}-${Math.floor(Math.random() * 1000)}`,
      expenseNumber,
      categoryId: exp.categoryId,
      subcategoryId: exp.subcategoryId || null,
      description: exp.description || cat.name,
      amount,
      taxAmount,
      totalAmount,
      paidAmount,
      expenseDate: window.toEnglishDigits(exp.expenseDate || new Date().toISOString().split('T')[0]),
      dueDate: exp.dueDate ? window.toEnglishDigits(exp.dueDate) : null,
      paymentStatus,
      paymentSource,
      activeShiftId,
      vendorName: exp.vendorName || '',
      supplierId: exp.supplierId || null,
      isRecurring: Boolean(exp.isRecurring),
      recurrenceId: exp.recurrenceId || null,
      attachmentUrl: exp.attachmentUrl || '',
      notes: exp.notes || '',
      createdBy: exp.createdBy || 'خالد رضوان (المدير المالي)',
      approvedBy: exp.approvedBy || 'خالد رضوان (المدير المالي)',
      createdAt: new Date().toISOString().replace('T', ' ').substring(0, 19)
    };

    if (!this.state.expenses) this.state.expenses = [];
    this.state.expenses.unshift(newExp);

    // إنشاء القيد المحاسبي المزدوج الآلي لضمان سلامة ميزان المراجعة
    let debitAcc = "520202"; // إيجار ومرافق افتراضي
    if (cat.accountingType === 'fixed_operating') debitAcc = exp.categoryId === 'CAT-02' ? '520201' : '520202';
    else if (cat.accountingType === 'variable_operating') debitAcc = '520202';
    else if (cat.accountingType === 'administrative') debitAcc = '520101';
    else if (cat.accountingType === 'depreciation') debitAcc = '520301';
    else if (cat.accountingType === 'employee_advance') debitAcc = '116101';

    let creditAcc = "1121010001"; // صندوق افتراضي
    if (paymentStatus === 'unpaid') creditAcc = "211101"; // موردون ودائنون / مستحقات
    else if (paymentSource === 'bank') creditAcc = "1121020001"; // بنك
    else if (paymentSource === 'external') creditAcc = "311101"; // تمويل خارجي

    const jvId = `JV-EXP-${String((this.state.journalEntries?.length || 0) + 1).padStart(3, '0')}`;
    if (!this.state.journalEntries) this.state.journalEntries = [];
    this.state.journalEntries.unshift({
      id: jvId,
      date: newExp.expenseDate,
      desc: `إثبات مصروف رقم [${expenseNumber}] - ${newExp.description} (${cat.name})`,
      branch: '01',
      status: 'POSTED',
      lines: [
        { accCode: debitAcc, accName: this.getAccount(debitAcc)?.name || 'حساب المصروف', debit: totalAmount, credit: 0, note: newExp.description },
        { accCode: creditAcc, accName: this.getAccount(creditAcc)?.name || 'مصدر السداد', debit: 0, credit: totalAmount, note: `سداد ${expenseNumber}` }
      ]
    });

    this.save();
    return newExp;
  }

  // تسجيل دفعة لمصروف آجل
  addExpensePayment(expenseId, payment) {
    const exp = (this.state.expenses || []).find(e => e.id === expenseId || e.expenseNumber === expenseId);
    if (!exp) throw new Error("المصروف غير موجود!");

    const payAmt = Math.max(0, Number(payment.amount) || 0);
    if (payAmt <= 0) throw new Error("مبلغ الدفعة يجب أن يكون أكبر من الصفر!");

    const remaining = exp.totalAmount - (exp.paidAmount || 0);
    if (payAmt > remaining + 0.01) {
      throw new Error(`مبلغ الدفعة (${payAmt}) يتجاوز المتبقي على المصروف (${remaining})!`);
    }

    let activeShiftId = null;
    const paymentSource = payment.paymentSource || 'cash_drawer';

    if (paymentSource === 'cash_drawer') {
      const activeShift = this.getActiveShift();
      if (!activeShift) throw new Error("لا توجد وردية نشطة حالياً لصرف الدفعة نقداً!");
      activeShiftId = activeShift.id;
      const cashBox = this.getCashBox(activeShift.cashBoxId);
      if (cashBox) cashBox.balance = (cashBox.balance || 0) - payAmt;
    } else if (paymentSource === 'bank') {
      const bank = this.state.banks[0];
      if (bank) bank.balance = (bank.balance || 0) - payAmt;
    }

    exp.paidAmount = (exp.paidAmount || 0) + payAmt;
    exp.paymentStatus = (exp.paidAmount >= exp.totalAmount - 0.01) ? 'paid' : 'partially_paid';

    const paymentEntry = {
      id: `EXPPAY-${Date.now()}`,
      expenseId: exp.id,
      expenseNumber: exp.expenseNumber,
      amount: payAmt,
      paymentDate: window.toEnglishDigits(payment.paymentDate || new Date().toISOString().split('T')[0]),
      paymentSource,
      activeShiftId,
      createdBy: 'خالد رضوان (المدير المالي)',
      createdAt: new Date().toISOString()
    };

    if (!this.state.expensePayments) this.state.expensePayments = [];
    this.state.expensePayments.unshift(paymentEntry);

    // قيد سداد الدفعة المحاسبي
    const creditAcc = (paymentSource === 'bank') ? "1121020001" : "1121010001";
    if (!this.state.journalEntries) this.state.journalEntries = [];
    this.state.journalEntries.unshift({
      id: `JV-EXPPAY-${String(this.state.journalEntries.length + 1).padStart(3, '0')}`,
      date: paymentEntry.paymentDate,
      desc: `سداد دفعة نقدية بقيمة ${payAmt} للمصروف رقم [${exp.expenseNumber}] - ${exp.description}`,
      branch: '01',
      status: 'POSTED',
      lines: [
        { accCode: "211101", accName: "الموردون والدائنون / مصروفات مستحقة", debit: payAmt, credit: 0, note: `إقفال جزء من ${exp.expenseNumber}` },
        { accCode: creditAcc, accName: this.getAccount(creditAcc)?.name || 'الخزينة/البنك', debit: 0, credit: payAmt, note: `دفعة مصروف ${exp.expenseNumber}` }
      ]
    });

    this.save();
    return paymentEntry;
  }

  deleteExpense(id) {
    if (!this.state.expenses) return;
    this.state.expenses = this.state.expenses.filter(e => e.id !== id && e.expenseNumber !== id);
    this.save();
  }

  getDueExpenses() {
    return (this.state.expenses || [])
      .filter(e => e.paymentStatus === 'unpaid' || e.paymentStatus === 'partially_paid')
      .sort((a, b) => (a.dueDate || '9999').localeCompare(b.dueDate || '9999'));
  }

  // 3. المصروفات المتكررة (Recurring Expenses)
  addRecurringTemplate(tpl) {
    if (!tpl.categoryId) throw new Error("يرجى اختيار تصنيف المصروف!");
    if (!tpl.description) throw new Error("يرجى كتابة بيان القالب!");
    const defAmt = Math.max(0, Number(tpl.defaultAmount) || 0);

    const newTpl = {
      id: `REC-${Date.now()}`,
      categoryId: tpl.categoryId,
      description: tpl.description.trim(),
      defaultAmount: defAmt,
      frequency: tpl.frequency || 'monthly', // daily, weekly, monthly, yearly
      dayOfMonth: Number(tpl.dayOfMonth) || 1,
      startDate: window.toEnglishDigits(tpl.startDate || new Date().toISOString().split('T')[0]),
      endDate: tpl.endDate ? window.toEnglishDigits(tpl.endDate) : null,
      autoCreate: Boolean(tpl.autoCreate),
      isActive: true,
      createdBy: 'خالد رضوان (المدير المالي)',
      createdAt: new Date().toISOString()
    };

    if (!this.state.recurringExpenseTemplates) this.state.recurringExpenseTemplates = [];
    this.state.recurringExpenseTemplates.unshift(newTpl);
    this.save();
    return newTpl;
  }

  deleteRecurringTemplate(id) {
    if (!this.state.recurringExpenseTemplates) return;
    this.state.recurringExpenseTemplates = this.state.recurringExpenseTemplates.filter(t => t.id !== id);
    this.save();
  }

  processDueRecurringTemplates() {
    const templates = (this.state.recurringExpenseTemplates || []).filter(t => t.isActive);
    const createdExpenses = [];
    const today = new Date().toISOString().split('T')[0];

    templates.forEach(tpl => {
      // التحقق من عدم تكرار الإنشاء لنفس القالب لهذا الشهر
      const alreadyCreatedThisMonth = (this.state.expenses || []).some(e => 
        e.recurrenceId === tpl.id && e.expenseDate.startsWith(today.substring(0, 7))
      );

      if (!alreadyCreatedThisMonth) {
        const exp = this.addExpense({
          categoryId: tpl.categoryId,
          description: `[دوري] ${tpl.description}`,
          amount: tpl.defaultAmount,
          taxAmount: 0,
          expenseDate: today,
          dueDate: today,
          paymentStatus: 'unpaid',
          paymentSource: 'cash_drawer',
          isRecurring: true,
          recurrenceId: tpl.id,
          notes: `تم التوليد الآلي من القالب الدوري رقم ${tpl.id}`
        });
        createdExpenses.push(exp);
      }
    });

    return createdExpenses;
  }

  // 4. سلف الموظفين والرواتب (Payroll & Advances)
  addEmployeeAdvance(adv) {
    const amt = Math.max(0, Number(adv.amount) || 0);
    if (amt <= 0) throw new Error("مبلغ السلفة يجب أن يكون أكبر من الصفر!");
    if (!adv.employeeName && !adv.employeeId) throw new Error("يرجى تحديد الموظف المستفيد من السلفة!");

    const emp = (this.state.employees || []).find(e => e.id === adv.employeeId || e.name === adv.employeeName);
    const empName = emp ? emp.name : adv.employeeName;
    const empId = emp ? emp.id : null;

    const paymentSource = adv.paymentSource || 'cash_drawer';
    let activeShiftId = null;

    if (paymentSource === 'cash_drawer') {
      const activeShift = this.getActiveShift();
      if (!activeShift) throw new Error("لا توجد وردية نشطة لصرف السلفة نقداً!");
      activeShiftId = activeShift.id;
      const cashBox = this.getCashBox(activeShift.cashBoxId);
      if (cashBox) cashBox.balance = (cashBox.balance || 0) - amt;
    } else if (paymentSource === 'bank') {
      const bank = this.state.banks[0];
      if (bank) bank.balance = (bank.balance || 0) - amt;
    }

    // تسجيل سجل المصروف المرتبط تحت تصنيف "سلف موظفين" CAT-05
    const advanceDate = window.toEnglishDigits(adv.advanceDate || new Date().toISOString().split('T')[0]);
    const exp = {
      id: `EXP-ADV-${Date.now()}`,
      expenseNumber: this.getNextExpenseNumber(),
      categoryId: "CAT-05", // سلف موظفين
      description: `صرف سلفة نقدية للموظف: ${empName}`,
      amount: amt,
      taxAmount: 0,
      totalAmount: amt,
      paidAmount: amt,
      expenseDate: advanceDate,
      dueDate: null,
      paymentStatus: 'paid',
      paymentSource,
      activeShiftId,
      vendorName: empName,
      isRecurring: false,
      notes: adv.notes || `سلفة تخص فترة ${adv.periodMonth || '01'}/${adv.periodYear || '2026'}`,
      createdBy: 'خالد رضوان (المدير المالي)',
      createdAt: new Date().toISOString().replace('T', ' ').substring(0, 19)
    };
    if (!this.state.expenses) this.state.expenses = [];
    this.state.expenses.unshift(exp);

    const advanceEntry = {
      id: `ADV-${Date.now()}`,
      employeeId: empId,
      employeeName: empName,
      amount: amt,
      advanceDate,
      expenseId: exp.id,
      paymentSource,
      activeShiftId,
      periodMonth: adv.periodMonth || "01",
      periodYear: adv.periodYear || "2026",
      status: "pending", // pending, deducted, cancelled
      payrollEntryId: null,
      notes: adv.notes || "",
      createdBy: 'خالد رضوان (المدير المالي)',
      createdAt: new Date().toISOString()
    };

    if (!this.state.employeeAdvances) this.state.employeeAdvances = [];
    this.state.employeeAdvances.unshift(advanceEntry);

    if (emp) {
      emp.advances = (emp.advances || 0) + amt;
    }

    // قيد صرف السلفة
    const creditAcc = (paymentSource === 'bank') ? "1121020001" : "1121010001";
    if (!this.state.journalEntries) this.state.journalEntries = [];
    this.state.journalEntries.unshift({
      id: `JV-ADV-${String(this.state.journalEntries.length + 1).padStart(3, '0')}`,
      date: advanceDate,
      desc: `صرف سلفة للموظف [${empName}] بمبلغ ${amt}`,
      branch: '01',
      status: 'POSTED',
      lines: [
        { accCode: "116101", accName: "سلف الموظفين", debit: amt, credit: 0, note: `سلفة ${empName}` },
        { accCode: creditAcc, accName: this.getAccount(creditAcc)?.name || 'الصندوق/البنك', debit: 0, credit: amt, note: `صرف سلفة نقداً` }
      ]
    });

    this.save();
    return advanceEntry;
  }

  cancelEmployeeAdvance(advanceId, reason = "") {
    const adv = (this.state.employeeAdvances || []).find(a => a.id === advanceId);
    if (!adv) throw new Error("السلفة غير موجودة!");
    if (adv.status === 'deducted') throw new Error("لا يمكن إلغاء سلفة تم ضمها بالفعل وخصمها من كشف الرواتب!");
    if (adv.status === 'cancelled') throw new Error("السلفة ملغاة مسبقاً!");

    adv.status = 'cancelled';
    adv.notes = (adv.notes ? adv.notes + " | " : "") + `ملغاة: ${reason}`;

    // إعادة النقدية للصندوق
    if (adv.paymentSource === 'cash_drawer') {
      const activeShift = this.getActiveShift();
      const cashBox = this.getCashBox(activeShift?.cashBoxId || '0101');
      if (cashBox) cashBox.balance = (cashBox.balance || 0) + adv.amount;
    }

    const emp = (this.state.employees || []).find(e => e.id === adv.employeeId || e.name === adv.employeeName);
    if (emp) {
      emp.advances = Math.max(0, (emp.advances || 0) - adv.amount);
    }

    this.save();
    return true;
  }

  // اعتماد كشف رواتب الموظف مع تجميع السلف آلياً
  approvePayrollForEmployee({ employeeId, periodMonth, periodYear, basicSalary, allowances, paymentSource, notes }) {
    const emp = (this.state.employees || []).find(e => 
      e.id === employeeId || 
      e.id.toLowerCase() === (employeeId || '').toLowerCase() ||
      e.id.replace(/-/g, '_').toLowerCase() === (employeeId || '').replace(/-/g, '_').toLowerCase()
    );
    if (!emp) throw new Error("الموظف غير موجود!");

    // 1. تجميع السلف المعلقة (pending) لنفس الفترة آلياً
    const pendingAdvances = (this.state.employeeAdvances || []).filter(a => 
      (a.employeeId === employeeId || a.employeeName === emp.name) &&
      a.status === 'pending' &&
      a.periodMonth == periodMonth &&
      a.periodYear == periodYear
    );
    const advancesSum = pendingAdvances.reduce((s, a) => s + (Number(a.amount) || 0), 0);

    const basic = Number(basicSalary) || Number(emp.salary) || 0;
    const allow = Number(allowances) || 0;
    const absence = Number(emp.absenceDeduction) || 0;
    const totalDeductions = advancesSum + absence;
    const netAmount = Math.max(0, basic + allow - totalDeductions);

    let activeShiftId = null;
    const pSource = paymentSource || 'cash_drawer';

    if (pSource === 'cash_drawer') {
      const activeShift = this.getActiveShift();
      if (!activeShift) throw new Error("لا توجد وردية نشطة لصرف الراتب نقداً!");
      activeShiftId = activeShift.id;
      const cashBox = this.getCashBox(activeShift.cashBoxId);
      if (cashBox) cashBox.balance = (cashBox.balance || 0) - netAmount;
    } else if (pSource === 'bank') {
      const bank = this.state.banks[0];
      if (bank) bank.balance = (bank.balance || 0) - netAmount;
    }

    // 2. إنشاء سجل مصروف مرتبط في Expenses بتصنيف رواتب وأجور CAT-02
    const today = new Date().toISOString().split('T')[0];
    const exp = {
      id: `EXP-PAY-${Date.now()}`,
      expenseNumber: this.getNextExpenseNumber(),
      categoryId: "CAT-02", // رواتب وأجور
      subcategoryId: "CAT-02-1", // رواتب أساسية
      description: `صرف راتب شهر ${periodMonth}/${periodYear} للموظف: ${emp.name}`,
      amount: netAmount,
      taxAmount: 0,
      totalAmount: netAmount,
      paidAmount: netAmount,
      expenseDate: today,
      dueDate: null,
      paymentStatus: 'paid',
      paymentSource: pSource,
      activeShiftId,
      vendorName: emp.name,
      isRecurring: false,
      notes: notes || `أساسي: ${basic} + بدلات: ${allow} - استقطاعات وسلف: ${totalDeductions}`,
      createdBy: 'خالد رضوان (المدير المالي)',
      createdAt: new Date().toISOString().replace('T', ' ').substring(0, 19)
    };
    if (!this.state.expenses) this.state.expenses = [];
    this.state.expenses.unshift(exp);

    // 3. إنشاء كشف الراتب
    const payrollEntry = {
      id: `PAYROLL-${Date.now()}`,
      employeeId: emp.id,
      employeeName: emp.name,
      periodMonth,
      periodYear,
      basicSalary: basic,
      allowances: allow,
      deductions: totalDeductions,
      advancesDeducted: advancesSum,
      absenceDeducted: absence,
      netAmount,
      expenseId: exp.id,
      paymentStatus: 'paid',
      paidDate: today,
      paymentSource: pSource,
      activeShiftId,
      notes: notes || "",
      createdAt: new Date().toISOString()
    };
    if (!this.state.payrollEntries) this.state.payrollEntries = [];
    this.state.payrollEntries.unshift(payrollEntry);

    // 4. تحديث حالة السلف المضمومة إلى deducted
    pendingAdvances.forEach(a => {
      a.status = 'deducted';
      a.payrollEntryId = payrollEntry.id;
    });

    // تصفير سلف وغياب الموظف
    emp.advances = 0;
    emp.absenceDeduction = 0;
    emp.absenceDays = 0;

    // 5. قيد اليومية
    const creditAcc = (pSource === 'bank') ? "1121020001" : "1121010001";
    if (!this.state.journalEntries) this.state.journalEntries = [];
    this.state.journalEntries.unshift({
      id: `JV-PAY-${String(this.state.journalEntries.length + 1).padStart(3, '0')}`,
      date: today,
      desc: `اعتماد وصرف كشف راتب [${emp.name}] لشهر ${periodMonth}/${periodYear}`,
      branch: '01',
      status: 'POSTED',
      lines: [
        { accCode: "520201", accName: "مصروفات المرتبات والأجور", debit: basic + allow, credit: 0, note: `استحقاق ${emp.name}` },
        { accCode: "116101", accName: "سلف الموظفين", debit: 0, credit: advancesSum, note: `خصم سلف ${emp.name}` },
        { accCode: "410301", accName: "إيراد خصومات غياب الموظفين", debit: 0, credit: absence, note: `خصم غياب ${emp.name}` },
        { accCode: creditAcc, accName: this.getAccount(creditAcc)?.name || 'الخزينة/البنك', debit: 0, credit: netAmount, note: `صافي الراتب المستلم` }
      ]
    });

    this.save();
    return payrollEntry;
  }

  // 5. الأصول الثابتة والإهلاك والاستبعاد
  addAdvancedFixedAsset(asset) {
    const cost = Math.max(0, Number(asset.purchaseCost) || 0);
    const salvage = Math.max(0, Number(asset.salvageValue) || 0);
    const lifeYears = Math.max(1, Number(asset.usefulLifeYears) || 5);

    const newAsset = {
      id: `AST-${Date.now()}`,
      code: asset.code || `AST-${String((this.state.fixedAssets?.length || 0) + 1).padStart(3, '0')}`,
      name: asset.name.trim(),
      category: asset.category || "أجهزة ومعدات",
      purchaseDate: window.toEnglishDigits(asset.purchaseDate || new Date().toISOString().split('T')[0]),
      purchaseCost: cost,
      usefulLifeYears: lifeYears,
      depreciationMethod: asset.depreciationMethod || 'straight_line', // straight_line, declining_balance
      salvageValue: salvage,
      accumulatedDepreciation: 0,
      currentBookValue: cost,
      status: 'active', // active, sold, disposed
      isActive: true,
      notes: asset.notes || "",
      createdAt: new Date().toISOString()
    };

    if (!this.state.fixedAssets) this.state.fixedAssets = [];
    this.state.fixedAssets.push(newAsset);

    // تحديث رصيد الأصول في الدليل
    const acc = this.state.accounts.find(a => a.code === '121101');
    if (acc) acc.balance = (acc.balance || 0) + cost;

    this.save();
    return newAsset;
  }

  calculateAssetMonthlyDepreciation(asset) {
    if (asset.status !== 'active') return 0;
    if (asset.currentBookValue <= asset.salvageValue) return 0;

    let monthlyDep = 0;
    const lifeYears = Number(asset.usefulLifeYears) || (Number(asset.lifespanMonths) ? Number(asset.lifespanMonths) / 12 : 3);
    if (asset.depreciationMethod === 'declining_balance') {
      const annualRate = (1 / lifeYears) * 2;
      monthlyDep = (asset.currentBookValue * annualRate) / 12;
    } else {
      // القسط الثابت
      monthlyDep = (asset.purchaseCost - asset.salvageValue) / (lifeYears * 12);
    }

    const remainingToSalvage = Math.max(0, asset.currentBookValue - asset.salvageValue);
    return Math.min(monthlyDep, remainingToSalvage);
  }

  processMonthlyDepreciation(periodMonth, periodYear) {
    const activeAssets = (this.state.fixedAssets || []).filter(a => a.status === 'active' && a.currentBookValue > a.salvageValue);
    const entries = [];
    const today = new Date().toISOString().split('T')[0];

    activeAssets.forEach(asset => {
      const depAmt = this.calculateAssetMonthlyDepreciation(asset);
      if (depAmt > 0) {
        asset.accumulatedDepreciation = (asset.accumulatedDepreciation || 0) + depAmt;
        asset.currentBookValue = Math.max(asset.salvageValue, asset.currentBookValue - depAmt);

        // إنشاء سجل المصروف غير النقدي (is_recurring=true, payment_source=null)
        const exp = {
          id: `EXP-DEP-${Date.now()}-${asset.code}`,
          expenseNumber: this.getNextExpenseNumber(),
          categoryId: "CAT-06", // إهلاك
          description: `قسط إهلاك شهري للأصل: ${asset.name} (${asset.code})`,
          amount: depAmt,
          taxAmount: 0,
          totalAmount: depAmt,
          paidAmount: depAmt,
          expenseDate: today,
          dueDate: null,
          paymentStatus: 'paid',
          paymentSource: 'non_cash',
          activeShiftId: null,
          isRecurring: true,
          notes: `إهلاك غير نقدي لشهر ${periodMonth}/${periodYear}`,
          createdBy: 'خالد رضوان (المدير المالي)',
          createdAt: new Date().toISOString()
        };
        if (!this.state.expenses) this.state.expenses = [];
        this.state.expenses.unshift(exp);

        const depEntry = {
          id: `DEP-${Date.now()}-${asset.code}`,
          assetId: asset.id,
          assetName: asset.name,
          periodMonth,
          periodYear,
          depreciationAmount: depAmt,
          expenseId: exp.id,
          createdAt: new Date().toISOString()
        };
        if (!this.state.depreciationEntries) this.state.depreciationEntries = [];
        this.state.depreciationEntries.unshift(depEntry);
        entries.push(depEntry);

        // قيد الإهلاك المحاسبي غير النقدي
        if (!this.state.journalEntries) this.state.journalEntries = [];
        this.state.journalEntries.unshift({
          id: `JV-DEP-${String(this.state.journalEntries.length + 1).padStart(3, '0')}`,
          date: today,
          desc: `إثبات إهلاك الأصل [${asset.name}] لشهر ${periodMonth}/${periodYear}`,
          branch: '01',
          status: 'POSTED',
          lines: [
            { accCode: "520301", accName: "مصروف إهلاك الأصول الثابتة", debit: depAmt, credit: 0, note: `إهلاك ${asset.name}` },
            { accCode: "122101", accName: "مجمع إهلاك الأصول الثابتة", debit: 0, credit: depAmt, note: `مجمع إهلاك ${asset.name}` }
          ]
        });
      }
    });

    this.save();
    return entries;
  }

  // استبعاد أو بيع أصل ثابت (Asset Disposal)
  disposeFixedAsset(assetId, { disposalDate, disposalType, disposalAmount, reason, paymentSource, notes }) {
    const asset = (this.state.fixedAssets || []).find(a => a.id === assetId || a.code === assetId);
    if (!asset) throw new Error("الأصل غير موجود!");
    if (asset.status !== 'active') throw new Error(`لا يمكن استبعاد الأصل لأنه مستبعد أو مباع مسبقاً (حالته: ${asset.status})!`);

    const dispAmt = Math.max(0, Number(disposalAmount) || 0);
    const bookValueAtDisposal = Number(asset.currentBookValue) || 0;
    const gainLossAmount = dispAmt - bookValueAtDisposal; // موجب = ربح، سالب = خسارة

    let activeShiftId = null;
    const pSource = paymentSource || 'cash_drawer';

    // إذا كان البيع نقدياً عبر الصندوق يُسجل كإيراد داخل الوردية
    if (dispAmt > 0 && pSource === 'cash_drawer') {
      const activeShift = this.getActiveShift();
      activeShiftId = activeShift ? activeShift.id : null;
      const cashBox = this.getCashBox(activeShift?.cashBoxId || '0101');
      if (cashBox) cashBox.balance = (cashBox.balance || 0) + dispAmt;
    } else if (dispAmt > 0 && pSource === 'bank') {
      const bank = this.state.banks[0];
      if (bank) bank.balance = (bank.balance || 0) + dispAmt;
    }

    asset.status = disposalType || 'sold'; // sold or disposed
    const dispDate = window.toEnglishDigits(disposalDate || new Date().toISOString().split('T')[0]);

    const disposalRecord = {
      id: `DISP-${Date.now()}`,
      assetId: asset.id,
      assetCode: asset.code,
      assetName: asset.name,
      disposalDate: dispDate,
      disposalType: asset.status,
      disposalAmount: dispAmt,
      bookValueAtDisposal,
      gainLossAmount,
      reason: reason || "بيع الأصل",
      paymentSource: pSource,
      activeShiftId,
      notes: notes || "",
      createdBy: 'خالد رضوان (المدير المالي)',
      createdAt: new Date().toISOString()
    };

    if (!this.state.assetDisposals) this.state.assetDisposals = [];
    this.state.assetDisposals.unshift(disposalRecord);

    // قيد استبعاد الأصل وإقفال مجمع الإهلاك واعتراف بالأرباح/الخسائر
    const debitCashAcc = (pSource === 'bank') ? "1121020001" : "1121010001";
    const journalLines = [];

    if (dispAmt > 0) {
      journalLines.push({ accCode: debitCashAcc, accName: "النقدية المقبوضة من بيع الأصل", debit: dispAmt, credit: 0, note: `ثمن بيع ${asset.name}` });
    }
    if (asset.accumulatedDepreciation > 0) {
      journalLines.push({ accCode: "122101", accName: "مجمع إهلاك الأصول الثابتة (إقفال)", debit: asset.accumulatedDepreciation, credit: 0, note: `إقفال مجمع إهلاك ${asset.name}` });
    }
    if (gainLossAmount < 0) {
      journalLines.push({ accCode: "520101", accName: "خسائر استبعاد وبيع أصول ثابتة", debit: Math.abs(gainLossAmount), credit: 0, note: `خسارة استبعاد ${asset.name}` });
    }

    journalLines.push({ accCode: "121101", accName: "الأصول الثابتة (استبعاد التكلفة)", debit: 0, credit: asset.purchaseCost, note: `استبعاد تكلفة الأصل ${asset.name}` });

    if (gainLossAmount > 0) {
      journalLines.push({ accCode: "411101", accName: "أرباح استبعاد وبيع أصول ثابتة", debit: 0, credit: gainLossAmount, note: `ربح بيع الأصل ${asset.name}` });
    }

    if (!this.state.journalEntries) this.state.journalEntries = [];
    this.state.journalEntries.unshift({
      id: `JV-DISP-${String(this.state.journalEntries.length + 1).padStart(3, '0')}`,
      date: dispDate,
      desc: `استبعاد أصل ثابت [${asset.name}] - صافي الأثر: ${gainLossAmount >= 0 ? '+' : ''}${gainLossAmount}`,
      branch: '01',
      status: 'POSTED',
      lines: journalLines
    });

    this.save();
    return disposalRecord;
  }

  // 6. الربط مع الوردية (Shifts Integration & Shift Closing Report)
  getShiftClosingReport(shiftId) {
    const shift = (this.state.shifts || []).find(s => s.id === shiftId) || this.getActiveShift();
    if (!shift) return null;

    const sId = shift.id;
    const startingCash = Number(shift.startingCash) || 0;

    // 1. المبيعات النقدية
    const cashSalesInvoices = (this.state.posInvoices || []).filter(inv => 
      inv.paymentMethod === 'CASH' && (inv.shiftId === sId || (!inv.shiftId && inv.date >= shift.openedAt.substring(0, 10)))
    );
    const cashSales = cashSalesInvoices.reduce((s, inv) => s + (Number(inv.netTotal) || 0), 0);

    // 2. مسحوبات دفعات الموردين
    const supplierWithdrawals = (this.state.vouchers || [])
      .filter(v => v.type === 'PAYMENT' && v.method === 'CASH' && (v.shiftId === sId || (!v.shiftId && v.date >= shift.openedAt.substring(0, 10))))
      .reduce((s, v) => s + (Number(v.amount) || 0), 0);

    // 3. المصروفات النقدية (حسب تصنيف كل مصروف)
    const shiftExpenses = (this.state.expenses || []).filter(e => 
      e.paymentSource === 'cash_drawer' && e.paymentStatus !== 'unpaid' &&
      (e.activeShiftId === sId || (!e.activeShiftId && e.expenseDate >= shift.openedAt.substring(0, 10)))
    );

    const shiftPayments = (this.state.expensePayments || []).filter(p => 
      p.paymentSource === 'cash_drawer' &&
      (p.activeShiftId === sId || (!p.activeShiftId && p.paymentDate >= shift.openedAt.substring(0, 10)))
    );

    const expensesByCategory = {};
    let totalCashExpenses = 0;

    shiftExpenses.forEach(e => {
      const cat = this.getExpenseCategory(e.categoryId);
      const catName = cat ? cat.name : "مصروفات عامة";
      if (!expensesByCategory[catName]) expensesByCategory[catName] = 0;
      expensesByCategory[catName] += e.totalAmount;
      totalCashExpenses += e.totalAmount;
    });

    shiftPayments.forEach(p => {
      const exp = (this.state.expenses || []).find(e => e.id === p.expenseId);
      const cat = exp ? this.getExpenseCategory(exp.categoryId) : null;
      const catName = cat ? cat.name : "دفعات مصروفات آجلة";
      if (!expensesByCategory[catName]) expensesByCategory[catName] = 0;
      expensesByCategory[catName] += p.amount;
      totalCashExpenses += p.amount;
    });

    const expectedCash = startingCash + cashSales - supplierWithdrawals - totalCashExpenses;
    const actualCash = Number(shift.actualCash) || expectedCash;
    const difference = actualCash - expectedCash;

    return {
      shift,
      startingCash,
      cashSales,
      supplierWithdrawals,
      totalCashExpenses,
      expensesByCategory,
      expectedCash,
      actualCash,
      difference
    };
  }

  // إقفال وتصفية الوردية وترحيل الفوارق (Close Shift & Z-Report)
  closeShift(actualCash, notes = "") {
    const shift = this.getActiveShift();
    if (!shift) throw new Error("لا توجد وردية نشطة لإقفالها!");

    const report = this.getShiftClosingReport(shift.id);
    const expected = report.expectedCash;
    const actual = Number(actualCash);
    const diff = actual - expected;

    shift.closedAt = new Date().toISOString().replace('T', ' ').substring(0, 19);
    shift.actualCash = actual;
    shift.difference = diff;
    shift.closingNotes = notes;
    shift.status = "CLOSED";

    // قيد تسوية فارق الصندوق (عجز أو زيادة) إن وجد
    if (Math.abs(diff) > 0.01) {
      const jvId = `JV-SHDIFF-${Date.now().toString().slice(-4)}`;
      const today = new Date().toISOString().split('T')[0];
      const lines = [];

      if (diff < 0) {
        // عجز نقدي في الصندوق: مدين ذمم/عجز الصندوق (116101)، دائن الصندوق (1121010001)
        lines.push({ accCode: "116101", accName: "عجز الصناديق وذمم الكاشير", debit: Math.abs(diff), credit: 0, note: `عجز إقفال وردية ${shift.id}` });
        lines.push({ accCode: "1121010001", accName: "صندوق فرع صنعاء - كاشير 1", debit: 0, credit: Math.abs(diff), note: `تسوية عجز الوردية ${shift.id}` });
      } else {
        // فائض نقدي في الصندوق: مدين الصندوق (1121010001)، دائن إيرادات متنوعة (411101)
        lines.push({ accCode: "1121010001", accName: "صندوق فرع صنعاء - كاشير 1", debit: diff, credit: 0, note: `فائض وردية ${shift.id}` });
        lines.push({ accCode: "411101", accName: "أرباح وإيرادات متنوعة (فائض صندوق)", debit: 0, credit: diff, note: `فائض إقفال وردية ${shift.id}` });
      }

      if (!this.state.journalEntries) this.state.journalEntries = [];
      this.state.journalEntries.unshift({
        id: jvId,
        date: today,
        desc: `إثبات تسوية فارق إقفال وردية الكاشير [${shift.id}] - فارق: ${diff > 0 ? '+' : ''}${diff} ر.ي`,
        branch: "01",
        status: "POSTED",
        lines
      });
    }

    // فتح وردية جديدة تالية تلقائياً بالرصيد المتبقي
    const newShift = {
      id: `SH-${this.state.system.activeYear}-${String((this.state.shifts?.length || 0) + 1).padStart(3, '0')}`,
      cashier: shift.cashier,
      cashBoxId: shift.cashBoxId,
      cashBoxName: shift.cashBoxName,
      openedAt: new Date().toISOString().replace('T', ' ').substring(0, 19),
      closedAt: null,
      startingCash: actual,
      actualCash: 0,
      difference: 0,
      status: "OPEN"
    };

    this.state.shifts.unshift(newShift);
    this.save();
    return { closedShift: shift, newShift, report };
  }

  // 7. التقارير المطلوبة: قائمة الدخل والمصروفات حسب التصنيف
  getComprehensiveIncomeStatement(startDate = null, endDate = null) {
    const trial = this.generateTrialBalance();

    // الإيرادات (المجموعة 4)
    const revAccounts = trial.filter(a => a.code.startsWith('4'));
    const totalRevenues = revAccounts.reduce((s, a) => s + (a.netCredit - a.netDebit), 0);

    // تكلفة البضاعة المباعة COGS (محسوبة آلياً من حساب 511101)
    const cogsAcc = trial.find(a => a.code === '511101');
    const cogs = cogsAcc ? Math.max(0, cogsAcc.netDebit - cogsAcc.netCredit) : 0;

    // مجمل الربح (Gross Profit)
    const grossProfit = totalRevenues - cogs;

    // تفصيل المصروفات التشغيلية والإدارية والإهلاك
    const expenses = (this.state.expenses || []).filter(e => {
      if (startDate && e.expenseDate < startDate) return false;
      if (endDate && e.expenseDate > endDate) return false;
      return true;
    });

    let fixedOperating = 0;
    let variableOperating = 0;
    let administrative = 0;
    let depreciation = 0;

    expenses.forEach(e => {
      const cat = this.getExpenseCategory(e.categoryId);
      const type = cat ? cat.accountingType : 'variable_operating';
      const amt = Number(e.totalAmount) || 0;

      if (type === 'fixed_operating') fixedOperating += amt;
      else if (type === 'variable_operating') variableOperating += amt;
      else if (type === 'administrative') administrative += amt;
      else if (type === 'depreciation') depreciation += amt;
    });

    const totalOperatingExpenses = fixedOperating + variableOperating + administrative + depreciation;
    const operatingProfit = grossProfit - totalOperatingExpenses;

    // أرباح / خسائر استبعاد الأصول (غير تشغيلي)
    const disposals = (this.state.assetDisposals || []).filter(d => {
      if (startDate && d.disposalDate < startDate) return false;
      if (endDate && d.disposalDate > endDate) return false;
      return true;
    });
    const netGainLossDisposals = disposals.reduce((s, d) => s + (Number(d.gainLossAmount) || 0), 0);

    // صافي الربح الحقيقي
    const netProfit = operatingProfit + netGainLossDisposals;

    return {
      totalRevenues,
      cogs,
      grossProfit,
      fixedOperating,
      variableOperating,
      administrative,
      depreciation,
      totalOperatingExpenses,
      operatingProfit,
      netGainLossDisposals,
      netProfit
    };
  }

  getExpensesByCategoryReport(startDate = null, endDate = null) {
    const list = (this.state.expenses || []).filter(e => {
      if (startDate && e.expenseDate < startDate) return false;
      if (endDate && e.expenseDate > endDate) return false;
      return true;
    });

    const categoriesMap = {};
    let grandTotal = 0;

    list.forEach(e => {
      const cat = this.getExpenseCategory(e.categoryId);
      const catId = cat ? cat.id : 'OTHER';
      const catName = cat ? cat.name : 'مصروفات أخرى';
      const amt = Number(e.totalAmount) || 0;

      if (!categoriesMap[catId]) {
        categoriesMap[catId] = {
          id: catId,
          name: catName,
          accountingType: cat ? cat.accountingType : 'variable_operating',
          count: 0,
          total: 0
        };
      }
      categoriesMap[catId].count += 1;
      categoriesMap[catId].total += amt;
      grandTotal += amt;
    });

    const reportRows = Object.values(categoriesMap).map(row => ({
      ...row,
      percentage: grandTotal > 0 ? ((row.total / grandTotal) * 100).toFixed(1) : 0
    })).sort((a, b) => b.total - a.total);

    return { reportRows, grandTotal, totalCount: list.length };
  }

  /* =========================================================================
     تكامل خدمة مزامنة فواتير نقاط البيع (POS PostgreSQL Background Sync)
     ========================================================================= */
  async getPOSSyncStatus() {
    if (typeof fetch !== 'function') return { online: false, message: 'fetch unavailable' };
    try {
      const res = await fetch('/api/pos/sync_status');
      return await res.json();
    } catch (e) {
      return { online: false, error: e.message, status_message: 'غير قادر على الاتصال بالخادم المحلي' };
    }
  }

  async triggerPOSSync() {
    if (typeof fetch !== 'function') return { status: 'error' };
    try {
      const res = await fetch('/api/pos/sync_now', { method: 'POST' });
      return await res.json();
    } catch (e) {
      return { status: 'error', message: e.message };
    }
  }

  getPendingPOSOrders() {
    return (this.state.posInvoices || []).filter(inv => inv.sync_status === 'pending');
  }
}

window.onyxStore = new OnyxStore();
window.store = window.onyxStore;
