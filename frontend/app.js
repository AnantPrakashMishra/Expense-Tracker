/* ============================================
   SPENDWISE FRONTEND — app.js
   Connects to FastAPI backend at /api (proxied)
   ============================================ */

'use strict';

const API = 'https://expense-tracker-nx5j.onrender.com';

// ── STATE ───────────────────────────────────
let token = localStorage.getItem('sw_token') || null;
let currentUser = JSON.parse(localStorage.getItem('sw_user') || 'null');
let categories = [];
let currentPage = 'dashboard';
let txPage = 1;
let txSearchTimer = null;
let budgetMonth = new Date().getMonth() + 1;
let budgetYear = new Date().getFullYear();
let analyticsPeriod = 'this_month';
let charts = {};

// ── API HELPER ───────────────────────────────
async function api(path, opts = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const resp = await fetch(`${API}${path}`, { headers, ...opts });
  if (resp.status === 401) { handleLogout(); return null; }
  if (resp.status === 204) return null;
  const data = await resp.json().catch(() => null);
  if (!resp.ok) throw new Error(data?.detail || 'Request failed');
  return data;
}

// ── INIT ─────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  lucide.createIcons();
  if (token && currentUser) {
    showApp();
  } else {
    document.getElementById('auth-screen').classList.remove('hidden');
  }
});

// ── AUTH ─────────────────────────────────────
function switchAuthTab(tab) {
  const isLogin = tab === 'login';
  document.getElementById('login-form').classList.toggle('hidden', !isLogin);
  document.getElementById('register-form').classList.toggle('hidden', isLogin);
  document.getElementById('tab-login').classList.toggle('active', isLogin);
  document.getElementById('tab-register').classList.toggle('active', !isLogin);
}

async function handleLogin(e) {
  e.preventDefault();
  const errEl = document.getElementById('login-error');
  errEl.classList.add('hidden');
  const btn = document.getElementById('login-btn');
  btn.disabled = true; btn.querySelector('.btn-text').textContent = 'Signing in…';
  try {
    const data = await api('/auth/login', {
      method: 'POST',
      body: JSON.stringify({
        email: document.getElementById('login-email').value,
        password: document.getElementById('login-password').value,
      })
    });
    if (data) { saveAuth(data); showApp(); }
  } catch (err) {
    errEl.textContent = err.message; errEl.classList.remove('hidden');
  } finally {
    btn.disabled = false; btn.querySelector('.btn-text').textContent = 'Sign In';
  }
}

async function handleRegister(e) {
  e.preventDefault();
  const errEl = document.getElementById('reg-error');
  errEl.classList.add('hidden');
  const btn = document.getElementById('reg-btn');
  btn.disabled = true; btn.querySelector('.btn-text').textContent = 'Creating…';
  try {
    const data = await api('/auth/register', {
      method: 'POST',
      body: JSON.stringify({
        full_name: document.getElementById('reg-name').value,
        email: document.getElementById('reg-email').value,
        password: document.getElementById('reg-password').value,
      })
    });
    if (data) { saveAuth(data); showApp(); }
  } catch (err) {
    errEl.textContent = err.message; errEl.classList.remove('hidden');
  } finally {
    btn.disabled = false; btn.querySelector('.btn-text').textContent = 'Create Account';
  }
}

function saveAuth(data) {
  token = data.access_token;
  currentUser = data.user;
  localStorage.setItem('sw_token', token);
  localStorage.setItem('sw_user', JSON.stringify(currentUser));
}

function handleLogout() {
  token = null; currentUser = null;
  localStorage.removeItem('sw_token');
  localStorage.removeItem('sw_user');
  document.getElementById('app').classList.add('hidden');
  document.getElementById('auth-screen').classList.remove('hidden');
  // Reset auth forms
  document.getElementById('login-email').value = '';
  document.getElementById('login-password').value = '';
  switchAuthTab('login');
}

// ── APP INIT ─────────────────────────────────
async function showApp() {
  document.getElementById('auth-screen').classList.add('hidden');
  document.getElementById('app').classList.remove('hidden');
  updateUserUI();
  await loadCategories();
  navigate('dashboard');
  loadNotifications();
  lucide.createIcons();
}

function updateUserUI() {
  if (!currentUser) return;
  const initial = (currentUser.full_name || 'U')[0].toUpperCase();
  document.getElementById('user-avatar-sidebar').textContent = initial;
  document.getElementById('user-name-sidebar').textContent = currentUser.full_name;
  document.getElementById('user-email-sidebar').textContent = currentUser.email;
}

