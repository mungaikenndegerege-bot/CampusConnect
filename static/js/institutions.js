// Institution Directory & Community System

const instState = {
  view: 'directory',
  currentInstitution: null,
  categoryFilter: 'All',
  countyFilter: '',
  searchQuery: '',
  page: 1,
  hasMore: true,
  posts: [],
  postPage: 1,
  postHasMore: true
};

// Called by navigate('institutions')
async function renderInstitutions() {
  const mc = document.getElementById('main-content');
  instState.view = 'directory';
  instState.page = 1;
  instState.hasMore = true;
  instState.categoryFilter = 'All';
  instState.countyFilter = '';
  instState.searchQuery = '';

  mc.innerHTML = `
    <div class="section-header">
      <h2 class="section-title">🏫 Institution Directory</h2>
      <p style="font-size:0.82rem;color:#666;margin-top:4px">Find and join your institution's community</p>
    </div>
    <div style="margin-bottom:12px">
      <input id="inst-search" class="form-input" placeholder="🔍 Search by name, abbreviation or county…" style="margin-bottom:8px">
      <div class="inst-category-tabs" id="inst-cat-tabs">
        <button class="active" data-cat="All">All</button>
        <button data-cat="University">Universities</button>
        <button data-cat="National Polytechnic">Polytechnics</button>
        <button data-cat="Technical Training Institute">TTIs</button>
        <button data-cat="Technical and Vocational College">TVETs</button>
        <button data-cat="Specialised Training Institution">Specialised</button>
        <button data-cat="Other">Other</button>
      </div>
      <select id="inst-county-filter" class="form-input" style="margin-top:8px">
        <option value="">All Counties</option>
      </select>
    </div>
    <div id="inst-cards"></div>
    <button id="inst-load-more" class="load-more-btn" style="display:none">Load More</button>
  `;

  // Populate county dropdown
  try {
    const data = await fetch('/api/institutions/counties').then(r => r.json());
    const sel = document.getElementById('inst-county-filter');
    (data.counties || []).forEach(c => {
      const opt = document.createElement('option');
      opt.value = c;
      opt.textContent = c;
      sel.appendChild(opt);
    });
  } catch(e) {}

  const fab = document.getElementById('fab-btn');
  if (fab) fab.style.display = 'none';

  loadInstitutionCards(true);

  // Debounced search
  let searchTimer;
  document.getElementById('inst-search').addEventListener('input', e => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      instState.searchQuery = e.target.value.trim();
      instState.page = 1;
      loadInstitutionCards(true);
    }, 300);
  });

  // Category tabs
  document.getElementById('inst-cat-tabs').addEventListener('click', e => {
    const btn = e.target.closest('button[data-cat]');
    if (!btn) return;
    document.querySelectorAll('#inst-cat-tabs button').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    instState.categoryFilter = btn.dataset.cat;
    instState.page = 1;
    loadInstitutionCards(true);
  });

  // County filter
  document.getElementById('inst-county-filter').addEventListener('change', e => {
    instState.countyFilter = e.target.value;
    instState.page = 1;
    loadInstitutionCards(true);
  });

  // Load more
  document.getElementById('inst-load-more').addEventListener('click', () => {
    instState.page++;
    loadInstitutionCards(false);
  });
}

async function loadInstitutionCards(reset) {
  const container = document.getElementById('inst-cards');
  const loadMoreBtn = document.getElementById('inst-load-more');
  if (!container) return;

  if (reset) {
    container.innerHTML = '<div class="spinner"></div>';
    instState.page = 1;
  }

  // Build query params
  const params = new URLSearchParams();
  params.set('page', instState.page);
  params.set('per_page', '30');

  if (instState.searchQuery) params.set('q', instState.searchQuery);
  if (instState.countyFilter) params.set('county', instState.countyFilter);

  // Map category filter to API param
  const cat = instState.categoryFilter;
  if (cat !== 'All' && cat !== 'University' && cat !== 'Other') {
    params.set('category', cat);
  }

  try {
    const data = await fetch(`/api/institutions?${params}`).then(r => r.json());
    let institutions = data.institutions || [];

    // Client-side filter for 'University' tab (matches both Public and Private universities)
    if (cat === 'University') {
      institutions = institutions.filter(i => i.category && i.category.toLowerCase().includes('university'));
    } else if (cat === 'Other') {
      institutions = institutions.filter(i => {
        if (!i.category) return true;
        const known = ['university', 'polytechnic', 'technical training', 'technical and vocational', 'specialised'];
        return !known.some(k => i.category.toLowerCase().includes(k));
      });
    }

    if (reset) container.innerHTML = '';

    if (institutions.length === 0 && reset) {
      container.innerHTML = '<div class="empty-state"><div class="empty-icon">🏫</div><p>No institutions found.</p></div>';
      if (loadMoreBtn) loadMoreBtn.style.display = 'none';
      return;
    }

    institutions.forEach(inst => {
      container.insertAdjacentHTML('beforeend', renderInstitutionCard(inst));
    });

    // Wire up card clicks
    container.querySelectorAll('.inst-card:not([data-wired])').forEach(card => {
      card.dataset.wired = '1';
      card.addEventListener('click', e => {
        if (e.target.closest('button')) return;
        openInstitutionCommunity(parseInt(card.dataset.id));
      });
      const btn = card.querySelector('.btn-view-community');
      if (btn) btn.addEventListener('click', () => openInstitutionCommunity(parseInt(card.dataset.id)));
    });

    instState.hasMore = data.page < data.pages;
    if (loadMoreBtn) loadMoreBtn.style.display = instState.hasMore ? 'block' : 'none';

  } catch(e) {
    if (reset) container.innerHTML = '<div class="empty-state"><p>Could not load institutions.</p></div>';
  }
}

