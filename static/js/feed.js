async function renderFeed() {
  const mc = document.getElementById('main-content');
  mc.innerHTML = '<div class="spinner"></div>';
  try {
    const items = await api('GET', '/api/feed');
    const withAds = injectAds(items);
    if (!withAds.length) {
      mc.innerHTML = '<div class="empty-state"><div class="empty-icon">&#127968;</div><p>No posts yet. Be the first!</p></div>';
      return;
    }
    let html = '<div class="section-header"><h2 class="section-title">&#127968; Feed &mdash; What\'s happening</h2></div>';

    // Institution quick-access
    const myInst = (() => { try { return JSON.parse(localStorage.getItem('cc_my_institution') || 'null'); } catch(e) { return null; } })();
    if (myInst && myInst.id) {
      html += `<div style="margin-bottom:12px"><button class="inst-quick-btn" onclick="openInstitutionCommunity(${myInst.id})">🏫 ${escHtml(myInst.abbreviation || myInst.name)} Community</button></div>`;
    } else {
      html += `<div style="margin-bottom:12px"><button class="inst-quick-btn" onclick="navigate('institutions')">🏫 Find Your Institution</button></div>`;
    }
    withAds.forEach(item => {
      if (item.type === 'ad') { html += renderAdBanner(item); return; }
      if (item.section === 'community') html += renderPostCard(item);
      else if (item.section === 'marketplace') html += renderMarketCard(item);
      else if (item.section === 'lostandfound') html += renderLFCard(item);
      else if (item.section === 'announcement') html += renderAnnCard(item);
    });
    mc.innerHTML = html;

    // Wire up click-to-open on every card
    mc.querySelectorAll('.card[data-id]').forEach(card => {
      card.style.cursor = 'pointer';
      card.addEventListener('click', e => {
        // Don't trigger if clicking a button or link inside the card
        if (e.target.closest('button, a')) return;
        const id      = card.dataset.id;
        const section = card.dataset.section;
        openDetailModal(id, section);
      });
    });
  } catch(e) {
    mc.innerHTML = '<div class="empty-state"><div class="empty-icon">&#128565;</div><p>Could not load feed.</p></div>';
  }
}