// ── NAVIGATION ───────────────────────────────
function navigate(page) {
  // Hide all views
  document.querySelectorAll('.view').forEach(v => v.classList.add('hidden'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  // Show target
  const view = document.getElementById(`view-${page}`);
  if (view) view.classList.remove('hidden');
  const navItem = document.getElementById(`nav-${page}`);
  if (navItem) navItem.classList.add('active');
  // Update title
  const titles = {
    dashboard: 'Dashboard', transactions: 'Transactions', analytics: 'Analytics',
    budgets: 'Budgets', goals: 'Goals', subscriptions: 'Subscriptions', recurring: 'Recurring'
  };
  document.getElementById('page-title').textContent = titles[page] || page;
  currentPage = page;
  // Close sidebar on mobile
  if (window.innerWidth < 768) toggleSidebar(false);
  // Load data
  switch(page) {
    case 'dashboard': loadDashboard(); break;
    case 'transactions': loadTransactions(); break;
    case 'analytics': loadAnalytics(); break;
    case 'budgets': loadBudgets(); break;
    case 'goals': loadGoals(); break;
    case 'subscriptions': loadSubscriptions(); break;
    case 'recurring': loadRecurring(); break;
  }
  lucide.createIcons();
}

// ── SIDEBAR TOGGLE ────────────────────────────
function toggleSidebar(force) {
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('mob-overlay');
  const open = force !== undefined ? force : !sidebar.classList.contains('open');
  sidebar.classList.toggle('open', open);
  overlay.classList.toggle('hidden', !open);
}

// ── DEMO DATA ─────────────────────────────────
async function loadDemoData() {
  const btn = document.getElementById('demo-btn') || document.querySelector('[onclick="loadDemoData()"]');
  if (btn) { btn.disabled = true; }
  showToast('Loading demo data…', 'info');
  try {
    const res = await api('/demo/load', { method: 'POST' });
    if (res) {
      showToast(`Demo data loaded! ${res.transactions} transactions created.`, 'success');
      navigate(currentPage);
      loadNotifications();
    }
  } catch (err) {
    showToast('Failed to load demo data: ' + err.message, 'error');
  } finally {
    if (btn) btn.disabled = false;
  }
}

// ── CATEGORIES ────────────────────────────────
async function loadCategories() {
  try {
    categories = await api('/categories') || [];
  } catch(e) { categories = []; }
}

function getCategoryName(id) {
  const cat = categories.find(c => c.id === id);
  return cat ? cat.name : '—';
}

function getCategoryColor(id) {
  const cat = categories.find(c => c.id === id);
  return cat ? cat.color : '#a1a1aa';
}

function getCategoryIcon(id) {
  const cat = categories.find(c => c.id === id);
  return cat ? cat.icon : 'tag';
}

function populateCategorySelect(elId, type, allowEmpty = true) {
  const sel = document.getElementById(elId);
  if (!sel) return;
  sel.innerHTML = allowEmpty ? '<option value="">No Category</option>' : '';
  const filtered = type ? categories.filter(c => c.type === type) : categories;
  filtered.forEach(c => {
    const opt = document.createElement('option');
    opt.value = c.id; opt.textContent = c.name;
    sel.appendChild(opt);
  });
}

// ── NOTIFICATIONS ─────────────────────────────
async function loadNotifications() {
  try {
    const notifs = await api('/notifications') || [];
    const unread = notifs.filter(n => !n.is_read).length;
    const badge = document.getElementById('notif-badge');
    if (unread > 0) {
      badge.textContent = unread; badge.classList.remove('hidden');
    } else {
      badge.classList.add('hidden');
    }
    const list = document.getElementById('notif-items');
    if (notifs.length === 0) {
      list.innerHTML = '<div class="empty-sm">No notifications</div>';
      return;
    }
    list.innerHTML = notifs.map(n => `
      <div class="notif-item ${n.is_read ? '' : 'unread'}" onclick="markRead(${n.id})">
        <div class="notif-item-title">${escHtml(n.title)}</div>
        <div class="notif-item-msg">${escHtml(n.message)}</div>
      </div>
    `).join('');
  } catch(e) {}
}

function toggleNotifications() {
  const panel = document.getElementById('notif-panel');
  panel.classList.toggle('hidden');
  // Close on outside click
  if (!panel.classList.contains('hidden')) {
    setTimeout(() => {
      document.addEventListener('click', closeNotifOnClick, { once: true });
    }, 10);
  }
}

function closeNotifOnClick(e) {
  const panel = document.getElementById('notif-panel');
  const btn = document.getElementById('notif-btn');
  if (!panel.contains(e.target) && !btn.contains(e.target)) {
    panel.classList.add('hidden');
  }
}

async function markRead(id) {
  try { await api(`/notifications/${id}/read`, { method: 'PUT' }); loadNotifications(); } catch(e) {}
}
async function markAllRead() {
  try { await api('/notifications/read-all', { method: 'PUT' }); loadNotifications(); document.getElementById('notif-panel').classList.add('hidden'); } catch(e) {}
}

// ── DASHBOARD ─────────────────────────────────
async function loadDashboard() {
  await Promise.all([
    loadDashSummary(),
    loadMonthlyChart(),
    loadHealthScore(),
    loadDashCategories(),
    loadRecentTransactions(),
    loadDashBudgets(),
    loadInsights(),
  ]);
}

async function loadDashSummary() {
  try {
    const data = await api('/analytics/summary?period=this_month');
    if (!data) return;
    document.getElementById('d-income').textContent = fmt(data.total_income);
    document.getElementById('d-expense').textContent = fmt(data.total_expense);
    document.getElementById('d-savings').textContent = fmt(data.net_savings);
    document.getElementById('d-rate').textContent = data.savings_rate.toFixed(1) + '%';
  } catch(e) {}
}

async function loadMonthlyChart() {
  try {
    const data = await api('/analytics/monthly?months=6') || [];
    if (charts['monthly']) { charts['monthly'].destroy(); }
    const ctx = document.getElementById('monthly-chart').getContext('2d');
    charts['monthly'] = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: data.map(d => d.month_name),
        datasets: [
          { label: 'Income', data: data.map(d => d.income), backgroundColor: '#ffffff', borderRadius: 4, borderSkipped: false },
          { label: 'Expenses', data: data.map(d => d.expense), backgroundColor: '#3f3f46', borderRadius: 4, borderSkipped: false },
        ]
      },
      options: chartDefaults()
    });
  } catch(e) {}
}

async function loadHealthScore() {
  try {
    const h = await api('/analytics/health-score');
    if (!h) return;
    document.getElementById('health-num').textContent = h.score;
    document.getElementById('health-lbl').textContent = h.rating;
    // Animate ring
    const ring = document.getElementById('health-ring');
    const circumference = 314;
    const offset = circumference - (h.score / 100) * circumference;
    ring.style.strokeDashoffset = offset;
    ring.style.stroke = '#ffffff';
    // Factors
    const facts = document.getElementById('health-facts');
    const pos = h.positive_factors.map(f => `<div class="fact-row fact-pos"><div class="fact-dot"></div>${escHtml(f)}</div>`).join('');
    const neg = h.attention_factors.map(f => `<div class="fact-row fact-neg"><div class="fact-dot"></div>${escHtml(f)}</div>`).join('');
    facts.innerHTML = pos + neg;
  } catch(e) {}
}