function renderInstitutionCard(inst) {
  const abbr = inst.abbreviation ? `<span class="inst-abbr-badge">${escHtml(inst.abbreviation)}</span>` : '';
  const cat = inst.category ? `<span class="inst-category">${escHtml(inst.category)}</span>` : '';
  const county = inst.county ? `<span>📍 ${escHtml(inst.county)}</span>` : '';
  const members = `<span>👥 ${inst.member_count || 0} members</span>`;
  return `
    <div class="inst-card card" data-id="${inst.id}">
      <div class="inst-card-header">
        ${abbr}
        <div class="inst-card-title"><h3>${escHtml(inst.name)}</h3></div>
      </div>
      <div class="inst-card-meta">
        ${cat}${county}${members}
      </div>
      <button class="btn-view-community">View Community →</button>
    </div>
  `;
}

async function openInstitutionCommunity(id) {
  const mc = document.getElementById('main-content');
  instState.view = 'community';
  instState.postPage = 1;
  instState.postHasMore = true;

  mc.innerHTML = '<div class="spinner"></div>';
  try {
    const inst = await fetch(`/api/institutions/${id}`).then(r => r.json());
    instState.currentInstitution = inst;
    const comm = inst.community || {};
    const myInst = getMyInstitution();
    const isMyInst = myInst && myInst.id === inst.id;

    mc.innerHTML = `
      <div style="margin-bottom:12px">
        <button id="inst-back-btn" style="background:none;border:none;color:#6C3CE1;font-size:0.9rem;cursor:pointer;padding:0;font-weight:600">← Back to Directory</button>
      </div>
      <div class="card" style="margin-bottom:12px">
        <div class="inst-card-header">
          ${inst.abbreviation ? `<span class="inst-abbr-badge">${escHtml(inst.abbreviation)}</span>` : ''}
          <div class="inst-card-title"><h3 style="font-size:1.1rem">${escHtml(inst.name)}</h3></div>
        </div>
        <div class="inst-card-meta" style="margin-bottom:8px">
          ${inst.category ? `<span class="inst-category">${escHtml(inst.category)}</span>` : ''}
          ${inst.county ? `<span>📍 ${escHtml(inst.county)}${inst.town ? ', ' + escHtml(inst.town) : ''}</span>` : ''}
          ${inst.ownership ? `<span class="badge">${escHtml(inst.ownership)}</span>` : ''}
        </div>
        ${inst.website ? `<p style="font-size:0.82rem;margin-bottom:8px"><a href="${escHtml(inst.website)}" target="_blank" rel="noopener" style="color:#2563eb">${escHtml(inst.website)}</a></p>` : ''}
        <div style="display:flex;gap:16px;font-size:0.85rem;color:#666;margin-bottom:10px">
          <span>👥 <strong>${comm.member_count || 0}</strong> members</span>
          <span>💬 <strong>${comm.post_count || 0}</strong> posts</span>
        </div>
        <button id="inst-select-btn" class="btn-primary" style="margin-top:0;background:${isMyInst ? '#2e7d32' : '#2563eb'}">
          ${isMyInst ? '✅ My Institution' : '⭐ Select as My Institution'}
        </button>
      </div>
      <div class="inst-category-tabs" id="inst-view-tabs" style="margin-bottom:12px">
        <button class="active" data-view="posts">Posts</button>
        <button data-view="about">About</button>
      </div>
      <div id="inst-community-content"></div>
      <button id="inst-post-load-more" class="load-more-btn" style="display:none">Load More Posts</button>
    `;

    document.getElementById('inst-back-btn').addEventListener('click', () => renderInstitutions());
    document.getElementById('inst-select-btn').addEventListener('click', () => selectMyInstitution(inst));
    document.getElementById('inst-view-tabs').addEventListener('click', e => {
      const btn = e.target.closest('button[data-view]');
      if (!btn) return;
      document.querySelectorAll('#inst-view-tabs button').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      if (btn.dataset.view === 'posts') {
        instState.postPage = 1;
        loadInstitutionPosts(id, true);
      } else {
        renderInstAbout(inst);
      }
    });

    document.getElementById('inst-post-load-more').addEventListener('click', () => {
      instState.postPage++;
      loadInstitutionPosts(id, false);
    });

    // Show FAB for posting
    const fab = document.getElementById('fab-btn');
    if (fab) {
      fab.textContent = '✏️ Post Here';
      fab.style.display = 'flex';
      fab.onclick = () => openInstPostForm(id);
    }

    loadInstitutionPosts(id, true);

  } catch(e) {
    mc.innerHTML = '<div class="empty-state"><p>Could not load institution.</p></div>';
  }
}