async function openDetailModal(id, section) {
  openModal('<div class="spinner"></div>');
  try {
    if (section === 'community') {
      const [post, comments] = await Promise.all([
        api('GET', `/api/posts`).then(r => (r.posts || r).find(p => String(p.id) === String(id))),
        api('GET', `/api/posts/${id}/comments`).catch(() => [])
      ]);
      if (!post) { closeModal(); return; }
      const commList = Array.isArray(comments) ? comments : (comments.comments || []);
      openModal(`
        <div class="detail-modal">
          <div class="card-header">
            <div class="avatar">${escHtml(avatarLetter(post.poster_name))}</div>
            <div class="poster-info">
              <div class="poster-name">${escHtml(post.poster_name)}</div>
              <div class="post-time">${timeAgo(post.created_at)}</div>
            </div>
          </div>
          <h3 style="margin:12px 0 6px">${escHtml(post.title)}</h3>
          <p style="color:#374151;line-height:1.6">${escHtml(post.body)}</p>
          <div class="card-meta" style="margin-top:10px">
            <span class="badge">${escHtml(post.topic || 'General')}</span>
          </div>
          <hr style="margin:16px 0;border:none;border-top:1px solid #e5e7eb">
          <h4 style="margin-bottom:10px">💬 Comments (${commList.length})</h4>
          <div id="comments-list">
            ${commList.length === 0 ? '<p style="color:#9ca3af;font-size:0.88rem">No comments yet. Be the first!</p>' :
              commList.map(c => `
                <div style="padding:8px 0;border-bottom:1px solid #f3f4f6">
                  <strong style="font-size:0.88rem">${escHtml(c.poster_name)}</strong>
                  <span style="font-size:0.75rem;color:#9ca3af;margin-left:8px">${timeAgo(c.created_at)}</span>
                  <p style="margin:4px 0;font-size:0.9rem;color:#374151">${escHtml(c.body)}</p>
                </div>`).join('')}
          </div>
          <div style="margin-top:14px">
            <input id="comment-name" class="form-input" placeholder="Your name" style="margin-bottom:6px">
            <textarea id="comment-body" class="form-input" placeholder="Write a comment…" rows="2" style="resize:none"></textarea>
            <button id="submit-comment" class="btn btn-primary" style="margin-top:6px;width:100%">Post Comment</button>
          </div>
        </div>
      `);
      document.getElementById('submit-comment').addEventListener('click', async () => {
        const name = document.getElementById('comment-name').value.trim();
        const body = document.getElementById('comment-body').value.trim();
        if (!name || !body) { showToast('Please enter your name and comment', 'error'); return; }
        try {
          await api('POST', `/api/posts/${id}/comments`, { poster_name: name, body });
          openDetailModal(id, section); // refresh
        } catch(e) { showToast('Failed to post comment', 'error'); }
      });
    } else if (section === 'marketplace') {
      const items = await api('GET', '/api/marketplace');
      const item = (items.items || items).find(m => String(m.id) === String(id));
      if (!item) { closeModal(); return; }
      openModal(`
        <div class="detail-modal">
          ${item.image_path ? `<img src="/api/uploads/${escHtml(item.image_path)}" style="width:100%;border-radius:8px;margin-bottom:12px;max-height:220px;object-fit:cover">` : ''}
          <h3 style="margin-bottom:6px">${escHtml(item.title)}</h3>
          <div class="card-price" style="font-size:1.3rem;margin-bottom:8px">${item.price ? 'KSh ' + Number(item.price).toLocaleString() : 'Price not listed'}</div>
          <p style="color:#374151;line-height:1.6;margin-bottom:12px">${escHtml(item.description)}</p>
          <div class="card-meta"><span class="badge badge-accent">${escHtml(item.category)}</span>${item.sold ? '<span class="badge badge-red">Sold</span>' : ''}</div>
          <hr style="margin:14px 0;border:none;border-top:1px solid #e5e7eb">
          <div style="font-size:0.9rem;color:#374151">
            <p>👤 <strong>${escHtml(item.poster_name)}</strong></p>
            ${item.poster_contact ? `<p>📞 <a href="tel:${escHtml(item.poster_contact)}" style="color:#6C3CE1;font-weight:600">${escHtml(item.poster_contact)}</a></p>` : ''}
            <p style="color:#9ca3af;font-size:0.78rem">Posted ${timeAgo(item.created_at)}</p>
          </div>
        </div>
      `);
    } else if (section === 'lostandfound') {
      const items = await api('GET', '/api/lostandfound');
      const item = (items.items || items).find(l => String(l.id) === String(id));
      if (!item) { closeModal(); return; }
      const cls = item.item_type === 'lost' ? 'badge-red' : 'badge-green';
      openModal(`
        <div class="detail-modal">
          <span class="badge ${cls}" style="font-size:0.9rem;padding:4px 12px">${item.item_type === 'lost' ? '🔴 Lost' : '🟢 Found'}</span>
          <h3 style="margin:10px 0 6px">${escHtml(item.title)}</h3>
          <p style="color:#374151;line-height:1.6;margin-bottom:12px">${escHtml(item.description)}</p>
          <hr style="margin:14px 0;border:none;border-top:1px solid #e5e7eb">
          <div style="font-size:0.9rem;color:#374151">
            <p>📍 <strong>${escHtml(item.location)}</strong></p>
            <p>👤 <strong>${escHtml(item.poster_name)}</strong></p>
            ${item.poster_contact ? `<p>📞 <a href="tel:${escHtml(item.poster_contact)}" style="color:#6C3CE1;font-weight:600">${escHtml(item.poster_contact)}</a></p>` : ''}
            <p style="color:#9ca3af;font-size:0.78rem">Posted ${timeAgo(item.created_at)}</p>
          </div>
        </div>
      `);
    } else if (section === 'announcement') {
      const items = await api('GET', '/api/announcements');
      const item = (items.announcements || items).find(a => String(a.id) === String(id));
      if (!item) { closeModal(); return; }
      openModal(`
        <div class="detail-modal">
          ${item.pinned ? '<span class="pinned-badge">📌 Pinned</span>' : ''}
          <h3 style="margin:10px 0 8px">${escHtml(item.title)}</h3>
          <p style="color:#374151;line-height:1.6">${escHtml(item.body)}</p>
          <p style="color:#9ca3af;font-size:0.78rem;margin-top:12px">Posted ${timeAgo(item.created_at)}</p>
        </div>
      `);
    }
  } catch(e) {
    openModal('<div class="empty-state"><p>Could not load details.</p></div>');
  }
}

