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
  const loaders = { ads: loadAdsTab, announcements: loadAnnouncementsTab, posts: loadPostsTab, marketplace: loadMarketplaceTab, lostandfound: loadLFTab };
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