async function loadDashCategories() {
  try {
    const data = await api('/analytics/categories?period=this_month&type=expense') || [];
    const el = document.getElementById('d-cat-list');
    if (data.length === 0) { el.innerHTML = '<div class="empty-sm">No expense data yet</div>'; return; }
    el.innerHTML = data.slice(0,5).map(c => `
      <div class="cat-row">
        <div class="cat-icon">
          <i data-lucide="${iconFor(c.category_icon)}" width="14" height="14"></i>
        </div>
        <div class="cat-info">
          <div class="cat-name">${escHtml(c.category_name)}</div>
          <div class="cat-bar-wrap"><div class="cat-bar" style="width:${c.percentage}%"></div></div>
        </div>
        <div class="cat-amount">${fmt(c.amount)}</div>
      </div>
    `).join('');
    lucide.createIcons();
  } catch(e) {}
}

async function loadRecentTransactions() {
  try {
    const data = await api('/transactions?per_page=5&sort_order=desc');
    if (!data) return;
    const el = document.getElementById('d-recent-list');
    if (data.items.length === 0) { el.innerHTML = '<div class="empty-sm">No transactions yet</div>'; return; }
    el.innerHTML = data.items.map(t => {
      const icon = t.category ? t.category.icon : 'tag';
      const sign = t.type === 'income' ? '+' : '-';
      return `
        <div class="tx-row">
          <div class="tx-cat-dot">
            <i data-lucide="${iconFor(icon)}" width="14" height="14"></i>
          </div>
          <div class="tx-info">
            <div class="tx-desc">${escHtml(t.description)}</div>
            <div class="tx-meta">${formatDate(t.date)} · ${t.category ? t.category.name : 'Uncategorized'}</div>
          </div>
          <div class="tx-amount ${t.type}">${sign}${fmt(t.amount)}</div>
        </div>
      `;
    }).join('');
    lucide.createIcons();
  } catch(e) {}
}

async function loadDashBudgets() {
  try {
    const today = new Date();
    const data = await api(`/budgets?month=${today.getMonth()+1}&year=${today.getFullYear()}`) || [];
    const el = document.getElementById('d-budget-list');
    if (data.length === 0) { el.innerHTML = '<div class="empty-sm">No budgets for this month</div>'; return; }
    el.innerHTML = data.slice(0,5).map(b => {
      const cls = b.percentage >= 100 ? 'over' : b.percentage >= 80 ? 'warn-bar' : 'ok';
      return `
        <div class="bmini-row">
          <div class="bmini-hd"><span class="bmini-name">${escHtml(b.category_name)}</span><span class="bmini-pct">${b.percentage}%</span></div>
          <div class="progress-bar"><div class="progress-fill ${cls}" style="width:${Math.min(b.percentage,100)}%"></div></div>
        </div>
      `;
    }).join('');
  } catch(e) {}
}

async function loadInsights() {
  try {
    const data = await api('/analytics/insights');
    if (!data) return;
    const el = document.getElementById('d-insights');
    el.innerHTML = data.insights.map(i => `
      <div class="insight-card ${i.type}">
        <div class="insight-icon"><i data-lucide="${iconFor(i.icon)}" width="16" height="16"></i></div>
        <div class="insight-body">
          <div class="insight-title">${escHtml(i.title)}</div>
          <div class="insight-msg">${escHtml(i.message)}</div>
        </div>
      </div>
    `).join('');
    lucide.createIcons();
  } catch(e) {}
}

// ── TRANSACTIONS ──────────────────────────────
async function loadTransactions() {
  // Populate category filter
  if (categories.length > 0) {
    const sel = document.getElementById('tx-cat-f');
    if (sel.options.length <= 1) {
      categories.forEach(c => {
        const opt = document.createElement('option');
        opt.value = c.id; opt.textContent = c.name;
        sel.appendChild(opt);
      });
    }
  }
  const params = new URLSearchParams({
    page: txPage, per_page: 20, sort_order: 'desc'
  });
  const search = document.getElementById('tx-search')?.value;
  const type = document.getElementById('tx-type-f')?.value;
  const cat = document.getElementById('tx-cat-f')?.value;
  const method = document.getElementById('tx-pay-f')?.value;
  if (search) params.set('search', search);
  if (type) params.set('type', type);
  if (cat) params.set('category_id', cat);
  if (method) params.set('payment_method', method);

  const tbody = document.getElementById('tx-body');
  tbody.innerHTML = '<tr><td colspan="7" class="load-cell">Loading…</td></tr>';
  try {
    const data = await api(`/transactions?${params}`);
    if (!data) return;
    if (data.items.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" class="load-cell">No transactions found</td></tr>';
      document.getElementById('tx-pages').innerHTML = '';
      return;
    }
    tbody.innerHTML = data.items.map(t => {
      const icon = t.category ? t.category.icon : 'tag';
      const sign = t.type === 'income' ? '+' : '-';
      return `
        <tr>
          <td>${formatDate(t.date)}</td>
          <td>
            <div style="display:flex;align-items:center;gap:10px;">
              <div class="tx-cat-dot" style="width:28px;height:28px;border-radius:6px;">
                <i data-lucide="${iconFor(icon)}" width="13" height="13"></i>
              </div>
              <span style="font-weight:500;">${escHtml(t.description)}</span>
            </div>
          </td>
          <td>${t.category ? `<span style="font-size:12px;color:var(--text2);">${escHtml(t.category.name)}</span>` : '<span style="color:var(--text3)">—</span>'}</td>
          <td><span class="method-badge">${fmtMethod(t.payment_method)}</span></td>
          <td><span class="badge badge-${t.type}">${t.type}</span></td>
          <td class="tr" style="color:${t.type==='income'?'#ffffff':'#a1a1aa'}; font-weight:600;">${sign}${fmt(t.amount)}</td>
          <td class="tc">
            <div style="display:flex;gap:4px;justify-content:center;">
              <button class="btn-icon" onclick="openEditTransaction(${t.id})" title="Edit"><i data-lucide="pencil" width="13" height="13"></i></button>
              <button class="btn-icon" onclick="deleteTransaction(${t.id})" title="Delete"><i data-lucide="trash-2" width="13" height="13"></i></button>
            </div>
          </td>
        </tr>
      `;
    }).join('');
    lucide.createIcons();
    renderPagination(data.page, data.total_pages, 'tx-pages', (p) => { txPage = p; loadTransactions(); });
  } catch(err) {
    tbody.innerHTML = `<tr><td colspan="7" class="load-cell">${err.message}</td></tr>`;
  }
}

