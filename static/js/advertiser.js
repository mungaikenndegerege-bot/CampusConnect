/**
 * CampusConnect Advertiser Portal SPA
 * Screens: login/register → dashboard → campaigns → new-campaign → campaign-detail → settings
 */
'use strict';

// ── State ──────────────────────────────────────────────────────────────
const advState = {
  token: localStorage.getItem('cc_adv_token') || null,
  advertiser: JSON.parse(localStorage.getItem('cc_adv_user') || 'null'),
  screen: 'dashboard',
  placements: [],
  chartInstance: null,
};

// ── API ────────────────────────────────────────────────────────────────
async function advApi(method, path, body, isFormData) {
  const headers = {};
  if (advState.token) headers['X-Advertiser-Token'] = advState.token;
  if (!isFormData && body) headers['Content-Type'] = 'application/json';
  const opts = { method, headers };
  if (body) opts.body = isFormData ? body : JSON.stringify(body);
  const res = await fetch(path, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || data.message || `Error ${res.status}`);
  return data;
}

// ── Helpers ────────────────────────────────────────────────────────────
function escH(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function fmtDate(d) { return d ? new Date(d).toLocaleDateString('en-KE',{day:'2-digit',month:'short',year:'numeric'}) : '—'; }
function fmtNum(n) { return Number(n||0).toLocaleString(); }
function badgeHtml(status) {
  const map = { pending:'adv-badge-pending', approved:'adv-badge-approved', active:'adv-badge-active', rejected:'adv-badge-rejected', paused:'adv-badge-paused', completed:'adv-badge-completed' };
  return `<span class="adv-badge ${map[status]||'adv-badge-pending'}">${escH(status)}</span>`;
}
function showAlert(container, msg, type='error') {
  const el = document.createElement('div');
  el.className = `adv-alert adv-alert-${type}`;
  el.textContent = msg;
  container.prepend(el);
  setTimeout(() => el.remove(), 5000);
}

// ── Chart.js loader ────────────────────────────────────────────────────
let _chartJsLoaded = false;
function loadChartJs(cb) {
  if (_chartJsLoaded) { cb(); return; }
  if (window.Chart) { _chartJsLoaded = true; cb(); return; }
  const s = document.createElement('script');
  s.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js';
  s.onload = () => { _chartJsLoaded = true; cb(); };
  s.onerror = () => console.warn('Chart.js failed to load');
  document.head.appendChild(s);
}

// ── Top bar ────────────────────────────────────────────────────────────
function renderUserBar() {
  const bar = document.getElementById('adv-user-bar');
  if (!bar) return;
  if (!advState.advertiser) {
    bar.innerHTML = '<span style="font-size:.85rem;opacity:.8">Not logged in</span>';
    return;
  }
  bar.innerHTML = `
    <span style="font-size:.88rem">${escH(advState.advertiser.business_name)}</span>
    <button class="adv-logout-btn" id="adv-logout-btn">Sign Out</button>
  `;
  document.getElementById('adv-logout-btn').addEventListener('click', advLogout);
}

function advLogout() {
  if (advState.token) {
    fetch('/api/advertiser/logout', { method: 'POST', headers: { 'X-Advertiser-Token': advState.token } }).catch(() => {});
  }
  advState.token = null; advState.advertiser = null;
  localStorage.removeItem('cc_adv_token');
  localStorage.removeItem('cc_adv_user');
  renderUserBar();
  renderSidebar(false);
  showScreen('auth');
}

// ── Sidebar ────────────────────────────────────────────────────────────
function renderSidebar(show) {
  const sb = document.getElementById('adv-sidebar');
  if (!sb) return;
  sb.style.display = show ? '' : 'none';
  if (!show) return;
  sb.querySelectorAll('.adv-nav-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.screen === advState.screen);
    btn.onclick = () => navigate(btn.dataset.screen);
  });
}

// ── Router ─────────────────────────────────────────────────────────────
function navigate(screen, params) {
  advState.screen = screen;
  renderSidebar(!!advState.token);
  const app = document.getElementById('adv-app');
  app.innerHTML = '<div class="adv-loading"><div class="adv-spinner"></div>Loading…</div>';
  const screens = { auth: showAuth, dashboard: showDashboard, campaigns: showCampaigns, 'new-campaign': showNewCampaign, 'campaign-detail': showCampaignDetail, settings: showSettings };
  (screens[screen] || showDashboard)(app, params);
}

