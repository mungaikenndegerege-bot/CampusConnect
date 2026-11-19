// State
const state = { section: 'feed', ads: [], adIndex: 0 };

// API helper
async function api(method, path, body, isFormData) {
  const opts = { method, headers: {} };
  if (body && !isFormData) {
    opts.headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(body);
  } else if (body && isFormData) {
    opts.body = body;
  }
  const token = localStorage.getItem('cc_admin_token');
  if (token) opts.headers['X-Admin-Token'] = token;
  const accountToken = localStorage.getItem('cc_account_token');
  if (accountToken) opts.headers['X-Account-Token'] = accountToken;
  const res = await fetch(path, opts);
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw { status: res.status, data };
  }
  return res.json();
}

// Helpers
function timeAgo(dateStr) {
  const diff = (Date.now() - new Date(dateStr.endsWith('Z') ? dateStr : dateStr + 'Z')) / 1000;
  if (diff < 60) return 'just now';
  if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
  if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
  return Math.floor(diff / 86400) + 'd ago';
}

function avatarLetter(name) { return (name || '?')[0].toUpperCase(); }

function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function showToast(msg, type) {
  const t = document.createElement('div');
  t.className = 'toast ' + (type || '');
  t.textContent = msg;
  document.getElementById('toast-container').appendChild(t);
  setTimeout(() => t.remove(), 3200);
}

function openModal(html) {
  document.getElementById('modal-body').innerHTML = html;
  document.getElementById('modal-overlay').classList.add('open');
}

function closeModal() {
  document.getElementById('modal-overlay').classList.remove('open');
  document.getElementById('modal-body').innerHTML = '';
}

function injectAds(items) {
  if (!state.ads.length) return items;
  const result = [];
  items.forEach((item, i) => {
    result.push(item);
    if ((i + 1) % 5 === 0) {
      const ad = state.ads[state.adIndex % state.ads.length];
      state.adIndex++;
      result.push({ ...ad, type: 'ad' });
    }
  });
  return result;
}

function renderAdBanner(ad) {
  return `<div class="ad-banner">
    <div class="ad-label">Sponsored</div>
    ${ad.image_path ? `<img class="ad-image" src="/api/uploads/${escHtml(ad.image_path)}" alt="">` : ''}
    <div class="ad-title">${escHtml(ad.title)}</div>
    <div class="ad-body">${escHtml(ad.body)}</div>
    ${ad.link_url ? `<a class="ad-link" href="${escHtml(ad.link_url)}" target="_blank" rel="noopener" onclick="fetch('/api/ads/${ad.id}/click',{method:'POST'})">Learn More</a>` : ''}
  </div>`;
}

function navigate(section) {
  state.section = section;
  document.querySelectorAll('#bottom-nav button').forEach(b =>
    b.classList.toggle('active', b.dataset.section === section)
  );
  const fab = document.getElementById('fab-btn');
  const fabLabels = { community: '\u270f\ufe0f Post', marketplace: '+ List Item', lostandfound: '+ Report' };
  if (fabLabels[section]) {
    fab.textContent = fabLabels[section];
    fab.style.display = 'flex';
    fab.onclick = () => openPostForm(section);
  } else {
    fab.style.display = 'none';
  }
  const renders = { feed: renderFeed, community: renderCommunity, marketplace: renderMarketplace, lostandfound: renderLostFound, announcements: renderAnnouncements, institutions: renderInstitutions };
  renders[section]();
}

function openPostForm(section) {
  if (section === 'community') openCommunityForm();
  else if (section === 'marketplace') openMarketplaceForm();
  else if (section === 'lostandfound') openLostFoundForm();
}

document.addEventListener('DOMContentLoaded', async () => {
  try { state.ads = await api('GET', '/api/ads/active'); } catch(e) { state.ads = []; }
  document.querySelectorAll('#bottom-nav button').forEach(b =>
    b.addEventListener('click', () => navigate(b.dataset.section))
  );
  document.getElementById('modal-close').addEventListener('click', closeModal);
  document.getElementById('modal-overlay').addEventListener('click', e => {
    if (e.target.id === 'modal-overlay') closeModal();
  });
  navigate('feed');
});

if ('serviceWorker' in navigator) navigator.serviceWorker.register('/static/sw.js').catch(() => {});