function debounceTxSearch() {
  clearTimeout(txSearchTimer);
  txSearchTimer = setTimeout(() => { txPage = 1; loadTransactions(); }, 350);
}

// Transaction modal
function openAddTransaction() {
  document.getElementById('tx-form').reset();
  document.getElementById('tx-edit-id').value = '';
  document.getElementById('tx-modal-ttl').textContent = 'Add Transaction';
  document.getElementById('tx-save-btn').textContent = 'Save Transaction';
  document.getElementById('tx-date').value = today();
  updateTxCats();
  openModal('tx-overlay');
}

async function openEditTransaction(id) {
  try {
    const t = await api(`/transactions/${id}`);
    if (!t) return;
    document.getElementById('tx-edit-id').value = t.id;
    document.getElementById('tx-modal-ttl').textContent = 'Edit Transaction';
    document.getElementById('tx-save-btn').textContent = 'Update Transaction';
    // Set type radio
    document.querySelectorAll('[name="tx-type-r"]').forEach(r => { r.checked = r.value === t.type; });
    updateTxCats();
    document.getElementById('tx-amount').value = t.amount;
    document.getElementById('tx-date').value = t.date;
    document.getElementById('tx-desc').value = t.description;
    document.getElementById('tx-cat').value = t.category_id || '';
    document.getElementById('tx-pay').value = t.payment_method || 'cash';
    document.getElementById('tx-notes').value = t.notes || '';
    openModal('tx-overlay');
  } catch(e) { showToast('Failed to load transaction', 'error'); }
}

function updateTxCats() {
  const type = document.querySelector('[name="tx-type-r"]:checked')?.value || 'expense';
  populateCategorySelect('tx-cat', type);
}

async function submitTransaction(e) {
  e.preventDefault();
  const editId = document.getElementById('tx-edit-id').value;
  const type = document.querySelector('[name="tx-type-r"]:checked').value;
  const body = {
    type, amount: parseFloat(document.getElementById('tx-amount').value),
    date: document.getElementById('tx-date').value,
    description: document.getElementById('tx-desc').value,
    category_id: parseInt(document.getElementById('tx-cat').value) || null,
    payment_method: document.getElementById('tx-pay').value,
    notes: document.getElementById('tx-notes').value || null,
  };
  try {
    if (editId) {
      await api(`/transactions/${editId}`, { method: 'PUT', body: JSON.stringify(body) });
      showToast('Transaction updated!', 'success');
    } else {
      await api('/transactions', { method: 'POST', body: JSON.stringify(body) });
      showToast('Transaction added!', 'success');
    }
    closeModal('tx-overlay');
    if (currentPage === 'transactions') loadTransactions();
    else if (currentPage === 'dashboard') loadDashboard();
    loadNotifications();
  } catch(err) { showToast(err.message, 'error'); }
}

async function deleteTransaction(id) {
  if (!confirm('Delete this transaction?')) return;
  try {
    await api(`/transactions/${id}`, { method: 'DELETE' });
    showToast('Transaction deleted', 'success');
    loadTransactions();
  } catch(err) { showToast(err.message, 'error'); }
}

// ── ANALYTICS ─────────────────────────────────
async function loadAnalytics() {
  await Promise.all([
    loadCashflowChart(),
    loadCategoryDonut(),
    loadDailyChart(),
    loadPaymentChart(),
  ]);
}

function setAnalyticsPeriod(p, btn) {
  analyticsPeriod = p;
  document.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  loadAnalytics();
}

async function loadCashflowChart() {
  try {
    const data = await api('/analytics/cashflow?months=6') || [];
    destroyChart('cashflow-chart');
    const ctx = document.getElementById('cashflow-chart').getContext('2d');
    charts['cashflow-chart'] = new Chart(ctx, {
      type: 'line',
      data: {
        labels: data.map(d => d.period),
        datasets: [
          { label: 'Income', data: data.map(d => d.income), borderColor: '#ffffff', backgroundColor: 'rgba(255,255,255,0.06)', fill: true, tension: 0.3, pointRadius: 4, pointBackgroundColor: '#ffffff' },
          { label: 'Expenses', data: data.map(d => d.expense), borderColor: '#71717a', backgroundColor: 'transparent', borderDash: [4, 4], fill: false, tension: 0.3, pointRadius: 4, pointBackgroundColor: '#71717a' },
        ]
      },
      options: chartDefaults()
    });
  } catch(e) {}
}

async function loadCategoryDonut() {
  try {
    const data = await api(`/analytics/categories?period=${analyticsPeriod}&type=expense`) || [];
    destroyChart('cat-donut');
    const ctx = document.getElementById('cat-donut').getContext('2d');
    const monoColors = ['#ffffff', '#e4e4e7', '#d4d4d8', '#a1a1aa', '#71717a', '#52525b', '#3f3f46', '#27272a'];
    charts['cat-donut'] = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: data.map(d => d.category_name),
        datasets: [{ data: data.map(d => d.amount), backgroundColor: data.map((_, i) => monoColors[i % monoColors.length]), borderWidth: 2, borderColor: '#09090b', hoverOffset: 4 }]
      },
      options: { ...donutDefaults(), plugins: { ...donutDefaults().plugins, legend: { ...donutDefaults().plugins.legend, display: true } } }
    });
  } catch(e) {}
}