function renderPostCard(p) {
  return `<div class="card" data-id="${p.id}" data-section="community">
    <div class="card-header">
      <div class="avatar">${escHtml(avatarLetter(p.poster_name))}</div>
      <div class="poster-info"><div class="poster-name">${escHtml(p.poster_name)}</div><div class="post-time">${timeAgo(p.created_at)}</div></div>
    </div>
    <div class="card-title">${escHtml(p.title)}</div>
    <div class="card-body">${escHtml(p.body)}</div>
    <div class="card-meta"><span class="badge">${escHtml(p.topic || 'General')}</span><span class="badge badge-accent">Community</span><span style="font-size:0.75rem;color:#9ca3af;margin-left:auto">Tap to read &amp; comment →</span></div>
    <div style="margin-top:6px;text-align:right"><button class="report-btn" onclick="event.stopPropagation();openReportModal('post',${p.id})" style="background:none;border:none;color:#9ca3af;font-size:0.75rem;cursor:pointer;padding:2px 4px">🚩 Report</button></div>
  </div>`;
}

function renderMarketCard(m) {
  return `<div class="card" data-id="${m.id}" data-section="marketplace">
    ${m.image_path ? `<img class="card-image" src="/api/uploads/${escHtml(m.image_path)}" alt="">` : ''}
    <div class="card-title">${escHtml(m.title)}</div>
    <div class="card-body">${escHtml(m.description)}</div>
    ${m.price ? `<div class="card-price">KSh ${Number(m.price).toLocaleString()}</div>` : ''}
    <div class="card-meta"><span class="badge badge-accent">${escHtml(m.category)}</span><span class="badge">Marketplace</span><span style="font-size:0.75rem;color:#9ca3af;margin-left:auto">Tap for details →</span></div>
    <div class="contact-row">&#128222; ${escHtml(m.poster_contact)} &bull; ${escHtml(m.poster_name)} &bull; ${timeAgo(m.created_at)}</div>
    <div style="margin-top:6px;text-align:right"><button class="report-btn" onclick="event.stopPropagation();openReportModal('marketplace',${m.id})" style="background:none;border:none;color:#9ca3af;font-size:0.75rem;cursor:pointer;padding:2px 4px">🚩 Report</button></div>
  </div>`;
}

function renderLFCard(l) {
  const cls = l.item_type === 'lost' ? 'badge-red' : 'badge-green';
  return `<div class="card" data-id="${l.id}" data-section="lostandfound">
    <div class="card-title">${escHtml(l.title)}</div>
    <div class="card-body">${escHtml(l.description)}</div>
    <div class="card-meta"><span class="badge ${cls}">${l.item_type === 'lost' ? 'Lost' : 'Found'}</span><span class="badge">Lost &amp; Found</span><span style="font-size:0.75rem;color:#9ca3af;margin-left:auto">Tap for details →</span></div>
    <div class="contact-row">&#128205; ${escHtml(l.location)} &bull; ${escHtml(l.poster_contact)} &bull; ${timeAgo(l.created_at)}</div>
    <div style="margin-top:6px;text-align:right"><button class="report-btn" onclick="event.stopPropagation();openReportModal('lostandfound',${l.id})" style="background:none;border:none;color:#9ca3af;font-size:0.75rem;cursor:pointer;padding:2px 4px">🚩 Report</button></div>
  </div>`;
}

function renderAnnCard(a) {
  return `<div class="card announcement-card" data-id="${a.id}" data-section="announcement">
    ${a.pinned ? '<span class="pinned-badge">&#128204; Pinned</span>' : ''}
    <div class="card-title">${escHtml(a.title)}</div>
    <div class="card-body">${escHtml(a.body)}</div>
    <div class="card-meta"><span class="badge">Announcement</span><span style="font-size:0.75rem;color:var(--text-muted)">${timeAgo(a.created_at)}</span><span style="font-size:0.75rem;color:#9ca3af;margin-left:auto">Tap to read →</span></div>
  </div>`;
}