// ── AUTH ───────────────────────────────────────────────────────────────
function showAuth(app) {
  app.innerHTML = `
    <div class="adv-auth-wrap">
      <div class="adv-auth-card">
        <h2>Advertiser Portal</h2>
        <p>Reach thousands of Kenyan students across universities, polytechnics and colleges.</p>
        <div class="adv-auth-tabs">
          <button class="adv-tab-btn active" id="tab-login">Login</button>
          <button class="adv-tab-btn" id="tab-register">Register</button>
        </div>
        <div id="auth-form-area"></div>
      </div>
    </div>
  `;
  document.getElementById('tab-login').onclick = () => { setActiveTab('tab-login'); renderLoginForm(); };
  document.getElementById('tab-register').onclick = () => { setActiveTab('tab-register'); renderRegisterForm(); };
  renderLoginForm();
}

function setActiveTab(id) {
  document.querySelectorAll('.adv-tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById(id).classList.add('active');
}

function renderLoginForm() {
  const area = document.getElementById('auth-form-area');
  area.innerHTML = `
    <form class="adv-form" id="login-form">
      <label>Email <input type="email" id="login-email" required placeholder="your@business.com"></label>
      <label>Password <input type="password" id="login-pass" required placeholder="••••••••"></label>
      <button type="submit" class="adv-btn adv-btn-primary adv-btn-block">Sign In</button>
    </form>
  `;
  document.getElementById('login-form').onsubmit = async (e) => {
    e.preventDefault();
    const btn = e.target.querySelector('button');
    btn.disabled = true; btn.textContent = 'Signing in…';
    try {
      const res = await advApi('POST', '/api/advertiser/login', {
        email: document.getElementById('login-email').value.trim(),
        password: document.getElementById('login-pass').value
      });
      advState.token = res.token;
      advState.advertiser = res.advertiser;
      localStorage.setItem('cc_adv_token', res.token);
      localStorage.setItem('cc_adv_user', JSON.stringify(res.advertiser));
      renderUserBar();
      navigate('dashboard');
    } catch(err) { showAlert(area, err.message); btn.disabled = false; btn.textContent = 'Sign In'; }
  };
}

function renderRegisterForm() {
  const area = document.getElementById('auth-form-area');
  area.innerHTML = `
    <form class="adv-form" id="register-form">
      <label>Business Name <input type="text" id="reg-biz" required placeholder="e.g. Acme Kenya Ltd"></label>
      <label>Contact Name <input type="text" id="reg-contact" required placeholder="Your full name"></label>
      <label>Email <input type="email" id="reg-email" required placeholder="contact@business.com"></label>
      <label>Phone <input type="tel" id="reg-phone" placeholder="e.g. 0712 345 678"></label>
      <label>Password <input type="password" id="reg-pass" required placeholder="Min 8 characters"></label>
      <label>Website <input type="url" id="reg-web" placeholder="https://yourbusiness.com (optional)"></label>
      <label>Brief Description <textarea id="reg-desc" rows="2" placeholder="What does your business do?"></textarea></label>
      <button type="submit" class="adv-btn adv-btn-primary adv-btn-block">Create Account</button>
      <p style="font-size:.8rem;color:var(--muted);text-align:center">Your account will be reviewed and approved within 24 hours.</p>
    </form>
  `;
  document.getElementById('register-form').onsubmit = async (e) => {
    e.preventDefault();
    const btn = e.target.querySelector('button[type=submit]');
    btn.disabled = true; btn.textContent = 'Creating account…';
    try {
      await advApi('POST', '/api/advertiser/register', {
        business_name: document.getElementById('reg-biz').value.trim(),
        contact_name: document.getElementById('reg-contact').value.trim(),
        email: document.getElementById('reg-email').value.trim(),
        phone: document.getElementById('reg-phone').value.trim(),
        password: document.getElementById('reg-pass').value,
        website: document.getElementById('reg-web').value.trim(),
        description: document.getElementById('reg-desc').value.trim()
      });
      area.innerHTML = `<div class="adv-alert adv-alert-success">✅ Account created! We'll review and approve your account within 24 hours. You can then log in and create campaigns.</div>`;
    } catch(err) { showAlert(area, err.message); btn.disabled = false; btn.textContent = 'Create Account'; }
  };
}

// ── DASHBOARD ──────────────────────────────────────────────────────────
async function showDashboard(app) {
  if (!advState.advertiser) { navigate('auth'); return; }
  if (advState.advertiser.status === 'pending') {
    app.innerHTML = `
      <div class="adv-page-header"><h2>📊 Dashboard</h2></div>
      <div class="adv-pending-notice">
        <h3>⏳ Account Under Review</h3>
        <p>Your advertiser account is pending approval. Our team will review your application within 24 hours. You'll be able to create campaigns once approved.</p>
      </div>`;
    return;
  }
  try {
    const camps = await advApi('GET', '/api/advertiser/campaigns');
    const campaigns = camps.campaigns || [];
    let totalImpressions = 0, totalClicks = 0, activeCamps = 0;
    campaigns.forEach(c => {
      totalImpressions += c.total_impressions || 0;
      totalClicks += c.total_clicks || 0;
      if (c.status === 'active') activeCamps++;
    });
    const ctr = totalImpressions > 0 ? ((totalClicks / totalImpressions) * 100).toFixed(2) : '0.00';

    app.innerHTML = `
      <div class="adv-page-header">
        <h2>📊 Dashboard</h2>
        <button class="adv-btn adv-btn-gold" id="dash-new-btn">➕ New Campaign</button>
      </div>
      <div class="adv-stats-grid">
        <div class="adv-stat-card"><div class="stat-label">Total Impressions</div><div class="stat-value">${fmtNum(totalImpressions)}</div></div>
        <div class="adv-stat-card gold"><div class="stat-label">Total Clicks</div><div class="stat-value">${fmtNum(totalClicks)}</div></div>
        <div class="adv-stat-card green"><div class="stat-label">CTR</div><div class="stat-value">${ctr}%</div></div>
        <div class="adv-stat-card"><div class="stat-label">Active Campaigns</div><div class="stat-value">${activeCamps}</div></div>
      </div>
      <div class="adv-page-header" style="margin-top:8px"><h2 style="font-size:1.1rem">Recent Campaigns</h2></div>
      ${campaigns.length === 0 ? '<div class="adv-empty"><div class="adv-empty-icon">📋</div><p>No campaigns yet. Create your first campaign to reach students!</p></div>' :
        `<div class="adv-table-wrap"><table class="adv-table">
          <thead><tr><th>Campaign</th><th>Status</th><th>Dates</th><th>Impressions</th><th>Clicks</th><th>CTR</th><th></th></tr></thead>
          <tbody>${campaigns.slice(0,5).map(c => {
            const cCtr = c.total_impressions > 0 ? ((c.total_clicks/c.total_impressions)*100).toFixed(2) : '0.00';
            return `<tr>
              <td><strong>${escH(c.name)}</strong></td>
              <td>${badgeHtml(c.status)}</td>
              <td style="font-size:.82rem;color:var(--muted)">${fmtDate(c.start_date)} – ${fmtDate(c.end_date)}</td>
              <td>${fmtNum(c.total_impressions||0)}</td>
              <td>${fmtNum(c.total_clicks||0)}</td>
              <td>${cCtr}%</td>
              <td><button class="adv-btn adv-btn-secondary adv-btn-sm view-camp-btn" data-id="${c.id}">View</button></td>
            </tr>`;
          }).join('')}</tbody>
        </table></div>`}
    `;
    document.getElementById('dash-new-btn').onclick = () => navigate('new-campaign');
    app.querySelectorAll('.view-camp-btn').forEach(btn => {
      btn.onclick = () => navigate('campaign-detail', { id: btn.dataset.id });
    });
  } catch(err) { app.innerHTML = `<div class="adv-alert adv-alert-error">${escH(err.message)}</div>`; }
}

// ── CAMPAIGNS LIST ─────────────────────────────────────────────────────
async function showCampaigns(app) {
  if (!advState.advertiser) { navigate('auth'); return; }
  try {
    const res = await advApi('GET', '/api/advertiser/campaigns');
    const campaigns = res.campaigns || [];
    app.innerHTML = `
      <div class="adv-page-header">
        <h2>📋 My Campaigns</h2>
        <button class="adv-btn adv-btn-gold" id="camps-new-btn">➕ New Campaign</button>
      </div>
      ${campaigns.length === 0 ? '<div class="adv-empty"><div class="adv-empty-icon">📋</div><p>No campaigns yet.</p></div>' :
        `<div class="adv-table-wrap"><table class="adv-table">
          <thead><tr><th>Campaign</th><th>Status</th><th>Start</th><th>End</th><th>Impressions</th><th>Clicks</th><th>CTR</th><th>Payment</th><th></th></tr></thead>
          <tbody>${campaigns.map(c => {
            const ctr = c.total_impressions > 0 ? ((c.total_clicks/c.total_impressions)*100).toFixed(2) : '0.00';
            return `<tr>
              <td><strong>${escH(c.name)}</strong></td>
              <td>${badgeHtml(c.status)}</td>
              <td>${fmtDate(c.start_date)}</td>
              <td>${fmtDate(c.end_date)}</td>
              <td>${fmtNum(c.total_impressions||0)}</td>
              <td>${fmtNum(c.total_clicks||0)}</td>
              <td>${ctr}%</td>
              <td>${badgeHtml(c.payment_status)}</td>
              <td><button class="adv-btn adv-btn-secondary adv-btn-sm view-btn" data-id="${c.id}">View</button></td>
            </tr>`;
          }).join('')}</tbody>
        </table></div>`}
    `;
    document.getElementById('camps-new-btn').onclick = () => navigate('new-campaign');
    app.querySelectorAll('.view-btn').forEach(btn => btn.onclick = () => navigate('campaign-detail', { id: btn.dataset.id }));
  } catch(err) { app.innerHTML = `<div class="adv-alert adv-alert-error">${escH(err.message)}</div>`; }
}

// ── NEW CAMPAIGN ───────────────────────────────────────────────────────
async function showNewCampaign(app) {
  if (!advState.advertiser) { navigate('auth'); return; }
  if (advState.advertiser.status !== 'approved') {
    app.innerHTML = `<div class="adv-page-header"><h2>➕ New Campaign</h2></div><div class="adv-pending-notice"><h3>Account Not Yet Approved</h3><p>You need an approved advertiser account to create campaigns.</p></div>`;
    return;
  }
  // Load placements
  let placements = advState.placements;
  if (!placements.length) {
    try { const r = await advApi('GET', '/api/advertiser/placements'); placements = r.placements || []; advState.placements = placements; } catch(e) { placements = []; }
  }
  const today = new Date().toISOString().slice(0,10);
  app.innerHTML = `
    <div class="adv-page-header">
      <h2>➕ New Campaign</h2>
      <button class="adv-btn adv-btn-secondary" id="back-btn">← Back</button>
    </div>
    <div style="max-width:600px">
      <form class="adv-form" id="new-camp-form">
        <label>Campaign Name <input type="text" id="nc-name" required placeholder="e.g. Back to School Promo 2026"></label>
        <div class="adv-form-row">
          <label>Start Date <input type="date" id="nc-start" required min="${today}" value="${today}"></label>
          <label>End Date <input type="date" id="nc-end" required min="${today}"></label>
        </div>
        <label>Ad Placement
          <select id="nc-placement" required>
            <option value="">Select placement</option>
            ${placements.map(p => `<option value="${p.id}">${escH(p.name)} — KSh ${fmtNum(p.price_per_day)}/day</option>`).join('')}
          </select>
        </label>
        <label>Ad Title <input type="text" id="nc-title" required placeholder="Catchy headline for your ad"></label>
        <label>Ad Body <textarea id="nc-body" rows="3" placeholder="Describe your offer or message…"></textarea></label>
        <label>Destination URL <input type="url" id="nc-url" placeholder="https://yourbusiness.com"></label>
        <label>Ad Image (optional, JPG/PNG/WebP max 5MB)
          <input type="file" id="nc-image" accept=".jpg,.jpeg,.png,.webp">
        </label>
        <div id="nc-budget-preview" style="padding:12px;background:#f3f0ff;border-radius:8px;font-size:.88rem;color:var(--primary);display:none"></div>
        <button type="submit" class="adv-btn adv-btn-primary adv-btn-block">Submit Campaign</button>
        <p style="font-size:.8rem;color:var(--muted);text-align:center">Campaigns are reviewed by our team before going live.</p>
      </form>
    </div>
  `;
  document.getElementById('back-btn').onclick = () => navigate('campaigns');
  // Budget preview
  function updateBudget() {
    const start = document.getElementById('nc-start').value;
    const end = document.getElementById('nc-end').value;
    const pid = document.getElementById('nc-placement').value;
    const bp = document.getElementById('nc-budget-preview');
    if (start && end && pid) {
      const days = Math.max(1, Math.ceil((new Date(end) - new Date(start)) / 86400000) + 1);
      const pl = placements.find(p => String(p.id) === String(pid));
      if (pl) { const total = days * pl.price_per_day; bp.style.display = ''; bp.textContent = `Estimated cost: KSh ${fmtNum(total)} (${days} days × KSh ${fmtNum(pl.price_per_day)}/day)`; return; }
    }
    bp.style.display = 'none';
  }
  ['nc-start','nc-end','nc-placement'].forEach(id => document.getElementById(id).addEventListener('change', updateBudget));

  document.getElementById('new-camp-form').onsubmit = async (e) => {
    e.preventDefault();
    const btn = e.target.querySelector('button[type=submit]');
    btn.disabled = true; btn.textContent = 'Submitting…';
    try {
      const fd = new FormData();
      fd.append('name', document.getElementById('nc-name').value.trim());
      fd.append('start_date', document.getElementById('nc-start').value);
      fd.append('end_date', document.getElementById('nc-end').value);
      fd.append('placement_id', document.getElementById('nc-placement').value);
      fd.append('title', document.getElementById('nc-title').value.trim());
      fd.append('body', document.getElementById('nc-body').value.trim());
      fd.append('link_url', document.getElementById('nc-url').value.trim());
      const imgFile = document.getElementById('nc-image').files[0];
      if (imgFile) fd.append('image', imgFile);
      await advApi('POST', '/api/advertiser/campaigns', fd, true);
      app.innerHTML = `<div class="adv-page-header"><h2>✅ Campaign Submitted</h2></div><div class="adv-alert adv-alert-success">Your campaign has been submitted for review. We'll notify you once it's approved and live.</div><br><button class="adv-btn adv-btn-primary" id="go-camps">View Campaigns</button>`;
      document.getElementById('go-camps').onclick = () => navigate('campaigns');
    } catch(err) { showAlert(e.target, err.message); btn.disabled = false; btn.textContent = 'Submit Campaign'; }
  };
}

// ── CAMPAIGN DETAIL ────────────────────────────────────────────────────
async function showCampaignDetail(app, params) {
  if (!advState.advertiser) { navigate('auth'); return; }
  const id = params && params.id;
  if (!id) { navigate('campaigns'); return; }
  try {
    const [campRes, statsRes] = await Promise.all([
      advApi('GET', `/api/advertiser/campaigns/${id}`),
      advApi('GET', `/api/advertiser/campaigns/${id}/stats`).catch(() => ({ impressions:0, unique_reach:0, clicks:0, ctr:'0.00', daily:[] }))
    ]);
    const c = campRes.campaign;
    const s = statsRes;
    const daily = s.daily || [];

    app.innerHTML = `
      <div class="adv-page-header">
        <h2>${escH(c.name)}</h2>
        <div style="display:flex;gap:8px">
          <button class="adv-btn adv-btn-secondary adv-btn-sm" id="back-btn">← Campaigns</button>
          <button class="adv-btn adv-btn-gold adv-btn-sm" id="dl-csv-btn">⬇ Download CSV</button>
        </div>
      </div>
      <div style="margin-bottom:16px">${badgeHtml(c.status)} ${badgeHtml(c.payment_status)}</div>
      <div class="adv-stats-grid">
        <div class="adv-stat-card"><div class="stat-label">Impressions</div><div class="stat-value">${fmtNum(s.impressions)}</div></div>
        <div class="adv-stat-card"><div class="stat-label">Unique Reach</div><div class="stat-value">${fmtNum(s.unique_reach)}</div></div>
        <div class="adv-stat-card gold"><div class="stat-label">Clicks</div><div class="stat-value">${fmtNum(s.clicks)}</div></div>
        <div class="adv-stat-card green"><div class="stat-label">CTR</div><div class="stat-value">${s.ctr}%</div></div>
      </div>
      <div class="adv-detail-grid">
        <div class="adv-detail-card"><div class="detail-label">Start Date</div><div class="detail-value">${fmtDate(c.start_date)}</div></div>
        <div class="adv-detail-card"><div class="detail-label">End Date</div><div class="detail-value">${fmtDate(c.end_date)}</div></div>
        <div class="adv-detail-card"><div class="detail-label">Placement</div><div class="detail-value">${escH(c.placement_name||'—')}</div></div>
        <div class="adv-detail-card"><div class="detail-label">Budget</div><div class="detail-value">KSh ${fmtNum(c.total_budget)}</div></div>
      </div>
      <div class="adv-chart-wrap">
        <h3>📈 Daily Performance</h3>
        ${daily.length === 0 ? '<p style="color:var(--muted);font-size:.88rem">No data yet — impressions and clicks will appear here once your campaign is live.</p>' : '<canvas id="perf-chart" class="adv-chart-canvas"></canvas>'}
      </div>
      ${c.status === 'rejected' ? `<div class="adv-alert adv-alert-error">This campaign was rejected. Please contact support for more information.</div>` : ''}
    `;
    document.getElementById('back-btn').onclick = () => navigate('campaigns');
    document.getElementById('dl-csv-btn').onclick = () => { window.location.href = `/api/advertiser/campaigns/${id}/report`; };

    // Render chart if data exists
    if (daily.length > 0) {
      loadChartJs(() => {
        const ctx = document.getElementById('perf-chart');
        if (!ctx || !window.Chart) return;
        if (advState.chartInstance) { advState.chartInstance.destroy(); advState.chartInstance = null; }
        advState.chartInstance = new Chart(ctx, {
          type: 'line',
          data: {
            labels: daily.map(d => d.date),
            datasets: [
              { label: 'Impressions', data: daily.map(d => d.impressions), borderColor: '#6C3CE1', backgroundColor: 'rgba(108,60,225,.08)', tension: .4, fill: true },
              { label: 'Clicks', data: daily.map(d => d.clicks), borderColor: '#F5A623', backgroundColor: 'rgba(245,166,35,.08)', tension: .4, fill: true }
            ]
          },
          options: { responsive: true, plugins: { legend: { position: 'top' } }, scales: { y: { beginAtZero: true } } }
        });
      });
    }
  } catch(err) { app.innerHTML = `<div class="adv-alert adv-alert-error">${escH(err.message)}</div>`; }
}

// ── SETTINGS ───────────────────────────────────────────────────────────
async function showSettings(app) {
  if (!advState.advertiser) { navigate('auth'); return; }
  const a = advState.advertiser;
  app.innerHTML = `
    <div class="adv-page-header"><h2>⚙️ Settings</h2></div>
    <div style="max-width:500px">
      <div class="adv-detail-card" style="margin-bottom:20px">
        <div class="detail-label">Account Status</div>
        <div class="detail-value">${badgeHtml(a.status)}</div>
      </div>
      <form class="adv-form" id="settings-form">
        <label>Business Name <input type="text" id="set-biz" value="${escH(a.business_name)}" required></label>
        <label>Contact Name <input type="text" id="set-contact" value="${escH(a.contact_name)}" required></label>
        <label>Phone <input type="tel" id="set-phone" value="${escH(a.phone||'')}"></label>
        <label>Website <input type="url" id="set-web" value="${escH(a.website||'')}"></label>
        <label>Description <textarea id="set-desc" rows="3">${escH(a.description||'')}</textarea></label>
        <button type="submit" class="adv-btn adv-btn-primary adv-btn-block">Save Changes</button>
      </form>
    </div>
  `;
  document.getElementById('settings-form').onsubmit = async (e) => {
    e.preventDefault();
    const btn = e.target.querySelector('button[type=submit]');
    btn.disabled = true; btn.textContent = 'Saving…';
    try {
      const res = await advApi('PUT', '/api/advertiser/me', {
        business_name: document.getElementById('set-biz').value.trim(),
        contact_name: document.getElementById('set-contact').value.trim(),
        phone: document.getElementById('set-phone').value.trim(),
        website: document.getElementById('set-web').value.trim(),
        description: document.getElementById('set-desc').value.trim()
      });
      advState.advertiser = res.advertiser;
      localStorage.setItem('cc_adv_user', JSON.stringify(res.advertiser));
      showAlert(e.target, 'Settings saved!', 'success');
    } catch(err) { showAlert(e.target, err.message); }
    finally { btn.disabled = false; btn.textContent = 'Save Changes'; }
  };
}

// ── INIT ───────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  renderUserBar();
  if (!advState.token) {
    renderSidebar(false);
    navigate('auth');
    return;
  }
  // Validate token
  try {
    const res = await advApi('GET', '/api/advertiser/me');
    advState.advertiser = res.advertiser;
    localStorage.setItem('cc_adv_user', JSON.stringify(res.advertiser));
    renderUserBar();
    renderSidebar(true);
    navigate('dashboard');
  } catch(_) {
    advState.token = null; advState.advertiser = null;
    localStorage.removeItem('cc_adv_token');
    localStorage.removeItem('cc_adv_user');
    renderSidebar(false);
    navigate('auth');
  }
});