async function loadDailyChart() {
  try {
    const data = await api(`/analytics/daily?period=${analyticsPeriod}`) || [];
    destroyChart('daily-chart');
    const ctx = document.getElementById('daily-chart').getContext('2d');
    charts['daily-chart'] = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: data.map(d => d.date.slice(8)),  // day number
        datasets: [{ label: 'Expense', data: data.map(d => d.amount), backgroundColor: '#ffffff', borderRadius: 4, borderSkipped: false }]
      },
      options: chartDefaults()
    });
  } catch(e) {}
}

async function loadPaymentChart() {
  try {
    const data = await api(`/analytics/payment-methods?period=${analyticsPeriod}`) || [];
    destroyChart('pay-chart');
    const ctx = document.getElementById('pay-chart').getContext('2d');
    const monoPalette = ['#ffffff', '#d4d4d8', '#a1a1aa', '#71717a', '#52525b', '#3f3f46', '#27272a'];
    charts['pay-chart'] = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: data.map(d => fmtMethod(d.method)),
        datasets: [{ data: data.map(d => d.amount), backgroundColor: monoPalette, borderWidth: 2, borderColor: '#09090b' }]
      },
      options: donutDefaults()
    });
  } catch(e) {}
}

// ── BUDGETS ───────────────────────────────────
function moveBudgetMonth(dir) {
  budgetMonth += dir;
  if (budgetMonth > 12) { budgetMonth = 1; budgetYear++; }
  if (budgetMonth < 1) { budgetMonth = 12; budgetYear--; }
  loadBudgets();
}

async function loadBudgets() {
  const months = ['January','February','March','April','May','June','July','August','September','October','November','December'];
  document.getElementById('budget-month-lbl').textContent = `${months[budgetMonth-1]} ${budgetYear}`;
  const grid = document.getElementById('budgets-grid');
  grid.innerHTML = '<div class="skel-card"></div><div class="skel-card"></div><div class="skel-card"></div>';
  try {
    const data = await api(`/budgets?month=${budgetMonth}&year=${budgetYear}`) || [];
    if (data.length === 0) {
      grid.innerHTML = `<div style="grid-column:1/-1"><div class="empty-state"><div class="empty-icon"><i data-lucide="wallet" width="24" height="24"></i></div><p>No budgets for this month. Click "Add Budget" to get started.</p></div></div>`;
      lucide.createIcons();
      return;
    }
    grid.innerHTML = data.map(b => {
      const cls = b.percentage >= 100 ? 'pct-over' : b.percentage >= 80 ? 'pct-warn' : 'pct-ok';
      const barCls = b.percentage >= 100 ? 'over' : b.percentage >= 80 ? 'warn-bar' : 'ok';
      return `
        <div class="budget-card">
          <div class="budget-card-hd">
            <div class="budget-cat-info">
              <div class="budget-icon">
                <i data-lucide="${iconFor(b.category_icon)}" width="16" height="16"></i>
              </div>
              <div>
                <div class="budget-cat-name">${escHtml(b.category_name)}</div>
                <div class="budget-cat-period">${months[budgetMonth-1]} ${budgetYear}</div>
              </div>
            </div>
            <div class="budget-actions">
              <button class="btn-icon" onclick="deleteBudget(${b.id})" title="Delete"><i data-lucide="trash-2" width="14" height="14"></i></button>
            </div>
          </div>
          <div class="budget-amounts">
            <span class="budget-spent">${fmt(b.spent)} spent</span>
            <span class="budget-limit">of ${fmt(b.amount)}</span>
          </div>
          <div class="budget-pct ${cls}">${b.percentage}%</div>
          <div class="progress-bar"><div class="progress-fill ${barCls}" style="width:${Math.min(b.percentage,100)}%"></div></div>
          <div style="font-size:11.5px;color:var(--text3);margin-top:8px;">${fmt(b.remaining)} remaining</div>
        </div>
      `;
    }).join('');
    lucide.createIcons();
  } catch(e) {
    grid.innerHTML = `<div style="grid-column:1/-1;color:var(--text2);padding:16px;">${e.message}</div>`;
  }
}

function openAddBudget() {
  document.getElementById('budget-form').reset();
  populateCategorySelect('b-cat', 'expense', false);
  // Set current month
  const y = budgetYear, m = String(budgetMonth).padStart(2,'0');
  document.getElementById('b-month').value = `${y}-${m}`;
  openModal('budget-overlay');
}

async function submitBudget(e) {
  e.preventDefault();
  const [y, m] = document.getElementById('b-month').value.split('-');
  const body = {
    category_id: parseInt(document.getElementById('b-cat').value),
    amount: parseFloat(document.getElementById('b-amount').value),
    month: parseInt(m), year: parseInt(y)
  };
  try {
    await api('/budgets', { method: 'POST', body: JSON.stringify(body) });
    showToast('Budget created!', 'success');
    closeModal('budget-overlay');
    loadBudgets();
  } catch(err) { showToast(err.message, 'error'); }
}

async function deleteBudget(id) {
  if (!confirm('Delete this budget?')) return;
  try {
    await api(`/budgets/${id}`, { method: 'DELETE' });
    showToast('Budget deleted', 'success');
    loadBudgets();
  } catch(err) { showToast(err.message, 'error'); }
}