async function loadInstitutionPosts(id, reset) {
  const container = document.getElementById('inst-community-content');
  const loadMoreBtn = document.getElementById('inst-post-load-more');
  if (!container) return;

  if (reset) {
    container.innerHTML = '<div class="spinner"></div>';
    instState.postPage = 1;
  }

  try {
    const data = await fetch(`/api/institutions/${id}/posts?page=${instState.postPage}`).then(r => r.json());
    const posts = data.posts || [];
    const inst = instState.currentInstitution;

    if (reset) container.innerHTML = '';

    if (posts.length === 0 && reset) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">💬</div>
          <p>No posts yet. Be the first to post!</p>
          <button class="btn-primary" style="width:auto;padding:10px 20px;margin-top:12px" onclick="openInstPostForm(${id})">Create First Post</button>
        </div>`;
      if (loadMoreBtn) loadMoreBtn.style.display = 'none';
      return;
    }

    posts.forEach(post => {
      const card = document.createElement('div');
      card.innerHTML = renderInstPostCard(post, inst);
      const el = card.firstElementChild;
      el.addEventListener('click', () => openInstPostDetail(post, inst));
      container.appendChild(el);
    });

    instState.postHasMore = data.page < data.pages;
    if (loadMoreBtn) loadMoreBtn.style.display = instState.postHasMore ? 'block' : 'none';

  } catch(e) {
    if (reset) container.innerHTML = '<div class="empty-state"><p>Could not load posts.</p></div>';
  }
}

function renderInstPostCard(post, inst) {
  const topic = post.topic || 'General';
  const topicColors = {
    General: '#6C3CE1', Academic: '#2563eb', Housing: '#d97706',
    Jobs: '#059669', Events: '#db2777', Announcements: '#dc2626', Other: '#6b7280'
  };
  const color = topicColors[topic] || '#6C3CE1';
  const preview = post.body.length > 120 ? post.body.substring(0, 120) + '…' : post.body;
  return `
    <div class="card" style="cursor:pointer" data-post-id="${post.id}">
      <div style="margin-bottom:6px">
        <span class="badge" style="background:${color}20;color:${color}">${escHtml(topic)}</span>
      </div>
      <div class="card-title">${escHtml(post.title)}</div>
      <div class="card-body">${escHtml(preview)}</div>
      ${post.file_url && post.file_type === 'image' ? `<img src="${escHtml(post.file_url)}" style="width:100%;max-height:200px;object-fit:cover;border-radius:8px;margin-top:8px">` : ''}
      ${post.file_url && post.file_type === 'file' ? `<a href="${escHtml(post.file_url)}" target="_blank" style="color:#6C3CE1;font-size:.85rem">&#128196; View Attachment</a>` : ''}
      <div class="card-meta" style="margin-top:8px">
        <span style="font-size:0.78rem;color:#666">👤 ${escHtml(post.poster_name)}</span>
        <span style="font-size:0.78rem;color:#9ca3af;margin-left:auto">${timeAgo(post.created_at)}</span>
      </div>
    </div>
  `;
}

async function openInstPostDetail(post, inst) {
  openModal('<div class="spinner"></div>');
  try {
    const data = await fetch(`/api/institutions/${inst.id}/posts/${post.id}/comments`).then(r => r.json());
    const comments = data.comments || [];
    openModal(`
      <div class="detail-modal">
        <div class="card-header">
          <div class="avatar">${escHtml(avatarLetter(post.poster_name))}</div>
          <div class="poster-info">
            <div class="poster-name">${escHtml(post.poster_name)}</div>
            <div class="post-time">${timeAgo(post.created_at)}</div>
          </div>
        </div>
        <span class="badge" style="margin-bottom:8px;display:inline-block">${escHtml(post.topic || 'General')}</span>
        <h3 style="margin:8px 0 6px">${escHtml(post.title)}</h3>
        <p style="color:#374151;line-height:1.6">${escHtml(post.body)}</p>
        ${post.file_url && post.file_type === 'image' ? `<img src="${escHtml(post.file_url)}" style="width:100%;max-height:260px;object-fit:cover;border-radius:8px;margin-top:8px">` : ''}
        ${post.file_url && post.file_type === 'file' ? `<a href="${escHtml(post.file_url)}" target="_blank" style="color:#6C3CE1;font-size:.9rem">&#128196; View Attachment</a>` : ''}
        ${post.poster_contact ? `<p style="font-size:0.85rem;color:#666;margin-top:6px">📞 ${escHtml(post.poster_contact)}</p>` : ''}
        <hr style="margin:14px 0;border:none;border-top:1px solid #e5e7eb">
        <h4 style="margin-bottom:10px">💬 Comments (${comments.length})</h4>
        <div id="inst-comments-list">
          ${comments.length === 0
            ? '<p style="color:#9ca3af;font-size:0.88rem">No comments yet. Be the first!</p>'
            : comments.map(c => `
              <div style="padding:8px 0;border-bottom:1px solid #f3f4f6">
                <strong style="font-size:0.88rem">${escHtml(c.poster_name)}</strong>
                <span style="font-size:0.75rem;color:#9ca3af;margin-left:8px">${timeAgo(c.created_at)}</span>
                <p style="margin:4px 0;font-size:0.9rem;color:#374151">${escHtml(c.body)}</p>
              </div>`).join('')}
        </div>
        <div style="margin-top:14px">
          <input id="inst-comment-name" class="form-input" placeholder="Your name" style="margin-bottom:6px">
          <textarea id="inst-comment-body" class="form-input" placeholder="Write a comment…" rows="2" style="resize:none"></textarea>
          <button id="inst-submit-comment" class="btn-primary" style="margin-top:6px;width:100%">Post Comment</button>
        </div>
      </div>
    `);
    document.getElementById('inst-submit-comment').addEventListener('click', async () => {
      const name = document.getElementById('inst-comment-name').value.trim();
      const body = document.getElementById('inst-comment-body').value.trim();
      if (!name || !body) { showToast('Please enter your name and comment', 'error'); return; }
      try {
        await fetch(`/api/institutions/${inst.id}/posts/${post.id}/comments`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ poster_name: name, body })
        });
        openInstPostDetail(post, inst);
      } catch(e) { showToast('Failed to post comment', 'error'); }
    });
  } catch(e) {
    openModal('<div class="empty-state"><p>Could not load post.</p></div>');
  }
}

function openInstPostForm(institutionId) {
  openModal(`
    <div>
      <div class="form-title">✏️ New Post</div>
      <div class="form-group"><label>Your Name *</label><input id="ip-name" class="form-input" placeholder="Enter your name"></div>
      <div class="form-group"><label>Contact <span class="optional-label">(optional)</span></label><input id="ip-contact" class="form-input" placeholder="Phone or email"></div>
      <div class="form-group"><label>Title *</label><input id="ip-title" class="form-input" placeholder="Post title"></div>
      <div class="form-group"><label>Body *</label><textarea id="ip-body" class="form-input" rows="4" placeholder="Write your post…" style="resize:none"></textarea></div>
      <div class="form-group"><label>Topic</label>
        <select id="ip-topic" class="form-input">
          <option>General</option>
          <option>Academic</option>
          <option>Housing</option>
          <option>Jobs</option>
          <option>Events</option>
          <option>Announcements</option>
          <option>Other</option>
        </select>
      </div>
      <div class="form-group"><label style="font-size:.8rem;color:#9ca3af;margin-top:4px">&#128206; Attach image or file (optional, max 10MB)<input type="file" id="ip-attachment" accept=".jpg,.jpeg,.png,.webp,.gif,.pdf,.doc,.docx" style="margin-top:4px;display:block"></label></div>
      <button id="ip-submit" class="btn-primary">Post</button>
    </div>
  `);
  document.getElementById('ip-submit').addEventListener('click', async () => {
    const poster_name = document.getElementById('ip-name').value.trim();
    const title = document.getElementById('ip-title').value.trim();
    const body = document.getElementById('ip-body').value.trim();
    const topic = document.getElementById('ip-topic').value;
    const poster_contact = document.getElementById('ip-contact').value.trim();
    if (!poster_name || !title || !body) {
      showToast('Name, title, and body are required', 'error');
      return;
    }
    const fileInput = document.getElementById('ip-attachment');
    const file = fileInput && fileInput.files && fileInput.files[0];
    const requestHeaders = idempotencyHeaders('institution_post');
    try {
      if (file) {
        const fd = new FormData();
        fd.append('poster_name', poster_name);
        fd.append('title', title);
        fd.append('body', body);
        fd.append('topic', topic);
        if (poster_contact) fd.append('poster_contact', poster_contact);
        fd.append('attachment', file);
        const res = await fetch(`/api/institutions/${institutionId}/posts`, {
          method: 'POST',
          headers: requestHeaders,
          body: fd
        });
        if (!res.ok) throw new Error();
        const created = await res.json();
        rememberContentOwnerToken('institution_post', created.id, created.owner_token);
      } else {
        const res = await fetch(`/api/institutions/${institutionId}/posts`, {
          method: 'POST',
          headers: Object.assign({ 'Content-Type': 'application/json' }, requestHeaders),
          body: JSON.stringify({ poster_name, title, body, topic, poster_contact: poster_contact || undefined })
        });
        if (!res.ok) throw new Error();
        const created = await res.json();
        rememberContentOwnerToken('institution_post', created.id, created.owner_token);
      }
      completeIdempotentSubmission('institution_post');
      showToast('Post created!', 'success');
      closeModal();
      instState.postPage = 1;
      loadInstitutionPosts(institutionId, true);
    } catch(e) { showToast('Failed to create post', 'error'); }
  });
}

function renderInstAbout(inst) {
  const container = document.getElementById('inst-community-content');
  if (!container) return;
  container.innerHTML = `
    <div class="card">
      <h4 style="margin-bottom:12px;color:#2563eb">About ${escHtml(inst.name)}</h4>
      <table style="width:100%;font-size:0.9rem;border-collapse:collapse">
        ${row('Full Name', inst.name)}
        ${row('Abbreviation', inst.abbreviation)}
        ${row('Category', inst.category)}
        ${row('Ownership', inst.ownership)}
        ${row('County', inst.county)}
        ${row('Town', inst.town)}
        ${inst.website ? `<tr><td style="padding:6px 0;color:#666;width:40%">Website</td><td><a href="${escHtml(inst.website)}" target="_blank" rel="noopener" style="color:#2563eb">${escHtml(inst.website)}</a></td></tr>` : ''}
        ${row('Source', inst.source)}
      </table>
    </div>
  `;
  function row(label, val) {
    if (!val) return '';
    return `<tr><td style="padding:6px 0;color:#666;width:40%">${escHtml(label)}</td><td style="font-weight:600">${escHtml(val)}</td></tr>`;
  }
}

function getMyInstitution() {
  try {
    return JSON.parse(localStorage.getItem('cc_my_institution') || 'null');
  } catch(e) { return null; }
}

function selectMyInstitution(inst) {
  const data = { id: inst.id, name: inst.name, abbreviation: inst.abbreviation };
  localStorage.setItem('cc_my_institution', JSON.stringify(data));
  fetch(`/api/institutions/${inst.id}/join`, { method: 'POST' }).catch(() => {});
  renderMyInstitutionBadge();
  showToast(`✅ ${inst.abbreviation || inst.name} set as your institution`, 'success');
  // Refresh the select button
  const btn = document.getElementById('inst-select-btn');
  if (btn) {
    btn.textContent = '✅ My Institution';
    btn.style.background = '#2e7d32';
  }
}

function renderMyInstitutionBadge() {
  const existing = document.getElementById('my-inst-badge');
  if (existing) existing.remove();

  const myInst = getMyInstitution();
  if (!myInst) return;

  const topBar = document.getElementById('top-bar');
  if (!topBar) return;

  const badge = document.createElement('div');
  badge.id = 'my-inst-badge';
  badge.className = 'my-institution-badge';
  badge.innerHTML = `🏫 <strong>${escHtml(myInst.abbreviation || myInst.name)}</strong> <a href="#" id="inst-badge-change">Change</a>`;
  topBar.appendChild(badge);

  document.getElementById('inst-badge-change').addEventListener('click', e => {
    e.preventDefault();
    navigate('institutions');
  });
}

// Run on page load
document.addEventListener('DOMContentLoaded', () => {
  renderMyInstitutionBadge();
});
