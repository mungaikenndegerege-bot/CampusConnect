const ADMIN_TOKEN_KEY = 'cc_admin_token';

async function adminApi(method, path, body, isFormData) {
  const opts = { method, headers: { 'X-Admin-Token': localStorage.getItem(ADMIN_TOKEN_KEY) || '' } };
  if (body && !isFormData) { opts.headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(body); }
  else if (body && isFormData) { opts.body = body; }
  const res = await fetch(path, opts);
  if (!res.ok) throw { status: res.status, data: await res.json().catch(() => ({})) };
  return res.json();
}

function escHtml(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

document.addEventListener('DOMContentLoaded', () => {
  const token = localStorage.getItem(ADMIN_TOKEN_KEY);
  if (token) showDashboard();
  document.getElementById('admin-login-btn').addEventListener('click', doLogin);
  document.getElementById('admin-logout-btn').addEventListener('click', doLogout);
  document.querySelectorAll('.admin-tab-btn').forEach(b => b.addEventListener('click', () => loadTab(b.dataset.tab)));
});

async function doLogin() {
  const username = document.getElementById('admin-username').value.trim();
  const password = document.getElementById('admin-password').value;
  document.getElementById('login-error').textContent = '';
  try {
    const res = await fetch('/api/admin/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    if (!res.ok) { document.getElementById('login-error').textContent = 'Invalid credentials.'; return; }
    const data = await res.json();
    localStorage.setItem(ADMIN_TOKEN_KEY, data.token);
    showDashboard();
  } catch(e) { document.getElementById('login-error').textContent = 'Login failed.'; }
}

async function doLogout() {
  await fetch('/api/admin/logout', { method: 'POST', headers: { 'X-Admin-Token': localStorage.getItem(ADMIN_TOKEN_KEY) || '' } }).catch(() => {});
  localStorage.removeItem(ADMIN_TOKEN_KEY);
  document.getElementById('admin-dashboard').style.display = 'none';
  document.getElementById('admin-login-form').style.display = 'block';
}

function showDashboard() {
  document.getElementById('admin-login-form').style.display = 'none';
  document.getElementById('admin-dashboard').style.display = 'block';
  loadTab('ads');
}

function loadTab(tab) {
  document.querySelectorAll('.admin-tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
  const loaders = { ads: loadAdsTab, announcements: loadAnnouncementsTab, posts: loadPostsTab, marketplace: loadMarketplaceTab, lostandfound: loadLFTab, reports: loadReportsTab, institutions: loadInstitutionsAdminTab, advertisers: loadAdvertisersTab, adcampaigns: loadAdCampaignsTab, placements: loadPlacementsTab, revenue: loadRevenueTab, payments: loadPaymentsTab };
  if (loaders[tab]) loaders[tab]();
}

async function loadAdsTab() {
  const c = document.getElementById('admin-tab-content');
  c.innerHTML = '<div>Loading...</div>';
  const ads = await adminApi('GET', '/api/admin/ads').catch(() => []);
  let html = `<div class="admin-form">
    <h3>Create New Ad</h3>
    <div class="form-group"><label>Title *</label><input id="ad-title" type="text"></div>
    <div class="form-group"><label>Body *</label><textarea id="ad-body"></textarea></div>
    <div class="form-group"><label>Link URL</label><input id="ad-link" type="url" placeholder="https://"></div>
    <div class="form-group"><label>Image (optional)</label><input id="ad-image" type="file" accept="image/jpeg,image/png,image/webp"></div>
    <div class="form-group"><label><input type="checkbox" id="ad-active" checked> Active</label></div>
    <button class="btn-primary" onclick="createAd()">Create Ad</button>
  </div><h3 style="margin-bottom:12px">All Ads (${ads.length})</h3>`;
  ads.forEach(ad => {
    html += `<div class="admin-item">
      <div class="admin-item-info">
        <strong>${escHtml(ad.title)}</strong>
        <small>${escHtml(ad.body.substring(0,80))}${ad.body.length > 80 ? '...' : ''}</small>
        <small>Clicks: ${ad.click_count} &bull; ${ad.active ? 'Active' : 'Inactive'}</small>
      </div>
      <div class="admin-item-actions">
        <button class="${ad.active ? 'btn-warning' : 'btn-success'}" onclick="toggleAd(${ad.id}, ${!ad.active})">${ad.active ? 'Deactivate' : 'Activate'}</button>
        <button class="btn-danger" onclick="deleteAd(${ad.id})">Delete</button>
      </div>
    </div>`;
  });
  c.innerHTML = html;
}

async function createAd() {
  const title = document.getElementById('ad-title').value.trim();
  const body = document.getElementById('ad-body').value.trim();
  const link = document.getElementById('ad-link').value.trim();
  const active = document.getElementById('ad-active').checked;
  const imageFile = document.getElementById('ad-image').files[0];
  if (!title || !body) { alert('Title and body required.'); return; }
  const fd = new FormData();
  fd.append('title', title); fd.append('body', body);
  fd.append('link_url', link); fd.append('active', active ? 'true' : 'false');
  if (imageFile) fd.append('image', imageFile);
  await adminApi('POST', '/api/admin/ads', fd, true).catch(e => alert('Error: ' + JSON.stringify(e.data)));
  loadAdsTab();
}

async function toggleAd(id, active) {
  await adminApi('PUT', `/api/admin/ads/${id}`, { active }).catch(e => alert('Error'));
  loadAdsTab();
}

async function deleteAd(id) {
  if (!confirm('Delete this ad?')) return;
  await adminApi('DELETE', `/api/admin/ads/${id}`).catch(e => alert('Error'));
  loadAdsTab();
}

async function loadAnnouncementsTab() {
  const c = document.getElementById('admin-tab-content');
  const items = await adminApi('GET', '/api/announcements').catch(() => []);
  let html = `<div class="admin-form">
    <h3>Post Announcement</h3>
    <div class="form-group"><label>Title *</label><input id="ann-title" type="text"></div>
    <div class="form-group"><label>Body *</label><textarea id="ann-body"></textarea></div>
    <div class="form-group"><label><input type="checkbox" id="ann-pinned"> Pin this announcement</label></div>
    <button class="btn-primary" onclick="createAnnouncement()">Post</button>
  </div><h3 style="margin-bottom:12px">All Announcements (${items.length})</h3>`;
  items.forEach(a => {
    html += `<div class="admin-item">
      <div class="admin-item-info"><strong>${escHtml(a.title)}</strong><small>${escHtml(a.body.substring(0,80))}</small></div>
      <div class="admin-item-actions"><button class="btn-danger" onclick="deleteAnnouncement(${a.id})">Delete</button></div>
    </div>`;
  });
  c.innerHTML = html;
}

async function createAnnouncement() {
  const title = document.getElementById('ann-title').value.trim();
  const body = document.getElementById('ann-body').value.trim();
  const pinned = document.getElementById('ann-pinned').checked;
  if (!title || !body) { alert('Title and body required.'); return; }
  await adminApi('POST', '/api/admin/announcements', { title, body, pinned }).catch(e => alert('Error'));
  loadAnnouncementsTab();
}

async function deleteAnnouncement(id) {
  if (!confirm('Delete announcement?')) return;
  await adminApi('DELETE', `/api/admin/announcements/${id}`).catch(e => alert('Error'));
  loadAnnouncementsTab();
}

async function loadPostsTab() {
  const c = document.getElementById('admin-tab-content');
  const data = await adminApi('GET', '/api/posts?page=1').catch(() => ({ items: [] }));
  let html = `<h3 style="margin-bottom:12px">Community Posts (${data.total || 0})</h3>`;
  (data.items || []).forEach(p => {
    html += `<div class="admin-item">
      <div class="admin-item-info"><strong>${escHtml(p.title)}</strong><small>By ${escHtml(p.poster_name)} &bull; ${p.topic}</small></div>
      <div class="admin-item-actions"><button class="btn-danger" onclick="deletePost(${p.id})">Delete</button></div>
    </div>`;
  });
  c.innerHTML = html || '<p>No posts.</p>';
}

async function deletePost(id) {
  if (!confirm('Delete post?')) return;
  await adminApi('DELETE', `/api/admin/posts/${id}`).catch(e => alert('Error'));
  loadPostsTab();
}

async function loadMarketplaceTab() {
  const c = document.getElementById('admin-tab-content');
  const data = await adminApi('GET', '/api/marketplace?page=1').catch(() => ({ items: [] }));
  let html = `<h3 style="margin-bottom:12px">Marketplace Items</h3>`;
  (data.items || []).forEach(m => {
    html += `<div class="admin-item">
      <div class="admin-item-info"><strong>${escHtml(m.title)}</strong><small>${escHtml(m.poster_name)} &bull; ${escHtml(m.category)}</small></div>
      <div class="admin-item-actions"><button class="btn-danger" onclick="deleteMarketItem(${m.id})">Delete</button></div>
    </div>`;
  });
  c.innerHTML = html;
}

async function deleteMarketItem(id) {
  if (!confirm('Delete listing?')) return;
  await adminApi('DELETE', `/api/admin/marketplace/${id}`).catch(e => alert('Error'));
  loadMarketplaceTab();
}

async function loadLFTab() {
  const c = document.getElementById('admin-tab-content');
  const data = await adminApi('GET', '/api/lostandfound?page=1').catch(() => ({ items: [] }));
  let html = `<h3 style="margin-bottom:12px">Lost &amp; Found</h3>`;
  (data.items || []).forEach(l => {
    html += `<div class="admin-item">
      <div class="admin-item-info"><strong>${escHtml(l.title)}</strong><small>${l.item_type.toUpperCase()} &bull; ${escHtml(l.poster_name)}</small></div>
      <div class="admin-item-actions"><button class="btn-danger" onclick="deleteLFItem(${l.id})">Delete</button></div>
    </div>`;
  });
  c.innerHTML = html;
}

async function deleteLFItem(id) {
  if (!confirm('Delete report?')) return;
  await adminApi('DELETE', `/api/admin/lostandfound/${id}`).catch(e => alert('Error'));
  loadLFTab();
}

async function loadReportsTab() {
  const c = document.getElementById('admin-tab-content');
  c.innerHTML = '<div>Loading...</div>';
  const reports = await adminApi('GET', '/api/admin/reports').catch(() => []);
  if (!reports.length) { c.innerHTML = '<h3 style="margin-bottom:12px">Reports</h3><p style="color:#9ca3af">No unresolved reports.</p>'; return; }
  let html = `<h3 style="margin-bottom:12px">Unresolved Reports (${reports.length})</h3>`;
  reports.forEach(r => {
    const typeLabel = r.content_type === 'post' ? 'Post' : r.content_type === 'marketplace' ? 'Marketplace' : 'Lost &amp; Found';
    const deleteEndpoint = r.content_type === 'post' ? `/api/admin/posts/${r.content_id}` :
                           r.content_type === 'marketplace' ? `/api/admin/marketplace/${r.content_id}` :
                           `/api/admin/lostandfound/${r.content_id}`;
    html += `<div class="admin-item">
      <div class="admin-item-info">
        <strong><span class="badge">${typeLabel}</span> ${escHtml(r.content_preview || '#' + r.content_id)}</strong>
        <small>Reason: ${escHtml(r.reason)}</small>
        <small>Reported: ${new Date(r.created_at).toLocaleString()} &bull; IP: ${escHtml(r.reporter_ip || 'unknown')}</small>
      </div>
      <div class="admin-item-actions">
        <button class="btn-danger" onclick="deleteReportedContent('${deleteEndpoint}', ${r.id})">Delete Content</button>
        <button class="btn-warning" onclick="dismissReport(${r.id})">Dismiss</button>
      </div>
    </div>`;
  });
  c.innerHTML = html;
}

async function deleteReportedContent(endpoint, reportId) {
  if (!confirm('Delete this content and resolve the report?')) return;
  await adminApi('DELETE', endpoint).catch(e => alert('Error deleting content'));
  await adminApi('POST', `/api/admin/reports/${reportId}/resolve`).catch(e => {});
  loadReportsTab();
}

async function dismissReport(reportId) {
  if (!confirm('Dismiss this report without deleting content?')) return;
  await adminApi('POST', `/api/admin/reports/${reportId}/resolve`).catch(e => alert('Error'));
  loadReportsTab();
}

// ---- Institutions Admin Tab ----

async function loadInstitutionsAdminTab() {
  const c = document.getElementById('admin-tab-content');
  c.innerHTML = '<div>Loading institutions…</div>';

  let categories = [];
  try {
    const catData = await fetch('/api/institutions/categories').then(r => r.json());
    categories = catData.categories || [];
  } catch(e) {}

  const catOptions = categories.map(cat => `<option value="${escHtml(cat.name)}">${escHtml(cat.name)}</option>`).join('');

  let html = `
    <div class="admin-form">
      <h3>Add Institution</h3>
      <div class="form-group"><label>Name *</label><input id="inst-adm-name" type="text" placeholder="Full institution name"></div>
      <div class="form-group"><label>Abbreviation</label><input id="inst-adm-abbr" type="text" placeholder="e.g. UoN"></div>
      <div class="form-group"><label>Category</label>
        <select id="inst-adm-cat"><option value="">-- Select Category --</option>${catOptions}</select>
      </div>
      <div class="form-group"><label>Ownership</label>
        <select id="inst-adm-own"><option value="Public">Public</option><option value="Private">Private</option></select>
      </div>
      <div class="form-group"><label>County</label><input id="inst-adm-county" type="text"></div>
      <div class="form-group"><label>Town</label><input id="inst-adm-town" type="text"></div>
      <div class="form-group"><label>Website</label><input id="inst-adm-website" type="url" placeholder="https://"></div>
      <button class="btn-primary" onclick="adminCreateInstitution()">Add Institution</button>
    </div>
    <div class="admin-form" style="margin-top:16px">
      <h3>Import CSV</h3>
      <p style="font-size:0.82rem;color:#666;margin-bottom:8px">CSV columns: name, abbreviation, category, ownership, county, town, website, source</p>
      <div class="form-group"><input id="inst-csv-file" type="file" accept=".csv"></div>
      <button class="btn-warning" onclick="adminImportInstitutionCSV()">Upload CSV</button>
      <span id="inst-csv-result" style="margin-left:10px;font-size:0.85rem"></span>
    </div>
  `;

  let institutions = [];
  try {
    const data = await adminApi('GET', '/api/admin/institutions');
    institutions = data.institutions || [];
  } catch(e) {}

  html += `<h3 style="margin-bottom:12px">All Institutions (${institutions.length})</h3>`;
  html += `<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:0.82rem">
    <thead><tr style="background:#f3f4f6">
      <th style="padding:8px;text-align:left">ID</th>
      <th style="padding:8px;text-align:left">Name</th>
      <th style="padding:8px;text-align:left">Abbr</th>
      <th style="padding:8px;text-align:left">Category</th>
      <th style="padding:8px;text-align:left">County</th>
      <th style="padding:8px;text-align:left">Status</th>
      <th style="padding:8px;text-align:left">Actions</th>
    </tr></thead><tbody>`;

  institutions.forEach(inst => {
    const active = inst.active !== false;
    html += `<tr style="border-bottom:1px solid #e5e7eb">
      <td style="padding:6px 8px">${inst.id}</td>
      <td style="padding:6px 8px"><strong>${escHtml(inst.name)}</strong></td>
      <td style="padding:6px 8px">${escHtml(inst.abbreviation || '')}</td>
      <td style="padding:6px 8px">${escHtml(inst.category || '')}</td>
      <td style="padding:6px 8px">${escHtml(inst.county || '')}</td>
      <td style="padding:6px 8px"><span style="color:${active ? '#2e7d32' : '#c62828'}">${active ? 'Active' : 'Inactive'}</span></td>
      <td style="padding:6px 8px;white-space:nowrap">
        <button class="btn-warning" style="font-size:0.75rem;padding:4px 8px" onclick="adminEditInstitutionForm(${inst.id})">Edit</button>
        ${active ? `<button class="btn-danger" style="font-size:0.75rem;padding:4px 8px;margin-left:4px" onclick="adminDeactivateInstitution(${inst.id})">Deactivate</button>` : ''}
      </td>
    </tr>`;
  });
  html += '</tbody></table></div>';

  c.innerHTML = html;
  window._instAdminCategories = categories;
  window._instAdminData = institutions;
}

async function adminCreateInstitution() {
  const name = document.getElementById('inst-adm-name').value.trim();
  if (!name) { alert('Name is required'); return; }
  const data = {
    name,
    abbreviation: document.getElementById('inst-adm-abbr').value.trim() || undefined,
    category: document.getElementById('inst-adm-cat').value || undefined,
    ownership: document.getElementById('inst-adm-own').value,
    county: document.getElementById('inst-adm-county').value.trim() || undefined,
    town: document.getElementById('inst-adm-town').value.trim() || undefined,
    website: document.getElementById('inst-adm-website').value.trim() || undefined
  };
  try {
    await adminApi('POST', '/api/admin/institutions', data);
    loadInstitutionsAdminTab();
  } catch(e) { alert('Error: ' + JSON.stringify((e && e.data) || e)); }
}

async function adminDeactivateInstitution(id) {
  if (!confirm('Deactivate this institution?')) return;
  try {
    await adminApi('DELETE', `/api/admin/institutions/${id}`);
    loadInstitutionsAdminTab();
  } catch(e) { alert('Error'); }
}

function adminEditInstitutionForm(id) {
  const inst = (window._instAdminData || []).find(i => i.id === id);
  if (!inst) return;
  const cats = window._instAdminCategories || [];
  const catOptions = cats.map(c => `<option value="${escHtml(c.name)}" ${inst.category === c.name ? 'selected' : ''}>${escHtml(c.name)}</option>`).join('');
  openModal(`
    <div>
      <div class="form-title">Edit Institution</div>
      <div class="form-group"><label>Name *</label><input id="edt-name" class="form-input" value="${escHtml(inst.name)}"></div>
      <div class="form-group"><label>Abbreviation</label><input id="edt-abbr" class="form-input" value="${escHtml(inst.abbreviation || '')}"></div>
      <div class="form-group"><label>Category</label>
        <select id="edt-cat" class="form-input"><option value="">-- Select --</option>${catOptions}</select>
      </div>
      <div class="form-group"><label>Ownership</label>
        <select id="edt-own" class="form-input">
          <option value="Public" ${inst.ownership === 'Public' ? 'selected' : ''}>Public</option>
          <option value="Private" ${inst.ownership === 'Private' ? 'selected' : ''}>Private</option>
        </select>
      </div>
      <div class="form-group"><label>County</label><input id="edt-county" class="form-input" value="${escHtml(inst.county || '')}"></div>
      <div class="form-group"><label>Town</label><input id="edt-town" class="form-input" value="${escHtml(inst.town || '')}"></div>
      <div class="form-group"><label>Website</label><input id="edt-website" class="form-input" value="${escHtml(inst.website || '')}"></div>
      <div class="form-group"><label><input type="checkbox" id="edt-active" ${inst.active !== false ? 'checked' : ''}> Active</label></div>
      <button class="btn-primary" onclick="adminUpdateInstitution(${id})">Save Changes</button>
    </div>
  `);
  // openModal from admin context (no app.js openModal available, define inline)
}

async function adminUpdateInstitution(id) {
  const data = {
    name: document.getElementById('edt-name').value.trim(),
    abbreviation: document.getElementById('edt-abbr').value.trim() || null,
    category: document.getElementById('edt-cat').value || null,
    ownership: document.getElementById('edt-own').value,
    county: document.getElementById('edt-county').value.trim() || null,
    town: document.getElementById('edt-town').value.trim() || null,
    website: document.getElementById('edt-website').value.trim() || null,
    active: document.getElementById('edt-active').checked
  };
  if (!data.name) { alert('Name is required'); return; }
  try {
    await adminApi('PUT', `/api/admin/institutions/${id}`, data);
    // Close modal if present
    const overlay = document.getElementById('modal-overlay');
    if (overlay) overlay.classList.remove('open');
    loadInstitutionsAdminTab();
  } catch(e) { alert('Error: ' + JSON.stringify((e && e.data) || e)); }
}

async function adminImportInstitutionCSV() {
  const fileInput = document.getElementById('inst-csv-file');
  const result = document.getElementById('inst-csv-result');
  if (!fileInput || !fileInput.files[0]) { alert('Please select a CSV file'); return; }
  const fd = new FormData();
  fd.append('file', fileInput.files[0]);
  try {
    const res = await adminApi('POST', '/api/admin/institutions/import-csv', fd, true);
    result.textContent = `✅ Added: ${res.added}, Skipped: ${res.skipped}`;
    loadInstitutionsAdminTab();
  } catch(e) {
    result.textContent = '❌ Import failed';
    alert('Error: ' + JSON.stringify((e && e.data) || e));
  }
}

// Admin modal helper (admin.html doesn't use app.js modal)
function openModal(html) {
  let overlay = document.getElementById('modal-overlay');
  if (!overlay) {
    overlay = document.createElement('div');
    overlay.id = 'modal-overlay';
    overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:300;display:flex;align-items:flex-end;justify-content:center';
    overlay.innerHTML = '<div id="modal-box" style="background:white;border-radius:20px 20px 0 0;width:100%;max-width:680px;max-height:90vh;overflow-y:auto;padding:20px;position:relative"><button id="modal-close" style="position:absolute;top:12px;right:16px;background:none;border:none;font-size:1.5rem;cursor:pointer">&times;</button><div id="modal-body"></div></div>';
    document.body.appendChild(overlay);
    overlay.addEventListener('click', e => { if (e.target.id === 'modal-overlay') overlay.classList.remove('open'); });
    overlay.querySelector('#modal-close').addEventListener('click', () => overlay.classList.remove('open'));
  }
  overlay.querySelector('#modal-body').innerHTML = html;
  overlay.classList.add('open');
  overlay.style.display = 'flex';
}