// ── GOALS ─────────────────────────────────────
async function loadGoals() {
  const grid = document.getElementById('goals-grid');
  grid.innerHTML = '<div class="skel-card"></div><div class="skel-card"></div>';
  try {
    const data = await api('/goals') || [];
    if (data.length === 0) {
      grid.innerHTML = `<div style="grid-column:1/-1"><div class="empty-state"><div class="empty-icon"><i data-lucide="target" width="24" height="24"></i></div><p>No savings goals yet. Create one to start tracking!</p></div></div>`;
      lucide.createIcons();
      return;
    }
    grid.innerHTML = data.map(g => {
      const completeBadge = g.is_completed ? `<div class="goal-complete-badge"><i data-lucide="check-circle" width="12" height="12"></i> Completed!</div>` : '';
      return `
        <div class="goal-card">
          <div class="goal-hd">
            <div class="goal-name">${escHtml(g.name)}</div>
            <div style="display:flex;gap:4px;">
              <button class="btn-icon" onclick="openEditGoal(${g.id})" title="Edit"><i data-lucide="pencil" width="14" height="14"></i></button>
              <button class="btn-icon" onclick="deleteGoal(${g.id})" title="Delete"><i data-lucide="trash-2" width="14" height="14"></i></button>
            </div>
          </div>
          <div class="goal-desc">${escHtml(g.description || '')}</div>
          ${completeBadge}
          <div class="goal-amounts">
            <div class="goal-current">${fmt(g.current_amount)}</div>
            <div class="goal-target">of ${fmt(g.target_amount)}</div>
          </div>
          <div class="goal-progress-bar"><div class="goal-progress-fill" style="width:${g.progress_percentage}%"></div></div>
          <div class="goal-pct-row">
            <span>${g.progress_percentage}% complete</span>
            <span>${fmt(g.remaining_amount)} to go</span>
          </div>
          ${g.target_date ? `<div style="font-size:11.5px;color:var(--text3);margin-bottom:12px;">Target: ${formatDate(g.target_date)}</div>` : ''}
          <div class="goal-footer">
            <button class="btn btn-sm btn-primary" onclick="openContribute(${g.id})" style="flex:1;justify-content:center;" ${g.is_completed ? 'disabled' : ''}>
              <i data-lucide="plus" width="12" height="12"></i> Add Funds
            </button>
          </div>
        </div>
      `;
    }).join('');
    lucide.createIcons();
  } catch(e) {
    grid.innerHTML = `<div style="color:var(--text2);padding:16px;">${e.message}</div>`;
  }
}

function openAddGoal() {
  document.getElementById('goal-form').reset();
  document.getElementById('g-edit-id').value = '';
  document.getElementById('goal-modal-ttl').textContent = 'Add Savings Goal';
  openModal('goal-overlay');
}

async function openEditGoal(id) {
  try {
    const g = await api(`/goals`);
    const goal = (g || []).find(x => x.id === id);
    if (!goal) return;
    document.getElementById('g-edit-id').value = id;
    document.getElementById('goal-modal-ttl').textContent = 'Edit Goal';
    document.getElementById('g-name').value = goal.name;
    document.getElementById('g-target').value = goal.target_amount;
    document.getElementById('g-current').value = goal.current_amount;
    document.getElementById('g-date').value = goal.target_date || '';
    document.getElementById('g-desc').value = goal.description || '';
    openModal('goal-overlay');
  } catch(e) { showToast('Failed to load goal', 'error'); }
}

async function submitGoal(e) {
  e.preventDefault();
  const editId = document.getElementById('g-edit-id').value;
  const body = {
    name: document.getElementById('g-name').value,
    target_amount: parseFloat(document.getElementById('g-target').value),
    current_amount: parseFloat(document.getElementById('g-current').value) || 0,
    target_date: document.getElementById('g-date').value || null,
    description: document.getElementById('g-desc').value || null,
  };
  try {
    if (editId) {
      await api(`/goals/${editId}`, { method: 'PUT', body: JSON.stringify(body) });
      showToast('Goal updated!', 'success');
    } else {
      await api('/goals', { method: 'POST', body: JSON.stringify(body) });
      showToast('Goal created!', 'success');
    }
    closeModal('goal-overlay');
    loadGoals();
  } catch(err) { showToast(err.message, 'error'); }
}

async function deleteGoal(id) {
  if (!confirm('Delete this goal?')) return;
  try {
    await api(`/goals/${id}`, { method: 'DELETE' });
    showToast('Goal deleted', 'success');
    loadGoals();
  } catch(err) { showToast(err.message, 'error'); }
}

function openContribute(goalId) {
  document.getElementById('contrib-form').reset();
  document.getElementById('contrib-gid').value = goalId;
  document.getElementById('contrib-date').value = today();
  openModal('contrib-overlay');
}

async function submitContribution(e) {
  e.preventDefault();
  const goalId = document.getElementById('contrib-gid').value;
  const body = {
    amount: parseFloat(document.getElementById('contrib-amt').value),
    date: document.getElementById('contrib-date').value,
    note: document.getElementById('contrib-note').value || null,
  };
  try {
    await api(`/goals/${goalId}/contributions`, { method: 'POST', body: JSON.stringify(body) });
    showToast('Contribution added!', 'success');
    closeModal('contrib-overlay');
    loadGoals();
  } catch(err) { showToast(err.message, 'error'); }
}

