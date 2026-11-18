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
    withAds.forEach(item => {
      if (item.type === 'ad') { html += renderAdBanner(item); return; }
      if (item.section === 'community') html += renderPostCard(item);
      else if (item.section === 'marketplace') html += renderMarketCard(item);
      else if (item.section === 'lostandfound') html += renderLFCard(item);
      else if (item.section === 'announcement') html += renderAnnCard(item);
    });
    mc.innerHTML = html;
  } catch(e) {
    mc.innerHTML = '<div class="empty-state"><div class="empty-icon">&#128565;</div><p>Could not load feed.</p></div>';
  }
}

function renderPostCard(p) {
  return `<div class="card">
    <div class="card-header">
      <div class="avatar">${escHtml(avatarLetter(p.poster_name))}</div>
      <div class="poster-info"><div class="poster-name">${escHtml(p.poster_name)}</div><div class="post-time">${timeAgo(p.created_at)}</div></div>
    </div>
    <div class="card-title">${escHtml(p.title)}</div>
    <div class="card-body">${escHtml(p.body)}</div>
    <div class="card-meta"><span class="badge">${escHtml(p.topic || 'General')}</span><span class="badge badge-accent">Community</span></div>
  </div>`;
}

function renderMarketCard(m) {
  return `<div class="card">
    ${m.image_path ? `<img class="card-image" src="/api/uploads/${escHtml(m.image_path)}" alt="">` : ''}
    <div class="card-title">${escHtml(m.title)}</div>
    <div class="card-body">${escHtml(m.description)}</div>
    ${m.price ? `<div class="card-price">KSh ${escHtml(m.price)}</div>` : ''}
    <div class="card-meta"><span class="badge badge-accent">${escHtml(m.category)}</span><span class="badge">Marketplace</span></div>
    <div class="contact-row">&#128222; ${escHtml(m.poster_contact)} &bull; ${escHtml(m.poster_name)} &bull; ${timeAgo(m.created_at)}</div>
  </div>`;
}

function renderLFCard(l) {
  const cls = l.item_type === 'lost' ? 'badge-red' : 'badge-green';
  return `<div class="card">
    <div class="card-title">${escHtml(l.title)}</div>
    <div class="card-body">${escHtml(l.description)}</div>
    <div class="card-meta"><span class="badge ${cls}">${l.item_type === 'lost' ? 'Lost' : 'Found'}</span><span class="badge">Lost &amp; Found</span></div>
    <div class="contact-row">&#128205; ${escHtml(l.location)} &bull; ${escHtml(l.poster_contact)} &bull; ${timeAgo(l.created_at)}</div>
  </div>`;
}

function renderAnnCard(a) {
  return `<div class="card announcement-card">
    ${a.pinned ? '<span class="pinned-badge">&#128204; Pinned</span>' : ''}
    <div class="card-title">${escHtml(a.title)}</div>
    <div class="card-body">${escHtml(a.body)}</div>
    <div class="card-meta"><span class="badge">Announcement</span><span style="font-size:0.75rem;color:var(--text-muted)">${timeAgo(a.created_at)}</span></div>
  </div>`;
}
