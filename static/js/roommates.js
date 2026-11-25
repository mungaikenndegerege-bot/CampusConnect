// roommates.js — Roommate Finder for CampusConnect

(function () {
  let _page = 1;
  let _filters = { location: '', gender_preference: 'Any', budget_max: '' };
  let _loading = false;

  function _roommateApi(method, path, body, extraHeaders) {
    const opts = { method, headers: { 'Content-Type': 'application/json' } };
    if (extraHeaders) Object.assign(opts.headers, extraHeaders);
    if (body) opts.body = JSON.stringify(body);
    return fetch(path, opts).then(async r => {
      const d = await r.json().catch(() => ({}));
      if (!r.ok) throw d;
      return d;
    });
  }

  async function loadRoommates(reset) {
    if (_loading) return;
    _loading = true;
    if (reset) _page = 1;

    const container = document.getElementById('roommate-cards');
    if (!container) { _loading = false; return; }
    if (reset) container.innerHTML = '<div class="spinner" style="margin:24px auto"></div>';

    const params = new URLSearchParams({ page: _page });
    if (_filters.location) params.set('location', _filters.location);
    if (_filters.gender_preference && _filters.gender_preference !== 'Any') params.set('gender_preference', _filters.gender_preference);

    try {
      const data = await _roommateApi('GET', '/api/roommates?' + params.toString());
      if (!document.getElementById('roommate-cards')) { _loading = false; return; }
      const items = data.items || [];
      if (reset) container.innerHTML = '';

      if (!items.length && _page === 1) {
        container.innerHTML = '<div class="empty-state" style="text-align:center;padding:32px"><div style="font-size:2rem">🏠</div><p>No roommate listings yet. Be the first!</p></div>';
        _loading = false; return;
      }

      items.forEach(item => {
        const card = document.createElement('div');
        card.className = 'card roommate-card';
        card.style.marginBottom = '12px';
        card.innerHTML = `
          <div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:8px">
            <strong>${escHtml(item.poster_name)}</strong>
            <span class="budget-badge">KES ${item.budget_min.toLocaleString()} – ${item.budget_max.toLocaleString()}/mo</span>
            <span class="gender-badge">${escHtml(item.gender_preference)}</span>
          </div>
          <div style="font-size:.85rem;color:var(--text-muted);margin-bottom:6px">📍 ${escHtml(item.location)}${item.institution ? ' · ' + escHtml(item.institution) : ''}</div>
          ${item.move_in_date ? `<div style="font-size:.82rem;color:var(--text-muted);margin-bottom:6px">Move-in: ${escHtml(item.move_in_date)}</div>` : ''}
          <p style="font-size:.88rem;margin-bottom:10px">${escHtml(item.description)}</p>
          <button class="btn btn-primary" style="font-size:.82rem;padding:6px 16px" onclick="window._contactRoommate('${escHtml(item.poster_contact)}', '${escHtml(item.poster_name)}')">Contact</button>
          <span style="font-size:.72rem;color:var(--text-muted);margin-left:8px">${timeAgo(item.created_at)}</span>
        `;
        container.appendChild(card);
      });

      const loadMoreBtn = document.getElementById('roommate-load-more');
      if (loadMoreBtn) {
        loadMoreBtn.style.display = data.page < data.pages ? 'block' : 'none';
      }
      _page++;
    } catch (e) {
      if (document.getElementById('roommate-cards')) {
        document.getElementById('roommate-cards').innerHTML += '<div style="color:#ef4444;padding:12px">Failed to load listings.</div>';
      }
    }
    _loading = false;
  }

  window._contactRoommate = function (contact, name) {
    openModal(`
      <div style="max-width:320px;margin:0 auto;text-align:center">
        <h3 style="margin-bottom:12px">Contact ${escHtml(name)}</h3>
        <p style="font-size:1rem;font-weight:600;margin-bottom:16px">${escHtml(contact)}</p>
        <p style="font-size:.85rem;color:var(--text-muted)">Reach out directly via phone, WhatsApp, or email above.</p>
      </div>
    `);
  };

  function openRoommateForm() {
    openModal(`
      <div style="max-width:400px;margin:0 auto">
        <h3 style="margin-bottom:14px">🏠 Find a Roommate</h3>
        <div style="margin-bottom:10px">
          <label class="form-label">Your Name *</label>
          <input id="rm-name" class="form-input" placeholder="Full name">
        </div>
        <div style="margin-bottom:10px">
          <label class="form-label">Contact (phone/email/WhatsApp) *</label>
          <input id="rm-contact" class="form-input" placeholder="0712 345 678">
        </div>
        <div style="margin-bottom:10px">
          <label class="form-label">Institution (optional)</label>
          <input id="rm-institution" class="form-input" placeholder="University / College">
        </div>
        <div style="margin-bottom:10px">
          <label class="form-label">Location / Area *</label>
          <input id="rm-location" class="form-input" placeholder="e.g. Westlands, Nairobi">
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:10px">
          <div>
            <label class="form-label">Budget Min (KES)</label>
            <input id="rm-bmin" class="form-input" type="number" min="0" placeholder="3000">
          </div>
          <div>
            <label class="form-label">Budget Max (KES)</label>
            <input id="rm-bmax" class="form-input" type="number" min="0" placeholder="8000">
          </div>
        </div>
        <div style="margin-bottom:10px">
          <label class="form-label">Gender Preference</label>
          <select id="rm-gender" class="form-input">
            <option value="Any">Any</option>
            <option value="Male">Male</option>
            <option value="Female">Female</option>
          </select>
        </div>
        <div style="margin-bottom:10px">
          <label class="form-label">Move-in Date (optional)</label>
          <input id="rm-movein" class="form-input" type="date">
        </div>
        <div style="margin-bottom:14px">
          <label class="form-label">Description *</label>
          <textarea id="rm-desc" class="form-input" rows="3" placeholder="About you, lifestyle, what you're looking for…"></textarea>
        </div>
        <div id="rm-error" style="color:#ef4444;font-size:.82rem;margin-bottom:8px;display:none"></div>
        <button class="btn btn-primary" style="width:100%" onclick="window._submitRoommate()">Post Listing</button>
      </div>
    `);
  }

  window._submitRoommate = async function () {
    const name = (document.getElementById('rm-name').value || '').trim();
    const contact = (document.getElementById('rm-contact').value || '').trim();
    const institution = (document.getElementById('rm-institution').value || '').trim();
    const location = (document.getElementById('rm-location').value || '').trim();
    const bmin = parseInt(document.getElementById('rm-bmin').value) || 0;
    const bmax = parseInt(document.getElementById('rm-bmax').value) || 0;
    const gender = document.getElementById('rm-gender').value;
    const movein = (document.getElementById('rm-movein').value || '').trim();
    const desc = (document.getElementById('rm-desc').value || '').trim();
    const errEl = document.getElementById('rm-error');
    errEl.style.display = 'none';

    if (!name || !contact || !location || !desc) {
      errEl.textContent = 'Please fill in all required fields.';
      errEl.style.display = 'block';
      return;
    }
    try {
      const res = await _roommateApi('POST', '/api/roommates', {
        poster_name: name, poster_contact: contact, institution, location,
        budget_min: bmin, budget_max: bmax, gender_preference: gender,
        move_in_date: movein, description: desc,
      });
      closeModal();
      showToast('Listing posted!', 'success');
      if (res.owner_token) {
        showToast('Save your edit token: ' + res.owner_token, 'info');
      }
      loadRoommates(true);
    } catch (e) {
      errEl.textContent = (e && e.error) ? e.error : 'Failed to post listing.';
      errEl.style.display = 'block';
    }
  };

  window.renderRoommates = function () {
    const main = document.getElementById('main-content');
    main.innerHTML = `
      <div style="margin-bottom:14px">
        <h2 style="font-size:1.1rem;margin-bottom:10px">🏠 Roommate Finder</h2>
        <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px">
          <input id="filter-location" class="form-input" style="flex:1;min-width:140px" placeholder="Filter by location…" value="${escHtml(_filters.location)}" oninput="window._rmFilter()">
          <select id="filter-gender" class="form-input" style="min-width:120px" onchange="window._rmFilter()">
            <option value="Any"${_filters.gender_preference === 'Any' ? ' selected' : ''}>Any gender</option>
            <option value="Male"${_filters.gender_preference === 'Male' ? ' selected' : ''}>Male</option>
            <option value="Female"${_filters.gender_preference === 'Female' ? ' selected' : ''}>Female</option>
          </select>
        </div>
      </div>
      <div id="roommate-cards"></div>
      <div style="text-align:center;margin:12px 0">
        <button id="roommate-load-more" class="btn" style="display:none" onclick="loadRoommates(false)">Load More</button>
      </div>
      <button class="fab-btn" style="position:fixed;bottom:80px;right:16px;background:#6C3CE1;color:white;border:none;border-radius:50px;padding:12px 20px;font-size:.9rem;font-weight:700;cursor:pointer;z-index:50;box-shadow:0 4px 12px rgba(108,60,225,0.4)" onclick="window._openRoommateForm()">🏠 Find Roommate</button>
    `;
    window._openRoommateForm = openRoommateForm;
    loadRoommates(true);
  };

  window._rmFilter = function () {
    _filters.location = (document.getElementById('filter-location').value || '').trim();
    _filters.gender_preference = document.getElementById('filter-gender').value;
    loadRoommates(true);
  };

  window.loadRoommates = loadRoommates;
})();