// ── SUBSCRIPTIONS ─────────────────────────────
async function loadSubscriptions() {
  const grid = document.getElementById('subs-grid');
  grid.innerHTML = '<div class="skel-card"></div><div class="skel-card"></div><div class="skel-card"></div>';
  try {
    const data = await api('/subscriptions') || [];
    // Compute totals
    let monthly = 0, yearly = 0;
    data.forEach(s => { monthly += s.monthly_cost; yearly += s.yearly_cost; });
    document.getElementById('sub-mo').textContent = fmt(monthly);
    document.getElementById('sub-yr').textContent = fmt(yearly);
    if (data.length === 0) {
      grid.innerHTML = `<div style="grid-column:1/-1"><div class="empty-state"><div class="empty-icon"><i data-lucide="credit-card" width="24" height="24"></i></div><p>No subscriptions tracked yet.</p></div></div>`;
      lucide.createIcons();
      return;
    }
    grid.innerHTML = data.map(s => {
      const initials = s.name.slice(0,2).toUpperCase();
      return `
        <div class="sub-card">
          <div class="sub-card-hd">
            <div class="sub-name-row">
              <div class="sub-avatar">${initials}</div>
              <div>
                <div class="sub-name">${escHtml(s.name)}</div>
                <div class="sub-cat">${escHtml(s.category_name || 'Uncategorized')}</div>
              </div>
            </div>
            <span class="active-chip">${s.is_active ? 'Active' : 'Inactive'}</span>
          </div>
          <div class="sub-amounts">
            <div><span class="sub-main-amount">${fmt(s.amount)}</span><span class="sub-cycle-lbl">/ ${s.billing_cycle}</span></div>
            <div class="sub-yearly">${fmt(s.yearly_cost)} / year</div>
          </div>
          <div class="sub-next"><i data-lucide="calendar" width="12" height="12"></i> Next billing: ${formatDate(s.next_billing_date)}</div>
          <div class="sub-footer">
            <button class="btn btn-sm btn-outline" onclick="openEditSubscription(${s.id})" style="flex:1;justify-content:center;"><i data-lucide="pencil" width="12" height="12"></i> Edit</button>
            <button class="btn-icon" onclick="deleteSubscription(${s.id})" title="Delete"><i data-lucide="trash-2" width="14" height="14"></i></button>
          </div>
        </div>
      `;
    }).join('');
    lucide.createIcons();
  } catch(e) {
    grid.innerHTML = `<div style="color:var(--text2);padding:16px;">${e.message}</div>`;
  }
}

function openAddSubscription() {
  document.getElementById('sub-form').reset();
  document.getElementById('s-edit-id').value = '';
  populateCategorySelect('s-cat', null, true);
  document.getElementById('s-next').value = today();
  openModal('sub-overlay');
}

async function openEditSubscription(id) {
  try {
    const subs = await api('/subscriptions') || [];
    const s = subs.find(x => x.id === id);
    if (!s) return;
    document.getElementById('s-edit-id').value = id;
    document.getElementById('s-name').value = s.name;
    document.getElementById('s-amount').value = s.amount;
    document.getElementById('s-cycle').value = s.billing_cycle;
    document.getElementById('s-next').value = s.next_billing_date;
    document.getElementById('s-desc').value = s.description || '';
    populateCategorySelect('s-cat', null, true);
    setTimeout(() => { document.getElementById('s-cat').value = s.category_id || ''; }, 50);
    openModal('sub-overlay');
  } catch(e) { showToast('Failed to load subscription', 'error'); }
}

async function submitSubscription(e) {
  e.preventDefault();
  const editId = document.getElementById('s-edit-id').value;
  const body = {
    name: document.getElementById('s-name').value,
    amount: parseFloat(document.getElementById('s-amount').value),
    billing_cycle: document.getElementById('s-cycle').value,
    next_billing_date: document.getElementById('s-next').value,
    category_id: parseInt(document.getElementById('s-cat').value) || null,
    description: document.getElementById('s-desc').value || null,
  };
  try {
    if (editId) {
      await api(`/subscriptions/${editId}`, { method: 'PUT', body: JSON.stringify(body) });
      showToast('Subscription updated!', 'success');
    } else {
      await api('/subscriptions', { method: 'POST', body: JSON.stringify(body) });
      showToast('Subscription added!', 'success');
    }
    closeModal('sub-overlay');
    loadSubscriptions();
  } catch(err) { showToast(err.message, 'error'); }
}

async function deleteSubscription(id) {
  if (!confirm('Delete this subscription?')) return;
  try {
    await api(`/subscriptions/${id}`, { method: 'DELETE' });
    showToast('Subscription deleted', 'success');
    loadSubscriptions();
  } catch(err) { showToast(err.message, 'error'); }
}

// ── RECURRING ─────────────────────────────────
async function loadRecurring() {
  const grid = document.getElementById('recurring-grid');
  grid.innerHTML = '<div class="skel-card"></div><div class="skel-card"></div>';
  try {
    const data = await api('/recurring') || [];
    if (data.length === 0) {
      grid.innerHTML = `<div style="grid-column:1/-1"><div class="empty-state"><div class="empty-icon"><i data-lucide="repeat" width="24" height="24"></i></div><p>No recurring transactions set up yet.</p></div></div>`;
      lucide.createIcons();
      return;
    }
    grid.innerHTML = data.map(r => `
      <div class="rec-card">
        <div class="rec-hd">
          <div class="rec-name-row">
            <div class="rec-dot ${r.type === 'income' ? 'rec-income-dot' : 'rec-expense-dot'}"></div>
            <div class="rec-name">${escHtml(r.name)}</div>
          </div>
          <div style="display:flex;gap:4px;">
            <span class="freq-chip">${r.frequency}</span>
            <button class="btn-icon" onclick="deleteRecurring(${r.id})" title="Delete"><i data-lucide="trash-2" width="14" height="14"></i></button>
          </div>
        </div>
        <div class="rec-body">
          <div class="rec-amount ${r.type}">${r.type==='income'?'+':'-'}${fmt(r.amount)}</div>
          <div class="rec-meta">
            <div>${r.category_name || 'Uncategorized'}</div>
            <div>Next: ${formatDate(r.next_occurrence)}</div>
          </div>
        </div>
      </div>
    `).join('');
    lucide.createIcons();
  } catch(e) {
    grid.innerHTML = `<div style="color:var(--text2);padding:16px;">${e.message}</div>`;
  }
}

function openAddRecurring() {
  document.getElementById('rec-form').reset();
  document.getElementById('r-edit-id').value = '';
  populateCategorySelect('r-cat', null, true);
  document.getElementById('r-start').value = today();
  openModal('rec-overlay');
}

