// learning.js — Learning Hub for CampusConnect

(function () {
  let _page = 1;
  let _filters = { resource_type: '', subject: '', q: '' };
  let _loading = false;

  const TYPE_LABELS = {
    notes: 'Notes',
    past_paper: 'Past Paper',
    textbook: 'Textbook',
    other: 'Other',
  };

  function _learnApi(method, path, body) {
    const opts = { method, headers: {} };
    if (body && !(body instanceof FormData)) {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    } else if (body) {
      opts.body = body;
    }
    return fetch(path, opts).then(async r => {
      const d = await r.json().catch(() => ({}));
      if (!r.ok) throw d;
      return d;
    });
  }

  async function loadResources(reset) {
    if (_loading) return;
    _loading = true;
    if (reset) _page = 1;

    const container = document.getElementById('learn-cards');
    if (!container) { _loading = false; return; }
    if (reset) container.innerHTML = '<div class="spinner" style="margin:24px auto"></div>';

    const params = new URLSearchParams({ page: _page });
    if (_filters.resource_type) params.set('resource_type', _filters.resource_type);
    if (_filters.subject) params.set('subject', _filters.subject);
    if (_filters.q) params.set('q', _filters.q);

    try {
      const data = await _learnApi('GET', '/api/learn?' + params.toString());
      if (!document.getElementById('learn-cards')) { _loading = false; return; }
      const items = data.items || [];
      if (reset) container.innerHTML = '';

      if (!items.length && _page === 1) {
        container.innerHTML = '<div class="empty-state" style="text-align:center;padding:32px"><div style="font-size:2rem">📚</div><p>No resources yet. Share the first one!</p></div>';
        _loading = false; return;
      }

      items.forEach(item => {
        const card = document.createElement('div');
        card.className = 'card resource-card';
        card.style.marginBottom = '12px';
        const typeClass = item.resource_type || 'other';
        const fileIcon = item.file_type === 'image' ? '🖼️' : (item.file_type === 'pdf' ? '📄' : '📝');
        card.innerHTML = `
          <div style="display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-bottom:6px">
            <strong style="font-size:.95rem">${escHtml(item.title)}</strong>
            <span class="resource-type-badge ${typeClass}">${escHtml(TYPE_LABELS[item.resource_type] || item.resource_type)}</span>
          </div>
          <div style="font-size:.82rem;color:var(--text-muted);margin-bottom:4px">
            📖 ${escHtml(item.subject)}
            ${item.institution_name ? ' · ' + escHtml(item.institution_name) : ''}
          </div>
          ${item.description ? `<p style="font-size:.85rem;margin-bottom:8px;color:#374151">${escHtml(item.description)}</p>` : ''}
          <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">
            <span style="font-size:.78rem;color:var(--text-muted)">By ${escHtml(item.uploader_name)}</span>
            <span class="download-count">${fileIcon} ${item.download_count} downloads</span>
            <span style="font-size:.72rem;color:var(--text-muted)">${timeAgo(item.created_at)}</span>
          </div>
          <div style="margin-top:10px;display:flex;gap:8px;flex-wrap:wrap">
            <a href="/api/learn/${item.id}/download" target="_blank" class="btn btn-primary" style="font-size:.82rem;padding:6px 16px;text-decoration:none">⬇ Download</a>
            ${item.uploader_contact ? `<button class="btn" style="font-size:.82rem;padding:6px 16px" onclick="window._contactUploader('${escHtml(item.uploader_contact)}', '${escHtml(item.uploader_name)}')">Contact</button>` : ''}
          </div>
        `;
        container.appendChild(card);
      });

      const loadMoreBtn = document.getElementById('learn-load-more');
      if (loadMoreBtn) {
        loadMoreBtn.style.display = data.page < data.pages ? 'block' : 'none';
      }
      _page++;
    } catch (e) {
      if (document.getElementById('learn-cards')) {
        document.getElementById('learn-cards').innerHTML += '<div style="color:#ef4444;padding:12px">Failed to load resources.</div>';
      }
    }
    _loading = false;
  }

  window._contactUploader = function (contact, name) {
    openModal(`
      <div style="max-width:320px;margin:0 auto;text-align:center">
        <h3 style="margin-bottom:12px">Contact ${escHtml(name)}</h3>
        <p style="font-size:1rem;font-weight:600;margin-bottom:16px">${escHtml(contact)}</p>
        <p style="font-size:.85rem;color:var(--text-muted)">Reach out directly.</p>
      </div>
    `);
  };

  function openUploadForm() {
    openModal(`
      <div style="max-width:420px;margin:0 auto">
        <h3 style="margin-bottom:14px">📚 Share a Resource</h3>
        <div style="margin-bottom:10px">
          <label class="form-label">Title *</label>
          <input id="lr-title" class="form-input" placeholder="e.g. BCOM Year 2 Accounts Notes">
        </div>
        <div style="margin-bottom:10px">
          <label class="form-label">Subject *</label>
          <input id="lr-subject" class="form-input" placeholder="e.g. Financial Accounting">
        </div>
        <div style="margin-bottom:10px">
          <label class="form-label">Resource Type *</label>
          <select id="lr-type" class="form-input">
            <option value="notes">Notes</option>
            <option value="past_paper">Past Paper</option>
            <option value="textbook">Textbook</option>
            <option value="other">Other</option>
          </select>
        </div>
        <div style="margin-bottom:10px">
          <label class="form-label">Institution (optional)</label>
          <input id="lr-institution" class="form-input" placeholder="e.g. KU, UoN, Strathmore">
        </div>
        <div style="margin-bottom:10px">
          <label class="form-label">Description (optional)</label>
          <textarea id="lr-desc" class="form-input" rows="2" placeholder="Brief description…"></textarea>
        </div>
        <div style="margin-bottom:10px">
          <label class="form-label">Your Name *</label>
          <input id="lr-uploader" class="form-input" placeholder="Your name">
        </div>
        <div style="margin-bottom:10px">
          <label class="form-label">Contact (optional)</label>
          <input id="lr-contact" class="form-input" placeholder="Phone or email">
        </div>
        <div style="margin-bottom:14px">
          <label class="form-label">File * (PDF, DOC, DOCX, JPG, PNG — max 20 MB)</label>
          <input id="lr-file" type="file" accept=".pdf,.doc,.docx,.jpg,.jpeg,.png" class="form-input">
        </div>
        <div id="lr-error" style="color:#ef4444;font-size:.82rem;margin-bottom:8px;display:none"></div>
        <button class="btn btn-primary" style="width:100%" onclick="window._submitLearn()">Upload Resource</button>
      </div>
    `);
  }

  window._submitLearn = async function () {
    const title = (document.getElementById('lr-title').value || '').trim();
    const subject = (document.getElementById('lr-subject').value || '').trim();
    const rtype = document.getElementById('lr-type').value;
    const institution = (document.getElementById('lr-institution').value || '').trim();
    const desc = (document.getElementById('lr-desc').value || '').trim();
    const uploader = (document.getElementById('lr-uploader').value || '').trim();
    const contact = (document.getElementById('lr-contact').value || '').trim();
    const fileInput = document.getElementById('lr-file');
    const errEl = document.getElementById('lr-error');
    errEl.style.display = 'none';

    if (!title || !subject || !uploader) {
      errEl.textContent = 'Please fill in all required fields.';
      errEl.style.display = 'block';
      return;
    }
    if (!fileInput.files || !fileInput.files[0]) {
      errEl.textContent = 'Please select a file to upload.';
      errEl.style.display = 'block';
      return;
    }
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('title', title);
    formData.append('subject', subject);
    formData.append('resource_type', rtype);
    formData.append('uploader_name', uploader);
    if (institution) formData.append('institution_name', institution);
    if (desc) formData.append('description', desc);
    if (contact) formData.append('uploader_contact', contact);

    try {
      const res = await fetch('/api/learn', { method: 'POST', body: formData });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw data;
      closeModal();
      showToast('Resource uploaded!', 'success');
      if (data.owner_token) {
        showToast('Save your edit token: ' + data.owner_token, 'info');
      }
      loadResources(true);
    } catch (e) {
      errEl.textContent = (e && e.error) ? e.error : 'Upload failed. Check the file and try again.';
      errEl.style.display = 'block';
    }
  };

  window.renderLearning = function () {
    const main = document.getElementById('main-content');
    main.innerHTML = `
      <div style="margin-bottom:14px">
        <h2 style="font-size:1.1rem;margin-bottom:10px">📚 Learning Hub</h2>
        <!-- Category tabs -->
        <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px" id="learn-type-tabs">
          ${['', 'notes', 'past_paper', 'textbook', 'other'].map(t =>
            `<button class="btn${_filters.resource_type === t ? ' btn-primary' : ''}" style="font-size:.8rem;padding:5px 12px" onclick="window._learnTypeFilter('${t}')">${t ? (TYPE_LABELS[t] || t) : 'All'}</button>`
          ).join('')}
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <input id="learn-subject-filter" class="form-input" style="flex:1;min-width:130px" placeholder="Filter by subject…" value="${escHtml(_filters.subject)}" oninput="window._learnSubjectFilter()">
          <input id="learn-search-filter" class="form-input" style="flex:1;min-width:130px" placeholder="Search resources…" value="${escHtml(_filters.q)}" oninput="window._learnSearchFilter()">
        </div>
      </div>
      <div id="learn-cards"></div>
      <div style="text-align:center;margin:12px 0">
        <button id="learn-load-more" class="btn" style="display:none" onclick="loadResources(false)">Load More</button>
      </div>
      <button class="fab-btn" style="position:fixed;bottom:80px;right:16px;background:#6C3CE1;color:white;border:none;border-radius:50px;padding:12px 20px;font-size:.9rem;font-weight:700;cursor:pointer;z-index:50;box-shadow:0 4px 12px rgba(108,60,225,0.4)" onclick="window._openUploadForm()">📚 Share Resource</button>
    `;
    window._openUploadForm = openUploadForm;
    loadResources(true);
  };

  const TYPE_LABELS_REF = {
    notes: 'Notes', past_paper: 'Past Paper', textbook: 'Textbook', other: 'Other',
  };

  window._learnTypeFilter = function (type) {
    _filters.resource_type = type;
    document.querySelectorAll('#learn-type-tabs button').forEach((btn, i) => {
      const types = ['', 'notes', 'past_paper', 'textbook', 'other'];
      btn.classList.toggle('btn-primary', types[i] === type);
    });
    loadResources(true);
  };

  window._learnSubjectFilter = function () {
    _filters.subject = (document.getElementById('learn-subject-filter').value || '').trim();
    clearTimeout(window._learnSubjectTimer);
    window._learnSubjectTimer = setTimeout(() => loadResources(true), 400);
  };

  window._learnSearchFilter = function () {
    _filters.q = (document.getElementById('learn-search-filter').value || '').trim();
    clearTimeout(window._learnSearchTimer);
    window._learnSearchTimer = setTimeout(() => loadResources(true), 400);
  };

  window.loadResources = loadResources;
})();