async function submitRecurring(e) {
  e.preventDefault();
  const type = document.querySelector('[name="rec-type-r"]:checked').value;
  const body = {
    name: document.getElementById('r-name').value,
    amount: parseFloat(document.getElementById('r-amount').value),
    type, frequency: document.getElementById('r-freq').value,
    category_id: parseInt(document.getElementById('r-cat').value) || null,
    start_date: document.getElementById('r-start').value,
    payment_method: document.getElementById('r-pay').value,
  };
  try {
    await api('/recurring', { method: 'POST', body: JSON.stringify(body) });
    showToast('Recurring transaction added!', 'success');
    closeModal('rec-overlay');
    loadRecurring();
  } catch(err) { showToast(err.message, 'error'); }
}

async function deleteRecurring(id) {
  if (!confirm('Delete this recurring transaction?')) return;
  try {
    await api(`/recurring/${id}`, { method: 'DELETE' });
    showToast('Deleted', 'success');
    loadRecurring();
  } catch(err) { showToast(err.message, 'error'); }
}

// ── MODALS ────────────────────────────────────
function openModal(id) {
  document.getElementById(id).classList.remove('hidden');
  document.body.style.overflow = 'hidden';
  setTimeout(() => lucide.createIcons(), 50);
}
function closeModal(id) {
  document.getElementById(id).classList.add('hidden');
  document.body.style.overflow = '';
}
// Close modals on Escape
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    document.querySelectorAll('.overlay:not(.hidden)').forEach(o => {
      o.classList.add('hidden');
      document.body.style.overflow = '';
    });
  }
});

// ── PAGINATION ────────────────────────────────
function renderPagination(page, totalPages, containerId, onPage) {
  const el = document.getElementById(containerId);
  if (totalPages <= 1) { el.innerHTML = ''; return; }
  let html = `<button class="page-btn" onclick="(${onPage})(${page-1})" ${page===1?'disabled':''}>‹ Prev</button>`;
  const start = Math.max(1, page-2), end = Math.min(totalPages, page+2);
  if (start > 1) html += `<button class="page-btn" onclick="(${onPage})(1)">1</button>${start>2?'<span style="color:var(--text3)">…</span>':''}`;
  for (let i=start; i<=end; i++) {
    html += `<button class="page-btn ${i===page?'active':''}" onclick="(${onPage})(${i})">${i}</button>`;
  }
  if (end < totalPages) html += `${end<totalPages-1?'<span style="color:var(--text3)">…</span>':''}<button class="page-btn" onclick="(${onPage})(${totalPages})">${totalPages}</button>`;
  html += `<button class="page-btn" onclick="(${onPage})(${page+1})" ${page===totalPages?'disabled':''}>Next ›</button>`;
  el.innerHTML = html;
}

// ── TOASTS ────────────────────────────────────
function showToast(msg, type = 'info') {
  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  el.textContent = msg;
  document.getElementById('toasts').appendChild(el);
  setTimeout(() => { el.classList.add('toast-out'); setTimeout(() => el.remove(), 300); }, 3500);
}

// ── CHART HELPERS ─────────────────────────────
function chartDefaults() {
  return {
    responsive: true, maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: '#09090b',
        borderColor: 'rgba(255,255,255,0.15)',
        borderWidth: 1,
        titleColor: '#ffffff',
        bodyColor: '#a1a1aa',
        padding: 10,
        callbacks: { label: ctx => ` ₹${ctx.parsed.y?.toLocaleString('en-IN') || ctx.parsed.toLocaleString('en-IN')}` }
      }
    },
    scales: {
      x: { grid: { color: 'rgba(255,255,255,0.05)', drawBorder: false }, ticks: { color: '#71717a', font: { family: 'Inter', size: 11 } } },
      y: { grid: { color: 'rgba(255,255,255,0.05)', drawBorder: false }, ticks: { color: '#71717a', font: { family: 'Inter', size: 11 }, callback: v => '₹'+v.toLocaleString('en-IN') } }
    }
  };
}
function donutDefaults() {
  return {
    responsive: true, maintainAspectRatio: false, cutout: '70%',
    plugins: {
      legend: { display: true, position: 'bottom', labels: { color: '#a1a1aa', font: { family: 'Inter', size: 11 }, padding: 12, boxWidth: 10 } },
      tooltip: { backgroundColor: '#09090b', borderColor: 'rgba(255,255,255,0.15)', borderWidth: 1, titleColor: '#ffffff', bodyColor: '#a1a1aa', padding: 10 }
    }
  };
}
function destroyChart(id) {
  if (charts[id]) { charts[id].destroy(); delete charts[id]; }
}

// ── FORMATTING ────────────────────────────────
function fmt(n) {
  return '₹' + (n || 0).toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}
function formatDate(d) {
  if (!d) return '—';
  const dt = new Date(d + 'T00:00:00');
  return dt.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}
function today() {
  return new Date().toISOString().split('T')[0];
}
function fmtMethod(m) {
  const map = { cash:'Cash', upi:'UPI', debit_card:'Debit', credit_card:'Credit', bank_transfer:'Bank', other:'Other' };
  return map[m] || m;
}
function escHtml(s) {
  return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// Map backend icon names to Lucide icon names
const ICON_MAP = {
  'utensils':'utensils', 'car':'car', 'shopping-bag':'shopping-bag',
  'film':'film', 'book-open':'book-open', 'heart':'heart',
  'zap':'zap', 'home':'home', 'map-pin':'map-pin',
  'credit-card':'credit-card', 'shopping-cart':'shopping-cart',
  'user':'user', 'more-horizontal':'more-horizontal',
  'briefcase':'briefcase', 'laptop':'laptop', 'trending-up':'trending-up',
  'gift':'gift', 'plus-circle':'plus-circle', 'tag':'tag',
  'bar-chart-2':'bar-chart-2', 'info':'info',
  'alert-triangle':'alert-triangle', 'alert-circle':'alert-circle',
  'trending-down':'trending-down', 'pie-chart':'pie-chart',
  'calendar':'calendar', 'sparkles':'sparkles', 'check-circle':'check-circle',
  'pencil':'pencil', 'trash-2':'trash-2', 'plus':'plus', 'x':'x',
};
function iconFor(name) {
  return ICON_MAP[name] || 'circle';
}
